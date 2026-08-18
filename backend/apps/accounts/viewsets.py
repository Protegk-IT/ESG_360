from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import HasRolePermission
from apps.accounts.mixins import ScopedPermissionMixin


class RBACModelViewSet(ScopedPermissionMixin, viewsets.ModelViewSet):
    """
    Base ViewSet for RBAC protected APIs.
    """

    permission_classes = (
        IsAuthenticated,
        HasRolePermission,
    )

    # Example:
    # module_code = "user"
    module_code = None

    ACTION_PERMISSION_MAP = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "update": "edit",
        "partial_update": "edit",
        "destroy": "delete",
    }

    def get_required_permission(self):
        """
        Returns permission code based on
        module_code and DRF action.

        Example:
            user.view
            role.create
            permission.edit
        """

        permission_action = self.ACTION_PERMISSION_MAP.get(
            self.action
        )

        if not permission_action:
            return None

        if not self.module_code:
            raise ValueError(
                f"{self.__class__.__name__} must define module_code."
            )

        return f"{self.module_code}.{permission_action}"
