# Gestione amministrativa, visibilità leghe e documentazione — Design

## Obiettivo

Completare la distinzione tra amministratore globale e utenti normali, limitare la
visibilità delle leghe in base alla partecipazione, rendere funzionante la directory
utenti tramite `Ctrl+Y`, riordinare la home page e sostituire il README del solo backend
con una documentazione generale italiana nella root del progetto.

Tutto il nuovo codice sorgente, inclusi identificatori, nomi dei test, commenti e
messaggi tecnici, deve essere scritto in inglese. Il nuovo `README.md` costituisce
l'eccezione esplicita e deve essere scritto interamente in italiano; i testi già
visibili nell'interfaccia restano in italiano per coerenza con il sito.

## Ruoli e account amministratore

L'applicazione mantiene i due ruoli esistenti, `ADMIN` e `USER`. L'account globale
`ADMIN` continua a essere creato automaticamente da `AdminAccountInitializer`; non
vengono introdotti pannelli per promuovere altri account né vengono pubblicate
credenziali nel frontend o nel README.

L'autorizzazione è sempre applicata dal backend. I controlli visibili nel frontend
servono esclusivamente a rendere chiara l'interfaccia e non sostituiscono i controlli
Spring Security e di servizio.

## Visibilità delle leghe

`GET /api/leagues` usa l'utente autenticato per determinare il risultato:

- un account `ADMIN` riceve tutte le leghe presenti nel sito;
- un account `USER` riceve le leghe che ha creato e quelle nelle quali possiede un
  FantaTeam;
- se il creatore possiede anche un FantaTeam nella stessa lega, la lega compare una
  sola volta;
- l'ordinamento è stabile per identificativo crescente, così la UI e i test producono
  risultati prevedibili.

Il controller passa `authentication.getName()` al servizio. Il servizio recupera
l'utente e sceglie tra la query globale per `ADMIN` e una query dedicata alla
partecipazione per `USER`. Non viene effettuato alcun filtraggio di sicurezza nel
browser.

Anche `GET /api/leagues/{id}` deve rispettare la stessa regola: l'admin globale può
aprire qualsiasi lega, mentre un utente normale può aprire soltanto una lega creata da
lui o alla quale partecipa. Questo impedisce di aggirare il filtro dell'elenco digitando
direttamente l'URL della pagina di dettaglio.

## Cancellazione delle leghe

Il comportamento backend esistente viene conservato e coperto da test:

- l'admin globale può cancellare qualsiasi lega;
- il creatore può cancellare la propria lega;
- gli altri utenti ricevono un errore di autorizzazione.

Ogni scheda lega cancellabile mostra un pulsante `Elimina`. Per l'admin globale il
pulsante è presente su tutte le schede; per un utente normale è presente soltanto sulle
leghe che ha creato. Il pulsante non è annidato nel link che apre la lega, per evitare
markup interattivo non valido e navigazioni accidentali.

Prima della richiesta `DELETE /api/leagues/{id}` viene richiesta una conferma che cita
il nome della lega. Dopo una risposta positiva, la UI mostra un messaggio e ricarica
l'elenco. In caso di errore conserva la scheda e mostra il messaggio restituito
dall'API.

## Directory utenti con `Ctrl+Y`

`GET /api/users` resta accessibile esclusivamente a `ROLE_ADMIN`. La risposta contiene
tutti e soli gli account con ruolo `USER`, ordinati alfabeticamente per username. Ogni
elemento espone esattamente:

```json
{
  "username": "summoner",
  "email": "summoner@example.com"
}
```

ID, password, hash, ruolo, profilo e altre proprietà non vengono serializzati. L'email
è visibile perché richiesta esplicitamente per la directory amministrativa.

Il frontend intercetta `Ctrl+Y` tramite `KeyboardEvent.code === "KeyY"`, con fallback
su `event.key`, così la scorciatoia non dipende dal layout della tastiera. La apre solo
quando il token esiste, il ruolo della sessione è `ADMIN`, non sono premuti `Alt` o
`Meta` e il focus non si trova in `input`, `textarea`, `select` o un elemento
content-editable. In tal caso impedisce l'azione predefinita del browser, carica dati
aggiornati e mostra username ed email nel dialog.

Per rendere diagnosticabili sessioni obsolete, dopo il login il ruolo continua a
essere salvato dalla risposta autenticata. Gli errori `401` invalidano la sessione;
gli altri errori della directory producono un messaggio visibile. Il dialog gestisce
anche caricamento e lista vuota. La build Maven continua a incorporare
`fantalol-frontend` sotto `static`, e un test verifica che il JavaScript servito contenga
la scorciatoia aggiornata.

## Ordine della pagina principale

La navigazione principale diventa:

1. Home
2. Le mie leghe
3. Players

Le sezioni nel DOM seguono lo stesso ordine: hero, leghe, giocatori. Anche il link
principale della hero che invita a esplorare i player continua a puntare a `#players`.
Non sono previsti altri cambiamenti grafici o testuali alla home oltre a quelli
necessari per i pulsanti di cancellazione e per la directory utenti.

## README generale

`fantalol-backend/README.md` viene rimosso e il contenuto utile confluisce in
`README.md` nella root `/home/massimilianofabbo/FantaLol`. Soltanto questo file è
richiesto interamente in italiano; la richiesta non implica la traduzione di sorgenti,
nomi tecnici o altri documenti.

Il README generale descrive:

- cos'è FantaLeague e quali problemi risolve;
- funzionalità per visitatori, utenti, creatori di lega e admin globale;
- registrazione, login, creazione/adesione alle leghe, asta, rosa, formazione,
  giornate e punteggi;
- comportamento di `Ctrl+Y` e gestione amministrativa delle leghe;
- architettura frontend/backend, tecnologie e struttura delle cartelle;
- prerequisiti e avvio con Docker Compose;
- avvio locale, variabili d'ambiente e URL principali;
- esecuzione dei test, Swagger e collection Postman;
- note di sicurezza, integrazioni e provenienza dei dati.

Le credenziali dell'account amministratore non vengono inserite nel README. La
documentazione spiega invece come configurarle tramite le variabili già supportate
dall'applicazione.

## Gestione errori e sicurezza

- Le richieste senza autenticazione ricevono `401`.
- Un utente autenticato ma non autorizzato riceve `403` o l'errore applicativo già
  normalizzato dal progetto, senza divulgare dati della lega.
- La directory non restituisce account amministrativi né proprietà non previste.
- Username, email e nomi delle leghe vengono inseriti nel DOM tramite escaping.
- La cancellazione non viene eseguita senza conferma esplicita nel browser.
- Le relazioni JPA esistenti gestiscono la rimozione dei dati dipendenti secondo le
  regole già definite dal modello; non vengono introdotte cancellazioni massive.

## Strategia di test

I test backend verificano:

- l'admin vede tutte le leghe;
- un utente vede le leghe create e quelle partecipate, senza duplicati;
- un utente non vede e non apre leghe estranee;
- admin e creatore possono cancellare, un estraneo non può;
- la directory è vietata a visitatori e utenti normali;
- la directory esclude gli admin, ordina gli utenti e restituisce soltanto username ed
  email.

I controlli frontend verificano:

- ordine dei link e delle sezioni `Home → Le mie leghe → Players`;
- presenza della conferma e della richiesta DELETE;
- rendering condizionale del comando `Elimina`;
- riconoscimento di `Ctrl+Y` tramite codice tasto e rispetto dei campi editabili;
- rendering escaped di username ed email;
- inclusione dei file frontend aggiornati nelle risorse statiche generate da Maven.

## Criteri di accettazione

- L'admin globale vede e può eliminare qualsiasi lega dal sito.
- Un utente normale vede soltanto le leghe create o partecipate e non può accedere a
  una lega estranea tramite URL diretto.
- `Ctrl+Y` apre per l'admin una lista funzionante degli account normali con username ed
  email; non ha effetto per utenti normali o durante la digitazione.
- La home e il menu presentano nell'ordine Home, Le mie leghe, Players.
- Esiste un solo README principale nella root, completo e scritto in italiano; il
  precedente README del backend non esiste più.
- Tutti i test automatici pertinenti terminano con successo.
