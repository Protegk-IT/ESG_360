from rest_framework import viewsets

from .models import City, Company, Country, Department, State, UserDepartment
from .serializers import CitySerializer, CompanySerializer, CountrySerializer, DepartmentSerializer, StateSerializer, UserDepartmentSerializer


class CountryViewSet(viewsets.ModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer


class StateViewSet(viewsets.ModelViewSet):
    queryset = State.objects.select_related('country').all()
    serializer_class = StateSerializer


class CityViewSet(viewsets.ModelViewSet):
    queryset = City.objects.select_related('country', 'state').all()
    serializer_class = CitySerializer


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.select_related('billing_country', 'billing_state', 'billing_city').all()
    serializer_class = CompanySerializer


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.select_related('company').all()
    serializer_class = DepartmentSerializer


class UserDepartmentViewSet(viewsets.ModelViewSet):
    queryset = UserDepartment.objects.select_related('company').all()
    serializer_class = UserDepartmentSerializer
