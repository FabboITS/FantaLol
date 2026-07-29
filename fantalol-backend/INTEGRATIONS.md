# LEC data integrations

## Responsibilities

- **PandaScore free plan**: tournament calendar, scheduled matches, match status and final series result.
- **Oracle's Elixir CSV**: per-game player statistics used by FantaLoL: champion, kills, deaths, assists, total CS, vision score and game result.
- **FantaLoL backend**: durable per-game import, cumulative fantasy score
  calculation, five-slot average and general standings.

## Environment variables

Add these values locally and on Render:

```env
PANDASCORE_BASE_URL=https://api.pandascore.co
PANDASCORE_API_TOKEN=<private PandaScore token>
LEC_TOURNAMENT_ID=21344
LEC_LEAGUE=LEC
LEC_SPLIT=Summer
LEC_TIMEZONE=Europe/Rome
LEC_BACKFILL_FROM=2026-07-24T00:00:00+02:00
ORACLE_ELIXIR_CSV_URL=<direct URL of the 2026 annual CSV>
LEC_SYNC_CRON=0 15 */6 * * *
```

These are the exact environment-variable names bound by `application.yml`.
`PANDASCORE_BASE_URL`, `LEC_TOURNAMENT_ID`, `LEC_LEAGUE`, `LEC_SPLIT`,
`LEC_TIMEZONE`, `LEC_BACKFILL_FROM`, and `LEC_SYNC_CRON` have the exact defaults
shown above. `LEC_TIMEZONE` controls the lineup editing calendar and Friday
effective boundary. `LEC_BACKFILL_FROM` is the initial effective-lineup start
used only when a fantasy team has no effective periods yet. The token and
direct CSV URL have no default and must be supplied with real
private/configured values in Render.
Never expose `PANDASCORE_API_TOKEN` in frontend JavaScript or commit it to Git.

## Automatic LEC synchronization

The backend synchronizes PandaScore match data and the configured Oracle's
Elixir CSV at minute 15 every six hours by default. A global administrator can
trigger the same idempotent operation with the `Sincronizza ora` control or:

```http
POST /api/admin/lec/synchronize
Authorization: Bearer ADMIN_JWT
```

The ADMIN control retries both providers and recalculation. It cannot synthesize
games or player statistics that the provider has not published with complete
data. The league page reads `/api/lec/standings`, `/api/lec/performances`, and
`/api/lec/matches`. Provider games and player-game rows are persisted, so
Render restarts do not erase imported fantasy observations. If a provider
fails, the last valid persisted results remain available; incomplete
statistics are never invented.

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

The scheduled and ADMIN synchronization downloads the annual CSV from
`ORACLE_ELIXIR_CSV_URL`. The backend performs these filters itself:

- `league` equals `LEC`;
- `split` equals `Summer`;
- `datacompleteness` equals `complete`;
- `position` is one of `top`, `jng`, `mid`, `bot`, `sup`.

The importer groups the filtered rows by Oracle `gameid` and resolves every
player before accepting that game. It persists each complete game and its
player rows as a durable unit; it never assigns the whole annual CSV to one
matchday. The provider plus `gameid` is unique, so synchronization can be
repeated without duplicating fantasy observations. The report counts inserted,
updated, skipped and failed games and lists unmatched players.

Players are matched first through `playerid`. If an Oracle ID has not yet been stored, the importer falls back to a case-insensitive nickname match and saves the external ID for later imports.

## Initial Summer 2026 backfill

Before importing Summer games, the backend creates missing effective lineup
periods from `2026-07-24T00:00:00+02:00` (`Europe/Rome`). For leagues of at
most five teams it uses the latest valid saved formation; for larger leagues it
uses the fixed five-player roster. Existing periods are not recreated, so the
backfill is safe to run again. This is an initial, idempotent operation:
changing `LEC_BACKFILL_FROM` after effective periods exist does not rewrite,
move, or delete those periods.

## Cumulative score calculation

For every game actually played, the backend calculates a role-specific score:

```text
player game score = kills * role kill coefficient
                  + assists * role assist coefficient
                  - deaths * role death coefficient
                  + role resource score
                  + 3 when the game is won
```

For Top, Jungle, Mid and ADC, the role resource score is the continuous CS
coefficient. For Support it is `vision score / 50`; Support CS contributes zero.

The individual performance is the cumulative average of played Summer games;
not playing adds no zero observation. Bench players retain an individual
evaluation. A fantasy role slot receives a game only from the player effective
in that slot at game time and retains older observations after a lineup change.
The fantasy-team score is the mean of its five slot averages. Until every slot
has an eligible observation, the result is provisional and has no numeric
overall score.

## Diagnostics and manual corrections

```http
GET /api/admin/lec/synchronization
Authorization: Bearer ADMIN_JWT
```

The response exposes separate PandaScore and Oracle statuses, attempt/success
timestamps, import counts, unmatched player rows, and one of these freshness
states:

- `fresh`: both sources have completed successfully;
- `awaiting-data`: at least one source has not completed successfully yet;
- `stale`: the latest attempt failed and the last valid persisted data remains visible.

A global ADMIN can correct a resolved player row for one provider game:

```http
PUT /api/admin/lec/games/{gameId}/players/{playerId}
Authorization: Bearer ADMIN_JWT
Content-Type: application/json
```

Editable fields are `participated`, `kills`, `deaths`, `assists`, `cs`,
`visionScore`, and `win`. The backend preserves the provider snapshot and
records the corrected values, ADMIN actor, and timestamp. Later synchronization
does not overwrite the active correction.

To discard the override, use `Ripristina fonte` in the ADMIN panel or:

```http
DELETE /api/admin/lec/games/{gameId}/players/{playerId}/override
Authorization: Bearer ADMIN_JWT
```

Restoring removes the override, reapplies the current stored provider values,
and recalculates the affected projections.

## Late or postponed games

Publication is driven by complete provider games, not by a weekly matchday
close. A postponed game contributes automatically after Oracle's Elixir
publishes its complete rows and the next scheduled or ADMIN synchronization
imports them. Existing cumulative observations remain published while the
missing game is still unavailable.
