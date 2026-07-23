# Live Auction and Formation Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver stable 15-second custom bidding, block self-reraises, keep submitted lineups visible, and synchronize all league-page data automatically.

**Architecture:** Keep the Spring REST API authoritative for auction deadlines and bid validation. Extract browser-safe pure UI state helpers into `league-utils.js`, run a page-wide non-overlapping synchronization loop, and update the countdown independently from server-backed rendering so active form input is preserved.

**Tech Stack:** Java 17, Spring Boot 3.3, JUnit 5, Mockito, vanilla JavaScript, HTML/CSS, Node test runner.

## Global Constraints

- All new identifiers, helper names, comments, and code are in English.
- Existing user-facing interface messages remain in Italian.
- Do not use Git commands.
- The server `endsAt` timestamp remains authoritative.
- Automatic refresh must preserve focused controls, open dialogs, and unsaved values.

---

### Task 1: Server Auction Duration and Leader Validation

**Files:**
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/league/AuctionServiceTest.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/AuctionService.java`

**Interfaces:**
- Consumes: `AuctionStartRequest`, `AuctionBidRequest`, and locked `AuctionSession` entities.
- Produces: 15-second `endsAt` deadlines and `BusinessRuleException("Sei già il miglior offerente")` for a self-reraise.

- [ ] **Step 1: Add failing tests**

Add tests that capture `Instant before`, start or bid, capture `Instant after`, and assert `endsAt` lies between `before.plusSeconds(15)` and `after.plusSeconds(15)`. Add a separate test whose request team ID equals `highestBidder.id` and assert the exact business-rule message.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `cd fantalol-backend && mvn -q -Dtest=AuctionServiceTest test`

Expected: duration assertions and current-leader rejection fail against the existing 10-second implementation.

- [ ] **Step 3: Implement the minimal server changes**

Change `SECONDS_PER_BID` to `15`. In `bid`, after loading and authorizing the requested fantasy team and before minimum/credit/roster validation, compare `auction.getHighestBidder().getId()` with `team.getId()` and throw `BusinessRuleException("Sei già il miglior offerente")` when equal.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run: `cd fantalol-backend && mvn -q -Dtest=AuctionServiceTest test`

Expected: all `AuctionServiceTest` tests pass.

### Task 2: Testable Frontend State Helpers

**Files:**
- Modify: `fantalol-frontend/tests/league-utils.test.js`
- Modify: `fantalol-frontend/js/league-utils.js`

**Interfaces:**
- Produces: `auctionViewState(auction, activeTeam, draftAmount)`, `remainingAuctionSeconds(endsAt, now)`, and `mergeBidDraft(previousDraft, auction, activeTeam)`.
- Consumes: plain auction and fantasy-team response objects.

- [ ] **Step 1: Add failing helper tests**

Test that the leader cannot bid, a non-leader receives the next minimum, remaining seconds derives from `endsAt`, and a valid custom draft survives refresh while an obsolete draft is raised to the new minimum.

- [ ] **Step 2: Run the helper tests and verify RED**

Run: `node --test fantalol-frontend/tests/league-utils.test.js`

Expected: failures report missing helper functions.

- [ ] **Step 3: Implement and export the pure helpers**

Implement the helpers without DOM access. Export them through the existing CommonJS/browser module pattern used by `league-utils.js`.

- [ ] **Step 4: Run the helper tests and verify GREEN**

Run: `node --test fantalol-frontend/tests/league-utils.test.js`

Expected: all helper and existing utility tests pass.

### Task 3: Stable Countdown and Page-Wide Synchronization

**Files:**
- Create: `fantalol-frontend/tests/league-detail-behavior.test.js`
- Modify: `fantalol-frontend/js/league-detail.js`

**Interfaces:**
- Consumes: the Task 2 helpers and current REST endpoints.
- Produces: `startPageSynchronization`, `stopPageSynchronization`, `synchronizeLeaguePage`, `startCountdown`, `renderCountdown`, and stable auction rendering.

- [ ] **Step 1: Add failing source-behavior tests**

Assert the page starts synchronization from `initialise`, does not stop it when navigation changes, contains separate synchronization and countdown timers, uses `highestBidderId` to suppress the bid form, renders `Sei il miglior offerente`, and contains the 15-second explanatory copy.

- [ ] **Step 2: Run the frontend tests and verify RED**

Run: `node --test fantalol-frontend/tests/*.test.js`

Expected: the new behavior test fails against section-only polling and 10-second copy.

- [ ] **Step 3: Implement stable live state**

Replace section-scoped auction polling with a page-wide non-overlapping synchronization loop. Fetch leagues, league teams, matchdays, and active auction. Preserve the bid draft in state and render the countdown by updating only `.countdown`. Trigger an immediate synchronization when the countdown reaches zero and after every mutation. Do not reset the loop from `setSection`.

- [ ] **Step 4: Run frontend tests and syntax validation**

Run: `node --test fantalol-frontend/tests/*.test.js && node --check fantalol-frontend/js/league-detail.js`

Expected: all tests pass and syntax validation exits successfully.

### Task 4: Persisted Formation Summary in the Dialog

**Files:**
- Modify: `fantalol-frontend/tests/league-detail-behavior.test.js`
- Modify: `fantalol-frontend/lega.html`
- Modify: `fantalol-frontend/js/league-detail.js`
- Modify: `fantalol-frontend/css/league-detail.css`

**Interfaces:**
- Consumes: `FormationResponse` returned by the save and history APIs.
- Produces: `renderFormationSummary`, saved-state dialog markup, and an edit action for an editable open matchday.

- [ ] **Step 1: Add failing formation-dialog tests**

Assert that submission stores the response, does not call `close()` on the dialog, renders a saved five-role summary, includes an edit action, and triggers an immediate page synchronization.

- [ ] **Step 2: Run the focused frontend tests and verify RED**

Run: `node --test fantalol-frontend/tests/league-detail-behavior.test.js`

Expected: failures show that the current handler closes the dialog and has no saved summary.

- [ ] **Step 3: Implement the saved formation view**

Use the save response as authoritative dialog state. Keep the dialog open, hide selectors in saved view, render the five players sorted by role, and provide `Modifica formazione` to restore selectors while editable. When reopening, select the persisted formation matching the chosen matchday before falling back to the latest valid formation.

- [ ] **Step 4: Run frontend tests and syntax validation**

Run: `node --test fantalol-frontend/tests/*.test.js && node --check fantalol-frontend/js/league-detail.js`

Expected: all frontend tests pass.

### Task 5: Full Regression Verification

**Files:**
- Verify: all modified backend and frontend files.

**Interfaces:**
- Consumes: the completed implementation.
- Produces: fresh evidence that backend, frontend, and packaging are valid.

- [ ] **Step 1: Run the complete backend test suite**

Run: `cd fantalol-backend && mvn test`

Expected: BUILD SUCCESS with zero test failures.

- [ ] **Step 2: Run all frontend tests and JavaScript syntax checks**

Run: `node --test fantalol-frontend/tests/*.test.js && node --check fantalol-frontend/js/league-utils.js && node --check fantalol-frontend/js/league-detail.js`

Expected: every test passes and both syntax checks exit successfully.

- [ ] **Step 3: Build the deployable backend artifact**

Run: `cd fantalol-backend && mvn -q -DskipTests package`

Expected: exit code 0 and the frontend resources are packaged into the Spring Boot artifact.

