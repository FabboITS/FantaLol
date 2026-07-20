# FantaLeague Visual Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change the site's visible brand to FantaLeague, present Caps and SkewMond with their local portraits in the hero, and replace the lime theme with an electric blue-to-purple palette.

**Architecture:** Keep this as a frontend-only presentation change. `index.html` owns visible branding and accessible hero-card structure, while `style.css` owns the shared accent palette and the complete hero-card treatment; the existing Spring static-resource integration test provides regression coverage against the packaged frontend.

**Tech Stack:** HTML5, CSS custom properties, vanilla JavaScript-compatible static markup, Java 17, Spring Boot MockMvc, JUnit 5, Maven.

## Global Constraints

- Do not run Git commands.
- Change only the visible name to “FantaLeague”; keep directories, packages, database names, configuration namespaces, API endpoints, and browser-storage keys unchanged.
- Use the existing `/Player_immage/Mid/Caps.jpg` and `/Player_immage/Jungle/SkewMond.jpg` files.
- Keep the current dark foundation and replace lime presentation accents with electric blue and violet.
- Keep orange and red for warnings, errors, and destructive actions.
- Do not change backend application behavior.

## File Map

- `fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java`: regression checks for packaged branding, hero image references, accessible markup, and theme tokens.
- `fantalol-frontend/index.html`: visible site name and semantic Caps/SkewMond hero-card content.
- `fantalol-frontend/css/style.css`: electric-blue/violet theme plus photographic hero-card layout and responsive presentation.

---

### Task 1: Define static frontend regression coverage

**Files:**
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java`

**Interfaces:**
- Consumes: packaged `/index.html` and `/css/style.css` static resources.
- Produces: `homeUsesFantaLeagueBrandAndPlayerHeroImages()` and `mainStylesheetUsesBlueVioletTheme()` regression tests.

- [ ] **Step 1: Add the failing branding and hero-card test**

Add the following test method inside `StaticResourceIntegrationTest`:

```java
@Test
void homeUsesFantaLeagueBrandAndPlayerHeroImages() throws Exception {
    mockMvc.perform(get("/index.html"))
            .andExpect(status().isOk())
            .andExpect(content().string(containsString("<title>FantaLeague — Build your legacy</title>")))
            .andExpect(content().string(containsString("aria-label=\"FantaLeague home\"")))
            .andExpect(content().string(containsString("FANTA<span>LEAGUE</span>")))
            .andExpect(content().string(containsString("src=\"/Player_immage/Mid/Caps.jpg\"")))
            .andExpect(content().string(containsString("alt=\"Caps, mid laner for G2 Esports\"")))
            .andExpect(content().string(containsString("src=\"/Player_immage/Jungle/SkewMond.jpg\"")))
            .andExpect(content().string(containsString("alt=\"SkewMond, jungler\"")));
}
```

- [ ] **Step 2: Add the failing blue-violet theme test**

Add these static imports:

```java
import static org.hamcrest.Matchers.not;
```

Then add:

```java
@Test
void mainStylesheetUsesBlueVioletTheme() throws Exception {
    mockMvc.perform(get("/css/style.css"))
            .andExpect(status().isOk())
            .andExpect(content().string(containsString("--lime:#4f8cff")))
            .andExpect(content().string(containsString("--violet:#8b5cf6")))
            .andExpect(content().string(containsString(".hero-player-image")))
            .andExpect(content().string(containsString("linear-gradient")))
            .andExpect(content().string(not(containsString("#c7ff37"))))
            .andExpect(content().string(not(containsString("#d6ff6b"))));
}
```

- [ ] **Step 3: Run the focused tests and confirm the expected failures**

Run:

```bash
cd fantalol-backend && mvn -Dtest=StaticResourceIntegrationTest test
```

Expected: Maven exits nonzero; the new assertions fail because the packaged frontend still contains `FantaLoL`, monogram-based hero cards, `#c7ff37`, and `#d6ff6b`.

---

### Task 2: Apply visible branding and accessible hero portraits

**Files:**
- Modify: `fantalol-frontend/index.html`

**Interfaces:**
- Consumes: existing local Caps and SkewMond JPG paths.
- Produces: visible `FantaLeague` branding and `.hero-player-image` elements with meaningful alternative text.

- [ ] **Step 1: Change only user-facing brand strings**

Replace the document metadata with:

```html
<meta name="description" content="FantaLeague — crea la tua lega e costruisci il roster LEC perfetto.">
<title>FantaLeague — Build your legacy</title>
```

Replace the header brand with:

```html
<a class="brand" href="#home" aria-label="FantaLeague home"><span class="brand-mark">F</span><span>FANTA<span>LEAGUE</span></span></a>
```

Replace the footer brand with:

```html
<a class="brand" href="#home" aria-label="FantaLeague home"><span class="brand-mark">F</span><span>FANTA<span>LEAGUE</span></span></a>
```

Do not alter any lowercase `fantalol` technical identifier outside these visible strings.

- [ ] **Step 2: Replace the abstract hero cards with semantic portrait markup**

Replace the current `.hero-visual` block with:

```html
<div class="hero-visual">
    <div class="orbit orbit-a" aria-hidden="true"></div>
    <div class="orbit orbit-b" aria-hidden="true"></div>
    <article class="player-card card-back">
        <img class="hero-player-image" src="/Player_immage/Jungle/SkewMond.jpg" alt="SkewMond, jungler">
        <div class="card-shade" aria-hidden="true"></div>
        <div class="card-back-copy"><span>JUNGLE</span><b>SKEWMOND</b></div>
    </article>
    <article class="player-card card-main">
        <img class="hero-player-image" src="/Player_immage/Mid/Caps.jpg" alt="Caps, mid laner for G2 Esports">
        <div class="card-shade" aria-hidden="true"></div>
        <div class="card-top"><span>MID</span><small>G2</small></div>
        <div class="card-main-copy"><h2>CAPS</h2><p>G2 ESPORTS · MID LANER</p></div>
        <div class="rating"><strong>100</strong><span>QUOTAZIONE</span></div>
    </article>
    <div class="float-pill pill-one" aria-hidden="true">⚡ MVP <b>+3</b></div>
    <div class="float-pill pill-two" aria-hidden="true">◆ VITTORIA <b>+1</b></div>
</div>
```

- [ ] **Step 3: Check the HTML references and visible-brand scope**

Run:

```bash
rg -n "FantaLoL|FANTALOL|Caps.jpg|SkewMond.jpg|FantaLeague" fantalol-frontend/index.html
```

Expected: both image paths and the new visible brand are found; no old visible `FantaLoL`/`FANTALOL` string remains in `index.html`.

---

### Task 3: Replace lime styling and build photographic hero cards

**Files:**
- Modify: `fantalol-frontend/css/style.css`

**Interfaces:**
- Consumes: Task 2 classes `.hero-player-image`, `.card-shade`, `.card-back-copy`, and `.card-main-copy`.
- Produces: an electric-blue/violet theme and readable layered portrait cards.

- [ ] **Step 1: Update the shared theme tokens and fixed lime colors**

Keep the existing internal `--lime` name but set the root tokens to:

```css
:root {
    --ink: #070914;
    --panel: #101526;
    --panel-2: #171d33;
    --line: #29314c;
    --muted: #949db5;
    --white: #f4f5ff;
    --lime: #4f8cff;
    --violet: #8b5cf6;
    --orange: #ff5c35;
    --font-display: "Space Grotesk", sans-serif;
    --font-body: "DM Sans", sans-serif;
}
```

Update the second ambient glow from orange to `var(--violet)`. Replace `rgba(199,255,55,.12)` with `rgba(79,140,255,.24)`, replace the primary-button hover `#d6ff6b` with `#70a2ff`, and replace the scout-card hover border `#596230` with `#596fba`. Preserve red/orange error and destructive styles.

- [ ] **Step 2: Replace the old monogram card rules with layered photo-card rules**

Remove the `.monogram` rule and the old `.card-back b` margin hack. Define the hero-card styles with these declarations:

```css
.player-card {
    position: absolute;
    overflow: hidden;
    isolation: isolate;
    background: #0d1222;
    border: 1px solid rgba(112, 162, 255, .55);
    box-shadow: 0 35px 80px #000, 0 0 45px rgba(79, 140, 255, .18);
    padding: 24px;
}
.hero-player-image {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center top;
    z-index: -2;
}
.card-shade {
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, rgba(5, 8, 22, .08) 25%, rgba(7, 10, 25, .92) 82%, #070a19 100%);
    z-index: -1;
}
.card-main {
    width: 310px;
    height: 450px;
    transform: rotate(4deg);
    z-index: 2;
    clip-path: polygon(0 0, 100% 0, 100% 90%, 88% 100%, 0 100%);
}
.card-back {
    width: 235px;
    height: 330px;
    left: 1%;
    top: 12%;
    transform: rotate(-12deg);
    border-color: rgba(139, 92, 246, .55);
    box-shadow: 0 30px 70px #000, 0 0 38px rgba(139, 92, 246, .2);
}
.card-back .card-shade {
    background: linear-gradient(180deg, rgba(17, 10, 40, .08) 20%, rgba(12, 8, 31, .94) 90%);
}
.card-back-copy,
.card-main-copy {
    position: absolute;
    left: 24px;
    right: 24px;
    bottom: 24px;
}
.card-back-copy span {
    color: #b59cff;
    font: 700 10px var(--font-display);
    letter-spacing: .15em;
}
.card-back-copy b {
    display: block;
    margin-top: 7px;
    color: var(--white);
    font: 700 24px var(--font-display);
}
.card-main-copy h2 {
    font: 700 41px/.8 var(--font-display);
    margin: 8px 0;
}
.card-main-copy p {
    margin: 0;
    font-size: 9px;
    letter-spacing: .13em;
    color: #b4bdd3;
}
```

Keep `.card-top` and `.rating` above the image by giving both `position: relative; z-index: 1`; retain the rating's absolute bottom-right placement by setting `.rating { position: absolute; z-index: 1; }`. Move `.card-main-copy` left of the rating with `right: 92px` so labels never overlap.

- [ ] **Step 3: Add a blue-to-violet accent gradient where it communicates the new palette**

Set `.brand-mark` and `.button-primary` backgrounds to:

```css
background: linear-gradient(135deg, var(--lime), var(--violet));
```

Use solid `var(--lime)` for text, focus, and active-state contrast. Keep dark text on primary buttons and the brand mark.

- [ ] **Step 4: Verify the focused static-resource tests pass**

Run:

```bash
cd fantalol-backend && mvn -Dtest=StaticResourceIntegrationTest test
```

Expected: all `StaticResourceIntegrationTest` tests pass, including both new methods.

---

### Task 4: Complete regression and responsive verification

**Files:**
- Verify: `fantalol-frontend/index.html`
- Verify: `fantalol-frontend/css/style.css`
- Verify: `fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java`

**Interfaces:**
- Consumes: completed presentation changes from Tasks 1–3.
- Produces: evidence that the redesign is packaged correctly and existing behavior remains intact.

- [ ] **Step 1: Confirm technical names were not renamed**

Run:

```bash
rg -n "fantalol_token|fantalol_user" fantalol-frontend/js/app.js
rg -n "com\.fantalol|DB_NAME:fantalol|fantalol:" fantalol-backend/src/main fantalol-backend/pom.xml
```

Expected: the existing browser-storage keys, Java package namespace, database default, and application configuration namespace are still present.

- [ ] **Step 2: Confirm old lime literals and visible brand strings are absent from frontend presentation files**

Run:

```bash
rg -n "#c7ff37|#d6ff6b|FantaLoL|FANTALOL" fantalol-frontend/index.html fantalol-frontend/css
```

Expected: no matches.

- [ ] **Step 3: Run the full automated test suite**

Run:

```bash
cd fantalol-backend && mvn test
```

Expected: Maven exits 0 and reports zero failures and zero errors.

- [ ] **Step 4: Perform a browser smoke test at representative widths**

Serve the app using the project's normal local workflow and inspect widths of 1440 px, 1024 px, 768 px, and 390 px. Confirm:

- the header and footer read `FantaLeague`;
- Caps is the large foreground portrait and SkewMond is the tilted background portrait on desktop;
- player names, roles, team, and Caps valuation remain readable;
- blue and violet replace lime across buttons, active navigation, headings, filters, dialogs, auction UI, and glows;
- the hero visual hides at the existing tablet breakpoint without leaving horizontal overflow;
- dialogs, players, leagues, auctions, and user-directory presentation remain usable;
- red/orange warning and destructive states remain distinct.

- [ ] **Step 5: Record the outcome without Git operations**

Report the exact test command results, browser widths checked, and modified file paths. Do not stage, commit, branch, or run any other Git command.
