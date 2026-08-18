from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.frameworks.models import (
    Framework,
    FrameworkNode,
    FrameworkVersion,
    DatapointMapping,
)

from apps.frameworks.serializers import (
    FrameworkSerializer,
    FrameworkNodeSerializer,
    FrameworkTreeNodeSerializer,
    FrameworkVersionSerializer,
    DatapointMappingSerializer,
    
)


class FrameworkListCreateView(
    generics.ListCreateAPIView
):
    """
    GET:
        List frameworks.

    POST:
        Create a framework.

    Authentication:
        Authenticated users only.

    RBAC:
        Not implemented yet.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = FrameworkSerializer

    def get_queryset(self):
        queryset = Framework.objects.all()

        is_enabled = self.request.query_params.get(
            "is_enabled"
        )

        search = self.request.query_params.get(
            "search"
        )

        if is_enabled is not None:
            queryset = queryset.filter(
                is_enabled=is_enabled.lower() == "true"
            )

        if search:
            queryset = queryset.filter(
                Q(code__icontains=search)
                | Q(name__icontains=search)
            )

        return queryset


class FrameworkDetailView(
    generics.RetrieveUpdateAPIView
):
    """
    Retrieve or update a framework.

    Authentication:
        Authenticated users only.

    RBAC:
        Not implemented yet.
    """

    permission_classes = [IsAuthenticated]

    queryset = Framework.objects.all()

    serializer_class = FrameworkSerializer


class FrameworkVersionListView(
    generics.ListCreateAPIView
):
    """
    List or create versions belonging to a framework.

    Authentication:
        Authenticated users only.

    RBAC:
        Not implemented yet.
    """

    permission_classes = [IsAuthenticated]

    serializer_class = FrameworkVersionSerializer

    def get_queryset(self):
        return (
            FrameworkVersion.objects
            .filter(
                framework_id=self.kwargs["framework_id"]
            )
            .select_related("framework")
        )

    def perform_create(self, serializer):
        framework = get_object_or_404(
            Framework,
            pk=self.kwargs["framework_id"],
        )

        serializer.save(
            framework=framework
        )


class FrameworkVersionDetailView(
    generics.RetrieveUpdateAPIView
):
    """
    Retrieve or update a framework version.

    Authentication:
        Authenticated users only.

    RBAC:
        Not implemented yet.
    """

    permission_classes = [IsAuthenticated]

    queryset = (
        FrameworkVersion.objects
        .select_related("framework")
    )

    serializer_class = FrameworkVersionSerializer


class FrameworkNodeDetailView(
    generics.RetrieveAPIView
):
    """
    Retrieve a framework node.

    Authentication:
        Authenticated users only.

    RBAC:
        Not implemented yet.
    """

    permission_classes = [IsAuthenticated]

    queryset = (
        FrameworkNode.objects
        .select_related(
            "framework_version",
            "parent",
        )
    )

    serializer_class = FrameworkNodeSerializer


class FrameworkVersionTreeView(APIView):
    """
    Return the complete framework tree for a version.

    One HTTP request returns the complete hierarchy.

    Authentication:
        Authenticated users only.

    RBAC:
        Not implemented yet.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, version_id):

        version = get_object_or_404(
            FrameworkVersion.objects.select_related(
                "framework"
            ),
            pk=version_id,
        )

        nodes = list(
            FrameworkNode.objects
            .filter(
                framework_version_id=version.id,
                is_active=True,
            )
            .select_related("parent")
            .order_by(
                "display_order",
                "code",
            )
        )

        children_map = {}

        for node in nodes:
            children_map.setdefault(
                node.parent_id,
                [],
            ).append(node)

        # Ensure deterministic sibling ordering.
        for children in children_map.values():
            children.sort(
                key=lambda node: (
                    node.display_order,
                    node.code,
                )
            )

        roots = children_map.get(
            None,
            [],
        )

        serializer = FrameworkTreeNodeSerializer(
            roots,
            many=True,
            context={
                "request": request,
                "children_map": children_map,
            },
        )

        return Response(
            {
                "framework": {
                    "id": str(version.framework.id),
                    "code": version.framework.code,
                    "name": version.framework.name,
                },
                "version": {
                    "id": str(version.id),
                    "code": version.version_code,
                    "name": version.version_name,
                },
                "tree": serializer.data,
            }
        )

class DatapointMappingListCreateView(
    generics.ListCreateAPIView
):
    """
    List or create datapoint mappings.

    Query parameters:
        framework_node
        datapoint
        mapping_type
        confidence
    """

    permission_classes = [IsAuthenticated]

    serializer_class = DatapointMappingSerializer

    def get_queryset(self):
        queryset = (
            DatapointMapping.objects
            .select_related(
                "framework_node",
                "framework_node__framework_version",
                "datapoint",
            )
            .order_by(
                "framework_node__path",
                "datapoint__code",
            )
        )

        framework_node = self.request.query_params.get(
            "framework_node"
        )

        datapoint = self.request.query_params.get(
            "datapoint"
        )

        mapping_type = self.request.query_params.get(
            "mapping_type"
        )

        confidence = self.request.query_params.get(
            "confidence"
        )

        if framework_node:
            queryset = queryset.filter(
                framework_node_id=framework_node
            )

        if datapoint:
            queryset = queryset.filter(
                datapoint_id=datapoint
            )

        if mapping_type:
            queryset = queryset.filter(
                mapping_type=mapping_type
            )

        if confidence:
            queryset = queryset.filter(
                confidence=confidence
            )

        return queryset


class DatapointMappingDetailView(
    generics.RetrieveUpdateDestroyAPIView
):
    """
    Retrieve, update or delete a datapoint mapping.
    """

    permission_classes = [IsAuthenticated]

    queryset = (
        DatapointMapping.objects
        .select_related(
            "framework_node",
            "framework_node__framework_version",
            "datapoint",
        )
    )

    serializer_class = DatapointMappingSerializer    