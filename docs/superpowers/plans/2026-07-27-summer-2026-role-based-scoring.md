# Summer 2026 Role-Based Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the Summer 2026 role-based fantasy scoring system while preserving the corrected roster and historical results.

**Architecture:** Add a focused `scoring` package that owns versioned per-game calculation, imported game statistics, series aggregation, matchday totals, conflict handling, and ranking recalculation. Keep the corrected current workspace as the roster authority, integrate with existing matchday and formation services through explicit interfaces, and render only backend-calculated results in the static frontend.

**Tech Stack:** Java 17, Spring Boot 3.3, Spring Data JPA, MySQL/H2, JUnit 5, Mockito, AssertJ, HTML5, CSS, vanilla JavaScript, Node test runner.

## Global Constraints

- Do not run Git commands.
- Do not replace or revert corrected Summer 2026 players, teams, quotations, portraits, or seed data.
- Use English for identifiers, comments, API names, and test names.
- Use `SUMMER_2026_V1` for the new formula and preserve the historical formula for older results.
- Keep the backend authoritative for every calculation.
- Do not add the React prototype, unrelated repository cleanup, or configurable per-league coefficients.

---

### Task 1: Versioned Per-Game Score Calculator

**Files:**
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/scoring/ScoringFormulaVersion.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/scoring/RoleScoreWeights.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/scoring/GameScoreCalculator.java`
- Test: `fantalol-backend/src/test/java/com/fantalol/backend/scoring/GameScoreCalculatorTest.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/FantaScoreCalculator.java`
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/matchday/FantaScoreCalculatorTest.java`

**Interfaces:**
- Consumes: `PlayerRole`.
- Produces: `double GameScoreCalculator.calculate(PlayerRole role, int kills, int deaths, int assists, int cs, boolean win)`.
- Produces: `RoleScoreWeights.forRole(PlayerRole)` and `ScoringFormulaVersion.SUMMER_2026_V1`.

- [ ] **Step 1: Write failing coefficient and continuous-CS tests**

Add assertions covering all five approved coefficient rows, fractional CS, the
win bonus, and negative results:

```java
assertThat(calculator.calculate(PlayerRole.TOP, 1, 1, 1, 100, true)).isEqualTo(7.25);
assertThat(calculator.calculate(PlayerRole.JUNGLE, 1, 1, 1, 100, true)).isEqualTo(6.95);
assertThat(calculator.calculate(PlayerRole.MID, 1, 1, 1, 100, true)).isEqualTo(7.0);
assertThat(calculator.calculate(PlayerRole.ADC, 1, 1, 1, 100, true)).isEqualTo(6.85);
assertThat(calculator.calculate(PlayerRole.SUPPORT, 1, 1, 1, 100, true)).isEqualTo(5.15);
assertThat(calculator.calculate(PlayerRole.TOP, 0, 0, 0, 50, false)).isEqualTo(0.625);
assertThat(calculator.calculate(PlayerRole.SUPPORT, 0, 4, 0, 0, false)).isEqualTo(-7.0);
```

- [ ] **Step 2: Run the new calculator test and verify RED**

Run:

```bash
docker run --rm -v /home/massimilianofabbo/Desktop/FantaLol:/workspace -v /tmp/fantaleague-m2:/root/.m2 -w /workspace/fantalol-backend maven:3.9.9-eclipse-temurin-17 mvn -q -Dtest=GameScoreCalculatorTest test
```

Expected: compilation failure because the scoring classes do not exist.

- [ ] **Step 3: Implement the immutable Summer 2026 coefficients**

Create one immutable mapping:

```java
TOP     -> (3.00, 2.00, 2.00, 1.25)
JUNGLE  -> (3.00, 2.25, 2.00, 0.70)
MID     -> (3.00, 2.00, 2.00, 1.00)
ADC     -> (3.25, 1.75, 2.25, 1.10)
SUPPORT -> (2.15, 2.55, 1.75, 0.20)
```

Use `cs / 100.0`, not integer division. Keep the existing historical calculator
as the legacy implementation and make compatibility naming delegate rather than
duplicate arithmetic.

- [ ] **Step 4: Run focused calculator tests and verify GREEN**

Run both calculator test classes and confirm every expected decimal and legacy
historical assertion passes.

### Task 2: Per-Game Statistics and Conflict-Safe Administration

**Files:**
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/scoring/OfficialSeries.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/scoring/OfficialGame.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/scoring/PlayerGameStat.java`
- Create: repository interfaces for all three entities.
- Create: `StatSource.java`, `ScoringDataStatus.java`, `GameStatService.java`, and DTOs under `scoring/dto`.
- Create: `GameStatAdminController.java`.
- Test: `PlayerGameStatTest.java` and `GameStatServiceTest.java`.

**Interfaces:**
- Consumes: corrected `LecPlayer` entities and `GameScoreCalculator`.
- Produces: one unique stat row for `(game_id, lec_player_id)`.
- Produces: `submitOracle(...)`, `submitManual(...)`, and `resolveConflict(...)`.

- [ ] **Step 1: Write failing domain tests**

Test that Oracle-only and manual-only submissions become effective, equal
candidates resolve automatically, unequal candidates remain conflicted, explicit
resolution selects the requested source, and the team-name snapshot remains
unchanged after the player's current team changes.

- [ ] **Step 2: Run the domain tests and verify RED**

Expected: compilation failure for missing scoring persistence types.

- [ ] **Step 3: Implement entities, repositories, DTOs, and service**

Store Oracle and manual candidates separately, including audit timestamps and
actor identity. Never overwrite one source with the other. Store
`teamNameSnapshot` when the game stat is created and enforce the database unique
constraint.

- [ ] **Step 4: Add validation tests**

Test rejection of negative kills, deaths, assists, or CS; an unknown player ID;
an unknown game ID; and resolving a source with no candidate.

- [ ] **Step 5: Implement explicit validation and run focused tests**

Return existing project-standard business or resource errors with clear English
administrative messages. Confirm all scoring-domain tests pass.

### Task 3: Oracle and PandaScore Summer Data Integration

**Files:**
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/integration/oracle/OracleElixirCsvImporter.java`
- Create: `OracleGameCsvIngestionService.java`, `OracleScheduledSyncService.java`, `OracleSyncHealth.java`, and `InMemoryMultipartFile.java`.
- Modify: `OracleElixirImportController.java`.
- Create: `SummerScheduleService.java` and `SummerScheduleSyncResult.java`.
- Modify: `PandaScoreAdminController.java`, `PandaScoreProperties.java`, and `application.yml`.
- Test: importer and schedule service tests using corrected roster nicknames.

**Interfaces:**
- Consumes: stable external player IDs where available; otherwise
  `LecPlayerRepository.findFirstByNicknameIgnoreCase`.
- Produces: idempotent Summer series, games, and Oracle stat candidates.

- [ ] **Step 1: Write failing corrected-roster import tests**

Use representative corrected players including `Soboro`, `Oscarinin`, `Daglas`,
`FIESTA`, `SlowQ`, `Hype`, `Skeanz`, and `Stend`. Assert that repeated imports do
not create duplicate games or player stats and that unknown/ambiguous mappings
are reported rather than inserted.

- [ ] **Step 2: Run integration-focused tests and verify RED**

Expected: failures because game-level ingestion and Summer schedule services are
absent.

- [ ] **Step 3: Implement idempotent ingestion**

Filter the expected competition and split, reject incomplete rows, map corrected
players, create historical team snapshots, and feed Oracle candidates through
`GameStatService`.

- [ ] **Step 4: Implement schedule synchronization**

Create series and games by stable provider identifiers, group them into
matchdays, and preserve existing entities on repeated synchronization.

- [ ] **Step 5: Run importer, schedule, and roster-correction tests**

Confirm scoring integration does not modify the roster synchronization behavior
or any quotation.

### Task 4: Series, Matchday, Fantasy-Team, and Historical Aggregation

**Files:**
- Create: `MatchdaySeries.java`, `MatchdaySeriesRepository.java`, and `MatchdayScoringEngine.java`.
- Modify: `Matchday.java`, `MatchdayRepository.java`, `MatchdayService.java`, and `MatchdayController.java`.
- Modify: `Formation.java`, `FormationService.java`, and response DTOs.
- Modify: `FantaTeam.java` and `FantaTeamResponse.java`.
- Test: `MatchdayScoringEngineTest.java`, `FantasyTeamPointsTest.java`, and existing matchday scoring tests.

**Interfaces:**
- Consumes: effective `PlayerGameStat` candidates and `GameScoreCalculator`.
- Produces: player series average, player matchday sum, five-player team average,
  accumulated closed-matchday total, and formula-version metadata.

- [ ] **Step 1: Write failing aggregation tests**

Test a player who appears in two of three games, two series in one matchday, a
missing active player's zero contribution with divisor five, and a fantasy team
with a negative total.

- [ ] **Step 2: Write failing historical-version test**

Create a pre-Summer result and assert recalculation uses the historical
`FantaScoreCalculator`; create a Summer result and assert
`SUMMER_2026_V1`.

- [ ] **Step 3: Run aggregation tests and verify RED**

Expected: failures because game-to-series and version-aware matchday aggregation
are not implemented.

- [ ] **Step 4: Implement the scoring engine**

Average only games with an actual player appearance, sum series results, insert
zero for an active player without statistics, always divide team totals by five,
and sum only closed matchdays into the overall ranking.

- [ ] **Step 5: Integrate recalculation and immutability**

Recalculate provisional results after accepted stat changes. Refuse finalization
when required data conflicts remain. Preserve finalized historical results
unless the explicit authorized correction path is used.

- [ ] **Step 6: Run all matchday, formation, and fantasy-team tests**

Confirm existing auction locking, formation carry-forward, automatic formations,
and ranking behavior still pass.

### Task 5: Public Rules and League Presentation

**Files:**
- Modify: `Rules.md`
- Modify: `README.md`
- Modify: `fantalol-frontend/index.html`
- Modify: `fantalol-frontend/lega.html`
- Modify: `fantalol-frontend/js/league-detail.js`
- Modify or create focused CSS only if needed.
- Test: `home-visuals.test.js` and `league-detail-behavior.test.js`.

**Interfaces:**
- Consumes: backend-provided player and fantasy-team score fields.
- Produces: consistent Italian rules copy and score presentation.

- [ ] **Step 1: Write failing frontend content tests**

Assert the public rules contain the five approved coefficient rows, continuous
CS explanation, `+3` win bonus, series averaging, and five-player team average.
Assert obsolete `MVP +3` and `VITTORIA +1` badges are absent.

- [ ] **Step 2: Run Node tests and verify RED**

Run:

```bash
node --test fantalol-frontend/tests/*.test.js
```

Expected: new content assertions fail against the historical public rules.

- [ ] **Step 3: Update all rules copies**

Use decimal commas in Italian prose and keep the mathematical meaning identical
to the backend coefficients. Remove the vague role-weight paragraph and replace
it with exact behavior.

- [ ] **Step 4: Update score rendering**

Render backend-provided values consistently without calculating coefficients in
JavaScript. Keep negative-score styling and historical matchday presentation.

- [ ] **Step 5: Run frontend tests and syntax checks**

Confirm Node tests and `node --check` pass for every modified JavaScript file.

### Task 6: Full Verification and Consistency Audit

**Files:**
- Modify tests or documentation only when a verification failure demonstrates a
  requirement gap.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: release-ready evidence without publishing or Git operations.

- [ ] **Step 1: Run the complete backend suite**

Run the Maven test suite in the approved Maven Docker image and require a zero
exit code.

- [ ] **Step 2: Run the complete frontend suite**

Run all Node tests and JavaScript syntax checks and require zero exit codes.

- [ ] **Step 3: Audit coefficient consistency**

Search source, tests, `Rules.md`, `README.md`, and `index.html` for every old and
new scoring coefficient. Confirm no active Summer rule retains Top `1.10`, ADC
death `2.00`, ADC CS `1.20`, or Support `2.50/2.50/2.00`.

- [ ] **Step 4: Audit corrected roster preservation**

Run the roster correction and asset-reference tests. Confirm the eight corrected
players and their portraits remain available and no obsolete roster entry is
restored.

- [ ] **Step 5: Report results**

Summarize files changed, formula behavior, test commands and outcomes, and any
remaining deployment action. Do not commit, push, merge, or update GitHub PR
state.

