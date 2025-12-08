# MCP API Reference

**Last Updated**: 2025-11-29
**Purpose**: Centralized reference for MCP tool response formats and parameters

---

## Standard Response Formats

All MCP tools return JSON dictionaries with standardized structures to ensure consistency across the API.

### Base Response Structure

Every tool response includes:
- `status`: `"completed"` or `"error"`
- Tool-specific data fields (see sections below)
- `error`: Error message (only present when status is `"error"`)

### Config Response Format

Used by: All `config_*` tools

**Success Response**:
```json
{
  "status": "completed",
  "message": "Human-readable success message",
  "config_path": "/path/to/.mcp-ticketer/config.json",
  // Tool-specific fields (previous_value, new_value, etc.)
}
```

**Error Response**:
```json
{
  "status": "error",
  "error": "Detailed error message with context",
  "valid_options": ["option1", "option2"]  // When applicable
}
```

### Ticket Response Format

Used by: `ticket_create`, `ticket_read`, `ticket_update`, `ticket_assign`

**Success Response**:
```json
{
  "status": "completed",
  "ticket": {
    "id": "TICKET-123",
    "identifier": "PROJ-123",
    "title": "Ticket title",
    "description": "Detailed description",
    "state": "open",  // See: Workflow States
    "priority": "high",  // See: Priority Levels
    "assignee": "user@example.com",
    "tags": ["tag1", "tag2"],
    "created_at": "2025-11-29T10:00:00Z",
    "updated_at": "2025-11-29T12:00:00Z",
    // Adapter-specific additional fields
  },
  "adapter": "linear",
  "adapter_name": "Linear"
}
```

### List Response Format

Used by: `ticket_list`, `label_list`, `epic_list`

**Success Response**:
```json
{
  "status": "completed",
  "items": [/* Array of objects */],
  "count": 25,
  "total": 150,  // When pagination supported
  "has_more": true,  // When pagination supported
  "adapter": "linear",
  "adapter_name": "Linear"
}
```

**Compact Mode** (when `compact=true`):
```json
{
  "status": "completed",
  "items": [
    {"id": "TICKET-1", "title": "Title 1", "state": "open"},
    {"id": "TICKET-2", "title": "Title 2", "state": "in_progress"}
  ],
  "count": 2
}
```

### Label Response Format

Used by: `label_list`, `label_merge`, `label_rename`

**Label Object**:
```json
{
  "id": "label-uuid",
  "name": "bug",
  "color": "#ff0000",  // Adapter-specific
  "description": "Bug reports",  // Optional
  "usage_count": 42  // When include_usage_count=true
}
```

### Validation Response Format

Used by: `config_validate`, `config_test_adapter`, `instructions_validate`

**Success Response**:
```json
{
  "status": "completed",
  "valid": true,
  "warnings": ["Warning message"],  // Optional
  "errors": [],  // Empty when valid
  "message": "Validation summary"
}
```

**Failure Response**:
```json
{
  "status": "completed",  // Note: Status is completed even on validation failure
  "valid": false,
  "errors": ["Error 1", "Error 2"],
  "warnings": [],
  "message": "Validation failed"
}
```

---

## Shared Parameter Glossary

### Workflow States

Valid values for `state` parameter in ticket operations:

| State | Description | Common Transitions |
|-------|-------------|-------------------|
| `open` | New ticket, not started | → `in_progress`, `waiting`, `blocked`, `closed` |
| `in_progress` | Active work in progress | → `ready`, `waiting`, `blocked`, `open` |
| `ready` | Work complete, awaiting review | → `tested`, `in_progress`, `blocked` |
| `tested` | Passed review/testing | → `done`, `in_progress` |
| `done` | Work complete and merged | → `closed` |
| `waiting` | Paused for external dependency | → `open`, `in_progress`, `closed` |
| `blocked` | Cannot proceed due to blocker | → `open`, `in_progress`, `closed` |
| `closed` | Terminal state, archived | No valid transitions |

**Usage**:
- `ticket_list(state="in_progress")` - Filter by state
- `ticket_update(ticket_id="...", state="ready")` - Update state
- `ticket_transition(ticket_id="...", to_state="done")` - Validated transition

**See Also**: `/docs/ticket-workflows.md` for complete state machine rules

---

### Priority Levels

Valid values for `priority` parameter:

| Priority | Description | Use Case | Auto-Assignment |
|----------|-------------|----------|----------------|
| `low` | Minor issues, nice-to-haves | Documentation, small improvements | No urgency |
| `medium` | Standard priority (default) | Regular features, non-blocking bugs | Normal queue |
| `high` | Important, time-sensitive | Customer-facing bugs, deadlines | Escalated attention |
| `critical` | Urgent, blocking work | Production outages, security issues | Immediate action |

**Semantic Matching**: `ticket_create` and `ticket_update` support natural language:
- `"urgent"`, `"asap"`, `"important"` → `high`
- `"blocker"`, `"emergency"` → `critical`
- `"minor"`, `"trivial"` → `low`

**Usage**:
- `ticket_create(title="...", priority="high")` - Set priority
- `ticket_list(priority="critical")` - Filter by priority
- `ticket_update(ticket_id="...", priority="urgent")` - Supports semantic input

---

### Adapter Types

Valid values for `adapter` or `adapter_name` parameters:

| Adapter | Description | Configuration Required |
|---------|-------------|----------------------|
| `aitrackdown` | File-based local tracking | Project path |
| `linear` | Linear.app integration | API key, team key |
| `github` | GitHub Issues | Personal access token, repo |
| `jira` | Atlassian JIRA | API token, domain, project key |
| `asana` | Asana projects | Personal access token, workspace |

**Usage**:
- `config_set_primary_adapter("linear")` - Set default
- `config_test_adapter("github")` - Test connectivity
- `label_list(adapter_name="jira")` - Query specific adapter

**See Also**: `/docs/adapter-configuration.md` for setup instructions

---

### Common Parameters

#### Pagination Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 10-20 | Maximum items to return (max: 50-100) |
| `offset` | int | 0 | Items to skip for pagination |
| `page` | int | 1 | Page number (alternative to offset) |

**Usage**:
- `ticket_list(limit=50, offset=0)` - First 50 tickets
- `ticket_list(limit=50, offset=50)` - Next 50 tickets

---

#### Filter Parameters

| Parameter | Type | Description | Valid Values |
|-----------|------|-------------|--------------|
| `state` | str\|None | Workflow state filter | See: Workflow States |
| `priority` | str\|None | Priority level filter | See: Priority Levels |
| `assignee` | str\|None | User filter (ID or email) | User identifier |
| `tags` | list[str]\|None | Tag filter (all must match) | Tag names |
| `compact` | bool | Return minimal fields | `true`, `false` |

**Usage**:
- `ticket_list(state="open", assignee="user@example.com")`
- `ticket_search(query="bug", priority="high", tags=["backend"])`

---

#### User Identifiers

Accepted formats for `assignee`, `user_id`, `lead_id` parameters:

- **Email**: `user@example.com` (recommended, works across adapters)
- **UUID**: `550e8400-e29b-41d4-a716-446655440000` (Linear, Asana)
- **Username**: `github-username` (GitHub)
- **Account ID**: `557058:f58131cb-b67d-43c7-b30d-6b58d40bd077` (JIRA)

**Adapter-Specific**:
- Linear: Prefers UUID or email
- GitHub: Requires username
- JIRA: Requires account ID or email
- Asana: Accepts GID or email

---

## Error Handling Patterns

### Common Error Types

**Configuration Errors**:
```json
{
  "status": "error",
  "error": "API_KEY environment variable not set",
  "error_type": "ConfigurationError",
  "remediation": "Set LINEAR_API_KEY in environment or .env file"
}
```

**Validation Errors**:
```json
{
  "status": "error",
  "error": "Invalid state transition: closed → in_progress",
  "error_type": "ValidationError",
  "valid_transitions": ["No transitions from closed state"],
  "current_state": "closed"
}
```

**Not Found Errors**:
```json
{
  "status": "error",
  "error": "Ticket PROJ-999 not found",
  "error_type": "NotFoundError",
  "ticket_id": "PROJ-999"
}
```

**Adapter Errors**:
```json
{
  "status": "error",
  "error": "Linear API returned 401 Unauthorized",
  "error_type": "AdapterError",
  "adapter": "linear",
  "http_status": 401,
  "remediation": "Check LINEAR_API_KEY is valid and not expired"
}
```

---

## Performance Considerations

### Token Usage Optimization

**Compact Mode**: Use `compact=true` for list operations to reduce token usage by 85%

```python
# Full mode: ~185 tokens per ticket
ticket_list(limit=20, compact=False)  # ~3,700 tokens

# Compact mode: ~15 tokens per ticket
ticket_list(limit=20, compact=True)   # ~300 tokens (recommended)
```

**Pagination**: Limit results to reduce token consumption

```python
# Inefficient: Returns all tickets
ticket_list(limit=100)  # May return thousands of tokens

# Efficient: Fetch only what you need
ticket_list(limit=10, state="in_progress")  # Minimal tokens
```

### Rate Limiting

Some adapters enforce rate limits:

- **Linear**: 50 requests/second, 5000/hour
- **GitHub**: 5000 requests/hour (authenticated)
- **JIRA**: 10 requests/second (varies by plan)

**Best Practice**: Cache results when possible, use `compact=true` for bulk operations.

---

## Response Field Mappings

### Adapter Field Variations

Different adapters may return slightly different field names:

| Standard Field | Linear | GitHub | JIRA | Asana |
|---------------|--------|--------|------|-------|
| `id` | UUID | Number | Key | GID |
| `identifier` | Identifier | `#123` | Key | GID |
| `state` | State name | State | Status | Custom field |
| `assignee` | User UUID | Username | Account ID | User GID |
| `tags` | Label names | Label names | Labels | Tags |
| `created_at` | ISO timestamp | ISO timestamp | ISO timestamp | ISO timestamp |

**Normalization**: All adapters normalize to standard fields in responses.

---

## See Also

- `/docs/ticket-workflows.md` - Complete state machine and validation rules
- `/docs/adapter-configuration.md` - Adapter-specific setup instructions
- `/docs/semantic-matching.md` - Natural language input patterns
- `/docs/error-recovery.md` - Error handling and recovery strategies

---

**Note**: This reference document is maintained to reduce token usage in tool docstrings. All tool docstrings now reference this document instead of duplicating content.
