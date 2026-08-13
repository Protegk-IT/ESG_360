CRUD_MODULES = (
    "company",
    "country",
    "state",
    "city",
    "department",
    "organization",
    "reporting_period",
)

CRUD_ACTIONS = (
    ("view", "VIEW"),
    ("create", "CREATE"),
    ("edit", "EDIT"),
    ("delete", "DELETE"),
)

CRUD_PERMISSIONS = [
    (f"{module}.{action}", f"{action.title()} {module.replace('_', ' ').title()}", module, db_action)
    for module in CRUD_MODULES
    for action, db_action in CRUD_ACTIONS
]

DEPRECATED_PERMISSION_CODES = (
    "org.manage",
    "period.manage",
    "period.reopen",
    "permission.create",
    "permission.edit",
    "permission.delete",
)

PERMISSIONS = [
    ("user.view", "View User", "user", "VIEW"),
    ("user.create", "Create User", "user", "CREATE"),
    ("user.edit", "Edit User", "user", "EDIT"),
    ("user.delete", "Delete User", "user", "DELETE"),

    ("role.view", "View Role", "role", "VIEW"),
    ("role.create", "Create Role", "role", "CREATE"),
    ("role.edit", "Edit Role", "role", "EDIT"),
    ("role.delete", "Delete Role", "role", "DELETE"),

    ("permission.view", "View Permission", "permission", "VIEW"),
    # §7.2 Capability permissions

    ("organization.manage", "Manage org structure", "organization", "MANAGE"),

    ("user.manage", "Manage users and scopes", "user", "MANAGE"),

    ("reporting_period.manage", "Manage reporting periods", "reporting_period", "MANAGE"),

    ("datapoint.manage", "Manage datapoint catalog", "datapoint", "MANAGE"),

    ("emission_factor.manage", "Manage emission factors", "emission_factor", "MANAGE"),

    ("framework_mapping.manage", "Manage framework mappings", "framework_mapping", "MANAGE"),

    ("data.enter", "Enter data", "data", "EDIT"),

    ("evidence.upload", "Upload evidence", "evidence", "CREATE"),

    ("data.submit", "Submit for review", "data", "APPROVE"),

    ("data.approve", "Approve or reject data", "data", "APPROVE"),

    ("reporting_period.reopen", "Reopen a locked period", "reporting_period", "EDIT"),

    ("materiality.run", "Run materiality assessment", "materiality", "CREATE"),

    ("materiality.approve", "Approve materiality", "materiality", "APPROVE"),

    ("report.create_run", "Create report run", "report", "CREATE"),

    ("disclosure.assign", "Assign disclosures", "disclosure", "MANAGE"),

    ("disclosure.answer", "Answer assigned disclosure", "disclosure", "EDIT"),

    ("disclosure.approve", "Approve disclosure response", "disclosure", "APPROVE"),

    ("report.finalise", "Finalise report", "report", "CLOSE"),

    ("report.export", "Export report", "report", "EXPORT"),

    ("target.set", "Set targets", "target", "EDIT"),

    ("dashboard.view", "View dashboards", "dashboard", "VIEW"),

    ("evidence.view", "View evidence", "evidence", "VIEW"),

    ("audit.raise_query", "Raise audit query", "audit", "CREATE"),

    ("audit.respond_query", "Respond to audit query", "audit", "EDIT"),

    ("activity_log.view", "View activity log", "activity_log", "VIEW"),
] + CRUD_PERMISSIONS


ROLES = [
    (
        "platform_admin",
        "Platform Admin",
        "Full system access",
    ),
    (
        "company_admin",
        "Company Admin",
        "Manages company organization, users, scopes, reporting configuration and other administrative capabilities.",
    ),
    (
        "esg_manager",
        "ESG Manager",
        "Manages ESG reporting, reviews data, materiality, disclosures and report finalisation.",
    ),
    (
        "reviewer",
        "Reviewer",
        "Reviews and approves or rejects submitted data and responds to audit queries.",
    ),
    (
        "data_entry",
        "Data Entry",
        "Enters reporting data, uploads evidence and submits data for review.",
    ),
    (
        "contributor",
        "Contributor",
        "Uploads evidence and answers assigned disclosures.",
    ),
    (
        "auditor",
        "Auditor",
        "Performs audit activities, raises audit queries and reviews evidence and activity logs.",
    ),
    (
        "exec",
        "Executive",
        "Views dashboards and exports reports.",
    ),
]

ROLE_PERMISSIONS = {
    "platform_admin": [
        *[code for code, *_ in PERMISSIONS],
    ],
    "company_admin": [
        *[
            code for code, *_ in CRUD_PERMISSIONS
            if code.split(".", 1)[0] in {
                "company", "country", "state", "city", "department",
                "organization", "reporting_period",
            }
        ],
        "organization.manage",
        "user.manage",
        "reporting_period.manage",
        "datapoint.manage",
        "emission_factor.manage",
        "framework_mapping.manage",
        "evidence.upload",
        "reporting_period.reopen",
        "report.export",
        "target.set",
        "dashboard.view",
        "evidence.view",
        "activity_log.view",

        "user.view",
        "user.create",
        "user.edit",
        
        "role.view",
        
        "permission.view",
    ],

    "esg_manager": [
        "reporting_period.view",
        "reporting_period.create",
        "reporting_period.edit",
        "reporting_period.manage",
        "datapoint.manage",
        "emission_factor.manage",
        "framework_mapping.manage",
        "evidence.upload",
        "data.approve",
        "materiality.run",
        "materiality.approve",
        "report.create_run",
        "disclosure.assign",
        "disclosure.answer",
        "disclosure.approve",
        "report.finalise",
        "report.export",
        "target.set",
        "dashboard.view",
        "evidence.view",
        "audit.respond_query",
        "activity_log.view",
    ],

    "reviewer": [
        "evidence.upload",
        "data.approve",
        "report.export",
        "dashboard.view",
        "evidence.view",
        "audit.respond_query",
        "user.view",
    ],

    "data_entry": [
        "data.enter",
        "evidence.upload",
        "data.submit",
        "dashboard.view",
        "evidence.view",
        "user.view",
        "user.edit",
        "user.create",
        "user.delete",
    ],

    "contributor": [
        "evidence.upload",
        "disclosure.answer",
    ],

    "auditor": [
        "report.export",
        "dashboard.view",
        "evidence.view",
        "audit.raise_query",
        "activity_log.view",
    ],

    "exec": [
        "report.export",
        "dashboard.view",
    ],
}
