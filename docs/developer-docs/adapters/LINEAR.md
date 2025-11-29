# Linear Adapter Documentation

The Linear adapter provides comprehensive integration with Linear's modern issue tracking and project management platform through its native GraphQL API. This document covers the Linear adapter's core features, including recent enhancements for project assignment, label management, and flexible user assignment.

## Table of Contents

- [Overview](#overview)
- [URL Handling](#url-handling)
- [Configuration](#configuration)
- [Core Features](#core-features)
- [Enhanced Features](#enhanced-features)
  - [Project Assignment by URL/ID](#project-assignment-by-urlid)
  - [Enhanced Label Management](#enhanced-label-management)
  - [User Assignment by Username](#user-assignment-by-username)
  - [Priority Management](#priority-management)
- [Complete Usage Examples](#complete-usage-examples)
- [State Mapping](#state-mapping)
- [Troubleshooting](#troubleshooting)
- [API Reference](#api-reference)
- [Best Practices](#best-practices)

## Overview

Linear is a modern issue tracking and project management tool designed for software teams. The MCP Ticketer Linear adapter provides full integration with Linear's GraphQL API, supporting:

- **CRUD operations** for issues and projects
- **Flexible project assignment** using URLs, slugs, names, or IDs
- **Advanced label management** with add/replace/remove capabilities
- **Multi-format user assignment** by email, username, or display name
- **State transitions** and workflow management
- **Comment management** with full thread support
- **Epic/Issue/Task hierarchy** support

## URL Handling

The Linear adapter intelligently handles different Linear URL formats. All project URL variants (e.g., `/issues`, `/overview`, `/updates`) are treated identically because these are frontend-only routes. The adapter extracts the project ID and uses Linear's unified GraphQL API.

### Quick Overview

**All these URLs work identically:**
```
https://linear.app/workspace/project/my-project-abc123/issues
https://linear.app/workspace/project/my-project-abc123/overview
https://linear.app/workspace/project/my-project-abc123/updates
```

They all extract `my-project-abc123` and fetch the same project data.

### Understanding URL Suffixes

Linear's web UI uses different URL paths to show different views:
- `/issues` - Shows project issues list
- `/overview` - Shows project summary
- `/updates` - Shows status updates feed

**Important:** These suffixes are frontend routes only. Linear's GraphQL API doesn't distinguish between them. All project URLs query the same `project(id:)` endpoint.

### Getting Different Data Types

To access different types of project data, use the appropriate MCP tool:

| Data Type | MCP Tool | GraphQL Query |
|-----------|----------|---------------|
| Project metadata + issues | `epic_get(project_id)` | `project(id:)` + `issues()` |
| Project updates only | `project_update_list(project_id)` | `project(id:).projectUpdates` |
| Issues only | `epic_issues(project_id)` | `issues(filter: {project: ...})` |
| Single issue | `ticket_read(issue_id)` | `issue(id:)` |

**For detailed documentation**, see [Linear URL Handling Guide](LINEAR_URL_HANDLING.md).

## Configuration

### Environment Variables

```bash
export LINEAR_API_KEY="lin_api_your_personal_access_token"
export LINEAR_TEAM_ID="team-uuid-or-key"
```

### CLI Configuration

```bash
mcp-ticket init --adapter linear \
  --team-id "your-team-id" \
  --api-key "lin_api_your_token"
```

### Programmatic Configuration

```python
from mcp_ticketer.adapters.linear import LinearAdapter

adapter = LinearAdapter({
    "api_key": "lin_api_your_token",
    "team_id": "team-uuid-or-key",  # Team UUID or key (e.g., "ENG")
    "api_url": "https://api.linear.app/graphql",  # Optional
})
```

### Getting Your Linear API Key

1. Go to [Linear Settings > API](https://linear.app/settings/api)
2. Click "Create Personal API Key"
3. Give it a descriptive name (e.g., "MCP Ticketer")
4. Copy the generated key (starts with `lin_api_`)
5. Store it securely in your environment variables

### Finding Your Team ID

Your team ID can be found in several ways:

1. **From Linear URL**: `https://linear.app/your-workspace/team/TEAM/active` - the `TEAM` part is your team key
2. **Via GraphQL query**: Use the Linear API to list your teams
3. **Team UUID format**: `02d15669-7351-4451-9719-807576c16049`

## Core Features

### Issue Management

- **Create, read, update, delete** issues
- **State transitions** with workflow validation
- **Priority levels** (1-4 mapped to Critical-Low)
- **Rich text descriptions** with Markdown support
- **Assignee management** with flexible identifier support
- **Due dates** and estimation support

### Project (Epic) Management

- **Create and manage projects** (Linear's equivalent of Epics)
- **Link issues to projects** for organization
- **Project milestones** and progress tracking

### Comments

- **Add comments** to issues
- **Retrieve comment threads** with pagination
- **Markdown support** in comment content

### Search and Filtering

- **Text search** across titles and descriptions
- **State-based filtering** by workflow state
- **Priority filtering** by importance level
- **Tag/label filtering** for categorization
- **Assignee filtering** by user

## Enhanced Features

### Project Assignment by URL/ID

The Linear adapter supports multiple formats for assigning issues to projects, making it easy to link issues regardless of how you reference the project.

#### Supported Formats

1. **Full Project URL**
   ```python
   task.parent_epic = "https://linear.app/travel-bta/project/crm-smart-monitoring-system-f59a41a96c52/overview"
   ```

2. **Project Slug with Short ID**
   ```python
   task.parent_epic = "crm-smart-monitoring-system-f59a41a96c52"
   ```

3. **Project Slug (Name-based)**
   ```python
   task.parent_epic = "crm-smart-monitoring-system"
   ```

4. **Short ID Only**
   ```python
   task.parent_epic = "f59a41a96c52"
   ```

5. **Project Name**
   ```python
   task.parent_epic = "CRM Smart Monitoring System"
   ```

6. **Full UUID** (if you have it)
   ```python
   task.parent_epic = "02d15669-7351-4451-9719-807576c16049"
   ```

#### How It Works

The adapter intelligently resolves project identifiers through the following process:

1. **URL Extraction**: If a full URL is provided, extracts the slug-shortid combination
2. **UUID Detection**: Checks if the identifier is already a full UUID (36 chars, 4 dashes)
3. **Project Lookup**: Queries all team projects and matches against:
   - Full `slugId` (e.g., "crm-smart-monitoring-system-f59a41a96c52")
   - Slug part only (e.g., "crm-smart-monitoring-system")
   - Short ID only (e.g., "f59a41a96c52")
   - Project name (case-insensitive exact match)

#### Usage Examples

**Creating Issue with Project Assignment (Various Formats)**

```python
from mcp_ticketer.core.models import Task, Priority, TicketState

# Using full URL (copy from browser)
task1 = Task(
    title="Implement monitoring dashboard",
    description="Create real-time monitoring for CRM system",
    priority=Priority.HIGH,
    state=TicketState.OPEN,
    parent_epic="https://linear.app/travel-bta/project/crm-smart-monitoring-system-f59a41a96c52/overview"
)
created_task1 = await adapter.create(task1)

# Using project name
task2 = Task(
    title="Add alerting system",
    parent_epic="CRM Smart Monitoring System"
)
created_task2 = await adapter.create(task2)

# Using short ID
task3 = Task(
    title="Configure metrics collection",
    parent_epic="f59a41a96c52"
)
created_task3 = await adapter.create(task3)
```

**Updating Issue to Move to Different Project**

```python
# Update issue to move to different project
await adapter.update("ENG-123", {
    "parent_epic": "https://linear.app/company/project/new-project-abc123/overview"
})

# Or using project name
await adapter.update("ENG-123", {
    "parent_epic": "Q2 Infrastructure Improvements"
})
```

**Via MCP Tools**

```python
# Using the MCP tool with various project formats
result = mcp__mcp_ticketer__issue_create(
    title="Setup CI/CD pipeline",
    description="Configure automated deployment",
    assignee="devops-team",
    priority="high"
)

# Then assign to project using update
mcp__mcp_ticketer__ticket_update(
    ticket_id=result["id"],
    # Any format works:
    # - Full URL from Linear
    # - Project slug
    # - Project name
    # - Short ID
)
```

#### Edge Cases and Behaviors

**Invalid Project Identifier**
- If a project identifier cannot be resolved, a warning is logged
- The issue is created/updated without the project assignment
- No exception is raised to allow the operation to continue

```python
# Invalid project - warning logged, issue created without project
task = Task(
    title="New task",
    parent_epic="non-existent-project"  # Warning logged
)
created = await adapter.create(task)
# Issue created successfully, but not assigned to any project
```

**Ambiguous Matches**
- Project resolution prioritizes exact matches over partial matches
- Case-insensitive matching is used for convenience
- If multiple projects have similar names, use the full slug or short ID for precision

**URL Format Variations**
- Both `/overview` and `/issues` URL endings are supported
- Trailing slashes are handled automatically
- URL parameters are ignored

### Enhanced Label Management

The Linear adapter provides flexible label (tag) management with support for adding, replacing, and removing labels during both create and update operations.

#### Label Operations

**Adding Labels During Creation**

```python
from mcp_ticketer.core.models import Task

# Labels are specified as a list of strings
task = Task(
    title="Fix authentication bug",
    description="Users cannot login with SSO",
    tags=["bug", "security", "high-priority"],  # Labels to add
)
created = await adapter.create(task)
print(f"Created with labels: {created.tags}")
```

**Replacing Labels During Update**

```python
# Replace all existing labels with new set
await adapter.update("ENG-123", {
    "tags": ["bug", "frontend", "urgent"]  # Replaces all existing labels
})
```

**Adding Labels to Existing Issue**

```python
# Fetch current issue to preserve existing labels
current = await adapter.read("ENG-123")
current_labels = current.tags or []

# Add new label while keeping existing ones
new_labels = current_labels + ["regression"]

await adapter.update("ENG-123", {
    "tags": new_labels
})
```

**Removing All Labels**

```python
# Set empty list to remove all labels
await adapter.update("ENG-123", {
    "tags": []  # Removes all labels from issue
})
```

**Removing Specific Labels**

```python
# Fetch current issue
current = await adapter.read("ENG-123")
current_labels = current.tags or []

# Remove specific label
updated_labels = [label for label in current_labels if label != "wont-fix"]

await adapter.update("ENG-123", {
    "tags": updated_labels
})
```

#### Label Resolution

The adapter automatically resolves label names to Linear label IDs:

1. **Label Cache**: Labels are loaded and cached when the adapter initializes
2. **Case-Insensitive Matching**: Label names are matched case-insensitively
3. **Warning on Mismatch**: If a label doesn't exist in the team, a warning is logged
4. **Partial Success**: Valid labels are applied even if some labels don't exist

```python
# Mixed valid and invalid labels
task = Task(
    title="Update user profile",
    tags=["feature", "invalid-label", "frontend"]
    # Warning logged for "invalid-label"
    # "feature" and "frontend" applied if they exist
)
created = await adapter.create(task)
```

#### Creating Labels in Linear

Labels must exist in your Linear team before they can be used. Create them via:

1. **Linear UI**: Team Settings > Labels > Create Label
2. **Linear API**: Use GraphQL mutation (not covered in this adapter)

#### Best Practices

**Label Naming Conventions**
```python
# Good: Consistent, lowercase, hyphenated
tags=["bug", "frontend", "high-priority"]

# Avoid: Mixed case, spaces, special characters
tags=["Bug", "Front End", "High Priority!!!"]
```

**Label Categories**
```python
# Use prefixes for categorization
tags=[
    "type:bug",           # Type category
    "priority:high",      # Priority category
    "team:frontend",      # Team category
    "status:blocked"      # Status category
]
```

**Label Reuse**
```python
# Define label sets for reuse
BUG_LABELS = ["bug", "needs-triage"]
SECURITY_LABELS = ["security", "high-priority"]

task = Task(
    title="Security vulnerability in auth",
    tags=BUG_LABELS + SECURITY_LABELS
)
```

#### Edge Cases

**Empty Label Array vs None**
```python
# None = Don't modify labels
await adapter.update("ENG-123", {})  # Labels unchanged

# Empty array = Remove all labels
await adapter.update("ENG-123", {"tags": []})  # All labels removed
```

**Non-Existent Labels**
```python
# Labels that don't exist are skipped with warning
task = Task(
    title="New feature",
    tags=["feature", "does-not-exist", "frontend"]
)
created = await adapter.create(task)
# Only "feature" and "frontend" applied (if they exist)
# Warning logged: "Label 'does-not-exist' not found in team"
```

**Duplicate Labels**
```python
# Duplicate labels are deduplicated by Linear
task = Task(
    title="Bug fix",
    tags=["bug", "bug", "frontend"]  # Duplicate "bug"
)
created = await adapter.create(task)
# Result: ["bug", "frontend"] (deduplicated)
```

### User Assignment by Username

The Linear adapter provides flexible user identification, supporting multiple formats for assigning issues to team members.

#### Supported User Identifiers

1. **Email Address** (Most Specific)
   ```python
   task.assignee = "john.smith@company.com"
   ```

2. **Display Name**
   ```python
   task.assignee = "john.smith"  # Linear displayName field
   ```

3. **Full Name**
   ```python
   task.assignee = "John Smith"  # Linear name field
   ```

4. **User ID** (Direct UUID)
   ```python
   task.assignee = "02d15669-7351-4451-9719-807576c16049"
   ```

#### User Resolution Process

The adapter resolves user identifiers using this priority:

1. **Email Lookup**: Exact match on email address
2. **Name Search**: Case-insensitive search on `displayName` and `name` fields
3. **Ambiguity Handling**: If multiple matches, tries exact match, then uses first result
4. **Direct ID**: Assumes it's a user ID if no matches found

#### Usage Examples

**Assigning During Issue Creation**

```python
from mcp_ticketer.core.models import Task, Priority

# Using email (recommended for precision)
task1 = Task(
    title="Implement OAuth flow",
    description="Add OAuth 2.0 authentication",
    assignee="john.smith@company.com",  # Email
    priority=Priority.HIGH
)
created1 = await adapter.create(task1)

# Using display name
task2 = Task(
    title="Review pull request",
    assignee="john.smith",  # Display name
)
created2 = await adapter.create(task2)

# Using full name
task3 = Task(
    title="Update documentation",
    assignee="John Smith",  # Full name
)
created3 = await adapter.create(task3)
```

**Reassigning Existing Issue**

```python
# Reassign to different user
await adapter.update("ENG-123", {
    "assignee": "jane.doe@company.com"
})

# Reassign using username
await adapter.update("ENG-456", {
    "assignee": "jane.doe"
})

# Unassign issue (set to None)
await adapter.update("ENG-789", {
    "assignee": None
})
```

**Search by Assignee**

```python
from mcp_ticketer.core.models import SearchQuery

# Search using any identifier format
query = SearchQuery(
    assignee="john.smith",  # Works with email, username, or full name
    state=TicketState.IN_PROGRESS
)
results = await adapter.search(query)
```

**Via MCP Tools**

```python
# Create issue with user assignment
result = mcp__mcp_ticketer__issue_create(
    title="Setup monitoring",
    assignee="devops-team@company.com"  # Or username
)

# Update assignee
mcp__mcp_ticketer__ticket_update(
    ticket_id="ENG-123",
    assignee="new.assignee"  # Email or username
)
```

#### Ambiguity Handling

When multiple users match a name, the adapter handles it intelligently:

**Single Match** - Used automatically:
```python
# Only one "John Smith" in team
task.assignee = "John Smith"  # Resolves to that user
```

**Multiple Matches - Exact Match Preferred**:
```python
# Multiple users with "smith" in name:
# - john.smith (displayName)
# - jane.smith (displayName)
# - Adam Smith (name)

task.assignee = "john.smith"  # Exact displayName match used
```

**Multiple Matches - First Result Used**:
```python
# Multiple "John" matches, no exact match
# Warning logged with list of matches
# First match used automatically

task.assignee = "John"
# Warning: "Multiple users match 'John': ['john.smith', 'john.doe', 'johnny'].
#          Using first match: john.smith"
```

#### Edge Cases and Behaviors

**Non-Existent User**
```python
# User doesn't exist - identifier passed as-is to Linear
# Linear API will return error during creation/update
task = Task(
    title="New task",
    assignee="non-existent@company.com"  # Will fail at Linear API
)
# Raises ValueError with Linear error message
```

**Email vs Username Collision**
```python
# User has email: john@company.com
# User has displayName: john@company.com (unusual but possible)

task.assignee = "john@company.com"
# Email lookup takes precedence - matches user with that email
```

**Case Sensitivity**
```python
# All formats are case-insensitive
task1.assignee = "john.smith"      # Matches
task2.assignee = "JOHN.SMITH"      # Also matches same user
task3.assignee = "John.Smith"      # Also matches
```

**Empty or None Assignee**
```python
# None = Unassigned
task.assignee = None  # Issue created without assignee

# Empty string = Unassigned
task.assignee = ""    # Treated as no assignee
```

#### Best Practices

**Use Email for Precision**
```python
# Recommended: Always use email when possible
task.assignee = "team.member@company.com"
```

**Avoid Ambiguous Names**
```python
# Avoid: Common first names
task.assignee = "John"  # Could match multiple users

# Better: Use display name or email
task.assignee = "john.smith"
task.assignee = "john.smith@company.com"
```

**Team Assignment Pattern**
```python
# For team-owned issues, use team email or tag
task = Task(
    title="Infrastructure upgrade",
    assignee="devops@company.com",
    tags=["team:devops"]  # Also tag for visibility
)
```

**Dynamic Assignment**
```python
# Get user ID once, reuse for multiple operations
user_id = await adapter._get_user_id("john.smith@company.com")

task1.assignee = user_id
task2.assignee = user_id
task3.assignee = user_id
```

### Priority Management

The Linear adapter maps universal priority levels to Linear's priority system.

#### Priority Levels

| Universal Priority | Linear Priority | Numeric Value | Description |
|-------------------|-----------------|---------------|-------------|
| `CRITICAL` | 1 | Urgent | Requires immediate attention |
| `HIGH` | 2 | High | Important, should be addressed soon |
| `MEDIUM` | 3 | Normal | Standard priority (default) |
| `LOW` | 4 | Low | Can be deferred |

#### Usage Examples

**Setting Priority During Creation**

```python
from mcp_ticketer.core.models import Task, Priority

# High priority bug
task = Task(
    title="Critical production bug",
    description="Service is down",
    priority=Priority.CRITICAL,
    tags=["bug", "production"]
)
created = await adapter.create(task)
```

**Updating Priority**

```python
# Escalate to high priority
await adapter.update("ENG-123", {
    "priority": Priority.HIGH
})

# Using string value
await adapter.update("ENG-456", {
    "priority": "critical"
})
```

**Search by Priority**

```python
from mcp_ticketer.core.models import SearchQuery

# Find all critical issues
query = SearchQuery(
    priority=Priority.CRITICAL,
    state=TicketState.OPEN
)
critical_issues = await adapter.search(query)
```

## Complete Usage Examples

### End-to-End Workflow Example

```python
from mcp_ticketer.adapters.linear import LinearAdapter
from mcp_ticketer.core.models import Task, Priority, TicketState

# Initialize adapter
adapter = LinearAdapter({
    "api_key": "lin_api_your_token",
    "team_id": "your-team-id"
})

# 1. Create issue with full metadata
task = Task(
    title="Implement user authentication",
    description="Add JWT-based authentication with refresh tokens",
    priority=Priority.HIGH,
    state=TicketState.OPEN,
    assignee="backend-dev@company.com",
    tags=["feature", "security", "backend"],
    parent_epic="https://linear.app/company/project/q1-auth-improvements-abc123/overview"
)
created_task = await adapter.create(task)
print(f"Created: {created_task.id}")

# 2. Add comment
from mcp_ticketer.core.models import Comment

comment = Comment(
    ticket_id=created_task.id,
    content="Starting implementation. Will create PR by EOD."
)
await adapter.add_comment(comment)

# 3. Update progress
await adapter.update(created_task.id, {
    "state": TicketState.IN_PROGRESS,
    "tags": ["feature", "security", "backend", "in-review"]  # Add label
})

# 4. Update assignee and priority
await adapter.update(created_task.id, {
    "assignee": "senior-dev@company.com",  # Reassign
    "priority": Priority.CRITICAL  # Escalate
})

# 5. Move to different project
await adapter.update(created_task.id, {
    "parent_epic": "Q2 Security Enhancements"  # Project name
})

# 6. Complete the issue
await adapter.update(created_task.id, {
    "state": TicketState.DONE,
    "tags": []  # Remove all labels
})

# 7. Search related issues
query = SearchQuery(
    query="authentication",
    tags=["security"],
    priority=Priority.HIGH
)
related = await adapter.search(query)
```

### Bulk Operations Example

```python
# Create multiple related issues in a project
project_url = "https://linear.app/company/project/api-redesign-xyz/overview"

issues = [
    {
        "title": "Design new API endpoints",
        "assignee": "api-designer@company.com",
        "priority": Priority.HIGH,
        "tags": ["design", "api"]
    },
    {
        "title": "Implement v2 authentication",
        "assignee": "backend-dev@company.com",
        "priority": Priority.HIGH,
        "tags": ["implementation", "auth"]
    },
    {
        "title": "Write API documentation",
        "assignee": "tech-writer@company.com",
        "priority": Priority.MEDIUM,
        "tags": ["documentation"]
    }
]

created_issues = []
for issue_data in issues:
    task = Task(
        title=issue_data["title"],
        assignee=issue_data["assignee"],
        priority=issue_data["priority"],
        tags=issue_data["tags"],
        parent_epic=project_url  # All in same project
    )
    created = await adapter.create(task)
    created_issues.append(created)
    print(f"Created: {created.id} - {created.title}")
```

### Label Management Example

```python
# Tag management workflow
issue_id = "ENG-123"

# Add initial tags
await adapter.update(issue_id, {
    "tags": ["bug", "frontend"]
})

# Add more tags (preserving existing)
current = await adapter.read(issue_id)
updated_tags = current.tags + ["high-priority", "regression"]
await adapter.update(issue_id, {
    "tags": updated_tags
})

# Remove specific tag
current = await adapter.read(issue_id)
filtered_tags = [t for t in current.tags if t != "regression"]
await adapter.update(issue_id, {
    "tags": filtered_tags
})

# Replace all tags
await adapter.update(issue_id, {
    "tags": ["resolved", "tested"]
})

# Remove all tags
await adapter.update(issue_id, {
    "tags": []
})
```

## State Mapping

Linear states are mapped to universal states based on their type:

| Universal State | Linear State Type | Description |
|----------------|-------------------|-------------|
| `OPEN` | `unstarted` | New, unstarted issues (typically "To Do") |
| `IN_PROGRESS` | `started` | Actively being worked (typically "In Progress") |
| `READY` | `unstarted` | Ready for work |
| `TESTED` | `started` | Under testing |
| `DONE` | `completed` | Completed work |
| `CLOSED` | `canceled` | Closed without completion |
| `WAITING` | `unstarted` | Waiting on external factors |
| `BLOCKED` | `unstarted` | Blocked by dependency |

**Note**: The actual state IDs are loaded from your team's workflow configuration during adapter initialization.

## Troubleshooting

### Common Issues

#### Troubleshooting Label Errors

**Problem**: Label creation or update fails with clear error message

Starting in version 1.3.2+, label operations now fail-fast instead of silently succeeding with partial results. This is a **positive breaking change** that improves data integrity.

**Error Messages You Might See**:

```
ValueError: Label creation failed for 'priority:urgent'. Use label_list tool to check available labels or verify permissions.
```

```
ValueError: Label 'high-priority' not found in team. Available labels can be listed using the label_list tool.
```

```
ValueError: Failed to resolve labels: ['invalid-label', 'another-bad-label']
```

**What Changed**:

- **Before v1.3.2**: Silent partial failures - if some labels didn't exist, they were skipped with only a warning, and the ticket was created/updated with only the valid labels
- **After v1.3.2**: Fail-fast approach - if ANY label doesn't exist, the entire operation fails with a clear error message

**Why This Change Matters**:

Silent failures led to data integrity issues:
- Users expected labels to be applied but they weren't
- No clear indication that labels were missing
- Difficult to debug why labels weren't showing up
- Partial updates created inconsistent state

**Solutions**:

1. **Check Available Labels Before Use**:
   ```python
   from mcp_ticketer.mcp.server.tools import label_list

   # List all available labels in your team
   result = label_list()
   available_labels = [label["name"] for label in result["labels"]]
   print(f"Available labels: {available_labels}")
   ```

2. **Create Missing Labels in Linear**:
   - Go to Linear → Team Settings → Labels → Create Label
   - Add the label with appropriate name and color
   - Retry your operation

3. **Verify Label Names**:
   ```python
   # Labels are case-insensitive but must match exactly
   # Good:
   tags=["bug", "frontend", "high-priority"]

   # These will fail if labels don't exist:
   tags=["Bug", "Front-End", "priority:urgent"]
   ```

4. **Use Only Existing Labels**:
   ```python
   # Check before creating ticket
   available = ["bug", "feature", "frontend", "backend"]
   requested = ["bug", "frontend", "invalid"]

   # Filter to only valid labels
   valid_labels = [tag for tag in requested if tag in available]

   task = Task(
       title="Fix login issue",
       tags=valid_labels  # Only uses labels that exist
   )
   ```

5. **Handle Label Errors Gracefully**:
   ```python
   try:
       task = Task(
           title="New feature",
           tags=["feature", "might-not-exist"]
       )
       created = await adapter.create(task)
   except ValueError as e:
       if "Label" in str(e):
           print(f"Label error: {e}")
           # Create without labels, add them manually later
           task.tags = []
           created = await adapter.create(task)
   ```

**Migration Guide**:

If you're upgrading from v1.3.1 or earlier:

1. **Audit Your Label Usage**:
   - Review all code that creates/updates tickets with labels
   - List all labels used in your codebase
   - Compare against available labels in Linear

2. **Create Missing Labels**:
   - Use `label_list` tool to get current labels
   - Create any missing labels in Linear UI
   - Or update code to use only existing labels

3. **Add Error Handling**:
   - Wrap label operations in try-catch blocks
   - Handle `ValueError` exceptions specifically for labels
   - Provide fallback behavior (e.g., create without labels)

4. **Test Thoroughly**:
   - Test ticket creation with all label combinations
   - Verify error messages are actionable
   - Ensure fallback logic works as expected

**Best Practices**:

```python
# 1. Use label constants to avoid typos
VALID_LABELS = ["bug", "feature", "enhancement", "documentation"]

def create_ticket_with_labels(title, label_names):
    # Validate labels before use
    invalid = [l for l in label_names if l not in VALID_LABELS]
    if invalid:
        raise ValueError(f"Invalid labels: {invalid}. Valid: {VALID_LABELS}")

    return Task(title=title, tags=label_names)

# 2. Maintain a label registry
class LabelRegistry:
    def __init__(self, adapter):
        self.adapter = adapter
        self._cache = None

    def get_available_labels(self):
        if self._cache is None:
            result = label_list()
            self._cache = [l["name"] for l in result["labels"]]
        return self._cache

    def validate_labels(self, labels):
        available = self.get_available_labels()
        invalid = [l for l in labels if l not in available]
        if invalid:
            raise ValueError(
                f"Invalid labels: {invalid}. "
                f"Use label_list tool to see available labels."
            )

# 3. Use defensive label filtering
def safe_create_with_labels(task, requested_labels):
    # Get available labels
    available = get_available_labels()

    # Filter to only valid labels
    valid_labels = [l for l in requested_labels if l in available]

    # Warn about skipped labels
    skipped = [l for l in requested_labels if l not in available]
    if skipped:
        logger.warning(f"Skipping unavailable labels: {skipped}")

    task.tags = valid_labels
    return adapter.create(task)
```

**See Also**:
- [Enhanced Label Management](#enhanced-label-management) - Full label management documentation
- [Troubleshooting Guide](../../user-docs/troubleshooting/TROUBLESHOOTING.md#linear-label-creation-failures) - Additional troubleshooting steps
- [CHANGELOG.md](../../../CHANGELOG.md#unreleased) - Release notes for this change

---

#### Project Not Found

**Problem**: Warning about unable to resolve project identifier

```
WARNING: Could not resolve project identifier 'my-project'
```

**Solutions**:
1. Verify the project exists in Linear
2. Try using the full project URL from browser
3. Check spelling of project name (case-insensitive but must be exact)
4. Ensure you have access to the project in Linear

#### Label Not Found

**Problem**: Warning about label not existing in team

```
WARNING: Label 'priority:urgent' not found in team. Available labels: ['bug', 'feature', ...]
```

**Solutions**:
1. Create the label in Linear: Team Settings > Labels > Create Label
2. Check spelling (case-insensitive matching)
3. List available labels to see what exists
4. Use only labels that exist in your team

#### Multiple User Matches

**Problem**: Warning about ambiguous username

```
WARNING: Multiple users match 'john': ['john.smith', 'john.doe', 'johnny']. Using first match: john.smith
```

**Solutions**:
1. Use email address instead: `john.smith@company.com`
2. Use full display name: `john.smith`
3. Provide more specific identifier

#### User Not Found

**Problem**: ValueError during creation/update with user assignment

```
ValueError: Failed to create issue: User not found
```

**Solutions**:
1. Verify user exists in Linear workspace
2. Check email address spelling
3. Ensure user is member of the team
4. Try using email instead of username

#### Authentication Failures

**Problem**: 401 Unauthorized or Invalid API key

**Solutions**:
1. Verify API key is correct and starts with `lin_api_`
2. Check API key hasn't expired
3. Regenerate API key in Linear settings
4. Ensure API key has necessary permissions

### Debug Mode

Enable detailed logging to troubleshoot issues:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Now adapter operations will show detailed logs
adapter = LinearAdapter(config)
```

### Testing Connection

```python
# Test if adapter can connect to Linear
is_valid, error = adapter.validate_credentials()
if not is_valid:
    print(f"Connection failed: {error}")
else:
    print("Connection successful")
```

## API Reference

### Core Methods

#### `create(ticket: Epic | Task) -> Epic | Task`

Create a new issue or project.

**Parameters:**
- `ticket`: Epic or Task to create
  - `title` (required): Issue title
  - `description`: Markdown description
  - `priority`: Priority level (Critical/High/Medium/Low)
  - `state`: Initial state
  - `assignee`: Email, username, or user ID
  - `tags`: List of label names
  - `parent_epic`: Project identifier (URL/slug/name/ID)
  - `parent_issue`: Parent issue ID (for sub-issues)

**Returns:** Created ticket with Linear ID and metadata

#### `read(ticket_id: str) -> Epic | Task`

Retrieve an issue by ID.

**Parameters:**
- `ticket_id`: Linear issue identifier (e.g., "ENG-123") or UUID

**Returns:** Issue with all fields populated

#### `update(ticket_id: str, updates: dict) -> Epic | Task`

Update an existing issue.

**Parameters:**
- `ticket_id`: Linear issue identifier
- `updates`: Dictionary with fields to update
  - `title`: New title
  - `description`: New description
  - `priority`: New priority
  - `state`: New state
  - `assignee`: New assignee (email/username/ID)
  - `tags`: New label list (replaces existing)
  - `parent_epic`: New project assignment

**Returns:** Updated issue

#### `delete(ticket_id: str) -> bool`

Delete an issue (moves to trash in Linear).

**Parameters:**
- `ticket_id`: Linear issue identifier

**Returns:** True if successful

#### `search(query: SearchQuery) -> list[Epic | Task]`

Search for issues.

**Parameters:**
- `query`: SearchQuery with filters
  - `query`: Text search
  - `state`: Filter by state
  - `priority`: Filter by priority
  - `tags`: Filter by labels
  - `assignee`: Filter by user
  - `limit`: Max results (default 50)

**Returns:** List of matching issues

### Comment Methods

#### `add_comment(comment: Comment) -> Comment`

Add comment to issue.

**Parameters:**
- `comment`: Comment with `ticket_id` and `content`

**Returns:** Created comment with ID

#### `get_comments(ticket_id: str, limit: int = 50) -> list[Comment]`

Get comments for issue.

**Parameters:**
- `ticket_id`: Issue identifier
- `limit`: Max comments to retrieve

**Returns:** List of comments

## Best Practices

### 1. Use Structured Identifiers

```python
# Good: Use email for users
task.assignee = "developer@company.com"

# Good: Use full URL for projects
task.parent_epic = "https://linear.app/company/project/project-name-abc/overview"

# Acceptable: Use clear names
task.parent_epic = "Q1 Security Improvements"
task.assignee = "john.smith"
```

### 2. Consistent Label Strategy

```python
# Define label taxonomy
LABEL_TYPES = ["bug", "feature", "task", "spike"]
LABEL_PRIORITIES = ["critical", "high", "medium", "low"]
LABEL_TEAMS = ["frontend", "backend", "devops", "design"]

# Use consistently
task.tags = ["bug", "critical", "backend"]
```

### 3. Project Organization

```python
# Group related work in projects
PROJECTS = {
    "auth": "Authentication Improvements",
    "api": "API Redesign",
    "ui": "UI Refresh"
}

task.parent_epic = PROJECTS["auth"]
```

### 4. Error Handling

```python
try:
    created = await adapter.create(task)
except ValueError as e:
    if "project" in str(e).lower():
        print(f"Project assignment failed: {e}")
        # Retry without project
        task.parent_epic = None
        created = await adapter.create(task)
    else:
        raise
```

### 5. Batch Operations

```python
# Reuse user/project IDs for efficiency
user_id = await adapter._get_user_id("dev@company.com")
project_id = await adapter._resolve_project_id("Q1 Goals")

for issue_data in batch_data:
    task = Task(
        title=issue_data["title"],
        assignee=user_id,  # Reuse resolved ID
        parent_epic=project_id  # Reuse resolved ID
    )
    await adapter.create(task)
```

### 6. State Transitions

```python
# Follow logical workflow
await adapter.update(issue_id, {"state": TicketState.IN_PROGRESS})
# ... do work ...
await adapter.update(issue_id, {"state": TicketState.READY})
# ... review ...
await adapter.update(issue_id, {"state": TicketState.DONE})
```

### 7. Search Optimization

```python
# Use specific filters for faster searches
query = SearchQuery(
    assignee="team@company.com",
    state=TicketState.IN_PROGRESS,
    tags=["high-priority"],
    limit=20  # Limit results
)
```

---

This documentation covers the Linear adapter's comprehensive feature set including the recently enhanced project assignment, label management, and user assignment capabilities. For additional information, refer to the main [ADAPTERS.md](../ADAPTERS.md) documentation.
