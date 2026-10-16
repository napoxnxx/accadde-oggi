"""Cinegiornali Universal di pubblico dominio (archive.org, collezione universal_newsreels).

Ogni filmato è dedicato a una sola notizia e ha la data di uscita nel nome
(es. 1961-10-16_Civil_Planes_Grounded): filmato e data coincidono per costruzione.
"""

import re

import requests

from .eventi import UA
from .fonti import licenza_ok, testo_pulito, url_video_archive

COLLEZIONI = ["universal_newsreels"]
RICERCA = "https://archive.org/advancedsearch.php"
NOME_DATATO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})_")


def candidati(giorno, mese):
    """Tutti i cinegiornali usciti in questo giorno e mese, di qualsiasi anno."""
    collezioni = " OR ".join(f"collection:{c}" for c in COLLEZIONI)
    q = f"({collezioni}) AND identifier:*-{mese:02d}-{giorno:02d}_*"
    r = requests.get(RICERCA, headers=UA, timeout=40, params={
        "q": q, "rows": 200, "output": "json",
        "fl[]": ["identifier", "title", "description", "licenseurl"],
    })
    r.raise_for_status()
    trovati = []
    for d in r.json().get("response", {}).get("docs", []):
        m = NOME_DATATO.match(d["identifier"])
        if not m or (int(m.group(2)), int(m.group(3))) != (mese, giorno):
            continue
        if not licenza_ok(d.get("licenseurl")):
            continue
        trovati.append({
            "fonte": "Internet Archive", "id": d["identifier"],
            "titolo": testo_pulito(d.get("title", ""), 200),
            "descrizione": testo_pulito(d.get("description", ""), 1500),
            "anno": int(m.group(1)),
            "pagina": f"https://archive.org/details/{d['identifier']}",
            "licenza_url": d["licenseurl"],
        })
    return trovati


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


def link_video(candidato):
    return url_video_archive(candidato["id"])
