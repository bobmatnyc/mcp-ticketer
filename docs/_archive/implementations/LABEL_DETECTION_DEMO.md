# Automatic Label/Tag Detection Feature

## Overview

The MCP Ticketer now includes **automatic label/tag detection** that intelligently applies relevant labels to tickets based on their title and description. This feature works across all supported adapters (GitHub, Jira, Linear, etc.).

## How It Works

When creating a ticket via MCP tools, the system:

1. **Scans available labels** from the configured adapter
2. **Analyzes ticket content** (title + description) for keywords
3. **Matches labels** based on semantic patterns
4. **Combines** auto-detected labels with user-specified ones
5. **Applies** the final label set to the ticket

## Supported Adapters

- **GitHub**: Uses repository labels
- **Jira**: Uses project labels (sampled from recent issues)
- **Linear**: Uses team labels
- **Asana**: Uses workspace tags (if supported)

## Usage Examples

### Example 1: Bug Detection

```python
# Title: "Fix crash when opening file"
# Description: "The app crashes unexpectedly when users try to open large files"

# Auto-detected labels: ["bug", "critical"]
```

**Keywords detected**: `crash`, `bug`, `fix`

### Example 2: Feature Request

```python
# Title: "Add dark mode support"
# Description: "Implement dark mode feature for better UI experience"

# Auto-detected labels: ["feature", "ui", "enhancement"]
```

**Keywords detected**: `add`, `feature`, `implement`, `ui`

### Example 3: Performance Optimization

```python
# Title: "Optimize database queries"
# Description: "Improve performance of slow queries in the backend"

# Auto-detected labels: ["performance", "backend", "improvement"]
```

**Keywords detected**: `optimize`, `performance`, `slow`, `backend`, `improve`

### Example 4: Security Issue

```python
# Title: "Fix authentication vulnerability"
# Description: "Security issue with auth middleware"

# Auto-detected labels: ["security", "bug", "critical"]
```

**Keywords detected**: `fix`, `security`, `vulnerability`, `auth`

## Label Keyword Patterns

The system recognizes these common patterns:

| Label Category | Keywords |
|---------------|----------|
| **bug** | bug, error, broken, crash, fix, issue, defect |
| **feature** | feature, add, new, implement, create, enhancement |
| **improvement** | enhance, improve, update, upgrade, refactor, optimize |
| **documentation** | doc, documentation, readme, guide, manual |
| **test** | test, testing, qa, validation, verify |
| **security** | security, vulnerability, auth, permission, exploit |
| **performance** | performance, slow, optimize, speed, latency |
| **ui** | ui, ux, interface, design, layout, frontend |
| **api** | api, endpoint, rest, graphql, backend |
| **backend** | backend, server, database, storage |
| **frontend** | frontend, client, web, react, vue |
| **critical** | critical, urgent, emergency, blocker |

## MCP Tool Parameters

All ticket creation tools now support:

- `tags` (optional): User-specified labels/tags
- `auto_detect_labels` (optional, default: `true`): Enable/disable auto-detection

### ticket_create

```python
await ticket_create(
    title="Fix authentication bug",
    description="Security vulnerability in login",
    tags=["high-priority"],  # User-specified
    auto_detect_labels=True   # Auto-detect enabled
)

# Result: tags = ["high-priority", "bug", "security"]
```

### issue_create

```python
await issue_create(
    title="Add user dashboard",
    description="Create new dashboard with analytics",
    epic_id="EPIC-123",
    tags=["sprint-5"],
    auto_detect_labels=True
)

# Result: tags = ["sprint-5", "feature", "ui"]
```

### task_create

```python
await task_create(
    title="Write unit tests for API",
    description="Add test coverage for authentication endpoints",
    issue_id="ISSUE-456",
    tags=["qa"],
    auto_detect_labels=True
)

# Result: tags = ["qa", "test", "api"]
```

## Disabling Auto-Detection

To disable auto-detection and use only user-specified labels:

```python
await ticket_create(
    title="Fix bug",
    description="Bug description",
    tags=["custom-label"],
    auto_detect_labels=False  # Disabled
)

# Result: tags = ["custom-label"]  # Only user labels
```

## Label Deduplication

The system automatically prevents duplicate labels:

```python
await ticket_create(
    title="Fix bug",
    description="Bug in authentication",
    tags=["bug"],  # User already specified "bug"
    auto_detect_labels=True
)

# Result: tags = ["bug", "security"]  # No duplicate "bug"
```

## Adapter-Specific Behavior

### GitHub
- Uses repository labels via GitHub API
- Creates missing labels automatically if needed
- Caches labels for performance

### Jira
- Queries recent issues (100 max) to extract used labels
- No direct "list all labels" endpoint in Jira
- Returns sorted unique labels

### Linear
- Uses team labels from Linear workspace
- Caches labels on initialization
- Returns labels with color information

## Implementation Details

### Core Function

```python
async def detect_and_apply_labels(
    adapter,
    ticket_title: str,
    ticket_description: str,
    existing_labels: list[str] | None = None,
) -> list[str]:
    """Detect and suggest labels/tags based on ticket content."""
```

**Located in**: `src/mcp_ticketer/mcp/server/tools/ticket_tools.py`

### Adapter Methods

All adapters now implement:

```python
async def list_labels(self) -> builtins.list[dict[str, Any]]:
    """List all labels available in the adapter."""
```

**Returns**:
```python
[
    {"id": "bug", "name": "bug", "color": "#d73a4a"},
    {"id": "feature", "name": "feature", "color": "#0052cc"},
    ...
]
```

## Test Coverage

The feature includes 20 comprehensive tests covering:

- ✅ Bug keyword detection
- ✅ Feature keyword detection
- ✅ Performance keyword detection
- ✅ Security keyword detection
- ✅ Documentation keyword detection
- ✅ Direct label name matching
- ✅ Multiple label detection
- ✅ User label preservation
- ✅ No duplicate labels
- ✅ Adapter without label support
- ✅ Empty content handling
- ✅ No matches scenario
- ✅ Case-insensitive matching
- ✅ UI/Frontend detection
- ✅ Backend/API detection
- ✅ Test/QA detection
- ✅ Adapter exception handling
- ✅ Empty adapter labels
- ✅ String format labels

**Test file**: `tests/test_label_detection.py`

## Configuration

No additional configuration required. The feature works automatically with existing adapter configurations.

## Benefits

1. **Consistency**: Automatically applies standard labels across all tickets
2. **Time-saving**: No manual label selection needed
3. **Accuracy**: Semantic matching improves label relevance
4. **Flexibility**: Can be disabled when needed
5. **Additive**: Combines with user-specified labels

## Edge Cases Handled

- Adapter doesn't support labels → Returns user labels only
- Adapter.list_labels() fails → Gracefully returns user labels
- Empty adapter labels → Returns user labels only
- No matching labels → Returns user labels only
- Duplicate labels → Deduplicates automatically
- Case sensitivity → All matching is case-insensitive

## Future Enhancements

Potential improvements:

- ML-based label prediction
- Custom keyword mappings per project
- Label confidence scores
- Label suggestion UI in Claude Desktop
- Historical label usage statistics

## Implementation Summary

**Files Modified**:
1. `src/mcp_ticketer/mcp/server/tools/ticket_tools.py` - Core detection function + updated `ticket_create`
2. `src/mcp_ticketer/mcp/server/tools/hierarchy_tools.py` - Updated `issue_create` and `task_create`
3. `src/mcp_ticketer/adapters/github.py` - Added `list_labels()` method
4. `src/mcp_ticketer/adapters/jira.py` - Added `list_labels()` method
5. `src/mcp_ticketer/adapters/linear/adapter.py` - Added `list_labels()` method

**New Files**:
1. `tests/test_label_detection.py` - 20 comprehensive tests

**Net LOC Impact**: +~250 lines (within minimization guidelines for new feature)

## Documentation

- Docstrings updated for all modified functions
- MCP tool descriptions enhanced with auto-detection details
- Type hints use proper `builtins.list` for compatibility
