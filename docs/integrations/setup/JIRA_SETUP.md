# JIRA Adapter Setup Guide

This guide walks you through setting up the JIRA adapter for mcp-ticketer.

## Prerequisites

- JIRA Cloud or JIRA Server account
- API token (for Cloud) or password (for Server)
- Project access permissions

## Installation

Install the JIRA Python library (optional dependency):

```bash
pip install jira>=3.5.0
# or
pip install mcp-ticketer[jira]
```

## Configuration

### 1. Generate API Token (JIRA Cloud)

1. Go to [Atlassian API Tokens](https://id.atlassian.com/manage/api-tokens)
2. Click "Create API token"
3. Give it a descriptive name (e.g., "mcp-ticketer")
4. Copy the generated token

### 2. Set Environment Variables

Create a `.env` file or export these variables:

```bash
export JIRA_SERVER="https://yourcompany.atlassian.net"  # Your JIRA URL
export JIRA_EMAIL="your.email@company.com"              # Your JIRA email
export JIRA_API_TOKEN="your-api-token-here"            # API token from step 1
export JIRA_PROJECT_KEY="PROJ"                         # Optional: default project
```

### 3. Initialize MCP Ticketer

```bash
# Using environment variables
mcp-ticket init --adapter jira

# Or specify directly
mcp-ticket init \
  --adapter jira \
  --jira-server https://yourcompany.atlassian.net \
  --jira-email your.email@company.com \
  --api-key your-api-token \
  --jira-project PROJ
```

## Usage Examples

### Create a Task

```bash
# Create a simple task
mcp-ticket create "Fix login bug" \
  --description "Users unable to login with SSO" \
  --priority high

# Create with tags
mcp-ticket create "Add dark mode" \
  --tag frontend \
  --tag ui \
  --priority medium
```

### List Tasks

```bash
# List recent tasks
mcp-ticket list

# List with filters
mcp-ticket list --state in_progress --limit 20

# List high priority tasks
mcp-ticket list --priority high
```

### Search Tasks

```bash
# Search by text
mcp-ticket search "authentication"

# Search with filters
mcp-ticket search --state open --priority high

# Search by assignee
mcp-ticket search --assignee "john.doe"
```

### Update Task State

```bash
# Move to in progress
mcp-ticket update PROJ-123 --state in_progress

# Mark as done
mcp-ticket update PROJ-123 --state done

# Update with comment
mcp-ticket comment PROJ-123 "Started working on this"
```

### Advanced JQL Queries

The JIRA adapter supports native JQL queries through the search functionality:

```python
from mcp_ticketer.adapters.jira import JiraAdapter

adapter = JiraAdapter(config)

# Execute custom JQL
results = await adapter.execute_jql(
    "project = PROJ AND status = 'In Progress' AND assignee = currentUser()",
    limit=50
)
```

## JIRA-Specific Features

### Issue Types

The adapter maps JIRA issue types to our universal model:
- **Epic** → Epic
- **Story/Task/Bug** → Task
- **Sub-task** → Task (with parent)

### State Mapping

JIRA states are dynamically mapped based on workflow:

| Universal State | Common JIRA States |
|----------------|-------------------|
| `open` | To Do, Open, New |
| `in_progress` | In Progress, In Development |
| `ready` | In Review, Ready for Test |
| `tested` | Testing, QA |
| `done` | Done, Resolved |
| `blocked` | Blocked, On Hold |
| `closed` | Closed |

### Priority Mapping

| Universal Priority | JIRA Priority |
|-------------------|---------------|
| `critical` | Highest, Blocker |
| `high` | High |
| `medium` | Medium |
| `low` | Low, Lowest |

### Custom Fields

The adapter preserves JIRA custom fields in the metadata:

```python
task = await adapter.read("PROJ-123")
custom_fields = task.metadata["jira"]
```

### Sprint Support (JIRA Software)

Get active sprints:

```python
sprints = await adapter.get_sprints(board_id=1)
```

## Testing

Run the test script to verify your setup:

```bash
python test_jira.py
```

This will:
1. Create a test task
2. Update its properties
3. Add comments
4. Test state transitions
5. Search and list tasks
6. Optionally clean up

## Troubleshooting

### Authentication Issues

**Error: 401 Unauthorized**
- Verify your email and API token are correct
- For JIRA Server, you might need to use password instead of API token
- Check if your account has the necessary permissions

### Project Not Found

**Error: Project key not found**
- Verify the project key exists
- Check you have access to the project
- Try listing all projects first

### State Transitions

**Error: Invalid transition**
- JIRA workflows are project-specific
- Some transitions may require specific permissions
- Check available transitions for the issue's current state

### Rate Limiting

**Error: 429 Too Many Requests**
- The adapter includes automatic retry with exponential backoff
- For bulk operations, consider adding delays
- Check your JIRA plan's API rate limits

## JIRA Server vs Cloud

### Configuration Differences

```python
# JIRA Cloud (default)
config = {
    "server": "https://company.atlassian.net",
    "cloud": True,  # Default
    "api_token": "your-token"
}

# JIRA Server/Data Center
config = {
    "server": "https://jira.company.com",
    "cloud": False,
    "api_token": "your-password"  # Uses password for Server
}
```

### API Differences

- Cloud uses REST API v3
- Server uses REST API v2
- Some features may not be available on Server

## Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `JIRA_SERVER` | JIRA server URL | Yes |
| `JIRA_EMAIL` | User email for authentication | Yes |
| `JIRA_API_TOKEN` | API token (Cloud) or password (Server) | Yes |
| `JIRA_PROJECT_KEY` | Default project key | No |

## Links

- [JIRA REST API Documentation](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- [Create API Token](https://id.atlassian.com/manage/api-tokens)
- [JQL Reference](https://support.atlassian.com/jira-software-cloud/docs/advanced-search-reference-jql-fields/)
- [JIRA Python Library](https://jira.readthedocs.io/)