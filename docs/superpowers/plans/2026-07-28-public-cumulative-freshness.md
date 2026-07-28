# Public Cumulative Freshness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose sanitized persisted Oracle freshness with public cumulative score data and render fresh, stale, and awaiting states accurately.

**Architecture:** Wrap both existing cumulative endpoint item arrays in a shared `CumulativeDataResponse<T>` containing `status`, `lastUpdatedAt`, source-level `provisional`, and `items`. A focused service derives only these fields from the persisted Oracle provider row; the frontend normalizes both wrapped and legacy array payloads and keeps source freshness separate from ranking-team provisional scoring.

**Tech Stack:** Java 17, Spring Boot MVC/Security, JPA repository, JUnit 5/Mockito/MockMvc, browser JavaScript, Node test runner.

## Global Constraints

- Do not expose provider errors, unmatched-player data, import counters, or provider snapshots publicly.
- Do not change scoring batch internals.
- Keep ranking team-level `provisional` distinct from wrapper source-level `provisional`.
- Do not commit these changes.

---

### Task 1: Sanitized backend wrapper

**Files:**
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/scoring/dto/CumulativeDataResponse.java`
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/scoring/CumulativeDataFreshnessService.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/scoring/CumulativeScoringController.java`
- Test: `fantalol-backend/src/test/java/com/fantalol/backend/scoring/CumulativeDataFreshnessServiceTest.java`
- Test: `fantalol-backend/src/test/java/com/fantalol/backend/scoring/CumulativeScoringControllerTest.java`
- Test: `fantalol-backend/src/test/java/com/fantalol/backend/scoring/CumulativeScoringControllerSecurityTest.java`

**Interfaces:**
- Consumes: `ProviderSyncStateRepository.findByProvider(ProviderGame.ORACLES_ELIXIR)` and existing cumulative scoring lists.
- Produces: `CumulativeDataResponse<T>(String status, Instant lastUpdatedAt, boolean provisional, List<T> items)` and `CumulativeDataFreshnessService.wrap(List<T>)`.

- [ ] Write service tests for fresh, stale-with-last-success, and initial-awaiting mappings, asserting the public response type contains no diagnostic fields.
- [ ] Run the service test and verify it fails because the response/service do not exist.
- [ ] Implement the response record and minimal persisted-state mapping.
- [ ] Run the service test and verify it passes.
- [ ] Write controller and security tests proving both endpoints return wrapper metadata, the LEC endpoint remains anonymous, and league ranking remains authenticated and membership-checked.
- [ ] Run the controller/security tests and verify the old bare-list contract fails.
- [ ] Update the controller to wrap existing score lists; run focused tests to green.

### Task 2: Defensive frontend normalization and rendering

**Files:**
- Modify: `fantalol-frontend/js/lec-data-source.js`
- Modify: `fantalol-frontend/js/league-detail.js`
- Test: `fantalol-frontend/tests/lec-data-source.test.js`
- Test: `fantalol-frontend/tests/league-detail-behavior.test.js`

**Interfaces:**
- Consumes: wrapped payloads with `status`, `lastUpdatedAt`, `provisional`, and `items`, plus legacy arrays.
- Produces: normalized cumulative sections and visible freshness labels without modifying each ranking item's own `provisional` flag.

- [ ] Add executable data-source tests with a fake request for wrapped and legacy responses; verify they fail against raw forwarding.
- [ ] Implement `normalizeCumulativeSection` and apply it to both cumulative loaders; run tests to green.
- [ ] Add executable rendering-contract tests for fresh, stale, and awaiting source labels and separate team-level provisional rendering; verify they fail against array-only renderers.
- [ ] Store normalized section metadata separately from item arrays and render labels from wrapper state while preserving last-known-good refresh semantics.
- [ ] Run focused and complete frontend suites to green.

### Task 3: Verification and report

**Files:**
- Create: `.superpowers/sdd/2026-07-28-cumulative-summer-fantasy-scoring/final-fix-freshness-report.md`

- [ ] Run focused backend tests in Docker and record exact results.
- [ ] Run all frontend tests and record exact results.
- [ ] Run scoped `git diff --check`, inspect overlap, and document changes, red/green evidence, security properties, and verification without committing.
