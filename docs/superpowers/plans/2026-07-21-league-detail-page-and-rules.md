# League Detail Page and Rules Modal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do not use subagents or Git commands for this plan.

**Goal:** Add a dedicated sidebar-based page for each fantasy league, move league management into it, and show the complete `Rules.md` content in a homepage modal.

**Architecture:** Keep the vanilla HTML/CSS/JavaScript frontend and existing REST contracts. The homepage becomes a league launcher, while `lega.html` owns league-scoped loading, navigation, rosters, auction, matchdays, and formations. Pure ranking and query-parameter behavior lives in a small testable utility module; external LEC data is represented by an isolated client boundary returning a not-connected state.

**Tech Stack:** Java 17, Spring Boot 3.3.4, MockMvc/JUnit 5, HTML5, CSS, vanilla JavaScript, Node built-in test runner.

## Global Constraints

- Do not run any Git command.
- Do not create commits.
- Do not add a frontend framework or package-manager dependency.
- Preserve existing REST API contracts and authentication storage keys.
- Do not add demo or fabricated LEC standings/player-performance values.
- Preserve the dark blue-violet FantaLeague design system.
- Escape all dynamic values before inserting them into HTML.

---

## File Structure

- Modify `fantalol-frontend/index.html`: add the rules trigger/dialog and remove league-mode dialogs that move to the detail page.
- Modify `fantalol-frontend/js/app.js`: render league/team launcher cards and open the rules dialog; remove homepage league-mode handlers.
- Modify `fantalol-frontend/css/style.css`: style the rules trigger/dialog and clickable launcher cards.
- Create `fantalol-frontend/lega.html`: dedicated league dashboard markup, sidebar, section panels, and league-mode dialogs.
- Create `fantalol-frontend/css/league-detail.css`: desktop/mobile dashboard, ranking, roster, error, and integration-state styles.
- Create `fantalol-frontend/js/league-utils.js`: pure league ID parsing and alphabetical/score ranking helpers.
- Create `fantalol-frontend/js/lec-data-source.js`: explicit future API integration boundary.
- Create `fantalol-frontend/js/league-detail.js`: league-page session, loading, rendering, navigation, auction, matchday, and formation behavior.
- Create `fantalol-frontend/tests/league-utils.test.js`: Node tests for pure ranking and ID parsing behavior.
- Modify `fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java`: integration coverage for the new page/assets and homepage rules contract.

### Task 1: Test the Pure League Navigation and Ranking Contract

**Files:**

- Create: `fantalol-frontend/tests/league-utils.test.js`
- Create: `fantalol-frontend/js/league-utils.js`

**Interfaces:**

- Produces: `parseLeagueId(search: string): number | null`
- Produces: `rankFantasyTeams(teams: Array<object>): Array<object>`
- Ranking reads `team.nome` and optional numeric `team.punti`; it does not mutate its input.

- [ ] **Step 1: Write the failing utility tests**

```javascript
const test = require('node:test');
const assert = require('node:assert/strict');
const { parseLeagueId, rankFantasyTeams } = require('../js/league-utils.js');

test('parseLeagueId accepts a positive integer id', () => {
  assert.equal(parseLeagueId('?id=12'), 12);
});

test('parseLeagueId rejects missing, zero, negative, and non-numeric ids', () => {
  for (const search of ['', '?id=0', '?id=-2', '?id=abc', '?id=1.5']) {
    assert.equal(parseLeagueId(search), null);
  }
});

test('rankFantasyTeams sorts alphabetically and supplies zero points when scores are unavailable', () => {
  const input = [{ nome: 'Zeta' }, { nome: 'Alpha' }, { nome: 'Beta' }];
  assert.deepEqual(
    rankFantasyTeams(input).map(team => [team.nome, team.punti]),
    [['Alpha', 0], ['Beta', 0], ['Zeta', 0]]
  );
  assert.equal(input[0].punti, undefined);
});

test('rankFantasyTeams sorts real scores descending and names alphabetically on ties', () => {
  const input = [
    { nome: 'Zeta', punti: 8 },
    { nome: 'Beta', punti: 12 },
    { nome: 'Alpha', punti: 12 }
  ];
  assert.deepEqual(
    rankFantasyTeams(input).map(team => team.nome),
    ['Alpha', 'Beta', 'Zeta']
  );
});
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `node --test fantalol-frontend/tests/league-utils.test.js`

Expected: FAIL because `../js/league-utils.js` does not exist.

- [ ] **Step 3: Implement the pure utility module**

```javascript
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.LeagueUtils = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  function parseLeagueId(search) {
    const raw = new URLSearchParams(search).get('id');
    if (!raw || !/^\d+$/.test(raw)) return null;
    const id = Number(raw);
    return Number.isSafeInteger(id) && id > 0 ? id : null;
  }

  function rankFantasyTeams(teams) {
    return teams
      .map(team => ({ ...team, punti: Number.isFinite(Number(team.punti)) ? Number(team.punti) : 0 }))
      .sort((left, right) => right.punti - left.punti || left.nome.localeCompare(right.nome, 'it'));
  }

  return { parseLeagueId, rankFantasyTeams };
});
```

- [ ] **Step 4: Run the tests and verify GREEN**

Run: `node --test fantalol-frontend/tests/league-utils.test.js`

Expected: 4 tests pass, 0 fail.

---

### Task 2: Add the Rules Modal and Convert the Homepage into a League Launcher

**Files:**

- Modify: `fantalol-frontend/index.html`
- Modify: `fantalol-frontend/js/app.js`
- Modify: `fantalol-frontend/css/style.css`
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java`

**Interfaces:**

- Consumes: existing `state.mine`, `state.leagues`, authentication handlers, and native `<dialog>` behavior.
- Produces: `#rules-button`, `#rules-dialog`, and homepage links matching `/lega.html?id=<leagueId>`.

- [ ] **Step 1: Add failing static-resource assertions**

Add tests asserting that `/index.html` contains `id="rules-button"`, `id="rules-dialog"`, `Regole FantaLeague LEC`, `Cambi nei roster reali`, and `Accettazione delle regole`; assert that `/js/app.js` contains `/lega.html?id=${league.id}` and does not contain homepage `data-auction` or `data-matchday` card markup.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `cd fantalol-backend && ./mvnw -Dtest=StaticResourceIntegrationTest test` if `mvnw` exists; otherwise run `cd fantalol-backend && mvn -Dtest=StaticResourceIntegrationTest test`.

Expected: FAIL because the rules controls/content and league-detail links are absent.

- [ ] **Step 3: Add the homepage rules trigger and complete rules dialog**

Place `REGOLAMENTO` in a vertically stacked hero action group directly beneath `Inizia a giocare`. Add a scrollable native dialog whose semantic headings, paragraphs, and lists reproduce every section of `Rules.md`: introduction, Creazione della lega, Composizione della rosa, Asta, Formazione, Punteggi, Mercato e cambi, Cambi nei roster reali, Aggiornamento dei risultati, Comportamento dei partecipanti, and Accettazione delle regole.

- [ ] **Step 4: Simplify homepage league rendering**

Replace the separate team management cards and league admin action buttons with one clickable card per visible league. Each card includes league name, participant count, administrator, invite code, and an `Apri lega →` link to `/lega.html?id=${league.id}`. Retain the create/join buttons and guest empty state. Remove homepage-only auction, formation, and matchday dialog markup and handlers after their equivalents exist in `lega.html`.

- [ ] **Step 5: Wire and style the rules dialog and launcher cards**

Add a click handler that calls `showModal()` on `#rules-dialog`; reuse `[data-close]` for closing. Add `.hero-primary-actions`, `.rules-trigger`, `.rules-dialog`, `.rules-content`, and clickable `.league-panel` focus/hover styles. Cap rules dialog height at `min(82vh, 760px)` and make only its content region scroll.

- [ ] **Step 6: Run the focused static-resource test and utility tests**

Run: `cd fantalol-backend && mvn -Dtest=StaticResourceIntegrationTest test`

Run: `node --test fantalol-frontend/tests/league-utils.test.js`

Expected: both commands pass.

---

### Task 3: Build the Dedicated League Dashboard Shell and Data Views

**Files:**

- Create: `fantalol-frontend/lega.html`
- Create: `fantalol-frontend/css/league-detail.css`
- Create: `fantalol-frontend/js/lec-data-source.js`
- Create: `fantalol-frontend/js/league-detail.js`
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java`

**Interfaces:**

- Consumes: `LeagueUtils.parseLeagueId`, `LeagueUtils.rankFantasyTeams`, `/api/leagues`, `/api/fanta-teams/me`, `/api/fanta-teams/by-league/{leagueId}`, `/api/players`, `/api/teams`, and `/api/matchdays`.
- Produces: `window.LecDataSource.loadStandings(): Promise<{status:'not-connected',items:[]}>` and `loadPlayerPerformances()` with the same result shape.
- Produces sections named `overview`, `teams`, `auction`, `matchdays`, `lec`, and `performance` selected by sidebar buttons carrying `data-section`.

- [ ] **Step 1: Add failing static-resource tests for the dashboard shell**

Assert `/lega.html`, `/css/league-detail.css`, `/js/league-utils.js`, `/js/lec-data-source.js`, and `/js/league-detail.js` return 200. Assert the HTML contains every `data-section` destination, `id="league-error"`, the auction controls, formation dialog, and matchday dialog. Assert `lec-data-source.js` contains `status:'not-connected'` and contains no numeric standings records.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `cd fantalol-backend && mvn -Dtest=StaticResourceIntegrationTest test`

Expected: FAIL with 404 for `/lega.html`.

- [ ] **Step 3: Create the semantic page shell**

Build `lega.html` with the shared favicon/fonts/styles, compact brand header and back-home link, `#league-loading`, `#league-error`, and a hidden `#league-dashboard`. Inside the dashboard add an `<aside>` with league identity and six buttons, plus `<section>` elements for Overview, Squadre, Asta, Giornate, Classifica LEC, and Performance. Move the existing auction, formation, and matchday dialog structures here with unchanged internal IDs needed by their handlers.

- [ ] **Step 4: Implement session, access validation, and core loading**

In `league-detail.js`, load `fantalol_token` and `fantalol_user`, redirect unauthenticated users to `/?login=1#leagues`, parse the league ID, and show a dedicated invalid-ID error when parsing fails. Fetch visible leagues, find the requested league, reject an inaccessible league, then load the league teams, current user's teams, public players/teams, and matchdays concurrently. Store only selected-league records in page state.

- [ ] **Step 5: Render overview ranking and all rosters**

Use `rankFantasyTeams` with `punti: 0` until a real score field becomes available. Render rank number, team name, owner username, and `0 pt`. Render every fantasy team and every roster entry grouped in role order. Use `ownerUsername` from the existing DTO and explicit empty roster text. Escape all league, owner, team, and player strings.

- [ ] **Step 6: Implement sidebar navigation and integration-pending states**

Each navigation click hides all inactive sections, updates `aria-current`, and activates exactly one section. `LecDataSource` returns `{status:'not-connected',items:[]}` for both functions. Render a polished icon, heading, explanation, and `Fonte ufficiale non collegata` status in both external-data panels with no demo rows.

- [ ] **Step 7: Style desktop and mobile layouts**

Use a two-column dashboard with a sticky sidebar at widths above 900px. Below 900px, switch to one column and make the navigation a horizontal, overflow-safe button row. Add styles for league metadata, ranking table, roster team cards, role chips, errors, loading skeletons, and pending-integration panels. Ensure dialogs remain usable below 460px.

- [ ] **Step 8: Run focused tests and verify GREEN**

Run: `cd fantalol-backend && mvn -Dtest=StaticResourceIntegrationTest test`

Run: `node --test fantalol-frontend/tests/league-utils.test.js`

Expected: all focused tests pass.

---

### Task 4: Move Auction, Giornata, and Formation Behavior to the League Page

**Files:**

- Modify: `fantalol-frontend/js/league-detail.js`
- Modify: `fantalol-frontend/js/app.js`
- Modify: `fantalol-frontend/index.html`
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java`

**Interfaces:**

- Consumes: selected league and current user's selected-league fantasy team from Task 3.
- Consumes existing auction endpoints, `/api/matchdays`, `/api/fanta-teams/{id}/formazioni`, and `/api/leagues/{id}/rosters/complete-randomly`.
- Produces: fully functional league-scoped `Asta` and `Giornate` sections without homepage management duplicates.

- [ ] **Step 1: Change static integration assertions to require management controls on `lega.html` and `league-detail.js`**

Update the existing auction-control test so it requests `/lega.html` and `/js/league-detail.js`. Add assertions for `/auction/${action}`, `/rosters/complete-randomly`, `/formazioni`, and `/matchdays`. Add negative assertions showing `index.html` no longer owns `auction-dialog`, `formation-dialog`, or `matchday-dialog`.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `cd fantalol-backend && mvn -Dtest=StaticResourceIntegrationTest test`

Expected: FAIL because the behavior still resides in `app.js` or is not complete in `league-detail.js`.

- [ ] **Step 3: Port auction behavior using selected-league state**

Adapt the existing auction refresh/render/start/bid/release/open/close/random-completion functions. Use the current user's team in the selected league; if none exists, show a read-only message instead of controls. Start the 500 ms polling interval only when Asta becomes active, prevent overlapping refreshes, and clear it on section change, dialog close, and `beforeunload`.

- [ ] **Step 4: Port giornata and formation behavior**

Render selected-league matchdays in the Giornate section. Show `+ Giornata` only to the global administrator or league creator. Show the formation action only when the current user owns a selected-league fantasy team with at least five roster entries and an open matchday exists. Preserve the five-role selection, captain options, payload shape, validation messages, and successful refresh/toast behavior.

- [ ] **Step 5: Remove management duplication from the homepage**

Delete homepage auction/matchday/formation markup and their event handlers, timer state, and management-specific functions. Retain creation/joining, authentication, public player browsing, user-directory behavior, league launcher rendering, and rules behavior.

- [ ] **Step 6: Run the focused regression tests**

Run: `cd fantalol-backend && mvn -Dtest=StaticResourceIntegrationTest test`

Run: `node --test fantalol-frontend/tests/league-utils.test.js`

Expected: all tests pass.

---

### Task 5: Full Verification and Responsive Review

**Files:**

- Modify only files proven necessary by verification failures.

**Interfaces:**

- Verifies all interfaces produced by Tasks 1–4.

- [ ] **Step 1: Run the complete backend suite**

Run: `cd fantalol-backend && mvn test`

Expected: BUILD SUCCESS with 0 failures and 0 errors.

- [ ] **Step 2: Run all frontend utility tests**

Run: `node --test fantalol-frontend/tests/*.test.js`

Expected: all tests pass.

- [ ] **Step 3: Confirm no fabricated LEC data exists**

Run: `rg -n "demo|mock|fixture|fake" fantalol-frontend/lega.html fantalol-frontend/js/league-detail.js fantalol-frontend/js/lec-data-source.js`

Expected: no result containing fabricated standings or performance data.

- [ ] **Step 4: Confirm homepage/detail responsibility boundaries**

Run: `rg -n "auction-dialog|formation-dialog|matchday-dialog" fantalol-frontend/index.html fantalol-frontend/lega.html`

Expected: all three dialog IDs appear only in `lega.html`.

- [ ] **Step 5: Perform manual responsive and interaction checks**

At desktop, tablet, and mobile widths verify: rules dialog scrolling; clickable league cards; direct invalid-ID state; sidebar-to-horizontal navigation transition; full roster visibility; alphabetical `0 pt` ranking; auction polling lifecycle; giornata/formation permissions; LEC pending states; keyboard focus visibility; Escape-to-close dialogs; and absence of horizontal page overflow.

- [ ] **Step 6: Re-run both automated suites after any verification fix**

Run: `cd fantalol-backend && mvn test`

Run: `node --test fantalol-frontend/tests/*.test.js`

Expected: both commands pass with no failures.

---

### Task 6: Enlarge the Homepage Rules Button

**Files:**

- Modify: `fantalol-frontend/css/style.css`
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java`

**Interfaces:**

- Consumes: existing `.hero-primary-actions` and `.rules-trigger` selectors.
- Produces: a rules trigger matching the primary action's full width, minimum height, and prominent typography while retaining an outlined blue-violet secondary appearance.

- [ ] **Step 1: Add a failing stylesheet assertion**

Assert `/css/style.css` contains `.rules-trigger`, `width:100%`, `min-height:45px`, and `border:1px solid var(--lime)`.

- [ ] **Step 2: Run the focused static-resource test and verify RED**

Run the Docker-based `StaticResourceIntegrationTest` command used by the preceding tasks.

Expected: FAIL because the rules trigger is still a small underlined text control.

- [ ] **Step 3: Implement the larger secondary button**

Change `.rules-trigger` to full width with a 45px minimum height, a blue border, blue-violet translucent background, 12px display typography, and a filled blue-violet hover/focus state. Remove its underline treatment.

- [ ] **Step 4: Run focused and full verification**

Run the focused static-resource test, all frontend utility tests, JavaScript syntax checks, and the complete backend suite.

Expected: all commands pass.
