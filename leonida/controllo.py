"""Controllo che i video siano usciti davvero su YouTube, e recupero di quelli saltati.

Zapier a volte non carica un video (limiti di YouTube, errori temporanei) e da GitHub non si
vede. Qui si legge l'elenco pubblico dei video del canale: se un video doveva essere già
uscito e non c'è, lo si ripropone a Zapier una volta, con un nuovo orario vicino.
Usa solo la libreria standard, così gira in pochi secondi a ogni giro.
"""

import datetime as dt
import json
import re
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

from . import feed

RADICE = Path(__file__).resolve().parent.parent
CANALE = "UCE96_mB4hgibQ2I9W7AfHJw"
ROMA = ZoneInfo("Europe/Rome")
ATTESA = dt.timedelta(minutes=75)      # tempo lasciato a YouTube dopo l'ora di uscita (il suo elenco arriva in ritardo)
FINESTRA = dt.timedelta(hours=30)      # oltre, il video è troppo vecchio per recuperarlo


def _norma(titolo):
    return re.sub(r"[^a-z0-9]", "", titolo.lower())


def titoli_online():
    """Titoli dei video pubblici del canale; None se YouTube non risponde."""
    try:
        richiesta = urllib.request.Request(f"https://www.youtube.com/feeds/videos.xml?channel_id={CANALE}",
                                           headers={"User-Agent": "Mozilla/5.0"})
        testo = urllib.request.urlopen(richiesta, timeout=30).read().decode("utf-8", "replace")
    except Exception as errore:  # noqa: BLE001
        print(f"Controllo uscite: YouTube non raggiungibile ({errore!r}).")
        return None
    titoli = re.findall(r"<entry>.*?<title>(.*?)</title>", testo, flags=re.S)
    import html
    return {_norma(html.unescape(t)) for t in titoli}


def nuova_uscita(adesso):
    prima = adesso + dt.timedelta(minutes=90)
    resto = prima.minute % 30
    return (prima + dt.timedelta(minutes=(30 - resto) % 30)).replace(second=0, microsecond=0)


def controlla(adesso=None, online=None):
    adesso = adesso or dt.datetime.now(ROMA)
    percorso = RADICE / "storico_leonida.json"
    if not percorso.exists() or not (RADICE / "via_libera_leonida.txt").exists():
        return []
    storico = json.loads(percorso.read_text(encoding="utf-8"))
    online = titoli_online() if online is None else online
    if online is None:
        return []
    video = storico.get("video", [])
    # prova che il confronto dei titoli funziona: almeno un nostro video deve risultare online
    if not any(_norma(v["titolo"]) in online for v in video):
        print("Controllo uscite: nessun nostro video riconosciuto nell'elenco, non tocco niente.")
        attesi = [v for v in video if v.get("uscita") and
                  adesso - dt.timedelta(days=3) < dt.datetime.fromisoformat(v["uscita"]) < adesso - ATTESA]
        if len(attesi) >= 3 and storico.get("ultimo_allarme") != adesso.date().isoformat():
            storico["ultimo_allarme"] = adesso.date().isoformat()
            percorso.write_text(json.dumps(storico, ensure_ascii=False, indent=1), encoding="utf-8")
            (RADICE / "avviso_leonida.txt").write_text(
                "Negli ultimi 3 giorni dovevano uscire %d video ma sul canale non ne risulta nessuno.\n\n"
                "Controlla su Zapier che lo Zap di Until Leonida sia acceso (On) e guarda la Zap history.\n" % len(attesi),
                encoding="utf-8")
        return []
    avvisi = []
    for v in video:
        if v.get("online") or v.get("perso") or not v.get("uscita"):
            continue
        uscita = dt.datetime.fromisoformat(v["uscita"])
        if not (adesso - FINESTRA < uscita < adesso - ATTESA):
            continue
        if _norma(v["titolo"]) in online:
            v["online"] = True
            continue
        nuova = nuova_uscita(adesso)
        scaduto = v.get("formato") == "countdown" and nuova.date().isoformat() != v["data"]
        if v.get("riproposto") or scaduto or nuova.hour >= 23 or nuova.hour < 7:
            if v.get("riproposto") or scaduto:
                v["perso"] = True
                avvisi.append(f"{adesso:%d/%m %H:%M} NON USCITO su YouTube: {v['titolo']} — controllare Zap history")
            continue  # di notte si riprova al mattino
        v["riproposto"] = 1
        v["uscita"] = nuova.isoformat()
        feed.aggiungi(RADICE / "feed_leonida.xml", v["titolo"], v["descrizione"], v["url"],
                      f"{v['tag']}-r1", v["dimensione"], nuova)
        avvisi.append(f"{adesso:%d/%m %H:%M} non era uscito, riproposto per le {nuova:%H:%M}: {v['titolo']}")
    persi = [a for a in avvisi if "NON USCITO" in a]
    if persi:
        (RADICE / "avviso_leonida.txt").write_text(
            "\n".join(persi) + "\n\nIl sistema ha già riprovato una volta da solo. Controlla su Zapier che lo Zap "
            "di Until Leonida sia acceso (On) e guarda la Zap history per vedere l'errore.\n", encoding="utf-8")
    if avvisi:
        print("\n".join(avvisi))
        storico["avvisi"] = (storico.get("avvisi", []) + avvisi)[-10:]
        stato_file = RADICE / "stato_leonida.json"
        try:
            stato = json.loads(stato_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            stato = {}
        stato["avvisi"] = storico["avvisi"]
        stato_file.write_text(json.dumps(stato, ensure_ascii=False, indent=1), encoding="utf-8")
    else:
        print("Controllo uscite: tutto a posto.")
    percorso.write_text(json.dumps(storico, ensure_ascii=False, indent=1), encoding="utf-8")
    return avvisi


if __name__ == "__main__":
    try:
        controlla()
    except Exception as errore:  # noqa: BLE001 — il controllo non deve mai fermare il giro
        print(f"Controllo uscite saltato: {errore!r}")
