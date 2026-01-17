# Linear Adapter Relationship Methods Implementation

## Summary

Implemented the three relationship methods in the Linear adapter to support ticket relationships (blocks, blocked_by, duplicates, duplicated_by, relates_to).

## Changes Made

### 1. GraphQL Queries and Mutations (`src/mcp_ticketer/adapters/linear/queries.py`)

Added three new GraphQL operations:

- **CREATE_ISSUE_RELATION_MUTATION**: Creates a relationship between two issues
- **DELETE_ISSUE_RELATION_MUTATION**: Deletes a relationship by its ID
- **GET_ISSUE_RELATIONS_QUERY**: Fetches all relationships for a given issue

### 2. Type Mappings (`src/mcp_ticketer/adapters/linear/types.py`)

Added two mapping functions for bidirectional conversion:

- **get_linear_relation_type(RelationType) -> str**: Converts universal RelationType to Linear's IssueRelationType
- **get_universal_relation_type(str) -> RelationType**: Converts Linear's relation type back to universal RelationType

Mapping table:
| Universal Type | Linear Type |
|----------------|-------------|
| BLOCKS | blocks |
| BLOCKED_BY | blockedBy |
| DUPLICATES | duplicate |
| DUPLICATED_BY | duplicatedBy |
| RELATES_TO | relates |

### 3. Adapter Methods (`src/mcp_ticketer/adapters/linear/adapter.py`)

Implemented three methods in the LinearAdapter class:

#### `add_relation(source_id, target_id, relation_type) -> TicketRelation`
- Converts universal relation type to Linear type
- Calls CREATE_ISSUE_RELATION_MUTATION
- Returns TicketRelation with populated metadata
- Raises exception on failure

#### `remove_relation(source_id, target_id, relation_type) -> bool`
- Lists relations to find the specific relation ID
- Calls DELETE_ISSUE_RELATION_MUTATION
- Returns True if successful, False otherwise
- Handles missing relations gracefully

#### `list_relations(ticket_id, relation_type=None) -> list[TicketRelation]`
- Queries issue relations using GET_ISSUE_RELATIONS_QUERY
- Optionally filters by relation type
- Returns list of TicketRelation objects
- Handles errors gracefully, returning empty list on failure

## Implementation Details

### Error Handling
- All methods use try/except blocks
- Errors are logged using the standard logger
- `add_relation` raises exceptions for failures
- `remove_relation` and `list_relations` return False/empty list on errors

### Logging
- Debug logs for all operations
- Info logs for successful operations
- Warning logs for not-found scenarios
- Error logs for exceptions

### Metadata
All TicketRelation objects include Linear-specific metadata:
- `relation_id`: Linear's internal relation ID
- `issue`: Source issue details
- `related_issue`: Target issue details (ID, identifier, title)

## Testing

Created `test_relations.py` with three test suites:
1. ✓ Bidirectional type mapping tests
2. ✓ Adapter method existence tests
3. ✓ GraphQL query/mutation definition tests

All tests pass successfully.

## Files Modified

1. `src/mcp_ticketer/adapters/linear/queries.py` (+58 lines)
2. `src/mcp_ticketer/adapters/linear/types.py` (+41 lines)
3. `src/mcp_ticketer/adapters/linear/adapter.py` (+201 lines)

## LOC Delta

- Added: 300 lines
- Removed: 0 lines
- Net Change: +300 lines

This is new functionality implementing the relationship interface defined in the base adapter.

## Usage Example

```python
from mcp_ticketer.adapters.linear.adapter import LinearAdapter
from mcp_ticketer.core.models import RelationType

adapter = LinearAdapter(...)

# Create a blocking relationship
relation = await adapter.add_relation(
    source_id="ISSUE-123",
    target_id="ISSUE-456",
    relation_type=RelationType.BLOCKS
)

# List all relations
relations = await adapter.list_relations("ISSUE-123")

# List only blocking relations
blocking = await adapter.list_relations(
    "ISSUE-123",
    relation_type=RelationType.BLOCKS
)

# Remove a relation
success = await adapter.remove_relation(
    source_id="ISSUE-123",
    target_id="ISSUE-456",
    relation_type=RelationType.BLOCKS
)
```

## Notes

- Linear automatically creates inverse relationships (e.g., creating BLOCKS also creates BLOCKED_BY)
- The implementation follows existing Linear adapter patterns (error handling, logging, GraphQL usage)
- All methods are async and use the existing LinearGraphQLClient
- Type conversions ensure compatibility between universal and Linear-specific types
