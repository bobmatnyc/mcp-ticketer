"""Tests for field validation utilities."""

import pytest

from mcp_ticketer.core.validators import FieldValidator, ValidationError


def test_linear_description_limit() -> None:
    """Test Linear epic description 255-char limit."""
    short_desc = "Short description"
    assert (
        FieldValidator.validate_field("linear", "epic_description", short_desc)
        == short_desc
    )

    long_desc = "x" * 300
    with pytest.raises(ValidationError, match="255 characters"):
        FieldValidator.validate_field("linear", "epic_description", long_desc)

    # Test truncation
    truncated = FieldValidator.validate_field(
        "linear", "epic_description", long_desc, truncate=True
    )
    assert len(truncated) == 255


def test_linear_name_limit() -> None:
    """Test Linear epic name 255-char limit."""
    short_name = "Short name"
    assert (
        FieldValidator.validate_field("linear", "epic_name", short_name) == short_name
    )

    long_name = "y" * 300
    with pytest.raises(ValidationError, match="255 characters"):
        FieldValidator.validate_field("linear", "epic_name", long_name)

    # Test truncation
    truncated = FieldValidator.validate_field(
        "linear", "epic_name", long_name, truncate=True
    )
    assert len(truncated) == 255


def test_validation_with_none() -> None:
    """Test validation handles None values."""
    result = FieldValidator.validate_field("linear", "epic_description", None)
    assert result == ""


def test_validation_with_empty_string() -> None:
    """Test validation handles empty strings."""
    result = FieldValidator.validate_field("linear", "epic_description", "")
    assert result == ""


def test_linear_issue_description_higher_limit() -> None:
    """Test Linear issue description has 100k char limit."""
    # Epic description should fail at 300 chars
    long_desc = "x" * 300
    with pytest.raises(ValidationError, match="255 characters"):
        FieldValidator.validate_field("linear", "epic_description", long_desc)

    # Issue description should succeed at 300 chars
    result = FieldValidator.validate_field("linear", "issue_description", long_desc)
    assert result == long_desc

    # Issue description should fail at 100001 chars
    very_long_desc = "x" * 100001
    with pytest.raises(ValidationError, match="100000 characters"):
        FieldValidator.validate_field("linear", "issue_description", very_long_desc)


def test_unknown_adapter() -> None:
    """Test validation with unknown adapter (no limits)."""
    # Unknown adapter should not have limits, so no validation error
    long_text = "x" * 1000
    result = FieldValidator.validate_field("unknown_adapter", "some_field", long_text)
    assert result == long_text


def test_unknown_field() -> None:
    """Test validation with unknown field (no limits)."""
    # Unknown field should not have limits, so no validation error
    long_text = "x" * 1000
    result = FieldValidator.validate_field("linear", "unknown_field", long_text)
    assert result == long_text


def test_validation_error_message() -> None:
    """Test validation error message includes useful info."""
    long_desc = "x" * 300
    with pytest.raises(ValidationError) as exc_info:
        FieldValidator.validate_field("linear", "epic_description", long_desc)

    error_msg = str(exc_info.value)
    assert "epic_description" in error_msg
    assert "linear" in error_msg
    assert "255" in error_msg
    assert "300" in error_msg
    assert "truncate=True" in error_msg


def test_jira_limits() -> None:
    """Test JIRA field limits."""
    # JIRA summary has 255 char limit
    long_summary = "x" * 256
    with pytest.raises(ValidationError, match="255 characters"):
        FieldValidator.validate_field("jira", "summary", long_summary)

    # JIRA description has 32767 char limit
    long_description = "x" * 32768
    with pytest.raises(ValidationError, match="32767 characters"):
        FieldValidator.validate_field("jira", "description", long_description)


def test_github_limits() -> None:
    """Test GitHub field limits."""
    # GitHub title has 256 char limit
    long_title = "x" * 257
    with pytest.raises(ValidationError, match="256 characters"):
        FieldValidator.validate_field("github", "title", long_title)

    # GitHub body has 65536 char limit
    long_body = "x" * 65537
    with pytest.raises(ValidationError, match="65536 characters"):
        FieldValidator.validate_field("github", "body", long_body)


def test_case_insensitive_adapter_name() -> None:
    """Test adapter name is case-insensitive."""
    long_desc = "x" * 300

    # Test uppercase
    with pytest.raises(ValidationError, match="255 characters"):
        FieldValidator.validate_field("LINEAR", "epic_description", long_desc)

    # Test mixed case
    with pytest.raises(ValidationError, match="255 characters"):
        FieldValidator.validate_field("Linear", "epic_description", long_desc)
