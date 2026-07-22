# Favicon Gradient Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the page's blue-to-violet brand gradient to the favicon letter.

**Architecture:** Add an SVG linear gradient definition and reference it from the existing F path. Extend the frontend static tests to protect the exact brand colors and removal of the obsolete green fill.

**Tech Stack:** SVG, Node.js built-in test runner

## Global Constraints

- Keep the favicon geometry, dark background, view box, and accessibility attributes unchanged.
- Use `#4f8cff` and `#8b5cf6` in a 135-degree linear gradient.
- Do not execute any Git command.

---

### Task 1: Favicon Brand Gradient

**Files:**
- Modify: `fantalol-frontend/favicon.svg`
- Modify: `fantalol-frontend/tests/home-visuals.test.js`

- [ ] Add a failing test that reads the favicon, requires a `linearGradient`, both brand colors, an F-path `url(#brand-gradient)` fill, and absence of `#c8ff33`.
- [ ] Run `node --test fantalol-frontend/tests/home-visuals.test.js` and confirm failure on the missing gradient.
- [ ] Add `brand-gradient` with coordinates equivalent to 135 degrees and update only the F path fill.
- [ ] Parse the SVG as XML, run all frontend tests, and run JavaScript syntax validation.
