"""Time parsing utilities for relative time expressions.

This module provides utilities for parsing relative time expressions like "24h",
"7d", "2w", "1m" into datetime objects. Useful for filtering tickets by age or
activity thresholds in a human-friendly way.

Design Decision: Relative time parsing
- Supports hours (h), days (d), weeks (w), months (m)
- Months approximated as 30 days (trade-off: simple vs. calendar-accurate)
- Returns timezone-aware UTC datetimes for consistency
- Rationale: Human-friendly time expressions without complex calendar logic

Performance: O(1) for parsing (regex match + arithmetic)
Memory: O(1) auxiliary space (no allocations beyond datetime objects)
"""

import re
from datetime import datetime, timedelta, timezone

# Regex pattern for relative time expressions (e.g., "24h", "7d", "2w", "1m")
# Format: <number><unit> where unit is h/d/w/m
RELATIVE_TIME_PATTERN = re.compile(r"^(\d+)([hdwm])$", re.IGNORECASE)


def parse_relative_time(value: str) -> datetime:
    """Parse relative time expression to datetime.

    Supports relative time expressions:
    - h: hours (e.g., "24h" = 24 hours ago)
    - d: days (e.g., "7d" = 7 days ago)
    - w: weeks (e.g., "2w" = 2 weeks ago)
    - m: months (e.g., "1m" = 1 month ago, approximated as 30 days)

    Design Trade-offs:
    - Month approximation: 1 month = 30 days (not calendar months)
        - Rationale: Avoids complex calendar arithmetic (leap years, varying month lengths)
        - Good enough for filtering tickets by age thresholds
        - Alternative: Use dateutil.relativedelta for exact calendar months (adds dependency)
    - UTC timezone: All results are timezone-aware UTC
        - Rationale: Consistent comparison with ticket timestamps
        - Avoids ambiguity from local timezone assumptions

    Args:
        value: Relative time string (e.g., "24h", "7d", "2w", "1m")

    Returns:
        Timezone-aware UTC datetime representing the calculated past time

    Raises:
        ValueError: If value format is invalid or not recognized

    Examples:
        >>> # 24 hours ago
        >>> dt = parse_relative_time("24h")
        >>> isinstance(dt, datetime)
        True

        >>> # 7 days ago
        >>> dt = parse_relative_time("7d")

        >>> # 2 weeks ago (14 days)
        >>> dt = parse_relative_time("2w")

        >>> # 1 month ago (30 days approximation)
        >>> dt = parse_relative_time("1m")

        >>> # Invalid format raises ValueError
        >>> parse_relative_time("invalid")  # doctest: +SKIP
        Traceback (most recent call last):
        ...
        ValueError: Invalid time format: 'invalid'. Expected format: <number><unit> (e.g., 24h, 7d, 2w, 1m)

    Performance:
    - Time Complexity: O(1) - regex match + datetime arithmetic
    - Space Complexity: O(1) - single datetime object allocation
    """
    match = RELATIVE_TIME_PATTERN.match(value.strip())
    if not match:
        raise ValueError(
            f"Invalid time format: {value!r}. "
            "Expected format: <number><unit> (e.g., 24h, 7d, 2w, 1m)"
        )

    amount = int(match.group(1))
    unit = match.group(2).lower()

    # Current time in UTC
    now = datetime.now(timezone.utc)

    # Calculate timedelta based on unit
    if unit == "h":
        delta = timedelta(hours=amount)
    elif unit == "d":
        delta = timedelta(days=amount)
    elif unit == "w":
        delta = timedelta(weeks=amount)
    elif unit == "m":
        # Approximate month as 30 days
        # Trade-off: Simple approximation vs. exact calendar months
        delta = timedelta(days=amount * 30)
    else:
        # Should never reach here due to regex, but defensive programming
        raise ValueError(f"Unsupported time unit: {unit!r}")

    return now - delta


def parse_time_filter(
    updated_after: str | None = None,
    since: str | None = None,
) -> datetime | None:
    """Parse time filter parameters into a single datetime.

    Combined parser for common API filter patterns like updated_after/since.
    Handles both absolute ISO timestamps and relative time expressions.

    Design Decision: Flexible input formats
    - Accepts ISO 8601 timestamps (e.g., "2025-01-01T00:00:00Z")
    - Accepts relative time expressions (e.g., "24h", "7d")
    - Prioritizes updated_after over since if both provided
    - Returns None if neither provided (no filtering)

    Args:
        updated_after: Optional time filter (ISO timestamp or relative time)
        since: Optional time filter (ISO timestamp or relative time, fallback)

    Returns:
        Timezone-aware UTC datetime if filter provided, None otherwise

    Raises:
        ValueError: If time format is invalid

    Examples:
        >>> # Relative time expression
        >>> dt = parse_time_filter(updated_after="24h")
        >>> isinstance(dt, datetime)
        True

        >>> # ISO timestamp
        >>> dt = parse_time_filter(since="2025-01-01T00:00:00Z")
        >>> dt.year
        2025

        >>> # Prioritizes updated_after
        >>> dt1 = parse_time_filter(updated_after="7d", since="14d")
        >>> dt2 = parse_time_filter(updated_after="7d")
        >>> dt1 == dt2  # updated_after takes precedence
        True

        >>> # No filter returns None
        >>> parse_time_filter() is None
        True

    Performance:
    - Time Complexity: O(1) - single parse operation
    - Space Complexity: O(1) - single datetime object
    """
    # Prioritize updated_after over since
    value = updated_after or since
    if not value:
        return None

    # Try parsing as relative time first
    try:
        return parse_relative_time(value)
    except ValueError:
        pass

    # Try parsing as ISO timestamp
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # Ensure timezone-aware (convert naive to UTC if needed)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError) as e:
        raise ValueError(
            f"Invalid time format: {value!r}. "
            "Expected ISO timestamp (e.g., 2025-01-01T00:00:00Z) "
            "or relative time (e.g., 24h, 7d, 2w, 1m)"
        ) from e
