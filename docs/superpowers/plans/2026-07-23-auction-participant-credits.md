# Auction Participant Credits Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show every fantasy team's credits in the live auction view, with the current leader's balance projected after the active bid.

**Architecture:** Add a pure `participantCreditBalances(teams, auction)` frontend helper that derives display balances from the synchronized team list and active auction. Render its output in a dedicated panel inside `renderAuction()` so the existing two-second synchronization and immediate post-bid refresh keep the values current.

**Tech Stack:** Browser JavaScript, Node.js built-in test runner, HTML templates, CSS.

## Global Constraints

- Do not change backend endpoints, database persistence, or auction rules.
- Keep function, variable, test, and CSS class names in English.
- Keep user-facing interface text in Italian.
- Do not run Git commands.
- Use the existing two-second synchronization loop; do not add WebSocket or Server-Sent Events.

---

### Task 1: Derive Participant Credit Balances

**Files:**
- Modify: `fantalol-frontend/tests/league-utils.test.js`
- Modify: `fantalol-frontend/js/league-utils.js`

**Interfaces:**
- Consumes: fantasy team objects with `id`, `nome`, `ownerUsername`, and `creditiResidui`; an optional auction with `highestBidderId` and `currentBid`.
- Produces: `participantCreditBalances(teams, auction)`, returning cloned team objects extended with `displayCredits` and `isProjected`.

- [ ] **Step 1: Write failing helper tests**

Import `participantCreditBalances` and add:

```javascript
test('participantCreditBalances projects only the current leader balance', () => {
  const teams = [
    { id: 7, nome: 'Alpha', creditiResidui: 500 },
    { id: 8, nome: 'Beta', creditiResidui: 420 }
  ];

  assert.deepEqual(
    participantCreditBalances(teams, { highestBidderId: '8', currentBid: 120 })
      .map(team => [team.nome, team.displayCredits, team.isProjected]),
    [['Alpha', 500, false], ['Beta', 300, true]]
  );
});

test('participantCreditBalances uses safe persisted balances without an auction', () => {
  const teams = [
    { id: 7, nome: 'Alpha', creditiResidui: '500' },
    { id: 8, nome: 'Beta', creditiResidui: null }
  ];

  assert.deepEqual(
    participantCreditBalances(teams, null).map(team => team.displayCredits),
    [500, 0]
  );
});

test('participantCreditBalances clamps a projected balance to zero', () => {
  const [leader] = participantCreditBalances(
    [{ id: 7, nome: 'Alpha', creditiResidui: 50 }],
    { highestBidderId: 7, currentBid: 80 }
  );

  assert.equal(leader.displayCredits, 0);
  assert.equal(leader.isProjected, true);
});
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
node --test fantalol-frontend/tests/league-utils.test.js
```

Expected: FAIL because `participantCreditBalances` is not exported.

- [ ] **Step 3: Implement the pure helper**

Add to `league-utils.js`:

```javascript
function participantCreditBalances(teams, auction) {
    return (teams || []).map(team => {
        const remainingCredits = Number.isFinite(Number(team.creditiResidui))
            ? Number(team.creditiResidui)
            : 0;
        const isProjected = Boolean(
            auction && Number(team.id) === Number(auction.highestBidderId)
        );
        const currentBid = Number.isFinite(Number(auction?.currentBid))
            ? Number(auction.currentBid)
            : 0;
        return {
            ...team,
            displayCredits: Math.max(0, remainingCredits - (isProjected ? currentBid : 0)),
            isProjected
        };
    });
}
```

Export `participantCreditBalances` from the returned utility object.

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```bash
node --test fantalol-frontend/tests/league-utils.test.js
```

Expected: all utility tests PASS.

### Task 2: Render and Style the Live Credit Panel

**Files:**
- Modify: `fantalol-frontend/tests/league-detail-behavior.test.js`
- Modify: `fantalol-frontend/js/league-detail.js`
- Modify: `fantalol-frontend/css/live-auction.css`

**Interfaces:**
- Consumes: `LeagueUtils.participantCreditBalances(state.leagueTeams, state.activeAuction)`.
- Produces: `renderParticipantCredits()` HTML and `.participant-credits*` presentation styles.

- [ ] **Step 1: Write a failing rendering behavior test**

Add:

```javascript
test('live auction renders synchronized participant credit balances', () => {
  assert.match(script, /function renderParticipantCredits\(/);
  assert.match(script, /LeagueUtils\.participantCreditBalances\(state\.leagueTeams,state\.activeAuction\)/);
  assert.match(script, /participant-credits/);
  assert.match(script, /Saldo previsto/);
  assert.match(script, /renderParticipantCredits\(\)/);
});
```

- [ ] **Step 2: Run the behavior test and verify RED**

Run:

```bash
node --test fantalol-frontend/tests/league-detail-behavior.test.js
```

Expected: FAIL because `renderParticipantCredits()` does not exist.

- [ ] **Step 3: Implement the participant panel**

Add `renderParticipantCredits()` before `renderAuction()`:

```javascript
function renderParticipantCredits(){
    const participants=LeagueUtils.participantCreditBalances(state.leagueTeams,state.activeAuction);
    if(!participants.length)return '<section class="participant-credits"><p class="participant-credits-empty">Nessun partecipante.</p></section>';
    return `<section class="participant-credits"><div class="participant-credits-heading"><span>Crediti partecipanti</span><small>Saldo aggiornato durante l’asta</small></div><div class="participant-credits-list">${participants.map(team=>`<article class="participant-credit ${team.isProjected?'projected':''}"><div><strong>${escapeHtml(team.nome)}</strong><span>${escapeHtml(team.ownerUsername||'Manager')}</span></div><div class="participant-credit-balance"><b>${team.displayCredits}</b><span>${team.isProjected?'Saldo previsto':'Crediti rimasti'}</span></div></article>`).join('')}</div></section>`;
}
```

Append `${renderParticipantCredits()}` to the auction summary content for regular participants, and include it in spectator mode so every viewer can see the balances. Preserve existing bid controls and empty auction content.

- [ ] **Step 4: Add responsive styles**

Add to `live-auction.css`:

```css
.participant-credits{width:100%;border-top:1px solid var(--line);padding-top:14px}
.participant-credits-heading{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin-bottom:10px}
.participant-credits-heading>span{font:600 14px var(--font-display)}
.participant-credits-heading small,.participant-credit span,.participant-credits-empty{color:var(--muted);font-size:10px}
.participant-credits-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px}
.participant-credit{display:flex;align-items:center;justify-content:space-between;gap:12px;background:#0b0e12;border:1px solid #262c34;padding:10px 12px}
.participant-credit>div:first-child{display:flex;flex-direction:column;gap:2px;min-width:0}
.participant-credit strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.participant-credit-balance{display:flex;flex-direction:column;align-items:flex-end;flex-shrink:0}
.participant-credit-balance b{color:var(--lime);font:700 18px var(--font-display)}
.participant-credit.projected{border-color:var(--lime);box-shadow:inset 3px 0 0 var(--lime)}
```

Extend the existing mobile media query so `.participant-credits-heading` stacks when needed.

- [ ] **Step 5: Run frontend tests and verify GREEN**

Run:

```bash
node --test fantalol-frontend/tests/*.test.js
```

Expected: all frontend tests PASS.

### Task 3: Verify Packaged Static Resources

**Files:**
- Modify only if a regression is found: `fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java`

**Interfaces:**
- Consumes: frontend files copied into Spring Boot static resources by the Maven build.
- Produces: verified deployable frontend behavior with no backend contract changes.

- [ ] **Step 1: Run relevant backend integration tests**

Run:

```bash
cd fantalol-backend
mvn -Dtest=StaticResourceIntegrationTest test
```

Expected: `BUILD SUCCESS`.

- [ ] **Step 2: Run the complete backend test suite**

Run:

```bash
cd fantalol-backend
mvn test
```

Expected: `BUILD SUCCESS` with no test failures.

- [ ] **Step 3: Confirm source language and scope**

Run:

```bash
rg -n "participantCreditBalances|renderParticipantCredits|participant-credits" fantalol-frontend
rg -n "WebSocket|EventSource" fantalol-frontend/js/league-detail.js
```

Expected: the first command finds the English code identifiers and tests; the second command returns no matches.
