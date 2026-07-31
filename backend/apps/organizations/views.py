from django.db.models import Count
from rest_framework import viewsets

from .models import OrgNode
from .serializers import OrgNodeSerializer


class OrgNodeViewSet(viewsets.ModelViewSet):
    queryset = (
        OrgNode.objects.select_related("company", "parent")
        .annotate(children_count=Count("children"))
        .all()
    )
    serializer_class = OrgNodeSerializer
