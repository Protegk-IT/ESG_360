from apps.accounts.services.rbac import RBACService


class ScopedPermissionMixin:
    """
    Restricts queryset based on the user's
    allowed organisation scope.
    """

    scope_field = "org_node"

    def get_queryset(self):

        queryset = super().get_queryset()

        user = self.request.user

        if user.is_superuser:
            return queryset

        permission_code = self.get_required_permission()

        allowed_org_nodes = RBACService.get_allowed_org_nodes(
            user,
            permission_code,
        )

        # Company-wide access
        if allowed_org_nodes is None:
            return queryset

        if not allowed_org_nodes:
            return queryset.none()

        return queryset.filter(
            **{
                f"{self.scope_field}__in": allowed_org_nodes
            }
        )