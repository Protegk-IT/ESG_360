from rest_framework.permissions import BasePermission


class HasRolePermission(BasePermission):
    """
    Generic RBAC permission.

    Usage:
        class UserViewPermission(HasRolePermission):
            permission_code = "user.view"
    """

    permission_code = None

    def has_permission(self, request, view):

        user = request.user

        # User must be logged in
        if not user or not user.is_authenticated:
            return False

        # Superuser bypass
        if user.is_superuser:
            return True

        # User has no role assigned
        if not user.role.exists():
            return False

        # Check whether any assigned role has the required permission
        return user.role.filter(
            permissions__code=self.permission_code,
            is_active=True
        ).exists()
