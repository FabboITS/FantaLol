# FantaLoL — backend Django

Backend del fantasy game **FantaLoL**, scritto in **Python 3.12 / Django 5 /
Django REST Framework**. Sostituisce integralmente il precedente backend
Java 17 / Spring Boot 3.3, che è stato rimosso dal repository.

Tre cose cambiano rispetto alla versione Java:

1. **stack**: Django + DRF + Celery + Postgres al posto di Spring Boot + JPA + MySQL;
2. **dati di gioco**: l'import manuale dei CSV di Oracle's Elixir sparisce, sostituito
   da una pipeline **PandaScore** (calendario, stato, risultati) + **Leaguepedia**
   (box score per game);
3. **modalità Worlds**: un formato event-based, in stile Fantacalcio Champions League,
   affiancato alle leghe stagionali LEC/LPL/LCK.

Le **regole di gioco stagionali sono invariate**: formula fantapunti per ruolo,
vincoli d'asta, dimensionamento rosa e finestra formazione sono portati 1:1, e la
suite di test blocca qualsiasi deriva numerica.

---

## Indice

- [Avvio rapido](#avvio-rapido)
- [Esecuzione in locale](#esecuzione-in-locale)
- [Configurazione](#configurazione)
- [Roster pro: LEC, LPL e LCK](#roster-pro-lec-lpl-e-lck)
- [Regole di gioco](#regole-di-gioco)
- [Modalità Worlds](#modalità-worlds)
- [Pipeline di ingest](#pipeline-di-ingest)
- [API](#api)
- [Test e qualità](#test-e-qualità)
- [Utenti e reset](#utenti-e-reset)
- [Mappa dei package](#mappa-dei-package)

---

## Avvio rapido

### Docker Compose (consigliato)

```bash
cp .env.example .env      # compila almeno DJANGO_SECRET_KEY e JWT_SECRET
docker compose up --build
```

Servizi: `db` (Postgres 16), `redis`, `backend` (Gunicorn su **8080**, come il
setup Spring precedente), `worker` (Celery) e `beat` (Celery Beat). Il servizio
`backend` esegue a ogni avvio `migrate` e `seed_base_data`, entrambi idempotenti.

- API: <http://localhost:8080/api/>
- Swagger: <http://localhost:8080/api/docs/> (sostituisce `/swagger-ui.html`)
- Schema OpenAPI: <http://localhost:8080/api/schema/>
- Django admin: <http://localhost:8080/django-admin/>

---

## Esecuzione in locale

Serve **solo Python 3.12+**: niente Docker, niente Postgres, niente Redis.
Quando `DB_HOST` non è impostata il progetto usa SQLite, e con `DEBUG` attivo
Django serve anche il frontend provvisorio sulla stessa porta delle API — quindi
un solo processo e nessun problema di CORS.

```bash
cd fantalol-django

python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements/dev.txt

python manage.py migrate             # crea db.sqlite3
python manage.py seed_base_data      # admin globale + 10 roster LEC
python manage.py runserver 8080
```

Poi apri **<http://localhost:8080>** e accedi come `Natsu_Admin`.

| Indirizzo | Cosa c'è |
| --- | --- |
| <http://localhost:8080> | frontend provvisorio di collaudo |
| <http://localhost:8080/lega.html?leagueId=1> | dettaglio di una lega stagionale |
| <http://localhost:8080/lega.html?worldsLeagueId=1> | dettaglio di una lega Worlds |
| <http://localhost:8080/api/docs/> | Swagger UI |
| <http://localhost:8080/django-admin/> | pannello di amministrazione Django |

`psycopg` in `requirements/base.txt` richiede i header di PostgreSQL. Se
l'installazione fallisce e vuoi restare su SQLite, basta installare le sole
dipendenze applicative:

```bash
pip install "Django>=5.0,<5.3" djangorestframework djangorestframework-simplejwt \
            drf-spectacular celery redis httpx bcrypt \
            pytest pytest-django factory_boy coverage respx
```

### Celery serve?

**No, non per il collaudo locale.** I task periodici (sync PandaScore, enrich
Leaguepedia, deadline Worlds) richiedono Redis, ma il resto del gioco funziona
senza: le aste scadute vengono chiuse alla prima lettura utile, grazie a
`FINALIZE_AUCTIONS_ON_READ` (attiva per default).

Se vuoi comunque provarli, con un Redis in ascolto:

```bash
celery -A config worker --loglevel=info
celery -A config beat   --loglevel=info
```

In alternativa, per eseguire un task subito e in-process:

```bash
python manage.py shell -c "from ingest.tasks import sync_pandascore; print(sync_pandascore())"
```

### Ricominciare da zero

```bash
rm db.sqlite3
python manage.py migrate && python manage.py seed_base_data
```

---

## Configurazione

Tutto passa da variabili d'ambiente (vedi [`.env.example`](.env.example)). Le più
rilevanti:

| Variabile | Default | Effetto se assente |
| --- | --- | --- |
| `PANDASCORE_API_TOKEN` | — | `sync_pandascore` non parte: si serve solo la cache su DB |
| `PANDASCORE_API_BASE` | `https://api.pandascore.co` | — |
| `LEAGUEPEDIA_BOT_USERNAME` / `_PASSWORD` | — | `enrich_leaguepedia` non parte: si servono solo i game già arricchiti |
| `LEAGUEPEDIA_API_BASE` | `https://lol.fandom.com` | — |
| `SUPPORTED_PRO_LEAGUES` | `LEC:4198,LPL:294,LCK:293` | fallback ai soli campionati stagionali |
| `LINEUP_TIMEZONE` | `Europe/Rome` | fuso della finestra formazione |
| `AUCTION_SECONDS_PER_BID` | `15` | countdown d'asta, riarmato a ogni rilancio |
| `SPLIT_BACKFILL_FROM` | `2026-07-24T00:00:00+02:00` | inizio split per lo storico formazioni |
| `DB_HOST` | — | se assente si usa SQLite (comodo per i test locali) |
| `DJANGO_DEBUG` | `true` | in produzione va messa a `false` |
| `SERVE_LOCAL_FRONTEND` | segue `DJANGO_DEBUG` | se attiva, Django serve il frontend provvisorio su `/` |
| `FINALIZE_AUCTIONS_ON_READ` | `true` | chiude le aste scadute senza bisogno di un worker Celery |
| `DJANGO_ADMIN_PASSWORD` | — | password dell'admin creato da `seed_base_data` |
| `WORLDS_IN_DEVELOPMENT` | `true` | finché è attiva, `/api/worlds/**` risponde solo all'ADMIN |

`SUPPORTED_PRO_LEAGUES` è l'allowlist delle leghe sincronizzate, nel formato
`CODICE:pandascore_league_id`. **Nessun id di lega è hardcoded nel client**: le
leghe e i tornei Worlds si aggiungono qui.

---

## Roster pro: LEC, LPL e LCK

`seed_base_data` porta solo i 10 roster **LEC**. LPL e LCK si importano da
**Leaguepedia**, la stessa fonte da cui l'ingest prende i box score: i nomi
arrivano quindi già nella forma canonica, e l'aggancio delle statistiche
funziona senza dover creare alias a mano.

Le query Cargo di lettura non richiedono credenziali bot, quindi il comando
funziona senza configurare nulla:

```bash
python manage.py import_rosters_leaguepedia --competition LPL
python manage.py import_rosters_leaguepedia --competition LCK
```

| Opzione | Effetto |
| --- | --- |
| `--competition` | codice competitivo: `LEC`, `LPL`, `LCK`, `LCS`, `PCS`, ... |
| `--region` | regione Leaguepedia, se serve forzarla (default dedotto dal competitivo) |
| `--quotazione N` | quotazione base assegnata ai player importati (default 50) |
| `--mark-worlds` | marca i player come qualificati a Worlds |
| `--dry-run` | mostra cosa verrebbe importato, senza scrivere |

Il comando salta le squadre sciolte, i player ritirati e lo staff tecnico, ed è
idempotente: rieseguirlo aggiorna i roster invece di duplicarli. Se una squadra
non risponde, le altre vengono importate comunque e l'errore finisce su stderr.

Conviene guardare prima cosa arriverebbe:

```bash
python manage.py import_rosters_leaguepedia --competition LPL --dry-run
```

### Quotazioni

Leaguepedia non espone alcun valore economico, quindi tutti i player importati
partono dalla stessa quotazione. Vanno poi differenziate da
`/django-admin/teams/proplayer/`, altrimenti l'asta perde di senso: i roster LEC
del seed, per confronto, vanno da 50 a 100 crediti.

### In alternativa, da PandaScore

```bash
python manage.py import_pro_rosters --tournament-id <ID> --mark-worlds
```

Richiede `PANDASCORE_API_TOKEN` e l'id del torneo. Utile soprattutto per le
regioni minori qualificate a Worlds.

---

## Regole di gioco

Portate 1:1 dal backend Java per LEC, LPL e LCK, trattati come competitivi pro
indipendenti (una lega fantasy ne sceglie uno solo).

### Formula fantapunti

```
fantapunti = uccisioni × K(ruolo)
           + assist    × A(ruolo)
           − morti     × D(ruolo)
           + risorsa(ruolo)
           + 3 se vittoria
```

Coefficienti ripresi senza modifiche dall'originale
`scoring/RoleScoreWeights.java` (ora solo nella storia dei commit) — vedi
[`scoring/weights.py`](scoring/weights.py):

| Ruolo | K (kill) | A (assist) | D (morte) | risorsa |
| --- | --- | --- | --- | --- |
| TOP | 3.00 | 2.00 | 2.00 | `(CS / 100) × 1.25` |
| JUNGLE | 3.00 | 2.25 | 2.00 | `(CS / 100) × 0.70` |
| MID | 3.00 | 2.00 | 2.00 | `(CS / 100) × 1.00` |
| ADC | 3.25 | 1.75 | 2.25 | `(CS / 100) × 1.10` |
| SUPPORT | 2.15 | 2.55 | 1.75 | `vision score / 50` |

Il punteggio del player è la **media cumulativa** dei game dello split; quello del
FantaTeam è la **media dei 5 slot di ruolo**, usando il titolare storicamente
schierato al momento di ogni partita.

### Asta a crediti

- budget iniziale per partecipante (default 1000 crediti, configurabile per lega);
- base d'asta = quotazione del player; ogni rilancio riarma il countdown di 15s;
- un player non può stare in due FantaTeam della stessa lega;
- chiusura amministrativa della lega, oppure completamento casuale delle rose
  incomplete nel rispetto di quotazioni e budget.

### Dimensionamento rosa

| Partecipanti | Rosa | Per ruolo | Titolari |
| --- | --- | --- | --- |
| 2–5 | 10 | 2 | 5 (formazione scelta) |
| 6–10 | 5 | 1 | 5 (coincide con la rosa) |

Il numero di partecipanti si **congela** alla creazione della prima giornata.

### Finestra formazione

Modifiche aperte **martedì 00:00 → giovedì 23:59:59** (`Europe/Rome`), effettive
dal **venerdì 00:00**. Ogni conferma chiude il `LineupPeriod` corrente e ne apre
uno nuovo con `valid_from` / `valid_to`: i punti già maturati restano legati al
titolare storico e non vengono riscritti.

---

## Modalità Worlds

> **In fase di sviluppo.** Finché `WORLDS_IN_DEVELOPMENT` è attiva (default),
> tutte le rotte `/api/worlds/**` rispondono **403** a chi non è l'ADMIN
> globale, con un messaggio che spiega il motivo. Fa eccezione
> `/api/worlds/status/`, leggibile da qualunque utente autenticato: serve al
> frontend per mostrare l'avviso senza incassare un errore. Per aprire la
> sezione a tutti basta `WORLDS_IN_DEVELOPMENT=false`.

Formato **event-based** ispirato al Fantacalcio Champions League, nell'app
[`worlds/`](worlds/), separato dalle leghe stagionali ma con la stessa formula
fantapunti per ruolo.

| Aspetto | Leghe stagionali | Worlds |
| --- | --- | --- |
| Competitivo | uno solo (LEC **o** LPL **o** LCK) | **multi-regione**: tutti i roster qualificati |
| Rosa | 10/5 secondo i partecipanti | fissa e configurabile per edizione (default **10, 2 per ruolo**) |
| Formazione | finestra settimanale mar→gio | **5 titolari, uno per ruolo, entro la deadline di ogni fase** |
| "Giornata" | `Matchday` | `WorldsStage` (Play-In, Swiss, Quarti, Semifinali, Finale) |
| Punteggio | media dei 5 slot | **somma** per fase, cumulativa sul torneo |
| Classifica | per lega stagionale | separata, con bonus torneo |

### Fasi e deadline

`WorldsStage` è ordinata (`ordine`) e porta una `lineup_deadline`; se non è
valorizzata si usa l'inizio della prima serie della fase. Un task Celery
(`worlds.tasks.lock_due_stage_lineups`, ogni 10 minuti) blocca le formazioni
quando la deadline scade.

### Bonus torneo

Isolati in [`worlds/bonuses.py`](worlds/bonuses.py), per non toccare la formula
base condivisa con LEC/LPL/LCK. Tutti configurabili:

| Bonus | Default | Configurazione |
| --- | --- | --- |
| MVP di serie (dato Leaguepedia) | **+3** per game | `WorldsLeague.mvp_bonus` |
| Avanzamento di fase | **+2** per titolare | `WorldsStage.advancement_bonus` |
| Vittoria serie della squadra pro | **+1** per serie | `WorldsLeague.series_win_bonus` |

### Sostituzioni fra fasi

Con `allow_reentry_swap` attivo (default) si può sostituire **liberamente** un
player della rosa fra una fase e l'altra — non solo quelli con squadra eliminata —
pagandone la quotazione con i crediti residui e restando nello stesso ruolo. Lo
storico dell'ingaggio precedente resta (`released_at_stage`), quindi i punti già
maturati non si perdono. Con il flag disattivo la rosa è congelata dopo l'asta e
lo slot di un player eliminato resta "morto".

### Tie-break della classifica

A parità di punti totali: **più bonus** → **punteggio più alto nella fase più
avanzata disputata** → ordine alfabetico.

### Impostare un'edizione

```bash
# 1. squadre e roster qualificati (da PandaScore, per torneo)
python manage.py import_pro_rosters --tournament-id <ID> --mark-worlds

# 2. edizione, fasi e squadre qualificate: da Django admin
# 3. marca il player pool
curl -X POST /api/worlds/editions/<id>/sync-pool/ -H "Authorization: Bearer <admin>"
# 4. importa le serie di ogni fase
curl -X POST /api/worlds/stages/<id>/import-matches/ -H "Authorization: Bearer <admin>"
```

---

## Pipeline di ingest

Sostituisce integralmente Oracle's Elixir. **Nessun CSV manuale**: se in sviluppo
serve un fixture, si usano fixture Django generate da risposte reali dell'API.

| Componente | File | Cadenza |
| --- | --- | --- |
| Client PandaScore | [`ingest/pandascore_client.py`](ingest/pandascore_client.py) | — |
| Sync calendario/risultati | `ingest.tasks.sync_pandascore` | ogni ora |
| Client Leaguepedia (Cargo) | [`ingest/leaguepedia_client.py`](ingest/leaguepedia_client.py) | — |
| Enrich box score | `ingest.tasks.enrich_leaguepedia` | ogni 30 min, batch di 10 serie |

**PandaScore** viene interrogato per lega × stato (`past`/`running`/`upcoming`),
`per_page` 100, auth `Bearer`, timeout 20s. **Leaguepedia** risolve ogni serie con
`ScoreboardGames` LEFT JOIN `MatchScheduleGame`, poi `ScoreboardPlayers` per i 10
box score di ciascun game, con self-throttling a ~1 req/sec e gestione esplicita
del rate limit. La finestra di ricerca è allargata (`begin_at − 6h` … `end_at + 12h`)
perché gli orari dei due provider non coincidono; una serie non risolvibile viene
abbandonata dopo 7 giorni.

Tre principi, ereditati dalla pipeline sorgente:

1. **il frontend non raggiunge mai un provider esterno** — legge solo dal DB Django;
2. **il fallimento parziale è normale** — l'errore di una lega o di una serie non
   interrompe il ciclo, viene registrato in `SyncState` (`OK`/`PARTIAL`/`ERROR`);
3. **i mismatch di nome sono dati, non codice** — si correggono da Django admin
   con `TeamAlias` e `PlayerAlias`, mai con costanti nel client.

La differenza sostanziale rispetto alla pipeline read-only di partenza: qui
l'enrich **alimenta lo scoring**. Ogni volta che una serie viene marcata
`leaguepedia_synced_at`, i fantapunti dei player coinvolti vengono ricalcolati
tramite `scoring/services.py` e si propagano alle classifiche stagionali e Worlds.

### Attribuzione Leaguepedia

I dati Leaguepedia sono coperti da **CC BY-SA 3.0**. Ogni risposta API che espone
box score o MVP include il campo `attribution`, che il frontend deve mostrare.

---

## API

Prefisso `/api/`. I path e i payload delle rotte esistenti sono invariati, così il
frontend attuale continua a funzionare.

### Auth e utenti

| Metodo | Path |
| --- | --- |
| POST | `/api/auth/register`, `/api/auth/login`, `/api/auth/refresh` |
| GET / PUT | `/api/users/me`, `/api/users/me/profile` |
| GET | `/api/admin/users` *(admin)* |

### Leghe stagionali

| Metodo | Path |
| --- | --- |
| GET / POST / DELETE | `/api/leagues`, `/api/leagues/{id}` |
| PUT | `/api/leagues/{id}/auction/open`, `/api/leagues/{id}/auction/close` |
| POST | `/api/leagues/{id}/rosters/complete-randomly` |
| GET | `/api/leagues/{id}/cumulative-ranking` |
| POST / GET | `/api/fanta-teams/join`, `/api/fanta-teams/me`, `/api/fanta-teams/{id}` |
| GET | `/api/fanta-teams/by-league/{leagueId}` |
| POST / DELETE | `/api/fanta-teams/{id}/rosa`, `/api/fanta-teams/{id}/rosa/{entryId}` |
| POST | `/api/fanta-teams/{id}/rosa/gratis`, `/api/fanta-teams/{id}/rosa/completa-casualmente` |
| GET / POST | `/api/auctions/active`, `/api/auctions`, `/api/auctions/{id}/bids` |

### Giornate e formazioni

| Metodo | Path |
| --- | --- |
| GET / POST | `/api/matchdays`, `/api/matchdays/{id}`, `/api/matchdays/{id}/stats` |
| POST | `/api/matchdays/{id}/chiudi`, `/api/matchdays/{id}/waiting-for-postponed` |
| GET / PUT | `/api/fanta-teams/{id}/formazioni/window`, `.../formazioni/lineup` |
| GET / POST | `/api/fanta-teams/{id}/formazioni/{matchdayId}`, `.../confirm` |
| POST | `/api/admin/leagues/{id}/matchdays/{id}/formations/confirm-all` |

### Squadre, player e punteggi

| Metodo | Path |
| --- | --- |
| GET | `/api/teams`, `/api/players` — filtri `?competition=LEC\|LPL\|LCK`, `?ruolo=`, `?worldsEligible=` |
| GET | `/api/lec/cumulative-performances` *(alias: `/api/cumulative-performances`)* |
| GET | `/api/matches`, `/api/matches/{pandascoreId}`, `/api/games/{externalGameId}` |

### Worlds

| Metodo | Path |
| --- | --- |
| GET | `/api/worlds/status/` — stato della sezione, aperto a ogni utente autenticato |
| GET | `/api/worlds/editions/`, `/api/worlds/editions/{id}/`, `.../stages/`, `.../pool/` |
| POST | `/api/worlds/editions/{id}/sync-pool/`, `/api/worlds/stages/{id}/import-matches/` *(admin)* |
| GET / POST | `/api/worlds/leagues/`, `/api/worlds/leagues/join/`, `/api/worlds/leagues/{id}/` |
| GET | `/api/worlds/leagues/{id}/teams/` |
| GET / POST / PUT | `/api/worlds/leagues/{id}/auction/`, `.../auction/{open\|close}/`, `/api/worlds/auctions/{id}/bids/` |
| POST | `/api/worlds/leagues/{id}/swap/`, `/api/worlds/teams/{id}/roster/complete/` |
| GET / POST | `/api/worlds/leagues/{id}/lineup/` |
| GET | `/api/worlds/leagues/{id}/standings/` |

### Admin ingest

| Metodo | Path |
| --- | --- |
| GET | `/api/admin/ingest/status` |
| POST | `/api/admin/ingest/{pandascore\|leaguepedia}/sync` |
| PUT / DELETE | `/api/admin/ingest/games/{gameId}/players/{playerId}` — correzione manuale e ripristino |

---

## Test e qualità

```bash
python -m pytest                       # suite completa
python -m coverage run -m pytest       # con coverage
python -m coverage report              # soglia minima 75%
```

La suite porta **caso per caso** i test JUnit esistenti: formula fantapunti per
ruolo, vincoli d'asta, dimensionamento rosa, finestra formazione, storico
titolarità, idempotenza dell'import e fallimento parziale dell'ingest. Si
aggiungono i test dedicati a Worlds (fasi, deadline, swap, bonus, tie-break) e
alla pipeline PandaScore/Leaguepedia (risposte mockate, **nessuna chiamata reale**).

| File | Origine Java |
| --- | --- |
| `tests/test_scoring_formula.py` | `GameScoreCalculatorTest`, `FantaScoreCalculatorTest` |
| `tests/test_lineup_window.py` | `LineupWindowTest` |
| `tests/test_roster_policy.py` | `RosterPolicyTest` |
| `tests/test_auction_rules.py` | `AuctionServiceTest`, `LeagueAuctionPhaseServiceTest` |
| `tests/test_roster_and_lineup.py` | `FantaTeamServiceTest`, `LeagueRosterCompletionTest`, `EffectiveLineupServiceTest` |
| `tests/test_matchdays.py` | `MatchdayLifecycleServiceTest`, `MatchdayScoringServiceTest`, `FormationServiceTest` |
| `tests/test_cumulative_scoring.py` | `CumulativeScoringServiceTest` |
| `tests/test_ingest_pipeline.py` | `OracleGameImportServiceTest`, `LecSynchronizationServiceTest` (riadattati) |
| `tests/test_api_contracts.py`, `tests/test_api_league_flow.py` | `AuthIntegrationTest`, `FormationControllerTest`, `AdminUserDirectoryIntegrationTest` |
| `tests/test_worlds.py`, `tests/test_worlds_api.py` | nuovi (incluso il gating admin-only) |
| `tests/test_roster_import.py` | nuovo: import roster da Leaguepedia, Cargo API mockata |
| `tests/test_tasks_and_commands.py` | `DataSeederRosterCorrectionTest`, `AdminAccountInitializerIntegrationTest` |

CI: [`.github/workflows/django-backend-ci.yml`](../.github/workflows/django-backend-ci.yml)
esegue lint, verifica che le migration siano allineate ai modelli e lancia i test
con coverage.

---

## Utenti e reset

L'unico account creato dal seed è l'admin globale **`Natsu_Admin`**: non esistono
utenze di prova, e ogni altro utente nasce dalla registrazione via API.

```bash
python manage.py seed_base_data                              # crea l'admin se manca
python manage.py seed_base_data --admin-password 'nuova'     # solo alla creazione
python manage.py seed_base_data --admin-password 'nuova' --reset-admin-password
```

La password si può anche passare con la variabile `DJANGO_ADMIN_PASSWORD`. In
assenza di entrambe, il comando usa l'hash BCrypt incluso in
`accounts/management/commands/seed_base_data.py`.

> **Nota di sicurezza.** Quell'hash è materiale sensibile versionato: chi clona
> il repository può tentare un attacco a dizionario offline. In produzione
> imposta `DJANGO_ADMIN_PASSWORD` e ruota la credenziale.

### Svuotare le utenze

```bash
python manage.py reset_users --dry-run   # mostra chi verrebbe cancellato
python manage.py reset_users             # chiede conferma
python manage.py reset_users --yes       # senza conferma
```

Cancella tutti gli utenti tranne `Natsu_Admin` e, a cascata, le loro leghe,
FantaTeam, rose, formazioni e storico di titolarità. I dati pro (squadre,
player, serie, box score) restano intatti. Con `--keep <username>` si preserva
un utente diverso.

Per azzerare davvero tutto, database compreso, basta eliminare `db.sqlite3` e
rieseguire `migrate` + `seed_base_data`.

---

## Mappa dei package

Il backend Java non è più nel repository; la tabella resta come traccia della
corrispondenza, utile per orientarsi nella storia dei commit.

| Package Java (`com.fantalol.backend.*`) | App Django |
| --- | --- |
| `common` | [`core/`](core/) — error handling, permessi, paginazione, CORS |
| `config` | [`config/`](config/) — settings, urls, Celery |
| `integration` | [`ingest/`](ingest/) — PandaScore + Leaguepedia (ex Oracle's Elixir) |
| `league` | [`leagues/`](leagues/) — leghe, FantaTeam, aste, rose |
| `lineup` | [`lineups/`](lineups/) — finestre e storico formazioni |
| `matchday` | [`matchdays/`](matchdays/) — giornate, statistiche, formazioni |
| `scoring` | [`scoring/`](scoring/) — formula, punteggi cumulativi, classifiche |
| `security` | `accounts/` via `djangorestframework-simplejwt` |
| `team` | [`teams/`](teams/) — squadre e player pro, multi-lega |
| `user` | [`accounts/`](accounts/) — registrazione, login, profilo, ruoli |
| — | [`worlds/`](worlds/) — **nuova**: modalità Worlds |

---

## Frontend

Il frontend definitivo resta in [`../fantalol-frontend`](../fantalol-frontend) e
non è stato toccato. Per il collaudo manuale del backend c'è un placeholder
minimale in [`../fantalol-frontend-placeholder`](../fantalol-frontend-placeholder)
(stesse pagine `index.html` / `lega.html`, stessa suddivisione `css/` e `js/`),
che consuma le nuove API senza curare lo stile.

Con `runserver` attivo lo trovi già su <http://localhost:8080>: Django lo serve
dalla stessa origine delle API, e le immagini di player e loghi arrivano da
`../fantalol-frontend`. Se preferisci servirlo a parte:

```bash
cd ../fantalol-frontend-placeholder && python -m http.server 5500
```

In quel caso la pagina punta al backend su `http://localhost:8080/api` e il CORS
è già aperto in sviluppo (`CORS_ALLOWED_ORIGINS`, default `*`).
