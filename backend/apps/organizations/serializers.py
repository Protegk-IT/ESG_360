from rest_framework import serializers

from .models import Department, Facility, Organization


class OrganizationSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.company_name', read_only=True)
    parent_organization_name = serializers.CharField(source='parent_organization.name', read_only=True)

    class Meta:
        model = Organization
        fields = [
            'id',
            'company',
            'company_name',
            'name',
            'organization_code',
            'parent_organization',
            'parent_organization_name',
            'country',
            'state',
            'city',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class DepartmentSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    parent_department_name = serializers.CharField(source='parent_department.name', read_only=True)

    class Meta:
        model = Department
        fields = [
            'id',
            'organization',
            'organization_name',
            'name',
            'department_code',
            'parent_department',
            'parent_department_name',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class FacilitySerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = Facility
        fields = [
            'id',
            'organization',
            'organization_name',
            'department',
            'department_name',
            'name',
            'facility_code',
            'facility_type',
            'country',
            'state',
            'city',
            'address',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
