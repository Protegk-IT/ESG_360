from rest_framework.permissions import BasePermission

from apps.accounts.services.rbac import RBACService


class HasRolePermission(BasePermission):
    """
    Checks whether the authenticated user has
    the required permission for the current action.
    """

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):

        if request.user.is_superuser:
            return True

        permission_code = view.get_required_permission()

        if not permission_code:
            return False

        return RBACService.has_permission(
            request.user,
            permission_code
        )