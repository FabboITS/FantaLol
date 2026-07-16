# Admin User Directory Design

## Goal

Allow an authenticated administrator to press `Ctrl+Y` and open a popup listing every regular registered user's username. The feature must never expose passwords, password hashes, email addresses, IDs, or profile data.

## Scope

- The directory lists all registered accounts whose role is `USER`, whether or not they are currently online.
- Accounts whose role is `ADMIN`, including the seeded `admin` account, are excluded.
- Usernames are sorted alphabetically for predictable display.
- The feature is read-only. Searching, editing, deleting, pagination, and online-presence tracking are outside this change.

## Backend Design

Add an authenticated `GET /api/users` endpoint to the existing user controller. Access is restricted to `ROLE_ADMIN` at the Spring Security layer. This authorization is authoritative; hiding the shortcut in the frontend is only a user-interface convenience.

The repository queries only users with role `USER`, ordered by username. The service maps the result to a dedicated response DTO containing one field:

```json
{
  "username": "example"
}
```

Using a dedicated DTO prevents accidental serialization of the `User` entity and guarantees that credentials and other personal data cannot enter the response.

An unauthenticated request receives `401 Unauthorized`. An authenticated non-admin request receives `403 Forbidden`.

## Frontend Design

Add a dialog consistent with the existing FantaLoL modal styling. It contains:

- An admin-directory heading.
- A count of regular registered users.
- An alphabetically ordered list of usernames.
- The existing modal close control.
- Loading, empty, and error states.

Register a document-level `keydown` handler. It opens the directory only when:

- The key is `Y` with the Control modifier.
- The current stored session role is `ADMIN`.
- Focus is not inside an input, textarea, select, or content-editable element.

When those conditions are met, the handler prevents the browser's redo action, fetches `/api/users` with the existing JWT-aware API helper, renders the returned usernames as escaped text, and opens the dialog. For non-admin users the shortcut has no effect. The user list is fetched each time the dialog opens so newly registered accounts appear without a page refresh.

## Data Flow

1. The administrator logs in and receives a JWT containing the `ADMIN` authority.
2. The administrator presses `Ctrl+Y` outside an editable control.
3. The frontend requests `GET /api/users` with the bearer token.
4. Spring Security verifies `ROLE_ADMIN`.
5. The backend queries only `USER` accounts and returns username-only DTOs.
6. The frontend renders the count and usernames, then displays the dialog.

## Error Handling

- A failed directory request does not open a popup containing stale data.
- The frontend displays the existing toast error message for request failures.
- Existing JWT behavior remains unchanged: an expired token producing `401` logs the user out through the shared API helper.
- An empty result opens the dialog with a clear message that no regular users are registered.

## Testing

Backend tests will verify:

- An administrator can retrieve the directory.
- A regular authenticated user receives `403 Forbidden`.
- An unauthenticated caller receives `401 Unauthorized`.
- Admin accounts are excluded.
- Usernames are sorted alphabetically.
- Each response object exposes only the `username` field.

Frontend behavior will be verified for the admin role guard, editable-control guard, correct request/rendering, empty state, and error handling using the project's available frontend test approach or focused manual verification if no JavaScript test harness exists.

## Acceptance Criteria

- Pressing `Ctrl+Y` as the seeded `admin` account opens the username directory.
- The popup lists all and only regular registered usernames in alphabetical order.
- No password, password hash, email, ID, or profile information is returned by the endpoint or rendered in the UI.
- Pressing `Ctrl+Y` as a regular or logged-out visitor has no effect.
- Calling the endpoint directly as a regular user is forbidden.
- `Ctrl+Y` retains its normal behavior while typing in editable controls.
