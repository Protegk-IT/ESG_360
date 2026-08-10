from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel
from apps.core.mixins import ActivityLogMixin


##### COUNTRY MODEL ########
class Country(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    iso_code = models.CharField(max_length=5, unique=True)  
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Countries"
        indexes = [
            models.Index(fields=['iso_code']),
        ]

    def __str__(self):
        return self.name


######## STATE MODEL ########
class State(BaseModel):
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="states"
    )
    name = models.CharField(max_length=100)
    state_code = models.CharField(max_length=10)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        unique_together = (
            ('country', 'name'),
            ('country', 'state_code'),
        )
        indexes = [
            models.Index(fields=['country']),
            models.Index(fields=['state_code']),
        ]

    def __str__(self):
        return f"{self.name} ({self.country.name})"


######## CITY MODEL ########
class City(BaseModel):
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="cities"
    )
    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="cities"
    )
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        unique_together = (
            ('country', 'state', 'name'),
        )
        indexes = [
            models.Index(fields=['country']),
            models.Index(fields=['state']),
        ]

    def __str__(self):
        return f"{self.name}, {self.state.name}"



######## COMPANY MODEL ########

class Company(ActivityLogMixin, BaseModel):
    # Basic Information
    company_name = models.CharField(max_length=255)
    company_code = models.CharField(max_length=20, unique=True)
    company_logo = models.ImageField(upload_to="company_logos/", blank=True, null=True)
    about_company = models.TextField(blank=True, null=True)
    date_of_incorporation = models.DateField(blank=True, null=True)

    # Legal Information
    cin_number = models.CharField(max_length=50, blank=True, null=True)
    gst_number = models.CharField(max_length=50, blank=True, null=True)
    listed_company = models.BooleanField(default=False)
    stock_exchanges = models.CharField(max_length=255, blank=True, null=True, help_text="Comma separated stock exchanges.")
    paid_up_capital = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    turnover = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    ownership_form = models.CharField(max_length=100, blank=True, null=True, help_text="Private, Public, Government, Partnership, etc.")

    # Addresses
    registered_address = models.TextField(blank=True, null=True)
    corporate_address = models.TextField(blank=True, null=True)

    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True, related_name="companies")
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True, related_name="companies")
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, related_name="companies")

    # Contact Information
    contact_person = models.CharField(max_length=255)
    email = models.EmailField()
    mobile_number = models.CharField(max_length=20)
    website = models.URLField(blank=True, null=True)

    # Reporting Information
    employee_count = models.PositiveIntegerField(default=0)
    financial_year_start_month = models.PositiveSmallIntegerField(default=4, help_text="1=January ... 12=December")

    # Common Fields
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company_name"]
        indexes = [
            models.Index(fields=["company_code"]),
            models.Index(fields=["company_name"]),
            models.Index(fields=["is_active"]),
        ]

    def clean(self):
        if self.city:
            if not self.state:
                raise ValidationError({"state": "State is required when a city is selected."})
            if not self.country:
                raise ValidationError({"country": "Country is required when a city is selected."})
            if self.city.state_id != self.state_id:
                raise ValidationError({"city": "Selected city does not belong to the selected state."})

        if self.state:
            if not self.country:
                raise ValidationError({"country": "Country is required when a state is selected."})
            if self.state.country_id != self.country_id:
                raise ValidationError({"state": "Selected state does not belong to the selected country."})

        if self.financial_year_start_month not in range(1, 13):
            raise ValidationError({"financial_year_start_month": "Month must be between 1 and 12."})
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.company_code} - {self.company_name}"


## DEPARTMENT MODEL 

class Department(ActivityLogMixin, BaseModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="departments",
    )

    parent_department = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="children",
        null=True,
        blank=True,
    )

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company__company_name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["company", "name"], name="unique_department_name_per_company"),
            models.UniqueConstraint(fields=["company", "code"], name="unique_department_code_per_company"),
        ]
        indexes = [
            models.Index(fields=["company"]),
            models.Index(fields=["company", "name"]),
            models.Index(fields=["company", "code"]),
            models.Index(fields=["parent_department"]),
        ]

    def clean(self):
        # Department cannot be its own parent
        if self.parent_department == self:
            raise ValidationError({
                "parent_department": "A department cannot be its own parent."
            })

        # Prevent circular hierarchy
        parent = self.parent_department
        while parent:
            if parent == self:
                raise ValidationError({
                    "parent_department": "Circular department hierarchy is not allowed."
                })
            parent = parent.parent_department

        # Parent must belong to the same company
        if (
            self.parent_department
            and self.parent_department.company_id != self.company_id
        ):
            raise ValidationError({
                "parent_department": "Parent department must belong to the same company."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.company.company_code} - {self.name}"
