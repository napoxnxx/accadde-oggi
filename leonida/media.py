"""Immagini e clip ufficiali di GTA VI, dalla pagina di Rockstar "Download and share"
(https://www.rockstargames.com/VI/media). Si scaricano una volta e restano in cache su GitHub.

Le clip si usano sempre SENZA il loro audio (la musica dei trailer è protetta da Content ID).
Se i file non sono disponibili, si usa un tramonto in stile Vice City disegnato da zero.
"""

import json
import random
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import requests
from PIL import Image

RADICE = Path(__file__).resolve().parent.parent
CARTELLA = RADICE / "media_rockstar"
_BASE = "https://media-rockstargames-com.akamaized.net/VI/downloads"
# Tutti i pacchetti ufficiali della pagina "Download and share": più immagini possibile.
PACCHETTI = {
    "screenshot": f"{_BASE}/screenshots/GTAVI_Screenshots.zip",
    "edizioni": f"{_BASE}/screenshots/GTAVI_Ultimate_Edition_Benefits.zip",
    "vintage": f"{_BASE}/screenshots/GTAVI_Vintage_Vice_City_Pack.zip",
    "artwork": f"{_BASE}/artwork_wallpapers/GTAVI_Artwork_Wallpapers.zip",
    "clip": f"{_BASE}/videos/GTAVI_Videos.zip",
}
MAX_BYTE = {"screenshot": 4_000_000_000, "edizioni": 1_500_000_000, "vintage": 1_500_000_000,
            "artwork": 2_000_000_000, "clip": 8_000_000_000}
TIPI_FOTO = ("screenshot", "artwork", "edizioni", "vintage")
UA = {"User-Agent": "Mozilla/5.0 (compatible; UntilLeonidaBot/1.0)"}
CREDITO = "Immagini: Rockstar Games"
ESTENSIONI_FOTO = {".jpg", ".jpeg", ".png"}
ESTENSIONI_VIDEO = {".mp4", ".mov", ".m4v", ".webm"}


_RUMORE = r"(?i)\b(gtavi?|gta|vi|screenshots?|wallpapers?|video|clip|landscape|portrait|mobile|desktop|\d{3,4}x\d{3,4}|\d+k)\b"
_NON_DIDASCALIA = ("COVER", "ART", "LOGO", "EDITION", "PACK", "BADGE", "POSTER", "KEY", "ALBUM")


def didascalia(nome_file):
    """Didascalia dal nome ufficiale del file: Vice_City_27.jpg -> VICE CITY; Jason_and_Lucia_14 -> JASON E LUCIA."""
    base = re.sub(r"\.[a-z0-9]+$", "", Path(nome_file).name, flags=re.I)
    base = re.sub(r"[_\-]+", " ", base)
    base = re.sub(_RUMORE, " ", base)
    base = re.sub(r"\b\d+\b", " ", base)
    base = re.sub(r"\band\b", "e", base, flags=re.I)
    return re.sub(r"\s+", " ", base).strip().upper()


def didascalia_mostrabile(testo):
    """Solo nomi di luoghi e personaggi: niente 'COVER ART', 'ULTIMATE EDITION' e simili."""
    parole = set(testo.split())
    return testo if testo and len(testo) <= 28 and not parole & set(_NON_DIDASCALIA) else ""


def _chiave(nome):
    """Stessa immagine in formati diversi = stessa chiave (si tiene la versione più grande)."""
    base = re.sub(r"\.[a-z0-9]+$", "", nome, flags=re.I)
    verticale = "P" if re.search(r"(?i)portrait|mobile|vertical", base) else "L"
    base = re.sub(r"(?i)\d{3,4}x\d{3,4}|\d+k\b", " ", base)
    numeri = re.findall(r"\d+", base)
    return f"{didascalia(nome)}#{numeri[-1] if numeri else ''}#{verticale}"


def _scarica(url, destinazione, massimo):
    with requests.get(url, headers=UA, stream=True, timeout=60) as r:
        r.raise_for_status()
        dimensione = int(r.headers.get("Content-Length") or 0)
        if dimensione > massimo:
            raise RuntimeError(f"pacchetto troppo grande ({dimensione / 1e9:.1f} GB)")
        scritti = 0
        with open(destinazione, "wb") as f:
            for blocco in r.iter_content(1 << 20):
                f.write(blocco)
                scritti += len(blocco)
                if scritti > massimo:
                    raise RuntimeError("pacchetto troppo grande")


def _prepara_foto(sorgente, destinazione):
    with Image.open(sorgente) as img:
        img = img.convert("RGB")
        if img.width < 1200 or img.height < 600:
            return False
        if img.height > 2600:
            img = img.resize((int(img.width * 2600 / img.height), 2600), Image.LANCZOS)
        img.save(destinazione, "JPEG", quality=90)
    return True


def _prepara_clip(sorgente, destinazione):
    """Clip ridotta a 1080p H.264, senza audio: leggera da tenere in cache e da usare come fondale."""
    esito = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(sorgente), "-an", "-t", "40",
                            "-vf", "scale=-2:1080", "-c:v", "libx264", "-crf", "22", "-preset", "veryfast",
                            "-pix_fmt", "yuv420p", str(destinazione)], capture_output=True)
    return esito.returncode == 0 and destinazione.exists()


def _firma(url):
    """ETag/data/dimensione del pacchetto sul server: se cambia, Rockstar l'ha aggiornato."""
    try:
        r = requests.head(url, headers=UA, timeout=30, allow_redirects=True)
        if r.status_code >= 400:
            return None
        return "|".join(r.headers.get(k, "") for k in ("ETag", "Last-Modified", "Content-Length"))
    except requests.RequestException:
        return None


def prepara():
    """Scarica e sistema i pacchetti ufficiali nuovi o aggiornati. Restituisce l'elenco dei file pronti."""
    elenco_file = CARTELLA / "elenco.json"
    elenco = json.loads(elenco_file.read_text()) if elenco_file.exists() else {}
    firme = elenco.setdefault("_firme", {})
    for tipo, url in PACCHETTI.items():
        firma = _firma(url)
        if elenco.get(tipo) and (firma is None or firma == firme.get(tipo)):
            continue
        if firma is None and not elenco.get(tipo):
            print(f"  Pacchetto '{tipo}' non raggiungibile adesso: riprovo al prossimo giro.")
            continue
        cartella_tipo = CARTELLA / tipo
        cartella_tipo.mkdir(parents=True, exist_ok=True)
        temporaneo = CARTELLA / f"{tipo}.zip"
        try:
            print(f"Scarico il pacchetto ufficiale '{tipo}' da Rockstar…")
            _scarica(url, temporaneo, MAX_BYTE[tipo])
            pronti, visti = [], set()
            with zipfile.ZipFile(temporaneo) as z:
                voci = sorted(z.infolist(), key=lambda v: -v.file_size)  # prima le versioni più grandi
                for voce in voci:
                    estensione = Path(voce.filename).suffix.lower()
                    nome = Path(voce.filename).name
                    if nome.startswith(".") or voce.is_dir():
                        continue
                    chiave = _chiave(nome) + estensione
                    if chiave in visti:
                        continue
                    sorgente = CARTELLA / "estratto" / nome
                    sorgente.parent.mkdir(exist_ok=True)
                    if tipo != "clip" and estensione in ESTENSIONI_FOTO:
                        with z.open(voce) as d, open(sorgente, "wb") as f:
                            shutil.copyfileobj(d, f)
                        meta = cartella_tipo / (Path(nome).stem + ".jpg")
                        if _prepara_foto(sorgente, meta):
                            pronti.append({"file": str(meta.relative_to(RADICE)), "didascalia": didascalia(nome)})
                            visti.add(chiave)
                    elif tipo == "clip" and estensione in ESTENSIONI_VIDEO:
                        with z.open(voce) as d, open(sorgente, "wb") as f:
                            shutil.copyfileobj(d, f)
                        meta = cartella_tipo / (Path(nome).stem + ".mp4")
                        if _prepara_clip(sorgente, meta):
                            pronti.append({"file": str(meta.relative_to(RADICE)), "didascalia": didascalia(nome)})
                            visti.add(chiave)
                    sorgente.unlink(missing_ok=True)
            if pronti:
                for vecchio in elenco.get(tipo, []):  # via i file della versione precedente
                    if vecchio["file"] not in {p["file"] for p in pronti}:
                        (RADICE / vecchio["file"]).unlink(missing_ok=True)
                elenco[tipo] = pronti
                firme[tipo] = firma
            print(f"  {len(pronti)} file '{tipo}' pronti")
        except (requests.RequestException, zipfile.BadZipFile, RuntimeError, OSError) as errore:
            print(f"  Pacchetto '{tipo}' non disponibile: {errore}")
        finally:
            temporaneo.unlink(missing_ok=True)
            shutil.rmtree(CARTELLA / "estratto", ignore_errors=True)
    CARTELLA.mkdir(parents=True, exist_ok=True)
    elenco_file.write_text(json.dumps(elenco, ensure_ascii=False, indent=1))
    return elenco


def _compatto(testo):
    return re.sub(r"[^A-Z0-9]", "", (testo or "").upper())


def scegli_per(elenco, parole, seme, quanti=1, evita=()):
    """File ufficiali il cui nome contiene una delle parole (es. LUCIA, VICE CITY). [] se nessuno."""
    chiavi = [_compatto(p) for p in parole if _compatto(p)]
    adatti = [dict(v, tipo=t) for t in TIPI_FOTO for v in elenco.get(t, [])
              if (RADICE / v["file"]).exists()
              and any(k in _compatto(v.get("didascalia", "")) or k in _compatto(Path(v["file"]).stem) for k in chiavi)]
    if not adatti:
        return []
    freschi = [v for v in adatti if v["file"] not in set(evita)] or adatti
    random.Random(seme).shuffle(freschi)
    return [dict(v, percorso=str(RADICE / v["file"])) for v in freschi[:quanti]]


def scegli(elenco, seme, quanti=1, tipi=("screenshot", "artwork"), evita=()):
    """File ufficiali a caso (ma riproducibili), evitando quelli usati di recente se possibile."""
    tutti = [dict(v, tipo=t) for t in tipi for v in elenco.get(t, []) if (RADICE / v["file"]).exists()]
    if not tutti:
        return []
    freschi = [v for v in tutti if v["file"] not in set(evita)] or tutti
    random.Random(seme).shuffle(freschi)
    return [dict(v, percorso=str(RADICE / v["file"])) for v in freschi[:quanti]]
