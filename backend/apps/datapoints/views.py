from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import HasRolePermission
from apps.accounts.viewsets import RBACModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status


from .models import (
    UnitFamily,
    Unit,
    DatapointCategory,
    Datapoint,
    DatapointOption,
    DatapointTableColumn,
    DatapointTableRow,
    DatapointDataType
)

from .serializers import (
    DatapointDetailSerializer,
    UnitFamilySerializer,
    UnitSerializer,
    DatapointCategorySerializer,
    DatapointSerializer,
    DatapointOptionSerializer,
    DatapointTableColumnSerializer,
    DatapointTableRowSerializer,
)


class CatalogModelViewSet(RBACModelViewSet):
    """
    Base ViewSet for catalog/definition models.

    Catalog data is readable by authenticated users.

    Administrative changes require:
        datapoint.manage
    """

    permission_code = "datapoint.manage"

    def get_permissions(self):
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
        return "datapoint.manage"
    

class UnitFamilyViewSet(CatalogModelViewSet):
    queryset = UnitFamily.objects.all()
    serializer_class = UnitFamilySerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "code",
    ]

    search_fields = [
        "code",
        "name",
    ]

    ordering_fields = [
        "code",
        "name",
    ]

    ordering = [
        "code",
    ]


class UnitViewSet(CatalogModelViewSet):
    queryset = Unit.objects.select_related("family")
    serializer_class = UnitSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "family",
        "is_base_unit",
        "is_active",
    ]

    search_fields = [
        "code",
        "name",
    ]

    ordering_fields = [
        "code",
        "name",
    ]

    ordering = [
        "family",
        "name",
    ]



class DatapointCategoryViewSet(CatalogModelViewSet):
    queryset = DatapointCategory.objects.select_related("module")
    serializer_class = DatapointCategorySerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "module",
        "esg_pillar",
        "is_active",
    ]

    search_fields = [
        "code",
        "name",
    ]

    ordering_fields = [
        "display_order",
        "code",
        "name",
    ]

    ordering = [
        "display_order",
        "name",
    ] 


class DatapointViewSet(CatalogModelViewSet):
    queryset = (
        Datapoint.objects
        .select_related(
            "category",
            "module",
            "unit_family",
            "default_unit",
        )
        .prefetch_related(
            "options",
            "table_columns",
            "table_rows",
        )
    )

    serializer_class = DatapointSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "module",
        "category",
        "data_type",
        "is_active",
        "collection_level",
        "frequency",
        "is_required",
    ]

    search_fields = [
        "code",
        "label",
        "description",
    ]

    ordering_fields = [
        "display_order",
        "code",
        "label",
    ]

    ordering = [
        "display_order",
        "code",
    ]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return DatapointDetailSerializer

        return DatapointSerializer

    @action(detail=True, methods=["get"])
    def options(self, request, pk=None):
        datapoint = self.get_object()

        if datapoint.data_type != DatapointDataType.SELECT:
            return Response(
                {
                    "detail": (
                        "Options are only available "
                        "for SELECT datapoints."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = datapoint.options.filter(is_active=True)

        serializer = DatapointOptionSerializer(
            queryset,
            many=True,
        )

        return Response(serializer.data)

    @action(
        detail=True,
        methods=["get"],
        url_path="table-definition",
    )
    def table_definition(self, request, pk=None):
        datapoint = self.get_object()

        if datapoint.data_type != DatapointDataType.TABLE:
            return Response(
                {
                    "detail": (
                        "Table definition is only available "
                        "for TABLE datapoints."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        columns = datapoint.table_columns.all()
        rows = datapoint.table_rows.all()

        return Response(
            {
                "datapoint": DatapointSerializer(
                    datapoint
                ).data,
                "columns": DatapointTableColumnSerializer(
                    columns,
                    many=True,
                ).data,
                "rows": DatapointTableRowSerializer(
                    rows,
                    many=True,
                ).data,
            }
        ) 

    
     
class DatapointOptionViewSet(CatalogModelViewSet):
    queryset = DatapointOption.objects.select_related(
        "datapoint",
    )
    serializer_class = DatapointOptionSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "datapoint",
        "is_active",
    ]

    search_fields = [
        "code",
        "label",
    ]

    ordering_fields = [
        "display_order",
        "code",
        "label",
    ]

    ordering = [
        "display_order",
        "code",
    ] 



class DatapointTableColumnViewSet(CatalogModelViewSet):
    queryset = DatapointTableColumn.objects.select_related(
        "datapoint",
        "unit_family",
        "default_unit",
    )
    serializer_class = DatapointTableColumnSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "datapoint",
        "data_type",
        "is_required",
    ]

    search_fields = [
        "code",
        "label",
    ]

    ordering_fields = [
        "display_order",
        "code",
        "label",
    ]

    ordering = [
        "display_order",
        "code",
    ]


class DatapointTableRowViewSet(CatalogModelViewSet):
    queryset = DatapointTableRow.objects.select_related(
        "datapoint",
    )
    serializer_class = DatapointTableRowSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "datapoint",
    ]

    search_fields = [
        "code",
        "label",
    ]

    ordering_fields = [
        "display_order",
        "code",
        "label",
    ]

    ordering = [
        "display_order",
        "code",
    ]