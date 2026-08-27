"""Same-assignment RBAC scoping for M10 OrgNode-scoped planning records."""
from django.db.models import Q

from apps.accounts.services.rbac import RBACService
from apps.organizations.models import OrgNode


TARGET_MODULE = "target"
READ_PERMISSIONS = ("target.view", "target.set")


def allowed_nodes(user, permission_code):
    return RBACService.get_allowed_org_nodes(
        user, permission_code, module_code=TARGET_MODULE
    )


def has_target_permission(user, permission_code):
    return RBACService.has_permission(user, permission_code)


def can_read_targets(user):
    return any(has_target_permission(user, code) for code in READ_PERMISSIONS)


def has_company_wide_target_scope(user):
    """Whether one *target.set* assignment is company-wide.

    ``None`` from the RBAC resolver is deliberately significant: it is not
    interchangeable with an empty list, and is the only non-superuser route
    to creating or changing a company-wide (``org_node=None``) target or
    initiative.
    """
    return user.is_superuser or allowed_nodes(user, "target.set") is None


def has_target_scope(user, org_node_id):
    allowed = allowed_nodes(user, "target.set")
    return allowed is None or org_node_id in allowed


def target_set_company_ids(user):
    """Companies represented by the *same* qualifying ``target.set`` scopes.

    ``None`` preserves the existing company-wide/superuser contract. A list
    is derived only from assignments that actually grant ``target.set``;
    another role assignment at a different Company cannot lend its scope.
    """
    allowed = allowed_nodes(user, "target.set")
    if allowed is None:
        return None
    return set(
        OrgNode.objects.filter(pk__in=allowed).values_list("company_id", flat=True)
    )


def write_scoped_queryset(queryset, user, field="org_node_id"):
    if user.is_superuser:
        return queryset
    allowed = allowed_nodes(user, "target.set")
    if allowed is None:
        return queryset
    return queryset.filter(**{f"{field}__in": allowed})


def read_scoped_queryset(queryset, user, field="org_node_id"):
    """Scope reads from each qualifying read assignment independently.

    A user can read where either ``target.view`` or ``target.set`` grants
    access.  This is a union of *read* grants only; writes continue to use
    ``write_scoped_queryset`` and therefore can never inherit a ``target.view``
    scope.
    """
    if user.is_superuser:
        return queryset
    predicate = Q(pk__in=[])
    for permission_code in READ_PERMISSIONS:
        allowed = allowed_nodes(user, permission_code)
        if allowed is None:
            return queryset
        if allowed:
            predicate |= Q(**{f"{field}__in": allowed})
    return queryset.filter(predicate)
