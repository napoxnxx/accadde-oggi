"""Grafica di UNTIL LEONIDA: Short verticali 1080x1920 a 30 fps, in stile Vice City.

Fondali: immagini ufficiali Rockstar che si muovono piano (effetto Ken Burns), clip ufficiali
senza audio, oppure un tramonto synthwave disegnato da zero. Sopra: testi, conto alla rovescia,
notizie. Audio: musica synthwave originale (musica.py) più piccoli effetti sonori.
"""

import math
import random
import subprocess
import tempfile
import wave
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import musica

RADICE = Path(__file__).resolve().parent.parent
CARATTERI = RADICE / "caratteri"
L, A = 1080, 1920
FPS = 30
ROSA = (255, 46, 136)
ARANCIO = (255, 150, 30)
VIOLA = (110, 40, 190)
AZZURRO = (40, 220, 240)
BIANCO = (255, 255, 255)
NERO = (14, 6, 24)
X_MIN, X_MAX = 64, 936      # zona sicura: a destra ci sono i pulsanti degli Shorts
Y_MAX = 1500                # sotto ci sono titolo e nome del canale

FILE_CARATTERI = {"titolo": "Anton-Regular.ttf", "forte": "BarlowCondensed-ExtraBold.ttf",
                  "bold": "BarlowCondensed-Bold.ttf", "semi": "BarlowCondensed-SemiBold.ttf",
                  "medio": "BarlowCondensed-Medium.ttf"}


# ---------------------------------------------------------------- testo

@lru_cache(maxsize=None)
def _supportati(nome):
    from fontTools.ttLib import TTFont
    return set(TTFont(str(CARATTERI / FILE_CARATTERI[nome])).getBestCmap())


@lru_cache(maxsize=None)
def carattere(nome, dimensione):
    from PIL import ImageFont
    return ImageFont.truetype(str(CARATTERI / FILE_CARATTERI[nome]), int(dimensione))


def stile_per(testo, preferito):
    if all(ord(c) in _supportati(preferito) or c.isspace() for c in testo):
        return preferito
    return "forte"


def larghezza(testo, stile, dim):
    return carattere(stile, dim).getlength(testo)


def adatta(testo, stile, massima, larghezza_max, minima=24):
    dim = int(massima)
    while dim > minima and larghezza(testo, stile, dim) > larghezza_max:
        dim -= 2
    return dim


def immagine_testo(testo, stile, dim, colore, ombra=True):
    f = carattere(stile, dim)
    x0, y0, x1, y1 = f.getbbox(testo)
    m = int(dim * 0.12) + 6
    img = Image.new("RGBA", (int(x1 - x0) + 2 * m, int(y1 - y0) + 2 * m), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if ombra:
        d.text((m - x0 + 3, m - y0 + 5), testo, font=f, fill=(0, 0, 0, 160))
    d.text((m - x0, m - y0), testo, font=f, fill=colore)
    return img


def sfumatura(larg, alt, alto=ROSA, basso=ARANCIO):
    y = np.linspace(0, 1, alt)[:, None, None]
    colori = np.array(alto, np.float32) * (1 - y) + np.array(basso, np.float32) * y
    return Image.fromarray(np.broadcast_to(colori, (alt, larg, 3)).astype(np.uint8), "RGB")


def testo_sfumato(testo, stile, dim, alto=ROSA, basso=ARANCIO, alone=True):
    """Testo riempito con la sfumatura rosa-arancio del tramonto, con alone luminoso dietro."""
    f = carattere(stile, dim)
    x0, y0, x1, y1 = f.getbbox(testo)
    m = int(dim * 0.25) + 10
    larg, alt = int(x1 - x0) + 2 * m, int(y1 - y0) + 2 * m
    maschera = Image.new("L", (larg, alt), 0)
    ImageDraw.Draw(maschera).text((m - x0, m - y0), testo, font=f, fill=255)
    img = Image.new("RGBA", (larg, alt), (0, 0, 0, 0))
    if alone:
        bagliore = Image.new("RGBA", (larg, alt), (*alto, 0))
        bagliore.putalpha(maschera.filter(ImageFilter.GaussianBlur(dim * 0.07)).point(lambda v: int(v * 0.85)))
        img.alpha_composite(bagliore)
    ombra = Image.new("RGBA", (larg, alt), (*NERO, 0))
    ombra.putalpha(maschera.point(lambda v: int(v * 0.55)))
    img.alpha_composite(ombra, (4, 8))
    colore = sfumatura(larg, alt, alto, basso).convert("RGBA")
    colore.putalpha(maschera)
    img.alpha_composite(colore)
    return img


def righe_a_capo(testo, stile, dim, larghezza_max):
    righe, corrente = [], ""
    for parola in testo.split():
        prova = f"{corrente} {parola}".strip()
        if not corrente or larghezza(prova, stile, dim) <= larghezza_max:
            corrente = prova
        else:
            righe.append(corrente)
            corrente = parola
    if corrente:
        righe.append(corrente)
    return righe


def blocco_testo(testo, stile, dim_max, larghezza_max, max_righe, colore, dim_min=30, interlinea=1.12):
    stile = stile_per(testo, stile)
    dim = int(dim_max)
    while dim > dim_min:
        righe = righe_a_capo(testo, stile, dim, larghezza_max)
        if len(righe) <= max_righe and all(larghezza(r, stile, dim) <= larghezza_max for r in righe):
            break
        dim -= 3
    righe = righe_a_capo(testo, stile, dim, larghezza_max)
    f = carattere(stile, dim)
    passo = int(dim * interlinea)
    img = Image.new("RGBA", (int(larghezza_max) + 24, passo * len(righe) + int(dim * 0.45)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, riga in enumerate(righe):
        d.text((12 + 3, i * passo + 5), riga, font=f, fill=(0, 0, 0, 170))
        d.text((12, i * passo), riga, font=f, fill=colore)
    return img


def etichetta(testo, fondo=ROSA, colore=BIANCO, dim=42):
    f = carattere("forte", dim)
    lg, alt = int(f.getlength(testo) + 52), int(dim * 1.55)
    k = 2
    img = Image.new("RGBA", (lg * k, alt * k), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle((0, 0, lg * k - 1, alt * k - 1), radius=alt * k // 2, fill=fondo)
    img = img.resize((lg, alt), Image.LANCZOS)
    ImageDraw.Draw(img).text((lg / 2, alt / 2 + 2), testo, font=f, fill=colore, anchor="mm")
    return img


def riga_piccola(testo, dim=27):
    testo = testo if len(testo) <= 95 else testo[:92] + "…"
    dim = adatta(testo, "medio", dim, X_MAX - X_MIN, minima=18)
    return immagine_testo(testo, "medio", dim, (255, 255, 255, 215))


def scheda_domanda(riga1, riga2="SCRIVILO NEI COMMENTI"):
    larg = X_MAX - X_MIN
    t1 = blocco_testo(riga1, "titolo", 92, larg - 80, 3, BIANCO, dim_min=50)
    alt = t1.height + 150
    img = Image.new("RGBA", (larg, alt), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, larg - 1, alt - 1), radius=40, fill=(20, 6, 34, 235), outline=ROSA, width=6)
    img.alpha_composite(t1, (40 - 12, 40))
    d.text((larg / 2, alt - 70), riga2, font=carattere("forte", 50), fill=ARANCIO, anchor="mm")
    return img


def intestazione():
    """UNTIL in bianco, LEONIDA con la sfumatura del tramonto."""
    img = Image.new("RGBA", (L, 140), (0, 0, 0, 0))
    a = immagine_testo("UNTIL", "titolo", 62, BIANCO)
    b = testo_sfumato("LEONIDA", "titolo", 62, alone=False)
    spazio = 18
    tot = a.width + b.width + spazio - 30
    x = (L - tot) // 2
    img.alpha_composite(a, (x, 18))
    img.alpha_composite(b, (x + a.width + spazio - 30, 18 - (b.height - a.height) // 2))
    ImageDraw.Draw(img).rounded_rectangle((L / 2 - 70, 120, L / 2 + 70, 127), radius=4, fill=ROSA)
    return img


def opacita(img, fattore):
    if fattore >= 0.999:
        return img
    copia = img.copy()
    copia.putalpha(copia.getchannel("A").point(lambda v: int(v * max(0.0, fattore))))
    return copia


def scala(img, fattore):
    if abs(fattore - 1) < 0.01:
        return img
    return img.resize((max(1, int(img.width * fattore)), max(1, int(img.height * fattore))), Image.LANCZOS)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_back(x):
    x = min(max(x, 0.0), 1.0)
    return 1 + 2.70158 * (x - 1) ** 3 + 1.70158 * (x - 1) ** 2


# ---------------------------------------------------------------- fondali

@lru_cache(maxsize=4)
def velo(scuro=0.5):
    """Sfumatura scura in alto e in basso, per leggere bene i testi su qualsiasi immagine."""
    y = np.linspace(0, 1, A)
    alto = np.clip(1 - y / 0.25, 0, 1) * 0.75
    basso = np.clip((y - 0.55) / 0.45, 0, 1) * 0.9
    alfa = np.clip(scuro + (1 - scuro) * np.maximum(alto, basso) * 0.9, 0, 0.93) * 255
    livello = np.zeros((A, L, 4), np.uint8)
    livello[..., :3] = np.array([18, 4, 30], np.uint8)
    livello[..., 3] = alfa[:, None].astype(np.uint8)
    return Image.fromarray(livello, "RGBA")


def tramonto(seme=0):
    """Tramonto synthwave: cielo viola-rosa, sole a strisce, griglia al neon e palme."""
    rnd = random.Random(seme)
    larg, alt = int(L * 1.2), int(A * 1.2)
    orizzonte = int(alt * 0.6)
    y = np.linspace(0, 1, orizzonte)[:, None]
    cima, mezzo, fondo = np.array([16, 0, 40]), np.array([110, 20, 150]), np.array([255, 90, 120])
    cielo = np.where(y < 0.55, cima + (mezzo - cima) * (y / 0.55), mezzo + (fondo - mezzo) * ((y - 0.55) / 0.45))
    img = np.zeros((alt, larg, 3), np.float32)
    img[:orizzonte] = cielo[:, None, :]
    img[orizzonte:] = np.array([22, 4, 40])
    base = Image.fromarray(img.astype(np.uint8), "RGB").convert("RGBA")
    d = ImageDraw.Draw(base)
    for _ in range(90):
        sx, sy = rnd.randrange(larg), rnd.randrange(int(orizzonte * 0.5))
        r = rnd.choice([1, 1, 2])
        d.ellipse((sx - r, sy - r, sx + r, sy + r), fill=(255, 255, 255, rnd.randrange(80, 220)))
    raggio = int(larg * 0.3)
    cx, cy = larg // 2, orizzonte - int(raggio * 0.35)
    sole = sfumatura(2 * raggio, 2 * raggio, (255, 230, 90), (255, 40, 140)).convert("RGBA")
    maschera = Image.new("L", (2 * raggio, 2 * raggio), 0)
    md = ImageDraw.Draw(maschera)
    md.ellipse((0, 0, 2 * raggio - 1, 2 * raggio - 1), fill=255)
    for i in range(7):  # strisce del sole
        yy = int(raggio * (1.05 + i * 0.13))
        md.rectangle((0, yy, 2 * raggio, yy + int(6 + i * 3.5)), fill=0)
    sole.putalpha(maschera)
    alone = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(alone).ellipse((cx - raggio * 1.5, cy - raggio * 1.5, cx + raggio * 1.5, cy + raggio * 1.5),
                                  fill=(255, 60, 140, 90))
    base.alpha_composite(alone.filter(ImageFilter.GaussianBlur(80)))
    base.alpha_composite(sole, (cx - raggio, cy - raggio))
    d = ImageDraw.Draw(base)
    d.rectangle((0, orizzonte, larg, alt), fill=(22, 4, 40, 255))
    for i in range(1, 16):  # linee orizzontali della griglia, sempre più fitte verso l'orizzonte
        yy = orizzonte + int((alt - orizzonte) * (i / 15) ** 2.2)
        d.line((0, yy, larg, yy), fill=(255, 46, 136, 200), width=3)
    for i in range(-14, 15):
        d.line((cx + i * 40, orizzonte, cx + i * 220, alt), fill=(255, 46, 136, 170), width=3)
    d.line((0, orizzonte, larg, orizzonte), fill=(255, 120, 200, 255), width=5)
    for lato in (-1, 1):  # palme in controluce
        px = cx + lato * int(larg * 0.4)
        piede = orizzonte + 160
        cima_x, cima_y = px - lato * 70, orizzonte - int(alt * 0.33)
        tronco = [(px - 16, piede), (px + 16, piede), (cima_x + 8, cima_y), (cima_x - 8, cima_y)]
        d.polygon(tronco, fill=(10, 0, 18, 255))
        for k in range(8):
            ang = math.radians(-160 + k * 40 + rnd.uniform(-8, 8))
            lunghezza = rnd.randint(180, 260)
            punti = [(cima_x + math.cos(ang) * lunghezza * s,
                      cima_y + math.sin(ang) * lunghezza * s + 90 * s * s) for s in np.linspace(0, 1, 12)]
            d.line(punti, fill=(10, 0, 18, 255), width=22, joint="curve")
    return base.convert("RGB")


class Fondale:
    """Immagine (ufficiale o tramonto) che si muove piano: zoom lento e panoramica."""

    def __init__(self, percorso=None, durata=12.0, seme=0, scuro=0.35, sfocato=False):
        img = Image.open(percorso).convert("RGB") if percorso else tramonto(seme)
        alt = int(A / 0.78)
        larg = int(img.width * alt / img.height)
        if larg < int(L / 0.78):
            larg = int(L / 0.78)
            alt = int(img.height * larg / img.width)
        self.img = img.resize((larg, alt), Image.BILINEAR)
        if sfocato:
            self.img = self.img.filter(ImageFilter.GaussianBlur(22))
        rnd = random.Random(seme)
        self.z0, self.z1 = (0.95, 0.80) if rnd.random() < 0.6 else (0.80, 0.93)
        self.x0, self.x1 = rnd.choice([(0.3, 0.7), (0.7, 0.3), (0.45, 0.55)])
        self.durata = max(durata, 0.1)
        self.velo = velo(scuro)

    def __call__(self, t):
        p = min(max(t / self.durata, 0.0), 1.0)
        p = p * p * (3 - 2 * p)
        z = self.z0 + (self.z1 - self.z0) * p
        h = int(self.img.height * z)
        w = int(h * L / A)
        if w > self.img.width:
            w, h = self.img.width, int(self.img.width * A / L)
        cx = (self.x0 + (self.x1 - self.x0) * p) * self.img.width
        x = int(min(max(cx - w / 2, 0), self.img.width - w))
        y = int((self.img.height - h) / 2)
        quadro = self.img.crop((x, y, x + w, y + h)).resize((L, A), Image.BILINEAR).convert("RGBA")
        quadro.alpha_composite(self.velo)
        return quadro

    def chiudi(self):
        pass


class FondaleClip:
    """Clip ufficiale ritagliata in verticale, sempre senza audio."""

    def __init__(self, percorso, durata=12.0, seme=0, scuro=0.35):
        self.velo = velo(scuro)
        try:
            lunghezza = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                              "-of", "csv=p=0", str(percorso)], capture_output=True,
                                             text=True).stdout.strip() or 0)
        except ValueError:
            lunghezza = 0
        inizio = random.Random(seme).uniform(0, max(0.0, lunghezza - durata - 0.5)) if lunghezza else 0
        self.processo = subprocess.Popen(
            ["ffmpeg", "-loglevel", "error", "-ss", f"{inizio:.2f}", "-stream_loop", "-1", "-i", str(percorso),
             "-an", "-vf", f"scale=-2:{A},crop={L}:{A}", "-r", str(FPS), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            stdout=subprocess.PIPE)
        self.ultimo = None

    def __call__(self, t):
        dati = self.processo.stdout.read(L * A * 3)
        if len(dati) == L * A * 3:
            self.ultimo = Image.frombytes("RGB", (L, A), dati).convert("RGBA")
            self.ultimo.alpha_composite(self.velo)
        if self.ultimo is None:
            raise RuntimeError("clip non leggibile")
        return self.ultimo.copy()

    def chiudi(self):
        self.processo.kill()
        self.processo.wait()


# ---------------------------------------------------------------- audio e montaggio

SR = musica.SR


def _effetto(nome):
    t = lambda durata: np.arange(int(SR * durata)) / SR  # noqa: E731
    if nome == "colpo":  # botta grave per i numeri che entrano
        x = t(0.6)
        return 0.9 * np.sin(2 * np.pi * (40 + 90 * np.exp(-x * 20)) * x) * np.exp(-x * 6)
    if nome == "fruscio":
        x = t(0.3)
        rumore = np.convolve(np.random.default_rng(3).normal(0, 1, x.size), np.ones(30) / 30, mode="same")
        return 0.6 * rumore * np.sin(np.pi * x / x[-1]) ** 2
    if nome == "pop":
        x = t(0.16)
        f = 320 + 900 * x / x[-1]
        return 0.45 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 18)
    if nome == "finale":
        x = t(1.2)
        out = np.zeros(x.size)
        for i, f in enumerate([523.25, 659.25, 784.0, 1046.5]):
            y = x[: x.size - int(SR * 0.075 * i)]
            out[int(SR * 0.075 * i):] += 0.3 * (np.sin(2 * np.pi * f * y) + 0.3 * np.sin(4 * np.pi * f * y)) * np.exp(-y * 4.5)
        return out
    raise ValueError(nome)


class Video:
    def __init__(self, uscita, fondale, seme=0):
        self.uscita = Path(uscita)
        self.lavoro = tempfile.TemporaryDirectory()
        self.muto = Path(self.lavoro.name) / "muto.mp4"
        self.fondale = fondale
        self.testa = intestazione()
        self.seme = seme
        self.n = 0
        self.eventi = []
        self.processo = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{L}x{A}",
             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p", str(self.muto)], stdin=subprocess.PIPE)

    @property
    def tempo(self):
        return self.n / FPS

    def suono(self, nome, ritardo=0.0):
        self.eventi.append((self.tempo + ritardo, nome))

    def fotogramma(self, livelli, fondale=None):
        img = (fondale or self.fondale)(self.tempo)
        img.alpha_composite(self.testa, (0, 96))
        for livello, (x, y) in livelli:
            if livello is None:
                continue
            x, y = int(round(x)), int(round(y))
            if x < 0 or y < 0:
                livello = livello.crop((max(0, -x), max(0, -y), livello.width, livello.height))
                x, y = max(0, x), max(0, y)
            if x >= L or y >= A:
                continue
            if x + livello.width > L or y + livello.height > A:
                livello = livello.crop((0, 0, min(livello.width, L - x), min(livello.height, A - y)))
            img.alpha_composite(livello, (x, y))
        self.processo.stdin.write(img.convert("RGB").tobytes())
        self.n += 1

    def chiudi(self):
        self.processo.stdin.close()
        if self.processo.wait() != 0:
            raise RuntimeError("ffmpeg non è riuscito a creare il video")
        durata = self.tempo
        brano = musica.synthwave(durata, self.seme).astype(np.float64)
        effetti = np.zeros_like(brano)
        for quando, nome in self.eventi:
            s, i = _effetto(nome), int(SR * quando)
            if i < effetti.size:
                fine = min(effetti.size, i + s.size)
                effetti[i:fine] += s[: fine - i]
        totale = 0.62 * brano + 0.75 * effetti
        totale = totale / (np.max(np.abs(totale)) or 1) * 0.9
        audio = Path(self.lavoro.name) / "audio.wav"
        with wave.open(str(audio), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((totale * 32767).astype(np.int16).tobytes())
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(self.muto), "-i", str(audio),
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                        str(self.uscita)], check=True)
        for f in (self.fondale,):
            f.chiudi()
        self.lavoro.cleanup()
        return durata


# ---------------------------------------------------------------- formati

def visibile(img):
    """Dove inizia e finisce davvero il disegno (senza margini e aloni deboli): (alto, basso)."""
    scatola = img.getchannel("A").point(lambda v: 255 if v > 140 else 0).getbbox()
    return (scatola[1], scatola[3]) if scatola else (0, img.height)


def impila(elementi, y_inizio, spazio=24):
    """Mette gli elementi uno sotto l'altro, a `spazio` pixel tra le parti visibili. Restituisce le y."""
    posizioni, y = [], y_inizio
    for img in elementi:
        alto, basso = visibile(img)
        posizioni.append(y - alto)
        y = y - alto + basso + spazio
    return posizioni, y


def _fondale_per(media_scelti, durata, seme, scuro=0.35, sfocato=False):
    if media_scelti:
        m = media_scelti[0]
        try:
            if m.get("tipo") == "clip":
                return FondaleClip(m["percorso"], durata, seme, scuro)
            return Fondale(m["percorso"], durata, seme, scuro, sfocato)
        except (OSError, RuntimeError):
            pass
    return Fondale(None, durata, seme, scuro, sfocato)


def video_countdown(dati, uscita, media_scelti=(), seme=0):
    """MANCANO X GIORNI A GTA VI, con un "lo sapevi?" verificato e una domanda per i commenti."""
    durata, t_domanda = 11.0, 8.3
    fondale = _fondale_per(media_scelti, durata, seme, scuro=0.42)
    video = Video(uscita, fondale, seme)
    giorni = dati["giorni"]
    if giorni <= 0:
        riga1 = immagine_testo("È IL GIORNO", "titolo", 120, BIANCO)
        numero = testo_sfumato("GTA VI", "titolo", 300)
        riga2 = immagine_testo("ESCE OGGI", "titolo", 110, BIANCO)
    else:
        riga1 = immagine_testo("MANCA" if giorni == 1 else "MANCANO", "titolo", 120, BIANCO)
        numero = testo_sfumato(str(giorni), "titolo", 560 if giorni < 10 else 470)
        riga2 = immagine_testo(f"{'GIORNO' if giorni == 1 else 'GIORNI'} A GTA VI", "titolo", 110, BIANCO)
    pill = etichetta("LO SAPEVI?", ROSA)
    fatto = blocco_testo(dati["fatto"], "semi", 50, X_MAX - X_MIN, 3, BIANCO, dim_min=38)
    credito = riga_piccola("Immagini: Rockstar Games") if media_scelti else None
    domanda = scheda_domanda(dati["domanda"])
    (y_riga1, y_numero, y_riga2, y_pill), y_fine = impila([riga1, numero, riga2, pill], 300, spazio=26)
    y_fatto = y_fine - 8
    eccesso = y_fatto + fatto.height - (Y_MAX - 10)
    if eccesso > 0:  # se non entra, si sale tutto insieme
        y_riga1, y_numero, y_riga2, y_pill, y_fatto = (v - eccesso for v in (y_riga1, y_numero, y_riga2, y_pill, y_fatto))
    video.suono("pop")
    video.suono("colpo", 0.45)
    video.suono("fruscio", 1.6)
    video.suono("finale", t_domanda)
    inizio = video.tempo
    while video.tempo - inizio < durata:
        t = video.tempo - inizio
        livelli = []
        p1 = ease_back(t / 0.3)
        r1 = scala(riga1, 0.7 + 0.3 * p1)
        livelli.append((opacita(r1, ease_out(t / 0.2)), ((L - r1.width) / 2, y_riga1 + (riga1.height - r1.height) / 2)))
        pn = ease_out((t - 0.45) / 0.35)
        if pn > 0:
            battito = 1 + 0.025 * math.sin(t * 2 * math.pi * 1.8)
            n = scala(numero, (1.7 - 0.7 * pn) * battito)
            livelli.append((opacita(n, pn), ((L - n.width) / 2, y_numero + (numero.height - n.height) / 2)))
        pr = ease_out((t - 0.9) / 0.3)
        if pr > 0:
            livelli.append((opacita(riga2, pr), ((L - riga2.width) / 2, y_riga2)))
        pf = ease_out((t - 1.6) / 0.35)
        if pf > 0:
            attenua = 0.35 if t >= t_domanda else 1
            livelli.append((opacita(pill, pf * attenua), (X_MIN, y_pill)))
            livelli.append((opacita(fatto, pf * attenua), (X_MIN - 12 + 40 * (1 - pf), y_fatto)))
        if credito is not None:
            livelli.append((credito, ((X_MIN + X_MAX) / 2 - credito.width / 2, Y_MAX + 6)))
        if t >= t_domanda:
            pd = ease_back((t - t_domanda) / 0.35)
            ds = scala(domanda, 0.7 + 0.3 * pd)
            livelli.append((opacita(ds, ease_out((t - t_domanda) / 0.2)), ((X_MIN + X_MAX) / 2 - ds.width / 2,
                                                                          900 - ds.height / 2)))
        video.fotogramma(livelli)
    return video.chiudi()


def foto_riquadro(percorso, larg, alt, raggio=28, bordo=6):
    foto = Image.open(percorso).convert("RGB")
    rapporto = larg / alt
    if foto.width / foto.height > rapporto:
        nuova = int(foto.height * rapporto)
        foto = foto.crop(((foto.width - nuova) // 2, 0, (foto.width - nuova) // 2 + nuova, foto.height))
    else:
        nuova = int(foto.width / rapporto)
        foto = foto.crop((0, (foto.height - nuova) // 2, foto.width, (foto.height - nuova) // 2 + nuova))
    foto = foto.resize((larg, alt), Image.LANCZOS).convert("RGBA")
    maschera = Image.new("L", (larg * 2, alt * 2), 0)
    ImageDraw.Draw(maschera).rounded_rectangle((0, 0, larg * 2 - 1, alt * 2 - 1), radius=raggio * 2, fill=255)
    foto.putalpha(maschera.resize((larg, alt), Image.LANCZOS))
    img = Image.new("RGBA", (larg + 2 * bordo, alt + 2 * bordo), (0, 0, 0, 0))
    cornice = sfumatura(img.width, img.height).convert("RGBA")
    m2 = Image.new("L", img.size, 0)
    ImageDraw.Draw(m2).rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius=raggio + bordo, fill=255)
    cornice.putalpha(m2)
    img.alpha_composite(cornice)
    img.alpha_composite(foto, (bordo, bordo))
    return img


def _tempo_lettura(testo):
    return max(2.4, len(testo) / 16.0)


def video_notizia(notizia, uscita, media_scelti=(), seme=0):
    """Notizia su GTA VI: titolo, immagine ufficiale, 2-3 frasi, fonti, domanda per i commenti."""
    largo = X_MAX - X_MIN
    foto_possibile = bool(media_scelti) and media_scelti[0].get("tipo") != "clip"
    # si rimpicciolisce il testo finché c'è posto per la foto ufficiale (le foto sono la cosa che si guarda)
    for dim_titolo, dim_frasi in ((98, 52), (90, 48), (84, 45), (78, 42), (72, 40)):
        titolo = blocco_testo(notizia["titolo"].upper(), "titolo", dim_titolo, largo, 3, BIANCO, dim_min=52)
        frasi = [blocco_testo(f, "semi", dim_frasi, largo, 3, BIANCO, dim_min=36) for f in notizia["frasi"]]
        spazio = Y_MAX - 50 - (320 + titolo.height + 20) - sum(f.height for f in frasi) - 16 * len(frasi)
        if not foto_possibile or spazio >= 330:
            break
    tempi, t = [], 1.5
    for testo in notizia["frasi"]:
        tempi.append(t)
        t += _tempo_lettura(testo)
    t_domanda = t + 0.3
    durata = t_domanda + 2.8
    fondale = _fondale_per(media_scelti, durata, seme, scuro=0.58, sfocato=True)
    video = Video(uscita, fondale, seme)
    pill = etichetta(notizia.get("etichetta", "NEWS GTA VI"), ROSA)
    y_titolo = 320
    y = y_titolo + titolo.height + 20
    spazio_frasi = sum(f.height for f in frasi) + 16 * len(frasi)
    riquadro = None
    disponibile = Y_MAX - 50 - y - spazio_frasi
    if foto_possibile and disponibile >= 250:
        try:
            riquadro = foto_riquadro(media_scelti[0]["percorso"], largo - 12, int(min(520, disponibile - 24)))
        except OSError:
            riquadro = None
    y_riquadro = y
    y_frasi = y + (riquadro.height + 22 if riquadro else 10)
    posizioni = []
    for f in frasi:
        posizioni.append(y_frasi)
        y_frasi += f.height + 16
    fonti = riga_piccola("Fonti: " + ", ".join(notizia["fonti"]), 28)
    credito = riga_piccola("Immagini: Rockstar Games", 24) if media_scelti else None
    domanda = scheda_domanda(notizia.get("domanda") or "TU COSA NE PENSI?")
    video.suono("pop")
    if riquadro:
        video.suono("fruscio", 0.7)
    for tt in tempi:
        video.suono("fruscio", tt)
    video.suono("finale", t_domanda)
    inizio = video.tempo
    while video.tempo - inizio < durata:
        t = video.tempo - inizio
        livelli = [(scala(pill, 0.6 + 0.4 * ease_back(t / 0.3)), (X_MIN, 238))]
        tit = scala(titolo, 0.85 + 0.15 * ease_back((t - 0.1) / 0.35))
        livelli.append((opacita(tit, ease_out((t - 0.1) / 0.25)), (X_MIN - 12, y_titolo)))
        if riquadro is not None:
            pf = ease_back((t - 0.7) / 0.35)
            if pf > 0:
                fs = scala(riquadro, 0.75 + 0.25 * pf)
                livelli.append((opacita(fs, ease_out((t - 0.7) / 0.2) * (0.35 if t >= t_domanda else 1)),
                                ((X_MIN + X_MAX) / 2 - fs.width / 2, y_riquadro + (riquadro.height - fs.height) / 2)))
        for img, y0, t0 in zip(frasi, posizioni, tempi):
            pf = ease_out((t - t0) / 0.3)
            if pf > 0:
                livelli.append((opacita(img, pf * (0.35 if t >= t_domanda else 1.0)), (X_MIN - 12 + 40 * (1 - pf), y0)))
        livelli.append((fonti, ((X_MIN + X_MAX) / 2 - fonti.width / 2, Y_MAX + 4)))
        if credito is not None:
            livelli.append((credito, ((X_MIN + X_MAX) / 2 - credito.width / 2, Y_MAX + 40)))
        if t >= t_domanda:
            pd = ease_back((t - t_domanda) / 0.35)
            ds = scala(domanda, 0.7 + 0.3 * pd)
            centro = y_riquadro + riquadro.height / 2 if riquadro is not None else 960
            livelli.append((opacita(ds, ease_out((t - t_domanda) / 0.2)),
                            ((X_MIN + X_MAX) / 2 - ds.width / 2, centro - ds.height / 2)))
        video.fotogramma(livelli)
    return video.chiudi()


def video_montaggio(dati, uscita, media_scelti=(), seme=0):
    """Benvenuti a Leonida: 4 immagini ufficiali in sequenza, con didascalie e domanda finale."""
    scene = list(media_scelti)[:4] or [None]
    per_scena = 2.6
    durata = per_scena * len(scene) + 2.6
    fondali = [_fondale_per([m] if m else [], per_scena + 0.6, seme + i, scuro=0.3) for i, m in enumerate(scene)]
    video = Video(uscita, fondali[0], seme)
    titolo = testo_sfumato(dati.get("titolo", "BENVENUTI A LEONIDA"), "titolo", 104)
    titolo = scala(titolo, min(1.0, (X_MAX - X_MIN) / titolo.width))
    pill = etichetta(dati["contatore"], ARANCIO, NERO) if dati.get("contatore") else None
    didascalie = [etichetta(m["didascalia"], (20, 6, 34), BIANCO, 40) if m and m.get("didascalia") else None
                  for m in scene]
    credito = riga_piccola("Immagini: Rockstar Games") if any(scene) else None
    domanda = scheda_domanda(dati["domanda"])
    t_domanda = per_scena * len(scene)
    for i in range(len(scene)):
        video.suono("fruscio", i * per_scena)
    video.suono("pop", 0.1)
    video.suono("finale", t_domanda)
    inizio = video.tempo
    while video.tempo - inizio < durata:
        t = video.tempo - inizio
        i = min(int(t // per_scena), len(scene) - 1)
        fondale = fondali[i]
        locale = t - i * per_scena
        base_t = locale
        livelli = []
        if t < 2.2:
            p = ease_back(t / 0.4)
            ts = scala(titolo, 0.7 + 0.3 * p)
            livelli.append((opacita(ts, ease_out(t / 0.25) * (1 - ease_out((t - 1.8) / 0.4))),
                            ((L - ts.width) / 2, 330)))
        if pill is not None:
            livelli.append((pill, (X_MIN, 250 if t >= 2.2 else 470)))
        if didascalie[i] is not None and t < t_domanda:
            pd = ease_out((locale - 0.3) / 0.3) * (1 - ease_out((locale - per_scena + 0.35) / 0.3))
            if pd > 0:
                livelli.append((opacita(didascalie[i], pd), (X_MIN + 30 * (1 - pd), 1360)))
        if credito is not None:
            livelli.append((credito, ((X_MIN + X_MAX) / 2 - credito.width / 2, Y_MAX + 6)))
        if t >= t_domanda:
            pd = ease_back((t - t_domanda) / 0.35)
            ds = scala(domanda, 0.7 + 0.3 * pd)
            livelli.append((opacita(ds, ease_out((t - t_domanda) / 0.2)), ((X_MIN + X_MAX) / 2 - ds.width / 2,
                                                                          900 - ds.height / 2)))
        # dissolvenza tra una scena e l'altra
        if i + 1 < len(scene) and locale > per_scena - 0.35:
            a = fondale(base_t)
            b = fondali[i + 1](0)
            mix = Image.blend(a, b, ease_out((locale - per_scena + 0.35) / 0.35))
            video.fotogramma(livelli, fondale=lambda _t, m=mix: m)
        else:
            video.fotogramma(livelli, fondale=lambda _t, f=fondale, bt=base_t: f(bt))
    for f in fondali[1:]:
        f.chiudi()
    return video.chiudi()
