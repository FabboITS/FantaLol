# LEC Live Data and Support Vision Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically publish current LEC standings, split fantasy performance, per-game player statistics, and champion pick counts while scoring Supports with one point per 50 vision score instead of CS.

**Architecture:** Extend the existing scoring and Oracle import path with vision and champion data, then add a focused `integration.lec` domain that stores provider matches and game-level statistics. A scheduled backend synchronizer combines PandaScore metadata with Oracle's Elixir rows and exposes normalized read-only projections consumed by the existing static league page.

**Tech Stack:** Java 17, Spring Boot 3.3, Spring Data JPA, Spring RestClient, Jackson, Apache Commons CSV, MySQL/H2, JUnit 5, Mockito, AssertJ, HTML5, CSS, vanilla JavaScript, Node test runner.

## Global Constraints

- Use English for every new identifier, comment, configuration property, API name, and test name.
- Keep existing Italian user-facing copy in Italian.
- Keep `PANDASCORE_API_TOKEN` server-side and never commit or render it.
- Use PandaScore for match metadata and Oracle's Elixir for per-game statistics.
- Use local Riot Data Dragon or CommunityDragon champion icons under `fantalol-frontend/Player_immage/Champions/`.
- Preserve all non-Support Summer 2026 coefficients.
- Support CS contributes zero; Support vision contributes `visionScore / 50.0`.
- Never fabricate statistics for incomplete matches.
- Every synchronization write is idempotent and retains the last complete snapshot on provider failure.
- Commit each completed task separately and do not push or open a pull request.

---

### Task 1: Support Vision Scoring

**Files:**
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/scoring/RoleScoreWeights.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/scoring/GameScoreCalculator.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/FantaScoreCalculator.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/PlayerStat.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/dto/PlayerStatRequest.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/dto/PlayerStatResponse.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/MatchdayService.java`
- Test: `fantalol-backend/src/test/java/com/fantalol/backend/scoring/GameScoreCalculatorTest.java`
- Test: `fantalol-backend/src/test/java/com/fantalol/backend/matchday/FantaScoreCalculatorTest.java`

**Interfaces:**
- Consumes: `PlayerRole`, aggregate matchday statistics.
- Produces: `double GameScoreCalculator.calculate(PlayerRole role, int kills, int deaths, int assists, int cs, int visionScore, boolean win)`.
- Produces: `double GameScoreCalculator.calculateAverage(PlayerRole role, int kills, int deaths, int assists, int cs, int visionScore, int wins, int gamesPlayed)`.
- Produces: persisted and API-visible `Integer visionScore`.

- [ ] **Step 1: Write failing Support resource tests**

```java
assertThat(calculator.calculate(SUPPORT, 0, 0, 0, 999, 0, false)).isZero();
assertThat(calculator.calculate(SUPPORT, 0, 0, 0, 0, 25, false)).isEqualTo(0.5);
assertThat(calculator.calculate(SUPPORT, 0, 0, 0, 0, 50, false)).isEqualTo(1.0);
assertThat(calculator.calculate(SUPPORT, 0, 0, 0, 0, 100, false)).isEqualTo(2.0);
assertThat(calculator.calculate(TOP, 0, 0, 0, 50, 999, false)).isEqualTo(0.625);
```

- [ ] **Step 2: Run focused scoring tests and verify RED**

Run:

```bash
docker run --rm -v /home/massimilianofabbo/Desktop/FantaLol:/workspace -v /tmp/fantaleague-m2:/root/.m2 -w /workspace/fantalol-backend maven:3.9.9-eclipse-temurin-17 mvn -q -Dtest=GameScoreCalculatorTest,FantaScoreCalculatorTest test
```

Expected: compilation failure because calculator methods do not accept
`visionScore`.

- [ ] **Step 3: Implement role-specific resource scoring**

Add a private resource method:

```java
private double resourceScore(PlayerRole role, int cs, int visionScore) {
    if (role == PlayerRole.SUPPORT) {
        return visionScore / 50.0;
    }
    return (cs / 100.0) * RoleScoreWeights.forRole(role).csPerHundred();
}
```

Remove the obsolete Support CS weight from active arithmetic, pass
`PlayerStat.getVisionScore()` through `FantaScoreCalculator`, and default legacy
database rows to zero.

- [ ] **Step 4: Extend manual statistic DTOs and persistence**

Add `@Min(0) Integer visionScore` after `cs` in `PlayerStatRequest`, include it
in `PlayerStatResponse`, and assign:

```java
stat.setVisionScore(request.visionScore() != null ? request.visionScore() : 0);
```

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Task 1 command and require a zero exit code.

- [ ] **Step 6: Commit**

```bash
git add fantalol-backend/src/main/java/com/fantalol/backend/scoring \
  fantalol-backend/src/main/java/com/fantalol/backend/matchday \
  fantalol-backend/src/test/java/com/fantalol/backend/scoring \
  fantalol-backend/src/test/java/com/fantalol/backend/matchday
git commit -m "feat: score support vision instead of cs"
```

### Task 2: Oracle Vision and Champion Import

**Files:**
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/integration/oracle/OracleElixirCsvImporter.java`
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/integration/oracle/OracleElixirCsvImporterTest.java`
- Modify: `fantalol-backend/src/test/resources/oracle-elixir-sample.csv`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/LecMatch.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/LecGame.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/LecPlayerGameStat.java`
- Create repository interfaces for the three entities in the same package.
- Test: `fantalol-backend/src/test/java/com/fantalol/backend/integration/lec/LecPlayerGameStatTest.java`

**Interfaces:**
- Consumes: Oracle columns `gameid`, `playerid`, `playername`, `champion`,
  `kills`, `deaths`, `assists`, `total cs`, `visionscore`, and `result`.
- Produces: one `LecPlayerGameStat` per `(lec_game_id, lec_player_id)` with
  champion, K/D/A, CS, vision score, win, and calculated fantasy score.

- [ ] **Step 1: Write failing importer and entity tests**

Use a complete CSV row:

```csv
GAME-1,LEC,Summer,complete,mid,oe-caps,Caps,Ahri,4,1,7,245,31,1
```

Assert `visionScore == 31`, `championName.equals("Ahri")`, repeated rows update
the same game/player identity, and negative vision is rejected.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
docker run --rm -v /home/massimilianofabbo/Desktop/FantaLol:/workspace -v /tmp/fantaleague-m2:/root/.m2 -w /workspace/fantalol-backend maven:3.9.9-eclipse-temurin-17 mvn -q -Dtest=OracleElixirCsvImporterTest,LecPlayerGameStatTest test
```

Expected: missing game-level entities and missing `visionscore` import.

- [ ] **Step 3: Implement game-level persistence**

Use unique constraints on PandaScore/Oracle external IDs and on
`(lec_game_id, lec_player_id)`. Store provider team names as snapshots. Add
non-negative Bean Validation constraints to all numeric statistics.

- [ ] **Step 4: Extend Oracle parsing**

Parse optional vision safely:

```java
int visionScore = integer(record, "visionscore");
String championName = value(record, "champion");
```

Keep existing matchday aggregation and add the imported vision total before
recalculating `fantavoto`. Feed the same row to the game-stat repository when
its `LecGame` mapping exists.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Task 2 command and require a zero exit code.

- [ ] **Step 6: Commit**

```bash
git add fantalol-backend/src/main/java/com/fantalol/backend/integration \
  fantalol-backend/src/test/java/com/fantalol/backend/integration \
  fantalol-backend/src/test/resources/oracle-elixir-sample.csv
git commit -m "feat: import LEC vision and champion statistics"
```

### Task 3: Automatic LEC Synchronization

**Files:**
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/integration/pandascore/PandaScoreClient.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/integration/pandascore/PandaScoreProperties.java`
- Modify: `fantalol-backend/src/main/resources/application.yml`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/LecSyncProperties.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/OracleElixirClient.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/LecDataSynchronizer.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/LecSyncState.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/LecSyncStateRepository.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/LecSyncScheduler.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/integration/pandascore/PandaScoreAdminController.java`
- Test: `fantalol-backend/src/test/java/com/fantalol/backend/integration/lec/LecDataSynchronizerTest.java`

**Interfaces:**
- Consumes: PandaScore series/tournament/match JSON and Oracle annual CSV bytes.
- Produces: `LecSyncResult LecDataSynchronizer.synchronize()`.
- Produces: `POST /api/admin/lec/synchronize`.
- Produces: configurable `LEC_SERIES_SLUG`, `LEC_SPLIT`, `LEC_SEASON`,
  `ORACLE_ELIXIR_CSV_URL`, and `LEC_SYNC_CRON`.

- [ ] **Step 1: Write failing synchronization tests**

Stub clients and assert:

```java
assertThat(result.matchesUpserted()).isEqualTo(2);
assertThat(result.gamesUpserted()).isEqualTo(5);
assertThat(result.playerStatsUpserted()).isEqualTo(50);
assertThat(secondRun.totalRows()).isEqualTo(firstRun.totalRows());
```

Also assert a provider exception leaves the previous successful
`LecSyncState.lastSuccessfulAt` unchanged and records a failed attempt.

- [ ] **Step 2: Run the synchronizer test and verify RED**

Run:

```bash
docker run --rm -v /home/massimilianofabbo/Desktop/FantaLol:/workspace -v /tmp/fantaleague-m2:/root/.m2 -w /workspace/fantalol-backend maven:3.9.9-eclipse-temurin-17 mvn -q -Dtest=LecDataSynchronizerTest test
```

- [ ] **Step 3: Implement provider discovery and upserts**

Add PandaScore calls for filtered series/tournaments and matches. Select only
the configured LEC season and split. Upsert complete objects inside a
transaction after both provider payloads have been validated.

- [ ] **Step 4: Add scheduling and administrator trigger**

Enable scheduling on the application and call `synchronize()` with
`@Scheduled(cron = "${fantalol.lec.sync-cron}")`. The administrator endpoint
returns counts, freshness, last success, and unmatched players.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Task 3 command and require a zero exit code.

- [ ] **Step 6: Commit**

```bash
git add fantalol-backend/src/main/java/com/fantalol/backend/integration \
  fantalol-backend/src/main/java/com/fantalol/backend/FantaLolBackendApplication.java \
  fantalol-backend/src/main/resources/application.yml \
  fantalol-backend/src/test/java/com/fantalol/backend/integration
git commit -m "feat: synchronize current LEC data automatically"
```

### Task 4: Public Standings and Performance API

**Files:**
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/LecDataController.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/LecDataQueryService.java`
- Create DTO records under `fantalol-backend/src/main/java/com/fantalol/backend/integration/lec/dto/`.
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/config/SecurityConfig.java`
- Test: `fantalol-backend/src/test/java/com/fantalol/backend/integration/lec/LecDataQueryServiceTest.java`
- Test: `fantalol-backend/src/test/java/com/fantalol/backend/integration/lec/LecDataControllerTest.java`

**Interfaces:**
- Produces: `GET /api/lec/standings`.
- Produces: `GET /api/lec/performances`.
- Produces: `GET /api/lec/matches`.
- Produces: `GET /api/lec/matches/{matchId}/games/{gameId}`.
- Produces: KDA as nullable decimal plus `perfectKda: boolean`.

- [ ] **Step 1: Write failing projection tests**

Create fixtures for two teams, two games, a zero-death player, and repeated
champion picks. Assert standings order, fantasy mean, `Ahri -> 2 picks`, numeric
KDA for deaths above zero, and `perfectKda == true` with null KDA at zero deaths.

- [ ] **Step 2: Run query tests and verify RED**

Run:

```bash
docker run --rm -v /home/massimilianofabbo/Desktop/FantaLol:/workspace -v /tmp/fantaleague-m2:/root/.m2 -w /workspace/fantalol-backend maven:3.9.9-eclipse-temurin-17 mvn -q -Dtest=LecDataQueryServiceTest,LecDataControllerTest test
```

- [ ] **Step 3: Implement normalized projections**

Return immutable DTOs with `lastUpdatedAt`, `freshness`, and `provisional`.
Fantasy averages divide by games actually played. Champion picks group by
normalized champion name. Match lists use reverse chronological order and game
detail includes exactly the participating players for that game.

- [ ] **Step 4: Permit authenticated league users to read LEC endpoints**

Keep synchronization endpoints ADMIN-only. Add only the four read paths to the
same authenticated access level used by league data.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Task 4 command and require a zero exit code.

- [ ] **Step 6: Commit**

```bash
git add fantalol-backend/src/main/java/com/fantalol/backend/integration/lec \
  fantalol-backend/src/main/java/com/fantalol/backend/config/SecurityConfig.java \
  fantalol-backend/src/test/java/com/fantalol/backend/integration/lec
git commit -m "feat: expose LEC standings and performance data"
```

### Task 5: League Page Standings and Performance UI

**Files:**
- Modify: `fantalol-frontend/js/lec-data-source.js`
- Modify: `fantalol-frontend/js/league-detail.js`
- Modify: `fantalol-frontend/lega.html`
- Modify: `fantalol-frontend/css/league-detail.css`
- Modify: `fantalol-frontend/tests/league-detail-behavior.test.js`
- Create: `fantalol-frontend/tests/lec-data-source.test.js`

**Interfaces:**
- Consumes: the four `/api/lec` endpoints from Task 4.
- Produces: standings table, split fantasy ranking, match/game selector, and
  role-specific stat rows.

- [ ] **Step 1: Write failing frontend behavior tests**

Assert the source calls `/api/lec/standings`, `/api/lec/performances`, and
`/api/lec/matches`; the page includes match and game selectors; Support rows use
`Vision`; other roles use `CS`; perfect KDA renders `Perfetto`; and neither file
contains `not-connected` or `Fonte ufficiale non collegata`.

- [ ] **Step 2: Run Node tests and verify RED**

Run:

```bash
node --test fantalol-frontend/tests/*.test.js
```

- [ ] **Step 3: Implement the frontend data adapter**

Reuse the authenticated `api` helper through an injected request function and
return normalized error objects. Do not parse CSV or calculate fantasy points in
JavaScript.

- [ ] **Step 4: Render standings and performance**

Render semantic tables and selectors with Italian loading, empty, stale, and
awaiting-statistics messages. Format ordinary KDA to two decimals. For Support
render `Vision ${visionScore}`; otherwise render `${cs} CS`.

- [ ] **Step 5: Run frontend tests and syntax checks**

Run:

```bash
node --test fantalol-frontend/tests/*.test.js
node --check fantalol-frontend/js/lec-data-source.js
node --check fantalol-frontend/js/league-detail.js
```

- [ ] **Step 6: Commit**

```bash
git add fantalol-frontend/lega.html fantalol-frontend/css/league-detail.css \
  fantalol-frontend/js/lec-data-source.js fantalol-frontend/js/league-detail.js \
  fantalol-frontend/tests
git commit -m "feat: render live LEC standings and performances"
```

### Task 6: Local Champion Assets

**Files:**
- Create: `fantalol-frontend/Player_immage/Champions/*.png`
- Create: `fantalol-frontend/Player_immage/Champions/unknown.svg`
- Create: `fantalol-frontend/Player_immage/Champions/manifest.json`
- Modify: `fantalol-frontend/tests/league-detail-behavior.test.js`
- Test: `fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java`

**Interfaces:**
- Consumes: normalized champion names returned by Task 4.
- Produces: `/Player_immage/Champions/{riotChampionId}.png`.

- [ ] **Step 1: Add failing asset-reference tests**

Assert every champion path emitted by performance fixtures exists beneath the
Champions directory and rejects `..`, URL schemes, or unnormalized names.

- [ ] **Step 2: Fetch Riot champion metadata and required square icons**

Read the current Data Dragon version manifest, map Oracle champion names to Riot
IDs, download only champions present in synchronized/current-split fixtures, and
write a manifest containing Riot ID, display name, version, and local path.

- [ ] **Step 3: Implement the local fallback**

Return `/Player_immage/Champions/unknown.svg` for an unmapped champion. Keep
remote URLs out of API DTOs and rendered image sources.

- [ ] **Step 4: Run asset tests and static resource integration**

Run:

```bash
node --test fantalol-frontend/tests/*.test.js
docker run --rm -v /home/massimilianofabbo/Desktop/FantaLol:/workspace -v /tmp/fantaleague-m2:/root/.m2 -w /workspace/fantalol-backend maven:3.9.9-eclipse-temurin-17 mvn -q -Dtest=StaticResourceIntegrationTest test
```

- [ ] **Step 5: Commit**

```bash
git add fantalol-frontend/Player_immage/Champions \
  fantalol-frontend/tests/league-detail-behavior.test.js \
  fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java
git commit -m "feat: add local champion performance assets"
```

### Task 7: Documentation and Full Verification

**Files:**
- Modify: `Rules.md`
- Modify: `README.md`
- Modify: `fantalol-backend/INTEGRATIONS.md`
- Modify: `fantalol-frontend/index.html`
- Modify tests only when a verification failure proves a requirement gap.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: exact Support scoring rules, deployment configuration, synchronization
  instructions, and release evidence.

- [ ] **Step 1: Write failing documentation consistency assertions**

Require every public rules copy to describe Support as `1 point per 50 vision
score`, reject the active Support `0.20 per 100 CS` rule, and require all
environment variable names from Task 3 in `INTEGRATIONS.md`.

- [ ] **Step 2: Update rules and integration documentation**

Document automatic and manual synchronization, stale snapshots, source
responsibilities, champion assets, and the administrator endpoint. Keep secrets
as placeholder environment-variable names only.

- [ ] **Step 3: Run the complete backend suite**

Run:

```bash
docker run --rm -v /home/massimilianofabbo/Desktop/FantaLol:/workspace -v /tmp/fantaleague-m2:/root/.m2 -w /workspace/fantalol-backend maven:3.9.9-eclipse-temurin-17 mvn -q test
```

- [ ] **Step 4: Run complete frontend verification**

Run:

```bash
node --test fantalol-frontend/tests/*.test.js
node --check fantalol-frontend/js/app.js
node --check fantalol-frontend/js/league-utils.js
node --check fantalol-frontend/js/lec-data-source.js
node --check fantalol-frontend/js/league-detail.js
```

- [ ] **Step 5: Audit active rules and secrets**

Run:

```bash
rg -n "0[.,]20|100 CS|vision|PANDASCORE_API_TOKEN|not-connected|Fonte ufficiale non collegata" \
  Rules.md README.md fantalol-backend fantalol-frontend
```

Confirm the only `0.20` references are historical documentation if retained,
the token appears only as an environment-variable name, and disconnected-source
copy is absent.

- [ ] **Step 6: Commit**

```bash
git add Rules.md README.md fantalol-backend/INTEGRATIONS.md \
  fantalol-frontend/index.html fantalol-backend/src/test fantalol-frontend/tests
git commit -m "docs: document live LEC data and vision scoring"
```

- [ ] **Step 7: Confirm repository state**

Run:

```bash
git status --short
git log -8 --oneline
```

Expected: no uncommitted task changes and one sequential commit for each
completed deliverable.
