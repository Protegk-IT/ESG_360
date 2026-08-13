# Identity, authentication, and scoped access

## Design

ESG360 uses Django session authentication and a role-assignment model for
row-level authorisation. A user does not have one global role. Each
`UserRoleAssignment` binds a `User`, a `Role`, and an optional organisation
scope:

- `Role.permissions` is the reusable permission bundle.
- `UserRoleAssignment.org_node` scopes that role to an `OrgNode` and every
  descendant. `null` is company-wide scope.
- `module_code` and `framework_code` further restrict an assignment when set.
- `is_active`, `valid_from`, and `valid_to` are enforced by the resolver.
- a superuser bypasses role and scope checks; a normal user with no matching
  active assignment has no access.

This means a person can, for example, hold Data Entry at one site and Reviewer
at a different site without receiving either capability at both sites.

## Permission codes

The contract is lowercase `<module>.<action>`. The seed source of truth is
`apps/accounts/constants.py`; run `python manage.py seed_rbac` after deploying
new permission definitions. The current platform CRUD modules are:

```text
company, country, state, city, department, organization, reporting_period
```

Each has `view`, `create`, `edit`, and `delete` permissions. Identity/admin
codes are `user.*`, `role.*`, and `permission.view`; other platform codes
include `dashboard.view` and `activity_log.view`. Feature-specific codes such
as `data.enter` and `data.approve` remain available for later ESG modules.

Use `organization.*` and `reporting_period.*` in frontend routes and API
viewsets. `org.*` and `period.*` are retired aliases; `seed_rbac` removes
those old records from an existing database.

## Auth API

All APIs use the Django session cookie. The SPA must send requests with
credentials and attach `X-CSRFToken` to unsafe methods.

```http
POST /api/accounts/login/
Content-Type: application/json

{"username":"rahul","password":"…"}
```

```json
{
  "csrfToken": "…",
  "user": {
    "id": 17,
    "username": "rahul",
    "roles": ["Data Entry", "Reviewer"],
    "permissions": ["data.approve", "data.enter"],
    "scope_summary": [
      {"role":"Data Entry", "org_node":{"id":"…","name":"Site A"}, "module_code":null, "framework_code":null, "valid_from":null, "valid_to":null}
    ]
  }
}
```

- `GET /api/accounts/csrf/` returns `{"csrfToken":"…"}` and ensures the
  CSRF cookie exists.
- The public login page obtains that token before submitting credentials. This
  also handles a browser that retained a session cookie after a reload.
- `GET /api/accounts/me/` is the authoritative session-restoration endpoint
  and returns the same current-user shape (including a flat `permissions`
  array).
- `POST /api/accounts/logout/` and `POST /api/accounts/change-password/` are
  authenticated, CSRF-protected requests.

The frontend may cache a display copy, but its authenticated state is restored
from `/me`, not trusted from local storage. Its local development default is
`http://localhost:8000/api`; set `VITE_API_BASE_URL` to override it. Use the
same hostname (`localhost` or `127.0.0.1`) for both frontend and backend during
session development so browser SameSite cookie rules do not suppress the
session cookie.

## Administration APIs

`/api/accounts/users/` provides user CRUD plus scoped assignments:

```http
POST /api/accounts/users/{user_id}/assignments/
Content-Type: application/json

{"role":"<role-uuid>","org_node":"<node-uuid>","module_code":"data","valid_to":"2026-12-31"}
```

The direct user create/update form can add a legacy single role/department,
but it does not remove existing scoped assignments. Use the assignment routes
for multi-role administration.

For compatibility with that editor, user detail responses also expose `role`,
`org_node`, and `department` as UUIDs for the oldest active role assignment
and the primary department. They are convenience projections only; consumers
that need the complete access picture must use `role_assignments`.

`GET /api/accounts/roles/` requires `role.view`. Role creation, modification,
and deletion are superuser-only. `GET /api/accounts/permissions/` requires
`permission.view` and is intentionally read-only. System roles cannot be
deleted or renamed through the API, but their description, active state, and
permission matrix may be updated.

## Applying RBAC in future modules

For a normal protected viewset, inherit `RBACModelViewSet` and set
`module_code`; it maps list/retrieve/create/update/delete to the corresponding
permission code.

```python
class AnswerViewSet(RBACModelViewSet):
    module_code = "data"
    scope_field = "org_node"  # or "submission__org_node" for indirect scope
```

`scope_field` opt-in is deliberate: only models that are actually tied to an
organisation should be row-scoped. The mixin filters both collection and
detail queryset access when the viewset applies `get_scoped_queryset` in its
`get_queryset`; out-of-scope detail requests must become 404 rather than 403.
For an `OrgNode` queryset itself use `scope_field = "id"`.

For custom actions, override `get_required_permission()` and return the code
for that action. Permission resolution always considers the requested code,
module restriction, validity dates, and each qualifying role assignment's
scope independently.

## Deployment configuration

`SECRET_KEY` is required when `DEBUG` is false. The remaining documented
environment settings are `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_ENGINE`, `DATABASE_NAME`,
`CORS_ALLOWED_ORIGINS`, and `CSRF_TRUSTED_ORIGINS`; see `backend/.env.example`.
Production cookies are marked secure and use `SameSite=Lax`.

The detailed wire contracts live in `docs/contracts/auth-api.md` and
`docs/contracts/permission-codes.md`.
