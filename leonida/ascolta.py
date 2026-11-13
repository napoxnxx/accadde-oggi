"""Solo per le prove: trascrive il parlato dei video, per controllare che la voce si capisca."""

import subprocess
import sys

import numpy as np
from faster_whisper import WhisperModel

modello = WhisperModel("small", device="cpu", compute_type="int8")
for file in sys.argv[1:]:
    grezzo = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", file, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                            capture_output=True, check=True).stdout
    audio = np.frombuffer(grezzo, dtype=np.int16).astype(np.float32) / 32768
    pezzi, _ = modello.transcribe(audio, language="it")
    print(f"TRASCRIZIONE {file}: " + " ".join(p.text.strip() for p in pezzi))
