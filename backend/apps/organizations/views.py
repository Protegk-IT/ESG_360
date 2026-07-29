from rest_framework import viewsets

from .models import Department, Facility, Organization
from .serializers import DepartmentSerializer, FacilitySerializer, OrganizationSerializer


class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.select_related('company', 'parent_organization', 'country', 'state', 'city').all()
    serializer_class = OrganizationSerializer


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.select_related('organization', 'parent_department').all()
    serializer_class = DepartmentSerializer


class FacilityViewSet(viewsets.ModelViewSet):
    queryset = Facility.objects.select_related('organization', 'department', 'country', 'state', 'city').all()
    serializer_class = FacilitySerializer
