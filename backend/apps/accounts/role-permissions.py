from .permissions import HasRolePermission


# =======================
# USER
# =======================

class CanViewUsers(HasRolePermission):
    permission_code = "user.view"


class CanCreateUsers(HasRolePermission):
    permission_code = "user.create"


class CanEditUsers(HasRolePermission):
    permission_code = "user.edit"


class CanDeleteUsers(HasRolePermission):
    permission_code = "user.delete"


# =======================
# ROLE
# =======================

class CanViewRoles(HasRolePermission):
    permission_code = "role.view"


class CanCreateRoles(HasRolePermission):
    permission_code = "role.create"


class CanEditRoles(HasRolePermission):
    permission_code = "role.edit"


class CanDeleteRoles(HasRolePermission):
    permission_code = "role.delete"


# =======================
# PERMISSION
# =======================

class CanViewPermissions(HasRolePermission):
    permission_code = "permission.view"


class CanCreatePermissions(HasRolePermission):
    permission_code = "permission.create"


class CanEditPermissions(HasRolePermission):
    permission_code = "permission.edit"


class CanDeletePermissions(HasRolePermission):
    permission_code = "permission.delete"

