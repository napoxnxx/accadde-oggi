"""Il formato parlato (notizie e curiosità), in stile "vetro liquido".

Montaggio veloce: un'immagine ufficiale nuova ogni 2-3 secondi, con stacco netto, colpo di zoom
e lampo. Il testo sta in un pannello di vetro smerigliato (sfoca davvero quello che ha dietro) e
si accende parola per parola insieme alla voce.
"""

import random
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import grafica as g
from . import voce as voce_

L, A, FPS, SR = g.L, g.A, g.FPS, g.SR
X0, X1 = g.X_MIN, g.X_MAX
LARGO = X1 - X0
STACCO_MAX = 2.7        # secondi: oltre, si cambia immagine anche a metà frase
MARGINE = 46            # spazio tra il bordo del vetro e il testo


# ---------------------------------------------------------------- sfondo: stacchi veloci

class Ripresa:
    """Una foto ufficiale che riempie lo schermo e si muove: zoom e panoramica, sempre in moto."""

    def __init__(self, percorso, seme):
        rnd = random.Random(seme)
        img = Image.open(percorso).convert("RGB") if percorso else g.tramonto(rnd.randrange(10 ** 6))
        scala = max(L / img.width, A / img.height) * 1.22
        self.img = img.resize((max(L + 2, int(img.width * scala)), max(A + 2, int(img.height * scala))), Image.BILINEAR)
        self.verso = rnd.choice([-1, 1])
        self.avanti = rnd.random() < 0.65          # zoom in avanti o indietro
        self.y = rnd.uniform(0.25, 0.6)            # i soggetti stanno di solito un po' sopra il centro

    def quadro(self, p, colpo):
        """p: 0-1 lungo la ripresa; colpo: 0-1, il colpo di zoom subito dopo lo stacco."""
        z = (1.0 - 0.10 * p) if self.avanti else (0.90 + 0.10 * p)
        z *= 1.0 - 0.07 * (1 - colpo)              # parte più stretta e si apre di scatto
        h = min(self.img.height, int(A * 1.22 * z))
        w = int(h * L / A)
        if w > self.img.width:
            w, h = self.img.width, int(self.img.width * A / L)
        libero_x = self.img.width - w
        cx = 0.5 + self.verso * (p - 0.5) * 0.8    # panoramica laterale: le foto sono orizzontali
        x = int(min(max(cx * libero_x, 0), libero_x))
        y = int((self.img.height - h) * self.y)
        return self.img.crop((x, y, x + w, y + h)).resize((L, A), Image.BILINEAR)


@lru_cache(maxsize=1)
def _ombre():
    """Scurisce in alto (logo) e in basso (testi e pulsanti), lasciando viva la foto al centro."""
    y = np.linspace(0, 1, A)
    alfa = 0.16 + 0.42 * np.clip((0.16 - y) / 0.16, 0, 1) ** 1.5 + 0.62 * np.clip((y - 0.45) / 0.55, 0, 1) ** 1.3
    img = np.zeros((A, L, 4), np.uint8)
    img[..., :3] = g.NERO
    img[..., 3] = (np.clip(alfa, 0, 0.9) * 255).astype(np.uint8)[:, None]
    return Image.fromarray(img, "RGBA")


# ---------------------------------------------------------------- vetro

@lru_cache(maxsize=64)
def _sagoma(larg, alt, raggio):
    k = 3
    m = Image.new("L", (larg * k, alt * k), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, larg * k - 1, alt * k - 1), radius=raggio * k, fill=255)
    return m.resize((larg, alt), Image.LANCZOS)


@lru_cache(maxsize=64)
def _finitura(larg, alt, raggio):
    """Quello che fa sembrare vetro il pannello: velo chiaro, riflesso in alto, bordo luminoso."""
    sagoma = _sagoma(larg, alt, raggio)
    y = np.linspace(0, 1, alt)[:, None]
    x = np.linspace(0, 1, larg)[None, :]
    velo = 0.10 + 0.16 * np.clip(1 - y / 0.42, 0, 1) ** 2 + 0.05 * (1 - x)       # riflesso dall'alto a sinistra
    strato = np.zeros((alt, larg, 4), np.uint8)
    strato[..., :3] = 255
    strato[..., 3] = (np.clip(velo, 0, 1) * 255 * (np.asarray(sagoma) / 255)).astype(np.uint8)
    img = Image.fromarray(strato, "RGBA")
    k = 3
    bordo = Image.new("L", (larg * k, alt * k), 0)
    ImageDraw.Draw(bordo).rounded_rectangle((k, k, larg * k - 1 - k, alt * k - 1 - k), radius=raggio * k, outline=255, width=2 * k + 1)
    bordo = bordo.resize((larg, alt), Image.LANCZOS)
    forza = 0.75 - 0.5 * np.clip(y * 1.2, 0, 1) + 0.25 * np.clip((y - 0.8) / 0.2, 0, 1)   # più luce in alto, un filo in basso
    luce = Image.new("RGBA", (larg, alt), (255, 255, 255, 0))
    luce.putalpha(Image.fromarray((np.asarray(bordo) * np.broadcast_to(forza, (alt, larg))).astype(np.uint8), "L"))
    img.alpha_composite(luce)
    return img


@lru_cache(maxsize=64)
def _ombra(larg, alt, raggio):
    m = 60
    img = Image.new("L", (larg + 2 * m, alt + 2 * m), 0)
    ImageDraw.Draw(img).rounded_rectangle((m, m + 14, m + larg, m + alt + 14), radius=raggio, fill=120)
    img = img.filter(ImageFilter.GaussianBlur(26))
    ombra = Image.new("RGBA", img.size, (*g.NERO, 0))
    ombra.putalpha(img)
    return ombra, m


def vetro(quadro, x, y, larg, alt, raggio=44, forza=1.0, tinta=None):
    """Disegna sul quadro un pannello di vetro smerigliato: sfoca davvero quello che c'è dietro."""
    x, y, larg, alt = int(x), int(y), int(larg), int(alt)
    if forza <= 0.01 or larg < 8 or alt < 8:
        return
    raggio = min(raggio, alt // 2, larg // 2)
    x = min(max(x, 0), L - larg)
    y = min(max(y, 0), A - alt)
    ombra, m = _ombra(larg, alt, raggio)
    sx, sy = max(0, m - x), max(0, m - y)      # l'ombra sporge dal pannello: si taglia ai bordi dello schermo
    pezzo = ombra.crop((sx, sy, min(ombra.width, L - x + m), min(ombra.height, A - y + m)))
    quadro.alpha_composite(g.opacita(pezzo, forza), (x - m + sx, y - m + sy))
    dietro = quadro.crop((x, y, x + larg, y + alt)).convert("RGB")
    piccolo = dietro.resize((max(2, larg // 6), max(2, alt // 6)), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5))
    sfocato = piccolo.resize((larg, alt), Image.BICUBIC)
    sfocato = Image.blend(sfocato, Image.new("RGB", (larg, alt), tinta or (26, 12, 44)), 0.34 if tinta is None else 0.5)
    sfocato = sfocato.convert("RGBA")
    sfocato.alpha_composite(_finitura(larg, alt, raggio))
    sagoma = _sagoma(larg, alt, raggio)
    if forza < 0.999:
        sagoma = sagoma.point(lambda v: int(v * forza))
    quadro.paste(sfocato, (x, y), sagoma)


# ---------------------------------------------------------------- testo che si accende con la voce

class Didascalia:
    """Una frase impaginata: ogni parola ha la sua posizione e il momento in cui viene detta."""

    def __init__(self, testo, stile="forte", dim_max=78, dim_min=46, max_righe=4, maiuscolo=False, largo=LARGO - 2 * MARGINE):
        testo = testo.upper() if maiuscolo else testo
        stile = g.stile_per(testo, stile)
        dim = dim_max
        while dim > dim_min and len(g.righe_a_capo(testo, stile, dim, largo)) > max_righe:
            dim -= 3
        self.righe = g.righe_a_capo(testo, stile, dim, largo)
        f = g.carattere(stile, dim)
        passo = int(dim * 1.14)
        self.larg, self.alt = int(largo), passo * len(self.righe) + int(dim * 0.22)
        strati = {n: Image.new("RGBA", (self.larg + 12, self.alt + 12), (0, 0, 0, 0)) for n in ("spento", "detto")}
        maschera = Image.new("L", (self.larg + 12, self.alt + 12), 0)
        self.parole = []   # (riquadro, peso)
        spazio = f.getlength(" ")
        for i, riga in enumerate(self.righe):
            x = (self.larg - f.getlength(riga)) / 2     # righe centrate
            for parola in riga.split():
                lw = f.getlength(parola)
                ImageDraw.Draw(strati["spento"]).text((x, i * passo), parola, font=f, fill=(255, 255, 255, 105))
                d = ImageDraw.Draw(strati["detto"])
                d.text((x + 2, i * passo + 4), parola, font=f, fill=(10, 4, 20, 150))
                d.text((x, i * passo), parola, font=f, fill=(255, 255, 255, 255))
                ImageDraw.Draw(maschera).text((x, i * passo), parola, font=f, fill=255)
                pausa = 3 if parola[-1] in ".,:;!?" else 0
                self.parole.append(((int(x) - 4, i * passo - 2, int(x + lw) + 6, i * passo + passo + 2), len(parola) + 2 + pausa))
                x += lw + spazio
        acceso = g.sfumatura(self.larg + 12, self.alt + 12, (255, 214, 92), g.ARANCIO).convert("RGBA")   # giallo-arancio: la parola del momento
        acceso.putalpha(maschera)
        self.spento, self.detto, self.acceso = strati["spento"], strati["detto"], acceso
        totale = sum(p for _, p in self.parole) or 1
        self.inizi, somma = [], 0
        for _, peso in self.parole:
            self.inizi.append(somma / totale)
            somma += peso

    def immagine(self, p):
        """p: 0-1, a che punto della frase è la voce."""
        img = self.spento.copy()
        for i, (riquadro, _) in enumerate(self.parole):
            if p < self.inizi[i]:
                break
            fine = self.inizi[i + 1] if i + 1 < len(self.parole) else 1.01
            strato = self.acceso if p < fine and p < 1 else self.detto
            riquadro = (max(0, riquadro[0]), max(0, riquadro[1]), min(img.width, riquadro[2]), min(img.height, riquadro[3]))
            img.paste(strato.crop(riquadro), riquadro[:2])
        return img


def _pillola_testo(testo, dim=40):
    f = g.carattere("forte", dim)
    return int(f.getlength(testo)) + 64, int(dim * 1.7), f


# ---------------------------------------------------------------- il video

def video_parlato(notizia, uscita, media_scelti=(), seme=0):
    """Titolo, 2-3 frasi e domanda finale: letti dalla voce, con montaggio veloce di immagini ufficiali."""
    rnd = random.Random(seme)
    testo_domanda = notizia.get("domanda") or "TU COSA NE PENSI?"
    domanda_detta = testo_domanda[:1] + testo_domanda[1:].lower()
    testi = [notizia["titolo"], *notizia["frasi"], domanda_detta + " Scrivilo nei commenti."]
    pezzi, motore = voce_.parla(testi, SR)
    print(f"  Voce: {motore}")

    # --- tempi: ogni blocco (titolo, frasi, domanda) dura quanto la voce che lo legge
    blocchi, parlato, t = [], [], 0.25
    for i, testo in enumerate(testi):
        dura = pezzi[i].size / SR if pezzi else 0.9 + len(testo) / 15.0
        if pezzi:
            parlato.append((t + 0.05, pezzi[i]))
        pausa = 0.28 if i < len(testi) - 1 else 0.9
        blocchi.append({"inizio": t, "voce": dura, "fine": t + dura + pausa})
        t += dura + pausa
    durata = max(t, blocchi[-1]["inizio"] + 2.6)
    blocchi[-1]["fine"] = durata

    # --- stacchi: una ripresa nuova a ogni blocco, e anche a metà dei blocchi lunghi
    stacchi = []
    for b in blocchi:
        n = max(1, int(np.ceil((b["fine"] - b["inizio"]) / STACCO_MAX)))
        stacchi += [b["inizio"] + k * (b["fine"] - b["inizio"]) / n for k in range(n)]
    stacchi[0] = 0.0
    foto = [m["percorso"] for m in media_scelti if m.get("tipo") != "clip"]
    riprese, ultima = [], None
    for k in range(len(stacchi)):
        percorso = foto[k % len(foto)] if foto else None
        if percorso is None or percorso != ultima or len(foto) == 1:
            try:
                riprese.append(Ripresa(percorso, rnd.randrange(10 ** 6)))
            except OSError:
                riprese.append(Ripresa(None, rnd.randrange(10 ** 6)))
        ultima = percorso
    while len(riprese) < len(stacchi):
        riprese.append(riprese[len(riprese) % max(1, len(riprese))])
    fini = stacchi[1:] + [durata]

    # --- testi
    titolo = Didascalia(notizia["titolo"], "titolo", 104, 60, 4, maiuscolo=True)
    frasi = [Didascalia(f, "forte", 76, 48, 4) for f in notizia["frasi"]]
    domanda = Didascalia(testo_domanda, "titolo", 96, 56, 3, maiuscolo=True)
    invito = g.immagine_testo("SCRIVILO NEI COMMENTI", "forte", 50, g.ARANCIO)
    didascalie = [titolo, *frasi, domanda]
    nome_etichetta = notizia.get("etichetta", "NEWS GTA VI")
    larg_et, alt_et, f_et = _pillola_testo(nome_etichetta)
    fonti = g.riga_piccola("Fonti: " + ", ".join(notizia["fonti"]), 28)
    credito = g.riga_piccola("Immagini: Rockstar Games", 24) if foto else None
    barra_piena = g.sfumatura(10, LARGO, g.ROSA, g.ARANCIO).rotate(90, expand=True).convert("RGBA")

    class _Niente:
        def chiudi(self):
            pass

    video = g.Video(uscita, _Niente(), seme)
    video.parlato = parlato
    video.suono("pop")
    for s in stacchi[1:]:
        video.suono("fruscio", s - 0.05)
    video.suono("finale", blocchi[-1]["inizio"])
    ombre = _ombre()

    while video.tempo < durata:
        t = video.tempo
        k = max(i for i, s in enumerate(stacchi) if s <= t + 1e-6)
        dentro = t - stacchi[k]
        quadro = riprese[k].quadro(dentro / max(0.1, fini[k] - stacchi[k]), g.ease_out(dentro / 0.28)).convert("RGBA")
        quadro.alpha_composite(ombre)
        if dentro < 0.12 and k > 0:      # lampo sullo stacco
            lampo = Image.new("RGBA", (L, A), (255, 255, 255, int(95 * (1 - dentro / 0.12))))
            quadro.alpha_composite(lampo)
        livelli = []

        # etichetta in alto (pillola di vetro)
        entra = g.ease_out(t / 0.3)
        x_et = (X0 + X1 - larg_et) // 2
        vetro(quadro, x_et, 236 - 30 * (1 - entra), larg_et, alt_et, alt_et // 2, entra, tinta=(150, 24, 96))
        d = ImageDraw.Draw(quadro)
        if entra > 0.5:
            d.text((x_et + larg_et / 2, 236 + alt_et / 2 + 1), nome_etichetta, font=f_et, fill=(255, 255, 255, 255), anchor="mm")

        # il blocco di adesso: pannello di vetro con il testo che si accende
        i = max(j for j, b in enumerate(blocchi) if b["inizio"] <= t + 1e-6) if t >= blocchi[0]["inizio"] else 0
        b, dida = blocchi[i], didascalie[i]
        ultimo = i == len(blocchi) - 1
        nel_blocco = t - b["inizio"]
        entra = g.ease_back(nel_blocco / 0.26) if nel_blocco >= 0 else 0
        esce = 1.0 if ultimo else g.ease_out((b["fine"] - t) / 0.12)
        visibile_ = max(0.0, min(1.0, g.ease_out(nel_blocco / 0.16))) * esce
        alt_p = dida.alt + 2 * MARGINE + (invito.height + 8 if ultimo else 0)
        if i == 0:
            y_p = 760 - alt_p // 2          # il titolo sta al centro
        elif ultimo:
            y_p = 900 - alt_p // 2
        else:
            y_p = 1385 - alt_p              # le frasi in basso, sopra la zona dei pulsanti
        y_p += int(46 * (1 - min(1.0, entra)))
        if visibile_ > 0.02:
            vetro(quadro, X0, y_p, LARGO, alt_p, 48, visibile_, tinta=(120, 20, 90) if ultimo else None)
            p = min(1.0, max(0.0, nel_blocco - 0.05) / max(0.2, b["voce"]))
            if ultimo:
                p = min(1.0, p * 2.2)       # la domanda si accende subito, poi resta
            livelli.append((g.opacita(dida.immagine(p), visibile_), (X0 + MARGINE, y_p + MARGINE - 4)))
            if ultimo:
                battito = 1.0 + 0.04 * np.sin(nel_blocco * 7)
                inv = g.scala(invito, battito)
                livelli.append((g.opacita(inv, visibile_), ((X0 + X1) / 2 - inv.width / 2, y_p + alt_p - MARGINE - invito.height + 6)))

        # barra di avanzamento (vetro) e fonti
        vetro(quadro, X0, 1436, LARGO, 14, 7, 0.9)
        pieno = int((LARGO - 4) * min(1.0, t / durata))
        if pieno > 6:
            livelli.append((barra_piena.crop((0, 0, pieno, 10)), (X0 + 2, 1438)))
        livelli.append((fonti, ((X0 + X1) / 2 - fonti.width / 2, g.Y_MAX - 32)))
        if credito is not None:
            livelli.append((credito, ((X0 + X1) / 2 - credito.width / 2, g.Y_MAX + 6)))
        video.fotogramma(livelli, fondale=lambda _t, q=quadro: q)
    return video.chiudi()
