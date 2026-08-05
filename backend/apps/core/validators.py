import re

from django.core.exceptions import ValidationError


def validate_mobile_number(value):
    """
    Validates Indian mobile numbers.
    Example: 9876543210
    """
    pattern = r'^[6-9]\d{9}$'

    if not re.match(pattern, value):
        raise ValidationError(
            "Enter a valid 10-digit mobile number."
        )


def validate_iso_code(value):
    """
    Validates ISO country code.
    Accepts 2 or 3 uppercase characters.
    Examples:
        IN
        IND
        US
        USA
    """
    pattern = r'^[A-Z]{2,3}$'

    if not re.match(pattern, value):
        raise ValidationError(
            "ISO code must contain 2 or 3 uppercase letters."
        )


def validate_financial_year(value):
    """
    Validates financial year.

    Example:
        2025-26
        2026-27
    """
    pattern = r'^\d{4}-\d{2}$'

    if not re.match(pattern, value):
        raise ValidationError(
            "Financial year must be in YYYY-YY format."
        )


def validate_percentage(value):
    """
    Valid percentage:
    0 to 100
    """
    if value < 0 or value > 100:
        raise ValidationError(
            "Percentage must be between 0 and 100."
        )


def validate_positive_number(value):
    """
    Ensures value is greater than zero.
    """
    if value <= 0:
        raise ValidationError(
            "Value must be greater than zero."
        )


def validate_non_negative_number(value):
    """
    Ensures value is zero or positive.
    """
    if value < 0:
        raise ValidationError(
            "Value cannot be negative."
        )


def validate_file_size(file):
    """
    Maximum upload size = 10 MB.
    """
    max_size = 10 * 1024 * 1024

    if file.size > max_size:
        raise ValidationError(
            "File size must not exceed 10 MB."
        )


def validate_file_extension(file):
    """
    Allowed upload extensions.
    """
    allowed_extensions = {
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".csv",
    }

    filename = file.name.lower()

    if not any(filename.endswith(ext) for ext in allowed_extensions):
        raise ValidationError(
            "Unsupported file type."
        )


def validate_name(value):
    """
    Allows alphabets, spaces, hyphen and apostrophe.
    """
    pattern = r"^[A-Za-z\s'-]+$"

    if not re.match(pattern, value):
        raise ValidationError(
            "Name contains invalid characters."
        )


def validate_code(value):
    """
    Generic code validator.

    Examples:
        COMP001
        GRI-101
        FACILITY_01
    """
    pattern = r'^[A-Za-z0-9_-]+$'

    if not re.match(pattern, value):
        raise ValidationError(
            "Only letters, numbers, hyphen and underscore are allowed."
        )