# UNTIL LEONIDA — canale YouTube automatico su GTA VI

Ogni giorno, da solo e anche a PC spento, escono due Short.

## 13:00 — Notizia
1. Il sistema legge i siti di videogiochi: Multiplayer.it, Spaziogames, Everyeye, Eurogamer, IGN Italia, IGN, GameSpot e VGC.
2. Tiene solo i **fatti ufficiali su GTA VI riportati da almeno 3 testate diverse**. Leak, indiscrezioni, "insider", speculazioni e spoiler vengono esclusi in automatico.
3. **Claude** (il tuo abbonamento Pro) scrive il testo **solo** con quello che dicono gli articoli. Un secondo passaggio di Claude lo ricontrolla. Poi ci sono i controlli automatici:
   - ogni numero, data e prezzo deve comparire in almeno 2 testate;
   - niente citazioni;
   - "ufficiale" si scrive solo se lo dicono 2 testate.
4. Se entro le 10:00 non c'è una notizia sicura, esce una **chicca ufficiale**.

## Chicche e dettagli
Sono 20 curiosità prese **solo dai testi ufficiali di Rockstar** e raccontate con parole nostre: gli 8 personaggi (Jason, Lucia, Cal, Boobie Ike, Dre'Quan, Real Dimez, Raul, Brian), Vice City e i luoghi di Leonida, la trama, la colonna sonora dei Justice, l'Ultimate Edition, il pacchetto Vintage Vice City, i trailer e le date. Ogni chicca mostra l'immagine ufficiale del soggetto, trovata dal nome del file di Rockstar. Le chicche sono in `leonida/testi.py`, con le fonti, e se ne possono aggiungere altre.

## 19:00 — Sera
- **Fino al 19 novembre 2026** c'è il conto alla rovescia ("MANCANO X GIORNI A GTA VI"), con un "lo sapevi?" preso da una lista di fatti ufficiali verificati e una domanda per i commenti.
- **Dopo l'uscita** si alternano, un giorno sì e uno no, una chicca ufficiale e un montaggio di 4 immagini di gioco ufficiali, con il nome del luogo o del personaggio preso dal file di Rockstar.

## Immagini, video e musica
- **Immagini e clip:** tutti e 5 i pacchetti ufficiali della pagina di Rockstar "Download and share" (rockstargames.com/VI/media): screenshot, artwork, clip, Ultimate Edition e Vintage Vice City. Hanno il credito "Immagini: Rockstar Games" e le clip si usano **sempre senza audio**. Restano in cache su GitHub e, se Rockstar aggiorna un pacchetto (per esempio con nuove immagini dopo l'uscita), viene riscaricato da solo.
- **Musica:** synthwave anni '80 **originale**, generata a ogni video (tonalità e tempo cambiano). Content ID non ha niente da riconoscere.
- **Mai usati:** canzoni famose (anche quelle dei trailer), leak e video presi da altri canali.
- Se le immagini ufficiali non sono disponibili, il fondale diventa un tramonto con palme disegnato da zero.

## Sicurezza
- Le sere dei prossimi 3 giorni sono sempre pronte, più 2 video di riserva.
- **Via libera:** finché nel repository non c'è il file `via_libera_leonida.txt`, non viene programmato niente su YouTube.

## Prova
Vai in **Actions → Until Leonida → Run workflow**, lascia spuntato "Solo prova", scegli il formato (notizia, countdown, chicca, montaggio o "tutti") e premi **Run**. I video di prova vanno in una Release chiamata `prova-…`.

## Controllo
Il file `stato_leonida.json` contiene i video programmati, quante immagini ufficiali sono pronte, gli ultimi intoppi e l'esito dell'ultima prova.

## Zapier (uno Zap tutto suo, separato da quello di Accadde Oggi)
- **Trigger:** RSS → New Item in Feed, con `https://raw.githubusercontent.com/napoxnxx/accadde-oggi/main/feed_leonida.xml`. Il primo elemento del feed è una prova di collegamento e non viene mai pubblicato.
- **Azione:** YouTube → Upload Video, con questi campi:
  - Video = Link;
  - Title = Title;
  - Description = Description;
  - **Privacy = private**;
  - **Publish At = Categories**;
  - **Category = Gaming**;
  - Made for kids = No.

## Promemoria
- **Token di Claude:** va rinnovato tra un anno con `claude setup-token`.
- **Stesso repository di Accadde Oggi, ma separato:** Until Leonida ha i suoi file (`leonida/`, `feed_leonida.xml`, `storico_leonida.json`, `stato_leonida.json`, `requirements_leonida.txt`) e il suo workflow (`until-leonida.yml`). Accadde Oggi non viene toccato.
- **Fatti del conto alla rovescia:** si trovano in `leonida/testi.py`, con le fonti indicate.

## Protezioni automatiche (aggiunte l'11/11/2026)

- **Controllo delle uscite**: a ogni giro si legge l'elenco pubblico dei video del canale. Se un video doveva essere uscito da più di 75 minuti e non c'è, viene riproposto a Zapier una volta, con un nuovo orario.
- **Avviso**: se anche il secondo tentativo non esce, il sistema apre una Issue in questo repository (GitHub ti manda una email). Vuol dire che va guardata la Zap history su Zapier.
- **Tetto ai caricamenti**: al massimo 4 video nuovi in 24 ore, perché YouTube limita i caricamenti dalle app esterne.
- **Orari elastici**: se GitHub fa partire il giro in ritardo, il video di mezzogiorno esce più tardi (entro le 17:30) e quello della sera entro le 22:30, invece di saltare.
- **Niente notizie doppie**: una notizia già pubblicata negli ultimi 7 giorni non viene riproposta, anche se ne parlano articoli nuovi.
