from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.core.exceptions import ValidationError
from apps.accounts.viewsets import RBACModelViewSet

from .models import OrgNode
from .serializers import OrgNodeSerializer, OrgTreeSerializer


class OrgNodeViewSet(RBACModelViewSet):
    module_code = "org"
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
        return (
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

    def get_required_permission(self):
        # Map custom actions to permissions
        if self.action in ("tree", "subtree", "ancestors"):
            return f"{self.module_code}.view"
        if self.action == "move":
            return f"{self.module_code}.edit"
        return super().get_required_permission()

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