# Companies module

The Companies module owns the organization-wide company profile, departments,
and location master data.

## Models and rules

`Country -> State -> City` is a strict hierarchy. State names/codes are unique
within a country; city names are unique within a country/state pair. A Company
may omit location fields, but a selected state must belong to its country and a
selected city must belong to both selected state and country. `company_code` is
unique and `financial_year_start_month` is 1–12.

`Department` belongs to one Company. Its parent is optional but must belong to
the same company; self-parenting and cycles are rejected. Department name and
code are unique per company. These cross-field checks run for model callers and
at API serializer validation time.

## API

All endpoints are under `/api/company/` and use UUID identifiers.

| Endpoint | Use |
| --- | --- |
| `GET /countries/` | List country master data |
| `GET /states/?country=<uuid>` | List states for a country |
| `GET /cities/?state=<uuid>` | List cities for a state |
| `GET,PATCH /profile/` | Read/update configured company profile |
| `/departments/` | Department CRUD |

Company profile responses retain UUID fields (`country`, `state`, `city`) for
edits and also include `country_name`, `state_name`, and `city_name` for
read-only displays. Consumers submit the UUID fields and render the matching
`*_name` fields without extra location lookups.

Example profile patch:

```json
{"company_name":"Example Holdings","company_code":"EXH","country":"<uuid>","state":"<uuid>","city":"<uuid>","financial_year_start_month":4}
```

Future modules should use Company as their tenant/business owner and Department
only for departmental ownership—not as an organization hierarchy substitute.
