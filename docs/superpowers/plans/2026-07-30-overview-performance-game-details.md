# Overview Fantasy Ranking and LEC Game Details Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show only fantasy teams and cumulative scores in Overview, and show selectable LEC series/game player details including the backend fantasy score in Performance.

**Architecture:** Keep the existing Spring/JPA synchronization and the nested `/api/lec/matches` contract. Extend `LecDataSnapshot.GamePlayer` with the persisted/calculated game score, then update the static frontend renderer so selectors operate on already loaded series/game data and Overview uses a compact team-only ranking.

**Tech Stack:** Spring Boot 3, Java records/Jackson, JUnit 5/AssertJ, vanilla HTML/CSS/JavaScript, Node test runner.

## Global Constraints

- The backend remains the sole authority for fantasy scores.
- Do not change formation windows, scoring coefficients, synchronization cadence, or official LEC standings.
- Do not add provider requests when changing the Performance selectors.
- Missing provider data must remain “In attesa” and must not become a fabricated zero.

---

### Task 1: Extend per-game backend data with fantasy score

**Files:**
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/LecDataSnapshot.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/LecDataParser.java`
- Test: `fantalol-backend/src/test/java/com/fantalol/backend/integration/lec/LecDataParserTest.java`

**Interfaces:**
- `LecDataSnapshot.GamePlayer` produces a `Double fantasyScore` field after `perfectKda`.
- `LecDataParser.gamePlayer` populates that field from `PlayerRow.fantasyScore`.
- `LecDataParser.persistedRow` continues supplying the persisted statistic score.

- [ ] **Step 1: Write the failing parser assertion**

  Extend `buildsStandingsPerformancesChampionPicksAndPerGameRows` to select Caps and assert `fantasyScore()` equals the score calculated from the sample row.

- [ ] **Step 2: Run the focused test and verify it fails**

  Run:

  ```bash
  docker run --rm -v /tmp/fantalol-plan-m2:/root/.m2 -v /home/massimiliano/FantaLol:/workspace -w /workspace/fantalol-backend maven:3.9-eclipse-temurin-17 mvn -q -Dtest=LecDataParserTest test
  ```

  Expected: compilation failure because `GamePlayer.fantasyScore()` does not exist.

- [ ] **Step 3: Implement the minimal record/parser change**

  Add `Double fantasyScore` to `GamePlayer` and pass `row.fantasyScore` from `gamePlayer` without changing any calculations or filters.

- [ ] **Step 4: Run the focused test and verify it passes**

  Run the same Maven command; expected result is PASS.

- [ ] **Step 5: Commit the backend contract change**

  ```bash
  git add fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/LecDataSnapshot.java fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/LecDataParser.java fantalol-backend/src/test/java/com/fantalol/backend/integration/lec/LecDataParserTest.java
  git commit -m "feat: expose fantasy score in game players"
  ```

### Task 2: Simplify Overview to a team-only ranking

**Files:**
- Modify: `fantalol-frontend/js/league-detail.js`
- Modify: `fantalol-frontend/lega.html` only if the existing Overview placeholder needs copy adjustment.
- Test: `fantalol-frontend/tests/league-detail-behavior.test.js`

**Interfaces:**
- `renderRanking` continues to render `#fantasy-ranking` from the cumulative ranking response.
- `renderTeams` remains unchanged and continues to render players only in the Teams section.

- [ ] **Step 1: Write the failing frontend assertions**

  Assert the Overview renderer uses `renderCumulativeRanking` and that its ranking markup does not include roster/player iteration. Assert the Teams renderer still contains `roster-list`.

- [ ] **Step 2: Run the focused frontend test and verify it fails**

  Run:

  ```bash
  node --test tests/league-detail-behavior.test.js
  ```

  Expected: FAIL if Overview still renders team cards with roster content or the ranking helper is not the sole Overview path.

- [ ] **Step 3: Implement the minimal Overview rendering change**

  Keep `renderRanking()` bound to the cumulative ranking list and ensure no player/roster HTML is injected into `#fantasy-ranking`. Preserve rank, fantasy team name, provisional state, slot averages, and overall points; leave `renderTeams()` as the player-bearing view.

- [ ] **Step 4: Run the focused frontend test and verify it passes**

  Run the same Node command; expected result is PASS.

- [ ] **Step 5: Commit the Overview change**

  ```bash
  git add fantalol-frontend/js/league-detail.js fantalol-frontend/lega.html fantalol-frontend/tests/league-detail-behavior.test.js
  git commit -m "feat: keep Overview focused on fantasy teams"
  ```

### Task 3: Render complete selectable series/game performance details

**Files:**
- Modify: `fantalol-frontend/js/league-detail.js`
- Modify: `fantalol-frontend/css/league-detail.css`
- Test: `fantalol-frontend/tests/league-detail-behavior.test.js`

**Interfaces:**
- `renderLecMatches(data)` populates the series selector and selects the first game.
- `renderSelectedMatch()` repopulates the game selector and renders the first game of the selected series.
- `renderSelectedGame()` renders champion, nickname/role, K/D/A, CS or Vision Score, and `fantasyScore` for every returned player.

- [ ] **Step 1: Write failing renderer assertions**

  Assert the frontend source references `player.fantasyScore`, has both selectors, and labels the game score. Assert the responsive game row has a dedicated score column/class.

- [ ] **Step 2: Run the focused frontend test and verify it fails**

  Run:

  ```bash
  node --test tests/league-detail-behavior.test.js
  ```

  Expected: FAIL because the current renderer does not print `fantasyScore`.

- [ ] **Step 3: Implement the minimal rendering and CSS**

  Add an explicit `Fanta`/`Fantapunteggio` value to each game-player row, formatting numeric scores consistently and showing `In attesa` for null values. Keep support rows on Vision Score and non-support rows on CS. Add only the grid rules needed for the new score column and mobile wrapping.

- [ ] **Step 4: Run focused and full frontend tests**

  ```bash
  node --test tests/league-detail-behavior.test.js
  node --test tests/*.test.js
  ```

  Expected: all frontend tests pass.

- [ ] **Step 5: Commit the Performance UI change**

  ```bash
  git add fantalol-frontend/js/league-detail.js fantalol-frontend/css/league-detail.css fantalol-frontend/tests/league-detail-behavior.test.js
  git commit -m "feat: show per-game fantasy performance"
  ```

### Task 4: Full verification and handoff

**Files:**
- No production files; inspect the final diff and generated artifacts only.

- [ ] **Step 1: Run the complete backend suite**

  ```bash
  docker run --rm -v /tmp/fantalol-final-m2:/root/.m2 -v /home/massimiliano/FantaLol:/workspace -w /workspace/fantalol-backend maven:3.9-eclipse-temurin-17 mvn -q test
  ```

- [ ] **Step 2: Run the complete frontend suite**

  ```bash
  node --test fantalol-frontend/tests/*.test.js
  ```

- [ ] **Step 3: Clean generated target changes and inspect the final diff**

  Restore tracked `fantalol-backend/target` files, remove only untracked generated files under that directory, then run `git diff --check` and `git status --short`.

- [ ] **Step 4: Report deployment handoff**

  State the final commit(s), test results, and that Render must deploy `main` before the new Overview and Performance UI is visible.

