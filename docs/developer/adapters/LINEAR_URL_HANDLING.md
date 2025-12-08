# Linear URL Structure and Adapter Handling

**Last Updated:** 2025-11-29
**Related Research:** [linear-url-structure-analysis-2025-11-29.md](../../research/linear-url-structure-analysis-2025-11-29.md)

## Overview

This document clarifies how the Linear adapter handles different Linear URL formats and explains the relationship between Linear's web UI routes and the underlying GraphQL API. Understanding this distinction is crucial for using the adapter effectively.

## Table of Contents

- [Linear URL Structure](#linear-url-structure)
- [How URL Parsing Works](#how-url-parsing-works)
- [GraphQL API vs Web UI Routes](#graphql-api-vs-web-ui-routes)
- [MCP Tool Usage Guide](#mcp-tool-usage-guide)
- [Common Misconceptions](#common-misconceptions)
- [Code References](#code-references)

---

## Linear URL Structure

Linear uses different URL paths in its web interface to show different views of projects:

### Project URL Formats

```
https://linear.app/{workspace}/project/{project-slug-id}/{view}
```

**View Suffixes:**
- `/issues` - Project issues list view (default view in web UI)
- `/overview` - Project summary and description view
- `/updates` - Project status updates feed view
- *No suffix* - Redirects to default view (typically `/issues`)

### Example URLs

All of these URLs reference the **same project** (`mcp-ticketer-eac28953c267`):

```
https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267/issues
https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267/overview
https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267/updates
https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267
```

### Issue URL Formats

```
https://linear.app/{workspace}/issue/{issue-identifier}
```

**Example:**
```
https://linear.app/1m-hyperdev/issue/1M-123
```

---

## How URL Parsing Works

### URL Parsing Implementation

The adapter extracts the project or issue identifier from URLs using regex patterns:

**File:** `src/mcp_ticketer/core/url_parser.py`

**Project Pattern:**
```python
project_pattern = r"https?://linear\.app/[\w-]+/project/([\w-]+)"
```

**Issue Pattern:**
```python
issue_pattern = r"https?://linear\.app/[\w-]+/issue/([\w-]+-\d+)"
```

### What Gets Extracted

| Input URL | Extracted ID | Notes |
|-----------|-------------|-------|
| `https://linear.app/team/project/my-proj-abc123/issues` | `my-proj-abc123` | View suffix stripped |
| `https://linear.app/team/project/my-proj-abc123/overview` | `my-proj-abc123` | View suffix stripped |
| `https://linear.app/team/project/my-proj-abc123/updates` | `my-proj-abc123` | View suffix stripped |
| `https://linear.app/team/issue/ABC-123` | `ABC-123` | Issue identifier |

**Key Behavior:**
- ✅ All view suffixes (`/issues`, `/overview`, `/updates`) are **ignored**
- ✅ Only the project slug-id or issue identifier is extracted
- ✅ Identical results regardless of URL variant

### Test Coverage

**File:** `tests/adapters/test_linear_resolve_project_id.py`

Tests verify URL parsing handles all suffix variants:
- Lines 212-233: `/updates` suffix test
- Lines 235-261: Multiple suffixes test
- Lines 40-211: Various project URL formats

---

## GraphQL API vs Web UI Routes

### Important Distinction

**Linear's web UI** uses different URL paths (`/issues`, `/overview`, `/updates`) to show different views of the same project data. These are **frontend-only routes** that control what the browser displays.

**Linear's GraphQL API** does not have separate endpoints for these views. Instead, it provides a unified `project(id:)` query with nested fields for accessing different data types.

### GraphQL Structure

```graphql
query {
  project(id: "project-id") {
    # Project metadata (overview data)
    id
    name
    description
    state
    targetDate

    # Issues (nested field, paginated)
    issues(first: 100) {
      nodes {
        id
        title
        state
        # ... other issue fields
      }
    }

    # Project updates (nested field, paginated)
    projectUpdates(first: 10) {
      nodes {
        id
        body
        createdAt
        # ... other update fields
      }
    }
  }
}
```

### What This Means

**The GraphQL API doesn't care about URL suffixes.** Whether you provide:
- `https://linear.app/team/project/abc/issues`
- `https://linear.app/team/project/abc/overview`
- `https://linear.app/team/project/abc/updates`

The adapter extracts `abc` and queries the same `project(id: "abc")` endpoint. The URL suffix has **no effect** on what data is fetched.

---

## MCP Tool Usage Guide

To access different types of Linear project data, use the appropriate MCP tool:

### 1. Project Metadata + Issue List

**Use Case:** Get project overview (name, description, state, dates) plus list of all issues in the project.

**MCP Tool:** `epic_get(project_id)` or `ticket_read(project_url)`

**GraphQL Query:** `project(id:)` + `issues(filter: {project: ...})`

**Example:**
```python
# Using project ID
result = await epic_get("mcp-ticketer-eac28953c267")

# Using project URL (any variant works)
result = await ticket_read("https://linear.app/team/project/mcp-ticketer-eac28953c267/issues")
result = await ticket_read("https://linear.app/team/project/mcp-ticketer-eac28953c267/overview")
```

**Returns:**
```python
{
    "id": "mcp-ticketer-eac28953c267",
    "name": "MCP Ticketer",
    "description": "Universal ticket management...",
    "state": "started",
    "target_date": "2025-12-31",
    "child_issues": ["1M-123", "1M-124", "1M-125"]  # List of issue IDs
}
```

### 2. Project Status Updates

**Use Case:** Get the project's status updates feed (equivalent to `/updates` view in web UI).

**MCP Tool:** `project_update_list(project_id)`

**GraphQL Query:** `project(id:).projectUpdates`

**Example:**
```python
# Fetch project updates
result = await project_update_list(
    project_id="mcp-ticketer-eac28953c267",
    limit=10
)
```

**Returns:**
```python
{
    "updates": [
        {
            "id": "update-1",
            "body": "Sprint completed with 15/20 stories done",
            "health": "at_risk",
            "created_at": "2025-11-26T10:00:00Z"
        },
        # ... more updates
    ]
}
```

### 3. Project Issues Only

**Use Case:** Get only the issues in a project, without project metadata.

**MCP Tool:** `epic_issues(project_id)`

**GraphQL Query:** `issues(filter: {project: {id: {eq: "..."}}})`

**Example:**
```python
# Fetch issues only
result = await epic_issues("mcp-ticketer-eac28953c267")
```

**Returns:**
```python
{
    "issues": [
        {
            "id": "1M-123",
            "identifier": "1M-123",
            "title": "Fix bug",
            "state": "in_progress",
            "priority": "high"
        },
        # ... more issues
    ]
}
```

### 4. Single Issue

**Use Case:** Get details of a specific issue.

**MCP Tool:** `ticket_read(issue_id_or_url)`

**GraphQL Query:** `issue(id:)`

**Example:**
```python
# Using issue identifier
result = await ticket_read("1M-123")

# Using issue URL
result = await ticket_read("https://linear.app/team/issue/1M-123")
```

**Returns:**
```python
{
    "id": "1M-123",
    "identifier": "1M-123",
    "title": "Fix authentication bug",
    "description": "Users can't log in...",
    "state": "in_progress",
    "priority": "high",
    "assignee": "user@example.com"
}
```

---

## Common Misconceptions

### ❌ Misconception 1: URL Suffix Determines Data Returned

**Incorrect Assumption:**
- `/issues` URL → Returns only issues
- `/overview` URL → Returns only overview data
- `/updates` URL → Returns only updates

**Reality:**
- All project URLs return the **same data** (project metadata + issues)
- URL suffixes are frontend routes only
- Use different MCP tools to get different data subsets

### ❌ Misconception 2: Different URLs Need Different Tools

**Incorrect Assumption:**
- Need different MCP tools for `/issues` vs `/overview` URLs

**Reality:**
- Same MCP tool works for all URL variants
- `ticket_read()` accepts any project URL format
- The adapter automatically extracts the project ID

### ❌ Misconception 3: Updates Are Included in Project Query

**Incorrect Assumption:**
- `ticket_read(project_url)` includes project updates

**Reality:**
- Project updates require separate query via `project_update_list()`
- `ticket_read()` returns project metadata + issue list only
- This matches Linear's GraphQL API structure (updates are separate nested field)

---

## Quick Reference Table

| What You Want | MCP Tool | Input Format | GraphQL Query |
|---------------|----------|--------------|---------------|
| Project overview + issues | `epic_get()` or `ticket_read()` | Project ID or URL (any variant) | `project(id:)` + `issues()` |
| Project status updates | `project_update_list()` | Project ID | `project(id:).projectUpdates` |
| Issues only | `epic_issues()` | Project ID | `issues(filter: {project: ...})` |
| Single issue | `ticket_read()` | Issue ID or URL | `issue(id:)` |

**All project URL variants work identically:**
- `https://linear.app/team/project/id/issues` ✅
- `https://linear.app/team/project/id/overview` ✅
- `https://linear.app/team/project/id/updates` ✅
- Project ID string (e.g., `mcp-ticketer-abc123`) ✅

---

## Code References

### URL Parsing

**File:** `src/mcp_ticketer/core/url_parser.py`

**Function:** `extract_linear_id(url: str)` (lines 58-122)

**Regex Pattern:**
```python
# Project pattern - strips all path suffixes
project_pattern = r"https?://linear\.app/[\w-]+/project/([\w-]+)"
```

### Linear Adapter

**File:** `src/mcp_ticketer/adapters/linear/adapter.py`

**Key Methods:**
- `get_project()` (lines 375-439) - Fetches project metadata
- `_get_project_issues()` (lines 741-783) - Fetches project issues
- `read()` (lines 1488-1599) - Main read method
  - Line 1538: Calls `get_project(ticket_id)`
  - Line 1541: Calls `_get_project_issues(ticket_id)`

### GraphQL Queries

**File:** `src/mcp_ticketer/adapters/linear/queries.py`

**Queries:**
- `GET_PROJECT_QUERY` - Project metadata query
- `LIST_ISSUES_QUERY` - Issues list query
- `LIST_PROJECT_UPDATES_QUERY` (lines 530-545) - Project updates query

### Tests

**File:** `tests/adapters/test_linear_resolve_project_id.py`

**Test Coverage:**
- Lines 40-261: Comprehensive URL parsing tests
- Lines 212-233: `/updates` suffix test
- Lines 235-261: Multiple suffixes test

---

## Summary

**Key Takeaways:**

1. ✅ Linear URL suffixes (`/issues`, `/overview`, `/updates`) are **frontend routes only**
2. ✅ The GraphQL API uses a unified `project(id:)` query regardless of URL suffix
3. ✅ The adapter automatically extracts project IDs from all URL variants
4. ✅ Different data types (issues vs updates) require different MCP tools
5. ✅ All project URL variants work identically with `ticket_read()` or `epic_get()`

**When in doubt:**
- Use `epic_get(project_id)` for project overview + issues
- Use `project_update_list(project_id)` for status updates
- Use `epic_issues(project_id)` for issues only
- Any project URL variant works with any of these tools

---

## Related Documentation

- [Linear Adapter Overview](LINEAR.md) - Complete Linear adapter documentation
- [Linear Setup Guide](../../integrations/setup/LINEAR_SETUP.md) - Configuration instructions
- [URL Structure Analysis](../../research/linear-url-structure-analysis-2025-11-29.md) - Detailed research findings
- [MCP API Reference](../../mcp-api-reference.md) - All MCP tool signatures

---

**Document Status:** ✅ Complete
**Validation:** All code references verified against current implementation
**Test Coverage:** URL parsing fully tested in `test_linear_resolve_project_id.py`
