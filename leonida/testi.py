"""Titoli, descrizioni, fatti verificati e domande per i commenti."""

import hashlib

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
    righe = [apertura, "", f"Lo sapevi? {fatto}", "", f"{domanda.capitalize()} Scrivilo nei commenti 👇", "",
             INVITO, "", CREDITI, "", HASHTAG]
    return titolo, "\n".join(righe)


def notizia(n):
    titolo = (n.get("titolo_youtube") or n["titolo"]).strip()
    righe = [*n["frasi"], "", "Tu cosa ne pensi? Scrivilo nei commenti 👇", "", INVITO, "",
             "Notizia confermata da almeno 3 testate diverse e raccontata con parole nostre. Fonti:"]
    righe += [f"- {a['fonte']}: {a['link']}" for a in n.get("articoli", [])[:5]]
    righe += ["", CREDITI, "", HASHTAG]
    return titolo[:100], "\n".join(righe)


def montaggio(domanda, seme, giorni=None):
    if giorni is not None and giorni > 0:
        quando = "1 giorno" if giorni == 1 else f"{giorni} giorni"
        titolo = scegli([f"Leonida ti aspetta: -{quando} a GTA 6 🌴", f"Vice City tra {quando} 🌴 GTA 6"], seme)
    else:
        titolo = scegli(["Benvenuti a Leonida 🌴 GTA 6", "Vice City come non l'hai mai vista 🌴 GTA 6",
                         "Questa è Leonida 🌴 GTA 6", "Un giro a Vice City 🌆 GTA 6", "Leonida in 10 secondi 🌴 GTA 6",
                         "Le immagini più belle di GTA 6 🌴", "Tramonto a Vice City 🌅 GTA 6"], seme)
    righe = ["Immagini ufficiali di GTA 6 con musica originale in stile anni '80. 🌴", "",
             f"{domanda.capitalize()} Scrivilo nei commenti 👇", "", INVITO, "", CREDITI, "", HASHTAG]
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


def chicca(c, seme):
    emoji = {"PERSONAGGI": "🕶️", "LUOGHI": "🌴", "MUSICA": "🎵", "EDIZIONI": "💎", "BONUS": "🎁"}.get(c["etichetta"], "👀")
    titolo = f"{c['titolo']} {emoji} GTA 6"
    righe = [*c["frasi"], "", f"{c['domanda'].capitalize()} Scrivilo nei commenti 👇", "", INVITO, "",
             "Informazioni ufficiali di Rockstar Games (rockstargames.com/VI), raccontate con parole nostre.",
             CREDITI, "", HASHTAG]
    return titolo[:100], "\n".join(righe)
