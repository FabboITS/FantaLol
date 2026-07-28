# Cumulative Summer Fantasy Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist complete LEC Summer player-game statistics, attribute them through time-bound fantasy lineups, and publish durable cumulative player and fantasy-team averages with automatic and administrator-triggered synchronization.

**Architecture:** Oracle and PandaScore data are normalized into durable JPA entities instead of an in-memory snapshot. Immutable effective lineup periods identify the active player for each fantasy-team role at game time, while query services derive cumulative player, slot, and team projections from per-game scores. The scheduler and ADMIN actions share one idempotent synchronization service; manual overrides retain source values and a minimal audit trail.

**Tech Stack:** Java 17, Spring Boot 3.3, Spring Data JPA, Spring Security/JWT, MySQL 8, H2/JUnit 5/Mockito/AssertJ, Apache Commons CSV, static HTML/CSS/JavaScript, Node test runner.

## Global Constraints

- Technical identifiers and implementation code are English.
- User-facing copy and regulation text are Italian.
- Use `Europe/Rome` for lineup-window boundaries and daylight-saving transitions.
- Import only `league=LEC`, `split=Summer`, `datacompleteness=complete`.
- Backfill begins at `2026-07-24T00:00:00+02:00[Europe/Rome]`.
- A player who does not play produces no score observation.
- Bench players retain individual evaluations but never contribute while benched.
- Provider plus external game ID and provider game plus player are unique.
- Synchronization and backfill are idempotent.
- Manual overrides survive provider synchronization until explicitly restored.
- Persist last-known-good data and report PandaScore and Oracle failures independently.
- Do not add a numeric fantasy-team score until all five role slots have at least one eligible observation.

---

### Task 1: Durable Oracle player-game model and parser

**Files:**
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/oracle/ProviderGame.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/oracle/ProviderGameRepository.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/oracle/ProviderPlayerGameStat.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/oracle/ProviderPlayerGameStatRepository.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/oracle/OracleGameBatch.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/oracle/OraclePlayerGameRow.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/oracle/OracleElixirGameParser.java`
- Test: `fantalol-backend/src/test/java/com/fantalol/backend/integration/oracle/OracleElixirGameParserTest.java`

**Interfaces:**
- Consumes: Oracle annual CSV text and `GameScoreCalculator.calculate(PlayerRole, int, int, int, int, int, boolean)`.
- Produces: `List<OracleGameBatch> OracleElixirGameParser.parse(String csv, String league, String split)`; repositories for durable source-of-truth rows.

- [ ] **Step 1: Write parser tests for complete LEC Summer games**

Create tests using a minimal CSV with `gameid,date,league,split,datacompleteness,playerid,playername,teamname,position,champion,kills,deaths,assists,total cs,visionscore,result`. Assert:

```java
List<OracleGameBatch> games = parser.parse(csv, "LEC", "Summer");
assertThat(games).singleElement().satisfies(game -> {
    assertThat(game.externalGameId()).isEqualTo("LEC_2026_001");
    assertThat(game.playedAt()).isEqualTo(Instant.parse("2026-07-24T16:00:00Z"));
    assertThat(game.players()).hasSize(10);
});
```

Also assert Spring rows, incomplete rows, team-summary rows, and blank game IDs are excluded.

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
cd fantalol-backend
mvn -Dtest=OracleElixirGameParserTest test
```

Expected: compilation failure because the parser records do not exist.

- [ ] **Step 3: Implement immutable parser records**

Define:

```java
public record OracleGameBatch(
        String externalGameId,
        Instant playedAt,
        List<OraclePlayerGameRow> players,
        String sourceFingerprint) {}

public record OraclePlayerGameRow(
        String externalPlayerId,
        String nickname,
        String teamName,
        PlayerRole role,
        String champion,
        int kills,
        int deaths,
        int assists,
        int cs,
        int visionScore,
        boolean win) {}
```

Parse the Oracle `date` value into an `Instant`, group player rows by `gameid`, require exactly ten player rows before returning a batch, and compute a stable SHA-256 fingerprint from normalized row values.

- [ ] **Step 4: Implement JPA source-of-truth entities**

`ProviderGame` stores provider `ORACLES_ELIXIR`, external game ID, played instant, league, split, source fingerprint, and source timestamps. `ProviderPlayerGameStat` stores the resolved `LecPlayer`, raw provider identity, raw/corrected fields, fantasy score, override flag, override actor, and override timestamp. Add uniqueness constraints:

```java
@UniqueConstraint(columnNames = {"provider", "external_game_id"})
@UniqueConstraint(columnNames = {"provider_game_id", "lec_player_id"})
```

Repositories expose:

```java
Optional<ProviderGame> findByProviderAndExternalGameId(String provider, String externalGameId);
List<ProviderPlayerGameStat> findByProviderGameId(Long providerGameId);
List<ProviderPlayerGameStat> findAllByOrderByProviderGamePlayedAtAsc();
```

- [ ] **Step 5: Run parser and backend tests**

Run:

```bash
cd fantalol-backend
mvn -Dtest=OracleElixirGameParserTest,GameScoreCalculatorTest test
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add fantalol-backend/src/main/java/com/fantalol/backend/integration/oracle \
        fantalol-backend/src/test/java/com/fantalol/backend/integration/oracle/OracleElixirGameParserTest.java
git commit -m "feat: persist Oracle player game data"
```

---

### Task 2: Idempotent Oracle import and provider diagnostics

**Files:**
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/ProviderSyncState.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/ProviderSyncStateRepository.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/SyncReport.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/oracle/OracleGameImportService.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/team/LecPlayerRepository.java`
- Test: `fantalol-backend/src/test/java/com/fantalol/backend/integration/oracle/OracleGameImportServiceTest.java`

**Interfaces:**
- Consumes: `OracleElixirGameParser`, provider-game repositories, `LecPlayerRepository`, and `GameScoreCalculator`.
- Produces: `OracleImportSummary OracleGameImportService.importCsv(String csv, String league, String split)` and durable per-provider health state.

- [ ] **Step 1: Write failing idempotency and correction tests**

Test first import, repeated identical import, changed provider row, and unmatched player:

```java
OracleImportSummary first = service.importCsv(csv, "LEC", "Summer");
assertThat(first.insertedGames()).isEqualTo(1);

OracleImportSummary repeated = service.importCsv(csv, "LEC", "Summer");
assertThat(repeated.skippedGames()).isEqualTo(1);

OracleImportSummary changed = service.importCsv(correctedCsv, "LEC", "Summer");
assertThat(changed.updatedGames()).isEqualTo(1);
```

Assert a game containing one unresolved player is rejected as a whole and its
nickname appears in `unmatchedPlayers`.

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
cd fantalol-backend
mvn -Dtest=OracleGameImportServiceTest test
```

Expected: compilation failure for missing import service.

- [ ] **Step 3: Implement atomic game import**

Resolve players by Oracle ID, then case-insensitive nickname. Reject the entire
batch unless every row resolves. Insert new batches; update provider values and
fantasy scores only when the fingerprint changes. If a row has
`manualOverride=true`, update only its provider snapshot fields and preserve the
active corrected values.

Return:

```java
public record OracleImportSummary(
        int insertedGames,
        int updatedGames,
        int skippedGames,
        int failedGames,
        List<String> unmatchedPlayers) {}
```

- [ ] **Step 4: Persist independent provider state**

`ProviderSyncState` is unique by provider and stores `status`, `lastAttemptAt`,
`lastSuccessAt`, and `lastError`. Add service helpers that record Oracle success
or failure without changing PandaScore state.

- [ ] **Step 5: Run Oracle integration tests**

Run:

```bash
cd fantalol-backend
mvn -Dtest=OracleGameImportServiceTest,OracleElixirCsvImporterTest test
```

Expected: PASS; adapt the legacy importer test only to keep its existing manual
endpoint compatible until Task 5 removes its use from live scoring.

- [ ] **Step 6: Commit**

```bash
git add fantalol-backend/src/main/java/com/fantalol/backend/integration \
        fantalol-backend/src/main/java/com/fantalol/backend/team/LecPlayerRepository.java \
        fantalol-backend/src/test/java/com/fantalol/backend/integration/oracle
git commit -m "feat: import Oracle games idempotently"
```

---

### Task 3: Effective lineup periods and Rome editing window

**Files:**
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/lineup/EffectiveLineupPeriod.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/lineup/EffectiveLineupPeriodRepository.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/lineup/LineupPeriodOrigin.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/lineup/LineupWindow.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/lineup/EffectiveLineupService.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/lineup/LineupBackfillService.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/FormationService.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/dto/FormationResponse.java`
- Test: `fantalol-backend/src/test/java/com/fantalol/backend/lineup/LineupWindowTest.java`
- Test: `fantalol-backend/src/test/java/com/fantalol/backend/lineup/EffectiveLineupServiceTest.java`

**Interfaces:**
- Consumes: saved `Formation`, roster entries, league participant count, and injected `Clock`.
- Produces: effective period history and `LineupWindow.Status LineupWindow.status(Instant now)`.

- [ ] **Step 1: Write boundary tests with an injected clock**

Assert Rome-local Tuesday 00:00 and Thursday 23:59 are open, while Monday and
Friday are locked. Include dates on both sides of the daylight-saving change:

```java
assertThat(window.status(rome("2026-07-28T00:00:00")).editable()).isTrue();
assertThat(window.status(rome("2026-07-31T00:00:00")).editable()).isFalse();
assertThat(window.nextEffectiveAt(rome("2026-07-30T20:00:00")))
        .isEqualTo(rome("2026-07-31T00:00:00"));
```

- [ ] **Step 2: Run lineup tests and verify failure**

Run:

```bash
cd fantalol-backend
mvn -Dtest=LineupWindowTest,EffectiveLineupServiceTest test
```

Expected: compilation failure for missing lineup package.

- [ ] **Step 3: Implement the lineup window**

Use:

```java
public static final ZoneId ZONE = ZoneId.of("Europe/Rome");
public record Status(boolean editable, Instant nextEffectiveAt, String reason) {}
```

Do not use the Render server default zone.

- [ ] **Step 4: Implement immutable role periods**

Store fantasy team, role, player, `effectiveFrom`, nullable `effectiveUntil`,
and origin. Saving a valid five-role formation closes open periods at the next
Friday instant and inserts new periods at that instant. Reject saves outside
the editing window or for leagues with at least six teams.

Expose:

```java
Set<LecPlayer> activePlayersAt(Long fantaTeamId, Instant playedAt);
Optional<EffectiveLineupPeriod> activePeriodAt(Long fantaTeamId, PlayerRole role, Instant playedAt);
void schedule(String username, Long fantaTeamId, Set<LecPlayer> players);
```

- [ ] **Step 5: Implement fixed-roster and initial backfill**

Create automatic periods for leagues with at least six teams. For all existing
teams lacking periods, use the current saved formation (or fixed roster) from:

```java
ZonedDateTime.of(2026, 7, 24, 0, 0, 0, 0, LineupWindow.ZONE).toInstant()
```

Mark these periods `BACKFILL`; repeated execution must not duplicate them.

- [ ] **Step 6: Adapt formation APIs**

Keep the existing endpoint and dialog contract, but make saves schedule
effective periods. Extend `FormationResponse` with `editable`,
`nextEffectiveAt`, and `effectivePlayers`; preserve historical `Formation`
records for compatibility.

- [ ] **Step 7: Run formation and lineup tests**

Run:

```bash
cd fantalol-backend
mvn -Dtest=LineupWindowTest,EffectiveLineupServiceTest,FormationServiceTest test
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add fantalol-backend/src/main/java/com/fantalol/backend/lineup \
        fantalol-backend/src/main/java/com/fantalol/backend/matchday \
        fantalol-backend/src/test/java/com/fantalol/backend/lineup \
        fantalol-backend/src/test/java/com/fantalol/backend/matchday/FormationServiceTest.java
git commit -m "feat: track effective fantasy lineups"
```

---

### Task 4: Cumulative player, slot, and fantasy-team projections

**Files:**
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/scoring/CumulativeScoringService.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/scoring/dto/CumulativePlayerScore.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/scoring/dto/FantasyRoleSlotScore.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/scoring/dto/CumulativeFantasyTeamScore.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/scoring/CumulativeScoringController.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/dto/FantaTeamResponse.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/FantaTeamService.java`
- Test: `fantalol-backend/src/test/java/com/fantalol/backend/scoring/CumulativeScoringServiceTest.java`

**Interfaces:**
- Consumes: persisted `ProviderPlayerGameStat` rows and effective lineup periods.
- Produces: public player projections and authenticated league/team cumulative projections.

- [ ] **Step 1: Write failing cumulative scoring tests**

Cover:

```java
assertThat(service.playerScore(playerId).gamesPlayed()).isEqualTo(3);
assertThat(service.playerScore(playerId).average()).isEqualTo(20.0);
assertThat(service.teamScore(teamId).slots()).extracting(FantasyRoleSlotScore::role)
        .containsExactlyInAnyOrder(PlayerRole.values());
```

Add cases where a bench player has an individual score but no slot
contribution, a starter does not play, a Mid changes on Friday, and a team has
one awaiting slot. Assert the awaiting team has `overallAverage == null`.

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```bash
cd fantalol-backend
mvn -Dtest=CumulativeScoringServiceTest test
```

Expected: compilation failure for missing service and DTOs.

- [ ] **Step 3: Implement query DTOs**

Define:

```java
public record CumulativePlayerScore(
        Long playerId, String nickname, PlayerRole role,
        int gamesPlayed, Double average, String status) {}

public record FantasyRoleSlotScore(
        PlayerRole role, int gamesPlayed, Double average,
        List<String> contributingPlayers, String status) {}

public record CumulativeFantasyTeamScore(
        Long fantasyTeamId, String teamName,
        List<FantasyRoleSlotScore> slots,
        Double overallAverage, boolean provisional) {}
```

- [ ] **Step 4: Implement attribution and averages**

For each complete participating player-game row, include its score in a fantasy
role slot only when a matching effective period covers `game.playedAt`.
Calculate player averages independently of lineup status. Calculate a team
overall only when every role slot has at least one game.

- [ ] **Step 5: Expose projections**

Add:

```http
GET /api/lec/cumulative-performances
GET /api/fanta-teams/{id}/cumulative-score
GET /api/leagues/{id}/cumulative-ranking
```

League endpoints remain authenticated and enforce existing visibility rules.
Update `FantaTeamResponse.punti` from the cumulative projection rather than
incrementing mutable totals.

- [ ] **Step 6: Run cumulative and league tests**

Run:

```bash
cd fantalol-backend
mvn -Dtest=CumulativeScoringServiceTest,FantaTeamServiceTest,LeagueVisibilityServiceTest test
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add fantalol-backend/src/main/java/com/fantalol/backend/scoring \
        fantalol-backend/src/main/java/com/fantalol/backend/league \
        fantalol-backend/src/test/java/com/fantalol/backend/scoring/CumulativeScoringServiceTest.java
git commit -m "feat: calculate cumulative fantasy scores"
```

---

### Task 5: Unified scheduler, backfill, ADMIN sync, and manual overrides

**Files:**
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/LecSynchronizationService.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/LecSyncStatusResponse.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/oracle/dto/ManualPlayerGameCorrectionRequest.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/oracle/PlayerGameCorrectionService.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/LecLiveDataService.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/LecDataController.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/config/SecurityConfig.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/config/DataSeeder.java`
- Test: `fantalol-backend/src/test/java/com/fantalol/backend/integration/lec/LecSynchronizationServiceTest.java`
- Test: `fantalol-backend/src/test/java/com/fantalol/backend/integration/oracle/PlayerGameCorrectionServiceTest.java`

**Interfaces:**
- Consumes: PandaScore client, Oracle client/import service, lineup backfill, scoring projections, authentication.
- Produces: shared scheduled/manual synchronization, diagnostic status, correction and restore actions.

- [ ] **Step 1: Write failing orchestration tests**

Assert Oracle failure does not discard persisted Panda standings, Panda failure
does not discard Oracle projections, manual sync calls the same method as the
scheduler, and repeated backfill is safe.

- [ ] **Step 2: Write failing manual override tests**

Correct one stat row, assert recalculated fantasy score and audit fields, run a
provider update and assert override survival, then restore provider data and
assert provider values become active.

- [ ] **Step 3: Run focused tests and verify failure**

Run:

```bash
cd fantalol-backend
mvn -Dtest=LecSynchronizationServiceTest,PlayerGameCorrectionServiceTest test
```

Expected: compilation failure for missing services.

- [ ] **Step 4: Implement unified synchronization**

Expose:

```java
SyncReport synchronize(SyncTrigger trigger);
LecSyncStatusResponse status();
```

Use separate `try/catch` blocks and transactions for PandaScore and Oracle.
Run initial lineup backfill before Oracle attribution. Persist sync counts and
provider error messages. Replace the in-memory-only snapshot with projections
rebuilt from persisted provider games; retain the last valid Panda projection.

- [ ] **Step 5: Implement correction APIs**

Add global-ADMIN endpoints:

```http
GET  /api/admin/lec/synchronization
POST /api/admin/lec/synchronize
PUT  /api/admin/lec/games/{gameId}/players/{playerId}
DELETE /api/admin/lec/games/{gameId}/players/{playerId}/override
```

The request contains nullable `participated`, `kills`, `deaths`, `assists`,
`cs`, `visionScore`, and `win`; supplied corrected values become one complete
active override snapshot.

- [ ] **Step 6: Run integration and security tests**

Run:

```bash
cd fantalol-backend
mvn -Dtest=LecSynchronizationServiceTest,PlayerGameCorrectionServiceTest,LecLiveDataServiceTest,AuthIntegrationTest test
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add fantalol-backend/src/main/java/com/fantalol/backend/integration \
        fantalol-backend/src/main/java/com/fantalol/backend/config \
        fantalol-backend/src/test/java/com/fantalol/backend/integration
git commit -m "feat: automate and administer LEC synchronization"
```

---

### Task 6: League UI for cumulative scoring, lineup window, and ADMIN diagnostics

**Files:**
- Modify: `fantalol-frontend/lega.html`
- Modify: `fantalol-frontend/js/lec-data-source.js`
- Modify: `fantalol-frontend/js/league-detail.js`
- Modify: `fantalol-frontend/js/league-utils.js`
- Modify: `fantalol-frontend/css/league-detail.css`
- Modify: `fantalol-frontend/tests/league-detail-behavior.test.js`
- Modify: `fantalol-frontend/tests/league-utils.test.js`
- Modify: `fantalol-frontend/tests/lec-data-source.test.js`

**Interfaces:**
- Consumes: Task 4 cumulative endpoints and Task 5 ADMIN endpoints.
- Produces: Italian user-facing cumulative rankings, lineup status, sync diagnostics, and override form.

- [ ] **Step 1: Write failing frontend contract tests**

Assert source calls for `/lec/cumulative-performances`,
`/leagues/{id}/cumulative-ranking`, `/admin/lec/synchronization`, and
`/admin/lec/synchronize`. Assert the page contains ADMIN panel hooks and Italian
states `In attesa`, `Provvisorio`, `Aggiornato`, and `Fonte non disponibile`.

- [ ] **Step 2: Run frontend tests and verify failure**

Run:

```bash
node --test fantalol-frontend/tests/*.test.js
```

Expected: new assertions FAIL.

- [ ] **Step 3: Render cumulative performance and fantasy ranking**

Replace mutable point sorting with server cumulative projections. Show games
played, averages, five slot rows, contributors, awaiting slots, and no numeric
team total while provisional.

- [ ] **Step 4: Enforce lineup-window presentation**

Display the backend-provided `editable` and `nextEffectiveAt`. Hide edit
controls for fixed five-player rosters and show:

```text
Modifiche aperte da martedì a giovedì.
La nuova formazione sarà valida da venerdì.
```

Backend enforcement remains authoritative.

- [ ] **Step 5: Add ADMIN diagnostics and corrections**

Show the panel only when `state.user.role === 'ADMIN'`. Implement sync action,
provider states, counts, unmatched players, game/player correction form, and
restore-provider action. Display API errors without clearing the last rendered
ranking.

- [ ] **Step 6: Run frontend tests**

Run:

```bash
node --test fantalol-frontend/tests/*.test.js
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add fantalol-frontend
git commit -m "feat: manage cumulative scoring in league UI"
```

---

### Task 7: Update Italian regulation and operational documentation

**Files:**
- Modify: `fantalol-frontend/index.html`
- Modify: `README.md`
- Modify: `fantalol-backend/INTEGRATIONS.md`
- Modify: `fantalol-frontend/tests/home-visuals.test.js`

**Interfaces:**
- Consumes: approved Italian rules from the design.
- Produces: public regulation and Render/ADMIN operating instructions matching implemented behavior.

- [ ] **Step 1: Write failing regulation assertions**

Require the public page to mention cumulative Summer average, no zero for an
unplayed game, bench evaluations, Tuesday-through-Thursday changes,
`Europe/Rome`, Friday effectiveness, fixed lineups above five teams, and
automatic synchronization.

- [ ] **Step 2: Run the regulation test and verify failure**

Run:

```bash
node --test fantalol-frontend/tests/home-visuals.test.js
```

Expected: new text assertions FAIL.

- [ ] **Step 3: Replace obsolete matchday scoring copy**

Update the Italian regulation with the approved wording. Explain that ADMIN
`Sincronizza ora` retries providers but cannot create incomplete source data.

- [ ] **Step 4: Update integration documentation**

Document exact Render variables, automatic cadence, durable per-game import,
backfill date, diagnostic states, correction audit, and restore behavior.
Remove instructions implying that the annual CSV should be assigned wholesale
to one matchday.

- [ ] **Step 5: Run documentation-facing tests**

Run:

```bash
node --test fantalol-frontend/tests/home-visuals.test.js
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add README.md fantalol-backend/INTEGRATIONS.md fantalol-frontend/index.html \
        fantalol-frontend/tests/home-visuals.test.js
git commit -m "docs: publish cumulative Summer scoring rules"
```

---

### Task 8: Full regression, production configuration, and migration safety

**Files:**
- Modify: `fantalol-backend/src/main/resources/application.yml`
- Modify: `fantalol-backend/src/test/resources/application-test.yml`
- Test: `fantalol-backend/src/test/java/com/fantalol/backend/integration/lec/LecSynchronizationServiceTest.java`
- Test: `fantalol-backend/src/test/java/com/fantalol/backend/lineup/EffectiveLineupServiceTest.java`

**Interfaces:**
- Consumes: all prior tasks.
- Produces: deployable Spring Boot artifact and verified static frontend.

- [ ] **Step 1: Add explicit configuration**

Add:

```yaml
fantalol:
  lec:
    timezone: ${LEC_TIMEZONE:Europe/Rome}
    backfill-from: ${LEC_BACKFILL_FROM:2026-07-24T00:00:00+02:00}
```

Keep the confirmed PandaScore, Oracle URL, split, tournament, and cron
properties. Do not embed secrets.

- [ ] **Step 2: Run all backend tests**

Run:

```bash
cd fantalol-backend
mvn clean test
```

Expected: BUILD SUCCESS.

- [ ] **Step 3: Run all frontend tests**

Run:

```bash
node --test fantalol-frontend/tests/*.test.js
```

Expected: all tests PASS.

- [ ] **Step 4: Build the production artifact**

Run:

```bash
cd fantalol-backend
mvn -DskipTests package
```

Expected: `target/fantalol-backend.jar` is created.

- [ ] **Step 5: Inspect schema-update compatibility**

Start the application against H2 or the existing integration-test context and
verify that Hibernate creates the new tables without dropping existing
`formations`, `player_stats`, leagues, rosters, or users. Confirm the backfill
does not delete or replace existing records.

- [ ] **Step 6: Run diff and secret checks**

Run:

```bash
git diff --check
rg -n "PANDASCORE_API_TOKEN=|JWT_SECRET=|DB_PASSWORD=" . \
  --glob '!target/**' --glob '!.git/**'
```

Expected: no committed secret values.

- [ ] **Step 7: Commit final configuration fixes**

```bash
git add fantalol-backend/src/main/resources/application.yml \
        fantalol-backend/src/test README.md fantalol-backend/INTEGRATIONS.md \
        fantalol-frontend
git commit -m "test: verify cumulative Summer scoring"
```

- [ ] **Step 8: Record deployment handoff**

Report required Render redeploy, the ADMIN `Synchronize now` first-run action,
expected backfill from July 24, provider diagnostic checks, and the fact that
production deployment/push requires explicit GitHub/Render authority if not
already requested.
