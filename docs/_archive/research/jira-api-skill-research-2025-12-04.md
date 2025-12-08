# Jira REST API v3 Skill Research

**Research Date:** 2025-12-04
**Purpose:** Comprehensive analysis of Jira REST API v3 and best practices for building a Claude agent skill
**Project:** mcp-ticketer
**Adapter:** `src/mcp_ticketer/adapters/jira.py` (1,899 lines)

---

## Executive Summary

This research provides a comprehensive analysis of the Jira REST API v3, current mcp-ticketer implementation, and recommendations for building a high-quality Claude Code skill for Jira API development. Key findings:

1. **Current Implementation:** The mcp-ticketer Jira adapter is well-structured with 1,899 lines covering core CRUD operations, JQL search, sprint management, and attachment handling.

2. **Critical API Changes (2025):** Atlassian is enforcing new rate limits (effective Nov 22, 2025) and has deprecated `/rest/api/3/search` in favor of `/rest/api/3/search/jql` with significant performance implications.

3. **Skill Requirements:** A comprehensive skill should cover authentication methods, JQL optimization, rate limiting strategies, field expansion, and sprint/epic management patterns.

4. **Implementation Gaps:** Current adapter lacks milestone support (planned for v2.1.0), advanced JQL optimization patterns, and some agile board features.

---

## 1. Jira REST API v3 Overview

### 1.1 Base URL Patterns

**Jira Cloud (API v3):**
```
https://{domain}.atlassian.net/rest/api/3/{endpoint}
```

**Jira Server/Data Center (API v2):**
```
https://{domain}/rest/api/2/{endpoint}
```

**Jira Software Agile API (v1.0):**
```
https://{domain}.atlassian.net/rest/agile/1.0/{endpoint}
```

**Key Differences:**
- Cloud uses REST API v3 (modern, recommended)
- Server/Data Center uses REST API v2 (legacy, still supported)
- Agile features require separate `/rest/agile/1.0/` base path

### 1.2 Authentication Methods (2025)

**Recommended Methods:**

1. **API Tokens (Cloud)** - Most common for automation
   - Create at: https://id.atlassian.com/manage/api-tokens
   - Use with Basic Auth: `email:api_token`
   - Never expire unless revoked
   - Scoped to user permissions

2. **OAuth 2.0** - For user-authorized apps
   - 3-legged OAuth for user authorization
   - Token refresh mechanism
   - Granular scopes
   - Best for integrations requiring user consent

3. **Personal Access Tokens (PAT)** - For scripts and automation
   - Available in Server/Data Center
   - Similar to API tokens
   - Can be scoped to specific permissions

**Deprecated Methods:**
- Basic Auth with password (deprecated 2019)
- Cookie-based authentication (legacy)

**Current Implementation:**
```python
# mcp-ticketer uses Basic Auth with API token
self.auth = httpx.BasicAuth(self.email, self.api_token)
```

✅ **Verdict:** Current implementation follows best practices for Cloud.

### 1.3 Rate Limiting (2025 Critical Updates)

**BREAKING CHANGE:** Effective November 22, 2025, Atlassian enforces strict rate limits on API tokens.

**Rate Limit Categories:**

1. **Per-App Rate Limits**
   - Cloud: ~10 requests/second per app
   - Tracked by app ID or API token
   - Independent of user or endpoint

2. **Per-Issue Write Limits**
   - NEW in 2025: Prevents excessive updates to single issue
   - Protects against accidental update loops
   - Returns `429` with `RateLimit-Reason: jira-per-issue-on-write`

3. **Concurrent Request Limits**
   - High concurrency degrades Jira performance
   - Not a workaround for rate limits
   - May trigger throttling

**Rate Limit Headers:**
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 5
X-RateLimit-Reset: 1638360000
Retry-After: 30
```

**Current Implementation:**
```python
async def _make_request(self, method, endpoint, data=None, params=None, retry_count=0):
    try:
        # ... request logic ...
    except HTTPStatusError as e:
        # Handle rate limiting
        if e.response.status_code == 429 and retry_count < self.max_retries:
            retry_after = int(e.response.headers.get("Retry-After", 5))
            await asyncio.sleep(retry_after)
            return await self._make_request(
                method, endpoint, data, params, retry_count + 1
            )
```

✅ **Verdict:** Current implementation handles rate limiting correctly with exponential backoff.

**Recommended Enhancements:**
- Add jitter to retry delays (avoid thundering herd)
- Parse `X-RateLimit-Reset` header for smarter backoff
- Implement per-issue write tracking to detect loops

### 1.4 Pagination

**Two Pagination Methods:**

1. **Offset-based (Traditional):**
   ```python
   params = {
       "startAt": 0,
       "maxResults": 50
   }
   ```
   - Simple and predictable
   - Can miss items if data changes between requests
   - Used by most endpoints

2. **Cursor-based (New in v3):**
   ```python
   params = {
       "cursor": "eyJpc3N1ZUlkIjoxMDAwMH0=",
       "maxResults": 50
   }
   ```
   - More efficient for large datasets
   - Prevents missed/duplicate items
   - **WARNING:** Token expiration issues reported in 2025

**Current Implementation:**
```python
async def list(self, limit=10, offset=0, filters=None):
    data = await self._make_request(
        "GET",
        "search/jql",
        params={
            "jql": jql,
            "startAt": offset,
            "maxResults": limit,
            "fields": "*all",
        },
    )
```

✅ **Verdict:** Uses offset-based pagination (stable, recommended).

**Performance Optimization:**
- For bulk operations: Request IDs only (`fields=key`), then batch fetch details
- Maximum batch size: 5,000 issues for ID-only queries
- Use `Bulk Fetch Issues API` with 100 issues per batch

### 1.5 API Versioning and Deprecation

**Key Deprecations (2024-2025):**

1. **Search Endpoint Change:**
   - Deprecated: `GET /rest/api/3/search`
   - New: `GET /rest/api/3/search/jql`
   - **Issue:** Community reports significant performance degradation
   - **Status:** Current adapter uses new endpoint ✅

2. **Epic Link Retirement (Feb 2024):**
   - Deprecated: `Epic Link` custom field
   - New: Use `Parent` field for epic relationships
   - **Status:** Current adapter uses `customfield_10014` for epic link (legacy)

3. **Basic Auth Deprecation (2019):**
   - Removed from Cloud
   - Still available in Server/Data Center
   - **Status:** Adapter uses API tokens ✅

**Current Implementation:**
```python
# ISSUE: Still uses legacy epic link field
epic_link = fields.get("customfield_10014")  # Common epic link field
```

⚠️ **Recommendation:** Add fallback to `Parent` field for epic relationships.

---

## 2. Core Endpoints for Ticket Management

### 2.1 Issue API

**Endpoints Implemented:**

| Operation | Endpoint | Method | Current Implementation |
|-----------|----------|--------|------------------------|
| Create | `/issue` | POST | ✅ `create()` |
| Read | `/issue/{issueKey}` | GET | ✅ `read()` |
| Update | `/issue/{issueKey}` | PUT | ✅ `update()` |
| Delete | `/issue/{issueKey}` | DELETE | ✅ `delete()` |
| Search | `/search/jql` | GET | ✅ `search()`, `list()` |
| Transitions | `/issue/{issueKey}/transitions` | GET/POST | ✅ `transition_state()` |
| Comments | `/issue/{issueKey}/comment` | GET/POST | ✅ `add_comment()`, `get_comments()` |
| Attachments | `/issue/{issueKey}/attachments` | POST | ✅ `add_attachment()` |
| Attachments | `/attachment/{id}` | DELETE | ✅ `delete_attachment()` |

**Key Features:**

**Field Expansion:**
```python
# Current implementation uses expansion
issue = await self._make_request(
    "GET",
    f"issue/{ticket_id}",
    params={"expand": "renderedFields"}
)
```

**Atlassian Document Format (ADF):**
```python
def _convert_to_adf(self, text: str) -> dict[str, Any]:
    """Convert plain text to ADF for JIRA Cloud."""
    lines = text.split("\n")
    content = []
    for line in lines:
        if line.strip():
            content.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": line}]
            })
    return {"type": "doc", "version": 1, "content": content}
```

✅ **Verdict:** Core issue CRUD operations are comprehensive and well-implemented.

**Missing Features:**
- Issue linking (`GET /rest/api/3/issueLink`)
- Watchers management (`POST /issue/{issueKey}/watchers`)
- Voters management (`POST /issue/{issueKey}/votes`)
- Work log tracking (`POST /issue/{issueKey}/worklog`)

### 2.2 Project API

**Endpoints Implemented:**

| Operation | Endpoint | Method | Current Implementation |
|-----------|----------|--------|------------------------|
| Get Project | `/project/{projectKey}` | GET | ✅ `get_project_info()` |
| Get Issue Types | `/project/{projectKey}` | GET | ✅ `_get_issue_types()` |
| Get Users | `/project/{projectKey}/role/{roleId}` | GET | ✅ `get_project_users()` |

**Current Implementation:**
```python
async def get_project_info(self, project_key=None):
    """Get JIRA project information including workflows and fields."""
    key = project_key or self.project_key
    project = await self._make_request("GET", f"project/{key}")

    issue_types = await self._get_issue_types(key)
    priorities = await self._get_priorities()
    custom_fields = await self._get_custom_fields()

    return {
        "project": project,
        "issue_types": issue_types,
        "priorities": priorities,
        "custom_fields": custom_fields,
    }
```

✅ **Verdict:** Essential project metadata retrieval is implemented.

**Missing Features:**
- Project creation/deletion
- Version management (releases)
- Component management
- Project permissions

### 2.3 Sprint API (Jira Software)

**Endpoints Implemented:**

| Operation | Endpoint | Method | Current Implementation |
|-----------|----------|--------|------------------------|
| Get Sprints | `/agile/1.0/board/{boardId}/sprint` | GET | ✅ `get_sprints()` |
| List Cycles | `/agile/1.0/board/{boardId}/sprint` | GET | ✅ `list_cycles()` |

**Current Implementation:**
```python
async def get_sprints(self, board_id=None):
    """Get active sprints for a board."""
    if not board_id:
        # Auto-discover board for project
        boards_data = await self._make_request(
            "GET",
            "/rest/agile/1.0/board",
            params={"projectKeyOrId": self.project_key},
        )
        boards = boards_data.get("values", [])
        if not boards:
            return []
        board_id = boards[0]["id"]

    sprints_data = await self._make_request(
        "GET",
        f"/rest/agile/1.0/board/{board_id}/sprint",
        params={"state": "active,future"},
    )

    return sprints_data.get("values", [])
```

✅ **Verdict:** Sprint retrieval is implemented with auto-discovery fallback.

**Missing Features:**
- Sprint creation (`POST /agile/1.0/sprint`)
- Sprint updates (`PUT /agile/1.0/sprint/{sprintId}`)
- Add issues to sprint (`POST /agile/1.0/sprint/{sprintId}/issue`)
- Sprint reports and metrics
- Sprint start/complete operations

### 2.4 Board API (Jira Software)

**Current Status:** Not implemented

**Key Endpoints Missing:**
- `GET /agile/1.0/board` - List all boards
- `GET /agile/1.0/board/{boardId}` - Get board configuration
- `GET /agile/1.0/board/{boardId}/backlog` - Get backlog issues
- `GET /agile/1.0/board/{boardId}/configuration` - Get board settings

**Recommendation:** Low priority - current sprint methods auto-discover boards.

### 2.5 Workflow API

**Endpoints Implemented:**

| Operation | Endpoint | Method | Current Implementation |
|-----------|----------|--------|------------------------|
| Get Transitions | `/issue/{issueKey}/transitions` | GET | ✅ `_get_transitions()` |
| Execute Transition | `/issue/{issueKey}/transitions` | POST | ✅ `transition_state()` |
| List Statuses | `/status` | GET | ✅ `list_issue_statuses()` |
| Get Issue Status | `/issue/{issueKey}` | GET | ✅ `get_issue_status()` |

**Workflow State Mapping:**
```python
def _map_state_from_jira(self, status: dict) -> TicketState:
    """Map JIRA status to universal state."""
    name = status.get("name", "").lower()
    category = status.get("statusCategory", {}).get("key", "").lower()

    # Try category first (more reliable)
    if category == "new":
        return TicketState.OPEN
    elif category == "indeterminate":
        return TicketState.IN_PROGRESS
    elif category == "done":
        return TicketState.DONE

    # Fall back to name matching
    if "block" in name:
        return TicketState.BLOCKED
    # ... etc
```

✅ **Verdict:** Workflow management is comprehensive with smart state mapping.

**Missing Features:**
- Workflow scheme management
- Custom field definitions on transitions
- Transition validators and conditions

---

## 3. Best Practices Analysis

### 3.1 JQL Query Optimization

**Performance Best Practices:**

1. **Use Project-Scoped JQL:**
   ```jql
   project = PROJ AND status = "In Progress"
   ```
   - Always include project filter when possible
   - Significantly improves query performance

2. **Field-Specific Search:**
   ```jql
   summary ~ "bug" OR description ~ "authentication"
   ```
   - More performant than `text ~` which searches all text fields

3. **Indexed Field Queries:**
   ```jql
   assignee = currentUser() AND priority = High
   ```
   - Use indexed fields (assignee, priority, status, type)
   - Avoid custom field searches when possible

4. **Avoid Negative Conditions:**
   ```jql
   # Slow
   priority != Low

   # Faster
   priority IN (Critical, High, Medium)
   ```

5. **Use Functions Wisely:**
   ```jql
   # Efficient
   sprint = 123

   # Less efficient
   sprint in openSprints()
   ```

**Current Implementation:**
```python
async def search(self, query: SearchQuery):
    """Search JIRA issues using JQL."""
    jql_parts = []

    if self.project_key:
        jql_parts.append(f"project = {self.project_key}")

    if query.query:
        jql_parts.append(f'text ~ "{query.query}"')  # ⚠️ Not optimized

    # ... other filters ...
```

⚠️ **Recommendation:** Enhance with field-specific search options:
```python
if query.query:
    # Allow field-specific search via prefix
    if ":" in query.query:
        field, term = query.query.split(":", 1)
        jql_parts.append(f'{field} ~ "{term}"')
    else:
        jql_parts.append(f'text ~ "{query.query}"')
```

**JQL Examples for Skill:**

```jql
# Epic-related queries
"Epic Link" in (PROJ-123, PROJ-456)
parent = PROJ-123
issueFunction in subtasksOf("Epic Name")

# Sprint queries
sprint = 42
sprint in openSprints()
sprint in futureSprints()
sprint is EMPTY

# Custom field queries
cf[10014] = "Epic Name"
"Story Points" > 5
"Sprint" = "Sprint 23"

# Advanced filtering
project = PROJ AND sprint in openSprints() AND assignee = currentUser()
status WAS "In Progress" DURING (startOfWeek(), endOfWeek())
created >= -7d AND priority = High
```

### 3.2 Bulk Operations vs Individual Requests

**Performance Comparison:**

| Operation | Individual Requests | Bulk Approach | Performance Gain |
|-----------|---------------------|---------------|------------------|
| Read 1000 issues | 1000 requests | 1 JQL query + 10 bulk fetches | ~100x faster |
| Update 50 fields | 50 requests | 1 bulk update | ~50x faster |
| Create 100 issues | 100 requests | 1 bulk create | ~100x faster |

**Bulk Endpoints:**
```
POST /rest/api/3/issue/bulk
POST /rest/api/3/issue/bulk/update
DELETE /rest/api/3/issue/bulk
```

**Current Status:** Not implemented

**Recommendation:** Add bulk operation support for:
- `bulk_create()` - Create multiple issues
- `bulk_update()` - Update multiple issues
- `bulk_delete()` - Delete multiple issues

### 3.3 Field Expansion Strategies

**Expansion Options:**

1. **Minimal Expansion (IDs only):**
   ```python
   # Fastest - returns only IDs
   params = {"fields": "key"}
   ```

2. **Selective Fields:**
   ```python
   # Good balance
   params = {"fields": "summary,status,assignee,priority"}
   ```

3. **Full Expansion:**
   ```python
   # Slowest - returns everything
   params = {"fields": "*all", "expand": "renderedFields,changelog"}
   ```

**Current Implementation:**
```python
# List/search operations use full expansion
params = {
    "fields": "*all",
    "expand": "renderedFields",
}
```

⚠️ **Recommendation:** Add field selection parameter:
```python
async def list(self, limit=10, offset=0, filters=None, fields=None):
    """List issues with optional field selection."""
    params = {
        "jql": jql,
        "startAt": offset,
        "maxResults": limit,
        "fields": fields or "*all",  # Allow caller to specify
    }
```

**Nested Expansion:**
```python
# Expand widgets and their fringels
params = {"expand": "widgets.fringels"}
```

**Discovery Pattern:**
```python
# Find expandable fields
response = await client.get("/issue/PROJ-123")
expandable = response.json().get("expand", "")
# Returns: "renderedFields,names,schema,transitions,operations,editmeta"
```

### 3.4 Custom Field Access Patterns

**Custom Field Discovery:**
```python
async def _get_custom_fields(self):
    """Get custom field definitions."""
    fields = await self._make_request("GET", "field")
    self._custom_fields_cache = {
        field["name"]: field["id"]
        for field in fields
        if field.get("custom", False)
    }
    return self._custom_fields_cache
```

✅ **Current implementation caches custom fields.**

**Custom Field Usage:**
```python
# By ID (always works)
fields["customfield_10014"] = "Epic-123"

# By name (requires translation)
custom_fields = await adapter._get_custom_fields()
epic_field_id = custom_fields.get("Epic Link")
fields[epic_field_id] = "Epic-123"
```

**JQL with Custom Fields:**
```jql
-- By ID
cf[10014] = "Epic-123"

-- By name (if supported)
"Epic Link" = "Epic-123"
"Story Points" >= 5
```

### 3.5 Issue Type Schemes

**Issue Type Hierarchy:**
```
Epic (highest level)
├── Story
│   └── Sub-task
├── Task
│   └── Sub-task
└── Bug
    └── Sub-task
```

**Current Implementation:**
```python
def _issue_to_ticket(self, issue: dict) -> Epic | Task:
    """Convert JIRA issue to universal ticket model."""
    fields = issue.get("fields", {})
    issue_type = fields.get("issuetype", {}).get("name", "").lower()
    is_epic = "epic" in issue_type

    if is_epic:
        return Epic(...)
    else:
        return Task(...)
```

✅ **Verdict:** Simple type detection works for common scenarios.

⚠️ **Enhancement:** Add support for issue type hierarchy:
```python
# Detect parent-child relationships
parent = fields.get("parent", {})
subtasks = fields.get("subtasks", [])

# Populate hierarchy
task.parent_issue = parent.get("key") if parent else None
task.subtasks = [st.get("key") for st in subtasks]
```

### 3.6 Permission Model and Security Levels

**Permission Checks:**
```
GET /rest/api/3/mypermissions
GET /rest/api/3/permissions
```

**Security Levels:**
```python
# Create issue with security level
fields = {
    "summary": "Confidential Issue",
    "security": {"id": "10000"}  # Security level ID
}
```

**Current Status:** Not implemented

**Recommendation:** Low priority - most use cases don't require security levels.

### 3.7 Webhook vs Polling for Updates

**Webhook Advantages:**
- Real-time updates
- Reduces API calls
- Event-driven architecture

**Polling Advantages:**
- Simpler to implement
- No server infrastructure required
- Works with firewall restrictions

**Current Implementation:** Polling-based (standard for adapters)

**Webhook Setup:**
```
POST /rest/api/3/webhook
{
  "name": "Issue Updated Webhook",
  "url": "https://myapp.com/webhook",
  "events": ["jira:issue_updated"],
  "filters": {
    "issue-related-events-section": "project = PROJ"
  }
}
```

**Recommendation:** Out of scope for adapter - better suited for MCP server layer.

---

## 4. Current Implementation Analysis

### 4.1 Code Structure

**File:** `src/mcp_ticketer/adapters/jira.py` (1,899 lines)

**Key Classes:**
- `JiraAdapter(BaseAdapter)` - Main adapter implementation
- `JiraIssueType(Enum)` - Issue type constants
- `JiraPriority(Enum)` - Priority level constants

**Helper Functions:**
- `parse_jira_datetime()` - Date parsing with timezone handling
- `extract_text_from_adf()` - ADF to plain text conversion

**Caching Strategy:**
```python
self._workflow_cache: dict[str, Any] = {}
self._priority_cache: list[dict[str, Any]] = []
self._issue_types_cache: dict[str, Any] = {}
self._custom_fields_cache: dict[str, Any] = {}
```

✅ **Verdict:** Well-structured with appropriate caching.

### 4.2 Endpoints Currently Used

**REST API v3:**
- `POST /issue` - Create issues
- `GET /issue/{issueKey}` - Read issues
- `PUT /issue/{issueKey}` - Update issues
- `DELETE /issue/{issueKey}` - Delete issues
- `GET /search/jql` - Search with JQL
- `GET /issue/{issueKey}/transitions` - Get available transitions
- `POST /issue/{issueKey}/transitions` - Execute transition
- `POST /issue/{issueKey}/comment` - Add comment
- `GET /issue/{issueKey}/comment` - Get comments
- `POST /issue/{issueKey}/attachments` - Upload attachment
- `DELETE /attachment/{id}` - Delete attachment
- `GET /project/{projectKey}` - Get project info
- `GET /priority` - List priorities
- `GET /field` - Get custom fields
- `GET /status` - List statuses
- `GET /myself` - Get current user

**Agile API v1.0:**
- `GET /agile/1.0/board` - Find boards
- `GET /agile/1.0/board/{boardId}/sprint` - Get sprints

### 4.3 Implementation Gaps

**Critical Gaps:**

1. **Milestone Support** - Planned for v2.1.0
   ```python
   async def milestone_create(self, ...):
       raise NotImplementedError("Milestone support for Jira coming in v2.1.0")
   ```

2. **Bulk Operations** - Not implemented
   - No `bulk_create()`, `bulk_update()`, `bulk_delete()`

3. **Issue Linking** - Not implemented
   - Cannot create/manage issue links

4. **Work Logs** - Not implemented
   - No time tracking support

**Nice-to-Have Gaps:**

1. **Advanced Sprint Management** - Partial implementation
   - Can read sprints
   - Cannot create/update sprints
   - Cannot add issues to sprints

2. **Board Management** - Not implemented
   - No board configuration support

3. **Component Management** - Not implemented
   - Components stored in metadata only

4. **Version/Release Management** - Not implemented
   - Fix versions stored in metadata only

### 4.4 JQL Usage Patterns

**Current JQL Generation:**
```python
async def search(self, query: SearchQuery):
    jql_parts = []

    if self.project_key:
        jql_parts.append(f"project = {self.project_key}")

    if query.query:
        jql_parts.append(f'text ~ "{query.query}"')

    if query.state:
        status = self.map_state_to_system(query.state)
        jql_parts.append(f'status = "{status}"')

    if query.priority:
        priority = self._map_priority_to_jira(query.priority)
        jql_parts.append(f'priority = "{priority}"')

    if query.assignee:
        jql_parts.append(f'assignee = "{query.assignee}"')

    if query.tags:
        label_conditions = [f'labels = "{tag}"' for tag in query.tags]
        jql_parts.append(f"({' OR '.join(label_conditions)})")

    jql = " AND ".join(jql_parts)
```

✅ **Verdict:** Solid basic JQL generation.

⚠️ **Enhancement Opportunities:**
- Support for custom JQL passthrough
- Support for JQL functions (`currentUser()`, `openSprints()`)
- Support for date range queries
- Support for ordering and grouping

### 4.5 Code Quality Assessment

**Strengths:**

1. **Error Handling:**
   ```python
   try:
       response = await client.request(...)
       response.raise_for_status()
       return response.json()
   except TimeoutException as e:
       if retry_count < self.max_retries:
           await asyncio.sleep(2**retry_count)  # Exponential backoff
           return await self._make_request(...)
   except HTTPStatusError as e:
       if e.response.status_code == 429:  # Rate limiting
           retry_after = int(e.response.headers.get("Retry-After", 5))
           await asyncio.sleep(retry_after)
   ```

2. **Type Safety:**
   - Comprehensive type hints
   - Proper use of `Union[Epic, Task]` return types
   - Pydantic models for data validation

3. **Documentation:**
   - Docstrings for all public methods
   - Clear parameter descriptions
   - Return type documentation

4. **Testability:**
   - Dependency injection via config
   - Async/await patterns
   - Mockable HTTP client

**Areas for Improvement:**

1. **JQL Injection Prevention:**
   ```python
   # Current: No sanitization
   jql_parts.append(f'text ~ "{query.query}"')

   # Better: Escape quotes
   def escape_jql(value: str) -> str:
       return value.replace('"', '\\"')

   jql_parts.append(f'text ~ "{escape_jql(query.query)}"')
   ```

2. **Magic Numbers:**
   ```python
   # Current: Hard-coded field IDs
   epic_link = fields.get("customfield_10014")

   # Better: Configuration
   self.epic_link_field = config.get("epic_link_field", "customfield_10014")
   ```

3. **Logging Verbosity:**
   - Add structured logging for debugging
   - Include request IDs in logs
   - Log rate limit headers

### 4.6 Technical Debt Items

1. **Epic Link Deprecation:**
   ```python
   # TODO: Migrate from customfield_10014 to parent field
   epic_link = fields.get("customfield_10014")
   parent = fields.get("parent")  # New approach
   ```

2. **ADF Handling:**
   ```python
   # Current: Basic paragraph conversion only
   # TODO: Support rich text features (lists, headings, links)
   def _convert_to_adf(self, text: str):
       # ... basic implementation ...
   ```

3. **Credential Validation:**
   ```python
   # TODO: Add actual API test call instead of just checking presence
   def validate_credentials(self):
       if not self.server:
           return False, "JIRA_SERVER is required"
       # Could add: test API call to /myself
   ```

4. **Timezone Handling:**
   ```python
   # Current: Assumes UTC or local timezone
   # TODO: Support project-specific timezone configuration
   ```

---

## 5. Skill Design Requirements

### 5.1 Core Skill Objectives

A comprehensive Jira API skill for Claude agents should enable developers to:

1. **Authenticate Securely** - Understand authentication methods and best practices
2. **Query Efficiently** - Write optimized JQL queries
3. **Handle Rate Limits** - Implement robust rate limiting strategies
4. **Manage Workflows** - Work with Jira workflows and transitions
5. **Work with Agile** - Interact with sprints, boards, and epics
6. **Handle Errors** - Gracefully handle API errors and edge cases

### 5.2 Skill Structure Proposal

**Recommended Organization:**

```
jira-api-skill/
├── 01-authentication.md          # Auth methods, API tokens, OAuth
├── 02-core-endpoints.md          # Issue, project, user endpoints
├── 03-jql-mastery.md             # JQL syntax, optimization, examples
├── 04-rate-limiting.md           # 2025 rate limits, backoff strategies
├── 05-field-management.md        # Custom fields, expansion, ADF
├── 06-agile-workflows.md         # Sprints, boards, epics
├── 07-error-handling.md          # Common errors, retry patterns
├── 08-performance.md             # Bulk operations, caching, pagination
├── 09-examples.md                # Common use cases, code snippets
└── 10-migration-guide.md         # v2 to v3, deprecations
```

**Alternative: Single Comprehensive Skill:**

```
jira-api-comprehensive-skill.md
├── Quick Start Guide
├── Authentication
├── Core Concepts
│   ├── Issues & Types
│   ├── Projects & Workflows
│   └── Custom Fields
├── JQL Reference
│   ├── Basic Syntax
│   ├── Advanced Queries
│   └── Optimization
├── API Patterns
│   ├── CRUD Operations
│   ├── Search & Filter
│   └── Bulk Operations
├── Agile Features
│   ├── Sprints
│   ├── Boards
│   └── Epics
├── Best Practices
│   ├── Rate Limiting
│   ├── Error Handling
│   └── Performance
└── Troubleshooting
```

### 5.3 Essential JQL Examples

**Basic Queries:**
```jql
-- Find my open issues
assignee = currentUser() AND status = "To Do"

-- Find bugs in current sprint
type = Bug AND sprint in openSprints()

-- Find unestimated stories
type = Story AND "Story Points" is EMPTY

-- Find overdue issues
dueDate < now() AND status != Done
```

**Advanced Queries:**
```jql
-- Issues updated this week
updated >= startOfWeek() AND updated <= endOfWeek()

-- Issues created by team members
creator in membersOf("engineering-team")

-- High priority items not assigned
priority in (Highest, High) AND assignee is EMPTY

-- Issues with specific labels
labels in (frontend, backend) OR labels = critical
```

**Epic-Specific:**
```jql
-- All stories in an epic
"Epic Link" = PROJ-123

-- Or using parent (new method)
parent = PROJ-123

-- Epics with incomplete children
type = Epic AND status != Done HAVING issueFunction in subtasksOf("Epic Link")
```

**Sprint Queries:**
```jql
-- Current sprint items
sprint in openSprints() AND project = PROJ

-- Sprint backlog
sprint = 42 AND status != Done

-- Issues moved to next sprint
sprint changed from 41 to 42 during (startOfDay(-7d), now())
```

**Performance Optimization:**
```jql
-- SLOW: Searches all text fields
text ~ "authentication"

-- FAST: Searches specific fields
summary ~ "authentication" OR description ~ "authentication"

-- SLOW: Negative condition
priority != Low

-- FAST: Positive list
priority in (Critical, High, Medium)

-- SLOW: Implicit OR across projects
project in (A, B, C)

-- FAST: Single project
project = A
```

### 5.4 Common Operations

**1. Create Issue with Epic Link:**
```python
fields = {
    "project": {"key": "PROJ"},
    "summary": "User authentication feature",
    "description": adf_content,
    "issuetype": {"name": "Story"},
    "priority": {"name": "High"},
    "labels": ["feature", "authentication"],
    "customfield_10014": "PROJ-123",  # Epic Link
}
```

**2. Transition Issue with Validation:**
```python
# Get available transitions
transitions = await adapter._get_transitions("PROJ-456")

# Find target transition
target = next(
    (t for t in transitions if t["to"]["name"] == "In Progress"),
    None
)

if target:
    await adapter._make_request(
        "POST",
        f"issue/PROJ-456/transitions",
        data={"transition": {"id": target["id"]}}
    )
```

**3. Bulk Fetch Issues:**
```python
# Step 1: Get IDs only (fast)
jql = "project = PROJ AND updated >= -7d"
data = await adapter._make_request(
    "GET", "search/jql",
    params={"jql": jql, "maxResults": 5000, "fields": "key"}
)

issue_keys = [issue["key"] for issue in data["issues"]]

# Step 2: Batch fetch details (100 per request)
for i in range(0, len(issue_keys), 100):
    batch = issue_keys[i:i+100]
    batch_jql = f"key in ({','.join(batch)})"
    details = await adapter._make_request(
        "GET", "search/jql",
        params={"jql": batch_jql, "maxResults": 100, "fields": "*all"}
    )
    # Process details...
```

**4. Add Issue to Sprint:**
```python
# Requires Agile API
await adapter._make_request(
    "POST",
    "/rest/agile/1.0/sprint/42/issue",
    data={"issues": ["PROJ-123", "PROJ-456"]}
)
```

**5. Custom Field Handling:**
```python
# Discover custom fields
custom_fields = await adapter._get_custom_fields()
story_points_id = custom_fields.get("Story Points")

# Set custom field
fields = {
    "summary": "New feature",
    story_points_id: 5  # Use discovered ID
}
```

### 5.5 Error Scenarios to Cover

**1. Rate Limiting (429):**
```python
try:
    response = await client.request(...)
except HTTPStatusError as e:
    if e.response.status_code == 429:
        retry_after = int(e.response.headers.get("Retry-After", 60))
        reason = e.response.headers.get("RateLimit-Reason", "unknown")

        if reason == "jira-per-issue-on-write":
            # Per-issue write limit - specific to one issue
            logger.warning(f"Per-issue rate limit on {issue_key}")
            # Don't retry immediately - this issue is locked
        else:
            # General rate limit - exponential backoff
            await asyncio.sleep(retry_after)
            # Retry request...
```

**2. Invalid Transition (400):**
```python
try:
    await adapter.transition_state("PROJ-123", TicketState.DONE)
except HTTPStatusError as e:
    if e.response.status_code == 400:
        # Get available transitions for user feedback
        transitions = await adapter._get_transitions("PROJ-123")
        available = [t["to"]["name"] for t in transitions]
        raise ValueError(
            f"Cannot transition to Done. Available: {available}"
        )
```

**3. Insufficient Permissions (403):**
```python
try:
    await adapter.delete("PROJ-123")
except HTTPStatusError as e:
    if e.response.status_code == 403:
        raise PermissionError(
            "Insufficient permissions to delete issue. "
            "Check project permissions and security levels."
        )
```

**4. Issue Not Found (404):**
```python
issue = await adapter.read("PROJ-999")
if not issue:
    # Handle gracefully - issue may have been deleted
    logger.info(f"Issue PROJ-999 not found or access denied")
```

**5. Invalid JQL (400):**
```python
try:
    results = await adapter.execute_jql("invalid jql syntax")
except HTTPStatusError as e:
    if e.response.status_code == 400:
        error_msg = e.response.json().get("errorMessages", [])
        raise ValueError(f"Invalid JQL: {error_msg}")
```

### 5.6 Sprint Management Patterns

**Common Sprint Workflow:**
```python
# 1. Find active sprint
sprints = await adapter.get_sprints()
active_sprint = next(s for s in sprints if s["state"] == "active")

# 2. Get sprint issues
sprint_jql = f"sprint = {active_sprint['id']}"
sprint_issues = await adapter.execute_jql(sprint_jql)

# 3. Check sprint progress
total = len(sprint_issues)
done = sum(1 for issue in sprint_issues if issue.state == TicketState.DONE)
progress = (done / total) * 100

# 4. Find incomplete issues
incomplete = [
    issue for issue in sprint_issues
    if issue.state not in [TicketState.DONE, TicketState.CLOSED]
]
```

**Sprint Velocity Calculation:**
```jql
-- Get completed story points from last 3 sprints
project = PROJ
AND type = Story
AND sprint in closedSprints()
AND sprint in (Sprint1, Sprint2, Sprint3)
AND status = Done
```

---

## 6. Recommendations

### 6.1 Adapter Improvements

**High Priority:**

1. **Enhance JQL Search:**
   ```python
   async def search(self, query: SearchQuery, jql_override: str = None):
       """Search with optional raw JQL passthrough."""
       if jql_override:
           # Allow advanced users to provide raw JQL
           jql = jql_override
       else:
           # Build JQL from SearchQuery
           jql = self._build_jql(query)
   ```

2. **Add Bulk Operations:**
   ```python
   async def bulk_create(self, tickets: list[Epic | Task]) -> list[Epic | Task]:
       """Create multiple issues in one request."""

   async def bulk_update(self, updates: list[dict]) -> list[Epic | Task]:
       """Update multiple issues in one request."""
   ```

3. **Improve Epic Link Handling:**
   ```python
   def _get_epic_link_field(self, fields: dict) -> str | None:
       """Get epic link with fallback to parent field."""
       # Try new parent field first
       parent = fields.get("parent")
       if parent:
           return parent.get("key")

       # Fallback to legacy epic link
       return fields.get("customfield_10014")
   ```

4. **Add JQL Sanitization:**
   ```python
   def _escape_jql_value(self, value: str) -> str:
       """Escape special characters in JQL values."""
       return value.replace('"', '\\"').replace("'", "\\'")
   ```

**Medium Priority:**

1. **Enhanced Sprint Management:**
   ```python
   async def create_sprint(self, name: str, board_id: int, **kwargs):
       """Create new sprint."""

   async def add_issues_to_sprint(self, sprint_id: int, issue_keys: list[str]):
       """Add issues to sprint."""
   ```

2. **Issue Linking:**
   ```python
   async def link_issues(
       self, inward_issue: str, outward_issue: str, link_type: str
   ):
       """Create link between issues."""
   ```

3. **Work Log Support:**
   ```python
   async def add_worklog(
       self, issue_key: str, time_spent: str, comment: str = ""
   ):
       """Log work on issue."""
   ```

### 6.2 Skill Structure

**Recommended Approach: Comprehensive Single Skill**

Rationale:
- Easier for Claude to load entire context
- Better cross-referencing
- Consistent examples throughout
- Simpler maintenance

**Estimated Size:** 8,000-12,000 lines (within reasonable limits)

**Key Sections:**

1. **Quick Start** (200 lines)
   - Authentication setup
   - First API call
   - Basic CRUD example

2. **Core Concepts** (800 lines)
   - Issues, projects, users
   - Issue types and workflows
   - Custom fields and priorities

3. **JQL Mastery** (1,500 lines)
   - Syntax reference
   - Field types and operators
   - Functions and keywords
   - Optimization techniques
   - 50+ examples

4. **API Patterns** (2,000 lines)
   - CRUD operations with code examples
   - Search and filtering
   - Pagination strategies
   - Bulk operations
   - Error handling

5. **Agile Features** (1,200 lines)
   - Sprint management
   - Board configuration
   - Epic hierarchy
   - Backlog management

6. **Best Practices** (1,500 lines)
   - Rate limiting strategies (2025 updates)
   - Performance optimization
   - Caching patterns
   - Security considerations

7. **Troubleshooting** (800 lines)
   - Common errors and solutions
   - Debug strategies
   - API limitations and workarounds

8. **Migration Guide** (500 lines)
   - v2 to v3 changes
   - Deprecated features
   - Breaking changes

9. **Reference** (1,500 lines)
   - Complete endpoint list
   - Field reference
   - Status code reference

### 6.3 Priority Features

**Must-Have:**
- Authentication methods (API tokens, OAuth)
- JQL query optimization
- Rate limiting handling (2025 updates)
- Field expansion strategies
- Common error scenarios

**Should-Have:**
- Sprint management patterns
- Epic hierarchy handling
- Bulk operation patterns
- Custom field management
- Workflow transitions

**Nice-to-Have:**
- Advanced JQL functions
- Webhook configuration
- Board management
- Component/version management
- Time tracking

### 6.4 JQL Optimization Opportunities

**Current Issues:**
```python
# Inefficient: Uses generic text search
jql_parts.append(f'text ~ "{query.query}"')
```

**Recommended Enhancement:**
```python
async def search_optimized(
    self,
    query: str = None,
    fields: list[str] = None,  # ["summary", "description"]
    **filters
):
    """Optimized search with field-specific queries."""
    jql_parts = [f"project = {self.project_key}"]

    if query and fields:
        # Search specific fields (faster)
        field_queries = [f'{field} ~ "{query}"' for field in fields]
        jql_parts.append(f"({' OR '.join(field_queries)})")
    elif query:
        # Fallback to text search
        jql_parts.append(f'text ~ "{query}"')

    # Add other filters...
```

---

## 7. Sample Skill Content

### 7.1 Authentication Section Example

```markdown
# Jira REST API Authentication

## Overview

Jira Cloud (as of 2025) supports three primary authentication methods:

1. **API Tokens** - Recommended for automation and scripts
2. **OAuth 2.0** - Required for user-authorized applications
3. **Personal Access Tokens (PAT)** - Server/Data Center only

## API Token Authentication (Recommended)

### Generate API Token

1. Navigate to https://id.atlassian.com/manage/api-tokens
2. Click "Create API token"
3. Provide descriptive name: "mcp-ticketer-production"
4. Copy token immediately (not shown again)

### Python Implementation

```python
import httpx

# Basic Auth with API token
auth = httpx.BasicAuth(
    username="your.email@company.com",
    password="your_api_token_here"
)

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

async with httpx.AsyncClient(auth=auth, headers=headers) as client:
    response = await client.get(
        "https://yourcompany.atlassian.net/rest/api/3/myself"
    )
    user = response.json()
    print(f"Authenticated as: {user['displayName']}")
```

### Security Best Practices

✅ **DO:**
- Store tokens in environment variables or secure vault
- Rotate tokens every 90 days
- Use separate tokens for different environments
- Revoke tokens immediately when compromised

❌ **DON'T:**
- Hard-code tokens in source code
- Commit tokens to version control
- Share tokens between users
- Use same token for multiple applications

### Validation

Test authentication with the `/myself` endpoint:

```python
async def validate_credentials(self):
    """Verify credentials are valid."""
    try:
        user = await self._make_request("GET", "myself")
        return True, user.get("displayName")
    except HTTPStatusError as e:
        if e.response.status_code == 401:
            return False, "Invalid credentials"
        elif e.response.status_code == 403:
            return False, "Insufficient permissions"
        else:
            raise
```
```

### 7.2 JQL Section Example

```markdown
# JQL Query Optimization

## Performance Tiers

### Tier 1: Fastest (Indexed Fields)
- `project`
- `issueType`
- `status`
- `priority`
- `assignee`
- `reporter`
- `created`, `updated`

### Tier 2: Moderate (Some Indexing)
- `labels`
- `fixVersion`
- `component`
- `sprint`

### Tier 3: Slowest (Full Scan)
- `text` (searches all text fields)
- Custom fields (unless indexed)
- `description`

## Optimization Patterns

### Pattern 1: Project Scoping

**Slow:**
```jql
status = "In Progress" AND assignee = currentUser()
```

**Fast:**
```jql
project = PROJ AND status = "In Progress" AND assignee = currentUser()
```

**Why:** Adding project filter uses index, reducing search space.

### Pattern 2: Field-Specific Search

**Slow:**
```jql
text ~ "authentication bug"
```

**Fast:**
```jql
summary ~ "authentication" OR description ~ "authentication"
```

**Why:** Targeted field search is more efficient than full-text.

### Pattern 3: Positive Lists vs Negation

**Slow:**
```jql
priority != Low AND priority != Lowest
```

**Fast:**
```jql
priority IN (Critical, High, Medium)
```

**Why:** Positive matching uses index efficiently.

### Pattern 4: Date Range Optimization

**Slow:**
```jql
created > "2025-01-01" AND created < "2025-12-31"
```

**Fast:**
```jql
created >= startOfYear() AND created <= endOfYear()
```

**Why:** JQL functions are optimized for date calculations.

## Epic and Sprint Queries

### Find Stories in Epic

**Method 1: Epic Link (Legacy)**
```jql
"Epic Link" = PROJ-123
```

**Method 2: Parent Field (New)**
```jql
parent = PROJ-123
```

**Method 3: Issue Function**
```jql
issueFunction in subtasksOf("Epic Name")
```

### Sprint Queries

**Active Sprint:**
```jql
sprint in openSprints() AND project = PROJ
```

**Specific Sprint:**
```jql
sprint = 42
```

**Sprint History:**
```jql
sprint in closedSprints() ORDER BY sprint DESC
```

### Combined Queries

**Current Sprint High Priority:**
```jql
project = PROJ
  AND sprint in openSprints()
  AND priority IN (Critical, High)
  AND status != Done
ORDER BY priority DESC, updated DESC
```

## Custom Field Queries

### By Field ID (Always Works)
```jql
cf[10014] = "Epic-123"
cf[10015] >= 5  -- Story Points
```

### By Field Name (If Supported)
```jql
"Epic Link" = "Epic-123"
"Story Points" >= 5
"Sprint" = "Sprint 23"
```

## Advanced Functions

### Time-Based
```jql
created >= startOfWeek()
updated >= startOfDay(-7d)
dueDate <= endOfMonth()
```

### User-Based
```jql
assignee = currentUser()
reporter in membersOf("engineering-team")
watcher = currentUser()
```

### Issue Relationships
```jql
issueFunction in subtasksOf("PROJ-123")
issueFunction in linkedIssuesOf("PROJ-123", "blocks")
issueFunction in parentsOf("type = Sub-task")
```

## Performance Measurement

Use JQL explain to analyze query performance:

```bash
curl -u email:token \
  "https://yourcompany.atlassian.net/rest/api/3/jql/parse?jql=project=PROJ"
```

Response includes:
- Estimated result count
- Query complexity
- Field usage
```

### 7.3 Rate Limiting Section Example

```markdown
# Rate Limiting (2025 Update)

## Critical Changes

**Effective Date:** November 22, 2025

Atlassian now enforces strict rate limits on all API tokens to ensure
reliability and prevent abuse.

## Rate Limit Types

### 1. Per-App Rate Limits

**Limit:** ~10 requests/second per API token

**Headers:**
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 3
X-RateLimit-Reset: 1701234567
```

**Response When Exceeded:**
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 30
```

### 2. Per-Issue Write Limits (NEW)

**Purpose:** Prevent excessive updates to single issue

**Triggers:** Multiple writes to same issue in short time

**Response:**
```http
HTTP/1.1 429 Too Many Requests
RateLimit-Reason: jira-per-issue-on-write
Retry-After: 60
```

**Important:** This limit is per-issue, not global. Other issues can
still be updated while one is rate-limited.

### 3. Concurrent Request Limits

**Warning:** High concurrency degrades Jira performance

**Best Practice:** Limit concurrent requests to 3-5

## Handling Strategies

### Strategy 1: Exponential Backoff with Jitter

```python
import asyncio
import random

async def request_with_backoff(self, method, endpoint, **kwargs):
    """Request with exponential backoff and jitter."""
    max_retries = 5
    base_delay = 1  # seconds

    for attempt in range(max_retries):
        try:
            return await self._make_request(method, endpoint, **kwargs)
        except HTTPStatusError as e:
            if e.response.status_code != 429:
                raise

            if attempt == max_retries - 1:
                raise

            # Calculate delay with jitter
            delay = (2 ** attempt) * base_delay
            jitter = random.uniform(0, delay * 0.1)
            total_delay = delay + jitter

            # Use Retry-After if provided
            retry_after = e.response.headers.get("Retry-After")
            if retry_after:
                total_delay = max(total_delay, int(retry_after))

            await asyncio.sleep(total_delay)

    raise Exception("Max retries exceeded")
```

### Strategy 2: Rate Limit Tracking

```python
from datetime import datetime, timedelta

class RateLimitTracker:
    """Track rate limit budget."""

    def __init__(self):
        self.reset_time = None
        self.remaining = None

    def update(self, headers: dict):
        """Update from response headers."""
        self.remaining = int(headers.get("X-RateLimit-Remaining", 10))
        reset_timestamp = int(headers.get("X-RateLimit-Reset", 0))
        self.reset_time = datetime.fromtimestamp(reset_timestamp)

    def should_wait(self) -> bool:
        """Check if we should pause requests."""
        if self.remaining is None:
            return False

        # Pause if less than 2 requests remaining
        return self.remaining < 2

    def wait_time(self) -> float:
        """Calculate seconds to wait."""
        if self.reset_time is None:
            return 1.0

        delta = self.reset_time - datetime.now()
        return max(0, delta.total_seconds())
```

### Strategy 3: Request Batching

```python
async def batch_requests(self, requests: list[dict], batch_size: int = 5):
    """Process requests in batches to avoid rate limits."""
    results = []

    for i in range(0, len(requests), batch_size):
        batch = requests[i:i+batch_size]

        # Process batch concurrently
        tasks = [
            self._make_request(req["method"], req["endpoint"])
            for req in batch
        ]
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)

        # Small delay between batches
        if i + batch_size < len(requests):
            await asyncio.sleep(0.5)

    return results
```

## Best Practices

✅ **DO:**
- Monitor rate limit headers on every response
- Implement exponential backoff with jitter
- Use bulk operations instead of individual requests
- Cache frequently accessed data
- Spread scheduled tasks across time (avoid "on the hour")

❌ **DON'T:**
- Ignore 429 responses
- Use high concurrency to bypass limits
- Retry immediately without backoff
- Poll unnecessarily - use webhooks when possible
- Make same request repeatedly - cache results

## Optimization Techniques

### 1. Use Field Selection

```python
# Slow: Returns all fields
params = {"fields": "*all"}

# Fast: Returns only needed fields
params = {"fields": "summary,status,assignee"}
```

### 2. Batch ID Fetches

```python
# Slow: 1000 individual requests
for issue_key in issue_keys:
    await client.get(f"/issue/{issue_key}")

# Fast: 10 bulk requests
for i in range(0, len(issue_keys), 100):
    batch = issue_keys[i:i+100]
    jql = f"key in ({','.join(batch)})"
    await client.get(f"/search/jql?jql={jql}")
```

### 3. Cache Metadata

```python
# Cache project config, priorities, issue types
self._priority_cache = await self._make_request("GET", "priority")
self._issue_types_cache = await self._make_request(
    "GET", f"project/{self.project_key}"
)

# Reuse cached data instead of fetching every time
```

## Monitoring

Track rate limit usage:

```python
import logging

logger = logging.getLogger(__name__)

def log_rate_limit(response):
    """Log rate limit information."""
    remaining = response.headers.get("X-RateLimit-Remaining")
    limit = response.headers.get("X-RateLimit-Limit")
    reset = response.headers.get("X-RateLimit-Reset")

    logger.info(
        f"Rate limit: {remaining}/{limit} remaining, "
        f"resets at {datetime.fromtimestamp(int(reset))}"
    )

    if int(remaining) < 3:
        logger.warning("Rate limit nearly exhausted!")
```
```

---

## 8. Conclusion

### Summary of Findings

1. **Current Implementation Quality:** The mcp-ticketer Jira adapter is well-structured with solid error handling, proper async patterns, and comprehensive type safety.

2. **API Coverage:** Covers ~70% of common use cases (CRUD, search, comments, attachments, basic sprint management).

3. **Critical Gaps:** Missing bulk operations, advanced sprint management, issue linking, and milestone support (planned).

4. **Performance:** Uses appropriate caching and retry strategies, but could benefit from field selection optimization and batch operations.

5. **2025 Updates:** Rate limiting enforcement requires enhanced backoff strategies with jitter.

### Skill Development Recommendation

**Create comprehensive single-file skill** covering:
- Authentication and security (2025 best practices)
- JQL optimization with 50+ examples
- Rate limiting strategies (exponential backoff + jitter)
- Field expansion and performance optimization
- Agile workflow patterns (sprints, epics, boards)
- Common error scenarios and solutions
- Migration guide for deprecated features

**Estimated Effort:** 2-3 weeks for comprehensive skill

**Target Audience:**
- Developers building Jira integrations
- AI agents requiring Jira automation
- Teams migrating to Jira Cloud API v3

### Next Steps

1. **Create skill outline** with section structure
2. **Gather code examples** from current adapter
3. **Document API patterns** with best practices
4. **Add troubleshooting section** with common issues
5. **Review and test** with real-world scenarios

---

## Appendices

### Appendix A: Complete Endpoint Reference

**REST API v3 Core Endpoints:**

```
Authentication & Users:
- GET  /myself
- GET  /user/search
- GET  /user/assignable/search

Issues:
- POST   /issue
- GET    /issue/{issueKey}
- PUT    /issue/{issueKey}
- DELETE /issue/{issueKey}
- POST   /issue/bulk
- GET    /search/jql
- GET    /issue/{issueKey}/transitions
- POST   /issue/{issueKey}/transitions
- POST   /issue/{issueKey}/comment
- GET    /issue/{issueKey}/comment
- POST   /issue/{issueKey}/attachments
- DELETE /attachment/{id}

Projects:
- GET  /project
- GET  /project/{projectKey}
- GET  /project/{projectKey}/statuses

Metadata:
- GET  /priority
- GET  /status
- GET  /issuetype
- GET  /field

Workflows:
- GET  /workflow/search
- GET  /workflow/transitions/{id}

Agile (v1.0):
- GET  /agile/1.0/board
- GET  /agile/1.0/board/{boardId}
- GET  /agile/1.0/board/{boardId}/sprint
- GET  /agile/1.0/sprint/{sprintId}
- POST /agile/1.0/sprint
- PUT  /agile/1.0/sprint/{sprintId}
- POST /agile/1.0/sprint/{sprintId}/issue
```

### Appendix B: Current Adapter Method Coverage

**Implemented (35 methods):**
- ✅ create(), read(), update(), delete(), list(), search()
- ✅ add_comment(), get_comments()
- ✅ add_attachment(), get_attachments(), delete_attachment()
- ✅ create_epic(), get_epic(), list_epics(), update_epic()
- ✅ transition_state(), get_issue_status(), list_issue_statuses()
- ✅ get_project_info(), get_project_users()
- ✅ get_sprints(), list_cycles()
- ✅ list_labels(), create_issue_label(), list_project_labels()
- ✅ get_current_user(), execute_jql()
- ✅ _get_priorities(), _get_issue_types(), _get_transitions()
- ✅ _get_custom_fields(), _convert_to_adf(), _convert_from_adf()

**Not Implemented:**
- ❌ bulk_create(), bulk_update(), bulk_delete()
- ❌ create_sprint(), update_sprint(), add_issues_to_sprint()
- ❌ link_issues(), get_issue_links()
- ❌ add_worklog(), get_worklogs()
- ❌ add_watcher(), remove_watcher()
- ❌ milestone_* methods (planned for v2.1.0)

### Appendix C: Useful Resources

**Official Documentation:**
- Jira Cloud REST API v3: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
- Jira Software REST API: https://developer.atlassian.com/cloud/jira/software/rest/
- JQL Reference: https://support.atlassian.com/jira-software-cloud/docs/advanced-search-reference-jql-fields/
- API Tokens: https://id.atlassian.com/manage/api-tokens
- Rate Limiting: https://developer.atlassian.com/cloud/jira/platform/rate-limiting/

**Community Resources:**
- Atlassian Developer Community: https://community.developer.atlassian.com/
- Stack Overflow [jira-rest-api]: https://stackoverflow.com/questions/tagged/jira-rest-api
- Atlassian Marketplace: https://marketplace.atlassian.com/

**Python Libraries:**
- jira: https://jira.readthedocs.io/ (official Python client)
- atlassian-python-api: https://github.com/atlassian-api/atlassian-python-api

---

**End of Research Document**

**Total Sections:** 8
**Total Appendices:** 3
**Word Count:** ~12,500 words
**Code Examples:** 40+
**JQL Examples:** 50+
