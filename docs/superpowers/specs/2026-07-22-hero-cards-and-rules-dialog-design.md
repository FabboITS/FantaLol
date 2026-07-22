# Hero Cards and Rules Dialog Design

## Goal

Improve the perceived sharpness of the Caps and SkewMond portraits in the home-page hero and give the rules dialog a more centered, spacious, and layered presentation.

## Scope

The change is limited to the home-page hero cards and the rules dialog. It does not alter copy, application behavior, repository visibility, or `.gitignore`.

## Hero Cards

The current portraits are very small compressed WebP assets stored with `.jpg` extensions. Both are stretched with `object-fit: cover` across relatively large cards, which makes their limited source detail more noticeable.

The cards will remain fully filled. Their dimensions will be reduced moderately to lower the required image enlargement while preserving the existing overlapping composition. Caps and SkewMond will receive independent crop positioning so each face remains prominent. The solution will avoid artificial sharpening filters because they amplify compression artifacts without restoring detail.

## Rules Dialog

The rules dialog will be explicitly centered in the viewport. Its outer frame will retain the current visual language and constrained height. The scrollable content area will receive additional bottom padding so the final paragraph does not sit against the dialog edge. A subtle bottom fade will visually separate the scrolling text from the frame and add depth without obscuring content.

## Responsive Behavior

The existing breakpoint that hides the hero visual below 1000 pixels will remain unchanged. The rules dialog will continue to fit narrow viewports, with spacing adjusted so the added depth does not reduce mobile readability.

## Verification

Static checks will confirm that the hero images retain `object-fit: cover`, use player-specific positioning, and that the rules dialog has explicit centering and bottom breathing room. The frontend JavaScript syntax check and the backend test suite will be run to guard against regressions.
