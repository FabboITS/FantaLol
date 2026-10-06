# FantaLeague

FantaLeague è un'applicazione web fantasy di **League of Legends** per quattro competizioni:

| Codice | Competizione | Modalità |
| --- | --- | --- |
| `LEC` | LoL EMEA Championship | Regionale ([Rules.md](Rules.md)) |
| `LCK` | LoL Champions Korea | Regionale ([Rules.md](Rules.md)) |
| `LPL` | LoL Pro League | Regionale ([Rules.md](Rules.md)) |
| `WORLDS` | World Championship | Worlds, stile FantaChampions ([Rules-WORLDS.md](Rules-WORLDS.md)) |

Gli utenti creano leghe private agganciate a una competizione e a un'edizione (stagione/split),
invitano gli amici, costruiscono la rosa (asta a crediti nel regionale, listone a prezzi fissi ai
Worlds), schierano la formazione e competono in classifica con i punti calcolati sulle prestazioni
reali dei pro player.

## Cosa può fare un utente

Un visitatore può consultare player e squadre di ogni competizione (con loghi e foto), il calendario
e i risultati con il box score delle partite, leggere i regolamenti, registrarsi e accedere.

Un utente con ruolo `USER` può:

- creare una lega scegliendo competizione ed edizione e condividerne il codice di invito;
- entrare nelle leghe create da altri (un solo FantaTeam per lega);
- **regionale:** partecipare all'asta live, schierare i titolari nella finestra della competizione;
- **Worlds:** comprare dal listone, fare cambi (2 gratuiti per giornata Swiss), scegliere capitano,
  vice e ordine della panchina;
- seguire classifica della competizione, prestazioni dei player, fantapunteggi e classifica di lega;
- modificare il profilo ed eliminare le leghe di cui è creatore.

Il creatore di una lega ne è l'amministratore locale: apre/chiude l'asta, completa casualmente le
rose, crea le giornate (o genera il calendario Worlds) e le chiude.

## Cosa può fare un amministratore

L'account con ruolo `ADMIN` viene creato all'avvio dal comando `ensure_admin` con le credenziali delle
variabili `ADMIN_USERNAME`, `ADMIN_EMAIL` e `ADMIN_PASSWORD` (mai nel repository). L'amministratore
globale può vedere ed eliminare qualsiasi lega, gestire team e player, richiedere una
sincronizzazione, consultare lo stato di PandaScore e Leaguepedia, correggere manualmente le
statistiche per game, associare le righe Leaguepedia non riconosciute (alias), pubblicare il listone
Worlds e correggerne le quotazioni, e consultare con `Ctrl+Y` la directory degli utenti registrati.

## Architettura

```text
Browser (HTML5 + CSS + JavaScript vanilla, nessun build step)
   │  REST JSON camelCase, JWT "Authorization: Bearer <token>"
   ▼
Django 5.2 + DRF  (gunicorn, porta 8080; whitenoise serve anche il frontend)
   ├── apps/users         utenti, JWT, profilo, admin bootstrap, migrazione dal MySQL Java
   ├── apps/competitions  Competition, CompetitionEdition, Stage, LineupPolicy
   ├── apps/esports       team, player, roster per edizione, serie, game, statistiche, alias
   ├── apps/providers     client e worker PandaScore + Leaguepedia, stato dei provider
   ├── apps/leagues       leghe, FantaTeam, rose, asta
   ├── apps/lineups       finestre di formazione e storico dei titolari
   ├── apps/matchdays     giornate, formazioni, aggregati per giornata, chiusura automatica
   ├── apps/scoring       formule e punteggi cumulativi
   └── apps/worlds        listone, cambi, capitano, sostituzioni, classifica Worlds
   │
   ├──▶ PostgreSQL 16
   └──  processo scheduler (APScheduler, lock advisory Postgres):
        sync PandaScore ogni 60', arricchimento Leaguepedia ogni 30', sweeper aste ogni 1",
        manutenzione giornate ogni 5', richieste di sync admin ogni 15"
```

Le view HTTP leggono solo dal database; i provider sono interrogati esclusivamente dallo scheduler.
Il design della pipeline dati è in [docs/pro-matches-pipeline.md](docs/pro-matches-pipeline.md), le
decisioni architetturali in [docs/adr/](docs/adr/README.md).

### Fonti dati e attribuzioni

- **PandaScore** (piano gratuito "Fixtures"): calendario, risultati, squadre, player, roster, loghi e
  foto. Si usano solo gli endpoint di lista disponibili nel piano gratuito.
- **Leaguepedia** (`lol.fandom.com`): statistiche per game (`ScoreboardGames`, `ScoreboardPlayers`,
  `MatchScheduleGame`). I contenuti Leaguepedia sono disponibili con licenza **CC BY-SA 3.0**:
  l'attribuzione è restituita dalle API (`source`, `attribution`) e mostrata nell'interfaccia.
- Loghi, nomi e immagini di squadre e player sono marchi dei rispettivi titolari; il progetto è a
  uso non commerciale. Non si scaricano immagini da Leaguepedia/Fandom.
- La precedente fonte CSV delle statistiche e il relativo workflow GitHub sono stati rimossi: vedi
  [CHANGELOG.md](CHANGELOG.md).

### Struttura del repository

```text
FantaLol/
├── backend/            progetto Django (manage.py, pyproject.toml, Dockerfile, docker-compose.yml)
│   ├── config/         settings base/dev/prod/test, urls
│   ├── apps/           app di dominio (vedi sopra)
│   ├── scheduler/      job e comando run_scheduler
│   └── tests/          pytest (+ fixture JSON PandaScore/Leaguepedia)
├── frontend/           index.html, lega.html, css/, js/, tests/ (node:test), asset statici
├── docs/               pipeline dati e ADR
├── Rules.md            regolamento regionale (LEC · LCK · LPL)
├── Rules-WORLDS.md     regolamento Worlds
└── CHANGELOG.md
```

## Avvio con Docker Compose

Requisiti: Docker e Docker Compose.

```bash
cp backend/.env.example backend/.env    # imposta almeno DJANGO_SECRET_KEY e JWT_SECRET (≥ 32 caratteri)
docker compose -f backend/docker-compose.yml up --build
```

Servizi:

- `db`: PostgreSQL 16 (porta host `5433`, volume `fantalol_pg_data`);
- `web`: gunicorn su **[http://localhost:8080](http://localhost:8080)** (API + frontend), esegue
  `migrate` ed `ensure_admin` all'avvio;
- `scheduler`: `python manage.py run_scheduler` (stessa immagine).

Swagger UI: **[http://localhost:8080/swagger-ui.html](http://localhost:8080/swagger-ui.html)** ·
schema OpenAPI: `/v3/api-docs` · health check: `/api/health`.

### Primo popolamento dei dati

```bash
docker compose -f backend/docker-compose.yml exec web python manage.py sync_pandascore --discover
docker compose -f backend/docker-compose.yml exec web python manage.py enrich_leaguepedia
docker compose -f backend/docker-compose.yml exec web python manage.py download_esports_images --competition LCK
docker compose -f backend/docker-compose.yml exec web python manage.py compute_worlds_prices
```

`sync_pandascore --discover` crea le edizioni dalle serie PandaScore (attive se in corso o imminenti);
le edizioni e le fasi si possono rifinire dall'admin Django (`/django-admin/`). Altri comandi:
`resolve_pandascore_leagues` (ID PandaScore della lega Worlds), `import_legacy_assets` (loghi e foto
LEC dell'originale), `migrate_from_mysql --mysql-url mysql://…` (dati del backend Java, richiede
`pip install ".[mysql]"`).

## Variabili d'ambiente

| Variabile | Default | Effetto se assente |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | — | avvio rifiutato in produzione |
| `DATABASE_URL` | `postgres://fantalol:fantalol@db:5432/fantalol` | — |
| `JWT_SECRET`, `JWT_EXPIRATION_MS` | —, `86400000` | avvio rifiutato in produzione |
| `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` | — | nessun admin creato (warning) |
| `PANDASCORE_API_TOKEN` | — | sync non eseguito, si serve la cache |
| `PANDASCORE_API_BASE` | `https://api.pandascore.co` | — |
| `LEAGUEPEDIA_BOT_USERNAME`, `LEAGUEPEDIA_BOT_PASSWORD` | — | arricchimento non eseguito, si serve la cache |
| `LEAGUEPEDIA_API_BASE` | `https://lol.fandom.com` | — |
| `LEAGUEPEDIA_ENRICH_BATCH_SIZE`, `LEAGUEPEDIA_GIVE_UP_DAYS` | `10`, `7` | — |
| `ESPORTS_STALE_AFTER_MINUTES` | `90` | — |
| `AUCTION_SECONDS_PER_BID` | `15` | — |
| `CREDITI_INIZIALI_DEFAULT` | `1000` (regionale) | — |

L'elenco completo è in [backend/.env.example](backend/.env.example).

## Sviluppo e test

```bash
cd backend
python3.12 -m venv .venv && . .venv/bin/activate
pip install ".[dev]"
export DATABASE_URL=postgres://fantalol:fantalol@localhost:5432/fantalol
pytest --cov=apps          # test backend (soglia di coverage 80% su apps/)
ruff check . && ruff format --check .
cd ../frontend && node --test   # test JavaScript
```

La CI GitHub (`.github/workflows/ci.yml`) esegue ruff, controllo delle migrazioni, pytest con
coverage su un PostgreSQL di servizio e i test JavaScript.

## Link del progetto

**[FantaLol](https://fantalol.win)**
