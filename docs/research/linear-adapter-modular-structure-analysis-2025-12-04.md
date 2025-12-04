# Linear Adapter Modular Structure Analysis

**Research Date:** 2025-12-04
**Objective:** Analyze Linear adapter's modular architecture to create refactoring blueprint for GitHub and Jira adapters
**Status:** ✅ Complete

## Executive Summary

The Linear adapter demonstrates a well-organized modular structure across 6 files totaling ~6,212 lines. This structure separates concerns into distinct modules:

- **adapter.py** (4,095 lines): Core business logic and orchestration
- **queries.py** (666 lines): GraphQL queries and fragments
- **mappers.py** (527 lines): Data transformation logic
- **client.py** (500 lines): API client and error handling
- **types.py** (400 lines): Type mappings and helper functions
- **__init__.py** (24 lines): Public API exports

### Key Findings

1. **Modularity Benefits**: The structure enables:
   - Easy testing of individual components
   - Clear separation of API communication from business logic
   - Reusable query fragments and type conversions
   - Centralized error handling

2. **Current State**:
   - GitHub adapter: **2,585 lines** in single file (49 methods)
   - Jira adapter: **1,899 lines** in single file (53 methods)
   - Both adapters mix all concerns in one monolithic file

3. **Refactoring Impact**:
   - Estimated 40-50% line reduction in main adapter files
   - Improved maintainability and testability
   - Consistent architecture across all adapters

---

## Linear Adapter Module Breakdown

### 1. **types.py** (400 lines)
**Purpose:** Platform-specific type definitions, enums, and conversion utilities

**Responsibilities:**
- State and priority mappings (bidirectional)
- Semantic state name matching for flexible workflows
- GraphQL filter builders (`build_issue_filter`, `build_project_filter`)
- Metadata extraction from Linear responses
- UUID validation and type conversion helpers

**Key Components:**
```python
class LinearPriorityMapping:
    TO_LINEAR: dict[Priority, int]      # Universal → Linear
    FROM_LINEAR: dict[int, Priority]    # Linear → Universal

class LinearStateMapping:
    TO_LINEAR: dict[TicketState, str]
    FROM_LINEAR: dict[str, TicketState]
    SEMANTIC_NAMES: dict[TicketState, list[str]]  # Synonym matching

# Helper functions
get_linear_priority(priority: Priority) -> int
get_universal_state(linear_state_type: str, state_name: str | None) -> TicketState
build_issue_filter(...) -> dict[str, Any]
extract_linear_metadata(issue_data: dict) -> dict
```

**Design Patterns:**
- **Bidirectional Mapping**: Explicit TO/FROM dictionaries for clarity
- **Semantic Matching**: Flexible state name synonyms (e.g., "todo", "to do", "backlog" → OPEN)
- **Filter Builders**: Composable GraphQL filter construction
- **Metadata Extraction**: Platform-specific fields isolated from universal model

**GitHub/Jira Equivalent:**
- `GitHubStateMapping` class → Move to `github/types.py`
- `GitHubGraphQLQueries` constants → Move to `github/queries.py`
- Priority label mappings → Move to `github/types.py`
- Jira status/priority mappings → Move to `jira/types.py`
- ADF conversion helpers → Move to `jira/types.py`

---

### 2. **client.py** (500 lines)
**Purpose:** API client abstraction with error handling and retry logic

**Responsibilities:**
- GraphQL client lifecycle management
- HTTP error handling and retries
- Authentication and rate limiting
- Connection testing
- User/team lookup utilities

**Key Components:**
```python
class LinearGraphQLClient:
    def __init__(self, api_key: str, timeout: int = 30)
    def create_client() -> Client
    async def execute_query(query_string, variables, retries=3) -> dict
    async def execute_mutation(mutation_string, variables, retries=3) -> dict
    async def test_connection() -> bool
    async def get_team_info(team_id: str) -> dict | None
    async def get_user_by_email(email: str) -> dict | None
    async def get_users_by_name(name: str) -> list[dict]
```

**Error Handling:**
- `TransportQueryError` → `AdapterError` (validation errors)
- `TransportError` → Retry with exponential backoff
- HTTP 401/403 → `AuthenticationError`
- HTTP 429 → `RateLimitError`
- HTTP 5xx → Retry with backoff

**Design Patterns:**
- **Separation of Concerns**: No business logic, pure API communication
- **Error Translation**: Platform exceptions → Universal exceptions
- **Retry Logic**: Exponential backoff with configurable retries
- **Async Context Manager**: Automatic cleanup of resources

**GitHub/Jira Equivalent:**
- GitHub REST/GraphQL client → `github/client.py`
  - `_make_request()` → `async def execute_request()`
  - `_graphql_request()` → `async def execute_graphql()`
  - Error handling → Centralize in client
- Jira REST client → `jira/client.py`
  - `_make_request()` → `async def execute_request()`
  - Error handling and retries → Extract from adapter

---

### 3. **queries.py** (666 lines)
**Purpose:** GraphQL query strings, mutations, and reusable fragments

**Responsibilities:**
- Fragment definitions for reusable field sets
- Query definitions for read operations
- Mutation definitions for write operations
- Fragment composition for different use cases

**Key Components:**
```python
# Fragments (reusable field sets)
USER_FRAGMENT = "fragment UserFields on User { ... }"
WORKFLOW_STATE_FRAGMENT = "fragment WorkflowStateFields on WorkflowState { ... }"
ISSUE_COMPACT_FRAGMENT = "fragment IssueCompactFields on Issue { ... }"
ISSUE_FULL_FRAGMENT = "fragment IssueFullFields on Issue { ... }"

# Fragment combinations
ALL_FRAGMENTS = USER_FRAGMENT + WORKFLOW_STATE_FRAGMENT + ...
ISSUE_LIST_FRAGMENTS = USER_FRAGMENT + WORKFLOW_STATE_FRAGMENT + ...

# Queries
LIST_ISSUES_QUERY = ISSUE_LIST_FRAGMENTS + "query ListIssues(...) { ... }"
SEARCH_ISSUES_QUERY = ISSUE_LIST_FRAGMENTS + "query SearchIssues(...) { ... }"

# Mutations
CREATE_ISSUE_MUTATION = ALL_FRAGMENTS + "mutation CreateIssue(...) { ... }"
UPDATE_ISSUE_MUTATION = ALL_FRAGMENTS + "mutation UpdateIssue(...) { ... }"
```

**Design Patterns:**
- **Fragment Composition**: Reusable field sets reduce duplication
- **Token Optimization**: Compact vs. Full fragments for different use cases
- **Type Safety**: GraphQL type system enforced at query level
- **Operation Naming**: Clear, descriptive query/mutation names

**Token Efficiency Example:**
```python
# Compact format (120 tokens/item): id, title, state, priority, assignee
ISSUE_COMPACT_FRAGMENT = "fragment IssueCompactFields on Issue { ... }"

# Full format (600 tokens/item): + description, comments, relations, attachments
ISSUE_FULL_FRAGMENT = "fragment IssueFullFields on Issue { ... IssueCompactFields ... }"
```

**GitHub/Jira Equivalent:**
- GitHub GraphQL queries → Extract to `github/queries.py`
  - `ISSUE_FRAGMENT` → Already defined in code
  - Search queries → Extract and compose with fragments
- Jira doesn't use GraphQL, but similar pattern:
  - JQL query builders → `jira/queries.py`
  - Field selection strings → Reusable constants
  - Expand parameters → Composable field sets

---

### 4. **mappers.py** (527 lines)
**Purpose:** Bidirectional data transformation between Linear and universal models

**Responsibilities:**
- Linear → Universal model conversion
- Universal → Linear input construction
- Compact format serialization (token optimization)
- Child/parent relationship extraction

**Key Components:**
```python
# Linear → Universal
def map_linear_issue_to_task(issue_data: dict) -> Task
def map_linear_project_to_epic(project_data: dict) -> Epic
def map_linear_comment_to_comment(comment_data: dict, ticket_id: str) -> Comment
def map_linear_attachment_to_attachment(attachment_data: dict, ticket_id: str) -> Attachment

# Universal → Linear
def build_linear_issue_input(task: Task, team_id: str) -> dict
def build_linear_issue_update_input(updates: dict) -> dict

# Helpers
def extract_child_issue_ids(issue_data: dict) -> list[str]
def task_to_compact_format(task: Task) -> dict
def epic_to_compact_format(epic: Epic) -> dict
```

**Transformation Logic:**
```python
def map_linear_issue_to_task(issue_data: dict) -> Task:
    # 1. Extract basic fields
    task_id = issue_data["identifier"]
    title = issue_data["title"]

    # 2. Convert priorities (Linear int → Universal enum)
    linear_priority = issue_data.get("priority", 3)
    priority = get_universal_priority(linear_priority)

    # 3. Convert states with synonym matching
    state_type = issue_data["state"]["type"]
    state_name = issue_data["state"]["name"]
    state = get_universal_state(state_type, state_name)

    # 4. Extract relationships
    parent_epic = issue_data.get("project", {}).get("id")
    parent_issue = issue_data.get("parent", {}).get("identifier")
    children = extract_child_issue_ids(issue_data)

    # 5. Build universal model
    return Task(id=task_id, title=title, ...)
```

**Design Patterns:**
- **Pure Functions**: No side effects, testable transformations
- **Null Safety**: Defensive extraction with `.get()` and fallbacks
- **Type Conversion**: Centralized via `types.py` helpers
- **Metadata Preservation**: Platform-specific fields stored in `metadata`

**Token Optimization:**
```python
def task_to_compact_format(task: Task) -> dict:
    """Reduce from ~600 tokens to ~120 tokens per task.

    Compact: id, title, state, priority, assignee (essentials only)
    Full: + description, tags, children, dates, metadata
    """
    return {
        "id": task.id,
        "title": task.title,
        "state": task.state.value,
        "priority": task.priority.value,
        "assignee": task.assignee,
    }
```

**GitHub/Jira Equivalent:**
- GitHub: `_task_from_github_issue()` → `github/mappers.py`
  - Extract inline transformation logic
  - Add compact format functions
  - Separate read vs. write transformations
- Jira: `_issue_to_ticket()` → `jira/mappers.py`
  - `_convert_from_adf()` → Keep in `jira/types.py` (format-specific)
  - Extract state/priority mapping logic

---

### 5. **adapter.py** (4,095 lines)
**Purpose:** Core business logic and operation orchestration

**Responsibilities:**
- Adapter initialization and configuration
- CRUD operations (create, read, update, delete)
- Business logic and validation
- State transition workflows
- Label management and caching
- Comment and attachment handling
- Epic/Issue/Task hierarchy
- Project updates and milestones

**Architecture:**
```python
class LinearAdapter(BaseAdapter[Task]):
    def __init__(self, config: dict[str, Any]):
        self.client = LinearGraphQLClient(api_key, timeout)
        self.label_cache = MemoryCache(ttl=300)  # 5min cache
        self.workflow_states_cache = {}

    # === Initialization ===
    async def initialize() -> None
    async def _ensure_team_id() -> str
    async def _load_workflow_states(team_id: str) -> None
    async def _load_team_labels(team_id: str) -> None

    # === CRUD Operations ===
    async def create(ticket: Epic | Task) -> Epic | Task
    async def read(ticket_id: str) -> Task | Epic | None
    async def update(ticket_id: str, updates: dict) -> Task | None
    async def delete(ticket_id: str) -> bool

    # === Business Logic ===
    async def transition_state(ticket_id, to_state, comment) -> Task
    async def validate_transition(ticket_id, from_state, to_state) -> bool
    async def _resolve_label_ids(label_names: list[str]) -> list[str]
    async def _ensure_labels_exist(label_names: list[str]) -> list[str]

    # === Helper Methods ===
    async def _get_user_id(user_identifier: str) -> str | None
    async def _resolve_project_id(project_identifier: str) -> str | None
    async def _validate_project_team_association(...) -> bool
```

**Delegation Pattern:**
```python
async def create(self, ticket: Epic | Task) -> Epic | Task:
    # Orchestrate operation
    if isinstance(ticket, Task):
        return await self._create_task(ticket)
    elif isinstance(ticket, Epic):
        return await self._create_epic(ticket)

async def _create_task(self, task: Task) -> Task:
    # 1. Validate and resolve references
    label_ids = await self._resolve_label_ids(task.tags)
    assignee_id = await self._get_user_id(task.assignee)

    # 2. Build input using mapper
    issue_input = build_linear_issue_input(task, self.team_id)
    issue_input["labelIds"] = label_ids

    # 3. Execute via client
    result = await self.client.execute_mutation(
        CREATE_ISSUE_MUTATION,
        {"input": issue_input}
    )

    # 4. Transform response using mapper
    issue_data = result["issueCreate"]["issue"]
    return map_linear_issue_to_task(issue_data)
```

**Design Patterns:**
- **Orchestration Layer**: Coordinates client, mappers, types modules
- **Cache Management**: Label and workflow state caching
- **Lazy Loading**: Team/workflow states loaded on first use
- **Validation Logic**: Business rules enforced before API calls
- **Error Propagation**: Let client errors bubble up (already translated)

**GitHub/Jira Equivalent:**
- Main adapter file should shrink from 2,585/1,899 lines to ~1,500-1,800 lines
- Extract helpers to appropriate modules:
  - API calls → `client.py`
  - Transformations → `mappers.py`
  - Type conversions → `types.py`
  - Queries/mutations → `queries.py`

---

### 6. **__init__.py** (24 lines)
**Purpose:** Module public API definition and documentation

**Content:**
```python
"""Linear adapter for MCP Ticketer.

This module provides integration with Linear's GraphQL API for universal ticket management.
The adapter is split into multiple modules for better organization:

- adapter.py: Main LinearAdapter class with core functionality
- queries.py: GraphQL queries and fragments
- types.py: Linear-specific types and mappings
- client.py: GraphQL client management
- mappers.py: Data transformation between Linear and universal models

Usage:
    from mcp_ticketer.adapters.linear import LinearAdapter

    config = {"api_key": "...", "team_id": "..."}
    adapter = LinearAdapter(config)
"""

from .adapter import LinearAdapter

__all__ = ["LinearAdapter"]
```

**Design Patterns:**
- **Information Hiding**: Only expose main adapter class
- **Documentation**: Module-level docstring explains structure
- **Clean Imports**: Users don't need to know about internal modules

---

## Comparison: Current Monolithic vs. Modular Structure

### GitHub Adapter (2,585 lines, 49 methods)

**Current Structure:**
```
github.py (2,585 lines)
├── GitHubStateMapping (class)
├── GitHubGraphQLQueries (class)
├── GitHubAdapter (class)
│   ├── Client methods (_make_request, _graphql_request)
│   ├── Transformation methods (_task_from_github_issue)
│   ├── Type conversions (inline)
│   ├── CRUD operations
│   ├── Business logic
│   └── All queries/mutations (embedded)
```

**Proposed Modular Structure:**
```
github/
├── __init__.py (24 lines) - Public API
├── adapter.py (~1,600 lines) - Business logic only
├── client.py (~400 lines) - REST + GraphQL client
├── queries.py (~350 lines) - GraphQL queries + fragments
├── types.py (~300 lines) - State/priority mappings, filters
└── mappers.py (~400 lines) - Data transformations
```

**What Moves Where:**

| Current Location | New Location | Component |
|-----------------|--------------|-----------|
| `GitHubStateMapping` class | `github/types.py` | State mappings |
| `GitHubGraphQLQueries` class | `github/queries.py` | GraphQL fragments |
| `_make_request()` | `github/client.py` | REST client |
| `_graphql_request()` | `github/client.py` | GraphQL client |
| `_task_from_github_issue()` | `github/mappers.py` | Issue → Task |
| Inline priority mapping | `github/types.py` | Priority utils |
| Inline state label logic | `github/types.py` | State label helpers |
| Query strings | `github/queries.py` | All queries |

---

### Jira Adapter (1,899 lines, 53 methods)

**Current Structure:**
```
jira.py (1,899 lines)
├── parse_jira_datetime (function)
├── extract_text_from_adf (function)
├── JiraAdapter (class)
│   ├── Client methods (_make_request)
│   ├── ADF conversion (_convert_from_adf, _convert_to_adf)
│   ├── Transformation methods (_issue_to_ticket)
│   ├── Type conversions (inline)
│   ├── CRUD operations
│   └── Business logic
```

**Proposed Modular Structure:**
```
jira/
├── __init__.py (24 lines) - Public API
├── adapter.py (~1,200 lines) - Business logic only
├── client.py (~350 lines) - REST client + auth
├── queries.py (~200 lines) - JQL builders, field selectors
├── types.py (~400 lines) - Status/priority mappings, ADF utils
└── mappers.py (~350 lines) - Data transformations
```

**What Moves Where:**

| Current Location | New Location | Component |
|-----------------|--------------|-----------|
| `parse_jira_datetime()` | `jira/types.py` | Date parsing |
| `extract_text_from_adf()` | `jira/types.py` | ADF utilities |
| `_convert_from_adf()` | `jira/types.py` | ADF to text |
| `_convert_to_adf()` | `jira/types.py` | Text to ADF |
| `_make_request()` | `jira/client.py` | HTTP client |
| `_issue_to_ticket()` | `jira/mappers.py` | Issue → Task/Epic |
| Inline status mapping | `jira/types.py` | Status mappings |
| Inline priority mapping | `jira/types.py` | Priority mappings |
| JQL query building | `jira/queries.py` | JQL builders |

---

## Module Interaction Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    External User                        │
└─────────────────────┬───────────────────────────────────┘
                      │
                      │ from adapter import GitHubAdapter
                      │
┌─────────────────────▼───────────────────────────────────┐
│              __init__.py (24 lines)                     │
│  - Exports: GitHubAdapter                               │
│  - Documentation: Module structure                      │
└─────────────────────┬───────────────────────────────────┘
                      │
                      │ Imports adapter class
                      │
┌─────────────────────▼───────────────────────────────────┐
│           adapter.py (~1,600 lines)                     │
│                                                          │
│  Main Responsibilities:                                 │
│  - CRUD orchestration (create, read, update, delete)   │
│  - Business logic and validation                        │
│  - State transition workflows                           │
│  - Label/user resolution                                │
│  - Caching coordination                                 │
│                                                          │
│  Delegates to:                                          │
│  ├── client.execute_*()      (API calls)               │
│  ├── mappers.map_*()         (transformations)         │
│  ├── types.get_*()           (type conversions)        │
│  └── queries.*_QUERY         (GraphQL strings)         │
└───────────┬──────────┬──────────┬──────────┬───────────┘
            │          │          │          │
    ┌───────▼──┐  ┌────▼────┐ ┌──▼─────┐ ┌─▼────────┐
    │ client.py│  │mappers  │ │types.py│ │queries.py│
    │ (~400)   │  │ (~400)  │ │ (~300) │ │  (~350)  │
    └──────────┘  └─────────┘ └────────┘ └──────────┘
         │
         │ HTTP/GraphQL requests
         │
    ┌────▼──────────────────┐
    │  GitHub/Jira API      │
    └───────────────────────┘
```

**Data Flow Example (Create Task):**

```
1. User calls: adapter.create(task)
   │
2. adapter.py orchestrates:
   ├── types.py: Validate and convert priority/state
   ├── mappers.py: Build API input from Task
   ├── client.py: Execute POST request
   ├── mappers.py: Transform API response to Task
   └── Return Task to user
```

**Dependency Rules:**
- `adapter.py` → Can import from ALL modules (orchestrator)
- `client.py` → Can import from `types.py` only (for exceptions)
- `mappers.py` → Can import from `types.py` only (for conversions)
- `queries.py` → NO imports (pure strings)
- `types.py` → NO imports from other modules (base layer)

---

## Refactoring Strategy

### Phase 1: Preparation (Non-Breaking)
**Goal:** Set up infrastructure without changing functionality

1. **Create module directories**:
   ```bash
   mkdir -p src/mcp_ticketer/adapters/github
   mkdir -p src/mcp_ticketer/adapters/jira
   ```

2. **Create empty module files** with proper imports:
   ```python
   # github/__init__.py
   from .adapter import GitHubAdapter
   __all__ = ["GitHubAdapter"]

   # github/types.py
   from ...core.models import Priority, TicketState

   # github/client.py
   import httpx
   from ...core.exceptions import AdapterError, AuthenticationError

   # github/queries.py
   # (no imports, pure strings)

   # github/mappers.py
   from ...core.models import Task, Epic, Comment, Attachment
   from .types import get_universal_state, get_github_priority
   ```

3. **Update imports** in test files to use new module:
   ```python
   # Before
   from mcp_ticketer.adapters.github import GitHubAdapter

   # After
   from mcp_ticketer.adapters.github import GitHubAdapter  # same!
   ```

### Phase 2: Extract Types Module
**Goal:** Move type definitions and mappings first (no dependencies)

**GitHub:**
```python
# github/types.py

class GitHubStateMapping:
    OPEN = "open"
    CLOSED = "closed"
    STATE_LABELS = {
        TicketState.IN_PROGRESS: "in-progress",
        TicketState.READY: "ready",
        ...
    }

def get_universal_state(github_state: str, labels: list[str]) -> TicketState:
    """Convert GitHub state + labels to universal state."""
    if github_state == "closed":
        return TicketState.CLOSED

    # Check for state labels
    for state, label in GitHubStateMapping.STATE_LABELS.items():
        if label in labels:
            return state

    return TicketState.OPEN

def get_github_priority(labels: list[str]) -> Priority:
    """Extract priority from GitHub labels."""
    for priority, priority_labels in GitHubStateMapping.PRIORITY_LABELS.items():
        if any(label in labels for label in priority_labels):
            return priority
    return Priority.MEDIUM
```

**Jira:**
```python
# jira/types.py

def parse_jira_datetime(date_str: str) -> datetime | None:
    """Parse JIRA datetime strings."""
    # Move existing implementation

def extract_text_from_adf(adf_content: Any) -> str:
    """Extract text from Atlassian Document Format."""
    # Move existing implementation

def convert_from_adf(adf_content: Any) -> str:
    """Convert ADF to plain text."""
    # Move from adapter._convert_from_adf()

def convert_to_adf(text: str) -> dict[str, Any]:
    """Convert plain text to ADF."""
    # Move from adapter._convert_to_adf()

def get_universal_priority(jira_priority: str) -> Priority:
    """Convert JIRA priority name to universal."""
    # Extract from adapter

def get_jira_status(state: TicketState) -> str:
    """Convert universal state to JIRA status."""
    # Extract from adapter
```

**Validation:**
```python
# Test that types module works independently
from mcp_ticketer.adapters.github.types import get_universal_state

state = get_universal_state("open", ["in-progress"])
assert state == TicketState.IN_PROGRESS
```

### Phase 3: Extract Queries Module
**Goal:** Move all query strings and fragments

**GitHub:**
```python
# github/queries.py

# GraphQL Fragments
ISSUE_FRAGMENT = """
    fragment IssueFields on Issue {
        id
        number
        title
        body
        state
        createdAt
        updatedAt
        ...
    }
"""

USER_FRAGMENT = """
    fragment UserFields on User {
        login
        email
        name
    }
"""

LABEL_FRAGMENT = """
    fragment LabelFields on Label {
        name
        color
        description
    }
"""

# Compact vs Full fragments
ISSUE_COMPACT_FRAGMENT = ISSUE_FRAGMENT  # Subset of fields
ISSUE_FULL_FRAGMENT = ISSUE_FRAGMENT + """
    comments(first: 50) { ... }
    timeline { ... }
"""

# Queries
SEARCH_ISSUES_QUERY = ISSUE_COMPACT_FRAGMENT + """
    query SearchIssues($query: String!) {
        search(query: $query, type: ISSUE) {
            nodes {
                ... on Issue {
                    ...IssueFields
                }
            }
        }
    }
"""

GET_ISSUE_QUERY = ISSUE_FULL_FRAGMENT + """
    query GetIssue($owner: String!, $repo: String!, $number: Int!) {
        repository(owner: $owner, name: $repo) {
            issue(number: $number) {
                ...IssueFields
            }
        }
    }
"""

# Mutations
CREATE_ISSUE_MUTATION = ISSUE_FULL_FRAGMENT + """
    mutation CreateIssue($input: CreateIssueInput!) {
        createIssue(input: $input) {
            issue {
                ...IssueFields
            }
        }
    }
"""
```

**Jira (REST, not GraphQL):**
```python
# jira/queries.py

# JQL Query Builders
def build_jql_filter(
    project: str | None = None,
    status: str | None = None,
    assignee: str | None = None,
    labels: list[str] | None = None,
) -> str:
    """Build JQL query string from parameters."""
    clauses = []

    if project:
        clauses.append(f"project = {project}")
    if status:
        clauses.append(f"status = '{status}'")
    if assignee:
        clauses.append(f"assignee = '{assignee}'")
    if labels:
        label_clause = " AND ".join(f"labels = '{label}'" for label in labels)
        clauses.append(f"({label_clause})")

    return " AND ".join(clauses) if clauses else ""

# Field Selectors (for REST API expand parameters)
ISSUE_COMPACT_FIELDS = "id,key,summary,status,priority,assignee"
ISSUE_FULL_FIELDS = ISSUE_COMPACT_FIELDS + ",description,comment,attachment,parent,subtasks"
EPIC_FIELDS = "id,key,summary,status,description,customfield_epic"

# Expand Parameters
EXPAND_COMMENTS = "renderedFields,comment"
EXPAND_ATTACHMENTS = "attachment"
EXPAND_CHANGELOG = "changelog"
```

**Validation:**
```python
# Test query composition
from mcp_ticketer.adapters.github.queries import SEARCH_ISSUES_QUERY

assert "fragment IssueFields" in SEARCH_ISSUES_QUERY
assert "query SearchIssues" in SEARCH_ISSUES_QUERY
```

### Phase 4: Extract Client Module
**Goal:** Move API communication and error handling

**GitHub:**
```python
# github/client.py

class GitHubClient:
    """GitHub REST and GraphQL client with error handling."""

    def __init__(self, token: str, owner: str, repo: str):
        self.token = token
        self.owner = owner
        self.repo = repo
        self._rest_base = "https://api.github.com"
        self._graphql_base = "https://api.github.com/graphql"

    async def execute_rest(
        self,
        method: str,
        endpoint: str,
        json_data: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """Execute REST API request with error handling."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method,
                    f"{self._rest_base}/{endpoint}",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json=json_data,
                    params=params,
                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise AuthenticationError("Invalid GitHub token", "github")
                elif e.response.status_code == 403:
                    if "rate limit" in e.response.text.lower():
                        raise RateLimitError("GitHub rate limit exceeded", "github")
                    raise AuthenticationError("Forbidden", "github")
                raise AdapterError(f"GitHub REST error: {e}", "github")

    async def execute_graphql(
        self,
        query: str,
        variables: dict | None = None,
    ) -> dict[str, Any]:
        """Execute GraphQL query with error handling."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self._graphql_base,
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={"query": query, "variables": variables or {}},
                )
                response.raise_for_status()
                data = response.json()

                if "errors" in data:
                    raise AdapterError(f"GraphQL errors: {data['errors']}", "github")

                return data["data"]

            except httpx.HTTPStatusError as e:
                # Similar error handling
                raise AdapterError(f"GitHub GraphQL error: {e}", "github")

    async def test_connection(self) -> bool:
        """Test GitHub authentication."""
        try:
            await self.execute_rest("GET", "user")
            return True
        except Exception:
            return False
```

**Jira:**
```python
# jira/client.py

class JiraClient:
    """JIRA REST client with error handling."""

    def __init__(self, base_url: str, email: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.api_token = api_token

    async def execute_request(
        self,
        method: str,
        endpoint: str,
        json_data: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """Execute JIRA REST request with error handling."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method,
                    f"{self.base_url}/rest/api/3/{endpoint}",
                    auth=(self.email, self.api_token),
                    json=json_data,
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json() if response.text else {}

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise AuthenticationError("Invalid JIRA credentials", "jira")
                elif e.response.status_code == 403:
                    raise AuthenticationError("Forbidden", "jira")
                elif e.response.status_code == 429:
                    raise RateLimitError("JIRA rate limit exceeded", "jira")
                raise AdapterError(f"JIRA REST error: {e}", "jira")

    async def test_connection(self) -> bool:
        """Test JIRA authentication."""
        try:
            await self.execute_request("GET", "myself")
            return True
        except Exception:
            return False
```

**Validation:**
```python
# Test client independently
from mcp_ticketer.adapters.github.client import GitHubClient

client = GitHubClient(token="...", owner="octocat", repo="hello-world")
is_valid = await client.test_connection()
assert is_valid
```

### Phase 5: Extract Mappers Module
**Goal:** Move data transformation logic

**GitHub:**
```python
# github/mappers.py

from ...core.models import Task, Epic, Comment, Attachment, Priority, TicketState
from .types import get_universal_state, get_github_priority

def map_github_issue_to_task(issue: dict[str, Any]) -> Task:
    """Convert GitHub issue to universal Task model."""
    # Extract basic fields
    task_id = str(issue["number"])
    title = issue["title"]
    description = issue.get("body", "")

    # Extract labels
    labels = [label["name"] for label in issue.get("labels", [])]

    # Convert state (GitHub state + labels)
    github_state = issue["state"]
    state = get_universal_state(github_state, labels)

    # Convert priority (from labels)
    priority = get_github_priority(labels)

    # Extract assignees
    assignees = issue.get("assignees", [])
    assignee = assignees[0]["login"] if assignees else None

    # Extract dates
    created_at = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
    updated_at = datetime.fromisoformat(issue["updated_at"].replace("Z", "+00:00"))

    # Extract parent (milestone or project)
    parent_epic = None
    if issue.get("milestone"):
        parent_epic = str(issue["milestone"]["number"])

    return Task(
        id=task_id,
        title=title,
        description=description,
        state=state,
        priority=priority,
        assignee=assignee,
        tags=labels,
        parent_epic=parent_epic,
        created_at=created_at,
        updated_at=updated_at,
        metadata={"github": {"url": issue.get("html_url")}},
    )

def build_github_issue_input(task: Task) -> dict[str, Any]:
    """Build GitHub issue creation input from Task."""
    from .types import GitHubStateMapping

    issue_input = {
        "title": task.title,
        "body": task.description or "",
    }

    # Add labels (combine tags + state label + priority label)
    labels = list(task.tags or [])

    # Add state label if needed
    if task.state and task.state != TicketState.OPEN:
        state_label = GitHubStateMapping.STATE_LABELS.get(task.state)
        if state_label:
            labels.append(state_label)

    # Add priority label
    if task.priority:
        priority_labels = GitHubStateMapping.PRIORITY_LABELS.get(task.priority, [])
        if priority_labels:
            labels.append(priority_labels[0])

    issue_input["labels"] = labels

    # Add assignee
    if task.assignee:
        issue_input["assignees"] = [task.assignee]

    # Add milestone (from parent_epic)
    if task.parent_epic:
        issue_input["milestone"] = int(task.parent_epic)

    return issue_input

def task_to_compact_format(task: Task) -> dict[str, Any]:
    """Convert Task to compact format (token optimization)."""
    return {
        "id": task.id,
        "title": task.title,
        "state": task.state.value if task.state else None,
        "priority": task.priority.value if task.priority else None,
        "assignee": task.assignee,
    }
```

**Jira:**
```python
# jira/mappers.py

from ...core.models import Task, Epic, Comment, Attachment, Priority, TicketState
from .types import (
    parse_jira_datetime,
    extract_text_from_adf,
    convert_from_adf,
    convert_to_adf,
    get_universal_priority,
)

def map_jira_issue_to_task(issue: dict[str, Any]) -> Task:
    """Convert JIRA issue to universal Task model."""
    fields = issue["fields"]

    # Extract basic fields
    task_id = issue["key"]
    title = fields["summary"]
    description = ""
    if fields.get("description"):
        description = convert_from_adf(fields["description"])

    # Convert status to state
    jira_status = fields["status"]["name"]
    state = get_universal_state_from_jira(jira_status)

    # Convert priority
    jira_priority = fields.get("priority", {}).get("name", "Medium")
    priority = get_universal_priority(jira_priority)

    # Extract assignee
    assignee = None
    if fields.get("assignee"):
        assignee = fields["assignee"]["emailAddress"]

    # Extract labels
    tags = fields.get("labels", [])

    # Extract parent
    parent_epic = None
    if fields.get("parent"):
        parent_epic = fields["parent"]["key"]

    # Extract dates
    created_at = parse_jira_datetime(fields["created"])
    updated_at = parse_jira_datetime(fields["updated"])

    return Task(
        id=task_id,
        title=title,
        description=description,
        state=state,
        priority=priority,
        assignee=assignee,
        tags=tags,
        parent_epic=parent_epic,
        created_at=created_at,
        updated_at=updated_at,
        metadata={"jira": {"self": issue["self"]}},
    )

def build_jira_issue_input(task: Task, project_key: str) -> dict[str, Any]:
    """Build JIRA issue creation input from Task."""
    fields = {
        "project": {"key": project_key},
        "summary": task.title,
        "issuetype": {"name": "Task"},
    }

    # Add description (convert to ADF)
    if task.description:
        fields["description"] = convert_to_adf(task.description)

    # Add priority
    if task.priority:
        jira_priority = get_jira_priority(task.priority)
        fields["priority"] = {"name": jira_priority}

    # Add assignee
    if task.assignee:
        fields["assignee"] = {"emailAddress": task.assignee}

    # Add labels
    if task.tags:
        fields["labels"] = task.tags

    # Add parent
    if task.parent_epic:
        fields["parent"] = {"key": task.parent_epic}

    return {"fields": fields}
```

**Validation:**
```python
# Test mappers independently
from mcp_ticketer.adapters.github.mappers import map_github_issue_to_task

github_issue = {
    "number": 123,
    "title": "Test issue",
    "body": "Description",
    "state": "open",
    "labels": [{"name": "in-progress"}],
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-02T00:00:00Z",
}

task = map_github_issue_to_task(github_issue)
assert task.id == "123"
assert task.state == TicketState.IN_PROGRESS
```

### Phase 6: Refactor Main Adapter
**Goal:** Slim down adapter.py to orchestration only

**Before (adapter.py: 2,585 lines):**
```python
class GitHubAdapter(BaseAdapter):
    def __init__(self, config):
        self.token = config["token"]
        self.owner = config["owner"]
        self.repo = config["repo"]
        # Inline client setup
        self._base_url = "https://api.github.com"

    async def _make_request(self, method, endpoint, ...):
        # 100+ lines of HTTP client logic
        ...

    async def _graphql_request(self, query, variables):
        # 50+ lines of GraphQL client logic
        ...

    def _task_from_github_issue(self, issue):
        # 80+ lines of transformation logic
        ...

    async def create(self, ticket):
        # Mix of validation, transformation, API calls
        ...
```

**After (adapter.py: ~1,600 lines):**
```python
from .client import GitHubClient
from .mappers import (
    map_github_issue_to_task,
    build_github_issue_input,
    task_to_compact_format,
)
from .queries import CREATE_ISSUE_MUTATION, GET_ISSUE_QUERY
from .types import get_universal_state, GitHubStateMapping

class GitHubAdapter(BaseAdapter):
    def __init__(self, config):
        # Delegate client creation
        self.client = GitHubClient(
            token=config["token"],
            owner=config["owner"],
            repo=config["repo"],
        )
        self.owner = config["owner"]
        self.repo = config["repo"]

    async def create(self, ticket: Epic | Task) -> Epic | Task:
        """Orchestrate ticket creation."""
        if isinstance(ticket, Task):
            return await self._create_task(ticket)
        elif isinstance(ticket, Epic):
            return await self._create_epic(ticket)

    async def _create_task(self, task: Task) -> Task:
        """Create GitHub issue from Task.

        Orchestration flow:
        1. Validate task data
        2. Build API input (via mapper)
        3. Execute API call (via client)
        4. Transform response (via mapper)
        """
        # 1. Validation
        if not task.title:
            raise ValueError("Task title is required")

        # 2. Build input (delegate to mapper)
        issue_input = build_github_issue_input(task)

        # 3. Execute API call (delegate to client)
        result = await self.client.execute_rest(
            "POST",
            f"repos/{self.owner}/{self.repo}/issues",
            json_data=issue_input,
        )

        # 4. Transform response (delegate to mapper)
        return map_github_issue_to_task(result)

    async def read(self, ticket_id: str) -> Task | None:
        """Read ticket by ID.

        Orchestration flow:
        1. Fetch from API (via client)
        2. Transform to universal model (via mapper)
        """
        # 1. Fetch (delegate to client)
        issue = await self.client.execute_rest(
            "GET",
            f"repos/{self.owner}/{self.repo}/issues/{ticket_id}",
        )

        # 2. Transform (delegate to mapper)
        return map_github_issue_to_task(issue)

    # All other methods follow same pattern:
    # - Minimal business logic
    # - Delegate to client/mappers/types
    # - Focus on orchestration
```

**Key Changes:**
- ❌ Remove: `_make_request()`, `_graphql_request()` → `client.execute_*()`
- ❌ Remove: `_task_from_github_issue()` → `mappers.map_github_issue_to_task()`
- ❌ Remove: Inline type conversions → `types.get_universal_state()`
- ❌ Remove: Embedded query strings → `queries.CREATE_ISSUE_MUTATION`
- ✅ Keep: Business logic (validation, caching, workflow)
- ✅ Keep: Orchestration (calling client/mappers in correct order)

**Line Count Reduction:**
- Client logic: -150 lines (moved to `client.py`)
- Transformation logic: -250 lines (moved to `mappers.py`)
- Type mappings: -100 lines (moved to `types.py`)
- Query strings: -150 lines (moved to `queries.py`)
- **Total reduction: ~650 lines** (2,585 → ~1,935 lines)

### Phase 7: Update Tests
**Goal:** Test modules independently

**New Test Structure:**
```python
# tests/adapters/github/test_types.py
def test_state_mapping():
    from mcp_ticketer.adapters.github.types import get_universal_state

    # Open issue
    assert get_universal_state("open", []) == TicketState.OPEN

    # Open + in-progress label
    assert get_universal_state("open", ["in-progress"]) == TicketState.IN_PROGRESS

    # Closed issue
    assert get_universal_state("closed", []) == TicketState.CLOSED

# tests/adapters/github/test_client.py
@pytest.mark.asyncio
async def test_rest_request():
    from mcp_ticketer.adapters.github.client import GitHubClient

    client = GitHubClient(token="test", owner="test", repo="test")

    # Mock httpx response
    with patch("httpx.AsyncClient.request") as mock:
        mock.return_value.json.return_value = {"id": 123}
        result = await client.execute_rest("GET", "test")
        assert result["id"] == 123

# tests/adapters/github/test_mappers.py
def test_map_github_issue_to_task():
    from mcp_ticketer.adapters.github.mappers import map_github_issue_to_task

    issue = {
        "number": 123,
        "title": "Test",
        "state": "open",
        "labels": [],
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }

    task = map_github_issue_to_task(issue)
    assert task.id == "123"
    assert task.title == "Test"

# tests/adapters/github/test_adapter.py
@pytest.mark.asyncio
async def test_create_task_integration():
    """Integration test using all modules together."""
    from mcp_ticketer.adapters.github import GitHubAdapter

    adapter = GitHubAdapter({
        "token": "test",
        "owner": "test",
        "repo": "test",
    })

    # Mock client.execute_rest()
    with patch.object(adapter.client, "execute_rest") as mock:
        mock.return_value = {
            "number": 123,
            "title": "Test",
            "state": "open",
            ...
        }

        task = Task(title="Test", description="Test")
        result = await adapter.create(task)

        assert result.id == "123"
```

---

## Implementation Checklist

### GitHub Adapter Refactoring

- [ ] **Phase 1: Setup**
  - [ ] Create `src/mcp_ticketer/adapters/github/` directory
  - [ ] Create `__init__.py` with GitHubAdapter export
  - [ ] Create empty `types.py`, `client.py`, `queries.py`, `mappers.py`
  - [ ] Update imports in existing tests

- [ ] **Phase 2: Types Module**
  - [ ] Move `GitHubStateMapping` class to `types.py`
  - [ ] Add `get_universal_state(state, labels)` function
  - [ ] Add `get_github_priority(labels)` function
  - [ ] Add state/priority helper functions
  - [ ] Write unit tests for `types.py`

- [ ] **Phase 3: Queries Module**
  - [ ] Move `GitHubGraphQLQueries` class to `queries.py`
  - [ ] Extract fragment definitions (ISSUE_FRAGMENT, etc.)
  - [ ] Create compact vs. full fragment variants
  - [ ] Extract all query strings from adapter
  - [ ] Write validation tests for query composition

- [ ] **Phase 4: Client Module**
  - [ ] Create `GitHubClient` class in `client.py`
  - [ ] Move `_make_request()` → `execute_rest()`
  - [ ] Move `_graphql_request()` → `execute_graphql()`
  - [ ] Add error handling and retries
  - [ ] Add `test_connection()` method
  - [ ] Write unit tests with mocked HTTP

- [ ] **Phase 5: Mappers Module**
  - [ ] Move `_task_from_github_issue()` → `map_github_issue_to_task()`
  - [ ] Add `build_github_issue_input(task)` function
  - [ ] Add `map_github_comment_to_comment()` function
  - [ ] Add `task_to_compact_format()` function
  - [ ] Write unit tests for all mappers

- [ ] **Phase 6: Refactor Adapter**
  - [ ] Update `__init__()` to use `GitHubClient`
  - [ ] Replace inline transformations with mapper calls
  - [ ] Replace inline type conversions with types calls
  - [ ] Replace embedded queries with query imports
  - [ ] Remove all moved code from adapter.py
  - [ ] Update integration tests

- [ ] **Phase 7: Cleanup**
  - [ ] Remove old `github.py` file
  - [ ] Update all imports across codebase
  - [ ] Run full test suite
  - [ ] Update documentation

### Jira Adapter Refactoring

- [ ] **Phase 1: Setup**
  - [ ] Create `src/mcp_ticketer/adapters/jira/` directory
  - [ ] Create `__init__.py` with JiraAdapter export
  - [ ] Create empty `types.py`, `client.py`, `queries.py`, `mappers.py`
  - [ ] Update imports in existing tests

- [ ] **Phase 2: Types Module**
  - [ ] Move `parse_jira_datetime()` to `types.py`
  - [ ] Move `extract_text_from_adf()` to `types.py`
  - [ ] Move `_convert_from_adf()` to `types.py`
  - [ ] Move `_convert_to_adf()` to `types.py`
  - [ ] Add status/priority mapping functions
  - [ ] Write unit tests for ADF conversion

- [ ] **Phase 3: Queries Module**
  - [ ] Create JQL query builder functions
  - [ ] Create field selector constants
  - [ ] Create expand parameter constants
  - [ ] Write unit tests for JQL building

- [ ] **Phase 4: Client Module**
  - [ ] Create `JiraClient` class in `client.py`
  - [ ] Move `_make_request()` → `execute_request()`
  - [ ] Add error handling and retries
  - [ ] Add `test_connection()` method
  - [ ] Write unit tests with mocked HTTP

- [ ] **Phase 5: Mappers Module**
  - [ ] Move `_issue_to_ticket()` → `map_jira_issue_to_task()`
  - [ ] Add `build_jira_issue_input(task)` function
  - [ ] Add `map_jira_comment_to_comment()` function
  - [ ] Add `task_to_compact_format()` function
  - [ ] Write unit tests for all mappers

- [ ] **Phase 6: Refactor Adapter**
  - [ ] Update `__init__()` to use `JiraClient`
  - [ ] Replace inline transformations with mapper calls
  - [ ] Replace inline type conversions with types calls
  - [ ] Replace embedded JQL with query builders
  - [ ] Remove all moved code from adapter.py
  - [ ] Update integration tests

- [ ] **Phase 7: Cleanup**
  - [ ] Remove old `jira.py` file
  - [ ] Update all imports across codebase
  - [ ] Run full test suite
  - [ ] Update documentation

---

## Expected Benefits

### 1. **Improved Maintainability**
- **Single Responsibility**: Each module has one clear purpose
- **Easier Navigation**: Find code by category (queries, types, mappers)
- **Reduced Complexity**: Smaller files are easier to understand

### 2. **Better Testability**
- **Unit Testing**: Test modules in isolation
- **Mock Simplification**: Mock client instead of entire adapter
- **Faster Tests**: Run type/mapper tests without API calls

### 3. **Enhanced Reusability**
- **Shared Types**: Use type converters across multiple methods
- **Query Composition**: Reuse fragments in multiple queries
- **Mapper Functions**: Call transformations from anywhere

### 4. **Token Efficiency**
- **Compact Formats**: Dedicated functions for minimal serialization
- **Fragment Reuse**: Avoid duplicating field definitions
- **Selective Loading**: Load only needed fields via queries

### 5. **Developer Experience**
- **Consistent Structure**: Same pattern across all adapters
- **Clear Interfaces**: Public API remains simple
- **Easy Extension**: Add new platforms following same pattern

---

## Risks and Mitigations

### Risk 1: Breaking Changes
**Impact:** Existing imports may break
**Mitigation:**
- Keep `from mcp_ticketer.adapters.github import GitHubAdapter` working
- Use `__init__.py` to maintain public API
- Deprecate old imports gradually with warnings

### Risk 2: Test Coverage Gaps
**Impact:** Refactoring may introduce bugs
**Mitigation:**
- Write tests for each module before refactoring adapter
- Run full test suite after each phase
- Add integration tests that cover all modules together

### Risk 3: Performance Regression
**Impact:** Additional function calls may slow down operations
**Mitigation:**
- Benchmark before/after refactoring
- Optimize hot paths if needed
- Use caching for frequently called functions

### Risk 4: Incomplete Migration
**Impact:** Some code may remain in adapter.py
**Mitigation:**
- Use checklist to track all moved code
- Lint for remaining inline transformations
- Code review to verify clean separation

---

## Success Metrics

### Quantitative Metrics
- [ ] **Line Count Reduction**: Adapter files reduced by 30-40%
- [ ] **Test Coverage**: Maintain or increase coverage (>80%)
- [ ] **Performance**: No regression in operation latency
- [ ] **Module Size**: No module exceeds 600 lines

### Qualitative Metrics
- [ ] **Code Clarity**: Easier to find and modify code
- [ ] **Test Simplicity**: Tests are easier to write and maintain
- [ ] **Consistency**: All adapters follow same structure
- [ ] **Documentation**: Clear module responsibilities documented

---

## Conclusion

The Linear adapter's modular structure provides a proven blueprint for refactoring GitHub and Jira adapters. The key principles are:

1. **Separation of Concerns**: Client, types, queries, mappers, adapter
2. **Clear Boundaries**: Each module has well-defined responsibilities
3. **Testability**: Pure functions and dependency injection
4. **Consistency**: Same pattern across all adapters
5. **Maintainability**: Smaller, focused files

By following the phased refactoring approach, we can:
- Reduce adapter file sizes by ~40%
- Improve testability and code quality
- Maintain backward compatibility
- Create consistent architecture across all adapters

The refactoring will take approximately **40-60 hours** of development time:
- GitHub adapter: 20-30 hours
- Jira adapter: 15-20 hours
- Testing and validation: 5-10 hours

**Recommended approach**: Start with GitHub adapter (larger file, more complexity), then apply learned lessons to Jira adapter.

---

## Appendix: File Size Comparison

### Current State
| Adapter | File | Lines | Methods |
|---------|------|-------|---------|
| Linear | adapter.py | 4,095 | ~50 |
| Linear | client.py | 500 | 8 |
| Linear | queries.py | 666 | 0 |
| Linear | types.py | 400 | 10 |
| Linear | mappers.py | 527 | 12 |
| **Linear Total** | | **6,212** | **~80** |
| | | | |
| GitHub | github.py | 2,585 | 49 |
| Jira | jira.py | 1,899 | 53 |

### Projected State After Refactoring
| Adapter | File | Lines | Methods |
|---------|------|-------|---------|
| GitHub | adapter.py | ~1,600 | ~35 |
| GitHub | client.py | ~400 | ~6 |
| GitHub | queries.py | ~350 | 0 |
| GitHub | types.py | ~300 | ~8 |
| GitHub | mappers.py | ~400 | ~10 |
| **GitHub Total** | | **~3,050** | **~59** |
| | | | |
| Jira | adapter.py | ~1,200 | ~30 |
| Jira | client.py | ~350 | ~5 |
| Jira | queries.py | ~200 | ~5 |
| Jira | types.py | ~400 | ~10 |
| Jira | mappers.py | ~350 | ~8 |
| **Jira Total** | | **~2,500** | **~58** |

**Key Insights:**
- Linear total (~6,200 lines) is higher because it's fully featured with all operations
- After refactoring, GitHub/Jira totals will increase slightly due to better organization
- Main adapter files will shrink by 40-50% (easier to navigate)
- Total line count may increase slightly, but code quality and testability improve significantly

---

## Next Steps

1. **Review and approve this analysis** with the team
2. **Create refactoring tickets** for each phase
3. **Start with GitHub adapter** (phase 1: setup)
4. **Track progress** using the implementation checklist
5. **Apply learnings** to Jira adapter refactoring

**Estimated Timeline:**
- Week 1-2: GitHub adapter refactoring
- Week 3: GitHub adapter testing and validation
- Week 4-5: Jira adapter refactoring
- Week 6: Jira adapter testing and final validation

---

**End of Analysis**
