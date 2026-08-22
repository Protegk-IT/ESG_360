from apps.core.models import BaseModel
from django.core.exceptions import ValidationError
from django.db import models

from decimal import Decimal
from apps.datapoints.models import Unit



class EmissionFactorSource(BaseModel):
    """
    Represents the provenance and version context for
    a group of emission factors.
    """

    code = models.CharField(
        max_length=100,
        help_text="Stable machine-readable source/factor-set code.",
    )

    name = models.CharField(
        max_length=255,
        help_text="Human-readable name of the factor source or set.",
    )

    publisher = models.CharField(
        max_length=255,
        help_text="Organization or authority that published the source.",
    )

    version = models.CharField(
        max_length=100,
        help_text="Source or factor-set version.",
    )

    source_reference = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Publication, document, dataset, or reference identifier.",
    )

    publication_date = models.DateField(
        null=True,
        blank=True,
    )

    effective_from = models.DateField(
        null=True,
        blank=True,
    )

    effective_to = models.DateField(
        null=True,
        blank=True,
    )

    source_url = models.URLField(
        blank=True,
        default="",
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["code", "version"]
        constraints = [
            models.UniqueConstraint(
                fields=["code", "version"],
                name="unique_emission_factor_source_version",
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.effective_from
            and self.effective_to
            and self.effective_to < self.effective_from
        ):
            raise ValidationError(
                {
                    "effective_to": (
                        "Effective end date cannot be earlier "
                        "than the effective start date."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.version})"
    


class EmissionFactor(BaseModel):
    """
    Reusable emission factor definition.

    Factors belong to a versioned/provenanced source and use
    the canonical M4 Unit registry for their input/output units.
    """

    code = models.CharField(
        max_length=150,
        help_text="Stable machine-readable emission factor code.",
    )

    source = models.ForeignKey(
        "EmissionFactorSource",
        on_delete=models.PROTECT,
        related_name="factors",
    )

    activity_key = models.CharField(
        max_length=150,
        help_text=(
            "Stable key identifying the activity or factor category "
            "for which this factor applies."
        ),
    )

    input_unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="emission_factor_inputs",
        help_text="Canonical M4 unit in which the activity quantity is supplied.",
    )

    output_unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="emission_factor_outputs",
        help_text="Canonical M4 unit produced by the factor calculation.",
    )

    factor_value = models.DecimalField(
        max_digits=30,
        decimal_places=15,
        help_text="Decimal-safe emission factor value.",
    )

    geography = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text=(
            "Optional geography/applicability identifier used during "
            "factor selection."
        ),
    )

    effective_from = models.DateField(
        null=True,
        blank=True,
    )

    effective_to = models.DateField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    notes = models.TextField(
        blank=True,
        default="",
        help_text="Traceability or source-specific notes.",
    )

    class Meta:
        ordering = ["code"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "source",
                    "code",
                ],
                name="unique_factor_code_per_source",
            ),
        ]

    def clean(self):
        super().clean()

        # Factor values must be positive.
        if self.factor_value <= Decimal("0"):
            raise ValidationError(
                {
                    "factor_value": (
                        "Emission factor value must be greater than zero."
                    )
                }
            )

        # Effective date range must be valid.
        if (
            self.effective_from
            and self.effective_to
            and self.effective_to < self.effective_from
        ):
            raise ValidationError(
                {
                    "effective_to": (
                        "Effective end date cannot be earlier "
                        "than the effective start date."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.factor_value}"
    


class CalculationRule(BaseModel):
    """
    Declarative calculation rule used by the M6 calculation service.

    The rule stores configuration/metadata only. It must never contain
    executable Python code or arbitrary expressions.
    """

    code = models.CharField(
        max_length=150,
        unique=True,
        help_text="Stable machine-readable calculation rule code.",
    )

    name = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    datapoint = models.ForeignKey(
        "datapoints.Datapoint",
        on_delete=models.PROTECT,
        related_name="calculation_rules",
        null=True,
        blank=True,
        help_text="Optional M4 datapoint to which this calculation rule applies.",
    )

    rule_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Declarative calculation configuration. "
            "Must contain metadata only and must not execute arbitrary code."
        ),
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["code"]

    def clean(self):
        super().clean()

        if not isinstance(self.rule_metadata, dict):
            raise ValidationError(
                {
                    "rule_metadata": (
                        "Rule metadata must be a JSON object."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"
