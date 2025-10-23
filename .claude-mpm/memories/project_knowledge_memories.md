# MCP Ticketer - Project Knowledge

**Created**: 2025-01-22
**Project Version**: 0.1.11

## Project Identity

**Name**: MCP Ticketer
**Purpose**: Universal ticket management interface for AI agents with MCP support
**Type**: Python package / CLI tool / MCP server
**Primary Language**: Python 3.9+
**Architecture**: Adapter pattern with pluggable ticket system integrations

## Core Principles

1. **Single-Path Principle**: ONE way to do ANYTHING - enforced through Makefile
2. **Universal Model**: Simplified Epic → Task → Comment hierarchy
3. **Adapter Pattern**: Pluggable integrations for JIRA, Linear, GitHub, AI-Trackdown
4. **MCP Native**: Built for AI agent interactions via Model Context Protocol
5. **Type Safety**: Comprehensive type hints and Pydantic validation

## Critical Commands (THE ONLY WAYS)

```bash
# Setup
make install-dev          # THE way to set up development
make install-all          # THE way to install with all adapters

# Development
make dev                  # THE way to run MCP server
make test                 # THE way to run tests
make format               # THE way to format code
make lint-fix             # THE way to fix linting
make quality              # THE way to run all quality checks

# Building
make build                # THE way to build package
make publish              # THE way to publish to PyPI
```

## Architecture Overview

```
Core Components:
├── adapters/        # Ticket system integrations (extend here)
│   ├── aitrackdown.py  # Local file-based
│   ├── linear.py       # Linear GraphQL API
│   ├── jira.py         # JIRA REST API
│   └── github.py       # GitHub Issues API
├── core/            # Foundation layer (modify carefully)
│   ├── models.py       # Universal ticket models
│   ├── adapter.py      # BaseAdapter interface
│   ├── config.py       # Configuration management
│   └── registry.py     # Adapter factory
├── cli/             # Typer-based CLI
├── mcp/             # JSON-RPC MCP server
├── cache/           # TTL-based memory cache
└── queue/           # Async job queue system
```

## State Machine

```
OPEN → IN_PROGRESS → READY → TESTED → DONE → CLOSED
  ↓         ↓          ↓
WAITING  BLOCKED    BLOCKED
```

Valid transitions enforced by `TicketState.can_transition_to()`

## Technology Stack

- **Data Validation**: Pydantic v2
- **CLI**: Typer + Rich
- **Async**: asyncio + httpx
- **Testing**: pytest + pytest-asyncio
- **Linting**: ruff + mypy
- **Formatting**: black + isort
- **GraphQL**: gql[httpx] for Linear
- **MCP**: JSON-RPC over stdio

## Key Design Decisions

1. **Generic Type Parameters**: `BaseAdapter[T]` where T is Epic or Task
2. **State Mapping**: Each adapter maps universal states to system-specific states
3. **Async First**: All I/O operations use async/await
4. **Cache Strategy**: TTL-based caching with adapter-level control
5. **Queue System**: Async operations for long-running tasks

## Extension Points

1. **New Adapters**: Implement `BaseAdapter` interface and register
2. **Custom Fields**: Extend models with Optional fields for compatibility
3. **CLI Commands**: Add to `cli/main.py` using Typer decorators
4. **MCP Methods**: Extend server with custom JSON-RPC methods

## Testing Requirements

- **Core**: 95% coverage required
- **Adapters**: 90% coverage required
- **Overall**: 80% minimum
- **Categories**: unit, integration, e2e, performance

## Code Quality Standards

1. **Type Hints**: ALL functions must have type hints
2. **Docstrings**: ALL public APIs need Google-style docstrings
3. **Error Handling**: Specific exceptions, never bare except
4. **Formatting**: Black (88 char) + isort enforced
5. **Linting**: Ruff + mypy zero-tolerance

## Commit Message Format

```
<type>(<scope>): <description>

Types: feat, fix, docs, style, refactor, test, chore
Example: feat(linear): add story points support
```

## Configuration

**Location**: `~/.mcp-ticketer/config.json`
**Format**: JSON with adapter and config keys
**Environment**: Override with MCP_TICKETER_* variables

## Documentation Structure

- **CLAUDE.md**: AI agent instructions (priority-based)
- **CODE_STRUCTURE.md**: Architecture and module breakdown
- **QUICK_START.md**: 5-minute setup guide
- **docs/DEVELOPER_GUIDE.md**: Comprehensive developer docs
- **docs/USER_GUIDE.md**: End-user documentation
- **CONTRIBUTING.md**: Contribution guidelines

## Dependencies Management

**Add dependencies in `pyproject.toml` ONLY**:
- Core dependencies in `dependencies`
- Optional in `[project.optional-dependencies]`
- Dev tools in `[project.optional-dependencies.dev]`

## Common Pitfalls to Avoid

1. ❌ Don't modify core/models.py without team discussion
2. ❌ Don't modify core/adapter.py interface (breaks all adapters)
3. ❌ Don't commit secrets or API keys
4. ❌ Don't create new command patterns (use Makefile)
5. ❌ Don't skip quality checks before committing
6. ❌ Don't use pip/pytest/black directly (use Make commands)

## Release Process

1. Update `__version__.py`
2. Update `CHANGELOG.md`
3. Run `make ci` (full CI pipeline locally)
4. Tag release: `git tag -a v0.X.Y -m "Release v0.X.Y"`
5. Build: `make build`
6. Publish: `make publish`

## Performance Characteristics

- **Adapter reads**: 5-minute cache TTL
- **List operations**: 1-minute cache TTL
- **Search results**: 30-second cache TTL
- **Connection pooling**: Max 20 concurrent connections
- **Async operations**: Non-blocking I/O throughout

## Security Considerations

1. API keys via environment variables ONLY
2. No secrets in version control
3. Pre-commit hook scans for secrets
4. Bandit security checks in CI/CD
5. Rate limiting for API calls

## Troubleshooting Quick Fixes

```bash
# Import errors
make clean && make install-dev

# Test failures
make test-unit -v

# Format issues
make format

# Type errors
make typecheck

# Full reset
make clean && make install-dev && make test
```

## Project Metrics (as of v0.1.11)

- **Source Files**: 28 Python modules
- **Lines of Code**: ~5000 (excluding tests)
- **Test Coverage**: 85%+
- **Adapters**: 4 (AITrackdown, Linear, JIRA, GitHub)
- **CLI Commands**: 15+
- **MCP Methods**: 12+

## Future Roadmap

### v0.2.0
- Web UI Dashboard
- Webhook support
- Advanced search improvements
- Bulk operations API

### v0.3.0+
- GitLab Issues adapter
- Slack/Teams integration
- Custom adapters SDK
- Analytics dashboard

## Important Links

- **Repository**: https://github.com/mcp-ticketer/mcp-ticketer
- **PyPI**: https://pypi.org/project/mcp-ticketer
- **Documentation**: https://mcp-ticketer.readthedocs.io
- **Issues**: https://github.com/mcp-ticketer/mcp-ticketer/issues

## Claude Code Optimizations

### MCP Server Configuration

**Claude Desktop Integration**:
```json
{
  "mcpServers": {
    "ticketer": {
      "command": "mcp-ticketer-server",
      "env": {
        "MCP_TICKETER_ADAPTER": "aitrackdown",
        "MCP_TICKETER_BASE_PATH": "${workspaceFolder}/.aitrackdown"
      }
    }
  }
}
```

### AI Agent Patterns

1. **Single-Path Enforcement**: All operations through Makefile prevents agent confusion
2. **Type-Safe Models**: Pydantic validation ensures data integrity in agent operations
3. **State Machine**: Clear state transitions prevent invalid agent actions
4. **Queue System**: Async operations allow agents to offload long-running tasks
5. **Memory Integration**: Agents can persist learnings in `.claude-mpm/memories/`

### Agent-Friendly Features

- **Comprehensive Docstrings**: All public APIs document parameters, returns, exceptions
- **Type Hints**: Full type coverage enables IDE/agent autocomplete
- **Error Messages**: Specific error types help agents diagnose issues
- **JSON-RPC Protocol**: Standard protocol for agent-server communication
- **Rich CLI Output**: Human-readable tables for debugging agent actions

## Adapter Implementation Patterns

### State Mapping Pattern
```python
def _get_state_mapping(self) -> Dict[TicketState, str]:
    """Map universal states to system-specific states."""
    return {
        TicketState.OPEN: "Todo",
        TicketState.IN_PROGRESS: "In Progress",
        TicketState.DONE: "Done",
        # ... map all states
    }
```

### Error Handling Pattern
```python
try:
    result = await self.client.post(url, json=data)
except httpx.TimeoutError:
    raise AdapterError("Timeout", self.__class__.__name__)
except httpx.HTTPStatusError as e:
    if e.response.status_code == 401:
        raise AuthenticationError("Invalid credentials")
    elif e.response.status_code == 429:
        raise RateLimitError("Rate limited")
```

### Caching Pattern
```python
@cache_decorator(ttl=300, key_prefix="adapter")
async def read(self, ticket_id: str) -> Optional[Task]:
    """Read with 5-minute cache."""
    # Implementation
```

## Memory Tags

#mcp-ticketer #python #tickets #mcp #adapters #async #pydantic #cli #json-rpc #claude-code #ai-agents
