from django.core.exceptions import ValidationError
from django.db import models
from apps.core.models import BaseModel


class Framework(BaseModel):
    """
    Represents a reporting framework / standard.

    Examples:
        GRI
        BRSR
        GHG Protocol
    """

    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Stable machine-readable framework code.",
    )

    name = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    is_enabled = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "frameworks"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class FrameworkVersion(BaseModel):
    """
    Represents a specific edition/version of a framework.

    Examples:
        GRI 2021
        BRSR 2023
    """

    framework = models.ForeignKey(
        Framework,
        on_delete=models.PROTECT,
        related_name="versions",
    )

    version_code = models.CharField(
        max_length=100,
        help_text="Stable version identifier.",
    )

    version_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    effective_from = models.DateField(
        null=True,
        blank=True,
    )

    effective_to = models.DateField(
        null=True,
        blank=True,
    )

    published_at = models.DateField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    is_default = models.BooleanField(
        default=False,
    )

    class Meta:
        db_table = "framework_versions"

        ordering = [
            "framework__code",
            "version_code",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["framework", "version_code"],
                name="uq_framework_version_code",
            ),
        ]

    def __str__(self):
        return f"{self.framework.code} - {self.version_code}"




class FrameworkNode(BaseModel):
    """
    Represents a node in a framework hierarchy.

    Example:

        GRI 2021
            └── Topic Standards
                    └── GRI 300
                            └── GRI 302
                                    └── 302-1
    """

    class NodeType(models.TextChoices):
        SECTION = "SECTION", "Section"
        SUBSECTION = "SUBSECTION", "Subsection"
        DISCLOSURE = "DISCLOSURE", "Disclosure"
        INDICATOR = "INDICATOR", "Indicator"
        SUBINDICATOR = "SUBINDICATOR", "Subindicator"

    framework_version = models.ForeignKey(
        FrameworkVersion,
        on_delete=models.PROTECT,
        related_name="nodes",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="children",
        null=True,
        blank=True,
    )

    code = models.CharField(
        max_length=150,
    )

    title = models.CharField(
        max_length=500,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    instructions = models.TextField(
        blank=True,
        default="",
    )

    node_type = models.CharField(
        max_length=30,
        choices=NodeType.choices,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    depth = models.PositiveIntegerField(
        default=0,
        editable=False,
    )

    path = models.TextField(
        blank=True,
        editable=False,
    )

    response_format = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    is_answerable = models.BooleanField(
        default=False,
    )

    is_core = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "framework_nodes"

        ordering = [
            "framework_version",
            "path",
            "display_order",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "framework_version",
                    "code",
                ],
                name="uq_framework_node_code_per_version",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "framework_version",
                    "parent",
                ],
                name="idx_fw_node_parent",
            ),
            models.Index(
                fields=[
                    "framework_version",
                    "display_order",
                ],
                name="idx_fw_node_order",
            ),
            models.Index(
                fields=["path"],
                name="idx_fw_node_path",
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.title}"

    def clean(self):
        super().clean()

        if self.parent is None:
            return

        # Prevent self-parent.
        if self.parent_id == self.id:
            raise ValidationError(
                {
                    "parent": (
                        "A framework node cannot be its own parent."
                    )
                }
            )

        # Parent must belong to same framework version.
        if (
            self.framework_version_id
            and self.parent.framework_version_id
            != self.framework_version_id
        ):
            raise ValidationError(
                {
                    "parent": (
                        "Parent node must belong to the same "
                        "framework version."
                    )
                }
            )

        # Cycle detection.
        ancestor = self.parent
        visited = set()

        while ancestor is not None:

            if ancestor.pk in visited:
                raise ValidationError(
                    {
                        "parent": (
                            "Invalid cyclic framework hierarchy detected."
                        )
                    }
                )

            visited.add(ancestor.pk)

            if ancestor.pk == self.pk:
                raise ValidationError(
                    {
                        "parent": (
                            "A node cannot be moved below "
                            "one of its descendants."
                        )
                    }
                )

            ancestor = ancestor.parent

    def calculate_tree_metadata(self):
        """
        Calculate depth and materialized path.
        """

        if self.parent is None:
            self.depth = 0
            self.path = f"/{self.code}/"
            return

        self.depth = self.parent.depth + 1
        self.path = f"{self.parent.path}{self.code}/"

    def save(self, *args, **kwargs):
        self.full_clean()
        self.calculate_tree_metadata()
        super().save(*args, **kwargs)




'''
 class DatapointMapping(BaseModel):
    """
    Connects an M7 framework node to the canonical M4 Datapoint.

    M7 does not duplicate or redefine Datapoint.
    """

    class MappingType(models.TextChoices):
        DIRECT = "DIRECT", "Direct"
        CALCULATED = "CALCULATED", "Calculated"

    class Aggregation(models.TextChoices):
        NONE = "NONE", "None"
        SUM = "SUM", "Sum"
        AVG = "AVG", "Average"
        LATEST = "LATEST", "Latest"
        COUNT = "COUNT", "Count"

    class Confidence(models.TextChoices):
        CONFIRMED = "CONFIRMED", "Confirmed"
        PROVISIONAL = "PROVISIONAL", "Provisional"

    framework_node = models.ForeignKey(
        FrameworkNode,
        on_delete=models.PROTECT,
        related_name="datapoint_mappings",
    )

    datapoint = models.ForeignKey(
        "datapoints.Datapoint",
        on_delete=models.PROTECT,
        related_name="framework_mappings",
    )

    mapping_type = models.CharField(
        max_length=30,
        choices=MappingType.choices,
        default=MappingType.DIRECT,
    )

    aggregation = models.CharField(
        max_length=20,
        choices=Aggregation.choices,
        default=Aggregation.NONE,
    )

    transform_expression = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Optional future transformation metadata. "
            "Not executed by M7."
        ),
    )

    is_primary = models.BooleanField(
        default=False,
    )

    confidence = models.CharField(
        max_length=20,
        choices=Confidence.choices,
        default=Confidence.PROVISIONAL,
    )

    mapping_note = models.TextField(
        blank=True,
        default="",
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "datapoint_mappings"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "framework_node",
                    "datapoint",
                ],
                name="uq_framework_node_datapoint",
            ),
        ]

        indexes = [
            models.Index(
                fields=["framework_node"],
                name="idx_mapping_framework_node",
            ),
            models.Index(
                fields=["datapoint"],
                name="idx_mapping_datapoint",
            ),
            models.Index(
                fields=["confidence"],
                name="idx_mapping_confidence",
            ),
        ]

    def __str__(self):
        return (
            f"{self.framework_node.code} -> "
            f"{self.datapoint.code}"
        )

    def clean(self):
        super().clean()

        if not self.framework_node_id:
            return

        if not self.datapoint_id:
            return

        # Only active canonical datapoints may be mapped.
        if not self.datapoint.is_active:
            raise ValidationError(
                {
                    "datapoint": (
                        "Only active datapoints can be mapped "
                        "to framework nodes."
                    )
                }
            )

        

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
'''
    



       