# Core API contract

Base path: `/api/`. All endpoints use Django session authentication. Unsafe
requests require the CSRF header described in [the auth contract](auth-api.md).

## Activity log

`GET /activity-logs/` is a read-only DRF viewset endpoint. It requires
`activity_log.view` (superusers bypass role checks).

```json
[
  {
    "id": "0c9c…",
    "action": "UPDATE",
    "model_name": "ReportingPeriod",
    "object_id": "2d1e…",
    "object_repr": "FY 2026 (2026-04-01 - 2027-03-31)",
    "changes": {"status": {"old": "OPEN", "new": "LOCKED"}},
    "user": 17,
    "ip_address": "203.0.113.11",
    "user_agent": "Mozilla/5.0",
    "request_path": "/api/periods/…/lock/",
    "created_at": "2026-08-10T10:00:00Z",
    "updated_at": "2026-08-10T10:00:00Z"
  }
]
```

There are intentionally no create, update, or delete audit-log routes. Audit
logs reflect direct model saves/deletes for models using `ActivityLogMixin` and
auth login/logout events; they are not a substitute for an explicit module
event when auditing a many-to-many relation or bulk queryset update.

## Notifications

All notification endpoints are authenticated and always operate on the
current session user. A notification belonging to another user is treated as
not found rather than exposing its existence.

| Method and path | Result |
| --- | --- |
| `GET /notifications/` | Current user's notifications, newest first. |
| `GET /notifications/unread-count/` | `{"count": 3}` for the current user. |
| `PATCH /notifications/{id}/read/` | Marks one owned notification read. Repeating it is idempotent and preserves the first `read_at`. |
| `PATCH /notifications/read-all/` | Marks all current-user unread notifications read and returns `updated_count`. |

Example mark-all response:

```json
{"message": "All notifications marked as read", "updated_count": 3}
```

`NotificationSerializer` exposes `recipient` as read-only. There is no public
notification-creation endpoint; feature modules should use the Python helper
documented in [the core module](../modules/core.md).

## Error shape

Handled DRF errors use the common envelope:

```json
{
  "success": false,
  "message": "Notification not found.",
  "errors": {"detail": "Notification not found."}
}
```

For field validation, `message` is the first field message while `errors`
contains every field error. Consumers should show `message` for a generic
toast and consult `errors` to render field-level feedback.

Shared response helpers are available for new internal endpoints:
`success_response` and `created_response` return the success envelope;
`no_content_response` returns a bodyless HTTP 204, as required by HTTP.
