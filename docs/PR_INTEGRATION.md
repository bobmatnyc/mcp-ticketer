# Pull Request Integration Guide

The mcp-ticketer now supports creating and linking GitHub pull requests to tickets across different issue tracking systems.

## Features

### 1. Create Pull Requests from Tickets
- Automatically generate PR titles with ticket IDs
- Include ticket links in PR descriptions
- Auto-generate branch names from ticket IDs and titles
- Support for draft PRs

### 2. Link Existing PRs to Tickets
- Link any GitHub PR to a ticket
- Automatic bidirectional references
- Comments added to both PR and ticket

### 3. Multi-Platform Support
- **GitHub Issues**: Full PR creation and linking
- **Linear**: PR metadata and GitHub attachment linking

## MCP Tools

### `ticket_create_pr`
Create a new GitHub pull request linked to a ticket.

**Parameters:**
- `ticket_id` (required): The ticket ID to link the PR to
- `base_branch`: Target branch (default: "main")
- `head_branch`: Source branch name (auto-generated if not provided)
- `title`: PR title (uses ticket title if not provided)
- `body`: PR description (auto-generated with issue link if not provided)
- `draft`: Create as draft PR (default: false)

**Example:**
```json
{
  "name": "ticket_create_pr",
  "arguments": {
    "ticket_id": "123",
    "base_branch": "main",
    "draft": true
  }
}
```

### `ticket_link_pr`
Link an existing pull request to a ticket.

**Parameters:**
- `ticket_id` (required): The ticket ID to link the PR to
- `pr_url` (required): GitHub PR URL to link

**Example:**
```json
{
  "name": "ticket_link_pr",
  "arguments": {
    "ticket_id": "123",
    "pr_url": "https://github.com/owner/repo/pull/456"
  }
}
```

## Adapter-Specific Features

### GitHub Adapter

The GitHub adapter provides full PR management capabilities:

1. **Direct PR Creation**: Creates actual GitHub pull requests
2. **Branch Management**: Automatically creates branches if they don't exist
3. **Issue Linking**: Uses GitHub's native issue linking (e.g., "Fixes #123")
4. **Bidirectional Updates**: Comments added to both issue and PR

```python
# Example: Create PR for GitHub issue
adapter = GitHubAdapter(config)
result = await adapter.create_pull_request(
    ticket_id="123",
    base_branch="main",
    title="Fix authentication bug",
    draft=True
)
```

### Linear Adapter

The Linear adapter integrates with Linear's GitHub attachment system:

1. **Branch Name Management**: Sets branch names in Linear issues
2. **GitHub Attachments**: Creates GitHub PR attachments in Linear
3. **Metadata Tracking**: Stores PR information in issue metadata

```python
# Example: Link PR to Linear issue
adapter = LinearAdapter(config)
result = await adapter.link_to_pull_request(
    ticket_id="ENG-123",
    pr_url="https://github.com/owner/repo/pull/456"
)
```

## Workflow Examples

### 1. Create PR from GitHub Issue
```python
# Create issue
issue = await github_adapter.create(Task(
    title="Add user authentication",
    description="Implement JWT authentication"
))

# Create PR for the issue
pr = await github_adapter.create_pull_request(
    ticket_id=issue.id,
    base_branch="main"
)
print(f"PR created: {pr['url']}")
```

### 2. Link PR to Linear Issue
```python
# Create Linear issue
issue = await linear_adapter.create(Task(
    title="Refactor database layer",
    description="Optimize database queries"
))

# Set branch name for Linear issue
pr_metadata = await linear_adapter.create_pull_request_for_issue(
    ticket_id=issue.id,
    github_config={
        "owner": "myorg",
        "repo": "myrepo",
        "base_branch": "develop"
    }
)

# After creating PR in GitHub, link it back
await linear_adapter.link_to_pull_request(
    ticket_id=issue.id,
    pr_url="https://github.com/myorg/myrepo/pull/789"
)
```

### 3. Using MCP Server
```python
# Via MCP server with automatic adapter detection
server = MCPTicketServer(adapter_type="github", config=github_config)

# Create PR through MCP tool
result = await server._handle_tools_call({
    "name": "ticket_create_pr",
    "arguments": {
        "ticket_id": "456",
        "base_branch": "develop",
        "draft": true
    }
})
```

## Configuration

### GitHub Configuration
```json
{
  "adapter_type": "github",
  "config": {
    "token": "ghp_...",
    "owner": "organization",
    "repo": "repository"
  }
}
```

### Linear Configuration with GitHub Integration
```json
{
  "adapter_type": "linear",
  "config": {
    "api_key": "lin_api_...",
    "team_key": "ENG",
    "github_owner": "organization",
    "github_repo": "repository"
  }
}
```

## Best Practices

1. **Branch Naming Convention**: Let the system auto-generate branch names for consistency
2. **PR Templates**: Use custom PR body templates for standardized descriptions
3. **Draft PRs**: Start with draft PRs for work in progress
4. **Linking Strategy**: Always link PRs to tickets for traceability
5. **Comments**: System automatically adds comments for audit trail

## Error Handling

The PR operations handle various error cases:
- Invalid ticket IDs
- Missing GitHub permissions
- Branch conflicts
- Network failures
- Invalid PR URLs

All errors are returned with descriptive messages to help diagnose issues.

## Testing

Run the test script to verify PR functionality:
```bash
python test_pr_functionality.py
```

Set environment variables for testing:
```bash
export GITHUB_TOKEN="your_github_token"
export GITHUB_OWNER="your_github_owner"
export GITHUB_REPO="your_github_repo"
export LINEAR_API_KEY="your_linear_api_key"
export LINEAR_TEAM_KEY="your_team_key"
```