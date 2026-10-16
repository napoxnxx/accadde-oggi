"""Monta lo Short verticale 1080x1920: grafica con data e testo, filmato al centro, barra di avanzamento."""

import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .eventi import MESI

W, H = 1080, 1920
AMBRA = (242, 179, 61)
BIANCO = (245, 241, 235)
GRIGIO = (150, 144, 136)
SFONDO = (15, 13, 11)
DURATA_MAX = 45
MARGINE = 60
LARGH_VIDEO = 1000

CARTELLE_FONT = ["/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype/inter",
                 "/usr/share/fonts/truetype/dejavu"]
RISERVA = {"ExtraBold": "DejaVuSans-Bold.ttf", "Bold": "DejaVuSans-Bold.ttf",
           "SemiBold": "DejaVuSans-Bold.ttf", "Medium": "DejaVuSans.ttf"}


def font(peso, dimensione):
    for cartella in CARTELLE_FONT:
        for nome in (f"Inter-{peso}.otf", f"Inter-{peso}.ttf", RISERVA[peso]):
            p = Path(cartella) / nome
            if p.exists():
                return ImageFont.truetype(str(p), dimensione)
    return ImageFont.load_default(dimensione)


def analizza(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json",
                          "-show_streams", "-show_format", str(video)],
                         capture_output=True, text=True, check=True).stdout
    info = json.loads(out)
    durata = float(info["format"].get("duration", 0))
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    larghezza, altezza = int(v["width"]), int(v["height"])
    sar = v.get("sample_aspect_ratio", "1:1")
    if sar and sar not in ("0:1", "N/A"):
        a, b = (int(x) for x in sar.split(":"))
        larghezza = larghezza * a / b if b else larghezza
    audio = any(s["codec_type"] == "audio" for s in info["streams"])
    return durata, larghezza / altezza, audio


def scegli_segmento(durata):
    clip = min(DURATA_MAX, durata)
    if durata <= clip + 5:
        return 0.0, clip
    inizio = min(durata * 0.15, durata - clip)  # salta countdown e titoli di testa
    return round(inizio, 2), clip


def _spaziato(draw, xy, testo, f, colore, spazio):
    x, y = xy
    for c in testo:
        draw.text((x, y), c, font=f, fill=colore)
        x += draw.textlength(c, font=f) + spazio
    return x


def _larghezza_spaziata(draw, testo, f, spazio):
    return sum(draw.textlength(c, font=f) for c in testo) + spazio * (len(testo) - 1)


def _testo_a_capo(draw, testo, f, larghezza, max_righe):
    righe = []
    for parola in testo.split():
        prova = (righe[-1] + " " + parola) if righe else parola
        if righe and draw.textlength(prova, font=f) <= larghezza:
            righe[-1] = prova
        else:
            righe.append(parola)
    if len(righe) > max_righe:
        righe = righe[:max_righe]
        while draw.textlength(righe[-1] + "…", font=f) > larghezza:
            righe[-1] = righe[-1].rsplit(" ", 1)[0]
        righe[-1] = righe[-1].rstrip(",;:") + "…"
    return righe


def disegna_grafica(evento, data, anni_fa, crediti, rapporto, destinazione,
                    etichetta="ACCADDE OGGI"):
    """Sfondo con buchi trasparenti dove passano il video e la barra di avanzamento."""
    altezza_video = int(min(680, max(500, LARGH_VIDEO / rapporto)))
    x_video, y_video = (W - LARGH_VIDEO) // 2, 600

    img = Image.new("RGBA", (W, H), SFONDO + (255,))
    # vignettatura calda + grana da pellicola
    alone = Image.new("L", (W, H), 0)
    ImageDraw.Draw(alone).ellipse((-300, -200, W + 300, H + 100), fill=60)
    alone = alone.filter(ImageFilter.GaussianBlur(220))
    img.paste(Image.new("RGBA", (W, H), (60, 40, 18, 255)), mask=alone)
    grana = Image.effect_noise((W, H), 28).convert("RGBA")
    grana.putalpha(14)
    img = Image.alpha_composite(img, grana)
    d = ImageDraw.Draw(img)

    # intestazione
    f_etichetta = font("Bold", 38)
    larg = _larghezza_spaziata(d, etichetta, f_etichetta, 9)
    x0 = (W - larg) / 2
    d.line((x0 - 90, 145, x0 - 25, 145), fill=AMBRA, width=3)
    d.line((x0 + larg + 25, 145, x0 + larg + 90, 145), fill=AMBRA, width=3)
    _spaziato(d, (x0, 122), etichetta, f_etichetta, AMBRA, 9)

    f_data = font("ExtraBold", 76)
    data_txt = f"{data.day} {MESI[data.month - 1].upper()}"
    d.text((W / 2, 230), data_txt, font=f_data, fill=BIANCO, anchor="mm")

    f_anno = font("ExtraBold", 220)
    d.text((W / 2, 385), str(evento["anno"]), font=f_anno, fill=AMBRA, anchor="mm")

    f_pillola = font("SemiBold", 40)
    pillola = f"{anni_fa} anni fa" if anni_fa != 1 else "1 anno fa"
    lp = d.textlength(pillola, font=f_pillola)
    d.rounded_rectangle((W / 2 - lp / 2 - 34, 495, W / 2 + lp / 2 + 34, 555),
                        radius=30, outline=AMBRA, width=3)
    d.text((W / 2, 525), pillola, font=f_pillola, fill=BIANCO, anchor="mm")

    # cornice e buco per il video
    d.rounded_rectangle((x_video - 6, y_video - 6, x_video + LARGH_VIDEO + 6,
                         y_video + altezza_video + 6), radius=14, outline=(70, 60, 48), width=3)
    d.rectangle((x_video, y_video, x_video + LARGH_VIDEO - 1, y_video + altezza_video - 1),
                fill=(0, 0, 0, 0))

    # testo dell'evento (lontano dai pulsanti di YouTube sulla destra)
    f_testo = font("SemiBold", 46)
    y_testo = y_video + altezza_video + 48
    righe_max = max(2, (1600 - y_testo) // 60)
    for i, riga in enumerate(_testo_a_capo(d, evento["testo"], f_testo, 880, righe_max)):
        d.text((MARGINE, y_testo + i * 60), riga, font=f_testo, fill=BIANCO)

    # binario e buco della barra di avanzamento
    y_barra = 1625
    d.rectangle((MARGINE, y_barra, W - MARGINE - 1, y_barra + 7), fill=(0, 0, 0, 0))

    f_crediti = font("Medium", 27)
    for i, riga in enumerate(crediti):
        d.text((MARGINE, 1655 + i * 38), riga, font=f_crediti, fill=GRIGIO)

    img.save(destinazione)
    return x_video, y_video, altezza_video, y_barra


def monta(video, evento, data, anni_fa, crediti, uscita, cartella_lavoro,
          etichetta="ACCADDE OGGI"):
    durata, rapporto, ha_audio = analizza(video)
    if durata < 8:
        raise ValueError(f"Filmato troppo corto ({durata:.1f}s)")
    inizio, clip = scegli_segmento(durata)
    grafica = Path(cartella_lavoro) / "grafica.png"
    xv, yv, hv, yb = disegna_grafica(evento, data, anni_fa, crediti, rapporto, grafica,
                                     etichetta)
    lb = W - 2 * MARGINE

    comandi = ["ffmpeg", "-y", "-loglevel", "error",
               "-loop", "1", "-framerate", "30", "-t", f"{clip}", "-i", str(grafica),
               "-ss", f"{inizio}", "-t", f"{clip}", "-i", str(video)]
    if not ha_audio:
        comandi += ["-f", "lavfi", "-t", f"{clip}", "-i", "anullsrc=r=48000:cl=stereo"]
    fine_fade = max(0.0, clip - 0.6)
    filtri = (
        f"color=c=0x2b2722:s={W}x{H}:r=30:d={clip}[base];"
        f"[1:v]scale={LARGH_VIDEO}:{hv}:force_original_aspect_ratio=decrease,"
        f"pad={LARGH_VIDEO}:{hv}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=30,"
        f"setpts=PTS-STARTPTS[vid];"
        f"color=c=0x{''.join(f'{c:02X}' for c in AMBRA)}:s={lb}x8:r=30:d={clip}[barra];"
        f"[base][vid]overlay={xv}:{yv}:shortest=1[a];"
        f"[a][barra]overlay=x='{MARGINE}-{lb}+{lb}*t/{clip}':y={yb}[b];"
        f"[b][0:v]overlay=0:0,fade=t=in:st=0:d=0.4,fade=t=out:st={fine_fade}:d=0.6,"
        f"format=yuv420p[vout];"
    )
    sorgente_audio = "[1:a]" if ha_audio else "[2:a]"
    filtri += (f"{sorgente_audio}asetpts=PTS-STARTPTS,aresample=48000,"
               f"loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:d=0.4,"
               f"afade=t=out:st={fine_fade}:d=0.6[aout]")
    comandi += ["-filter_complex", filtri, "-map", "[vout]", "-map", "[aout]",
                "-t", f"{clip}", "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-maxrate", "6M", "-bufsize", "12M",
                "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart",
                str(uscita)]
    subprocess.run(comandi, check=True)
    return {"inizio": inizio, "durata": clip}
