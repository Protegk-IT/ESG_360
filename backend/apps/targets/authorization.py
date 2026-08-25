"""Same-assignment RBAC scoping for M10 OrgNode-scoped planning records."""
from apps.accounts.services.rbac import RBACService


def has_target_scope(user, org_node_id):
    allowed = RBACService.get_allowed_org_nodes(user, "target.set", module_code="target")
    return allowed is None or org_node_id in allowed


def scoped_queryset(queryset, user, field="org_node_id"):
    if user.is_superuser:
        return queryset
    allowed = RBACService.get_allowed_org_nodes(user, "target.set", module_code="target")
    if allowed is None:
        return queryset
    return queryset.filter(**{f"{field}__in": allowed})
