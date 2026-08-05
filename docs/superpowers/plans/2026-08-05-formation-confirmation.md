# Formation Confirmation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let managers confirm the fixed five-player formation for each matchday during the Tuesday–Thursday window, and let global ADMIN confirm all teams.

**Architecture:** Persist a `confirmed` flag on each matchday formation. Add server-side confirmation endpoints that reuse existing roster validation and lineup scheduling, then expose manager and ADMIN controls in the existing matchday/formation UI.

**Tech Stack:** Spring Boot, JPA/Hibernate, Java tests, vanilla JavaScript, HTML/CSS, Node test runner.

## Global Constraints

- Confirmation is allowed only Tuesday 00:00 through Thursday 23:59 in the existing application timezone/clock.
- Past effective lineup periods and their scores must not be rewritten.
- Global confirmation requires the `ADMIN` role and must be enforced server-side.
- A valid confirmation contains exactly five distinct players, one for each role.

### Task 1: Backend confirmation model and service behavior

**Files:**
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/Formation.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/dto/FormationResponse.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/FormationService.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/matchday/FormationController.java`
- Test: existing formation service/controller test locations under `fantalol-backend/src/test/java`

- [ ] Write failing tests for manager confirmation, Tuesday–Thursday enforcement, idempotent repeat confirmation, and ADMIN bulk authorization.
- [ ] Run the focused Maven tests and verify the new tests fail for the missing endpoint/field.
- [ ] Add `confirmed` to `Formation`, expose it in the response DTO, and implement manager confirmation using the current five-player roster for fixed-roster leagues.
- [ ] Add a role-protected bulk confirmation endpoint scoped to a league and matchday; reuse the same validation and avoid rewriting closed/past lineup periods.
- [ ] Run focused backend tests, then the complete backend test suite.

### Task 2: Matchday UI controls

**Files:**
- Modify: `fantalol-frontend/lega.html`
- Modify: `fantalol-frontend/js/league-detail.js`
- Modify: `fantalol-frontend/css/league-detail.css`
- Test: `fantalol-frontend/tests/league-detail-behavior.test.js`

- [ ] Write failing frontend tests asserting manager `Conferma rosa` and ADMIN `Conferma tutte le squadre` hooks and hidden-state behavior.
- [ ] Run the focused Node tests and verify failure.
- [ ] Add the manager button/status inside the Rosa dialog and render it only during the backend-reported editable window.
- [ ] Add the ADMIN bulk button under each matchday’s global administration area, call the new API, and refresh formation/ranking data after success.
- [ ] Run all frontend tests.

### Task 3: Verification and handoff

- [ ] Run `git diff --check` and the complete backend/frontend suites.
- [ ] Inspect the final diff for authorization, timezone, and past-period regressions.
- [ ] Report the changed files and exact Render deployment/retest steps.
