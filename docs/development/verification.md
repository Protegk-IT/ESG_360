# Foundation verification

Use this checklist after a clean checkout of the ESG360 foundation. Run the
backend commands from `backend/` with the project virtual environment active.
Use a disposable SQLite database for this process; do not point the commands at
shared local development data.

## Clean setup

```bash
python manage.py migrate --noinput
python manage.py seed_modules
python manage.py seed_rbac
python manage.py seed_locations
```

Run the three seed commands a second time. They must complete without duplicate
records. `seed_modules` creates the canonical module catalog; `seed_rbac`
creates/updates roles and permissions and removes retired `org.*` / `period.*`
permissions; `seed_locations` loads country, state, and city reference data.

## Materiality visual demo states

For a deterministic local Materiality workspace, create a superuser (or pass
an existing active username) and run:

```bash
python manage.py seed_demo_materiality --owner <username>
```

The command also calls the foundation seed and creates exactly three named demo
assessments: **Demo — Draft Materiality Assessment** (blank scope), **Demo — FY
2025-26 Materiality Assessment** (topics, weighted groups, known stakeholders,
invitations, and group links ready for manual survey testing), and **Demo —
Completed Materiality Assessment** (a locked historical score run, matrix, and
documented override). The completed fixture includes eighteen submitted
responses across all six stakeholder groups (one identified and seventeen
anonymous), producing examples in every materiality-matrix quadrant.
Re-running the command resets only those named demo
assessments to those deterministic states; it never changes user-created
assessments.

Create a superuser and minimum company, organisation node, department, and
normal user through the API, admin, or Django shell as needed for manual
testing. Keep test identities and generated records in the disposable database.

## Automated verification

```bash
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
cd ../frontend
npm run build
npm run lint
cd ..
git diff --check
```

The Module Registry seed should contain canonical `organization` and
`reporting_period` entries, never `org` or `period`. Every `Permission` record
must have a `module_code` equal to its code prefix and registered in
`/api/modules/`.

## Browser smoke flows

Start the backend at `localhost:8000` and Vite at `localhost:5173`. Use the
same host spelling on both sides (`localhost` or `127.0.0.1`) so session cookies
and CSRF remain same-site.

1. Load the app, log in, reload, verify `/me` restores the server session, then
   log out. Confirm protected routes redirect or deny access when signed out.
2. As a superuser, visit dashboard, company, organisations, departments, users,
   roles, reporting periods, and modules. Check browser console and network for
   failed requests.
3. Edit company and organisation locations and verify country/state/city labels
   hydrate after save and reload. Edit a department through its UUID route,
   including parent selection.
4. Create a normal scoped user with assignments on two organisation nodes and
   distinct roles. Verify permitted data is visible only for the matching
   scope, and an out-of-scope detail URL returns no data.
5. Verify role-permission matrix persistence and system-role protection.
6. Create an April-March annual period; generate supported subperiods once;
   verify duplicate generation, locked periods, and non-annual periods are
   rejected. Confirm UI action visibility follows the returned state.
7. Mark and read a notification as its owner, and verify create/update/delete
   actions produce activity-log entries. Test a 400 validation response as well
   as a normal loading and empty state.
8. At a mobile-width viewport, verify navigation and primary forms remain
   usable.

See the module and contract documents in `docs/modules/` and `docs/contracts/`
for request shapes, permission vocabulary, and scoped-viewset rules.
