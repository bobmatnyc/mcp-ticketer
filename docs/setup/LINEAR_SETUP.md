# Linear Integration Setup Guide

This guide explains how to set up and use the Linear adapter with mcp-ticketer.

## Prerequisites

1. A Linear account with access to a team
2. A Linear API key
3. Your Linear team ID

## Getting Your Linear API Key

1. Go to Linear Settings → API → Personal API keys
2. Click "Create key"
3. Give it a descriptive name like "MCP Ticketer"
4. Copy the generated API key

## Finding Your Team ID

1. In Linear, go to Settings → Teams
2. Click on your team
3. The team ID is in the URL: `linear.app/YOUR-TEAM-ID/...`
4. Or check the team settings page for the ID

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Or if using the package:

```bash
pip install mcp-ticketer[linear]
```

## Configuration

### Option 1: Using Environment Variables (Recommended)

Create a `.env` file in your project root:

```bash
LINEAR_API_KEY=lin_api_YOUR_KEY_HERE
```

Then initialize with your team ID:

```bash
mcp-ticket init --adapter linear --team-id YOUR-TEAM-ID
```

### Option 2: Direct Configuration

```bash
mcp-ticket init \
  --adapter linear \
  --team-id YOUR-TEAM-ID \
  --api-key lin_api_YOUR_KEY_HERE
```

## Usage Examples

### Create an Issue

```bash
mcp-ticket create "Fix login bug" \
  --description "Users can't log in with Google OAuth" \
  --priority high \
  --tag "bug" \
  --tag "auth"
```

### List Issues

```bash
# List all issues
mcp-ticket list

# Filter by state
mcp-ticket list --state in_progress

# Filter by priority
mcp-ticket list --priority critical --limit 20
```

### Search Issues

```bash
# Search by text
mcp-ticket search "authentication"

# Search with filters
mcp-ticket search --state open --priority high --assignee "user@example.com"
```

### Update an Issue

```bash
# Update title and priority
mcp-ticket update ISSUE-123 \
  --title "Updated title" \
  --priority critical

# Assign to someone
mcp-ticket update ISSUE-123 --assignee "user@example.com"
```

### Transition State

```bash
# Move to in progress
mcp-ticket transition ISSUE-123 in_progress

# Mark as done
mcp-ticket transition ISSUE-123 done
```

### View Issue Details

```bash
# Show issue details
mcp-ticket show ISSUE-123

# Include comments
mcp-ticket show ISSUE-123 --comments
```

## State Mapping

The adapter maps between mcp-ticketer states and Linear workflow states:

| MCP Ticketer State | Linear State Type |
|-------------------|-------------------|
| open              | backlog/unstarted |
| in_progress       | started           |
| ready             | in_review         |
| tested            | in_review         |
| done              | completed         |
| waiting           | todo              |
| blocked           | todo + "blocked" label |
| closed            | canceled          |

## Priority Mapping

| MCP Ticketer Priority | Linear Priority |
|----------------------|-----------------|
| critical             | 1 (Urgent)      |
| high                 | 2 (High)        |
| medium               | 3 (Medium)      |
| low                  | 4 (Low)         |

## Features Supported

✅ Create issues
✅ Read/view issues
✅ Update issues
✅ Delete (archive) issues
✅ List issues with filters
✅ Search issues
✅ State transitions
✅ Comments (add and view)
✅ Priority management
✅ Labels/tags
✅ Parent/child relationships

## Limitations

- Assignee updates require user lookup (not yet implemented)
- Custom fields are not yet supported
- Attachments are not supported
- Webhook events for real-time sync not yet implemented

## Troubleshooting

### Authentication Error

If you get an authentication error, verify:
1. Your API key is correct
2. The API key has proper permissions
3. The environment variable is set correctly

### Team Not Found

Ensure your team ID is correct. You can verify it in Linear's settings.

### Rate Limiting

Linear's API has rate limits. If you hit them, the adapter will return errors. Wait a moment and retry.

## Programmatic Usage

```python
from mcp_ticketer.core import AdapterRegistry, Task, Priority, TicketState

# Initialize Linear adapter
config = {
    "api_key": "lin_api_YOUR_KEY",
    "team_id": "YOUR-TEAM-ID"
}
adapter = AdapterRegistry.get_adapter("linear", config)

# Create a task
task = Task(
    title="New feature",
    description="Implement user dashboard",
    priority=Priority.HIGH,
    tags=["feature", "frontend"]
)

created = await adapter.create(task)
print(f"Created: {created.id}")

# Search tasks
from mcp_ticketer.core.models import SearchQuery

query = SearchQuery(
    query="dashboard",
    state=TicketState.OPEN,
    priority=Priority.HIGH
)
results = await adapter.search(query)
```

## Contributing

To contribute to the Linear adapter:

1. Check existing issues in the repository
2. Create tests for new features
3. Follow the existing code patterns
4. Update this documentation as needed