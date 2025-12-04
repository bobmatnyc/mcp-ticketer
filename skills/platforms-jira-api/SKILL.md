# platforms-jira-api

Jira REST API v3 integration patterns for issue tracking, sprint management, and JQL query optimization. Production-ready patterns for 2025 rate limiting, field expansion, and workflow management.

## When to Use This Skill

- Building Jira issue integrations and automation
- Implementing sprint/epic/backlog management
- Optimizing JQL queries for performance
- Handling 2025 rate limiting enforcement
- Automating Jira workflows and transitions
- Managing Jira Cloud or Server/Data Center

## Quick Start (Entry Point)

### Authentication Setup (API Tokens - Recommended 2025)

```python
import httpx

# API Token Authentication (Jira Cloud)
auth = httpx.BasicAuth(
    username="your.email@company.com",
    password="your_api_token_here"  # From https://id.atlassian.com/manage/api-tokens
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

### Base URL Patterns

**Jira Cloud (API v3):**
```
https://{domain}.atlassian.net/rest/api/3/{endpoint}
```

**Jira Server/Data Center (API v2):**
```
https://{domain}/rest/api/2/{endpoint}
```

**Agile API (Sprints/Boards):**
```
https://{domain}.atlassian.net/rest/agile/1.0/{endpoint}
```

### Critical 2025 Rate Limiting Update

**Effective November 22, 2025:** Strict enforcement of 10 requests/second per API token.

```python
# Rate limit headers to monitor
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 5
X-RateLimit-Reset: 1638360000
Retry-After: 30  # Seconds to wait on 429 response
```

### Common Operations Teaser

```python
# Create issue
POST /rest/api/3/issue

# Search with JQL (optimized endpoint)
GET /rest/api/3/search/jql?jql=project=PROJ AND status="In Progress"

# Get sprint issues
GET /rest/agile/1.0/sprint/{sprintId}/issue

# Transition workflow state
POST /rest/api/3/issue/{issueKey}/transitions
```

### JQL Performance Tiers

**Fast (Indexed):** project, status, priority, assignee, created/updated
**Moderate:** labels, sprint, fixVersion
**Slow (Full Scan):** text search, custom fields, description

### Common Pitfalls Preview

- ❌ Using `text ~` instead of field-specific search (10x slower)
- ❌ Ignoring rate limit headers (causes 429 errors)
- ❌ Not using project scoping in JQL (massive performance hit)
- ❌ Requesting `fields=*all` when only need specific fields
- ❌ Using deprecated Epic Link instead of Parent field

---

**Load Full Content Below for Comprehensive Guide (8,000+ tokens)**

---

## FULL CONTENT: Complete Jira REST API v3 Reference

## Table of Contents

1. [Authentication Methods](#authentication-methods)
2. [Rate Limiting (2025 Updates)](#rate-limiting-2025-updates)
3. [JQL Mastery](#jql-mastery)
4. [Issue Management](#issue-management)
5. [Sprint and Agile APIs](#sprint-and-agile-apis)
6. [Project and Workflow APIs](#project-and-workflow-apis)
7. [Pagination Strategies](#pagination-strategies)
8. [Error Handling](#error-handling)
9. [Best Practices](#best-practices)
10. [Common Pitfalls](#common-pitfalls)
11. [Code Examples](#code-examples)
12. [2025 API Changes](#2025-api-changes)

---

## Authentication Methods

### API Token Authentication (Recommended 2025)

**Generate API Token:**
1. Navigate to https://id.atlassian.com/manage/api-tokens
2. Click "Create API token"
3. Name: "mcp-ticketer-production"
4. Copy token immediately (not shown again)

**Python Implementation:**

```python
import httpx
from httpx import AsyncClient, HTTPStatusError

class JiraClient:
    def __init__(self, server: str, email: str, api_token: str):
        self.server = server.rstrip("/")
        self.api_base = f"{self.server}/rest/api/3"

        # Basic Auth with API token
        self.auth = httpx.BasicAuth(email, api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    async def get_client(self) -> AsyncClient:
        return AsyncClient(
            auth=self.auth,
            headers=self.headers,
            timeout=30,
            verify=True
        )

    async def validate_credentials(self):
        """Test authentication with /myself endpoint."""
        async with await self.get_client() as client:
            try:
                response = await client.get(f"{self.api_base}/myself")
                response.raise_for_status()
                user = response.json()
                return True, user.get("displayName")
            except HTTPStatusError as e:
                if e.response.status_code == 401:
                    return False, "Invalid credentials"
                elif e.response.status_code == 403:
                    return False, "Insufficient permissions"
                raise
```

### OAuth 2.0 (User-Authorized Apps)

**When to Use:**
- User-authorized applications requiring consent
- Granular permission scopes
- Token refresh mechanism

**Flow:**
```python
# 3-legged OAuth flow
# 1. Direct user to authorization URL
auth_url = f"https://auth.atlassian.com/authorize?audience=api.atlassian.com&client_id={client_id}&scope={scopes}&redirect_uri={redirect_uri}&response_type=code"

# 2. Exchange code for access token
token_response = requests.post(
    "https://auth.atlassian.com/oauth/token",
    data={
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": authorization_code,
        "redirect_uri": redirect_uri
    }
)

access_token = token_response.json()["access_token"]

# 3. Use access token
headers = {"Authorization": f"Bearer {access_token}"}
```

### Personal Access Tokens (Server/Data Center)

```python
# PAT authentication (Server/Data Center only)
headers = {
    "Authorization": f"Bearer {personal_access_token}",
    "Content-Type": "application/json"
}
```

### Security Best Practices

✅ **DO:**
- Store tokens in environment variables or secure vault (e.g., AWS Secrets Manager)
- Rotate tokens every 90 days
- Use separate tokens for dev/staging/production
- Revoke tokens immediately when compromised
- Use HTTPS only

❌ **DON'T:**
- Hard-code tokens in source code
- Commit tokens to version control
- Share tokens between users or applications
- Use same token for multiple environments
- Log tokens in plaintext

---

## Rate Limiting (2025 Updates)

### Critical Changes (Effective Nov 22, 2025)

Atlassian now enforces **strict rate limits** on all API tokens.

### Rate Limit Types

#### 1. Per-App Rate Limits

**Limit:** ~10 requests/second per API token

**Response Headers:**
```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 3
X-RateLimit-Reset: 1701234567
```

**Response When Exceeded:**
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 30
```

#### 2. Per-Issue Write Limits (NEW in 2025)

**Purpose:** Prevent excessive updates to single issue

**Triggers:** Multiple writes to same issue in short time

**Response:**
```http
HTTP/1.1 429 Too Many Requests
RateLimit-Reason: jira-per-issue-on-write
Retry-After: 60
```

**Important:** This limit is per-issue, not global. Other issues can still be updated.

#### 3. Concurrent Request Limits

**Warning:** High concurrency (>5 simultaneous requests) degrades Jira performance

**Best Practice:** Limit concurrent requests to 3-5

### Handling Strategies

#### Strategy 1: Exponential Backoff with Jitter

```python
import asyncio
import random
from httpx import HTTPStatusError

async def request_with_backoff(
    self,
    method: str,
    endpoint: str,
    max_retries: int = 5,
    **kwargs
):
    """Request with exponential backoff and jitter."""
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

            # Check if per-issue write limit
            reason = e.response.headers.get("RateLimit-Reason", "")
            if reason == "jira-per-issue-on-write":
                # This issue is locked, wait longer
                total_delay = max(total_delay, 60)

            await asyncio.sleep(total_delay)

    raise Exception("Max retries exceeded")
```

#### Strategy 2: Rate Limit Tracking

```python
from datetime import datetime

class RateLimitTracker:
    """Track rate limit budget from response headers."""

    def __init__(self):
        self.reset_time = None
        self.remaining = None

    def update(self, headers: dict):
        """Update from response headers."""
        self.remaining = int(headers.get("X-RateLimit-Remaining", 10))
        reset_timestamp = int(headers.get("X-RateLimit-Reset", 0))
        if reset_timestamp:
            self.reset_time = datetime.fromtimestamp(reset_timestamp)

    def should_wait(self) -> bool:
        """Check if we should pause requests."""
        if self.remaining is None:
            return False
        # Pause if less than 2 requests remaining
        return self.remaining < 2

    def wait_time(self) -> float:
        """Calculate seconds to wait."""
        if not self.reset_time:
            return 1.0
        delta = self.reset_time - datetime.now()
        return max(0, delta.total_seconds())
```

#### Strategy 3: Request Batching

```python
async def batch_requests(
    self,
    requests: list[dict],
    batch_size: int = 5,
    delay_between_batches: float = 0.5
):
    """Process requests in batches to avoid rate limits."""
    results = []

    for i in range(0, len(requests), batch_size):
        batch = requests[i:i+batch_size]

        # Process batch concurrently
        tasks = [
            self._make_request(req["method"], req["endpoint"])
            for req in batch
        ]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        results.extend(batch_results)

        # Small delay between batches
        if i + batch_size < len(requests):
            await asyncio.sleep(delay_between_batches)

    return results
```

### Optimization Techniques

#### 1. Use Field Selection

```python
# Slow: Returns all fields (hundreds of KB per issue)
params = {"fields": "*all"}

# Fast: Returns only needed fields (few KB per issue)
params = {"fields": "summary,status,assignee,priority"}
```

#### 2. Batch ID Fetches

```python
# Slow: 1000 individual requests
for issue_key in issue_keys:
    await client.get(f"/issue/{issue_key}")

# Fast: 10 bulk requests (100 issues each)
for i in range(0, len(issue_keys), 100):
    batch = issue_keys[i:i+100]
    jql = f"key in ({','.join(batch)})"
    await client.get(f"/search/jql?jql={jql}&maxResults=100")
```

#### 3. Cache Metadata

```python
# Cache project config, priorities, issue types (rarely change)
class JiraClient:
    def __init__(self):
        self._priority_cache = None
        self._issue_types_cache = {}
        self._custom_fields_cache = {}

    async def get_priorities(self):
        if not self._priority_cache:
            self._priority_cache = await self._make_request("GET", "priority")
        return self._priority_cache
```

### Best Practices

✅ **DO:**
- Monitor rate limit headers on every response
- Implement exponential backoff with jitter
- Use bulk operations instead of individual requests
- Cache frequently accessed data
- Spread scheduled tasks across time (avoid "on the hour")
- Use webhooks instead of polling when possible

❌ **DON'T:**
- Ignore 429 responses
- Use high concurrency to bypass limits
- Retry immediately without backoff
- Poll unnecessarily
- Make same request repeatedly without caching

---

## JQL Mastery

### Performance Tiers

| Tier | Speed | Fields |
|------|-------|--------|
| **Tier 1: Fastest** | Indexed | project, issueType, status, priority, assignee, reporter, created, updated |
| **Tier 2: Moderate** | Partial Index | labels, fixVersion, component, sprint |
| **Tier 3: Slowest** | Full Scan | text (all fields), description, custom fields (unless indexed) |

### Optimization Patterns

#### Pattern 1: Project Scoping (Critical)

```jql
-- Slow: Searches entire Jira instance
status = "In Progress" AND assignee = currentUser()

-- Fast: Scoped to project (uses index)
project = PROJ AND status = "In Progress" AND assignee = currentUser()
```

**Why:** Always include project filter. Reduces search space by 100x-1000x.

#### Pattern 2: Field-Specific Search

```jql
-- Slow: Searches ALL text fields (summary, description, comments, etc.)
text ~ "authentication bug"

-- Fast: Searches specific fields only
summary ~ "authentication" OR description ~ "bug"
```

**Performance Gain:** 5-10x faster

#### Pattern 3: Positive Lists vs Negation

```jql
-- Slow: Requires checking every priority
priority != Low AND priority != Lowest

-- Fast: Positive matching uses index
priority IN (Critical, High, Medium)
```

#### Pattern 4: Date Range Optimization

```jql
-- Slow: String comparison
created > "2025-01-01" AND created < "2025-12-31"

-- Fast: JQL functions are optimized
created >= startOfYear() AND created <= endOfYear()
```

### JQL Syntax Reference

#### Basic Operators

```jql
-- Equality
status = "In Progress"
priority = High

-- Inequality
status != Done

-- IN/NOT IN
priority IN (High, Critical)
status NOT IN (Done, Closed)

-- Comparison
created >= -7d
"Story Points" > 5

-- Text search (contains)
summary ~ "authentication"
description ~ "bug"

-- Empty/Not Empty
assignee is EMPTY
labels is not EMPTY
```

#### Date Functions

```jql
-- Relative dates
created >= -7d           -- Last 7 days
updated <= -1w           -- Older than 1 week
dueDate < now()          -- Overdue

-- Time-based functions
created >= startOfWeek()
updated >= startOfDay(-7d)
dueDate <= endOfMonth()
resolved > startOfYear()

-- Date ranges
created >= startOfWeek() AND created <= endOfWeek()
```

#### User Functions

```jql
-- Current user
assignee = currentUser()
reporter = currentUser()
watcher = currentUser()

-- Team membership
reporter in membersOf("engineering-team")
assignee in membersOf("frontend-developers")

-- User activity
assignee was currentUser()
assignee changed from currentUser() to "john.doe"
```

### Epic and Hierarchy Queries

```jql
-- Method 1: Epic Link (Legacy - deprecated Feb 2024)
"Epic Link" = PROJ-123

-- Method 2: Parent Field (New - recommended)
parent = PROJ-123

-- Method 3: Issue Function
issueFunction in subtasksOf("Epic Name")

-- All stories in epic (including sub-tasks)
"Epic Link" = PROJ-123 OR parent = PROJ-123

-- Epics without children
type = Epic AND issueFunction not in parentsOf("type != Epic")
```

### Sprint Queries

```jql
-- Active sprint items
sprint in openSprints() AND project = PROJ

-- Specific sprint
sprint = 42

-- Sprint backlog (incomplete items)
sprint = 42 AND status != Done

-- Sprint history
sprint in closedSprints() ORDER BY sprint DESC

-- Issues moved between sprints
sprint changed from 41 to 42 during (startOfDay(-7d), now())

-- Items not in any sprint (backlog)
sprint is EMPTY AND project = PROJ
```

### Advanced Queries

#### Blocked Issues

```jql
-- Using status
status = Blocked

-- Using issue links
issueFunction in linkedIssuesOf("project = PROJ", "is blocked by")
```

#### Unestimated Work

```jql
-- Story points empty
"Story Points" is EMPTY AND type = Story

-- Original estimate missing
originalEstimate is EMPTY
```

#### Overdue Items

```jql
-- Simple overdue
dueDate < now() AND status NOT IN (Done, Closed)

-- High priority overdue
dueDate < now() AND priority IN (Critical, High) AND status != Done
```

#### Stale Issues

```jql
-- Not updated in 30 days
updated <= -30d AND status NOT IN (Done, Closed)

-- Created but never assigned
created <= -7d AND assignee is EMPTY AND status = "To Do"
```

### Custom Field Queries

```jql
-- By field ID (always works)
cf[10014] = "Epic-123"
cf[10015] >= 5  -- Story Points

-- By field name (if supported)
"Epic Link" = "Epic-123"
"Story Points" >= 5
"Sprint" = "Sprint 23"
```

### Complex Combined Queries

```jql
-- Current sprint high priority items
project = PROJ
  AND sprint in openSprints()
  AND priority IN (Critical, High)
  AND status != Done
ORDER BY priority DESC, updated DESC

-- Recently created bugs assigned to team
project = PROJ
  AND type = Bug
  AND created >= -7d
  AND assignee in membersOf("qa-team")
  AND status IN ("To Do", "In Progress")

-- Epic progress query
"Epic Link" = PROJ-123
  AND status IN ("To Do", "In Progress", "In Review")
ORDER BY priority DESC, created ASC
```

### 50+ JQL Examples Library

#### Project Management

```jql
-- 1. All open items in project
project = PROJ AND status != Done

-- 2. High priority backlog
project = PROJ AND sprint is EMPTY AND priority IN (High, Critical)

-- 3. Items created this week
project = PROJ AND created >= startOfWeek()

-- 4. Recently updated issues
project = PROJ AND updated >= -1d ORDER BY updated DESC

-- 5. Overdue tasks
project = PROJ AND dueDate < now() AND status NOT IN (Done, Closed)
```

#### Sprint Planning

```jql
-- 6. Current sprint items
sprint in openSprints() AND project = PROJ

-- 7. Sprint backlog (not done)
sprint = 42 AND status NOT IN (Done, Closed)

-- 8. Sprint completed items
sprint = 42 AND status = Done

-- 9. Sprint scope creep (added after start)
sprint = 42 AND sprint changed after startOfSprint(42)

-- 10. Next sprint candidates
sprint is EMPTY AND priority = High AND status = "Ready"
```

#### Team Management

```jql
-- 11. My open tasks
assignee = currentUser() AND status NOT IN (Done, Closed)

-- 12. My items in current sprint
assignee = currentUser() AND sprint in openSprints()

-- 13. Unassigned items
assignee is EMPTY AND project = PROJ AND status = "To Do"

-- 14. Team workload
assignee in membersOf("dev-team") AND status = "In Progress"

-- 15. Items I'm watching
watcher = currentUser() AND status NOT IN (Done, Closed)
```

#### Bug Tracking

```jql
-- 16. Open bugs
type = Bug AND status NOT IN (Done, Closed)

-- 17. Critical bugs
type = Bug AND priority = Critical AND status != Done

-- 18. Recent regression bugs
type = Bug AND labels = regression AND created >= -7d

-- 19. Bugs in production
type = Bug AND environment = production AND status = Open

-- 20. Bugs reported by customers
type = Bug AND reporter in membersOf("customer-support")
```

#### Epic Management

```jql
-- 21. Active epics
type = Epic AND status NOT IN (Done, Closed)

-- 22. Epic progress
"Epic Link" = PROJ-123 ORDER BY status, priority DESC

-- 23. Epics with no stories
type = Epic AND issueFunction not in parentsOf("type != Epic")

-- 24. Blocked epics
type = Epic AND status = Blocked

-- 25. Epics due this quarter
type = Epic AND dueDate >= startOfMonth(-2) AND dueDate <= endOfMonth(2)
```

#### Quality Assurance

```jql
-- 26. Items in testing
status = Testing

-- 27. Failed QA items
status = "Failed QA" OR labels = qa-failed

-- 28. Ready for QA
status = "Ready for QA" AND assignee is EMPTY

-- 29. Items tested this week
status changed to Done during (startOfWeek(), now())

-- 30. Reopened issues
status = Reopened OR status changed to "To Do" after status was Done
```

#### Release Management

```jql
-- 31. Items in next release
fixVersion = "v2.0" AND status NOT IN (Done, Closed)

-- 32. Release blockers
fixVersion = "v2.0" AND priority = Critical AND status != Done

-- 33. Completed in release
fixVersion = "v2.0" AND status = Done

-- 34. Release candidates
fixVersion is EMPTY AND status = Done AND labels = release-candidate

-- 35. Items missing fix version
status = Done AND fixVersion is EMPTY AND type IN (Bug, Story)
```

#### Technical Debt

```jql
-- 36. Tech debt items
labels = tech-debt AND status NOT IN (Done, Closed)

-- 37. Old debt items (>90 days)
labels = tech-debt AND created <= -90d AND status = Open

-- 38. High priority debt
labels = tech-debt AND priority IN (High, Critical)

-- 39. Refactoring tasks
summary ~ "refactor" OR labels = refactoring

-- 40. Code quality issues
labels IN (code-smell, maintainability, performance)
```

#### Workflow State Tracking

```jql
-- 41. Items in code review
status = "In Review" OR labels = code-review

-- 42. Blocked items
status = Blocked OR labels = blocked

-- 43. Waiting on external
status = Waiting OR labels = external-dependency

-- 44. Long-running items (>14 days in progress)
status = "In Progress" AND status changed to "In Progress" before -14d

-- 45. Items that moved backwards
status changed from Done to "In Progress"
```

#### Component-Based

```jql
-- 46. Frontend items
component = "Frontend" AND status NOT IN (Done, Closed)

-- 47. Backend bugs
type = Bug AND component = "Backend"

-- 48. Infrastructure tasks
component = "Infrastructure" AND type = Task

-- 49. Cross-component items
component in (Frontend, Backend, API) AND type = Story

-- 50. Items missing component
component is EMPTY AND project = PROJ
```

#### Performance Optimization Examples

```jql
-- 51. FAST: Indexed field search
project = PROJ AND status = "In Progress" AND assignee = currentUser()

-- 52. SLOW: Text search (avoid if possible)
text ~ "authentication" AND project = PROJ

-- 53. FAST: Field-specific search
(summary ~ "authentication" OR description ~ "authentication") AND project = PROJ

-- 54. FAST: Positive list
priority IN (High, Critical) AND project = PROJ

-- 55. SLOW: Negative condition
priority != Low AND project = PROJ
```

### JQL Anti-Patterns to Avoid

```jql
-- ❌ DON'T: Missing project scope
status = "In Progress"

-- ✅ DO: Include project
project = PROJ AND status = "In Progress"

-- ❌ DON'T: Generic text search
text ~ "bug"

-- ✅ DO: Field-specific search
summary ~ "bug" OR labels = bug

-- ❌ DON'T: Negative conditions
priority != Low AND priority != Lowest

-- ✅ DO: Positive lists
priority IN (Critical, High, Medium)

-- ❌ DON'T: Slow date formats
created > "2025-01-01"

-- ✅ DO: JQL date functions
created >= startOfYear()
```

---

## Issue Management

### Create Issue

```python
async def create_issue(
    self,
    project_key: str,
    summary: str,
    description: str,
    issue_type: str = "Task",
    priority: str = "Medium",
    labels: list[str] = None,
    assignee_account_id: str = None,
    parent_key: str = None,  # For subtasks or child issues
):
    """Create Jira issue with comprehensive field support."""

    # Convert description to ADF format (Jira Cloud requirement)
    adf_description = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": line}]
            }
            for line in description.split("\n") if line.strip()
        ]
    }

    fields = {
        "project": {"key": project_key},
        "summary": summary,
        "description": adf_description,
        "issuetype": {"name": issue_type},
        "priority": {"name": priority},
    }

    # Optional fields
    if labels:
        fields["labels"] = labels

    if assignee_account_id:
        fields["assignee"] = {"accountId": assignee_account_id}

    if parent_key:
        fields["parent"] = {"key": parent_key}

    response = await self._make_request(
        "POST",
        "issue",
        data={"fields": fields}
    )

    return response.get("key")  # Returns issue key (e.g., PROJ-123)
```

### Read Issue

```python
async def read_issue(
    self,
    issue_key: str,
    expand: list[str] = None,
    fields: list[str] = None
):
    """Read issue with field expansion control."""

    params = {}

    # Control field expansion for performance
    if expand:
        # Options: renderedFields, changelog, transitions, operations
        params["expand"] = ",".join(expand)

    if fields:
        # Specific fields only (saves bandwidth)
        params["fields"] = ",".join(fields)
    else:
        # Default: all fields
        params["fields"] = "*all"

    try:
        issue = await self._make_request("GET", f"issue/{issue_key}", params=params)
        return issue
    except HTTPStatusError as e:
        if e.response.status_code == 404:
            return None
        raise
```

### Update Issue

```python
async def update_issue(
    self,
    issue_key: str,
    summary: str = None,
    description: str = None,
    priority: str = None,
    assignee_account_id: str = None,
    labels: list[str] = None,
):
    """Update issue fields."""

    fields = {}

    if summary:
        fields["summary"] = summary

    if description:
        # Convert to ADF
        fields["description"] = self._convert_to_adf(description)

    if priority:
        fields["priority"] = {"name": priority}

    if assignee_account_id:
        fields["assignee"] = {"accountId": assignee_account_id}

    if labels is not None:  # Allow empty list to clear labels
        fields["labels"] = labels

    if not fields:
        raise ValueError("At least one field must be updated")

    await self._make_request(
        "PUT",
        f"issue/{issue_key}",
        data={"fields": fields}
    )
```

### Delete Issue

```python
async def delete_issue(self, issue_key: str) -> bool:
    """Delete issue (permanent)."""
    try:
        await self._make_request("DELETE", f"issue/{issue_key}")
        return True
    except HTTPStatusError as e:
        if e.response.status_code == 404:
            return False  # Already deleted
        raise
```

### Search Issues

```python
async def search_issues(
    self,
    jql: str,
    start_at: int = 0,
    max_results: int = 50,
    fields: list[str] = None,
    expand: list[str] = None,
):
    """Search issues using JQL."""

    params = {
        "jql": jql,
        "startAt": start_at,
        "maxResults": max_results,
    }

    if fields:
        params["fields"] = ",".join(fields)
    else:
        params["fields"] = "*all"

    if expand:
        params["expand"] = ",".join(expand)

    data = await self._make_request("GET", "search/jql", params=params)

    return {
        "total": data.get("total", 0),
        "startAt": data.get("startAt", 0),
        "maxResults": data.get("maxResults", 0),
        "issues": data.get("issues", [])
    }
```

### Transitions (Workflow State Changes)

```python
async def get_transitions(self, issue_key: str):
    """Get available transitions for issue."""
    data = await self._make_request("GET", f"issue/{issue_key}/transitions")
    return data.get("transitions", [])

async def transition_issue(
    self,
    issue_key: str,
    transition_id: str,
    comment: str = None,
    resolution: str = None,
):
    """Execute workflow transition."""

    data = {
        "transition": {"id": transition_id}
    }

    # Optional comment
    if comment:
        data["update"] = {
            "comment": [{
                "add": {
                    "body": {
                        "type": "doc",
                        "version": 1,
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": comment}]
                        }]
                    }
                }
            }]
        }

    # Optional resolution
    if resolution:
        data["fields"] = {
            "resolution": {"name": resolution}
        }

    await self._make_request(
        "POST",
        f"issue/{issue_key}/transitions",
        data=data
    )
```

### Comments

```python
async def add_comment(self, issue_key: str, text: str):
    """Add comment to issue."""
    data = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [{
                "type": "paragraph",
                "content": [{"type": "text", "text": text}]
            }]
        }
    }

    response = await self._make_request(
        "POST",
        f"issue/{issue_key}/comment",
        data=data
    )
    return response

async def get_comments(
    self,
    issue_key: str,
    start_at: int = 0,
    max_results: int = 50
):
    """Get issue comments with pagination."""
    params = {
        "expand": "comments",
        "fields": "comment",
    }

    issue = await self._make_request("GET", f"issue/{issue_key}", params=params)
    comments_data = issue.get("fields", {}).get("comment", {})

    all_comments = comments_data.get("comments", [])

    # Manual pagination
    paginated = all_comments[start_at:start_at + max_results]

    return {
        "total": len(all_comments),
        "comments": paginated
    }
```

### Attachments

```python
async def add_attachment(
    self,
    issue_key: str,
    file_path: str
):
    """Upload attachment to issue."""
    from pathlib import Path

    file = Path(file_path)
    if not file.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    headers = {
        "X-Atlassian-Token": "no-check",
        # Don't set Content-Type - httpx handles multipart
    }

    with open(file, "rb") as f:
        files = {"file": (file.name, f, "application/octet-stream")}

        url = f"{self.api_base}/issue/{issue_key}/attachments"

        async with await self.get_client() as client:
            response = await client.post(
                url,
                files=files,
                headers={**self.headers, **headers}
            )
            response.raise_for_status()
            return response.json()[0]  # Returns array with single attachment

async def delete_attachment(self, attachment_id: str) -> bool:
    """Delete attachment."""
    try:
        await self._make_request("DELETE", f"attachment/{attachment_id}")
        return True
    except HTTPStatusError as e:
        if e.response.status_code == 404:
            return False
        raise
```

---

## Sprint and Agile APIs

### Get Boards

```python
async def get_boards(
    self,
    project_key: str = None,
    start_at: int = 0,
    max_results: int = 50
):
    """Get Agile boards (requires Jira Software)."""
    params = {
        "startAt": start_at,
        "maxResults": max_results
    }

    if project_key:
        params["projectKeyOrId"] = project_key

    data = await self._make_request("GET", "/rest/agile/1.0/board", params=params)
    return data.get("values", [])
```

### Get Sprints

```python
async def get_sprints(
    self,
    board_id: int,
    state: str = None,  # active, closed, future
    start_at: int = 0,
    max_results: int = 50
):
    """Get sprints for board."""
    params = {
        "startAt": start_at,
        "maxResults": max_results
    }

    if state:
        params["state"] = state

    data = await self._make_request(
        "GET",
        f"/rest/agile/1.0/board/{board_id}/sprint",
        params=params
    )
    return data.get("values", [])
```

### Create Sprint

```python
async def create_sprint(
    self,
    name: str,
    board_id: int,
    start_date: str = None,  # ISO format: 2025-01-01T00:00:00.000Z
    end_date: str = None,
    goal: str = None
):
    """Create new sprint."""
    data = {
        "name": name,
        "originBoardId": board_id
    }

    if start_date:
        data["startDate"] = start_date
    if end_date:
        data["endDate"] = end_date
    if goal:
        data["goal"] = goal

    response = await self._make_request("POST", "/rest/agile/1.0/sprint", data=data)
    return response
```

### Add Issues to Sprint

```python
async def add_issues_to_sprint(
    self,
    sprint_id: int,
    issue_keys: list[str]
):
    """Move issues to sprint."""
    data = {"issues": issue_keys}

    await self._make_request(
        "POST",
        f"/rest/agile/1.0/sprint/{sprint_id}/issue",
        data=data
    )
```

### Get Sprint Issues

```python
async def get_sprint_issues(
    self,
    sprint_id: int,
    start_at: int = 0,
    max_results: int = 50,
    jql: str = None
):
    """Get issues in sprint."""
    params = {
        "startAt": start_at,
        "maxResults": max_results
    }

    if jql:
        params["jql"] = jql

    data = await self._make_request(
        "GET",
        f"/rest/agile/1.0/sprint/{sprint_id}/issue",
        params=params
    )

    return {
        "total": data.get("total", 0),
        "issues": data.get("issues", [])
    }
```

### Sprint Progress Calculation

```python
async def calculate_sprint_progress(self, sprint_id: int):
    """Calculate sprint completion percentage."""

    # Get all sprint issues
    issues = await self.get_sprint_issues(sprint_id, max_results=1000)

    total = len(issues["issues"])
    if total == 0:
        return {"total": 0, "done": 0, "percentage": 0}

    done_count = sum(
        1 for issue in issues["issues"]
        if issue["fields"]["status"]["statusCategory"]["key"] == "done"
    )

    return {
        "total": total,
        "done": done_count,
        "in_progress": total - done_count,
        "percentage": round((done_count / total) * 100, 1)
    }
```

---

## Project and Workflow APIs

### Get Project

```python
async def get_project(self, project_key: str):
    """Get project details."""
    return await self._make_request("GET", f"project/{project_key}")
```

### Get Project Statuses

```python
async def get_project_statuses(self, project_key: str):
    """Get all workflow statuses for project."""
    data = await self._make_request("GET", f"project/{project_key}/statuses")

    # Extract unique statuses from all issue types
    status_map = {}
    for issue_type_data in data:
        for status in issue_type_data.get("statuses", []):
            status_id = status.get("id")
            if status_id not in status_map:
                status_map[status_id] = status

    return list(status_map.values())
```

### Get Custom Fields

```python
async def get_custom_fields(self):
    """Get all custom field definitions."""
    fields = await self._make_request("GET", "field")

    # Filter to custom fields only
    custom_fields = {
        field["name"]: {
            "id": field["id"],
            "key": field.get("key"),
            "type": field.get("schema", {}).get("type"),
            "custom": field.get("custom", False)
        }
        for field in fields
        if field.get("custom", False)
    }

    return custom_fields
```

### Get Issue Types

```python
async def get_issue_types(self, project_key: str):
    """Get issue types for project."""
    project = await self._make_request("GET", f"project/{project_key}")
    return project.get("issueTypes", [])
```

### Get Priorities

```python
async def get_priorities(self):
    """Get all priority levels."""
    return await self._make_request("GET", "priority")
```

---

## Pagination Strategies

### Offset-Based Pagination (Standard)

```python
async def paginate_search(
    self,
    jql: str,
    page_size: int = 50,
    max_pages: int = None
):
    """Paginate through JQL search results."""
    start_at = 0
    page = 0
    all_issues = []

    while True:
        data = await self.search_issues(
            jql=jql,
            start_at=start_at,
            max_results=page_size
        )

        issues = data["issues"]
        all_issues.extend(issues)

        # Check if more results exist
        if len(issues) < page_size:
            break  # Last page

        # Check max pages limit
        page += 1
        if max_pages and page >= max_pages:
            break

        start_at += page_size

    return all_issues
```

### Bulk Fetch Pattern (High Performance)

```python
async def bulk_fetch_issues(self, issue_keys: list[str]):
    """Efficiently fetch many issues."""

    # Step 1: Fetch IDs in batches
    batch_size = 100
    all_issues = []

    for i in range(0, len(issue_keys), batch_size):
        batch = issue_keys[i:i+batch_size]

        # Build JQL for batch
        jql = f"key in ({','.join(batch)})"

        # Fetch batch
        data = await self.search_issues(
            jql=jql,
            max_results=batch_size,
            fields=["*all"]
        )

        all_issues.extend(data["issues"])

    return all_issues
```

---

## Error Handling

### Common HTTP Status Codes

| Code | Meaning | Handling |
|------|---------|----------|
| 200 | OK | Success |
| 201 | Created | Resource created |
| 204 | No Content | Delete successful |
| 400 | Bad Request | Invalid input (check field validation) |
| 401 | Unauthorized | Invalid credentials |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 429 | Too Many Requests | Rate limited (retry with backoff) |
| 500 | Internal Server Error | Jira error (retry) |

### Error Handling Patterns

```python
async def robust_request(self, method, endpoint, **kwargs):
    """Request with comprehensive error handling."""
    try:
        return await self._make_request(method, endpoint, **kwargs)

    except HTTPStatusError as e:
        status = e.response.status_code

        if status == 400:
            # Validation error
            error_data = e.response.json()
            error_msgs = error_data.get("errorMessages", [])
            field_errors = error_data.get("errors", {})

            raise ValueError(
                f"Invalid input: {error_msgs}. Field errors: {field_errors}"
            )

        elif status == 401:
            raise PermissionError("Invalid credentials. Check API token.")

        elif status == 403:
            raise PermissionError(
                "Insufficient permissions for this operation. "
                "Check project permissions and security levels."
            )

        elif status == 404:
            return None  # Resource not found

        elif status == 429:
            # Rate limited - already handled in _make_request with retry
            raise

        elif status >= 500:
            # Server error - transient, can retry
            raise ConnectionError(
                f"Jira server error ({status}). Try again later."
            )

        else:
            raise

    except TimeoutException:
        raise TimeoutError("Request timed out. Jira may be slow or unavailable.")

    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error: {e}")
        raise
```

---

## Best Practices

### 1. Field Expansion Control

```python
# ❌ DON'T: Request all fields unnecessarily
params = {"fields": "*all"}

# ✅ DO: Request only needed fields
params = {"fields": "summary,status,assignee,priority"}
```

### 2. Project Scoping

```python
# ❌ DON'T: Search without project filter
jql = 'status = "In Progress"'

# ✅ DO: Always scope by project
jql = 'project = PROJ AND status = "In Progress"'
```

### 3. Bulk Operations

```python
# ❌ DON'T: Loop individual updates
for issue_key in issue_keys:
    await update_issue(issue_key, {"priority": "High"})

# ✅ DO: Use bulk operations
# (Note: Jira doesn't have bulk update API, but you can batch requests)
tasks = [update_issue(key, {"priority": "High"}) for key in issue_keys]
await asyncio.gather(*tasks, return_exceptions=True)
```

### 4. Caching Strategy

```python
class JiraClient:
    def __init__(self):
        # Cache static/rarely-changing data
        self._priority_cache = None
        self._issue_types_cache = {}
        self._custom_fields_cache = {}

        # Cache TTL
        self._cache_ttl = 3600  # 1 hour
        self._cache_timestamp = {}

    async def get_priorities(self):
        """Get priorities with caching."""
        if self._priority_cache is None:
            self._priority_cache = await self._make_request("GET", "priority")
        return self._priority_cache
```

### 5. Connection Pooling

```python
# Use persistent client for connection pooling
class JiraClient:
    def __init__(self):
        self._client = None

    async def get_client(self):
        if self._client is None:
            self._client = AsyncClient(
                auth=self.auth,
                headers=self.headers,
                timeout=30,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
```

---

## Common Pitfalls

### 1. Epic Link Deprecation

**Problem:** Using deprecated `Epic Link` custom field

```python
# ❌ DEPRECATED (Feb 2024)
fields["customfield_10014"] = "PROJ-123"  # Epic Link

# ✅ NEW APPROACH
fields["parent"] = {"key": "PROJ-123"}
```

### 2. Text Search Performance

**Problem:** Using `text ~` searches entire database

```python
# ❌ SLOW: Searches all text fields
jql = 'text ~ "authentication"'

# ✅ FAST: Field-specific search
jql = 'summary ~ "authentication" OR description ~ "authentication"'
```

### 3. Missing Project Scope

**Problem:** JQL without project filter

```python
# ❌ SLOW: Searches all projects
jql = 'assignee = currentUser() AND status = "In Progress"'

# ✅ FAST: Project scoped
jql = 'project = PROJ AND assignee = currentUser() AND status = "In Progress"'
```

### 4. Ignoring Rate Limits

**Problem:** Not monitoring rate limit headers

```python
# ❌ WRONG: No rate limit awareness
for i in range(1000):
    await make_request(...)

# ✅ CORRECT: Monitor and throttle
tracker = RateLimitTracker()
for i in range(1000):
    if tracker.should_wait():
        await asyncio.sleep(tracker.wait_time())
    response = await make_request(...)
    tracker.update(response.headers)
```

### 5. JQL Injection

**Problem:** Unsanitized user input in JQL

```python
# ❌ DANGEROUS: JQL injection vulnerability
user_input = 'test" OR 1=1 OR summary ~ "'
jql = f'summary ~ "{user_input}"'

# ✅ SAFE: Escape quotes
def escape_jql(value: str) -> str:
    return value.replace('"', '\\"').replace("'", "\\'")

jql = f'summary ~ "{escape_jql(user_input)}"'
```

### 6. ADF Format Errors

**Problem:** Sending plain text instead of ADF

```python
# ❌ WRONG (Jira Cloud): Plain text
fields["description"] = "This is a description"

# ✅ CORRECT: ADF format
fields["description"] = {
    "type": "doc",
    "version": 1,
    "content": [{
        "type": "paragraph",
        "content": [{"type": "text", "text": "This is a description"}]
    }]
}
```

### 7. Concurrent Request Overload

**Problem:** Too many concurrent requests

```python
# ❌ WRONG: Unbounded concurrency
tasks = [fetch_issue(key) for key in issue_keys]  # 1000+ concurrent
await asyncio.gather(*tasks)

# ✅ CORRECT: Batched execution
async def batch_process(items, batch_size=5):
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        await asyncio.gather(*[fetch_issue(key) for key in batch])
```

---

## Code Examples

### Complete Production Example

```python
import asyncio
import logging
from datetime import datetime
from httpx import AsyncClient, HTTPStatusError, TimeoutException

logger = logging.getLogger(__name__)

class JiraClient:
    """Production-ready Jira REST API v3 client."""

    def __init__(self, server: str, email: str, api_token: str, project_key: str):
        self.server = server.rstrip("/")
        self.email = email
        self.api_token = api_token
        self.project_key = project_key

        self.api_base = f"{self.server}/rest/api/3"
        self.auth = httpx.BasicAuth(email, api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        # Caching
        self._priority_cache = None
        self._custom_fields_cache = {}

        # Rate limiting
        self.max_retries = 3
        self._rate_limit_tracker = RateLimitTracker()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict = None,
        params: dict = None,
        retry_count: int = 0
    ):
        """Make HTTP request with retry logic and rate limiting."""
        url = f"{self.api_base}/{endpoint.lstrip('/')}"

        # Check rate limit
        if self._rate_limit_tracker.should_wait():
            wait_time = self._rate_limit_tracker.wait_time()
            logger.warning(f"Rate limit approaching, waiting {wait_time}s")
            await asyncio.sleep(wait_time)

        async with AsyncClient(
            auth=self.auth,
            headers=self.headers,
            timeout=30,
            verify=True
        ) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params
                )

                # Update rate limit tracker
                self._rate_limit_tracker.update(response.headers)

                response.raise_for_status()

                if response.status_code == 204:
                    return {}

                return response.json()

            except TimeoutException:
                if retry_count < self.max_retries:
                    await asyncio.sleep(2 ** retry_count)
                    return await self._make_request(
                        method, endpoint, data, params, retry_count + 1
                    )
                raise

            except HTTPStatusError as e:
                # Rate limiting with exponential backoff
                if e.response.status_code == 429 and retry_count < self.max_retries:
                    retry_after = int(e.response.headers.get("Retry-After", 5))

                    # Add jitter
                    jitter = random.uniform(0, retry_after * 0.1)
                    total_delay = retry_after + jitter

                    logger.warning(f"Rate limited, retrying after {total_delay}s")
                    await asyncio.sleep(total_delay)

                    return await self._make_request(
                        method, endpoint, data, params, retry_count + 1
                    )

                logger.error(f"API error: {e.response.status_code} - {e.response.text}")
                raise

    async def create_issue(
        self,
        summary: str,
        description: str,
        issue_type: str = "Task",
        priority: str = "Medium",
        labels: list[str] = None,
    ):
        """Create issue with ADF description."""

        # Convert to ADF
        adf_description = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": line}]
                }
                for line in description.split("\n") if line.strip()
            ]
        }

        fields = {
            "project": {"key": self.project_key},
            "summary": summary,
            "description": adf_description,
            "issuetype": {"name": issue_type},
            "priority": {"name": priority},
        }

        if labels:
            fields["labels"] = labels

        response = await self._make_request("POST", "issue", data={"fields": fields})
        return response.get("key")

    async def search_issues(
        self,
        jql: str,
        fields: list[str] = None,
        max_results: int = 50
    ):
        """Search with optimized field selection."""

        params = {
            "jql": jql,
            "maxResults": max_results,
            "fields": ",".join(fields) if fields else "*all"
        }

        data = await self._make_request("GET", "search/jql", params=params)
        return data.get("issues", [])

# Usage
async def main():
    client = JiraClient(
        server="https://yourcompany.atlassian.net",
        email="your.email@company.com",
        api_token="your_api_token",
        project_key="PROJ"
    )

    # Create issue
    issue_key = await client.create_issue(
        summary="Implement user authentication",
        description="Add OAuth2 support for user login",
        issue_type="Story",
        priority="High",
        labels=["feature", "security"]
    )
    print(f"Created: {issue_key}")

    # Search issues
    issues = await client.search_issues(
        jql=f"project = {client.project_key} AND status = 'In Progress'",
        fields=["summary", "status", "assignee"]
    )
    print(f"Found {len(issues)} issues in progress")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 2025 API Changes

### Rate Limiting Enforcement (Nov 22, 2025)

**Change:** Strict enforcement of 10 requests/second per API token

**Impact:**
- 429 errors increase significantly
- Per-issue write limits prevent update loops
- Concurrent requests limited

**Migration:**
- Add exponential backoff with jitter
- Monitor rate limit headers
- Implement request batching
- Use bulk operations where possible

### Search Endpoint Change

**Deprecated:** `GET /rest/api/3/search`
**New:** `GET /rest/api/3/search/jql`

**Migration:**
```python
# Old (deprecated)
await client.get("/rest/api/3/search", params={"jql": jql})

# New (required)
await client.get("/rest/api/3/search/jql", params={"jql": jql})
```

### Epic Link Retirement (Feb 2024)

**Deprecated:** `Epic Link` custom field (`customfield_10014`)
**New:** `Parent` field

**Migration:**
```python
# Old (deprecated)
fields["customfield_10014"] = "PROJ-123"

# New (recommended)
fields["parent"] = {"key": "PROJ-123"}

# Fallback for compatibility
async def set_epic_link(self, issue_key: str, epic_key: str):
    """Set epic with fallback."""
    try:
        # Try new parent field first
        await self.update_issue(issue_key, parent={"key": epic_key})
    except HTTPStatusError as e:
        if e.response.status_code == 400:
            # Fallback to legacy epic link
            await self.update_custom_field(issue_key, "customfield_10014", epic_key)
        else:
            raise
```

---

## Summary

This skill provides production-ready Jira REST API v3 integration patterns including:

✅ **Authentication:** API tokens, OAuth 2.0, PAT
✅ **Rate Limiting:** 2025 enforcement, exponential backoff, jitter
✅ **JQL Optimization:** 50+ examples, performance tiers, anti-patterns
✅ **Issue Management:** CRUD, search, transitions, comments, attachments
✅ **Agile APIs:** Sprints, boards, backlog management
✅ **Error Handling:** Comprehensive exception handling, retry logic
✅ **Best Practices:** Field expansion, caching, bulk operations
✅ **2025 Updates:** API changes, deprecations, migration paths

**Token Estimate:** ~9,500 tokens (full content)

**Last Updated:** 2025-12-04
**API Version:** Jira Cloud REST API v3
**Jira Software:** Agile API v1.0
