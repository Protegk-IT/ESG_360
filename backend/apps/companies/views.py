from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import City, Company, Country, Department, State
from .serializers import CitySerializer, CompanySerializer, CountrySerializer, DepartmentSerializer, StateSerializer
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.viewsets import RBACModelViewSet

class CountryViewSet(RBACModelViewSet):
    module_code = "country"
    queryset = Country.objects.all()
    serializer_class = CountrySerializer


class StateViewSet(RBACModelViewSet):
    module_code = "state"
    queryset = State.objects.select_related('country')
    serializer_class = StateSerializer
    filter_backends = [DjangoFilterBackend]  ##frontend can do filtering GET /api/company/states/?country=<country_uuid>
    filterset_fields = ["country"]


class CityViewSet(RBACModelViewSet):
    module_code = "city"
    queryset = City.objects.select_related(
        "country",
        "state",
    )
    serializer_class = CitySerializer
    filter_backends = [DjangoFilterBackend]  ##frontend  can do filtering GET /api/company/cities/?state=<state_uuid>
    filterset_fields = ["country","state"]  

class CompanyViewSet(RBACModelViewSet):
    module_code = "company"
    queryset = Company.objects.select_related(
        "country",
        "state",
        "city",
    )
    serializer_class = CompanySerializer

    def get_required_permission(self):
        # Map custom 'profile' action to view/edit depending on HTTP method
        if self.action == "profile":
            # GET -> view, PATCH/PUT -> edit
            method = getattr(self, 'request', None).method if hasattr(self, 'request') else None
            if method in ("PATCH", "PUT"):
                return f"{self.module_code}.edit"
            return f"{self.module_code}.view"
        return super().get_required_permission()

    @action(detail=False, methods=["get", "patch"], url_path="profile")
    def profile(self, request):
        company = self.get_queryset().first()

        if not company:
            return Response(
                {"detail": "Company profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if request.method == "GET":
            serializer = self.get_serializer(company)
            return Response(serializer.data)

        serializer = self.get_serializer(
            company,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)


class DepartmentViewSet(RBACModelViewSet):
    module_code = "department"
    queryset = Department.objects.select_related(
        "company",
        "parent_department",
    )
    serializer_class = DepartmentSerializer
