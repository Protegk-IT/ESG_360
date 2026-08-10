# Reporting Periods module

`ReportingPeriod` supports `ANNUAL`, `HALF_YEARLY`, `QUARTERLY`, and `MONTHLY`
periods with optional parent/child relationships. Statuses are `OPEN`, `LOCKED`,
and `CLOSED`.

## Rules

- `end_date` must be after `start_date`; children must fit inside the parent.
- Active annual periods cannot overlap and only one active baseline year exists.
- CLOSED is terminal.
- An OPEN annual period can generate exactly one child cadence. Generation is
  transactional and row-locked, preventing concurrent duplicates.
- Calendar boundaries follow the annual period start date, so April–March years
  produce Apr–Jun / Jul–Sep / Oct–Dec / Jan–Mar quarters.

## API

All endpoints are under `/api/periods/`.

| Endpoint | Use |
| --- | --- |
| `/` | CRUD; filters `period_type`, `status` |
| `GET /current/` | Current OPEN period containing today |
| `POST /<uuid>/lock/` | Lock and record current user/time |
| `POST /<uuid>/unlock/` | Reopen non-CLOSED period |
| `POST /<uuid>/generate-subperiods/` | Create child cadence |

Generate example:

```json
{"period_type":"QUARTERLY"}
```

Future ESG data modules should attach reporting data to ReportingPeriod and use
the status to decide whether normal editing is permitted.
