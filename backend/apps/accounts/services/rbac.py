from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import UserRoleAssignment


class RBACService:

    @staticmethod
    def get_active_assignments(user):
        """
        Return all active role assignments for a user.
        """

        if user.is_superuser:
            return UserRoleAssignment.objects.none()

        today = timezone.now().date()

        return (
            UserRoleAssignment.objects
            .select_related("role")
            .prefetch_related("role__permissions")
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

        if user.is_superuser:
            return True

        assignments = RBACService.get_active_assignments(user)

        return assignments.filter(
            role__permissions__code=permission_code
        ).exists()

    @staticmethod
    def get_assignments_for_permission(user,permission_code):
         return RBACService.get_active_assignments(user).filter(
            role__permissions__code=permission_code
        ).distinct()

    @staticmethod
    def get_allowed_org_nodes(user,permission_code):
        assignments = RBACService.get_assignments_for_permission(
            user,
            permission_code,
        )

        # Company-wide access
        if assignments.filter(Q(org_node__isnull=True) | Q(org_node="")).exists():
            return None

        return list(
            assignments.values_list(
                "org_node",
                flat=True,
            ).distinct()
        )