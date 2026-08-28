# M6 — Emission Factor Library and Calculation

**Application:** `apps.calculations`  
**Issues:** #36 foundation + #43 approved-M5 calculation result/provenance integration

## 1. Purpose

M6 manages emission-factor sources, emission factors and declarative calculation rules, and provides deterministic Decimal-safe calculations.

M6 also integrates approved M5 numeric Answers into persisted `CalculationResult` records with provenance, versioning, idempotent replay and scoped RBAC.

## 2. Core Relationships

```text
EmissionFactorSource
        │
        └──< EmissionFactor
                ├── input_unit  ──► M4 Unit
                └── output_unit ──► M4 Unit

CalculationRule ──► optional M4 Datapoint

M5 Answer ──► ApprovedAnswerCalculationService
                         │
                         ▼
                FactorSelectionService
                         │
                         ▼
                 CalculationService
                         │
                         ▼
               CalculationResultService
                         │
                         ▼
                 CalculationResult
```

M6 uses the canonical M4 `Unit`/`UnitFamily` registry and existing authentication/RBAC. It does not create a second unit system or replacement M5 models.

## 3. Factor and Source Contract

`EmissionFactorSource` provides source/version and validity metadata. Inactive or date-invalid sources cannot be used.

`EmissionFactor` contains:

- stable `code`
- `source`
- `activity_key`
- `input_unit`
- `output_unit`
- Decimal `factor_value`
- optional `geography`
- effective dates
- active state

Factor selection uses:

```text
activity_key
+ active factor/source
+ factor effective dates
+ source effective dates
+ geography
→ matching factors
```

Exactly one valid match is required. No match and ambiguity both raise validation errors.

## 4. Calculation Contract

```python
CalculationService.calculate(
    quantity=...,
    quantity_unit=...,
    factor=...,
    calculation_date=...,
    geography=...,
)
```

Calculation flow:

```text
quantity validation
        ↓
factor/source validation
        ↓
date/geography validation
        ↓
unit active-state validation
        ↓
UnitFamily compatibility
        ↓
unit normalization
        ↓
Decimal multiplication
        ↓
calculation context
```

Normalization is based on the M4 conversion metadata:

```text
normalized_quantity =
    quantity * quantity_unit.factor_to_base
    / factor.input_unit.factor_to_base
```

## 5. Calculation Rules

`CalculationRule.rule_metadata` is declarative configuration only. It cannot contain executable code or arbitrary expressions.

The approved-M5 adapter currently supports the explicitly implemented activity-factor semantics:

```json
{
  "operation": "multiply",
  "input": "activity_quantity",
  "factor": "emission_factor",
  "activity_key": "electricity_consumption"
}
```

The adapter rejects unsupported operation/input/factor semantics instead of claiming a rule was executed when it was not.

## 6. Approved M5 → M6 Flow

The integration has two services with separate responsibilities.

### `ApprovedAnswerCalculationService`

Calculates an approved M5 numeric Answer without persisting the result.

```text
Answer
  ↓
scope permission
  ↓
Submission = APPROVED
  ↓
DECIMAL / INTEGER validation
  ↓
quantity + unit
  ↓
active CalculationRule
  ↓
activity_key
  ↓
FactorSelectionService
  ↓
CalculationService
  ↓
calculation context
```

### `CalculationResultService`

Persists the calculation and owns result lifecycle/provenance.

```text
calculation context
  ↓
reload + lock authoritative Answer
  ↓
verify current APPROVED state
  ↓
lock current/latest result state
  ↓
compare calculation fingerprint
  ├── unchanged → return CURRENT result
  └── changed   → next version
                    ↓
                 supersede old CURRENT
                    ↓
                 create new CURRENT
```

## 7. CalculationResult Contract

`CalculationResult` keeps live foreign keys for traceability and immutable snapshot fields for historical reproducibility.

### M5/M4 context

- `answer`
- `submission`
- `data_request`
- `datapoint`
- `org_node`
- `reporting_period`

### Rule provenance

- `calculation_rule`
- `calculation_rule_code`
- `calculation_rule_name`
- `calculation_rule_metadata`

### Factor/source provenance

- `emission_factor`
- `factor_code`
- `factor_value`
- `factor_source_code`
- `factor_source_name`
- `factor_source_version`
- `factor_source_reference`

### Unit provenance

- `input_unit`
- `input_unit_code`
- `input_unit_name`
- `input_unit_factor_to_base`
- `factor_input_unit_code`
- `factor_input_unit_name`
- `factor_input_unit_factor_to_base`
- `output_unit`
- `output_unit_code`
- `output_unit_name`

### Calculation context/result

- `input_quantity`
- `normalized_quantity`
- `activity_key`
- `geography`
- `calculation_date`
- `calculated_value`
- `status`
- `calculation_version`
- `calculated_by`
- `calculated_at`

## 8. Recalculation and Versioning

`CalculationResultStatus`:

```text
CURRENT
SUPERSEDED
```

For the same Answer:

```text
unchanged replay
    → reuse existing CURRENT result

relevant calculation context/rule/factor/provenance changed
    → create next calculation_version
    → previous CURRENT becomes SUPERSEDED
```

The database also enforces unique `(answer, calculation_version)`.

## 9. Historical Reproducibility

A historical result does not rely only on mutable Rule, Factor or Unit rows.

The stored rule, factor/source and unit snapshots preserve the context used for the original calculation even when live catalog rows are later edited.

## 10. Security and Scope

Calculation and result access use the existing RBAC system.

The canonical calculation/result permission is:

```text
data.approve
```

Permission and OrgNode scope must come from the same qualifying assignment.

For API lookups:

```text
accessible resource      → normal response
nonexistent resource     → 404
existing out-of-scope    → protected 404
```

Result retrieval is scoped by `org_node`. CalculationResult mutation is not exposed through normal update/delete APIs.

## 11. API Flow

### Preview

```text
POST /api/calculations/preview/
```

Standalone calculation; no `CalculationResult` persistence.

### Approved Answer calculation

```text
POST /api/calculations/approved-answer/
```

Calculates an approved M5 Answer without persisting a result.

### Persisted result

```text
POST /api/calculations/results/create/
```

Runs approved-answer calculation and persists `CalculationResult`.

### Result retrieval

```text
GET /api/calculations/results/{id}/
```

Returns only results visible within the user's approved scope.

## 12. M5 Boundary

M6 does not mutate M5 state during calculation/persistence.

The M6 flow only reads the approved Answer, Submission and DataRequest and persists the separate `CalculationResult` record.

The M5 Answer/Submission remains authoritative for workflow state.

## 13. Seed Data

`seed_emission_factors` is representative development/test data only. It is idempotent and consumes the canonical M4 unit/datapoint registry rather than creating duplicate M4 definitions.

## 14. Testing Contract

The test suite covers:

- DECIMAL and INTEGER approved Answers
- unit conversion, incompatible/inactive units
- factor/source active and effective-date validation
- geography, no-match and ambiguity
- CalculationRule semantics
- idempotent replay
- changed-context versioning/supersession
- persisted rule/factor/source/unit provenance
- historical provenance after live catalog edits
- M5 state non-mutation
- scoped Answer/result access and non-union RBAC
- normal non-superuser `data.approve` path
- approved-answer/result API create and retrieve paths
- protected wrong-scope API access
- immutable CalculationResult endpoints
- seed idempotency
- migration drift

## 15. Verification Commands

```bash
python manage.py test apps.calculations
python manage.py test apps.data_capture
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
git diff --check
```

Runtime acceptance should exercise the real flow:

```text
M4 numeric datapoint
      ↓
M5 DataRequest
      ↓
maker enters Answer
      ↓
maker submits
      ↓
reviewer approves
      ↓
M6 calculate
      ↓
M6 persist CalculationResult
      ↓
retrieve scoped result
```

## 16. Future M8 Boundary

Future M8 reporting should consume the persisted M6 calculated value through a defined provider boundary, conceptually:

```text
M5 approved activity/value
        ↓
M6 calculation/result
        ↓
SnapshotMapping / calculated-value provider
        ↓
M8 reporting
```

M8 should consume the persisted calculated value and its provenance rather than re-implementing factor selection or calculation logic.
