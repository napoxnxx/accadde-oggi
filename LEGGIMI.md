# ACCADDE OGGI — canale YouTube automatico

Ogni mattina, da solo e anche a PC spento:

1. legge la data di oggi e gli eventi del giorno su Wikipedia;
2. per ogni evento cerca un filmato d'epoca **libero da diritti** (NASA e Internet Archive). Scarta in automatico tutto ciò che non è pubblico dominio, CC0, CC BY o CC BY-SA;
3. monta uno Short verticale 1080x1920 con data, anno, "X anni fa", testo dell'evento, filmato originale e barra di avanzamento;
4. lo pubblica sul canale con titolo, descrizione e fonti/licenze già scritte;
5. si segna il filmato in `storico.json` per non riusarlo mai.

**Costo: zero** con la strada Zapier. GitHub Actions è gratis per i repository pubblici e il sistema non usa l'API di Claude.

---

## Attivazione (una volta sola, circa 30 minuti)

Sono passaggi che nessun programma può fare al posto tuo, perché richiedono il tuo accesso ai tuoi account.

### 1. Il canale
Crea il canale YouTube (es. "Accadde Oggi") con il tuo account Google.

### 2. Come caricare i video: scegli una strada

**Strada A — Zapier (GRATIS, un video al giorno, pubblico da subito) ✅ consigliata**
Come funziona: GitHub crea lo Short e lo mette online, Zapier se ne accorge e lo carica sul canale. L'app YouTube di Zapier è già approvata da Google, quindi i video escono pubblici.

Per questa strada **non servono secret**: se non ne trova, il sistema usa Zapier da solo. L'unico requisito è che il repository GitHub sia **pubblico**, perché Zapier deve poter scaricare il video. Le chiavi restano comunque segrete nei Secrets.

Dopo il passo 3, quando il repository esiste:
1. Registrati gratis su https://zapier.com e premi **Create → Zap**.
2. **Trigger:** cerca **RSS by Zapier**, scegli **New Item in Feed**. Come Feed URL incolla:
   `https://raw.githubusercontent.com/TUO-UTENTE/TUO-REPOSITORY/main/feed.xml`
   Il file `feed.xml` appare dopo il primo giro vero, cioè senza "Solo prova".
3. **Azione:** cerca **YouTube**, scegli **Upload Video** e collega il canale. Compila i campi così:
   - **Video** → il campo **Link** del feed;
   - **Title** → **Title**;
   - **Description** → **Description**;
   - **Privacy Status** → Public;
   - **Category** → Education;
   - **Made for kids** → No.
4. Premi **Publish**. Nota: il test dentro l'editor di Zapier non carica davvero il video, la prova vera è il primo giro pubblicato.

Limiti del piano gratuito di Zapier: 100 operazioni al mese, un video al giorno ne usa circa 30. I video devono restare piccoli e veloci da caricare, e il sistema li comprime già apposta.

**Strada B — Upload-Post (gratis 10 video al mese, illimitati a pagamento)**
1. Registrati su https://www.upload-post.com, crea un profilo (es. `accadde-oggi`), collega il canale e genera una API key.
2. Crea su GitHub i secret `UPLOADPOST_API_KEY` e `UPLOADPOST_USER`.
3. Se resti sul piano gratuito, crea la variabile `OGNI_QUANTI_GIORNI` con valore `3`.

**Strada C — API di Google (gratis, ma lenta a partire)**
Finché Google non approva il progetto con l'audit, che può richiedere settimane, i video vengono **bloccati come privati e non si possono rendere pubblici neanche a mano**.
1. Su https://console.cloud.google.com crea un progetto e abilita **YouTube Data API v3**.
2. In **Schermata consenso OAuth** scegli tipo **Esterno** e premi **PUBBLICA APP**: se resta "In test", il collegamento scade dopo 7 giorni.
3. Crea un **ID client OAuth** di tipo **App desktop**, scarica il JSON e rinominalo `client_secret.json`.
4. Esegui `pip install google-auth-oauthlib` e poi `python ottieni_token.py`.
5. Crea su GitHub i secret `YT_CLIENT_ID`, `YT_CLIENT_SECRET` e `YT_REFRESH_TOKEN`.
6. Compila il modulo **"YouTube API Services – Audit and Quota Extension Form"**.

Priorità se ci sono più secret: Upload-Post, poi API di Google. Senza secret si usa Zapier.

### 3. GitHub (dove gira tutto)
1. Crea un repository su https://github.com/new e carica tutti i file di questa cartella, **tranne** `client_secret.json`. Per la strada Zapier deve essere **pubblico**; per le altre può essere anche privato.
2. Solo per le strade B o C: vai in **Settings → Secrets and variables → Actions** e crea i secret.
3. Vai in **Settings → Actions → General → Workflow permissions**, scegli **Read and write permissions** e salva.

### 4. Prima prova
1. Vai in **Actions → Accadde Oggi → Run workflow**, lascia spuntato "Solo prova" e premi **Run**. Dopo qualche minuto, in fondo alla pagina del giro trovi l'allegato con lo Short.
2. Se ti piace, rilancia **togliendo la spunta**: il video viene pubblicato davvero. Controlla sul canale che sia pubblico.

Fatto questo **non devi fare più niente**: ogni giorno alle 10:47 (09:47 con l'ora solare) esce lo Short.

---

## Regolazioni (facoltative)
- **Visibilità:** in **Settings → Secrets and variables → Actions → Variables** crea `PRIVACY` con valore `public`, `unlisted` o `private`.
- **Orario:** cambialo nella riga `cron` del file `.github/workflows/accadde-oggi.yml` (l'orario è UTC).
- **Prova in locale:** `python -m accadde_oggi --demo` crea `output/demo.mp4` con un filmato finto, per vedere la grafica.

## Note legali già gestite dal programma
- Usa solo filmati con licenza che permette l'uso commerciale, e ricontrolla la licenza sulla scheda completa prima di scaricare.
- Cita sempre fonte, link e licenza nella descrizione e in sovrimpressione.
- I testi vengono da Wikipedia (CC BY-SA 4.0); per questo testi e grafiche del video sono dichiarati con la stessa licenza.
- Per i filmati NASA aggiunge la frase che la NASA non sponsorizza il canale.
