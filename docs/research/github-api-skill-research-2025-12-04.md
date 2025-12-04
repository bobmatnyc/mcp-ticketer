# GitHub REST API v3 Skill Research

**Research Date:** 2025-12-04
**Researcher:** Research Agent
**Objective:** Analyze GitHub REST API v3 and current mcp-ticketer implementation to design comprehensive Claude Code skill for GitHub API integration

---

## Executive Summary

This research analyzed GitHub's REST API v3, the current mcp-ticketer GitHub adapter implementation, and best practices for building robust API integrations. The findings reveal a mature, well-structured adapter implementation that effectively uses both REST API v3 and GraphQL API v4, with opportunities for enhancement in areas like conditional requests, webhook integration, and advanced search capabilities.

**Key Findings:**
- Current implementation uses ~2,568 lines of well-structured code covering CRUD, milestones, projects, and advanced operations
- Hybrid REST/GraphQL approach leverages strengths of both APIs
- Rate limiting, retry logic, and error handling are production-ready
- Missing: ETag caching, webhook integration, advanced project automation, GitHub Apps authentication
- Test coverage: 717 lines across 40+ test cases with strong integration testing

**Recommended Skill Focus:**
1. GitHub API patterns and best practices (authentication, rate limiting, pagination)
2. Issue and project management workflows
3. Advanced search and filtering techniques
4. Error handling and retry strategies
5. Milestone and epic management patterns
6. Pull request workflows and automation

---

## 1. GitHub REST API v3 Overview

### 1.1 Base Configuration

**Base URL:** `https://api.github.com`

**API Version Header:**
```
X-GitHub-Api-Version: 2022-11-28
```

**Accept Header:**
```
Accept: application/vnd.github.v3+json
```

### 1.2 Authentication Methods

#### Personal Access Token (PAT) - Current Implementation
```python
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
```

**Scopes Required:**
- `repo` - Full control of private repositories
- `public_repo` - Access public repositories
- `write:discussion` - Read/write team discussions
- `read:org` - Read org and team membership

#### OAuth2 (Not Currently Implemented)
- **Flow:** Authorization Code Grant
- **Use Case:** Multi-user applications
- **Token Refresh:** Supported with refresh tokens
- **Benefit:** User-level permissions, revocable access

#### GitHub App (Future Enhancement)
- **Benefits:** Higher rate limits (15,000/hour vs 5,000/hour), fine-grained permissions
- **Use Case:** Organization-wide integrations
- **Installation-level tokens:** Repository-specific access
- **Current Status:** Planned enhancement (docs/adapters/github.md:203)

### 1.3 Rate Limiting

**Current Limits:**
- **Authenticated:** 5,000 requests/hour
- **Unauthenticated:** 60 requests/hour
- **Search API:** 30 requests/minute (authenticated)
- **GraphQL API:** 5,000 points/hour

**Implementation (src/mcp_ticketer/core/http_client.py:376-403):**
```python
class GitHubHTTPClient(BaseHTTPClient):
    def __init__(self, token: str, api_url: str = "https://api.github.com"):
        # GitHub rate limiting: 5000 requests per hour
        rate_limiter = RateLimiter(max_requests=5000, time_window=3600)

        super().__init__(
            base_url=api_url,
            headers=headers,
            rate_limiter=rate_limiter,
            retry_config=RetryConfig(
                max_retries=3,
                retry_on_status=[429, 502, 503, 504, 522, 524]
            ),
        )
```

**Rate Limit Headers:**
```
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 4999
X-RateLimit-Reset: 1372700873  # Unix timestamp
X-RateLimit-Used: 1
```

**Current Implementation Tracking (src/mcp_ticketer/adapters/github.py:859-864):**
```python
# Store rate limit info after each request
self._rate_limit = {
    "limit": response.headers.get("X-RateLimit-Limit"),
    "remaining": response.headers.get("X-RateLimit-Remaining"),
    "reset": response.headers.get("X-RateLimit-Reset"),
}
```

**Rate Limit Check (src/mcp_ticketer/adapters/github.py:1047-1051):**
```python
async def get_rate_limit(self) -> dict[str, Any]:
    """Get current rate limit status."""
    response = await self.client.get("/rate_limit")
    response.raise_for_status()
    return response.json()
```

### 1.4 Pagination Patterns

#### Link Header-Based Pagination (REST API)

**Response Headers:**
```
Link: <https://api.github.com/repos/owner/repo/issues?page=2>; rel="next",
      <https://api.github.com/repos/owner/repo/issues?page=5>; rel="last"
```

**Current Implementation (src/mcp_ticketer/adapters/github.py:806-869):**
```python
async def list(
    self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
) -> list[Task]:
    params: dict[str, Any] = {
        "per_page": min(limit, 100),  # GitHub max is 100
        "page": (offset // limit) + 1 if limit > 0 else 1,
    }
    # ... filter handling ...
    response = await self.client.get(
        f"/repos/{self.owner}/{self.repo}/issues", params=params
    )
```

**Limitation:** Offset-based pagination inefficient for large datasets

#### Cursor-Based Pagination (GraphQL)

**Current Implementation (src/mcp_ticketer/adapters/github.py:910-934):**
```python
variables = {
    "query": github_query,
    "first": min(query.limit, 100),
    "after": None,
}

# Handle pagination for offset
if query.offset > 0:
    pages_to_skip = query.offset // 100
    for _ in range(pages_to_skip):
        temp_result = await self._graphql_request(full_query, variables)
        page_info = temp_result["search"]["pageInfo"]
        if page_info["hasNextPage"]:
            variables["after"] = page_info["endCursor"]
        else:
            return []  # Offset beyond available results
```

**GraphQL Pagination Fields:**
```graphql
pageInfo {
    hasNextPage
    hasPreviousPage
    startCursor
    endCursor
}
```

### 1.5 Error Handling and Status Codes

**HTTP Status Codes:**
- `200 OK` - Success
- `201 Created` - Resource created
- `204 No Content` - Success with no response body (e.g., DELETE)
- `304 Not Modified` - Conditional request, cached version valid
- `400 Bad Request` - Invalid request format
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - GitHub server error
- `502 Bad Gateway` - GitHub overloaded
- `503 Service Unavailable` - GitHub maintenance

**Current Retry Configuration (src/mcp_ticketer/core/http_client.py:25-48):**
```python
class RetryConfig:
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_on_status: Optional[list[int]] = None,
        retry_on_exceptions: Optional[list[type]] = None,
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on_status = retry_on_status or [429, 502, 503, 504]
        self.retry_on_exceptions = retry_on_exceptions or [
            TimeoutException,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
        ]
```

**Exponential Backoff Implementation:**
```python
def _should_retry(
    self,
    exception: Exception,
    response: Optional[httpx.Response] = None,
    attempt: int = 1,
) -> bool:
    """Determine if request should be retried."""
    if attempt >= self.retry_config.max_retries:
        return False

    # Check response status codes
    if response and response.status_code in self.retry_config.retry_on_status:
        return True

    # Check exception types
    for exc_type in self.retry_config.retry_on_exceptions:
        if isinstance(exception, exc_type):
            return True

    return False
```

---

## 2. Core Endpoints for Ticket Management

### 2.1 Issues API

#### Create Issue
**Endpoint:** `POST /repos/{owner}/{repo}/issues`

**Current Implementation (src/mcp_ticketer/adapters/github.py:515-586):**
```python
async def create(self, ticket: Task) -> Task:
    # Prepare labels (state + priority + tags)
    labels = ticket.tags.copy() if ticket.tags else []

    # Add state label if needed
    state_label = self._get_state_label(ticket.state)
    if state_label:
        labels.append(state_label)
        await self._ensure_label_exists(state_label, "fbca04")

    # Add priority label
    priority_label = self._get_priority_label(ticket.priority)
    labels.append(priority_label)
    await self._ensure_label_exists(priority_label, "d73a4a")

    # Build issue data
    issue_data = {
        "title": ticket.title,
        "body": ticket.description or "",
        "labels": labels,
    }

    if ticket.assignee:
        issue_data["assignees"] = [ticket.assignee]

    if ticket.parent_epic:
        # Try numeric milestone ID or search by title
        issue_data["milestone"] = milestone_number

    response = await self.client.post(
        f"/repos/{self.owner}/{self.repo}/issues", json=issue_data
    )
    response.raise_for_status()

    # Handle DONE/CLOSED states
    if ticket.state in [TicketState.DONE, TicketState.CLOSED]:
        await self.client.patch(
            f"/repos/{self.owner}/{self.repo}/issues/{created_issue['number']}",
            json={"state": "closed"},
        )
```

**Request Body:**
```json
{
  "title": "Issue title",
  "body": "Issue description with markdown support",
  "assignees": ["username"],
  "milestone": 5,
  "labels": ["bug", "high-priority", "in-progress"],
  "assignee": "username"  // Deprecated, use assignees
}
```

**Response:** Full issue object with `number`, `id`, `url`, etc.

#### Read Issue
**Endpoint:** `GET /repos/{owner}/{repo}/issues/{issue_number}`

**Current Implementation (src/mcp_ticketer/adapters/github.py:588-653):**
```python
async def read(self, ticket_id: str) -> Task | Epic | None:
    """Read issue OR milestone with unified find.

    Tries in order:
    1. Issue (most common) - returns Task
    2. Milestone (epic) - returns Epic
    """
    try:
        entity_number = int(ticket_id)
    except ValueError:
        return None

    # Try reading as Issue first
    try:
        response = await self.client.get(
            f"/repos/{self.owner}/{self.repo}/issues/{entity_number}"
        )
        if response.status_code == 200:
            issue = response.json()
            return self._task_from_github_issue(issue)
        elif response.status_code == 404:
            # Try milestone next
            pass
    except httpx.HTTPError as e:
        logger.debug(f"Error reading as Issue: {e}")

    # Try reading as Milestone
    try:
        milestone = await self.get_milestone(entity_number)
        if milestone:
            return milestone
    except Exception as e:
        logger.debug(f"Error reading as Milestone: {e}")

    return None
```

**Response Fields (Transformed to Task):**
- `number` → `id`
- `title` → `title`
- `body` → `description`
- `state` + labels → `state` (TicketState enum)
- Labels → `priority` extraction + `tags`
- `assignees` → `assignee`
- `milestone` → `parent_epic`

#### Update Issue
**Endpoint:** `PATCH /repos/{owner}/{repo}/issues/{issue_number}`

**Current Implementation (src/mcp_ticketer/adapters/github.py:655-782):**

**Label Management Strategy:**
```python
# Get current issue to preserve labels
current_issue = response.json()
current_labels = [label["name"] for label in current_issue.get("labels", [])]

# Remove old state labels
labels_to_update = [
    label for label in current_labels
    if label.lower() not in [sl.lower() for sl in GitHubStateMapping.STATE_LABELS.values()]
]

# Add new state label
state_label = self._get_state_label(new_state)
if state_label:
    await self._ensure_label_exists(state_label, "fbca04")
    labels_to_update.append(state_label)
```

**State Mapping:**
```python
# GitHub has binary states: open/closed
# Extended states tracked via labels
if new_state in [TicketState.DONE, TicketState.CLOSED]:
    update_data["state"] = "closed"
else:
    update_data["state"] = "open"
```

#### List Issues
**Endpoint:** `GET /repos/{owner}/{repo}/issues`

**Query Parameters:**
- `state` - `open`, `closed`, `all`
- `labels` - Comma-separated label names
- `assignee` - Username or `*` (assigned to anyone)
- `milestone` - Milestone number or `*` or `none`
- `sort` - `created`, `updated`, `comments`
- `direction` - `asc`, `desc`
- `per_page` - Results per page (max 100)
- `page` - Page number

**Current Implementation (src/mcp_ticketer/adapters/github.py:806-869):**
```python
params: dict[str, Any] = {
    "per_page": min(limit, 100),
    "page": (offset // limit) + 1 if limit > 0 else 1,
}

if filters:
    # State filter
    if "state" in filters:
        if state in [TicketState.DONE, TicketState.CLOSED]:
            params["state"] = "closed"
        else:
            params["state"] = "open"
            # Add label filter for extended states
            state_label = self._get_state_label(state)
            if state_label:
                params["labels"] = state_label

    # Priority filter via labels
    if "priority" in filters:
        priority_label = self._get_priority_label(priority)
        if "labels" in params:
            params["labels"] += f",{priority_label}"
        else:
            params["labels"] = priority_label

    # Assignee filter
    if "assignee" in filters:
        params["assignee"] = filters["assignee"]

    # Milestone filter
    if "parent_epic" in filters:
        params["milestone"] = filters["parent_epic"]

# Filter out pull requests
issues = [issue for issue in issues if "pull_request" not in issue]
```

#### Search Issues (Advanced)
**Endpoint:** GraphQL `search(query: String!, type: ISSUE)`

**Current Implementation (src/mcp_ticketer/adapters/github.py:871-955):**
```python
# Build GitHub search query
search_parts = [f"repo:{self.owner}/{self.repo}", "is:issue"]

if query.query:
    escaped_query = query.query.replace('"', '\\"')
    search_parts.append(f'"{escaped_query}"')

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
```

**Search Query Examples:**
```
repo:owner/repo is:issue is:open label:"bug"
repo:owner/repo is:issue assignee:username
repo:owner/repo is:issue "authentication" label:"high-priority"
```

#### Issue Comments
**Endpoints:**
- `POST /repos/{owner}/{repo}/issues/{issue_number}/comments` - Add comment
- `GET /repos/{owner}/{repo}/issues/{issue_number}/comments` - List comments

**Current Implementation (src/mcp_ticketer/adapters/github.py:968-1045):**
```python
async def add_comment(self, comment: Comment) -> Comment:
    response = await self.client.post(
        f"/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments",
        json={"body": comment.content},
    )
    response.raise_for_status()

    created_comment = response.json()

    return Comment(
        id=str(created_comment["id"]),
        ticket_id=comment.ticket_id,
        author=created_comment["user"]["login"],
        content=created_comment["body"],
        created_at=datetime.fromisoformat(
            created_comment["created_at"].replace("Z", "+00:00")
        ),
        metadata={
            "github": {
                "id": created_comment["id"],
                "url": created_comment["html_url"],
                "author_avatar": created_comment["user"]["avatar_url"],
            }
        },
    )

async def get_comments(
    self, ticket_id: str, limit: int = 10, offset: int = 0
) -> list[Comment]:
    params = {
        "per_page": min(limit, 100),
        "page": (offset // limit) + 1 if limit > 0 else 1,
    }

    response = await self.client.get(
        f"/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments",
        params=params,
    )
```

### 2.2 Labels API

**Endpoints:**
- `GET /repos/{owner}/{repo}/labels` - List labels
- `POST /repos/{owner}/{repo}/labels` - Create label
- `PATCH /repos/{owner}/{repo}/labels/{name}` - Update label
- `DELETE /repos/{owner}/{repo}/labels/{name}` - Delete label

**Current Implementation (src/mcp_ticketer/adapters/github.py:480-499, 1454-1476):**
```python
async def _ensure_label_exists(
    self, label_name: str, color: str = "0366d6"
) -> None:
    """Ensure a label exists in the repository."""
    if not self._labels_cache:
        response = await self.client.get(f"/repos/{self.owner}/{self.repo}/labels")
        response.raise_for_status()
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

async def list_labels(self) -> list[dict[str, Any]]:
    """List all labels available in the repository."""
    if self._labels_cache:
        return self._labels_cache

    response = await self.client.get(f"/repos/{self.owner}/{self.repo}/labels")
    response.raise_for_status()
    labels = response.json()

    # Transform to standardized format
    standardized_labels = [
        {"id": label["name"], "name": label["name"], "color": label["color"]}
        for label in labels
    ]

    self._labels_cache = standardized_labels
    return standardized_labels
```

**Label-Based State Management:**

GitHub's binary state model (open/closed) is extended via labels:

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

### 2.3 Milestones API

**Endpoints:**
- `POST /repos/{owner}/{repo}/milestones` - Create milestone
- `GET /repos/{owner}/{repo}/milestones/{number}` - Get milestone
- `GET /repos/{owner}/{repo}/milestones` - List milestones
- `PATCH /repos/{owner}/{repo}/milestones/{number}` - Update milestone
- `DELETE /repos/{owner}/{repo}/milestones/{number}` - Delete milestone

**Current Implementation (src/mcp_ticketer/adapters/github.py:2096-2559):**

**Create Milestone:**
```python
async def milestone_create(
    self,
    name: str,
    target_date: date | None = None,
    labels: list[str] | None = None,
    description: str = "",
    project_id: str | None = None,
) -> Milestone:
    # GitHub API expects ISO 8601 datetime for due_on
    due_on = None
    if target_date:
        due_on = dt.combine(target_date, dt.min.time()).isoformat() + "Z"

    milestone_data = {
        "title": name,
        "description": description,
        "state": "open",
    }

    if due_on:
        milestone_data["due_on"] = due_on

    # Create milestone via GitHub API
    response = await self.client.post(
        f"/repos/{self.owner}/{self.repo}/milestones",
        json=milestone_data,
    )
    response.raise_for_status()

    gh_milestone = response.json()

    # Convert to Milestone model
    milestone = self._github_milestone_to_milestone(gh_milestone, labels)

    # Save to local storage for label tracking (labels not stored in GitHub)
    manager = MilestoneManager(config_dir)
    manager.save_milestone(milestone)

    return milestone
```

**Hybrid Storage Strategy:**
- GitHub API: Stores title, description, due_on, state, progress
- Local Storage (`.mcp-ticketer/milestones.json`): Stores labels (GitHub limitation)

**Progress Tracking:**
```python
# GitHub calculates progress automatically
total = gh_milestone.get("open_issues", 0) + gh_milestone.get("closed_issues", 0)
closed = gh_milestone.get("closed_issues", 0)
progress_pct = (closed / total * 100) if total > 0 else 0.0
```

**State Mapping:**
```python
# GitHub native: open, closed
# Computed states based on due date
state = "closed" if gh_milestone["state"] == "closed" else "open"
if state == "open" and target_date:
    if target_date < date.today():
        state = "closed"  # Past due
    else:
        state = "active"
```

### 2.4 Projects API (v2)

**GraphQL Query for Iterations (Cycles/Sprints):**

```python
GET_PROJECT_ITERATIONS = """
    query GetProjectIterations($projectId: ID!, $first: Int!, $after: String) {
        node(id: $projectId) {
            ... on ProjectV2 {
                iterations(first: $first, after: $after) {
                    nodes {
                        id
                        title
                        startDate
                        duration
                    }
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                }
            }
        }
    }
"""
```

**Current Implementation (src/mcp_ticketer/adapters/github.py:1724-1830):**
```python
async def list_cycles(
    self, project_id: str | None = None, limit: int = 50
) -> list[dict[str, Any]]:
    """List GitHub Project iterations (cycles/sprints).

    Requires Projects V2 node ID (e.g., 'PVT_kwDOABcdefgh').
    """
    if not project_id:
        raise ValueError(
            "project_id is required for GitHub Projects V2. "
            "Provide a project node ID (e.g., 'PVT_kwDOABcdefgh')."
        )

    query = GitHubGraphQLQueries.GET_PROJECT_ITERATIONS
    variables = {"projectId": project_id, "first": min(limit, 100), "after": None}

    result = await self._graphql_request(query, variables)

    project_node = result.get("node")
    if not project_node:
        raise ValueError(
            f"Project not found with ID: {project_id}. "
            "Verify the project ID is correct and you have access."
        )

    iterations_data = project_node.get("iterations", {})
    iteration_nodes = iterations_data.get("nodes", [])

    # Calculate end dates from start + duration
    iterations = []
    for iteration in iteration_nodes:
        start_date = iteration.get("startDate")
        duration = iteration.get("duration", 0)

        end_date = None
        if start_date and duration:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end_dt = start_dt + timedelta(days=duration)
            end_date = end_dt.isoformat()

        iterations.append({
            "id": iteration["id"],
            "title": iteration.get("title", ""),
            "startDate": start_date,
            "duration": duration,
            "endDate": end_date,
        })

    return iterations
```

**Limitation:** Requires project node ID (not numeric ID shown in UI)

**How to Get Project Node ID:**
```graphql
query {
  organization(login: "org-name") {
    projectV2(number: 1) {
      id  # Returns: PVT_kwDOABcdefgh
    }
  }
}
```

### 2.5 Pull Requests API

**Create Pull Request from Issue:**

**Current Implementation (src/mcp_ticketer/adapters/github.py:1170-1350):**
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
    """Create PR linked to issue."""
    issue = await self.read(ticket_id)
    if not issue:
        raise ValueError(f"Issue #{ticket_id} not found")

    # Auto-generate branch name from issue
    if not head_branch:
        safe_title = "-".join(
            issue.title.lower()
            .replace("[", "").replace("]", "")
            .replace("#", "")
            .split()[:5]
        )
        head_branch = f"{issue_number}-{safe_title}"

    # Auto-generate PR title
    if not title:
        title = f"[#{issue_number}] {issue.title}"

    # Auto-generate PR body with issue link
    if not body:
        body = f"""## Summary

This PR addresses issue #{issue_number}.

**Issue:** #{issue_number} - {issue.title}
**Link:** {issue.metadata.get('github', {}).get('url', '')}

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
- [ ] Documentation updated if needed

Fixes #{issue_number}
"""

    # Create branch if doesn't exist
    if not branch_exists:
        base_response = await self.client.get(
            f"/repos/{self.owner}/{self.repo}/branches/{base_branch}"
        )
        base_sha = base_response.json()["commit"]["sha"]

        await self.client.post(
            f"/repos/{self.owner}/{self.repo}/git/refs",
            json={
                "ref": f"refs/heads/{head_branch}",
                "sha": base_sha,
            },
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

    # Add comment to issue about PR
    await self.add_comment(
        Comment(
            ticket_id=ticket_id,
            content=f"Pull request #{pr['number']} has been created: {pr['html_url']}",
            author="system",
        )
    )

    return {
        "number": pr["number"],
        "url": pr["html_url"],
        "api_url": pr["url"],
        "branch": head_branch,
        "state": pr["state"],
        "draft": pr.get("draft", False),
        "title": pr["title"],
        "linked_issue": issue_number,
    }
```

**Link Existing PR to Issue:**

```python
async def link_existing_pull_request(
    self,
    ticket_id: str,
    pr_url: str,
) -> dict[str, Any]:
    """Link existing PR to ticket."""
    # Parse PR URL
    pr_pattern = r"github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.search(pr_pattern, pr_url)

    if not match:
        raise ValueError(f"Invalid GitHub PR URL format: {pr_url}")

    pr_owner, pr_repo, pr_number = match.groups()

    # Verify same repository
    if pr_owner != self.owner or pr_repo != self.repo:
        raise ValueError(
            f"PR must be from the same repository ({self.owner}/{self.repo})"
        )

    # Get PR details
    pr_response = await self.client.get(
        f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}"
    )
    pr = pr_response.json()

    # Update PR body to include issue reference
    current_body = pr.get("body", "")
    issue_ref = f"#{issue_number}"

    if issue_ref not in current_body:
        updated_body = current_body or ""
        if updated_body:
            updated_body += "\n\n"
        updated_body += f"Related to #{issue_number}"

        await self.client.patch(
            f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}",
            json={"body": updated_body},
        )

    # Add comment to issue
    await self.add_comment(
        Comment(
            ticket_id=ticket_id,
            content=f"Linked to pull request #{pr_number}: {pr_url}",
            author="system",
        )
    )

    return {
        "success": True,
        "pr_number": pr["number"],
        "pr_url": pr["html_url"],
        "pr_title": pr["title"],
        "pr_state": pr["state"],
        "linked_issue": issue_number,
        "message": f"Successfully linked PR #{pr_number} to issue #{issue_number}",
    }
```

---

## 3. Best Practices

### 3.1 Conditional Requests (ETags)

**⚠️ NOT CURRENTLY IMPLEMENTED - Opportunity for Enhancement**

**How It Works:**
```python
# First request
response = await client.get("/repos/owner/repo/issues/123")
etag = response.headers.get("ETag")  # e.g., "W/\"abc123\""

# Subsequent requests with ETag
headers = {"If-None-Match": etag}
response = await client.get("/repos/owner/repo/issues/123", headers=headers)

if response.status_code == 304:
    # Not modified, use cached version
    return cached_issue
else:
    # Updated, store new ETag and data
    new_etag = response.headers.get("ETag")
    return response.json()
```

**Benefits:**
- Reduces bandwidth consumption
- Faster responses (304 vs 200)
- Doesn't count against rate limit if 304 returned
- Particularly useful for frequently accessed issues

**Recommended Implementation Location:**
- `BaseHTTPClient` class (src/mcp_ticketer/core/http_client.py)
- Add ETag cache dictionary
- Modify GET requests to include If-None-Match header
- Handle 304 responses

### 3.2 GraphQL vs REST Tradeoffs

**Current Hybrid Approach:**

**REST API Used For:**
- CRUD operations (create, update, delete issues)
- Milestone management
- Label operations
- Comments
- Simple list operations

**GraphQL Used For:**
- Advanced search (better filtering)
- Project iterations (Projects V2 only available via GraphQL)
- Complex queries with nested data
- Reducing over-fetching

**GraphQL Advantages:**
- Single request for multiple resources
- Precise field selection (reduce payload size)
- No over-fetching
- Type-safe queries

**GraphQL Disadvantages:**
- More complex query construction
- No automatic caching like REST
- Requires understanding of schema
- Point-based rate limiting (different from REST)

**Current GraphQL Fragments (src/mcp_ticketer/adapters/github.py:58-120):**
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
        milestone { id number title state description }
        projectCards(first: 10) {
            nodes {
                project { name url }
                column { name }
            }
        }
        comments(first: 100) {
            nodes {
                id
                body
                author { login }
                createdAt
            }
        }
        reactions(first: 10) {
            nodes {
                content
                user { login }
            }
        }
    }
"""
```

**Best Practice:** Use GraphQL for read-heavy operations with complex filtering, REST for mutations.

### 3.3 Webhook Integration Patterns

**⚠️ NOT CURRENTLY IMPLEMENTED - Future Enhancement**

**Webhook Events Relevant to Ticketing:**
- `issues` - Issue created, edited, deleted, closed, reopened
- `issue_comment` - Comment added, edited, deleted
- `milestone` - Milestone created, edited, deleted, closed, opened
- `label` - Label created, edited, deleted
- `pull_request` - PR created, edited, closed, merged
- `project_card` - Project card moved, created, deleted

**Implementation Considerations:**
1. **Webhook Endpoint:** Requires HTTP server to receive events
2. **Signature Verification:** Validate webhook payload with HMAC
3. **Event Processing:** Queue-based processing for reliability
4. **Idempotency:** Handle duplicate events
5. **Real-time Updates:** Update local cache on webhook events

**Signature Verification:**
```python
import hmac
import hashlib

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature."""
    expected_signature = "sha256=" + hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)
```

**Recommended Use Cases:**
- Real-time issue updates in UI
- Automated workflows (e.g., auto-assign on label)
- Notification systems
- Audit logging

### 3.4 Search API Usage and Limits

**Search Rate Limits:**
- **Authenticated:** 30 requests/minute
- **Unauthenticated:** 10 requests/minute

**Search API Capabilities:**

**Code Search:**
```
filename:config extension:json repo:owner/repo
```

**Issue Search (Current Implementation):**
```python
# Search query construction
search_parts = [
    f"repo:{self.owner}/{self.repo}",
    "is:issue",
    f'"{escaped_query}"',
    "is:open",
    f'label:"{label}"',
    f"assignee:{username}",
]
github_query = " ".join(search_parts)
```

**Advanced Search Qualifiers:**
- `author:username` - Issue creator
- `assignee:username` - Issue assignee
- `mentions:username` - User mentioned in issue
- `commenter:username` - User commented
- `involves:username` - Combination of above
- `label:"bug"` - Has label
- `created:>2025-01-01` - Date filters
- `updated:<2025-12-31` - Last updated
- `is:open`, `is:closed` - State
- `is:pr`, `is:issue` - Type
- `no:assignee` - No assignee
- `no:label` - No labels
- `milestone:"v2.0"` - In milestone
- `project:repo/1` - In project board

**Performance Tip:** Use GraphQL search for better performance and richer results.

### 3.5 Private Repositories and Organization Context

**Current Authentication:**
- Personal Access Token (PAT) with `repo` scope
- Repository ownership: `owner` + `repo` configuration

**Organization Context:**

**Get Organization Members:**
```python
# Not currently implemented
async def get_organization_members(org: str) -> list[dict]:
    response = await client.get(f"/orgs/{org}/members")
    return response.json()
```

**Repository Permissions:**
```python
# Not currently implemented
async def get_repository_permissions(user: str) -> dict:
    response = await client.get(
        f"/repos/{self.owner}/{self.repo}/collaborators/{user}/permission"
    )
    return response.json()
```

**Team Management:**
```python
# Not currently implemented
async def list_team_repositories(org: str, team_slug: str) -> list[dict]:
    response = await client.get(f"/orgs/{org}/teams/{team_slug}/repos")
    return response.json()
```

---

## 4. Current mcp-ticketer GitHub Adapter Analysis

### 4.1 Architecture Overview

**File:** `src/mcp_ticketer/adapters/github.py`
**Lines of Code:** 2,568
**Class:** `GitHubAdapter(BaseAdapter[Task])`

**Components:**
1. **State Mapping** (`GitHubStateMapping`) - Label-based extended states
2. **GraphQL Queries** (`GitHubGraphQLQueries`) - Fragments and queries
3. **Main Adapter** (`GitHubAdapter`) - REST/GraphQL hybrid implementation

### 4.2 Endpoints Currently Used

**REST API v3 Endpoints:**
- ✅ `GET /repos/{owner}/{repo}/issues` - List issues
- ✅ `POST /repos/{owner}/{repo}/issues` - Create issue
- ✅ `GET /repos/{owner}/{repo}/issues/{number}` - Get issue
- ✅ `PATCH /repos/{owner}/{repo}/issues/{number}` - Update issue
- ✅ `POST /repos/{owner}/{repo}/issues/{number}/comments` - Add comment
- ✅ `GET /repos/{owner}/{repo}/issues/{number}/comments` - List comments
- ✅ `GET /repos/{owner}/{repo}/labels` - List labels
- ✅ `POST /repos/{owner}/{repo}/labels` - Create label
- ✅ `GET /repos/{owner}/{repo}/milestones` - List milestones
- ✅ `POST /repos/{owner}/{repo}/milestones` - Create milestone
- ✅ `GET /repos/{owner}/{repo}/milestones/{number}` - Get milestone
- ✅ `PATCH /repos/{owner}/{repo}/milestones/{number}` - Update milestone
- ✅ `DELETE /repos/{owner}/{repo}/milestones/{number}` - Delete milestone
- ✅ `GET /repos/{owner}/{repo}/collaborators` - Get collaborators
- ✅ `GET /user` - Get current user
- ✅ `GET /rate_limit` - Check rate limit
- ✅ `POST /repos/{owner}/{repo}/pulls` - Create pull request
- ✅ `GET /repos/{owner}/{repo}/pulls/{number}` - Get pull request
- ✅ `PATCH /repos/{owner}/{repo}/pulls/{number}` - Update pull request
- ✅ `POST /repos/{owner}/{repo}/git/refs` - Create branch

**GraphQL API v4 Queries:**
- ✅ `GetIssue` - Get issue with nested data (comments, reactions, projects)
- ✅ `SearchIssues` - Advanced issue search with filters
- ✅ `GetProjectIterations` - List project iterations (sprints/cycles)

### 4.3 Missing Functionality (Gaps)

**API Gaps:**
1. ❌ **Reactions API** - Add/remove reactions (👍, ❤️, etc.)
2. ❌ **Issue Events** - Timeline events (labeled, assigned, referenced)
3. ❌ **Issue Locks** - Lock/unlock conversation
4. ❌ **Issue Transfer** - Transfer issue to another repository
5. ❌ **Assignee Management** - Add/remove multiple assignees
6. ❌ **Label Management** - Update/delete labels (only create exists)
7. ❌ **Milestone Batch Operations** - Bulk assign issues to milestone
8. ❌ **Project Cards** - Add/move issues in project boards (classic)
9. ❌ **Projects V2 Full Support** - Create/update project items, fields
10. ❌ **Code Scanning Alerts** - Security alerts for issues
11. ❌ **Repository Topics** - Tag repositories with topics
12. ❌ **Issue Templates** - List/use issue templates
13. ❌ **PR Reviews** - Get/create/update reviews
14. ❌ **PR Review Comments** - Line-level comments
15. ❌ **PR Status Checks** - CI/CD check statuses
16. ❌ **PR Mergeability** - Check if PR can be merged
17. ❌ **Webhooks Management** - Create/list/delete webhooks
18. ❌ **Notifications** - Mark as read, subscribe/unsubscribe
19. ❌ **Team Mentions** - @team mentions in issues
20. ❌ **Organization Projects** - Org-level project boards

**Feature Gaps:**
1. ❌ **ETag Caching** - Conditional requests for bandwidth savings
2. ❌ **Webhook Integration** - Real-time event processing
3. ❌ **GitHub Apps Authentication** - Higher rate limits, fine-grained permissions
4. ❌ **OAuth2 Flow** - User-level authentication
5. ❌ **Batch Operations** - Bulk issue updates
6. ❌ **Issue Templates** - Programmatic template usage
7. ❌ **Advanced Search Builders** - Type-safe search query construction
8. ❌ **Retry-After Header Handling** - Better rate limit backoff
9. ❌ **Parallel Requests** - Concurrent API calls for performance
10. ❌ **Response Pagination Helpers** - Automatic page fetching

### 4.4 Code Quality Assessment

**Strengths:**
- ✅ **Comprehensive Error Handling:** Try/except blocks with logging
- ✅ **Rate Limiting:** Built-in rate limiter (5000 req/hr)
- ✅ **Retry Logic:** Exponential backoff for 429, 502, 503, 504
- ✅ **Type Safety:** Full type hints throughout
- ✅ **State Management:** Label-based extended states (in_progress, blocked, etc.)
- ✅ **Priority Mapping:** P0-P3 labels with custom schemes
- ✅ **Hybrid REST/GraphQL:** Uses best tool for each operation
- ✅ **Caching:** Labels and milestones cached to reduce API calls
- ✅ **Validation:** Credential validation before operations
- ✅ **Documentation:** Comprehensive docstrings

**Technical Debt Items:**
1. ⚠️ **Label Cache Invalidation:** No TTL, manual refresh needed
2. ⚠️ **Milestone Cache Invalidation:** No automatic refresh
3. ⚠️ **Offset Pagination Inefficiency:** GraphQL offset emulation wasteful
4. ⚠️ **No Connection Pooling:** Creates new client per adapter instance
5. ⚠️ **Synchronous Cache Access:** Labels cache not async-safe
6. ⚠️ **Hard-coded Colors:** Label colors not configurable
7. ⚠️ **No Bulk Operations:** One API call per issue update
8. ⚠️ **GraphQL Fragment Duplication:** ISSUE_FRAGMENT repeated in queries
9. ⚠️ **Mixed Error Handling:** Some methods return None, others raise
10. ⚠️ **No Request Logging:** Difficult to debug API issues

**Anti-Patterns Identified:**
1. **Cache Staleness:** Labels cache never expires
   ```python
   # Current implementation
   if not self._labels_cache:  # Only loads once
       response = await self.client.get(...)
   ```
   **Fix:** Add TTL-based cache invalidation

2. **Inefficient Offset Pagination:**
   ```python
   # Wasteful: Fetches and discards 500 results to skip to page 6
   pages_to_skip = query.offset // 100  # 500 // 100 = 5
   for _ in range(pages_to_skip):
       temp_result = await self._graphql_request(...)  # Discard
   ```
   **Fix:** Use cursor-based pagination, store cursors

3. **Duplicate Label Creation Attempts:**
   ```python
   # Risk: Multiple concurrent creates can race
   if label_name.lower() not in existing_labels:
       response = await self.client.post(...)  # Race condition
   ```
   **Fix:** Check-then-act pattern, handle 422 errors gracefully

### 4.5 Performance Characteristics

**API Call Patterns:**

**Issue Creation:**
- Minimum: 3 API calls (create issue + 2 label creates)
- Maximum: 5+ API calls (if milestone lookup needed)

**Issue Retrieval:**
- Cached: 0 API calls (if in cache)
- Uncached: 1 API call (GET issue)
- With milestone: 2 API calls (GET issue + GET milestone)

**Issue Search:**
- GraphQL: 1 API call (multiple results)
- Pagination: +1 per page

**Milestone Operations:**
- Create: 1 API call + local file write
- Read: 1 API call + local file read
- List: 1 API call + local file reads

**Bottlenecks:**
1. **Label Synchronization:** Every issue create ensures 3+ labels exist
2. **Milestone Cache Miss:** No caching, reads file every time
3. **GraphQL Offset Emulation:** O(n) API calls for large offsets
4. **Sequential Label Creates:** Not parallelized
5. **No Request Batching:** Each operation separate API call

**Optimization Opportunities:**
1. **Batch Label Creation:** Create all labels in single loop
2. **Parallel API Calls:** Use `asyncio.gather()` for independent requests
3. **Cursor-Based Pagination:** Eliminate offset emulation
4. **In-Memory Cache:** Avoid file I/O for milestones
5. **Request Coalescing:** Combine multiple updates into single PATCH

### 4.6 Test Coverage Analysis

**Test Files:**
- `tests/adapters/test_github.py` - 187 lines - Integration test
- `tests/adapters/test_github_new_operations.py` - 530 lines - New features
- `tests/adapters/test_github_epic_attachments.py` - Not counted

**Test Cases (from grep output):**
- ✅ `test_github_adapter` - Full integration workflow
- ✅ `test_list_cycles_success` - Project iterations
- ✅ `test_list_cycles_no_project_id` - Error handling
- ✅ `test_list_cycles_project_not_found` - 404 handling
- ✅ `test_list_cycles_invalid_credentials` - Auth errors
- ✅ `test_get_issue_status_*` - Status tracking (7 tests)
- ✅ `test_list_issue_statuses_*` - Available statuses (3 tests)
- ✅ `test_list_project_labels_*` - Label operations (5 tests)
- ✅ `test_update_milestone_*` - Milestone updates (10 tests)
- ✅ `test_add_attachment_*` - File attachments (5 tests)
- ✅ `test_markdown_formatting_*` - Rich text support
- ✅ `test_unicode_and_emoji_support` - Character encoding
- ✅ `test_concurrent_updates_handling` - Race conditions

**Coverage Gaps:**
- ❌ No tests for search edge cases (empty results, >1000 results)
- ❌ No tests for rate limit exhaustion scenarios
- ❌ No tests for network failures/timeouts
- ❌ No tests for GraphQL error responses
- ❌ No tests for invalid state transitions
- ❌ No tests for label cache invalidation
- ❌ No tests for concurrent label creation races
- ❌ No tests for pagination cursor handling

---

## 5. Skill Design Requirements

### 5.1 Core Patterns to Document

**Priority 1: Essential Patterns**

1. **Authentication and Configuration**
   ```python
   # PAT Authentication
   config = {
       "token": "ghp_xxxxxxxxxxxx",
       "owner": "organization",
       "repo": "repository",
   }
   adapter = GitHubAdapter(config)

   # Validate credentials
   is_valid, error = adapter.validate_credentials()
   ```

2. **Rate Limiting Strategy**
   ```python
   # Check remaining quota
   rate_limit = await adapter.get_rate_limit()
   remaining = rate_limit["rate"]["remaining"]
   reset_time = datetime.fromtimestamp(rate_limit["rate"]["reset"])

   # Automatic retry on 429
   # Built-in: RetryConfig with exponential backoff
   ```

3. **Label-Based State Management**
   ```python
   # Extended states via labels
   STATE_LABELS = {
       TicketState.IN_PROGRESS: "in-progress",
       TicketState.BLOCKED: "blocked",
       TicketState.READY: "ready",
   }

   # Creating issue with extended state
   task = Task(
       title="Feature request",
       state=TicketState.IN_PROGRESS,  # Creates "in-progress" label
       priority=Priority.HIGH,  # Creates "P1" label
       tags=["feature", "api"],
   )
   ```

4. **Milestone Management Pattern**
   ```python
   # Create milestone (Epic)
   milestone = await adapter.milestone_create(
       name="v2.1.0 Release",
       target_date=date(2025, 12, 31),
       labels=["release", "v2.1"],  # Stored locally
       description="Q4 2025 release",
   )

   # Hybrid storage: GitHub API + local labels
   # Progress auto-calculated: (closed_issues / total_issues) * 100
   ```

5. **Hybrid REST/GraphQL Pattern**
   ```python
   # Use REST for mutations
   created = await adapter.create(task)
   updated = await adapter.update(task_id, {"state": "closed"})

   # Use GraphQL for complex queries
   results = await adapter.search(SearchQuery(
       query="authentication bug",
       state=TicketState.OPEN,
       tags=["security"],
   ))
   ```

**Priority 2: Advanced Patterns**

6. **Pull Request Automation**
   ```python
   # Create PR from issue with auto-generated branch/title/body
   pr = await adapter.create_pull_request(
       ticket_id="123",
       base_branch="main",
       # Auto-generates:
       # - Branch: "123-fix-authentication-bug"
       # - Title: "[#123] Fix authentication bug"
       # - Body: Links to issue, checklist, etc.
   )

   # Link existing PR
   result = await adapter.link_existing_pull_request(
       ticket_id="123",
       pr_url="https://github.com/owner/repo/pull/456",
   )
   ```

7. **Advanced Search Query Construction**
   ```python
   # Type-safe search builder
   query = SearchQuery(
       query="authentication",
       state=TicketState.OPEN,
       priority=Priority.HIGH,
       assignee="username",
       tags=["security", "bug"],
   )

   # Translates to:
   # repo:owner/repo is:issue is:open
   # "authentication" label:"P1" assignee:username
   # label:"security" label:"bug"
   ```

8. **Pagination Best Practices**
   ```python
   # REST API pagination (offset-based)
   issues = await adapter.list(limit=50, offset=100)

   # GraphQL pagination (cursor-based)
   # Automatically handles pageInfo cursors
   # More efficient for large datasets
   ```

9. **Error Handling Patterns**
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
           # Rate limited (auto-retried)
           logger.info("Rate limited, retrying...")
       else:
           # Other HTTP errors
           logger.error(f"HTTP {e.response.status_code}: {e}")
   except httpx.TimeoutException:
       # Network timeout
       logger.error("Request timed out")
   ```

10. **Caching Strategy**
    ```python
    # Label caching (in-memory)
    # Loaded once per adapter instance
    labels = await adapter.list_labels()  # First call: API request
    labels = await adapter.list_labels()  # Second call: cache hit

    # Milestone caching (file-based)
    # Hybrid: GitHub API + local JSON
    milestone = await adapter.milestone_get("42")
    # - Fetches from GitHub: title, description, progress
    # - Loads from local: labels
    ```

### 5.2 Example Operations

**Example 1: Create Issue with Full Workflow**
```python
# Create issue with extended state and priority
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

# Create milestone for sprint
milestone = await adapter.milestone_create(
    name="Sprint 24 - Authentication",
    target_date=date(2025, 12, 31),
    labels=["sprint-24", "Q4"],
    description="Focus: OAuth2 and security improvements",
)

# Link issue to milestone
await adapter.update(created_issue.id, {
    "parent_epic": milestone.id,
})

# Add comment with progress update
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

# Create PR from issue
pr = await adapter.create_pull_request(
    ticket_id=created_issue.id,
    base_branch="main",
    draft=True,  # WIP
)

print(f"Created draft PR #{pr['number']}: {pr['url']}")

# When work complete, transition state
await adapter.update(created_issue.id, {
    "state": TicketState.READY,  # Adds "ready" label
})

# Close issue when merged
await adapter.update(created_issue.id, {
    "state": TicketState.DONE,  # Closes issue
})
```

**Example 2: Advanced Issue Search and Filtering**
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

**Example 3: Milestone Progress Tracking**
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

**Example 4: Project Iterations (Sprints)**
```python
# List sprints/cycles for project
# Note: Requires Projects V2 node ID
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

### 5.3 Common Pitfalls and Solutions

**Pitfall 1: Rate Limit Exhaustion**
```python
# ❌ BAD: No rate limit awareness
for i in range(10000):
    await adapter.create(task)  # Will hit 429 after 5000

# ✅ GOOD: Check rate limit before batch operations
rate_limit = await adapter.get_rate_limit()
if rate_limit["rate"]["remaining"] < 100:
    reset_time = datetime.fromtimestamp(rate_limit["rate"]["reset"])
    wait_seconds = (reset_time - datetime.now()).total_seconds()
    print(f"Rate limit low, waiting {wait_seconds}s...")
    await asyncio.sleep(wait_seconds)

# Batch operations with throttling
for i in range(len(tasks)):
    await adapter.create(tasks[i])
    if (i + 1) % 100 == 0:
        await asyncio.sleep(1)  # Throttle
```

**Pitfall 2: Label Cache Staleness**
```python
# ❌ BAD: Label created outside adapter, cache stale
# User manually creates "critical" label in GitHub UI
await adapter.create(Task(tags=["critical"]))  # Tries to create duplicate

# ✅ GOOD: Clear cache or use ensure_label_exists
adapter._labels_cache = None  # Clear cache
await adapter.create(Task(tags=["critical"]))  # Re-fetches labels

# OR: Pre-create labels
await adapter._ensure_label_exists("critical", "d73a4a")
```

**Pitfall 3: Inefficient Pagination**
```python
# ❌ BAD: Fetching all issues with large offset
issues = await adapter.list(limit=10, offset=5000)
# GraphQL emulation: Fetches 5000 issues, returns 10

# ✅ GOOD: Use cursor-based pagination for large datasets
# Store cursor from previous page
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

**Pitfall 4: Milestone Label Confusion**
```python
# ❌ BAD: Expecting labels stored in GitHub milestone
milestone = await adapter.milestone_get("5")
# milestone.labels fetched from local storage, NOT GitHub

# ✅ GOOD: Understand hybrid storage
# GitHub stores: title, description, due_on, state, progress
# Local storage: labels (not supported by GitHub API)

# To sync labels, always use milestone methods
await adapter.milestone_update("5", labels=["new-label"])
```

**Pitfall 5: State Transition Errors**
```python
# ❌ BAD: Direct state change without label update
await adapter.client.patch(
    f"/repos/{owner}/{repo}/issues/{number}",
    json={"state": "open"},  # Missing state label
)

# ✅ GOOD: Use adapter methods for state transitions
await adapter.update(issue_id, {
    "state": TicketState.IN_PROGRESS,
    # Automatically:
    # 1. Adds "in-progress" label
    # 2. Removes old state labels
    # 3. Sets GitHub state to "open"
})
```

**Pitfall 6: Pull Request Creation Failures**
```python
# ❌ BAD: Creating PR without checking branch exists
pr = await adapter.create_pull_request(
    ticket_id="123",
    head_branch="feature-branch",  # Might not exist
)

# ✅ GOOD: Adapter auto-creates branch if needed
pr = await adapter.create_pull_request(
    ticket_id="123",
    # Omit head_branch: auto-generates from issue title
    # Creates branch from base if doesn't exist
)

# OR: Check branch existence first
branches = await adapter.client.get(f"/repos/{owner}/{repo}/branches")
branch_names = [b["name"] for b in branches.json()]
if "feature-branch" not in branch_names:
    # Create branch manually
    pass
```

### 5.4 Best Practices Summary

**Authentication:**
- ✅ Use Personal Access Token with `repo` scope
- ✅ Store token in environment variables, not code
- ✅ Validate credentials before operations
- ⚠️ Consider GitHub Apps for higher rate limits (future)

**Rate Limiting:**
- ✅ Monitor remaining quota with `get_rate_limit()`
- ✅ Use exponential backoff for 429 responses (built-in)
- ✅ Throttle batch operations (sleep between requests)
- ⚠️ GraphQL uses point-based system (different limits)

**State Management:**
- ✅ Use label-based extended states (in_progress, blocked, etc.)
- ✅ Let adapter handle label synchronization
- ✅ Use `update()` method for state transitions, not raw API
- ⚠️ GitHub native states are binary: open/closed

**Milestone Management:**
- ✅ Understand hybrid storage (GitHub API + local labels)
- ✅ Use milestone methods, not raw API calls
- ✅ Check progress before closing milestones
- ⚠️ Labels stored locally, not in GitHub

**Search and Filtering:**
- ✅ Use GraphQL search for complex queries
- ✅ Use REST list for simple filtering
- ✅ Build search queries with SearchQuery model
- ⚠️ Search API has lower rate limit (30/min)

**Performance:**
- ✅ Cache labels and milestones
- ✅ Use cursor-based pagination for large datasets
- ✅ Batch independent operations with `asyncio.gather()`
- ⚠️ Clear cache when stale

**Error Handling:**
- ✅ Handle 422 validation errors gracefully
- ✅ Retry 429, 502, 503, 504 automatically
- ✅ Log errors with context
- ⚠️ Network errors can occur, use timeouts

---

## 6. Recommendations

### 6.1 Adapter Improvements

**Priority 1: Critical Enhancements**

1. **ETag Caching Implementation**
   - **Impact:** Reduce bandwidth, improve performance, save rate limit quota
   - **Effort:** Medium (2-3 days)
   - **Location:** `BaseHTTPClient` class
   - **Implementation:**
     ```python
     class ETagCache:
         def __init__(self):
             self._cache: dict[str, tuple[str, Any, datetime]] = {}

         def get(self, url: str, etag: str) -> Optional[Any]:
             if url in self._cache:
                 cached_etag, data, timestamp = self._cache[url]
                 if cached_etag == etag:
                     return data
             return None

         def set(self, url: str, etag: str, data: Any):
             self._cache[url] = (etag, data, datetime.now())
     ```

2. **Cursor-Based Pagination**
   - **Impact:** Eliminate inefficient offset emulation
   - **Effort:** Medium (2-3 days)
   - **Implementation:**
     ```python
     class PaginationCursor:
         def __init__(self, cursor: str | None = None):
             self.cursor = cursor

         async def next_page(self, adapter, query):
             variables = {"after": self.cursor, "first": 100}
             result = await adapter._graphql_request(query, variables)
             self.cursor = result["pageInfo"]["endCursor"]
             return result["nodes"]
     ```

3. **Label Cache TTL**
   - **Impact:** Prevent stale cache issues
   - **Effort:** Low (1 day)
   - **Implementation:**
     ```python
     from datetime import datetime, timedelta

     class TimedCache:
         def __init__(self, ttl_seconds: int = 300):
             self._cache = {}
             self._timestamps = {}
             self.ttl = timedelta(seconds=ttl_seconds)

         def get(self, key: str) -> Optional[Any]:
             if key in self._cache:
                 if datetime.now() - self._timestamps[key] < self.ttl:
                     return self._cache[key]
                 else:
                     del self._cache[key]
                     del self._timestamps[key]
             return None
     ```

**Priority 2: Feature Additions**

4. **GitHub Apps Authentication**
   - **Impact:** Higher rate limits (15K/hr), fine-grained permissions
   - **Effort:** High (1 week)
   - **Use Case:** Organization-wide integrations

5. **Webhook Integration**
   - **Impact:** Real-time updates, reduced polling
   - **Effort:** High (1 week)
   - **Use Case:** Live dashboards, notifications

6. **Batch Operations**
   - **Impact:** Reduce API calls, improve performance
   - **Effort:** Medium (3-4 days)
   - **Example:**
     ```python
     async def batch_update_issues(
         self,
         updates: list[dict[str, Any]],
     ) -> list[Task]:
         tasks = []
         for update in updates:
             task = asyncio.create_task(
                 self.update(update["id"], update["changes"])
             )
             tasks.append(task)

         return await asyncio.gather(*tasks)
     ```

**Priority 3: Quality Improvements**

7. **Request Logging**
   - **Impact:** Easier debugging, performance monitoring
   - **Effort:** Low (1 day)
   - **Implementation:**
     ```python
     import logging

     logger = logging.getLogger(__name__)

     async def _request(self, method: str, endpoint: str, **kwargs):
         logger.debug(f"{method} {endpoint}")
         start = time.time()
         response = await self.client.request(method, endpoint, **kwargs)
         duration = time.time() - start
         logger.debug(f"{method} {endpoint} - {response.status_code} ({duration:.2f}s)")
         return response
     ```

8. **Error Context Enhancement**
   - **Impact:** Better error messages, easier troubleshooting
   - **Effort:** Low (1-2 days)
   - **Implementation:**
     ```python
     class GitHubAPIError(Exception):
         def __init__(self, status_code: int, message: str, endpoint: str):
             self.status_code = status_code
             self.message = message
             self.endpoint = endpoint
             super().__init__(
                 f"GitHub API error {status_code} at {endpoint}: {message}"
             )
     ```

9. **Test Coverage Expansion**
   - **Impact:** Prevent regressions, improve reliability
   - **Effort:** Medium (3-4 days)
   - **Focus Areas:**
     - Search edge cases
     - Rate limit scenarios
     - Network failures
     - Concurrent operations

### 6.2 Skill Structure Proposal

**Skill File:** `toolchains-platforms-github-api.md`

**Proposed Structure:**

```markdown
# GitHub REST API v3 Integration Skill

## Overview
- GitHub API capabilities
- When to use REST vs GraphQL
- Authentication methods
- Rate limiting strategies

## Core Patterns

### 1. Authentication and Configuration
- PAT setup and scopes
- Environment variable management
- Credential validation

### 2. Rate Limiting Strategy
- Checking quota
- Handling 429 responses
- Exponential backoff
- Batch operation throttling

### 3. Label-Based State Management
- Extended state mapping
- Label synchronization
- Priority labels
- Custom label schemes

### 4. Milestone Management
- Hybrid storage pattern
- Progress tracking
- Date-based state computation
- Label storage workarounds

### 5. Hybrid REST/GraphQL Pattern
- When to use each API
- GraphQL fragments
- Pagination strategies
- Error handling differences

## Advanced Operations

### 6. Pull Request Automation
- Creating PRs from issues
- Auto-generating branches
- Linking existing PRs
- PR templates

### 7. Advanced Search
- Query construction
- Search qualifiers
- Filtering techniques
- Performance optimization

### 8. Project Iterations
- Projects V2 GraphQL API
- Listing cycles/sprints
- Node ID resolution
- Iteration management

## Common Pitfalls
- Rate limit exhaustion
- Label cache staleness
- Inefficient pagination
- State transition errors
- PR creation failures

## Best Practices
- Authentication security
- Rate limit monitoring
- State management
- Search optimization
- Error handling
- Performance tuning

## Examples
- Full workflow example
- Search and filter example
- Milestone tracking example
- Sprint management example

## Troubleshooting
- Common errors and solutions
- Debug logging
- API response inspection
- Network issues
```

### 6.3 Priority Features for Skill

**Must-Have (P0):**
1. ✅ Authentication patterns (PAT, scopes, validation)
2. ✅ Rate limiting strategy (check quota, handle 429, backoff)
3. ✅ Label-based state management (extended states, priority mapping)
4. ✅ Milestone management (hybrid storage, progress tracking)
5. ✅ Error handling (status codes, exceptions, retries)

**Should-Have (P1):**
6. ✅ Pull request automation (create from issue, link existing)
7. ✅ Advanced search (query construction, filters, qualifiers)
8. ✅ Pagination best practices (cursor vs offset, efficiency)
9. ✅ Caching strategies (labels, milestones, ETags)
10. ✅ Common pitfalls (rate limits, cache staleness, state transitions)

**Nice-to-Have (P2):**
11. ⚠️ Webhook integration (signatures, event processing)
12. ⚠️ GitHub Apps authentication (installation tokens, permissions)
13. ⚠️ Batch operations (parallel requests, asyncio patterns)
14. ⚠️ Projects V2 advanced (custom fields, views, automation)
15. ⚠️ Code scanning integration (security alerts, SARIF uploads)

---

## 7. Conclusion

### 7.1 Summary

The GitHub REST API v3 is mature, well-documented, and comprehensive. The current mcp-ticketer GitHub adapter is production-ready with excellent coverage of core ticket management operations. The hybrid REST/GraphQL approach is well-designed and leverages the strengths of both APIs.

**Key Strengths:**
- Comprehensive CRUD operations for issues, milestones, labels
- Label-based extended state management (solves GitHub's binary state limitation)
- Hybrid storage for milestones (GitHub API + local labels)
- Built-in rate limiting and retry logic
- Strong error handling and validation
- Good test coverage with integration tests

**Areas for Improvement:**
- ETag caching for bandwidth savings
- Cursor-based pagination efficiency
- Label cache TTL management
- Webhook integration for real-time updates
- GitHub Apps authentication for higher rate limits
- Batch operation support
- Enhanced logging and debugging

### 7.2 Skill Development Recommendations

**Recommended Approach:**
1. Focus on patterns that solve real-world problems
2. Include concrete examples with explanations
3. Document common pitfalls with solutions
4. Provide decision trees (when to use REST vs GraphQL)
5. Include performance optimization techniques
6. Add troubleshooting section with debug techniques

**Skill Should Enable:**
- Understanding GitHub API authentication and authorization
- Effective rate limit management
- Label-based state extension patterns
- Hybrid REST/GraphQL usage
- Advanced search and filtering
- Pull request automation workflows
- Error handling and retry strategies

**Target Audience:**
- Claude agents building GitHub integrations
- Developers implementing ticket management systems
- Teams automating GitHub workflows
- Projects requiring advanced GitHub API usage

---

## 8. References

**Official Documentation:**
- GitHub REST API v3: https://docs.github.com/en/rest
- GitHub GraphQL API v4: https://docs.github.com/en/graphql
- Authentication: https://docs.github.com/en/authentication
- Rate Limiting: https://docs.github.com/en/rest/rate-limit
- Search: https://docs.github.com/en/search-github

**mcp-ticketer Documentation:**
- GitHub Adapter: `/docs/adapters/github.md`
- GitHub Milestones: `/docs/adapters/github-milestones.md`
- Core Models: `/docs/models.md`

**Implementation Files:**
- GitHub Adapter: `/src/mcp_ticketer/adapters/github.py` (2,568 lines)
- HTTP Client: `/src/mcp_ticketer/core/http_client.py` (rate limiting, retries)
- Tests: `/tests/adapters/test_github*.py` (717 lines)

**Research Context:**
- Current mcp-ticketer version: v2.1.0
- GitHub API version: 2022-11-28
- Analysis scope: REST API v3 + GraphQL API v4
- Date: 2025-12-04

---

## Appendix A: Endpoint Coverage Matrix

| Endpoint Category | REST API | GraphQL | Implemented | Notes |
|-------------------|----------|---------|-------------|-------|
| **Issues** | | | | |
| Create issue | ✅ | ✅ | ✅ | REST preferred |
| Get issue | ✅ | ✅ | ✅ | GraphQL for nested data |
| Update issue | ✅ | ✅ | ✅ | REST only |
| List issues | ✅ | ✅ | ✅ | Both used |
| Search issues | ❌ | ✅ | ✅ | GraphQL only |
| Delete issue | ❌ | ❌ | ⚠️ | Close instead |
| **Comments** | | | | |
| Add comment | ✅ | ✅ | ✅ | REST only |
| List comments | ✅ | ✅ | ✅ | REST only |
| Update comment | ✅ | ❌ | ❌ | Not implemented |
| Delete comment | ✅ | ❌ | ❌ | Not implemented |
| **Labels** | | | | |
| List labels | ✅ | ❌ | ✅ | REST + cache |
| Create label | ✅ | ❌ | ✅ | REST only |
| Update label | ✅ | ❌ | ❌ | Not implemented |
| Delete label | ✅ | ❌ | ❌ | Not implemented |
| **Milestones** | | | | |
| Create milestone | ✅ | ❌ | ✅ | REST + local storage |
| Get milestone | ✅ | ❌ | ✅ | REST + local labels |
| List milestones | ✅ | ❌ | ✅ | REST only |
| Update milestone | ✅ | ❌ | ✅ | REST + local labels |
| Delete milestone | ✅ | ❌ | ✅ | REST + local cleanup |
| Get milestone issues | ✅ | ❌ | ✅ | REST only |
| **Pull Requests** | | | | |
| Create PR | ✅ | ❌ | ✅ | REST + auto-gen |
| Get PR | ✅ | ✅ | ⚠️ | Basic support |
| Update PR | ✅ | ❌ | ⚠️ | Basic support |
| List PRs | ✅ | ✅ | ❌ | Not implemented |
| Merge PR | ✅ | ❌ | ❌ | Not implemented |
| **Projects** | | | | |
| List iterations | ❌ | ✅ | ✅ | GraphQL only (V2) |
| Get project | ❌ | ✅ | ❌ | Not implemented |
| Update project | ❌ | ✅ | ❌ | Not implemented |
| **Other** | | | | |
| Get user | ✅ | ✅ | ✅ | REST only |
| List collaborators | ✅ | ✅ | ✅ | REST only |
| Get rate limit | ✅ | ✅ | ✅ | REST only |
| Create branch | ✅ | ❌ | ✅ | REST only (for PRs) |

**Legend:**
- ✅ Fully implemented
- ⚠️ Partially implemented
- ❌ Not implemented

---

## Appendix B: Test Coverage Summary

| Test Category | Test Count | Coverage | Notes |
|---------------|------------|----------|-------|
| **Integration Tests** | 1 | Basic | Full CRUD workflow |
| **Cycles/Iterations** | 5 | High | Success, errors, edge cases |
| **Issue Status** | 7 | High | All state combinations |
| **Status Listing** | 3 | High | Structure, native vs extended |
| **Label Operations** | 5 | High | Repository, milestone, filtering |
| **Milestone Updates** | 10 | High | All fields, errors, concurrency |
| **Attachments** | 5 | Medium | Files, references, guidance |
| **Markdown/Unicode** | 2 | Medium | Rich text, emoji support |
| **Workflow** | 1 | Medium | End-to-end status tracking |

**Total Test Lines:** 717
**Test Files:** 3
**Test Coverage:** ~85% (estimated)

**Coverage Gaps:**
- Search edge cases (empty results, pagination)
- Rate limit exhaustion
- Network failures
- GraphQL errors
- State transition validation
- Cache invalidation
- Concurrent label creation

---

**END OF RESEARCH DOCUMENT**
