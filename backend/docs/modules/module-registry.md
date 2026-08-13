# ESG360 Module Registry

## Purpose

The ESG360 Module Registry provides a controlled, canonical catalog of modules used across the platform.

Instead of allowing individual features to invent their own module identifiers, the registry provides each module with a stable machine-readable code and common metadata.

The registry allows the backend, APIs, permissions, Django admin, and future frontend module selectors to refer to the same module definitions.

It also provides a central place to determine which modules are enabled and which modules are considered core to ESG360.

## Model

The module registry is implemented using the `Module` model in `apps.modules`.

### Fields

| Field           | Description                                                                        |
| --------------- | ---------------------------------------------------------------------------------- |
| `code`          | Unique, stable, machine-readable module identifier.                                |
| `name`          | Human-readable module name.                                                        |
| `description`   | Description of the module and its purpose.                                         |
| `esg_pillar`    | ESG classification: `E`, `S`, `G`, or `PLATFORM`.                                  |
| `icon`          | Optional icon identifier used by consumers such as the frontend.                   |
| `is_core`       | Indicates whether the module is a core ESG360 module.                              |
| `is_enabled`    | Indicates whether the module is currently enabled.                                 |
| `display_order` | Determines the ordering of modules for consumers such as navigation and selectors. |

### Important Rules

* `code` is unique.
* Module codes are stable identifiers and should not be changed casually.
* `is_core` identifies modules that form part of the core ESG360 platform.
* `is_enabled` controls whether a module is available to consumers.
* `esg_pillar` uses the controlled `ESGPillar` choices defined by the model.
* The registry is the canonical source for module definitions.

## Canonical Codes

The following module codes are seeded by the current implementation:

| Code           | Name              | Pillar   | Core |
| -------------- | ----------------- | -------- | ---- |
| `company`      | Company           | PLATFORM | Yes  |
| `org`          | Organization      | PLATFORM | Yes  |
| `user`         | Users & Access    | PLATFORM | Yes  |
| `period`      | Reporting Periods | PLATFORM | Yes  |
| `energy`       | Energy            | E        | No   |
| `emissions`    | Emissions         | E        | No   |
| `water`        | Water             | E        | No   |
| `waste`        | Waste             | E        | No   |
| `social`       | Social            | S        | No   |
| `governance`   | Governance        | G        | No   |
| `supplier`     | Supplier          | S/G      | No   |
| `materiality`  | Materiality       | PLATFORM | No   |
| `report`       | Reporting         | PLATFORM | No   |

These values represent the canonical identifiers currently used by the module registry.

Future features must reference these codes rather than creating alternative identifiers.

## API

The module registry is exposed through the API.

### Endpoint

```text
GET /api/modules/
```

The endpoint returns the registered modules and their metadata.

### Response Example

```json
[
  {
    "code": "company",
    "name": "Company",
    "description": "Company and organizational management.",
    "esg_pillar": "PLATFORM",
    "icon": "building",
    "is_core": true,
    "is_enabled": true,
    "display_order": 1
  }
]
```

Consumers that need the currently available module list should use the registry API rather than maintaining a separate hard-coded list.

## Seeding

The module registry is populated using the Django management command provided for seeding modules.

A fresh environment should:

1. Apply the database migrations.
2. Run the module seed command.
3. Verify that the canonical module records exist.

The seed operation creates or updates the defined module records so developers do not need to manually enter every module through Django admin.

The seeded definitions are maintained in the module seeding command and should remain consistent with this documentation.

## Rules for Future Developers

When adding or implementing a new feature:

1. **Never invent a module code inside a new feature.**

2. **Check the module registry first** to determine whether the required module already exists.

3. **Stable module codes should not be renamed casually.** Other parts of the system may use the code for permissions, configuration, APIs, or data references.

4. Permissions use the format:

   ```text
   <module>.<action>
   ```

   Examples:

   ```text
   energy.view
   energy.create
   energy.edit
   energy.delete
   ```

5. Any `module_code` string stored elsewhere in the application should correspond to a registered module.

6. **Core modules remain enabled.** Core modules are fundamental platform modules and should not be disabled as part of normal feature configuration.

7. Before adding a new module, verify that it is genuinely a new module and not an existing registry entry with a different name.

## Current Integration Status

The Module Registry is now the canonical catalog of ESG360 modules.

However, existing `module_code` string fields elsewhere in the application have **intentionally not been migrated to foreign keys to `Module` in this task**.

Therefore, there is currently no database-level foreign-key referential integrity between those existing string fields and the `Module` table.

Future work may migrate those fields to `ForeignKey(Module, ...)` where appropriate.

Until that migration happens, developers must ensure that any `module_code` values correspond to a registered module code.

The registry should therefore be treated as the authoritative source for module definitions, while existing string-based integrations remain unchanged until they are explicitly migrated.
