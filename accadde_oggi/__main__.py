"""IL CINEGIORNALE DI OGGI — ogni giorno uno Short automatico con un cinegiornale d'epoca
di pubblico dominio uscito in questa stessa data, con testo scritto dalla sua scheda d'archivio.

Uso:
    python -m accadde_oggi            giro completo (cerca, scrive, monta, pubblica)
    python -m accadde_oggi --demo     prova solo il montaggio con un filmato finto

Variabili d'ambiente utili:
    PROVA=1        monta ma non pubblica
    PRIVACY=...    public (predefinito), unlisted o private
    DATA=AAAA-MM-GG  forza una data diversa da oggi
    FORZA=1        pubblica anche se oggi è già uscito un video
"""

import datetime as dt
import json
import os
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from . import cinegiornali, montaggio
from .eventi import MESI
from .fonti import scarica
from .verifica import IANonDisponibile, Redattore

RADICE = Path(__file__).resolve().parent.parent
STORICO = RADICE / "storico.json"
USCITA = RADICE / "output"
MAX_PER_GIORNO = 4
# prima oggi, poi i giorni vicini, poi sempre più lontano fino a coprire tutto l'anno:
# così esce sempre un video, e la data scritta è sempre quella vera.
SCOSTAMENTI = [0] + [segno * k for k in range(1, 184) for segno in (-1, 1)]


ORA_PUBBLICAZIONE = dt.time(10, 0)


def oggi():
    """Giorno di USCITA del video: il video si prepara il giorno prima e YouTube
    lo rende pubblico da solo alle 10:00 di questo giorno."""
    if os.environ.get("DATA"):
        return dt.date.fromisoformat(os.environ["DATA"])
    return dt.datetime.now(ZoneInfo("Europe/Rome")).date() + dt.timedelta(days=1)


def ora_di_uscita(data):
    return dt.datetime.combine(data, ORA_PUBBLICAZIONE, tzinfo=ZoneInfo("Europe/Rome"))


def leggi_storico():
    storico = {"video": []}
    if STORICO.exists():
        storico = json.loads(STORICO.read_text(encoding="utf-8"))
    storico.setdefault("video", [])
    storico.setdefault("scartati", {})
    return storico


def salva_storico(storico):
    STORICO.write_text(json.dumps(storico, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def segna_scartato(storico, filmato, motivo):
    storico["scartati"][filmato["id"]] = motivo[:200]
    salva_storico(storico)


def data_del(candidato, giorno, mese):
    return dt.date(candidato["anno"], mese, giorno)


def titolo_youtube(scheda, data_uscita):
    return f"{data_uscita.day} {MESI[data_uscita.month - 1]} {data_uscita.year}: " \
           f"{scheda['titolo']}"[:100]


def descrizione_youtube(scheda, data_uscita, anni_fa, filmato, stesso_giorno=True):
    formula = ("Ogni giorno un cinegiornale d'epoca, uscito proprio in questa data."
               if stesso_giorno else "Ogni giorno un cinegiornale d'epoca dall'archivio Universal.")
    return "\n".join([
        f"{scheda['titolo']}",
        "",
        f"{scheda['testo']}",
        "",
        f"Cinegiornale Universal uscito il {data_uscita.day} {MESI[data_uscita.month - 1]} "
        f"{data_uscita.year}, {anni_fa} anni fa. {formula}",
        "",
        "FONTE",
        f"Titolo originale: \"{filmato['titolo']}\"",
        f"{filmato['pagina']}",
        "Universal Newsreel — Internet Archive, collezione universal_newsreels",
        f"Licenza del filmato: Pubblico dominio ({filmato['licenza_url']})",
        "Il testo italiano è un riassunto della scheda d'archivio originale.",
        "",
        f"#cinegiornale #storia #{data_uscita.year} #accaddeoggi #shorts",
    ])


GIORNI_DI_SCORTA = 3  # si tengono pronti i video dei prossimi 3 giorni


def giro_completo():
    """Prepara i video mancanti dei prossimi giorni. Non fallisce mai: ogni problema
    viene recuperato dal giro successivo, che ha giorni di margine."""
    for k in range(GIORNI_DI_SCORTA if not os.environ.get("DATA") else 1):
        giorno = oggi() + dt.timedelta(days=k)
        try:
            prepara(giorno)
        except Exception as errore:  # noqa: BLE001 — si riprova al prossimo giro
            print(f"Problema sul video del {giorno}: {errore!r}. Riprova il prossimo giro.")
    return 0


def scheda_dal_titolo(filmato):
    """Riserva senza IA: titolo originale d'archivio, quindi sempre fedele."""
    titolo = re.sub(r",?\s*\d{4}/\d{2}/\d{2}\s*$", "", filmato["titolo"]).strip() or filmato["id"]
    return {"titolo": titolo[:55], "testo": "Titolo originale del cinegiornale Universal dell'epoca."}


def prepara(data):
    storico = leggi_storico()
    if any(v["data"] == data.isoformat() and v.get("youtube_id") for v in storico["video"]) \
            and not os.environ.get("FORZA"):
        print(f"Il video del {data} è già pronto e programmato. Fine.")
        return 0
    ogni = int(os.environ.get("OGNI_QUANTI_GIORNI") or 1)
    if ogni > 1 and data.toordinal() % ogni and not os.environ.get("FORZA"):
        print(f"Si pubblica un giorno ogni {ogni}: oggi riposo.")
        return 0
    redattore = Redattore()
    cinegiornali.catalogo()
    un_anno_fa = (data - dt.timedelta(days=365)).isoformat()
    # passata 1: mai usati. Passata 2 (scorta finita): si riusano quelli usciti più di un anno fa.
    for recenti_soltanto in (False, True):
        pubblicati = [v for v in storico["video"]
                      if not recenti_soltanto or v["data"] >= un_anno_fa]
        gia_usati = {v["id_filmato"] for v in pubblicati} | set(storico["scartati"])
        if _cerca(data, storico, redattore, gia_usati) is not None:
            return 0
    print("Nessun cinegiornale disponibile.")
    return 0


def _cerca(data, storico, redattore, gia_usati):
    giorni_visti = set()
    if True:
        for scostamento in SCOSTAMENTI:
            giorno_cercato = data + dt.timedelta(days=scostamento)
            g, m = giorno_cercato.day, giorno_cercato.month
            if (g, m) in giorni_visti:
                continue
            giorni_visti.add((g, m))
            lista = [c for c in cinegiornali.candidati(g, m)
                     if c["id"] not in gia_usati and c["anno"] < data.year]
            if not lista:
                continue
            random.shuffle(lista)
            lista.sort(key=lambda c: cinegiornali.priorita(c, data.year), reverse=True)
            print(f"=== Cinegiornali usciti il {g} {MESI[m - 1]}: {len(lista)} disponibili ===")
            for filmato in lista[:MAX_PER_GIORNO]:
                data_uscita = data_del(filmato, g, m)
                print(f"→ {filmato['id']}")
                gia_usati.add(filmato["id"])
                try:
                    filmato["url_video"], motivo = cinegiornali.link_video(filmato)
                except (requests.RequestException, ValueError) as errore:
                    print(f"  Scheda non raggiungibile ({errore}), riproverò un altro giorno.")
                    continue
                if not filmato["url_video"]:
                    print(f"  Saltato: {motivo}")
                    segna_scartato(storico, filmato, motivo)
                    continue
                try:
                    if not redattore.disponibile():
                        raise IANonDisponibile("limite di controlli raggiunto")
                    scheda, esito = redattore.scrivi_scheda(filmato, data_uscita)
                except IANonDisponibile as errore:
                    print(f"  IA non disponibile ({errore}): uso il titolo originale d'archivio.")
                    scheda, esito = scheda_dal_titolo(filmato), "senza IA: titolo originale"
                print(f"  Redattore: {esito}")
                if not scheda:
                    if esito.startswith("scartato"):
                        segna_scartato(storico, filmato, esito)
                    continue
                filmato["verifica"] = esito
                risultato = produci(scheda, filmato, data, data_uscita, scostamento, storico)
                if risultato is not None:
                    return risultato
    salva_storico(storico)
    return None


def produci(scheda, filmato, data, data_uscita, scostamento, storico):
    print(f"  Filmato pronto: {filmato['titolo']}")
    if scostamento == 0:
        etichetta = "IL CINEGIORNALE DI OGGI"
    elif abs(scostamento) <= 3:
        etichetta = "CINEGIORNALE DELLA SETTIMANA"
    else:
        etichetta = "DALL'ARCHIVIO DEI CINEGIORNALI"
    anni_fa = data.year - data_uscita.year
    evento = {"anno": data_uscita.year, "titolo": scheda["titolo"], "testo": scheda["testo"]}
    with tempfile.TemporaryDirectory() as lavoro:
        sorgente = scarica(filmato["url_video"], Path(lavoro) / "sorgente.mp4")
        crediti = ["Filmato: Universal Newsreel · Pubblico dominio",
                   "Fonte: Internet Archive"]
        USCITA.mkdir(exist_ok=True)
        file_short = USCITA / f"accadde-oggi-{data.isoformat()}.mp4"
        try:
            segmento = montaggio.monta(sorgente, evento, data_uscita, anni_fa, crediti,
                                       file_short, lavoro, etichetta)
        except (ValueError, subprocess.CalledProcessError, StopIteration) as errore:
            print("  Montaggio non riuscito, provo il prossimo:", errore)
            segna_scartato(storico, filmato, f"montaggio: {errore}")
            return None

    voce = {"data": data.isoformat(), "data_uscita": data_uscita.isoformat(),
            "titolo": scheda["titolo"], "testo": scheda["testo"], "fonte": filmato["fonte"],
            "id_filmato": filmato["id"], "pagina_filmato": filmato["pagina"],
            "verifica": filmato.get("verifica", ""), **segmento}
    titolo = titolo_youtube(scheda, data_uscita)
    descrizione = descrizione_youtube(scheda, data_uscita, anni_fa, filmato, scostamento == 0)
    (USCITA / "ultimo-video.txt").write_text(
        titolo + "\n\n" + descrizione + "\n\n[Controllo redattore IA: "
        + filmato.get("verifica", "") + "]\n[Descrizione d'archivio originale: "
        + filmato.get("descrizione", "") + "]", encoding="utf-8")

    from . import youtube
    if os.environ.get("PROVA") == "1":
        print("Modalità prova: video creato ma non pubblicato.")
        return 0
    if not youtube.credenziali_presenti():
        # Strada gratuita: il video va in una Release di GitHub e nel feed RSS,
        # Zapier lo vede e lo carica su YouTube.
        from . import feed
        tag_release = f"short-{data.isoformat()}"
        url = feed.url_release(tag_release, file_short.name)
        if os.environ.get("GITHUB_ACTIONS"):
            note = USCITA / f"note-{data.isoformat()}.txt"
            note.write_text(titolo + "\n\n" + descrizione, encoding="utf-8")
            esiste = subprocess.run(["gh", "release", "view", tag_release],
                                    capture_output=True).returncode == 0
            comando = (["gh", "release", "upload", tag_release, str(file_short), "--clobber"]
                       if esiste else
                       ["gh", "release", "create", tag_release, str(file_short),
                        "--title", tag_release, "--notes-file", str(note)])
            caricato = subprocess.run(comando, capture_output=True, text=True)
            if caricato.returncode != 0:
                raise RuntimeError(f"caricamento su GitHub non riuscito: {caricato.stderr[-300:]}")
        feed.aggiungi(RADICE / "feed.xml", titolo, descrizione, url, tag_release,
                      file_short.stat().st_size, ora_di_uscita(data))
        voce["youtube_id"] = "zapier:" + tag_release
        storico["video"].append(voce)
        salva_storico(storico)
        print(f"Video pronto per Zapier: {url}")
        return 0
    tag = ["cinegiornale", "storia", "filmati d'epoca", "accadde oggi", str(data_uscita.year)]
    privacy = os.environ.get("PRIVACY") or "public"
    voce["youtube_id"] = youtube.carica(file_short, titolo, descrizione, tag, privacy)
    voce["privacy"] = privacy
    storico["video"].append(voce)
    salva_storico(storico)
    if youtube.usa_uploadpost():
        print(f"Inviato a Upload-Post (richiesta {voce['youtube_id']}).")
    else:
        print(f"Pubblicato: https://youtube.com/shorts/{voce['youtube_id']}")
    return 0


def demo():
    """Prova il montaggio senza internet: filmato finto in stile pellicola."""
    USCITA.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as lavoro:
        finto = Path(lavoro) / "finto.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "testsrc2=s=640x480:r=24:d=70", "-f", "lavfi", "-i",
                        "sine=f=220:d=70", "-vf", "hue=s=0,noise=alls=25:allf=t",
                        "-c:v", "libx264", "-c:a", "aac", "-shortest", str(finto)], check=True)
        data = dt.date(2026, 10, 16)
        evento = {"anno": 1961, "titolo": "Aerei civili a terra per l'allerta difesa",
                  "testo": "Un'esercitazione della difesa civile chiude gli aeroporti per 12 "
                  "ore: è l'operazione Sky Shield."}
        crediti = ["Filmato: Universal Newsreel · Pubblico dominio", "Fonte: Internet Archive"]
        montaggio.monta(finto, evento, data, 65, crediti, USCITA / "demo.mp4", lavoro,
                        "IL CINEGIORNALE DI OGGI")
    print("Creato:", USCITA / "demo.mp4")


if __name__ == "__main__":
    sys.exit(demo() if "--demo" in sys.argv else giro_completo())
