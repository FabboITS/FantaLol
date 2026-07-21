# League Detail Page and Rules Modal Design

## Goal

Create a dedicated page for each fantasy league, move all league-specific modes and information from the homepage to that page, and expose the complete project rules in a homepage modal.

## Constraints

- Do not run Git commands during design or implementation.
- Use the existing HTML, CSS, and vanilla JavaScript frontend architecture.
- Preserve the current dark blue-violet FantaLeague visual identity.
- Do not display fabricated LEC standings or player-performance data.
- Keep the future external LEC API integration isolated from page rendering.

## Navigation and Access

The homepage remains responsible for public discovery, authentication, league creation, and joining a league. After authentication, its league area displays clickable league cards instead of league-specific management controls. Clicking a card opens a separate URL in the form `/lega.html?id=<leagueId>`.

The league detail page requires authentication. Direct unauthenticated access redirects to the homepage and triggers the login flow. The page reads and validates the numeric `id` query parameter, loads the leagues visible to the authenticated user, and permits access only when the requested league is in that result. A missing, invalid, or inaccessible league produces a dedicated error state with a link back to the homepage rather than a partially rendered dashboard.

## Page Layout

The selected layout is a management dashboard with a persistent sidebar and one main content area. The sidebar identifies the active league and provides these destinations:

- Overview;
- Squadre;
- Asta;
- Giornate;
- Classifica LEC;
- Performance.

On desktop, the sidebar remains visible while the main content scrolls. On smaller screens it becomes a horizontally scrollable section menu and the active content uses the full viewport width. The page reuses the existing header branding, typography, colors, controls, dialogs, and responsive conventions.

## Overview

The overview presents the league name, administrator, invite code, initial credits, participating-team count, and auction state. It also contains the fantasy-team ranking.

Fantasy teams display `0 pt` while calculated totals are unavailable. When every team is at zero or has no score, teams are ordered alphabetically by fantasy-team name. Once real non-zero totals exist, teams are ordered by score descending, with fantasy-team name as the deterministic tie-breaker.

## Fantasy Teams and Rosters

The Squadre section loads every fantasy team belonging to the selected league from the existing by-league endpoint. Each team displays its name, manager when that field is available, remaining credits, current score or `0 pt`, and its full roster. Roster players are grouped consistently by `TOP`, `JUNGLE`, `MID`, `ADC`, and `SUPPORT`; an empty roster has an explicit empty state.

## Asta

The existing live-auction behavior moves from the homepage to the Asta section. This includes:

- opening and closing the league auction for authorized league managers;
- nominating available players;
- bidding and the live countdown;
- showing assigned players and current roster capacity;
- releasing a player where currently supported;
- random roster completion after the auction where currently supported.

The existing API contracts and permission rules remain unchanged. Polling runs only while the auction section is active and stops when the user leaves it or the page.

## Giornate and Formations

The Giornate section owns all matchday-specific actions previously exposed on the homepage. League administrators can open a giornata. A user with a fantasy team in the selected league can configure a valid formation for an open giornata once their roster satisfies the existing requirements. The current dialogs and API contracts remain the behavioral source of truth.

## LEC Standings and Player Performance

The Classifica LEC and Performance sections ship without demo data. Each has a polished, accessible integration-pending state that explains that an official data source is not connected yet.

External data access will be isolated behind a small client boundary rather than embedded in rendering functions. Once an API is selected, the standings section can consume normalized team standing records and the performance section can consume normalized player-statistic records without restructuring navigation or presentation. Failures from that future source will show a recoverable error state instead of stale or invented values.

## Homepage Rules Modal

A `REGOLAMENTO` button appears directly below the `Inizia a giocare` button in the homepage hero action area. It matches the primary button's width, height, and typographic prominence while using a blue-violet outlined secondary style. It opens an accessible, scrollable dialog containing the complete Italian text from the root `Rules.md` file, including every heading, paragraph, and list item.

The dialog supports its visible close button and the browser's native Escape behavior. Its content remains readable on mobile and does not overflow the viewport.

## Data Safety and Error Handling

All dynamic API values are escaped before they are inserted into HTML. Loading, empty, invalid-ID, inaccessible-league, backend-failure, and external-source-not-connected states have distinct messages. Existing authentication expiration behavior remains intact.

The new page avoids copying session and API behavior into loosely divergent implementations: common behavior will be extracted into a focused shared frontend module only where doing so does not destabilize the existing page.

## Testing and Verification

Implementation follows test-driven development. Tests are written and observed failing before production changes.

Verification covers:

- the dedicated static league page and its linked assets are served;
- league cards navigate to `/lega.html?id=<leagueId>`;
- league-specific management actions no longer appear on homepage cards;
- invalid, inaccessible, and unauthenticated league access is handled safely;
- ranking fallback is alphabetical and displays `0 pt`;
- all fantasy teams and their full rosters render;
- auction, giornata, and formation behavior remains functional on the league page;
- the LEC sections contain integration-pending states and no fabricated data;
- the `REGOLAMENTO` button opens a modal containing all content from `Rules.md`;
- desktop and mobile layouts avoid horizontal page overflow;
- the complete backend test suite passes.

## Out of Scope

- Selecting or connecting the external LEC standings/statistics API.
- Inventing provisional competition statistics.
- Changing existing backend auction, formation, scoring, or authorization rules unless a narrowly scoped read endpoint is proven necessary during implementation.
- Introducing a frontend framework or redesigning unrelated homepage content.
