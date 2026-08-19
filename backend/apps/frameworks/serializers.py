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

        read_only_fields = [
            "created_at",
            "updated_at",
        ]


class FrameworkVersionSerializer(
    serializers.ModelSerializer
):
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

    def validate(self, attrs):
        """
        Prevent changing stable version identity once
        an existing version is active.
        """

        if self.instance and self.instance.is_active:
            if (
                "framework" in attrs
                and attrs["framework"].pk
                != self.instance.framework_id
            ):
                raise serializers.ValidationError(
                    {
                        "framework": (
                            "The framework of an active "
                            "version cannot be changed."
                        )
                    }
                )

            if (
                "version_code" in attrs
                and attrs["version_code"]
                != self.instance.version_code
            ):
                raise serializers.ValidationError(
                    {
                        "version_code": (
                            "The version code of an active "
                            "framework version cannot be changed."
                        )
                    }
                )

        return attrs


class FrameworkNodeSerializer(
    serializers.ModelSerializer
):
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

    def validate(self, attrs):
        parent = attrs.get(
            "parent",
            getattr(self.instance, "parent", None),
        )

        framework_version = attrs.get(
            "framework_version",
            getattr(
                self.instance,
                "framework_version",
                None,
            ),
        )

        if parent and self.instance:
            if parent.pk == self.instance.pk:
                raise serializers.ValidationError(
                    {
                        "parent": (
                            "A framework node cannot be "
                            "its own parent."
                        )
                    }
                )

        if parent and framework_version:
            if (
                parent.framework_version_id
                != framework_version.pk
            ):
                raise serializers.ValidationError(
                    {
                        "parent": (
                            "Parent node must belong to the "
                            "same framework version."
                        )
                    }
                )

        return attrs


class FrameworkTreeNodeSerializer(
    serializers.ModelSerializer
):
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


class DatapointMappingSerializer(
    serializers.ModelSerializer
):
    framework_node_code = serializers.CharField(
        source="framework_node.code",
        read_only=True,
    )

    framework_version_id = serializers.UUIDField(
        source="framework_node.framework_version_id",
        read_only=True,
    )

    framework_version_code = serializers.CharField(
        source="framework_node.framework_version.version_code",
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
            "framework_version_id",
            "framework_version_code",
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
            "framework_version_id",
            "framework_version_code",
            "datapoint_code",
            "datapoint_label",
            "datapoint_data_type",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        mapping_type = attrs.get(
            "mapping_type",
            getattr(
                self.instance,
                "mapping_type",
                DatapointMapping.MappingType.DIRECT,
            ),
        )

        aggregation = attrs.get(
            "aggregation",
            getattr(
                self.instance,
                "aggregation",
                DatapointMapping.Aggregation.NONE,
            ),
        )

        framework_node = attrs.get(
            "framework_node",
            getattr(
                self.instance,
                "framework_node",
                None,
            ),
        )

        datapoint = attrs.get(
            "datapoint",
            getattr(
                self.instance,
                "datapoint",
                None,
            ),
        )

        if framework_node and not framework_node.is_active:
            raise serializers.ValidationError(
                {
                    "framework_node": (
                        "Only active framework nodes can "
                        "have datapoint mappings."
                    )
                }
            )

        if datapoint and not datapoint.is_active:
            raise serializers.ValidationError(
                {
                    "datapoint": (
                        "Only active datapoints can be mapped."
                    )
                }
            )

        if (
            mapping_type
            == DatapointMapping.MappingType.DIRECT
            and aggregation
            != DatapointMapping.Aggregation.NONE
        ):
            raise serializers.ValidationError(
                {
                    "aggregation": (
                        "Direct mappings cannot use aggregation."
                    )
                }
            )

        if (
            mapping_type
            == DatapointMapping.MappingType.NARRATIVE
            and aggregation
            != DatapointMapping.Aggregation.NONE
        ):
            raise serializers.ValidationError(
                {
                    "aggregation": (
                        "Narrative mappings cannot use aggregation."
                    )
                }
            )

        return attrs
