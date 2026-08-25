# Core module

The `apps.core` app provides the shared persistence, audit, request-context,
notification, and API-error building blocks used by ESG360 modules. It does
not own business-specific permissions or organisation scoping; those live in
`apps.accounts` and are documented in [Identity and access](identity-access.md).

## Shared models

`BaseModel` is an abstract model with a UUID primary key and `created_at` /
`updated_at` timestamps. New domain models should inherit it unless they have
a deliberate compatibility reason not to.

`ActivityLog` is append-only audit data:

- `user` is the authenticated actor when a request is available; it becomes
  null if that user is later deleted.
- `action` supports create, update, delete, login, logout, and explicit
  workflow actions such as approve and export.
- `model_name`, `object_id`, and `object_repr` identify the affected record.
- `changes` is JSON: creates and deletes contain a safe field snapshot;
updates contain only `{field: {old, new}}` entries that were actually
  persisted.
- `ip_address`, `user_agent`, and `request_path` come from the active Django
request when available.

The audited model write and its log entry are in the same database transaction:
if the audit write fails, the model write is rolled back. Delete logs are
created before the deletion within that transaction so a user deleting their
own account can still be represented safely; Django's `SET_NULL` relationship
policy then removes that actor reference after deletion.

`Notification` is an in-app message owned by exactly one user. It has an
optional related model/object reference and action URL, plus `LOW`, `NORMAL`,
or `HIGH` priority. It is not a general cross-user work queue: recipients can
only retrieve or mark their own notifications read.

## Auditing model writes

Add `ActivityLogMixin` before `BaseModel` for a model whose direct
create/update/delete operations must be audited:

```python
class Submission(ActivityLogMixin, BaseModel):
    org_node = models.ForeignKey("organizations.OrgNode", on_delete=models.PROTECT)
    value = models.DecimalField(max_digits=12, decimal_places=2)
```

The mixin captures request metadata through `CurrentRequestMiddleware`, which
is already enabled globally. It omits fields whose names contain sensitive
credentials (`password`, `token`, `secret`, `api_key`, or `private_key`) and
file fields; it never records file contents. Custom `save()` implementations
must call `super().save()` for audit logging to run.

When calling `save(update_fields=...)`, the audit log contains only those
persisted fields. This prevents an in-memory change that was intentionally not
saved from being recorded as a database change. M2M relationship operations do
not call model `save()`; a module that needs to audit those must explicitly log
that domain event.

Login and authenticated logout are recorded by Django auth signals. The audit
API is read-only and protected by `activity_log.view`; only grant that code to
roles that should see platform-wide audit history.

## Notifications

`Notification` is the shared in-app notification model owned by `apps.core`. A
notification belongs to exactly one recipient and is intentionally independent
of the business model that caused it. Business modules should use the shared
creation service rather than creating notification rows directly.

### Model fields

The notification model contains:

* `recipient` — the user who owns the notification. This is the only user
  relationship on the notification.
* `notification_type` — a stable application-defined event/type identifier,
  such as `SUBMISSION_APPROVED`.
* `title` — the short notification heading shown to the recipient.
* `message` — the notification body.
* `priority` — `LOW`, `NORMAL`, or `HIGH`.
* `is_read` — whether the recipient has marked the notification as read.
* `read_at` — the timestamp at which the notification was marked as read,
  when available.
* `related_model` — optional model/class name identifying the business object
  associated with the notification.
* `related_object_id` — optional primary-key value of the related object,
  stored as a string.
* `action_url` — optional application URL that the recipient can follow to
  inspect or act on the related object.
* `email_sent` — a compatibility field reserved for future email delivery.
  Creating an in-app notification does not send email and the notification
  creation service must not mark this field as sent.

The related-object fields deliberately use model name and object ID values
instead of a Django `ForeignKey`. This keeps the core notification model
decoupled from business applications and allows future modules to reference
their own domain objects without introducing hard dependencies into
`apps.core`.

### Notification creation service

Create notifications through the supported `notify()` service:

```python
notify(
    recipient=user,
    notification_type="SUBMISSION_APPROVED",
    title="Submission approved",
    message="FY 2026 Q1 data was approved.",
    related_object=submission,
    action_url=f"/submissions/{submission.id}",
    priority="NORMAL",
)
```

The service contract is:

* `recipient` is required and identifies the single notification owner.
* `notification_type` is a stable event identifier supplied by the calling
  module.
* `title` and `message` contain the user-facing notification content.
* `related_object` is optional. When supplied, its model/class name and primary
  key are stored as strings.
* `action_url` is optional and is stored as supplied by the caller.
* `priority` defaults to the normal priority when no higher or lower priority
  is required.
* The service creates an in-app notification only; it does not send email,
  publish a cross-user work item, or create a business-specific relationship.

Future modules should call this service rather than importing or depending on
the notification model's persistence details.

For example, a future approvals module can notify a user without adding a
foreign key from `Notification` to `Submission`:

```python
from apps.core.notifications.services.notification_service import notify

notify(
    recipient=submission.owner,
    notification_type="SUBMISSION_APPROVED",
    title="Submission approved",
    message=f"{submission.name} was approved.",
    related_object=submission,
    action_url=f"/submissions/{submission.id}",
    priority="NORMAL",
)
```

Another module can use exactly the same service with a completely different
domain model:

```python
notify(
    recipient=assessment.owner,
    notification_type="ASSESSMENT_COMPLETED",
    title="Assessment completed",
    message="Your materiality assessment is ready for review.",
    related_object=assessment,
    action_url=f"/materiality/assessments/{assessment.id}",
    priority="HIGH",
)
```

Neither module requires a notification-specific foreign key to its own model.

### Read/unread lifecycle

Notifications are created as unread.

The recipient can:

1. retrieve their unread notifications;
2. retrieve their notification history;
3. mark an individual notification as read; and
4. use the notification's read state when rendering notification badges or
   inboxes.

Marking a notification as read is an idempotent operation. A notification
already marked as read remains read.

The read state belongs to the notification itself because each notification has
exactly one recipient. There is no shared read state between users.

The API does not provide a mechanism for one user to mark another user's
notification as read.

### Recipient privacy rules

Notifications are recipient-private.

All notification retrieval and mutation operations must be scoped to the
authenticated user. A user must not be able to:

* list another user's notifications;
* retrieve another user's notification by ID;
* mark another user's notification as read; or
* infer another user's notification contents through an API endpoint.

The recipient restriction is an application-level access rule and is not
replaced by the fact that a caller may otherwise have administrative or
business permissions over the related object.

Platform-wide audit permissions do not grant access to another user's private
notifications.

### API endpoints

The notification API exposes recipient-scoped operations for:

* listing the authenticated user's notifications;
* retrieving an individual notification belonging to that user; and
* marking one of the authenticated user's notifications as read.

The endpoint implementation must enforce recipient ownership in the queryset
and/or object lookup rather than retrieving an unrestricted notification and
checking ownership only after retrieval.

The detailed HTTP request/response contract is maintained in
[Core API contract](../contracts/core-api.md).

Typical usage is conceptually:

```text
GET   /api/notifications/
GET   /api/notifications/<notification-id>/
PATCH  /api/notifications/<notification-id>/read/
GET   /api/notifications/unread-count/
PATCH /api/notifications/read-all/
```

The exact route names and response envelopes are defined by the implemented
Core API contract and should be kept consistent with that document.

### Related objects and action URLs

Notifications may optionally point back to the business object that caused the
event.

The relationship is represented by:

```text
related_model
related_object_id
```

rather than a Django foreign key.

For example:

```text
related_model = "Submission"
related_object_id = "8d4..."
action_url = "/submissions/8d4..."
```

This provides a generic reference without making `apps.core` depend on
`Submission` or any other business-specific model.

`action_url` is also optional. A notification does not have to provide a
navigation target when the event is informational or when the target is not
appropriate for the recipient.

The notification system does not attempt to resolve the related object into a
business-specific Python model at creation time. Calling modules remain
responsible for supplying a valid reference and an appropriate action URL.

### `email_sent` compatibility status

`email_sent` remains available for compatibility with the planned notification
delivery workflow.

Its presence does **not** mean that the current notification service sends
email.

The current behavior is:

* `notify()` creates an in-app notification only.
* `notify()` must not send email.
* `notify()` must not set `email_sent=True`.
* A future email-delivery workflow may set `email_sent=True` only after
  successful email delivery.
* Existing consumers that inspect `email_sent` remain compatible with the
  field being present.

Email delivery, retry handling, provider integration, templates, delivery
events, and delivery failure tracking are outside the current notification
foundation.

### Intentionally deferred

The following capabilities are intentionally not part of the current
notification foundation:

* email notification delivery;
* push notifications;
* SMS notifications;
* notification preferences and per-user channel configuration;
* digest or scheduled notifications;
* notification templates and localization;
* delivery retry and dead-letter handling;
* delivery-provider integrations;
* cross-user notification/work-queue semantics;
* notification grouping or deduplication;
* bulk notification campaigns;
* advanced notification retention policies;
* real-time WebSocket/SSE notification delivery; and
* business-specific foreign keys from `Notification` to domain models.

These features can be added later without changing the fundamental recipient
privacy model or the generic related-object reference pattern.
