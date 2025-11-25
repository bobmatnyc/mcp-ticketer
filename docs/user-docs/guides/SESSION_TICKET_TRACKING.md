# Session Ticket Tracking

## Overview

mcp-ticketer includes session-based ticket tracking to help you associate your work with specific tickets.

## How It Works

### Session Lifecycle
- A session starts when you first use mcp-ticketer tools
- Sessions expire after **30 minutes of inactivity**
- Each session has a unique ID

### Ticket Association States

1. **Associated**: Work is linked to a specific ticket
2. **Opted Out**: You've chosen not to associate work with a ticket
3. **No Association**: Neither associated nor opted out (prompts for association)

## Using attach_ticket

### Associate with a Ticket
```python
attach_ticket(action="set", ticket_id="PROJ-123")
```

### Check Current Status
```python
attach_ticket(action="status")
```

### Opt Out for This Session
```python
attach_ticket(action="none")
```

### Clear Association
```python
attach_ticket(action="clear")
```

## Integration with ticket_create

When you create a ticket without specifying `parent_epic`:

1. **If ticket associated**: Uses session ticket as parent
2. **If opted out**: Proceeds without parent_epic
3. **If no decision**: Prompts you to associate or opt out

## Best Practices

- Associate work with tickets at the start of your session
- Use `attach_ticket(action="status")` to check current association
- Opt out consciously if work isn't ticket-related

## Session Storage

Session state is stored in `.mcp-ticketer/session.json` and includes:
- Session ID
- Current ticket association
- Opt-out status
- Last activity timestamp

## Example Workflow

```python
# Start of work session
attach_ticket(action="set", ticket_id="EPIC-001")

# Create child tickets - automatically linked to EPIC-001
ticket_create(title="Implement login page")
ticket_create(title="Add password validation")
ticket_create(title="Create user registration flow")

# Check current association
attach_ticket(action="status")

# Work on unrelated task
attach_ticket(action="clear")
ticket_create(title="Update documentation", parent_epic="DOC-005")

# Opt out for exploratory work
attach_ticket(action="none")
ticket_create(title="Research new framework options")
```

## API Reference

### attach_ticket

**Parameters:**
- `action` (string, required): Action to perform
  - `"set"`: Associate with a ticket
  - `"clear"`: Remove association
  - `"none"`: Opt out of association
  - `"status"`: Check current status
- `ticket_id` (string, optional): Ticket ID (required for `action="set"`)

**Returns:**
```json
{
  "success": true,
  "message": "Work session now associated with ticket: PROJ-123",
  "current_ticket": "PROJ-123",
  "session_id": "uuid-here",
  "opted_out": false
}
```

### get_session_info

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "session_id": "uuid-here",
  "current_ticket": "PROJ-123",
  "opted_out": false,
  "last_activity": "2025-01-19T20:00:00",
  "session_timeout_minutes": 30
}
```

## Troubleshooting

### Session Not Persisting
- Check that `.mcp-ticketer/` directory has write permissions
- Verify session hasn't expired (30-minute timeout)

### Unexpected Prompts
- Check session status: `attach_ticket(action="status")`
- Ensure you've opted out if you don't want association: `attach_ticket(action="none")`

### Session File Location
The session state file is stored at:
```
<project-root>/.mcp-ticketer/session.json
```

This file is automatically created and managed by mcp-ticketer. You generally don't need to edit it manually.
