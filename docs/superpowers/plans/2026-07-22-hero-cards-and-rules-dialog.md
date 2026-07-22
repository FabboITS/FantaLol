# Hero Cards and Rules Dialog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve hero portrait sharpness and give the rules dialog stronger centering, bottom spacing, and depth.

**Architecture:** Keep the existing HTML structure and implement the presentation changes in the shared stylesheet. Add a small Node static regression test that reads the stylesheet and verifies the required selectors and declarations.

**Tech Stack:** HTML5, CSS, Node.js built-in test runner

## Global Constraints

- Keep all generated code, comments, test names, and documentation in English.
- Do not alter `.gitignore`, `docs/` tracking, or `.superpowers/` tracking.
- Do not execute any Git command.
- Keep `object-fit: cover` so both hero cards remain fully filled.
- Do not add artificial image sharpening filters.

---

### Task 1: Hero Portrait Presentation

**Files:**
- Modify: `fantalol-frontend/css/style.css`
- Create: `fantalol-frontend/tests/home-visuals.test.js`

**Interfaces:**
- Consumes: `.card-main`, `.card-back`, and `.hero-player-image` selectors from the home-page hero.
- Produces: player-specific crop rules and smaller card dimensions enforced by a static regression test.

- [ ] **Step 1: Write the failing hero-card regression test**

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const stylesheet = fs.readFileSync(path.join(__dirname, '../css/style.css'), 'utf8');

test('hero portraits use smaller filled cards and player-specific crops', () => {
  assert.match(stylesheet, /\.hero-player-image\{[^}]*object-fit:cover/);
  assert.match(stylesheet, /\.card-main\{width:280px;height:410px/);
  assert.match(stylesheet, /\.card-back\{width:210px;height:300px/);
  assert.match(stylesheet, /\.card-main \.hero-player-image\{[^}]*object-position:center top/);
  assert.match(stylesheet, /\.card-back \.hero-player-image\{[^}]*object-position:center top/);
  assert.doesNotMatch(stylesheet, /filter:\s*(?:contrast|sharpen)/);
});
```

- [ ] **Step 2: Run the test and confirm the expected failure**

Run: `node --test fantalol-frontend/tests/home-visuals.test.js`

Expected: FAIL because the current cards are `310x450` and `235x330`, and player-specific crop rules do not exist.

- [ ] **Step 3: Implement the minimal hero-card CSS**

Update the card rules to use `280x410` for Caps and `210x300` for SkewMond. Preserve `object-fit: cover`, add separate portrait selectors, and keep the existing transforms, borders, shadows, and visual hierarchy.

- [ ] **Step 4: Run the hero-card test**

Run: `node --test fantalol-frontend/tests/home-visuals.test.js`

Expected: PASS.

### Task 2: Rules Dialog Spacing and Depth

**Files:**
- Modify: `fantalol-frontend/css/style.css`
- Modify: `fantalol-frontend/tests/home-visuals.test.js`

**Interfaces:**
- Consumes: `.rules-dialog` and `.rules-content` selectors.
- Produces: explicit viewport centering, scroll-safe bottom spacing, and a non-interactive bottom depth fade.

- [ ] **Step 1: Add the failing rules-dialog regression test**

```js
test('rules dialog is centered and preserves bottom depth', () => {
  assert.match(stylesheet, /\.rules-dialog\{[^}]*margin:auto/);
  assert.match(stylesheet, /\.rules-dialog::after\{[^}]*linear-gradient/);
  assert.match(stylesheet, /\.rules-dialog::after\{[^}]*pointer-events:none/);
  assert.match(stylesheet, /\.rules-content\{[^}]*padding:0 18px 48px 0/);
});
```

- [ ] **Step 2: Run the test and confirm the expected failure**

Run: `node --test fantalol-frontend/tests/home-visuals.test.js`

Expected: one passing hero test and one failing rules-dialog test because centering, fade, and bottom padding are absent.

- [ ] **Step 3: Implement the minimal rules-dialog CSS**

Add `margin: auto` and `position: relative` to the dialog, add a bottom pseudo-element with a transparent-to-panel gradient and `pointer-events: none`, and change the scroll area to include `48px` bottom padding while retaining `18px` right padding.

- [ ] **Step 4: Run all frontend tests and syntax checks**

Run: `node --test fantalol-frontend/tests/*.test.js && node --check fantalol-frontend/js/app.js`

Expected: all tests PASS and JavaScript syntax validation exits with status 0.

### Task 3: Full Project Verification

**Files:**
- Verify: `fantalol-frontend/css/style.css`
- Verify: `fantalol-frontend/tests/home-visuals.test.js`

**Interfaces:**
- Consumes: completed CSS and regression tests.
- Produces: fresh evidence that frontend checks and backend tests remain green.

- [ ] **Step 1: Run the complete verification suite**

Run: `docker run --rm -v /home/massimilianofabbo/FantaLol:/workspace -v /tmp/fantaleague-m2:/root/.m2 -w /workspace/fantalol-backend maven:3.9.9-eclipse-temurin-17 mvn test -q && node --test fantalol-frontend/tests/*.test.js && node --check fantalol-frontend/js/app.js`

Expected: Maven exits with status 0, all Node tests pass, and the syntax check exits with status 0.
