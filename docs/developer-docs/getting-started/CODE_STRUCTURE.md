# CODE_STRUCTURE.md - MCP Ticketer Architecture

**Generated**: 2025-10-22
**Project Version**: 0.1.11
**Optimized For**: AI Agents, Claude Code, Claude MPM

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Directory Structure](#directory-structure)
3. [Module Breakdown](#module-breakdown)
4. [Core Abstractions](#core-abstractions)
5. [Data Flow](#data-flow)
6. [Dependency Map](#dependency-map)
7. [Extension Points](#extension-points)

---

## Project Overview

**MCP Ticketer** is a universal ticket management interface designed for AI agents using the Model Context Protocol (MCP). It provides a unified API for managing tickets across multiple systems (JIRA, Linear, GitHub, AI-Trackdown) through adapters.

### Key Architectural Patterns

- **Adapter Pattern**: Pluggable ticket system integrations
- **Strategy Pattern**: Configurable state mappings per adapter
- **Repository Pattern**: Abstract data access layer
- **Observer Pattern**: Event-driven queue system
- **Factory Pattern**: Adapter registry and instantiation

---

## Directory Structure

```
mcp-ticketer/
├── src/mcp_ticketer/              # Primary source code
│   ├── __init__.py               # Package initialization
│   ├── __version__.py            # Version management
│   │
│   ├── adapters/                 # Ticket system adapters
│   │   ├── __init__.py          # Adapter registration
│   │   ├── aitrackdown.py       # Local file-based adapter (28 methods)
│   │   ├── linear.py            # Linear GraphQL adapter (30 methods)
│   │   ├── jira.py              # JIRA REST adapter (32 methods)
│   │   └── github.py            # GitHub Issues adapter (28 methods)
│   │
│   ├── core/                     # Core business logic
│   │   ├── __init__.py          # Core exports
│   │   ├── adapter.py           # BaseAdapter abstract class (11 methods)
│   │   ├── config.py            # Configuration management (8 methods)
│   │   ├── models.py            # Pydantic data models (7 classes)
│   │   ├── registry.py          # Adapter factory (6 methods)
│   │   ├── http_client.py       # Shared HTTP client (5 methods)
│   │   └── mappers.py           # Data transformation utilities (10 functions)
│   │
│   ├── cli/                      # Command-line interface
│   │   ├── __init__.py          # CLI exports
│   │   ├── main.py              # Typer app and commands (15 commands)
│   │   ├── utils.py             # CLI utilities (8 helper functions)
│   │   └── queue_commands.py    # Queue management commands (5 commands)
│   │
│   ├── mcp/                      # MCP server implementation
│   │   ├── __init__.py          # MCP exports
│   │   └── server.py            # JSON-RPC server (12 methods)
│   │
│   ├── cache/                    # Caching layer
│   │   ├── __init__.py          # Cache exports
│   │   └── memory.py            # TTL-based memory cache (7 methods)
│   │
│   └── queue/                    # Async queue system
│       ├── __init__.py          # Queue exports
│       ├── manager.py           # Queue manager (9 methods)
│       ├── queue.py             # Queue implementation (6 methods)
│       ├── worker.py            # Worker processes (4 methods)
│       ├── __main__.py          # Queue CLI entry point
│       └── run_worker.py        # Worker runner script
│
├── tests/                        # Test suite
│   ├── unit/                    # Unit tests (90% coverage target)
│   ├── integration/             # Integration tests (70% coverage)
│   └── e2e/                     # End-to-end tests
│
├── docs/                         # Documentation
│   ├── DEVELOPER_GUIDE.md       # Comprehensive dev docs
│   ├── USER_GUIDE.md            # End-user guide
│   ├── API_REFERENCE.md         # API documentation
│   ├── CONFIGURATION.md         # Configuration guide
│   └── adapters/                # Adapter-specific docs
│
├── Makefile                      # Command interface (40+ targets)
├── pyproject.toml               # Project configuration
├── pytest.ini                   # Test configuration
├── .pre-commit-config.yaml      # Pre-commit hooks
├── CLAUDE.md                    # AI agent instructions (this project)
├── CODE_STRUCTURE.md            # This file
├── QUICK_START.md               # 5-minute setup guide
├── CONTRIBUTING.md              # Contribution guidelines
└── README.md                    # Project overview
```

---

## Module Breakdown

### Core Models (`src/mcp_ticketer/core/models.py`)

**Purpose**: Define universal data structures using Pydantic for validation

**Key Classes**:

```python
Priority(Enum)              # LOW, MEDIUM, HIGH, CRITICAL
TicketState(Enum)          # OPEN, IN_PROGRESS, READY, TESTED, DONE, CLOSED, WAITING, BLOCKED
    └── valid_transitions()  # State machine validation
    └── can_transition_to()  # Transition check

BaseTicket(BaseModel)      # Base ticket fields
    ├── id: Optional[str]
    ├── title: str
    ├── description: Optional[str]
    ├── state: TicketState
    ├── priority: Priority
    ├── tags: List[str]
    ├── created_at: Optional[datetime]
    ├── updated_at: Optional[datetime]
    └── metadata: Dict[str, Any]

Epic(BaseTicket)           # High-level container
    └── child_issues: List[str]

Task(BaseTicket)           # Individual work item
    ├── parent_issue: Optional[str]
    ├── parent_epic: Optional[str]
    ├── assignee: Optional[str]
    ├── estimated_hours: Optional[float]
    └── actual_hours: Optional[float]

Comment(BaseModel)         # Ticket comment
    ├── id: Optional[str]
    ├── ticket_id: str
    ├── author: Optional[str]
    ├── content: str
    ├── created_at: Optional[datetime]
    └── metadata: Dict[str, Any]

SearchQuery(BaseModel)     # Search parameters
    ├── query: Optional[str]
    ├── state: Optional[TicketState]
    ├── priority: Optional[Priority]
    ├── tags: Optional[List[str]]
    ├── assignee: Optional[str]
    ├── limit: int = 10
    └── offset: int = 0
```

**Dependencies**: pydantic, datetime, typing

---

### Base Adapter (`src/mcp_ticketer/core/adapter.py`)

**Purpose**: Abstract base class defining adapter interface

**Key Methods**:

```python
class BaseAdapter(ABC, Generic[T]):
    def __init__(config: Dict[str, Any]) -> None

    # Abstract methods (must implement)
    @abstractmethod
    def _get_state_mapping() -> Dict[TicketState, str]

    @abstractmethod
    async def create(ticket: T) -> T

    @abstractmethod
    async def read(ticket_id: str) -> Optional[T]

    @abstractmethod
    async def update(ticket_id: str, updates: Dict[str, Any]) -> Optional[T]

    @abstractmethod
    async def delete(ticket_id: str) -> bool

    @abstractmethod
    async def list(limit: int, offset: int, filters: Optional[Dict]) -> List[T]

    @abstractmethod
    async def search(query: SearchQuery) -> List[T]

    @abstractmethod
    async def transition_state(ticket_id: str, target_state: TicketState) -> Optional[T]

    @abstractmethod
    async def add_comment(comment: Comment) -> Comment

    @abstractmethod
    async def get_comments(ticket_id: str, limit: int, offset: int) -> List[Comment]

    # Concrete helper methods
    def map_state_to_system(state: TicketState) -> str
    def map_state_from_system(system_state: str) -> TicketState
    async def validate_transition(ticket_id: str, target_state: TicketState) -> bool
    async def close() -> None
```

**Type Parameters**:
- `T`: TypeVar bound to `BaseTicket` (Epic or Task)

**Dependencies**: abc, typing, core.models

---

### Adapter Registry (`src/mcp_ticketer/core/registry.py`)

**Purpose**: Factory pattern for adapter instantiation and management

**Key Methods**:

```python
class AdapterRegistry:
    _adapters: Dict[str, Type[BaseAdapter]] = {}
    _instances: Dict[str, BaseAdapter] = {}

    @classmethod
    def register(name: str, adapter_class: Type[BaseAdapter]) -> None

    @classmethod
    def get_adapter(name: str, config: Dict[str, Any]) -> BaseAdapter

    @classmethod
    def list_adapters() -> List[str]

    @classmethod
    def clear() -> None

    @classmethod
    def is_registered(name: str) -> bool

    @classmethod
    def unregister(name: str) -> None
```

**Registered Adapters**:
- `aitrackdown`: AITrackdownAdapter
- `linear`: LinearAdapter
- `jira`: JiraAdapter
- `github`: GitHubAdapter

**Dependencies**: typing, core.adapter

---

### CLI Application (`src/mcp_ticketer/cli/main.py`)

**Purpose**: Typer-based command-line interface

**Commands**:

```python
# Configuration
init(adapter: AdapterType, **adapter_options) -> None
config_show() -> None
config_set(key: str, value: str) -> None

# Ticket Operations
create(title: str, description: str, priority: str, assignee: str, tags: List[str]) -> None
read(ticket_id: str, comments: bool) -> None
update(ticket_id: str, **updates) -> None
delete(ticket_id: str) -> None
list(state: str, priority: str, limit: int, offset: int) -> None
search(query: str, state: str, priority: str, limit: int) -> None

# State Transitions
transition(ticket_id: str, target_state: str) -> None

# Comments
comment_add(ticket_id: str, content: str) -> None
comment_list(ticket_id: str, limit: int) -> None

# Utility
show(ticket_id: str, comments: bool) -> None  # Alias for read
version() -> None
```

**CLI Framework**: Typer + Rich
**Output**: Rich tables, colored text, progress bars

**Dependencies**: typer, rich, core.registry, core.models

---

### MCP Server (`src/mcp_ticketer/mcp/server.py`)

**Purpose**: JSON-RPC server implementing Model Context Protocol

**Key Methods**:

```python
class MCPTicketServer:
    def __init__(adapter: BaseAdapter) -> None

    # JSON-RPC handlers
    async def handle_request(request: Dict[str, Any]) -> Dict[str, Any]

    # Tool implementations
    async def ticket_create(params: Dict) -> Dict
    async def ticket_read(params: Dict) -> Dict
    async def ticket_update(params: Dict) -> Dict
    async def ticket_delete(params: Dict) -> Dict
    async def ticket_list(params: Dict) -> Dict
    async def ticket_search(params: Dict) -> Dict
    async def ticket_transition(params: Dict) -> Dict
    async def ticket_comment_add(params: Dict) -> Dict
    async def ticket_comment_list(params: Dict) -> Dict

    # Resource management
    async def list_resources() -> List[Dict]
    async def read_resource(uri: str) -> Dict

    # Server lifecycle
    async def start() -> None
    async def stop() -> None
```

**Protocol**: JSON-RPC 2.0 over stdio
**Transport**: Standard input/output streams

**Dependencies**: json, asyncio, core.adapter, core.models

---

### Cache Layer (`src/mcp_ticketer/cache/memory.py`)

**Purpose**: TTL-based in-memory caching for performance optimization

**Key Classes**:

```python
class CacheEntry:
    value: Any
    created_at: float
    ttl: int

    def is_expired() -> bool

class MemoryCache:
    _cache: Dict[str, CacheEntry] = {}

    async def get(key: str) -> Optional[Any]
    async def set(key: str, value: Any, ttl: int) -> None
    async def delete(key: str) -> None
    async def clear() -> None
    async def cleanup_expired() -> int

    def get_stats() -> Dict[str, Any]
    def cache_decorator(ttl: int, key_prefix: str) -> Callable

# Usage
@cache_decorator(ttl=300, key_prefix="adapter")
async def cached_function(param: str) -> Any:
    # Function implementation
    pass
```

**Features**:
- Time-to-live expiration
- Automatic cleanup
- Statistics tracking
- Decorator support
- Thread-safe operations

**Dependencies**: time, asyncio, functools, typing

---

### Queue System (`src/mcp_ticketer/queue/`)

**Purpose**: Asynchronous job queue for long-running operations

**Components**:

```python
# manager.py
class QueueManager:
    def __init__(storage_path: Path) -> None
    async def enqueue(operation: str, params: Dict) -> str  # Returns queue_id
    async def get_status(queue_id: str) -> Dict
    async def list_jobs(state: str) -> List[Dict]
    async def cancel_job(queue_id: str) -> bool
    async def retry_job(queue_id: str) -> bool
    async def cleanup_completed(older_than: timedelta) -> int

# queue.py
class JobQueue:
    async def push(job: Dict) -> None
    async def pop() -> Optional[Dict]
    async def peek() -> Optional[Dict]
    async def size() -> int
    async def clear() -> None

# worker.py
class QueueWorker:
    def __init__(manager: QueueManager, adapter: BaseAdapter) -> None
    async def start() -> None
    async def stop() -> None
    async def process_job(job: Dict) -> Dict
```

**Job States**: pending, processing, completed, failed, cancelled

**Dependencies**: asyncio, pathlib, json, datetime

---

## Core Abstractions

### State Machine

```
┌─────────────────────────────────────────────────────────────┐
│                    Ticket State Machine                      │
└─────────────────────────────────────────────────────────────┘

    OPEN ────────┐
      │          │
      │          ▼
      ├────► IN_PROGRESS ────────┐
      │          │                │
      │          │                ▼
      │          ├──────────► READY ────────┐
      │          │                │          │
      │          │                │          ▼
      │          │                ├────► TESTED ────► DONE ────► CLOSED
      │          │                │
      │          ▼                ▼
      ├────► WAITING         BLOCKED
      │          │                │
      └──────────┴────────────────┘
```

**Valid Transitions**:
- OPEN → IN_PROGRESS, WAITING, BLOCKED, CLOSED
- IN_PROGRESS → READY, WAITING, BLOCKED, OPEN
- READY → TESTED, IN_PROGRESS, BLOCKED
- TESTED → DONE, IN_PROGRESS
- DONE → CLOSED
- WAITING → OPEN, IN_PROGRESS, CLOSED
- BLOCKED → OPEN, IN_PROGRESS, CLOSED
- CLOSED → (terminal state)

---

### Adapter Pattern Implementation

```
┌────────────────────────────────────────────────┐
│              BaseAdapter (Abstract)            │
│  ┌──────────────────────────────────────────┐  │
│  │ • create(ticket) -> ticket              │  │
│  │ • read(id) -> ticket                    │  │
│  │ • update(id, updates) -> ticket         │  │
│  │ • delete(id) -> bool                    │  │
│  │ • list(filters) -> tickets              │  │
│  │ • search(query) -> tickets              │  │
│  │ • transition_state(id, state) -> ticket │  │
│  │ • add_comment(comment) -> comment       │  │
│  │ • get_comments(id) -> comments          │  │
│  └──────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
                       ▲
        ┌──────────────┼──────────────┐
        │              │              │
┌───────┴────┐  ┌──────┴─────┐  ┌────┴──────┐
│AITrackdown │  │   Linear   │  │   JIRA    │
│  Adapter   │  │  Adapter   │  │  Adapter  │
└────────────┘  └────────────┘  └───────────┘
      │              │              │
┌─────▼────┐  ┌──────▼─────┐  ┌────▼──────┐
│ File I/O │  │  GraphQL   │  │ REST API  │
│   JSON   │  │  API Call  │  │   Call    │
└──────────┘  └────────────┘  └───────────┘
```

---

## Data Flow

### Ticket Creation Flow

```
1. User Input
   ├─ CLI: `mcp-ticketer create "Title"`
   ├─ MCP: JSON-RPC call to ticket_create
   └─ API: Direct adapter.create() call

2. CLI Layer (cli/main.py)
   ├─ Parse arguments
   ├─ Load configuration
   ├─ Get adapter from registry
   └─ Call adapter.create()

3. Adapter Layer (adapters/*.py)
   ├─ Validate input (Task model)
   ├─ Map universal model → system model
   ├─ Make API call / file operation
   ├─ Map system response → universal model
   └─ Return Task with ID

4. Presentation Layer
   ├─ Format output (Rich table)
   ├─ Display success/error
   └─ Return to user

5. Cache Layer (if enabled)
   ├─ Store in memory cache
   ├─ Set TTL expiration
   └─ Update cache stats
```

### Search Flow with Caching

```
1. Search Request
   └─ Query: "bug priority:high"

2. Cache Check
   ├─ Generate cache key: "adapter:search:{hash}"
   ├─ Check if cached
   │   ├─ Hit: Return cached results
   │   └─ Miss: Continue to adapter

3. Adapter Search
   ├─ Parse search query
   ├─ Build system-specific query
   ├─ Execute search API call
   ├─ Map results → universal Task models
   └─ Return List[Task]

4. Cache Update
   ├─ Store results with TTL
   └─ Update cache statistics

5. Return Results
   └─ Format and display to user
```

---

## Dependency Map

### External Dependencies

```
Core Dependencies:
├── pydantic >= 2.0        # Data validation and models
├── httpx >= 0.25.0        # Async HTTP client
├── python-dotenv >= 1.0   # Environment variable loading
├── typer >= 0.9.0         # CLI framework
├── rich >= 13.0.0         # Terminal formatting
├── gql[httpx] >= 3.0.0    # GraphQL client (Linear)
└── typing-extensions >= 4.8.0

Adapter-Specific:
├── jira >= 3.5.0          # JIRA adapter
├── PyGithub >= 2.1.0      # GitHub adapter
└── ai-trackdown-pytools >= 1.5.0  # AI-Trackdown adapter

Development:
├── pytest >= 7.4.0
├── pytest-asyncio >= 0.21.0
├── pytest-cov >= 4.1.0
├── black >= 23.0.0
├── ruff >= 0.1.0
├── mypy >= 1.5.0
├── pre-commit >= 3.5.0
└── bump2version >= 1.0.1
```

### Internal Dependencies

```
mcp_ticketer/
├── __init__.py
├── __version__.py
│
├── core/  (No internal dependencies - foundation)
│   ├── models.py
│   ├── adapter.py (depends on: models)
│   ├── config.py
│   ├── registry.py (depends on: adapter, models)
│   ├── http_client.py
│   └── mappers.py (depends on: models)
│
├── adapters/ (depends on: core)
│   ├── aitrackdown.py (depends on: core.adapter, core.models)
│   ├── linear.py (depends on: core.adapter, core.models, core.http_client)
│   ├── jira.py (depends on: core.adapter, core.models)
│   └── github.py (depends on: core.adapter, core.models)
│
├── cache/ (depends on: nothing - standalone utility)
│   └── memory.py
│
├── cli/ (depends on: core, adapters, cache)
│   ├── main.py (depends on: core.registry, core.models, adapters)
│   ├── utils.py (depends on: core.models)
│   └── queue_commands.py (depends on: queue)
│
├── mcp/ (depends on: core, adapters)
│   └── server.py (depends on: core.adapter, core.models)
│
└── queue/ (depends on: core, adapters)
    ├── manager.py (depends on: core.adapter, core.models)
    ├── queue.py
    ├── worker.py (depends on: manager, core.adapter)
    └── run_worker.py (depends on: worker, manager)
```

---

## Extension Points

### Adding a New Adapter

**Required Steps**:

1. **Create Adapter Class** (`src/mcp_ticketer/adapters/new_adapter.py`):
   ```python
   from ..core.adapter import BaseAdapter
   from ..core.models import Task, Comment, TicketState

   class NewAdapter(BaseAdapter[Task]):
       def __init__(self, config: Dict[str, Any]) -> None:
           super().__init__(config)
           # Initialize client

       def _get_state_mapping(self) -> Dict[TicketState, str]:
           return {...}  # Map states

       # Implement all abstract methods
       async def create(self, ticket: Task) -> Task: ...
       async def read(self, ticket_id: str) -> Optional[Task]: ...
       # ... etc
   ```

2. **Register Adapter** (`src/mcp_ticketer/adapters/__init__.py`):
   ```python
   from .new_adapter import NewAdapter
   from ..core.registry import AdapterRegistry

   AdapterRegistry.register("new_adapter", NewAdapter)
   ```

3. **Add CLI Support** (`src/mcp_ticketer/cli/main.py`):
   ```python
   class AdapterType(str, Enum):
       # ... existing
       NEW_ADAPTER = "new_adapter"

   # Add init options for new adapter
   ```

4. **Create Tests** (`tests/adapters/test_new_adapter.py`):
   ```python
   import pytest
   from mcp_ticketer.adapters.new_adapter import NewAdapter

   @pytest.mark.asyncio
   async def test_create_ticket(adapter):
       # Test implementation
       pass
   ```

### Adding Custom Fields to Models

**Extend BaseTicket without breaking compatibility**:

```python
# src/mcp_ticketer/core/models.py

class ExtendedTask(Task):
    """Extended task with custom fields."""

    # New fields must be Optional to maintain compatibility
    story_points: Optional[int] = Field(None, description="Story points")
    sprint_id: Optional[str] = Field(None, description="Sprint ID")

    # Computed properties
    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.due_date:
            return False
        return datetime.now() > self.due_date
```

### Adding Custom CLI Commands

**Extend CLI with new commands**:

```python
# src/mcp_ticketer/cli/custom_commands.py

import typer
from .main import app

@app.command()
def custom_command(
    param: str = typer.Option(..., help="Parameter"),
) -> None:
    """Custom command description."""
    # Implementation
    pass
```

### Adding Custom MCP Methods

**Extend MCP server**:

```python
# src/mcp_ticketer/mcp/extensions.py

from .server import MCPTicketServer

class ExtendedMCPServer(MCPTicketServer):
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        method = request.get("method")

        if method.startswith("custom/"):
            return await self._handle_custom_method(request)

        return await super().handle_request(request)

    async def _handle_custom_method(self, request: Dict[str, Any]) -> Dict[str, Any]:
        # Custom logic
        pass
```

---

## Architecture Diagrams

### Component Interaction

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│     CLI     │     │ MCP Server  │     │  Web API    │
│   (Typer)   │     │ (JSON-RPC)  │     │  (Future)   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                ┌──────────▼──────────┐
                │   Core Engine       │
                │  ┌───────────────┐  │
                │  │  Registry     │  │
                │  │  (Factory)    │  │
                │  └────────┬──────┘  │
                │           │         │
                │  ┌────────▼──────┐  │
                │  │  BaseAdapter  │  │
                │  │  (Interface)  │  │
                │  └────────┬──────┘  │
                └───────────┼─────────┘
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
┌──────▼──────┐  ┌─────────▼────────┐  ┌───────▼────────┐
│AITrackdown  │  │    Linear        │  │     JIRA       │
│  Adapter    │  │    Adapter       │  │    Adapter     │
└──────┬──────┘  └─────────┬────────┘  └───────┬────────┘
       │                    │                    │
┌──────▼──────┐  ┌─────────▼────────┐  ┌───────▼────────┐
│ File System │  │  Linear GraphQL  │  │  JIRA REST API │
│    (JSON)   │  │      API         │  │                │
└─────────────┘  └──────────────────┘  └────────────────┘
```

### Data Model Hierarchy

```
BaseModel (Pydantic)
    │
    ├─── BaseTicket (abstract base)
    │       ├── id: Optional[str]
    │       ├── title: str
    │       ├── description: Optional[str]
    │       ├── state: TicketState
    │       ├── priority: Priority
    │       ├── tags: List[str]
    │       ├── created_at: Optional[datetime]
    │       ├── updated_at: Optional[datetime]
    │       └── metadata: Dict[str, Any]
    │       │
    │       ├─── Epic (high-level container)
    │       │       └── child_issues: List[str]
    │       │
    │       └─── Task (work item)
    │               ├── parent_issue: Optional[str]
    │               ├── parent_epic: Optional[str]
    │               ├── assignee: Optional[str]
    │               ├── estimated_hours: Optional[float]
    │               └── actual_hours: Optional[float]
    │
    ├─── Comment
    │       ├── id: Optional[str]
    │       ├── ticket_id: str
    │       ├── author: Optional[str]
    │       ├── content: str
    │       ├── created_at: Optional[datetime]
    │       └── metadata: Dict[str, Any]
    │
    └─── SearchQuery
            ├── query: Optional[str]
            ├── state: Optional[TicketState]
            ├── priority: Optional[Priority]
            ├── tags: Optional[List[str]]
            ├── assignee: Optional[str]
            ├── limit: int = 10
            └── offset: int = 0
```

---

## Performance Considerations

### Caching Strategy

- **Adapter reads**: 5-minute TTL
- **List operations**: 1-minute TTL
- **Search results**: 30-second TTL
- **Metadata**: 10-minute TTL

### Async Operations

- All I/O operations use `async/await`
- Connection pooling for HTTP clients
- Batch operations supported where possible
- Concurrent operations with `asyncio.gather()`

### Memory Management

- Cache automatic cleanup on expiration
- Queue job cleanup after completion
- Adapter connection pooling
- Lazy loading of adapter instances

---

## AI Agent Integration Patterns

### MCP Protocol Implementation

**Server Architecture**:
```python
class MCPTicketServer:
    """JSON-RPC server over stdio."""

    async def handle_request(request: Dict) -> Dict:
        """Route JSON-RPC methods to handlers."""
        # Methods: initialize, ticket/*, tools/*, etc.
```

**Available MCP Methods**:
- `initialize` - Server initialization
- `ticket/create` - Create new ticket
- `ticket/read` - Read ticket by ID
- `ticket/update` - Update ticket fields
- `ticket/delete` - Delete ticket
- `ticket/list` - List tickets with filters
- `ticket/search` - Search tickets
- `ticket/transition` - Change ticket state
- `ticket/comment` - Add comment
- `ticket/status` - Check queue job status
- `ticket/create_pr` - Create GitHub PR linked to ticket
- `ticket/link_pr` - Link existing PR to ticket
- `tools/list` - List available tools
- `tools/call` - Execute tool

### Type Safety Features

**Pydantic Models**:
```python
class Task(BaseTicket):
    """Type-safe task model."""
    ticket_type: str = Field(default="task", frozen=True)
    assignee: Optional[str] = Field(None, description="Assigned user")

    # Validation happens automatically
    # Type hints enable IDE/agent autocomplete
```

**Generic Adapters**:
```python
class BaseAdapter(ABC, Generic[T]):
    """Generic adapter supporting Epic or Task."""
    # T bound to BaseTicket enables type-safe operations
```

### Agent-Friendly Error Handling

**Specific Exceptions**:
```python
from ..core.exceptions import (
    AdapterError,           # Base adapter error
    AuthenticationError,    # Auth failures
    RateLimitError,        # API rate limits
    ValidationError,       # Data validation
    NetworkError,          # Network issues
)
```

**Error Context**:
```python
raise AdapterError(
    message="Failed to create ticket",
    adapter_name=self.__class__.__name__,
    context={"ticket_id": ticket_id, "error": str(e)}
)
```

### CLI Agent Patterns

**Typer Commands**:
```python
@app.command()
def create(
    title: str = typer.Argument(..., help="Ticket title"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    priority: Optional[str] = typer.Option("medium", "--priority", "-p"),
) -> None:
    """Create a new ticket."""
    # Rich output for human-readable results
    console.print(table)
```

**Rich Output**:
- Colored text for status indicators
- Tables for structured data
- Progress bars for long operations
- Formatted JSON for debugging

## Performance Optimization Patterns

### Caching Strategy

**Memory Cache Implementation**:
```python
class MemoryCache:
    """TTL-based in-memory cache."""
    _cache: Dict[str, CacheEntry] = {}

    async def get(key: str) -> Optional[Any]:
        """Get with expiration check."""

    async def set(key: str, value: Any, ttl: int) -> None:
        """Set with TTL."""
```

**Cache Decorator Usage**:
```python
@cache_decorator(ttl=300, key_prefix="linear")
async def read(self, ticket_id: str) -> Optional[Task]:
    """Cached read with 5-minute TTL."""
```

**TTL Guidelines**:
- Reads: 5 minutes (300s)
- Lists: 1 minute (60s)
- Searches: 30 seconds
- Metadata: 10 minutes (600s)

### Async Patterns

**Concurrent Operations**:
```python
# Batch operations with asyncio.gather
tasks = [adapter.create(ticket) for ticket in batch]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Connection Pooling**:
```python
# httpx client with connection pool
client = httpx.AsyncClient(
    limits=httpx.Limits(max_connections=20),
    timeout=httpx.Timeout(30.0)
)
```

### Queue System

**Async Job Processing**:
```python
class QueueManager:
    """Manage async job queue."""

    async def enqueue(operation: str, params: Dict) -> str:
        """Add job to queue, return queue_id."""

    async def get_status(queue_id: str) -> Dict:
        """Check job status."""
```

**Job States**:
- `pending` - Waiting in queue
- `processing` - Currently executing
- `completed` - Successfully finished
- `failed` - Execution error
- `cancelled` - User cancelled

## Testing Patterns

### Test Organization

**Pytest Structure**:
```
tests/
├── unit/               # Fast, isolated tests
│   ├── test_models.py
│   ├── test_adapter.py
│   └── test_registry.py
├── integration/        # External API tests (mocked)
│   ├── test_linear_integration.py
│   └── test_jira_integration.py
└── e2e/               # End-to-end workflows
    └── test_ticket_lifecycle.py
```

**Test Markers**:
```python
@pytest.mark.unit          # Fast unit tests
@pytest.mark.integration   # Integration tests
@pytest.mark.slow          # Tests > 1 second
@pytest.mark.adapter       # Adapter-specific
```

### Fixture Patterns

**Adapter Fixtures**:
```python
@pytest.fixture
def adapter():
    """Provide configured adapter."""
    config = {"key": "value"}
    return Adapter(config)

@pytest.mark.asyncio
async def test_create(adapter):
    """Test ticket creation."""
    result = await adapter.create(task)
    assert result.id is not None
```

### Coverage Requirements

**Minimum Coverage**:
- Core modules: 95%
- Adapters: 90%
- CLI: 70%
- Overall: 80%

**Measured by**:
```bash
pytest --cov=mcp_ticketer --cov-report=html
# Opens htmlcov/index.html
```

## Documentation Patterns

### Docstring Standard

**Google Style**:
```python
def method(param: str, optional: Optional[int] = None) -> Result:
    """One-line summary.

    Detailed description explaining what the method does,
    edge cases, and important behavior.

    Args:
        param: Description of param
        optional: Description of optional parameter

    Returns:
        Description of return value

    Raises:
        ValueError: When param is invalid
        AdapterError: When operation fails

    Example:
        >>> result = method("value", optional=42)
        >>> print(result)
    """
```

### Type Hint Patterns

**Comprehensive Typing**:
```python
from typing import Optional, List, Dict, Any, TypeVar, Generic

async def search(
    query: SearchQuery,
    limit: int = 10,
    offset: int = 0
) -> List[Task]:
    """Fully typed async method."""
```

## Configuration Patterns

### Environment Variables

**Supported Variables**:
```bash
MCP_TICKETER_ADAPTER=aitrackdown     # Default adapter
MCP_TICKETER_BASE_PATH=/path         # Base path for files
MCP_TICKETER_DEBUG=1                 # Enable debug mode
MCP_TICKETER_LOG_LEVEL=DEBUG         # Logging level
LINEAR_API_KEY=xxx                   # Linear API key
LINEAR_TEAM_ID=yyy                   # Linear team ID
GITHUB_TOKEN=xxx                     # GitHub token
JIRA_SERVER=xxx                      # JIRA server URL
JIRA_EMAIL=xxx                       # JIRA email
JIRA_API_TOKEN=xxx                   # JIRA API token
```

### Configuration Files

**User Config**: `~/.mcp-ticketer/config.json`
```json
{
  "default_adapter": "aitrackdown",
  "adapters": {
    "aitrackdown": {
      "base_path": ".aitrackdown"
    },
    "linear": {
      "team_id": "xxx",
      "api_key": "yyy"
    }
  }
}
```

## Deployment Patterns

### Package Distribution

**Build Process**:
```bash
# 1. Clean previous builds
make clean

# 2. Run quality checks
make quality

# 3. Build distributions
make build
# Creates: dist/*.whl, dist/*.tar.gz

# 4. Publish to PyPI
make publish
# Or: make publish-test for TestPyPI
```

### Version Management

**Version Sources**:
- `src/mcp_ticketer/__version__.py` - Source of truth
- `pyproject.toml` - References `__version__.__version__`
- Git tags - `v0.X.Y` format

**Version Bumping**:
```bash
make version-patch  # 0.1.X
make version-minor  # 0.X.0
make version-major  # X.0.0
```

## Security Patterns

### Secret Management

**Never Commit**:
- API keys
- Authentication tokens
- Passwords
- Private keys

**Use Instead**:
- Environment variables
- Config files in `~/.mcp-ticketer/`
- `.env` files (gitignored)

**Pre-commit Checks**:
```yaml
# .pre-commit-config.yaml
- id: detect-private-key
- id: detect-aws-credentials
```

### API Security

**Rate Limiting**:
```python
# Respect API rate limits
await asyncio.sleep(rate_limit_delay)

# Handle 429 responses
if response.status_code == 429:
    retry_after = response.headers.get("Retry-After")
    raise RateLimitError(f"Retry after {retry_after}s")
```

**Authentication**:
```python
# Use secure credential storage
api_key = os.getenv("LINEAR_API_KEY")
if not api_key:
    raise AuthenticationError("API key not configured")
```

---

**END OF CODE_STRUCTURE.MD**

For implementation details, see `docs/DEVELOPER_GUIDE.md`.
For usage instructions, see `CLAUDE.md` and `QUICK_START.md`.
For AI agent optimization, see `.claude-mpm/memories/agentic_coder_optimizer_memories.md`.
