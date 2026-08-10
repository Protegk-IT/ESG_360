from apps.accounts.services.rbac import RBACService


class ScopedPermissionMixin:

    scope_permission = None
    scope_field = "org_node"

    def get_scoped_queryset(self, queryset):

        if not self.scope_permission:
            return queryset

        allowed_nodes = RBACService.get_allowed_org_nodes(
            user=self.request.user,
            permission_code=self.scope_permission,
        )

        # Company-wide access
        if allowed_nodes is None:
            return queryset

        # No access
        if not allowed_nodes:
            return queryset.none()

        return queryset.filter(
            **{
                f"{self.scope_field}__in": allowed_nodes
            }
        )