# Configuration and User Ticket Management Tools

This document describes the new MCP tools for managing configuration and user-specific ticket operations.

## Overview

Two new tool modules have been added to mcp-ticketer:
1. **config_tools**: Manage project-local configuration (adapter, project, user settings)
2. **user_ticket_tools**: User-specific ticket operations (my tickets, state transitions)

All configuration is stored in `.mcp-ticketer/config.json` within the project root for security and isolation.

## Configuration Tools

### config_set_primary_adapter

Set the default adapter for ticket operations.

**Parameters:**
- `adapter` (required): Adapter name - one of: "aitrackdown", "linear", "github", "jira"

**Returns:**
- `status`: "completed" or "error"
- `previous_adapter`: Previous default adapter
- `new_adapter`: New default adapter
- `config_path`: Path to configuration file

**Example:**
```python
result = await config_set_primary_adapter("linear")
# Result:
# {
#     "status": "completed",
#     "message": "Default adapter set to 'linear'",
#     "previous_adapter": "aitrackdown",
#     "new_adapter": "linear",
#     "config_path": "/project/.mcp-ticketer/config.json"
# }
```

**Error Cases:**
- Invalid adapter name → Returns error with valid options

---

### config_set_default_project

Set the default project/epic for new tickets.

**Parameters:**
- `project_id` (required): Project or epic ID
- `project_key` (optional): Project key (for adapters that use keys)

**Returns:**
- `status`: "completed" or "error"
- `previous_project`: Previous default project
- `new_project`: New default project ID

**Example:**
```python
# Set default project
result = await config_set_default_project("PROJ-123")

# Clear default project
result = await config_set_default_project("")
```

**Usage:**
- All new tickets created without explicit `parent_epic` will be assigned to this project
- Set to empty string to clear the default
- Works with `ticket_create`, `issue_create`, and `task_create` tools

---

### config_set_default_user

Set the default assignee for new tickets.

**Parameters:**
- `user_id` (required): User identifier or email
- `user_email` (optional): Email (for adapters requiring separate email field)

**Returns:**
- `status`: "completed" or "error"
- `previous_user`: Previous default user
- `new_user`: New default user ID

**Example:**
```python
# Set default user by email
result = await config_set_default_user("user@example.com")

# Set default user by UUID
result = await config_set_default_user("550e8400-e29b-41d4-a716-446655440000")

# Clear default user
result = await config_set_default_user("")
```

**Usage:**
- All new tickets created without explicit `assignee` will be assigned to this user
- Supports both email and UUID formats
- Works with `ticket_create`, `issue_create`, and `task_create` tools

---

### config_set_default_team

Set the default team for ticket operations (v1.1.6+).

**Parameters:**
- `team_id` (required): Team ID or key to set as default

**Returns:**
- `status`: "completed" or "error"
- `message`: Success or error message
- `previous_team`: Previous default team (if any)
- `new_team`: New default team ID
- `config_path`: Path to configuration file

**Example:**
```python
# Set default team
result = await config_set_default_team("team-abc123")
# Result:
# {
#     "status": "completed",
#     "message": "Default team set to 'team-abc123'",
#     "previous_team": None,
#     "new_team": "team-abc123",
#     "config_path": "/project/.mcp-ticketer/config.json"
# }

# Clear default team
result = await config_set_default_team("")
```

**Platform Support:**
| Platform | Team Identifier | Example |
|----------|----------------|---------|
| **Linear** | Team ID (UUID) | `"1a2b3c4d-5678-90ab-cdef-1234567890ab"` |
| **GitHub** | Organization/Owner | `"my-organization"` |
| **JIRA** | Project Key | `"ENG"` or `"PROJ"` |
| **Asana** | Workspace GID | `"1234567890"` |

**Usage:**
- Automatically scopes `ticket_list` and `ticket_search` to specified team
- Improves query performance for multi-team platforms
- Reduces token usage in AI interactions
- Prevents accidentally querying other teams' tickets
- Triggers warnings when querying large unscoped datasets

**Benefits:**
- **Performance**: Faster queries on multi-team platforms
- **Relevance**: Returns only team-specific tickets
- **Token Efficiency**: Reduces context size by 50-70% for large organizations
- **Safety**: Prevents cross-team data leaks

---

### config_set_default_cycle

Set the default cycle/sprint for ticket operations (v1.1.6+).

**Parameters:**
- `cycle_id` (required): Cycle/sprint ID to set as default

**Returns:**
- `status`: "completed" or "error"
- `message`: Success or error message
- `previous_cycle`: Previous default cycle (if any)
- `new_cycle`: New default cycle ID
- `config_path`: Path to configuration file

**Example:**
```python
# Set default cycle
result = await config_set_default_cycle("cycle-abc123def456")
# Result:
# {
#     "status": "completed",
#     "message": "Default cycle set to 'cycle-abc123def456'",
#     "previous_cycle": None,
#     "new_cycle": "cycle-abc123def456",
#     "config_path": "/project/.mcp-ticketer/config.json"
# }

# Clear default cycle
result = await config_set_default_cycle("")
```

**Platform Support:**
| Platform | Cycle Identifier | Example |
|----------|-----------------|---------|
| **Linear** | Cycle ID (UUID) | `"cycle-abc123def456"` |
| **JIRA** | Sprint ID | `"123"` |
| **GitHub** | Milestone number | `"5"` (GitHub uses milestones) |
| **Asana** | Project section GID | `"9876543210"` |

**Usage:**
- Automatically scopes queries to current sprint/cycle
- Focuses work on active sprint tickets
- Reduces noise from backlog or future sprint items
- Updates at sprint boundaries for continuous scoping

**Benefits:**
- **Focus**: Only see current sprint work
- **Clarity**: Removes backlog noise from queries
- **Planning**: Easy sprint-based reporting
- **Velocity**: Track sprint-specific metrics

---

### config_get

Get current configuration settings.

**Parameters:** None

**Returns:**
- `status`: "completed" or "error"
- `config`: Complete configuration dictionary
- `config_path`: Path to configuration file
- `config_exists`: Whether configuration file exists

**Example:**
```python
result = await config_get()
# Result:
# {
#     "status": "completed",
#     "config": {
#         "default_adapter": "linear",
#         "default_project": "PROJ-123",
#         "default_user": "user@example.com",
#         "adapters": {
#             "linear": {
#                 "api_key": "***",  # Masked for security
#                 "team_id": "team-uuid"
#             }
#         }
#     },
#     "config_path": "/project/.mcp-ticketer/config.json",
#     "config_exists": true
# }
```

**Security:**
- Sensitive values (API keys, tokens) are masked as "***"
- Non-sensitive fields are returned as-is

---

## User Ticket Tools

### get_my_tickets

Get tickets assigned to the configured default user.

**Parameters:**
- `state` (optional): Filter by state - one of: open, in_progress, ready, tested, done, closed, waiting, blocked
- `limit` (optional): Maximum number of tickets (default: 10, max: 100)

**Returns:**
- `status`: "completed" or "error"
- `tickets`: List of ticket objects
- `count`: Number of tickets returned
- `user`: User ID that was queried
- `state_filter`: State filter applied

**Example:**
```python
# Get all tickets for current user
result = await get_my_tickets()

# Get in-progress tickets
result = await get_my_tickets(state="in_progress", limit=5)
# Result:
# {
#     "status": "completed",
#     "tickets": [
#         {"id": "TICKET-1", "title": "Fix bug", "state": "in_progress"},
#         {"id": "TICKET-2", "title": "Add feature", "state": "in_progress"}
#     ],
#     "count": 2,
#     "user": "user@example.com",
#     "state_filter": "in_progress",
#     "limit": 5
# }
```

**Prerequisites:**
- Requires `default_user` to be set via `config_set_default_user()`
- Returns error with setup instructions if not configured

---

### get_available_transitions

Get valid next states for a ticket based on workflow rules.

**Parameters:**
- `ticket_id` (required): Unique identifier of the ticket

**Returns:**
- `status`: "completed" or "error"
- `ticket_id`: ID of the queried ticket
- `current_state`: Current workflow state
- `available_transitions`: List of valid target states
- `transition_descriptions`: Human-readable descriptions
- `is_terminal`: Whether current state is terminal (no transitions)

**Example:**
```python
result = await get_available_transitions("TICKET-123")
# Result:
# {
#     "status": "completed",
#     "ticket_id": "TICKET-123",
#     "current_state": "in_progress",
#     "available_transitions": ["ready", "waiting", "blocked", "open"],
#     "transition_descriptions": {
#         "ready": "Mark work as complete and ready for review",
#         "waiting": "Pause work while waiting for external dependency",
#         "blocked": "Work is blocked by an impediment",
#         "open": "Move back to backlog"
#     },
#     "is_terminal": false
# }
```

**Workflow State Machine:**
```
OPEN → IN_PROGRESS, WAITING, BLOCKED, CLOSED
IN_PROGRESS → READY, WAITING, BLOCKED, OPEN
READY → TESTED, IN_PROGRESS, BLOCKED
TESTED → DONE, IN_PROGRESS
DONE → CLOSED
WAITING → OPEN, IN_PROGRESS, CLOSED
BLOCKED → OPEN, IN_PROGRESS, CLOSED
CLOSED → (no transitions)
```

---

### ticket_transition

Move ticket through workflow with validation and optional comment.

**Parameters:**
- `ticket_id` (required): Unique identifier of the ticket
- `to_state` (required): Target state
- `comment` (optional): Comment explaining the transition

**Returns:**
- `status`: "completed" or "error"
- `ticket`: Updated ticket object
- `previous_state`: State before transition
- `new_state`: State after transition
- `comment_added`: Whether comment was added

**Example:**
```python
# Transition with comment
result = await ticket_transition(
    "TICKET-123",
    "ready",
    "Work complete, ready for code review"
)
# Result:
# {
#     "status": "completed",
#     "ticket": {"id": "TICKET-123", "state": "ready", ...},
#     "previous_state": "in_progress",
#     "new_state": "ready",
#     "comment_added": true,
#     "message": "Ticket TICKET-123 transitioned from in_progress to ready"
# }
```

**Error Cases:**
- Invalid transition → Returns error with valid options
- Invalid state name → Returns error with valid states
- Ticket not found → Returns error
- Terminal state (CLOSED) → Returns error (no valid transitions)

**Best Practices:**
1. Use `get_available_transitions()` first to see valid options
2. Always provide a comment explaining why the transition is happening
3. Handle invalid transition errors gracefully

---

## Workflow Examples

### Setting Up a Project

```python
# 1. Configure adapter
await config_set_primary_adapter("linear")

# 2. Set default project/epic
await config_set_default_project("PROJ-2025-Q1")

# 3. Set yourself as default assignee
await config_set_default_user("myemail@company.com")

# 4. Verify configuration
config = await config_get()
print(config)
```

### Creating Tickets with Defaults

```python
# With defaults configured, new tickets automatically get:
# - Assigned to default user
# - Added to default project
result = await ticket_create(
    title="Fix authentication bug",
    description="Users cannot log in with SSO"
    # No assignee or parent_epic needed!
)
```

### Managing Your Tickets

```python
# Get all your in-progress tickets
tickets = await get_my_tickets(state="in_progress")

for ticket in tickets["tickets"]:
    ticket_id = ticket["id"]

    # Check what transitions are available
    transitions = await get_available_transitions(ticket_id)

    if "ready" in transitions["available_transitions"]:
        # Move to ready state
        await ticket_transition(
            ticket_id,
            "ready",
            "Implementation complete, ready for review"
        )
```

### State Transition Validation

```python
# This will fail with clear error message
result = await ticket_transition("TICKET-1", "done")
# Error: Invalid transition from 'open' to 'done'
# Valid transitions: in_progress, waiting, blocked, closed

# Correct approach:
result = await ticket_transition("TICKET-1", "in_progress")
# Then later:
result = await ticket_transition("TICKET-1", "ready")
result = await ticket_transition("TICKET-1", "tested")
result = await ticket_transition("TICKET-1", "done")
```

---

## Configuration File Format

The `.mcp-ticketer/config.json` file uses this structure:

```json
{
  "default_adapter": "linear",
  "default_user": "user@example.com",
  "default_project": "PROJ-123",
  "default_epic": "PROJ-123",
  "adapters": {
    "linear": {
      "adapter": "linear",
      "api_key": "your-api-key",
      "team_id": "team-uuid"
    }
  }
}
```

**Security Notes:**
- File is project-local only (never in home directory)
- Prevents configuration leakage across projects
- Sensitive values masked in `config_get()` responses
- Should be added to `.gitignore`

---

## Testing

Comprehensive test suites are available:
- `tests/mcp/test_config_tools.py` - Configuration management tests
- `tests/mcp/test_user_ticket_tools.py` - User ticket operation tests

Run tests:
```bash
pytest tests/mcp/test_config_tools.py tests/mcp/test_user_ticket_tools.py -v
```

---

## Implementation Details

### Design Decisions

**Project-Local Configuration:**
- All configuration stored in `.mcp-ticketer/config.json` within project root
- Never reads from or writes to user home directory
- Prevents configuration leakage across projects
- Each project maintains its own isolated settings

**Default Value Injection:**
- `ticket_create`, `issue_create`, and `task_create` automatically use defaults
- Only applied when parameters are not explicitly provided
- Transparent to users - "just works" behavior
- No breaking changes to existing code

**State Machine Validation:**
- Enforces workflow integrity through `TicketState.can_transition_to()`
- Prevents invalid state changes
- O(1) validation using predefined transitions dict
- Clear error messages with valid options

### Performance Characteristics

- **Configuration reads**: O(1) after first load (cached by ConfigResolver)
- **State validation**: O(1) lookup in predefined transitions dict
- **Default injection**: Minimal overhead (single config read per ticket creation)
- **User ticket filtering**: Depends on adapter (native filter when available)

### Error Handling

All tools follow consistent error response format:
```json
{
  "status": "error",
  "error": "Human-readable error message",
  "additional_context": "Optional details"
}
```

Success responses always include:
```json
{
  "status": "completed",
  ...
}
```

---

## Migration Guide

### From Manual Configuration

**Before:**
```python
# Manual configuration on every ticket
await ticket_create(
    title="Fix bug",
    assignee="user@example.com",
    parent_epic="PROJ-123"
)
```

**After:**
```python
# One-time setup
await config_set_default_user("user@example.com")
await config_set_default_project("PROJ-123")

# Simplified ticket creation
await ticket_create(title="Fix bug")
```

### From String-Based States

**Before:**
```python
# Manual state management
await ticket_update(ticket_id, state="in_progress")
```

**After:**
```python
# Validated transitions with comments
await ticket_transition(
    ticket_id,
    "in_progress",
    "Starting work on this ticket"
)
```

---

## Troubleshooting

### "No default user configured" Error

**Problem:** Calling `get_my_tickets()` without setting default user

**Solution:**
```python
await config_set_default_user("your@email.com")
```

### "Invalid transition" Error

**Problem:** Attempting invalid state transition

**Solution:**
```python
# Check valid transitions first
transitions = await get_available_transitions(ticket_id)
print(transitions["available_transitions"])
```

### Configuration Not Persisting

**Problem:** Changes not saved to config file

**Solution:** Ensure `.mcp-ticketer` directory is writable and not in `.gitignore` at root level

### Defaults Not Applied

**Problem:** Tickets created without default values

**Solution:** Verify configuration exists:
```python
config = await config_get()
print(config["config"])
```

---

## Future Enhancements

Potential additions for future versions:
- Bulk state transitions with validation
- User ticket analytics (velocity, completion rates)
- Configuration profiles for different team members
- Workflow customization per project
- State transition hooks for custom logic
