# Re-enable Attachment Tools in MCP Interface

**Date:** 2025-12-09
**Type:** Feature Re-enablement
**Ticket:** User Request
**Status:** ✅ Complete

## Summary

Re-enabled file attachment functionality in the MCP interface. The attachment tools (`ticket_attach` and `ticket_attachments`) are now available via MCP, allowing Claude Desktop/Code to attach files directly to tickets without requiring a separate filesystem MCP server.

## Changes Made

### 1. Added MCP Tool Decorators

**File:** `src/mcp_ticketer/mcp/server/tools/attachment_tools.py`

Added `@mcp.tool()` decorators to register the functions with FastMCP:

```python
# Before
from ..server_sdk import get_adapter

async def ticket_attach(

# After
from ..server_sdk import get_adapter, mcp

@mcp.tool()
async def ticket_attach(
```

```python
# Before
async def ticket_attachments(

# After
@mcp.tool()
async def ticket_attachments(
```

**Lines Changed:** Lines 13, 16, 148

### 2. Re-enabled Import in Tools Module

**File:** `src/mcp_ticketer/mcp/server/tools/__init__.py`

Uncommented the `attachment_tools` import and added to `__all__` list:

```python
# Before
from . import (
    analysis_tools,  # noqa: F401
    # attachment_tools removed - CLI-only (Phase 2 Sprint 1.3 - use filesystem MCP)
    bulk_tools,  # noqa: F401
    ...
)

__all__ = [
    "analysis_tools",
    # "attachment_tools" removed - CLI-only (Phase 2 Sprint 1.3)
    "bulk_tools",
    ...
]

# After
from . import (
    analysis_tools,  # noqa: F401
    attachment_tools,  # noqa: F401
    bulk_tools,  # noqa: F401
    ...
)

__all__ = [
    "analysis_tools",
    "attachment_tools",
    "bulk_tools",
    ...
]
```

**Lines Changed:** Lines 21, 35, 54

### 3. Updated Module Documentation

**File:** `src/mcp_ticketer/mcp/server/tools/__init__.py`

Updated docstring to reflect attachment_tools availability:

```python
# Before
"""
Modules:
    ...
    milestone_tools: Milestone management and progress tracking (1M-607)

Note:
    attachment_tools: Removed from MCP server (CLI-only as of Phase 2 Sprint 1.3)
    These tools are available via CLI commands but not exposed through MCP interface.
    Use filesystem MCP for file operations and GitHub MCP for PR management.
"""

# After
"""
Modules:
    ...
    milestone_tools: Milestone management and progress tracking (1M-607)
    attachment_tools: File attachment management (ticket_attach, ticket_attachments)

Note:
    instruction_tools: Removed from MCP server (CLI-only as of Phase 2 Sprint 2.3)
    pr_tools: Removed from MCP server (CLI-only as of Phase 2 Sprint 1.3)
    These tools are available via CLI commands but not exposed through MCP interface.
    Use GitHub MCP for PR management.
"""
```

**Lines Changed:** Lines 7-27

### 4. Created Documentation

**New File:** `docs/ATTACHMENT_TOOLS.md`

Comprehensive documentation covering:
- Tool usage and parameters
- Adapter support matrix
- Implementation strategy and graceful degradation
- Error handling
- Migration guide from filesystem MCP
- Architecture and attachment flow

## MCP Tools Now Available

### `ticket_attach`

Attach a file to a ticket (issue or epic).

**Parameters:**
- `ticket_id` (str, required): Ticket ID or URL
- `file_path` (str, required): Absolute path to file
- `description` (str, optional): Attachment description

**Example:**
```python
result = await ticket_attach(
    ticket_id="PROJ-123",
    file_path="/Users/username/Documents/design.pdf",
    description="Updated design mockup"
)
```

### `ticket_attachments`

List all attachments for a ticket.

**Parameters:**
- `ticket_id` (str, required): Ticket ID or URL

**Example:**
```python
result = await ticket_attachments(ticket_id="PROJ-123")
```

## Implementation Details

### Graceful Degradation

The `ticket_attach` tool implements a three-tier fallback strategy:

1. **Linear Native Upload** (Preferred)
   - Uses `LinearAdapter.upload_file()` to upload to Linear storage
   - Uses `attach_file_to_issue()` or `attach_file_to_epic()` to create attachment
   - Returns full attachment metadata with URL

2. **Legacy Adapter Method**
   - Falls back to `adapter.add_attachment()` if available
   - Works with adapters that implement the legacy interface

3. **Comment Reference** (Always Works)
   - Adds file path as a comment if adapter doesn't support attachments
   - Ensures the operation never completely fails

### Adapter Support

| Adapter | Status | Implementation |
|---------|--------|---------------|
| **Linear** | ✅ Full Support | Native GraphQL upload + attachment |
| **GitHub** | ⚠️ Fallback Only | Comment reference (native impl possible) |
| **Jira** | ⚠️ Fallback Only | Comment reference (native impl possible) |
| **Asana** | ⚠️ Fallback Only | Comment reference (native impl possible) |

## Testing

### Syntax Validation

```bash
# Verified Python syntax
python3 -m py_compile src/mcp_ticketer/mcp/server/tools/attachment_tools.py
python3 -m py_compile src/mcp_ticketer/mcp/server/tools/__init__.py

# Verified AST parsing
python3 -c "import ast; ast.parse(open('src/mcp_ticketer/mcp/server/tools/attachment_tools.py').read())"
```

### Integration Testing

To fully test, restart the MCP server and verify tools appear in Claude Desktop/Code:

```bash
# Tools should now appear:
# - ticket_attach
# - ticket_attachments
```

## Important Considerations

### File Paths
- MCP tools require **absolute file paths**
- The MCP server must have read access to the file location
- Relative paths may not work correctly

### Security
- Be cautious about file contents (sensitive data, credentials, etc.)
- Files are uploaded to the ticket platform's storage
- Consider data sensitivity and compliance requirements

### Token Usage
- Attachment tools add approximately **~800 tokens** to MCP interface
- This is a one-time cost for tool definitions
- File upload is server-side (not in token context)

## Migration Path

### Previous Approach (Filesystem MCP)

```python
# 1. Upload via filesystem MCP
file_url = await filesystem_upload("/path/to/file.pdf")

# 2. Reference in comment
await ticket_comment(
    ticket_id="PROJ-123",
    operation="add",
    text=f"File: {file_url}"
)
```

### New Approach (Built-in Attachment)

```python
# Single step with native attachment
result = await ticket_attach(
    ticket_id="PROJ-123",
    file_path="/path/to/file.pdf",
    description="Design mockup"
)
```

## Why Was This Removed Originally?

From Phase 2 Sprint 1.3 comments:
> "Use filesystem MCP for file operations"

**Rationale:**
- Separation of concerns (file ops vs ticketing)
- Reduce token usage in MCP interface
- Leverage specialized filesystem MCP servers

## Why Re-enable Now?

**User Request:**
- Simplified workflow (one step vs two)
- Native platform integration (especially Linear)
- Attachment metadata stored in ticket system
- No need for additional MCP server

**Trade-offs Accepted:**
- Slightly higher token usage (~800 tokens)
- Some adapters only support fallback mode
- File access requirements for MCP server

## Future Enhancements

Potential improvements for other adapters:

1. **GitHub:** Implement via release assets or gists API
2. **Jira:** Implement via Jira REST API attachment endpoints
3. **Asana:** Implement via Asana file upload API
4. **Base64 Support:** Accept file content as base64 for remote scenarios
5. **URL Support:** Accept external URLs instead of file uploads

## References

- **Implementation:** `src/mcp_ticketer/mcp/server/tools/attachment_tools.py`
- **Documentation:** `docs/ATTACHMENT_TOOLS.md`
- **Research:** `docs/research/attachment-support-investigation-2025-12-09.md`
- **Linear Adapter:** `src/mcp_ticketer/adapters/linear/adapter.py` (upload_file, attach_file_to_issue, attach_file_to_epic)

## Rollback Instructions

If this change needs to be reverted:

1. Re-comment the import in `tools/__init__.py`:
   ```python
   # attachment_tools removed - CLI-only (Phase 2 Sprint 1.3 - use filesystem MCP)
   ```

2. Remove from `__all__` list

3. Optionally remove `@mcp.tool()` decorators from `attachment_tools.py`

---

**Change Author:** Python Engineer Agent
**Review Status:** Pending
**Testing Status:** Syntax validated, integration testing pending
**Documentation Status:** ✅ Complete
