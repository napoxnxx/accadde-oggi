"""Solo per le prove: trascrive il parlato dei video, per controllare che la voce si capisca."""

import sys

from faster_whisper import WhisperModel

modello = WhisperModel("small", device="cpu", compute_type="int8")
for file in sys.argv[1:]:
    pezzi, _ = modello.transcribe(file, language="it")
    print(f"TRASCRIZIONE {file}: " + " ".join(p.text.strip() for p in pezzi))
