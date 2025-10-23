# CLAUDE.md - MCP Ticketer AI Agent Instructions

**Version**: 0.1.24
**Last Updated**: 2025-10-24
**Project**: MCP Ticketer - Universal Ticket Management Interface for AI Agents
**Optimized For**: Claude Code, Gemini CLI, Codex CLI, Auggie, and AI Agent Collaboration

---

## PRIORITY INDEX

### 🔴 CRITICAL - Read First
1. [Single-Path Principle](#-critical-single-path-principle)
2. [Core Architecture](#-critical-core-architecture)
3. [Quick Commands](#-critical-quick-commands)
4. [DO NOT](#-critical-do-not)

### 🟡 IMPORTANT - Core Operations
5. [Development Workflow](#-important-development-workflow)
6. [Testing Requirements](#-important-testing-requirements)
7. [Code Quality Standards](#-important-code-quality-standards)

### 🟢 STANDARD - Day-to-Day Operations
8. [Adapter Development](#-standard-adapter-development)
9. [Common Tasks](#-standard-common-tasks)
10. [Troubleshooting](#-standard-troubleshooting)

### ⚪ OPTIONAL - Advanced Topics
11. [Performance Optimization](#-optional-performance-optimization)
12. [Custom Extensions](#-optional-custom-extensions)
13. [AI Agent Integration](#-optional-ai-agent-integration)
14. [Memory System](#-optional-memory-system)

---

## 🔴 CRITICAL: Single-Path Principle

### THE ONE WAY TO DO ANYTHING

**This project enforces exactly ONE method for each operation. No alternatives, no exceptions.**

#### Essential Commands (THE ONLY WAYS)

```bash
# Setup & Installation
make install-dev          # THE way to set up development environment
make install-all          # THE way to install with all adapters

# Development
make dev                  # THE way to run the MCP server
make cli                  # THE way to run the CLI

# Testing
make test                 # THE way to run all tests
make test-unit            # THE way to run unit tests
make test-coverage        # THE way to check coverage

# Code Quality
make format               # THE way to format code
make lint-fix             # THE way to fix linting issues
make quality              # THE way to run all quality checks

# Building
make build                # THE way to build the package
make publish              # THE way to publish to PyPI

# Documentation
make docs                 # THE way to build docs
make docs-serve           # THE way to serve docs locally
```

**WHY**: Eliminates cognitive load, prevents mistakes, ensures consistency. When there's only ONE way, there's ZERO ambiguity.

---

## 🔴 CRITICAL: Core Architecture

### Project Structure

```
mcp-ticketer/
├── src/mcp_ticketer/          # Source code (THE ONLY source location)
│   ├── adapters/              # Ticket system adapters (extend here)
│   │   ├── aitrackdown.py    # Local file-based adapter
│   │   ├── linear.py         # Linear API adapter
│   │   ├── jira.py           # JIRA API adapter
│   │   └── github.py         # GitHub Issues adapter
│   ├── core/                  # Core abstractions (DO NOT modify lightly)
│   │   ├── models.py         # Universal ticket models
│   │   ├── adapter.py        # BaseAdapter interface
│   │   ├── config.py         # Configuration management
│   │   └── registry.py       # Adapter registry
│   ├── cli/                   # CLI interface
│   │   └── main.py           # Typer-based CLI
│   ├── mcp/                   # MCP server implementation
│   │   └── server.py         # JSON-RPC MCP server
│   ├── cache/                 # Caching layer
│   │   └── memory.py         # TTL-based memory cache
│   └── queue/                 # Async queue system
│       └── manager.py        # Queue manager
├── tests/                     # Tests (THE ONLY test location)
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── e2e/                  # End-to-end tests
├── docs/                      # Documentation
├── Makefile                   # THE command interface
├── pyproject.toml            # THE config file
└── CLAUDE.md                  # THIS FILE - your guide

### Universal Ticket Model

```
Epic (highest level)
├── Task (individual work items)
    └── Comment (discussions)

State Machine:
OPEN → IN_PROGRESS → READY → TESTED → DONE → CLOSED
  ↓         ↓          ↓
WAITING  BLOCKED    BLOCKED
```

### Tech Stack

- **Language**: Python 3.9+
- **CLI**: Typer + Rich
- **Data Validation**: Pydantic v2
- **MCP Protocol**: JSON-RPC
- **Async**: asyncio + httpx
- **Testing**: pytest + pytest-asyncio
- **Linting**: ruff + mypy
- **Formatting**: black + isort

---

## 🔴 CRITICAL: Quick Commands

### First Time Setup

```bash
# 1. Clone and navigate
cd /path/to/mcp-ticketer

# 2. Install dev environment (THE ONLY WAY)
make install-dev

# 3. Initialize adapter (choose one)
make init-aitrackdown              # Local file-based (no API keys needed)
make init-linear LINEAR_API_KEY=xxx LINEAR_TEAM_ID=yyy
make init-jira JIRA_SERVER=xxx JIRA_EMAIL=yyy JIRA_API_TOKEN=zzz
make init-github GITHUB_TOKEN=xxx GITHUB_REPO=owner/repo

# 4. Verify installation
make test-unit
make cli
```

### Daily Development Workflow

```bash
# 1. Pull latest
git pull origin main

# 2. Create feature branch
git checkout -b feature/your-feature-name

# 3. Make changes

# 4. Run quality checks (THE ONLY WAY)
make quality                       # Runs format + lint + test

# 5. Commit and push
git add .
git commit -m "feat: your feature description"
git push origin feature/your-feature-name

# 6. Create PR (THE ONLY WAY)
gh pr create --title "Your Feature" --body "Description"
```

---

## 🔴 CRITICAL: DO NOT

### Absolute Prohibitions

1. **DO NOT** create new command patterns - USE MAKEFILE ONLY
2. **DO NOT** modify `core/models.py` without discussing - breaking change
3. **DO NOT** modify `core/adapter.py` interface - breaks all adapters
4. **DO NOT** commit secrets or API keys - use environment variables
5. **DO NOT** use `pip install` directly - USE `make install-*`
6. **DO NOT** run tests with `pytest` directly - USE `make test*`
7. **DO NOT** format with `black` or `isort` directly - USE `make format`
8. **DO NOT** skip quality checks before committing - USE `make quality`
9. **DO NOT** create documentation outside `docs/` folder
10. **DO NOT** add dependencies without adding to `pyproject.toml`

### WHY These Rules Exist

- **Consistency**: One way = zero confusion
- **Quality**: Makefile enforces best practices
- **Compatibility**: Core interfaces ensure adapter compatibility
- **Security**: Prevents accidental secret commits
- **Maintainability**: Standardized processes scale

---

## 🟡 IMPORTANT: Development Workflow

### Adding a New Adapter

**Example: Adding a Slack Adapter**

```bash
# 1. Create adapter file
touch src/mcp_ticketer/adapters/slack.py

# 2. Implement BaseAdapter interface
# See docs/DEVELOPER_GUIDE.md for complete example

# 3. Register adapter
# Edit src/mcp_ticketer/adapters/__init__.py
# Add: AdapterRegistry.register("slack", SlackAdapter)

# 4. Add CLI support
# Edit src/mcp_ticketer/cli/main.py
# Add adapter enum and init options

# 5. Write tests
# Create tests/adapters/test_slack.py

# 6. Run quality checks
make quality

# 7. Build and test
make build
make init-slack SLACK_TOKEN=xxx SLACK_CHANNEL=yyy
make test-integration
```

### Modifying Core Models

**IF YOU MUST** (discouraged - requires careful consideration):

```python
# 1. Discuss with team FIRST
# 2. Ensure backward compatibility
# 3. Update ALL adapters
# 4. Update documentation
# 5. Add migration guide if breaking

# Example: Adding new field to Task
class Task(BaseTicket):
    # Existing fields...

    # NEW FIELD - must be Optional to maintain compatibility
    your_new_field: Optional[str] = Field(
        None,
        description="Clear description"
    )
```

### Creating Tests

```python
# tests/adapters/test_your_adapter.py
import pytest
from unittest.mock import AsyncMock
from mcp_ticketer.adapters.your_adapter import YourAdapter
from mcp_ticketer.core.models import Task, Priority, TicketState

@pytest.fixture
def adapter():
    config = {"key": "value"}
    return YourAdapter(config)

@pytest.mark.asyncio
async def test_create_ticket(adapter):
    """Test ticket creation."""
    task = Task(
        title="Test",
        priority=Priority.HIGH
    )

    result = await adapter.create(task)

    assert result.id is not None
    assert result.title == "Test"
```

**Run tests**: `make test-unit`

---

## 🟡 IMPORTANT: Testing Requirements

### Test Coverage Requirements

- **Minimum**: 80% overall coverage
- **Adapters**: 90% coverage required
- **Core**: 95% coverage required
- **CLI**: 70% coverage acceptable

### Running Tests

```bash
make test                 # All tests
make test-unit            # Fast unit tests
make test-integration     # Integration tests (requires API keys)
make test-coverage        # Generate coverage report
```

### Test Categories

```python
@pytest.mark.unit          # Fast, isolated unit tests
@pytest.mark.integration   # Tests with external APIs (mocked)
@pytest.mark.slow          # Tests that take >1 second
@pytest.mark.adapter       # Adapter-specific tests
```

### Writing Good Tests

```python
# Good test
@pytest.mark.asyncio
async def test_create_ticket_with_valid_data(adapter):
    """Test successful ticket creation with valid data."""
    # Arrange
    task = Task(title="Valid Task", priority=Priority.HIGH)

    # Act
    result = await adapter.create(task)

    # Assert
    assert result.id is not None
    assert result.title == "Valid Task"
    assert result.priority == Priority.HIGH

# Bad test
async def test_stuff(adapter):
    """Test."""
    result = await adapter.create(Task(title="Test"))
    assert result  # What are we testing?
```

---

## 🟡 IMPORTANT: Code Quality Standards

### The Non-Negotiables

1. **Type Hints**: ALL functions must have type hints
2. **Docstrings**: ALL public functions must have Google-style docstrings
3. **Error Handling**: Specific exceptions, not bare `except:`
4. **Async/Await**: All I/O operations must be async
5. **Formatting**: Black + isort (enforced by `make format`)
6. **Linting**: Ruff + mypy (enforced by `make lint`)

### Code Style Example

```python
"""Module docstring explaining purpose."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from ..core.adapter import BaseAdapter
from ..core.models import Task, Comment, TicketState


class YourAdapter(BaseAdapter[Task]):
    """One-line description.

    Detailed description explaining what this adapter does,
    what service it connects to, and any important details.

    Args:
        config: Configuration dictionary containing:
            - api_key: Service API key
            - team_id: Team identifier

    Example:
        >>> config = {"api_key": "xxx", "team_id": "yyy"}
        >>> adapter = YourAdapter(config)
        >>> task = Task(title="Test")
        >>> created = await adapter.create(task)
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize adapter with configuration."""
        super().__init__(config)
        # Implementation...

    async def create(self, ticket: Task) -> Task:
        """Create a new ticket.

        Args:
            ticket: Task to create with title and optional fields

        Returns:
            Created task with populated ID and metadata

        Raises:
            ValidationError: If ticket data is invalid
            AdapterError: If API request fails

        Example:
            >>> task = Task(title="Fix bug", priority=Priority.HIGH)
            >>> created = await adapter.create(task)
        """
        # Implementation with proper error handling
        try:
            # Do work
            result = await self._do_create(ticket)
            return result
        except SpecificError as e:
            raise AdapterError(f"Failed to create: {e}")
```

### Commit Message Format

```bash
# Format: <type>(<scope>): <description>

# Types:
feat      # New feature
fix       # Bug fix
docs      # Documentation only
style     # Code style (formatting, no logic change)
refactor  # Code refactoring
test      # Adding or updating tests
chore     # Maintenance tasks

# Examples:
feat(linear): add support for story points estimation
fix(cache): prevent memory leak in long-running processes
docs: add configuration examples for all adapters
test(github): add integration tests for label management
```

---

## 🟢 STANDARD: Adapter Development

### BaseAdapter Interface

**Every adapter MUST implement these methods:**

```python
class BaseAdapter(ABC, Generic[T]):
    # CRUD Operations
    async def create(self, ticket: T) -> T
    async def read(self, ticket_id: str) -> Optional[T]
    async def update(self, ticket_id: str, updates: Dict[str, Any]) -> Optional[T]
    async def delete(self, ticket_id: str) -> bool

    # Query Operations
    async def list(self, limit: int, offset: int, filters: Optional[Dict]) -> List[T]
    async def search(self, query: SearchQuery) -> List[T]

    # Workflow Operations
    async def transition_state(self, ticket_id: str, target_state: TicketState) -> Optional[T]

    # Comment Operations
    async def add_comment(self, comment: Comment) -> Comment
    async def get_comments(self, ticket_id: str, limit: int, offset: int) -> List[Comment]

    # State Mapping
    def _get_state_mapping(self) -> Dict[TicketState, str]
```

### State Mapping Example

```python
def _get_state_mapping(self) -> Dict[TicketState, str]:
    """Map universal states to system-specific states."""
    return {
        TicketState.OPEN: "Todo",              # System's "open" state
        TicketState.IN_PROGRESS: "In Progress",
        TicketState.READY: "Ready for Review",
        TicketState.TESTED: "In Review",
        TicketState.DONE: "Done",
        TicketState.CLOSED: "Canceled",
        TicketState.WAITING: "Waiting",
        TicketState.BLOCKED: "Blocked",
    }
```

### Error Handling

```python
from ..core.exceptions import (
    AdapterError,
    AuthenticationError,
    RateLimitError,
    ValidationError
)

async def create(self, ticket: Task) -> Task:
    """Create ticket with proper error handling."""
    # Validation
    if not ticket.title:
        raise ValidationError("Title is required", field="title")

    try:
        # API call
        response = await self.client.post("/issues", json=ticket.dict())

    except httpx.TimeoutError:
        raise AdapterError("Request timeout", self.__class__.__name__)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise AuthenticationError("Invalid API key", self.__class__.__name__)
        elif e.response.status_code == 429:
            retry_after = e.response.headers.get("Retry-After")
            raise RateLimitError("Rate limit exceeded", self.__class__.__name__, retry_after)
        else:
            raise AdapterError(f"HTTP {e.response.status_code}", self.__class__.__name__)
```

---

## 🟢 STANDARD: Common Tasks

### Creating Tickets

```bash
# Via CLI
make create TITLE="Fix login bug" DESC="Users cannot authenticate" PRIORITY="high"

# Or directly
mcp-ticketer create "Fix login bug" \
  --description "Users cannot authenticate" \
  --priority high \
  --assignee john.doe \
  --tags bug,auth
```

### Listing & Searching

```bash
# List tickets
make list STATE="open" LIMIT=20
mcp-ticketer list --state open --limit 20

# Search tickets
make search QUERY="login bug"
mcp-ticketer search "login bug" --state open --priority high
```

### State Transitions

```bash
# Transition ticket state
mcp-ticketer transition TICKET-123 in_progress
mcp-ticketer transition TICKET-123 done
```

### Managing Comments

```bash
# Add comment
mcp-ticketer comment TICKET-123 "Fixed the authentication issue"

# View comments
mcp-ticketer show TICKET-123 --comments
```

---

## 🟢 STANDARD: Troubleshooting

### Common Issues

#### 1. Import Errors

```bash
# Symptom: ModuleNotFoundError
# Fix: Reinstall in development mode
make clean
make install-dev
```

#### 2. Test Failures

```bash
# Symptom: Tests fail after changes
# Fix: Check test isolation
make test-unit -v
# Review test output for specific failures
```

#### 3. API Authentication Issues

```bash
# Symptom: AuthenticationError
# Fix: Verify API keys
echo $LINEAR_API_KEY
echo $GITHUB_TOKEN

# Reinitialize adapter
make init-linear LINEAR_API_KEY=new_key LINEAR_TEAM_ID=team_id
```

#### 4. Type Check Errors

```bash
# Symptom: mypy errors
# Fix: Add proper type hints
make typecheck
# Address reported type issues
```

#### 5. Formatting Issues

```bash
# Symptom: Pre-commit hook failures
# Fix: Run format command
make format
git add .
git commit -m "style: fix formatting"
```

### Debug Mode

```bash
# Enable debug logging
export MCP_TICKETER_DEBUG=1
export MCP_TICKETER_LOG_LEVEL=DEBUG

# Run with verbose output
mcp-ticketer --verbose list
```

### Getting Help

```bash
# Command help
mcp-ticketer --help
mcp-ticketer create --help

# Makefile targets
make help

# Check installation
make check-env
```

---

## ⚪ OPTIONAL: Performance Optimization

### Caching Strategy

```python
# Use provided cache decorator
from ..cache.memory import cache_decorator

@cache_decorator(ttl=300, key_prefix="adapter")
async def read(self, ticket_id: str) -> Optional[Task]:
    """Read with 5-minute cache."""
    # Implementation...
    pass

@cache_decorator(ttl=60, key_prefix="adapter")
async def list(self, limit: int = 10, offset: int = 0, filters: Optional[Dict] = None) -> List[Task]:
    """List with 1-minute cache."""
    # Implementation...
    pass
```

### Batch Operations

```python
async def bulk_create(self, tickets: List[Task], batch_size: int = 10) -> List[Task]:
    """Create tickets in efficient batches."""
    results = []

    for i in range(0, len(tickets), batch_size):
        batch = tickets[i:i + batch_size]

        # Process batch concurrently
        batch_tasks = [self.create(ticket) for ticket in batch]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        # Handle results
        for result in batch_results:
            if not isinstance(result, Exception):
                results.append(result)

        # Rate limiting
        await asyncio.sleep(0.1)

    return results
```

---

## ⚪ OPTIONAL: Custom Extensions

### Adding Custom MCP Methods

```python
# src/mcp_ticketer/mcp/extensions.py
class ExtendedMCPServer(MCPTicketServer):
    """Extended MCP server with custom methods."""

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle custom requests."""
        method = request.get("method")

        if method.startswith("custom/"):
            return await self._handle_custom_method(request)

        return await super().handle_request(request)

    async def _handle_custom_method(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Implement custom methods."""
        # Your custom logic
        pass
```

---

## Documentation Links

### Essential Reading
- **README.md**: Project overview and installation
- **CONTRIBUTING.md**: Contribution guidelines
- **docs/DEVELOPER_GUIDE.md**: Comprehensive developer documentation
- **docs/USER_GUIDE.md**: End-user guide
- **docs/API_REFERENCE.md**: API documentation
- **QUICK_START.md**: 5-minute quick start guide

### Adapter-Specific
- **JIRA_SETUP.md**: JIRA adapter configuration
- **LINEAR_SETUP.md**: Linear adapter configuration
- **docs/adapters/github.md**: GitHub adapter details

### Advanced Topics
- **QUEUE_SYSTEM.md**: Queue system documentation
- **docs/MCP_INTEGRATION.md**: MCP protocol integration
- **docs/PR_INTEGRATION.md**: Pull request integration

---

## Meta-Instructions

### Updating This File

**When to Update CLAUDE.md:**
1. Breaking changes to core interfaces
2. New critical commands added
3. Major workflow changes
4. New adapters added
5. Security issues discovered

**How to Update:**
1. Edit sections as needed
2. Maintain priority structure
3. Update version and date at top
4. Keep examples practical and tested
5. Verify all commands work
6. Commit with message: `docs: update CLAUDE.md - <reason>`

**Version Format:**
- Matches project version in `__version__.py`
- Update date in ISO format: YYYY-MM-DD

---

## Quick Reference Card

```bash
# Setup
make install-dev          # Install for development
make init-aitrackdown     # Initialize local adapter

# Daily Use
make quality              # Format + Lint + Test
make test-coverage        # Check test coverage
make docs-serve           # Serve documentation

# Ticket Operations
make create TITLE="..."   # Create ticket
make list STATE="open"    # List tickets
make search QUERY="..."   # Search tickets

# Building & Publishing
make build                # Build package
make publish              # Publish to PyPI

# Help
make help                 # Show all commands
mcp-ticketer --help       # Show CLI help
```

---

## ⚪ OPTIONAL: AI Client Integration

### Overview: Multiple AI Client Support

**MCP Ticketer supports 4 major AI clients with MCP integration:**

| Client | Project-Level | Config Format | Config Location | Command |
|--------|---------------|---------------|-----------------|---------|
| **Claude Code** | ✅ Yes | JSON | `.claude/mcp.json` | `mcp-ticketer mcp claude` |
| **Gemini CLI** | ✅ Yes | JSON | `.gemini/settings.json` | `mcp-ticketer mcp gemini` |
| **Codex CLI** | ❌ No (Global only) | TOML | `~/.codex/config.toml` | `mcp-ticketer mcp codex` |
| **Auggie** | ❌ No (Global only) | JSON | `~/.augment/settings.json` | `mcp-ticketer mcp auggie` |

**Quick Setup:**
```bash
# Claude Code (project-level, recommended)
mcp-ticketer mcp claude

# Gemini CLI (project-level)
mcp-ticketer mcp gemini --scope project

# Codex CLI (global-only, restart required)
mcp-ticketer mcp codex

# Auggie (global-only)
mcp-ticketer mcp auggie
```

**When to use which client:**
- **Claude Code**: Best for project-specific workflows, native MCP support
- **Gemini CLI**: Google's AI client, supports project-level configuration
- **Codex CLI**: Global configuration only, requires restart after config changes
- **Auggie**: Simple global setup, suitable for single-project users

**See Also:** [AI Client Integration Guide](docs/AI_CLIENT_INTEGRATION.md) for comprehensive setup instructions.

---

### Claude Code Integration (Recommended)

**MCP Ticketer is optimized for Claude Code workflows:**

```bash
# 1. Initialize for Claude Code
make install-dev
make init-aitrackdown

# 2. Configure MCP integration (THE ONLY WAY)
mcp-ticketer mcp claude

# Alternative: Configure for Claude Desktop (global)
mcp-ticketer mcp claude --global

# 3. Configuration created at:
# Project-level: .claude/mcp.json
# Global: ~/Library/Application Support/Claude/claude_desktop_config.json (macOS)
#         %APPDATA%/Claude/claude_desktop_config.json (Windows)
#         ~/.config/Claude/claude_desktop_config.json (Linux)

# 4. Use via Claude Code
# Claude can now create, read, update tickets directly
# Example: "Create a high-priority task for fixing the login bug"
```

**Example Configuration (.claude/mcp.json):**
```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "/path/to/mcp-ticketer",
      "args": ["serve"],
      "cwd": "/Users/masa/Projects/mcp-ticketer",
      "env": {
        "MCP_TICKETER_ADAPTER": "aitrackdown",
        "MCP_TICKETER_BASE_PATH": "/Users/masa/Projects/mcp-ticketer/.aitrackdown"
      }
    }
  }
}
```

---

### Gemini CLI Integration

**Google's Gemini CLI with project-level MCP support:**

```bash
# 1. Initialize mcp-ticketer
make install-dev
make init-aitrackdown

# 2. Configure for Gemini CLI (THE ONLY WAY)
mcp-ticketer mcp gemini --scope project

# Alternative: Global configuration
mcp-ticketer mcp gemini --scope user

# 3. Configuration created at:
# Project-level: .gemini/settings.json (added to .gitignore automatically)
# User-level: ~/.gemini/settings.json

# 4. Use with Gemini CLI
# Run gemini command in project directory
# MCP tools automatically available
```

**Example Configuration (.gemini/settings.json):**
```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "/path/to/mcp-ticketer",
      "args": ["serve"],
      "env": {
        "PYTHONPATH": "/path/to/project/src",
        "MCP_TICKETER_ADAPTER": "aitrackdown",
        "MCP_TICKETER_BASE_PATH": "/path/to/project/.aitrackdown"
      },
      "timeout": 15000,
      "trust": false
    }
  }
}
```

**Features:**
- ✅ Project-level configuration support
- ✅ JSON configuration format (familiar)
- ✅ Automatic .gitignore management
- ✅ 15-second timeout for MCP operations
- ✅ Security: untrusted by default

---

### Codex CLI Integration

**⚠️ IMPORTANT: Codex CLI only supports GLOBAL configuration**

```bash
# 1. Initialize mcp-ticketer
make install-dev
make init-aitrackdown

# 2. Configure for Codex CLI (THE ONLY WAY)
mcp-ticketer mcp codex

# 3. Configuration created at:
# Global only: ~/.codex/config.toml

# 4. RESTART Codex CLI (REQUIRED)
# Codex does not hot-reload configuration

# 5. Use with Codex CLI
# Run codex command in any directory
# MCP tools will be available globally
```

**Example Configuration (~/.codex/config.toml):**
```toml
[mcp_servers.mcp-ticketer]
command = "/path/to/mcp-ticketer"
args = ["serve"]

[mcp_servers.mcp-ticketer.env]
PYTHONPATH = "/path/to/project/src"
MCP_TICKETER_ADAPTER = "aitrackdown"
MCP_TICKETER_BASE_PATH = "/path/to/project/.aitrackdown"
```

**Limitations:**
- ❌ No project-level configuration support
- ❌ Global configuration affects all projects
- ⚠️ Requires restart after configuration changes
- ⚠️ TOML format (different from other clients)

**Use when:**
- You primarily work on one project
- You need global MCP access across all directories
- You prefer TOML configuration

---

### Auggie Integration

**⚠️ IMPORTANT: Auggie only supports GLOBAL configuration**

```bash
# 1. Initialize mcp-ticketer
make install-dev
make init-aitrackdown

# 2. Configure for Auggie (THE ONLY WAY)
mcp-ticketer mcp auggie

# 3. Configuration created at:
# Global only: ~/.augment/settings.json

# 4. Restart Auggie CLI
# Auggie should pick up the new configuration

# 5. Use with Auggie CLI
# Run auggie command in any directory
# MCP tools will be available globally
```

**Example Configuration (~/.augment/settings.json):**
```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "/path/to/mcp-ticketer",
      "args": ["serve"],
      "env": {
        "MCP_TICKETER_ADAPTER": "aitrackdown",
        "MCP_TICKETER_BASE_PATH": "/Users/user/.mcp-ticketer/.aitrackdown"
      }
    }
  }
}
```

**Limitations:**
- ❌ No project-level configuration support
- ❌ Global configuration affects all projects
- ⚠️ Uses global paths for adapter storage

**Use when:**
- You work on a single project primarily
- You want simple, global MCP access
- You prefer JSON configuration

---

### Comparison: Which Client Should You Use?

| Feature | Claude Code | Gemini CLI | Codex CLI | Auggie |
|---------|-------------|------------|-----------|--------|
| **Project-level config** | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Global config** | ✅ Yes | ✅ Yes | ✅ Only option | ✅ Only option |
| **Config format** | JSON | JSON | TOML | JSON |
| **Hot reload** | ✅ Yes | ✅ Yes | ❌ Requires restart | ⚠️ May require restart |
| **Security options** | ⚠️ Basic | ✅ Trust setting | ⚠️ Basic | ⚠️ Basic |
| **Working directory** | ✅ Supported | ✅ Supported | ⚠️ Global only | ⚠️ Global only |
| **Auto .gitignore** | ⚠️ Manual | ✅ Automatic | N/A | N/A |
| **Maturity** | ✅ Stable | ✅ Stable | ⚠️ Beta | ⚠️ Emerging |

**Recommendation:**
- **Best choice**: Claude Code (native integration, project-level support)
- **Alternative**: Gemini CLI (excellent project-level support, security features)
- **Single project**: Codex CLI or Auggie (simple global setup)

---

### Agent Collaboration Patterns

**Multi-Agent Workflow:**

```bash
# PM creates epic
make create TITLE="User Authentication System" DESC="Complete auth overhaul"

# Engineer breaks down into tasks
mcp-ticketer create "Implement OAuth2 flow" --parent-epic EPIC-123
mcp-ticketer create "Add session management" --parent-epic EPIC-123
mcp-ticketer create "Write authentication tests" --parent-epic EPIC-123

# QA updates test status
mcp-ticketer transition TASK-456 tested

# Ops deploys and closes
mcp-ticketer transition TASK-456 done
mcp-ticketer transition TASK-456 closed
```

### MCP Tools Available

**When using MCP server, these tools are exposed:**

```javascript
// ticket/create - Create new ticket
{
  "title": "Fix bug",
  "description": "Description here",
  "priority": "high",
  "assignee": "john.doe",
  "tags": ["bug", "auth"]
}

// ticket/search - Search tickets
{
  "query": "authentication bug",
  "state": "open",
  "priority": "high"
}

// ticket/transition - Change state
{
  "ticket_id": "TASK-123",
  "target_state": "in_progress"
}

// ticket/status - Check queue job status
{
  "queue_id": "job-uuid-here"
}

// ticket/create_pr - Create GitHub PR linked to ticket
{
  "ticket_id": "TASK-123",
  "base_branch": "main",
  "head_branch": "feature/task-123",
  "title": "PR Title",
  "draft": false
}
```

### Memory-Driven Development

**Leverage `.claude-mpm/memories/` for persistent knowledge:**

```bash
# Memory files store project-specific learnings
.claude-mpm/memories/
├── project_knowledge.md      # Architecture, patterns, conventions
├── workflows.md              # Standard procedures
├── engineer_memories.md      # Engineering patterns
├── ops_memories.md           # Deployment knowledge
└── documentation_memories.md # Doc standards
```

**Update memories when:**
- Discovering new patterns or anti-patterns
- Learning configuration quirks
- Finding solutions to tricky problems
- Establishing team conventions

---

## ⚪ OPTIONAL: Memory System

### Memory Structure

**Location**: `.claude-mpm/memories/`

**Memory Files**:

```bash
project_knowledge.md       # Core project architecture and patterns
workflows.md              # Standard workflows and procedures
engineer_memories.md      # Engineering-specific knowledge
ops_memories.md          # Operations and deployment knowledge
documentation_memories.md # Documentation standards
qa_memories.md           # Testing patterns and requirements
research_memories.md     # Research findings and decisions
version-control_memories.md # Git workflows and conventions
```

### Memory Update Protocol

**When to Update Memories:**

1. **Architecture Changes**: Update `project_knowledge.md`
2. **New Workflows**: Update `workflows.md`
3. **Adapter Patterns**: Update `engineer_memories.md`
4. **Deployment Procedures**: Update `ops_memories.md`
5. **Documentation Standards**: Update `documentation_memories.md`

**How to Update:**

```bash
# 1. Read existing memory
cat .claude-mpm/memories/project_knowledge.md

# 2. Append new learning
echo "## New Pattern: State Machine Validation" >> .claude-mpm/memories/project_knowledge.md
echo "Always validate state transitions before attempting them." >> .claude-mpm/memories/project_knowledge.md

# 3. Commit memory update
git add .claude-mpm/memories/
git commit -m "docs: update project knowledge with state validation pattern"
```

### Memory Categories

**Project Knowledge** (`.claude-mpm/memories/project_knowledge.md`):
- Architecture patterns
- Core abstractions
- Design decisions
- Technology choices
- Performance characteristics

**Workflows** (`.claude-mpm/memories/workflows.md`):
- Development workflows
- Release procedures
- Testing strategies
- Code review processes
- CI/CD pipelines

**Engineer Memories** (`.claude-mpm/memories/engineer_memories.md`):
- Coding patterns
- Common pitfalls
- Optimization techniques
- Debugging strategies
- Adapter implementation patterns

**Ops Memories** (`.claude-mpm/memories/ops_memories.md`):
- Deployment procedures
- Configuration management
- Monitoring setup
- Incident response
- Infrastructure patterns

### AI Agent Memory Access

**Reading Memories:**

```python
# Agents can read memories to understand project context
import pathlib

def load_project_knowledge():
    memory_path = pathlib.Path(".claude-mpm/memories/project_knowledge.md")
    if memory_path.exists():
        return memory_path.read_text()
    return None
```

**Memory-Driven Decisions:**

When AI agents access memories, they can:
- Avoid repeating past mistakes
- Follow established conventions
- Apply learned patterns
- Make context-aware decisions
- Maintain consistency across sessions

### Memory Best Practices

1. **Be Specific**: Document concrete examples, not vague principles
2. **Link Context**: Reference related code, docs, or issues
3. **Date Entries**: Track when patterns were established
4. **Update Regularly**: Keep memories current with project evolution
5. **Categorize Clearly**: Use appropriate memory files

---

**END OF CLAUDE.MD**

For detailed technical documentation, see `docs/DEVELOPER_GUIDE.md`.
For quick start instructions, see `QUICK_START.md`.
For contribution guidelines, see `CONTRIBUTING.md`.
