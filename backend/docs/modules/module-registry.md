# ESG 360 - Module Registry

## Purpose

The Module Registry provides a canonical catalog of modules used by ESG 360.

The registry gives each module one stable, machine-readable identifier and provides
common metadata that can be consumed by the backend, Django admin, APIs, and
future frontend module selectors.

The registry is intentionally independent from individual module implementations.

---

## Canonical Module Identity

Each module is identified by its `code`.

The `code` is:

- unique
- stable
- machine-readable
- the canonical identifier for the module
- not intended to be used as an alias system

The current canonical module codes are:

- `company`
- `org`
- `user`
- `period`
- `energy`
- `emissions`
- `water`
- `waste`
- `social`
- `governance`
- `supplier`
- `materiality`
- `report`

Future modules should add one canonical code rather than introducing aliases
for an existing module.

---

## Model

The registry is implemented using the `Module` model in:

`apps/modules/models.py`

### Fields

| Field | Description |
|---|---|
| `id` | UUID primary key inherited from `BaseModel` |
| `code` | Unique, stable machine-readable module identifier |
| `name` | Human-readable module name |
| `description` | Description of the module |
| `esg_pillar` | ESG classification: `E`, `S`, `G`, or `PLATFORM` |
| `icon` | Icon identifier for future frontend use |
| `is_core` | Identifies foundation modules that cannot be disabled |
| `is_enabled` | Indicates whether the module is enabled in the deployment |
| `display_order` | Stable ordering for module discovery and navigation |

---

## ESG Pillars

The registry supports the following values:

| Value | Meaning |
|---|---|
| `E` | Environmental |
| `S` | Social |
| `G` | Governance |
| `PLATFORM` | Platform/foundation functionality |

---

## Core Module Rule

Core modules must always remain enabled.

The following modules are currently core:

- `company`
- `org`
- `user`
- `period`

A module cannot have:

```text
is_core = true
is_enabled = false