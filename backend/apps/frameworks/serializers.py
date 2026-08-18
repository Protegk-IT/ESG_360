from rest_framework import serializers

from apps.frameworks.models import (
    Framework,
    FrameworkNode,
    FrameworkVersion,
    DatapointMapping,
)


class FrameworkSerializer(serializers.ModelSerializer):

    class Meta:
        model = Framework
        fields = [
            "id",
            "code",
            "name",
            "description",
            "is_enabled",
            "created_at",
            "updated_at",
        ]


class FrameworkVersionSerializer(serializers.ModelSerializer):

    framework_code = serializers.CharField(
        source="framework.code",
        read_only=True,
    )

    class Meta:
        model = FrameworkVersion
        fields = [
            "id",
            "framework",
            "framework_code",
            "version_code",
            "version_name",
            "effective_from",
            "effective_to",
            "published_at",
            "is_active",
            "is_default",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "created_at",
            "updated_at",
            "framework_code",
        ]


class FrameworkNodeSerializer(serializers.ModelSerializer):

    parent_code = serializers.CharField(
        source="parent.code",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = FrameworkNode

        fields = [
            "id",
            "framework_version",
            "parent",
            "parent_code",
            "code",
            "title",
            "description",
            "instructions",
            "node_type",
            "display_order",
            "depth",
            "path",
            "response_format",
            "is_answerable",
            "is_core",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "depth",
            "path",
            "created_at",
            "updated_at",
            "parent_code",
        ]


class FrameworkTreeNodeSerializer(serializers.ModelSerializer):

    children = serializers.SerializerMethodField()

    class Meta:
        model = FrameworkNode

        fields = [
            "id",
            "code",
            "title",
            "description",
            "instructions",
            "node_type",
            "display_order",
            "depth",
            "path",
            "response_format",
            "is_answerable",
            "is_core",
            "is_active",
            "children",
        ]

    def get_children(self, obj):
        children_map = self.context.get(
            "children_map",
            {},
        )

        children = children_map.get(
            obj.pk,
            [],
        )

        return FrameworkTreeNodeSerializer(
            children,
            many=True,
            context=self.context,
        ).data


class DatapointMappingSerializer(serializers.ModelSerializer):
    framework_node_code = serializers.CharField(
        source="framework_node.code",
        read_only=True,
    )

    datapoint_code = serializers.CharField(
        source="datapoint.code",
        read_only=True,
    )

    datapoint_label = serializers.CharField(
        source="datapoint.label",
        read_only=True,
    )

    datapoint_data_type = serializers.CharField(
        source="datapoint.data_type",
        read_only=True,
    )

    class Meta:
        model = DatapointMapping

        fields = [
            "id",
            "framework_node",
            "framework_node_code",
            "datapoint",
            "datapoint_code",
            "datapoint_label",
            "datapoint_data_type",
            "mapping_type",
            "aggregation",
            "transform_expression",
            "is_primary",
            "confidence",
            "mapping_note",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "framework_node_code",
            "datapoint_code",
            "datapoint_label",
            "datapoint_data_type",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        mapping_type = attrs.get(
            "mapping_type",
            DatapointMapping.MappingType.DIRECT,
        )

        aggregation = attrs.get(
            "aggregation",
            DatapointMapping.Aggregation.NONE,
        )

        if (
            mapping_type == DatapointMapping.MappingType.DIRECT
            and aggregation != DatapointMapping.Aggregation.NONE
        ):
            raise serializers.ValidationError(
                {
                    "aggregation": (
                        "Direct mappings cannot use aggregation."
                    )
                }
            )

        return attrs
    