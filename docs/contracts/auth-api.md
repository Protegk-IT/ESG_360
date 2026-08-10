# Authentication API contract

Base path: `/api/accounts/`. Authentication is Django server-side session
authentication; clients must enable credentialed requests. There are no bearer
tokens in this contract.

## CSRF

Call `GET /csrf/` before the first unsafe request after a page reload:

```json
{"csrfToken":"masked-csrf-token"}
```

The response ensures the CSRF cookie is present. Send that value as
`X-CSRFToken` on `POST`, `PUT`, `PATCH`, and `DELETE`. Django enforces it for
session-authenticated requests. The frontend API client does this
automatically after login or `/me` restoration.

For local development, use `http://localhost:5173` with
`http://localhost:8000/api` (the frontend default), or use `127.0.0.1` for
both. Mixed hostnames make the cookie cross-site and will break session use.

## Endpoints

### `POST /login/`

```json
{"username":"rahul","password":"correct horse battery staple"}
```

Successful response (`200`):

```json
{
  "csrfToken":"masked-csrf-token",
  "user": {
    "id":17,
    "username":"rahul",
    "roles":["Data Entry"],
    "permissions":["data.enter"],
    "scope_summary":[
      {
        "role":"Data Entry",
        "org_node":{"id":"uuid","name":"Chakan"},
        "module_code":"data",
        "framework_code":null,
        "valid_from":null,
        "valid_to":null
      }
    ]
  }
}
```

`permissions` is always a flat, de-duplicated code array. Invalid credentials
return `401`.

### `GET /me/`

Returns the current session's user object using the exact `user` shape above.
This is the authoritative frontend bootstrap endpoint; do not restore access
from local storage alone. Unauthenticated session-authenticated requests are
rejected.

### `POST /logout/`

Requires a valid session and CSRF header. Invalidates the Django session and
returns `{"detail":"Logged out successfully."}`.

### `POST /change-password/`

Requires a valid session and CSRF header:

```json
{"old_password":"old","new_password":"new-password"}
```

The standard Django password validators apply.

## Environment contract

Backend settings read `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`,
`DATABASE_ENGINE`, `DATABASE_NAME`, `CORS_ALLOWED_ORIGINS`, and
`CSRF_TRUSTED_ORIGINS`. `SECRET_KEY` is mandatory when `DEBUG` is false.
`backend/.env.example` is the complete backend variable template. The frontend
accepts optional `VITE_API_BASE_URL` and defaults to the documented local API.
