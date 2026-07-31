import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.companies.models import Company


class OrgNode(models.Model):

    NODE_TYPE_CHOICES = [
        ("LEGAL_ENTITY", "Legal Entity"),
        ("BUSINESS_UNIT", "Business Unit"),
        ("DIVISION", "Division"),
        ("REGION", "Region"),
        ("FACILITY", "Facility"),

    ]    

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="org_nodes",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    name = models.CharField(max_length=255)
    node_type = models.CharField(max_length=30, choices=NODE_TYPE_CHOICES)
    node_code = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True)
    ownership_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    operational_control = models.BooleanField(default=True)
    financial_control = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["company__company_name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                name="unique_org_node_name_per_company",
            ),
            models.UniqueConstraint(
                fields=["company", "node_code"],
                name="unique_org_node_code_per_company",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "name"]),
            models.Index(fields=["company", "node_type"]),
            models.Index(fields=["parent"]),
        ]

    def clean(self):
        if self.parent_id is None:
            return

        if self.parent_id == self.id:
            raise ValidationError({"parent": "A node cannot be its own parent."})

        if self.parent.company_id != self.company_id:
            raise ValidationError({"parent": "Parent and child must belong to the same company."})

        ancestor = self.parent
        while ancestor is not None:
            if ancestor.id == self.id:
                raise ValidationError({"parent": "Circular organization hierarchy is not allowed."})
            ancestor = ancestor.parent

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.company.company_name} - {self.name}"
