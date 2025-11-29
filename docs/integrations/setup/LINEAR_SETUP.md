# Linear Integration Setup Guide

This guide explains how to set up and use the Linear adapter with mcp-ticketer.

> **Note:** For detailed information about how Linear URLs are handled, see [Linear URL Handling Guide](../../developer-docs/adapters/LINEAR_URL_HANDLING.md).

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

## Known Issues and Fixes

### Fixed in v1.1.1: Label Creation Argument Validation Error

**Issue**: Prior to v1.1.1, creating Linear issues with labels would fail with an "Argument Validation Error".

**Error Messages**:
```
Linear API transport error: {'message': 'Argument Validation Error', 'path': ['issueCreate']}
```

Or:

```
Variable '$labelIds' of required type '[String!]!' was provided invalid value
```

**Root Cause**: The Linear GraphQL API requires `labelIds` to be UUID strings (e.g., `["uuid-1", "uuid-2"]`), not label names (e.g., `["bug", "feature"]`). Earlier versions incorrectly passed label names.

**Status**: ✅ **FIXED in v1.1.1** (released 2025-11-21)

**Solution**: Upgrade to v1.1.1 or later:

```bash
pip install --upgrade mcp-ticketer
```

After upgrading, labels will work correctly:

```bash
mcp-ticket create "Fix login bug" \
  --description "Users can't log in" \
  --priority high \
  --tag "bug" \
  --tag "auth"  # ✅ Labels now work!
```

**Technical Details**:
- The fix ensures `labelIds` is always sent as a non-null array of non-null UUID strings
- Label names are now properly resolved to UUIDs before API calls
- UUID validation prevents type mismatches

**See Also**: [TROUBLESHOOTING.md](../../TROUBLESHOOTING.md#issue-argument-validation-error-when-creating-issues-with-labels) for detailed troubleshooting

---

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

## Linear Practical Workflow CLI

For daily Linear operations, you can use the dedicated workflow CLI script that provides quick shortcuts for common tasks:

### Quick Start

```bash
# Setup (one-time)
cp ops/scripts/linear/.env.example .env
# Edit .env with your LINEAR_API_KEY and LINEAR_TEAM_KEY

# Create tickets with auto-tagging
./ops/scripts/linear/practical-workflow.sh create-bug "Login fails" "Error 500" --priority high
./ops/scripts/linear/practical-workflow.sh create-feature "Dark mode" "Add theme toggle"
./ops/scripts/linear/practical-workflow.sh create-task "Update docs" "Refresh API docs"

# Workflow shortcuts
./ops/scripts/linear/practical-workflow.sh start-work BTA-123
./ops/scripts/linear/practical-workflow.sh ready-review BTA-123
./ops/scripts/linear/practical-workflow.sh deployed BTA-123

# Comments
./ops/scripts/linear/practical-workflow.sh add-comment BTA-123 "Working on this now"
./ops/scripts/linear/practical-workflow.sh list-comments BTA-123
```

**Benefits:**
- **Auto-tagging**: Automatically applies `bug`, `feature`, or `task` labels
- **Quick commands**: Common workflow actions as single commands
- **Comment tracking**: Add and list comments directly from CLI
- **Environment validation**: Built-in configuration checks

For complete documentation, see [Linear Workflow CLI Guide](../../../ops/scripts/linear/README.md).

## Project Status Updates

Track project progress with status updates and health indicators. Project updates help teams communicate progress, identify blockers, and maintain alignment on project goals.

### What are Project Updates?

Project updates are periodic status communications that include:
- **Progress summary**: What was accomplished
- **Health indicator**: Current project health status
- **Blockers**: Issues or dependencies affecting progress
- **Next steps**: Planned work items

### When to Use Project Updates

Use project updates for:
- **Weekly updates**: Regular progress check-ins for active projects
- **Milestone completion**: Celebrating significant achievements
- **Blockers**: Communicating issues that need attention
- **Status changes**: Transitioning between health states (e.g., on_track → at_risk)
- **Team communication**: Keeping stakeholders informed

### CLI Usage Examples

#### Create Project Update

```bash
# Create update with health indicator
mcp-ticketer project-update create "mcp-ticketer-eac28953c267" \
  "Completed MCP tools implementation. CLI commands in progress." \
  --health on_track

# Create update using full URL
mcp-ticketer project-update create \
  "https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267/updates" \
  "Sprint review completed successfully. All acceptance criteria met." \
  --health on_track

# Create update using UUID
mcp-ticketer project-update create "550e8400-e29b-41d4-a716-446655440000" \
  "Deployment delayed due to infrastructure issues." \
  --health at_risk

# Create update using short ID
mcp-ticketer project-update create "eac28953c267" \
  "Project completed ahead of schedule!" \
  --health complete
```

#### List Project Updates

```bash
# List recent updates (default: 10)
mcp-ticketer project-update list "mcp-ticketer-eac28953c267"

# List more updates with custom limit
mcp-ticketer project-update list "mcp-ticketer-eac28953c267" --limit 20

# List updates using full URL
mcp-ticketer project-update list \
  "https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267"
```

#### Get Specific Update

```bash
# Get detailed information about a specific update
mcp-ticketer project-update get "update-uuid-here"
```

### Health Indicators

Project updates include a health indicator to quickly communicate project status:

| Status | Meaning | CLI Display | When to Use |
|--------|---------|-------------|-------------|
| `on_track` | Project progressing as planned | ✓ On Track (green) | Normal progress, no blockers |
| `at_risk` | Potential issues identified | ⚠ At Risk (yellow) | Minor delays or emerging issues |
| `off_track` | Significant blockers or delays | ✗ Off Track (red) | Major blockers, needs attention |
| `complete` | Project finished | ✓ Complete (blue) | Milestone or project completed |
| `inactive` | Project paused or cancelled | ○ Inactive (dim) | Work suspended or archived |

### Project Identification

MCP Ticketer supports multiple formats for project identification:

- **UUID**: `550e8400-e29b-41d4-a716-446655440000` - Full project identifier
- **Slug ID**: `mcp-ticketer-eac28953c267` - Human-readable project slug
- **Short ID**: `eac28953c267` - Just the unique portion
- **Full URL**: `https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267`
- **URL with suffix**: `https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267/updates`

All formats are automatically detected and resolved to the correct project.

### MCP Tools

For programmatic access, use the following MCP tools:

- **`project_update_create`**: Create a new project status update
- **`project_update_list`**: List project updates with pagination
- **`project_update_get`**: Get detailed information about a specific update

These tools are available when using MCP Ticketer with Claude Desktop or other MCP-compatible clients.

### Best Practices

**Use health indicators consistently:**
- Start with `on_track` for new projects
- Use `at_risk` early when issues emerge (don't wait until `off_track`)
- Update health status when conditions change
- Use `complete` to celebrate milestones

**Keep updates concise but informative:**
- Focus on key accomplishments and blockers
- Include specific ticket references when relevant
- Avoid jargon or overly technical details
- Use bullet points for clarity

**Update regularly:**
- Weekly updates for active projects
- More frequent updates during critical phases
- Less frequent for maintenance or low-priority projects
- Always update when health status changes

**Link to specific work:**
- Reference ticket IDs when mentioning work items
- Link to pull requests or documentation
- Provide context for technical decisions

### Programmatic Usage Example

```python
from mcp_ticketer.core import AdapterRegistry, ProjectUpdateHealth

# Initialize Linear adapter
config = {
    "api_key": "lin_api_YOUR_KEY",
    "team_id": "YOUR-TEAM-ID"
}
adapter = AdapterRegistry.get_adapter("linear", config)

# Create project update
update = await adapter.create_project_update(
    project_id="mcp-ticketer-eac28953c267",
    body="Sprint 12 completed successfully. All acceptance criteria met. "
         "Next sprint: Focus on documentation and testing.",
    health=ProjectUpdateHealth.ON_TRACK
)

print(f"Created update: {update.url}")
print(f"Health: {update.health}")

# List recent updates
updates = await adapter.list_project_updates(
    project_id="mcp-ticketer-eac28953c267",
    limit=10
)

for update in updates:
    print(f"{update.created_at}: {update.health} - {update.body[:50]}...")

# Get specific update
detailed = await adapter.get_project_update(update_id=update.id)
print(f"Author: {detailed.user.name}")
print(f"Created: {detailed.created_at}")
print(f"Health: {detailed.health}")
print(f"Body: {detailed.body}")
```

### Cross-Platform Support

Project updates are available across multiple platforms with adapter-specific implementations:

| Platform | Support | Implementation | Notes |
|----------|---------|----------------|-------|
| **Linear** | ✅ Native | GraphQL API (`projectUpdate` mutations) | Full feature support |
| **GitHub V2** | ✅ Native | Project status updates API | Recently added by GitHub |
| **Asana** | ✅ Native | Immutable project status updates | Cannot be edited after creation |
| **Jira** | ⚠️ Workaround | Comments on epic/project issue | No native project update support |

**Platform-specific notes:**
- **Linear**: Supports all health indicators and rich formatting
- **GitHub**: Health indicators mapped to GitHub's status system
- **Asana**: Updates are immutable once created (no editing)
- **Jira**: Updates are posted as comments on the epic/project issue

## Contributing

To contribute to the Linear adapter:

1. Check existing issues in the repository
2. Create tests for new features
3. Follow the existing code patterns
4. Update this documentation as needed