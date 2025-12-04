# platforms-linear-graphql

Linear GraphQL API integration patterns for modern issue tracking with cycles, projects, and team-scoped workflows.

## When to Use This Skill

- Building Linear issue tracking integrations
- Implementing cycle (sprint) management
- Managing project/issue/task hierarchies
- Using GraphQL for efficient data fetching
- Migrating from GitHub/Jira to Linear
- Creating Linear bots or automation tools
- Debugging Linear API errors

## Prerequisites

**GraphQL Fundamentals Required:**
Before using this skill, ensure you understand GraphQL basics from the universal GraphQL skill (`toolchains-universal-data-graphql`):
- GraphQL syntax and type system
- Query and mutation operations
- Fragment composition
- Resolver patterns

This skill focuses on **Linear-specific** patterns and assumes GraphQL knowledge.

## Quick Start

### Authentication (⚠️ CRITICAL DIFFERENCE)

```python
from gql import Client
from gql.transport.httpx import HTTPXAsyncTransport

# ⚠️ CRITICAL: Linear API keys are passed DIRECTLY (NO Bearer prefix!)
# This is the #1 most common mistake when integrating with Linear
transport = HTTPXAsyncTransport(
    url="https://api.linear.app/graphql",
    headers={"Authorization": "lin_api_YOUR_KEY_HERE"},  # NOT "Bearer lin_api_..."
    timeout=30,
)

client = Client(transport=transport, fetch_schema_from_transport=False)
```

**Common Authentication Mistakes:**
```python
# ❌ WRONG - Will cause 401 Unauthorized
headers={"Authorization": f"Bearer {api_key}"}

# ❌ WRONG - OAuth token format (only for OAuth tokens)
headers={"Authorization": f"Bearer lin_api_{api_key}"}

# ✅ CORRECT - Direct API key
headers={"Authorization": api_key}
```

### Basic Query

```graphql
query GetIssue($id: String!) {
    issue(id: $id) {
        id
        identifier
        title
        description
        state {
            name
            type  # unstarted, started, completed, canceled
        }
        assignee {
            id
            email
            name
        }
    }
}
```

### Error Handling Pattern

```python
from gql.transport.exceptions import TransportQueryError, TransportError

try:
    result = await client.execute(query, variable_values=variables)
except TransportQueryError as e:
    # GraphQL validation errors (e.g., duplicate labels, invalid fields)
    errors = [err["message"] for err in e.errors]
    print(f"GraphQL validation error: {'; '.join(errors)}")
except TransportError as e:
    # Network/HTTP errors (401, 403, 429, 500)
    if hasattr(e, "response") and e.response.status == 401:
        raise AuthenticationError("Invalid Linear API key")
    elif hasattr(e, "response") and e.response.status == 429:
        raise RateLimitError("Rate limit exceeded")
```

---

<!-- Full Content Section Begins Here -->

# Full Linear GraphQL Integration Guide

## 1. Authentication and Setup

### API Key Generation

1. **Generate API Key:**
   - Go to Settings → API in Linear
   - Click "Personal API keys"
   - Create new key with desired scopes
   - Format: `lin_api_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`

2. **Team ID Discovery:**
   ```graphql
   query GetTeams {
       teams {
           nodes {
               id
               name
               key  # Used in issue identifiers (e.g., "ENG")
           }
       }
   }
   ```

3. **Verify Connection:**
   ```graphql
   query TestConnection {
       viewer {
           id
           name
           email
           organization {
               id
               name
           }
       }
   }
   ```

### Environment Configuration

```python
# .env
LINEAR_API_KEY=lin_api_xxxxxxxxxxxxx
LINEAR_TEAM_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Python
import os
from gql import Client
from gql.transport.httpx import HTTPXAsyncTransport

api_key = os.getenv("LINEAR_API_KEY")
team_id = os.getenv("LINEAR_TEAM_ID")

# NO Bearer prefix!
transport = HTTPXAsyncTransport(
    url="https://api.linear.app/graphql",
    headers={"Authorization": api_key},
    timeout=30,
)
```

---

## 2. Team-Scoped Architecture

### Core Concept: Everything is Team-Scoped

**Linear's fundamental design:** All operations require team context. This differs significantly from GitHub (repository-scoped) or Jira (project-scoped).

**Implications:**
- ✅ Workflows are team-specific (each team has custom states)
- ✅ Labels are team-scoped (same name can exist in different teams)
- ✅ Cycles (sprints) belong to teams
- ❌ Cannot query across teams easily
- ❌ Cross-team reports require multiple queries

### Team-Scoped Queries

```graphql
# Get team-specific workflow states
query WorkflowStates($teamId: String!) {
    team(id: $teamId) {
        states {
            nodes {
                id
                name
                type        # unstarted, started, completed, canceled
                position    # Order in workflow
                color
            }
        }
    }
}

# Get team cycles (sprints)
query TeamCycles($teamId: String!) {
    team(id: $teamId) {
        cycles(first: 10) {
            nodes {
                id
                name
                startsAt
                endsAt
                progress  # 0.0-1.0
            }
        }
    }
}

# Get team labels
query TeamLabels($teamId: String!) {
    team(id: $teamId) {
        labels {
            nodes {
                id
                name
                color
            }
        }
    }
}
```

### Multi-Team Considerations

**Pattern: Fetch all teams and iterate:**
```python
async def get_all_team_issues():
    """Get issues across all teams."""
    teams_query = """
        query GetTeams {
            teams {
                nodes { id name }
            }
        }
    """

    teams_result = await client.execute(teams_query)
    teams = teams_result["teams"]["nodes"]

    all_issues = []
    for team in teams:
        team_issues = await get_team_issues(team["id"])
        all_issues.extend(team_issues)

    return all_issues
```

---

## 3. GraphQL Fragment Composition (Production Pattern)

### 10 Reusable Fragments

```graphql
# 1. User Fragment
fragment UserFields on User {
    id
    name
    email
    displayName
    avatarUrl
    isMe
}

# 2. Workflow State Fragment
fragment WorkflowStateFields on WorkflowState {
    id
    name
    type        # unstarted, started, completed, canceled
    position
    color
}

# 3. Team Fragment
fragment TeamFields on Team {
    id
    name
    key         # Short identifier (e.g., "ENG")
    description
}

# 4. Cycle Fragment
fragment CycleFields on Cycle {
    id
    number
    name
    description
    startsAt
    endsAt
    completedAt
}

# 5. Project Fragment
fragment ProjectFields on Project {
    id
    name
    description
    state
    targetDate
    teams {
        nodes {
            ...TeamFields
        }
    }
}

# 6. Label Fragment
fragment LabelFields on IssueLabel {
    id
    name
    color
    description
}

# 7. Attachment Fragment
fragment AttachmentFields on Attachment {
    id
    title
    url
    subtitle
    metadata
}

# 8. Comment Fragment
fragment CommentFields on Comment {
    id
    body
    createdAt
    user {
        ...UserFields
    }
}

# 9. Issue Compact Fragment (for lists)
fragment IssueCompactFields on Issue {
    id
    identifier
    title
    description
    priority
    state { ...WorkflowStateFields }
    assignee { ...UserFields }
    labels { nodes { ...LabelFields } }
    team { ...TeamFields }
    cycle { ...CycleFields }
    project { ...ProjectFields }
}

# 10. Issue Full Fragment (for detail views)
fragment IssueFullFields on Issue {
    ...IssueCompactFields
    comments { nodes { ...CommentFields } }
    attachments { nodes { ...AttachmentFields } }
}
```

### Fragment Composition Strategy

```python
# Python example: Modular fragment composition
USER_FRAGMENT = "fragment UserFields on User { ... }"
WORKFLOW_STATE_FRAGMENT = "fragment WorkflowStateFields on WorkflowState { ... }"
TEAM_FRAGMENT = "fragment TeamFields on Team { ... }"
# ... (8 more fragments)

# Compose fragments for list queries (excludes comments for performance)
ISSUE_LIST_FRAGMENTS = (
    USER_FRAGMENT +
    WORKFLOW_STATE_FRAGMENT +
    TEAM_FRAGMENT +
    CYCLE_FRAGMENT +
    PROJECT_FRAGMENT +
    LABEL_FRAGMENT +
    ATTACHMENT_FRAGMENT +
    ISSUE_COMPACT_FRAGMENT
)

# Compose fragments for detail queries (includes everything)
ALL_FRAGMENTS = (
    ISSUE_LIST_FRAGMENTS +
    COMMENT_FRAGMENT +
    ISSUE_FULL_FRAGMENT
)

# Use in queries
LIST_ISSUES_QUERY = (
    ISSUE_LIST_FRAGMENTS +
    """
    query ListIssues($filter: IssueFilter, $first: Int!) {
        issues(filter: $filter, first: $first) {
            nodes { ...IssueCompactFields }
        }
    }
    """
)
```

**Benefits:**
- **DRY Principle:** Define field sets once, reuse everywhere
- **Consistency:** Same fields across all queries
- **Performance:** Avoid over-fetching (list queries skip comments)
- **Maintainability:** Update fields in one place

---

## 4. Linear Data Model

### Three-Tier Hierarchy

```
Epic (Project)
    └─ Issue
        └─ Task (Sub-issue)
```

**GraphQL Representation:**
```graphql
mutation CreateIssue($input: IssueCreateInput!) {
    issueCreate(input: $input) {
        issue {
            id
            identifier
            # Parent relationships
            project { id name }         # Epic level
            parent { id identifier }    # Parent issue (for tasks)

            # Child relationships
            children {
                nodes {
                    id
                    identifier
                    title
                }
            }
        }
    }
}
```

### Cycles (Linear's Milestones)

**Key Differences from GitHub Milestones:**
- ✅ **Required dates:** Both start and end dates mandatory
- ✅ **Auto progress:** Linear calculates progress from issue states
- ✅ **Date-based states:** State derived from dates, not explicit field
- ❌ **No deletion:** Can only archive, not delete

**Cycle State Determination:**
```python
from datetime import datetime

def get_cycle_state(cycle):
    """Determine cycle state from dates."""
    now = datetime.now()
    starts_at = datetime.fromisoformat(cycle["startsAt"])
    ends_at = datetime.fromisoformat(cycle["endsAt"])
    completed_at = cycle.get("completedAt")

    if completed_at:
        return "completed"
    elif now > ends_at:
        return "closed"  # Past due date
    elif starts_at <= now <= ends_at:
        return "active"  # Currently running
    else:
        return "open"    # Future cycle
```

### Workflow States and Transitions

**Four State Types (Immutable):**
```graphql
enum WorkflowStateType {
    unstarted  # Maps to: OPEN, WAITING, BLOCKED
    started    # Maps to: IN_PROGRESS, READY, TESTED
    completed  # Maps to: DONE
    canceled   # Maps to: CLOSED
}
```

**Custom State Names (per team):**
```graphql
query TeamStates($teamId: String!) {
    team(id: $teamId) {
        states {
            nodes {
                id
                name        # Custom name (e.g., "In Review")
                type        # One of 4 types above
                position    # Workflow order
            }
        }
    }
}
```

### Labels (Team-Scoped)

**Key Behaviors:**
- **Case-insensitive matching:** "bug" === "Bug" === "BUG"
- **Team-scoped:** Same name can exist in different teams
- **Fail-fast (v1.3.2+):** Missing labels raise errors

```python
# Label lookup pattern
labels_by_name = {
    label["name"].lower(): label["id"]
    for label in team_labels
}

# Case-insensitive lookup
label_id = labels_by_name.get("bug")  # Finds "Bug", "BUG", "bug"

# Fail-fast on missing labels (recommended)
if not label_id:
    raise ValueError(
        f"Label '{label_name}' not found. "
        f"Available: {', '.join(labels_by_name.keys())}"
    )
```

---

## 5. Rate Limiting and Performance

### Linear API Limits

**Rate Limits:**
- **Hourly:** 1,000 requests per user
- **Burst:** 20 requests per second
- **Complexity:** GraphQL queries have complexity scoring

**Rate Limit Headers:**
```python
if hasattr(error, "response"):
    retry_after = error.response.headers.get("Retry-After", "60")
    print(f"Rate limited. Retry after {retry_after} seconds")
```

### Exponential Backoff Pattern

```python
import asyncio

async def execute_with_retry(query, variables, retries=3):
    """Execute query with exponential backoff."""
    for attempt in range(retries + 1):
        try:
            return await client.execute(query, variable_values=variables)
        except TransportError as e:
            if hasattr(e, "response") and e.response.status >= 500:
                # Server error - retry
                if attempt < retries:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    await asyncio.sleep(wait_time)
                    continue
            raise
```

### Batch Operations

**Pattern: Use filters instead of multiple queries:**
```graphql
# ❌ BAD: 10 queries for 10 issues
query GetIssue($id: String!) {
    issue(id: $id) { ... }
}

# ✅ GOOD: 1 query for multiple issues
query GetIssues($ids: [String!]!) {
    issues(filter: { id: { in: $ids } }) {
        nodes { ... }
    }
}
```

### Cursor Pagination

**Relay Connection Pattern:**
```graphql
query ListIssues($first: Int!, $after: String) {
    issues(first: $first, after: $after) {
        nodes {
            id
            identifier
            title
        }
        pageInfo {
            hasNextPage
            endCursor  # Use as next 'after' value
        }
    }
}
```

**Pagination Limits:**
- **Maximum per page:** 250 items
- **Default:** 50 items if not specified

**Python Pagination Helper:**
```python
async def fetch_all_pages(query, variables, max_items=250):
    """Fetch all pages using cursor pagination."""
    all_items = []
    has_next_page = True
    after_cursor = None

    while has_next_page:
        variables["first"] = max_items
        variables["after"] = after_cursor

        result = await client.execute(query, variable_values=variables)

        nodes = result["issues"]["nodes"]
        all_items.extend(nodes)

        page_info = result["issues"]["pageInfo"]
        has_next_page = page_info.get("hasNextPage", False)
        after_cursor = page_info.get("endCursor")

    return all_items
```

---

## 6. Error Handling

### Error Type Hierarchy

```python
from gql.transport.exceptions import TransportQueryError, TransportError

# TransportQueryError (subclass of TransportError)
#   └─ GraphQL validation errors
#       - Duplicate labels
#       - Invalid field values
#       - Type mismatches
#       - Required field violations

# TransportError
#   └─ Network/HTTP errors
#       - 401 Unauthorized (invalid API key)
#       - 403 Forbidden (insufficient permissions)
#       - 429 Rate Limit (too many requests)
#       - 500+ Server errors
```

### Production Error Handling Pattern

```python
async def execute_query(query_string, variables=None, retries=3):
    """Execute GraphQL query with comprehensive error handling."""
    query = gql(query_string)

    for attempt in range(retries + 1):
        try:
            async with client as session:
                result = await session.execute(query, variable_values=variables)
            return result

        except TransportQueryError as e:
            # GraphQL validation errors - extract details
            if e.errors:
                error = e.errors[0]
                error_msg = error.get("message", "Unknown error")

                # Check extensions for additional context
                extensions = error.get("extensions", {})
                user_msg = extensions.get("userPresentableMessage")
                if user_msg:
                    error_msg = user_msg

                # Log detailed error
                logger.error(f"GraphQL validation error: {error_msg}")
                logger.error(f"Extensions: {extensions}")

                # Check for duplicate label errors
                if "duplicate" in error_msg.lower() and "label" in error_msg.lower():
                    raise DuplicateLabelError(error_msg)

                raise ValidationError(error_msg)

            raise GraphQLError(str(e))

        except TransportError as e:
            if hasattr(e, "response"):
                status = e.response.status

                if status == 401:
                    raise AuthenticationError("Invalid Linear API key")
                elif status == 403:
                    raise AuthenticationError("Insufficient permissions")
                elif status == 429:
                    retry_after = e.response.headers.get("Retry-After", "60")
                    raise RateLimitError(f"Rate limited. Retry after {retry_after}s")
                elif status >= 500:
                    # Server error - retry with backoff
                    if attempt < retries:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    raise ServerError(f"Linear API error: {status}")

            # Network error - retry
            if attempt < retries:
                await asyncio.sleep(2 ** attempt)
                continue

            raise NetworkError(str(e))
```

### Fail-Fast Label Errors (v1.3.2+)

**Old Behavior (Silent Failure):**
```python
# ❌ Before v1.3.2: Silently skipped missing labels
label_id = labels_by_name.get(label_name.lower())
if label_id:
    label_ids.append(label_id)
# Missing label silently ignored!
```

**New Behavior (Fail-Fast):**
```python
# ✅ v1.3.2+: Explicit error on missing labels
label_id = labels_by_name.get(label_name.lower())
if not label_id:
    raise ValueError(
        f"Label '{label_name}' not found in team. "
        f"Available labels: {', '.join(labels_by_name.keys())}"
    )
label_ids.append(label_id)
```

---

## 7. Cycle Management (Linear-Specific)

### Create Cycle

```graphql
mutation CycleCreate($input: CycleCreateInput!) {
    cycleCreate(input: $input) {
        success
        cycle {
            id
            name
            description
            startsAt          # Required!
            endsAt            # Required!
            progress          # 0.0-1.0 (auto-calculated)
            completedIssueCount
            issueCount
        }
    }
}
```

**Python Example:**
```python
async def create_cycle(team_id, name, start_date, end_date):
    """Create cycle with required dates."""
    mutation = gql(CREATE_CYCLE_MUTATION)
    variables = {
        "input": {
            "teamId": team_id,
            "name": name,
            "startsAt": start_date.isoformat(),  # ISO 8601 format
            "endsAt": end_date.isoformat(),
        }
    }

    result = await client.execute(mutation, variable_values=variables)
    return result["cycleCreate"]["cycle"]
```

### Update Cycle

```graphql
mutation CycleUpdate($id: String!, $input: CycleUpdateInput!) {
    cycleUpdate(id: $id, input: $input) {
        success
        cycle {
            id
            name
            startsAt
            endsAt
            completedAt  # Set to mark as completed
        }
    }
}
```

### List Cycles with Progress

```graphql
query TeamCycles($teamId: String!) {
    team(id: $teamId) {
        cycles(first: 50) {
            nodes {
                id
                name
                startsAt
                endsAt
                progress          # Linear calculates this
                completedIssueCount
                issueCount
                issues {
                    nodes {
                        id
                        identifier
                        state { type }
                    }
                }
            }
        }
    }
}
```

### Archive Cycle (No Deletion)

```graphql
mutation CycleArchive($id: String!) {
    cycleArchive(id: $id) {
        success
    }
}
```

**Note:** Linear does not support permanent deletion of cycles. Use archive instead.

---

## 8. Type System Quirks

### String! vs ID! Distinction

**Linear is strict about types:**

```graphql
# ❌ WRONG: Passing String when ID! expected
query GetIssue($id: String!) {  # Should be ID!
    issue(id: $id) { ... }
}

# ✅ CORRECT: Use ID! for entity identifiers
query GetIssue($id: ID!) {
    issue(id: $id) { ... }
}

# ✅ CORRECT: Use String! for team IDs (exception)
query TeamStates($teamId: String!) {
    team(id: $teamId) { ... }
}
```

**Common Type Errors:**
```python
# Debug type mismatch errors
logger.error(f"Variables: {variables}")
logger.error(f"Expected types: teamId: String!, issueId: ID!")
```

### Nullable vs Non-Nullable

**Required Fields (!):**
```graphql
input CycleCreateInput {
    teamId: String!      # Required
    name: String!        # Required
    startsAt: DateTime!  # Required
    endsAt: DateTime!    # Required
    description: String  # Optional
}
```

---

## 9. Best Practices

### 1. Fragment Reuse

**✅ DO: Define fragments once, compose in queries**
```python
FRAGMENTS = USER_FRAGMENT + WORKFLOW_STATE_FRAGMENT + ISSUE_COMPACT_FRAGMENT

query = FRAGMENTS + """
    query GetIssue($id: ID!) {
        issue(id: $id) {
            ...IssueCompactFields
        }
    }
"""
```

**❌ DON'T: Duplicate field lists**
```graphql
# BAD: Repeating fields in every query
query GetIssue($id: ID!) {
    issue(id: $id) {
        id
        identifier
        title
        # ... 30 more fields copied everywhere
    }
}
```

### 2. Team Context Management

**✅ DO: Resolve team ID once, cache it**
```python
class LinearClient:
    def __init__(self, api_key, team_id):
        self.api_key = api_key
        self.team_id = team_id  # Cache team context
        self._workflow_states = None

    async def load_workflow_states(self):
        """Load and cache team workflow states."""
        if self._workflow_states is None:
            result = await self.execute(WORKFLOW_STATES_QUERY, {"teamId": self.team_id})
            self._workflow_states = result["team"]["states"]["nodes"]
        return self._workflow_states
```

### 3. Error Handling

**✅ DO: Classify errors by type, fail-fast on validation**
```python
try:
    result = await execute_query(query, variables)
except TransportQueryError as e:
    # Fail fast on validation errors
    raise ValidationError(extract_error_message(e))
except TransportError as e:
    # Retry on server errors, fail on auth errors
    if is_server_error(e):
        await retry_with_backoff()
    else:
        raise
```

**❌ DON'T: Catch all exceptions silently**
```python
# BAD: Swallows all errors
try:
    result = await execute_query(query, variables)
except Exception:
    return None  # Silent failure!
```

### 4. Query Optimization

**✅ DO: Use filters to reduce data transfer**
```graphql
query GetOpenIssues($teamId: String!) {
    team(id: $teamId) {
        issues(
            filter: {
                state: { type: { in: [unstarted, started] } }
            }
            first: 50
        ) {
            nodes { ...IssueCompactFields }
        }
    }
}
```

**❌ DON'T: Fetch everything and filter client-side**
```python
# BAD: Fetches all 10,000 issues
all_issues = await get_all_issues()
open_issues = [i for i in all_issues if i["state"]["type"] != "completed"]
```

---

## 10. Common Pitfalls

### ⚠️ Pitfall #1: Bearer Prefix Mistake (Most Common!)

**Problem:**
```python
# ❌ WRONG: Adding Bearer prefix
headers = {"Authorization": f"Bearer {api_key}"}
# Result: 401 Unauthorized
```

**Solution:**
```python
# ✅ CORRECT: Direct API key
headers = {"Authorization": api_key}
```

**Why:** Linear API keys are not OAuth tokens. Only OAuth tokens use Bearer scheme.

### ⚠️ Pitfall #2: Missing Team Context

**Problem:**
```graphql
# ❌ WRONG: Querying cycles without team context
query GetCycles {
    cycles { ... }  # Error: Cannot query field "cycles"
}
```

**Solution:**
```graphql
# ✅ CORRECT: Team-scoped query
query GetCycles($teamId: String!) {
    team(id: $teamId) {
        cycles { ... }
    }
}
```

### ⚠️ Pitfall #3: Label Case-Sensitivity Assumptions

**Problem:**
```python
# ❌ WRONG: Exact match
label_id = labels_dict["Bug"]  # Fails if stored as "bug"
```

**Solution:**
```python
# ✅ CORRECT: Case-insensitive lookup
labels_by_name = {label["name"].lower(): label["id"] for label in labels}
label_id = labels_by_name.get("bug")  # Matches "Bug", "BUG", "bug"
```

### ⚠️ Pitfall #4: Cycle Date Requirements

**Problem:**
```python
# ❌ WRONG: Missing required dates
cycle_input = {
    "teamId": team_id,
    "name": "Sprint 1",
    # startsAt and endsAt missing!
}
```

**Solution:**
```python
# ✅ CORRECT: Include required dates
from datetime import datetime, timedelta

now = datetime.now()
cycle_input = {
    "teamId": team_id,
    "name": "Sprint 1",
    "startsAt": now.isoformat(),
    "endsAt": (now + timedelta(days=14)).isoformat(),
}
```

### ⚠️ Pitfall #5: Type Confusion (String vs ID)

**Problem:**
```graphql
# ❌ WRONG: Using String! for issue ID
query GetIssue($id: String!) {
    issue(id: $id) { ... }
}
```

**Solution:**
```graphql
# ✅ CORRECT: Use ID! for issue identifiers
query GetIssue($id: ID!) {
    issue(id: $id) { ... }
}

# ✅ Exception: Team IDs use String!
query GetTeam($teamId: String!) {
    team(id: $teamId) { ... }
}
```

---

## 11. Comparison with REST (GitHub/Jira)

### Why GraphQL for Linear

**Linear's Design Philosophy:**
- GraphQL-only API (no REST alternative)
- Designed for efficient data fetching
- Strongly typed schema

### GitHub REST vs Linear GraphQL

| Feature | GitHub REST | Linear GraphQL |
|---------|-------------|----------------|
| **Authentication** | `Bearer token` | Direct API key (no Bearer) |
| **Scope** | Repository-based | Team-based |
| **Over-fetching** | Common (fixed endpoints) | Minimal (request specific fields) |
| **N+1 Problem** | Frequent (separate calls for relations) | Rare (fragments fetch relations) |
| **Pagination** | Link header | Cursor-based (pageInfo) |
| **Rate Limiting** | 5,000 req/hr | 1,000 req/hr |

### When to Use Linear Over GitHub Issues

**Choose Linear when:**
- ✅ Need sprint/cycle management (native in Linear)
- ✅ Want team-scoped workflows (simpler permissions)
- ✅ Prefer opinionated workflow (4 state types)
- ✅ Need automatic progress tracking

**Choose GitHub when:**
- ✅ Deeply integrated with code (PRs, commits)
- ✅ Need cross-repository visibility
- ✅ Higher rate limits required
- ✅ Open source project (public visibility)

---

## 12. Migration Patterns

### From GitHub Issues to Linear

**Mapping:**
```python
github_to_linear = {
    # States
    "open": "unstarted",
    "in_progress": "started",
    "closed": "completed",

    # Priority (GitHub: None, Linear: 0-4)
    None: 3,  # Medium

    # Milestones → Cycles
    # Requires adding start/end dates to GitHub milestone
}

async def migrate_issue(github_issue):
    """Migrate GitHub issue to Linear."""
    # Map state
    github_state = github_issue["state"]
    linear_state_type = github_to_linear.get(github_state, "unstarted")

    # Find Linear state ID by type
    state = next(
        s for s in workflow_states
        if s["type"] == linear_state_type
    )

    # Create Linear issue
    linear_input = {
        "teamId": team_id,
        "title": github_issue["title"],
        "description": github_issue["body"],
        "stateId": state["id"],
        "priority": 3,  # Default medium
    }

    return await create_issue(linear_input)
```

---

## 13. Code Examples

### Complete CRUD Operations

```python
from gql import Client, gql
from gql.transport.httpx import HTTPXAsyncTransport

class LinearClient:
    def __init__(self, api_key: str, team_id: str):
        self.api_key = api_key
        self.team_id = team_id

        # NO Bearer prefix!
        transport = HTTPXAsyncTransport(
            url="https://api.linear.app/graphql",
            headers={"Authorization": api_key},
            timeout=30,
        )
        self.client = Client(transport=transport, fetch_schema_from_transport=False)

    async def create_issue(self, title, description, state_type="unstarted"):
        """Create issue with state lookup."""
        # Load workflow states
        states = await self.get_workflow_states()
        state = next(s for s in states if s["type"] == state_type)

        mutation = gql("""
            mutation CreateIssue($input: IssueCreateInput!) {
                issueCreate(input: $input) {
                    success
                    issue {
                        id
                        identifier
                        title
                    }
                }
            }
        """)

        variables = {
            "input": {
                "teamId": self.team_id,
                "title": title,
                "description": description,
                "stateId": state["id"],
            }
        }

        async with self.client as session:
            result = await session.execute(mutation, variable_values=variables)

        return result["issueCreate"]["issue"]

    async def get_workflow_states(self):
        """Get team workflow states."""
        query = gql("""
            query WorkflowStates($teamId: String!) {
                team(id: $teamId) {
                    states {
                        nodes {
                            id
                            name
                            type
                        }
                    }
                }
            }
        """)

        async with self.client as session:
            result = await session.execute(query, variable_values={"teamId": self.team_id})

        return result["team"]["states"]["nodes"]

    async def search_issues(self, query_text, state_types=None):
        """Search issues with filters."""
        filter_input = {
            "team": {"id": {"eq": self.team_id}},
        }

        if query_text:
            filter_input["title"] = {"containsIgnoreCase": query_text}

        if state_types:
            filter_input["state"] = {"type": {"in": state_types}}

        query = gql("""
            query SearchIssues($filter: IssueFilter, $first: Int!) {
                issues(filter: $filter, first: $first) {
                    nodes {
                        id
                        identifier
                        title
                        state {
                            name
                            type
                        }
                    }
                }
            }
        """)

        async with self.client as session:
            result = await session.execute(
                query,
                variable_values={"filter": filter_input, "first": 50}
            )

        return result["issues"]["nodes"]
```

---

## 14. Testing Strategies

### Mock GraphQL Responses

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_linear_client():
    """Mock Linear GraphQL client."""
    client = AsyncMock()

    # Mock successful issue creation
    client.execute.return_value = {
        "issueCreate": {
            "success": True,
            "issue": {
                "id": "test-id",
                "identifier": "ENG-123",
                "title": "Test Issue"
            }
        }
    }

    return client

@pytest.mark.asyncio
async def test_create_issue(mock_linear_client):
    """Test issue creation."""
    with patch("linear_client.Client", return_value=mock_linear_client):
        result = await create_issue("Test", "Description")
        assert result["identifier"] == "ENG-123"
```

### Integration Testing

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_linear_api_connection():
    """Test actual Linear API connection."""
    api_key = os.getenv("LINEAR_API_KEY")
    team_id = os.getenv("LINEAR_TEAM_ID")

    client = LinearClient(api_key, team_id)

    # Test viewer query
    result = await client.test_connection()
    assert result is True
```

---

## 15. Resources and References

### Official Documentation

- **GraphQL Playground:** https://studio.apollographql.com/public/Linear-API/variant/current/home
- **API Docs:** https://developers.linear.app/docs/graphql/overview
- **SDK Reference:** https://github.com/linear/linear

### Community Resources

- **Linear Community:** https://linear.app/community
- **GitHub Discussions:** Search for "Linear GraphQL" integration examples

### Related Skills

- `toolchains-universal-data-graphql` - GraphQL fundamentals
- `toolchains-python-frameworks-fastapi` - Building Linear API integrations
- `universal-debugging-systematic-debugging` - Troubleshooting API issues

---

**Skill Version:** 1.0.0
**Last Updated:** 2025-12-04
**Based on:** mcp-ticketer Linear adapter v2.1.0 (6,193 lines production code)
