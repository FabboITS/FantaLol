# FantaLeague

FantaLeague è un'applicazione web fantasy dedicata alla LEC, il campionato EMEA di
League of Legends. Permette di creare leghe private, invitare altri partecipanti,
costruire una rosa tramite asta a crediti, schierare una formazione e ottenere punti
dalle prestazioni reali dei giocatori professionisti.

Il repository contiene un backend Spring Boot e un frontend statico in HTML, CSS e
JavaScript. Il frontend viene incorporato nel file eseguibile del backend durante la
build, quindi l'applicazione completa è disponibile da un unico server.

## Funzionalità e ruoli

### Visitatori

Senza autenticazione è possibile:

- aprire la pagina principale;
- consultare giocatori e squadre LEC;
- leggere il regolamento;
- registrare un nuovo account o accedere.

### Utenti registrati

Un account con ruolo `USER` può:

- creare una lega privata;
- entrare in una lega usando il codice di invito;
- vedere soltanto le leghe create personalmente o alle quali partecipa;
- gestire un FantaTeam per lega;
- partecipare all'asta, consultare la rosa e schierare la formazione;
- seguire giornate, punteggi e classifica.

Il creatore della lega ne è anche l'amministratore locale. Può gestirne le fasi e
cancellare la propria lega, ma non può amministrare leghe estranee.

### Amministratore globale

L'applicazione inizializza un account con ruolo `ADMIN` all'avvio. Le credenziali non
sono pubblicate in questo documento e devono essere gestite in modo sicuro nella
configurazione dell'ambiente.

L'amministratore globale può:

- vedere e aprire tutte le leghe presenti nel sito;
- cancellare qualsiasi lega;
- gestire l'anagrafica LEC e le operazioni amministrative protette;
- premere `Ctrl+Y` fuori dai campi di scrittura per aprire la directory degli account
  normali registrati, con username ed email.

La directory non mostra account amministrativi, password, hash, profili o identificativi
interni.

## Come funziona una lega

1. Un utente autenticato crea una lega, scegliendo nome e crediti iniziali.
2. Il sistema genera un codice di invito univoco.
3. Gli altri utenti entrano con quel codice e assegnano un nome al proprio FantaTeam.
4. La creazione della prima giornata congela il numero dei partecipanti e apre l'asta.
5. I partecipanti acquistano giocatori rispettando budget, dimensione della rosa e
   limiti per ruolo.
6. Dopo la chiusura dell'asta viene definita la formazione valida per la giornata.
7. Le statistiche reali vengono importate, trasformate in fantapunti e sommate nella
   classifica generale.

Ogni utente può possedere al massimo un FantaTeam nella stessa lega. Un giocatore LEC
non può appartenere contemporaneamente a due FantaTeam della medesima lega.

## Asta, rosa e formazione

L'asta usa crediti virtuali. Un'offerta valida deve rispettare la quotazione minima del
giocatore e il budget residuo. Ogni rilancio riavvia il conto alla rovescia; alla
scadenza, il miglior offerente ottiene il giocatore.

La composizione dipende dal numero di partecipanti congelato all'avvio della
competizione:

- nelle leghe da 2 a 5 partecipanti, ogni rosa contiene 10 giocatori, 2 per ruolo;
- nelle leghe da 6 a 10 partecipanti, ogni rosa contiene 5 giocatori, 1 per ruolo.

Nelle leghe piccole il proprietario sceglie un titolare per ogni ruolo. Può salvare
un cambio da martedì 00:00 a giovedì 23:59:59 nel fuso `Europe/Rome`; il cambio
diventa efficace il venerdì alle 00:00 e non modifica i punti già acquisiti. Le
riserve ricevono una valutazione individuale, ma solo i cinque titolari contribuiscono
al risultato. Nelle leghe con più di cinque fantasy team i cinque componenti della
rosa formano una squadra attiva fissa e non modificabile.

## Giornate e punteggi

Le statistiche importate includono uccisioni, morti, assist, minion eliminati e
risultato della partita. Dalla Summer 2026 il punteggio viene calcolato per
singola partita con coefficienti specifici per ruolo:

```text
fantapunti = uccisioni × K(ruolo)
            + assist × A(ruolo)
            - morti × D(ruolo)
            + risorsa(ruolo)
            + 3 in caso di vittoria
```

Per Top, Jungle, Mid e ADC la risorsa è `(CS / 100) × C(ruolo)`. I
coefficienti K/A/D/C sono: Top 3,00/2,00/2,00/1,25; Jungle
3,00/2,25/2,00/0,70; Mid 3,00/2,00/2,00/1,00; ADC
3,25/1,75/2,25/1,10. Per i Support K/A/D sono 2,15/2,55/1,75 e la risorsa
è `vision score / 50`: ricevono 1 punto ogni 50 di vision score e i loro CS
non assegnano punti. CS e vision score sono continui.

La prestazione di un player è la media cumulativa delle sole partite effettivamente
disputate nella Summer Split. Una partita non giocata non aggiunge uno zero. Ogni
slot di ruolo conserva le osservazioni ottenute dal player che era attivo al momento
della partita; il punteggio del FantaTeam è la media dei cinque slot. Se uno slot non
ha ancora osservazioni, il totale resta provvisorio e non viene pubblicato come zero.

## Architettura e tecnologie

Il backend usa:

- Java 17;
- Spring Boot 3.3;
- Spring Web MVC;
- Spring Data JPA;
- Spring Security con JWT stateless;
- MySQL 8;
- Maven;
- springdoc-openapi e Swagger UI;
- JUnit 5, Mockito, AssertJ, H2 e JaCoCo per i test.

Il frontend usa HTML5, CSS e JavaScript senza framework. Maven copia la cartella
`fantalol-frontend` nelle risorse statiche del backend durante la build.

La struttura principale è:

```text
FantaLol/
├── fantalol-backend/
│   ├── src/main/java/com/fantalol/backend/
│   │   ├── common/       eccezioni e risposte API
│   │   ├── config/       sicurezza, dati iniziali e account admin
│   │   ├── integration/  PandaScore e Oracle's Elixir
│   │   ├── league/       leghe, aste, squadre e rose
│   │   ├── matchday/     giornate, statistiche e formazioni
│   │   ├── security/     JWT e autenticazione
│   │   └── team/         squadre e giocatori LEC
│   ├── postman/          collection per provare le API
│   ├── sql/              schema e dati SQL di supporto
│   └── docker-compose.yml
├── fantalol-frontend/
│   ├── assets/           loghi delle squadre
│   ├── Player_immage/    immagini dei giocatori
│   ├── css/              fogli di stile
│   ├── js/               applicazione e pagina della lega
│   ├── index.html        pagina principale
│   └── lega.html         dettaglio della lega
└── README.md
```

## Avvio con Docker Compose

Sono richiesti Docker e Docker Compose. Dalla root del repository eseguire:

```bash
docker compose -f fantalol-backend/docker-compose.yml up --build
```

Vengono avviati:

- MySQL sulla porta host `3307`;
- l'applicazione completa sulla porta `8080`.

Per arrestare i container:

```bash
docker compose -f fantalol-backend/docker-compose.yml down
```

Il volume `fantalol_mysql_data` conserva i dati tra un avvio e l'altro.

## Avvio locale

Prerequisiti:

- JDK 17;
- Maven 3.9 o successivo;
- MySQL 8 raggiungibile;
- le variabili d'ambiente descritte nella sezione successiva.

Dalla cartella del backend:

```bash
cd fantalol-backend
mvn spring-boot:run
```

Indirizzi principali:

- applicazione: `http://localhost:8080/`;
- pagina di una lega: `http://localhost:8080/lega.html?id=ID_LEGA`;
- Swagger UI: `http://localhost:8080/swagger-ui.html`;
- specifica OpenAPI: `http://localhost:8080/v3/api-docs`;
- controllo di salute: `http://localhost:8080/actuator/health`.

## Configurazione

Il backend legge queste variabili:

| Variabile | Descrizione | Valore predefinito |
|---|---|---|
| `PORT` | Porta HTTP | `8080` |
| `DB_HOST` | Host MySQL | obbligatorio |
| `DB_PORT` | Porta MySQL | obbligatorio |
| `DB_NAME` | Nome del database | obbligatorio |
| `DB_USER` | Utente del database | obbligatorio |
| `DB_PASSWORD` | Password del database | obbligatorio |
| `JWT_SECRET` | Segreto Base64 per firmare i token | obbligatorio |
| `JWT_EXPIRATION_MS` | Durata del token in millisecondi | `86400000` |
| `PANDASCORE_BASE_URL` | URL base PandaScore | `https://api.pandascore.co` |
| `PANDASCORE_API_TOKEN` | Token privato PandaScore | vuoto |
| `LEC_TOURNAMENT_ID` | Tournament ID PandaScore sincronizzato | `21344` |
| `LEC_LEAGUE` | Filtro lega Oracle's Elixir | `LEC` |
| `LEC_SPLIT` | Filtro split Oracle's Elixir | `Summer` |
| `LEC_TIMEZONE` | Fuso usato per la finestra formazione e l'efficacia del venerdì | `Europe/Rome` |
| `LEC_BACKFILL_FROM` | Inizio iniziale delle formazioni effettive per il backfill idempotente | `2026-07-24T00:00:00+02:00` |
| `ORACLE_ELIXIR_CSV_URL` | URL del CSV annuale Oracle's Elixir | vuoto |
| `LEC_SYNC_CRON` | Espressione cron Spring della sincronizzazione | `0 15 */6 * * *` |

In produzione bisogna usare password robuste, un segreto JWT casuale e sufficientemente
lungo e un token PandaScore mantenuto esclusivamente sul server. Nessun segreto deve
essere inserito nei file JavaScript del frontend.

## API e Swagger

Le API REST sono esposte sotto `/api`. Registrazione, login e consultazione pubblica
dell'anagrafica LEC non richiedono un token. Le operazioni su leghe, aste, rose e
formazioni richiedono `Authorization: Bearer TOKEN`. Le operazioni globali sotto
`/api/admin` e la directory `/api/users` richiedono il ruolo `ADMIN`.

Swagger UI permette di consultare e provare il contratto delle API. È inoltre
disponibile la collection:

```text
fantalol-backend/postman/FantaLoL-Backend.postman_collection.json
```

## Test e copertura

Dalla cartella `fantalol-backend` eseguire:

```bash
mvn clean test
```

I test usano un database H2 isolato. Il report JaCoCo viene generato in:

```text
fantalol-backend/target/site/jacoco/index.html
```

Per controllare soltanto la sintassi del frontend:

```bash
node --check fantalol-frontend/js/app.js
node --check fantalol-frontend/js/league-detail.js
```

## Integrazioni e dati

PandaScore fornisce calendario, stato delle partite e risultato delle serie. Il CSV
annuale di Oracle's Elixir fornisce le statistiche per partita usate nel calcolo
fantasy. Ogni sincronizzazione filtra `LEC`, `Summer`, righe complete e ruoli player,
quindi salva durevolmente ogni `gameid`: il CSV non viene assegnato in blocco a una
giornata e una nuova esecuzione non duplica le partite già importate.

La sincronizzazione automatica usa `LEC_SYNC_CRON` (ogni sei ore con il valore
predefinito). L'ADMIN globale può eseguire `Sincronizza ora`: l'operazione ritenta
entrambi i provider e il ricalcolo, ma non può creare statistiche che la fonte non ha
pubblicato in forma completa. Per il primo avvio della Summer 2026, le formazioni
valide correnti vengono retrodatate in modo idempotente al
`LEC_BACKFILL_FROM`, per impostazione predefinita
`2026-07-24T00:00:00+02:00`. Il fuso `LEC_TIMEZONE` (predefinito
`Europe/Rome`) governa la finestra settimanale e l'efficacia del venerdì. Il
backfill crea soltanto i periodi effettivi iniziali mancanti: dopo che una
squadra possiede già dei periodi, cambiare `LEC_BACKFILL_FROM` non riscrive né
retrodata nuovamente lo storico esistente.

Gli endpoint di importazione e verifica del fornitore sono riservati all'amministratore
globale. I dettagli operativi sono disponibili in
`fantalol-backend/INTEGRATIONS.md`.

## Sicurezza

- Le password sono memorizzate mediante hash BCrypt.
- I token JWT sono firmati e il backend non mantiene sessioni HTTP.
- La visibilità delle leghe viene filtrata sul server, non soltanto nell'interfaccia.
- Solo il creatore o l'admin globale possono cancellare una lega.
- Solo l'admin globale può consultare username ed email degli account normali.
- Le risposte dedicate evitano di serializzare entità contenenti credenziali o dati non
  necessari.
- Le chiavi e i token delle integrazioni devono rimanere variabili d'ambiente private.

Prima di distribuire l'applicazione è necessario sostituire ogni valore dimostrativo
presente nella configurazione Docker con segreti specifici dell'ambiente di produzione.
