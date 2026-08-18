from apps.accounts.services.rbac import RBACService


class ScopedPermissionMixin:
    """Apply the current action's RBAC scope to an organisation-backed queryset.

    Set ``scope_field`` to the ORM path that resolves a row to an ``OrgNode``.
    For an ``OrgNode`` queryset itself, use ``"id"``.  Viewsets without an
    organisation-backed resource leave it as ``None`` and receive permission
    enforcement without row scoping.
    """

    scope_permission = None
    scope_field = None

    def get_scope_permission(self):
        return self.scope_permission or self.get_required_permission()

    def get_scoped_queryset(self, queryset):
        if not self.scope_field:
            return queryset

        permission_code = self.get_scope_permission()
        if not permission_code:
            return queryset.none()

        allowed_nodes = RBACService.get_allowed_org_nodes(
            user=self.request.user,
            permission_code=permission_code,
            module_code=permission_code.split(".", 1)[0],
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
