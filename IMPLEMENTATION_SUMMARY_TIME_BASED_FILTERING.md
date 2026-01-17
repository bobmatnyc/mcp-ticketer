# Time-Based Filtering Implementation Summary

## Overview
Added time-based filtering capabilities to `ticket_search` tool, enabling users to filter tickets by update time using either ISO datetime strings or relative time expressions (e.g., "24h", "7d").

## Changes Made

### 1. Updated SearchQuery Model (`src/mcp_ticketer/core/models.py`)
- Added `updated_after: datetime | None` field to SearchQuery model
- This field accepts a parsed datetime object that will be used by adapters for filtering

### 2. Updated ticket_search Tool (`src/mcp_ticketer/mcp/server/tools/search_tools.py`)

#### New Parameters Added:
- `updated_after: str | None = None` - ISO datetime or relative time ("24h", "7d", "2w", "1m")
- `updated_before: str | None = None` - ISO datetime for upper bound (reserved for future use)
- `since: str | None = None` - Alias for `updated_after` (relative time shorthand)
- `include_activity: bool = False` - Include activity/comments per ticket
- `include_comments: bool = False` - Include comment previews
- `activity_limit: int = 5` - Maximum activity items per ticket

#### Implementation Details:

**Time Filter Parsing:**
```python
from ....utils.time_utils import parse_time_filter

parsed_time_filter = parse_time_filter(
    updated_after=updated_after,
    since=since
)
```

**Activity/Comments Fetching:**
- When `include_activity=True` or `include_comments=True`:
  - Fetches comments for each ticket using `adapter.get_comments()`
  - Stores activity data in separate dictionaries
  - Merges into response without modifying Pydantic models

**Response Enhancement:**
- Added `query_period` field to response when time filter is used
- Shows the original time filter string (e.g., "24h", "7d")
- Helps users understand what time range was queried

### 3. Used Existing Utilities (`src/mcp_ticketer/utils/time_utils.py`)
- Leveraged existing `parse_time_filter()` function
- Supports both ISO timestamps and relative time expressions
- Returns timezone-aware UTC datetime objects

## Backward Compatibility

✅ **Fully backward compatible** - all existing calls work unchanged:
- All new parameters are optional with sensible defaults
- Existing searches continue to work without modification
- Time filtering is opt-in via new parameters

## Usage Examples

### Basic Time Filtering
```python
# Last 24 hours
await ticket_search(updated_after="24h", state="open")

# Last 7 days
await ticket_search(since="7d", project_id="proj-123")

# Last 2 weeks
await ticket_search(updated_after="2w")

# Last month (30 days)
await ticket_search(since="1m")
```

### ISO Datetime Filtering
```python
# Specific date
await ticket_search(updated_after="2025-01-01T00:00:00Z")

# Specific datetime
await ticket_search(updated_after="2025-01-10T15:30:00Z")
```

### With Activity/Comments
```python
# Include full activity
await ticket_search(
    updated_after="24h",
    include_activity=True,
    activity_limit=10
)

# Include comment previews only
await ticket_search(
    since="7d",
    include_comments=True,
    activity_limit=5
)
```

### Combined Filters
```python
# Time + state + priority
await ticket_search(
    updated_after="48h",
    state="in_progress",
    priority="high",
    include_activity=True
)
```

## Response Format

### Standard Response (with time filter)
```json
{
  "status": "completed",
  "tickets": [
    {
      "id": "TICKET-123",
      "title": "Fix authentication bug",
      "state": "open",
      "updated_at": "2026-01-10T15:30:00Z",
      // ... other ticket fields
      "activity": [  // if include_activity=True
        {
          "id": "comment-1",
          "author": "user@example.com",
          "text": "Working on this now",
          "created_at": "2026-01-10T14:00:00Z"
        }
      ],
      "comment_preview": [  // if include_comments=True
        {
          "author": "user@example.com",
          "text": "Working on this now...",
          "created_at": "2026-01-10T14:00:00Z"
        }
      ]
    }
  ],
  "count": 1,
  "query": {
    "text": null,
    "state": "open",
    "priority": null,
    "tags": null,
    "assignee": null,
    "project": "proj-123"
  },
  "query_period": "24h"  // Shows the time filter used
}
```

## Time Filter Formats Supported

### Relative Time Expressions
- `h` - hours (e.g., "24h" = 24 hours ago)
- `d` - days (e.g., "7d" = 7 days ago)
- `w` - weeks (e.g., "2w" = 2 weeks ago)
- `m` - months (e.g., "1m" = 30 days ago)

### ISO 8601 Timestamps
- `2025-01-01T00:00:00Z` - UTC with Z suffix
- `2025-01-01T00:00:00+00:00` - UTC with explicit timezone
- `2025-01-01T15:30:00-05:00` - With timezone offset

## Adapter Integration

The `updated_after` datetime is passed to adapters via the SearchQuery model:

```python
search_query = SearchQuery(
    query=query,
    state=state_enum,
    priority=priority_enum,
    tags=tags,
    assignee=assignee,
    project=final_project,
    updated_after=parsed_time_filter,  # ← Added
    limit=min(limit, 100),
)
```

**Adapters can now:**
1. Check if `search_query.updated_after` is set
2. Use it to filter results by update time
3. Implement platform-specific filtering (e.g., Linear's `updatedAt` filter)

## Error Handling

**Invalid time format:**
```json
{
  "status": "error",
  "error": "Invalid time filter: Invalid time format: 'invalid'. Expected ISO timestamp (e.g., 2025-01-01T00:00:00Z) or relative time (e.g., 24h, 7d, 2w, 1m)"
}
```

**Comments fetch failure:**
- Logs warning but continues search
- Gracefully degrades if adapter doesn't support `get_comments()`
- Won't fail entire search if one ticket's comments fail to load

## Testing

Created and ran comprehensive tests for time filter parsing:
- ✅ Relative time expressions (24h, 7d, 2w, 1m)
- ✅ ISO datetime parsing
- ✅ Priority (updated_after takes precedence over since)
- ✅ None handling (no filter provided)
- ✅ Invalid format error handling

## LOC Delta

**Changes:**
- Added: ~60 lines (new parameters, time parsing, activity fetching, response building)
- Modified: ~30 lines (docstrings, response construction)
- Net Change: +90 lines

**Files Modified:**
1. `src/mcp_ticketer/core/models.py` (+3 lines)
2. `src/mcp_ticketer/mcp/server/tools/search_tools.py` (+87 lines)

**Files Unchanged:**
- `src/mcp_ticketer/utils/time_utils.py` (reused existing code)

## Next Steps for Adapters

Adapters should implement time-based filtering using `search_query.updated_after`:

**Example (Linear):**
```python
if query.updated_after:
    issue_filter["updatedAt"] = {"gte": query.updated_after.isoformat()}
```

**Example (GitHub):**
```python
if query.updated_after:
    # Use GitHub's updated filter
    search_query += f" updated:>={query.updated_after.strftime('%Y-%m-%d')}"
```

**Example (Jira):**
```python
if query.updated_after:
    jql += f" AND updated >= '{query.updated_after.strftime('%Y-%m-%d %H:%M')}'"
```

## Related Files

- `src/mcp_ticketer/core/models.py` - SearchQuery model
- `src/mcp_ticketer/mcp/server/tools/search_tools.py` - ticket_search tool
- `src/mcp_ticketer/utils/time_utils.py` - Time parsing utilities
- `src/mcp_ticketer/core/adapter.py` - BaseAdapter with get_comments()

## Design Decisions

1. **Time filter parsing centralized** - Used existing `parse_time_filter()` utility
2. **Activity/comments as opt-in** - Default behavior unchanged for performance
3. **Separate dictionaries for activity data** - Avoids modifying Pydantic models
4. **query_period in response** - Helps users understand what was queried
5. **Graceful degradation** - Comments fetch failures don't break search
6. **Adapter-agnostic** - SearchQuery passes datetime, adapters implement filtering

## Benefits

1. **Time-based queries** - Find recently updated tickets easily
2. **Relative time support** - Human-friendly expressions ("24h", "7d")
3. **Activity context** - See recent comments without separate API calls
4. **Backward compatible** - No breaking changes to existing code
5. **Flexible** - Supports both relative and absolute time expressions
6. **Type-safe** - Uses datetime objects internally
