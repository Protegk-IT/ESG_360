from decimal import Decimal

from rest_framework import serializers

from apps.calculations.models import (
    CalculationRule,
    EmissionFactor,
    EmissionFactorSource,
)
from apps.calculations.services.calculations import CalculationService
from apps.datapoints.models import Unit


class EmissionFactorSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmissionFactorSource
        fields = [
            "id",
            "code",
            "name",
            "publisher",
            "version",
            "source_reference",
            "publication_date",
            "effective_from",
            "effective_to",
            "source_url",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class EmissionFactorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmissionFactor
        fields = [
            "id",
            "code",
            "source",
            "activity_key",
            "input_unit",
            "output_unit",
            "factor_value",
            "geography",
            "effective_from",
            "effective_to",
            "is_active",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate_factor_value(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError(
                "Emission factor value must be greater than zero."
            )

        return value



class CalculationRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalculationRule
        fields = [
            "id",
            "code",
            "name",
            "description",
            "datapoint",
            "rule_metadata",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate_rule_metadata(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "Rule metadata must be a JSON object."
            )

        return value


class CalculationPreviewSerializer(serializers.Serializer):
    quantity = serializers.DecimalField(
        max_digits=30,
        decimal_places=15,
    )

    quantity_unit = serializers.PrimaryKeyRelatedField(
        queryset=Unit.objects.filter(is_active=True),
    )

    factor = serializers.PrimaryKeyRelatedField(
        queryset=EmissionFactor.objects.filter(
            is_active=True,
        ),
    )

    calculation_date = serializers.DateField()

    geography = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def validate_quantity(self, value):
        if value < Decimal("0"):
            raise serializers.ValidationError(
                "Quantity cannot be negative."
            )

        return value

    def validate(self, attrs):
        quantity_unit = attrs["quantity_unit"]
        factor = attrs["factor"]

        if quantity_unit.family_id != factor.input_unit.family_id:
            raise serializers.ValidationError(
                {
                    "quantity_unit": (
                        "Quantity unit is not compatible with "
                        "the emission factor input unit family."
                    )
                }
            )

        return attrs

    def calculate(self):
        return CalculationService.calculate(
            quantity=self.validated_data["quantity"],
            quantity_unit=self.validated_data["quantity_unit"],
            factor=self.validated_data["factor"],
            calculation_date=self.validated_data["calculation_date"],
            geography=self.validated_data.get("geography") or None,
        )