from rest_framework import serializers

from apps.frameworks.models import (
    Framework,
    FrameworkNode,
    FrameworkVersion,
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