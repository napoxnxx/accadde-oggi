"""Feed RSS letto da Zapier: ogni nuovo elemento = un video da caricare su YouTube."""

import datetime as dt
import os
import re
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

MAX_ELEMENTI = 15


def url_release(tag, nome_file):
    repo = os.environ.get("GITHUB_REPOSITORY", "UTENTE/REPOSITORY")
    return f"https://github.com/{repo}/releases/download/{tag}/{nome_file}"


def _elementi_esistenti(testo):
    return re.findall(r"<item>.*?</item>", testo, flags=re.S)


def aggiungi(percorso_feed, titolo, descrizione, url_video, guid, dimensione, uscita):
    percorso_feed = Path(percorso_feed)
    vecchi = _elementi_esistenti(percorso_feed.read_text(encoding="utf-8")) \
        if percorso_feed.exists() else []
    vecchi = [v for v in vecchi if f"<guid isPermaLink=\"false\">{escape(guid)}</guid>" not in v]
    adesso = format_datetime(dt.datetime.now(dt.timezone.utc))
    nuovo = (
        "<item>\n"
        f"  <title>{escape(titolo)}</title>\n"
        f"  <link>{escape(url_video)}</link>\n"
        f"  <description><![CDATA[{descrizione}]]></description>\n"
        f"  <enclosure url=\"{escape(url_video)}\" length=\"{dimensione}\" type=\"video/mp4\"/>\n"
        f"  <guid isPermaLink=\"false\">{escape(guid)}</guid>\n"
        f"  <pubDate>{adesso}</pubDate>\n"
        f"  <category>{uscita.isoformat()}</category>\n"
        "</item>"
    )
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    elementi = "\n".join([nuovo] + vecchi[:MAX_ELEMENTI - 1])
    percorso_feed.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0">\n<channel>\n'
        "<title>Accadde Oggi — nuovi Short</title>\n"
        f"<link>https://github.com/{repo}</link>\n"
        "<description>Video pronti da pubblicare su YouTube</description>\n"
        f"<lastBuildDate>{adesso}</lastBuildDate>\n"
        f"{elementi}\n</channel>\n</rss>\n", encoding="utf-8")
