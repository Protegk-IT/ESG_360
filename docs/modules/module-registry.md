# Module Registry

The `modules` app provides ESG360's canonical catalog of platform and ESG
modules. It is deliberately independent of feature applications: it stores no
foreign keys to roles, permissions, assignments, or future feature models.

## Model and invariants

`apps.modules.models.Module` has a UUID primary key inherited from
`core.BaseModel` and these public fields:

| Field | Meaning |
| --- | --- |
| `code` | Unique, stable machine identifier. |
| `name`, `description`, `icon` | Consumer-facing metadata. |
| `esg_pillar` | One of `PLATFORM`, `E`, `S`, or `G`. |
| `is_core` | The module is required by the platform. |
| `is_enabled` | The module is available in this deployment. |
| `display_order` | Stable presentation order. |

Core modules must remain enabled. This is enforced both by model validation and
the `modules_core_requires_enabled` database constraint, so direct queryset
updates cannot create an invalid state.

Do not rename a code as part of ordinary feature work. It is the registry side
of the permission vocabulary: permission codes use `<module>.<action>` and a
registered module code must use the same canonical prefix.

## Canonical codes

`python manage.py seed_modules` seeds the following complete catalog. The
platform/identity contract currently uses every enabled platform code and the
listed future-feature codes are reserved so later applications do not invent
aliases.

| Group | Codes |
| --- | --- |
| Core platform | `company`, `organization`, `user`, `reporting_period` |
| Enabled platform capabilities | `country`, `state`, `city`, `department`, `role`, `permission`, `dashboard`, `activity_log` |
| Reserved platform/data capabilities | `datapoint`, `emission_factor`, `framework_mapping`, `data`, `evidence`, `disclosure`, `target`, `audit` |
| ESG and future modules | `energy`, `emissions`, `water`, `waste`, `social`, `governance`, `supplier`, `materiality`, `report` |

`org` and `period` are retired aliases. Migration `0004` upgrades registry
rows seeded by the original implementation to `organization` and
`reporting_period`; new code must never use the aliases. This follows the
stabilized Identity/RBAC permission-code contract.

## Seeding and deployment

After migrations, run:

```bash
python manage.py seed_modules
```

The command is idempotent. It creates missing records, refreshes catalog
metadata, keeps an existing optional module's `is_enabled` choice, and ensures
all core modules are enabled. Run it again after deploying a catalog change.

## API

Authenticated users can read the catalog:

```text
GET /api/modules/
GET /api/modules/?enabled=true
GET /api/modules/?enabled=false
```

The endpoint is read-only and returns records ordered by `display_order` then
name. It may use the project's standard pagination envelope; clients should
accept either the list itself or `results`.

```json
{
  "code": "organization",
  "name": "Organization",
  "description": "Organization structure and hierarchy management.",
  "esg_pillar": "PLATFORM",
  "icon": "network",
  "is_core": true,
  "is_enabled": true,
  "display_order": 2
}
```

No write API is intentionally exposed. Registry maintenance is through Django
admin or controlled seed changes. The admin list has search, filtering and
ordering; its model validation prevents disabling a core module.

## Guidance for feature developers

Before adding a feature, look up its code here and use it consistently in
permissions, scopes, API contracts, and frontend navigation. Adding a truly
new code requires a reviewed seed/catalog change, tests, and documentation.
The registry is canonical metadata, not a migration mandate: existing
string-valued `module_code` fields remain strings until a separately scoped
data-model migration introduces a safe relationship.
