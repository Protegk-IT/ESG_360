from rest_framework import serializers

from .models import OrgNode


class OrgNodeSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.company_name", read_only=True)
    parent_name = serializers.CharField(source="parent.name", read_only=True)

    country_name = serializers.CharField(source="country.name", read_only=True)
    state_name = serializers.CharField(source="state.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)

    children_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = OrgNode
        fields = [
            "id",

            "company",
            "company_name",

            "parent",
            "parent_name",

            "node_type",
            "code",
            "name",

            "depth",
            "path",

            "facility_type",
            "address",
            "grid_region",
            "water_stressed_area",
            "latitude",
            "longitude",

            "country",
            "country_name",

            "state",
            "state_name",

            "city",
            "city_name",

            "ownership_percentage",
            "operational_control",
            "consolidation_method",

            "commissioned_on",
            "decommissioned_on",

            "is_active",

            "created_at",
            "updated_at",

            "children_count",
        ]

        read_only_fields = [
            "depth",
            "path",
            "created_at",
            "updated_at",
            "children_count",
        ]


class OrgTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = OrgNode
        fields = [
            "id",
            "code",
            "name",
            "node_type",
            "depth",
            "is_active",
            "children",
        ]

    def get_children(self, obj):
        children = (
            obj.children
            .filter(is_active=True)
            .order_by("name")
        )

        return OrgTreeSerializer(children, many=True).data