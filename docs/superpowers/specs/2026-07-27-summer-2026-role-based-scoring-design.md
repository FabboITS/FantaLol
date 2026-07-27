# Summer 2026 Role-Based Scoring Design

## Goal

Publish the Summer 2026 fantasy scoring system on top of the corrected player
roster, without restoring obsolete players, teams, portraits, or seed data from
the older scoring branches.

The implementation must use English identifiers, comments, API names, and test
names. Existing Italian user-facing text may remain Italian and will be updated
where it explains the scoring rules.

## Source of Truth

The current `main` workspace, including the corrected Summer 2026 roster, is the
source of truth for players, teams, quotations, portrait paths, and database
seeding.

The existing scoring branches are reference implementations only. Relevant
scoring behavior will be reapplied selectively to the current code instead of
replacing current roster-related files with older branch versions.

## Per-Game Player Score

Each player's fantasy score is calculated for each game:

```text
gameScore = (kills * roleKillWeight)
          + (assists * roleAssistWeight)
          - (deaths * roleDeathWeight)
          + ((cs / 100.0) * roleCsWeight)
          + (win ? 3.0 : 0.0)
```

The frozen `SUMMER_2026_V1` coefficients are:

| Role | Kill | Assist | Death | 100 CS |
|---|---:|---:|---:|---:|
| Top | 3.00 | 2.00 | 2.00 | 1.25 |
| Jungle | 3.00 | 2.25 | 2.00 | 0.70 |
| Mid | 3.00 | 2.00 | 2.00 | 1.00 |
| ADC | 3.25 | 1.75 | 2.25 | 1.10 |
| Support | 2.15 | 2.55 | 1.75 | 0.20 |

The death coefficient is shown as a positive magnitude in the table and is
subtracted by the formula.

CS scoring is continuous. For example, a Top player with 50 CS receives `0.625`
CS points. Partial hundreds are never discarded.

Negative game and aggregate scores are valid and must not be clamped to zero.

## Series and Matchday Aggregation

For a best-of series, the player's series score is the arithmetic mean of the
games that the player actually played. Games without an appearance are not part
of that player's divisor.

If a matchday contains more than one series, the player's series scores are
summed to produce the player's matchday score.

A fantasy team's matchday score is the arithmetic mean of its five active player
scores. An active player without usable statistics contributes zero, and the
team divisor remains five.

## Formula Versioning and History

The scoring model must store or resolve the formula version used for a result.
Summer 2026 results use `SUMMER_2026_V1`. Results belonging to competitions
before Summer 2026 retain the historical formula and must not be recalculated
with the new role weights.

Closed matchdays remain immutable unless an authorized correction workflow
explicitly reopens or recalculates them.

## Player and Team Identity

Imported game statistics must resolve against the corrected roster. Stable
external identifiers should be preferred when available, with normalized
nickname matching as a controlled fallback.

Each imported game-stat record stores the player's team name as a historical
snapshot. Later real-world roster changes must not rewrite previously calculated
results.

An unknown or ambiguous player mapping must be reported for administrative
review instead of creating a duplicate player or silently assigning statistics
to the wrong player.

## Data Import and Manual Corrections

Oracle's Elixir remains the primary source for per-game player statistics.
PandaScore remains the schedule and series source.

Administrators may enter or correct statistics manually. Oracle and manual
candidates are both retained. When they differ, the result remains marked as a
conflict until an administrator explicitly selects the effective source.

Every accepted import or manual correction recalculates affected provisional
player, fantasy-team, and ranking results. Administrative changes remain
auditable.

## Backend Responsibilities

The backend is the sole authority for:

- role coefficient selection;
- per-game score calculation;
- series averages;
- matchday aggregation;
- five-player fantasy-team averages;
- formula version selection;
- conflict handling;
- provisional and final ranking totals.

The implementation will consolidate active scoring behavior around one English
API rather than maintaining two independent calculators with overlapping
responsibilities. Temporary compatibility methods may remain only where required
by existing callers and must delegate to the authoritative implementation.

## User Interface and Documentation

The scoring section in `Rules.md`, `README.md`, and the public rules dialog must
show the exact role coefficients, continuous CS calculation, `+3` win bonus,
series averaging, matchday aggregation, and five-player team average.

The home-page decorative scoring badges must not advertise obsolete values such
as `MVP +3` or `WIN +1`.

The league page will display backend-provided player and fantasy-team scores. It
must not reproduce the formula in JavaScript.

## Error Handling

The system must expose clear administrative errors for:

- unknown or ambiguous player mappings;
- incomplete or malformed imported statistics;
- unresolved Oracle/manual conflicts;
- attempts to finalize a matchday with incomplete required data;
- attempts to mutate immutable historical results.

One player's invalid data must not be silently converted into a plausible score.

## Testing

Automated coverage will verify:

- the exact coefficients for all five roles;
- continuous CS scoring, including fractional hundreds;
- the `+3` win bonus;
- negative scores;
- per-series averaging using only games actually played;
- summing multiple series in one matchday;
- missing active-player statistics contributing zero with a divisor of five;
- formula version preservation for pre-Summer results;
- correct matching against the corrected Summer 2026 roster;
- team snapshots remaining stable after roster changes;
- Oracle/manual conflict detection and explicit resolution;
- recalculation of provisional fantasy-team totals and ranking order;
- consistency between backend behavior and every published rules copy.

## Out of Scope

- Replacing the static frontend with the separate React prototype.
- General repository cleanup unrelated to scoring publication.
- Changing the corrected Summer 2026 roster or player quotations.
- Adding further statistics such as vision score, damage, objectives, or MVP.
- Making scoring coefficients configurable per league.

