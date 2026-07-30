# Overview Fantasy Ranking and LEC Game Details

## Goal

Make the league Overview a compact fantasy-team ranking and make Performance
use the official LEC series/game data to show each player's champion, K/D/A,
role-specific resource statistic, and fantasy score for the selected game.

## Scope

The existing backend synchronization remains the source of truth. The change
only changes the Overview presentation and extends the existing per-game
response with the already calculated persisted fantasy score. It does not
change formation rules, scoring coefficients, official LEC standings, or
provider synchronization.

## Design

### Overview

The Overview ranking renders one compact row per fantasy team: position, team
name, and cumulative fantasy points/average returned by the cumulative-ranking
endpoint. Player roster entries are not rendered in Overview. The existing
Teams section remains responsible for roster/player visibility.

### Performance flow

Performance has two dependent selectors:

1. the LEC series/match;
2. the individual game within that series.

Changing the series replaces the game options and selects its first game.
Changing the game renders the two team groups and their player rows. Each row
contains champion (with existing asset path), nickname/role, kills/deaths/
assists, CS for non-support roles, Vision Score for support, and the backend's
fantasy score for that game. Missing data is rendered as an explicit pending
label rather than a fabricated zero.

### Backend contract

`LecDataSnapshot.GamePlayer` gains a nullable-safe numeric `fantasyScore`
field. The parser populates it from the calculated row score for live parsed
data and from the persisted provider statistic for durable projections. The
existing `/api/lec/matches` wrapper and series/game nesting stay unchanged, so
older clients can continue reading all other fields.

### Error and loading behavior

An empty match list keeps the existing “statistics pending” state. A selected
game with no player rows shows the same pending state. Selector changes never
trigger a provider request; they operate on the already synchronized response.

## Testing

- Backend parser test asserts a returned game player carries the expected
  calculated fantasy score.
- Frontend behavior test asserts Overview no longer renders roster markup in
  its ranking and that Performance contains the two selectors and score field.
- Existing backend and frontend suites remain green.

