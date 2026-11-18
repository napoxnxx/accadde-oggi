"""Gancio e valutazione: prima di montare un video si decide se vale la pena guardarlo.

- Per le curiosità: tra le prime candidate (le meno usate) Claude sceglie quella con più
  possibilità di trattenere e girare, e scrive il gancio parlato dei primi due secondi.
- Per le notizie: Claude dà un voto; se è bassa, al suo posto esce una curiosità.
Il gancio non può contenere numeri o nomi che il video non dice: se li ha, si usa un gancio di riserva.
Se Claude non è raggiungibile, si va avanti con i ganci di riserva (il video esce comunque).
"""

import datetime as dt
import json
import random
import re

from . import notizie

VOTO_MINIMO_NOTIZIA = 5
MAX_CARATTERI = 60

RISERVA = {
    "GAMEPLAY": ["Questa in GTA 6 non te l'aspetti", "In GTA 6 cambia tutto", "Questo dettaglio cambia come giocherai"],
    "LA STORIA": ["Nessuno ne sta parlando", "Questo dettaglio dice tanto sulla storia"],
    "STORIA DI GTA": ["Pochi se lo ricordano", "Questa storia la sanno in pochi"],
    "RECORD": ["Questo numero è assurdo", "Un record mai visto"],
    "RETROSCENA": ["Te lo ricordi?", "Questo retroscena lo sanno in pochi"],
    "SCANDALI": ["La storia che Rockstar non ama ricordare", "Te lo ricordi questo caso?"],
    "MUSICA": ["Ascolta qui", "Questa non la sapevi"],
    "PERSONAGGI": ["Guarda bene questo personaggio", "Chi è davvero?"],
    "LUOGHI": ["Qui ci passerai ore", "Guarda questo posto"],
    "NEWS GTA VI": ["Notizia appena arrivata", "Rockstar l'ha appena confermato"],
}
GENERICI = ["Aspetta, guarda qui", "Questo non lo sapevi", "Lo sapevi?"]

SCEGLI = """Sei il responsabile di un canale italiano di YouTube Shorts su GTA 6 (uscita: 19 novembre 2026; \
oggi è il {oggi}). L'obiettivo è fare più visualizzazioni possibile: lo spettatore deve fermarsi nei primi \
2 secondi e guardare fino alla fine.

Qui sotto ci sono alcune curiosità candidate (solo una andrà in onda). Per ognuna valuta da 1 a 10 il \
potenziale: quanto è sorprendente, quanto interessa ADESSO (a ridosso dell'uscita), quanto fa commentare. \
Poi scegli la migliore e scrivi il GANCIO: la frase che la voce dice prima del titolo, massimo 8 parole, \
in italiano parlato, che crea curiosità. Regole del gancio: niente numeri, nomi o fatti che non siano già \
nel testo della curiosità; niente promesse che il video non mantiene; niente "incredibile", "pazzesco", emoji.

Rispondi SOLO con JSON: {{"voti": {{"<id>": <1-10>, ...}}, "scelta": "<id>", "gancio": "<frase>", "motivo": "<breve>"}}

CURIOSITÀ:
{elenco}"""

VALUTA = """Sei il responsabile di un canale italiano di YouTube Shorts su GTA 6 (uscita: 19 novembre 2026; \
oggi è il {oggi}). Valuta da 1 a 10 quanto questa notizia può fare visualizzazioni come Short (interesse \
adesso, sorpresa, commenti). Poi scrivi il GANCIO: la frase che la voce dice prima del titolo, massimo 8 \
parole, italiano parlato, che crea curiosità. Niente numeri, nomi o fatti che non siano nel testo; niente \
promesse che il video non mantiene; niente "incredibile", "pazzesco", emoji.

Rispondi SOLO con JSON: {{"voto": <1-10>, "gancio": "<frase>", "motivo": "<breve>"}}

NOTIZIA:
{testo}"""


def _parole_chiave(testo):
    return {p for p in re.findall(r"[A-Za-zÀ-ÿ0-9]+", testo) if p[0].isupper() or p[0].isdigit()}


def gancio_valido(gancio, testo_video):
    """Corto, senza numeri o nomi propri che il video non contiene."""
    gancio = re.sub(r"\s+", " ", str(gancio or "")).strip().strip('"«»')
    if not gancio or len(gancio) > MAX_CARATTERI or re.search(r"[\U0001F000-\U0001FAFF]", gancio):
        return None
    nel_video = {p.lower() for p in re.findall(r"[A-Za-zÀ-ÿ0-9]+", testo_video)}
    parole = re.findall(r"[A-Za-zÀ-ÿ0-9]+", re.sub(r"\bGTA\s*(6|VI)\b", " ", gancio))
    for i, p in enumerate(parole):
        nome_proprio = p[0].isupper() and i > 0
        if (p[0].isdigit() or nome_proprio) and p.lower() not in nel_video and p.upper() not in ("GTA", "VI"):
            return None
    return gancio[0].upper() + gancio[1:]


def di_riserva(etichetta, seme):
    return random.Random(seme).choice(RISERVA.get(etichetta, []) + GENERICI)


def _testo(c):
    return " ".join([c["titolo"], *c["frasi"]])


def scegli_curiosita(candidate, oggi, chiedi=None):
    """(curiosità scelta, gancio, voti). Le candidate sono in ordine di priorità."""
    elenco = "\n".join(f'- id "{c["id"]}" [{c["etichetta"]}] {c["titolo"]}: {" ".join(c["frasi"])}' for c in candidate)
    try:
        risposta = notizie.chiedi_json(SCEGLI.format(oggi=oggi.strftime("%d/%m/%Y"), elenco=elenco), chiedi)
    except notizie.IANonDisponibile as errore:
        print(f"  Valutazione non disponibile: {errore}")
        risposta = {}
    per_id = {c["id"]: c for c in candidate}
    voti = {k: v for k, v in (risposta.get("voti") or {}).items() if k in per_id and isinstance(v, (int, float))}
    scelta = per_id.get(risposta.get("scelta")) or (max(candidate, key=lambda c: voti.get(c["id"], 0)) if voti else candidate[0])
    gancio = gancio_valido(risposta.get("gancio"), _testo(scelta)) if scelta is per_id.get(risposta.get("scelta")) else None
    if risposta:
        print(f"  Voti: {voti} → scelta {scelta['id']} ({risposta.get('motivo', '')[:120]})")
    return scelta, gancio or di_riserva(scelta["etichetta"], scelta["id"] + str(oggi)), voti


def valuta_notizia(n, oggi, chiedi=None):
    """(voto o None, gancio)."""
    testo = n["titolo"] + ". " + " ".join(n["frasi"])
    try:
        risposta = notizie.chiedi_json(VALUTA.format(oggi=oggi.strftime("%d/%m/%Y"), testo=testo), chiedi)
    except notizie.IANonDisponibile as errore:
        print(f"  Valutazione non disponibile: {errore}")
        risposta = {}
    voto = risposta.get("voto") if isinstance(risposta.get("voto"), (int, float)) else None
    print(f"  Voto notizia: {voto} ({str(risposta.get('motivo', ''))[:120]})")
    return voto, gancio_valido(risposta.get("gancio"), testo) or di_riserva("NEWS GTA VI", n["titolo"] + str(oggi))
