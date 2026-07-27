# LEC Live Data and Support Vision Scoring Design

## Goal

Replace the disconnected LEC standings and performance placeholders with
automatically synchronized competition data, and replace Support CS scoring
with one fantasy point per 50 vision score.

All identifiers, comments, configuration names, API names, and tests introduced
by this work must be written in English. Existing Italian user-facing copy will
remain Italian.

## Scoring Rule

The Summer 2026 fantasy score remains:

```text
gameScore = kills * roleKillWeight
          + assists * roleAssistWeight
          - deaths * roleDeathWeight
          + roleResourceScore
          + (win ? 3.0 : 0.0)
```

For Top, Jungle, Mid, and ADC:

```text
roleResourceScore = (cs / 100.0) * roleCsWeight
```

For Support:

```text
roleResourceScore = visionScore / 50.0
```

The former Support coefficient of `0.20` points per 100 CS is removed. Support
CS contributes no fantasy points. Vision scoring is continuous: 25 vision score
adds `0.5`, 50 adds `1.0`, and 100 adds `2.0`.

`visionScore` is a non-negative statistic accepted by manual administration,
stored in player statistics, returned by the API, and imported from the
Oracle's Elixir `visionscore` column. Legacy rows without the field are treated
as zero.

## External Sources

The backend is the only component allowed to communicate with external data
providers.

- PandaScore provides the current LEC tournament, scheduled and completed
  matches, series results, and team identities.
- Oracle's Elixir provides per-game player statistics, champion selections,
  CS, vision score, and game results.
- Riot Data Dragon or CommunityDragon provides champion square icons.

`PANDASCORE_API_TOKEN` remains a server-side environment variable and must
never appear in frontend code or committed configuration. The synchronization
must discover the configured competition rather than relying permanently on a
single tournament ID. Exact season, split, and league filters are configurable
with defaults for LEC Summer 2026.

Champion icons are downloaded during the asset preparation workflow and stored
under:

```text
fantalol-frontend/Player_immage/Champions/
```

The application serves these local assets at runtime. It does not hotlink
search-engine results or depend on Google Images.

## Synchronization and Persistence

A focused backend synchronization service coordinates both providers:

1. Load the configured LEC tournament and its matches from PandaScore.
2. Upsert matches using stable external IDs.
3. Load the current Oracle's Elixir annual CSV.
4. Filter complete rows for the configured league and split.
5. Upsert per-game player statistics and champion selections by external game
   and player identity.
6. Rebuild derived standings and performance projections.

The process is idempotent. Repeating a synchronization does not duplicate
matches, player statistics, or champion picks.

Synchronization runs on a configurable schedule and is also exposed through an
administrator-only endpoint. The backend stores the timestamp and outcome of
each attempt.

When one provider is temporarily unavailable, the last complete snapshot stays
visible. Responses identify the last successful update and whether data is
fresh or stale. A match without complete Oracle statistics is retained but
marked as awaiting statistics; no plausible-looking values are fabricated.

## LEC Standings

The LEC standings response contains:

- current position;
- team identity and local logo where available;
- series wins and losses;
- optional game wins and losses when the provider supplies them;
- last successful synchronization time;
- freshness status.

Ranking follows the official provider order when PandaScore supplies standings.
If only completed series are available, the backend derives the order from
series wins and losses and applies a stable documented fallback for unresolved
ties. The UI must label derived order as provisional.

## Performance Views

The Performance page contains two independently renderable views.

### Split Fantasy Average

Players are ordered by mean fantasy score per game across the configured split.
Each row includes player, team, role, games played, and fantasy average.

The same view displays every champion selected by that player during the split.
Each champion entry contains the local icon, champion name, and pick count.

### Match Detail

A match selector lists completed and scheduled LEC series in reverse
chronological order. Selecting a match displays both teams and the ten players
from its games.

Each player row shows:

```text
Caps · 1/2/3 · 123 CS · KDA 2.00
```

Support rows replace CS with vision score:

```text
Mikyx · 0/2/8 · Vision 87 · KDA 4.00
```

The mathematical KDA is `(kills + assists) / deaths`. When deaths are zero, the
API returns an explicit perfect-KDA state rather than infinity or a fabricated
divisor. For a multi-game series, the selector expands to individual games so
the displayed K/D/A, CS, vision score, and champion always belong to one game.

## Backend Boundaries

Separate units own:

- external PandaScore access;
- Oracle CSV retrieval and parsing;
- synchronized match and per-game statistic persistence;
- standings projection;
- split performance projection;
- champion asset metadata;
- public read-only LEC data endpoints;
- administrator synchronization control.

The frontend consumes normalized FantaLoL endpoints and contains no scoring,
ranking, provider-token, or CSV-parsing logic.

## Frontend Behavior

The existing `LecDataSource` adapter will call the FantaLoL backend instead of
returning `not-connected`.

The LEC standings section renders a responsive ranking table. The Performance
section renders the split fantasy ranking and match selector without changing
the league navigation structure.

Loading, empty, stale, awaiting-statistics, and provider-error states use clear
Italian copy. The old “Fonte ufficiale non collegata” placeholder is removed.

## Validation and Error Handling

The backend rejects negative vision scores and malformed provider values.
Unknown players and ambiguous nickname matches are reported for administrator
review rather than silently assigned.

A failed synchronization must not partially replace a previously complete
snapshot. Provider errors are logged without exposing tokens or sensitive
request details.

Champion names are normalized through Riot champion metadata before local asset
paths are generated. Missing icons fall back to one local generic asset and do
not break the performance response.

## Testing

Automated tests cover:

- Support vision scoring at 0, 25, 50, and 100 vision score;
- Support CS having no scoring effect;
- unchanged resource scoring for the other four roles;
- manual and CSV vision-score validation;
- Oracle `visionscore` and champion parsing;
- idempotent match, stat, and pick synchronization;
- standings order and provisional tie behavior;
- split fantasy averages;
- per-player champion pick counts;
- mathematical KDA and the zero-death state;
- per-game match selection and role-specific CS/vision presentation;
- stale snapshot fallback after provider failure;
- local champion icon references;
- removal of the disconnected-source placeholders.

Backend and frontend test suites, JavaScript syntax checks, and a final
cross-file scoring-rule audit must pass before completion is reported.

## Commit Strategy

Work is delivered as sequential, reviewable commits:

1. approved design specification;
2. Support vision scoring and Oracle/manual statistic support;
3. synchronized match and performance persistence;
4. public standings and performance APIs;
5. league-page UI and local champion assets;
6. integration documentation and final consistency fixes.

Each implementation commit must leave its focused tests passing.

## Out of Scope

- Exposing provider tokens to the browser.
- Scraping Google Images or third-party statistics pages at runtime.
- Changing non-Support role coefficients.
- Replacing the existing static frontend framework.
- Predicting statistics for matches that have not produced complete data.
