"""Musica originale in stile synthwave anni '80 (il mood di Vice City), generata da zero.

Niente brani di terzi: niente blocchi di Content ID, niente diritti da pagare. Ogni video ha la
sua variante: tonalità, giro di accordi, tempo e disegno dell'arpeggio cambiano col seme.
"""

import numpy as np
from scipy import signal

SR = 44100
NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
# giri di accordi classici del genere (minore, VI, III, VII)
PROGRESSIONI = [
    [("A", "m"), ("F", ""), ("C", ""), ("G", "")],
    [("F", "m"), ("C#", ""), ("G#", ""), ("D#", "")],
    [("E", "m"), ("C", ""), ("G", ""), ("D", "")],
    [("D", "m"), ("A#", ""), ("F", ""), ("C", "")],
    [("C", "m"), ("G#", ""), ("D#", ""), ("A#", "")],
    [("B", "m"), ("G", ""), ("D", ""), ("A", "")],
    [("G", "m"), ("D#", ""), ("A#", ""), ("F", "")],
]
ARPEGGI = [
    [0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 2, 1, 0, 1, 2, 3],
    [0, 2, 1, 3, 0, 2, 1, 3, 0, 2, 1, 3, 0, 2, 3, 1],
    [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 3, 2, 1, 0],
]


def _midi(nome, ottava):
    return 12 * (ottava + 1) + NOTE[nome]


def _hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def _dente(f, n, fase=0.0):
    t = np.arange(n) / SR
    return 2.0 * ((t * f + fase) % 1.0) - 1.0


def _filtro(x, taglio, tipo="low", ordine=2):
    if isinstance(taglio, (list, tuple)):
        wn = [min(c, SR * 0.45) / (SR / 2) for c in taglio]
    else:
        wn = min(taglio, SR * 0.45) / (SR / 2)
    b, a = signal.butter(ordine, wn, tipo)
    return signal.lfilter(b, a, x)


def _inviluppo(n, attacco, rilascio):
    env = np.ones(n)
    a, r = min(n, int(attacco * SR)), min(n, int(rilascio * SR))
    if a:
        env[:a] = np.linspace(0, 1, a)
    if r:
        env[-r:] *= np.linspace(1, 0, r)
    return env


def _cassa():
    t = np.arange(int(0.42 * SR)) / SR
    frequenza = 46 + 120 * np.exp(-t * 32)
    corpo = np.sin(2 * np.pi * np.cumsum(frequenza) / SR) * np.exp(-t * 8)
    click = np.exp(-t * 400) * 0.4
    return corpo + click


def _rullante(rng):
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    rumore = _filtro(rng.normal(0, 1, n), (1400, 7000), "band") * np.exp(-t * 18)
    tono = np.sin(2 * np.pi * 185 * t) * np.exp(-t * 28)
    return 0.8 * rumore / (np.max(np.abs(rumore)) or 1) + 0.45 * tono


def _charleston(rng):
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    rumore = _filtro(rng.normal(0, 1, n), 7500, "high") * np.exp(-t * 85)
    return rumore / (np.max(np.abs(rumore)) or 1)


def _riverbero(x, durata, umido, rng):
    n = int(durata * SR)
    t = np.arange(n) / SR
    risposta = _filtro(rng.normal(0, 1, n) * np.exp(-t * 3.6), 5500)
    risposta /= np.sqrt(np.sum(risposta ** 2)) or 1
    bagnato = signal.fftconvolve(x, risposta)[: len(x)]
    return x * (1 - umido) + bagnato * umido * 1.6


def synthwave(durata, seme=0):
    """Un brano synthwave della durata richiesta (secondi), mono, valori tra -1 e 1."""
    rng = np.random.default_rng(seme)
    bpm = int(rng.choice([100, 104, 108, 112]))
    battito = 60.0 / bpm
    sedicesimo, battuta = battito / 4, battito * 4
    giro = PROGRESSIONI[seme % len(PROGRESSIONI)]
    arpeggio = ARPEGGI[(seme // len(PROGRESSIONI)) % len(ARPEGGI)]
    n_tot = int((durata + 2.5) * SR)
    tracce = {k: np.zeros(n_tot) for k in ("cassa", "rullante", "hat", "basso", "pad", "arp")}
    pompa = np.ones(n_tot)
    cassa, rullante, hat = _cassa(), _rullante(rng), _charleston(rng)

    def metti(traccia, suono, quando, volume=1.0):
        i = int(quando * SR)
        if i >= n_tot:
            return
        fine = min(n_tot, i + len(suono))
        tracce[traccia][i:fine] += suono[: fine - i] * volume

    for b in range(int(np.ceil((durata + 1.5) / battuta))):
        nome, qualita = giro[b % 4]
        terza = 3 if qualita == "m" else 4
        t0 = b * battuta
        for passo in range(16):
            t = t0 + passo * sedicesimo
            if passo % 4 == 0:
                metti("cassa", cassa, t)
                i = int(t * SR)
                m = max(0, min(n_tot - i, int(0.3 * SR)))
                pompa[i:i + m] = np.minimum(pompa[i:i + m], 1 - 0.65 * np.exp(-np.arange(m) / SR * 11))
            if passo in (4, 12):
                metti("rullante", rullante, t)
            if passo % 4 == 2:
                metti("hat", hat, t, 1.0)
            elif passo % 2 == 1:
                metti("hat", hat, t, 0.35)
        radice = _midi(nome, 1)
        for ottavo in range(8):  # basso "a ottave" tipico del genere
            n = int(battito / 2 * SR * 0.92)
            nota = _dente(_hz(radice + (12 if ottavo % 2 else 0)), n) * _inviluppo(n, 0.004, 0.05)
            metti("basso", nota, t0 + ottavo * battito / 2)
        n = int(battuta * SR)
        pad = np.zeros(n)
        voci = [_midi(nome, 3), _midi(nome, 3) + terza, _midi(nome, 3) + 7, _midi(nome, 4)]
        for m in voci:
            for scostamento in (-0.09, 0.0, 0.09):
                pad += _dente(_hz(m + scostamento), n, rng.random())
        metti("pad", pad * _inviluppo(n, 0.22, 0.35) / (len(voci) * 3), t0)
        note_arp = [_midi(nome, 4), _midi(nome, 4) + terza, _midi(nome, 4) + 7, _midi(nome, 5)]
        for passo in range(16):
            n = int(sedicesimo * SR * 0.9)
            t = np.arange(n) / SR
            f = _hz(note_arp[arpeggio[passo] % 4])
            onda = 0.5 * np.sign(np.sin(2 * np.pi * f * t)) + 0.5 * _dente(f, n)
            metti("arp", onda * np.exp(-t * 10), t0 + passo * sedicesimo)

    basso = _filtro(tracce["basso"], 420) * pompa
    pad = _riverbero(_filtro(tracce["pad"], 1900) * pompa, 2.2, 0.35, rng)
    arp = _filtro(tracce["arp"], 3400)
    ritardo = int(3 * sedicesimo * SR)  # eco "puntato", il classico degli anni '80
    eco = np.zeros_like(arp)
    eco[ritardo:] += arp[:-ritardo] * 0.38
    eco[2 * ritardo:] += arp[:-2 * ritardo] * 0.16
    arp = arp + eco
    rullante_r = _riverbero(tracce["rullante"], 1.3, 0.45, rng)
    totale = (0.95 * tracce["cassa"] + 0.42 * rullante_r + 0.10 * tracce["hat"] + 0.50 * basso
              + 0.30 * pad + 0.15 * arp)
    totale = totale[: int(durata * SR)]
    totale = np.tanh(totale * 1.15)
    entrata, uscita = int(0.25 * SR), int(min(1.2, durata / 4) * SR)
    totale[:entrata] *= np.linspace(0, 1, entrata)
    totale[-uscita:] *= np.linspace(1, 0, uscita)
    picco = np.max(np.abs(totale)) or 1.0
    return (totale / picco * 0.92).astype(np.float32)
