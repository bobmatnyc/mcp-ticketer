# API Documentation

Complete API reference for MCP Ticketer - CLI, MCP Tools, and Python API.

## 📚 API Types

### Complete API Reference
Comprehensive documentation covering all MCP Ticketer APIs and interfaces.

**[Complete API Reference](API_REFERENCE.md)**
- All APIs in one document
- Cross-interface comparisons
- Complete usage examples

### CLI (Command Line Interface)
Command-line tools for managing tickets from the terminal.

**[CLI Reference](cli.md)** _(if available)_
- All commands and options
- Usage examples
- Configuration options

### MCP Tools
Tools for AI agent integration via Model Context Protocol.

**[MCP Tools Reference](mcp_tools.md)** _(if available)_
- Complete tool catalog
- Parameters and return values
- Integration examples

### Python API
Programmatic access to MCP Ticketer functionality.

**[Python API Reference](python.md)** _(if available)_
- Core classes and methods
- Adapter interfaces
- Exception handling

## 🚀 Quick Start by Use Case

### CLI Usage
```bash
# Initialize configuration
mcp-ticketer init --adapter linear

# Create a ticket
mcp-ticketer create "Fix bug" --description "Details..." --priority high

# List tickets
mcp-ticketer list --state open

# Manage instructions
mcp-ticketer instructions show
mcp-ticketer instructions add team_guidelines.md
```

**See**: [CLI Reference](cli.md)

### MCP Integration
```python
# MCP tool usage examples
await ticket_create(
    title="[Bug] Fix authentication",
    description="Users cannot login...",
    priority="high"
)

await instructions_get()  # Get current instructions
await instructions_set(content="# Custom guidelines...")
```

**See**: [MCP Tools Reference](mcp_tools.md)

### Python Programming
```python
from mcp_ticketer.core import TicketManager
from mcp_ticketer.core.instructions import TicketInstructionsManager

# Create ticket manager
manager = TicketManager(adapter="linear")
ticket = await manager.create_ticket(
    title="Fix bug",
    description="Details...",
    priority="high"
)

# Manage instructions
instructions_mgr = TicketInstructionsManager()
instructions = instructions_mgr.get_instructions()
```

**See**: [Python API Reference](python.md)

## 📖 Documentation Structure

### CLI Commands

**Ticket Management**
- `create` - Create new tickets
- `list` - List tickets with filters
- `show` - Display ticket details
- `update` - Update ticket fields
- `delete` - Delete tickets
- `transition` - Change ticket state
- `search` - Search tickets

**Configuration**
- `init` / `setup` - Initialize adapter configuration
- `config` - Manage configuration
- `doctor` - Validate configuration

**Instructions**
- `instructions show` - View instructions
- `instructions add` - Add custom instructions
- `instructions update` - Update instructions
- `instructions delete` - Remove custom instructions
- `instructions path` - Show instructions file path
- `instructions edit` - Edit instructions in editor

**MCP Integration**
- `install` - Install MCP server for AI clients
- `remove` / `uninstall` - Remove MCP configuration
- `mcp` - Start MCP server manually

### MCP Tools

**Ticket Operations**
- `ticket_create()` - Create tickets
- `ticket_read()` - Read ticket details
- `ticket_update()` - Update tickets
- `ticket_delete()` - Delete tickets
- `ticket_list()` - List tickets
- `ticket_search()` - Search tickets
- `ticket_comment()` - Add/list comments

**Hierarchy Management**
- `epic_create()` - Create epics
- `epic_list()` - List epics
- `epic_issues()` - Get epic's issues
- `issue_create()` - Create issues
- `issue_tasks()` - Get issue's tasks
- `task_create()` - Create tasks
- `hierarchy_tree()` - Get full hierarchy

**Instructions Management**
- `instructions_get()` - Get current instructions
- `instructions_set()` - Set custom instructions
- `instructions_reset()` - Reset to defaults
- `instructions_validate()` - Validate instructions

**Attachments** (AITrackdown adapter)
- `ticket_attach()` - Attach files
- `ticket_attachments()` - List attachments

**Pull Requests** (GitHub/JIRA adapters)
- `ticket_create_pr()` - Create PR linked to ticket
- `ticket_link_pr()` - Link existing PR

### Python API

**Core Classes**
- `TicketManager` - Main ticket management interface
- `TicketInstructionsManager` - Instructions management
- `BaseAdapter` - Adapter base class
- `Ticket`, `Epic`, `Task`, `Comment` - Data models

**Adapter Classes**
- `LinearAdapter` - Linear integration
- `JiraAdapter` - JIRA integration
- `GitHubAdapter` - GitHub Issues integration
- `AITrackdownAdapter` - Local file storage

**Exceptions**
- `MCPTicketerError` - Base exception
- `AdapterError` - Adapter-specific errors
- `InstructionsError` - Instructions errors
- `ValidationError` - Validation errors

## 🔍 Finding What You Need

**I want to...**

- **Use from command line** → [CLI Reference](cli.md)
- **Integrate with AI** → [MCP Tools Reference](mcp_tools.md)
- **Write Python code** → [Python API Reference](python.md)
- **Customize ticket format** → [CLI Instructions Commands](cli.md#instructions-commands)
- **Manage attachments** → [MCP Attachments Tools](mcp_tools.md#attachments)
- **Create hierarchies** → [MCP Hierarchy Tools](mcp_tools.md#hierarchy)
- **Search tickets** → [CLI Search](cli.md#search) or [MCP Search](mcp_tools.md#search)

## 📋 Common Patterns

### Creating Tickets with Custom Instructions

**CLI**:
```bash
# Set up custom instructions
mcp-ticketer instructions add team_guidelines.md

# Create ticket (uses custom instructions)
mcp-ticketer create "Fix bug" --description "Details..."
```

**MCP**:
```python
# Get instructions for context
result = await instructions_get()
instructions = result["instructions"]

# Create ticket following instructions
await ticket_create(title="Fix bug", description="Details...")
```

**Python**:
```python
# Get instructions
mgr = TicketInstructionsManager()
instructions = mgr.get_instructions()

# Use instructions to format ticket
ticket_mgr = TicketManager()
await ticket_mgr.create_ticket(...)
```

### Working with Hierarchies

**CLI**:
```bash
# Create epic
mcp-ticketer create-epic "Q4 Redesign" --description "Major UI overhaul"

# Create issue under epic
mcp-ticketer create-issue "Update navigation" --epic-id EPIC-123

# Create task under issue
mcp-ticketer create-task "Design mockup" --issue-id ISSUE-456
```

**MCP**:
```python
# Create hierarchy
epic = await epic_create(title="Q4 Redesign", description="...")
issue = await issue_create(title="Update navigation", epic_id=epic["id"])
task = await task_create(title="Design mockup", issue_id=issue["id"])

# Get full tree
tree = await hierarchy_tree(epic_id=epic["id"], max_depth=3)
```

**Python**:
```python
# Using adapter directly
adapter = get_adapter("linear")
epic = await adapter.create_epic(title="Q4 Redesign", ...)
issue = await adapter.create_issue(title="Update navigation", parent_epic=epic.id)
task = await adapter.create_task(title="Design mockup", parent_issue=issue.id)
```

## 🔗 Related Documentation

- [Features Documentation](../features/) - Feature guides and tutorials
- [Guides](../guides/) - How-to guides and examples
- [Setup](../setup/) - Adapter configuration guides
- [Development](../development/) - Development and contribution guides

## 🆘 Getting Help

- **Examples**: Check each API reference for detailed examples
- **Types**: See [Python API](python.md) for complete type information
- **Errors**: Exception documentation in [Python API](python.md#exceptions)
- **Issues**: [GitHub Issues](https://github.com/mcp-ticketer/mcp-ticketer/issues)

---

**Last Updated**: 2025-11-15
