from django.core.exceptions import ValidationError
from django.db import models

from apps.companies.models import Company, Country, State, City
from apps.core.mixins import ActivityLogMixin
from apps.core.models import BaseModel


class OrgNode(ActivityLogMixin, BaseModel):

    NODE_TYPE_CHOICES = [
        ("LEGAL_ENTITY", "Legal Entity"),
        ("BUSINESS_UNIT", "Business Unit"),
        ("DIVISION", "Division"),
        ("REGION", "Region"),
        ("FACILITY", "Facility"),
    ]

    CONSOLIDATION_METHOD_CHOICES = [
        ("FULL", "Full"),
        ("PROPORTIONAL", "Proportional"),
        ("EQUITY", "Equity"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="org_nodes")
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children",default=None)

    node_type = models.CharField(max_length=30, choices=NODE_TYPE_CHOICES)
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)

    depth = models.PositiveIntegerField(default=0, editable=False)
    path = models.CharField(max_length=1000, editable=False)

    # Facility fields
    facility_type = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    grid_region = models.CharField(max_length=100, blank=True, null=True)
    water_stressed_area = models.BooleanField(default=False)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    # Location
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True, related_name="org_nodes")
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True, related_name="org_nodes")
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, related_name="org_nodes")

    # Consolidation
    ownership_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    operational_control = models.BooleanField(default=True)
    consolidation_method = models.CharField(max_length=20, choices=CONSOLIDATION_METHOD_CHOICES, default="FULL")

    commissioned_on = models.DateField(blank=True, null=True)
    decommissioned_on = models.DateField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company__company_name", "depth", "name"]

        constraints = [
            models.UniqueConstraint(fields=["company", "code"], name="unique_orgnode_code_per_company"),
        ]

        indexes = [
            models.Index(fields=["company"]),
            models.Index(fields=["parent"]),
            models.Index(fields=["node_type"]),
            models.Index(fields=["path"]),
            models.Index(fields=["depth"]),
            models.Index(fields=["is_active"]),
        ]

    def clean(self):
        # Self-parent validation
        if self.parent_id == self.id:
            raise ValidationError({
                "parent": "A node cannot be its own parent."
            })

        # Parent belongs to same company
        if self.parent and self.parent.company_id != self.company_id:
            raise ValidationError({
                "parent": "Parent and child must belong to the same company."
            })

        # Prevent circular hierarchy
        ancestor = self.parent
        while ancestor:
            if ancestor == self:
                raise ValidationError({
                    "parent": "Circular organization hierarchy is not allowed."
                })
            ancestor = ancestor.parent

        # Only one root LEGAL_ENTITY
        if self.node_type == "LEGAL_ENTITY":
            if self.parent:
                raise ValidationError({
                    "parent": "LEGAL_ENTITY cannot have a parent."
                })

            root = OrgNode.objects.filter(
                company=self.company,
                node_type="LEGAL_ENTITY",
                parent__isnull=True,
            )

            if self.pk:
                root = root.exclude(pk=self.pk)

            if root.exists():
                raise ValidationError({
                    "node_type": "Only one LEGAL_ENTITY root node is allowed per company."
                })

        # FACILITY cannot have children
        if self.parent and self.parent.node_type == "FACILITY":
            raise ValidationError({
                "parent": "A FACILITY node cannot have child nodes."
            })

        # Facility-only fields
        facility_fields = [
            self.facility_type,
            self.address,
            self.grid_region,
            self.latitude,
            self.longitude,
        ]

        if self.node_type != "FACILITY":
            if any(field not in (None, "") for field in facility_fields) or self.water_stressed_area:
                raise ValidationError({
                    "node_type": "Facility-specific fields are only allowed for FACILITY nodes."
                })

        # Location validation
        if self.city:
            if not self.state:
                raise ValidationError({
                    "state": "State is required when city is selected."
                })

            if not self.country:
                raise ValidationError({
                    "country": "Country is required when city is selected."
                })

            if self.city.state_id != self.state_id:
                raise ValidationError({
                    "city": "Selected city does not belong to selected state."
                })

        if self.state:
            if not self.country:
                raise ValidationError({
                    "country": "Country is required when state is selected."
                })

            if self.state.country_id != self.country_id:
                raise ValidationError({
                    "state": "Selected state does not belong to selected country."
                })

        # Commission dates
        if (
            self.commissioned_on
            and self.decommissioned_on
            and self.decommissioned_on < self.commissioned_on
        ):
            raise ValidationError({
                "decommissioned_on": "Decommission date cannot be before commissioned date."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        update_subtree = False
        if self.pk:
            previous = OrgNode.objects.get(pk=self.pk)
            if (
                previous.parent_id != self.parent_id
                or previous.code != self.code
            ):
                update_subtree = True
        if self.parent:
            self.depth = self.parent.depth + 1
            self.path = f"{self.parent.path}{self.code}/"
        else:
            self.depth = 0
            self.path = f"/{self.code}/"
        super().save(*args, **kwargs)

        if update_subtree:
            self.update_subtree_paths()

    def update_subtree_paths(self):
        """
        Recalculate path and depth for all descendants recursively.
        """
        for child in self.children.all():
            child.depth = self.depth + 1
            child.path = f"{self.path}{child.code}/"

            # Save without triggering another subtree update
            super(OrgNode, child).save(update_fields=["depth", "path"])
            child.update_subtree_paths()    

    def __str__(self):
        return f"{self.company.company_code} - {self.name}"