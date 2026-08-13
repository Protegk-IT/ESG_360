from rest_framework import serializers

from .models import Module


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = [
            "id",
            "code",
            "name",
            "description",
            "esg_pillar",
            "icon",
            "is_core",
            "is_enabled",
            "display_order",
        ]
        read_only_fields = ["id"]