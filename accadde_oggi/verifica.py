"""Il "redattore": un'IA gratuita (GitHub Models) controlla che il filmato mostri DAVVERO l'evento.

Regola d'oro: nel dubbio si scarta. Se l'IA non risponde, non si pubblica nulla.
"""

import json
import os
import re
import time

import requests

ENDPOINT = "https://models.github.ai/inference/chat/completions"
MODELLO = os.environ.get("MODELLO_IA") or "openai/gpt-4o"
CERTEZZA_MINIMA = 90
MAX_CHIAMATE = int(os.environ.get("MAX_CHIAMATE_IA") or 20)

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

Rispondi solo con JSON: {"corrisponde": true/false, "certezza": 0-100, "motivo": "breve spiegazione in italiano"}"""


class IANonDisponibile(Exception):
    pass


class Redattore:
    def __init__(self):
        self.token = os.environ.get("GITHUB_TOKEN")
        self.chiamate = 0

    def disponibile(self):
        return bool(self.token) and self.chiamate < MAX_CHIAMATE

    def _chiedi(self, messaggi):
        if not self.token:
            raise IANonDisponibile("GITHUB_TOKEN mancante")
        if self.chiamate >= MAX_CHIAMATE:
            raise IANonDisponibile("limite di controlli per questo giro raggiunto")
        self.chiamate += 1
        for tentativo in range(3):
            try:
                r = requests.post(ENDPOINT, timeout=60, headers={
                    "Authorization": f"Bearer {self.token}", "Content-Type": "application/json",
                }, json={"model": MODELLO, "messages": messaggi, "temperature": 0})
            except requests.RequestException as e:
                errore = str(e)
            else:
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"]
                errore = f"HTTP {r.status_code}: {r.text[:300]}"
                if r.status_code not in (429, 500, 502, 503, 504):
                    break
            time.sleep(5 * (tentativo + 1))
        raise IANonDisponibile(errore)

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
        except (AttributeError, ValueError):
            return False, "risposta non leggibile"
        ok = esito.get("corrisponde") is True and int(esito.get("certezza", 0)) >= CERTEZZA_MINIMA
        return ok, f"{esito.get('certezza')}% — {esito.get('motivo', '')}"
