# Organizations module

`OrgNode` is ESG360's single organization hierarchy model. Every node belongs
to a Company and has a unique `code` within that company. Valid node types are
`LEGAL_ENTITY`, `BUSINESS_UNIT`, `DIVISION`, `REGION`, and `FACILITY`.

## Rules future modules can rely on

- Creating a Company creates its sole root `LEGAL_ENTITY` node.
- `path` and `depth` are model-maintained; do not write them.
- Moving a node or changing its code updates all descendant paths/depths.
- Parents must be in the same company; cycles are rejected.
- A facility cannot have children; facility metadata is allowed only for facilities.
- Country/state/city consistency follows the Companies module rules.

## API

All endpoints are under `/api/org/`.

| Endpoint | Use |
| --- | --- |
| `/nodes/` | CRUD; filters include `company`, `node_type`, `parent`, `is_active` |
| `GET /tree/` | Active roots with recursive active descendants |
| `GET /nodes/<uuid>/subtree/` | Node plus descendants |
| `GET /nodes/<uuid>/ancestors/` | Root-to-parent chain |
| `POST /nodes/<uuid>/move/` | Move with `{ "parent_id": "<uuid>" }` |

Example facility:

```json
{"company":"<uuid>","parent":"<uuid>","node_type":"FACILITY","code":"PUNE-01","name":"Pune Plant","facility_type":"Manufacturing"}
```

Use OrgNode, rather than a custom tree, when a future module needs location,
operational boundary, or org-scoped data ownership.
