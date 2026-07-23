# Auction Participant Credits Design

## Goal

Show every fantasy team's remaining credits in the live auction view. The current
highest bidder must display the balance projected after the current bid.

## User Experience

The live auction section contains a participant credit panel that remains visible
whether or not a player auction is active.

Each participant row displays:

- the fantasy team name;
- the owner's username;
- the available credit balance.

When a player auction is active, the current highest bidder is visually
highlighted. Its displayed balance is:

```text
remaining credits - current bid
```

All other participants display their persisted remaining balance. When no player
auction is active, every participant displays the persisted balance. A projected
balance is clamped to zero as a defensive rendering rule.

User-facing labels remain in Italian to match the existing interface. Function,
variable, test, and CSS class names are written in English.

## Architecture and Data Flow

The frontend computes presentation-only balances from data already returned by
the existing endpoints:

- `GET /fanta-teams/by-league/{leagueId}` supplies all fantasy teams and their
  persisted remaining credits;
- `GET /auctions/active?leagueId={leagueId}` supplies the current bid and highest
  bidder identifier.

A pure helper receives the fantasy team list and active auction and returns
display-ready participant credit entries. `renderAuction()` renders those entries
inside the auction section.

No backend, database, or API contract changes are required.

## Refresh Behavior

The existing league-page synchronization refreshes fantasy teams and active
auction data every two seconds. The participant credit panel is recalculated from
that synchronized state whenever auction-relevant state changes.

After a bid submitted from the current browser, the existing immediate
synchronization refreshes the panel without waiting for the next interval.
Remote bids appear on the next synchronization cycle.

## Error and Edge-Case Handling

- Spectators can see all participant balances.
- A missing active auction produces only persisted balances.
- A missing or unmatched highest bidder does not project any participant balance.
- Numeric identifiers are compared after normalization.
- Invalid or absent credit values render as zero.
- Projected balances never render below zero.
- Empty participant lists render a short empty-state message.

## Testing

Implementation follows test-driven development.

Frontend unit tests cover:

- persisted balances when no auction is active;
- projected balance for the highest bidder;
- unchanged balances for other participants;
- normalized identifier comparison;
- zero-clamping for defensive rendering.

A frontend behavior test confirms that the auction renderer consumes the helper
and includes the participant credit panel. The complete frontend test suite and
the relevant backend static-resource tests are run after implementation.

## Out of Scope

- WebSocket or Server-Sent Events;
- changes to how or when credits are persisted;
- reserving credits in the database while a bid is active;
- backend response changes;
- changes to auction bidding rules.
