"""Il "redattore": un'IA gratuita controlla che il filmato mostri DAVVERO l'evento.

Servizi supportati (basta la chiave nei Secrets di GitHub), provati in quest'ordine:
- CLAUDE_CODE_OAUTH_TOKEN → Claude con il tuo abbonamento Pro (consigliato)
- GEMINI_API_KEY          → Google Gemini (gratis, riserva)
- GROQ_API_KEY            → Groq (gratis, riserva)

Regola d'oro: nel dubbio si scarta. Se nessuna IA risponde, non si pubblica nulla.
"""

import json
import os
import re
import subprocess
import time

import requests

SERVIZI = [
    ("Gemini", "GEMINI_API_KEY",
     "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
     os.environ.get("MODELLO_GEMINI") or "gemini-2.5-flash"),
    ("Groq", "GROQ_API_KEY",
     "https://api.groq.com/openai/v1/chat/completions",
     os.environ.get("MODELLO_GROQ") or "llama-3.3-70b-versatile"),
]
CERTEZZA_MINIMA = 90
MAX_CHIAMATE = int(os.environ.get("MAX_CHIAMATE_IA") or 30)

ISTRUZIONI = """Sei il redattore di un canale YouTube di divulgazione storica. Il tuo unico compito è \
evitare errori e disinformazione. Ti do un evento storico (da Wikipedia) e la scheda d'archivio di un \
filmato d'epoca. Devi decidere se il filmato mostra DAVVERO quell'evento.

Rispondi "corrisponde": true SOLO se tutte queste condizioni sono vere:
1. Il filmato documenta proprio quell'evento specifico (stesso fatto, stesso luogo, stesso periodo), \
oppure il suo contesto immediato e diretto (es. il cinegiornale che ne dà la notizia in quei giorni).
2. Il filmato è interamente o quasi interamente dedicato a quell'evento. Se è un cinegiornale con \
più notizie, una raccolta, un documentario generico o un video su un tema simile ma diverso, rispondi false.
3. La data del filmato è compatibile con la data dell'evento. Un filmato girato anni dopo \
(anniversari, commemorazioni, discorsi successivi) NON corrisponde.
4. Il contenuto non è offensivo, razzista, di propaganda d'odio, né contiene violenza esplicita \
che renderebbe inopportuna la pubblicazione su YouTube.

Nel minimo dubbio rispondi false. È molto meglio scartare un filmato giusto che pubblicarne uno sbagliato.

Rispondi SOLO con un oggetto JSON, senza altro testo:
{"corrisponde": true/false, "certezza": 0-100, "motivo": "breve spiegazione in italiano"}"""


SCRIVI = """Sei il redattore di un canale YouTube italiano di storia che pubblica cinegiornali \
d'epoca di pubblico dominio. Ti do la scheda d'archivio di un cinegiornale: data di uscita, titolo \
originale e descrizione (in inglese). Scrivi in italiano:
- "titolo": titolo breve (massimo 55 caratteri), fedele, senza esagerazioni;
- "testo": 1 o 2 frasi (massimo 170 caratteri) che dicono cosa mostra il filmato.

REGOLE OBBLIGATORIE:
- Usa SOLO informazioni presenti nella scheda. Non aggiungere date, numeri, nomi, luoghi, cause \
o conseguenze che non sono scritti nella scheda, anche se li conosci.
- La data è quella di USCITA del cinegiornale: non scrivere che l'evento è avvenuto quel giorno.
- Se un dettaglio è incerto o ambiguo, omettilo.

Rispondi "pubblicabile": false se la scheda è troppo vaga per capire cosa mostra il filmato, se \
il contenuto è razzista, propaganda d'odio, mostra morti o violenza esplicita, o se hai dubbi.

Rispondi SOLO con JSON, senza altro testo:
{"pubblicabile": true/false, "motivo": "...", "titolo": "...", "testo": "..."}"""

CONTROLLA = """Sei un fact-checker severo. Ti do la scheda d'archivio originale di un \
cinegiornale e un titolo e un testo in italiano scritti a partire da essa. Verifica che OGNI \
affermazione sia direttamente supportata dalla scheda: traduzione fedele, nessun fatto aggiunto, \
nessuna esagerazione, nessuna data dell'evento inventata. Nel dubbio rispondi false.
Rispondi SOLO con JSON: {"corretto": true/false, "certezza": 0-100, "problemi": "..."}"""


class IANonDisponibile(Exception):
    pass


class Redattore:
    def __init__(self):
        self.servizi = [s for s in SERVIZI if os.environ.get(s[1])]
        self.claude = bool(os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"))
        self.chiamate = 0

    def disponibile(self):
        return (self.claude or bool(self.servizi)) and self.chiamate < MAX_CHIAMATE

    def _chiedi_a(self, nome, variabile, endpoint, modello, messaggi):
        errore = "nessuna risposta"
        for tentativo in range(3):
            try:
                r = requests.post(endpoint, timeout=90, headers={
                    "Authorization": f"Bearer {os.environ[variabile]}",
                    "Content-Type": "application/json",
                }, json={"model": modello, "messages": messaggi, "temperature": 0})
            except requests.RequestException as e:
                errore = str(e)
            else:
                if r.status_code == 200:
                    try:
                        return r.json()["choices"][0]["message"]["content"]
                    except (ValueError, KeyError, IndexError, TypeError):
                        errore = f"risposta non valida: {r.text[:200]!r}"
                else:
                    errore = f"HTTP {r.status_code}: {r.text[:300]}"
                    if r.status_code not in (429, 500, 502, 503, 504):
                        break
            time.sleep(8 * (tentativo + 1))
        raise IANonDisponibile(f"{nome}: {errore}")

    def _chiedi_claude(self, messaggi):
        """Claude tramite Claude Code e il tuo abbonamento Pro (CLAUDE_CODE_OAUTH_TOKEN)."""
        testo = messaggi[0]["content"] + "\n\n---\n\n" + messaggi[1]["content"]
        try:
            esito = subprocess.run(
                ["claude", "-p", testo, "--output-format", "json", "--tools", ""],
                capture_output=True, text=True, timeout=240)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise IANonDisponibile(f"Claude: {e}")
        if esito.returncode != 0:
            raise IANonDisponibile(f"Claude: {(esito.stderr or esito.stdout)[-300:]}")
        try:
            dati = json.loads(esito.stdout)
        except ValueError:
            return esito.stdout
        if dati.get("is_error"):
            raise IANonDisponibile(f"Claude: {str(dati.get('result'))[:300]}")
        return dati.get("result", "")

    def _chiedi(self, messaggi):
        if not self.servizi and not self.claude:
            raise IANonDisponibile("nessuna IA configurata nei Secrets "
                                   "(CLAUDE_CODE_OAUTH_TOKEN, GEMINI_API_KEY o GROQ_API_KEY)")
        self.chiamate += 1
        errori = []
        if self.claude:
            try:
                return self._chiedi_claude(messaggi)
            except IANonDisponibile as e:
                print(f"  [redattore] {e}")
                errori.append(str(e))
        for servizio in self.servizi:
            try:
                return self._chiedi_a(*servizio, messaggi)
            except IANonDisponibile as e:
                print(f"  [redattore] {e}")
                errori.append(str(e))
        raise IANonDisponibile(" | ".join(errori))

    def _json(self, testo):
        try:
            return json.loads(re.search(r"\{.*\}", testo, re.S).group(0))
        except (AttributeError, ValueError, TypeError):
            return None

    def scrivi_scheda(self, candidato, data_uscita):
        """Titolo e testo in italiano scritti SOLO dalla scheda d'archivio, poi ricontrollati."""
        scheda = (f"DATA DI USCITA DEL CINEGIORNALE: {data_uscita.day}/{data_uscita.month}/"
                  f"{data_uscita.year}\nTITOLO ORIGINALE: {candidato['titolo']}\n"
                  f"DESCRIZIONE D'ARCHIVIO: {candidato.get('descrizione') or '(nessuna)'}")
        bozza = self._json(self._chiedi([{"role": "system", "content": SCRIVI},
                                         {"role": "user", "content": scheda}]))
        if not bozza or bozza.get("pubblicabile") is not True:
            return None, "scartato: " + str((bozza or {}).get("motivo", "risposta non leggibile"))
        titolo = str(bozza.get("titolo", "")).strip()
        testo = str(bozza.get("testo", "")).strip()
        if not titolo or not testo or len(titolo) > 70 or len(testo) > 260:
            return None, "scartato: titolo o testo mancanti o troppo lunghi"
        controllo = self._json(self._chiedi([
            {"role": "system", "content": CONTROLLA},
            {"role": "user", "content": f"{scheda}\n\n---\nTITOLO ITALIANO: {titolo}\n"
                                        f"TESTO ITALIANO: {testo}"}]))
        if not controllo:
            return None, "scartato: controllo non leggibile"
        try:
            certezza = int(controllo.get("certezza", 0))
        except (TypeError, ValueError):
            certezza = 0
        if controllo.get("corretto") is not True or certezza < CERTEZZA_MINIMA:
            return None, f"scartato dal controllo ({certezza}%): {controllo.get('problemi', '')}"
        return {"titolo": titolo, "testo": testo}, f"{certezza}% — verificato sulla scheda"

    def giudica(self, evento, data_evento, candidato):
        scheda = (
            f"EVENTO ({data_evento.day}/{data_evento.month}/{evento['anno']}): {evento['testo']}\n\n"
            f"FILMATO D'ARCHIVIO\nFonte: {candidato['fonte']}\nTitolo: {candidato['titolo']}\n"
            f"Anno indicato dall'archivio: {candidato.get('anno') or 'sconosciuto'}\n"
            f"Descrizione: {candidato.get('descrizione') or '(nessuna)'}"
        )
        testo = self._chiedi([{"role": "system", "content": ISTRUZIONI},
                              {"role": "user", "content": scheda}])
        try:
            esito = json.loads(re.search(r"\{.*\}", testo, re.S).group(0))
            certezza = int(esito.get("certezza", 0))
        except (AttributeError, ValueError, TypeError):
            return False, "risposta non leggibile, scartato per sicurezza"
        ok = esito.get("corrisponde") is True and certezza >= CERTEZZA_MINIMA
        return ok, f"{certezza}% — {esito.get('motivo', '')}"
