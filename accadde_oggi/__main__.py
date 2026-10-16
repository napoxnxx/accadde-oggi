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
import time
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
# prima oggi, poi i giorni vicini, poi sempre più lontano fino a ±30 giorni:
# così esce sempre un video, e la data scritta è sempre quella vera.
SCOSTAMENTI = [0] + [segno * k for k in range(1, 31) for segno in (-1, 1)]


def oggi():
    if os.environ.get("DATA"):
        return dt.date.fromisoformat(os.environ["DATA"])
    return dt.datetime.now(ZoneInfo("Europe/Rome")).date()


def leggi_storico():
    if STORICO.exists():
        return json.loads(STORICO.read_text(encoding="utf-8"))
    return {"video": []}


def salva_storico(storico):
    STORICO.write_text(json.dumps(storico, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def giro_completo():
    data = oggi()
    storico = leggi_storico()
    if any(v["data"] == data.isoformat() and v.get("youtube_id") for v in storico["video"]) \
            and not os.environ.get("FORZA"):
        print(f"Oggi ({data}) è già stato pubblicato un video. Fine.")
        return 0
    ogni = int(os.environ.get("OGNI_QUANTI_GIORNI") or 1)
    if ogni > 1 and data.toordinal() % ogni and not os.environ.get("FORZA"):
        print(f"Si pubblica un giorno ogni {ogni}: oggi riposo.")
        return 0
    gia_usati = {v["id_filmato"] for v in storico["video"]}
    redattore = Redattore()

    try:
        for scostamento in SCOSTAMENTI:
            if not redattore.disponibile():
                print("Limite di controlli raggiunto per oggi.")
                break
            if scostamento:
                time.sleep(1)  # gentili con archive.org
            giorno_cercato = data + dt.timedelta(days=scostamento)
            g, m = giorno_cercato.day, giorno_cercato.month
            print(f"=== Cinegiornali usciti il {g} {MESI[m - 1]} ===")
            try:
                lista = cinegiornali.candidati(g, m)
            except (requests.RequestException, ValueError) as errore:
                print(f"  Archivio non raggiungibile: {errore}")
                continue
            lista = [c for c in lista if c["id"] not in gia_usati and c["anno"] < data.year]
            random.shuffle(lista)
            lista.sort(key=lambda c: cinegiornali.priorita(c, data.year), reverse=True)
            print(f"  {len(lista)} disponibili")
            for filmato in lista[:MAX_PER_GIORNO]:
                if not redattore.disponibile():
                    print("Limite di controlli raggiunto per oggi.")
                    break
                data_uscita = data_del(filmato, g, m)
                print(f"→ {filmato['id']}")
                scheda, esito = redattore.scrivi_scheda(filmato, data_uscita)
                print(f"  Redattore: {esito}")
                if not scheda:
                    continue
                try:
                    filmato["url_video"] = cinegiornali.link_video(filmato)
                except requests.RequestException:
                    filmato["url_video"] = None
                if not filmato["url_video"]:
                    print("  Video non scaricabile o licenza non confermata, salto.")
                    continue
                filmato["verifica"] = esito
                gia_usati.add(filmato["id"])
                risultato = produci(scheda, filmato, data, data_uscita, scostamento, storico)
                if risultato is not None:
                    return risultato
    except IANonDisponibile as errore:
        print(f"STOP: il controllo di precisione non è disponibile ({errore}). "
              "Per sicurezza oggi non pubblico nulla.")
        return 1

    print("Nessun cinegiornale verificato con certezza nel mese intorno a oggi. Oggi non pubblico nulla.")
    return 0


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
        feed.aggiungi(RADICE / "feed.xml", titolo, descrizione, url, tag_release,
                      file_short.stat().st_size)
        (USCITA / "release_tag.txt").write_text(tag_release, encoding="utf-8")
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
