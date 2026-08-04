from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from .models import City, Company, Country, Department, State


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['id', 'name', 'iso_code', 'is_active']


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ['id', 'country', 'name', 'state_code', 'is_active']


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['id', 'country', 'state', 'name', 'is_active']


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            "id",
            "company_logo",
            "company_code",
            "company_name",
            "about_company",
            "date_of_incorporation",

            "cin_number",
            "gst_number",
            "listed_company",
            "stock_exchanges",
            "paid_up_capital",
            "turnover",
            "ownership_form",

            "registered_address",
            "corporate_address",

            "country",
            "state",
            "city",

            "contact_person",
            "email",
            "mobile_number",
            "website",

            "employee_count",
            "financial_year_start_month",

            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "created_at",
            "updated_at",
        ]

class DepartmentSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.company_name", read_only=True)
    parent_department_name = serializers.CharField(source="parent_department.name", read_only=True)

    class Meta:
        model = Department
        fields = [
            "id",

            "company",
            "company_name",

            "parent_department",
            "parent_department_name",

            "name",
            "code",
            "description",

            "is_active",

            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "created_at",
            "updated_at",
        ]