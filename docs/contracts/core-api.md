# Core API contract

Base path: `/api/`.

All endpoints use Django session authentication. Unsafe requests require the CSRF header described in [the auth contract](auth-api.md).

---

## Activity log

`GET /activity-logs/` is a read-only DRF viewset endpoint. It requires `activity_log.view` (superusers bypass role checks).

### List activity logs

```http
GET /api/activity-logs/
```

Example response:

```json
[
  {
    "id": "0c9c...",
    "action": "UPDATE",
    "model_name": "ReportingPeriod",
    "object_id": "2d1e...",
    "object_repr": "FY 2026 (2026-04-01 - 2027-03-31)",
    "changes": {
      "status": {
        "old": "OPEN",
        "new": "LOCKED"
      }
    },
    "user": 17,
    "ip_address": "203.0.113.11",
    "user_agent": "Mozilla/5.0",
    "request_path": "/api/periods/.../lock/",
    "created_at": "2026-08-10T10:00:00Z",
    "updated_at": "2026-08-10T10:00:00Z"
  }
]
```

There are intentionally no create, update, or delete audit-log routes.

Audit logs reflect direct model saves/deletes for models using `ActivityLogMixin` and authentication login/logout events. They are not a substitute for an explicit module event when auditing many-to-many relations or bulk queryset updates.

---

## Notifications

Notifications are part of the shared Core module.

All notification endpoints require an authenticated session and always operate on the currently authenticated user.

A user can only access their own notifications.

A notification belonging to another user is intentionally treated as **not found**. This prevents notification IDs from being used to discover whether another user's notification exists.

There is no public notification creation endpoint. Feature modules should create notifications through the Core notification service documented in the Core module documentation.

### Notification representation

Notification responses use `NotificationSerializer`.

#### Example

```json
{
  "id": "5c6f4c2d-8c4b-4b17-a1c7-2b6d8c4f1234",
  "recipient": 17,
  "notification_type": "REPORT_READY",
  "title": "Report ready",
  "message": "Your report is ready.",
  "related_model": "Report",
  "related_object_id": "42",
  "action_url": "/reports/42/",
  "priority": "NORMAL",
  "is_read": false,
  "read_at": null,
  "email_sent": false,
  "created_at": "2026-08-20T10:30:00Z",
  "updated_at": "2026-08-20T10:30:00Z"
}
```

The following notification fields are **read-only** through the API:

* `id`
* `recipient`
* `notification_type`
* `title`
* `message`
* `related_model`
* `related_object_id`
* `action_url`
* `priority`
* `is_read`
* `read_at`
* `email_sent`
* `created_at`
* `updated_at`

The API does not expose notification creation or arbitrary notification updates.

Notification state changes are performed through the dedicated **read** and **read-all** endpoints.

---

## List notifications

### `GET /api/notifications/`

Returns notifications belonging only to the current authenticated user, newest first.

### Example

```json
[
  {
    "id": "5c6f4c2d-8c4b-4b17-a1c7-2b6d8c4f1234",
    "recipient": 17,
    "notification_type": "REPORT_READY",
    "title": "Report ready",
    "message": "Your report is ready.",
    "related_model": "Report",
    "related_object_id": "42",
    "action_url": "/reports/42/",
    "priority": "NORMAL",
    "is_read": false,
    "read_at": null,
    "email_sent": false,
    "created_at": "2026-08-20T10:30:00Z",
    "updated_at": "2026-08-20T10:30:00Z"
  }
]
```

Notifications belonging to another user are never included.

---

## Notification filters

The notification list endpoint supports the following query parameters:

* `is_read`
* `priority`
* `notification_type`

### Filter by read state

```http
GET /api/notifications/?is_read=true
```

Returns only read notifications.

```http
GET /api/notifications/?is_read=false
```

Returns only unread notifications.

Accepted values are:

* `true`
* `false`

An invalid `is_read` value returns an empty result.

#### Example

```http
GET /api/notifications/?is_read=invalid
```

Response:

```json
[]
```

### Filter by priority

```http
GET /api/notifications/?priority=HIGH
```

Supported notification priorities are:

* `LOW`
* `NORMAL`
* `HIGH`

### Filter by notification type

```http
GET /api/notifications/?notification_type=REPORT_READY
```

The value is matched against the notification's `notification_type`.

### Combine filters

Filters can be combined.

```http
GET /api/notifications/?is_read=false&priority=HIGH&notification_type=REPORT_READY
```

All filters apply to the current user's notifications only.

---

## Notification detail

### `GET /api/notifications/{id}/`

Returns a single notification belonging to the authenticated user.

### Example

```http
GET /api/notifications/5c6f4c2d-8c4b-4b17-a1c7-2b6d8c4f1234/
```

### Example response

```json
{
  "id": "5c6f4c2d-8c4b-4b17-a1c7-2b6d8c4f1234",
  "recipient": 17,
  "notification_type": "REPORT_READY",
  "title": "Report ready",
  "message": "Your report is ready.",
  "related_model": "Report",
  "related_object_id": "42",
  "action_url": "/reports/42/",
  "priority": "NORMAL",
  "is_read": false,
  "read_at": null,
  "email_sent": false,
  "created_at": "2026-08-20T10:30:00Z",
  "updated_at": "2026-08-20T10:30:00Z"
}
```

---

## Notification ownership and protected 404 behavior

Notification access is scoped to the authenticated user.

For example, if notification `123` belongs to another user:

```http
GET /api/notifications/123/
```

returns:

```http
404 Not Found
```

It does not return the notification and does not expose whether the notification exists.

The same protected behavior applies when attempting to mark another user's notification as read.

### Example

```http
PATCH /api/notifications/123/read/
```

Response:

```http
404 Not Found
```

This ownership rule applies regardless of whether the requester knows the notification UUID.

An unknown notification UUID also returns:

```http
404 Not Found
```

---

## Mark one notification as read

### `PATCH /api/notifications/{id}/read/`

Marks one notification belonging to the current user as read.

The request body is empty.

### Example

```http
PATCH /api/notifications/5c6f4c2d-8c4b-4b17-a1c7-2b6d8c4f1234/read/
```

### Example response

```json
{
  "message": "Notification marked as read"
}
```

The notification is updated so that:

```text
is_read = true
read_at = current timestamp
```

### Idempotency

Calling the endpoint repeatedly is safe.

If the notification is already read, its existing `read_at` timestamp is preserved rather than replaced with a new timestamp.

Therefore:

| Request        | Result                                   |
| -------------- | ---------------------------------------- |
| First request  | Marks notification as read               |
| Second request | Leaves existing read timestamp unchanged |

---

## Read-all notifications

### `PATCH /api/notifications/read-all/`

Marks all unread notifications belonging to the current user as read.

The request body is empty.

### Example response

```json
{
  "message": "All notifications marked as read",
  "updated_count": 3
}
```

`updated_count` is the number of notifications changed by the operation.

Only notifications belonging to the current authenticated user are modified.

Notifications belonging to other users are never changed.

All notifications changed by this operation receive a `read_at` timestamp.

If the current user has no unread notifications, the endpoint remains successful and returns:

```json
{
  "message": "All notifications marked as read",
  "updated_count": 0
}
```

---

## Unread notification count

### `GET /api/notifications/unread-count/`

Returns the number of unread notifications belonging to the current user.

### Example

```json
{
  "count": 3
}
```

The count is calculated using:

```text
recipient = current authenticated user
is_read = false
```

Notifications belonging to other users are not included.

---

## Notification read-state contract

Notification read state follows these rules:

| `is_read` | `read_at` | Meaning |
| --------- | --------- | ------- |
| `false`   | `null`    | Unread  |
| `true`    | timestamp | Read    |

The following states are invalid:

```text
is_read = true
read_at = null
```

and:

```text
is_read = false
read_at = timestamp
```

The database constraint `notification_read_state_consistent` protects this invariant.

Existing legacy notification rows are normalized by the migration before the database constraint is added.

For legacy read notifications without a timestamp, the migration backfills `read_at` using the notification's existing `created_at` timestamp.

For legacy unread notifications with a stale `read_at`, the migration clears the timestamp.

---

## Authentication and CSRF

All notification endpoints require an authenticated session.

Unauthenticated requests are rejected according to the configured DRF authentication and permission behavior.

Unsafe requests such as:

```http
PATCH /api/notifications/{id}/read/
PATCH /api/notifications/read-all/
```

require the CSRF header described in the auth contract.

---

## Notification creation

There is intentionally **no public HTTP endpoint** for creating notifications.

Feature modules should use the shared Python service:

```python
from apps.core.services.notification_service import notify
```

The service accepts generic notification information and does not introduce business-specific foreign keys into the Core notification model.

### Example

```python
notify(
    recipient=user,
    notification_type="REPORT_READY",
    title="Report ready",
    message="Your report is ready.",
    related_model="Report",
    related_object_id=str(report.pk),
    action_url=f"/reports/{report.pk}/",
    priority="NORMAL",
)
```

The Core notification foundation remains independent of:

* M5
* M8
* email delivery
* realtime/WebSocket delivery
* frontend notification-center behavior

---

## Deferred notification features

The following are intentionally outside the current Core notification API contract:

* email delivery
* realtime/WebSocket notification delivery
* frontend notification-center UI
* module-specific notification rules
* business-specific foreign keys
* M5 integrations
* M8 integrations
* notification scheduling
* notification preferences
* notification templates

These features can be added by later issues without changing the ownership and privacy guarantees of the Core notification foundation.

---

## Error shape

Handled DRF errors use the common envelope:

```json
{
  "success": false,
  "message": "Notification not found.",
  "errors": {
    "detail": "Notification not found."
  }
}
```

For field validation, `message` is the first field message while `errors` contains every field error.

Consumers should:

* show `message` for a generic toast;
* consult `errors` to render field-level feedback.

Shared response helpers are available for new internal endpoints:

* `success_response`
* `created_response`
* `no_content_response`

`success_response` and `created_response` return the success envelope.

`no_content_response` returns a bodyless HTTP `204` response as required by HTTP.
