# M6 — Emission Factor Library and Calculation Rule Foundation

---

## 1. Overview

M6 provides the foundation for managing emission factors and performing deterministic calculations in ESG 360.

The module builds on the canonical M4 Unit and UnitFamily foundation and provides:

- emission-factor source/version management;
- reusable emission-factor definitions;
- deterministic factor selection;
- explicit-input calculation services;
- declarative calculation-rule metadata;
- authenticated APIs;
- RBAC-protected administrative operations;
- representative seed data;
- automated tests.

M6 is intentionally independent of the unfinished M5 Data Capture models.

No M5 `Answer`, `Submission`, or `DataRequest` dependency is introduced.

---

## 2. M6 Scope

### 2.1 Included

This issue includes:

- `EmissionFactorSource`;
- `EmissionFactor`;
- `CalculationRule`;
- factor-selection service;
- calculation service;
- calculation preview API;
- factor/source APIs;
- calculation-rule APIs;
- RBAC integration;
- representative seed data;
- automated tests;
- M6 documentation.

### 2.2 Out of Scope

The following are explicitly outside this issue:

- M5 `Answer` models;
- M5 `Submission` models;
- M5 `DataRequest` models;
- foreign keys to M5 models;
- persistent calculation results tied to M5;
- complete emissions inventory;
- full Energy/Emissions activity-record workflow;
- M5 approval workflow;
- report generation;
- M8 report resolution;
- complete official emission-factor population;
- concrete M13 `EMISSION_FACTORS` import handler;
- frontend calculation screens;
- Materiality changes.

M6 must not modify M5 merely to complete this foundation.

---

## 3. Stable Dependencies

M6 uses the contracts already available in `develop`:

- M4 Datapoint Catalog;
- M4 `UnitFamily`;
- M4 `Unit`;
- M4 unit conversion foundation;
- M13 Module Registry;
- stabilized `BaseModel`;
- existing authentication;
- existing RBAC;
- existing API conventions.

M5 Data Capture is still in progress.

Therefore M6 does not introduce dependencies on:

```text
Answer
Submission
DataRequest
```

and does not create replacement models for them.

---

## 4. Domain Model Relationships

The core M6 model relationships are:

```text
EmissionFactorSource
        │
        │ 1
        │
        │ *
        ▼
EmissionFactor
        │
        ├──────────────► Unit
        │                 input_unit
        │
        └──────────────► Unit
                          output_unit
```

`EmissionFactor` belongs to an `EmissionFactorSource`.

The factor references the canonical M4 `Unit` registry for both its input and output units.

M6 does not create a separate unit system.

The calculation-rule relationship is separate:

```text
CalculationRule
       │
       └──────────────► optional M4 Datapoint
```

The calculation service does not persist calculated results.

The runtime calculation flow is:

```text
Explicit calculation input
            │
            ▼
     CalculationService
            │
            ▼
     Calculation result
```

---

## 5. EmissionFactorSource

`EmissionFactorSource` represents the provenance and version context for emission factors.

The source contains metadata needed to identify the origin and validity of factor records.

The source model supports information such as:

- stable code;
- name;
- publisher;
- version;
- source reference;
- publication date;
- effective-from date;
- effective-to date;
- source URL;
- active state.

### 5.1 Source and Version Contract

A factor is associated with a specific source/version.

The source code and version provide the provenance context for the factor.

The implementation must not fabricate official provenance.

Representative/demo sources used by the seed data are not official production sources.

### 5.2 Source Effective Dates

A source may define:

```text
effective_from
effective_to
```

The effective range must be valid.

An invalid range where `effective_from > effective_to` must be rejected.

A source that is outside its effective period must not be treated as valid for a calculation.

### 5.3 Source Active State

A source has an active state.

An inactive source must not be selected or used for calculations.

---

## 6. EmissionFactor

`EmissionFactor` represents a reusable emission-factor definition.

A factor supports:

- stable code;
- source/version relationship;
- activity/factor key;
- input unit;
- output unit;
- Decimal factor value;
- optional geography;
- effective dates;
- active state;
- notes/source metadata.

Conceptually:

```text
EmissionFactor
├── code
├── source
├── activity_key
├── input_unit
├── output_unit
├── factor_value
├── geography
├── effective_from
├── effective_to
├── is_active
└── notes
```

---

## 7. Factor Value

Factor values use `Decimal`.

This provides deterministic arithmetic and avoids binary floating-point behavior.

The implemented validation requires the factor value to be greater than zero.

---

## 8. M4 Unit Contract

M6 consumes the canonical M4 Unit registry.

The factor does not define or duplicate units.

```text
EmissionFactor.input_unit
        │
        ▼
     M4 Unit

EmissionFactor.output_unit
        │
        ▼
     M4 Unit
```

This keeps unit definitions and conversion behavior owned by M4.

---

## 9. Unit Compatibility

The calculation service validates that the supplied quantity unit is compatible with the factor's input unit.

Compatibility is determined through the M4 `UnitFamily`.

An incompatible UnitFamily is rejected.

M6 does not perform conversions between unrelated UnitFamilies.

### 9.1 Same UnitFamily

M6 does not require input and output units to belong to different UnitFamilies.

For example:

```text
input_unit  = KG
output_unit = KG
```

is not rejected solely because both units belong to the same UnitFamily.

This restriction was intentionally removed because it was not part of the M4/M6 contract.

---

## 10. Factor Validity and Applicability

A factor can be used for calculation only when its validity and applicability conditions are satisfied.

The relevant context includes:

```text
Factor active state
        +
Source active state
        +
Factor effective dates
        +
Source effective dates
        +
Geography applicability
        +
Unit active state
        +
Unit compatibility
```

The explicit calculation service validates these conditions even when the factor was supplied directly by the caller.

### 10.1 Inactive Factor

An inactive factor cannot be used for calculation.

### 10.2 Factor Effective Date

If a factor defines an effective period, the supplied calculation date must fall within that period.

### 10.3 Source Effective Date

The source effective period is also part of factor validity.

A source outside its effective period cannot be used for calculation.

---

## 11. Geography Applicability

A factor may define an applicable geography.

The calculation service accepts geography explicitly.

If a factor has a geographic scope:

- geography must be supplied;
- the supplied geography must match the factor applicability.

M6 does not infer geography from unfinished M5 models.

---

## 12. Factor Selection

M6 provides a dedicated `FactorSelectionService`.

The service selects a factor using explicit calculation context supplied by the caller.

The selection context includes:

```text
activity_key
calculation_date
geography
```

where applicable.

---

## 13. Factor Selection Contract

The selection process is:

```text
activity_key
      │
      ▼
active factors
      │
      ▼
active sources
      │
      ▼
factor effective dates
      │
      ▼
source effective dates
      │
      ▼
geography
      │
      ▼
matching factors
```

### 13.1 Deterministic Selection

When exactly one valid factor matches, that factor is returned.

### 13.2 No Match

When no valid factor matches, the service raises a clear validation error.

It does not silently return an arbitrary factor.

### 13.3 Ambiguous Selection

When multiple valid factors match, the service raises an ambiguity validation error.

It must not arbitrarily select one factor.

This prevents nondeterministic calculations.

---

## 14. CalculationService

M6 provides a pure/domain `CalculationService`.

The implemented contract is:

```python
CalculationService.calculate(
    quantity=...,
    quantity_unit=...,
    factor=...,
    calculation_date=...,
    geography=...,
)
```

The calculation service does not persist calculated results.

---

## 15. Calculation Service Behavior

The calculation flow is:

```text
Quantity
   │
   ▼
Quantity validation
   │
   ▼
Factor validation
   │
   ▼
Source validation
   │
   ▼
Date validity
   │
   ▼
Geography applicability
   │
   ▼
Unit validation
   │
   ▼
Unit-family compatibility
   │
   ▼
Unit conversion
   │
   ▼
Decimal calculation
   │
   ▼
Calculation result
```

Negative quantities are rejected.

The supplied quantity is converted to `Decimal` before calculation.

---

## 16. Unit Conversion

The supplied quantity may use another unit from the same UnitFamily as the factor input unit.

For example:

```text
Quantity:
1 MWH

Factor input:
KWH
```

If the M4 conversion metadata defines:

```text
1 MWH = 1000 KWH
```

the calculation service normalizes the quantity to the factor's input unit.

Conceptually:

```text
normalized_quantity =
    quantity * quantity_unit.factor_to_base
    / factor.input_unit.factor_to_base
```

---

## 17. Decimal Calculation

After normalization:

```text
calculated_value =
    normalized_quantity * factor.factor_value
```

Example:

```text
Quantity:
100 KWH

Factor:
0.5 KG/KWH

Calculation:
100 × 0.5

Result:
50 KG
```

No floating-point arithmetic is required for the calculation.

---

## 18. Calculation Result

The calculation service returns calculation information without persisting it.

The result contains:

```text
input_quantity
input_unit
normalized_quantity
calculated_value
output_unit
factor
```

The result is intended to be consumed by a future integration layer.

---

## 19. Calculation Preview API

M6 exposes:

```text
POST /api/calculations/preview/
```

Example request:

```json
{
    "quantity": "100",
    "quantity_unit": "<unit-id>",
    "factor": "<factor-id>",
    "calculation_date": "2026-08-21"
}
```

Optional geography may be supplied.

The endpoint:

1. requires authentication;
2. validates request data;
3. validates unit compatibility;
4. validates factor/source validity;
5. calls `CalculationService`;
6. returns the calculation result.

The endpoint does not persist an M5-dependent result.

---

## 20. CalculationRule

`CalculationRule` provides a declarative metadata layer for future calculation behavior.

The rule can optionally reference an M4 Datapoint.

It does not reference unfinished M5 Answer records.

The model supports:

```text
code
name
description
datapoint
rule_metadata
is_active
```

---

## 21. CalculationRule Metadata Contract

The current M6 foundation requires `rule_metadata` to be a JSON object.

Example:

```json
{
    "operation": "multiply"
}
```

Current M6 calculation-rule metadata supports a constrained
declarative multiplication rule:

```json
{
    "operation": "multiply",
    "input": "activity_quantity",
    "factor": "emission_factor"
}
```

Rule metadata is configuration only. It does not contain executable
code or arbitrary expressions. Additional rule types may be introduced
later through an explicitly defined contract.

---

## 22. CalculationRule Safety

M6 must not provide arbitrary executable expressions.

The rule metadata must not be used to execute arbitrary Python or other code.

The foundation does not introduce `eval()`, `exec()`, or a general-purpose expression engine.

Additional calculation-rule semantics should only be introduced when supported by a defined domain contract.

---

## 23. API Resources

M6 exposes authenticated APIs for:

```text
Emission Factor Sources
Emission Factors
Calculation Rules
Calculation Preview
```

The APIs follow existing Django REST Framework conventions.

---

## 24. API Authentication

M6 APIs require authentication according to the existing project authentication configuration.

Unauthenticated users cannot access protected M6 resources.

The calculation preview endpoint is also protected.

---

## 25. API RBAC

M6 uses the existing canonical RBAC system.

The canonical permission for factor administration is:

```text
emission_factor.manage
```

The permission is already present in the project's permission catalog.

The RBAC flow is:

```text
User
  │
  ▼
UserRoleAssignment
  │
  ▼
Role
  │
  ▼
Permission
  │
  ▼
emission_factor.manage
```

### 25.1 User Without Permission

An authenticated user without `emission_factor.manage` cannot perform administrative factor operations.

Expected result:

```text
403 Forbidden
```

### 25.2 User With Permission

A normal non-superuser can perform the administrative operation when the user's role assignment grants:

```text
emission_factor.manage
```

through the existing RBAC infrastructure.

Authentication alone does not grant this permission.

### 25.3 Superuser

Superuser behavior follows the existing project RBAC implementation.

M6 does not create a separate authorization mechanism.

---

## 26. Representative Seed Data

M6 provides representative seed data to prove the architecture and calculation flow.

The seed data is for development/testing purposes.

It must not be interpreted as an official production emission-factor library.

M6 does not fabricate official values from government sources, DEFRA, EPA, IPCC, regulatory databases, or other authoritative providers.

Official factor population is outside this issue unless separately sourced and reviewed.

---

## 27. Seed Idempotency

Where the M6 seed command is provided, it must be safe to execute more than once.

Running:

```bash
python manage.py seed_emission_factors
```

again should not create duplicate factor sources, factors, or rules.

The test suite verifies seed idempotency.

---

## 28. Testing Contract

The M6 test suite covers:

### EmissionFactorSource

- source/version creation;
- effective-date validation;
- code/version uniqueness.

### EmissionFactor

- factor creation;
- positive factor value;
- negative factor rejection;
- effective-date validation;
- canonical M4 Unit usage;
- same-family input/output acceptance;
- inactive factor state.

### CalculationRule

- rule creation;
- JSON-object metadata validation;
- declarative metadata acceptance;
- unique rule code.

### Calculation API

- authentication;
- authenticated factor access;
- RBAC denial without manage permission;
- administrative access;
- calculation preview;
- calculation date requirement;
- incompatible unit rejection;
- inactive factor rejection;
- inactive source rejection;
- expired factor rejection;
- future factor rejection;
- expired source rejection;
- future source rejection.

### Seed

- seed idempotency.

### Database

- migration drift verification.

---

## 29. Representative Calculation Verification

M6 verification should demonstrate:

### Base Unit

```text
100 KWH
```

with a representative factor such as:

```text
0.5 KG/KWH
```

produces:

```text
50 KG
```

### Converted Unit

For example:

```text
1 MWH
```

with:

```text
1 MWH = 1000 KWH
```

is normalized to:

```text
1000 KWH
```

before the factor is applied.

### Invalid Unit

A quantity using an incompatible UnitFamily must be rejected.

### No Factor

If no factor matches the explicit selection context, a clear validation error must be returned.

### Ambiguous Factor

If multiple valid factors match the same context, an ambiguity error must be returned.

The service must not select one arbitrarily.

---

## 30. Future M5 Adapter Boundary

M6 is intentionally designed so that M5 can consume it later without changing the core calculation service.

The future integration boundary is:

```text
M5 approved activity/value
            │
            ▼
       M5 Adapter
            │
            ▼
   Factor Selection
            │
            ▼
   CalculationService
            │
            ▼
Future calculated result
       + provenance
```

The M5 adapter is not implemented in this issue.

The calculation service currently receives explicit inputs such as:

```text
quantity
quantity_unit
factor
calculation_date
geography
```

This keeps M6 independent from the unfinished M5 Answer/Submission/DataRequest contract.

---

## 31. Why M5 Is Not a Dependency

M5 Data Capture is still being developed.

Adding M5 foreign keys at this stage would make M6 dependent on models whose contracts are not yet stable.

Therefore M6 intentionally uses explicit service inputs rather than M5 persistence models.

The future adapter will translate an approved M5 activity/value into the explicit M6 calculation inputs.

---

## 32. Persistent Calculation Results

Persistent calculation results are not part of M6.

The calculation service returns a result but does not create a persistent M5-linked result record.

Persistent calculation storage requires later decisions around:

- Answer integration;
- approval state;
- reporting period;
- factor provenance;
- recalculation;
- auditability;
- versioning.

Those decisions are outside Issue #36.

---

## 33. M13 Boundary

M6 does not implement the concrete M13 `EMISSION_FACTORS` import handler.

The M6 factor catalog can be used by a future integration mechanism, but external factor import is not part of this issue.

The current seed data is only representative development/test data.

---

## 34. Architecture Summary

```text
                    M4
             Unit / UnitFamily
                    │
                    ▼
        ┌────────────────────────┐
        │    EmissionFactor      │
        │                        │
        │ activity_key           │
        │ source                 │
        │ input_unit             │
        │ output_unit            │
        │ factor_value           │
        │ geography              │
        │ effective dates        │
        │ active state           │
        └───────────┬────────────┘
                    │
                    ▼
        ┌────────────────────────┐
        │ FactorSelectionService │
        │                        │
        │ explicit context       │
        │ validity               │
        │ applicability          │
        │ no-match               │
        │ ambiguity              │
        └───────────┬────────────┘
                    │
                    ▼
        ┌────────────────────────┐
        │ CalculationService     │
        │                        │
        │ Decimal arithmetic     │
        │ unit conversion        │
        │ validation             │
        │ calculation            │
        └───────────┬────────────┘
                    │
                    ▼
          Non-persistent result


        ┌────────────────────────┐
        │ CalculationRule        │
        │                        │
        │ declarative metadata   │
        │ optional M4 datapoint  │
        └────────────────────────┘
```

---

## 35. Final M6 Contract

M6 establishes:

```text
M4 Unit / UnitFamily
        +
Versioned Factor Sources
        +
Reusable Emission Factors
        +
Explicit Selection Context
        +
Deterministic Factor Selection
        +
Factor/Source Validity
        +
Geography Applicability
        +
Decimal-safe Calculation
        +
Canonical Unit Conversion
        +
Declarative CalculationRule Metadata
        +
Authenticated APIs
        +
Canonical RBAC
        +
Representative Seed Data
        +
Automated Tests
```

The foundation is intentionally limited to factor management and deterministic calculation.

The future M5 integration can consume the M6 calculation service through a small adapter once the M5 Data Capture contract is stable.

M6 does not implement persistent M5 calculation results, a complete emissions inventory, official production factor population, or other functionality listed as out of scope for Issue #36.
