from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from .models import City, Company, Country, Department, State, UserDepartment


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
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)
    class Meta:
        model = Company
        fields = [
            'id',
            'company_logo',
            'company_code',
            'company_name',
            'gst_number',
            'cin_number',
            'date_of_incorporation',
            'about_company',
            'password',
            'company_password_hash',
            'billing_address',
            'billing_zip_code',
            'billing_country',
            'billing_state',
            'billing_city',
            'contact_person',
            'email',
            'mobile_number',
            'website',
            'listed_company',
            'last_login',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'company_password_hash']

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        if password:
            validated_data["company_password_hash"] = make_password(password)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        if password:
            validated_data["company_password_hash"] = make_password(password)
        return super().update(instance, validated_data)


class DepartmentSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.company_name", read_only=True)
    class Meta:
        model = Department
        fields = [
            "id",
            "company",
            "company_name",
            "name",
            "department_code",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class UserDepartmentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = UserDepartment
        fields = [
            "id",
            "user",
            "username",
            "department",
            "department_name",
            "is_primary",
            "created_at",
        ]
        read_only_fields = ["created_at"]

    def validate(self, attrs):
        user = attrs.get("user", getattr(self.instance, "user", None))
        department = attrs.get("department", getattr(self.instance, "department", None))
        is_primary = attrs.get("is_primary", getattr(self.instance, "is_primary", False))

        if user and department and is_primary:
            existing_primary = UserDepartment.objects.filter(
                user=user,
                department__company=department.company,
                is_primary=True,
            )
            if self.instance:
                existing_primary = existing_primary.exclude(pk=self.instance.pk)

            if existing_primary.exists():
                raise serializers.ValidationError(
                    {"is_primary": "User already has a primary department for this company."}
                )

        return attrs
