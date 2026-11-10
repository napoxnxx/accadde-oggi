"""UNTIL LEONIDA — Short su GTA VI automatici, verificati e programmati su YouTube.

Due uscite al giorno:
- 13:00 NOTIZIA: il fatto del giorno su GTA VI, confermato da almeno 3 siti di videogiochi;
  se non c'è niente di confermato, una chicca ufficiale (personaggi, luoghi, dettagli);
- 19:00 SERA: il conto alla rovescia fino all'uscita (19 novembre 2026); dopo, a giorni
  alterni, chicche ufficiali e montaggi di immagini di gioco ufficiali.

Uso:
    python -m leonida            un giro: prepara quello che manca
Variabili d'ambiente:
    PROVA=1                                        video di prova in una Release "prova"
    FORMATO=tutti|notizia|countdown|montaggio      (con PROVA) quali formati provare
"""

import datetime as dt
import json
import os
import random
import subprocess
import sys
import time
import traceback
from pathlib import Path
from zoneinfo import ZoneInfo

from . import feed, grafica, media, notizie, testi

RADICE = Path(__file__).resolve().parent.parent
STORICO = RADICE / "storico_leonida.json"
STATO = RADICE / "stato_leonida.json"
USCITA = RADICE / "output"
ROMA = ZoneInfo("Europe/Rome")

USCITA_GTA = dt.date(2026, 11, 19)
ORARI = {"notizia": dt.time(13, 0), "sera": dt.time(19, 0)}
GIORNI_DI_SCORTA = 3
VIDEO_DI_RISERVA = 2
FINESTRA_NOTIZIE = range(8, 12)
TENTATIVI_NOTIZIA = 2


def ora_di_uscita(giorno, slot):
    return dt.datetime.combine(giorno, ORARI[slot], tzinfo=ROMA)


def giorni_mancanti(giorno):
    return (USCITA_GTA - giorno).days


# ---------------------------------------------------------------- archivi

def _leggi(percorso, predefinito):
    if percorso.exists():
        try:
            return json.loads(percorso.read_text(encoding="utf-8"))
        except ValueError:
            print(f"Attenzione: {percorso.name} illeggibile, riparto da zero.")
    return predefinito


def _scrivi(percorso, contenuto):
    percorso.parent.mkdir(parents=True, exist_ok=True)
    percorso.write_text(json.dumps(contenuto, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def leggi_storico():
    s = _leggi(STORICO, {})
    for chiave, valore in (("video", []), ("riserva", []), ("media_usati", []), ("tentativi_notizia", {}),
                           ("chicche_usate", [])):
        s.setdefault(chiave, valore)
    return s


def aggiorna_stato(storico, problemi, oggi, elenco_media=None, prova=None):
    vecchio = _leggi(STATO, {})
    nuovo = {
        "scorta": [{"data": v["data"], "ora": ORARI[v["slot"]].strftime("%H:%M"), "formato": v["formato"],
                    "titolo": v["titolo"]} for v in sorted(storico["video"], key=lambda v: (v["data"], v["slot"]))
                   if v["data"] >= oggi.isoformat()],
        "riserva": len(storico["riserva"]),
        "media_ufficiali": ({k: len(v) for k, v in elenco_media.items() if not k.startswith("_")}
                            if elenco_media is not None else vecchio.get("media_ufficiali")),
        "problemi": (vecchio.get("problemi", []) + [f"{oggi}: {p}" for p in problemi])[-12:],
        "prova": prova or vecchio.get("prova"),
    }
    if {k: v for k, v in vecchio.items() if k != "aggiornato"} != nuovo:
        nuovo["aggiornato"] = dt.datetime.now(ROMA).strftime("%Y-%m-%d %H:%M")
        _scrivi(STATO, nuovo)


# ---------------------------------------------------------------- contenuti

def _media(elenco, storico, seme, quanti, tipi=("screenshot", "artwork"), senza_grafiche=False):
    scelti = media.scegli(elenco, seme, quanti, tipi, evita=storico["media_usati"][-30:], senza_grafiche=senza_grafiche)
    storico["media_usati"] = (storico["media_usati"] + [m["file"] for m in scelti])[-60:]
    return scelti


def contenuto_countdown(giorno, elenco, storico):
    g = giorni_mancanti(giorno)
    fatto = testi.FATTI[max(g, 0) % len(testi.FATTI)]
    domanda = testi.scegli(testi.DOMANDE, f"c{giorno}")
    tipi = ("clip",) if g % 3 == 0 and elenco.get("clip") else ("screenshot", "artwork")
    return {"formato": "countdown", "giorni": g, "fatto": fatto, "domanda": domanda,
            "media": _media(elenco, storico, f"c{giorno}", 1, tipi, senza_grafiche=True)}


def contenuto_montaggio(giorno, elenco, storico, con_contatore=True):
    g = giorni_mancanti(giorno)
    variante = f"m{giorno}{time.time() if not con_contatore else ''}"
    scelti = _media(elenco, storico, variante, 4)
    for m in scelti:
        m["didascalia"] = media.didascalia_mostrabile(m.get("didascalia", ""))
    return {"formato": "montaggio", "giorni": g if con_contatore and g > 0 else None,
            "domanda": testi.scegli(testi.DOMANDE_MONTAGGIO, variante), "media": scelti}


def contenuto_chicca(giorno, elenco, storico):
    """La chicca ufficiale usata meno di recente (e ancora valida), con l'immagine giusta."""
    valide = [c for c in testi.CHICCHE if c.get("fino_al", "9999") >= giorno.isoformat()]
    usate = [u["id"] for u in storico["chicche_usate"]]
    def ultima_volta(c):
        return max((i for i, u in enumerate(usate) if u == c["id"]), default=-1)
    c = min(valide, key=lambda c: (ultima_volta(c), testi.CHICCHE.index(c)))
    storico["chicche_usate"] = (storico["chicche_usate"] + [{"id": c["id"], "data": giorno.isoformat()}])[-100:]
    seme = f"k{giorno}{c['id']}"
    scelti = media.scegli_per(elenco, c["media"], seme, 1, storico["media_usati"][-30:]) if c["media"] else []
    if not scelti and not c["media"]:
        scelti = _media(elenco, storico, seme, 1, senza_grafiche=True)
    elif not scelti:  # nessuna immagine del soggetto: meglio un luogo che il personaggio sbagliato
        scelti = media.scegli_per(elenco, ["VICE CITY", "LEONIDA"], seme, 1)
    else:
        storico["media_usati"] = (storico["media_usati"] + [m["file"] for m in scelti])[-60:]
    dati = {"titolo": c["titolo"], "frasi": c["frasi"], "domanda": c["domanda"], "etichetta": c["etichetta"],
            "fonti": testi.fonti_brevi(c)}
    return {"formato": "chicca", "chicca": c, "notizia": dati, "media": scelti}


def contenuto_notizia(oggi, elenco, storico):
    limite = (oggi - dt.timedelta(days=7)).isoformat()
    recenti = [v for v in storico["video"] if v.get("formato") == "notizia" and v["data"] >= limite]
    gia_usati = [link for v in recenti for link in v.get("link", [])]
    gia_usati += [v["chiave"] for v in recenti if v.get("chiave") and v["data"] >= (oggi - dt.timedelta(days=2)).isoformat()]
    n, motivo = notizie.notizia_del_giorno(gia_usati)
    if not n:
        return None, motivo
    n["domanda"] = (n.get("domanda") or "TU COSA NE PENSI?").upper()[:40]
    return {"formato": "notizia", "notizia": n, "media": _media(elenco, storico, f"n{oggi}{n['titolo']}", 1, senza_grafiche=True)}, None


# ---------------------------------------------------------------- video e pubblicazione

def monta(c, percorso, giorno, seme):
    if c["formato"] == "countdown":
        durata = grafica.video_countdown(c, percorso, c["media"], seme)
        titolo, descrizione = testi.countdown(c["giorni"], c["fatto"], c["domanda"])
    elif c["formato"] == "notizia":
        durata = grafica.video_notizia(c["notizia"], percorso, c["media"], seme)
        titolo, descrizione = testi.notizia(c["notizia"])
    elif c["formato"] == "chicca":
        durata = grafica.video_notizia(c["notizia"], percorso, c["media"], seme)
        titolo, descrizione = testi.chicca(c["chicca"], seme)
    else:
        contatore = f"- {c['giorni']} {'GIORNO' if c['giorni'] == 1 else 'GIORNI'}" if c.get("giorni") else None
        durata = grafica.video_montaggio({"contatore": contatore, "domanda": c["domanda"]}, percorso, c["media"], seme)
        titolo, descrizione = testi.montaggio(c["domanda"], f"{giorno}-{seme}", c.get("giorni"))
    print(f"Video montato: {percorso.name}, {durata:.1f} secondi — {titolo}")
    return titolo, descrizione


def carica_release(tag, file, titolo, note, prerelease=False):
    if not os.environ.get("GITHUB_ACTIONS"):
        print(f"(fuori da GitHub: la Release {tag} non viene creata)")
        return
    file_note = USCITA / f"note-{tag}.txt"
    file_note.write_text(note, encoding="utf-8")
    esiste = subprocess.run(["gh", "release", "view", tag], capture_output=True).returncode == 0
    comando = (["gh", "release", "upload", tag, str(file), "--clobber"] if esiste else
               ["gh", "release", "create", tag, str(file), "--title", titolo[:120], "--notes-file", str(file_note)]
               + (["--prerelease"] if prerelease else []))
    esito = subprocess.run(comando, capture_output=True, text=True)
    if esito.returncode != 0:
        raise RuntimeError(f"caricamento su GitHub non riuscito: {esito.stderr[-300:]}")


def produci(c, nome_file, tag, giorno, prerelease=False):
    USCITA.mkdir(exist_ok=True)
    percorso = USCITA / f"{nome_file}.mp4"
    seme = random.Random(nome_file).randrange(10 ** 6)
    titolo, descrizione = monta(c, percorso, giorno, seme)
    dettagli = ("Fonti: " + ", ".join(c["notizia"]["fonti"])) if c["formato"] == "notizia" else \
        ("Immagini: " + ", ".join(Path(m["file"]).name for m in c["media"]) if c["media"] else "Fondale disegnato")
    (USCITA / "ultimo-video.txt").write_text(f"{titolo}\n\n{descrizione}\n\n[{dettagli}]", encoding="utf-8")
    carica_release(tag, percorso, titolo, f"{titolo}\n\n{descrizione}\n\n{dettagli}", prerelease)
    voce = {"formato": c["formato"], "titolo": titolo, "descrizione": descrizione, "dettagli": dettagli,
            "tag": tag, "url": feed.url_release(tag, percorso.name), "dimensione": percorso.stat().st_size,
            "preparato": dt.datetime.now(ROMA).strftime("%Y-%m-%d %H:%M")}
    if c["formato"] == "notizia":
        voce["link"] = [a["link"] for a in c["notizia"]["articoli"]]
        voce["chiave"] = c["notizia"].get("chiave")
    return voce


def programma(giorno, slot, voce, storico):
    uscita = ora_di_uscita(giorno, slot)
    feed.aggiungi(RADICE / "feed_leonida.xml", voce["titolo"], voce["descrizione"], voce["url"], voce["tag"],
                  voce["dimensione"], uscita)
    storico["video"].append({**voce, "data": giorno.isoformat(), "slot": slot, "uscita": uscita.isoformat()})
    _scrivi(STORICO, storico)
    print(f"Programmato per il {giorno} alle {uscita:%H:%M}: {voce['titolo']}")


def usa_riserva(giorno, slot, storico):
    if not storico["riserva"]:
        return False
    print(f"Uso un video di riserva per il {giorno} alle {ORARI[slot]:%H:%M}.")
    programma(giorno, slot, storico["riserva"].pop(0), storico)
    return True


# ---------------------------------------------------------------- il giro

def notizia_di_oggi(oggi, adesso, elenco, storico, problemi):
    tentativi = storico["tentativi_notizia"]
    if tentativi.get("data") != oggi.isoformat():
        tentativi.clear()
        tentativi.update({"data": oggi.isoformat(), "n": 0})
    contenuto = None
    if tentativi["n"] < TENTATIVI_NOTIZIA:
        tentativi["n"] += 1
        print(f"\n=== Notizia del giorno (tentativo {tentativi['n']} di {TENTATIVI_NOTIZIA}) ===")
        try:
            contenuto, motivo = contenuto_notizia(oggi, elenco, storico)
            if not contenuto:
                print(f"Nessuna notizia pubblicabile: {motivo}")
                problemi.append(f"notizia non pubblicata: {motivo}"[:300])
        except notizie.IANonDisponibile as errore:
            problemi.append(f"notizia: {errore}"[:300])
    if contenuto is None and (tentativi["n"] >= TENTATIVI_NOTIZIA or adesso.hour >= 10):
        print("\n=== Al posto della notizia: una chicca ufficiale ===")
        contenuto = contenuto_chicca(oggi, elenco, storico)
    if contenuto is None:
        print("Riprovo la notizia al prossimo giro.")
        return
    voce = produci(contenuto, f"notizia-{oggi}", f"notizia-{oggi}", oggi)
    programma(oggi, "notizia", voce, storico)


def giro_completo():
    prova = os.environ.get("PROVA") == "1"
    adesso = dt.datetime.now(ROMA)
    oggi = adesso.date()
    if prova:
        return giro_di_prova(oggi, adesso)
    if not (RADICE / "via_libera_leonida.txt").exists():
        print("In attesa del via libera: nessun video viene programmato. "
              "Fai una prova da Actions e, se va bene, crea il file via_libera_leonida.txt.")
        return 0
    storico = leggi_storico()
    pronti = {(v["data"], v["slot"]) for v in storico["video"]}
    # se è presto, si prepara anche la sera di oggi (Zapier ha tutto il tempo di programmarla)
    primo = 0 if adesso.hour < 16 else 1
    giorni = [oggi + dt.timedelta(days=k) for k in range(primo, GIORNI_DI_SCORTA + 1)]
    sere_da_fare = [g for g in giorni if (g.isoformat(), "sera") not in pronti]
    serve_notizia = adesso.hour in FINESTRA_NOTIZIE and (oggi.isoformat(), "notizia") not in pronti
    riserva_mancante = VIDEO_DI_RISERVA - len(storico["riserva"])
    problemi = []
    if not sere_da_fare and not serve_notizia and riserva_mancante <= 0:
        print("Tutto pronto. Niente da fare.")
        aggiorna_stato(storico, problemi, oggi)
        return 0
    try:
        elenco = media.prepara()
    except Exception as errore:  # noqa: BLE001 — senza immagini ufficiali si usa il tramonto disegnato
        traceback.print_exc()
        elenco = {}
        problemi.append(f"immagini ufficiali non disponibili: {errore!r}"[:300])

    if serve_notizia:
        try:
            notizia_di_oggi(oggi, adesso, elenco, storico, problemi)
        except Exception as errore:  # noqa: BLE001
            traceback.print_exc()
            problemi.append(f"notizia di oggi: {errore!r}"[:300])
            if adesso.hour >= 10:
                usa_riserva(oggi, "notizia", storico)
        finally:
            _scrivi(STORICO, storico)

    for giorno in sere_da_fare:
        print(f"\n=== Sera del {giorno} ===")
        try:
            if giorni_mancanti(giorno) >= 0:
                c = contenuto_countdown(giorno, elenco, storico)
            elif giorno.toordinal() % 3 != 0:  # dopo l'uscita: 2 sere su 3 pillole, 1 su 3 montaggio di immagini
                c = contenuto_chicca(giorno, elenco, storico)
            else:
                c = contenuto_montaggio(giorno, elenco, storico)
            voce = produci(c, f"sera-{giorno}", f"sera-{giorno}", giorno)
            programma(giorno, "sera", voce, storico)
        except Exception as errore:  # noqa: BLE001
            traceback.print_exc()
            problemi.append(f"sera del {giorno}: {errore!r}"[:300])
            if giorno == oggi + dt.timedelta(days=1) and adesso.hour >= 12:
                usa_riserva(giorno, "sera", storico)
        finally:
            _scrivi(STORICO, storico)

    for k in range(max(0, riserva_mancante)):
        print("\n=== Video di riserva ===")
        try:
            c = contenuto_montaggio(oggi, elenco, storico, con_contatore=False)
            tag = f"riserva-{int(time.time())}-{k}"
            storico["riserva"].append(produci(c, tag, tag, oggi))
        except Exception as errore:  # noqa: BLE001
            traceback.print_exc()
            problemi.append(f"riserva: {errore!r}"[:300])
            break
        finally:
            _scrivi(STORICO, storico)

    aggiorna_stato(storico, problemi, oggi, elenco)
    return 0


def giro_di_prova(oggi, adesso):
    formato = (os.environ.get("FORMATO") or "tutti").strip().lower()
    formati = ["notizia", "countdown", "chicca", "montaggio"] if formato in ("", "tutti") else [formato]
    storico = leggi_storico()
    problemi, risultati = [], []
    tag = f"prova-{os.environ.get('RUN_ID') or int(time.time())}"
    try:
        elenco = media.prepara()
    except Exception as errore:  # noqa: BLE001
        traceback.print_exc()
        elenco = {}
        problemi.append(f"immagini ufficiali non disponibili: {errore!r}"[:300])
    domani = oggi + dt.timedelta(days=1)
    for f in formati:
        print(f"\n=== PROVA: {f} ===")
        try:
            motivo = None
            if f == "notizia":
                c, motivo = contenuto_notizia(oggi, elenco, storico)
            elif f == "countdown":
                c = contenuto_countdown(domani, elenco, storico)
            elif f == "chicca":
                c = contenuto_chicca(domani, elenco, storico)
            else:
                c = contenuto_montaggio(domani, elenco, storico)
            if c is None:
                raise RuntimeError(motivo or "nessun contenuto")
            voce = produci(c, f"{tag}-{f}", tag, domani, prerelease=True)
            risultati.append({"formato": f, "titolo": voce["titolo"], "video": voce["url"], "dettagli": voce["dettagli"]})
        except Exception as errore:  # noqa: BLE001
            traceback.print_exc()
            risultati.append({"formato": f, "errore": f"{errore!r}"[:300]})
    esito = {"quando": adesso.strftime("%Y-%m-%d %H:%M"), "release": tag, "video": risultati}
    print("\nESITO PROVA:", json.dumps(esito, ensure_ascii=False, indent=1))
    # la prova non tocca lo storico: chicche e immagini restano da usare nei video veri
    aggiorna_stato(leggi_storico(), problemi, oggi, elenco, esito)
    return 0


if __name__ == "__main__":
    sys.exit(giro_completo())
