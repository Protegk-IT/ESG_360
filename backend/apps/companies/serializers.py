from rest_framework import serializers

from .models import City, Company, Country, State


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
            'id',
            'company_logo',
            'company_code',
            'company_name',
            'gst_number',
            'cin_number',
            'date_of_incorporation',
            'about_company',
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
        read_only_fields = ['created_at', 'updated_at']
