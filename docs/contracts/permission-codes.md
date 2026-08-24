# Permission-code contract

The authoritative catalog is `apps/accounts/constants.py`. Permission codes
are lowercase `<module>.<action>` strings. `python manage.py seed_rbac` is
idempotent: it creates/updates the catalog, assigns the defined role bundles,
and removes retired `org.*`, `period.*`, and obsolete permission-master write
codes.

## Active platform endpoints

| Module | Codes |
| --- | --- |
| `company`, `country`, `state`, `city`, `department` | `.view`, `.create`, `.edit`, `.delete` |
| `organization` | `.view`, `.create`, `.edit`, `.delete`, `.manage` |
| `reporting_period` | `.view`, `.create`, `.edit`, `.delete`, `.manage`, `.reopen` |
| `user` | `.view`, `.create`, `.edit`, `.delete`, `.manage` |
| `role` | `.view`, `.create`, `.edit`, `.delete` |
| `permission` | `.view` |
| `dashboard`, `activity_log` | `.view` |
| `datapoint` | `.manage` (catalog administration; authenticated users may browse catalog reads) |
| `data` | `.enter`, `.submit`, `.approve`, `.manage` |

`/api/accounts/permissions/` is read-only; `permission.create`,
`permission.edit`, and `permission.delete` are not valid active codes.
Role write operations additionally require `is_superuser`, even if a user has
`role.create`, `role.edit`, or `role.delete`.

Feature capability codes (`data.*`, `evidence.*`, `report.*`, `disclosure.*`,
and related catalog codes) are reserved in the seed catalog for subsequent
modules. A future endpoint may only use a code already in this catalog or add
the code, role mapping, test, and documentation in the same change.

`data.manage` creates and reassigns M5 Data Requests. It does not grant draft
entry, submission, or approval; those remain `data.enter`, `data.submit`, and
`data.approve` respectively.

## Scoped resolution

An active `UserRoleAssignment` grants a permission only when all conditions
match:

1. Its role is active and has the requested code.
2. The assignment is active and within `valid_from`/`valid_to`.
3. Its `module_code` is null or matches the code's module.
4. Its optional framework restriction matches the request context.
5. Its org node is company-wide (`null`) or covers the target node/descendant.

Assignments are evaluated per permission, not globally per user. A user with
`data.enter` at Site A and `data.approve` at Site B therefore cannot approve
at Site A or enter data at Site B.

## Protecting a new scoped viewset

```python
class AnswerViewSet(RBACModelViewSet):
    module_code = "data"
    scope_field = "org_node"  # use "submission__org_node" when indirect

    def get_queryset(self):
        return self.get_scoped_queryset(
            Answer.objects.select_related("org_node")
        )
```

Override `get_required_permission()` for a custom action. Apply the scoped
queryset to detail retrieval as well as list operations so an out-of-scope
object returns 404 rather than disclosing its existence with 403.
