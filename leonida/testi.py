"""Titoli, descrizioni, fatti verificati e domande per i commenti."""

import hashlib
import re

USCITA_ANNO = 2026

# Fatti per il "LO SAPEVI?" del conto alla rovescia: solo informazioni ufficiali e verificate.
# Fonti: Take-Two (risultati del 9/11/2026), rockstargames.com/VI e /VI/media, annunci Rockstar
# del 2/5/2025 e del 6/11/2025 sui rinvii.
FATTI = [
    "Esce giovedì 19 novembre 2026 su PS5 e Xbox Series X|S.",
    "È ambientato nello stato di Leonida, con la sua Vice City.",
    "I protagonisti sono Jason Duval e Lucia Caminos.",
    "Doveva uscire nell'autunno 2025: è stato rinviato due volte, prima al 26 maggio e poi al 19 novembre 2026.",
    "Il Trailer 2 è uscito il 6 maggio 2025.",
    "Per la versione PC non c'è ancora una data: per ora esce solo su console.",
]

DOMANDE = ["L'HAI GIÀ PREORDINATO?", "JASON O LUCIA?", "SU QUALE CONSOLE LO GIOCHI?",
           "QUANTE ORE CI GIOCHI IL PRIMO GIORNO?", "COSA FAI APPENA ARRIVI A VICE CITY?",
           "TI SEI PRESO LE FERIE?", "CON CHI LO GIOCHERAI?", "CHE VOTO GLI DAI SULLA FIDUCIA?"]

DOMANDE_MONTAGGIO = ["DOVE VAI PER PRIMA COSA?", "QUALE POSTO VUOI VISITARE?", "JASON O LUCIA?",
                     "CHE AUTO RUBI PER PRIMA?", "SPIAGGIA O CITTÀ?", "GIORNO O NOTTE A VICE CITY?"]

INVITO = "Ogni giorno notizie e immagini ufficiali di GTA 6: iscriviti per non perderti niente."
CREDITI = ("Immagini e clip ufficiali: Rockstar Games (rockstargames.com/VI/media). "
           "Musica originale. Canale di fan non affiliato a Rockstar Games né a Take-Two.")
HASHTAG = "#gta6 #gtavi #gta #rockstargames #shorts"


_NOMI = ["GTA", "Jason", "Lucia", "Vice City", "Leonida", "Justice", "PS5", "Xbox", "Rockstar", "Keys", "Tommy Vercetti"]


def frase(domanda):
    """'JASON O LUCIA?' -> 'Jason o Lucia?' (maiuscole solo all'inizio e nei nomi)."""
    testo = domanda.strip().lower()
    for nome in _NOMI:
        testo = re.sub(r"\b" + re.escape(nome.lower()) + r"\b", nome, testo)
    return testo[:1].upper() + testo[1:]


def scegli(lista, seme):
    return lista[int(hashlib.sha256(str(seme).encode()).hexdigest(), 16) % len(lista)]


def countdown(giorni, fatto, domanda):
    if giorni <= 0:
        titolo = "GTA 6 esce OGGI! 🔥 Sei pronto?"
        apertura = "È il giorno: GTA 6 esce oggi su PS5 e Xbox Series X|S! 🔥"
    elif giorni == 1:
        titolo = "Manca 1 giorno a GTA 6! ⏳"
        apertura = "Manca un solo giorno all'uscita di GTA 6! ⏳"
    else:
        titolo = f"Mancano {giorni} giorni a GTA 6 ⏳"
        apertura = f"Mancano {giorni} giorni all'uscita di GTA 6! ⏳"
    righe = [apertura, "", f"Lo sapevi? {fatto}", "", f"{frase(domanda)} Scrivilo nei commenti 👇", "",
             INVITO, "", CREDITI, "", HASHTAG]
    return titolo, "\n".join(righe)


def notizia(n):
    titolo = (n.get("titolo_youtube") or n["titolo"]).strip()
    righe = [*n["frasi"], "", "Tu cosa ne pensi? Scrivilo nei commenti 👇", "", INVITO, "",
             "Notizia confermata da almeno 3 testate diverse e raccontata con parole nostre. Fonti:"]
    una_per_testata = list({a["fonte"]: a for a in reversed(n.get("articoli", []))}.values())[::-1]
    righe += [f"- {a['fonte']}: {a['link']}" for a in una_per_testata[:5]]
    righe += ["", CREDITI, "", HASHTAG]
    return titolo[:100], "\n".join(righe)


def montaggio(domanda, seme, giorni=None):
    if giorni is not None and giorni > 0:
        quando = "1 giorno" if giorni == 1 else f"{giorni} giorni"
        titolo = scegli([f"Leonida ti aspetta: -{quando} a GTA 6 🌴", f"Vice City tra {quando} 🌴 GTA 6"], seme)
    else:
        titolo = scegli(["Benvenuti a Leonida 🌴 GTA 6", "Vice City come non l'hai mai vista 🌴 GTA 6",
                         "Questa è Leonida 🌴 GTA 6", "Un giro a Vice City 🌆 GTA 6", "Leonida in 10 secondi 🌴 GTA 6",
                         "Le immagini più belle di GTA 6 🌴", "Tramonto a Vice City 🌅 GTA 6",
                         "Leonida dall'alto 🌴 GTA 6", "Vice City di notte 🌃 GTA 6", "Cartoline da Leonida 🌴 GTA 6",
                         "Dieci secondi a Vice City 🌆 GTA 6", "Leonida, che spettacolo 🌴 GTA 6",
                         "Vice City ti aspetta 🌴 GTA 6", "Dentro il mondo di GTA 6 🌴", "Scorci di Leonida 🌅 GTA 6",
                         "Luci di Vice City 🌃 GTA 6", "Un giorno a Leonida 🌴 GTA 6", "GTA 6: guarda che dettagli 👀"], seme)
    righe = ["Immagini ufficiali di GTA 6 con musica originale in stile anni '80. 🌴", "",
             f"{frase(domanda)} Scrivilo nei commenti 👇", "", INVITO, "", CREDITI, "", HASHTAG]
    return titolo, "\n".join(righe)


# Chicche e dettagli: SOLO informazioni ufficiali di Rockstar, raccontate con parole nostre.
# Fonti: rockstargames.com/VI/only-in-leonida (personaggi e luoghi), rockstargames.com/VI
# (trama, edizioni, notizie in evidenza), rockstargames.com/VI/media (nomi dei pacchetti ufficiali).
# "media" = parole per trovare l'immagine giusta tra i file ufficiali (dal loro nome).
# "fino_al" = da non usare dopo quella data (informazioni che possono cambiare).
CHICCHE = [
    {"id": "jason", "etichetta": "PERSONAGGI", "titolo": "Chi è Jason Duval?", "media": ["JASON"],
     "frasi": ["È cresciuto in mezzo a truffatori e criminali.",
               "Dopo l'esercito è tornato nelle Keys a lavorare per dei trafficanti locali.",
               "Incontrare Lucia potrebbe essere la cosa migliore o la peggiore della sua vita."],
     "domanda": "JASON O LUCIA?"},
    {"id": "lucia", "etichetta": "PERSONAGGI", "titolo": "Chi è Lucia Caminos?", "media": ["LUCIA"],
     "frasi": ["Suo padre le ha insegnato a combattere fin da piccola.",
               "È finita nel carcere di Leonida per aver difeso la sua famiglia.",
               "Uscita grazie alla fortuna, ora vuole una vita migliore pianificando ogni mossa."],
     "domanda": "TI PIACE LUCIA?"},
    {"id": "vice-city", "etichetta": "LUOGHI", "titolo": "Vice City, USA", "media": ["VICE CITY"],
     "frasi": ["Rockstar la descrive come il lato più oscuro del posto più soleggiato d'America.",
               "È la città al neon dove si muove la storia di Jason e Lucia."],
     "domanda": "SEI PRONTO PER VICE CITY?"},
    {"id": "storia", "etichetta": "LA STORIA", "titolo": "Di cosa parla GTA VI", "media": ["JASON", "LUCIA"],
     "frasi": ["Jason e Lucia finiscono in una cospirazione criminale che attraversa lo stato di Leonida.",
               "Tutto parte da un colpo facile andato storto.",
               "Per sopravvivere dovranno contare l'uno sull'altra."],
     "domanda": "COME FINIRÀ SECONDO TE?"},
    {"id": "cal", "etichetta": "PERSONAGGI", "titolo": "Chi è Cal Hampton?", "media": ["CAL HAMPTON"],
     "frasi": ["È amico di Jason e collabora con Brian.",
               "Si sente al sicuro solo a casa, a spiare le comunicazioni della Guardia Costiera con qualche birra."],
     "domanda": "TI STA SIMPATICO CAL?"},
    {"id": "luoghi", "etichetta": "LUOGHI", "titolo": "I luoghi di Leonida", "media": ["VICE CITY", "LEONIDA KEYS",
                                                                                      "GRASSRIVERS", "PORT GELLHORN",
                                                                                      "AMBROSIA", "KALAGA"],
     "frasi": ["Oltre a Vice City, Rockstar ha mostrato Leonida Keys, Grassrivers e Port Gellhorn.",
               "Poi ci sono Ambrosia e Mount Kalaga."],
     "domanda": "DOVE VAI PER PRIMA COSA?"},
    {"id": "boobie", "etichetta": "PERSONAGGI", "titolo": "Chi è Boobie Ike?", "media": ["BOOBIE"],
     "frasi": ["È una leggenda di Vice City.",
               "Ha trasformato i soldi della strada in immobili, uno strip club e uno studio di registrazione.",
               "È in società con Dre'Quan nell'etichetta Only Raw Records."],
     "domanda": "BOOBIE: AMICO O NEMICO?"},
    {"id": "justice", "etichetta": "MUSICA", "titolo": "La colonna sonora è dei Justice", "media": [],
     "frasi": ["La colonna sonora originale di GTA VI porta la firma dei Justice.",
               "Rockstar l'ha annunciato il 29 ottobre 2026."],
     "domanda": "TI PIACCIONO I JUSTICE?"},
    {"id": "drequan", "etichetta": "PERSONAGGI", "titolo": "Chi è Dre'Quan Priest?", "media": ["DREQUAN", "DRE QUAN"],
     "frasi": ["È sempre stato più un affarista che un gangster.",
               "Sognava di sfondare nella musica anche mentre spacciava.",
               "Ha messo sotto contratto i Real Dimez e punta alla scena di Vice City."],
     "domanda": "TI FIDERESTI DI LUI?"},
    {"id": "keys", "etichetta": "LUOGHI", "titolo": "Leonida Keys", "media": ["LEONIDA KEYS", "KEYS"],
     "frasi": ["È la zona di Jason.",
               "Dopo l'esercito è tornato lì a lavorare per i trafficanti locali."],
     "domanda": "TI PIACCIONO LE ISOLE?"},
    {"id": "real-dimez", "etichetta": "PERSONAGGI", "titolo": "Chi sono i Real Dimez?", "media": ["REAL DIMEZ", "DIMEZ"],
     "frasi": ["Sono un duo nato tra i banchi del liceo.",
               "Hanno conquistato il pubblico con i social e la musica.",
               "Dopo un successo con DWNPLY hanno firmato con la Only Raw Records."],
     "domanda": "TI PIACE LA LORO MUSICA?"},
    {"id": "raul", "etichetta": "PERSONAGGI", "titolo": "Chi è Raul Bautista?", "media": ["RAUL"],
     "frasi": ["È un rapinatore di banche con tanta esperienza.",
               "Cerca gente di talento disposta a rischiare grosso.",
               "La sua imprudenza alza la posta a ogni colpo."],
     "domanda": "LO SEGUIRESTI IN UN COLPO?"},
    {"id": "brian", "etichetta": "PERSONAGGI", "titolo": "Chi è Brian Heder?", "media": ["BRIAN"],
     "frasi": ["È un trafficante delle Keys che è in giro da molto tempo.",
               "Muove ancora la merce attraverso il suo cantiere navale.",
               "Fa vivere Jason senza affitto in cambio di aiuto con le estorsioni della zona."],
     "domanda": "TI FIDI DI BRIAN?"},
    {"id": "ultimate", "etichetta": "EDIZIONI", "titolo": "Cosa c'è nell'Ultimate Edition", "media": ["ULTIMATE", "CHEETAH",
                                                                                                    "MORGAN"],
     "frasi": ["Rockstar la presenta come una raccolta esclusiva legata alla storia di Jason e Lucia.",
               "Tra i contenuti mostrati ci sono una Grotti Cheetah del '95 e i revolver Hawk & Little Morgan."],
     "domanda": "PRENDI L'ULTIMATE?"},
    {"id": "vintage", "etichetta": "BONUS", "titolo": "Il pacchetto Vintage Vice City", "media": ["VINTAGE", "STANIER"],
     "frasi": ["È il bonus per chi preordina GTA VI.",
               "Nelle immagini ufficiali ci sono una Vapid Stanier del '55 e outfit e acconciature vintage."],
     "domanda": "L'HAI GIÀ PREORDINATO?"},
    {"id": "trailer", "etichetta": "TRAILER", "titolo": "I quattro trailer ufficiali", "media": [],
     "frasi": ["Rockstar ha pubblicato Trailer 1, Trailer 2, An Extended Look e il Launch Trailer.",
               "Il Trailer 2 è uscito il 6 maggio 2025."],
     "domanda": "QUAL È IL TUO PREFERITO?"},
    {"id": "rinvii", "etichetta": "LO SAPEVI?", "titolo": "Rinviato due volte", "media": [],
     "frasi": ["GTA VI doveva uscire nell'autunno 2025.",
               "Poi è slittato al 26 maggio 2026 e infine al 19 novembre 2026."],
     "domanda": "VALEVA LA PENA ASPETTARE?"},
    {"id": "collezione", "etichetta": "LO SAPEVI?", "titolo": "The Vice City Collection", "media": ["COLLECTION"],
     "frasi": ["Sullo store di Rockstar c'è anche un cofanetto da collezione.",
               "Si chiama The Vice City Collection."],
     "domanda": "LO COMPRERESTI?"},
    {"id": "piattaforme", "etichetta": "LO SAPEVI?", "titolo": "Su cosa esce GTA VI", "media": [], "fino_al": "2026-11-25",
     "frasi": ["Esce il 19 novembre 2026 su PS5 e Xbox Series X|S.",
               "Per la versione PC non c'è ancora una data."],
     "domanda": "SU COSA LO GIOCHI?"},
    {"id": "preload", "etichetta": "LO SAPEVI?", "titolo": "Il pre-load è aperto", "media": [], "fino_al": "2026-11-18",
     "frasi": ["Rockstar ha aperto il pre-load dal 10 novembre.",
               "Così il giorno dell'uscita si può giocare subito."],
     "domanda": "L'HAI GIÀ SCARICATO?"},
]


# ---------------------------------------------------------------- pillole dal web (verificate)
# Gameplay, storia della serie, record, retroscena e scandali. Ogni pillola ha le sue fonti,
# che finiscono nel video e nella descrizione. Ricerca del 10/11/2026.
_IGN = ("IGN (intervista a Rockstar)", "https://www.vice.com/en/article/rockstar-reveals-35-new-gta-6-features-ign/")
_DAZED = ("Dazed (intervista a Rockstar)", "https://www.techradar.com/gaming/new-gta-6-details-reveal-a-bonnie-and-clyde-type-narrative-life-sim-systems-and-the-ability-to-seamlessly-swap-between-jason-and-lucia-during-gameplay")
_ANTEPRIME = ("Anteprime della stampa", "https://www.gtabase.com/articles/gta-6/gta-6-previews-recap-all-new-gameplay-features-revealed")
_TAKETWO = ("Take-Two", "https://www.gamedeveloper.com/business/gta-v-surpasses-230-million-sales-months-before-gta-vi-touches-down")

PILLOLE = [
    # ------------------------------------------------ GAMEPLAY
    {"id": "g-cambio", "etichetta": "GAMEPLAY", "titolo": "Jason o Lucia? Cambi quando vuoi", "media": ["JASON", "LUCIA"],
     "frasi": ["Si può passare da Jason a Lucia in qualsiasi momento.",
               "Puoi giocare in coppia o mandarli ognuno per conto suo.",
               "Mentre uno guida, l'altro può sparare dal finestrino."],
     "domanda": "CHI USERAI DI PIÙ?", "fonti": [_DAZED, _IGN]},
    {"id": "g-fisico", "etichetta": "GAMEPLAY", "titolo": "In GTA 6 puoi ingrassare", "media": [],
     "frasi": ["Quello che mangiano Jason e Lucia cambia il loro peso.",
               "Con l'allenamento i muscoli crescono e si vedono.",
               "Anche notti in bianco e fughe dalla polizia lasciano il segno."],
     "domanda": "PALESTRA O FAST FOOD?", "fonti": [_DAZED, _ANTEPRIME]},
    {"id": "g-polizia", "etichetta": "GAMEPLAY", "titolo": "La polizia deve vederti", "media": [],
     "frasi": ["Diventi ricercato solo se qualcuno ti vede, ti denuncia o ti riprende una telecamera.",
               "Se la polizia non sa che faccia hai, le stelle restano vuote.",
               "Cambiare taglio di capelli può confondere le descrizioni."],
     "domanda": "QUANTE STELLE PRENDI SUBITO?", "fonti": [_IGN, _ANTEPRIME]},
    {"id": "g-cassaforte", "etichetta": "GAMEPLAY", "titolo": "Come si apre una cassaforte", "media": ["ROBBERY"],
     "frasi": ["Nei colpi puoi far saltare la cassaforte: fai prima, ma rovini parte del bottino.",
               "Se trovi la combinazione porti via di più.",
               "Alcuni edifici hanno uscite alternative per scappare."],
     "domanda": "ESPLOSIVO O COMBINAZIONE?", "fonti": [_IGN, _ANTEPRIME]},
    {"id": "g-mira", "etichetta": "GAMEPLAY", "titolo": "Non serve per forza uccidere", "media": [],
     "frasi": ["Puoi colpire braccia e gambe per fermare un nemico senza ucciderlo.",
               "Oppure mirare all'arma per disarmarlo.",
               "A volte basta puntare la pistola per farlo scappare."],
     "domanda": "GIOCHI BUONO O CATTIVO?", "fonti": [_IGN, _ANTEPRIME]},
    {"id": "g-bagagliaio", "etichetta": "GAMEPLAY", "titolo": "Il bagagliaio serve davvero", "media": [],
     "frasi": ["Le auto personali hanno un bagagliaio che si può usare.",
               "Dentro puoi tenere vestiti di ricambio e armi.",
               "E se l'auto è ammaccata, la rivendi a meno."],
     "domanda": "CHE AUTO TI TIENI?", "fonti": [_IGN]},
    {"id": "g-telefono", "etichetta": "GAMEPLAY", "titolo": "Il telefono di Jason e Lucia", "media": ["JASON", "LUCIA"],
     "frasi": ["Quando tiri fuori il telefono, la telecamera inquadra il cellulare in mano.",
               "Jason e Lucia si scrivono messaggi di tutti i giorni.",
               "Tipo ricordarsi di chiudere la porta o dire che vanno a letto."],
     "domanda": "TI PIACE QUESTO DETTAGLIO?", "fonti": [_IGN]},
    {"id": "g-animali", "etichetta": "GAMEPLAY", "titolo": "Gli animali di Leonida", "media": ["GRASSRIVERS", "KEYS"],
     "frasi": ["Puoi osservare gli animali e segnarli in un elenco, come in Red Dead Redemption 2.",
               "E sì: i cani si possono accarezzare."],
     "domanda": "ACCAREZZI SUBITO UN CANE?", "fonti": [_IGN]},
    {"id": "g-passanti", "etichetta": "GAMEPLAY", "titolo": "I passanti ti notano", "media": ["VICE CITY"],
     "frasi": ["Se origli o segui qualcuno troppo a lungo, può affrontarti o scappare.",
               "Alcuni passanti armati possono iniziare una sparatoria da soli.",
               "E certe chiacchiere ascoltate per strada fanno partire nuove attività."],
     "domanda": "LI SPIERESTI?", "fonti": [_IGN]},
    {"id": "g-scelte", "etichetta": "GAMEPLAY", "titolo": "Le tue scelte contano", "media": [],
     "frasi": ["Rockstar dice che la storia è pensata per essere rigiocata.",
               "Alcune piccole scelte possono avere conseguenze più avanti.",
               "E certe missioni si possono affrontare in modi diversi."],
     "domanda": "LO RIGIOCHERAI?", "fonti": [_IGN]},
    {"id": "g-pubblicita", "etichetta": "GAMEPLAY", "titolo": "Il panino da 30.000 calorie", "media": [],
     "frasi": ["GTA 6 ha più pubblicità alla radio e in TV di qualsiasi GTA precedente.",
               "Tra quelle mostrate c'è un panino da 30.000 calorie."],
     "domanda": "LA RADIO LA ASCOLTI?", "fonti": [_IGN]},
    {"id": "g-cavigliera", "etichetta": "LA STORIA", "titolo": "La cavigliera di Lucia", "media": ["LUCIA"],
     "frasi": ["Lucia porta un braccialetto elettronico alla caviglia.",
               "Secondo Rockstar ha un ruolo importante nella storia.",
               "Anche in come lei e Jason si mettono insieme."],
     "domanda": "COME SE LO TOGLIERÀ?", "fonti": [_IGN]},
    {"id": "g-bonnie", "etichetta": "LA STORIA", "titolo": "Bonnie e Clyde a Vice City", "media": ["JASON", "LUCIA"],
     "frasi": ["Rockstar ha descritto la storia come un racconto alla Bonnie e Clyde.",
               "È il primo GTA con una coppia come protagonisti.",
               "Jason è un ex militare, Lucia una lottatrice."],
     "domanda": "COME FINIRÀ TRA LORO?", "fonti": [_DAZED]},
    # ------------------------------------------------ STORIA DELLA SERIE
    {"id": "s-gta1", "etichetta": "STORIA DI GTA", "titolo": "Dove è nato tutto", "media": [],
     "frasi": ["Il primo Grand Theft Auto è uscito nel 1997, con la visuale dall'alto.",
               "L'aveva creato DMA Design, uno studio scozzese.",
               "Quello studio oggi si chiama Rockstar North."],
     "domanda": "QUAL È STATO IL TUO PRIMO GTA?", "fonti": [("Rockstar Games", "https://www.rockstargames.com")]},
    {"id": "s-vicecity", "etichetta": "STORIA DI GTA", "titolo": "Si torna a Vice City", "media": ["VICE CITY"],
     "frasi": ["Vice City c'era già in GTA Vice City del 2002, ambientato nel 1986.",
               "Il protagonista era Tommy Vercetti.",
               "Con GTA 6 si torna lì, 24 anni dopo."],
     "domanda": "HAI GIOCATO L'ORIGINALE?", "fonti": [("Rockstar Games", "https://www.rockstargames.com")]},
    {"id": "s-gtav", "etichetta": "STORIA DI GTA", "titolo": "Il miliardo di GTA V", "media": [],
     "frasi": ["GTA V è uscito il 17 settembre 2013.",
               "In tre giorni ha incassato un miliardo di dollari.",
               "Ad agosto 2026 aveva superato i 230 milioni di copie."],
     "domanda": "QUANTE ORE CI HAI GIOCATO?", "fonti": [_TAKETWO, ("Guinness World Records", "https://www.guinnessworldrecords.com")]},
    {"id": "s-attesa", "etichetta": "STORIA DI GTA", "titolo": "13 anni di attesa", "media": [],
     "frasi": ["Tra GTA V e GTA 6 passano più di 13 anni.",
               "È la pausa più lunga di sempre tra due capitoli principali.",
               "Nel frattempo Red Dead Redemption 2 ha superato gli 87 milioni di copie."],
     "domanda": "QUANTI ANNI AVEVI NEL 2013?", "fonti": [_TAKETWO]},
    {"id": "s-lucia", "etichetta": "STORIA DI GTA", "titolo": "Lucia fa la storia", "media": ["LUCIA"],
     "frasi": ["Nel primo GTA del 1997 si poteva scegliere anche un personaggio femminile.",
               "Ma Lucia è la prima protagonista donna di un GTA con una storia tutta sua."],
     "domanda": "LUCIA TI CONVINCE?", "fonti": [("GamesRadar+", "https://www.gamesradar.com/newly-revealed-gta-6-characters-showcase-the-series-first-ever-female-protagonist-and-her-bonnie-and-clyde-style-relationship"),
                                               ("LevelUp", "https://www.levelup.com/en/news/gta-6-lucia-is-not-the-first-female-protagonist-in-the-franchise/")]},
    {"id": "s-florida", "etichetta": "LUOGHI", "titolo": "Leonida è la Florida?", "media": ["LEONIDA", "VICE CITY"],
     "frasi": ["Leonida è lo stato inventato di GTA 6, ispirato alla Florida.",
               "Vice City è la sua versione di Miami.",
               "E le Leonida Keys ricordano le Florida Keys."],
     "domanda": "CI ANDRESTI IN VACANZA?", "fonti": [("Rockstar Games", "https://www.rockstargames.com/VI")]},
    # ------------------------------------------------ RECORD
    {"id": "r-trailer1", "etichetta": "RECORD", "titolo": "Il trailer dei record", "media": [],
     "frasi": ["Il primo trailer di GTA 6 è uscito il 5 dicembre 2023.",
               "In 24 ore ha superato i 90 milioni di visualizzazioni su YouTube.",
               "Nessun video non musicale aveva mai fatto tanto in un giorno."],
     "domanda": "L'HAI VISTO QUEL GIORNO?", "fonti": [("TechCrunch", "https://techcrunch.com/2023/12/05/grand-theft-auto-vi-trailer-breaks-mrbeasts-record-for-most-youtube-views-in-24-hours/")]},
    {"id": "r-trailer2", "etichetta": "RECORD", "titolo": "475 milioni in un giorno", "media": [],
     "frasi": ["Il Trailer 2 è uscito il 6 maggio 2025.",
               "Secondo Rockstar ha fatto 475 milioni di visualizzazioni in 24 ore, contando tutte le piattaforme.",
               "Rockstar l'ha definito il lancio video più grande di sempre."],
     "domanda": "QUANTE VOLTE L'HAI VISTO?", "fonti": [("TechRadar", "https://www.techradar.com/gaming/the-latest-grand-theft-auto-6-trailer-has-set-a-major-record-by-racking-up-475-million-views-in-just-24-hours")]},
    # ------------------------------------------------ RETROSCENA E SCANDALI
    {"id": "x-anticipo", "etichetta": "RETROSCENA", "titolo": "Il trailer uscito in anticipo", "media": [],
     "frasi": ["Il primo trailer di GTA 6 è finito online prima del tempo, in bassa qualità.",
               "Rockstar ha deciso di pubblicarlo subito, ore prima del previsto."],
     "domanda": "TE LO RICORDI?", "fonti": [("PC Gamer", "https://pcgamer.com/gta-6-trailer")]},
    {"id": "x-furto", "etichetta": "SCANDALI", "titolo": "Il grande furto del 2022", "media": [],
     "frasi": ["A settembre 2022 un hacker è entrato nei sistemi di Rockstar.",
               "Decine di video di una versione in sviluppo di GTA 6 sono finiti online.",
               "Rockstar ha confermato il furto e ha detto che lo sviluppo andava avanti."],
     "domanda": "TI HA ROVINATO LA SORPRESA?", "fonti": [("VGC", "https://videogameschronicle.com/news/gta-6-hacker-sentenced-to-an-indefinite-hospital-order")]},
    {"id": "x-licenziamenti", "etichetta": "SCANDALI", "titolo": "Il caso dei licenziamenti", "media": [], "fino_al": "2026-12-31",
     "frasi": ["A fine ottobre 2025 Rockstar ha licenziato 34 dipendenti, 31 nel Regno Unito.",
               "Rockstar dice che avevano diffuso informazioni riservate.",
               "Il sindacato IWGB dice che c'entra l'attività sindacale: il caso è finito in tribunale."],
     "domanda": "TU CHE NE PENSI?", "fonti": [("Digital Citizen", "https://www.digitalcitizen.life/rockstar-union-busting-case-will-go-to-trial-in-september-2026/"),
                                             ("PC Gamer", "https://www.pcgamer.com/gaming-industry/rockstar-faces-legal-setback-as-uk-tribunal-allows-its-fired-workers-to-bring-every-one-of-their-union-busting-allegations-to-trial/")]},
    # ------------------------------------------------ MUSICA
    {"id": "m-trailer", "etichetta": "MUSICA", "titolo": "Le canzoni dei trailer", "media": [],
     "frasi": ["Nel primo trailer c'era Love Is a Long Road di Tom Petty.",
               "Nel secondo Hot Together delle Pointer Sisters.",
               "E la colonna sonora originale del gioco è dei Justice."],
     "domanda": "QUALE PREFERISCI?", "fonti": [("Louder", "https://www.loudersound.com/news/gta-6-trailer-tom-petty"),
                                              ("NME", "https://www.nme.com/news/gaming-news/what-song-grand-theft-auto-6-trailer-2-3860654")]},
]


# ---------------------------------------------------------------- storia della serie (aggiunte il 13/11/2026)
def _wiki(pagina):
    return ("Wikipedia", "https://en.wikipedia.org/wiki/" + pagina)


PILLOLE += [
    {"id": "s-gta3", "etichetta": "STORIA DI GTA", "titolo": "Il GTA che ha cambiato tutto", "media": [],
     "frasi": ["GTA III è uscito nell'ottobre 2001 su PlayStation 2.",
               "È stato il primo GTA in tre dimensioni.",
               "Era ambientato a Liberty City, la New York della serie."],
     "domanda": "CI HAI GIOCATO?", "fonti": [_wiki("Grand_Theft_Auto_III")]},
    {"id": "s-sanandreas", "etichetta": "STORIA DI GTA", "titolo": "San Andreas, anno 1992", "media": [],
     "frasi": ["GTA San Andreas è uscito nel 2004 ed è ambientato nel 1992.",
               "Il protagonista è Carl Johnson, per tutti CJ.",
               "Aveva tre città: Los Santos, San Fierro e Las Venturas."],
     "domanda": "IL MIGLIORE DI SEMPRE?", "fonti": [_wiki("Grand_Theft_Auto:_San_Andreas")]},
    {"id": "s-gta4", "etichetta": "STORIA DI GTA", "titolo": "Niko Bellic a Liberty City", "media": [],
     "frasi": ["GTA IV è uscito il 29 aprile 2008.",
               "Il protagonista è Niko Bellic, arrivato a Liberty City dall'Europa dell'Est.",
               "È stato il primo GTA in alta definizione."],
     "domanda": "TI MANCA NIKO?", "fonti": [_wiki("Grand_Theft_Auto_IV")]},
    {"id": "s-tre", "etichetta": "STORIA DI GTA", "titolo": "Da tre protagonisti a due", "media": ["JASON", "LUCIA"],
     "frasi": ["In GTA V i protagonisti erano tre: Michael, Franklin e Trevor.",
               "Si poteva passare da uno all'altro in qualsiasi momento.",
               "In GTA 6 sono due: Jason e Lucia."],
     "domanda": "MEGLIO DUE O TRE?", "fonti": [_wiki("Grand_Theft_Auto_V"), _DAZED]},
    {"id": "s-online", "etichetta": "STORIA DI GTA", "titolo": "Quando è nato GTA Online", "media": [],
     "frasi": ["GTA Online è partito il 1° ottobre 2013.",
               "Due settimane dopo l'uscita di GTA V.",
               "Da allora non ha mai smesso di ricevere aggiornamenti."],
     "domanda": "CI GIOCHI ANCORA?", "fonti": [_wiki("Grand_Theft_Auto_Online")]},
    {"id": "s-rockstar", "etichetta": "STORIA DI GTA", "titolo": "Chi c'è dietro GTA", "media": [],
     "frasi": ["Rockstar Games è nata a New York nel dicembre 1998.",
               "I GTA principali li sviluppa Rockstar North, a Edimburgo, in Scozia.",
               "La casa madre è Take-Two Interactive."],
     "domanda": "LO SAPEVI?", "fonti": [_wiki("Rockstar_Games")]},
    {"id": "s-tommy", "etichetta": "STORIA DI GTA", "titolo": "La voce di Tommy Vercetti", "media": ["VICE CITY"],
     "frasi": ["Il protagonista di GTA Vice City, Tommy Vercetti, aveva la voce di Ray Liotta.",
               "L'attore di Quei bravi ragazzi.",
               "Il gioco è uscito nel 2002 su PlayStation 2."],
     "domanda": "TE LO RICORDI?", "fonti": [_wiki("Grand_Theft_Auto:_Vice_City")]},
    {"id": "s-vcs", "etichetta": "STORIA DI GTA", "titolo": "L'altra Vice City", "media": ["VICE CITY"],
     "frasi": ["Vice City è tornata nel 2006 con GTA Vice City Stories, su PSP.",
               "Era ambientato nel 1984, due anni prima di GTA Vice City.",
               "Il protagonista era Victor Vance."],
     "domanda": "L'HAI MAI GIOCATO?", "fonti": [_wiki("Grand_Theft_Auto:_Vice_City_Stories")]},
    {"id": "s-anni80", "etichetta": "STORIA DI GTA", "titolo": "Vice City e gli anni '80", "media": ["VICE CITY"],
     "frasi": ["La prima Vice City era ispirata alla Miami degli anni '80.",
               "Tra i modelli c'erano Miami Vice e Scarface.",
               "Quella di GTA 6 è invece una Vice City di oggi."],
     "domanda": "ANNI '80 O OGGI?", "fonti": [_wiki("Grand_Theft_Auto:_Vice_City")]},
    {"id": "s-rdr2", "etichetta": "STORIA DI GTA", "titolo": "Otto anni senza un gioco nuovo", "media": [],
     "frasi": ["L'ultimo grande gioco di Rockstar è Red Dead Redemption 2.",
               "È uscito il 26 ottobre 2018.",
               "GTA 6 arriva otto anni dopo."],
     "domanda": "NE È VALSA LA PENA?", "fonti": [_wiki("Red_Dead_Redemption_2")]},
    {"id": "s-generazioni", "etichetta": "STORIA DI GTA", "titolo": "Un gioco, tre PlayStation", "media": [],
     "frasi": ["GTA V è uscito su tre generazioni di PlayStation.",
               "Su PS3 nel 2013, su PS4 nel 2014 e su PS5 nel 2022.",
               "GTA 6 esce direttamente su PS5 e Xbox Series."],
     "domanda": "SU QUALE L'HAI GIOCATO?", "fonti": [_wiki("Grand_Theft_Auto_V")]},
    {"id": "s-nome", "etichetta": "STORIA DI GTA", "titolo": "Cosa vuol dire Grand Theft Auto", "media": [],
     "frasi": ["Negli Stati Uniti grand theft auto è il nome di un reato.",
               "È il furto di un'automobile.",
               "Cioè la prima cosa che si fa in ogni GTA."],
     "domanda": "LO SAPEVI GIÀ?", "fonti": [_wiki("Grand_Theft_Auto")]},
    {"id": "s-londra", "etichetta": "STORIA DI GTA", "titolo": "L'unico GTA in una città vera", "media": [],
     "frasi": ["Nel 1999 è uscito GTA London 1969.",
               "È l'unico GTA ambientato in una città reale.",
               "Ed è anche l'unico fuori dagli Stati Uniti."],
     "domanda": "UN GTA IN ITALIA LO VORRESTI?", "fonti": [_wiki("Grand_Theft_Auto:_London_1969")]},
    {"id": "s-citta", "etichetta": "STORIA DI GTA", "titolo": "Le tre città di GTA", "media": ["VICE CITY"],
     "frasi": ["Le città storiche della serie sono tre.",
               "Liberty City è New York, Los Santos è Los Angeles.",
               "E Vice City, quella di GTA 6, è Miami."],
     "domanda": "QUAL È LA TUA PREFERITA?", "fonti": [_wiki("Grand_Theft_Auto")]},
    {"id": "s-conferma", "etichetta": "RETROSCENA", "titolo": "Quando Rockstar ha detto sì", "media": [],
     "frasi": ["Rockstar ha confermato il nuovo GTA nel febbraio 2022.",
               "Disse solo che lo sviluppo era già a buon punto.",
               "Il primo trailer è arrivato quasi due anni dopo."],
     "domanda": "DA QUANTO LO ASPETTI?", "fonti": [_wiki("Grand_Theft_Auto_VI")]},
    {"id": "s-25anni", "etichetta": "RETROSCENA", "titolo": "Il trailer per i 25 anni", "media": [],
     "frasi": ["A novembre 2023 Sam Houser, capo di Rockstar, annunciò il primo trailer.",
               "L'occasione erano i 25 anni di Rockstar Games.",
               "Il trailer è uscito il mese dopo, a dicembre."],
     "domanda": "TI RICORDI QUEL GIORNO?", "fonti": [_wiki("Grand_Theft_Auto_VI")]},
    {"id": "s-houser", "etichetta": "RETROSCENA", "titolo": "GTA 6 senza Dan Houser", "media": [],
     "frasi": ["Dan Houser è tra i fondatori di Rockstar e ha scritto le storie dei GTA.",
               "Ha lasciato l'azienda nel 2020.",
               "GTA 6 è il primo capitolo principale dopo il suo addio."],
     "domanda": "SI SENTIRÀ LA DIFFERENZA?", "fonti": [_wiki("Dan_Houser")]},
    {"id": "x-hotcoffee", "etichetta": "SCANDALI", "titolo": "Lo scandalo Hot Coffee", "media": [],
     "frasi": ["Nel 2005 in GTA San Andreas fu scoperto un contenuto nascosto per adulti.",
               "Negli Stati Uniti il gioco fu riclassificato solo per adulti.",
               "Molti negozi lo tolsero dagli scaffali finché non uscì una versione corretta."],
     "domanda": "TE LO RICORDAVI?", "fonti": [_wiki("Hot_Coffee_(minigame)")]},
    {"id": "s-30anni", "etichetta": "STORIA DI GTA", "titolo": "Quasi 30 anni di GTA", "media": [],
     "frasi": ["Il primo Grand Theft Auto è uscito nel 1997.",
               "Nel 2027 la serie compie 30 anni.",
               "E GTA 6 è appena il sesto capitolo numerato."],
     "domanda": "DA QUALE HAI INIZIATO?", "fonti": [_wiki("Grand_Theft_Auto")]},
]


def _alternate(*gruppi):
    """Mescola le categorie: personaggio, gameplay, storia, record... invece di dieci uguali di fila."""
    per_etichetta = {}
    for c in [c for g in gruppi for c in g]:
        per_etichetta.setdefault(c["etichetta"], []).append(c)
    code, risultato = list(per_etichetta.values()), []
    while any(code):
        for coda in code:
            if coda:
                risultato.append(coda.pop(0))
    return risultato


CHICCHE = _alternate(PILLOLE, CHICCHE)  # prima le pillole dal web: le più forti prima dell'uscita


def fonti_brevi(c):
    return [f[0] for f in c.get("fonti", [])] or ["Rockstar Games (sito ufficiale)"]


def chicca(c, seme):
    emoji = {"PERSONAGGI": "🕶️", "LUOGHI": "🌴", "MUSICA": "🎵", "EDIZIONI": "💎", "BONUS": "🎁", "GAMEPLAY": "🎮",
             "STORIA DI GTA": "📼", "RECORD": "🏆", "RETROSCENA": "🕵️", "SCANDALI": "⚠️"}.get(c["etichetta"], "👀")
    titolo = f"{c['titolo']} {emoji} GTA 6"
    if c.get("fonti"):
        provenienza = ["Raccontato con parole nostre. Fonti:"] + [f"- {nome}: {link}" for nome, link in c["fonti"]]
    else:
        provenienza = ["Informazioni ufficiali di Rockstar Games (rockstargames.com/VI), raccontate con parole nostre."]
    righe = [*c["frasi"], "", f"{frase(c['domanda'])} Scrivilo nei commenti 👇", "", INVITO, "",
             *provenienza, "", CREDITI, "", HASHTAG]
    return titolo[:100], "\n".join(righe)
