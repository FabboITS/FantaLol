# Regole FantaLeague — competizioni regionali (LEC · LCK · LPL)

Crea la tua squadra scegliendo i giocatori professionisti della competizione scelta e sfida gli altri
partecipanti della lega. Costruisci una rosa equilibrata, segui le partite ufficiali e accumula punti
in base alle prestazioni reali dei tuoi giocatori. Il regolamento è identico per LEC, LCK e LPL; per
i Worlds vale il regolamento dedicato in [Rules-WORLDS.md](Rules-WORLDS.md).

| Competizione | Squadre (T) | Fuso | Finestra formazione (default) |
| --- | --- | --- | --- |
| LEC | 10 | Europe/Rome | modificabile mar 00:00 – gio 23:59:59, effettiva dal venerdì 00:00 |
| LCK | 10 | Asia/Seoul | modificabile fino a 60 minuti prima della prima serie della giornata |
| LPL | quelle dell'edizione (14–17) | Asia/Shanghai | modificabile fino a 60 minuti prima della prima serie della giornata |

## Creazione della lega

Il creatore della lega sceglie la competizione e l'edizione (stagione/split) da seguire; la scelta
non è più modificabile. Il numero massimo di fantasy team è pari al numero di squadre reali
dell'edizione (T): 10 in LEC e LCK, quante sono le squadre dell'edizione in LPL.

Ogni partecipante può gestire un solo fantasy team all'interno della stessa lega.

## Composizione della rosa

La composizione della rosa dipende dal numero di partecipanti, confrontato con metà delle squadre
reali dell'edizione (floor(T/2)).

### Leghe con più di T/2 partecipanti (con T = 10: da 6 a 10)

Ogni fantasy team è composto da 5 giocatori titolari, uno per ruolo: Top laner, Jungler, Mid laner,
ADC e Support. La formazione coincide automaticamente con la rosa.

### Leghe con al massimo T/2 partecipanti (con T = 10: da 2 a 5)

Ogni fantasy team è composto da 10 giocatori, due per ruolo: 5 titolari e 5 riserve.

Ogni professionista è esclusivo e può appartenere a un solo fantasy team all'interno della lega.
I giocatori non acquistati durante l'asta rimangono svincolati e possono essere acquistati
successivamente, secondo le regole del mercato stabilite dalla lega.

## Asta

Durante l'asta i partecipanti usano i crediti disponibili per acquistare i giocatori della
competizione. L'offerta iniziale è la quotazione del player, ogni rilancio deve superare di almeno
1 credito l'offerta corrente e riavvia il conto alla rovescia di 15 secondi; allo scadere il player
va al miglior offerente. Non è possibile acquistare un giocatore già appartenente a un altro fantasy
team né superare i limiti di rosa per ruolo. L'admin della lega può chiudere l'asta e completare
casualmente le rose incomplete.

## Formazione

La creazione della prima giornata blocca il numero di partecipanti della lega e apre automaticamente
l'asta. Finché l'asta è aperta, la giornata non può essere usata o chiusa.

Nelle leghe con riserve, dopo la chiusura dell'asta ogni proprietario sceglie un titolare per ruolo
secondo la finestra della competizione (vedi tabella). Se non la aggiorna, resta valida l'ultima
formazione schierata; se non ne ha mai schierata una, il fantasy team riceve 0 punti. Un cambio non
altera mai i punti già maturati: il sistema conserva lo storico dei periodi in cui ciascun player è
stato titolare.

Un giocatore che non disputa una partita ufficiale non riceve punti.

## Punteggi

I punteggi sono calcolati per ogni singola partita con le statistiche ufficiali (fonte Leaguepedia).
Per Top, Jungle, Mid e ADC i coefficienti sono elencati nell'ordine kill / assist / morte / 100 CS:

| Ruolo | Kill | Assist | Morte | Risorsa |
| --- | --- | --- | --- | --- |
| Top | 3,00 | 2,00 | −2,00 | 1,25 ogni 100 CS |
| Jungle | 3,00 | 2,25 | −2,00 | 0,70 ogni 100 CS |
| Mid | 3,00 | 2,00 | −2,00 | 1,00 ogni 100 CS |
| ADC | 3,25 | 1,75 | −2,25 | 1,10 ogni 100 CS |
| Support | 2,15 | 2,55 | −1,75 | 1 punto ogni 50 di vision score (i CS non contano) |

CS e vision score sono continui: 50 CS valgono metà del coefficiente, 25 di vision score valgono
0,5 punti. Ogni vittoria assegna 3 punti. Il ruolo usato è quello del roster ufficiale dell'edizione.

In una serie si calcola la media delle sole partite effettivamente disputate dal player. Se una
giornata comprende più serie, i relativi punteggi vengono sommati.

Il punteggio della giornata del fantasy team è la media aritmetica dei punteggi dei cinque player
attivi. Un player senza statistiche vale 0 punti e il totale viene comunque diviso per cinque. I
punteggi delle giornate chiuse vengono sommati per la classifica generale. I risultati storici
conservano la formula con cui sono stati calcolati.

## Mercato e cambi

I giocatori rimasti svincolati possono essere acquistati durante le finestre di mercato stabilite
dal creatore della lega. Per acquistare un nuovo giocatore il partecipante deve liberare uno spazio
valido nella propria rosa (rilascio con rimborso del 50% dei crediti spesi) e continuare a rispettare
i requisiti per ruolo.

Quando tutti i titolari della competizione sono già assegnati, i cambi possono avvenire tramite
scambi tra fantasy team (accettati da entrambe le parti), acquisto di nuovi giocatori aggiunti ai
roster ufficiali o sostituzione di un giocatore che lascia la competizione.

## Cambi nei roster reali

Se una squadra sostituisce un proprio giocatore, il professionista acquistato rimane nella rosa del
fantasy team ma riceve punti solo quando disputa una partita ufficiale. Un nuovo giocatore aggiunto
alla competizione entra nel mercato come svincolato. Se un professionista abbandona definitivamente
la competizione, il proprietario può sostituirlo con un giocatore disponibile dello stesso ruolo.

## Aggiornamento dei risultati

Calendario e risultati arrivano da PandaScore (ogni ora), le statistiche per partita da Leaguepedia
(ogni 30 minuti). Al termine delle partite il sistema aggiorna rendimento dei giocatori, punteggio
dei fantasy team, classifica della giornata e classifica generale.

I risultati restano provvisori finché mancano statistiche. Se una partita viene rinviata, la
giornata resta in attesa ed è esclusa dalla classifica generale finché non viene chiusa. Una giornata
si chiude automaticamente quando tutte le sue serie sono concluse e hanno statistiche complete (la
lega può disattivare la chiusura automatica). In caso di statistiche mancanti, errori della fonte o
partite annullate l'amministratore può correggere manualmente i risultati.

## Comportamento dei partecipanti

Non sono consentiti account multipli nella stessa lega, accordi per alterare la competizione, scambi
volutamente sbilanciati o fraudolenti, lo sfruttamento di errori tecnici e i tentativi di manipolare
aste, rose, risultati o classifiche. I comportamenti scorretti possono comportare l'annullamento di
un'operazione, una penalizzazione o l'esclusione dalla lega.

## Accettazione delle regole

Entrando in una lega, ogni partecipante dichiara di aver letto e accettato il regolamento. Il
creatore della lega può configurare alcune impostazioni (crediti, finestre di mercato, chiusura
automatica delle giornate) ma non le regole fondamentali su composizione delle rose ed esclusività.
