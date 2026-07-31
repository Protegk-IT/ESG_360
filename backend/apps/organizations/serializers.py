from rest_framework import serializers

from .models import OrgNode


class OrgNodeSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.company_name", read_only=True)
    parent_name = serializers.CharField(source="parent.name", read_only=True)
    children_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = OrgNode
        fields = [
            "id",
            "name",
            "node_type",
            "node_code",
            "company",
            "company_name",
            "parent",
            "parent_name",
            "description",
            "ownership_percentage",
            "operational_control",
            "financial_control",
            "is_active",
            "created_at",
            "updated_at",
            "children_count",
        ]
        read_only_fields = ["created_at", "updated_at", "children_count"]

    def validate(self, attrs):
        instance = self.instance
        company = attrs.get("company", getattr(instance, "company", None))
        parent = attrs.get("parent", getattr(instance, "parent", None))

        if parent and company and parent.company_id != company.id:
            raise serializers.ValidationError(
                {"parent": "Parent and child must belong to the same company."}
            )

        if instance and parent:
            if parent.id == instance.id:
                raise serializers.ValidationError({"parent": "A node cannot be its own parent."})

            ancestor = parent
            while ancestor is not None:
                if ancestor.id == instance.id:
                    raise serializers.ValidationError(
                        {"parent": "Circular organization hierarchy is not allowed."}
                    )
                ancestor = ancestor.parent

        return attrs
