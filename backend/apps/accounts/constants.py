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
    ("permission.create", "Create Permission", "permission", "CREATE"),
    ("permission.edit", "Edit Permission", "permission", "EDIT"),
    ("permission.delete", "Delete Permission", "permission", "DELETE"),
]


ROLES = [
    (
        "PLATFORM_ADMIN",
        "Platform Admin",
        "Full system access",
    ),
    (
        "COMPANY_ADMIN",
        "Company Admin",
        "Company administrator",
    ),
    (
        "DATA_ENTRY",
        "Data Entry",
        "Can enter ESG data",
    ),
    (
        "REVIEWER",
        "Reviewer",
        "Can review and approve",
    ),
    (
        "VIEWER",
        "Viewer",
        "Read only",
    ),
]

ROLE_PERMISSIONS = {
    "PLATFORM_ADMIN": [
        "user.view",
        "user.create",
        "user.edit",
        "user.delete",

        "role.view",
        "role.create",
        "role.edit",
        "role.delete",

        "permission.view",
        "permission.create",
        "permission.edit",
        "permission.delete",
    ],

    "COMPANY_ADMIN": [
        "user.view",
        "user.create",
        "user.edit",

        "role.view",

        "permission.view",
    ],

    "DATA_ENTRY": [
        "user.view",
    ],

    "REVIEWER": [
        "user.view",
    ],

    "VIEWER": [
        "user.view",
        "role.view",
        "permission.view",
    ],
}