"""Field validation utilities for adapter data."""


class ValidationError(Exception):
    """Raised when field validation fails."""

    pass


class FieldValidator:
    """Validates field lengths and formats across adapters."""

    # Field length limits per adapter
    LIMITS = {
        "linear": {
            "epic_description": 255,
            "epic_name": 255,
            "issue_description": 100000,  # Issues have much higher limit
            "issue_title": 255,
        },
        "jira": {
            "summary": 255,
            "description": 32767,
        },
        "github": {
            "title": 256,
            "body": 65536,
        },
    }

    @classmethod
    def validate_field(
        cls,
        adapter_name: str,
        field_name: str,
        value: str | None,
        truncate: bool = False,
    ) -> str:
        """Validate and optionally truncate a field value.

        Args:
            adapter_name: Name of adapter (linear, jira, github)
            field_name: Name of field being validated
            value: Field value to validate
            truncate: If True, truncate instead of raising error

        Returns:
            Validated (possibly truncated) value

        Raises:
            ValidationError: If value exceeds limit and truncate=False

        """
        if value is None:
            return ""

        adapter_limits = cls.LIMITS.get(adapter_name.lower(), {})
        limit = adapter_limits.get(field_name)

        if limit and len(value) > limit:
            if truncate:
                return value[:limit]
            else:
                raise ValidationError(
                    f"{field_name} exceeds {adapter_name} limit of {limit} characters "
                    f"(got {len(value)}). Use truncate=True to auto-truncate."
                )

        return value
