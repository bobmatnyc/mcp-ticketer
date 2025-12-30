# Research: CLI Flag Inconsistencies (Issue #46)

**Date**: 2025-12-30
**Issue**: #46
**Research Type**: Bug Investigation
**Status**: Complete

## Executive Summary

Investigation of CLI flag inconsistencies across mcp-ticketer commands reveals:
- **CLI (ticket_commands.py)**: Uses `--tag` (singular) for tags parameter
- **MCP Server Tools**: Consistently use `tags` (plural) for parameter names
- **CLI (ticket_commands.py)**: Uses both `--project` and `--epic` as synonyms for parent epic
- No aliases configured between singular/plural forms

**Impact**: Medium - Users may be confused by inconsistent naming, especially when transitioning between CLI and MCP interfaces.

## Investigation Findings

### 1. Tags Flag Analysis

#### CLI Layer (ticket_commands.py)

**Location**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/ticket_commands.py`

**Line 200-202**:
```python
tags: list[str] | None = typer.Option(
    None, "--tag", "-t", help="Tags (can be specified multiple times)"
),
```

**Finding**: The CLI uses `--tag` (singular) despite the Python parameter being named `tags` (plural).

#### MCP Server Layer

**Location**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/`

**Multiple files consistently use `tags` (plural)**:

1. **ticket_tools.py:250**:
```python
tags: list[str] | None = None,
```

2. **hierarchy_tools.py:88**:
```python
tags: list[str] | None = None,
```

3. **bulk_tools.py:40** (documentation):
```python
# description, priority, tags, assignee, ticket_type, parent_epic, parent_issue
```

4. **dto.py** (multiple locations):
```python
tags: list[str] = Field(default_factory=list, description="Ticket tags")
tags: list[str] = Field(default_factory=list, description="Issue tags")
tags: list[str] = Field(default_factory=list, description="Task tags")
tags: list[str] | None = Field(None, description="Filter by tags")
```

**Finding**: MCP server tools universally use `tags` (plural) for consistency.

### 2. Epic/Project Flag Analysis

#### CLI Layer (ticket_commands.py)

**Lines 206-215**:
```python
project: str | None = typer.Option(
    None,
    "--project",
    help="Parent project/epic ID (synonym for --epic)",
),
epic: str | None = typer.Option(
    None,
    "--epic",
    help="Parent epic/project ID (synonym for --project)",
),
```

**Line 302**:
```python
# Resolve project/epic synonym - prefer whichever is provided
parent_epic_id = project or epic
```

**Finding**: The CLI provides both `--project` and `--epic` as command-line options, treating them as synonyms. However, these are two separate parameters rather than aliases.

#### MCP Server Layer

**Consistent naming across all tools**:

1. **ticket_tools.py:252**:
```python
parent_epic: str | None = _UNSET,
```

2. **hierarchy_tools.py:68**:
```python
epic_id: str | None = None,
```

3. **bulk_tools.py:40**:
```python
# parent_epic, parent_issue
```

4. **dto.py:34**:
```python
epic_id: str | None = Field(None, description="Parent epic ID")
```

**Finding**: MCP tools consistently use `parent_epic` or `epic_id` (no "project" terminology).

### 3. Other Commands Analysis

**Search for other commands with these flags**:

Searched entire codebase for:
- Other ticket creation/update commands
- Issue/task creation commands
- Hierarchy management commands

**Result**: No other CLI commands found with `--tag/--tags` or `--epic/--project` flags. The ticket create command appears to be the only CLI command with these parameters.

### 4. Framework Capabilities (Typer)

**Typer Parameter Aliases**:

Typer supports multiple flag names through its option definition:
```python
typer.Option(None, "--flag-name", "--alias1", "--alias2", ...)
```

**Example from codebase**:
```python
# Line 201
tags: list[str] | None = typer.Option(
    None, "--tag", "-t", help="Tags (can be specified multiple times)"
)
```

This already uses `-t` as a short alias for `--tag`.

**Capability Confirmed**: Typer can support multiple long-form aliases (e.g., `--tag` and `--tags`).

## Inconsistency Summary Table

| Component | Parameter | Flag/Field Name | Notes |
|-----------|-----------|-----------------|-------|
| **CLI** (ticket create) | tags | `--tag` | Singular, has `-t` alias |
| **MCP Tools** | tags | `tags` | Plural, consistent across all tools |
| **CLI** (ticket create) | parent epic | `--project`, `--epic` | Both accepted, resolved as synonyms |
| **MCP Tools** | parent epic | `parent_epic`, `epic_id` | No "project" terminology |

## Root Cause Analysis

### Why This Happened

1. **CLI-first design**: The CLI command (`ticket create`) was likely designed independently with `--tag` (singular) following a "specify multiple times" pattern.

2. **MCP API evolution**: When MCP server tools were added, they followed Python naming conventions with plural `tags` for list parameters.

3. **Project/Epic confusion**: The terms "project" and "epic" are used interchangeably in different issue tracking systems:
   - Linear/GitHub: "Projects"
   - Jira: "Epics"
   - The CLI tried to accommodate both terminologies

4. **No cross-layer validation**: No linting or validation enforces consistency between CLI flags and MCP tool parameters.

## Impact Assessment

### User Impact

**Moderate Confusion**:
- Users calling `mcp-ticketer ticket create --tag bug` work correctly
- MCP clients using `tags=["bug"]` work correctly
- Documentation may show both forms, causing confusion

**Low Breakage Risk**:
- Both interfaces work correctly despite inconsistency
- No functional bugs, only naming inconsistency

### Developer Impact

**Medium Maintenance Burden**:
- Need to remember different naming conventions for CLI vs MCP
- Code reviews may miss inconsistencies
- Future CLI additions may propagate inconsistency

## Recommendations

### Primary Recommendation: Standardize on Plural with Aliases

**For Tags**:
```python
tags: list[str] | None = typer.Option(
    None,
    "--tags",      # Primary (plural, matches MCP)
    "--tag",       # Alias (backward compatibility)
    "-t",          # Short form
    help="Tags (can be specified multiple times)"
)
```

**Rationale**:
- Matches Python parameter name (`tags`)
- Matches MCP tool parameter names
- Maintains backward compatibility via alias
- Follows Python convention (list parameters are plural)

**For Epic/Project**:
```python
parent_epic: str | None = typer.Option(
    None,
    "--parent-epic",  # Primary (matches MCP tools)
    "--epic",         # Alias (shorter form)
    "--project",      # Alias (backward compatibility)
    "-e",             # Short form
    help="Parent epic/project ID"
)
```

**Rationale**:
- `--parent-epic` is more descriptive and explicit
- Matches MCP tool parameter name (`parent_epic`)
- Maintains all existing flags as aliases
- Improves clarity (distinguishes from project config)

### Alternative Recommendation: Document Current Behavior

If changing flags is too disruptive:
1. Document that CLI uses `--tag` (singular)
2. Document that MCP uses `tags` (plural)
3. Explain in CLI help text why singular is used
4. Add to FAQ/troubleshooting docs

### Implementation Approach

**Phase 1: Add Aliases (Non-Breaking)**
```python
# ticket_commands.py line ~200
tags: list[str] | None = typer.Option(
    None,
    "--tags",      # NEW: Primary plural form
    "--tag",       # EXISTING: Keep for backward compatibility
    "-t",          # EXISTING: Keep short form
    help="Tags/labels (plural: --tags recommended, singular: --tag for compatibility)"
)

# ticket_commands.py line ~206
parent_epic: str | None = typer.Option(
    None,
    "--parent-epic",  # NEW: Primary explicit form
    "--epic",         # EXISTING: Keep as alias
    "--project",      # EXISTING: Keep as alias
    "-e",             # NEW: Short form
    help="Parent epic/project ID (--parent-epic recommended)"
)
```

**Phase 2: Update Documentation**
- Update README examples to use `--tags` and `--parent-epic`
- Add note about aliases for backward compatibility
- Update CLI help text to indicate preferred forms

**Phase 3: Deprecation Notices (Optional, Future)**
- After 6-12 months, add deprecation warnings for `--tag` and `--project`
- Eventually remove aliases in major version bump (v3.0.0)

## Testing Strategy

### Test Cases Required

1. **Backward Compatibility Tests**:
   ```bash
   # Existing usage should still work
   mcp-ticketer ticket create "Test" --tag bug --tag feature
   mcp-ticketer ticket create "Test" --project EPIC-123
   mcp-ticketer ticket create "Test" --epic EPIC-123
   ```

2. **New Primary Forms Tests**:
   ```bash
   # New recommended usage
   mcp-ticketer ticket create "Test" --tags bug --tags feature
   mcp-ticketer ticket create "Test" --parent-epic EPIC-123
   ```

3. **Mixed Usage Tests**:
   ```bash
   # Ensure aliases work together
   mcp-ticketer ticket create "Test" --tag bug --tags feature  # Should work
   ```

4. **Short Form Tests**:
   ```bash
   # Existing and new short forms
   mcp-ticketer ticket create "Test" -t bug -t feature
   mcp-ticketer ticket create "Test" -e EPIC-123  # If added
   ```

5. **MCP Tool Integration Tests**:
   - Verify MCP `ticket(action="create", tags=["bug"])` still works
   - Verify CLI `--tags` values pass through correctly to MCP layer

## Related Files

### Files to Modify (Phase 1)
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/ticket_commands.py` (lines 200-215)

### Files to Review for Consistency
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/ticket_tools.py`
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/hierarchy_tools.py`
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/dto.py`

### Documentation to Update
- `README.md` (CLI examples)
- `docs/getting-started/` (quickstart guides)
- `docs/guides/` (CLI usage guides)
- CLI `--help` text (inline in commands)

## Implementation Checklist

- [ ] Update CLI flags with aliases (ticket_commands.py)
- [ ] Add unit tests for flag aliases
- [ ] Update CLI help text to indicate preferred forms
- [ ] Update README.md with new examples
- [ ] Update docs/getting-started/ examples
- [ ] Update docs/guides/ CLI reference
- [ ] Test backward compatibility
- [ ] Test new primary forms
- [ ] Add to CHANGELOG.md
- [ ] Consider deprecation timeline (optional)

## Questions for Maintainers

1. **Breaking Changes Policy**: What is the policy for changing CLI flags? Is backward compatibility required?
2. **Deprecation Timeline**: If we deprecate `--tag` and `--project`, what is the recommended timeline?
3. **MCP Consistency**: Should we enforce consistency between CLI flags and MCP parameter names?
4. **Documentation Priority**: Should docs show new forms or maintain existing examples?
5. **Other Commands**: Are there plans to add `--tag` or `--epic` flags to other commands (update, search, etc.)?

## Additional Notes

### Typer Alias Behavior

From Typer documentation and testing:
- Multiple option names are treated as aliases
- First option name is the "primary" shown in help text
- All aliases are functionally equivalent
- No performance penalty for using aliases

### Python Naming Conventions

PEP 8 guidance on parameter names:
- Collection parameters should be plural (e.g., `tags`, not `tag`)
- Singular naming is acceptable when "specify multiple times" pattern is used
- CLI flags can differ from Python parameter names for ergonomics

### Industry Conventions

Comparison with other CLIs:
- **git**: Uses plural (`--tags` in some commands)
- **docker**: Uses plural (`--label` but parameter is `labels`)
- **kubectl**: Mixed usage depending on command

**Recommendation**: Follow Python conventions (plural) for consistency with MCP layer.

---

## Conclusion

The CLI flag inconsistency is a moderate issue that can be resolved non-destructively by:
1. Adding plural forms (`--tags`, `--parent-epic`) as primary options
2. Maintaining existing forms as aliases for backward compatibility
3. Updating documentation to recommend new forms
4. Optionally planning deprecation timeline for legacy forms

This approach provides immediate consistency with MCP tools while maintaining full backward compatibility for existing users and scripts.
