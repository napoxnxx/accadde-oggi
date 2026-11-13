"""Il piano delle uscite: quanti video al giorno, a che ora, e quanti ne restano nel mese.

Zapier gratis carica al massimo 100 video al mese: qui si decide come spenderli.
- giorni normali: 3 video (13:00 notizia, 19:00 sera, 21:30 notte);
- giorni forti (attorno all'uscita di GTA VI): 5 video (in più 09:00 mattina e 16:00 pomeriggio).
Se il mese sta finendo i caricamenti, i giorni normali scendono a 2 e poi ci si ferma.

Usa solo la libreria standard: lo stesso codice gira nel controllo veloce di inizio giro.
"""

import datetime as dt
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from . import feed

RADICE = Path(__file__).resolve().parent.parent
ROMA = ZoneInfo("Europe/Rome")
USCITA_GTA = dt.date(2026, 11, 19)

ORARI = {"mattina": dt.time(9, 0), "notizia": dt.time(13, 0), "pomeriggio": dt.time(16, 0),
         "sera": dt.time(19, 0), "notte": dt.time(21, 30)}
# in ordine di importanza: i primi sono quelli che restano quando i video al giorno sono pochi
IMPORTANZA = ["notizia", "sera", "notte", "mattina", "pomeriggio"]
# slot con la notizia fresca: si preparano il giorno stesso, solo in queste ore (ora di Roma)
DEL_GIORNO = {"mattina": range(0, 10), "notizia": range(6, 16)}
TENTATIVI = {"mattina": 1, "notizia": 2}   # quante volte si cerca la notizia prima di ripiegare su una curiosità

VIDEO_AL_GIORNO = 3
VIDEO_GIORNI_FORTI = 5
GIORNI_FORTI = (dt.date(2026, 11, 17), dt.date(2026, 11, 22))   # dal - al, compresi

LIMITE_MESE = 96            # Zapier gratis: 100 al mese; 4 di margine per i recuperi
GIORNO_RINNOVO = 1          # giorno del mese in cui Zapier azzera il conteggio
GIORNI_DI_SCORTA = 3        # gli slot non legati alle notizie si preparano fino a 3 giorni prima
MAX_CARICAMENTI_24H = 5     # YouTube limita i caricamenti dalle app esterne
VIDEO_DI_RISERVA = 2


def forte(giorno):
    return GIORNI_FORTI[0] <= giorno <= GIORNI_FORTI[1]


def quanti(giorno):
    return VIDEO_GIORNI_FORTI if forte(giorno) else VIDEO_AL_GIORNO


# ---------------------------------------------------------------- conteggio del mese

def inizio_ciclo(giorno):
    if giorno.day >= GIORNO_RINNOVO:
        return giorno.replace(day=GIORNO_RINNOVO)
    mese_prima = (giorno.replace(day=1) - dt.timedelta(days=1))
    return mese_prima.replace(day=min(GIORNO_RINNOVO, mese_prima.day))


def fine_ciclo(giorno):
    """Ultimo giorno del ciclo di Zapier in corso."""
    inizio = inizio_ciclo(giorno)
    prossimo = (inizio.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
    prossimo = prossimo.replace(day=min(GIORNO_RINNOVO, 28))
    return prossimo - dt.timedelta(days=1)


def usati(storico, giorno):
    return storico.get("caricamenti", {}).get(inizio_ciclo(giorno).isoformat(), 0)


def registra_caricamento(storico, giorno):
    chiave = inizio_ciclo(giorno).isoformat()
    conteggi = storico.setdefault("caricamenti", {})
    conteggi[chiave] = conteggi.get(chiave, 0) + 1
    for vecchia in sorted(conteggi)[:-3]:
        del conteggi[vecchia]


def ancora_da_caricare(storico, oggi):
    """Quanti video mancano, secondo il piano, da oggi alla fine del ciclo di Zapier."""
    gia_pronti = {}
    for v in storico.get("video", []):
        gia_pronti[v["data"]] = gia_pronti.get(v["data"], 0) + 1
    giorni = [oggi + dt.timedelta(days=k) for k in range((fine_ciclo(oggi) - oggi).days + 1)]
    return sum(max(0, quanti(g) - gia_pronti.get(g.isoformat(), 0)) for g in giorni)


def slot_previsti(giorno, storico, oggi):
    """Gli slot di quel giorno, tenendo conto dei caricamenti rimasti nel mese."""
    n = quanti(giorno)
    if giorno <= fine_ciclo(oggi) and not forte(giorno) \
            and LIMITE_MESE - usati(storico, oggi) < ancora_da_caricare(storico, oggi):
        n = 2   # si risparmia sui giorni normali, non su quelli forti
    return IMPORTANZA[:n]


# ---------------------------------------------------------------- cosa manca

def ultima_ora(slot):
    """Dopo quest'ora (di Roma) lo slot di oggi non si recupera più."""
    return min(ORARI[slot].hour + 2, 22)


def mancanti(storico, adesso):
    """Elenco ordinato di (giorno, slot) da preparare: prima quelli di oggi, poi i giorni dopo."""
    oggi = adesso.date()
    pronti = {(v["data"], v["slot"]) for v in storico.get("video", [])}
    elenco = []
    for k in range(GIORNI_DI_SCORTA + 1):
        giorno = oggi + dt.timedelta(days=k)
        for slot in slot_previsti(giorno, storico, oggi):
            if (giorno.isoformat(), slot) in pronti:
                continue
            if slot in DEL_GIORNO:
                if k == 0 and adesso.hour in DEL_GIORNO[slot]:
                    elenco.append((giorno, slot))
            elif k > 0 or adesso.hour < ultima_ora(slot):
                elenco.append((giorno, slot))
    return elenco


def da_fare(storico, adesso):
    """Come mancanti(), ma rispettando il tetto di YouTube (24 ore) e quello di Zapier (mese)."""
    oggi = adesso.date()
    margine_giorno = MAX_CARICAMENTI_24H - feed.recenti(RADICE / "feed_leonida.xml")
    margine_mese = LIMITE_MESE - usati(storico, oggi)
    servono = ancora_da_caricare(storico, oggi)   # i video di questo mese hanno la precedenza
    scelti = []
    for giorno, slot in mancanti(storico, adesso):
        if len(scelti) >= min(margine_giorno, margine_mese):
            break
        del_mese_dopo = giorno > fine_ciclo(oggi)
        if del_mese_dopo and margine_mese - len(scelti) <= servono:
            continue   # si preparerà dopo il rinnovo di Zapier
        scelti.append((giorno, slot))
        servono -= 0 if del_mese_dopo else 1
    return scelti


def leggi_storico():
    try:
        return json.loads((RADICE / "storico_leonida.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


if __name__ == "__main__":
    # controllo veloce di inizio giro: c'è qualcosa da preparare?
    storico = leggi_storico()
    adesso = dt.datetime.now(ROMA)
    if os.environ.get("PROVA") == "1":
        fare = True
    elif not (RADICE / "via_libera_leonida.txt").exists():
        fare = False
    else:
        fare = bool(da_fare(storico, adesso)) or len(storico.get("riserva", [])) < VIDEO_DI_RISERVA
    print("fare=" + ("1" if fare else "0"))
