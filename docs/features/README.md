# Features Documentation

Comprehensive guides for all MCP Ticketer features.

## 📋 Core Features

### Ticket Management
Universal ticket operations across all adapters.

**Topics**:
- Creating tickets
- Updating and deleting tickets
- State transitions
- Searching and filtering
- Bulk operations

**See**: Ticket Management Guide (coming soon)

### Custom Instructions
Customize ticket writing guidelines for your team.

**[Ticket Instructions Guide](ticket_instructions.md)**
- View and manage instructions
- Add custom guidelines
- Use with CLI, MCP, and Python
- Best practices

**Quick Example**:
```bash
# View instructions
mcp-ticketer instructions show

# Add custom instructions
mcp-ticketer instructions add team_guidelines.md

# Edit interactively
mcp-ticketer instructions edit
```

### File Attachments
Upload and manage file attachments on tickets.

**Supported Adapters**: AITrackdown, JIRA (Epic attachments), GitHub (Issue attachments)

**Topics**:
- Uploading files
- Listing attachments
- Download and deletion
- Supported file types

**See**: [Attachments Guide](../ATTACHMENTS.md)

**Quick Example**:
```python
# Via MCP
await ticket_attach(
    ticket_id="task-123",
    file_path="/path/to/document.pdf",
    description="Requirements document"
)

# List attachments
result = await ticket_attachments(ticket_id="task-123")
```

### Hierarchical Tickets
Organize work with Epic → Issue → Task hierarchy.

**Topics**:
- Creating epics, issues, and tasks
- Linking hierarchies
- Viewing hierarchy trees
- Navigation

**Quick Example**:
```bash
# Create epic
mcp-ticketer create-epic "Q4 Redesign" --description "Major UI overhaul"

# Create issue under epic
mcp-ticketer create-issue "Update nav" --epic-id EPIC-123

# Create task under issue
mcp-ticketer create-task "Design mockup" --issue-id ISSUE-456
```

### Comments and Collaboration
Add comments and collaborate on tickets.

**Topics**:
- Adding comments
- Listing comments
- Mentioning users
- Comment formatting

**Quick Example**:
```bash
# Add comment via CLI
mcp-ticketer comment TICKET-123 "Updated the fix"

# Via MCP
await ticket_comment(
    ticket_id="TICKET-123",
    operation="add",
    text="Updated the fix"
)
```

### State Management
Built-in state machine with validation.

**States**:
- `OPEN` - Initial state
- `IN_PROGRESS` - Active work
- `READY` - Ready for review
- `TESTED` - Verification complete
- `DONE` - Complete and deployed
- `WAITING` - Blocked by external dependency
- `BLOCKED` - Cannot proceed
- `CLOSED` - Terminal state

**Quick Example**:
```bash
# Transition ticket state
mcp-ticketer transition TICKET-123 in_progress

# Update state with comment
mcp-ticketer update TICKET-123 --state ready --comment "Ready for review"
```

### Search and Filtering
Advanced search with multiple filters.

**Topics**:
- Full-text search
- Filter by state, priority, assignee
- Tag filtering
- Date range queries

**Quick Example**:
```bash
# Search by text
mcp-ticketer search "login bug" --state open

# Filter by priority
mcp-ticketer list --priority high --assignee john.doe

# Via MCP
result = await ticket_search(
    query="authentication",
    state="open",
    priority="high",
    limit=20
)
```

## 🔌 Adapter-Specific Features

### Linear Features
- Team-based ticket organization
- Cycle management
- Project tracking
- Issue relations

### JIRA Features
- Epic attachments
- Sprint management
- Custom fields
- Issue types

### GitHub Features
- Issue attachments
- Pull request linking
- Milestone tracking
- Label management

### AITrackdown Features
- Local file storage
- No external dependencies
- Full attachment support
- Simple setup

## 🚀 Advanced Features

### Pull Request Integration
Link tickets to pull requests (GitHub, JIRA adapters).

**Quick Example**:
```python
# Create PR linked to ticket
await ticket_create_pr(
    ticket_id="TICKET-123",
    title="Fix authentication bug",
    description="Resolves TICKET-123",
    source_branch="fix/auth-bug",
    target_branch="main"
)

# Link existing PR
await ticket_link_pr(
    ticket_id="TICKET-123",
    pr_url="https://github.com/org/repo/pull/456"
)
```

### Bulk Operations
Perform operations on multiple tickets.

**Quick Example**:
```python
# Create multiple tickets
await ticket_bulk_create(tickets=[
    {"title": "Task 1", "description": "...", "priority": "high"},
    {"title": "Task 2", "description": "...", "priority": "medium"},
    {"title": "Task 3", "description": "...", "priority": "low"}
])

# Update multiple tickets
await ticket_bulk_update(updates=[
    {"ticket_id": "T-1", "state": "done"},
    {"ticket_id": "T-2", "priority": "high"},
    {"ticket_id": "T-3", "assignee": "jane.doe"}
])
```

### Caching and Performance
Smart caching for improved performance.

**Topics**:
- Memory cache
- TTL configuration
- Cache invalidation
- Performance tuning

### MCP Integration
Native support for AI agent interactions.

**Topics**:
- MCP server setup
- Tool catalog
- Event handling
- Error handling

**See**: [MCP Tools Reference](../api/mcp_tools.md)

## 📊 Feature Comparison

### By Adapter

| Feature | Linear | JIRA | GitHub | AITrackdown |
|---------|--------|------|--------|-------------|
| Tickets | ✅ | ✅ | ✅ | ✅ |
| Comments | ✅ | ✅ | ✅ | ✅ |
| Hierarchy | ✅ | ✅ | ✅ | ✅ |
| Attachments | ❌ | ✅ (Epics) | ✅ (Issues) | ✅ (All) |
| Pull Requests | ❌ | ✅ | ✅ | ❌ |
| Search | ✅ | ✅ | ✅ | ✅ |
| States | ✅ | ✅ | ✅ | ✅ |
| Custom Fields | ✅ | ✅ | ✅ (Labels) | ❌ |

### By Feature Type

| Feature | CLI | MCP | Python API |
|---------|-----|-----|------------|
| Tickets | ✅ | ✅ | ✅ |
| Instructions | ✅ | ✅ | ✅ |
| Attachments | ❌ | ✅ | ✅ |
| Hierarchy | ✅ | ✅ | ✅ |
| Search | ✅ | ✅ | ✅ |
| Bulk Ops | ❌ | ✅ | ✅ |

## 🎯 Use Cases

### For Individual Users
- Track personal tasks
- Manage project tickets
- Search and filter work
- Customize ticket format

### For Teams
- Standardize ticket creation
- Enforce team conventions
- Collaborate on tickets
- Track project progress

### For AI Agents
- Automated ticket creation
- Intelligent search
- Context-aware updates
- Bulk operations

### For Integrations
- Webhook handling
- API access
- Custom workflows
- Data synchronization

## 🔗 Related Documentation

- [API Reference](../api/) - Complete API documentation
- [Guides](../guides/) - How-to guides and tutorials
- [Setup](../setup/) - Adapter configuration
- [Development](../development/) - Contributing and development

## 🆘 Getting Help

- **Feature Questions**: [GitHub Discussions](https://github.com/mcp-ticketer/mcp-ticketer/discussions)
- **Bug Reports**: [GitHub Issues](https://github.com/mcp-ticketer/mcp-ticketer/issues)
- **Feature Requests**: [GitHub Issues](https://github.com/mcp-ticketer/mcp-ticketer/issues)

---

**Last Updated**: 2025-11-15
