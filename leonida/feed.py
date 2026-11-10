"""Feed RSS letto da Zapier: ogni nuovo elemento è un video da caricare su YouTube.

Nel campo <category> c'è l'ora esatta di pubblicazione: Zapier la passa a YouTube come
"Publish At", così il video resta privato e diventa pubblico da solo a quell'ora.
"""

import datetime as dt
import os
import re
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

MAX_ELEMENTI = 15


def url_release(tag, nome_file):
    repo = os.environ.get("GITHUB_REPOSITORY", "napoxnxx/accadde-oggi")
    return f"https://github.com/{repo}/releases/download/{tag}/{nome_file}"


def aggiungi(percorso_feed, titolo, descrizione, url_video, guid, dimensione, uscita):
    percorso_feed = Path(percorso_feed)
    vecchi = re.findall(r"<item>.*?</item>", percorso_feed.read_text(encoding="utf-8"), flags=re.S) \
        if percorso_feed.exists() else []
    vecchi = [v for v in vecchi if f"<guid isPermaLink=\"false\">{escape(guid)}</guid>" not in v]
    adesso = format_datetime(dt.datetime.now(dt.timezone.utc))
    descrizione = descrizione.replace("]]>", "]] >")
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
        "<title>Until Leonida — nuovi Short</title>\n"
        f"<link>https://github.com/{repo}</link>\n"
        "<description>Short su GTA VI pronti da pubblicare su YouTube</description>\n"
        f"<lastBuildDate>{adesso}</lastBuildDate>\n"
        f"{elementi}\n</channel>\n</rss>\n", encoding="utf-8")
