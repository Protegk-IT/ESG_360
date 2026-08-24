"""Scoped authorization helpers for M5 request resources.

The resource scope is evaluated alongside each individual permission code.  Do
not collapse a user's roles into a single global org-node set: a role granting
``data.enter`` at Site A must not make ``data.approve`` usable at Site A merely
because another role grants it at Site B.
"""

from django.db.models import Q

from apps.accounts.services.rbac import RBACService


DATA_MODULE = "data"
ENTRY_PERMISSIONS = ("data.enter", "data.submit")
READ_PERMISSIONS = ("data.manage", "data.approve", *ENTRY_PERMISSIONS)


def has_scoped_permission(user, permission_code, org_node_id):
    """Whether one qualifying assignment grants a code for this org node."""

    allowed_nodes = RBACService.get_allowed_org_nodes(
        user,
        permission_code,
        module_code=permission_code.split(".", 1)[0],
    )
    return allowed_nodes is None or org_node_id in allowed_nodes


def permission_scoped_request_queryset(queryset, user, permission_code):
    """Return a request queryset scoped by one capability and its own module."""

    if user.is_superuser:
        return queryset
    allowed_nodes = RBACService.get_allowed_org_nodes(
        user,
        permission_code,
        module_code=permission_code.split(".", 1)[0],
    )
    if allowed_nodes is None:
        return queryset
    return queryset.filter(org_node_id__in=allowed_nodes)


def readable_request_queryset(queryset, user):
    """Scope M5 reads without cross-permission scope union.

    Managers/reviewers can see all requests in the scope of their corresponding
    capability. Capture users can see only requests assigned to themselves in
    the scope of their `data.enter` or `data.submit` assignment.
    """

    if user.is_superuser:
        return queryset

    predicate = Q(pk__in=[])
    for permission_code in ("data.manage", "data.approve"):
        allowed_nodes = RBACService.get_allowed_org_nodes(
            user, permission_code, module_code=DATA_MODULE
        )
        if allowed_nodes is None:
            return queryset
        if allowed_nodes:
            predicate |= Q(org_node_id__in=allowed_nodes)

    for permission_code in ENTRY_PERMISSIONS:
        allowed_nodes = RBACService.get_allowed_org_nodes(
            user, permission_code, module_code=DATA_MODULE
        )
        if allowed_nodes is None:
            predicate |= Q(assignee=user)
        elif allowed_nodes:
            predicate |= Q(assignee=user, org_node_id__in=allowed_nodes)

    return queryset.filter(predicate).distinct()
