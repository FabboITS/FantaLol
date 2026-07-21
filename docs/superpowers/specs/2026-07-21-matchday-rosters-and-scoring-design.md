# Matchday Rosters and Scoring Design

## Goal

Make matchday roster management depend on the number of fantasy teams frozen when the first Giornata is created, connect matchday availability to the league auction, preserve the last submitted five-player lineup, and calculate team results as the average of the five players' rule-based scores.

## Terminology

- **Rosa**: every LEC player currently owned by a fantasy team.
- **Formazione**: the five active players used for one Giornata, exactly one for each role: TOP, JUNGLE, MID, ADC, and SUPPORT.
- **Participant count**: the number of fantasy teams in the league when its first Giornata is created.
- **Small league**: 1–5 fantasy teams.
- **Large league**: 6 or more fantasy teams.

## League Lifecycle and Frozen Format

Creating the first Giornata permanently closes league enrollment. Later attempts to join through the invite code are rejected with a clear business-rule error.

At that moment, the league stores its participant count and roster format:

- a small league permits ten owned players, with at most two per role;
- a large league permits five owned players, with at most one per role.

The stored format, rather than a later live team count, controls every subsequent auction and formation rule. This prevents a league's roster constraints from changing after competition begins.

Existing leagues that already have a Giornata but no stored format will derive and persist the format from their current fantasy-team count the first time the new logic processes them.

## Giornata and Auction Lifecycle

Only the league creator or a global administrator can create a Giornata or control its auction.

Creating a Giornata automatically opens the league auction. An open auction locks the current open Giornata: owners cannot submit formations, the administrator cannot enter final results for it, and it cannot be closed for scoring.

Closing the auction unlocks the Giornata and exposes the roster control on the league page. The league creator can reopen the auction at any time while the Giornata remains open; reopening locks the Giornata again. An already closed/scored Giornata is immutable and is not affected by later auction activity.

Only one unclosed Giornata may exist in a league at a time. This keeps the league-wide auction state unambiguous.

## Formation Rules

Every effective formation contains exactly five distinct players, one for each required role.

For a small league:

- after the auction closes, the owner sees **Modifica formazione**;
- the owner selects one currently owned player for every role;
- only the fantasy-team owner or a global administrator may save it;
- a closed Giornata or auction-locked Giornata cannot be edited;
- captain selection and captain multipliers are removed.

For a large league:

- after the auction closes, the owner sees **Vedi la tua rosa**;
- no manual selection is required because the five owned players, one per role, are the effective formation;
- the same read-only view displays players and their matchday results.

When a small-league owner does not submit a formation for a new Giornata, scoring uses the most recent earlier submitted formation. The carried formation is a historical five-player snapshot and remains effective even if later auction activity changes the currently owned Rosa. When no earlier submitted formation exists, that fantasy team receives exactly `0` points for the Giornata.

Submitting a new formation always validates against the team's currently owned Rosa. Previous and closed formations remain unchanged.

## Player Scoring

The application will use the scoring rule in `Rules.md` and will remove the existing base-vote, MVP, and captain adjustments.

For one real player in one Giornata:

```text
playerScore = (kills × 3)
            + (assists × 2)
            - (deaths × 2)
            + floor(CS ÷ 100)
            + (win ? 3 : 0)
```

CS points are awarded only for complete groups of 100 CS. Player scores are allowed to be negative. Missing statistics for an active player contribute `0`.

The statistics input and persistence model will contain kills, assists, deaths, CS, and win status. Obsolete base-vote and MVP inputs will be removed from the active API and interface.

## Fantasy-Team Scoring and Ranking

For a valid effective formation:

```text
teamMatchdayScore = sum(the five active player scores) ÷ 5
```

The divisor remains five when one or more players have no statistics. A team without its first formation in a small league receives `0` rather than an average of an inferred lineup.

The overall fantasy-team score is the sum of its closed Giornata averages. League ranking uses this overall score, descending. Scores are stored with sufficient decimal precision and displayed consistently without silently rounding the value used for ranking.

Closing a Giornata resolves and stores each team's effective formation and result, so subsequent roster changes cannot rewrite history.

## League Page

The Giornate section reflects the current lifecycle:

- while the auction is open, it explains that the Giornata is waiting for the auction to close and does not expose formation editing;
- after the auction closes, a small-league owner sees **Modifica formazione**;
- after the auction closes, a large-league owner sees **Vedi la tua rosa**;
- spectators cannot edit another owner's formation;
- the league creator retains the existing auction open/close controls.

The roster dialog/view shows:

- the five roles and the effective player in each role;
- editable role selectors only for a small league and an unlocked open Giornata;
- each listed player's score for every closed Giornata;
- the fantasy team's five-player average for every closed Giornata;
- a clear `0 pt` state when the first formation was never submitted.

The overview ranking and team cards use backend-provided accumulated scores instead of fixed placeholder values.

## API and Data Responsibilities

The backend is the authority for the frozen league format, enrollment lock, auction lock, ownership validation, carried formation resolution, score calculation, averages, and ranking totals. The frontend only renders returned capabilities and results; it does not infer security or scoring rules.

Responses needed by the league page will expose the frozen roster format, whether the active Giornata is auction-locked, whether formation editing is permitted, the effective formation source (submitted, carried, automatic, or missing), per-player matchday scores, team matchday averages, and accumulated team points.

Business-rule failures return user-readable messages for locked enrollment, auction-locked editing/scoring, incomplete Rosa, invalid role composition, non-owned selections, and unauthorized updates.

## Compatibility and Data Migration

The schema changes must work with the project's JPA/H2 tests and its configured persistent database. Existing matchday, formation, and statistics rows are retained where possible. Historical rows that lack CS treat CS as zero. The former `votoBase`, `mvp`, and captain fields may remain nullable at the database level during migration, but they no longer affect calculations or appear as required API inputs.

Static frontend sources and the backend-served frontend copies must remain synchronized according to the repository's existing build/test conventions.

## Testing

Automated coverage will verify:

- the 1–5 versus 6+ threshold and its permanent freeze at first-Giornata creation;
- rejection of new league participants after the first Giornata;
- automatic auction opening, Giornata locking, closing/unlocking, and reopening;
- rejection of formation edits and scoring while the auction is open;
- manual one-per-role selection for small leagues and automatic one-per-role formation for large leagues;
- carry-forward of the last submitted formation and `0` for a missing first formation;
- removal of captain behavior;
- the exact kill, assist, death, complete-100-CS, and win formula, including negative scores;
- missing player statistics contributing zero and team averages always dividing by five;
- stored matchday averages, accumulated totals, and ranking order;
- authorization boundaries;
- league-page button labels, editability, historical player points, and team averages.

## Out of Scope

- Trades between fantasy teams.
- Automated import of official LEC statistics.
- Role-specific scoring weights beyond the explicit formula.
- Multiple simultaneous open Giornate in one league.
- Changing the league's frozen roster format after competition begins.
