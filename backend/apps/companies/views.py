from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import City, Company, Country, Department, State
from .serializers import CitySerializer, CompanySerializer, CountrySerializer, DepartmentSerializer, StateSerializer
from django_filters.rest_framework import DjangoFilterBackend

class CountryViewSet(viewsets.ModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer


class StateViewSet(viewsets.ModelViewSet):
    queryset = State.objects.select_related('country')
    serializer_class = StateSerializer
    filter_backends = [DjangoFilterBackend]  ##frontend can do filtering GET /api/company/states/?country=<country_uuid>
    filterset_fields = ["country"]


class CityViewSet(viewsets.ModelViewSet):
    queryset = City.objects.select_related(
        "country",
        "state",
    )
    serializer_class = CitySerializer
    filter_backends = [DjangoFilterBackend]  ##frontend  can do filtering GET /api/company/cities/?state=<state_uuid>
    filterset_fileds = ["country","states"]  

class CompanyViewSet(viewsets.GenericViewSet):
    queryset = Company.objects.select_related(
        "country",
        "state",
        "city",
    )
    serializer_class = CompanySerializer

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


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.select_related(
        "company",
        "parent_department",
    )
    serializer_class = DepartmentSerializer

