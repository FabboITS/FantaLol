# Player and Team Images Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display every uploaded player portrait and a local team logo on public player cards, while correcting `Hans SamD` to `SamD`.

**Architecture:** The backend stores and returns explicit local image URLs. The frontend joins each player's `teamId` to the existing team response, renders both images, and degrades to the current text/initial presentation when an asset is unavailable.

**Tech Stack:** Java 17, Spring Boot, JPA, MySQL SQL scripts, JUnit 5/AssertJ, vanilla JavaScript, HTML, CSS.

## Global Constraints

- Move the complete `Player_immage` directory to `fantalol-frontend/Player_immage`; do not duplicate it.
- Preserve all role subdirectories and all 50 JPG files.
- Store all 10 team logos locally; do not depend on third-party hosts at runtime.
- Do not rename the separate `Hans Sama` player.
- Use the existing letter and text presentation as image failure fallbacks.
- Do not run Git commands.

---

### Task 1: Expose player image URLs

**Files:**
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/team/LecPlayerServiceTest.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/team/LecPlayer.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/team/dto/LecPlayerRequest.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/team/dto/LecPlayerResponse.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/team/LecPlayerService.java`
- Modify: `fantalol-backend/sql/schema.sql`

**Interfaces:**
- Produces: nullable `String imageUrl` on `LecPlayer`, `LecPlayerRequest`, and `LecPlayerResponse`.

- [ ] Add `"/Player_immage/Mid/Caps.jpg"` to the create request test and assert `response.imageUrl()` returns it.
- [ ] Run `cd fantalol-backend && mvn -Dtest=LecPlayerServiceTest test`; expect compilation failure because the DTO signatures do not yet contain `imageUrl`.
- [ ] Add `imageUrl` to the entity column, request/response records, response factories, and service request-to-entity mapping. Add nullable `image_url VARCHAR(255)` to `lec_players`.
- [ ] Run `cd fantalol-backend && mvn -Dtest=LecPlayerServiceTest test`; expect all tests to pass.

### Task 2: Move portraits and seed every local asset URL

**Files:**
- Move: `Player_immage/` → `fantalol-frontend/Player_immage/`
- Modify: `fantalol-backend/sql/data-seed.sql`
- Create: `fantalol-backend/src/test/java/com/fantalol/backend/common/SeedAssetReferenceTest.java`

**Interfaces:**
- Consumes: `lec_players.image_url` from Task 1.
- Produces: 50 explicit `/Player_immage/<Role>/<file>.jpg` seed values.

- [ ] Write a repository-root-aware test that parses player seed image paths and asserts there are 50 unique paths and each resolves beneath `fantalol-frontend` to a regular file.
- [ ] Run `cd fantalol-backend && mvn -Dtest=SeedAssetReferenceTest test`; expect failure because no image paths are seeded.
- [ ] Move the directory with `mv Player_immage fantalol-frontend/Player_immage` and expand each player insert to include `image_url` with the exact uploaded filename, including `Hans_Sama.jpg`, `Naak_Nako.jpg`, `ISMA.jpg`, and lowercase `nuc.jpg`.
- [ ] Search all project-owned source files for `Hans SamD`; replace it with `SamD` only where found and verify `Hans Sama` remains unchanged.
- [ ] Run `cd fantalol-backend && mvn -Dtest=SeedAssetReferenceTest test`; expect 50 valid portrait references.

### Task 3: Add local team logos and seed their URLs

**Files:**
- Create: `fantalol-frontend/assets/team-logos/*` (10 logo files)
- Modify: `fantalol-backend/sql/data-seed.sql`
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/common/SeedAssetReferenceTest.java`

**Interfaces:**
- Produces: 10 explicit `lec_teams.logo_url` values under `/assets/team-logos/`.

- [ ] Extend the asset-reference test to assert 10 unique team-logo URLs exist locally.
- [ ] Run `cd fantalol-backend && mvn -Dtest=SeedAssetReferenceTest test`; expect the team-logo assertion to fail.
- [ ] Obtain a recognizable logo for each seeded organization from official/public brand sources, store it locally with stable lowercase filenames, and change the team insert to `(nome, sigla, logo_url)`.
- [ ] Run `cd fantalol-backend && mvn -Dtest=SeedAssetReferenceTest test`; expect all 60 asset references to pass.

### Task 4: Render portraits and inline team logos

**Files:**
- Modify: `fantalol-frontend/js/app.js`
- Modify: `fantalol-frontend/css/style.css`
- Modify: `fantalol-frontend/index.html`

**Interfaces:**
- Consumes: player `imageUrl`, `teamId`; team `id`, `logoUrl`.
- Produces: `renderPlayerCard(player, team)` markup with portrait and resilient fallbacks.

- [ ] Add a small self-contained render helper so player-card markup can be checked independently; map `state.teams` by numeric ID during rendering.
- [ ] Render the portrait inside `.avatar`, retain the initial beneath it, and attach an error handler that hides only the failed image.
- [ ] Render a decorative inline team logo before escaped `teamNome · nazionalita`; attach an error handler that hides only the failed logo.
- [ ] Add CSS for cropped portrait coverage, a compact inline metadata row, and consistently sized team logos.
- [ ] Update the static Caps hero card to use the local Caps portrait and G2 logo, while keeping its existing content and styling intent.
- [ ] Run a deterministic frontend syntax check with `node --check fantalol-frontend/js/app.js`; expect no output and exit code 0.

### Task 5: Full verification

**Files:**
- Verify all modified source and asset files.

- [ ] Run `cd fantalol-backend && mvn test`; expect the complete suite to pass.
- [ ] Count portraits with `find fantalol-frontend/Player_immage -type f -name '*.jpg'`; expect 50.
- [ ] Count team-logo files beneath `fantalol-frontend/assets/team-logos`; expect 10.
- [ ] Confirm the original root `Player_immage` no longer exists.
- [ ] Start the application using its documented Docker workflow and smoke-check that Caps shows his portrait, the G2 logo, and `G2 Esports · Danimarca`; check a missing-image simulation preserves the initial/text fallback.

### Task 6: Show complete uncropped portraits

**Files:**
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java`
- Modify: `fantalol-frontend/css/player-images.css`

- [ ] Add a static-resource regression test that requires the portrait stylesheet to contain `object-fit: contain` and `object-position: center bottom`.
- [ ] Run the focused integration test and verify it fails while the stylesheet still uses `cover` and `center top`.
- [ ] Update `.player-portrait` to use full-image containment, bottom-center alignment, and add a subtle dark background to `.avatar`.
- [ ] Run the focused test and complete backend suite; expect all tests to pass.
