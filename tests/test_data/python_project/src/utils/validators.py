"""Input validation utilities."""

import re
from typing import Any, Dict, Optional


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


def validate_string(
    value: Any,
    min_length: int = 0,
    max_length: int = 255,
    pattern: Optional[str] = None,
) -> str:
    """Validate string input with length and pattern constraints."""
    if not isinstance(value, str):
        raise ValidationError("Value must be a string")

    if len(value) < min_length:
        raise ValidationError(f"String too short (minimum {min_length} characters)")

    if len(value) > max_length:
        raise ValidationError(f"String too long (maximum {max_length} characters)")

    if pattern and not re.match(pattern, value):
        raise ValidationError("String does not match required pattern")

    return value


def validate_integer(
    value: Any, min_val: Optional[int] = None, max_val: Optional[int] = None
) -> int:
    """Validate integer input with range constraints."""
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise ValidationError("Value must be an integer")

    if min_val is not None and int_value < min_val:
        raise ValidationError(f"Value too small (minimum {min_val})")

    if max_val is not None and int_value > max_val:
        raise ValidationError(f"Value too large (maximum {max_val})")

    return int_value


def validate_email_format(email: str) -> str:
    """Validate email address format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        raise ValidationError("Invalid email format")
    return email.lower()


def validate_password_strength(password: str) -> str:
    """Validate password meets security requirements."""
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long")

    if not re.search(r"[A-Z]", password):
        raise ValidationError("Password must contain at least one uppercase letter")

    if not re.search(r"[a-z]", password):
        raise ValidationError("Password must contain at least one lowercase letter")

    if not re.search(r"\d", password):
        raise ValidationError("Password must contain at least one digit")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError("Password must contain at least one special character")

    return password


class SchemaValidator:
    """Validate data against schema definitions."""

    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data against schema."""
        validated = {}

        for field, rules in self.schema.items():
            if rules.get("required", False) and field not in data:
                raise ValidationError(f"Required field missing: {field}")

            if field not in data:
                if "default" in rules:
                    validated[field] = rules["default"]
                continue

            value = data[field]
            field_type = rules.get("type", "string")

            if field_type == "string":
                validated[field] = validate_string(
                    value,
                    rules.get("min_length", 0),
                    rules.get("max_length", 255),
                    rules.get("pattern"),
                )
            elif field_type == "integer":
                validated[field] = validate_integer(
                    value, rules.get("min_val"), rules.get("max_val")
                )
            elif field_type == "email":
                validated[field] = validate_email_format(value)
            elif field_type == "password":
                validated[field] = validate_password_strength(value)
            else:
                validated[field] = value

        return validated
