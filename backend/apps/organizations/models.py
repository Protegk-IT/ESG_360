import uuid

from django.db import models

from apps.companies.models import Company, Country, State, City


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='organizations',
    )
    name = models.CharField(max_length=255)
    organization_code = models.CharField(max_length=50, unique=True)
    parent_organization = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_organizations',
    )
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True, related_name='organizations')
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True, related_name='organizations')
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, related_name='organizations')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='departments',
    )
    name = models.CharField(max_length=255)
    department_code = models.CharField(max_length=50, unique=True)
    parent_department = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_departments',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Facility(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='facilities',
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='facilities',
    )
    name = models.CharField(max_length=255)
    facility_code = models.CharField(max_length=50, unique=True)
    facility_type = models.CharField(max_length=100, blank=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True, related_name='facilities')
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True, related_name='facilities')
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, related_name='facilities')
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
