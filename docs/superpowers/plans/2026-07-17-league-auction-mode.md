# League Auction Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a creator-controlled, reopenable league auction phase with custom bidding, dynamic roster sizes, league-wide random completion, and automatic roster refresh after awards.

**Architecture:** Persist the auction phase on `League`, manage it through creator-authorized league endpoints, and keep individual 10-second `AuctionSession` records unchanged. Centralize league-size-dependent roster rules in one policy class used by auction and completion services, then make the frontend render controls from league state and refresh private data when polling observes an auction finish.

**Tech Stack:** Java 17, Spring Boot, Spring Data JPA, Jakarta Validation, JUnit 5, Mockito, H2/MySQL-compatible schema, vanilla JavaScript, HTML, CSS.

## Global Constraints

- Do not run Git commands or create commits.
- The league creator or global administrator is the only actor allowed to open/close the auction phase and complete all rosters randomly.
- Closing is blocked while an individual player auction is active; reopening is allowed.
- The individual auction timer remains 10 seconds and resets to 10 seconds after an accepted bid.
- A league accepts at most 10 fantasy teams.
- Exactly 10 teams means 5 roster players and 1 per role; 1–9 teams means 10 roster players and 2 per role.
- The exact insufficient-credit copy is `Non hai abbastanza crediti per rilanciare`.

---

### Task 1: Persist and expose the league auction phase

**Files:**
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/League.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/dto/LeagueResponse.java`
- Modify: `fantalol-backend/sql/schema.sql`
- Create: `fantalol-backend/src/test/java/com/fantalol/backend/league/LeagueAuctionPhaseServiceTest.java`

**Interfaces:**
- Produces: `League.isAuctionOpen(): boolean`, `League.setAuctionOpen(boolean)`, and `LeagueResponse.auctionOpen(): boolean`.
- Consumes: existing `League.admin`, `LeagueRepository`, and `LeagueResponse.from(League)`.

- [ ] **Step 1: Write a failing persistence/DTO test**

Create a unit test that builds a league with `auctionOpen(false)`, converts it with `LeagueResponse.from`, and asserts `response.auctionOpen()` is false. Add a second assertion for `auctionOpen(true)`.

```java
@Test
void responseExposesAuctionPhaseState() {
    User creator = User.builder().username("creator").build();
    League closed = League.builder().id(1L).nome("LEC").codiceInvito("ABC")
            .creditiIniziali(1000).admin(creator).auctionOpen(false).build();
    League open = League.builder().id(2L).nome("Open").codiceInvito("DEF")
            .creditiIniziali(1000).admin(creator).auctionOpen(true).build();

    assertFalse(LeagueResponse.from(closed).auctionOpen());
    assertTrue(LeagueResponse.from(open).auctionOpen());
}
```

- [ ] **Step 2: Run the focused test and confirm failure**

Run: `cd fantalol-backend && mvn -Dtest=LeagueAuctionPhaseServiceTest test`

Expected: compilation fails because `auctionOpen` does not exist on `League` or `LeagueResponse`.

- [ ] **Step 3: Add the persisted field and response property**

Add to `League`:

```java
@Column(nullable = false)
@Builder.Default
private boolean auctionOpen = false;
```

Add `boolean auctionOpen` to `LeagueResponse` and pass `league.isAuctionOpen()` from `from`. Add this column to `leagues` in `schema.sql`:

```sql
auction_open BOOLEAN NOT NULL DEFAULT FALSE,
```

- [ ] **Step 4: Run the focused test and confirm success**

Run: `cd fantalol-backend && mvn -Dtest=LeagueAuctionPhaseServiceTest test`

Expected: `BUILD SUCCESS`.

### Task 2: Add creator-controlled open and close operations

**Files:**
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/LeagueService.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/LeagueController.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/LeagueRepository.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/AuctionSessionRepository.java`
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/league/LeagueAuctionPhaseServiceTest.java`

**Interfaces:**
- Produces: `LeagueService.openAuction(String, Long)`, `LeagueService.closeAuction(String, Long)`, `PUT /api/leagues/{id}/auction/open`, and `PUT /api/leagues/{id}/auction/close`.
- Consumes: `AuctionSessionRepository.findFirstByLeagueIdAndStatus`, `LeagueRepository.findByIdForUpdate`, and creator/global-admin authorization.

- [ ] **Step 1: Add failing lifecycle and authorization tests**

Mock the repositories and test these cases explicitly:

```java
@Test void creatorCanOpenClosedAuction() { /* assert response.auctionOpen() */ }
@Test void creatorCanCloseAndReopenAuction() { /* close, then open */ }
@Test void participantCannotOpenAuction() { /* expect BusinessRuleException */ }
@Test void closeIsRejectedWhilePlayerAuctionIsActive() { /* expect message mentioning active auction */ }
```

Use `User.builder().username("creator")`, `Role.USER`, a league whose `admin` is that creator, and an `AuctionSession` with `AuctionStatus.ACTIVE` for the blocking test.

- [ ] **Step 2: Run the lifecycle tests and confirm failure**

Run: `cd fantalol-backend && mvn -Dtest=LeagueAuctionPhaseServiceTest test`

Expected: compilation fails because the lifecycle methods and locking repository method do not exist.

- [ ] **Step 3: Implement locking, authorization, and endpoints**

Add `LeagueRepository.findByIdForUpdate(Long)` with `@Lock(PESSIMISTIC_WRITE)`. Inject `AuctionSessionRepository` into `LeagueService`. Implement:

```java
@Transactional
public LeagueResponse openAuction(String username, Long leagueId) {
    League league = getForUpdateOrThrow(leagueId);
    assertLeagueCreatorOrGlobalAdmin(username, league);
    league.setAuctionOpen(true);
    return LeagueResponse.from(leagueRepository.save(league));
}

@Transactional
public LeagueResponse closeAuction(String username, Long leagueId) {
    League league = getForUpdateOrThrow(leagueId);
    assertLeagueCreatorOrGlobalAdmin(username, league);
    if (auctionSessionRepository.findFirstByLeagueIdAndStatus(leagueId, AuctionStatus.ACTIVE).isPresent()) {
        throw new BusinessRuleException("Attendi la fine dell'asta del player prima di terminare l'asta della lega");
    }
    league.setAuctionOpen(false);
    return LeagueResponse.from(leagueRepository.save(league));
}
```

Add controller `@PutMapping` methods for `/auction/open` and `/auction/close`, returning `LeagueResponse`.

- [ ] **Step 4: Run lifecycle tests**

Run: `cd fantalol-backend && mvn -Dtest=LeagueAuctionPhaseServiceTest test`

Expected: all lifecycle tests pass.

### Task 3: Centralize dynamic roster rules and enforce the 10-team cap

**Files:**
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/league/RosterPolicy.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/FantaTeamService.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/AuctionService.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/FantaTeamRepository.java`
- Create: `fantalol-backend/src/test/java/com/fantalol/backend/league/RosterPolicyTest.java`
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/league/FantaTeamServiceTest.java`

**Interfaces:**
- Produces: `RosterPolicy.forLeague(League): Limits`, where `Limits` contains `maxRosterSize()` and `maxPerRole()`; `FantaTeamRepository.countByLeagueId(Long)`.
- Consumes: `League.id`, roster entries, and league team count.

- [ ] **Step 1: Write failing policy and join-limit tests**

```java
@Test void tenTeamsUseOnePlayerPerRole() {
    when(teamRepository.countByLeagueId(1L)).thenReturn(10L);
    assertEquals(new RosterPolicy.Limits(5, 1), policy.forLeague(league));
}

@Test void nineTeamsUseTwoPlayersPerRole() {
    when(teamRepository.countByLeagueId(1L)).thenReturn(9L);
    assertEquals(new RosterPolicy.Limits(10, 2), policy.forLeague(league));
}

@Test void eleventhTeamCannotJoin() {
    when(fantaTeamRepository.countByLeagueId(1L)).thenReturn(10L);
    BusinessRuleException error = assertThrows(BusinessRuleException.class,
            () -> service.joinLeague("new-user", request));
    assertEquals("La lega ha già raggiunto il limite di 10 squadre", error.getMessage());
}
```

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `cd fantalol-backend && mvn -Dtest=RosterPolicyTest,FantaTeamServiceTest test`

Expected: compilation or assertion failures for missing dynamic policy/count validation.

- [ ] **Step 3: Implement the shared policy and replace constants**

Create:

```java
@Component
@RequiredArgsConstructor
public class RosterPolicy {
    private final FantaTeamRepository fantaTeamRepository;

    public Limits forLeague(League league) {
        long teams = fantaTeamRepository.countByLeagueId(league.getId());
        return teams == 10 ? new Limits(5, 1) : new Limits(10, 2);
    }

    public record Limits(int maxRosterSize, int maxPerRole) {}
}
```

Add `long countByLeagueId(Long leagueId)` to the repository. In `joinLeague`, reject when the count is already 10. Inject `RosterPolicy` into `AuctionService` and `FantaTeamService`; replace fixed `MAX_ROSTER`/`MAX_PER_ROLE` checks in every acquisition path with the policy limits.

- [ ] **Step 4: Run policy and team-service tests**

Run: `cd fantalol-backend && mvn -Dtest=RosterPolicyTest,FantaTeamServiceTest test`

Expected: all focused tests pass.

### Task 4: Gate nominations/bids and add league-wide random completion

**Files:**
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/AuctionService.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/LeagueService.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/LeagueController.java`
- Create: `fantalol-backend/src/test/java/com/fantalol/backend/league/AuctionServiceTest.java`
- Create: `fantalol-backend/src/test/java/com/fantalol/backend/league/LeagueRosterCompletionTest.java`

**Interfaces:**
- Produces: `LeagueService.completeAllRostersRandomly(String, Long): List<FantaTeamResponse>` and `POST /api/leagues/{id}/rosters/complete-randomly`.
- Consumes: `RosterPolicy`, `RosterEntryRepository`, `LecPlayerRepository`, league creator authorization, and `League.auctionOpen`.

- [ ] **Step 1: Write failing auction-phase gate tests**

Cover nomination and bid while closed, valid custom jump while open, a full-credit bid, and unaffordable next bid:

```java
assertEquals("L'asta della lega non è aperta", closedError.getMessage());
assertEquals(200, service.bid("owner", auctionId, new AuctionBidRequest(teamId, 200)).currentBid());
assertEquals(1000, service.bid("owner", auctionId, new AuctionBidRequest(teamId, 1000)).currentBid());
```

Also verify a bid above remaining credits throws `Crediti insufficienti` and that 10-team role validation uses one slot per role.

- [ ] **Step 2: Run auction tests and confirm failure**

Run: `cd fantalol-backend && mvn -Dtest=AuctionServiceTest test`

Expected: closed phases are currently accepted and dynamic-limit cases fail.

- [ ] **Step 3: Add the phase gate to nomination and bidding**

Immediately after loading the locked league/session, enforce:

```java
if (!league.isAuctionOpen()) {
    throw new BusinessRuleException("L'asta della lega non è aperta");
}
```

Keep the existing minimum calculation (`currentBid + 1`), custom request amount, credit ceiling, and 10-second reset.

- [ ] **Step 4: Write failing random-completion tests**

Test creator-only access, rejection while open, skipping a complete roster, filling every missing role for all incomplete teams, zero-cost roster entries, no duplicate player within the league, 5-player behavior at 10 teams, 10-player behavior below 10 teams, and rollback/error when eligible players are insufficient.

- [ ] **Step 5: Implement transactional league-wide completion**

Move random assignment orchestration to `LeagueService.completeAllRostersRandomly`. Load the locked league, authorize creator/global admin, require `auctionOpen == false`, calculate limits once, build a shuffled candidate pool of league-unassigned players grouped by role, pre-validate that every team's missing role counts can be satisfied, and only then save all zero-credit `RosterEntry` records. Return refreshed `FantaTeamResponse` values.

Expose:

```java
@PostMapping("/{id}/rosters/complete-randomly")
public List<FantaTeamResponse> completeAllRostersRandomly(Authentication auth, @PathVariable Long id) {
    return leagueService.completeAllRostersRandomly(auth.getName(), id);
}
```

Remove or stop exposing the team-scoped `/{id}/rosa/completa-casualmente` route so ordinary team owners cannot invoke it.

- [ ] **Step 6: Run backend league/auction tests**

Run: `cd fantalol-backend && mvn -Dtest=AuctionServiceTest,LeagueRosterCompletionTest,LeagueAuctionPhaseServiceTest,RosterPolicyTest,FantaTeamServiceTest test`

Expected: all focused tests pass.

### Task 5: Render phase controls, dynamic capacities, and custom bid states

**Files:**
- Modify: `fantalol-frontend/index.html`
- Modify: `fantalol-frontend/js/app.js`
- Modify: `fantalol-frontend/css/auction.css`
- Modify: `fantalol-frontend/css/live-auction.css`
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java`

**Interfaces:**
- Consumes: `LeagueResponse.auctionOpen`, `LeagueResponse.adminUsername`, phase endpoints, league-wide completion endpoint, `FantaTeamResponse.creditiResidui`, and `AuctionResponse.currentBid`.
- Produces: creator phase controls, dynamic roster labels, editable custom bid input, and disabled unaffordable-bid presentation.

- [ ] **Step 1: Add failing static-resource assertions**

Extend `StaticResourceIntegrationTest` to request `/index.html`, `/js/app.js`, and auction CSS and assert the delivered resources contain `auction-phase-button`, `/auction/open`, `/auction/close`, `/rosters/complete-randomly`, and `Non hai abbastanza crediti per rilanciare`.

- [ ] **Step 2: Run the resource test and confirm failure**

Run: `cd fantalol-backend && mvn -Dtest=StaticResourceIntegrationTest test`

Expected: assertions fail because the new controls and handlers do not exist.

- [ ] **Step 3: Add semantic auction controls to the dialog**

Replace the always-visible random button with a phase status region and creator control container:

```html
<div id="auction-phase-controls" class="auction-phase-controls"></div>
<button class="button button-ghost free-player hidden" id="auto-complete-button">
  Completa casualmente i ruoli mancanti
</button>
```

- [ ] **Step 4: Track leagues and render dynamic team capacity**

Add `leagues: []` to state, save fetched leagues in `loadPrivateData`, and derive:

```javascript
const activeLeague=()=>state.leagues.find(league=>league.id===state.activeTeam?.leagueId);
const rosterLimit=league=>league?.numeroSquadre===10?5:10;
const canManageLeague=league=>state.user?.role==='ADMIN'||league?.adminUsername===state.user?.username;
```

Use `rosterLimit` in `renderMine` and `renderAuction` instead of hard-coded `/10` and nomination disable checks.

- [ ] **Step 5: Render creator/participant phase states and wire actions**

When closed, hide nomination/bid controls. For the creator, show `Avvia asta` and random completion. When open, show nomination/bid controls and creator-only `Termina asta`. Wire buttons to `PUT /leagues/{id}/auction/open`, `PUT /leagues/{id}/auction/close`, and `POST /leagues/{id}/rosters/complete-randomly`, then refresh private and auction data.

- [ ] **Step 6: Render the custom bid and insufficient-credit state**

Compute `nextMinimum = auction.currentBid + 1` and `canAfford = team.creditiResidui >= nextMinimum`. Keep the number input editable without a step-size restriction. When `canAfford` is false, disable the button, add a muted/gray class, and render exactly:

```html
<p class="bid-unavailable">Non hai abbastanza crediti per rilanciare</p>
```

Ensure submission sends the entered integer unchanged as `credits`.

- [ ] **Step 7: Style creator controls and disabled bidding**

Add focused CSS for `.auction-phase-controls`, `.auction-phase-closed`, `.bid-unavailable`, and disabled bid buttons. Preserve responsive stacking already used by `.live-auction`.

- [ ] **Step 8: Process edited frontend resources for Spring**

Run: `cd fantalol-backend && mvn resources:resources`

The Maven resource configuration copies `../fantalol-frontend` into `target/classes/static`. Verify the four changed files were delivered:

```bash
cmp fantalol-frontend/index.html fantalol-backend/target/classes/static/index.html
cmp fantalol-frontend/js/app.js fantalol-backend/target/classes/static/js/app.js
cmp fantalol-frontend/css/auction.css fantalol-backend/target/classes/static/css/auction.css
cmp fantalol-frontend/css/live-auction.css fantalol-backend/target/classes/static/css/live-auction.css
```

Expected: every `cmp` exits with status 0 and prints no differences.

- [ ] **Step 9: Run the static-resource test**

Run: `cd fantalol-backend && mvn -Dtest=StaticResourceIntegrationTest test`

Expected: `BUILD SUCCESS` and all resource assertions pass.

### Task 6: Refresh roster and credits immediately after an award

**Files:**
- Modify: `fantalol-frontend/js/app.js`
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java`

**Interfaces:**
- Consumes: existing 500 ms `refreshAuction` polling, `loadPrivateData()`, and the transition from a non-null active auction to `null`.
- Produces: automatic team, roster, credit, occupied-player, and available-player refresh after finalization.

- [ ] **Step 1: Add a failing delivered-script assertion for award transition handling**

Assert the delivered script contains a named `refreshAfterAuctionEnded` helper and calls `loadPrivateData()` before re-rendering the auction following a non-null-to-null transition.

- [ ] **Step 2: Run the resource test and confirm failure**

Run: `cd fantalol-backend && mvn -Dtest=StaticResourceIntegrationTest test`

Expected: failure because the transition helper is absent.

- [ ] **Step 3: Implement guarded transition refresh**

Capture the previous auction before polling. If it existed and the new active-auction response is null, await `loadPrivateData()`, replace `state.activeTeam` from the newly loaded `state.mine`, refetch league teams, rebuild `state.occupied`, and render. Guard the helper so overlapping 500 ms polls cannot trigger concurrent duplicate refreshes.

```javascript
async function refreshAfterAuctionEnded(teamId){
  if(state.auctionRefreshPending)return;
  state.auctionRefreshPending=true;
  try{
    await loadPrivateData();
    state.activeTeam=state.mine.find(team=>team.id===teamId)||null;
  }finally{
    state.auctionRefreshPending=false;
  }
}
```

- [ ] **Step 4: Process frontend assets and run focused verification**

Run: `cd fantalol-backend && mvn resources:resources` so the Maven resource mapping delivers `fantalol-frontend` to `target/classes/static`.

Run: `cd fantalol-backend && mvn -Dtest=StaticResourceIntegrationTest,AuctionServiceTest test`

Expected: both test classes pass.

### Task 7: Full regression and manual behavior verification

**Files:**
- Verify only; fix regressions in the files owned by Tasks 1–6.

**Interfaces:**
- Consumes: all backend endpoints and frontend behaviors above.
- Produces: evidence that the complete feature and existing application tests pass.

- [ ] **Step 1: Run the full backend test suite**

Run: `cd fantalol-backend && mvn test`

Expected: `BUILD SUCCESS`, zero test failures, zero test errors.

- [ ] **Step 2: Build the application**

Run: `cd fantalol-backend && mvn package -DskipTests`

Expected: `BUILD SUCCESS` and a packaged JAR under `fantalol-backend/target/`.

- [ ] **Step 3: Verify the core browser flow manually**

Start the application using the repository's documented Docker or Spring Boot command. With one creator and at least two participant accounts, verify:

1. Participants cannot open/close the league auction phase.
2. Creator opens the phase; both participant teams can nominate and bid.
3. Enter a custom jump (for example 100 to 200) and confirm it is accepted.
4. Bid all remaining credits and confirm the next relaunch is gray/disabled with `Non hai abbastanza crediti per rilanciare`.
5. Creator cannot close during the 10-second timer.
6. When the timer ends, the winning roster and credits update without closing/reopening the dialog.
7. Creator closes, completes every incomplete roster randomly, and full rosters are skipped.
8. Creator reopens the auction phase.
9. An eleventh team is rejected.
10. A 10-team league applies one player per role; a smaller league applies two per role.

- [ ] **Step 4: Re-run affected tests after any manual-flow correction**

Run: `cd fantalol-backend && mvn test`

Expected: `BUILD SUCCESS` with no failures or errors.
