# Frontend platform

The ESG360 frontend is a Vite, React, TypeScript, Tailwind, and shadcn/ui SPA
in `frontend/`. It consumes the Django API directly through the shared Axios
client in `src/services/api.ts`.

## Application structure

- `src/App.tsx` owns the routes. Public login is `/`; protected pages use
  `ProtectedRoute` with a canonical backend permission code.
- `src/context/AuthContext.tsx` owns current session user, permissions, loading
  state, and logout. It restores a protected-page session from
  `GET /accounts/me/` and obtains a CSRF token from `GET /accounts/csrf/`.
- `src/components/layout/AppShell.tsx` is the standard authenticated page
  frame: responsive sidebar, header, account menu, and content area.
- `src/components/layout/sidebar-data.ts` is the current module navigation
  registry. It includes only implemented routes and filters them against the
  authenticated user's canonical permission codes.
- `src/api/` contains thin resource clients. Keep endpoint paths and request
  types there; page components should not create ad-hoc Axios instances.
- `src/common/DataTable.tsx`, `DataTableToolbar.tsx`, and `ConfirmDialog.tsx`
  are the standard list/delete primitives.

The implemented platform routes are dashboard, company profile, organization
tree, departments, users, roles, and reporting periods. Future module links
must not be added to the sidebar until their route and usable screen exist.

## Authentication and permissions

`AuthContext` is the sole client-side source for authenticated UI state. The
server session is authoritative; no user or permission data is persisted in
`localStorage`. Use it from a component:

```tsx
const { user, permissions, isLoading } = useAuth();
const canCreate = user?.is_superuser || permissions.includes("data.create");
```

Protect a route with the same lowercase code enforced by the backend:

```tsx
<Route
  path="/data-points"
  element={
    <ProtectedRoute permission="datapoint.view">
      <DataPointList />
    </ProtectedRoute>
  }
/>
```

Unauthenticated protected navigation redirects to `/`; an authenticated user
without the specified permission sees `AccessDenied`. Hide unavailable
navigation and destructive controls for usability, but keep route protection:
the backend remains the security boundary.

The shared Axios client sends credentials and attaches `X-CSRFToken` to unsafe
methods after login/session restoration. It handles session expiry centrally;
feature pages own their 404 and 5xx UI because a 404 can legitimately mean an
empty state or out-of-scope record.

## API and error conventions

Add a client module under `src/api/<module>/` and import the shared `api`:

```ts
const DataPointApi = {
  getAll: () => api.get<DataPoint[]>("/data-points/"),
  create: (payload: DataPointPayload) => api.post("/data-points/", payload),
};
```

Use `getApiErrorMessage(error, fallback)` from `src/services/errors.ts` for
form submission failures. It supports the stabilized backend's
`{success:false, message, errors}` envelope and existing DRF `detail` or
field-error forms. Do not iterate `response.data` directly: envelopes are not
field-error maps.

Company location requests must use Axios `params`, for example
`CompanyApi.getStates(countryId)`. Do not manually concatenate query-string
placeholders.

## Page conventions

List pages use `AppShell`, `DataTable`, `DataTableToolbar`, a local loading
state, an explicit empty message, and `ConfirmDialog` for destructive actions.
Forms use an API module, show a saving state, then navigate back to their list
on success. For forms with backend validation, surface `getApiErrorMessage`.

Keep standard controls responsive: `AppShell` collapses the sidebar at narrow
widths, while `DataTable` owns horizontal overflow so the page itself does not
scroll sideways. Inputs need associated labels, appropriate autocomplete, and
icon-only buttons need an accessible name.

## Adding a module

1. Add the canonical permission code to the backend seed contract first.
2. Add typed payload/entity definitions under `src/types/`.
3. Add the resource client under `src/api/`.
4. Build list/form pages with `AppShell` and the shared table/dialog patterns.
5. Add `ProtectedRoute` entries and sidebar items with the exact `.view` code.
6. Test login/session restoration, authorized and unauthorized direct routes,
   empty/loading/error states, unsafe CSRF writes, and a narrow viewport.

For local sessions, use one hostname consistently: the frontend defaults to
`http://localhost:8000/api`; therefore run the SPA at `http://localhost:5173`
unless `VITE_API_BASE_URL` and Django CORS/CSRF settings are changed together.
