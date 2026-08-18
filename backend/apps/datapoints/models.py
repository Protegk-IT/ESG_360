from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel
from apps.modules.models import ESGPillar

##### unit family model #######

class UnitFamily(BaseModel):
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Stable machine-readable unit family code.",
    )

    name = models.CharField(
        max_length=100,
    )

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.name} ({self.code})"



## UNIT model ######

class Unit(BaseModel):
    family = models.ForeignKey(
        UnitFamily,
        on_delete=models.PROTECT,
        related_name="units",
    )

    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Stable machine-readable unit code.",
    )

    name = models.CharField(
        max_length=100,
    )

    factor_to_base = models.DecimalField(
        max_digits=20,
        decimal_places=10,
        help_text="Multiplication factor used to convert this unit to the family base unit.",
    )

    is_base_unit = models.BooleanField(
        default=False,
        help_text="Whether this is the base unit for its unit family.",
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["family", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["family"],
                condition=models.Q(is_base_unit=True),
                name="unique_unit_per_family",
            ),
        ]

    def clean(self):
        super().clean()

        if self.factor_to_base <= Decimal("0"):
            raise ValidationError(
                {
                    "factor_to_base": "Conversion factor must be greater than zero."
                }
            )
        if self.is_base_unit and self.factor_to_base != Decimal("1"):
            raise ValidationError(
                {
                    "factor_to_base": (
                        "The base unit conversion factor must be exactly 1."
                    )
                }
            )
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)   

    def __str__(self):
        return f"{self.name} ({self.code})"
    


### Datapoint Category model ######

class DatapointCategory(BaseModel):
    code = models.CharField(
        max_length=100,
        unique=True,
        help_text="Stable machine-readable category code.",
    )

    name = models.CharField(
        max_length=150,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    module = models.ForeignKey(
        "modules.Module",
        on_delete=models.PROTECT,
        related_name="datapoint_categories",
        to_field="code",
        db_column="module_code",
    )

    esg_pillar = models.CharField(
        max_length=10,
        choices=ESGPillar.choices,
        blank=True,
        null=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return f"{self.name} ({self.code})"    
    



##### Datapoint text choices ######
class DatapointDataType(models.TextChoices):
    DECIMAL = "DECIMAL", "Decimal"
    INTEGER = "INTEGER", "Integer"
    TEXT = "TEXT", "Text"
    LONG_TEXT = "LONG_TEXT", "Long Text"
    BOOLEAN = "BOOLEAN", "Boolean"
    SELECT = "SELECT", "Select"
    DATE = "DATE", "Date"
    TABLE = "TABLE", "Table"


class CollectionLevel(models.TextChoices):
    COMPANY = "COMPANY", "Company"
    ORG_NODE = "ORG_NODE", "Org Node"
    FACILITY = "FACILITY", "Facility"
    ANY = "ANY", "Any"


class CollectionFrequency(models.TextChoices):
    MONTHLY = "MONTHLY", "Monthly"
    QUARTERLY = "QUARTERLY", "Quarterly"
    ANNUAL = "ANNUAL", "Annual"



##### Datapoint model ######
class Datapoint(BaseModel):
    code = models.CharField(
        max_length=200,
        unique=True,
    )

    category = models.ForeignKey(
        DatapointCategory,
        on_delete=models.PROTECT,
        related_name="datapoints",
    )

    module = models.ForeignKey(
        "modules.Module",
        on_delete=models.PROTECT,
        related_name="datapoints",
        to_field="code",
        db_column="module_code",
    )

    label = models.CharField(
        max_length=500,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    data_type = models.CharField(
        max_length=20,
        choices=DatapointDataType.choices,
    )

    unit_family = models.ForeignKey(
        UnitFamily,
        on_delete=models.PROTECT,
        related_name="datapoints",
        null=True,
        blank=True,
    )

    default_unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="default_datapoints",
        null=True,
        blank=True,
    )

    collection_level = models.CharField(
        max_length=20,
        choices=CollectionLevel.choices,
    )

    frequency = models.CharField(
        max_length=20,
        choices=CollectionFrequency.choices,
    )

    is_required = models.BooleanField(
        default=False,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["display_order", "code"]

    def clean(self):
        super().clean()

        if self.default_unit_id and not self.unit_family_id:
            raise ValidationError(
                {
                    "default_unit": "Default unit requires a unit family."
                }
            )

        if (
            self.default_unit_id
            and self.unit_family_id
            and self.default_unit.family_id != self.unit_family_id
        ):
            raise ValidationError(
                {
                    "default_unit": (
                        "Default unit must belong to the selected unit family."
                    )
                }
            )

        if self.unit_family_id and self.data_type not in {
            DatapointDataType.DECIMAL,
            DatapointDataType.INTEGER,
        }:
            raise ValidationError(
                {
                    "unit_family": (
                        "Unit family can only be used with DECIMAL or INTEGER datapoints."
                    )
                }
            )
        
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)        

    def __str__(self):
        return f"{self.code} - {self.label}"
    

##### Datapoint Option model ######

class DatapointOption(BaseModel):
    datapoint = models.ForeignKey(
        Datapoint,
        on_delete=models.CASCADE,
        related_name="options",
    )

    code = models.CharField(
        max_length=100,
    )

    label = models.CharField(
        max_length=255,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["display_order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["datapoint", "code"],
                name="unique_datapoint_option_code",
            ),
        ]

    def clean(self):
        super().clean()

        if self.datapoint_id and self.datapoint.data_type != DatapointDataType.SELECT:
            raise ValidationError(
                {
                    "datapoint": (
                        "Datapoint options can only be defined "
                        "for SELECT datapoints."
                    )
                }
            )
        
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.datapoint.code} - {self.label}"    
    


##### Datapoint Table Column model ######
class DatapointTableColumn(BaseModel):
    datapoint = models.ForeignKey(
        Datapoint,
        on_delete=models.CASCADE,
        related_name="table_columns",
    )

    code = models.CharField(
        max_length=100,
    )

    label = models.CharField(
        max_length=255,
    )

    data_type = models.CharField(
        max_length=20,
        choices=DatapointDataType.choices,
    )

    unit_family = models.ForeignKey(
        UnitFamily,
        on_delete=models.PROTECT,
        related_name="table_columns",
        null=True,
        blank=True,
    )

    default_unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="default_table_columns",
        null=True,
        blank=True,
    )

    is_required = models.BooleanField(
        default=False,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = ["display_order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["datapoint", "code"],
                name="unique_table_column_code",
            ),
            models.UniqueConstraint(
                fields=["datapoint", "display_order"],
                name="unique_table_column_order",
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.datapoint_id
            and self.datapoint.data_type != DatapointDataType.TABLE
        ):
            raise ValidationError(
                {
                    "datapoint": (
                        "Table columns can only be defined "
                        "for TABLE datapoints."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.datapoint.code} - {self.label}"    
    


##### Datapoint Table row model ######  

class DatapointTableRow(BaseModel):
    datapoint = models.ForeignKey(
        Datapoint,
        on_delete=models.CASCADE,
        related_name="table_rows",
    )

    code = models.CharField(
        max_length=100,
    )

    label = models.CharField(
        max_length=255,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = ["display_order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["datapoint", "code"],
                name="unique_table_row_code",
            ),
            models.UniqueConstraint(
                fields=["datapoint", "display_order"],
                name="unique_table_row_order",
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.datapoint_id
            and self.datapoint.data_type != DatapointDataType.TABLE
        ):
            raise ValidationError(
                {
                    "datapoint": (
                        "Table rows can only be defined "
                        "for TABLE datapoints."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.datapoint.code} - {self.label}"  