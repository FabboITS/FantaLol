# Player and Team Images Design

## Goal

Replace the letter placeholder in every player card with the corresponding uploaded player portrait. Show a small team logo inline before the existing `Team · Nationality` text, and correct the player nickname `Hans SamD` to `SamD` wherever it remains in project-owned data.

## Asset storage

- Move the complete root-level `Player_immage` directory into `fantalol-frontend/Player_immage`, preserving its role subdirectories and all 50 JPG files.
- Add local logo assets for all 10 seeded teams in a separate frontend static-assets directory.
- Use stable, web-relative asset URLs. The application must not depend on third-party image hosting at runtime.
- Do not duplicate the portraits: after the move, `fantalol-frontend/Player_immage` is their canonical location.

## Data model and API

- Add an optional player image URL field to the player persistence model, SQL schema, seed data, request DTO, and response DTO.
- Populate every seeded player with the matching local portrait URL. Explicit seed mappings handle spaces, underscores, and capitalization safely.
- Populate each seeded team's existing `logo_url` field with its local logo URL.
- Continue returning team ID and team name with each player. The frontend joins `player.teamId` to the already-loaded teams response to obtain the logo URL.
- Correct any project-owned `Hans SamD` nickname to `SamD`. Do not rename the separate `Hans Sama` player.

## Player-card presentation

- Replace the large initial in `.avatar` with a full, uncropped portrait. Fit the entire image inside the portrait area without distortion, align it to the bottom center, and leave the avatar background transparent so the scout-card background remains visible.
- Keep the nickname, role, quotation, and nationality behavior unchanged.
- Render the team metadata as a compact inline row: small team logo, then `Team name · Nationality`, for example: G2 logo followed by `G2 Esports · Danimarca`.
- Give images useful alternative text while avoiding redundant screen-reader output for decorative team logos.

## Failure handling

- If a portrait URL is absent or the file fails to load, display the player's initial using the current placeholder styling.
- If a team logo is absent or fails to load, hide only the logo and retain `Team name · Nationality`.
- Continue escaping all user-visible API text before inserting generated markup.

## Verification

- Backend tests verify that player and team DTOs expose their image URLs correctly.
- Seed/static-asset checks verify that all seeded players and teams reference existing local files.
- Frontend tests, where supported by the current lightweight frontend setup, cover path lookup/rendering and image fallback behavior. Otherwise, use a deterministic static markup check plus browser-level smoke verification.
- Run the backend test suite and confirm all 50 portraits and all 10 team logos are present and served from local paths.

## Scope

This change applies to the public player-card section. It does not redesign auction, roster, or formation views, although the API image fields remain reusable by those views later.
