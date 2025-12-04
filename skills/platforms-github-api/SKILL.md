# platforms-github-api

GitHub REST API v3 and GraphQL v4 integration patterns for ticket management and automation.

## When to Use This Skill

- Building GitHub Issues integration
- Automating project boards and workflows
- Managing milestones and labels
- Implementing CI/CD with GitHub Actions
- Creating PR automation workflows
- Extending GitHub state management with labels
- Building GitHub Apps or OAuth integrations

---

## Quick Start (Entry Point)

### Authentication Quick Start

```python
# Personal Access Token (PAT)
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# Required scopes: repo, read:org
```

### Rate Limiting Basics

- **Authenticated**: 5,000 requests/hour
- **Search API**: 30 requests/minute
- **GraphQL**: 5,000 points/hour (different from REST)

### Core Endpoints Overview

- Issues: Create, update, search, comment
- Milestones: Progress tracking, epic management
- Labels: State management, priority tracking
- Pull Requests: Create from issues, link existing PRs
- Projects V2: Iterations (GraphQL only)

### Common Pitfalls Preview

1. **Label cache staleness** - No TTL, requires manual refresh
2. **Rate limit exhaustion** - Check quota before batch operations
3. **Inefficient pagination** - Use cursors, not offset emulation
4. **State transition errors** - Use adapter methods, not raw API
5. **Milestone label confusion** - Labels stored locally, not in GitHub

**💡 For full patterns and best practices, continue reading below.**

---

## Full Content

## 1. Authentication Patterns

### 1.1 Personal Access Token (Classic)

**Current Implementation** (from mcp-ticketer):

```python
class GitHubAdapter:
    def __init__(self, config: dict[str, Any]):
        self.token = config.get("api_key") or config.get("token")
        self.owner = config.get("owner")
        self.repo = config.get("repo")

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        self.client = httpx.AsyncClient(
            base_url="https://api.github.com",
            headers=self.headers,
            timeout=30.0,
        )
```

**Required Scopes**:
- `repo` - Full control of private repositories
- `public_repo` - Access public repositories
- `read:org` - Read org and team membership
- `write:discussion` - Read/write team discussions (optional)

**Security Best Practices**:

```python
import os

# ✅ GOOD: Environment variables
token = os.getenv("GITHUB_TOKEN")

# ❌ BAD: Hardcoded in code
token = "ghp_xxxxxxxxxxxx"  # NEVER DO THIS

# ✅ GOOD: Validate before use
def validate_credentials(self) -> tuple[bool, str]:
    if not self.token:
        return False, "GITHUB_TOKEN is required"
    if not self.owner:
        return False, "GitHub owner is required"
    if not self.repo:
        return False, "GitHub repo is required"
    return True, ""
```

### 1.2 Fine-Grained Personal Access Tokens (2024+)

**Benefits**:
- Repository-specific access
- Granular permission control
- Automatic expiration
- Audit logging

**Example Setup**:
```yaml
permissions:
  contents: write
  issues: write
  pull_requests: write
  metadata: read
repository_access: only_selected
repositories: ["mcp-ticketer"]
```

### 1.3 GitHub Apps Authentication (Future Enhancement)

**Benefits**:
- **15,000 requests/hour** (3x higher than PAT)
- Fine-grained permissions
- Installation-level tokens
- Organization-wide integrations

**Not Currently Implemented** - Planned for mcp-ticketer v3.0

---

## 2. Rate Limiting and Performance

### 2.1 Rate Limit Quotas

| API Type | Authenticated | Unauthenticated |
|----------|---------------|-----------------|
| REST API | 5,000/hour | 60/hour |
| Search API | 30/minute | 10/minute |
| GraphQL | 5,000 points/hour | - |
| GitHub Apps | 15,000/hour | - |

### 2.2 Rate Limit Tracking

```python
# Store rate limit info from headers
self._rate_limit = {
    "limit": response.headers.get("X-RateLimit-Limit"),
    "remaining": response.headers.get("X-RateLimit-Remaining"),
    "reset": response.headers.get("X-RateLimit-Reset"),
}

# Check before batch operations
async def get_rate_limit(self) -> dict[str, Any]:
    response = await self.client.get("/rate_limit")
    response.raise_for_status()
    return response.json()

# Usage
rate_limit = await adapter.get_rate_limit()
if rate_limit["rate"]["remaining"] < 100:
    reset_time = datetime.fromtimestamp(rate_limit["rate"]["reset"])
    wait_seconds = (reset_time - datetime.now()).total_seconds()
    await asyncio.sleep(wait_seconds)
```

### 2.3 Exponential Backoff Strategy

```python
class RetryConfig:
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retry_on_status: list[int] = [429, 502, 503, 504],
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retry_on_status = retry_on_status

# Retry delays: 1s, 2s, 4s, 8s (capped at max_delay)
```

### 2.4 Performance Optimization

**ETag Conditional Requests** (Not Currently Implemented):

```python
# First request
response = await client.get("/repos/owner/repo/issues/123")
etag = response.headers.get("ETag")  # "W/\"abc123\""

# Subsequent request with ETag
headers = {"If-None-Match": etag}
response = await client.get("/repos/owner/repo/issues/123", headers=headers)

if response.status_code == 304:
    # Not modified, use cached version (doesn't count against rate limit!)
    return cached_issue
```

**Benefits**:
- Reduce bandwidth consumption
- Faster 304 responses
- **Doesn't count against rate limit** when 304 returned

---

## 3. Label-Based State Management Pattern

### 3.1 Problem: GitHub's Binary State Limitation

GitHub natively supports only **two states**:
- `open`
- `closed`

This is insufficient for modern workflows requiring:
- `in_progress`
- `ready`
- `tested`
- `waiting`
- `blocked`

### 3.2 Solution: Label-Based Extended States

```python
class GitHubStateMapping:
    # Native states
    OPEN = "open"
    CLOSED = "closed"

    # Extended states via labels
    STATE_LABELS = {
        TicketState.IN_PROGRESS: "in-progress",
        TicketState.READY: "ready",
        TicketState.TESTED: "tested",
        TicketState.WAITING: "waiting",
        TicketState.BLOCKED: "blocked",
    }

    # Priority labels
    PRIORITY_LABELS = {
        Priority.CRITICAL: ["P0", "critical", "urgent"],
        Priority.HIGH: ["P1", "high"],
        Priority.MEDIUM: ["P2", "medium"],
        Priority.LOW: ["P3", "low"],
    }
```

### 3.3 State Transition Implementation

```python
async def update(self, ticket_id: str, updates: dict[str, Any]) -> Task | None:
    # Get current issue
    current_issue = await self.client.get(
        f"/repos/{self.owner}/{self.repo}/issues/{issue_number}"
    )
    current_labels = [label["name"] for label in current_issue.get("labels", [])]

    # Remove old state labels
    labels_to_update = [
        label for label in current_labels
        if label.lower() not in [
            sl.lower() for sl in GitHubStateMapping.STATE_LABELS.values()
        ]
    ]

    # Add new state label
    new_state = updates["state"]
    state_label = self._get_state_label(new_state)
    if state_label:
        await self._ensure_label_exists(state_label, "fbca04")
        labels_to_update.append(state_label)

    # Update GitHub native state
    if new_state in [TicketState.DONE, TicketState.CLOSED]:
        update_data["state"] = "closed"
    else:
        update_data["state"] = "open"

    update_data["labels"] = labels_to_update
```

### 3.4 Label Caching Strategy

```python
async def _ensure_label_exists(self, label_name: str, color: str = "0366d6") -> None:
    # Cache labels to reduce API calls
    if not self._labels_cache:
        response = await self.client.get(f"/repos/{self.owner}/{self.repo}/labels")
        self._labels_cache = response.json()

    # Check if label exists
    existing_labels = [label["name"].lower() for label in self._labels_cache]
    if label_name.lower() not in existing_labels:
        # Create the label
        response = await self.client.post(
            f"/repos/{self.owner}/{self.repo}/labels",
            json={"name": label_name, "color": color},
        )
        if response.status_code == 201:
            self._labels_cache.append(response.json())
```

**⚠️ Pitfall**: Cache never expires. Manual refresh needed if labels created outside adapter.

---

## 4. Milestone Management (Hybrid Storage)

### 4.1 Problem: GitHub Doesn't Store Labels on Milestones

GitHub Milestones API provides:
- ✅ Title, description, due date, state
- ✅ Progress tracking (open/closed issue counts)
- ❌ Labels (not supported natively)

### 4.2 Solution: Hybrid Storage Pattern

```python
async def milestone_create(
    self,
    name: str,
    target_date: date | None = None,
    labels: list[str] | None = None,
    description: str = "",
) -> Milestone:
    # Create via GitHub API (title, description, due_on)
    milestone_data = {
        "title": name,
        "description": description,
        "state": "open",
        "due_on": target_date.isoformat() + "Z" if target_date else None,
    }

    response = await self.client.post(
        f"/repos/{self.owner}/{self.repo}/milestones",
        json=milestone_data,
    )
    gh_milestone = response.json()

    # Store labels locally (GitHub limitation workaround)
    milestone = self._github_milestone_to_milestone(gh_milestone, labels)

    config_dir = Path.home() / ".mcp-ticketer"
    manager = MilestoneManager(config_dir)
    manager.save_milestone(milestone)  # Saves to ~/.mcp-ticketer/milestones.json

    return milestone
```

### 4.3 Progress Tracking (Auto-Calculated)

```python
def _github_milestone_to_milestone(
    self, gh_milestone: dict[str, Any], labels: list[str] | None = None
) -> Milestone:
    # GitHub calculates progress automatically
    total = gh_milestone.get("open_issues", 0) + gh_milestone.get("closed_issues", 0)
    closed = gh_milestone.get("closed_issues", 0)
    progress_pct = (closed / total * 100) if total > 0 else 0.0

    return Milestone(
        id=str(gh_milestone["number"]),
        name=gh_milestone["title"],
        total_issues=total,
        closed_issues=closed,
        progress_pct=progress_pct,
        labels=labels or [],  # From local storage
    )
```

### 4.4 State Computation

```python
# Determine milestone state
state = "closed" if gh_milestone["state"] == "closed" else "open"

# Compute based on due date
if state == "open" and target_date:
    if target_date < date.today():
        state = "closed"  # Past due
    else:
        state = "active"  # In progress
```

---

## 5. Hybrid REST/GraphQL Pattern

### 5.1 When to Use REST vs GraphQL

| Operation | Use | Reason |
|-----------|-----|--------|
| Create issue | REST | Simpler, mutations well-supported |
| Update issue | REST | Direct updates, label management |
| List issues | REST | Simple pagination, filtering |
| Search issues | GraphQL | Advanced search, nested data |
| Get issue (nested) | GraphQL | Fetch comments, reactions, projects in one call |
| Projects V2 | GraphQL | Only available via GraphQL |
| Milestones | REST | Full CRUD support |

### 5.2 GraphQL Fragments (Code Reuse)

```python
ISSUE_FRAGMENT = """
    fragment IssueFields on Issue {
        id
        number
        title
        body
        state
        createdAt
        updatedAt
        url
        author { login }
        assignees(first: 10) { nodes { login email } }
        labels(first: 20) { nodes { name color } }
        milestone { id number title state }
        comments(first: 100) { nodes { id body author { login } } }
    }
"""

# Use in queries
SEARCH_ISSUES = """
    query SearchIssues($query: String!, $first: Int!, $after: String) {
        search(query: $query, type: ISSUE, first: $first, after: $after) {
            nodes {
                ... on Issue {
                    ...IssueFields
                }
            }
        }
    }
"""

full_query = ISSUE_FRAGMENT + SEARCH_ISSUES
```

### 5.3 GraphQL Search Query Construction

```python
async def search(self, query: SearchQuery) -> list[Task]:
    # Build GitHub search query
    search_parts = [f"repo:{self.owner}/{self.repo}", "is:issue"]

    if query.query:
        escaped = query.query.replace('"', '\\"')
        search_parts.append(f'"{escaped}"')

    if query.state:
        if query.state in [TicketState.DONE, TicketState.CLOSED]:
            search_parts.append("is:closed")
        else:
            search_parts.append("is:open")
            state_label = self._get_state_label(query.state)
            if state_label:
                search_parts.append(f'label:"{state_label}"')

    if query.priority:
        priority_label = self._get_priority_label(query.priority)
        search_parts.append(f'label:"{priority_label}"')

    if query.assignee:
        search_parts.append(f"assignee:{query.assignee}")

    if query.tags:
        for tag in query.tags:
            search_parts.append(f'label:"{tag}"')

    github_query = " ".join(search_parts)
    # Result: repo:owner/repo is:issue "authentication" label:"P1" assignee:user
```

**Search Query Examples**:
```
repo:owner/repo is:issue is:open label:"bug"
repo:owner/repo is:issue assignee:username created:>2025-01-01
repo:owner/repo is:issue "authentication" label:"P0" is:closed
```

---

## 6. Pull Request Automation

### 6.1 Create PR from Issue (Auto-Generated)

```python
async def create_pull_request(
    self,
    ticket_id: str,
    base_branch: str = "main",
    head_branch: str | None = None,
    title: str | None = None,
    body: str | None = None,
    draft: bool = False,
) -> dict[str, Any]:
    # Get issue details
    issue = await self.read(ticket_id)

    # Auto-generate branch name from issue
    if not head_branch:
        safe_title = "-".join(
            issue.title.lower()
            .replace("[", "").replace("]", "")
            .split()[:5]  # Limit to 5 words
        )
        head_branch = f"{issue_number}-{safe_title}"
        # Result: "123-fix-authentication-bug"

    # Auto-generate PR title
    if not title:
        title = f"[#{issue_number}] {issue.title}"

    # Auto-generate PR body with checklist
    if not body:
        body = f"""## Summary
This PR addresses issue #{issue_number}.

**Issue:** #{issue_number} - {issue.title}

## Description
{issue.description or 'No description provided.'}

## Changes
- [ ] Implementation details to be added

## Testing
- [ ] Tests have been added/updated
- [ ] All tests pass

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed

Fixes #{issue_number}
"""

    # Create branch if doesn't exist
    if not branch_exists:
        base_sha = await self._get_branch_sha(base_branch)
        await self.client.post(
            f"/repos/{self.owner}/{self.repo}/git/refs",
            json={"ref": f"refs/heads/{head_branch}", "sha": base_sha},
        )

    # Create pull request
    pr_response = await self.client.post(
        f"/repos/{self.owner}/{self.repo}/pulls",
        json={
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
            "draft": draft,
        },
    )

    pr = pr_response.json()

    # Add comment to issue
    await self.add_comment(Comment(
        ticket_id=ticket_id,
        content=f"Pull request #{pr['number']} created: {pr['html_url']}",
    ))

    return {
        "number": pr["number"],
        "url": pr["html_url"],
        "branch": head_branch,
        "state": pr["state"],
        "draft": pr.get("draft", False),
        "linked_issue": issue_number,
    }
```

### 6.2 Link Existing PR to Issue

```python
async def link_existing_pull_request(
    self, ticket_id: str, pr_url: str
) -> dict[str, Any]:
    # Parse PR URL: https://github.com/owner/repo/pull/123
    pr_pattern = r"github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.search(pr_pattern, pr_url)
    pr_owner, pr_repo, pr_number = match.groups()

    # Verify same repository
    if pr_owner != self.owner or pr_repo != self.repo:
        raise ValueError("PR must be from same repository")

    # Get PR details
    pr = await self.client.get(
        f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}"
    ).json()

    # Update PR body to include issue reference
    current_body = pr.get("body", "")
    issue_ref = f"#{issue_number}"

    if issue_ref not in current_body:
        updated_body = current_body + f"\n\nRelated to #{issue_number}"
        await self.client.patch(
            f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}",
            json={"body": updated_body},
        )

    # Add comment to issue
    await self.add_comment(Comment(
        ticket_id=ticket_id,
        content=f"Linked to pull request #{pr_number}: {pr_url}",
    ))

    return {
        "success": True,
        "pr_number": pr["number"],
        "pr_url": pr["html_url"],
        "linked_issue": issue_number,
    }
```

---

## 7. Advanced Search and Filtering

### 7.1 Search Qualifiers Reference

| Qualifier | Example | Description |
|-----------|---------|-------------|
| `author:` | `author:username` | Issue creator |
| `assignee:` | `assignee:username` | Assigned user |
| `mentions:` | `mentions:username` | User mentioned |
| `commenter:` | `commenter:username` | User commented |
| `involves:` | `involves:username` | Combined: author, assignee, mentions, commenter |
| `label:` | `label:"bug"` | Has label |
| `created:` | `created:>2025-01-01` | Created after date |
| `updated:` | `updated:<2025-12-31` | Updated before date |
| `is:` | `is:open`, `is:closed` | State filter |
| `no:` | `no:assignee`, `no:label` | Missing field |
| `milestone:` | `milestone:"v2.0"` | In milestone |
| `project:` | `project:repo/1` | In project board |

### 7.2 Advanced Search Examples

```python
# Find all high-priority authentication bugs
query = SearchQuery(
    query="authentication",
    state=TicketState.OPEN,
    priority=Priority.HIGH,
    tags=["bug", "security"],
)
# → repo:owner/repo is:issue is:open "authentication" label:"P1" label:"bug" label:"security"

# Find stale issues (no activity in 90 days)
github_query = "repo:owner/repo is:issue is:open updated:<2024-10-01"

# Find issues involving specific user
github_query = "repo:owner/repo is:issue involves:username"

# Find unassigned critical issues
github_query = "repo:owner/repo is:issue is:open label:P0 no:assignee"
```

### 7.3 Search Performance Tips

1. **Use GraphQL search for complex queries** (better than REST)
2. **Limit results** (default: 30, max: 100)
3. **Rate limit**: 30 requests/minute (authenticated)
4. **Use specific qualifiers** (faster than broad text search)

```python
# ✅ GOOD: Specific query
"repo:owner/repo is:issue label:bug assignee:user"

# ❌ BAD: Broad text search
"repo:owner/repo bug user"
```

---

## 8. Pagination Strategies

### 8.1 REST API Link Header Pagination

```python
# Response headers
Link: <https://api.github.com/repos/owner/repo/issues?page=2>; rel="next",
      <https://api.github.com/repos/owner/repo/issues?page=5>; rel="last"

# Implementation
params = {
    "per_page": min(limit, 100),  # GitHub max: 100
    "page": (offset // limit) + 1 if limit > 0 else 1,
}

response = await self.client.get(
    f"/repos/{self.owner}/{self.repo}/issues",
    params=params,
)
```

**⚠️ Limitation**: Offset-based pagination inefficient for large datasets.

### 8.2 GraphQL Cursor-Based Pagination

```python
variables = {
    "query": github_query,
    "first": min(query.limit, 100),
    "after": None,  # Cursor from previous page
}

result = await self._graphql_request(SEARCH_ISSUES, variables)

issues = result["search"]["nodes"]
page_info = result["search"]["pageInfo"]

if page_info["hasNextPage"]:
    next_cursor = page_info["endCursor"]
    # Use next_cursor in next request
```

**✅ Efficient**: Only fetches needed data, no wasted API calls.

### 8.3 Pagination Best Practices

```python
# ❌ BAD: Large offset emulation (wasteful)
issues = await adapter.list(limit=10, offset=5000)
# GraphQL: Fetches 5000 issues, returns 10

# ✅ GOOD: Cursor-based pagination
cursor = None
all_issues = []

while len(all_issues) < desired_count:
    page = await adapter.search(SearchQuery(
        query="",
        limit=100,
        # Store cursor between requests
    ))
    all_issues.extend(page)
    if len(page) < 100:
        break  # No more results
```

---

## 9. Error Handling and Retry Strategies

### 9.1 HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | OK | Success |
| 201 | Created | Resource created |
| 204 | No Content | Delete success |
| 304 | Not Modified | Use cached version |
| 400 | Bad Request | Fix request format |
| 401 | Unauthorized | Check authentication |
| 403 | Forbidden | Check permissions |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limited (retry) |
| 500 | Server Error | GitHub issue (retry) |
| 502 | Bad Gateway | GitHub overloaded (retry) |
| 503 | Service Unavailable | Maintenance (retry) |

### 9.2 Retry Configuration

```python
class RetryConfig:
    retry_on_status = [429, 502, 503, 504, 522, 524]
    retry_on_exceptions = [
        TimeoutException,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
    ]

# Exponential backoff: 1s, 2s, 4s, 8s (max 60s)
def _calculate_backoff(attempt: int) -> float:
    delay = initial_delay * (exponential_base ** attempt)
    delay = min(delay, max_delay)
    if jitter:
        delay *= random.uniform(0.5, 1.5)
    return delay
```

### 9.3 Error Handling Patterns

```python
try:
    issue = await adapter.create(task)
except ValueError as e:
    # Invalid credentials or configuration
    logger.error(f"Auth error: {e}")
except httpx.HTTPStatusError as e:
    if e.response.status_code == 422:
        # Validation error (e.g., duplicate label)
        logger.warning(f"Validation failed: {e}")
    elif e.response.status_code == 429:
        # Rate limited (auto-retried by adapter)
        logger.info("Rate limited, retrying...")
    elif e.response.status_code == 404:
        # Resource not found
        logger.error(f"Issue not found: {e}")
    else:
        # Other HTTP errors
        logger.error(f"HTTP {e.response.status_code}: {e}")
except httpx.TimeoutException:
    # Network timeout
    logger.error("Request timed out")
except Exception as e:
    # Unexpected errors
    logger.exception(f"Unexpected error: {e}")
```

---

## 10. Best Practices

### 10.1 Authentication

- ✅ Use environment variables for tokens
- ✅ Validate credentials before operations
- ✅ Use fine-grained PATs for production
- ✅ Rotate tokens regularly
- ⚠️ Consider GitHub Apps for higher rate limits (15K/hr)

### 10.2 Rate Limiting

- ✅ Monitor remaining quota with `get_rate_limit()`
- ✅ Use exponential backoff for 429 responses (built-in)
- ✅ Throttle batch operations (sleep between requests)
- ✅ Use ETags for conditional requests (saves quota)
- ⚠️ GraphQL uses point-based system (different from REST)

### 10.3 State Management

- ✅ Use label-based extended states (in_progress, blocked, etc.)
- ✅ Let adapter handle label synchronization
- ✅ Use `update()` method for state transitions, not raw API
- ✅ Clear label cache when stale
- ⚠️ GitHub native states are binary: open/closed

### 10.4 Milestone Management

- ✅ Understand hybrid storage (GitHub API + local labels)
- ✅ Use milestone methods, not raw API calls
- ✅ Check progress before closing milestones
- ✅ Store labels locally (GitHub limitation)
- ⚠️ Progress auto-calculated by GitHub

### 10.5 Search and Filtering

- ✅ Use GraphQL search for complex queries
- ✅ Use REST list for simple filtering
- ✅ Build search queries with SearchQuery model
- ✅ Use specific qualifiers (faster than broad search)
- ⚠️ Search API has lower rate limit (30/min)

### 10.6 Performance

- ✅ Cache labels and milestones
- ✅ Use cursor-based pagination for large datasets
- ✅ Batch independent operations with `asyncio.gather()`
- ✅ Use ETags for conditional requests
- ⚠️ Clear cache when stale (no automatic TTL)

---

## 11. Common Pitfalls and Solutions

### 11.1 Pitfall: Rate Limit Exhaustion

**Problem**:
```python
# ❌ BAD: No rate limit awareness
for i in range(10000):
    await adapter.create(task)  # Will hit 429 after 5000
```

**Solution**:
```python
# ✅ GOOD: Check rate limit before batch operations
rate_limit = await adapter.get_rate_limit()
if rate_limit["rate"]["remaining"] < 100:
    reset_time = datetime.fromtimestamp(rate_limit["rate"]["reset"])
    wait_seconds = (reset_time - datetime.now()).total_seconds()
    logger.info(f"Rate limit low, waiting {wait_seconds}s...")
    await asyncio.sleep(wait_seconds)

# Throttle batch operations
for i in range(len(tasks)):
    await adapter.create(tasks[i])
    if (i + 1) % 100 == 0:
        await asyncio.sleep(1)  # Throttle every 100 requests
```

### 11.2 Pitfall: Label Cache Staleness

**Problem**:
```python
# ❌ BAD: Label created outside adapter, cache stale
# User manually creates "critical" label in GitHub UI
await adapter.create(Task(tags=["critical"]))  # Tries to create duplicate
```

**Solution**:
```python
# ✅ GOOD: Clear cache before operation
adapter._labels_cache = None  # Clear cache
await adapter.create(Task(tags=["critical"]))  # Re-fetches labels

# OR: Pre-create labels
await adapter._ensure_label_exists("critical", "d73a4a")
```

### 11.3 Pitfall: Inefficient Pagination

**Problem**:
```python
# ❌ BAD: Fetching all issues with large offset
issues = await adapter.list(limit=10, offset=5000)
# GraphQL emulation: Fetches 5000 issues, returns 10 (wasteful!)
```

**Solution**:
```python
# ✅ GOOD: Use cursor-based pagination
cursor = None
all_issues = []

while len(all_issues) < desired_count:
    page = await adapter.search(SearchQuery(
        query="",
        limit=100,
        # GraphQL uses cursor internally
    ))
    all_issues.extend(page)
    if len(page) < 100:
        break  # No more results
```

### 11.4 Pitfall: Milestone Label Confusion

**Problem**:
```python
# ❌ BAD: Expecting labels stored in GitHub milestone
milestone = await adapter.milestone_get("5")
# milestone.labels fetched from local storage, NOT GitHub
```

**Solution**:
```python
# ✅ GOOD: Understand hybrid storage
# GitHub stores: title, description, due_on, state, progress
# Local storage: labels (not supported by GitHub API)

# To sync labels, always use milestone methods
await adapter.milestone_update("5", labels=["new-label"])
```

### 11.5 Pitfall: State Transition Errors

**Problem**:
```python
# ❌ BAD: Direct state change without label update
await adapter.client.patch(
    f"/repos/{owner}/{repo}/issues/{number}",
    json={"state": "open"},  # Missing state label!
)
```

**Solution**:
```python
# ✅ GOOD: Use adapter methods for state transitions
await adapter.update(issue_id, {
    "state": TicketState.IN_PROGRESS,
    # Automatically:
    # 1. Adds "in-progress" label
    # 2. Removes old state labels
    # 3. Sets GitHub state to "open"
})
```

### 11.6 Pitfall: Pull Request Creation Failures

**Problem**:
```python
# ❌ BAD: Creating PR without checking branch exists
pr = await adapter.create_pull_request(
    ticket_id="123",
    head_branch="feature-branch",  # Might not exist!
)
```

**Solution**:
```python
# ✅ GOOD: Adapter auto-creates branch if needed
pr = await adapter.create_pull_request(
    ticket_id="123",
    # Omit head_branch: auto-generates from issue title
    # Creates branch from base if doesn't exist
)
```

---

## 12. Code Examples

### Example 1: Full Workflow (Create Issue → Milestone → PR → Close)

```python
# 1. Create issue with extended state and priority
task = Task(
    title="Implement OAuth2 authentication",
    description="""
## Overview
Add OAuth2 authentication support to API

## Requirements
- Support authorization code flow
- Token refresh mechanism
- Revocation endpoint

## Acceptance Criteria
- [ ] OAuth2 endpoints implemented
- [ ] Token storage secure
- [ ] Tests passing
    """,
    state=TicketState.IN_PROGRESS,
    priority=Priority.HIGH,
    tags=["feature", "authentication", "security"],
    assignee="developer",
)

created_issue = await adapter.create(task)
print(f"Created issue #{created_issue.id}: {created_issue.title}")

# 2. Create milestone for sprint
milestone = await adapter.milestone_create(
    name="Sprint 24 - Authentication",
    target_date=date(2025, 12, 31),
    labels=["sprint-24", "Q4"],
    description="Focus: OAuth2 and security improvements",
)

# 3. Link issue to milestone
await adapter.update(created_issue.id, {
    "parent_epic": milestone.id,
})

# 4. Add progress comment
await adapter.add_comment(Comment(
    ticket_id=created_issue.id,
    content="""
## Progress Update

✅ OAuth2 endpoints implemented
✅ Token storage secure
⏳ Working on tests

**Next:** Complete test coverage by EOD
    """,
))

# 5. Create PR from issue
pr = await adapter.create_pull_request(
    ticket_id=created_issue.id,
    base_branch="main",
    draft=True,  # WIP
)

print(f"Created draft PR #{pr['number']}: {pr['url']}")

# 6. Transition state to ready
await adapter.update(created_issue.id, {
    "state": TicketState.READY,  # Adds "ready" label
})

# 7. Close issue when merged
await adapter.update(created_issue.id, {
    "state": TicketState.DONE,  # Closes issue
})
```

### Example 2: Advanced Issue Search

```python
# Find all high-priority authentication bugs assigned to team
query = SearchQuery(
    query="authentication",
    state=TicketState.OPEN,
    priority=Priority.HIGH,
    tags=["bug", "security"],
)

issues = await adapter.search(query)

for issue in issues:
    print(f"#{issue.id}: {issue.title}")
    print(f"  Priority: {issue.priority}")
    print(f"  State: {issue.state}")
    print(f"  Labels: {', '.join(issue.tags)}")
    print()

# Filter issues in milestone
milestone_issues = await adapter.list(
    filters={"parent_epic": "5", "state": "open"}
)

print(f"Found {len(milestone_issues)} open issues in milestone")
```

### Example 3: Milestone Progress Tracking

```python
# Get milestone with progress
milestone = await adapter.milestone_get("5")

print(f"Milestone: {milestone.name}")
print(f"Target Date: {milestone.target_date}")
print(f"Progress: {milestone.progress_pct:.1f}%")
print(f"Total Issues: {milestone.total_issues}")
print(f"Closed Issues: {milestone.closed_issues}")
print(f"Open Issues: {milestone.total_issues - milestone.closed_issues}")

# Check if on track
if milestone.target_date < date.today():
    print("⚠️ OVERDUE")
elif milestone.progress_pct >= 80:
    print("✅ ON TRACK")
else:
    print("⚠️ AT RISK")

# Get issues in milestone
issues = await adapter.milestone_get_issues(
    milestone_id=milestone.id,
    state="open",
)

print("\nOpen Issues:")
for issue in issues:
    print(f"- #{issue['id']}: {issue['title']}")
```

### Example 4: Project Iterations (Sprints)

```python
# List sprints/cycles for project
# Note: Requires Projects V2 node ID (not numeric ID)
project_id = "PVT_kwDOABCD1234"  # From GraphQL

iterations = await adapter.list_cycles(
    project_id=project_id,
    limit=10,
)

print("Active Sprints:")
for iteration in iterations:
    print(f"\n{iteration['title']}")
    print(f"  Duration: {iteration['duration']} days")
    print(f"  Start: {iteration['startDate']}")
    print(f"  End: {iteration['endDate']}")
```

---

## 13. Troubleshooting

### Common Errors and Solutions

**Error: 401 Unauthorized**
```
Solution: Check GITHUB_TOKEN is valid and not expired
```

**Error: 403 Forbidden**
```
Solution: Check token has required scopes (repo, read:org)
```

**Error: 404 Not Found**
```
Solution: Verify owner/repo configuration is correct
```

**Error: 422 Unprocessable Entity**
```
Solution: Validation error - check request body format
Common: Duplicate label, invalid milestone number
```

**Error: 429 Too Many Requests**
```
Solution: Rate limited - wait for reset or use exponential backoff
Check: X-RateLimit-Reset header for reset time
```

**Error: 502/503 Bad Gateway**
```
Solution: GitHub server overloaded - retry with exponential backoff
```

### Debug Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("mcp_ticketer.adapters.github")

# Log all API requests
async def _request(self, method: str, endpoint: str, **kwargs):
    logger.debug(f"{method} {endpoint}")
    start = time.time()
    response = await self.client.request(method, endpoint, **kwargs)
    duration = time.time() - start
    logger.debug(f"{method} {endpoint} - {response.status_code} ({duration:.2f}s)")
    return response
```

---

## 14. References

**Official Documentation**:
- [GitHub REST API v3](https://docs.github.com/en/rest)
- [GitHub GraphQL API v4](https://docs.github.com/en/graphql)
- [Authentication](https://docs.github.com/en/authentication)
- [Rate Limiting](https://docs.github.com/en/rest/rate-limit)
- [Search Syntax](https://docs.github.com/en/search-github)

**mcp-ticketer Implementation**:
- GitHub Adapter: `/src/mcp_ticketer/adapters/github.py` (2,568 lines)
- Adapter Docs: `/docs/adapters/github.md`
- Milestone Docs: `/docs/adapters/github-milestones.md`

**Research**:
- Skill Research: `/docs/research/github-api-skill-research-2025-12-04.md`
