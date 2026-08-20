from rest_framework import serializers

from apps.core.serializers import ValidatedModelSerializer

from .models import (
    UnitFamily,
    Unit,
    DatapointCategory,
    Datapoint,
    DatapointOption,
    DatapointTableColumn,
    DatapointTableRow,
)


class UnitFamilySerializer(ValidatedModelSerializer):
    class Meta:
        model = UnitFamily
        fields = [
            "id",
            "code",
            "name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

class UnitSerializer(ValidatedModelSerializer):
    class Meta:
        model = Unit
        fields = [
            "id",
            "family",
            "code",
            "name",
            "factor_to_base",
            "is_base_unit",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]    


class DatapointCategorySerializer(ValidatedModelSerializer):
    class Meta:
        model = DatapointCategory
        fields = [
            "id",
            "code",
            "name",
            "description",
            "module",
            "esg_pillar",
            "display_order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]  

class DatapointOptionSerializer(ValidatedModelSerializer):
    class Meta:
        model = DatapointOption
        fields = [
            "id",
            "datapoint",
            "code",
            "label",
            "display_order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ] 


class DatapointTableColumnSerializer(ValidatedModelSerializer):
    class Meta:
        model = DatapointTableColumn
        fields = [
            "id",
            "datapoint",
            "code",
            "label",
            "data_type",
            "unit_family",
            "default_unit",
            "is_required",
            "validation_metadata",
            "display_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class DatapointTableRowSerializer(ValidatedModelSerializer):
    class Meta:
        model = DatapointTableRow
        fields = [
            "id",
            "datapoint",
            "code",
            "label",
            "display_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class DatapointSerializer(ValidatedModelSerializer):
    class Meta:
        model = Datapoint
        fields = [
            "id",
            "code",
            "category",
            "module",
            "label",
            "description",
            "data_type",
            "unit_family",
            "default_unit",
            "collection_level",
            "frequency",
            "is_required",
            "allow_dynamic_rows",
            "validation_metadata",
            "display_order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

###########################################
###### DATAPOINT DETAILED SERIALIZERS #####
###########################################
class DatapointDetailSerializer(ValidatedModelSerializer):
    category = DatapointCategorySerializer(read_only=True)
    unit_family = UnitFamilySerializer(read_only=True)
    default_unit = UnitSerializer(read_only=True)

    options = DatapointOptionSerializer(
        many=True,
        read_only=True,
    )

    table_columns = DatapointTableColumnSerializer(
        many=True,
        read_only=True,
    )

    table_rows = DatapointTableRowSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Datapoint
        fields = [
            "id",
            "code",
            "category",
            "module",
            "label",
            "description",
            "data_type",
            "unit_family",
            "default_unit",
            "collection_level",
            "frequency",
            "is_required",
            "allow_dynamic_rows",
            "validation_metadata",
            "display_order",
            "is_active",
            "options",
            "table_columns",
            "table_rows",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields