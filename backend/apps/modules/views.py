from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Module
from .serializers import ModuleSerializer


class ModuleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ModuleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Module.objects.all()

        enabled = self.request.query_params.get("enabled")

        if enabled == "true":
            queryset = queryset.filter(is_enabled=True)
        elif enabled == "false":
            queryset = queryset.filter(is_enabled=False)

        return queryset