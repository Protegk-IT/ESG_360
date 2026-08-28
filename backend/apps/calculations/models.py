from apps.core.models import BaseModel
from django.core.exceptions import ValidationError
from django.db import models

from decimal import Decimal
from apps.datapoints.models import Unit
from django.conf import settings



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

    M6 defines the structure of rule metadata, but does not define
    a fixed list of calculation operations at this stage.

    Example:

    {
        "operation": "multiply",
        "input": "activity_quantity",
        "factor": "emission_factor"
    }

    The metadata is configuration only. It must not contain
    executable code, arbitrary expressions, or unsafe instructions.
    """

    # Fields that define the supported M6 metadata shape.
    RULE_METADATA_FIELDS = {
        "operation",
        "input",
        "factor",
        "activity_key",
    }

    # Fields that would indicate executable or expression-based
    # configuration and are therefore not allowed.
    FORBIDDEN_METADATA_FIELDS = {
        "expression",
        "formula",
        "python",
        "eval",
        "code",
    }

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
            "Declarative calculation-rule metadata. "
            "Must contain operation, input and factor as strings. "
            "Must not contain executable code or arbitrary expressions."
        ),
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["code"]

    def clean(self):
        super().clean()

        metadata = self.rule_metadata

        # -----------------------------------------------
        # 1. Metadata must be a JSON object
        # -----------------------------------------------

        if not isinstance(metadata, dict):
            raise ValidationError(
                {
                    "rule_metadata": (
                        "Rule metadata must be a JSON object."
                    )
                }
            )

        # -----------------------------------------------
        # 2. Required fields
        # -----------------------------------------------

        missing_fields = (
            self.RULE_METADATA_FIELDS - metadata.keys()
        )

        if missing_fields:
            raise ValidationError(
                {
                    "rule_metadata": (
                        "Missing required rule metadata fields: "
                        + ", ".join(sorted(missing_fields))
                    )
                }
            )

        # -----------------------------------------------
        # 3. Field types
        # -----------------------------------------------

        for field in self.RULE_METADATA_FIELDS:
            if not isinstance(metadata[field], str):
                raise ValidationError(
                    {
                        "rule_metadata": (
                            f"The '{field}' field must be a string."
                        )
                    }
                )

        # -----------------------------------------------
        # 4. Reject executable/expression configuration
        # -----------------------------------------------

        forbidden_fields = (
            self.FORBIDDEN_METADATA_FIELDS
            & metadata.keys()
        )

        if forbidden_fields:
            raise ValidationError(
                {
                    "rule_metadata": (
                        "Executable or expression-style "
                        "configuration is not supported: "
                        + ", ".join(sorted(forbidden_fields))
                    )
                }
            )

        # -----------------------------------------------
        # 5. Reject undefined extra fields
        # -----------------------------------------------

        extra_fields = (
            metadata.keys() - self.RULE_METADATA_FIELDS
        )

        if extra_fields:
            raise ValidationError(
                {
                    "rule_metadata": (
                        "Unsupported rule metadata fields: "
                        + ", ".join(sorted(extra_fields))
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"


class CalculationResultStatus(models.TextChoices):
    CURRENT = "CURRENT", "Current"
    SUPERSEDED = "SUPERSEDED", "Superseded"


class CalculationResult(BaseModel):
    """
    Persisted M6 calculation result and immutable calculation provenance.

    This model stores a snapshot of the inputs and factor information used
    for a calculation so that historical results remain auditable even if
    the live M6 factor or rule is changed later.
    """

    # ------------------------------------------------------------------
    # SOURCE M5 CONTEXT
    # ------------------------------------------------------------------

    answer = models.ForeignKey(
        "data_capture.Answer",
        on_delete=models.PROTECT,
        related_name="calculation_results",
        help_text="Approved M5 Answer used as the calculation input.",
    )

    submission = models.ForeignKey(
        "data_capture.Submission",
        on_delete=models.PROTECT,
        related_name="calculation_results",
        help_text="M5 Submission containing the source Answer.",
    )

    data_request = models.ForeignKey(
        "data_capture.DataRequest",
        on_delete=models.PROTECT,
        related_name="calculation_results",
        help_text="M5 DataRequest associated with the calculation.",
    )

    # ------------------------------------------------------------------
    # CANONICAL M4 / ORGANIZATION CONTEXT
    # ------------------------------------------------------------------

    datapoint = models.ForeignKey(
        "datapoints.Datapoint",
        on_delete=models.PROTECT,
        related_name="calculation_results",
    )

    org_node = models.ForeignKey(
        "organizations.OrgNode",
        on_delete=models.PROTECT,
        related_name="calculation_results",
    )

    reporting_period = models.ForeignKey(
        "periods.ReportingPeriod",
        on_delete=models.PROTECT,
        related_name="calculation_results",
    )

    # ------------------------------------------------------------------
    # CALCULATION RULE
    # ------------------------------------------------------------------

    calculation_rule = models.ForeignKey(
        CalculationRule,
        on_delete=models.PROTECT,
        related_name="calculation_results",
    )

    calculation_rule_code = models.CharField(
        max_length=150,
        help_text="Snapshot of the calculation rule code used.",
    )

    calculation_rule_name = models.CharField(
        max_length=200,
        help_text="Snapshot of the calculation rule name used.",
    )

    calculation_rule_metadata = models.JSONField(
        help_text="Snapshot of the calculation rule metadata used.",
    )

    # ------------------------------------------------------------------
    # SELECTED FACTOR
    # ------------------------------------------------------------------

    emission_factor = models.ForeignKey(
        EmissionFactor,
        on_delete=models.PROTECT,
        related_name="calculation_results",
    )

    # ------------------------------------------------------------------
    # INPUT SNAPSHOT
    # ------------------------------------------------------------------

    input_quantity = models.DecimalField(
        max_digits=30,
        decimal_places=15,
        help_text="Original numeric quantity captured in the approved Answer.",
    )

    input_unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="calculation_result_inputs",
    )

    input_unit_code = models.CharField(
        max_length=100,
        help_text="Snapshot of the factor input unit code used for normalization.",
    )

    input_unit_name = models.CharField(
        max_length=255,
        help_text="Snapshot of the factor input unit name used for normalization.",
    )

    input_unit_factor_to_base = models.DecimalField(
        max_digits=30,
        decimal_places=15,
        help_text="Snapshot of the input unit conversion factor used for normalization.",
    )

    factor_input_unit_code = models.CharField(
        max_length=100,
        help_text="Snapshot of the emission factor input unit code.",
        )

    factor_input_unit_name = models.CharField(
        max_length=255,
        help_text="Snapshot of the emission factor input unit name.",
        )

    factor_input_unit_factor_to_base = models.DecimalField(
        max_digits=30,
        decimal_places=15,
        help_text="Snapshot of the emission factor input unit conversion factor.",
        )

    normalized_quantity = models.DecimalField(
        max_digits=30,
        decimal_places=15,
        help_text="Input quantity normalized to the factor input unit.",
    )

    # ------------------------------------------------------------------
    # FACTOR / SOURCE SNAPSHOT
    # ------------------------------------------------------------------

    factor_value = models.DecimalField(
        max_digits=30,
        decimal_places=15,
        help_text="Exact factor value used by this calculation.",
    )

    factor_source_code = models.CharField(
        max_length=100,
        help_text="Snapshot of the factor source code.",
    )

    factor_source_name = models.CharField(
        max_length=255,
        help_text="Snapshot of the factor source name.",
    )

    factor_source_version = models.CharField(
        max_length=100,
        help_text="Snapshot of the factor source version.",
    )

    factor_source_reference = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Snapshot of the factor source reference.",
    )

    factor_code = models.CharField(
        max_length=150,
        help_text="Snapshot of the selected emission factor code.",
    )

    # ------------------------------------------------------------------
    # CALCULATION CONTEXT SNAPSHOT
    # ------------------------------------------------------------------

    activity_key = models.CharField(
        max_length=150,
        help_text="Activity key used during factor selection.",
    )

    geography = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Geography used during factor selection.",
    )

    calculation_date = models.DateField(
        help_text="Date used for factor applicability.",
    )

    # ------------------------------------------------------------------
    # RESULT
    # ------------------------------------------------------------------

    calculated_value = models.DecimalField(
        max_digits=30,
        decimal_places=15,
        help_text="Calculated Decimal-safe result.",
    )

    output_unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="calculation_result_outputs",
    )

    output_unit_code = models.CharField(
        max_length=100,
        help_text="Snapshot of the output unit code used.",
    )

    output_unit_name = models.CharField(
        max_length=255,
        help_text="Snapshot of the output unit name used.",
    )

    # ------------------------------------------------------------------
    # VERSION / LIFECYCLE
    # ------------------------------------------------------------------

    status = models.CharField(
        max_length=20,
        choices=CalculationResultStatus.choices,
        default=CalculationResultStatus.CURRENT,
    )

    calculation_version = models.PositiveIntegerField(
        default=1,
        help_text="Version of the calculation for the same approved Answer.",
    )

    calculated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="calculation_results",
    )

    calculated_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-calculated_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "answer",
                    "calculation_version",
                ],
                name="unique_answer_calculation_version",
            ),
        ]

        indexes = [
            models.Index(
                fields=["answer", "status"],
            ),
            models.Index(
                fields=["submission", "status"],
            ),
            models.Index(
                fields=["datapoint", "org_node", "reporting_period"],
            ),
            models.Index(
                fields=["calculation_rule"],
            ),
            models.Index(
                fields=["emission_factor"],
            ),
        ]

    def clean(self):
        super().clean()

        if self.input_quantity < Decimal("0"):
            raise ValidationError(
                {
                    "input_quantity": (
                        "Input quantity cannot be negative."
                    )
                }
            )

        if self.normalized_quantity < Decimal("0"):
            raise ValidationError(
                {
                    "normalized_quantity": (
                        "Normalized quantity cannot be negative."
                    )
                }
            )

        if self.calculated_value < Decimal("0"):
            raise ValidationError(
                {
                    "calculated_value": (
                        "Calculated value cannot be negative."
                    )
                }
            )

        if self.calculation_version < 1:
            raise ValidationError(
                {
                    "calculation_version": (
                        "Calculation version must be at least 1."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.answer_id} - "
            f"v{self.calculation_version} - "
            f"{self.calculated_value}"
        )