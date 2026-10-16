"""Cinegiornali Universal di pubblico dominio (archive.org, collezione universal_newsreels).

Ogni filmato è dedicato a una sola notizia e ha la data di uscita nel nome
(es. 1961-10-16_Civil_Planes_Grounded): filmato e data coincidono per costruzione.
"""

import re
import time

import requests

from .eventi import UA
from .fonti import licenza_ok, testo_pulito

COLLEZIONI = ["universal_newsreels"]
RICERCA = "https://archive.org/advancedsearch.php"
NOME_DATATO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})_")


_CATALOGO = None


def catalogo():
    """Scarica UNA volta l'elenco completo dei cinegiornali (licenza filtrata) e lo tiene in memoria."""
    global _CATALOGO
    if _CATALOGO is not None:
        return _CATALOGO
    collezioni = " OR ".join(f"collection:{c}" for c in COLLEZIONI)
    ultimo_errore = None
    for tentativo in range(4):
        try:
            r = requests.get(RICERCA, headers=UA, timeout=60, params={
                "q": f"({collezioni}) AND mediatype:movies", "rows": 5000, "output": "json",
                "fl[]": ["identifier", "title", "description", "licenseurl"],
            })
            r.raise_for_status()
            docs = r.json().get("response", {}).get("docs", [])
            break
        except (requests.RequestException, ValueError) as errore:
            ultimo_errore = errore
            time.sleep(20 * (tentativo + 1))
    else:
        raise requests.RequestException(f"archivio non raggiungibile: {ultimo_errore}")
    elenco = []
    for d in docs:
        m = NOME_DATATO.match(d.get("identifier", ""))
        if not m or not licenza_ok(d.get("licenseurl")):
            continue
        elenco.append({
            "fonte": "Internet Archive", "id": d["identifier"],
            "titolo": testo_pulito(d.get("title", ""), 200),
            "descrizione": testo_pulito(d.get("description", ""), 1500),
            "anno": int(m.group(1)), "mese": int(m.group(2)), "giorno": int(m.group(3)),
            "pagina": f"https://archive.org/details/{d['identifier']}",
            "licenza_url": d["licenseurl"],
        })
    _CATALOGO = elenco
    print(f"Catalogo: {len(elenco)} cinegiornali di pubblico dominio con data")
    return _CATALOGO


def candidati(giorno, mese):
    """Tutti i cinegiornali usciti in questo giorno e mese, di qualsiasi anno."""
    return [dict(c) for c in catalogo() if c["giorno"] == giorno and c["mese"] == mese]


def priorita(candidato, anno_oggi):
    """Prima gli anniversari tondi, poi le schede con più descrizione."""
    anni = anno_oggi - candidato["anno"]
    p = 0
    for ogni, bonus in ((50, 6), (25, 5), (10, 4), (5, 2)):
        if anni % ogni == 0:
            p += bonus
            break
    p += min(len(candidato["descrizione"]), 600) / 200
    return p


DURATA_MASSIMA = 90  # secondi: il filmato si mostra SEMPRE intero, così il testo combacia


def _secondi(valore):
    try:
        if ":" in str(valore):
            parti = [float(x) for x in str(valore).split(":")]
            return sum(v * 60 ** i for i, v in enumerate(reversed(parti)))
        return float(valore)
    except (TypeError, ValueError):
        return None


def link_video(candidato):
    """Link al file mp4 migliore, solo se licenza confermata e durata entro il limite."""
    r = requests.get(f"https://archive.org/metadata/{candidato['id']}", headers=UA, timeout=30)
    r.raise_for_status()
    dati = r.json()
    if not licenza_ok(dati.get("metadata", {}).get("licenseurl")):
        return None, "licenza non confermata sulla scheda completa"
    mp4 = []
    for f in dati.get("files", []):
        nome = f.get("name", "")
        if not nome.lower().endswith(".mp4"):
            continue
        dimensione = int(f.get("size", 0) or 0)
        durata = _secondi(f.get("length"))
        if 300_000 < dimensione < 400_000_000:
            mp4.append((dimensione, nome, durata))
    if not mp4:
        return None, "nessun file mp4 utilizzabile"
    _, nome, durata = max(mp4)
    if durata is not None and durata > DURATA_MASSIMA:
        return None, f"troppo lungo ({durata:.0f}s): non si potrebbe mostrare intero"
    return f"https://archive.org/download/{candidato['id']}/{requests.utils.quote(nome)}", "ok"
