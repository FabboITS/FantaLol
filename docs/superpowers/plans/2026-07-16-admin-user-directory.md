# Admin User Directory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an admin-only `Ctrl+Y` popup that lists all regular registered usernames and never exposes sensitive user fields.

**Architecture:** A dedicated Spring endpoint returns username-only DTOs selected by role and ordered in the repository, with `ROLE_ADMIN` enforced by Spring Security. The existing static frontend adds one dialog and a guarded keyboard handler that fetches fresh data through the JWT-aware API helper each time it opens.

**Tech Stack:** Java 17, Spring Boot 3.3.4, Spring Security, Spring Data JPA, MockMvc/H2, vanilla HTML/CSS/JavaScript, Docker Compose.

## Global Constraints

- List all registered accounts whose role is exactly `USER`, including offline accounts.
- Exclude every `ADMIN` account, including the seeded `admin` account.
- Return and render only `username`; never expose password, password hash, email, ID, or profile data.
- Sort usernames alphabetically.
- Restrict `GET /api/users` to `ROLE_ADMIN` on the server; frontend role checks are not security controls.
- `Ctrl+Y` must do nothing for logged-out and regular users and while focus is in an input, textarea, select, or content-editable element.
- Fetch a fresh directory each time the popup opens.
- Do not run or include Git commands, per the user's explicit instruction.

## File Structure

- Create `fantalol-backend/src/main/java/com/fantalol/backend/user/dto/UserDirectoryEntry.java`: safe username-only response boundary.
- Create `fantalol-backend/src/test/java/com/fantalol/backend/user/AdminUserDirectoryIntegrationTest.java`: authorization, filtering, ordering, and response-shape coverage.
- Modify `fantalol-backend/src/main/java/com/fantalol/backend/user/UserRepository.java`: role-filtered ordered query.
- Modify `fantalol-backend/src/main/java/com/fantalol/backend/user/UserService.java`: entity-to-safe-DTO mapping.
- Modify `fantalol-backend/src/main/java/com/fantalol/backend/user/UserController.java`: directory endpoint.
- Modify `fantalol-backend/src/main/java/com/fantalol/backend/config/SecurityConfig.java`: explicit admin-only authorization rule.
- Modify `fantalol-frontend/index.html`: directory dialog markup.
- Modify `fantalol-frontend/css/style.css`: compact username-list, loading, and empty-state styling.
- Modify `fantalol-frontend/js/app.js`: keyboard guard, fetching, safe rendering, and dialog opening.
- Modify `fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java`: packaged frontend wiring checks.

---

### Task 1: Secure Username-Only Directory API

**Files:**
- Create: `fantalol-backend/src/main/java/com/fantalol/backend/user/dto/UserDirectoryEntry.java`
- Create: `fantalol-backend/src/test/java/com/fantalol/backend/user/AdminUserDirectoryIntegrationTest.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/user/UserRepository.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/user/UserService.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/user/UserController.java`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/config/SecurityConfig.java`

**Interfaces:**
- Produces: `GET /api/users -> List<UserDirectoryEntry>` for callers with `ROLE_ADMIN`.
- Produces: `UserDirectoryEntry(String username)` JSON objects with exactly one property.
- Produces: `UserRepository.findAllByRoleOrderByUsernameAsc(Role role) -> List<User>`.
- Produces: `UserService.getRegularUserDirectory() -> List<UserDirectoryEntry>`.

- [ ] **Step 1: Write the failing integration tests**

Create `AdminUserDirectoryIntegrationTest.java` with isolated test data and four security/shape cases:

```java
package com.fantalol.backend.user;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Instant;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class AdminUserDirectoryIntegrationTest {

    @Autowired MockMvc mockMvc;
    @Autowired UserRepository userRepository;

    @BeforeEach
    void setUp() {
        userRepository.deleteAll();
        userRepository.save(user("zeta", Role.USER));
        userRepository.save(user("alpha", Role.USER));
        userRepository.save(user("admin-test", Role.ADMIN));
    }

    @Test
    @WithMockUser(username = "admin-test", roles = "ADMIN")
    void adminRiceveSoloUsernameUserOrdinati() throws Exception {
        mockMvc.perform(get("/api/users"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[0].username").value("alpha"))
                .andExpect(jsonPath("$[1].username").value("zeta"))
                .andExpect(jsonPath("$[0].id").doesNotExist())
                .andExpect(jsonPath("$[0].email").doesNotExist())
                .andExpect(jsonPath("$[0].password").doesNotExist())
                .andExpect(jsonPath("$[0].role").doesNotExist());
    }

    @Test
    @WithMockUser(username = "alpha", roles = "USER")
    void utenteRegolareNonPuoLeggereLaDirectory() throws Exception {
        mockMvc.perform(get("/api/users"))
                .andExpect(status().isForbidden());
    }

    @Test
    void visitatoreNonAutenticatoNonPuoLeggereLaDirectory() throws Exception {
        mockMvc.perform(get("/api/users"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @WithMockUser(username = "admin-test", roles = "ADMIN")
    void adminNonCompareNellaDirectory() throws Exception {
        mockMvc.perform(get("/api/users"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[*].username").value(org.hamcrest.Matchers.not(
                        org.hamcrest.Matchers.hasItem("admin-test"))));
    }

    private User user(String username, Role role) {
        return User.builder()
                .username(username)
                .email(username + "@test.local")
                .password("encoded-not-returned")
                .role(role)
                .enabled(true)
                .createdAt(Instant.now())
                .build();
    }
}
```

- [ ] **Step 2: Run the tests and verify the expected failure**

Run:

```bash
cd fantalol-backend
./mvnw -Dtest=AdminUserDirectoryIntegrationTest test
```

If the repository has no Maven wrapper, run:

```bash
mvn -Dtest=AdminUserDirectoryIntegrationTest test
```

Expected: FAIL because `GET /api/users` has no controller mapping and the admin request returns a non-`200` response.

- [ ] **Step 3: Add the safe DTO and repository query**

Create `UserDirectoryEntry.java`:

```java
package com.fantalol.backend.user.dto;

import com.fantalol.backend.user.User;

public record UserDirectoryEntry(String username) {
    public static UserDirectoryEntry from(User user) {
        return new UserDirectoryEntry(user.getUsername());
    }
}
```

Add to `UserRepository`:

```java
import java.util.List;

List<User> findAllByRoleOrderByUsernameAsc(Role role);
```

- [ ] **Step 4: Add service and controller methods**

Add to `UserService`:

```java
import java.util.List;

@Transactional(readOnly = true)
public List<UserDirectoryEntry> getRegularUserDirectory() {
    return userRepository.findAllByRoleOrderByUsernameAsc(Role.USER).stream()
            .map(UserDirectoryEntry::from)
            .toList();
}
```

Add to `UserController`:

```java
import com.fantalol.backend.user.dto.UserDirectoryEntry;
import java.util.List;

@GetMapping
public List<UserDirectoryEntry> getRegularUserDirectory() {
    return userService.getRegularUserDirectory();
}
```

- [ ] **Step 5: Enforce administrator access in Spring Security**

Insert this matcher after the public matchers and before `.anyRequest().authenticated()` in `SecurityConfig`:

```java
.requestMatchers(HttpMethod.GET, "/api/users").hasRole("ADMIN")
```

The exact matcher intentionally does not change access to `/api/users/me`.

- [ ] **Step 6: Run the directory integration test**

Run:

```bash
cd fantalol-backend
mvn -Dtest=AdminUserDirectoryIntegrationTest test
```

Expected: `Tests run: 4, Failures: 0, Errors: 0` and `BUILD SUCCESS`.

- [ ] **Step 7: Run all backend tests**

Run:

```bash
cd fantalol-backend
mvn test
```

Expected: `BUILD SUCCESS` with zero failures and zero errors.

---

### Task 2: Admin Directory Dialog and Keyboard Shortcut

**Files:**
- Modify: `fantalol-frontend/index.html`
- Modify: `fantalol-frontend/css/style.css`
- Modify: `fantalol-frontend/js/app.js`
- Modify: `fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java`

**Interfaces:**
- Consumes: `GET /api/users -> Array<{username: string}>` from Task 1.
- Produces: `openUserDirectory() -> Promise<void>`.
- Produces: `isEditableTarget(Element) -> boolean`.
- Produces: `#user-directory-dialog`, `#user-directory-count`, and `#user-directory-list` DOM elements.

- [ ] **Step 1: Extend the static-resource test before changing frontend files**

Add tests to `StaticResourceIntegrationTest.java`, following its existing `MockMvc` setup:

```java
@Test
void homeContieneLaDirectoryUtentiAdmin() throws Exception {
    mockMvc.perform(get("/"))
            .andExpect(status().isOk())
            .andExpect(content().string(containsString("id=\"user-directory-dialog\"")))
            .andExpect(content().string(containsString("id=\"user-directory-list\"")));
}

@Test
void javascriptGestisceLaScorciatoiaAdmin() throws Exception {
    mockMvc.perform(get("/js/app.js"))
            .andExpect(status().isOk())
            .andExpect(content().string(containsString("openUserDirectory")))
            .andExpect(content().string(containsString("event.ctrlKey")))
            .andExpect(content().string(containsString("state.user?.role!=='ADMIN'")))
            .andExpect(content().string(containsString("api('/users')")));
}
```

Add this import if it is absent:

```java
import static org.hamcrest.Matchers.containsString;
```

- [ ] **Step 2: Run the focused frontend packaging tests and verify failure**

Run:

```bash
cd fantalol-backend
mvn -Dtest=StaticResourceIntegrationTest test
```

Expected: FAIL because the dialog and shortcut identifiers are absent.

- [ ] **Step 3: Add the directory dialog markup**

Insert before the toast element in `fantalol-frontend/index.html`:

```html
<dialog id="user-directory-dialog" class="modal">
    <button class="modal-close" data-close aria-label="Chiudi">×</button>
    <p class="eyebrow">Area amministratore</p>
    <h2>UTENTI REGISTRATI</h2>
    <p id="user-directory-count" class="directory-count"></p>
    <div id="user-directory-list" class="user-directory" aria-live="polite"></div>
</dialog>
```

- [ ] **Step 4: Add focused dialog styles**

Append to `fantalol-frontend/css/style.css` before its media queries:

```css
.directory-count{color:var(--muted);font-size:12px;margin:-10px 0 18px}
.user-directory{display:grid;gap:8px;max-height:50vh;overflow:auto;padding-right:5px}
.directory-user{background:#0a0d11;border:1px solid #303640;padding:12px 14px;font:600 14px var(--font-display);color:var(--white)}
.directory-empty,.directory-loading{color:var(--muted);text-align:center;padding:24px 10px}
```

- [ ] **Step 5: Implement safe rendering and the editable-target guard**

Add near the other UI helper functions in `app.js`:

```javascript
function isEditableTarget(target){return target instanceof Element&&(target.matches('input,textarea,select')||target.isContentEditable)}

async function openUserDirectory(){
    if(state.user?.role!=='ADMIN'||!state.token)return;
    const dialog=$('#user-directory-dialog');
    const count=$('#user-directory-count');
    const list=$('#user-directory-list');
    count.textContent='';
    list.innerHTML='<p class="directory-loading">Caricamento utenti…</p>';
    try{
        const users=await api('/users');
        count.textContent=`${users.length} ${users.length===1?'utente registrato':'utenti registrati'}`;
        list.innerHTML=users.length
            ?users.map(user=>`<div class="directory-user">${escapeHtml(user.username)}</div>`).join('')
            :'<p class="directory-empty">Nessun utente regolare registrato.</p>';
        dialog.showModal();
    }catch(error){
        toast(error.message,true);
    }
}
```

Escaping each username through the existing `escapeHtml` helper is mandatory even though usernames are validated server-side.

- [ ] **Step 6: Register the guarded keyboard shortcut**

Add alongside the other event listeners near the bottom of `app.js`:

```javascript
document.addEventListener('keydown',event=>{
    if(!event.ctrlKey||event.altKey||event.metaKey||event.key.toLowerCase()!=='y')return;
    if(state.user?.role!=='ADMIN'||isEditableTarget(event.target))return;
    event.preventDefault();
    openUserDirectory();
});
```

This intentionally allows either Shift state, since both `y` and `Y` normalize to `y`, and ignores Alt/Meta combinations.

- [ ] **Step 7: Run the focused static-resource tests**

Run:

```bash
cd fantalol-backend
mvn -Dtest=StaticResourceIntegrationTest test
```

Expected: all `StaticResourceIntegrationTest` cases pass and Maven reports `BUILD SUCCESS`.

- [ ] **Step 8: Run the full test suite**

Run:

```bash
cd fantalol-backend
mvn test
```

Expected: zero failures/errors and `BUILD SUCCESS`.

---

### Task 3: Rebuild and End-to-End Verification

**Files:**
- No source changes expected.

**Interfaces:**
- Consumes: Docker Compose application on `http://localhost:8080`.
- Verifies: real JWT authorization and username-only JSON over HTTP.

- [ ] **Step 1: Rebuild the application container from the current checkout**

Run from `fantalol-backend`:

```bash
docker compose up -d --build --force-recreate
```

Expected: `fantalol-mysql` becomes healthy and `fantalol-backend` starts with port `8080` published.

- [ ] **Step 2: Verify application startup**

Run:

```bash
docker compose ps
docker compose logs --tail=60 app
```

Expected: both services are `Up`, MySQL is `healthy`, and the backend log contains `Started FantaLolBackendApplication` without a startup exception.

- [ ] **Step 3: Verify unauthenticated protection**

Run:

```bash
curl --silent --output /dev/null --write-out '%{http_code}\n' http://localhost:8080/api/users
```

Expected: `401`.

- [ ] **Step 4: Log in as the seeded administrator and inspect the payload**

Run:

```bash
curl --silent --show-error -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"Admin123!"}' \
  http://localhost:8080/api/auth/login
```

Copy the returned token into a temporary shell variable manually, then run:

```bash
curl --silent --show-error -H 'Authorization: Bearer PASTE_TOKEN_HERE' \
  http://localhost:8080/api/users
```

Expected: HTTP `200`; a JSON array sorted by username; each object has only `username`; no entry has username `admin`.

- [ ] **Step 5: Verify the UI behavior in the browser**

Open `http://localhost:8080`, log in as `admin` / `Admin123!`, and press `Ctrl+Y` outside a form field.

Expected: the popup opens with the regular-user count and alphabetical usernames. Close it, focus a form input, and press `Ctrl+Y`; the popup must not open. Log in as a regular account and press `Ctrl+Y`; nothing must happen.
