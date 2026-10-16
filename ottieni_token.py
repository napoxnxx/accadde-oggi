"""Da lanciare UNA SOLA VOLTA sul tuo PC per collegare il canale YouTube.

1. Metti in questa cartella il file client_secret.json scaricato da Google Cloud.
2. Esegui:  pip install google-auth-oauthlib   e poi   python ottieni_token.py
3. Si apre il browser: accedi con l'account del canale e conferma.
4. Copia i tre valori stampati nei Secrets del repository GitHub.
"""

import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]

flusso = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPE)
cred = flusso.run_local_server(port=0, access_type="offline", prompt="consent")
dati = json.loads(Path("client_secret.json").read_text())
dati = dati.get("installed") or dati.get("web")

print("\nCopia questi tre valori in GitHub → Settings → Secrets and variables → Actions:\n")
print("YT_CLIENT_ID     =", dati["client_id"])
print("YT_CLIENT_SECRET =", dati["client_secret"])
print("YT_REFRESH_TOKEN =", cred.refresh_token)
