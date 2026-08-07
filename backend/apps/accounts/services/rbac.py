from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import UserRoleAssignment
from apps.organizations.models import OrgNode


class RBACService:
    """
    Central RBAC service.

    Responsibilities:
    - Resolve active role assignments.
    - Check permissions.
    - Resolve organisation scope.
    """

    @staticmethod
    def get_active_assignments(user):
        """
        Returns all active role assignments for the user
        whose validity period includes today.
        """

        if user.is_superuser:
            return UserRoleAssignment.objects.none()

        today = timezone.now().date()

        return (
            UserRoleAssignment.objects
            .select_related(
                "role",
                "org_node",
            )
            .prefetch_related(
                "role__permissions",
            )
            .filter(
                user=user,
                is_active=True,
            )
            .filter(
                Q(valid_from__isnull=True) | Q(valid_from__lte=today),
                Q(valid_to__isnull=True) | Q(valid_to__gte=today),
            )
        )

    @staticmethod
    def has_permission(user, permission_code):
        """
        Returns True if user has the permission
        through any active role assignment.
        """

        if user.is_superuser:
            return True

        return RBACService.get_active_assignments(user).filter(
            role__permissions__code=permission_code
        ).exists()

    @staticmethod
    def get_assignments_for_permission(
        user,
        permission_code,
        module_code=None,
        framework_code=None,
    ):
        """
        Returns only assignments that grant
        the requested permission.
        """

        assignments = (
            RBACService.get_active_assignments(user)
            .filter(
                role__permissions__code=permission_code
            )
            .distinct()
        )

        # Module restriction
        if module_code:
            assignments = assignments.filter(
                Q(module_code__isnull=True) |
                Q(module_code=module_code)
            )

        # Framework restriction
        if framework_code:
            assignments = assignments.filter(
                Q(framework_code__isnull=True) |
                Q(framework_code=framework_code)
            )

        return assignments

    @staticmethod
    def get_allowed_org_nodes(
        user,
        permission_code,
        module_code=None,
        framework_code=None,
    ):
        """
        Returns:

        None
            -> Company-wide access

        []
            -> No access

        [uuid1, uuid2, ...]
            -> OrgNodes user can access
               including descendants.
        """

        if user.is_superuser:
            return None

        assignments = RBACService.get_assignments_for_permission(
            user=user,
            permission_code=permission_code,
            module_code=module_code,
            framework_code=framework_code,
        )

        if not assignments.exists():
            return []

        # Company-wide assignment
        if assignments.filter(
            org_node__isnull=True
        ).exists():
            return None

        query = Q()

        for assignment in assignments:

            node = assignment.org_node

            query |= Q(
                path__startswith=node.path
            )

        return list(
            OrgNode.objects.filter(query)
            .values_list(
                "id",
                flat=True,
            )
        )