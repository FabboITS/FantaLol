# League Auction Mode Design

## Goal

Add a creator-controlled auction phase to each fantasy league. While the phase is open, every fantasy team in the league may nominate players and bid. The creator may close and later reopen the phase. After closing it, the creator may randomly complete every incomplete roster according to league-size-dependent role limits.

## Auction Phase Lifecycle

Each league stores a persistent `auctionOpen` state. The state is independent from an individual timed player auction.

- A new league starts with its auction phase closed.
- Only the league creator or the existing global administrator may open or close the phase.
- The creator may reopen a previously closed phase.
- Closing the phase is rejected while an individual player auction is active. The creator must wait for its existing timer to expire and for the player to be awarded or the session to expire.
- When the phase is closed, nominating a player and placing a bid are rejected by the backend.
- When the phase is open, any participant may nominate an available player for the fantasy team they own, and every fantasy-team owner in the league may bid for their own team.

The league auction UI displays the current phase state to all participants. Only the creator or global administrator sees the phase-management button. The button reads `Avvia asta` while closed and `Termina asta` while open.

## League and Roster Limits

A league accepts at most 10 fantasy teams. The backend rejects an eleventh team even if a client bypasses the UI.

Roster capacity is derived from the current number of fantasy teams in the league:

- Exactly 10 teams: each roster contains at most 5 players, with at most 1 Top, 1 Jungle, 1 Mid, 1 ADC, and 1 Support.
- Between 1 and 9 teams: each roster contains at most 10 players, with at most 2 players in each role.

The same derived limits apply when nominating a player, bidding, finalizing an awarded player, and randomly completing rosters. This design assumes the league team count is allowed to reach 10 after some teams have already built larger rosters. In that exceptional case, existing roster entries are preserved, but teams already above the new 5-player/1-per-role limit cannot acquire more players or receive random players. The application does not delete already acquired players automatically.

## Individual Player Auctions and Bidding

The existing 10-second timer and its reset after each accepted bid remain unchanged.

The nomination starts at the player's base quotation. The nominating team becomes the opening highest bidder at that amount, subject to ownership, credits, availability, and roster-slot validation.

The bid control accepts a custom positive integer. An accepted relaunch must be:

- At least the current bid plus 1 credit.
- No greater than the bidding team's remaining credits.
- Valid for the team's derived roster and role limits.

Larger bid jumps are valid. For example, when the current amount is 100 credits, a team with 1,000 remaining credits may bid 1,000 immediately. Credits are deducted only after the timed auction is won. Because the next minimum would then be 1,001, that team cannot relaunch again unless its available balance is higher.

When a participant's remaining credits are lower than the next minimum bid, the relaunch button is gray and disabled, and the interface displays `Non hai abbastanza crediti per rilanciare`. The backend independently rejects unaffordable bids so client-side controls cannot bypass the rule.

## Ending and Reopening the Auction

The creator's `Termina asta` action closes only the league-level phase. It does not shorten or override an individual player timer. If a player auction is active, the close endpoint returns a clear Italian business-rule error and leaves the phase open.

Once no individual player auction is active, closing succeeds. Nominations and bids then remain unavailable until the creator reopens the phase.

## League-Wide Random Roster Completion

The `Completa casualmente i ruoli mancanti` action is visible and usable only by the league creator or global administrator, and only while the league auction phase is closed.

One action processes every fantasy team in the league:

- A roster already complete under the derived league limits is skipped.
- Each incomplete roster receives randomly selected, unassigned players until every role reaches its derived limit.
- Randomly assigned players cost 0 credits.
- A player may belong to only one fantasy team within the league.
- The whole operation is transactional. If there are not enough eligible unassigned players to complete every incomplete roster, it fails with a clear error and makes no partial assignments.

The creator does not select teams individually. Reopening the auction later remains allowed after random completion, but normal availability and roster-limit validation still applies.

## Automatic Roster Refresh

The existing auction polling continues to monitor the active timed auction. When polling detects that an auction has ended, the client refreshes:

- The active auction state.
- The logged-in user's fantasy-team data and remaining credits.
- The displayed roster.
- The available player list.

This makes an awarded player and the deducted credits visible immediately without closing the auction dialog or manually refreshing the page. Other participants also see that the player is no longer available on their next poll.

## Backend Responsibilities

The league model and API expose the persistent auction-phase state and creator identity needed by the UI. Creator-only endpoints open and close the phase. The close operation checks for an active individual auction under a database lock before changing state.

Auction nomination and bid services validate that the phase is open in addition to their current membership, ownership, credit, player-availability, and roster checks. Shared roster-limit logic calculates capacity from the league's fantasy-team count so all acquisition paths use identical rules.

League-wide random completion belongs to a league-scoped service endpoint rather than the existing team-scoped completion endpoint. Authorization is checked against the league creator. Candidate selection and roster writes execute in one transaction with appropriate player locking and a final uniqueness check.

## Frontend Responsibilities

The auction dialog renders one of three useful states:

- Closed for participant: phase status and waiting message; no nomination or bidding controls.
- Closed for creator: phase status, `Avvia asta`, and league-wide random-completion control.
- Open: player nomination and live bidding controls for participants, plus `Termina asta` for the creator.

The bid amount field defaults to the next valid minimum but remains editable for custom jumps. Affordability is recalculated whenever refreshed auction or team data arrives. A disabled gray relaunch control includes the insufficient-credit message.

## Error Handling

Business-rule errors use clear Italian messages for these cases:

- A non-creator tries to manage the league auction phase.
- A nomination or bid is attempted while the phase is closed.
- The creator tries to close the phase while a timed player auction is active.
- A bid is below the next minimum or above remaining credits.
- A team violates the derived roster or per-role capacity.
- An eleventh fantasy team tries to join.
- Random completion is requested while the phase is open or by a non-creator.
- There are not enough eligible players to complete every roster.

## Verification

Backend tests cover:

- Creator open, close, and reopen flows.
- Unauthorized phase management.
- Rejection of closing during an active player timer.
- Nomination and bidding only while the phase is open.
- Participation by every team in the league and rejection of teams outside it.
- Custom bid jumps, bidding the full remaining balance, below-minimum bids, and unaffordable relaunches.
- The 10-team league cap.
- Ten-team rosters with 5 total players and 1 per role.
- One-to-nine-team rosters with 10 total players and 2 per role.
- Award finalization using the correct dynamic roster limits.
- Creator-only league-wide random completion, skipping complete rosters, uniqueness of assigned players, and transactional rollback when players are insufficient.

Frontend checks cover creator and participant views, phase-control visibility, the gray disabled relaunch state and its exact message, custom amount submission, blocked close errors, and automatic roster/credit refresh after an award.
