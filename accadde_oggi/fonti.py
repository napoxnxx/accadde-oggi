"""Cerca filmati liberi (NASA e Internet Archive) e scarta tutto ciò che non ha una licenza sicura."""

import re
from pathlib import Path

import requests

from .eventi import UA, get_wiki

PAROLE_SPAZIO = ("spazi", "nasa", "apollo", "luna", "lunare", "satellit", "astronaut",
                 "orbita", "sputnik", "shuttle", "razzo", "marte", "gemini", "mercury",
                 "voyager", "hubble", "cosmonaut", "iss", "telescopio")

# Generi troppo vaghi per cercare un filmato da soli
TROPPO_GENERICI = {"United States", "Italy", "France", "Germany", "United Kingdom", "Japan",
                   "China", "Soviet Union", "Russia", "Rome", "Paris", "London", "Europe",
                   "World War II", "World War I", "Pope", "President of the United States"}


def licenza_ok(url):
    """Accetta solo pubblico dominio, CC0, CC BY e CC BY-SA (uso commerciale permesso)."""
    if not url:
        return False
    u = url.lower()
    if "-nc" in u or "-nd" in u or "/nc" in u or "/nd" in u:
        return False
    return any(x in u for x in ("publicdomain", "/licenses/by/", "/licenses/by-sa/"))


def testo_pulito(testo, massimo=1500):
    if isinstance(testo, list):
        testo = " ".join(str(t) for t in testo)
    testo = re.sub(r"<[^>]+>", " ", str(testo or ""))
    return re.sub(r"\s+", " ", testo).strip()[:massimo]


def _parole(testo):
    return {p for p in re.findall(r"[a-z0-9]{4,}", testo.lower())}


def pertinente(titolo_filmato, parola_chiave):
    """Il titolo del filmato deve contenere le parole importanti della parola chiave."""
    chiave = _parole(re.sub(r"\(.*?\)", "", parola_chiave))
    if not chiave:
        return False
    comuni = chiave & _parole(titolo_filmato)
    serve = len(chiave) if len(chiave) <= 3 else -(-3 * len(chiave) // 4)
    return len(comuni) >= serve


def anno_compatibile(candidato, titolo, anno_evento, anno_ignoto_ok=False):
    """Il filmato deve essere dell'anno dell'evento (±1), anche secondo il titolo."""
    if not candidato and not anno_ignoto_ok:
        return False
    if candidato and abs(candidato - anno_evento) > 1:
        return False
    for a in re.findall(r"\b(1[89]\d\d|20\d\d)\b", titolo):
        if abs(int(a) - anno_evento) > 1:
            return False
    return True


def parole_chiave(evento):
    """Titoli inglesi più specifici per primi, i generici in fondo."""
    titoli = [t for t in evento.get("link_en", []) if t not in TROPPO_GENERICI]
    titoli.sort(key=lambda t: (-len(t.split()), -len(t)))
    return titoli[:4]


def e_spaziale(evento):
    t = (evento["testo"] + " " + " ".join(evento.get("link_en", []))).lower()
    return any(p in t for p in PAROLE_SPAZIO)


# ---------------------------------------------------------------- NASA

def cerca_nasa(parola, anno):
    r = requests.get("https://images-api.nasa.gov/search", headers=UA, timeout=30, params={
        "q": parola, "media_type": "video", "year_start": anno, "year_end": anno + 1,
    })
    r.raise_for_status()
    trovati = []
    for item in r.json().get("collection", {}).get("items", [])[:15]:
        d = item.get("data", [{}])[0]
        if not pertinente(d.get("title", "") + " " + " ".join(d.get("keywords", [])), parola):
            continue
        trovati.append({
            "fonte": "NASA", "id": d["nasa_id"], "titolo": d.get("title", ""),
            "anno": int(str(d.get("date_created", "0000"))[:4] or 0),
            "pagina": f"https://images.nasa.gov/details/{d['nasa_id']}",
            "descrizione": testo_pulito(d.get("description", "")),
            "licenza": "Pubblico dominio (NASA)",
        })
    return trovati


def url_video_nasa(nasa_id):
    r = requests.get(f"https://images-api.nasa.gov/asset/{nasa_id}", headers=UA, timeout=30)
    r.raise_for_status()
    hrefs = [i["href"].replace("http://", "https://")
             for i in r.json()["collection"]["items"]]
    for qualita in ("~large.mp4", "~medium.mp4", "~orig.mp4", "~small.mp4", "~mobile.mp4"):
        for h in hrefs:
            if h.endswith(qualita):
                return h.replace(" ", "%20")
    return None


# ---------------------------------------------------------- Internet Archive

def cerca_archive(parola, anno):
    filtro_anno = f" AND year:[{anno - 1} TO {anno + 1}]"
    base = f'title:("{parola}") AND mediatype:(movies){filtro_anno}'
    con_licenza = base + (' AND (licenseurl:*publicdomain* OR licenseurl:*licenses/by/*'
                          ' OR licenseurl:*licenses/by-sa/*)')
    docs = []
    for q in (con_licenza, base):  # se il filtro licenza lato server fallisce, filtra qui
        try:
            r = requests.get("https://archive.org/advancedsearch.php", headers=UA, timeout=30,
                             params={"q": q, "rows": 50, "output": "json",
                                     "fl[]": ["identifier", "title", "licenseurl", "year",
                                              "collection", "description"]})
            r.raise_for_status()
            docs = r.json().get("response", {}).get("docs", [])
        except (requests.RequestException, ValueError):
            docs = []
        if docs:
            break
    trovati = []
    for d in docs:
        if not licenza_ok(d.get("licenseurl")) or not pertinente(d.get("title", ""), parola):
            continue
        collezioni = d.get("collection", [])
        if isinstance(collezioni, str):
            collezioni = [collezioni]
        trovati.append({
            "fonte": "Internet Archive", "id": d["identifier"], "titolo": d.get("title", ""),
            "anno": int(str(d.get("year", "0"))[:4] or 0) if str(d.get("year", "")).isdigit() else 0,
            "pagina": f"https://archive.org/details/{d['identifier']}",
            "descrizione": testo_pulito(d.get("description", "")),
            "licenza_url": d["licenseurl"], "collezioni": collezioni,
        })
    return trovati


def url_video_archive(identificatore):
    """Ricontrolla la licenza sulla scheda completa e sceglie il file mp4 migliore."""
    r = requests.get(f"https://archive.org/metadata/{identificatore}", headers=UA, timeout=30)
    r.raise_for_status()
    dati = r.json()
    if not licenza_ok(dati.get("metadata", {}).get("licenseurl")):
        return None
    mp4 = []
    for f in dati.get("files", []):
        nome = f.get("name", "")
        dimensione = int(f.get("size", 0) or 0)
        if nome.lower().endswith(".mp4") and 2_000_000 < dimensione < 400_000_000:
            mp4.append((dimensione, nome))
    if not mp4:
        return None
    _, nome = max(mp4)
    return f"https://archive.org/download/{identificatore}/{requests.utils.quote(nome)}"


# ------------------------------------------------- Wikimedia Commons
# I video inseriti dagli editori nella voce Wikipedia di un evento sono quasi sempre
# il filmato di quell'evento: è la fonte più precisa.

WIKI_EN = "https://en.wikipedia.org/w/api.php"
COMMONS = "https://commons.wikimedia.org/w/api.php"
ESTENSIONI_VIDEO = (".webm", ".ogv", ".ogg", ".mpg", ".mpeg", ".mp4")


def licenza_commons_ok(nome, url=""):
    testo = f"{nome} {url}".lower()
    if re.search(r"(^|[^a-z])(nc|nd)([^a-z]|$)", testo.replace("-", " ")):
        return False
    return ("public domain" in testo or "publicdomain" in testo or testo.startswith("pd")
            or "cc0" in testo or "cc by" in testo or "/licenses/by/" in testo
            or "/licenses/by-sa/" in testo)


def _anno_da(testo):
    m = re.search(r"\b(18[89]\d|19\d\d|20\d\d)\b", testo or "")
    return int(m.group(1)) if m else 0


def cerca_commons(parola, anno):
    r = get_wiki(WIKI_EN, {
        "action": "query", "titles": parola, "prop": "images", "imlimit": "max",
        "redirects": 1, "format": "json", "formatversion": 2,
    })
    file = [i["title"] for p in r.json().get("query", {}).get("pages", [])
            for i in p.get("images", []) if i["title"].lower().endswith(ESTENSIONI_VIDEO)]
    if not file:
        return []
    r = get_wiki(COMMONS, {
        "action": "query", "titles": "|".join(file[:20]), "prop": "imageinfo",
        "iiprop": "url|extmetadata|mediatype|size", "format": "json", "formatversion": 2,
        "iiextmetadatafilter": "LicenseShortName|LicenseUrl|DateTimeOriginal|"
                               "ImageDescription|ObjectName|Artist",
    })
    trovati = []
    for p in r.json().get("query", {}).get("pages", []):
        info = (p.get("imageinfo") or [{}])[0]
        if info.get("mediatype") != "VIDEO" or not info.get("url"):
            continue
        if int(info.get("size") or 0) > 400_000_000:
            continue
        meta = info.get("extmetadata", {})
        val = lambda k: testo_pulito(meta.get(k, {}).get("value", ""), 1200)
        licenza, licenza_url = val("LicenseShortName"), val("LicenseUrl")
        if not licenza_commons_ok(licenza, licenza_url):
            continue
        titolo = val("ObjectName") or p["title"].removeprefix("File:")
        autore = val("Artist")
        trovati.append({
            "fonte": "Wikimedia Commons", "id": p["title"], "titolo": titolo,
            "anno": _anno_da(val("DateTimeOriginal")) or _anno_da(titolo),
            "pagina": "https://commons.wikimedia.org/wiki/" + p["title"].replace(" ", "_"),
            "descrizione": (val("ImageDescription")
                            + (f" — Autore: {autore}" if autore else "")
                            + f" — (File inserito nella voce Wikipedia inglese \"{parola}\")"),
            "licenza_breve": licenza, "licenza_url": licenza_url, "autore": autore,
            "url_video": info["url"],
        })
    return trovati


# ------------------------------------------------------------------ comune

def punteggio(candidato, evento):
    p = 0
    if candidato["anno"] == evento["anno"]:
        p += 3
    elif candidato["anno"] and abs(candidato["anno"] - evento["anno"]) <= 1:
        p += 2
    if any("newsreel" in c for c in candidato.get("collezioni", [])):
        p += 2
    if candidato["fonte"] == "NASA":
        p += 1
    if candidato["fonte"] == "Wikimedia Commons":
        p += 4
    return p


def trova_filmato(evento, gia_usati, data_evento, redattore):
    """Restituisce il primo filmato che supera tutti i controlli, redattore IA compreso."""
    candidati, visti = [], set()
    for indice, parola in enumerate(parole_chiave(evento)):
        # le voci Wikipedia più specifiche (le prime 2) bastano: meno richieste, meno blocchi
        ricerche = [cerca_commons, cerca_archive] if indice < 2 else [cerca_archive]
        if e_spaziale(evento):
            ricerche.insert(1 if indice < 2 else 0, cerca_nasa)
        for cerca in ricerche:
            try:
                for c in cerca(parola, evento["anno"]):
                    if c["id"] in visti or c["id"] in gia_usati:
                        continue
                    if not anno_compatibile(c["anno"], c["titolo"], evento["anno"],
                                            c["fonte"] == "Wikimedia Commons"):
                        continue
                    visti.add(c["id"])
                    c["parola_chiave"] = parola
                    candidati.append(c)
            except requests.RequestException as errore:
                print(f"  Ricerca {cerca.__name__} '{parola}' non riuscita: {errore}")
    candidati.sort(key=lambda c: punteggio(c, evento), reverse=True)
    for c in candidati[:4]:
        try:
            if c.get("url_video"):
                url = c["url_video"]
            elif c["fonte"] == "NASA":
                url = url_video_nasa(c["id"])
            else:
                url = url_video_archive(c["id"])
        except requests.RequestException:
            url = None
        if not url:
            continue
        if not redattore.disponibile():
            return None
        ok, motivo = redattore.giudica(evento, data_evento, c)
        print(f"  Redattore su \"{c['titolo'][:70]}\": {'OK' if ok else 'SCARTATO'} ({motivo})")
        if ok:
            c["url_video"] = url
            c["verifica"] = motivo
            return c
    return None


def scarica(url, destinazione):
    destinazione = Path(destinazione)
    with requests.get(url, headers=UA, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(destinazione, "wb") as f:
            for blocco in r.iter_content(1 << 20):
                f.write(blocco)
    return destinazione
