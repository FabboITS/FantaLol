# LEC data integrations

## Responsibilities

- **PandaScore free plan**: tournament calendar, scheduled matches, match status and final series result.
- **Oracle's Elixir CSV**: per-game player statistics used by FantaLoL: champion, kills, deaths, assists, total CS, vision score and game result.
- **FantaLoL backend**: weekly aggregation, fantasy score calculation, five-starter average and general standings.

## Environment variables

Add these values locally and on Render:

```env
PANDASCORE_API_TOKEN=your-private-token
PANDASCORE_BASE_URL=https://api.pandascore.co
LEC_TOURNAMENT_ID=21344
LEC_LEAGUE=LEC
LEC_SPLIT=Summer
ORACLE_ELIXIR_CSV_URL=https://example.invalid/2026_LoL_esports_match_data_from_OraclesElixir.csv
LEC_SYNC_CRON=0 15 */6 * * *
```

Never expose `PANDASCORE_API_TOKEN` in frontend JavaScript or commit it to Git.

## Automatic LEC synchronization

The backend synchronizes PandaScore match data and the configured Oracle's
Elixir CSV every six hours by default. A global administrator can trigger the
same idempotent operation immediately:

```http
POST /api/admin/lec/synchronize
Authorization: Bearer ADMIN_JWT
```

The league page reads `/api/lec/standings`, `/api/lec/performances`, and
`/api/lec/matches`. If a provider fails, the last complete in-memory snapshot
remains available with status `stale`; no incomplete statistics are invented.

## PandaScore admin endpoints

The endpoints require a JWT belonging to a global `ADMIN` account.

```http
GET /api/admin/pandascore/tournaments/{tournamentId}/matches
GET /api/admin/pandascore/matches/{matchId}
```

For LEC Summer 2026 Regular Season, the tournament ID identified during setup is `21344`.

Example:

```bash
curl --header "Authorization: Bearer $JWT" \
  "http://localhost:8080/api/admin/pandascore/tournaments/21344/matches"
```

## Oracle's Elixir import

Upload the original annual CSV. The backend performs these filters itself:

- `league` equals the requested league, normally `LEC`;
- `split` equals the requested split, for example `Spring` or `Summer`;
- `datacompleteness` equals `complete`;
- `position` is one of `top`, `jng`, `mid`, `bot`, `sup`.

```http
POST /api/admin/oracle-elixir/matchdays/{matchdayId}/import?league=LEC&split=Spring
Content-Type: multipart/form-data
```

Example:

```bash
curl --request POST \
  --header "Authorization: Bearer $JWT" \
  --form "file=@2026_LoL_esports_match_data_from_OraclesElixir.csv" \
  "http://localhost:8080/api/admin/oracle-elixir/matchdays/1/import?league=LEC&split=Spring"
```

The response reports imported games, skipped games and unmatched players. A game is uniquely identified by Oracle's Elixir `gameid`; uploading the same CSV again does not add its statistics twice.

Players are matched first through `playerid`. If an Oracle ID has not yet been stored, the importer falls back to a case-insensitive nickname match and saves the external ID for later imports.

## Weekly score calculation

For every player, statistics from all imported games assigned to the matchday are summed.

```text
player score = kills * 3
             + assists * 2
             - deaths * 2
             + role resource score
             + wins * 3
```

For Top, Jungle, Mid and ADC, the role resource score is the continuous CS
coefficient. For Support it is `vision score / 50`; Support CS contributes zero.

When the matchday closes, the fantasy-team score is the arithmetic mean of the five active starters. Missing player statistics count as zero and the divisor remains five.

## Postponed matches

When at least one scheduled match is postponed, mark the week as waiting:

```http
POST /api/matchdays/{matchdayId}/waiting-for-postponed
```

A waiting week:

- keeps already imported statistics;
- is excluded from the general standings;
- does not block creation and processing of later weeks;
- can receive the recovery game's CSV rows later;
- enters the standings only when `/api/matchdays/{matchdayId}/chiudi` is called after the recovery.
