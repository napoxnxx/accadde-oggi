"""La notizia del giorno su GTA VI, presa dal web: i feed RSS di più siti di videogiochi.

Regole contro errori e disinformazione:
- una notizia si usa solo se la riportano almeno 3 testate diverse nelle ultime 30 ore;
- niente leak, indiscrezioni, "insider", speculazioni e spoiler della trama;
- Claude (abbonamento Pro) scrive il testo SOLO con quello che c'è negli articoli; un secondo
  passaggio di Claude controlla ogni affermazione;
- in più, controlli automatici: ogni numero e risultato deve comparire in almeno 2 articoli,
  ogni citazione tra virgolette deve esistere davvero, "ufficiale" solo se lo dicono 2 testate.
Se anche un solo controllo fallisce, la notizia si scarta.
"""

import datetime as dt
import html
import json
import os
import re
import subprocess
import unicodedata
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

import requests

FONTI = [
    ("Multiplayer.it", "https://multiplayer.it/feed/rss/homepage/"),
    ("Spaziogames", "https://www.spaziogames.it/feed"),
    ("Everyeye.it", "https://www.everyeye.it/feed_news_rss.asp"),
    ("Eurogamer.it", "https://www.eurogamer.it/feed"),
    ("IGN Italia", "https://it.ign.com/feed.xml"),
    ("IGN", "https://feeds.feedburner.com/ign/games-all"),
    ("GameSpot", "https://www.gamespot.com/feeds/news/"),
    ("VGC", "https://www.videogameschronicle.com/feed/"),
    ("Eurogamer", "https://www.eurogamer.net/feed"),
]
MIN_TESTATE = 3
ORE = 30
UA_RSS = {"User-Agent": "Mozilla/5.0 (compatible; UntilLeonidaBot/1.0; "
                        f"+https://github.com/{os.environ.get('GITHUB_REPOSITORY', 'napoxnxx/accadde-oggi')})"}

# Argomenti che non tocchiamo mai, anche se veri: troppo delicati per un canale automatico.
ESCLUSI = re.compile(r"\bleak|\brumou?r|\binsider\b|\bindiscrez|\bspeculaz|\bspoiler|\btrapelat|\bdatamin"
                     r"|\bpresunt|\bvoci\b|\bsecondo alcun|\bpirat|\bmort[eiao]\b|\bdecedut|\bdecesso|\blutto\b|\btragedi|\barrestat|\barresto\b"
                     r"|\bindagat|\binchiest|\bprocura\b|\brazzis|\bviolenz|\baggredit|\baggression"
                     r"|\bscommess|\bsuicid|\btumor|\bmalattia\b|\bricoverat|\bomicid|\bcondannat"
                     r"|\bincidente stradale")


TEMA = re.compile(r"\bgta\b|\bgta ?(6|vi)\b|grand theft auto|rockstar|leonida|vice city|take two|take-two|jason duval|lucia caminos")


class IANonDisponibile(Exception):
    pass


# ---------------------------------------------------------------- lettura dei feed

def _testo(nodo, nome):
    for figlio in nodo:
        if figlio.tag.split("}")[-1] == nome:
            return (figlio.text or "").strip()
    return ""


def pulisci(testo, massimo=400):
    testo = html.unescape(re.sub(r"<[^>]+>", " ", html.unescape(testo or "")))
    return re.sub(r"\s+", " ", testo).strip()[:massimo]


def leggi_feed(nome, url, adesso):
    r = requests.get(url, headers=UA_RSS, timeout=25)
    r.raise_for_status()
    try:
        radice = ET.fromstring(r.content)
    except ET.ParseError:
        # alcuni feed usano entità HTML (&nbsp; &egrave;) che l'XML non conosce
        testo = r.content.decode(r.encoding or "utf-8", errors="replace")
        testo = re.sub(r"&(?!amp;|lt;|gt;|quot;|apos;|#)(\w+);",
                       lambda m: html.unescape(m.group(0)) if html.unescape(m.group(0)) not in "&<>" else "",
                       testo)
        radice = ET.fromstring(testo.encode("utf-8").replace(b'encoding="ISO-8859-1"', b'encoding="utf-8"'))
    articoli = []
    for nodo in radice.iter():
        if nodo.tag.split("}")[-1] not in ("item", "entry"):
            continue
        titolo = pulisci(_testo(nodo, "title"), 220)
        data = _testo(nodo, "pubDate") or _testo(nodo, "updated") or _testo(nodo, "published")
        quando = None
        try:
            quando = parsedate_to_datetime(data)
        except (TypeError, ValueError, IndexError):
            try:
                quando = dt.datetime.fromisoformat(data.replace("Z", "+00:00"))
            except ValueError:
                pass
        if quando is None:
            continue
        if quando.tzinfo is None:
            quando = quando.replace(tzinfo=dt.timezone.utc)
        if not titolo or adesso - quando > dt.timedelta(hours=ORE) or quando - adesso > dt.timedelta(hours=2):
            continue
        link = _testo(nodo, "link")
        if not link:
            for figlio in nodo:
                if figlio.tag.split("}")[-1] == "link" and figlio.get("href"):
                    link = figlio.get("href")
        articoli.append({"fonte": nome, "titolo": titolo, "quando": quando,
                         "sommario": pulisci(_testo(nodo, "description") or _testo(nodo, "summary"), 300),
                         "link": link.strip()})
    return articoli


def raccogli(adesso=None):
    adesso = adesso or dt.datetime.now(dt.timezone.utc)
    tutti, visti, esiti = [], set(), {}
    for nome, url in FONTI:
        try:
            nuovi = leggi_feed(nome, url, adesso)
            esiti[nome] = len(nuovi)
        except (requests.RequestException, ET.ParseError) as errore:
            esiti[nome] = f"non raggiungibile ({type(errore).__name__})"
            continue
        for a in nuovi:
            chiave = norma(a["titolo"])
            if chiave in visti:
                continue
            visti.add(chiave)
            tutti.append(a)
    tutti = [a for a in tutti if TEMA.search(norma(f"{a['titolo']} {a['sommario']}"))]
    tutti.sort(key=lambda a: a["quando"], reverse=True)
    tutti = tutti[:200]
    for i, a in enumerate(tutti, start=1):
        a["n"] = i
    print("Testate lette:", ", ".join(f"{k}: {v}" for k, v in esiti.items()))
    return tutti, esiti


# ---------------------------------------------------------------- controlli automatici

def norma(testo):
    testo = unicodedata.normalize("NFKD", testo or "").encode("ascii", "ignore").decode().lower()
    testo = re.sub(r"[‘’'`´]", " ", testo)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\-:\s]", " ", testo)).strip()


def _risultati(testo):
    """Risultati come 3-0 / 0-3, senza badare all'ordine (casa-trasferta o vincente-perdente)."""
    return {"-".join(sorted((a, b))) for a, b in re.findall(r"\b(\d{1,2})\s*[-–:]\s*(\d{1,2})\b", testo or "")}


def _numeri(testo):
    senza = re.sub(r"\b\d{1,2}\s*[-–:]\s*\d{1,2}\b", " ", testo or "")
    return set(re.findall(r"\d+", senza))


def controlli_automatici(scritto, citati):
    """Restituisce la lista dei problemi trovati (vuota = tutto a posto)."""
    problemi = []
    fonti_testo = [(a["fonte"], f"{a['titolo']} {a['sommario']}") for a in citati]
    tutto = " ".join([scritto.get("titolo", ""), *scritto.get("frasi", []), scritto.get("titolo_youtube", "")])
    for ris in _risultati(tutto):
        quante = {f for f, t in fonti_testo if ris in _risultati(t)}
        if len(quante) < 2:
            problemi.append(f"risultato {ris} confermato da {len(quante)} testate")
    for num in _numeri(tutto):
        quante = {f for f, t in fonti_testo if num in set(re.findall(r"\d+", t))}
        if len(quante) < 2:
            problemi.append(f"numero {num} confermato da {len(quante)} testate")
    for citazione in re.findall(r"[\"“«]([^\"”»]{4,})[\"”»]", tutto):
        if not any(norma(citazione) in norma(t) for _, t in fonti_testo):
            problemi.append(f"citazione non trovata negli articoli: {citazione}")
    if "ufficial" in tutto.lower():
        quante = {f for f, t in fonti_testo if "ufficial" in t.lower() or "official" in t.lower()}
        if len(quante) < 2:
            problemi.append("'ufficiale' detto da meno di 2 testate")
    if ESCLUSI.search(norma(tutto)):
        problemi.append("argomento escluso (morti, violenza, inchieste, scommesse…)")
    if not 1 <= len(scritto.get("titolo", "")) <= 70 or not 2 <= len(scritto.get("frasi", [])) <= 3:
        problemi.append("lunghezze non valide")
    if any(len(f) > 120 for f in scritto.get("frasi", [])):
        problemi.append("frase troppo lunga")
    return problemi


def valida_storia(storia, citati, gia_usati):
    testate = {a["fonte"] for a in citati}
    if len(testate) < MIN_TESTATE:
        return f"solo {len(testate)} testate"
    soggetti = [norma(s) for s in storia.get("soggetti", []) if norma(s)]
    if not soggetti:
        return "nessun protagonista indicato"
    for a in citati:
        testo = norma(f"{a['titolo']} {a['sommario']}")
        if not any(s in testo for s in soggetti):
            return f"l'articolo {a['n']} ({a['fonte']}) non parla dei protagonisti"
        if ESCLUSI.search(testo):
            return "argomento escluso (morti, violenza, inchieste, scommesse…)"
    if len({a["link"] for a in citati} & set(gia_usati)) >= 2 or chiave_storia(storia) in set(gia_usati):
        return "notizia già pubblicata"
    return None


def chiave_storia(storia):
    """Stessi protagonisti = stessa notizia, anche se gli articoli sono nuovi."""
    return "soggetti:" + "|".join(sorted({norma(s) for s in storia.get("soggetti", []) if norma(s)}))


# ---------------------------------------------------------------- Claude

SCEGLI = """Sei il caporedattore di un canale YouTube italiano dedicato a GTA VI. Ti do gli articoli \
usciti nelle ultime ore su diversi siti di videogiochi (numero, testata, ora, titolo, sommario).

Trova le notizie su GTA VI (o Rockstar e Take-Two, se riguardano GTA VI) che siano FATTI CERTI e \
UFFICIALI riportati da almeno 3 testate DIVERSE.
Vanno bene: annunci ufficiali di Rockstar o Take-Two, date, orari di sblocco, pre-load, prezzi \
ufficiali, trailer pubblicati, dati di vendita ufficiali, voti delle recensioni pubblicate, \
aggiornamenti e patch annunciati, eventi ufficiali.
NON vanno bene: leak, indiscrezioni, "insider", rumor, speculazioni, teorie dei fan, analisi di \
trailer, opinioni, spoiler della trama, pirateria, notizie su morti, violenza reale, inchieste, \
e tutto ciò che è "secondo alcune fonti".

Per ogni notizia indica i numeri degli articoli che riportano PROPRIO QUEL FATTO (almeno 3, di \
testate diverse) e i protagonisti (per esempio "GTA VI", "Rockstar") scritti come negli articoli.
Ordina dalla più importante. Massimo 4 notizie.

Rispondi SOLO con JSON, senza altro testo:
{"notizie": [{"fatto": "una frase", "articoli": [1, 5, 9], "soggetti": ["GTA"]}]}"""

SCRIVI = """Scrivi una notizia su GTA VI per uno Short di YouTube in italiano, usando SOLO gli articoli \
qui sotto (possono essere in italiano o in inglese).

Restituisci:
- "titolo": titolo per il video, massimo 60 caratteri, chiaro, in italiano;
- "frasi": 2 o 3 frasi brevi (massimo 95 caratteri ciascuna) con i fatti principali;
- "titolo_youtube": titolo per YouTube, massimo 85 caratteri, con "GTA 6";
- "domanda": domanda breve al pubblico per i commenti, massimo 34 caratteri, in maiuscolo;
- "soggetto_foto": "GTA VI".

REGOLE OBBLIGATORIE:
- Ogni fatto, nome, numero, data e prezzo deve comparire in ALMENO DUE degli articoli.
- Non aggiungere nulla che sai tu ma che non è negli articoli.
- Niente citazioni tra virgolette. Niente leak, rumor o spoiler della trama.
- Scrivi con parole tue, senza copiare i titoli; niente aggettivi esagerati.
- La parola "ufficiale" solo se almeno due articoli dicono che è ufficiale.

Rispondi SOLO con JSON:
{"titolo": "...", "frasi": ["...", "..."], "titolo_youtube": "...", "domanda": "...", "soggetto_foto": "GTA VI"}"""

CONTROLLA = """Sei un fact-checker severo. Ti do alcuni articoli e un testo scritto a partire da essi.
Elenca ogni affermazione del testo (fatti, nomi, numeri, risultati, citazioni, parole come \
"ufficiale", "storico", "record") che NON è riportata da almeno due articoli, o che va oltre \
quello che dicono. Se è tutto supportato, restituisci una lista vuota.

Rispondi SOLO con JSON: {"non_supportate": ["..."]}"""

CORREGGI = """Il fact-checker ha trovato queste affermazioni non supportate dagli articoli. \
Riscrivi il testo eliminandole o rendendole fedeli agli articoli, senza aggiungere altro. \
Rispondi SOLO con JSON, nello stesso formato di prima."""


def chiedi_claude(testo):
    if not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        raise IANonDisponibile("manca CLAUDE_CODE_OAUTH_TOKEN nei Secrets")
    try:
        esito = subprocess.run(["claude", "-p", testo, "--output-format", "json", "--tools", ""],
                               capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as errore:
        raise IANonDisponibile(f"Claude: {errore}")
    if esito.returncode != 0:
        raise IANonDisponibile(f"Claude: {(esito.stderr or esito.stdout)[-300:]}")
    try:
        dati = json.loads(esito.stdout)
    except ValueError:
        return esito.stdout
    if dati.get("is_error"):
        raise IANonDisponibile(f"Claude: {str(dati.get('result'))[:300]}")
    return dati.get("result", "")


def chiedi_json(testo, chiedi=None):
    risposta = (chiedi or chiedi_claude)(testo)
    try:
        return json.loads(re.search(r"\{.*\}", risposta, re.S).group(0))
    except (AttributeError, ValueError, TypeError):
        return {}


def _elenco(articoli, sommario=240):
    roma = ZoneInfo("Europe/Rome")
    return "\n".join(f"[{a['n']}] {a['fonte']} | {a['quando'].astimezone(roma):%d/%m %H:%M} "
                     f"| {a['titolo']} — {a['sommario'][:sommario]}" for a in articoli)


def scrivi_e_controlla(citati, chiedi=None):
    """Testo scritto da Claude e controllato due volte. None se non supera i controlli."""
    articoli = "ARTICOLI:\n" + _elenco(citati)
    scritto = chiedi_json(SCRIVI + "\n\n" + articoli, chiedi)
    for giro in range(2):
        if not scritto.get("titolo") or not isinstance(scritto.get("frasi"), list):
            return None, "testo non valido"
        scritto["frasi"] = [str(f).strip() for f in scritto["frasi"] if str(f).strip()][:3]
        verifica = chiedi_json(CONTROLLA + "\n\n" + articoli + "\n\nTESTO:\n"
                               + json.dumps(scritto, ensure_ascii=False), chiedi)
        problemi = list(verifica.get("non_supportate", ["controllo non riuscito"])) \
            if isinstance(verifica.get("non_supportate", None), list) else ["controllo non riuscito"]
        problemi += controlli_automatici(scritto, citati)
        if not problemi:
            return scritto, "verificata"
        print(f"  Controllo {giro + 1}: {problemi}")
        if giro == 1:
            break
        scritto = chiedi_json(SCRIVI + "\n\n" + articoli + "\n\nLA TUA RISPOSTA PRECEDENTE:\n"
                              + json.dumps(scritto, ensure_ascii=False) + "\n\n" + CORREGGI + "\n"
                              + json.dumps(problemi, ensure_ascii=False), chiedi)
    return None, f"non supera i controlli: {problemi[:3]}"


def notizia_del_giorno(gia_usati=(), chiedi=None, adesso=None):
    """Restituisce (notizia, None) oppure (None, motivo)."""
    articoli, esiti = raccogli(adesso)
    testate = {a["fonte"] for a in articoli}
    if len(articoli) < 6 or len(testate) < MIN_TESTATE:
        return None, f"troppe poche notizie lette ({len(articoli)} da {len(testate)} testate): {esiti}"
    per_numero = {a["n"]: a for a in articoli}
    scelta = chiedi_json(SCEGLI + "\n\nARTICOLI:\n" + _elenco(articoli, 150), chiedi)
    motivi = []
    for storia in (scelta.get("notizie") or [])[:4]:
        numeri = [n for n in storia.get("articoli", []) if isinstance(n, int) and n in per_numero]
        citati = [per_numero[n] for n in dict.fromkeys(numeri)]
        motivo = valida_storia(storia, citati, gia_usati)
        if motivo:
            motivi.append(f"{storia.get('fatto', '?')[:60]}: {motivo}")
            print(f"  Scartata: {motivi[-1]}")
            continue
        scritto, esito = scrivi_e_controlla(citati, chiedi)
        if not scritto:
            motivi.append(f"{storia.get('fatto', '?')[:60]}: {esito}")
            print(f"  Scartata: {motivi[-1]}")
            continue
        fonti = list(dict.fromkeys(a["fonte"] for a in citati))
        print(f"  Notizia verificata su {len(fonti)} testate: {scritto['titolo']}")
        return {**scritto, "fonti": fonti[:4], "articoli": [{"fonte": a["fonte"], "titolo": a["titolo"],
                                                              "link": a["link"]} for a in citati][:6],
                "soggetti": storia.get("soggetti", []), "chiave": chiave_storia(storia)}, None
    return None, "; ".join(motivi) or "nessuna notizia confermata da almeno 3 testate"
