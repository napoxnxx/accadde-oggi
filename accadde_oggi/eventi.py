"""Legge gli eventi del giorno da Wikipedia in italiano e li prepara per la ricerca dei filmati."""

import os
import re
import time

import requests

MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
        "agosto", "settembre", "ottobre", "novembre", "dicembre"]

_REPO = os.environ.get("GITHUB_REPOSITORY", "accadde-oggi")
# Wikipedia chiede un User-Agent che identifichi il bot e come contattarne l'autore
UA = {"User-Agent": f"AccaddeOggiBot/1.1 (https://github.com/{_REPO}; bot di divulgazione "
                    "storica che legge una pagina al giorno) python-requests"}

_ultima_richiesta = [0.0]


def get_wiki(url, params, pausa=1.5, tentativi=6):
    """Richiesta gentile alle API Wikimedia: pausa tra le chiamate e nuovi tentativi se bloccati."""
    params = dict(params, maxlag=5)
    for n in range(tentativi):
        attesa = pausa - (time.monotonic() - _ultima_richiesta[0])
        if attesa > 0:
            time.sleep(attesa)
        _ultima_richiesta[0] = time.monotonic()
        r = requests.get(url, headers=UA, timeout=30, params=params)
        if r.status_code in (429, 503) or "maxlag" in r.text[:200]:
            ritardo = int(r.headers.get("Retry-After", "0") or 0) or 10 * (n + 1)
            print(f"  Wikipedia chiede di rallentare: aspetto {ritardo}s")
            time.sleep(min(ritardo, 90))
            continue
        r.raise_for_status()
        return r
    r.raise_for_status()
    return r

WIKI_IT = "https://it.wikipedia.org/w/api.php"


def titolo_pagina(data):
    giorno = "1º" if data.day == 1 else str(data.day)
    return f"{giorno} {MESI[data.month - 1]}"


def scarica_wikitext(data):
    r = get_wiki(WIKI_IT, {
        "action": "parse", "page": titolo_pagina(data), "prop": "wikitext",
        "format": "json", "formatversion": 2, "redirects": 1,
    })
    return r.json()["parse"]["wikitext"]


def _sezione_eventi(wikitext):
    m = re.search(r"^==\s*Eventi\s*==\s*$", wikitext, re.M)
    if not m:
        return ""
    resto = wikitext[m.end():]
    fine = re.search(r"^==[^=].*?==\s*$", resto, re.M)
    return resto[:fine.start()] if fine else resto


def _togli_template(testo):
    precedente = None
    while precedente != testo:
        precedente = testo
        testo = re.sub(r"\{\{[^{}]*\}\}", "", testo)
    return testo


def pulisci(testo):
    """Trasforma il wikitesto in testo leggibile."""
    testo = re.sub(r"<ref[^>]*/>", "", testo)
    testo = re.sub(r"<ref[^>]*>.*?</ref>", "", testo, flags=re.S)
    testo = _togli_template(testo)
    testo = re.sub(r"\[\[(?:File|Immagine|Image):[^\]]*\]\]", "", testo, flags=re.I)
    testo = re.sub(r"\[\[([^\]|]*)\|([^\]]*)\]\]", r"\2", testo)
    testo = re.sub(r"\[\[([^\]]*)\]\]", r"\1", testo)
    testo = re.sub(r"\[https?://\S+\s([^\]]*)\]", r"\1", testo)
    testo = re.sub(r"'{2,}", "", testo)
    testo = re.sub(r"<[^>]+>", "", testo)
    testo = re.sub(r"\s+", " ", testo).strip(" -–—:;,")
    return testo


def _collegamenti(testo):
    link = []
    for target in re.findall(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]", testo):
        t = target.strip()
        if not t or re.fullmatch(r"\d{1,4}", t) or ":" in t:
            continue
        if re.fullmatch(r"\d{1,2}º? \w+", t):  # altre date, es. "16 ottobre"
            continue
        if t not in link:
            link.append(t)
    return link


RIGA_ANNO = re.compile(r"^(\*+)\s*\[\[(\d{1,4})(?:\|[^\]]*)?\]\]\s*(?:[-–—:]\s*)?(.*)$")


def estrai_eventi(wikitext):
    """Restituisce [{'anno', 'testo', 'link_it'}] dalla sezione Eventi."""
    eventi, anno_corrente = [], None
    for riga in _sezione_eventi(wikitext).splitlines():
        riga = riga.strip()
        if not riga.startswith("*"):
            continue
        m = RIGA_ANNO.match(riga)
        if m:
            anno_corrente, corpo = int(m.group(2)), m.group(3)
            if not corpo.strip():
                continue  # anno con sotto-elenco
        elif riga.startswith("**") and anno_corrente:
            corpo = riga.lstrip("* ")
        else:
            anno_corrente = None
            continue
        testo = pulisci(corpo)
        if len(testo) < 15:
            continue
        eventi.append({"anno": anno_corrente, "testo": testo, "link_it": _collegamenti(corpo)})
    return eventi


def titoli_inglesi(titoli_it):
    """Traduce i titoli delle voci italiane nei titoli della Wikipedia inglese."""
    risultato = {}
    titoli_it = list(dict.fromkeys(titoli_it))
    for i in range(0, len(titoli_it), 50):
        blocco = titoli_it[i:i + 50]
        r = get_wiki(WIKI_IT, {
            "action": "query", "titles": "|".join(blocco), "prop": "langlinks",
            "lllang": "en", "lllimit": "max", "redirects": 1,
            "format": "json", "formatversion": 2,
        })
        dati = r.json().get("query", {})
        alias = {}
        for chiave in ("normalized", "redirects"):
            for x in dati.get(chiave, []):
                alias[x["from"]] = x["to"]
        en_per_titolo = {p["title"]: p["langlinks"][0]["title"]
                         for p in dati.get("pages", []) if p.get("langlinks")}
        for t in blocco:
            finale = t
            while finale in alias:
                finale = alias[finale]
            if finale in en_per_titolo:
                risultato[t] = en_per_titolo[finale]
    return risultato


def eventi_del_giorno(data):
    eventi = estrai_eventi(scarica_wikitext(data))
    tutti = [t for e in eventi for t in e["link_it"]]
    try:
        en = titoli_inglesi(tutti)
    except requests.RequestException as errore:
        print("Traduzione titoli non riuscita:", errore)
        en = {}
    for e in eventi:
        e["link_en"] = [en[t] for t in e["link_it"] if t in en]
    return eventi
