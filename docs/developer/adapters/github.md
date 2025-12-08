# GitHub Adapter Documentation

The GitHub adapter provides comprehensive integration with GitHub Issues, supporting both REST API v3 and GraphQL API v4 for optimal performance and feature coverage.

## Features

### Core Functionality
- **Issue Management**: Create, read, update, and delete GitHub issues
- **State Management**: Maps GitHub's simple open/closed states to extended states using labels
- **Priority Support**: Implements priority levels through configurable label schemes
- **Comments**: Full comment support with reactions tracking
- **Search**: Advanced search using GitHub's search syntax
- **Milestones**: Treat GitHub milestones as Epics
- **Rate Limiting**: Automatic rate limit tracking and reporting

### Extended Features
- **GitHub Projects v2**: Optional integration with new GitHub Projects
- **Pull Request Linking**: Track issue-PR relationships
- **Label Management**: Automatic label creation and management
- **Cross-Repository References**: Support for cross-repo issue references
- **GitHub Enterprise**: Compatible with GitHub Enterprise Server

## Configuration

### Environment Variables
```bash
export GITHUB_TOKEN="ghp_your_personal_access_token"

# Option 1: Using repository URL (Recommended)
export GITHUB_REPO_URL="https://github.com/owner/repo"

# Option 2: Using separate owner/repo (Fallback)
export GITHUB_OWNER="repository_owner"
export GITHUB_REPO="repository_name"
```

### CLI Configuration
```bash
# Option 1: Interactive wizard (recommended)
mcp-ticket init --adapter github

# Option 2: Non-interactive with URL
mcp-ticket init --adapter github \
  --repo-url "https://github.com/your-org/your-repo" \
  --github-token "ghp_your_token"

# Option 3: Non-interactive with separate owner/repo (backward compatible)
mcp-ticket init --adapter github \
  --github-owner "your-org" \
  --github-repo "your-repo" \
  --github-token "ghp_your_token"
```

### Programmatic Configuration
```python
from mcp_ticketer.adapters.github import GitHubAdapter

adapter = GitHubAdapter({
    "owner": "your-org",
    "repo": "your-repo",
    "token": "ghp_your_token",
    "api_url": "https://api.github.com",  # Optional, for GitHub Enterprise
    "use_projects_v2": False,  # Optional, enable Projects v2 integration
    "custom_priority_scheme": {  # Optional, custom priority labels
        "critical": ["P0", "urgent", "blocker"],
        "high": ["P1", "important"],
        "medium": ["P2", "normal"],
        "low": ["P3", "minor"],
    }
})
```

## State Mapping

GitHub only supports two native states (open/closed), so we use labels for extended state management:

| Universal State | GitHub State | Label |
|----------------|--------------|-------|
| OPEN | open | - |
| IN_PROGRESS | open | `in-progress` |
| READY | open | `ready` |
| TESTED | open | `tested` |
| WAITING | open | `waiting` |
| BLOCKED | open | `blocked` |
| DONE | closed | - |
| CLOSED | closed | - |

The adapter automatically creates and manages these state labels.

## Priority Mapping

Priorities are managed through labels with configurable schemes:

### Default Priority Labels
| Priority | Default Labels |
|----------|---------------|
| CRITICAL | `P0`, `critical`, `urgent` |
| HIGH | `P1`, `high` |
| MEDIUM | `P2`, `medium` |
| LOW | `P3`, `low` |

### Custom Priority Schemes
You can configure custom priority label mappings:

```python
config = {
    "custom_priority_scheme": {
        "critical": ["severity-1", "blocker"],
        "high": ["severity-2", "major"],
        "medium": ["severity-3", "minor"],
        "low": ["severity-4", "trivial"],
    }
}
```

## Usage Examples

### Creating an Issue
```python
from mcp_ticketer.core.models import Task, Priority, TicketState

task = Task(
    title="Implement new feature",
    description="Detailed description with **markdown** support",
    priority=Priority.HIGH,
    state=TicketState.OPEN,
    tags=["feature", "enhancement"],
    assignee="username",
)

created_task = await adapter.create(task)
print(f"Created issue #{created_task.id}")
```

### Searching Issues
```python
from mcp_ticketer.core.models import SearchQuery

query = SearchQuery(
    query="bug fix",
    state=TicketState.IN_PROGRESS,
    priority=Priority.HIGH,
    tags=["bug", "critical"],
    assignee="developer",
    limit=20,
)

results = await adapter.search(query)
```

### Managing Milestones as Epics
```python
from mcp_ticketer.core.models import Epic

# Create a milestone
epic = Epic(
    title="Version 2.0 Release",
    description="Major release milestone",
    state=TicketState.OPEN,
)

milestone = await adapter.create_milestone(epic)

# List milestones
milestones = await adapter.list_milestones(state="open", limit=10)
```

### Working with Comments
```python
from mcp_ticketer.core.models import Comment

# Add a comment
comment = Comment(
    ticket_id="123",
    content="This has been fixed in PR #456",
)
created_comment = await adapter.add_comment(comment)

# Get comments
comments = await adapter.get_comments("123", limit=50)
```

## GitHub-Specific Features

### Epic Updates (Milestones)

GitHub milestones serve as epics in mcp-ticketer. The adapter provides full milestone update capabilities:

```python
# Update milestone (epic)
updated_epic = await adapter.update_epic(
    epic_id="milestone-5",  # or just "5"
    updates={
        "title": "v2.0 Release",
        "description": "Major release with breaking changes",
        "state": "open",  # open or closed
        "target_date": "2025-06-01"  # due_on in GitHub
    }
)

# Alternative: Direct milestone update
updated_milestone = await adapter.update_milestone(
    milestone_number=5,
    title="v2.0 Release",
    description="Updated milestone description",
    state="open",
    due_on="2025-06-01T00:00:00Z"
)
```

**Supported Fields:**
- `title`: Milestone title
- `description`: Milestone description (full Markdown support)
- `state`: Either `open` or `closed`
- `target_date`: Due date in ISO 8601 format

**Limitations:**
- Only binary state (open/closed), no intermediate states
- No priority field (use labels on issues instead)
- No visual customization (colors, icons)

### File Attachments

**Important**: GitHub Issues does not provide a native file attachment API. The adapter implements workarounds:

#### For Issues: Comment References

```python
# Attempts to attach file, creates comment with reference
result = await adapter.add_attachment(
    ticket_id="123",  # Issue number
    file_path="/path/to/file.pdf",
    description="Requirements document"
)

# Returns guidance:
# {
#   "method": "github_comment_reference",
#   "message": "Created comment with file reference. To upload file:",
#   "instructions": [
#     "1. Open issue #123 in browser",
#     "2. Drag and drop file into a comment",
#     "3. GitHub will generate markdown link automatically"
#   ]
# }
```

#### For Milestones: URL References

```python
# Add URL reference to milestone description
await adapter.add_attachment_reference_to_milestone(
    milestone_number=5,
    url="https://drive.google.com/file/d/xyz",
    description="Project Charter (external link)"
)

# Updates milestone description with:
# ## Attachments
# - [Project Charter (external link)](https://drive.google.com/file/d/xyz)
```

#### Manual Upload Process

For actual file uploads to issues:

1. Open the issue in your browser
2. Drag and drop the file into a comment box
3. GitHub automatically uploads and generates a markdown link
4. Save the comment with the file reference

**File Size Limit**: 25 MB per file

**Recommended Approach**: Use external file storage (Google Drive, Dropbox) and add URL references.

### Issue Templates
The adapter respects GitHub issue templates when creating issues. Include template fields in the description.

### Pull Request Linking
Link issues to pull requests:
```python
await adapter.link_to_pull_request(issue_number=123, pr_number=456)
```

### Rate Limit Monitoring
```python
rate_limit = await adapter.get_rate_limit()
core = rate_limit["resources"]["core"]
print(f"API calls remaining: {core['remaining']}/{core['limit']}")
```

### GraphQL Support
The adapter uses GraphQL for complex queries and batch operations, providing better performance for:
- Search operations
- Fetching issues with all related data
- Batch updates

## Authentication

### Personal Access Token (PAT)
1. Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Generate a new token with scopes:
   - `repo` (for private repositories)
   - `public_repo` (for public repositories only)
   - `write:discussion` (optional, for discussions)
   - `project` (optional, for Projects access)

### GitHub App (Future)
Support for GitHub App authentication is planned for enhanced security and higher rate limits.

## Best Practices

1. **Label Naming**: Use consistent label naming conventions
2. **Rate Limits**: Monitor rate limits for high-volume operations
3. **Batch Operations**: Use search and list operations instead of multiple individual reads
4. **Caching**: The adapter caches labels and milestones to reduce API calls
5. **Error Handling**: Always handle rate limit and permission errors gracefully

## Limitations

1. **State Transitions**: GitHub doesn't enforce state transition rules natively
2. **Binary States**: Milestones only support open/closed (no intermediate states)
3. **No Native Attachments**: Issues lack a file attachment API
   - Workaround: Manual drag-and-drop or external file hosting
   - 25 MB file size limit for issue comments
4. **Milestone Attachments**: Cannot attach files to milestones
   - Workaround: Add URL references to external files
5. **Time Tracking**: No built-in time tracking (use issue comments or Projects)
6. **Custom Fields**: Limited to labels and Projects for custom metadata
7. **Bulk Operations**: Some bulk operations require multiple API calls

## Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check your PAT is valid and has correct scopes
2. **404 Not Found**: Verify repository owner and name are correct
3. **403 Rate Limited**: You've exceeded API rate limits, wait or upgrade
4. **422 Validation Failed**: Check required fields and valid values

### Debug Mode
Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Migration from Other Systems

### From JIRA
- Map JIRA issue types to GitHub labels
- Convert JIRA workflows to label-based states
- Migrate attachments to issue comments with links

### From Linear
- Map Linear projects to GitHub milestones
- Convert Linear states to GitHub labels
- Preserve relationships through issue references

## API Reference

See the main adapter documentation for the complete API reference. The GitHub adapter implements all methods from the `BaseAdapter` class with GitHub-specific optimizations.