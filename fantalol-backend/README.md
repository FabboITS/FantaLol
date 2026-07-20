# Fanta LoL - Backend

Backend Java per il project work finale **UF14 - Java Backend**.

Il progetto implementa un "Fanta Calcio" applicato al competitivo di **League of Legends**,
limitato ai 10 team della **LEC** (League of Legends EMEA Championship):
Team Vitality, Karmine Corp, G2 Esports, Movistar KOI, Natus Vincere, GIANTX, Fnatic,
SK Gaming, Shifters, Team Heretics.

## Stack tecnologico

- Java 17, Spring Boot 3.3 (Spring Web MVC, Spring Data JPA, Spring Security)
- MySQL 8.0
- JWT (jjwt) per l'autenticazione stateless
- Maven
- JUnit 5, Mockito, AssertJ, JaCoCo (coverage)
- Docker / Docker Compose
- springdoc-openapi (Swagger UI)

## Struttura del progetto (moduli funzionali)

```
com.fantalol.backend
├── config      → SecurityConfig, DataSeeder
├── security    → JwtUtil, JwtAuthFilter, CustomUserDetailsService
├── common      → eccezioni custom, GlobalExceptionHandler, ApiError
├── user        → modulo Utenti (obbligatorio): User, UserProfile, Auth
├── team        → modulo Team/Player LEC: LecTeam, LecPlayer
├── league      → modulo Leghe/Asta/Rose: League, FantaTeam, RosterEntry
└── matchday    → modulo Giornate/Statistiche/Formazioni: Matchday, PlayerStat, Formation
```

Ogni modulo ha i propri Controller, Service, Repository e DTO, secondo l'architettura MVC
richiesta dalla traccia.

## Avvio rapido con Docker (consigliato)

Richiede solo Docker e Docker Compose installati.

```bash
docker compose up --build
```

Questo comando avvia:
- un container MySQL 8.0 (porta host **3307** → porta container 3306, per evitare conflitti con installazioni MySQL locali)
- il backend Spring Boot (porta 8080)

Al primo avvio, l'applicazione popola automaticamente il database (tramite `DataSeeder`)
con i 10 team LEC, i roster reali e un utente amministratore.

L'API sarà disponibile su **http://localhost:8080**.
Frontend web: **http://localhost:8080/**
Swagger UI: **http://localhost:8080/swagger-ui.html**

## Avvio in locale (senza Docker)

Prerequisiti: Java 17, Maven 3.9+, un'istanza MySQL 8.0 raggiungibile.

1. Creare il database (opzionale, l'app lo crea da sola se non esiste):
   ```bash
   mysql -u root -p < sql/schema.sql
   mysql -u root -p < sql/data-seed.sql   # popolamento dati (opzionale, l'app lo fa comunque)
   ```

2. Impostare le variabili d'ambiente (o modificare `application.yml`):
   ```
   DB_HOST=localhost
   DB_PORT=3306
   DB_NAME=fantalol
   DB_USER=fantalol
   DB_PASSWORD=fantalol
   ```

3. Avviare l'applicazione:
   ```bash
   mvn spring-boot:run
   ```

## Account amministratore

Il `DataSeeder` crea l'account amministratore senza pubblicarne le credenziali
nell'interfaccia, nella documentazione o negli esempi API. Lo script SQL standalone
crea soltanto tale account e una lega demo con codice invito `DEMO1234`.

## Esecuzione dei test e coverage

```bash
mvn clean test
```

Il report di coverage JaCoCo viene generato in `target/site/jacoco/index.html`.

## Collection Postman

Importare `postman/FantaLoL-Backend.postman_collection.json` in Postman.
La collection include script automatici che salvano il token JWT ottenuto dal login
nelle variabili di collection (`token` per utente standard, `adminToken` per l'admin).

## Frontend

Il progetto include un frontend responsive in HTML, CSS e JavaScript vanilla, servito
direttamente da Spring Boot da `src/main/resources/static`. Non richiede Node.js né un
server separato. Consente di esplorare team e player, registrarsi/accedere con JWT,
creare o raggiungere leghe e consultare le proprie rose.

## Sicurezza e ruoli

- **Pubblici**: registrazione/login, consultazione (GET) di team/player LEC e giornate/statistiche
- **Autenticati (ROLE_USER)**: gestione profilo, creazione/iscrizione a leghe, asta, formazioni;
  il creatore di una lega ne diventa admin e può aprire/chiudere le relative giornate
- **Riservati (ROLE_ADMIN)**: gestione anagrafica LEC (POST/PUT/DELETE), creazione giornate,
  inserimento statistiche, chiusura giornata

## Logica di dominio principale

- **Asta live a crediti**: ogni FantaTeam riceve un budget prefissato (1000 crediti virtuali
  di default). Un'asta parte dalla quotazione base del player; ogni rilancio riavvia un timer
  server-side di 10 secondi e allo scadere il player viene assegnato al miglior offerente.
  Chi avvia l'asta effettua automaticamente l'offerta iniziale, quindi vince al prezzo base
  se nessun altro partecipante rilancia.
  Quando una squadra non può più permettersi alcun player idoneo, i posti mancanti vengono
  completati casualmente e gratuitamente rispettando esattamente 2 player per ruolo.
- **Amministrazione lega**: il creatore può aprire le giornate o cancellare la propria lega;
  l'utente ADMIN globale può amministrare tutte le leghe.
- **Fantavoto**: calcolato da `FantaScoreCalculator` a partire dal voto base (inserito
  dall'admin) più bonus/malus su kill, assist, morti, MVP e vittoria.
- **Rosa e formazione**: ogni FantaTeam acquista fino a 10 player (massimo 2 per ruolo),
  quindi schiera per ogni giornata 5 titolari, uno per ruolo; gli altri 5 restano in panchina
  e possono sostituire i titolari nelle giornate successive. Il capitano
  raddoppia il proprio fantavoto nel punteggio finale della formazione.
