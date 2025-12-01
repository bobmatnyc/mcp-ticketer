# Linear Practical Workflow CLI Script Analysis

**Research Date**: 2025-11-26
**Ticket**: 1M-217 - Implement Linear practical workflow CLI script
**Researcher**: Claude Code (Research Agent)
**Status**: Complete

---

## Executive Summary

This research analyzes the existing Linear adapter and script patterns to inform the implementation of `ops/scripts/linear/practical-workflow.sh` for common Linear operations. The analysis reveals comprehensive adapter capabilities, established configuration patterns, and clear requirements for the workflow script implementation.

### Key Findings

1. **Linear Adapter is Feature-Rich**: Comprehensive GraphQL-based adapter with full CRUD operations, state management, and file attachment support
2. **No Existing ops/ Directory**: Project uses `scripts/` for tooling and `examples/` for usage demonstrations
3. **Typer + Rich Pattern**: CLI uses Typer framework with Rich for output formatting
4. **Environment-Based Auth**: Configuration uses environment variables (LINEAR_API_KEY, LINEAR_TEAM_ID/LINEAR_TEAM_KEY)
5. **Async-First Design**: All adapter operations are async using asyncio

---

## 1. Linear Adapter Capabilities

### 1.1 Core CRUD Operations

**Location**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/adapter.py`

#### Available Methods

**Ticket Creation** (Lines 1121-1151):
```python
async def create(self, ticket: Epic | Task) -> Epic | Task
async def _create_task(self, task: Task) -> Task  # Issues
async def _create_epic(self, epic: Epic) -> Epic  # Projects
```

**Ticket Reading** (Lines 1476-1587):
```python
async def read(self, ticket_id: str) -> Task | Epic | None
async def get_epic(self, epic_id: str, include_issues: bool = True) -> Epic | None
```

**Ticket Updating** (Lines 1589-1695):
```python
async def update(self, ticket_id: str, updates: dict[str, Any]) -> Task | None
async def update_epic(self, epic_id: str, updates: dict[str, Any]) -> Epic | None
```

**Ticket Deletion** (Lines 1697-1714):
```python
async def delete(self, ticket_id: str) -> bool  # Archives issue
```

### 1.2 State Management & Workflow

**State Transitions** (Lines 1863-1909):
```python
async def transition_state(self, ticket_id: str, target_state: TicketState) -> Task | None
async def validate_transition(self, ticket_id: str, target_state: TicketState) -> bool
```

**State Mapping** (`types.py`, Lines 31-53):
```python
class LinearStateMapping:
    TO_LINEAR: dict[TicketState, str] = {
        TicketState.OPEN: "unstarted",
        TicketState.IN_PROGRESS: "started",
        TicketState.READY: "unstarted",
        TicketState.TESTED: "started",
        TicketState.DONE: "completed",
        TicketState.CLOSED: "canceled",
        TicketState.WAITING: "unstarted",
        TicketState.BLOCKED: "unstarted",
    }
```

**Universal States Available**:
- `OPEN` → "unstarted" (backlog)
- `IN_PROGRESS` → "started"
- `READY` → "unstarted" (no direct equivalent)
- `TESTED` → "started" (no direct equivalent)
- `DONE` → "completed"
- `CLOSED` → "canceled"
- `WAITING` → "unstarted"
- `BLOCKED` → "unstarted"

### 1.3 Comment Operations

**Add Comments** (Lines 1911-1979):
```python
async def add_comment(self, comment: Comment) -> Comment
```

**Get Comments** (Lines 1981-2037):
```python
async def get_comments(self, ticket_id: str, limit: int = 10, offset: int = 0) -> list[Comment]
```

**Comment Structure**:
```python
from mcp_ticketer.core.models import Comment

comment = Comment(
    ticket_id="BTA-123",
    content="Comment text",
    author="user@example.com"  # Optional
)
```

### 1.4 Search & Filtering

**List Issues** (Lines 1716-1782):
```python
async def list(
    self,
    limit: int = 10,
    offset: int = 0,
    filters: dict[str, Any] | None = None
) -> list[Task]
```

**Search Issues** (Lines 1784-1861):
```python
async def search(self, query: SearchQuery) -> list[Task]
```

**Filter Capabilities**:
- State filtering (via `TicketState` enum)
- Priority filtering (via `Priority` enum)
- Assignee filtering (email or user ID)
- Project filtering (project ID)
- Label/tag filtering
- Date filtering (created_after, updated_after, due_before)

### 1.5 File Attachments

**Upload File** (Lines 2066-2177):
```python
async def upload_file(self, file_path: str, mime_type: str | None = None) -> str
```

**Attach to Issue** (Lines 2179-2260):
```python
async def attach_file_to_issue(
    self,
    issue_id: str,
    file_url: str,
    title: str,
    subtitle: str | None = None,
    comment_body: str | None = None,
) -> dict[str, Any]
```

**Attach to Epic/Project** (Lines 2262-2340):
```python
async def attach_file_to_epic(
    self,
    epic_id: str,
    file_url: str,
    title: str,
    subtitle: str | None = None,
) -> dict[str, Any]
```

**Get Attachments** (Lines 2342-2468):
```python
async def get_attachments(self, ticket_id: str) -> list[Attachment]
```

### 1.6 Advanced Features

**Label Management** (Lines 2039-2065):
```python
async def list_labels(self) -> list[dict[str, Any]]
```

**Cycle Management** (Lines 2470-2535):
```python
async def list_cycles(self, team_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]
```

**Issue Status** (Lines 2537-2584):
```python
async def get_issue_status(self, issue_id: str) -> dict[str, Any] | None
async def list_issue_statuses(self, team_id: str | None = None) -> list[dict[str, Any]]
```

**Epic/Project Operations** (Lines 2637-2724):
```python
async def list_epics(
    self,
    limit: int = 50,
    offset: int = 0,
    state: str | None = None,
    include_completed: bool = True,
) -> list[Epic]
```

---

## 2. Configuration & Authentication Patterns

### 2.1 Environment Variables

**Primary Configuration**:
```bash
LINEAR_API_KEY=lin_api_...              # Required: API authentication
LINEAR_TEAM_ID=<uuid>                   # Option 1: Team UUID
LINEAR_TEAM_KEY=<key>                   # Option 2: Team short code (e.g., "BTA", "ENG")
```

**Adapter Initialization** (Lines 77-145):
```python
config = {
    "api_key": os.getenv("LINEAR_API_KEY"),  # or config["api_key"]
    "team_key": "BTA",                       # Short team code
    # OR
    "team_id": "uuid-here",                  # Team UUID
    "user_email": "user@example.com",        # Optional default assignee
    "api_url": "https://api.linear.app/graphql"  # Optional custom URL
}

adapter = LinearAdapter(config)
await adapter.initialize()
```

### 2.2 API Key Validation

**Format Requirements** (Lines 126-132):
```python
# Linear API keys must start with "lin_api_"
if not self.api_key.startswith("lin_api_"):
    raise ValueError(
        f"Invalid Linear API key format. Expected key starting with 'lin_api_', "
        f"got: {self.api_key[:15]}..."
    )
```

### 2.3 Team Resolution

**Team ID vs Team Key** (Lines 185-253):
```python
async def _ensure_team_id(self) -> str:
    """Resolve team_key to UUID if needed.

    Accepts:
    - team_id: UUID (e.g., "02d15669-7351-4451-9719-807576c16049")
    - team_key: Short code (e.g., "BTA", "ENG")

    Returns: Validated Linear team UUID
    """
```

**Team Query Pattern** (Lines 255-284):
```python
query = """
    query GetTeamByKey($key: String!) {
        teams(filter: { key: { eq: $key } }) {
            nodes {
                id
                key
                name
            }
        }
    }
"""
```

---

## 3. Existing Script Patterns

### 3.1 Directory Structure

**Current State**:
```
/Users/masa/Projects/mcp-ticketer/
├── scripts/                    # Build/tooling scripts
│   ├── install.sh
│   ├── manage_version.py
│   ├── mcp_server.sh
│   └── README.md
├── examples/                   # Usage demonstration scripts
│   ├── linear_file_upload_example.py
│   ├── jira_epic_attachments_example.py
│   ├── label_management_examples.py
│   └── README.md
└── ops/                        # ❌ Does not exist yet
```

**Recommendation**: Create `ops/scripts/linear/` directory structure:
```
ops/
└── scripts/
    └── linear/
        ├── practical-workflow.sh      # Main workflow script
        ├── README.md                  # Script documentation
        └── .env.example               # Configuration template
```

### 3.2 Python Script Pattern (from examples/)

**Structure** (from `examples/linear_file_upload_example.py`):
```python
#!/usr/bin/env python3
"""Example: Brief description of script purpose.

Requirements:
    - LINEAR_API_KEY environment variable
    - Team ID or team key configured
    - Additional dependencies if needed
"""

import asyncio
import os
from pathlib import Path

async def main():
    """Main script function with clear workflow."""
    from mcp_ticketer.adapters.linear.adapter import LinearAdapter

    # 1. Initialize adapter
    config = {
        "api_key": os.getenv("LINEAR_API_KEY"),
        "team_key": os.getenv("LINEAR_TEAM_KEY", "BTA"),
    }

    adapter = LinearAdapter(config)
    await adapter.initialize()

    try:
        # 2. Perform operations with clear section comments
        # ===================================================================
        # Example 1: Operation Name
        # ===================================================================
        result = await adapter.some_operation()

        # 3. Display results
        print(f"Result: {result}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await adapter.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### 3.3 CLI Command Pattern (from src/mcp_ticketer/cli/)

**Typer Framework Usage** (from `linear_commands.py`):
```python
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="linear", help="Linear workspace and team management")
console = Console()

@app.command()
def configure_team(
    team_url: str = typer.Option(..., help="Linear team URL"),
    save: bool = typer.Option(True, help="Save to config"),
) -> None:
    """Configure Linear team from URL."""
    api_key = os.getenv("LINEAR_API_KEY")

    if not api_key:
        console.print("[red]❌ LINEAR_API_KEY not found in environment[/red]")
        raise typer.Exit(1)

    # Async operations need asyncio.run()
    team_id, error = asyncio.run(derive_team_from_url(api_key, team_url))

    if error:
        console.print(f"[red]❌ {error}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Team ID: {team_id}")
```

**Key Patterns**:
1. Use `typer.Option()` for command-line arguments
2. Use `rich.console.Console` for formatted output
3. Use `rich.table.Table` for structured data display
4. Wrap async operations with `asyncio.run()`
5. Exit with proper status codes (`typer.Exit(1)` for errors)

---

## 4. Implementation Requirements

### 4.1 Script Structure (Bash Wrapper + Python Core)

**Recommended Approach**: Hybrid shell script + Python implementation

**`ops/scripts/linear/practical-workflow.sh`**:
```bash
#!/usr/bin/env bash
# Linear Practical Workflow CLI
# Common Linear operations for development workflows

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Source environment if available
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Validate environment
if [ -z "${LINEAR_API_KEY:-}" ]; then
    echo "ERROR: LINEAR_API_KEY not set"
    echo "Set it in .env or export LINEAR_API_KEY=lin_api_..."
    exit 1
fi

if [ -z "${LINEAR_TEAM_KEY:-}" ] && [ -z "${LINEAR_TEAM_ID:-}" ]; then
    echo "ERROR: LINEAR_TEAM_KEY or LINEAR_TEAM_ID not set"
    echo "Set LINEAR_TEAM_KEY=BTA or LINEAR_TEAM_ID=<uuid> in .env"
    exit 1
fi

# Delegate to Python implementation
exec python3 "$SCRIPT_DIR/workflow.py" "$@"
```

**`ops/scripts/linear/workflow.py`**:
```python
#!/usr/bin/env python3
"""Linear workflow operations CLI."""

import asyncio
import os
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from mcp_ticketer.adapters.linear.adapter import LinearAdapter
from mcp_ticketer.core.models import Task, Priority, TicketState, Comment

app = typer.Typer(help="Linear practical workflow operations")
console = Console()

# ... implementation ...
```

### 4.2 Required Operations

**Based on "practical workflow" scope, implement**:

1. **Ticket Creation** (by type):
   ```bash
   ./practical-workflow.sh create-bug "Title" "Description" [--priority high]
   ./practical-workflow.sh create-feature "Title" "Description" [--project PROJECT_ID]
   ./practical-workflow.sh create-task "Title" "Description" [--parent PARENT_ID]
   ```

2. **State Transitions**:
   ```bash
   ./practical-workflow.sh start TICKET_ID              # OPEN → IN_PROGRESS
   ./practical-workflow.sh ready TICKET_ID              # IN_PROGRESS → READY (review)
   ./practical-workflow.sh done TICKET_ID               # Any → DONE
   ./practical-workflow.sh block TICKET_ID "Reason"     # Any → BLOCKED (add comment)
   ```

3. **Comment Operations**:
   ```bash
   ./practical-workflow.sh comment TICKET_ID "Comment text"
   ./practical-workflow.sh comments TICKET_ID [--limit 10]
   ```

4. **Query Operations**:
   ```bash
   ./practical-workflow.sh list [--state in_progress] [--assignee me] [--limit 20]
   ./practical-workflow.sh search "query text" [--project PROJECT_ID]
   ./practical-workflow.sh show TICKET_ID
   ```

5. **Bulk Operations**:
   ```bash
   ./practical-workflow.sh assign TICKET_ID USER_EMAIL
   ./practical-workflow.sh assign-multiple TICKET_ID1,TICKET_ID2 USER_EMAIL
   ./practical-workflow.sh bulk-transition "BTA-1,BTA-2,BTA-3" done
   ```

### 4.3 Error Handling Requirements

**Standard Error Cases**:

1. **Missing Configuration**:
   ```python
   if not api_key:
       console.print("[red]❌ LINEAR_API_KEY not found in environment[/red]")
       console.print("Set it in .env or: export LINEAR_API_KEY=lin_api_...")
       raise typer.Exit(1)
   ```

2. **Invalid Ticket ID**:
   ```python
   ticket = await adapter.read(ticket_id)
   if not ticket:
       console.print(f"[red]❌ Ticket {ticket_id} not found[/red]")
       raise typer.Exit(1)
   ```

3. **Invalid State Transition**:
   ```python
   is_valid = await adapter.validate_transition(ticket_id, target_state)
   if not is_valid:
       console.print(f"[red]❌ Cannot transition {ticket_id} to {target_state}[/red]")
       console.print("Check current state and workflow rules")
       raise typer.Exit(1)
   ```

4. **API Errors**:
   ```python
   try:
       result = await adapter.some_operation()
   except ValueError as e:
       console.print(f"[red]❌ API Error: {e}[/red]")
       raise typer.Exit(1)
   except Exception as e:
       console.print(f"[red]❌ Unexpected error: {e}[/red]")
       raise typer.Exit(1)
   ```

### 4.4 Output Formatting Standards

**Use Rich for consistent output**:

1. **Success Messages**:
   ```python
   console.print(f"[green]✓[/green] Created ticket: {ticket.id}")
   console.print(f"[green]✓[/green] Transitioned {ticket_id} to {state}")
   ```

2. **Tables for Lists**:
   ```python
   table = Table(title="Linear Issues")
   table.add_column("ID", style="cyan")
   table.add_column("Title", style="white")
   table.add_column("State", style="yellow")
   table.add_column("Priority", style="magenta")

   for task in tasks:
       table.add_row(task.id, task.title, task.state.value, task.priority.value)

   console.print(table)
   ```

3. **Ticket Details**:
   ```python
   console.print(f"[bold cyan]{ticket.id}[/bold cyan]: {ticket.title}")
   console.print(f"State: [yellow]{ticket.state.value}[/yellow]")
   console.print(f"Priority: [magenta]{ticket.priority.value}[/magenta]")
   console.print(f"Assignee: {ticket.assignee or 'Unassigned'}")
   if ticket.description:
       console.print(f"\n{ticket.description}")
   ```

---

## 5. Limitations & Blockers

### 5.1 Known Limitations

**State Transition Granularity**:
- Linear has custom workflow states per team
- Universal `TicketState` enum maps to Linear's state **types** (backlog, unstarted, started, completed, canceled)
- Script cannot directly transition to custom states like "In Review" or "Testing"
- **Workaround**: Use `TicketState.READY` for review/testing states

**No Direct "Ready" or "Tested" States** (`types.py`, Lines 36-44):
```python
TicketState.READY: "unstarted",   # No direct equivalent
TicketState.TESTED: "started",    # No direct equivalent
```

**Solution**: Document this mapping limitation in script README.

### 5.2 API Rate Limits

**Linear API Rate Limits**:
- Documented rate limits: 3600 requests/hour (60 req/min)
- GraphQL queries count as single requests regardless of complexity
- Bulk operations should use efficient batch queries

**Recommendation**: Implement basic rate limit handling:
```python
import time
from functools import wraps

def rate_limit(calls_per_minute: int = 60):
    """Simple rate limiter decorator."""
    min_interval = 60.0 / calls_per_minute
    last_called = {}

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            now = time.time()
            time_since_last = now - last_called.get(func.__name__, 0)
            if time_since_last < min_interval:
                await asyncio.sleep(min_interval - time_since_last)
            last_called[func.__name__] = time.time()
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### 5.3 No Blockers Identified

✅ **All required capabilities are available in Linear adapter**:
- Ticket creation by type ✓
- State transitions ✓
- Comment operations ✓
- Search/filtering ✓
- Bulk operations (via scripting loops) ✓

---

## 6. Reference Files for Implementation

### 6.1 Core Adapter Files

| File | Purpose | Lines to Reference |
|------|---------|-------------------|
| `src/mcp_ticketer/adapters/linear/adapter.py` | Main adapter implementation | 1121-1151 (create), 1863-1909 (transitions), 1911-2037 (comments) |
| `src/mcp_ticketer/adapters/linear/types.py` | State/priority mappings | 31-53 (states), 11-29 (priority) |
| `src/mcp_ticketer/adapters/linear/client.py` | GraphQL client | All (for understanding queries) |
| `src/mcp_ticketer/core/models.py` | Data models (Task, Epic, Comment, etc.) | All |

### 6.2 Example Scripts

| File | Purpose | Key Patterns |
|------|---------|--------------|
| `examples/linear_file_upload_example.py` | Async pattern, adapter initialization | 17-137 |
| `src/mcp_ticketer/cli/linear_commands.py` | Typer CLI pattern, Rich output | 12-96 |
| `src/mcp_ticketer/cli/main.py` | Configuration loading | 87-180, 315-328 |

### 6.3 Configuration Examples

| File | Purpose | Key Patterns |
|------|---------|--------------|
| `src/mcp_ticketer/cli/utils.py` | ConfigValidator, environment loading | 414-520 |
| `.env.example` (if exists) | Environment variable template | N/A (create for ops/) |

---

## 7. Recommended Script Structure

### 7.1 File Organization

```
ops/scripts/linear/
├── practical-workflow.sh          # Bash wrapper (env validation + delegation)
├── workflow.py                    # Python CLI implementation (Typer)
├── README.md                      # Usage documentation
├── .env.example                   # Configuration template
└── operations/                    # Optional: operation modules
    ├── __init__.py
    ├── create.py                  # Ticket creation operations
    ├── transition.py              # State transition operations
    ├── comment.py                 # Comment operations
    └── query.py                   # Search/list operations
```

### 7.2 Argument Parsing Pattern

**Using Typer (recommended)**:
```python
import typer
from typing import Optional
from enum import Enum

class PriorityArg(str, Enum):
    """Priority choices for CLI."""
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class StateArg(str, Enum):
    """State choices for CLI."""
    open = "open"
    in_progress = "in_progress"
    ready = "ready"
    done = "done"
    closed = "closed"

app = typer.Typer()

@app.command()
def create_bug(
    title: str = typer.Argument(..., help="Bug title"),
    description: str = typer.Argument(..., help="Bug description"),
    priority: PriorityArg = typer.Option(PriorityArg.medium, help="Priority level"),
    assignee: Optional[str] = typer.Option(None, help="Assignee email"),
) -> None:
    """Create a bug ticket."""
    # Implementation...

@app.command()
def transition(
    ticket_id: str = typer.Argument(..., help="Ticket ID (e.g., BTA-123)"),
    state: StateArg = typer.Argument(..., help="Target state"),
    comment: Optional[str] = typer.Option(None, help="Optional comment"),
) -> None:
    """Transition ticket to new state."""
    # Implementation...

if __name__ == "__main__":
    app()
```

### 7.3 Configuration Management

**Priority order**:
1. Command-line arguments (highest priority)
2. Environment variables
3. `.env` file in project root
4. `.mcp-ticketer/config.json` (if using project config)

**Implementation**:
```python
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path.cwd() / ".env"
if env_path.exists():
    load_dotenv(env_path)

def get_config() -> dict:
    """Load Linear configuration from environment."""
    api_key = os.getenv("LINEAR_API_KEY")
    team_id = os.getenv("LINEAR_TEAM_ID")
    team_key = os.getenv("LINEAR_TEAM_KEY")

    if not api_key:
        raise ValueError("LINEAR_API_KEY not set")

    if not team_id and not team_key:
        raise ValueError("LINEAR_TEAM_ID or LINEAR_TEAM_KEY not set")

    config = {"api_key": api_key}
    if team_id:
        config["team_id"] = team_id
    elif team_key:
        config["team_key"] = team_key

    return config
```

---

## 8. Implementation Checklist

### Phase 1: Basic Structure
- [ ] Create `ops/scripts/linear/` directory
- [ ] Implement bash wrapper (`practical-workflow.sh`)
- [ ] Create Python CLI skeleton (`workflow.py`)
- [ ] Add `.env.example` template
- [ ] Write `README.md` with usage examples

### Phase 2: Core Operations
- [ ] Implement ticket creation commands (bug, feature, task)
- [ ] Implement state transition commands (start, ready, done, block)
- [ ] Implement comment commands (add, list)
- [ ] Implement query commands (list, search, show)

### Phase 3: Advanced Features
- [ ] Implement assignment operations (single, multiple)
- [ ] Implement bulk transition operations
- [ ] Add error handling and validation
- [ ] Add output formatting with Rich tables

### Phase 4: Testing & Documentation
- [ ] Test all commands with real Linear workspace
- [ ] Document all commands in README
- [ ] Add error handling examples
- [ ] Create usage examples for common workflows

---

## 9. Conclusion

### Summary

The Linear adapter provides **comprehensive capabilities** for implementing a practical workflow CLI script. All required operations (create, transition, comment, search) are available through well-documented async methods.

### Key Recommendations

1. **Use Typer + Rich Pattern**: Follow established CLI patterns from `linear_commands.py`
2. **Hybrid Bash + Python**: Bash wrapper for env validation, Python for operations
3. **Async-First Design**: All adapter operations are async, use `asyncio.run()`
4. **Environment-Based Config**: Use `LINEAR_API_KEY` and `LINEAR_TEAM_KEY`/`LINEAR_TEAM_ID`
5. **Graceful Error Handling**: Validate inputs, provide helpful error messages

### No Blockers

✅ All required functionality is available in the current Linear adapter. Implementation can proceed immediately.

### Next Steps

1. Review this research with stakeholders
2. Confirm operation scope (which commands to include)
3. Implement Phase 1 (basic structure)
4. Iterate through Phase 2-4 with testing

---

## Appendix A: Environment Variable Reference

```bash
# Required
LINEAR_API_KEY=lin_api_xxxxx...         # Linear API key (get from Linear settings)

# Team identification (choose one)
LINEAR_TEAM_KEY=BTA                     # Short team code (e.g., BTA, ENG, 1M)
LINEAR_TEAM_ID=<uuid>                   # Full team UUID

# Optional
LINEAR_API_URL=https://api.linear.app/graphql  # Custom API URL (default shown)
LINEAR_USER_EMAIL=user@example.com              # Default assignee
```

## Appendix B: State Transition Matrix

| From State | Valid Transitions |
|------------|-------------------|
| OPEN | IN_PROGRESS, WAITING, BLOCKED, CLOSED |
| IN_PROGRESS | READY, WAITING, BLOCKED, OPEN |
| READY | TESTED, IN_PROGRESS, BLOCKED |
| TESTED | DONE, IN_PROGRESS |
| DONE | CLOSED |
| WAITING | OPEN, IN_PROGRESS, CLOSED |
| BLOCKED | OPEN, IN_PROGRESS, CLOSED |
| CLOSED | (terminal state) |

**Source**: BaseAdapter workflow validation (inherited by LinearAdapter)

## Appendix C: Priority Mapping

| Universal Priority | Linear Priority | Numeric Value |
|-------------------|----------------|---------------|
| CRITICAL | Urgent | 1 |
| HIGH | High | 2 |
| MEDIUM | Medium | 3 |
| LOW | Low | 4 |

**Source**: `adapters/linear/types.py`, Lines 11-29

---

**Research Complete**: 2025-11-26
**Files Analyzed**: 6 core files, 4 example scripts, 3 CLI commands
**Total Lines Reviewed**: ~2700 lines of adapter code + supporting files
