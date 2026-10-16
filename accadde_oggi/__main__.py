"""ACCADDE OGGI — ogni giorno uno Short automatico con un filmato d'epoca libero da diritti.

Uso:
    python -m accadde_oggi            giro completo (cerca, monta, pubblica)
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
import subprocess
import sys
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

from . import montaggio
from .eventi import MESI, eventi_del_giorno, titolo_pagina
from .fonti import e_spaziale, licenza_ok, scarica, trova_filmato
from .verifica import IANonDisponibile, Redattore

RADICE = Path(__file__).resolve().parent.parent
STORICO = RADICE / "storico.json"
USCITA = RADICE / "output"
MAX_EVENTI = 10
# prima oggi, poi i giorni vicini (sempre con la data vera scritta nel video)
SCOSTAMENTI = [0, -1, 1, -2, 2, -3, 3]


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


def priorita(evento, data):
    anni = data.year - evento["anno"]
    if anni < 1 or evento["anno"] < 1895:
        return None
    p = 0.0
    for ogni, bonus in ((50, 6), (25, 5), (10, 4), (5, 2)):
        if anni % ogni == 0:
            p += bonus
            break
    if 1910 <= evento["anno"] <= 1995:  # l'epoca dei cinegiornali e dei filmati liberi
        p += 2
    if e_spaziale(evento):
        p += 1
    p += min(len(evento.get("link_en", [])), 4) * 0.25
    return p


def nome_licenza(candidato):
    if candidato["fonte"] == "NASA":
        return "Pubblico dominio"
    if candidato.get("licenza_breve"):
        return candidato["licenza_breve"]
    u = candidato.get("licenza_url", "").lower()
    if "publicdomain/zero" in u:
        return "CC0 (pubblico dominio)"
    if "publicdomain" in u:
        return "Pubblico dominio"
    if "by-sa" in u:
        return "CC BY-SA"
    return "CC BY"


def titolo_youtube(evento, data):
    testo = evento["testo"]
    breve = testo if len(testo) <= 70 else testo[:70].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return f"{data.day} {MESI[data.month - 1]} {evento['anno']}: {breve}"[:100]


def descrizione_youtube(evento, data, anni_fa, filmato):
    pagina_wiki = "https://it.wikipedia.org/wiki/" + titolo_pagina(data).replace(" ", "_")
    licenza = nome_licenza(filmato)
    righe = [
        f"{data.day} {MESI[data.month - 1]} {evento['anno']} — {evento['testo']}",
        "",
        f"Accadeva {anni_fa} anni fa. Ogni giorno un momento della storia, "
        "raccontato con i filmati originali dell'epoca.",
        "",
        "FONTI",
        f"Filmato: \"{filmato['titolo']}\" — {filmato['fonte']}"
        + (f" — Autore: {filmato['autore']}" if filmato.get("autore") else ""),
        f"{filmato['pagina']}",
        f"Licenza del filmato: {licenza}"
        + (f" ({filmato['licenza_url']})" if filmato.get("licenza_url") else ""),
        f"Testo: Wikipedia, voce \"{titolo_pagina(data)}\" — {pagina_wiki} (CC BY-SA 4.0)",
        "Testi e grafiche di questo video sono distribuiti con licenza CC BY-SA 4.0.",
    ]
    if filmato["fonte"] == "NASA":
        righe.append("Filmato NASA: la NASA non approva né sponsorizza questo canale.")
    righe += ["", f"#accaddeoggi #storia #{evento['anno']} #shorts"]
    return "\n".join(righe)


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
            data_ev = data + dt.timedelta(days=scostamento)
            print(f"=== Eventi del {titolo_pagina(data_ev)} ===")
            eventi = eventi_del_giorno(data_ev)
            in_ordine = sorted(((priorita(e, data), e) for e in eventi
                                if priorita(e, data) is not None),
                               key=lambda x: x[0], reverse=True)
            for _, evento in in_ordine[:MAX_EVENTI]:
                if not redattore.disponibile():
                    print("Limite di controlli raggiunto per oggi.")
                    break
                print(f"→ {evento['anno']}: {evento['testo'][:90]}")
                filmato = trova_filmato(evento, gia_usati, data_ev, redattore)
                if not filmato:
                    continue
                if filmato["fonte"] == "Internet Archive" and \
                        not licenza_ok(filmato.get("licenza_url")):
                    continue
                gia_usati.add(filmato["id"])
                esito = produci(evento, filmato, data, data_ev, scostamento, storico)
                if esito is not None:
                    return esito
    except IANonDisponibile as errore:
        print(f"STOP: il controllo di precisione non è disponibile ({errore}). "
              "Per sicurezza oggi non pubblico nulla.")
        return 1

    print("Nessun filmato verificato con certezza questa settimana. Oggi non pubblico nulla.")
    return 0


def produci(evento, filmato, data, data_ev, scostamento, storico):
    print(f"  Filmato verificato: {filmato['titolo']} ({filmato['fonte']})")
    etichetta = "ACCADDE OGGI" if scostamento == 0 else "ACCADDE QUESTA SETTIMANA"
    anni_fa = data.year - evento["anno"]
    with tempfile.TemporaryDirectory() as lavoro:
        sorgente = scarica(filmato["url_video"], Path(lavoro) / "sorgente.mp4")
        crediti = [f"Filmato: {filmato['fonte']} · {nome_licenza(filmato)}",
                   "Testo: Wikipedia · CC BY-SA 4.0"]
        USCITA.mkdir(exist_ok=True)
        file_short = USCITA / f"accadde-oggi-{data.isoformat()}.mp4"
        try:
            segmento = montaggio.monta(sorgente, evento, data_ev, anni_fa, crediti,
                                       file_short, lavoro, etichetta)
        except (ValueError, subprocess.CalledProcessError, StopIteration) as errore:
            print("  Montaggio non riuscito, provo il prossimo:", errore)
            return None

    voce = {"data": data.isoformat(), "data_evento": f"{evento['anno']}-{data_ev:%m-%d}",
            "anno": evento["anno"], "evento": evento["testo"], "fonte": filmato["fonte"],
            "id_filmato": filmato["id"], "pagina_filmato": filmato["pagina"],
            "verifica": filmato.get("verifica", ""), **segmento}
    titolo = titolo_youtube(evento, data_ev)
    descrizione = descrizione_youtube(evento, data_ev, anni_fa, filmato)
    (USCITA / "ultimo-video.txt").write_text(
        titolo + "\n\n" + descrizione + "\n\n[Controllo redattore IA: "
        + filmato.get("verifica", "") + "]", encoding="utf-8")

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
    tag = ["accadde oggi", "storia", "filmati d'epoca", str(evento["anno"])]
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
        evento = {"anno": 1964, "testo": "Cina: viene fatta esplodere la prima bomba "
                  "atomica cinese nel deserto del Lop Nur, la Cina diventa la quinta potenza "
                  "nucleare del mondo", "link_en": ["Project 596"]}
        crediti = ["Filmato: Internet Archive · Pubblico dominio",
                   "Testo: Wikipedia · CC BY-SA 4.0"]
        montaggio.monta(finto, evento, data, 62, crediti, USCITA / "demo.mp4", lavoro)
    print("Creato:", USCITA / "demo.mp4")


if __name__ == "__main__":
    sys.exit(demo() if "--demo" in sys.argv else giro_completo())
