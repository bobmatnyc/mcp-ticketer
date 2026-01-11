"""Tests for time-based filtering in ticket_search.

Tests the time parsing utilities used for filtering tickets by creation/update time.
These utilities support both ISO timestamps and human-friendly relative time expressions
like "24h", "7d", "2w", "1m".

This test suite validates:
1. Relative time parsing (hours, days, weeks, months)
2. ISO timestamp parsing
3. Time filter parameter resolution (updated_after vs since)
4. Error handling for invalid formats
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from mcp_ticketer.utils.time_utils import parse_relative_time, parse_time_filter


class TestParseRelativeTime:
    """Test suite for parse_relative_time() function."""

    def test_parse_relative_time_hours(self):
        """Test parsing hours format (e.g., '24h')."""
        result = parse_relative_time("24h")
        now = datetime.now(timezone.utc)
        expected = now - timedelta(hours=24)

        # Allow 1 second tolerance for test execution time
        assert abs((result - expected).total_seconds()) < 1
        assert result.tzinfo == timezone.utc

    def test_parse_relative_time_days(self):
        """Test parsing days format (e.g., '7d')."""
        result = parse_relative_time("7d")
        now = datetime.now(timezone.utc)
        expected = now - timedelta(days=7)

        assert abs((result - expected).total_seconds()) < 1
        assert result.tzinfo == timezone.utc

    def test_parse_relative_time_weeks(self):
        """Test parsing weeks format (e.g., '2w')."""
        result = parse_relative_time("2w")
        now = datetime.now(timezone.utc)
        expected = now - timedelta(weeks=2)

        assert abs((result - expected).total_seconds()) < 1
        assert result.tzinfo == timezone.utc

    def test_parse_relative_time_months(self):
        """Test parsing months format (e.g., '1m')."""
        result = parse_relative_time("1m")
        now = datetime.now(timezone.utc)
        # Months approximated as 30 days
        expected = now - timedelta(days=30)

        assert abs((result - expected).total_seconds()) < 1
        assert result.tzinfo == timezone.utc

    @pytest.mark.parametrize(
        "value,expected_hours",
        [
            ("1h", 1),
            ("12h", 12),
            ("48h", 48),
            ("72h", 72),
        ],
    )
    def test_parse_relative_time_hours_parametrized(self, value, expected_hours):
        """Test various hour values."""
        result = parse_relative_time(value)
        now = datetime.now(timezone.utc)
        expected = now - timedelta(hours=expected_hours)

        assert abs((result - expected).total_seconds()) < 1

    @pytest.mark.parametrize(
        "value,expected_days",
        [
            ("1d", 1),
            ("3d", 3),
            ("14d", 14),
            ("30d", 30),
            ("90d", 90),
        ],
    )
    def test_parse_relative_time_days_parametrized(self, value, expected_days):
        """Test various day values."""
        result = parse_relative_time(value)
        now = datetime.now(timezone.utc)
        expected = now - timedelta(days=expected_days)

        assert abs((result - expected).total_seconds()) < 1

    @pytest.mark.parametrize(
        "value,expected_weeks",
        [
            ("1w", 1),
            ("2w", 2),
            ("4w", 4),
            ("8w", 8),
        ],
    )
    def test_parse_relative_time_weeks_parametrized(self, value, expected_weeks):
        """Test various week values."""
        result = parse_relative_time(value)
        now = datetime.now(timezone.utc)
        expected = now - timedelta(weeks=expected_weeks)

        assert abs((result - expected).total_seconds()) < 1

    @pytest.mark.parametrize(
        "value,expected_days",
        [
            ("1m", 30),  # 1 month = 30 days
            ("2m", 60),  # 2 months = 60 days
            ("3m", 90),  # 3 months = 90 days
            ("6m", 180),  # 6 months = 180 days
        ],
    )
    def test_parse_relative_time_months_parametrized(self, value, expected_days):
        """Test various month values (approximated as 30 days)."""
        result = parse_relative_time(value)
        now = datetime.now(timezone.utc)
        expected = now - timedelta(days=expected_days)

        assert abs((result - expected).total_seconds()) < 1

    def test_parse_relative_time_case_insensitive(self):
        """Test that parsing is case-insensitive."""
        lower = parse_relative_time("24h")
        upper = parse_relative_time("24H")

        # Both should be within 1 second of each other
        assert abs((lower - upper).total_seconds()) < 1

    def test_parse_relative_time_strips_whitespace(self):
        """Test that whitespace is handled correctly."""
        result = parse_relative_time("  24h  ")
        now = datetime.now(timezone.utc)
        expected = now - timedelta(hours=24)

        assert abs((result - expected).total_seconds()) < 1

    @pytest.mark.parametrize(
        "invalid_value,expected_error_substring",
        [
            ("invalid", "Invalid time format"),
            ("24", "Invalid time format"),  # Missing unit
            ("h24", "Invalid time format"),  # Wrong order
            ("24hours", "Invalid time format"),  # Full word instead of letter
            ("", "Invalid time format"),  # Empty string
            ("24 h", "Invalid time format"),  # Space in the middle
            ("-24h", "Invalid time format"),  # Negative value
            ("24.5h", "Invalid time format"),  # Decimal value
            ("24x", "Invalid time format"),  # Invalid unit
        ],
    )
    def test_parse_relative_time_invalid(self, invalid_value, expected_error_substring):
        """Test that invalid formats raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_relative_time(invalid_value)

        assert expected_error_substring in str(exc_info.value)

    def test_parse_relative_time_returns_utc_timezone(self):
        """Test that returned datetime is always UTC timezone-aware."""
        result = parse_relative_time("1h")

        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc


class TestParseTimeFilter:
    """Test suite for parse_time_filter() function."""

    def test_parse_time_filter_iso_timestamp(self):
        """Test parsing ISO timestamp format."""
        iso_string = "2025-01-01T00:00:00Z"
        result = parse_time_filter(updated_after=iso_string)

        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 0
        assert result.tzinfo == timezone.utc

    def test_parse_time_filter_iso_timestamp_without_z(self):
        """Test parsing ISO timestamp without 'Z' suffix."""
        iso_string = "2025-06-15T12:30:00+00:00"
        result = parse_time_filter(since=iso_string)

        assert result is not None
        assert result.year == 2025
        assert result.month == 6
        assert result.day == 15
        assert result.hour == 12
        assert result.minute == 30

    def test_parse_time_filter_iso_timestamp_naive_becomes_utc(self):
        """Test that naive ISO timestamps are converted to UTC."""
        iso_string = "2025-03-20T08:00:00"
        result = parse_time_filter(updated_after=iso_string)

        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_parse_time_filter_relative_time(self):
        """Test parsing relative time expression."""
        result = parse_time_filter(updated_after="24h")
        now = datetime.now(timezone.utc)
        expected = now - timedelta(hours=24)

        assert result is not None
        assert abs((result - expected).total_seconds()) < 1
        assert result.tzinfo == timezone.utc

    def test_parse_time_filter_priority_updated_after_over_since(self):
        """Test that updated_after takes priority over since."""
        updated_after_result = parse_time_filter(
            updated_after="7d",
            since="14d",
        )
        expected_result = parse_time_filter(updated_after="7d")

        assert updated_after_result is not None
        assert expected_result is not None
        # Should use 7d (updated_after), not 14d (since)
        assert abs((updated_after_result - expected_result).total_seconds()) < 1

    def test_parse_time_filter_fallback_to_since(self):
        """Test that since is used when updated_after is None."""
        result = parse_time_filter(
            updated_after=None,
            since="7d",
        )
        now = datetime.now(timezone.utc)
        expected = now - timedelta(days=7)

        assert result is not None
        assert abs((result - expected).total_seconds()) < 1

    def test_parse_time_filter_none_when_both_none(self):
        """Test that None is returned when both parameters are None."""
        result = parse_time_filter(
            updated_after=None,
            since=None,
        )

        assert result is None

    def test_parse_time_filter_none_when_both_omitted(self):
        """Test that None is returned when both parameters are omitted."""
        result = parse_time_filter()

        assert result is None

    @pytest.mark.parametrize(
        "time_value",
        [
            "24h",
            "7d",
            "2w",
            "1m",
            "2025-01-01T00:00:00Z",
            "2025-06-15T12:30:00+00:00",
        ],
    )
    def test_parse_time_filter_both_formats_via_updated_after(self, time_value):
        """Test that both relative and ISO formats work via updated_after."""
        result = parse_time_filter(updated_after=time_value)

        assert result is not None
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    @pytest.mark.parametrize(
        "time_value",
        [
            "24h",
            "7d",
            "2w",
            "1m",
            "2025-01-01T00:00:00Z",
            "2025-06-15T12:30:00+00:00",
        ],
    )
    def test_parse_time_filter_both_formats_via_since(self, time_value):
        """Test that both relative and ISO formats work via since."""
        result = parse_time_filter(since=time_value)

        assert result is not None
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    @pytest.mark.parametrize(
        "invalid_value",
        [
            "invalid",
            "not-a-date",
            "2025/01/01",  # Wrong date format
            "24",  # Missing unit
            "yesterday",  # Natural language not supported
        ],
    )
    def test_parse_time_filter_invalid_format(self, invalid_value):
        """Test that invalid formats raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_time_filter(updated_after=invalid_value)

        error_message = str(exc_info.value)
        assert "Invalid time format" in error_message
        assert invalid_value in error_message

    def test_parse_time_filter_empty_string_treated_as_none(self):
        """Test that empty string is treated as None (no filter)."""
        result = parse_time_filter(
            updated_after="",
            since="",
        )

        assert result is None

    def test_parse_time_filter_iso_with_different_timezones(self):
        """Test ISO timestamps with different timezone offsets."""
        # 10:00 UTC
        utc_time = parse_time_filter(updated_after="2025-01-01T10:00:00Z")
        # 10:00 UTC (5:00 EST which is UTC-5)
        est_time = parse_time_filter(updated_after="2025-01-01T05:00:00-05:00")

        assert utc_time is not None
        assert est_time is not None
        # Both should represent the same instant in time
        assert utc_time == est_time

    def test_parse_time_filter_preserves_timezone_info(self):
        """Test that all results are timezone-aware UTC."""
        test_cases = [
            parse_time_filter(updated_after="24h"),
            parse_time_filter(since="7d"),
            parse_time_filter(updated_after="2025-01-01T00:00:00Z"),
        ]

        for result in test_cases:
            assert result is not None
            assert result.tzinfo is not None
            assert result.tzinfo == timezone.utc


class TestTimeFilterEdgeCases:
    """Test edge cases and integration scenarios."""

    def test_far_future_relative_time(self):
        """Test handling of large relative time values."""
        # 365 days ago (1 year)
        result = parse_relative_time("365d")
        now = datetime.now(timezone.utc)
        expected = now - timedelta(days=365)

        assert abs((result - expected).total_seconds()) < 1

    def test_very_recent_relative_time(self):
        """Test handling of small relative time values."""
        # 1 hour ago
        result = parse_relative_time("1h")
        now = datetime.now(timezone.utc)
        expected = now - timedelta(hours=1)

        assert abs((result - expected).total_seconds()) < 1

    def test_month_approximation_accuracy(self):
        """Test that month approximation is documented behavior."""
        # 1 month = 30 days (not calendar month)
        result = parse_relative_time("1m")
        now = datetime.now(timezone.utc)
        expected = now - timedelta(days=30)

        assert abs((result - expected).total_seconds()) < 1
        # Verify it's NOT using calendar months (which would vary 28-31 days)

    def test_parse_time_filter_whitespace_handling(self):
        """Test that whitespace is handled in both parameters."""
        result1 = parse_time_filter(updated_after="  24h  ")
        result2 = parse_time_filter(since="  7d  ")

        assert result1 is not None
        assert result2 is not None
        assert isinstance(result1, datetime)
        assert isinstance(result2, datetime)

    def test_consistency_between_functions(self):
        """Test that parse_time_filter delegates correctly to parse_relative_time."""
        relative_time = "24h"

        direct_result = parse_relative_time(relative_time)
        filter_result = parse_time_filter(updated_after=relative_time)

        assert filter_result is not None
        # Should be within 1 second of each other (accounting for execution time)
        assert abs((direct_result - filter_result).total_seconds()) < 1
