"""Caricamento su YouTube.

Due strade, scelte in automatico in base ai Secrets presenti:
- Upload-Post (UPLOADPOST_API_KEY + UPLOADPOST_USER): servizio già verificato da Google,
  i video escono pubblici da subito.
- API ufficiale di YouTube (YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN): gratis, ma finché
  Google non approva il progetto (audit) i video restano bloccati come privati.
"""

import os
import time

import requests

SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]


def usa_uploadpost():
    return bool(os.environ.get("UPLOADPOST_API_KEY") and os.environ.get("UPLOADPOST_USER"))


def credenziali_presenti():
    return usa_uploadpost() or all(
        os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))


def carica(file_video, titolo, descrizione, tag, privacy="public"):
    if usa_uploadpost():
        return carica_uploadpost(file_video, titolo, descrizione, tag, privacy)
    return carica_api_youtube(file_video, titolo, descrizione, tag, privacy)


def carica_uploadpost(file_video, titolo, descrizione, tag, privacy):
    dati = {
        "user": os.environ["UPLOADPOST_USER"], "platform[]": "youtube",
        "title": titolo[:100], "description": descrizione[:4900], "tags": ",".join(tag[:15]),
        "privacyStatus": privacy, "categoryId": "27", "selfDeclaredMadeForKids": "false",
        "defaultLanguage": "it", "defaultAudioLanguage": "it", "containsSyntheticMedia": "false",
    }
    with open(file_video, "rb") as f:
        r = requests.post("https://api.upload-post.com/api/upload", timeout=600,
                          headers={"Authorization": "Apikey " + os.environ["UPLOADPOST_API_KEY"]},
                          data=dati, files={"video": (os.path.basename(file_video), f, "video/mp4")})
    print("Risposta Upload-Post:", r.status_code, r.text[:800])
    r.raise_for_status()
    risposta = r.json()
    if risposta.get("success") is False:
        raise RuntimeError(f"Upload-Post ha rifiutato il caricamento: {risposta}")
    return str(risposta.get("request_id") or risposta.get("id") or "uploadpost")


def carica_api_youtube(file_video, titolo, descrizione, tag, privacy):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    cred = Credentials(
        None, refresh_token=os.environ["YT_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=SCOPE,
    )
    yt = build("youtube", "v3", credentials=cred, cache_discovery=False)
    corpo = {
        "snippet": {
            "title": titolo[:100], "description": descrizione[:4900], "tags": tag[:15],
            "categoryId": "27", "defaultLanguage": "it", "defaultAudioLanguage": "it",
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(file_video), mimetype="video/mp4", chunksize=8 << 20, resumable=True)
    richiesta = yt.videos().insert(part="snippet,status", body=corpo, media_body=media)
    risposta, tentativi = None, 0
    while risposta is None:
        try:
            _, risposta = richiesta.next_chunk()
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and tentativi < 5:
                tentativi += 1
                time.sleep(2 ** tentativi)
                continue
            raise
    return risposta["id"]
