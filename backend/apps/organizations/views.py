from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from django.db import transaction
from django.core.exceptions import ValidationError
from apps.accounts.viewsets import RBACModelViewSet
from apps.accounts.services.rbac import RBACService

from .models import OrgNode
from .serializers import OrgNodeSerializer, OrgTreeSerializer


class OrgNodeViewSet(RBACModelViewSet):
    module_code = "organization"
    scope_field = "id"
    serializer_class = OrgNodeSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "company",
        "node_type",
        "parent",
        "is_active",
    ]

    search_fields = [
        "name",
        "code",
    ]

    ordering_fields = [
        "name",
        "depth",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "depth",
        "name",
    ]

    def get_queryset(self):
        queryset = (
            OrgNode.objects.select_related(
                "company",
                "parent",
                "country",
                "state",
                "city",
            ).annotate(
                children_count=Count("children")
            )
        )
        return self.get_scoped_queryset(queryset)

    def get_required_permission(self):
        # Map custom actions to permissions
        if self.action in ("tree", "subtree", "ancestors"):
            return f"{self.module_code}.view"
        if self.action == "move":
            return f"{self.module_code}.edit"
        return super().get_required_permission()

    def _ensure_write_scope(self, node):
        """Do not let a permitted writer choose a parent outside that role's scope."""
        permission_code = self.get_required_permission()
        allowed_nodes = RBACService.get_allowed_org_nodes(
            self.request.user,
            permission_code,
            module_code=self.module_code,
        )
        if allowed_nodes is not None and (node is None or node.id not in allowed_nodes):
            raise NotFound("Organization node not found.")

    def perform_create(self, serializer):
        # A scoped role may create only beneath a node covered by its *create*
        # assignment. Creating a root requires company-wide scope.
        self._ensure_write_scope(serializer.validated_data.get("parent"))
        serializer.save()

    def perform_update(self, serializer):
        # ``get_object`` already scopes the edited node. Validate a new parent
        # too so moving a node cannot cross into another role's scope.
        if "parent" in serializer.validated_data:
            self._ensure_write_scope(serializer.validated_data["parent"])
        serializer.save()

    @action(detail=False, methods=["get"])
    def tree(self, request):
        """
        Returns the complete organization tree.
        For now, returns all root nodes.
        Later this can use a dedicated recursive serializer.
        """
        queryset = self.get_queryset().filter(parent__isnull=True, is_active=True)
        serializer = OrgTreeSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def subtree(self, request, pk=None):
        """
        Returns this node and all its descendants.
        """
        node = self.get_object()

        queryset = self.get_queryset().filter(
            path__startswith=node.path
        )

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def ancestors(self, request, pk=None):
        """
        Returns all ancestors of the current node.
        """
        node = self.get_object()

        ancestors = []

        current = node.parent

        while current:
            ancestors.insert(0, current)
            current = current.parent

        ancestors = self.get_queryset().filter(pk__in=[ancestor.pk for ancestor in ancestors])
        serializer = self.get_serializer(ancestors, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def move(self, request, pk=None):
        """
        Moves a node to another parent.
        """

        node = self.get_object()

        parent_id = request.data.get("parent_id")

        if not parent_id:
            return Response(
                {"parent_id": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_parent = OrgNode.objects.get(pk=parent_id)
        except OrgNode.DoesNotExist:
            return Response(
                {"parent_id": "Invalid parent node."},
                status=status.HTTP_404_NOT_FOUND,
            )

        self._ensure_write_scope(new_parent)

        with transaction.atomic():
            try:
                node.parent = new_parent
                node.save()
                # node.update_subtree_paths()
            except ValidationError as e:
                return Response(
                    e.message_dict,
                    status=status.HTTP_400_BAD_REQUEST,
                )
        serializer = self.get_serializer(node)
        return Response(serializer.data)
