# Linear Integration Setup Guide

This guide explains how to set up and use the Linear adapter with mcp-ticketer.

## Prerequisites

1. A Linear account with access to a team
2. A Linear API key
3. Your Linear team URL, team key, or team ID (see below for easy setup options)

## Getting Your Linear API Key

1. Go to Linear Settings → API → Personal API keys
2. Click "Create key"
3. Give it a descriptive name like "MCP Ticketer"
4. Copy the generated API key

## Finding Your Team Information

### Option 1: Using Team URL (Easiest - Recommended)

The easiest way to configure your Linear team is to use your team's URL:

1. Go to your Linear workspace
2. Navigate to your team's issues page (the main view where you see your team's work)
3. Copy the full URL from your browser's address bar
4. Use it during setup - the system will automatically extract your team key and resolve it to the team ID

**Supported URL formats:**
- `https://linear.app/your-org/team/ABC/active` - Full issues page URL
- `https://linear.app/your-org/team/ABC/` - Team page URL
- `https://linear.app/your-org/team/ABC` - Short form URL

**Example:**
If your team URL is `https://linear.app/acme-corp/team/ENG/active`:
- Team key extracted: `ENG`
- System automatically resolves `ENG` to your team ID

### Option 2: Using Team Key (Manual)

1. In Linear, go to Settings → Teams
2. Click on your team
3. Look for the "Key" field (e.g., "ENG", "DESIGN", "PRODUCT")
4. This is a short, human-readable identifier

### Option 3: Using Team ID (Advanced)

1. In Linear, go to Settings → Teams
2. Click on your team
3. The team ID is in the URL: `linear.app/YOUR-TEAM-ID/...`
4. Or check the team settings page for the UUID-based ID

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

### Option 1: Using Team URL (Easiest - Recommended)

Simply paste your Linear team's issues URL:

```bash
# Set your API key in environment
export LINEAR_API_KEY=lin_api_YOUR_KEY_HERE

# Initialize with your team URL (paste directly from browser)
mcp-ticketer init --adapter linear --team-url https://linear.app/your-org/team/ENG/active
```

The system will automatically:
1. Extract the team key from the URL (`ENG` in this example)
2. Use the Linear API to resolve the team key to your team ID
3. Save the configuration with the resolved team ID

### Option 2: Using Team Key

If you prefer to enter your team key directly:

```bash
# Set your API key in environment
export LINEAR_API_KEY=lin_api_YOUR_KEY_HERE

# Initialize with team key
mcp-ticketer init --adapter linear --team-key ENG
```

### Option 3: Using Team ID (Advanced)

For direct team ID configuration:

```bash
# Set your API key in environment
export LINEAR_API_KEY=lin_api_YOUR_KEY_HERE

# Initialize with team ID
mcp-ticketer init --adapter linear --team-id YOUR-TEAM-ID
```

### Option 4: Using .env File

Create a `.env` file in your project root:

```bash
LINEAR_API_KEY=lin_api_YOUR_KEY_HERE
# Choose one of:
LINEAR_TEAM_URL=https://linear.app/your-org/team/ENG/active
# OR
LINEAR_TEAM_KEY=ENG
# OR
LINEAR_TEAM_ID=YOUR-TEAM-ID
```

Then initialize:

```bash
mcp-ticketer init --adapter linear
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

### Using the Doctor Command

Test your Linear configuration with the diagnostic tool:

```bash
# Run diagnostics to check your setup
mcp-ticketer doctor

# This will check:
# - Adapter configuration validity
# - API credential authentication
# - Team ID resolution
# - Network connectivity
# - Recent error logs
```

**Note**: The `diagnose` command is still available as an alias for backward compatibility.

### Authentication Error

If you get an authentication error, verify:
1. Your API key is correct
2. The API key has proper permissions
3. The environment variable is set correctly

Run `mcp-ticketer doctor` to test your authentication.

### Team Not Found

If the team cannot be found:
1. Verify your team URL, key, or ID is correct
2. Ensure you have access to the team in Linear
3. Try using the team URL method (easiest and most reliable)
4. Run `mcp-ticketer doctor` to see detailed error information

**Example with team URL:**
```bash
mcp-ticketer init --adapter linear --team-url https://linear.app/your-org/team/ENG/active
```

### Rate Limiting

Linear's API has rate limits. If you hit them, the adapter will return errors. Wait a moment and retry.

### Team URL Not Recognized

If your team URL isn't being recognized:
1. Ensure it matches one of the supported formats:
   - `https://linear.app/your-org/team/ABC/active`
   - `https://linear.app/your-org/team/ABC/`
   - `https://linear.app/your-org/team/ABC`
2. Copy the URL directly from your browser's address bar
3. Make sure the URL contains `/team/` followed by your team key

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