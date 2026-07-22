# Admin League Visibility, Navigation, and README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the global administrator complete league management and a working user/email directory, restrict regular users to their own leagues, reorder the landing page, and provide one complete Italian README at the repository root.

**Architecture:** Spring remains the authorization boundary: league collection and detail methods receive the authenticated username and query only accessible records unless the caller has `ADMIN`. Dedicated DTOs expose only approved directory fields. The vanilla frontend renders role-aware controls, while Maven continues packaging the frontend directory as Spring static resources.

**Tech Stack:** Java 17, Spring Boot 3.3.4, Spring Security, Spring Data JPA, H2/MockMvc/JUnit 5, vanilla HTML/CSS/JavaScript, Maven, Docker Compose.

## Global Constraints

- All new source identifiers, test names, code comments, and technical messages are in English.
- Existing Italian interface copy remains Italian.
- The root `README.md` is entirely in Italian.
- The global `ADMIN` can list, open, and delete every league.
- A `USER` can list and open only leagues they created or joined, without duplicates.
- `Ctrl+Y` lists only `USER` accounts and exposes exactly `username` and `email`.
- Backend authorization is authoritative; frontend role checks are presentation only.
- Do not publish administrator credentials.

## File Structure

- Create `fantalol-backend/src/test/java/com/fantalol/backend/league/LeagueVisibilityServiceTest.java`: focused role, membership, detail-access, and deletion tests.
- Modify `fantalol-backend/src/main/java/com/fantalol/backend/league/LeagueRepository.java`: accessible-league query ordered by ID.
- Modify `fantalol-backend/src/main/java/com/fantalol/backend/league/LeagueController.java`: pass authenticated identity to list/detail methods.
- Modify `fantalol-backend/src/main/java/com/fantalol/backend/league/LeagueService.java`: role-aware listing and detail authorization.
- Modify `fantalol-backend/src/test/java/com/fantalol/backend/user/AdminUserDirectoryIntegrationTest.java`: require email and English test names.
- Modify `fantalol-backend/src/main/java/com/fantalol/backend/user/dto/UserDirectoryEntry.java`: safe username/email boundary.
- Modify `fantalol-frontend/index.html`: navigation/section order and directory markup.
- Modify `fantalol-frontend/js/app.js`: delete controls, email rendering, and robust shortcut recognition.
- Modify `fantalol-frontend/css/style.css`: league-card action layout and destructive button.
- Modify `fantalol-frontend/css/user-directory.css`: username/email row layout.
- Modify `fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java`: packaged frontend acceptance tests.
- Create `README.md`: complete project documentation in Italian.
- Delete `fantalol-backend/README.md`: remove duplicate backend-only documentation.

---

### Task 1: Role-Aware League Access and Deletion

**Files:**
- Create: `fantalol-backend/src/test/java/com/fantalol/backend/league/LeagueVisibilityServiceTest.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/LeagueRepository.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/LeagueController.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/league/LeagueService.java`

**Interfaces:**
- Produces: `LeagueRepository.findAccessibleByUsername(String username) -> List<League>`.
- Produces: `LeagueService.findAll(String username) -> List<LeagueResponse>`.
- Produces: `LeagueService.findById(String username, Long id) -> LeagueResponse`.
- Preserves: `LeagueService.getOrThrow(Long id) -> League` for internal domain services.

- [ ] **Step 1: Write failing service tests**

Create a Mockito test with English names. Include these behaviors:

```java
@Test
void globalAdminListsEveryLeague() {
    when(userService.findByUsernameOrThrow("root-admin")).thenReturn(globalAdmin);
    when(leagueRepository.findAll(Sort.by(Sort.Direction.ASC, "id")))
            .thenReturn(List.of(firstLeague, secondLeague));

    assertThat(service.findAll("root-admin"))
            .extracting(LeagueResponse::id)
            .containsExactly(1L, 2L);
}

@Test
void regularUserListsOnlyCreatedOrJoinedLeaguesWithoutDuplicates() {
    when(userService.findByUsernameOrThrow("alice")).thenReturn(alice);
    when(leagueRepository.findAccessibleByUsername("alice"))
            .thenReturn(List.of(firstLeague, secondLeague));

    assertThat(service.findAll("alice"))
            .extracting(LeagueResponse::id)
            .containsExactly(1L, 2L);
}

@Test
void regularUserCannotOpenAnUnrelatedLeague() {
    when(userService.findByUsernameOrThrow("alice")).thenReturn(alice);
    when(leagueRepository.findAccessibleByUsername("alice")).thenReturn(List.of(firstLeague));

    assertThatThrownBy(() -> service.findById("alice", 2L))
            .isInstanceOf(AccessDeniedException.class);
}

@Test
void globalAdminCanDeleteAnyLeague() {
    when(leagueRepository.findById(2L)).thenReturn(Optional.of(secondLeague));
    when(userService.findByUsernameOrThrow("root-admin")).thenReturn(globalAdmin);

    service.delete("root-admin", 2L);

    verify(leagueRepository).delete(secondLeague);
}

@Test
void unrelatedUserCannotDeleteLeague() {
    when(leagueRepository.findById(2L)).thenReturn(Optional.of(secondLeague));
    when(userService.findByUsernameOrThrow("alice")).thenReturn(alice);

    assertThatThrownBy(() -> service.delete("alice", 2L))
            .isInstanceOf(AccessDeniedException.class);
    verify(leagueRepository, never()).delete(any());
}
```

Build league fixtures with non-null `fantaTeams`, `admin`, invitation code, and credits so `LeagueResponse.from` can map them. Add a creator-access test and a joined-user detail-access test.

- [ ] **Step 2: Run the new test and verify RED**

Run:

```bash
cd fantalol-backend
mvn -Dtest=LeagueVisibilityServiceTest test
```

Expected: compilation failure because the username-aware service methods and repository query do not exist.

- [ ] **Step 3: Add the distinct accessible-league query**

Add imports for `List`, `Sort`, and the query annotations as needed. Add:

```java
@Query("""
        select distinct l from League l
        left join l.fantaTeams ft
        where l.admin.username = :username or ft.owner.username = :username
        order by l.id asc
        """)
List<League> findAccessibleByUsername(@Param("username") String username);
```

Use `distinct` to remove the creator/member duplicate at the database boundary.

- [ ] **Step 4: Implement identity-aware service methods**

Replace the collection and detail methods with:

```java
@Transactional(readOnly = true)
public List<LeagueResponse> findAll(String username) {
    User user = userService.findByUsernameOrThrow(username);
    List<League> leagues = user.getRole() == Role.ADMIN
            ? leagueRepository.findAll(Sort.by(Sort.Direction.ASC, "id"))
            : leagueRepository.findAccessibleByUsername(username);
    return leagues.stream().map(LeagueResponse::from).toList();
}

@Transactional(readOnly = true)
public LeagueResponse findById(String username, Long id) {
    User user = userService.findByUsernameOrThrow(username);
    League league = getOrThrow(id);
    if (user.getRole() != Role.ADMIN
            && !league.getAdmin().getUsername().equals(username)
            && fantaTeamRepository.findByLeagueIdAndOwnerUsername(id, username).isEmpty()) {
        throw new AccessDeniedException("You cannot access this league");
    }
    return LeagueResponse.from(league);
}
```

Change the failed delete authorization to `AccessDeniedException("You cannot delete this league")`, keeping admin and creator access unchanged. Add `org.springframework.data.domain.Sort` and `org.springframework.security.access.AccessDeniedException` imports.

- [ ] **Step 5: Pass authentication from the controller**

Use:

```java
@GetMapping
public List<LeagueResponse> findAll(Authentication authentication) {
    return leagueService.findAll(authentication.getName());
}

@GetMapping("/{id}")
public LeagueResponse findById(Authentication authentication, @PathVariable Long id) {
    return leagueService.findById(authentication.getName(), id);
}
```

- [ ] **Step 6: Run focused and full backend tests**

Run:

```bash
cd fantalol-backend
mvn -Dtest=LeagueVisibilityServiceTest test
mvn test
```

Expected: both commands end with `BUILD SUCCESS`. Update existing mocks that call the old `findById(Long)` public method to use `getOrThrow(Long)` only where compilation proves necessary; do not broaden access.

- [ ] **Step 7: Commit the backend league boundary**

```bash
git add fantalol-backend/src/main/java/com/fantalol/backend/league/LeagueController.java \
  fantalol-backend/src/main/java/com/fantalol/backend/league/LeagueRepository.java \
  fantalol-backend/src/main/java/com/fantalol/backend/league/LeagueService.java \
  fantalol-backend/src/test/java/com/fantalol/backend/league/LeagueVisibilityServiceTest.java
git commit -m "feat: restrict league visibility by membership"
```

---

### Task 2: Safe Admin User and Email Directory

**Files:**
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/user/AdminUserDirectoryIntegrationTest.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/user/dto/UserDirectoryEntry.java`

**Interfaces:**
- Preserves: `GET /api/users`, restricted to `ROLE_ADMIN`.
- Changes response item to `UserDirectoryEntry(String username, String email)`.

- [ ] **Step 1: Change the integration test first**

Rename existing test methods to English and require the safe response shape:

```java
@Test
@WithMockUser(username = "admin-test", roles = "ADMIN")
void adminReceivesSortedRegularUsersWithUsernameAndEmailOnly() throws Exception {
    mockMvc.perform(get("/api/users"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.length()").value(2))
            .andExpect(jsonPath("$[0].username").value("alpha"))
            .andExpect(jsonPath("$[0].email").value("alpha@test.local"))
            .andExpect(jsonPath("$[1].username").value("zeta"))
            .andExpect(jsonPath("$[1].email").value("zeta@test.local"))
            .andExpect(jsonPath("$[0].id").doesNotExist())
            .andExpect(jsonPath("$[0].password").doesNotExist())
            .andExpect(jsonPath("$[0].role").doesNotExist())
            .andExpect(jsonPath("$[0].profile").doesNotExist());
}
```

Rename the remaining cases to `regularUserCannotReadDirectory`, `anonymousUserCannotReadDirectory`, and `adminAccountsAreExcludedFromDirectory` without weakening their assertions.

- [ ] **Step 2: Run and verify RED**

Run:

```bash
cd fantalol-backend
mvn -Dtest=AdminUserDirectoryIntegrationTest test
```

Expected: failure because `email` is absent.

- [ ] **Step 3: Extend only the safe DTO**

Replace it with:

```java
public record UserDirectoryEntry(String username, String email) {
    public static UserDirectoryEntry from(User user) {
        return new UserDirectoryEntry(user.getUsername(), user.getEmail());
    }
}
```

- [ ] **Step 4: Verify focused and complete backend suites**

Run:

```bash
cd fantalol-backend
mvn -Dtest=AdminUserDirectoryIntegrationTest test
mvn test
```

Expected: `BUILD SUCCESS` and the response still excludes every field not named in the DTO.

- [ ] **Step 5: Commit the directory contract**

```bash
git add fantalol-backend/src/main/java/com/fantalol/backend/user/dto/UserDirectoryEntry.java \
  fantalol-backend/src/test/java/com/fantalol/backend/user/AdminUserDirectoryIntegrationTest.java
git commit -m "feat: show user emails in admin directory"
```

---

### Task 3: Role-Aware League Cards, Robust Shortcut, and Page Order

**Files:**
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java`
- Modify: `fantalol-frontend/index.html`
- Modify: `fantalol-frontend/js/app.js`
- Modify: `fantalol-frontend/css/style.css`
- Modify: `fantalol-frontend/css/user-directory.css`

**Interfaces:**
- Consumes: `GET /api/leagues -> LeagueResponse[]` already scoped by the backend.
- Consumes: `DELETE /api/leagues/{id} -> 204`.
- Consumes: `GET /api/users -> Array<{username: string, email: string}>`.
- Produces: `canDeleteLeague(league) -> boolean` and `deleteLeague(league) -> Promise<void>`.
- Produces: `isAdminDirectoryShortcut(event) -> boolean`.

- [ ] **Step 1: Add failing packaged-resource assertions**

Add English-named tests which fetch `/index.html` and `/js/app.js`. Assert:

```java
String html = mockMvc.perform(get("/index.html"))
        .andExpect(status().isOk())
        .andReturn().getResponse().getContentAsString();
assertThat(html.indexOf("href=\"#leagues\""))
        .isLessThan(html.indexOf("href=\"#players\""));
assertThat(html.indexOf("id=\"leagues\""))
        .isLessThan(html.indexOf("id=\"players\""));
```

For JavaScript, require the strings `event.code==='KeyY'`, `user.email`,
`api(`/leagues/${league.id}`,{method:'DELETE'})`, `canDeleteLeague`, and
`confirm(`. Require the directory HTML to contain an explanatory shortcut hint.

- [ ] **Step 2: Run and verify RED**

Run:

```bash
cd fantalol-backend
mvn -Dtest=StaticResourceIntegrationTest test
```

Expected: failures for page order, email rendering, KeyY recognition, and deletion UI.

- [ ] **Step 3: Reorder navigation and sections**

Change the navigation to:

```html
<a class="active" href="#home">Home</a><a href="#leagues">Le mie leghe</a><a href="#players">Players</a>
```

Move the entire `section#leagues` block before `section#players`, without modifying their IDs or internal controls. Add a directory hint such as `<p class="directory-hint">Scorciatoia: Ctrl+Y</p>`.

- [ ] **Step 4: Render accessible cards with valid delete controls**

Replace anchor-only cards with an article containing a link and optional button. Add:

```javascript
function canDeleteLeague(league){
  return state.user?.role==='ADMIN'||league.adminUsername===state.user?.username
}

function renderLeagueCard(league){
  const deleteButton=canDeleteLeague(league)
    ?`<button class="league-delete" type="button" data-delete-league="${league.id}">Elimina</button>`:'';
  return `<article class="league-panel"><a class="league-launcher" href="/lega.html?id=${league.id}">...</a>${deleteButton}</article>`
}
```

Keep all existing displayed metadata in place of `...` and pass dynamic strings through `escapeHtml`. Make `renderLeagues` map through `renderLeagueCard`.

Add delegated handling:

```javascript
async function deleteLeague(league){
  if(!confirm(`Eliminare definitivamente la lega “${league.nome}”?`))return;
  try{
    await api(`/leagues/${league.id}`,{method:'DELETE'});
    toast('Lega eliminata');
    await loadPrivateData();
  }catch(error){toast(error.message,true)}
}

$('#leagues-list').addEventListener('click',event=>{
  const button=event.target.closest('[data-delete-league]');
  if(!button)return;
  const league=state.leagues.find(item=>item.id===Number(button.dataset.deleteLeague));
  if(league)deleteLeague(league);
});
```

- [ ] **Step 5: Make `Ctrl+Y` layout-tolerant and render email safely**

Add:

```javascript
function isAdminDirectoryShortcut(event){
  const yKey=event.code==='KeyY'||event.key.toLowerCase()==='y';
  return event.ctrlKey&&!event.altKey&&!event.metaKey&&yKey;
}
```

Use it in the document key handler while preserving the admin and editable-target guards. Render each row with separate escaped username and email elements:

```javascript
`<div class="directory-user"><strong>${escapeHtml(user.username)}</strong><span>${escapeHtml(user.email)}</span></div>`
```

- [ ] **Step 6: Style the controls and directory rows**

Give `.league-panel` a positioned card layout, `.league-launcher` a block link without inherited invalid nesting, and `.league-delete` a clearly destructive but keyboard-focusable appearance. Change `.directory-user` to a two-line grid and style its email `<span>` with muted text and safe wrapping (`overflow-wrap:anywhere`). Preserve responsive one-column behavior.

- [ ] **Step 7: Verify packaged frontend and JavaScript syntax**

Run:

```bash
cd fantalol-backend
mvn -Dtest=StaticResourceIntegrationTest test
cd ..
node --check fantalol-frontend/js/app.js
```

Expected: Maven reports `BUILD SUCCESS`; Node exits `0` without output.

- [ ] **Step 8: Commit the frontend behavior**

```bash
git add fantalol-frontend/index.html fantalol-frontend/js/app.js \
  fantalol-frontend/css/style.css fantalol-frontend/css/user-directory.css \
  fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java
git commit -m "feat: add admin league controls and reorder home"
```

---

### Task 4: One Complete Italian Root README

**Files:**
- Create: `README.md`
- Delete: `fantalol-backend/README.md`

**Interfaces:**
- Produces: the repository's single main onboarding and operating document.

- [ ] **Step 1: Add a failing documentation structure check**

Run before moving the file:

```bash
test -f README.md && test ! -f fantalol-backend/README.md
```

Expected: non-zero exit because the root README does not exist and the backend README still exists.

- [ ] **Step 2: Create the Italian root README and remove the old copy**

Write `README.md` with these concrete sections:

```markdown
# FantaLeague
## Cos'è FantaLeague
## Funzionalità e ruoli
## Come funziona una lega
## Asta, rosa e formazione
## Giornate e punteggi
## Area amministratore
## Architettura e tecnologie
## Struttura del repository
## Avvio con Docker Compose
## Avvio locale
## Configurazione
## API e Swagger
## Test e copertura
## Integrazioni e dati
## Sicurezza
```

Explain `USER`, league creator, and global `ADMIN`; explain `Ctrl+Y`; document the actual MySQL/JWT/PandaScore variables from `application.yml`; give commands from the repository root (`docker compose -f fantalol-backend/docker-compose.yml up --build`) and backend directory (`mvn spring-boot:run`, `mvn clean test`); include `/`, `/swagger-ui.html`, and the Postman collection path. Do not include literal admin username, email, password, or hash. Remove `fantalol-backend/README.md` after its still-current operational information has been incorporated.

- [ ] **Step 3: Verify documentation placement and sensitive-data exclusions**

Run:

```bash
test -f README.md
test ! -f fantalol-backend/README.md
rg -n "Cos'è FantaLeague|Funzionalità e ruoli|Ctrl\+Y|docker compose|mvn clean test|swagger-ui" README.md
! rg -n "Natsu_Admin|natsu-admin@|\$2[ayb]\$" README.md
```

Expected: all positive checks find content, all file checks pass, and the sensitive-value search returns no matches.

- [ ] **Step 4: Commit the documentation move**

```bash
git add README.md fantalol-backend/README.md
git commit -m "docs: add complete Italian project guide"
```

---

### Task 5: Final Regression Verification

**Files:**
- Verify only; modify a file only if a failing check exposes a regression caused by Tasks 1–4.

**Interfaces:**
- Verifies all acceptance criteria as a single releasable result.

- [ ] **Step 1: Run all automated backend and packaged-resource tests**

```bash
cd fantalol-backend
mvn clean test
```

Expected: `BUILD SUCCESS`, zero failures, and zero errors.

- [ ] **Step 2: Validate standalone frontend syntax and required artifacts**

```bash
cd ..
node --check fantalol-frontend/js/app.js
test -f README.md
test ! -f fantalol-backend/README.md
git diff --check
```

Expected: all commands exit `0` with no syntax or whitespace errors.

- [ ] **Step 3: Review the final diff against the specification**

Confirm from the diff that:

- no administrator credentials were added;
- no endpoint relies only on frontend filtering;
- regular-user list and detail access share the same membership rule;
- the directory response contains only username and email;
- the menu and DOM sections have matching order;
- unrelated existing behavior and user work remain untouched.

- [ ] **Step 4: Record the final verified state**

If Git is writable, commit only any verification-driven correction with:

```bash
git add <files-corrected-during-verification>
git commit -m "fix: address final admin workflow regressions"
```

If `.git` remains read-only, do not attempt workarounds; report that all source changes are present but commits could not be created.
