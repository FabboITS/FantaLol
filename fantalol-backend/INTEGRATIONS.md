# LEC data integrations

## Responsibilities

- **PandaScore free plan**: tournament calendar, scheduled matches, match status and final series result.
- **Oracle's Elixir CSV**: per-game player statistics used by FantaLoL: kills, deaths, assists, total CS and game result.
- **FantaLoL backend**: weekly aggregation, fantasy score calculation, five-starter average and general standings.

## Environment variables

Add these values locally and on Render:

```env
PANDASCORE_API_TOKEN=your-private-token
PANDASCORE_BASE_URL=https://api.pandascore.co
PANDASCORE_SUMMER_TOURNAMENT_IDS=21344
ORACLE_ELIXIR_CSV_URL=https://your-trusted-host/2026.csv
```

Never expose `PANDASCORE_API_TOKEN` in frontend JavaScript or commit it to Git.

## PandaScore admin endpoints

The endpoints require a JWT belonging to a global `ADMIN` account.

```http
GET /api/admin/pandascore/tournaments/{tournamentId}/matches
GET /api/admin/pandascore/matches/{matchId}
POST /api/admin/pandascore/summer/sync
```

For LEC Summer 2026 Regular Season, the tournament ID identified during setup is `21344`.
`PANDASCORE_SUMMER_TOURNAMENT_IDS` accepts a comma-separated list so playoff
tournament IDs can be added without changing code. The Summer sync groups both
regular-season and playoff series into Europe/Rome calendar weeks, upserts the
official series, creates missing league matchdays and links each series to its week.

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
POST /api/admin/oracle-elixir/sync
GET /api/admin/oracle-elixir/health
Content-Type: multipart/form-data
```

Example:

```bash
curl --request POST \
  --header "Authorization: Bearer $JWT" \
  --form "file=@2026_LoL_esports_match_data_from_OraclesElixir.csv" \
  "http://localhost:8080/api/admin/oracle-elixir/matchdays/1/import?league=LEC&split=Spring"
```

The scheduled sync runs daily when `ORACLE_ELIXIR_CSV_URL` is configured. It uses
conditional HTTP requests and safely reports a degraded health state when the source
is unavailable. The upload endpoint remains the fallback and accepts the original
annual CSV.

The response reports imported games, skipped games and unmatched players. A game is uniquely identified by Oracle's Elixir `gameid`; uploading the same CSV again does not add its statistics twice.

Players are matched first through `playerid`. If an Oracle ID has not yet been stored, the importer falls back to a case-insensitive nickname match and saves the external ID for later imports.

## Weekly score calculation

Scoring uses formula version `SUMMER_2026_V1`. A player's score is calculated for
each game using role-specific coefficients:

```text
game score = kills × K(role)
           + assists × A(role)
           - deaths × D(role)
           + (CS / 100) × C(role)
           + 3 when the game is won
```

| Role | K | A | D | C per 100 CS |
|---|---:|---:|---:|---:|
| Top | 3.00 | 2.00 | 2.00 | 1.10 |
| Jungle | 3.00 | 2.25 | 2.00 | 0.70 |
| Mid | 3.00 | 2.00 | 2.00 | 1.00 |
| ADC | 3.25 | 1.75 | 2.00 | 1.20 |
| Support | 2.50 | 2.50 | 2.00 | 0.20 |

CS are continuous: 50 CS award half of the role's 100-CS coefficient. A player's
series score is the average of only the games they played. Series scores are summed
within the matchday. The fantasy-team result is then the sum of the five starters'
scores divided by five; an absent starter contributes zero.

Imported values remain editable. Oracle and manual candidates are both retained.
Equal candidates verify automatically; a disagreement is exposed as a conflict and
keeps the previously effective value until an admin resolves it:

```http
PUT /api/admin/game-stats
GET /api/admin/game-stats/conflicts
POST /api/admin/game-stats/conflicts/{statId}/resolve
```

Every import, manual edit and resolution is audited. Recalculation is immediate and
standings remain provisional while data are incomplete or conflicted. Existing
pre-Summer formations keep their legacy scoring and totals.

## Formation lock

Formation locking is independent of scoring finality. Any participant in the league,
the league creator, or a global admin can lock or unlock the whole matchday:

```http
POST /api/matchdays/{matchdayId}/formation-lock
DELETE /api/matchdays/{matchdayId}/formation-lock
```

While locked, formation edits are rejected. The last actor and timestamp are shown
with the matchday and every change is audited.

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
