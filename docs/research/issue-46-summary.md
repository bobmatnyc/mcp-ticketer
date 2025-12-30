# Issue #46: CLI Flag Inconsistencies - Quick Reference

## Current State

### Tags Flag
- **CLI**: `--tag` (singular)
- **MCP**: `tags` (plural)
- **Inconsistency**: CLI uses singular, MCP uses plural

### Epic/Project Flag
- **CLI**: Both `--project` AND `--epic` accepted
- **MCP**: `parent_epic` or `epic_id` (no "project")
- **Inconsistency**: CLI has redundant synonyms

## Affected Files

**Primary File**:
- `src/mcp_ticketer/cli/ticket_commands.py:200-215`

**Related Files**:
- `src/mcp_ticketer/mcp/server/tools/ticket_tools.py`
- `src/mcp_ticketer/mcp/server/tools/hierarchy_tools.py`
- `src/mcp_ticketer/mcp/server/dto.py`

## Recommended Fix

```python
# CURRENT (line 200-202)
tags: list[str] | None = typer.Option(
    None, "--tag", "-t", help="Tags (can be specified multiple times)"
)

# RECOMMENDED
tags: list[str] | None = typer.Option(
    None,
    "--tags",      # Primary (matches MCP)
    "--tag",       # Alias (backward compatibility)
    "-t",          # Short form
    help="Tags (can be specified multiple times)"
)

# CURRENT (lines 206-215)
project: str | None = typer.Option(
    None, "--project", help="Parent project/epic ID (synonym for --epic)"
)
epic: str | None = typer.Option(
    None, "--epic", help="Parent epic/project ID (synonym for --project)"
)

# RECOMMENDED
parent_epic: str | None = typer.Option(
    None,
    "--parent-epic",  # Primary (matches MCP)
    "--epic",         # Alias
    "--project",      # Alias
    "-e",             # Short form
    help="Parent epic/project ID"
)
```

## Testing Commands

```bash
# Test backward compatibility
mcp-ticketer ticket create "Test" --tag bug --tag feature
mcp-ticketer ticket create "Test" --project EPIC-123
mcp-ticketer ticket create "Test" --epic EPIC-123

# Test new forms
mcp-ticketer ticket create "Test" --tags bug --tags feature
mcp-ticketer ticket create "Test" --parent-epic EPIC-123

# Test short forms
mcp-ticketer ticket create "Test" -t bug -t feature
mcp-ticketer ticket create "Test" -e EPIC-123
```

## Impact

- **Breaking Changes**: None (all existing flags maintained as aliases)
- **User Benefit**: Consistency between CLI and MCP interfaces
- **Migration Path**: Update docs to show preferred forms

## See Also

Full research document: `docs/research/issue-46-cli-flag-inconsistencies-2025-12-30.md`
