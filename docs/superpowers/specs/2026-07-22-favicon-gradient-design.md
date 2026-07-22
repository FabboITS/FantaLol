# Favicon Gradient Design

## Goal

Replace the favicon letter's obsolete green fill with the same blue-to-violet gradient used by the page brand mark.

## Design

Keep the existing 64 by 64 SVG view box, rounded dark background, letter geometry, accessibility attributes, and file path unchanged. Add one SVG `linearGradient` definition with a 135-degree direction, using `#4f8cff` at the start and `#8b5cf6` at the end. Reference that gradient from the existing F-shaped path.

## Verification

Validate the SVG as XML and confirm that the old `#c8ff33` fill is absent, both page colors are present, and the F path references the gradient. No Git command will be executed.
