# FantaLeague

FantaLeague è un'applicazione web fantasy dedicata alla **LEC**, il campionato EMEA
di League of Legends. Gli utenti possono creare leghe private, invitare altri
partecipanti, acquistare i giocatori professionisti tramite un'asta a crediti,
comporre la propria rosa e competere in una classifica basata sulle prestazioni
reali dei player.

## Cosa può fare un utente

Un visitatore può consultare giocatori e squadre LEC, leggere il regolamento,
registrarsi e accedere al sito.

Dopo l'accesso, un utente con ruolo `USER` può:

- creare una lega privata e condividerne il codice di invito;
- entrare nelle leghe create da altri utenti;
- creare un solo FantaTeam per ogni lega;
- partecipare all'asta e rilanciare usando i crediti disponibili;
- consultare budget, rosa e giocatori ancora acquistabili;
- scegliere un titolare per ciascun ruolo quando la lega prevede le riserve;
- seguire partite LEC, prestazioni dei player, fantapunteggi e classifica;
- modificare i dati del proprio profilo;
- eliminare una lega della quale è il creatore.

Il creatore della lega ne diventa l'amministratore locale e può aprire o chiudere
l'asta, completare casualmente le rose incomplete, gestire le giornate ed eliminare
la propria lega.

## Cosa può fare un amministratore

All'avvio dell'applicazione viene inizializzato un account con ruolo `ADMIN`.
Le sue credenziali sono definite dal backend e non devono essere pubblicate nel
repository.

L'amministratore globale può:

- vedere, aprire ed eliminare qualsiasi lega;
- gestire squadre e giocatori LEC;
- controllare le giornate e le operazioni amministrative protette;
- avviare manualmente la sincronizzazione dei dati LEC;
- verificare lo stato delle integrazioni PandaScore e Oracle's Elixir;
- consultare la directory degli utenti normali registrati, con username ed email,
  usando `Ctrl+Y` fuori dai campi di scrittura.

Password, hash e account amministrativi non vengono mostrati nella directory.

## Come funziona il sito

### 1. Creazione della lega

Un utente autenticato crea una lega scegliendo il nome. Il sistema assegna
all'utente il ruolo di amministratore della lega e genera un codice di invito
univoco. Gli altri partecipanti usano quel codice per entrare e dare un nome al
proprio FantaTeam.

Ogni utente può possedere un solo FantaTeam nella stessa lega. All'avvio della
competizione viene congelato il numero dei partecipanti, dal quale dipende anche
la dimensione delle rose.

### 2. Asta

L'amministratore della lega apre l'asta. Ogni partecipante dispone inizialmente di
crediti virtuali e può fare offerte sui player LEC nel rispetto del budget residuo
e della quotazione minima.

Ogni rilancio riavvia il conto alla rovescia. Alla scadenza, il miglior offerente
acquista il giocatore. Lo stesso player non può appartenere a due FantaTeam della
medesima lega. L'amministratore può chiudere l'asta quando le rose sono complete
oppure completare casualmente quelle rimaste incomplete.

### 3. Rosa e formazione

La rosa deve coprire i cinque ruoli di League of Legends: `TOP`, `JUNGLE`, `MID`,
`ADC` e `SUPPORT`.

- con 2-5 partecipanti, ogni FantaTeam possiede 10 giocatori, due per ruolo, e
  sceglie cinque titolari;
- con 6-10 partecipanti, ogni FantaTeam possiede 5 giocatori, uno per ruolo, che
  formano la squadra attiva.

Nelle leghe con riserve, la formazione può essere modificata da martedì 00:00 a
giovedì 23:59:59 nel fuso `Europe/Rome`. Il cambio diventa effettivo il venerdì
alle 00:00 e non altera i punti già maturati: il backend conserva infatti lo
storico dei periodi nei quali ciascun player è stato titolare.

### 4. Punteggi e classifica

PandaScore fornisce calendario, stato e risultati delle serie LEC; Oracle's Elixir
fornisce le statistiche delle singole partite. Il backend importa i dati senza
duplicare i game già elaborati e calcola i fantapunti usando uccisioni, assist,
morti, CS, vision score e vittorie.

```text
fantapunti = uccisioni × K(ruolo)
            + assist × A(ruolo)
            - morti × D(ruolo)
            + risorsa(ruolo)
            + 3 punti in caso di vittoria
```

Per `TOP`, `JUNGLE`, `MID` e `ADC` la risorsa dipende dai CS; per `SUPPORT`
dipende dal vision score. I coefficienti sono specifici per ruolo.

La prestazione di un player è la media cumulativa delle partite effettivamente
giocate nella Summer Split. Il punteggio del FantaTeam è la media dei cinque slot
di ruolo, calcolata usando il player che era titolare al momento di ogni partita.
I risultati alimentano la classifica cumulativa della lega e rimangono provvisori
quando i dati della fonte non sono ancora completi.

## Architettura

FantaLeague usa un'architettura client-server composta da un backend REST, un
frontend statico e un database relazionale:

```text
Browser
   │
   │ HTML, CSS, JavaScript / richieste REST con JWT
   ▼
Spring Boot
   ├── autenticazione e utenti
   ├── leghe, aste e rose
   ├── formazioni, giornate e punteggi
   └── integrazioni PandaScore e Oracle's Elixir
   │
   ▼
MySQL
```

Durante la build Maven copia il frontend nelle risorse statiche di Spring Boot.
L'intera applicazione viene quindi servita dalla stessa porta, senza dover avviare
separatamente un server frontend.

### Backend

Il backend è sviluppato con:

- Java 17 e Spring Boot 3.3;
- Spring Web MVC per le API REST;
- Spring Data JPA e MySQL 8 per la persistenza;
- Spring Security, BCrypt e JWT stateless per autenticazione e autorizzazione;
- springdoc-openapi per documentazione OpenAPI e Swagger UI;
- JUnit 5, Mockito, AssertJ, H2 e JaCoCo per test e copertura.

I package principali sono:

```text
com.fantalol.backend
├── common/       gestione centralizzata degli errori API
├── config/       sicurezza, configurazione e dati iniziali
├── integration/  sincronizzazione PandaScore e Oracle's Elixir
├── league/       leghe, FantaTeam, aste e rose
├── lineup/       finestre e storico delle formazioni effettive
├── matchday/     giornate, statistiche e formazioni
├── scoring/      formula, punteggi cumulativi e classifiche
├── security/     filtro e utilità JWT
├── team/         squadre e giocatori LEC
└── user/         registrazione, login, profilo e ruoli
```

Le API sono disponibili sotto `/api`. Le operazioni protette richiedono
l'header `Authorization: Bearer TOKEN`.

### Frontend

Il frontend è sviluppato senza framework, usando:

- HTML5 per homepage e dettaglio della lega;
- CSS modulare e responsive;
- JavaScript per autenticazione, chiamate REST, asta, rosa, formazione, dati live
  e classifica;
- asset locali per loghi, player e champion.

La struttura principale del repository è:

```text
FantaLol/
├── fantalol-backend/
│   ├── src/main/java/       codice backend
│   ├── src/main/resources/  configurazione
│   ├── postman/             collection delle API
│   ├── sql/                 script SQL di supporto
│   ├── Dockerfile
│   └── docker-compose.yml
├── fantalol-frontend/
│   ├── assets/              loghi delle squadre
│   ├── Player_immage/       immagini di player e champion
│   ├── css/                 fogli di stile
│   ├── js/                  logica frontend
│   ├── index.html
│   └── lega.html
├── Rules.md
└── README.md
```

## Avvio con Docker Compose

Sono richiesti Docker e Docker Compose. Dalla root del repository eseguire:

```bash
docker compose -f fantalol-backend/docker-compose.yml up --build
```

Docker Compose avvia:

- MySQL 8 sulla porta host `3307`;
- backend e frontend sulla porta `8080`.

Una volta completato l'avvio, il sito è disponibile all'indirizzo:

**[http://localhost:8080](http://localhost:8080)**

Swagger UI è disponibile su
**[http://localhost:8080/swagger-ui.html](http://localhost:8080/swagger-ui.html)**.

Per arrestare i container:

```bash
docker compose -f fantalol-backend/docker-compose.yml down
```

Il volume Docker `fantalol_mysql_data` conserva il database tra un avvio e
l'altro. I valori presenti nel file Compose sono adatti allo sviluppo: prima di
una distribuzione pubblica devono essere sostituiti con password e segreti sicuri.

## Link del progetto

Il codice sorgente e la pagina pubblica del progetto sono disponibili su GitHub:

**[github.com/FabboITS/FantaLol](https://github.com/FabboITS/FantaLol)**

Al momento il repository non dichiara un deployment pubblico separato; avviando
Docker Compose, l'applicazione completa è raggiungibile su
**[http://localhost:8080](http://localhost:8080)**.
