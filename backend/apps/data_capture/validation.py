"""Definition-driven validation shared by M5 models and submission workflow.

This module deliberately accepts an answer-like object plus an M4 datapoint or
table-column definition. It does not own a parallel capture schema.
"""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError

from apps.datapoints.models import DatapointDataType


NUMERIC_TYPES = {DatapointDataType.DECIMAL, DatapointDataType.INTEGER}
VALUE_FIELDS = (
    "decimal_value",
    "integer_value",
    "text_value",
    "boolean_value",
    "selected_option",
    "date_value",
)
VALUE_FIELD_BY_TYPE = {
    DatapointDataType.DECIMAL: "decimal_value",
    DatapointDataType.INTEGER: "integer_value",
    DatapointDataType.TEXT: "text_value",
    DatapointDataType.LONG_TEXT: "text_value",
    DatapointDataType.BOOLEAN: "boolean_value",
    DatapointDataType.SELECT: "selected_option",
    DatapointDataType.DATE: "date_value",
}


def is_present(value):
    """Treat ``False`` and zero as entered values, but blank text as empty."""

    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def expected_value_field(definition):
    return VALUE_FIELD_BY_TYPE.get(definition.data_type)


def _metadata_decimal(metadata, key, errors):
    if key not in metadata:
        return None
    try:
        return Decimal(str(metadata[key]))
    except (InvalidOperation, TypeError, ValueError):
        errors["validation_metadata"] = f"M4 {key} metadata must be numeric."
        return None


def _metadata_non_negative_integer(metadata, key, errors):
    if key not in metadata:
        return None
    try:
        value = int(metadata[key])
    except (TypeError, ValueError):
        errors["validation_metadata"] = f"M4 {key} metadata must be an integer."
        return None
    if value < 0:
        errors["validation_metadata"] = f"M4 {key} metadata must not be negative."
        return None
    return value


def validate_typed_value(instance, *, definition, field_name="datapoint"):
    """Validate a supplied value without requiring a draft to be complete.

    The definition can be an M4 ``Datapoint`` or ``DatapointTableColumn``.
    ``DatapointTableColumn`` currently has no separate option catalog; a SELECT
    column therefore cannot have a supplied value until M4 adds that contract.
    """

    data_type = definition.data_type
    populated = {name for name in VALUE_FIELDS if is_present(getattr(instance, name))}
    expected = expected_value_field(definition)
    errors = {}

    if data_type == DatapointDataType.TABLE:
        if populated or instance.unit_id:
            errors[field_name] = "TABLE definitions cannot store scalar values."
        raise_if_errors(errors)
        return

    if populated and populated != {expected}:
        errors[field_name] = f"{data_type} values must be stored only in {expected}."

    value = getattr(instance, expected) if expected else None
    has_value = is_present(value)
    metadata = definition.validation_metadata or {}

    if instance.unit_id:
        if data_type not in NUMERIC_TYPES:
            errors["unit"] = "Only numeric values may have a unit."
        elif not has_value:
            errors["unit"] = "A unit requires a numeric value."
        elif not definition.unit_family_id:
            errors["unit"] = "This definition does not allow a unit."
        elif instance.unit.family_id != definition.unit_family_id:
            errors["unit"] = "Unit must belong to the definition's unit family."
        elif not instance.unit.is_active:
            errors["unit"] = "Unit is inactive."
    elif has_value and data_type in NUMERIC_TYPES and definition.unit_family_id:
        errors["unit"] = "A numeric value requires a unit from the definition's unit family."

    if data_type == DatapointDataType.SELECT and instance.selected_option_id:
        if hasattr(definition, "datapoint_id"):
            errors["selected_option"] = (
                "M4 does not yet define SELECT options for TABLE columns."
            )
        elif instance.selected_option.datapoint_id != definition.id:
            errors["selected_option"] = "Option does not belong to this datapoint."
        elif not instance.selected_option.is_active:
            errors["selected_option"] = "Selected option is inactive."

    if has_value and data_type in NUMERIC_TYPES:
        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValidationError({expected: "Value must be numeric."}) from exc
        minimum = _metadata_decimal(metadata, "min", errors)
        maximum = _metadata_decimal(metadata, "max", errors)
        if minimum is not None and number < minimum:
            errors[expected] = f"Value must be at least {minimum}."
        if maximum is not None and number > maximum:
            errors[expected] = f"Value must be at most {maximum}."
        if data_type == DatapointDataType.DECIMAL:
            decimal_places = _metadata_non_negative_integer(
                metadata, "decimal_places", errors
            )
            if decimal_places is not None:
                # Django's DecimalField may retain storage-scale trailing zeroes
                # (for example Decimal("1.23000000")). M4 precision constrains
                # meaningful entered digits, not database padding.
                actual_places = max(0, -number.normalize().as_tuple().exponent)
                if actual_places > decimal_places:
                    errors[expected] = (
                        f"Value must not exceed {decimal_places} decimal places."
                    )
    elif has_value and data_type in {DatapointDataType.TEXT, DatapointDataType.LONG_TEXT}:
        max_length = _metadata_non_negative_integer(metadata, "max_length", errors)
        if max_length is not None and len(value) > max_length:
            errors[expected] = f"Value must not exceed {max_length} characters."

    raise_if_errors(errors)


def validate_complete_value(instance, *, definition, field_name="datapoint"):
    """Validate a typed value and require the definition's value field."""

    validate_typed_value(instance, definition=definition, field_name=field_name)
    expected = expected_value_field(definition)
    if expected and not is_present(getattr(instance, expected)):
        raise ValidationError({expected: "A value is required before submission."})


def minimum_table_rows(definition):
    """Return the M4 ``min_rows`` rule, rejecting malformed catalog metadata."""

    errors = {}
    minimum = _metadata_non_negative_integer(
        definition.validation_metadata or {}, "min_rows", errors
    )
    raise_if_errors(errors)
    return minimum or 0


def raise_if_errors(errors):
    if errors:
        raise ValidationError(errors)
