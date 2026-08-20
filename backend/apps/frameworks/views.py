from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasRolePermission
from apps.accounts.viewsets import RBACModelViewSet

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


class FrameworkCatalogModelViewSet(RBACModelViewSet):
    """
    Base ViewSet for M7 framework/catalog APIs.

    Read operations:
        Any authenticated user.

    Administrative operations:
        Require the canonical platform capability:

            framework_mapping.manage
    """

    permission_code = "framework_mapping.manage"

    def get_permissions(self):
        """
        Authenticated users can consume framework/catalog data.

        Administrative changes require the canonical
        framework_mapping.manage capability.
        """

        if self.action in {
            "create",
            "update",
            "partial_update",
            "destroy",
        }:
            return [
                IsAuthenticated(),
                HasRolePermission(),
            ]

        return [
            IsAuthenticated(),
        ]

    def get_required_permission(self):
        """
        Return the canonical administrative capability.

        This intentionally avoids deriving permissions such as:

            framework.view
            framework.create
            framework_version.view
            framework_node.create

        because those permissions are not part of the
        stabilized M7 RBAC vocabulary.
        """

        return self.permission_code


class FrameworkViewSet(FrameworkCatalogModelViewSet):
    """
    Framework CRUD API.

    Read:
        Authenticated users.

    Create/update/delete:
        framework_mapping.manage.
    """

    serializer_class = FrameworkSerializer

    queryset = Framework.objects.all()

    def get_queryset(self):
        queryset = (
            Framework.objects
            .all()
            .order_by("code")
        )

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


class FrameworkVersionViewSet(
    FrameworkCatalogModelViewSet
):
    """
    Framework version CRUD API.

    Read:
        Authenticated users.

    Create/update/delete:
        framework_mapping.manage.
    """

    serializer_class = FrameworkVersionSerializer

    queryset = (
        FrameworkVersion.objects
        .select_related("framework")
    )

    def get_queryset(self):
        queryset = (
            FrameworkVersion.objects
            .select_related("framework")
            .order_by(
                "framework__code",
                "version_code",
            )
        )

        framework_id = self.request.query_params.get(
            "framework"
        )

        is_active = self.request.query_params.get(
            "is_active"
        )

        is_default = self.request.query_params.get(
            "is_default"
        )

        search = self.request.query_params.get(
            "search"
        )

        if framework_id:
            queryset = queryset.filter(
                framework_id=framework_id
            )

        if is_active is not None:
            queryset = queryset.filter(
                is_active=is_active.lower() == "true"
            )

        if is_default is not None:
            queryset = queryset.filter(
                is_default=is_default.lower() == "true"
            )

        if search:
            queryset = queryset.filter(
                Q(version_code__icontains=search)
                | Q(version_name__icontains=search)
            )

        return queryset


class FrameworkNodeViewSet(
    FrameworkCatalogModelViewSet
):
    """
    Framework node CRUD API.

    Read:
        Authenticated users.

    Create/update/delete:
        framework_mapping.manage.
    """

    serializer_class = FrameworkNodeSerializer

    queryset = (
        FrameworkNode.objects
        .select_related(
            "framework_version",
            "parent",
        )
    )

    def get_queryset(self):
        queryset = (
            FrameworkNode.objects
            .select_related(
                "framework_version",
                "parent",
            )
            .order_by(
                "framework_version",
                "path",
                "display_order",
                "code",
            )
        )

        framework_version = (
            self.request.query_params.get(
                "framework_version"
            )
        )

        code = (
            self.request.query_params.get(
                "code"
            )
        )

        node_type = (
            self.request.query_params.get(
                "node_type"
            )
        )

        is_active = (
            self.request.query_params.get(
                "is_active"
            )
        )

        if framework_version:
            queryset = queryset.filter(
                framework_version_id=framework_version
            )

        if code:
            queryset = queryset.filter(
                code__icontains=code
            )

        if node_type:
            queryset = queryset.filter(
                node_type=node_type
            )

        if is_active is not None:
            queryset = queryset.filter(
                is_active=is_active.lower() == "true"
            )

        return queryset


class FrameworkTreeView(APIView):
    """
    Retrieve the complete framework tree for one
    framework version.

    Read access:
        Any authenticated user.

    No administrative RBAC capability is required
    for reading the framework tree.
    """

    permission_classes = (
        IsAuthenticated,
    )

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

        # Deterministic sibling ordering.
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
                    "id": str(
                        version.framework.id
                    ),
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


class DatapointMappingViewSet(
    FrameworkCatalogModelViewSet
):
    """
    Framework-node to canonical-datapoint mapping
    CRUD API.

    Read:
        Authenticated users.

    Create/update/delete:
        framework_mapping.manage.
    """

    serializer_class = (
        DatapointMappingSerializer
    )

    queryset = (
        DatapointMapping.objects
        .select_related(
            "framework_node",
            "framework_node__framework_version",
            "datapoint",
        )
    )

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

        framework_node = (
            self.request.query_params.get(
                "framework_node"
            )
        )

        framework_version = (
            self.request.query_params.get(
                "framework_version"
            )
        )

        datapoint = (
            self.request.query_params.get(
                "datapoint"
            )
        )

        mapping_type = (
            self.request.query_params.get(
                "mapping_type"
            )
        )

        confidence = (
            self.request.query_params.get(
                "confidence"
            )
        )

        is_primary = (
            self.request.query_params.get(
                "is_primary"
            )
        )

        if framework_node:
            queryset = queryset.filter(
                framework_node_id=framework_node
            )

        if framework_version:
            queryset = queryset.filter(
                framework_node__framework_version_id=(
                    framework_version
                )
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

        if is_primary is not None:
            queryset = queryset.filter(
                is_primary=is_primary.lower() == "true"
            )

        return queryset