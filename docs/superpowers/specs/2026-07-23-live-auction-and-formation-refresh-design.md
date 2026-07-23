# Live Auction and Formation Refresh Design

## Goal

Make live auctions stable and responsive by supporting custom bids without polling overwriting the bid control, extending each bid window to 15 seconds, preventing the current highest bidder from bidding against themselves, keeping submitted formations visible in the formation dialog, and synchronizing league data automatically across the entire league page.

## Auction Duration and Bid Rules

Every individual player auction starts with a 15-second bid window. Each accepted bid resets the server-authoritative deadline to 15 seconds after the bid is accepted.

The bid amount remains a custom positive integer. A valid bid must:

- come from a fantasy team in the auction's league;
- come from that fantasy team's owner or a global administrator acting for it;
- be at least the current bid plus 1 credit;
- not exceed the fantasy team's remaining credits;
- respect the roster size and role limits; and
- come from a fantasy team other than the current highest bidder.

The backend rejects a bid from the current highest bidder with a clear Italian business-rule message. This validation is based on the fantasy team identifier, not the username, so the rule also applies consistently when an administrator acts for a team.

## Stable Live Auction Interface

The server-provided `endsAt` value remains the authoritative auction deadline. The frontend displays the remaining time from that value and updates only the countdown text between server synchronizations.

The auction summary is not rebuilt on every countdown tick. The editable custom-bid input therefore keeps its current value and focus while time passes. Server synchronization may update the current bid, leader, affordability, and deadline without overwriting a custom amount that is still valid. If another bid raises the minimum above the entered amount, the control reports the new minimum and prevents submission until the amount is valid.

When the logged-in user's fantasy team is the current highest bidder:

- the bid form and `Rilancia` button are not rendered;
- the interface displays `Sei il miglior offerente`; and
- the countdown remains visible.

When another team leads, the custom bid form is visible if the logged-in team can afford the next minimum. If it cannot, the existing disabled state and insufficient-credit message remain visible.

All explanatory auction copy refers to a 15-second timer.

## Page-Wide Synchronization

Automatic synchronization runs while the league page is open, regardless of the currently selected section. It refreshes the data needed to render:

- league and auction-phase state;
- the active individual auction;
- fantasy teams, owned rosters, remaining credits, and ranking;
- occupied and available players;
- league matchdays and their auction-lock state; and
- the logged-in team's formation data when the formation dialog is open.

The synchronization loop must not overlap requests. It compares refreshed state with the current state and updates only the affected interface regions. It preserves:

- the currently selected navigation section;
- open dialogs;
- focused form controls;
- a custom bid amount being edited; and
- unsaved formation selections.

After an auction expires and the backend awards the player, the next synchronization shows the acquired player, deducted credits, updated roster, and player availability without a manual reload. Starting or ending an auction, saving a formation, releasing or acquiring a player, creating a matchday, and random roster completion also trigger an immediate synchronization rather than waiting for the next scheduled cycle.

Transient synchronization failures show at most one non-blocking error notification per failure period. The loop continues and retries on its next interval.

## Formation Dialog

The formation dialog remains the single place where the user edits and views their active lineup.

For a small league with manual formation selection:

- opening the dialog loads the formation history and preselects the latest valid submitted or carried formation;
- saving submits exactly one player per required role;
- a successful save does not close the dialog;
- the saved response immediately becomes the displayed formation;
- the dialog switches to a clear saved-state summary containing the five selected players, one per role; and
- an explicit edit action returns to the role selectors while the matchday remains editable.

Reopening the dialog loads the persisted formation and displays the same saved lineup. If page-wide synchronization detects a newer persisted formation while the dialog is open and the user has no unsaved edits, it refreshes the summary. It never replaces unsaved role selections.

For a large league, where the roster is the automatic formation, the dialog continues to show the five roster players and requires no save action.

## Backend Responsibilities

`AuctionService` owns the 15-second duration and the current-highest-bidder validation. The duration is applied consistently when starting an auction and when accepting a bid. Existing transactional locking remains responsible for serializing competing bids and award finalization.

The auction response already exposes `highestBidderId` and `endsAt`, which are sufficient for the frontend to determine whether the logged-in fantasy team leads and to render the authoritative countdown. No new auction transport field is required.

Formation save responses remain authoritative and are used immediately by the dialog. Existing formation lookup and history endpoints provide persisted state for reopening and synchronization.

## Frontend Responsibilities

The league page separates:

- scheduled server synchronization;
- countdown rendering;
- state comparison and targeted rendering; and
- bid and formation form state.

The countdown may update frequently for a smooth display, while server synchronization uses a less aggressive interval appropriate for the existing REST backend. An immediate refresh occurs after mutations and when the countdown reaches zero.

The frontend determines `isCurrentLeader` by comparing `activeAuction.highestBidderId` with `activeTeam.id`. This is a presentation rule only; the backend remains the security and business-rule authority.

All identifiers, helper names, comments, and newly written code use English. Existing Italian user-facing interface text remains Italian.

## Error Handling

The user receives clear Italian messages for:

- attempting to bid while already the highest bidder;
- bidding below the current minimum;
- bidding above remaining credits;
- bidding after the auction deadline;
- synchronization failures; and
- formation save or reload failures.

An unsuccessful bid leaves the custom amount available for correction when possible. An unsuccessful formation save leaves the selected roles and dialog open.

## Verification

Backend tests cover:

- a nomination sets a deadline approximately 15 seconds in the future;
- an accepted bid resets the deadline to approximately 15 seconds in the future;
- the current highest bidder cannot bid again;
- a different team can place a valid custom bid; and
- existing minimum, credit, ownership, roster, and expiration rules continue to pass.

Frontend tests cover:

- countdown updates do not replace or reset the custom bid input;
- a custom bid value survives an unrelated synchronization;
- the bid control disappears for the current highest bidder;
- the leader message and 15-second explanatory copy are rendered;
- an auction award refreshes rosters, credits, and availability automatically;
- synchronization continues outside the auction section;
- successful formation submission keeps the dialog open and shows the five-player summary;
- reopening the dialog shows the persisted formation; and
- synchronization preserves unsaved bid and formation input.

