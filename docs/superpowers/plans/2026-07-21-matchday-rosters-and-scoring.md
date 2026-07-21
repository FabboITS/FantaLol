# Matchday Rosters and Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze league size at the first Giornata, coordinate auction and matchday availability, preserve effective five-player formations, and score fantasy teams using the average of the five rule-based player scores.

**Architecture:** Persist the frozen roster format on `League`, keep the league auction as the lock for the single open `Matchday`, and resolve every team's effective formation in the backend. `MatchdayService` materializes carried or automatic formations when closing a day, while DTOs expose scoring history and UI capabilities to the league page.

**Tech Stack:** Java 17, Spring Boot 3.3, Spring Data JPA, Jakarta Validation, JUnit 5, Mockito, AssertJ, H2/MySQL, static HTML/CSS/JavaScript.

## Global Constraints

- Do not run any Git command and do not add commit steps.
- Freeze the participant threshold when the first Giornata is created: 1–5 teams use two players per role; 6+ use one.
- Every effective formation has exactly five players, one per role.
- An auction-open league locks its open Giornata.
- Player score is `kills * 3 + assists * 2 - deaths * 2 + floor(cs / 100) + (win ? 3 : 0)` and may be negative.
- Team matchday score is the arithmetic average of five active-player scores; missing player statistics contribute zero.
- Remove base-vote, MVP, and captain effects from active behavior.
- Follow test-driven development: add one focused failing test, run it and confirm the expected failure, implement minimally, then rerun it.

---

## File Structure

- `league/League.java`: persistent frozen participant count and competition-started state.
- `league/RosterPolicy.java`: map the frozen participant count to roster limits.
- `league/FantaTeamService.java`: reject joins after competition starts.
- `league/dto/LeagueResponse.java`: expose the frozen format and enrollment state.
- `matchday/MatchdayService.java`: create/lock lifecycle, statistics, effective formation resolution, averaging, and closing.
- `matchday/FormationService.java`: manual small-league formation commands and effective formation queries.
- `matchday/Formation.java`: immutable-per-day formation snapshot and source.
- `matchday/FormationSource.java`: `SUBMITTED`, `CARRIED`, `AUTOMATIC`, or `MISSING` semantics.
- matchday DTOs: accept the new statistics and return player/team scoring history.
- `fantalol-frontend/lega.html`, `js/league-detail.js`, and `css/league-detail.css`: roster view/edit controls and score history.
- existing unit/integration tests: verify each business boundary and served frontend contract.

### Task 1: Freeze League Format and Lock Enrollment

**Files:**
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/League.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/RosterPolicy.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/FantaTeamService.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/dto/LeagueResponse.java`
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/league/RosterPolicyTest.java`
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/league/FantaTeamServiceTest.java`

**Interfaces:**
- Produces: `League.freezeParticipantCount(int)`, `League.isCompetitionStarted()`, `RosterPolicy.forLeague(League)`, and response fields `participantCount`, `competitionStarted`, `maxRosterSize`, `maxPerRole`.

- [ ] **Step 1: Write failing threshold and frozen-count tests**

Add cases proving `5 -> Limits(10, 2)`, `6 -> Limits(5, 1)`, and that a stored `participantCount=5` remains small even if the repository later counts six teams. Add a join test with `competitionStarted=true` expecting `BusinessRuleException` containing `iniziata`.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
cd fantalol-backend && mvn -Dtest=RosterPolicyTest,FantaTeamServiceTest test
```

Expected: failures because the frozen fields and 5/6 policy do not exist and joining is still allowed.

- [ ] **Step 3: Implement frozen league state**

Add nullable `Integer participantCount` to `League`, plus:

```java
public boolean isCompetitionStarted() {
    return participantCount != null;
}

public void freezeParticipantCount(int count) {
    if (participantCount == null) participantCount = count;
}
```

Update `RosterPolicy.forLeague` to prefer the frozen count and otherwise use the repository count:

```java
int count = league.getParticipantCount() != null
        ? league.getParticipantCount()
        : Math.toIntExact(fantaTeamRepository.countByLeagueId(league.getId()));
return count <= 5 ? new Limits(10, 2) : new Limits(5, 1);
```

Reject joins when `league.isCompetitionStarted()`. Extend `LeagueResponse.from` with the backend-calculated capability fields; do not make the browser recompute policy.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: all selected tests pass.

### Task 2: Couple Giornata Creation and Auction Locking

**Files:**
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/MatchdayRepository.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/MatchdayService.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/dto/MatchdayResponse.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/LeagueService.java`
- Create: `fantalol-backend/src/test/java/com/fantalol/backend/matchday/MatchdayLifecycleServiceTest.java`

**Interfaces:**
- Consumes: `League.freezeParticipantCount(int)` from Task 1.
- Produces: `MatchdayRepository.existsByLeagueIdAndChiusaFalse(Long)` and `MatchdayResponse.auctionLocked`.

- [ ] **Step 1: Write lifecycle tests**

Cover these independent behaviors:

```java
@Test void creatingFirstMatchdayFreezesFiveParticipantsAndOpensAuction() { }
@Test void creatingMatchdayWithSixParticipantsFreezesLargeFormat() { }
@Test void rejectsSecondOpenMatchday() { }
@Test void rejectsStatsAndClosingWhileAuctionIsOpen() { }
@Test void reopeningAuctionDoesNotChangeClosedMatchday() { }
```

Mock repository calls with real `League` and `Matchday` objects and assert saved state and exact business-rule messages.

- [ ] **Step 2: Run the new test and verify RED**

```bash
cd fantalol-backend && mvn -Dtest=MatchdayLifecycleServiceTest test
```

Expected: compilation/test failures for missing lifecycle behavior.

- [ ] **Step 3: Implement lifecycle rules**

On create: reject another unclosed Giornata, freeze `countByLeagueId`, set `auctionOpen=true`, save the league, then save the day. In statistics entry and day closing, reject when `matchday.getLeague().isAuctionOpen()`. Expose `auctionLocked` in `MatchdayResponse` as `!chiusa && league.auctionOpen`.

Keep `LeagueService.openAuction` limited to leagues with an unclosed Giornata and ensure closing a completed Giornata is not undone by later auction changes.

- [ ] **Step 4: Run lifecycle and league-auction tests**

```bash
cd fantalol-backend && mvn -Dtest=MatchdayLifecycleServiceTest,LeagueAuctionPhaseServiceTest test
```

Expected: all selected tests pass.

### Task 3: Replace Player Scoring With the Rules Formula

**Files:**
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/FantaScoreCalculator.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/PlayerStat.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/dto/PlayerStatRequest.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/dto/PlayerStatResponse.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/MatchdayService.java`
- Rewrite: `fantalol-backend/src/test/java/com/fantalol/backend/matchday/FantaScoreCalculatorTest.java`

**Interfaces:**
- Produces: `double FantaScoreCalculator.calcola(int kills, int morti, int assist, int cs, boolean vittoria)` and request fields `(lecPlayerId, kills, morti, assist, cs, vittoria)`.

- [ ] **Step 1: Write failing formula tests**

Use exact assertions:

```java
assertThat(calculator.calcola(2, 1, 3, 250, true)).isEqualTo(15.0);
assertThat(calculator.calcola(0, 4, 0, 99, false)).isEqualTo(-8.0);
assertThat(calculator.calcola(0, 0, 0, 100, false)).isEqualTo(1.0);
assertThat(calculator.calcola(0, 0, 0, 199, false)).isEqualTo(1.0);
assertThat(calculator.calcola(0, 0, 0, 200, false)).isEqualTo(2.0);
```

- [ ] **Step 2: Run calculator tests and verify RED**

```bash
cd fantalol-backend && mvn -Dtest=FantaScoreCalculatorTest test
```

Expected: failures because the current formula uses base vote, fractional bonuses, MVP, and a zero floor.

- [ ] **Step 3: Implement the minimal score model**

Use:

```java
public double calcola(int kills, int morti, int assist, int cs, boolean vittoria) {
    return kills * 3.0 + assist * 2.0 - morti * 2.0
            + Math.floorDiv(cs, 100) + (vittoria ? 3.0 : 0.0);
}
```

Add non-null, non-negative `cs` with default zero. Remove base-vote and MVP from active DTOs and service assignments. Keep legacy database columns nullable only if needed for schema compatibility; they must not affect `fantavoto`.

- [ ] **Step 4: Run calculator tests and compile all backend tests**

```bash
(cd fantalol-backend && mvn -Dtest=FantaScoreCalculatorTest test)
(cd fantalol-backend && mvn -DskipTests compile)
```

Expected: tests pass and compilation succeeds with all DTO consumers updated.

### Task 4: Resolve Submitted, Carried, Automatic, and Missing Formations

**Files:**
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/FormationSource.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/Formation.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/FormationRepository.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/FormationService.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/dto/FormationRequest.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/dto/FormationResponse.java`
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/matchday/FormationServiceTest.java`

**Interfaces:**
- Produces: `FormationSource`, `FormationService.resolveEffectiveFormation(FantaTeam, Matchday)`, and detailed player entries in `FormationResponse`.

- [ ] **Step 1: Add failing formation-policy tests**

Add tests that small leagues accept exactly one owned player per role, reject edits during an open auction, reject manual editing in a large league, carry the newest earlier submitted formation, automatically use a complete large-league Rosa, and return `MISSING` when no first formation exists.

- [ ] **Step 2: Run formation tests and verify RED**

```bash
cd fantalol-backend && mvn -Dtest=FormationServiceTest test
```

Expected: failures for missing format/auction checks and effective-formation resolution.

- [ ] **Step 3: Implement formation resolution**

Remove `capitano` from request validation and active response behavior. Persist a non-null `FormationSource source`. Add a repository query ordered by matchday number descending for the latest earlier `SUBMITTED` formation.

Resolution order must be exact:

```text
existing formation for this team/day
large league -> snapshot the five currently owned role-valid players as AUTOMATIC
small league with prior submitted formation -> copy its five players as CARRIED
small league without prior submitted formation -> MISSING with empty players
```

Manual save is available only for small leagues, only while the day is open and auction unlocked, validates five distinct currently owned players with all roles, and marks the record `SUBMITTED`.

- [ ] **Step 4: Run formation tests and verify GREEN**

Run the Step 2 command. Expected: all formation tests pass.

### Task 5: Average Five Players and Expose Historical Results

**Files:**
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/MatchdayService.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/FormationService.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/dto/FormationResponse.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/dto/FantaTeamResponse.java`
- Create: `fantalol-backend/src/test/java/com/fantalol/backend/matchday/MatchdayScoringServiceTest.java`

**Interfaces:**
- Consumes: effective formation resolution from Task 4 and player `fantavoto` from Task 3.
- Produces: per-player score entries, `matchdayScore`, and `FantaTeamResponse.punti` as the sum of closed-day averages.

- [ ] **Step 1: Write failing team-scoring tests**

Cover: scores `10,8,6,4,2` average to `6`; four recorded players plus one missing stat still divide by five; negative values remain negative; a missing first formation stores zero; carried and automatic formations are materialized; accumulated points sum only closed days.

- [ ] **Step 2: Run scoring tests and verify RED**

```bash
cd fantalol-backend && mvn -Dtest=MatchdayScoringServiceTest test
```

Expected: failures because current closing only visits submitted formations, sums scores, and doubles a captain.

- [ ] **Step 3: Implement close-day materialization and averaging**

Iterate every fantasy team in the league. Resolve its effective formation, sum five player stats using zero for missing rows, divide by `5.0`, and persist `punteggioTotale`. For `MISSING`, persist zero. Never multiply a captain. Mark the day closed only after all snapshots/results save successfully.

Return detailed player IDs, nicknames, roles, per-day scores, source, and total in formation history. Calculate `FantaTeamResponse.punti` from persisted closed formations so all clients share one authoritative ranking value.

- [ ] **Step 4: Run matchday and formation suites**

```bash
cd fantalol-backend && mvn -Dtest=MatchdayScoringServiceTest,FormationServiceTest,FantaScoreCalculatorTest test
```

Expected: all selected tests pass.

### Task 6: Build the League-Page Rosa Experience

**Files:**
- Modify: `fantalol-frontend/lega.html`
- Modify: `fantalol-frontend/js/league-detail.js`
- Modify: `fantalol-frontend/css/league-detail.css`
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java`

**Interfaces:**
- Consumes: league format/capability fields, matchday `auctionLocked`, formation history, per-player scores, and `FantaTeamResponse.punti`.

- [ ] **Step 1: Add failing served-frontend contract tests**

Assert that served `lega.html` contains a roster-history container and no captain input. Assert that served JavaScript contains `Modifica formazione`, `Vedi la tua rosa`, renders `player.matchdayScore`, uses backend `team.punti`, and does not send `capitanoId`.

- [ ] **Step 2: Run static resource tests and verify RED**

```bash
cd fantalol-backend && mvn -Dtest=StaticResourceIntegrationTest test
```

Expected: new assertions fail against the existing captain dialog and placeholder team points.

- [ ] **Step 3: Implement the roster dialog/view**

Replace the captain field with:

```html
<div id="formation-status" class="formation-status"></div>
<div id="formation-roles" class="formation-roles"></div>
<div id="roster-history" class="roster-history"></div>
```

Render select controls only when `league.maxPerRole === 2`, the current day is unlocked, and the viewer owns the team. Render read-only role cards otherwise. Load effective formation/history when the day selector or active team changes. Show source-aware copy for submitted, carried, automatic, and missing states. Display each player score and the five-player average for every closed day.

Use backend points in both ranking and team cards:

```javascript
const points = Number(team.punti ?? 0);
```

The small-league submit payload contains only `matchdayId` and five `titolariIds`.

- [ ] **Step 4: Add responsive styles**

Style role cards, editable selectors, source/status copy, score columns, negative values, and the history table using existing theme variables. At narrow widths, stack each day's player rows without horizontal page overflow.

- [ ] **Step 5: Synchronize served frontend resources**

Run the repository's existing Maven resource phase rather than manually maintaining divergent copies:

```bash
cd fantalol-backend && mvn process-resources
```

Expected: the backend-served static resources match `fantalol-frontend`.

- [ ] **Step 6: Run frontend contract tests and JavaScript syntax check**

```bash
cd fantalol-backend && mvn -Dtest=StaticResourceIntegrationTest test
node --check fantalol-frontend/js/league-detail.js
```

Expected: tests pass and Node reports no syntax errors.

### Task 7: Update Rules and Run Full Verification

**Files:**
- Modify: `Rules.md`
- Modify: `fantalol-frontend/index.html` if its embedded rules are maintained separately.
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java`

**Interfaces:**
- Documents all behavior produced by Tasks 1–6.

- [ ] **Step 1: Add a failing rules-content assertion**

Assert that the served rules mention the 1–5/6+ split, last-formation reuse, first-formation zero, the five-player average, and do not mention captain doubling.

- [ ] **Step 2: Run the rules assertion and verify RED**

```bash
cd fantalol-backend && mvn -Dtest=StaticResourceIntegrationTest#homeContainsCompleteRulesDialogAndLeagueDetailNavigation test
```

Expected: failure because the current rules omit the new lifecycle and average.

- [ ] **Step 3: Update canonical and displayed rules**

Make `Rules.md` explicitly state the exact player formula, five-player average, missing-stat zero, small/large format split, enrollment lock, auction lock, carried lineup, and missing-first-lineup zero. Synchronize the visible rules dialog without changing unrelated rules.

- [ ] **Step 4: Run the complete verification suite**

```bash
(cd fantalol-backend && mvn test)
node --test fantalol-frontend/tests/*.test.js
node --check fantalol-frontend/js/league-detail.js
```

Expected: all Maven and Node tests pass with no JavaScript syntax errors.

- [ ] **Step 5: Perform a manual browser smoke test**

Verify one five-team league and one six-team league: first-Giornata creation locks enrollment and opens auction; auction close exposes the correct button; small-league selections persist/carry; large-league Rosa is read-only; player history and averages display; ranking totals match closed-day averages.
