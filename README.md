# FantaLeague

FantaLeague è un'applicazione web fantasy dedicata al League of Legends
professionistico — **LEC**, **LPL** e **LCK** — con in più una modalità dedicata ai
**Worlds**. Gli utenti possono creare leghe private, invitare altri partecipanti,
acquistare i giocatori professionisti tramite un'asta a crediti, comporre la
propria rosa e competere in una classifica basata sulle prestazioni reali dei
player.

> **Stato della migrazione.** Il backend è stato riscritto in **Python 3.12 /
> Django 5** dentro [`fantalol-django/`](fantalol-django/): stesse regole di gioco,
> stessi contratti REST, più la modalità Worlds e una pipeline dati basata su
> **PandaScore + Leaguepedia** al posto dei CSV di Oracle's Elixir. Il backend Java
> in [`fantalol-backend/`](fantalol-backend/) resta nel repository come riferimento
> finché la migrazione non è validata in produzione. Il dettaglio completo del
> nuovo backend è in [`fantalol-django/README.md`](fantalol-django/README.md).

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
- avviare manualmente la sincronizzazione dei dati pro;
- verificare lo stato delle integrazioni PandaScore e Leaguepedia;
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

PandaScore fornisce calendario, stato e risultati delle serie; Leaguepedia
fornisce i box score delle singole partite. Il backend importa i dati senza
duplicare i game già elaborati e calcola i fantapunti usando uccisioni, assist,
morti, CS, vision score e vittorie. I dati Leaguepedia sono distribuiti con
licenza **CC BY-SA 3.0** e ogni risposta API che li espone include la relativa
attribuzione.

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

### 5. Modalità Worlds

Accanto alle leghe stagionali c'è un formato **event-based** legato al mondiale,
in stile Fantacalcio Champions League. Il player pool è l'unione dei roster
qualificati, quindi non è vincolato a un singolo campionato; la "giornata" è la
**fase del torneo** (Play-In, gironi/Swiss, Quarti, Semifinali, Finale) e la
formazione va confermata prima dell'inizio di ciascuna fase. Budget e taglia rosa
sono configurabili per edizione, la classifica è separata da quelle stagionali e
prevede bonus per l'MVP di serie, per l'avanzamento di fase e per le serie vinte.

Regolamento e parametri sono descritti in
[`fantalol-django/README.md`](fantalol-django/README.md#modalità-worlds).

## Architettura

FantaLeague usa un'architettura client-server composta da un backend REST, un
frontend statico e un database relazionale:

```text
Browser
   │
   │ HTML, CSS, JavaScript / richieste REST con JWT
   ▼
Django + DRF (porta 8080)
   ├── autenticazione e utenti
   ├── leghe, aste e rose
   ├── formazioni, giornate e punteggi
   ├── modalità Worlds
   └── ingest PandaScore + Leaguepedia
   │         ▲
   │         │ task periodici
   │      Celery + Celery Beat ── Redis
   ▼
PostgreSQL
```

Nessuna richiesta del browser raggiunge mai un provider esterno: il frontend
legge solo dal database, attraverso le API REST di FantaLoL.

### Backend

Il backend è sviluppato con:

- Python 3.12 e Django 5;
- Django REST Framework per le API REST;
- PostgreSQL 16 per la persistenza;
- `djangorestframework-simplejwt`, BCrypt e JWT stateless per autenticazione e
  autorizzazione;
- Celery e Celery Beat (broker Redis) per sincronizzazioni e job periodici;
- drf-spectacular per documentazione OpenAPI e Swagger UI;
- pytest, pytest-django, factory_boy e coverage.py per test e copertura.

Le app principali sono:

```text
fantalol-django/
├── config/     settings, urls, Celery
├── core/       gestione centralizzata degli errori API, permessi, CORS
├── accounts/   registrazione, login, profilo e ruoli
├── teams/      squadre e giocatori pro (LEC/LPL/LCK e regioni Worlds)
├── leagues/    leghe, FantaTeam, aste e rose
├── lineups/    finestre e storico delle formazioni effettive
├── matchdays/  giornate, statistiche e formazioni
├── scoring/    formula, punteggi cumulativi e classifiche
├── ingest/     sincronizzazione PandaScore e Leaguepedia
└── worlds/     modalità Worlds
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
├── fantalol-django/                backend Django (attivo)
│   ├── config/ accounts/ core/     configurazione, utenti, utilità comuni
│   ├── teams/ leagues/ lineups/    squadre pro, leghe, formazioni
│   ├── matchdays/ scoring/         giornate, punteggi e classifiche
│   ├── ingest/ worlds/             pipeline dati e modalità Worlds
│   ├── tests/                      suite pytest
│   ├── requirements/
│   ├── Dockerfile
│   └── docker-compose.yml
├── fantalol-backend/               backend Java/Spring (riferimento storico)
├── fantalol-frontend/
│   ├── assets/                     loghi delle squadre
│   ├── Player_immage/              immagini di player e champion
│   ├── css/                        fogli di stile
│   ├── js/                         logica frontend
│   ├── index.html
│   └── lega.html
├── fantalol-frontend-placeholder/  frontend minimale di collaudo del backend
├── Rules.md
└── README.md
```

## Avvio con Docker Compose

Sono richiesti Docker e Docker Compose. Dalla root del repository eseguire:

```bash
cp fantalol-django/.env.example fantalol-django/.env
docker compose -f fantalol-django/docker-compose.yml up --build
```

Docker Compose avvia:

- PostgreSQL 16 e Redis;
- il backend Django sulla porta `8080`;
- un worker Celery e lo scheduler Celery Beat per sincronizzazioni e job periodici.

Una volta completato l'avvio, le API sono disponibili all'indirizzo:

**[http://localhost:8080/api/](http://localhost:8080/api/)**

Swagger UI è disponibile su
**[http://localhost:8080/api/docs/](http://localhost:8080/api/docs/)**.

Per arrestare i container:

```bash
docker compose -f fantalol-django/docker-compose.yml down
```

Il volume Docker `pgdata` conserva il database tra un avvio e l'altro. I valori
presenti in `.env.example` sono adatti allo sviluppo: prima di una distribuzione
pubblica devono essere sostituiti con password e segreti sicuri.

## Link del progetto

Il progetto è in fase di sviluppo e online sul sito qui presente:

**[FantaLol](https://fantalol.win)**
