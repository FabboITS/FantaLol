# FantaLeague Visual Redesign

## Goal

Refresh the site's visible identity and hero presentation while preserving all existing application behavior and technical identifiers.

## Scope

- Change the user-facing site name from “FantaLoL” to “FantaLeague”.
- Replace the abstract Caps and SkewMond hero-card artwork with their existing local player photographs.
- Replace the lime accent system with a blue palette that transitions toward purple.
- Preserve the current page structure, application behavior, responsive breakpoints, backend configuration, package names, storage keys, database identifiers, and directory names.

## Branding

The visible name will become “FantaLeague” in:

- the HTML document title;
- the meta description;
- the header brand;
- the footer brand;
- user-facing accessibility labels associated with the brand.

Technical references containing `fantalol`, including Java packages, application configuration, database settings, local-storage keys, URLs, and folders, will remain unchanged.

## Color System

The current dark visual foundation remains. The lime accent will be replaced by an electric blue primary accent with violet secondary tones. The palette will be applied consistently to buttons, active navigation indicators, headings, outlined display text, labels, values, borders, focus states, filters, ambient glows, and card highlights.

The existing internal `--lime` custom-property name will remain unchanged to minimize unrelated code churn, but its value will become the new electric-blue accent. Fixed lime-specific colors, shadows, and hover states will also be updated with blue or violet values so the theme is visually consistent. Orange and red remain reserved for warnings, errors, and destructive actions.

## Hero Player Cards

The hero keeps its two-card composition:

- Caps remains the large foreground card.
- SkewMond remains the smaller, tilted background card.
- Caps uses `/Player_immage/Mid/Caps.jpg`.
- SkewMond uses `/Player_immage/Jungle/SkewMond.jpg`.

Both cards use an esports portrait treatment: the photograph fills the main visual area using `object-fit: cover`, with a dark navy gradient overlay to maintain text contrast. Blue-violet borders and glows integrate the cards with the new palette. Existing useful information—player name, role, team, and valuation—remains legible. The decorative orbit and floating result pills remain, recolored to fit the new theme.

Images are content rather than decoration, so the markup will include meaningful alternative text. The current `aria-hidden="true"` on the whole hero visual will be removed or narrowed so the images and player identity are not hidden from assistive technology while purely decorative elements remain hidden.

## Responsive Behavior

The existing desktop hero layout remains. At the current tablet breakpoint, the hero visual may continue to be hidden to avoid crowding the copy. Existing mobile layouts and application sections must continue to work without horizontal overflow.

## Backend and Data Flow

No backend change is needed. Both player images already exist in the frontend, and all requested changes are static presentation changes. Authentication, API calls, player data, leagues, auctions, and local-storage behavior remain untouched.

## Verification

Verification will cover:

- all intended visible branding reads “FantaLeague”;
- internal `fantalol` identifiers remain unchanged;
- both local hero photographs load successfully;
- hero-card text remains readable over the photographs;
- lime visual accents are replaced by blue-violet styling across all linked frontend stylesheets;
- buttons, filters, dialogs, focus states, auction screens, and user-directory UI retain sufficient contrast;
- the page has no horizontal overflow at desktop, tablet, and mobile widths;
- existing automated frontend/backend static-resource checks still pass where applicable.

## Out of Scope

- Renaming directories, packages, database names, configuration namespaces, API endpoints, or browser storage keys.
- Changing application features or backend behavior.
- Replacing the existing local player photographs with downloaded or generated images.
- Redesigning sections unrelated to the branding, color theme, or hero cards.
