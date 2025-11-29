# MCP API Reference

This document provides standard response formats and parameter definitions for MCP Ticketer tools. Tools reference this document to reduce token usage while maintaining clarity.

## Standard Response Formats

### StandardResponse

Base response format for single-entity operations (create, read, update, delete, assign).

**Structure**:
```python
{
    "status": "completed" | "error",
    "adapter": str,              # Adapter type (linear, github, jira, etc.)
    "adapter_name": str,         # Human-readable adapter name
    "ticket": dict,              # Full ticket/entity object
    "error": str                 # Error message (if status="error")
}
```

**Optional Fields** (operation-dependent):
- `ticket_id`: Ticket identifier
- `routed_from_url`: Boolean indicating URL-based routing
- `previous_state`: State before operation
- `new_state`: State after operation
- `previous_assignee`: Assignee before operation
- `new_assignee`: Assignee after operation

**Usage**: References "StandardResponse with [specific fields]"

---

### ListResponse

Response format for list operations (ticket_list, epic_list, label_list).

**Structure**:
```python
{
    "status": "completed" | "error",
    "adapter": str,
    "adapter_name": str,
    "tickets": list[dict],       # List of entity objects
    "count": int,                # Number of entities returned
    "limit": int,                # Query limit used
    "offset": int,               # Query offset used
    "error": str                 # Error message (if status="error")
}
```

**Optional Fields**:
- `filters_applied`: Dict of filters used
- `total`: Total count (if adapter provides it)
- `has_more`: Boolean indicating more results available

**Usage**: References "ListResponse with tickets/epics/labels"

---

### ConfigResponse

Response format for configuration operations.

**Structure**:
```python
{
    "status": "completed" | "error",
    "message": str,              # Success/error message
    "config_path": str,          # Path to config file (if applicable)
    "error": str                 # Error message (if status="error")
}
```

**Optional Fields** (operation-dependent):
- `previous_value`: Previous configuration value
- `new_value`: New configuration value
- `config`: Complete configuration dictionary
- `validation_results`: Validation status per adapter

**Usage**: References "ConfigResponse with [specific fields]"

---

### TransitionResponse

Response format for state transition operations.

**Structure**:
```python
{
    "status": "completed" | "needs_confirmation" | "error",
    "adapter": str,
    "adapter_name": str,
    "ticket": dict,              # Updated ticket object
    "previous_state": str,       # State before transition
    "new_state": str,            # State after transition
    "error": str                 # Error message (if status="error")
}
```

**Optional Fields** (semantic matching):
- `matched_state`: State matched from natural language input
- `confidence`: Confidence score (0.0-1.0)
- `original_input`: User's original input
- `suggestions`: Alternative matches for ambiguous input
- `comment_added`: Boolean indicating comment was added

**Usage**: References "TransitionResponse with state changes and confidence"

---

### AnalysisResponse

Response format for analysis and reporting operations.

**Structure**:
```python
{
    "status": "completed" | "error",
    "adapter": str,
    "adapter_name": str,
    "summary": dict,             # High-level statistics
    "recommendations": list[str], # Actionable recommendations
    "error": str                 # Error message (if status="error")
}
```

**Optional Fields** (analysis-dependent):
- `duplicates`: List of duplicate groups
- `spelling_issues`: List of spelling problems
- `unused_labels`: List of unused labels
- `stale_tickets`: List of stale ticket objects

**Usage**: References "AnalysisResponse with summary and recommendations"

---

## Parameter Glossary

### Common Parameters

#### ticket_id
- **Type**: `str`
- **Description**: Unique identifier of the ticket
- **Formats**: Plain ID (e.g., "ABC-123", UUID) or full URL
- **Supported URLs**:
  - Linear: `https://linear.app/team/issue/ABC-123`
  - GitHub: `https://github.com/owner/repo/issues/123`
  - JIRA: `https://company.atlassian.net/browse/PROJ-123`
  - Asana: `https://app.asana.com/0/1234567890/9876543210`

#### state
- **Type**: `str | None`
- **Description**: Workflow state filter or target state
- **Valid Values**: `open`, `in_progress`, `ready`, `tested`, `done`, `closed`, `waiting`, `blocked`
- **State Machine**: See [Workflow Documentation](#workflow-state-machine)
- **Default**: `None` (no filter)

#### priority
- **Type**: `str`
- **Description**: Priority level (supports semantic matching)
- **Exact Values**: `low`, `medium`, `high`, `critical`
- **Natural Language Examples**: "urgent", "asap", "important", "not urgent"
- **Default**: `"medium"`
- **See**: [Priority Matching Documentation](#priority-semantic-matching)

#### tags / labels
- **Type**: `list[str] | None`
- **Description**: List of tags/labels to categorize the ticket
- **Format**: Platform-specific label identifiers or names
- **Default**: `None` or `[]`
- **Auto-detection**: Some tools support automatic label detection

#### assignee
- **Type**: `str | None`
- **Description**: User identifier or email to assign the ticket to
- **Formats**:
  - Linear: User UUID or email
  - GitHub: Username
  - JIRA: Account ID or email
  - Asana: User GID or email
- **Default**: `None` (unassigned) or configured default user

#### limit
- **Type**: `int`
- **Description**: Maximum number of results to return
- **Default**: Tool-specific (typically 10-20)
- **Max**: Tool-specific (typically 50-100)
- **Performance**: Use compact mode for large limits

#### offset
- **Type**: `int`
- **Description**: Number of results to skip for pagination
- **Default**: `0`
- **Usage**: For iterating through large result sets

#### project_id / epic_id
- **Type**: `str | None`
- **Description**: Parent project or epic identifier
- **Formats**: Platform-specific ID, key, or UUID
- **Default**: `None` or configured default project

---

## Workflow State Machine

Valid state transitions defined by `TicketState.can_transition_to()`:

```
OPEN → IN_PROGRESS, WAITING, BLOCKED, CLOSED
IN_PROGRESS → READY, WAITING, BLOCKED, OPEN
READY → TESTED, IN_PROGRESS, BLOCKED
TESTED → DONE, IN_PROGRESS
DONE → CLOSED
WAITING → OPEN, IN_PROGRESS, CLOSED
BLOCKED → OPEN, IN_PROGRESS, CLOSED
CLOSED → (terminal state, no transitions)
```

**State Descriptions**:
- `OPEN`: Ticket is in backlog, not started
- `IN_PROGRESS`: Active work in progress
- `READY`: Work complete, ready for review/testing
- `TESTED`: Code reviewed and tested, ready for deployment
- `DONE`: Deployed to production
- `CLOSED`: Ticket completed and archived
- `WAITING`: Paused while waiting for external dependency
- `BLOCKED`: Cannot proceed due to impediment

---

## Priority Semantic Matching

The priority parameter supports natural language input with semantic matching:

**Confidence Levels**:
- **High** (≥0.90): Auto-applied
- **Medium** (0.70-0.89): May require confirmation
- **Low** (<0.70): Returns suggestions

**Natural Language Examples**:
- "urgent", "asap", "critical", "emergency" → `critical`
- "important", "high priority" → `high`
- "normal", "standard" → `medium`
- "low priority", "not urgent", "minor" → `low`

**Exact Values** (for precise control):
- `low`, `medium`, `high`, `critical`

---

## Error Handling

All tools follow consistent error handling patterns:

**Error Response Structure**:
```python
{
    "status": "error",
    "error": str,                # Human-readable error message
    "adapter": str,              # Adapter type (if available)
    "adapter_name": str          # Adapter name (if available)
}
```

**Optional Error Fields**:
- `diagnostic_suggestion`: System-level diagnostic info
- `valid_values`: List of valid values for validation errors
- `setup_command`: Tool to run for configuration errors
- `requires_ticket_association`: Boolean for session errors

**Common Error Types**:
1. **Validation Errors**: Invalid parameter values
2. **Configuration Errors**: Missing or invalid configuration
3. **Adapter Errors**: Platform-specific API failures
4. **Workflow Errors**: Invalid state transitions
5. **Session Errors**: Missing ticket association

---

## Compact Mode

List operations support compact mode for token efficiency:

**Compact Mode** (`compact=True`, default for most list operations):
- Returns: `id`, `title`, `state` only
- Token usage: ~15 tokens per ticket
- Use for: Routine queries, large result sets

**Full Mode** (`compact=False`):
- Returns: Complete ticket object with all fields
- Token usage: ~185 tokens per ticket
- Use for: When descriptions/metadata explicitly needed

**Token Usage Examples**:
- 20 tickets, compact: ~300 tokens (~0.15% of context)
- 20 tickets, full: ~3,700 tokens (~1.85% of context)
- 50 tickets, compact: ~750 tokens (~0.38% of context)
- 50 tickets, full: ~9,250 tokens (~4.6% of context)

---

## Reference Patterns

Tools reference this document using these patterns:

**Standard Response**:
```python
Returns: StandardResponse with ticket and assignee changes
```

**List Response**:
```python
Returns: ListResponse with tickets (compact mode supported)
```

**Parameter Reference**:
```python
Args:
    ticket_id: See glossary
    state: Workflow state (see glossary for valid values)
    priority: Priority level (see glossary for semantic matching)
```

**Error Handling**:
```python
Error Conditions: See mcp-api-reference.md#error-handling
```

---

## Document Maintenance

**When to Update**:
- New response format patterns emerge
- Parameter definitions change
- Workflow state machine is modified
- Error handling patterns evolve

**Version History**:
- 2025-11-29: Initial version (Phase 2 optimization)
