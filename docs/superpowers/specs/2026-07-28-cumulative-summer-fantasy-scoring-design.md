# Cumulative Summer Fantasy Scoring Design

**Date:** 2026-07-28

## Goal

Replace the current matchday-level CSV aggregation with durable, per-game
Summer Split scoring. The system must ingest official external data
automatically, preserve lineup history, calculate cumulative fantasy averages,
survive Render restarts, and provide a safe global-administrator fallback.

The implementation and technical names will be in English. User-facing rules
remain in Italian.

## Confirmed Product Rules

### Individual player scoring

- Import only Oracle's Elixir rows where `league=LEC`, `split=Summer`, and
  `datacompleteness=complete`.
- Calculate a fantasy score for every game actually played by a player.
- Use the existing Summer 2026 role-based scoring formula.
- A player who does not play receives no new observation. The system must not
  add a zero to the player's cumulative average.
- A player's published performance is the arithmetic mean of all eligible game
  scores in the Summer Split.
- Bench players still receive and display their individual evaluation.

### Fantasy leagues with at most five teams

- Each fantasy roster contains ten players, two per role.
- Exactly one player per role is active in the lineup.
- Only active players contribute to the fantasy-team result.
- A lineup may be changed from Tuesday 00:00:00 through Thursday 23:59:59 in
  the `Europe/Rome` time zone.
- A saved change becomes effective on Friday at 00:00:00.
- Lineups are locked from Friday 00:00:00 through Monday 23:59:59.
- A change affects future games only. Previously accrued scores remain attached
  to the lineup slots and players that were active when those games occurred.

### Fantasy leagues with more than five teams

- Each roster contains five players, one per role.
- All five players are permanently active.
- The lineup cannot be changed.

### Cumulative fantasy-team scoring

- Each fantasy team has five role slots: Top, Jungle, Mid, ADC, and Support.
- A role slot accumulates game scores produced by players while they were
  active in that slot.
- When the active player changes, the slot retains all earlier observations and
  future observations are added for the new player.
- A slot with no new games retains its existing average.
- The fantasy-team score is the arithmetic mean of the five role-slot averages.
- A slot with no eligible game observation yet is `awaiting-data` and is not
  treated as a permanent zero. Until all five slots have at least one
  observation, the team has no numeric overall score: its result is provisional
  and the UI must identify the missing slots.
- Recalculation replaces the current projection; it must never add the same game
  twice.

## External Data Responsibilities

### PandaScore

PandaScore provides the configured LEC Summer tournament, scheduled series,
match status, opponents, and final series results. It feeds the public LEC
schedule and standings.

### Oracle's Elixir

Oracle's Elixir provides per-game player statistics: external game and player
IDs, game date, role, champion, kills, deaths, assists, total CS, vision score,
and result.

### FantaLoL

FantaLoL persists normalized provider data, resolves external players to the
local roster, calculates game scores, attributes them through effective lineup
history, and publishes individual and fantasy-team projections.

## Persistence Model

### Provider games

Persist one record per Oracle external `gameid`, including:

- provider and external game ID;
- tournament/split identity;
- scheduled or played timestamp;
- teams and series/match reference when resolvable;
- provider completion status;
- source fingerprint and timestamps.

The provider plus external game ID is unique.

### Provider player-game statistics

Persist one record per provider game and local LEC player, including:

- raw Oracle external player ID and source nickname;
- role and champion;
- kills, deaths, assists, CS, vision score, and win;
- calculated fantasy score;
- original provider values;
- source fingerprint;
- override status and audit timestamps.

The provider game plus local player is unique.

Unmatched rows remain visible in the administrator diagnostics and must not be
silently assigned to another player.

### Effective lineup history

Persist immutable effective periods for each fantasy team and role slot:

- fantasy team and role;
- active LEC player;
- effective start instant;
- optional effective end instant;
- origin (`USER`, `AUTOMATIC`, or `BACKFILL`);
- creation timestamp.

Saving a lineup during the Tuesday-through-Thursday window schedules five new
periods for Friday 00:00 in `Europe/Rome`. The preceding periods end at the same
instant. Games are attributed using their played timestamp, not import time.

For leagues with more than five teams, automatic periods are created from the
fixed five-player roster and cannot be changed by users.

### Projections

Individual, slot, and fantasy-team averages are derived from persisted
player-game scores and effective lineup history. They may be calculated through
query services and stored projections for efficient reads, but provider games
and effective periods remain the source of truth.

## Synchronization Flow

The existing six-hour scheduled synchronization remains the normal trigger. A
global administrator can run the same operation immediately from the league
page.

Each synchronization:

1. Loads PandaScore tournament matches.
2. Downloads the configured Oracle annual CSV.
3. Filters complete LEC Summer player rows.
4. Groups rows by external game ID.
5. Resolves every player in a game before accepting that game's statistics.
6. Inserts new games and updates changed provider records idempotently.
7. Preserves active manual overrides.
8. Recalculates individual, slot, and fantasy-team projections.
9. Publishes a synchronization report.

The operation must be transactional at a safe unit of work so a partially
resolved game cannot create partial fantasy results.

## Initial Summer 2026 Backfill

The deployment must backfill complete Summer Split games beginning
2026-07-24.

Because historical effective periods do not yet exist, each fantasy team's
currently saved lineup is treated as effective from
`2026-07-24T00:00:00+02:00[Europe/Rome]`. This applies only to the initial
backfill migration.

For leagues with more than five teams, the fixed roster is backfilled from the
same instant.

The backfill is idempotent and safe to rerun.

## Administrator Experience

A panel visible only to global `ADMIN` users provides:

- `Synchronize now`;
- last successful attempt and last completed update;
- separate PandaScore and Oracle status;
- inserted, updated, skipped, and failed game counts;
- unmatched player rows;
- `Provisional`, `Up to date`, or `Source unavailable` freshness state;
- selection of a game and player for a manual correction;
- restoration of provider values.

The synchronization button runs the same service as the scheduler. It retries
source access and recalculation but cannot manufacture provider data that is
not complete. Failures preserve the last valid persisted results and display a
specific diagnostic.

### Manual corrections

Only a global administrator may correct a player-game row. Editable fields are
participation, kills, deaths, assists, CS, vision score, and win.

An override stores the original provider values, corrected values, actor, and
timestamp. Later provider synchronizations update the stored provider snapshot
but do not replace the active override. `Restore provider data` removes the
override and recalculates all affected projections.

## Public and League UI

- Public LEC standings continue to use PandaScore match results.
- Performance displays cumulative fantasy average, games played, champion
  usage, and freshness.
- Bench players display individual evaluations.
- Fantasy ranking displays five slot averages and their overall mean.
- Slots without eligible games display `In attesa`, not a final zero.
- Lineup controls show the next effective time and whether the window is open
  or locked.
- Leagues with more than five teams display the fixed lineup without edit
  controls.
- Historical lineup and score views identify which player generated each
  observation.

## Failure Handling

- If either provider is unavailable, retain all last valid persisted data.
- Record provider failures independently so a PandaScore failure does not erase
  Oracle results and an Oracle failure does not erase standings.
- Reject malformed or partially matched games without recording partial
  fantasy statistics.
- Repeated imports must be idempotent.
- Provider corrections must trigger recalculation.
- Manual overrides must survive synchronization.
- Authorization failures must not expose diagnostics or correction controls.

## Italian Rules Update

The public regulation will state:

> Il fantapunteggio individuale è calcolato per ogni partita effettivamente
> disputata e la valutazione pubblicata è la media cumulativa delle partite del
> Summer Split. Una partita non disputata non aggiunge uno zero.

> Nelle leghe con un massimo di cinque FantaTeam, tutti i giocatori della rosa
> ricevono una valutazione individuale, ma soltanto i cinque titolari schierati,
> uno per ruolo, contribuiscono al punteggio del FantaTeam. La formazione può
> essere modificata da martedì alle 00:00 fino a giovedì alle 23:59, secondo il
> fuso Europe/Rome. Il cambio diventa valido dal venerdì successivo e non
> modifica i risultati già maturati.

> Nelle leghe con più di cinque FantaTeam, i cinque giocatori della rosa
> costituiscono la formazione fissa e non sono previsti cambi.

> Ogni slot di ruolo conserva le valutazioni ottenute dai giocatori mentre erano
> titolari. Il punteggio del FantaTeam è la media dei cinque slot. Se un titolare
> non disputa partite, non viene aggiunta alcuna valutazione e la media già
> maturata resta invariata.

> I risultati vengono aggiornati automaticamente quando le fonti esterne
> rendono disponibili dati completi. L'amministratore può richiedere una
> sincronizzazione immediata e, in casi eccezionali, correggere un dato
> conservando traccia della modifica.

## Testing

Automated coverage must include:

- every Summer 2026 role formula;
- per-game and cumulative player averages;
- no observation for a player who did not play;
- bench evaluation without fantasy-team contribution;
- role-slot continuity across lineup changes;
- Tuesday-through-Thursday editing in `Europe/Rome`, including DST-safe
  boundaries;
- Friday effective instants and immutable historical attribution;
- fixed lineups in leagues with more than five teams;
- idempotent imports and provider corrections;
- manual override persistence and restoration;
- unmatched-player and partial-game rejection;
- initial 2026-07-24 backfill;
- persistence and projection recovery after restart;
- global-admin authorization;
- independent source failures and last-known-good responses;
- frontend lineup-window, freshness, diagnostics, and ranking rendering.

## Out of Scope

- Mid-week emergency substitutions outside the confirmed window.
- Invented scores for games or players missing from official data.
- Changing the Summer 2026 role coefficients.
- Supporting competitions other than the configured LEC Summer split in this
  implementation.
