"""Il parlato: una voce legge titolo e frasi delle notizie e delle curiosità.

Due motori, entrambi gratuiti:
1. le voci neurali di Microsoft Edge (pacchetto edge-tts): molto naturali, ma è un accesso non
   ufficiale e potrebbe smettere di funzionare;
2. Piper, voce open source che gira qui dentro: di riserva, se la prima non risponde.
Se non va nessuno dei due, il video esce come prima, con la sola musica.
Tutto il video usa sempre lo stesso motore, per non cambiare voce a metà.
"""

import os
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

RADICE = Path(__file__).resolve().parent.parent
VOCI_EDGE = ["it-IT-IsabellaMultilingualNeural", "it-IT-IsabellaNeural", "it-IT-ElsaNeural"]   # voci femminili
VELOCITA_EDGE = "+8%"
VOCE_PIPER = "it_IT-paola-medium"
CARTELLA_PIPER = RADICE / "media_rockstar" / "voci"   # dentro la cache, così il modello si scarica una volta sola

_NUMERI_ROMANI = {"VI": "sei", "V": "cinque", "IV": "quattro", "III": "tre", "II": "due"}
_SOSTITUZIONI = [
    (r"\bGTA\s*(VI|V|IV|III|II)\b", lambda m: "Gi Ti A " + _NUMERI_ROMANI[m.group(1)]),
    (r"\bGTA\b", "Gi Ti A"),
    (r"\bPS5 Pro\b", "PlayStation 5 Pro"), (r"\bPS(\d)\b", r"PlayStation \1"), (r"\bPSP\b", "Pi Esse Pi"),
    (r"\bXbox Series X\s*[|/e]\s*S\b", "Xbox Series"), (r"\bfps\b", "fotogrammi al secondo"),
    (r"(\d)\s*GB\b", r"\1 giga"), (r"(\d)\s*TB\b", r"\1 tera"), (r"\bPC\b", "Pi Ci"),
    (r"\$\s*(\d+)[.,](\d\d)\b", r"\1 dollari e \2"), (r"(\d+)[.,](\d\d)\s*\$", r"\1 dollari e \2"),
    (r"\$\s*(\d+)", r"\1 dollari"), (r"(\d+)\s*\$", r"\1 dollari"),
    (r"(\d+)[.,](\d\d)\s*€", r"\1 euro e \2"), (r"(\d+)\s*€", r"\1 euro"), (r"€\s*(\d+)", r"\1 euro"),
    (r"(\d)\.(\d{3})\b", r"\1\2"),            # 30.000 -> 30000, così lo legge come un numero solo
    (r"\b1°", "primo"), (r"(\d)°", r"\1"), (r"\s-\s*(\d)", r" meno \1"), (r"&", " e "), (r"[|/]", ", "),
    (r"\bCJ\b", "Si Gei"), (r"\bIWGB\b", "I W G B"), (r"\banni '(\d\d)", r"anni \1"),
]


def per_voce(testo):
    """Il testo come va letto: sigle sciolte, niente emoji né simboli."""
    testo = re.sub(r"[\U0001F000-\U0001FAFF☀-➿️‍]", " ", testo)
    for schema, nuovo in _SOSTITUZIONI:
        testo = re.sub(schema, nuovo, testo)
    testo = re.sub(r"[\"“”«»*_#]", "", testo)
    testo = re.sub(r"\s+", " ", testo).strip()
    return testo if not testo or testo[-1] in ".!?" else testo + "."


def _carica(percorso_audio, sr):
    """Qualsiasi file audio -> campioni mono a sr, senza i silenzi all'inizio e alla fine."""
    with tempfile.TemporaryDirectory() as cartella:
        wav = Path(cartella) / "v.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(percorso_audio), "-ac", "1", "-ar", str(sr),
                        "-c:a", "pcm_s16le", str(wav)], check=True, timeout=60)
        with wave.open(str(wav), "rb") as w:
            campioni = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
    forti = np.flatnonzero(np.abs(campioni) > 0.012)
    if forti.size < sr * 0.2:
        raise RuntimeError("audio vuoto")
    campioni = campioni[max(0, forti[0] - int(0.03 * sr)): forti[-1] + int(0.08 * sr)]
    return campioni / (np.max(np.abs(campioni)) or 1) * 0.95


def _edge(testo, uscita, voce):
    subprocess.run([sys.executable, "-m", "edge_tts", "--voice", voce, f"--rate={VELOCITA_EDGE}", "--text", testo,
                    "--write-media", str(uscita)], check=True, capture_output=True, timeout=60)


def _piper(testo, uscita):
    for inglese, come_si_dice in (("Jason", "Géison"), ("Duval", "Duvàl"), ("Rockstar", "Rocstar"), ("Vice City", "Vais Siti")):
        testo = testo.replace(inglese, come_si_dice)   # Piper legge all'italiana: i nomi inglesi vanno scritti come si dicono
    CARTELLA_PIPER.mkdir(parents=True, exist_ok=True)
    if not (CARTELLA_PIPER / f"{VOCE_PIPER}.onnx").exists():
        subprocess.run([sys.executable, "-m", "piper.download_voices", VOCE_PIPER, "--data-dir", str(CARTELLA_PIPER)],
                       capture_output=True, timeout=300)
    base = [sys.executable, "-m", "piper", "-m", VOCE_PIPER, "--data-dir", str(CARTELLA_PIPER), "-f", str(uscita)]
    for comando in (base, base + ["--download-dir", str(CARTELLA_PIPER)]):
        esito = subprocess.run(comando, input=testo, text=True, capture_output=True, timeout=300)
        if esito.returncode == 0 and Path(uscita).exists():
            return
    raise RuntimeError(f"piper: {esito.stderr[-200:]}")


def parla(testi, sr):
    """Legge ogni testo. Restituisce (campioni per ogni testo, nome del motore) oppure (None, motivo)."""
    if os.environ.get("VOCE", "1") == "0":
        return None, "voce spenta"
    testi = [per_voce(t) for t in testi]
    motori = [(v, lambda t, u, v=v: _edge(t, u, v), ".mp3") for v in VOCI_EDGE] + [(f"piper {VOCE_PIPER}", _piper, ".wav")]
    if os.environ.get("VOCE") == "piper":   # per provare la voce di riserva
        motori = motori[-1:]
    errori = []
    for nome, motore, estensione in motori:
        try:
            pezzi = []
            with tempfile.TemporaryDirectory() as cartella:
                for i, testo in enumerate(testi):
                    file = Path(cartella) / f"{i}{estensione}"
                    motore(testo, file)
                    pezzi.append(_carica(file, sr))
            return pezzi, nome
        except Exception as errore:  # noqa: BLE001 — qualsiasi problema: si prova il motore dopo
            dettaglio = getattr(errore, "stderr", b"") or b""
            errori.append(f"{nome}: {errore!r} {dettaglio[-160:] if isinstance(dettaglio, bytes) else dettaglio[-160:]}"[:260])
    return None, "; ".join(errori)
