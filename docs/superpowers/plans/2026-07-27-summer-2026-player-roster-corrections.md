# Summer 2026 Player Roster Corrections Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct the Summer 2026 roster in clean and existing databases while preserving player quotations and serving every replacement portrait.

**Architecture:** Keep `DataSeeder` as the Java roster authority and update the SQL seed used by asset validation. Add an idempotent in-place synchronization path that renames or moves existing `LecPlayer` entities without replacing their IDs or quotation values.

**Tech Stack:** Java 17, Spring Boot, Spring Data JPA, JUnit 5, Mockito, AssertJ, Maven, static frontend assets

## Global Constraints

- Do not run Git commands.
- Write all new production code and test names in English.
- Store nationalities with the existing Italian display labels `Corea del Sud`, `Spagna`, and `Polonia`.
- Preserve every affected player's existing quotation.
- Use the portrait path `/Player_immage/{Role}/{Nickname}.jpg`.

---

### Task 1: Existing-database roster synchronization

**Files:**
- Create: `fantalol-backend/src/test/java/com/fantalol/backend/config/DataSeederRosterCorrectionTest.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/config/DataSeeder.java`

**Interfaces:**
- Consumes: `LecPlayerRepository.findFirstByNicknameIgnoreCase(String)` and `LecTeamRepository.findByNomeIgnoreCase(String)`
- Produces: startup synchronization invoked by `DataSeeder.run(String...)`

- [ ] **Step 1: Write failing synchronization tests**

Create Mockito-backed tests that instantiate `DataSeeder`, provide old player entities,
run the seeder, and assert:

```java
assertThat(empyros.getNickname()).isEqualTo("Soboro");
assertThat(empyros.getNazionalita()).isEqualTo("Corea del Sud");
assertThat(empyros.getQuotazione()).isEqualTo(55);
assertThat(empyros.getImageUrl()).isEqualTo("/Player_immage/Top/Soboro.jpg");
assertThat(sheo.getTeam().getNome()).isEqualTo("Shifters");
assertThat(stend.getTeam().getNome()).isEqualTo("Shifters");
assertThat(boukada.getNickname()).isEqualTo("Daglas");
assertThat(boukada.getTeam().getNome()).isEqualTo("Team Heretics");
```

Cover all replacements and invoke `run` twice to prove idempotence.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
docker run --rm -v /home/massimilianofabbo/Desktop/FantaLol:/workspace \
  -v /tmp/fantaleague-m2:/root/.m2 -w /workspace/fantalol-backend \
  maven:3.9.9-eclipse-temurin-17 \
  mvn -q -Dtest=DataSeederRosterCorrectionTest test
```

Expected: FAIL because the current existing-database path only refreshes asset metadata.

- [ ] **Step 3: Implement minimal idempotent corrections**

Add an immutable correction definition containing old nickname, new nickname, role,
nationality when changed, and target team. Apply each correction before asset
backfilling. Resolve either the old or already-corrected nickname, mutate the same
entity, leave `quotazione` untouched, and save it. Ensure the clean seed roster uses
the same corrected player names, teams, and nationalities.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the command from Step 2. Expected: PASS.

### Task 2: SQL seed and portrait coverage

**Files:**
- Modify: `fantalol-backend/sql/data-seed.sql`
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/common/SeedAssetReferenceTest.java`

**Interfaces:**
- Consumes: static portraits under `fantalol-frontend/Player_immage`
- Produces: corrected SQL seed roster with exactly 50 unique portrait references

- [ ] **Step 1: Extend the asset test with failing roster assertions**

Read `sql/data-seed.sql` and assert that it contains each new nickname and image path,
does not contain the eight removed nicknames, assigns Sheo and Stend to Shifters, and
assigns Daglas and Way to Team Heretics.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
docker run --rm -v /home/massimilianofabbo/Desktop/FantaLol:/workspace \
  -v /tmp/fantaleague-m2:/root/.m2 -w /workspace/fantalol-backend \
  maven:3.9.9-eclipse-temurin-17 \
  mvn -q -Dtest=SeedAssetReferenceTest test
```

Expected: FAIL because the SQL seed still references the old roster.

- [ ] **Step 3: Update the SQL seed**

Replace the eight obsolete players with Soboro, Oscarinin, Daglas, FIESTA, SlowQ,
Flakked, Hype, and Way. Move Sheo and Stend to the Shifters team ID. Preserve numeric
quotation values and use the requested nationalities and portrait paths.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the command from Step 2. Expected: PASS with 50 existing portrait references.

### Task 3: Full verification

**Files:**
- Verify all files modified by Tasks 1 and 2

**Interfaces:**
- Consumes: corrected Java seed, migration logic, SQL seed, portraits
- Produces: verified backend and frontend behavior

- [ ] **Step 1: Verify all replacement images exist**

Run `test -f` for Soboro, Oscarinin, Daglas, FIESTA, SlowQ, Flakked, Hype, and Way
using their exact role directories.

- [ ] **Step 2: Run the complete backend suite**

Run the Maven test suite in the approved Maven Docker image. Expected: exit code 0
and zero test failures.

- [ ] **Step 3: Run frontend tests and JavaScript syntax checks**

Run:

```bash
node --test fantalol-frontend/tests/*.test.js
node --check fantalol-frontend/js/app.js
node --check fantalol-frontend/js/league-detail.js
node --check fantalol-frontend/js/league-utils.js
```

Expected: all tests pass and every syntax check exits 0.

- [ ] **Step 4: Scan source seeds for obsolete roster data**

Search only source files, excluding generated `target` output. Expected: obsolete
nicknames appear only in the explicit migration mapping and regression tests.
