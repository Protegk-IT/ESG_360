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

Create notifications through the supported helper:

```python
from apps.core.services.notification_service import notify

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

The helper stores the related object's class name and primary key as strings;
it does not send email. `email_sent` is available for a future delivery
workflow and must only be set by that workflow after successful delivery.

## Errors and API responses

DRF exceptions produced by platform API views use this common shape:

```json
{
  "success": false,
  "message": "Notification not found.",
  "errors": {"detail": "Notification not found."}
}
```

`message` is the first useful leaf error and `errors` preserves the complete
DRF validation structure. Existing success endpoints retain their established
response shapes; `success_response`, `created_response`, and
`no_content_response` are opt-in helpers for new endpoints. The first two use
the success envelope; the last is a true bodyless HTTP 204 response. Use
`success_response` with HTTP 200 when a client needs a deletion confirmation
message. Do not wrap a response twice.

The detailed public endpoint contract is in
[Core API contract](../contracts/core-api.md).
