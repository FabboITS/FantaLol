# Administrator Account Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reset a legacy installation to the sole `Natsu_Admin` administrator, remove all prior user-owned data, invalidate old tokens, and remove login credential disclosure.

**Architecture:** A focused transactional `AdminAccountInitializer` owns the one-time legacy reset and fresh administrator creation. `DataSeeder` always invokes it independently of LEC team seeding. JWT filtering treats deleted token subjects as unauthenticated, while frontend and maintained examples contain no administrator credentials.

**Tech Stack:** Java 17, Spring Boot, Spring Data JPA, Spring Security, JUnit 5, MockMvc, H2/MySQL, vanilla HTML/JavaScript.

## Global Constraints

- Do not run Git commands or create commits.
- Never place the requested plaintext administrator password in maintained repository files.
- Store only a BCrypt hash for the administrator credential.
- Run the destructive reset only when the legacy `admin` account exists.
- Preserve users registered after the one-time migration.
- Keep the `Ctrl+Y` directory limited to regular usernames.

---

### Task 1: Transactional Administrator Initializer

**Files:**
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/config/AdminAccountInitializer.java`
- Create: `fantalol-backend/src/test/java/com/fantalol/backend/config/AdminAccountInitializerIntegrationTest.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/config/DataSeeder.java`

**Interfaces:**
- Consumes: `UserRepository`, `LeagueRepository`, and `PasswordEncoder`.
- Produces: `void initialize()` on `AdminAccountInitializer`, called once by `DataSeeder.run` on every startup.

- [ ] **Step 1: Write failing integration tests**

Add tests that persist a legacy `admin`, a regular user, and a league owned by that user; call `initialize()`; assert leagues are empty and the sole user is enabled `Natsu_Admin` with role `ADMIN` and a BCrypt credential. Add a second test that calls `initialize()`, registers another user directly, calls `initialize()` again, and asserts both accounts remain. Add a fresh-database test that asserts `Natsu_Admin` is created without a legacy account.

- [ ] **Step 2: Run the focused test and confirm RED**

Run: `docker run --rm -v /home/massimilianofabbo/FantaLol:/workspace -v /tmp/fantaleague-m2:/root/.m2 -w /workspace/fantalol-backend maven:3.9.9-eclipse-temurin-17 mvn -q -Dtest=AdminAccountInitializerIntegrationTest test`

Expected: compilation failure because `AdminAccountInitializer` does not exist.

- [ ] **Step 3: Implement the initializer minimally**

Create a `@Service @RequiredArgsConstructor` class with a `@Transactional public void initialize()` method. If `userRepository.existsByUsername("admin")`, execute `leagueRepository.deleteAllInBatch()`, `userRepository.deleteAllInBatch()`, and flush before creating the administrator. If `Natsu_Admin` does not exist, save an enabled `ADMIN` user with email `natsu-admin@fantalol.local` and the precomputed BCrypt hash. Never embed the plaintext credential.

Move administrator creation out of `DataSeeder.seedAdminUser()`. Restructure `run()` so LEC data is seeded only when absent, asset metadata is backfilled otherwise, and `adminAccountInitializer.initialize()` executes in both paths.

- [ ] **Step 4: Run the focused test and confirm GREEN**

Run the Task 1 Maven command again.

Expected: all `AdminAccountInitializerIntegrationTest` tests pass.

### Task 2: Deleted-User JWT Handling

**Files:**
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/security/JwtAuthFilter.java`
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/user/AuthIntegrationTest.java`

**Interfaces:**
- Consumes: existing `JwtUtil.extractUsername`, `CustomUserDetailsService.loadUserByUsername`, and bearer-token request flow.
- Produces: invalid or deleted-subject tokens leave the request unauthenticated, causing protected endpoints to return HTTP 401.

- [ ] **Step 1: Write the failing deleted-user token test**

Register and log in a uniquely named regular user, capture its token, delete that user through `UserRepository`, then call `GET /api/users/me` with the token and assert HTTP 401 rather than HTTP 500.

- [ ] **Step 2: Run the focused test and confirm RED**

Run: `docker run --rm -v /home/massimilianofabbo/FantaLol:/workspace -v /tmp/fantaleague-m2:/root/.m2 -w /workspace/fantalol-backend maven:3.9.9-eclipse-temurin-17 mvn -q -Dtest=AuthIntegrationTest test`

Expected: the deleted-user token test fails because `UsernameNotFoundException` escapes the filter.

- [ ] **Step 3: Handle invalid authentication tokens**

Wrap JWT parsing and user loading in `JwtAuthFilter` with a catch limited to JWT/security authentication failures. Clear the security context and continue the filter chain without authenticating. Do not log token contents or credentials.

- [ ] **Step 4: Run the focused test and confirm GREEN**

Run the Task 2 Maven command again.

Expected: all `AuthIntegrationTest` tests pass.

### Task 3: Remove Credential Disclosure

**Files:**
- Modify: `fantalol-frontend/index.html`
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java`
- Modify: `fantalol-backend/README.md`
- Modify: `fantalol-backend/postman/FantaLoL-Backend.postman_collection.json`
- Modify: `fantalol-backend/sql/data-seed.sql`

**Interfaces:**
- Consumes: Spring Boot static-resource copy from `fantalol-frontend` configured by Maven.
- Produces: blank login controls and maintained public artifacts with no administrator credential examples.

- [ ] **Step 1: Write failing static-resource assertions**

Extend `StaticResourceIntegrationTest` so `/` does not contain `Demo admin`, `Admin123!`, a preset username value, or a preset password value.

- [ ] **Step 2: Run the focused test and confirm RED**

Run: `docker run --rm -v /home/massimilianofabbo/FantaLol:/workspace -v /tmp/fantaleague-m2:/root/.m2 -w /workspace/fantalol-backend maven:3.9.9-eclipse-temurin-17 mvn -q -Dtest=StaticResourceIntegrationTest test`

Expected: failure because the login dialog currently renders the legacy demo hint.

- [ ] **Step 3: Remove maintained credential examples**

Delete the `.demo-hint` paragraph from `index.html`. Remove the obsolete CSS rule if unused. Replace the README credential table with a statement that administrator credentials are privately provisioned. Remove the Postman administrator request body rather than replacing it with the new secret. Update SQL seed data to use `Natsu_Admin` and the same BCrypt hash, with no plaintext password comment; update demo league lookup accordingly.

- [ ] **Step 4: Rebuild static resources and confirm GREEN**

Run the Task 3 Maven command again.

Expected: all `StaticResourceIntegrationTest` tests pass.

### Task 4: Full Verification and Secret Scan

**Files:**
- Verify all changed source, test, frontend, documentation, and SQL files.

**Interfaces:**
- Consumes: deliverables from Tasks 1–3.
- Produces: a verified release-ready authentication reset.

- [ ] **Step 1: Run the complete backend suite**

Run: `docker run --rm -v /home/massimilianofabbo/FantaLol:/workspace -v /tmp/fantaleague-m2:/root/.m2 -w /workspace/fantalol-backend maven:3.9.9-eclipse-temurin-17 mvn test -q`

Expected: Maven exits 0 with all tests passing.

- [ ] **Step 2: Validate frontend syntax**

Run: `node --check fantalol-frontend/js/app.js`

Expected: exit 0 with no output.

- [ ] **Step 3: Scan maintained files for leaked credentials**

Search source-controlled paths while excluding `target` and the historical Superpowers documents that record previous requirements. Confirm the old username/password pair, the new plaintext password, and `Demo admin` do not occur in maintained application, frontend, README, Postman, or SQL files.

- [ ] **Step 4: Inspect final changes without Git**

Read each modified file directly and confirm the initializer is one-time, transactional, and does not delete post-migration users; the login form remains blank; and the directory endpoint still exposes only usernames.
