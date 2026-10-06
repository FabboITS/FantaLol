# Pipeline dati delle partite professionistiche

> **Nota di provenienza.** Il prompt di progetto citava un documento di design allegato
> (`pro-matches-pipeline.md`, scritto per un'implementazione Go) che non è stato fornito insieme al
> prompt. Questo file ne ricostruisce il contenuto a partire dai requisiti della sezione 5 del prompt
> e descrive l'implementazione Django effettivamente presente nel repository.

## Obiettivo

Fornire a FantaLol calendario, risultati, roster e statistiche per game di **LEC, LCK, LPL e Worlds**
usando solo fonti gratuite:

| Fonte | Dati | Accesso |
| --- | --- | --- |
| **PandaScore** (piano gratuito "Fixtures") | leghe, serie, tornei, match, risultati, team, player, roster | REST, `Authorization: Bearer <token>`, 1.000 richieste/ora |
| **Leaguepedia** (Cargo API su `lol.fandom.com/api.php`) | game di ogni serie, MVP, statistiche per player (`ScoreboardGames`, `MatchScheduleGame`, `ScoreboardPlayers`) | bot password (`Special:BotPasswords`), self-throttle ~1 req/s |

Il piano gratuito di PandaScore **non** include i game di un match né le statistiche post-game e
non consente `GET /lol/matches/{id}`: si usano solo endpoint di lista.

## Regole non negoziabili

1. **Le view HTTP non chiamano mai i provider.** Leggono solo dal database; se un provider è giù le
   API restituiscono gli ultimi dati con `stale: true`, mai un 5xx. Anche il pulsante admin
   "Sincronizza ora" registra soltanto una richiesta che lo scheduler esegue entro ~15 secondi.
2. **I fallimenti parziali sono normali.** Ogni worker raccoglie gli errori per elemento, salva ciò
   che è riuscito e registra l'esito in `ProviderSyncState` (per provider e competizione).
3. **Le discrepanze di nomi sono dati, non codice.** Tabelle `TeamAlias` (nome PandaScore → nome
   Leaguepedia) e `PlayerAlias` (`Link` Leaguepedia → player), gestibili da admin e API.
4. **Leaguepedia è CC BY-SA 3.0.** Ogni risposta con dati Leaguepedia contiene `source` e
   `attribution` con il link alle pagine sorgente; l'interfaccia mostra sempre l'attribuzione.

## Componenti

```text
                 ┌──────────────────────────┐   ogni 60 min + all'avvio
 PandaScore ───▶ │ EsportsSyncWorker        │ ─▶ ProTeam, EsportsMatch, EsportsMatchTeam,
                 │ (apps/providers/         │    ProPlayer, EditionRoster, ProviderSyncState
                 │  pandascore/worker.py)   │
                 └──────────────────────────┘
                 ┌──────────────────────────┐   ogni 30 min
 Leaguepedia ──▶ │ LeaguepediaEnrichWorker  │ ─▶ EsportsGame, GamePlayerStat, ProviderSyncState
                 │ (apps/providers/         │    → ricalcolo PlayerStat delle giornate aperte
                 │  leaguepedia/worker.py)  │
                 └──────────────────────────┘
                 ┌──────────────────────────┐
 Browser ──────▶ │ API REST (solo DB)       │  /api/esports/matches, /api/competitions/{code}/…
                 └──────────────────────────┘
```

Lo scheduler è un processo separato (`python manage.py run_scheduler`, APScheduler) protetto da un
lock advisory PostgreSQL: un secondo scheduler resta in attesa.

## EsportsSyncWorker (PandaScore)

* Allowlist: competizioni con almeno un'edizione attiva (`Competition.pandascore_league_id`).
  LEC `4197`, LCK `293`, LPL `294`; l'ID WORLDS si ricava con
  `GET /lol/leagues?search[name]=World Championship` (`resolve_pandascore_leagues`).
* Per ogni lega × stato: `GET /leagues/{id}/matches/{past|upcoming|running}`;
  `past` con `sort=-begin_at&filter[status]=finished`, gli altri con `sort=begin_at`;
  `per_page` validato 1–100. Paginazione con `Link`/`X-Total` finché i match restano nella
  finestra temporale delle edizioni attive.
* Mappatura sull'edizione tramite `serie_id`/`tournament_id` (o finestra di date se l'edizione non ha
  ID PandaScore). Per WORLDS la fase (`Stage`) si ricava da nome torneo/match (Play-In, Swiss,
  quarti, semifinali, finale); se non riconosciuta il match si salva con `stage = null` e un warning.
* Upsert di team (logo light/dark), match ed `EsportsMatchTeam` (`score` da `results[]`, `winner`
  da `winner_id`).
* Roster: `GET /tournaments/{id}/rosters` → `ProPlayer` + `EditionRoster` con ruolo
  `top|jun|mid|adc|sup → TOP|JUNGLE|MID|ADC|SUPPORT`. Le quotazioni impostate dall'admin non vengono
  sovrascritte; un cambio di squadra chiude il periodo precedente (`active_to`).
* Con `--discover` (e a ogni giro dello scheduler) crea/aggiorna le `CompetitionEdition` dalle serie
  (`GET /leagues/{id}/series`).
* Budget: 4 competizioni × 3 stati + roster + serie ≈ 20–30 chiamate/ora.
* Senza `PANDASCORE_API_TOKEN` il worker non parte: viene loggato un warning e l'API serve la cache.

## LeaguepediaEnrichWorker

* Login con bot password (`LEAGUEPEDIA_BOT_USERNAME` = `Utente@Bot`) tramite `action=login` con
  token e sessione persistente. Self-throttle con lock (~1 richiesta/secondo); l'errore
  `ratelimited` solleva `LeaguepediaRateLimited` che **interrompe l'intero ciclo**.
* `list_games(team1, team2, from, to)`: `ScoreboardGames=SG` LEFT JOIN `MatchScheduleGame=MSG` on
  `SG.GameId=MSG.GameId` (l'MVP sta su `MatchScheduleGame`), con alias espliciti dei campi.
* **Una sola query `ScoreboardPlayers` per serie** con `SP.GameId IN (...)` (limite 500 righe) invece
  di una per game: 3–5 volte meno chiamate, importante per la LPL che gioca quasi ogni giorno.
* Tutti i valori interpolati passano da `escape_cargo_string()` (backslash e apici).
* Ciclo: al massimo `LEAGUEPEDIA_ENRICH_BATCH_SIZE` serie `finished` senza statistiche, nell'ordine
  dell'indice parziale
  `(leaguepedia_checked_at ASC NULLS FIRST, end_at DESC) WHERE status='finished' AND leaguepedia_synced_at IS NULL`.
* Nomi dei team risolti con `TeamAlias` (fallback al nome PandaScore); finestra di ricerca
  `begin_at − 6h … end_at + 12h`; `WinTeam` mappato sull'ID team (alias, poi nome grezzo).
* Player: `ProPlayer.leaguepedia_link`, poi `PlayerAlias`, poi nickname + team nell'`EditionRoster`
  (il `Link` viene memorizzato). Righe non associabili → `player = null`, esposte in
  `GET /api/admin/esports/unmatched-stats`. Righe `MISSING` o con campi mancanti → `is_complete=False`.
* Zero game trovati → `leaguepedia_checked_at = now` (il match torna in fondo alla coda); dopo
  `LEAGUEPEDIA_GIVE_UP_DAYS` (7) il match è marcato sincronizzato senza statistiche e la giornata resta
  **provvisoria** finché l'admin non inserisce i dati manualmente (game manuali + correzioni).
* Statistiche parziali (righe `MISSING`, meno game del punteggio della serie) → si salvano, ma il
  match resta in coda per i ritentativi fino al give-up.
* Dopo ogni upsert riuscito si ricalcolano in transazione i `PlayerStat` delle giornate aperte che
  contengono la serie.

## Endpoint di lettura (cache DB)

| Endpoint | Note |
| --- | --- |
| `GET /api/esports/matches?competition=&state=&limit=` | `competition ∈ all|lec|lck|lpl|worlds`, `state ∈ upcoming|results|live`, `limit` 1–100 (default 100); altri valori → 400 `ApiError`. Risposta con `source: "PandaScore"`, `refreshIntervalMinutes: 60`, `lastSyncedAt`, `verificationRequired: true`, `stale` (ultimo sync riuscito più vecchio di `ESPORTS_STALE_AFTER_MINUTES`). `Cache-Control: public, max-age=60, stale-while-revalidate=300` |
| `GET /api/esports/matches/{id}/games` | game + box score, `source: "Leaguepedia"`, `attribution` CC BY-SA con link alle pagine sorgente. `Cache-Control: public, max-age=300, stale-while-revalidate=600` |
| `GET /api/competitions/{code}/standings|performances|cumulative-performances|matches|matches/{m}/games/{g}` | proiezioni per competizione (alias `/api/lec/*`) |

## Copertura e limiti noti

* La copertura Leaguepedia della LPL ha buchi (player `MISSING`, serie non trovate): il sistema li
  gestisce con risultati provvisori, coda di ritentativi, alias e correzione manuale.
* Un'alternativa futura è il piano Historical di PandaScore come seconda fonte (a pagamento), vedi
  `docs/adr/0007-fallback-statistiche-lpl.md`.
