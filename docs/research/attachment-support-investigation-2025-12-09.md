# MCP-Ticketer Attachment Support Investigation

**Date:** 2025-12-09
**Researcher:** Research Agent
**Status:** Complete

## Executive Summary

**mcp-ticketer DOES support file attachments**, but the functionality is **NOT exposed via MCP tools**. Attachments are available only through the CLI interface. The attachment infrastructure is fully implemented in the Linear adapter with comprehensive upload and attachment capabilities.

## Key Findings

### 1. Attachment Model Exists

**Location:** `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/core/models.py` (line 389)

The `Attachment` model is defined with full metadata support:

```python
class Attachment(BaseModel):
    """File attachment metadata for tickets."""
    id: str | None
    ticket_id: str
    filename: str
    url: str | None
    content_type: str | None  # MIME type
    size_bytes: int | None
    created_at: datetime | None
    created_by: str | None
    description: str | None
    metadata: dict[str, Any]
```

### 2. Base Adapter Interface

**Location:** `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/core/adapter.py` (lines 554-584)

The base adapter defines attachment methods that raise `NotImplementedError` by default:

```python
async def add_attachment(
    self,
    ticket_id: str,
    file_path: str,
    description: str | None = None,
) -> Attachment:
    """Attach a file to a ticket."""
    raise NotImplementedError(
        f"{self.__class__.__name__} does not support file attachments. "
        "Use comments to reference external files instead."
    )

async def get_attachments(self, ticket_id: str) -> list[Attachment]:
    """Get all attachments for a ticket."""
    # Implementation not shown (also raises NotImplementedError)
```

### 3. Linear Adapter Implementation

**Location:** `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/adapter.py`

The Linear adapter has **full attachment support** with three specialized methods:

#### Method 1: `upload_file()` (line 2756)
Uploads a file to Linear's storage and returns the asset URL.

```python
async def upload_file(self, file_path: str, mime_type: str | None = None) -> str:
    """Upload a file to Linear's storage.

    Returns:
        Asset URL for the uploaded file
    """
```

#### Method 2: `attach_file_to_issue()` (line 2869)
Attaches an uploaded file (or external URL) to a Linear issue.

```python
async def attach_file_to_issue(
    self,
    issue_id: str,
    file_url: str,
    title: str,
    subtitle: str | None = None,
    comment_body: str | None = None,
) -> dict[str, Any]:
    """Attach a file to a Linear issue.

    The file must already be uploaded using upload_file() or be a publicly
    accessible URL.
    """
```

#### Method 3: `attach_file_to_epic()` (line 2952)
Attaches an uploaded file (or external URL) to a Linear project (epic).

```python
async def attach_file_to_epic(
    self,
    epic_id: str,
    file_url: str,
    title: str,
    subtitle: str | None = None,
) -> dict[str, Any]:
    """Attach a file to a Linear project (epic).

    The file must already be uploaded using upload_file() or be a publicly
    accessible URL.
    """
```

### 4. Attachment Tools (CLI-Only)

**Location:** `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/attachment_tools.py`

The attachment tools exist and provide comprehensive functionality:

- `ticket_attach()`: Attach a file to a ticket (issue or epic)
- `ticket_attachments()`: List all attachments for a ticket

**Implementation Strategy:**
1. Tries Linear-specific upload methods first (most advanced)
2. Falls back to legacy `add_attachment()` method
3. Final fallback: Adds file reference as a comment

**Status:** Removed from MCP tool exports in Phase 2 Sprint 1.3

From `tools/__init__.py`:
```python
# attachment_tools removed - CLI-only (Phase 2 Sprint 1.3 - use filesystem MCP)
```

## Architecture Analysis

### Attachment Flow (Linear)

```
User Request → CLI/MCP Tool
    ↓
ticket_attach()
    ↓
1. Read ticket (validate exists)
2. Check file exists locally
3. Determine MIME type
    ↓
LinearAdapter.upload_file()
    ↓ (GraphQL: fileUpload mutation)
Linear Storage (returns asset URL)
    ↓
LinearAdapter.attach_file_to_issue() OR attach_file_to_epic()
    ↓ (GraphQL: attachmentCreate mutation)
Attachment created in Linear
    ↓
Return attachment metadata
```

### Graceful Degradation

If Linear-specific methods fail or adapter doesn't support attachments:
- Fallback 1: Try generic `add_attachment()` method
- Fallback 2: Add file reference as comment (always works)

## Adapter Support Matrix

| Adapter | Upload Support | Native Attachments | Fallback Method |
|---------|---------------|-------------------|-----------------|
| Linear | ✅ Full | ✅ Yes | Comment reference |
| GitHub | ❌ Not implemented | ❓ Unknown | Comment reference |
| Jira | ❌ Not implemented | ❓ Unknown | Comment reference |
| Asana | ❌ Not implemented | ❓ Unknown | Comment reference |

## MCP Tool Availability

| Tool | Available via MCP | Available via CLI | Notes |
|------|------------------|-------------------|-------|
| `ticket_attach` | ❌ No | ✅ Yes | Removed in Phase 2 Sprint 1.3 |
| `ticket_attachments` | ❌ No | ✅ Yes | Removed in Phase 2 Sprint 1.3 |

**Reason for Removal:** "Use filesystem MCP for file operations"

## Implementation Requirements

To add full attachment support across all adapters, you would need:

### 1. For Each Adapter

Implement these methods in the adapter class:

```python
async def add_attachment(
    self,
    ticket_id: str,
    file_path: str,
    description: str | None = None,
) -> Attachment:
    """Platform-specific implementation"""

async def get_attachments(self, ticket_id: str) -> list[Attachment]:
    """Fetch attachments from platform"""
```

### 2. For GitHub Adapter

- Use GitHub's attachment API (if available)
- Or use release assets API as workaround
- Or store as commit artifacts in a specific branch

### 3. For Jira Adapter

- Use Jira's attachment REST API endpoints
- Handle authentication and multipart upload

### 4. For Asana Adapter

- Use Asana's attachment API
- Handle file upload to Asana storage

### 5. Re-enable MCP Tools

To expose attachments via MCP again:

1. Uncomment in `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/__init__.py`:
   ```python
   from . import attachment_tools  # noqa: F401
   ```

2. Add to `__all__` list

3. Consider why it was removed (likely token efficiency or filesystem MCP preference)

## Code Examples

### Using Attachment Tools (CLI)

```python
from mcp_ticketer.mcp.server.tools.attachment_tools import (
    ticket_attach,
    ticket_attachments
)

# Attach file
result = await ticket_attach(
    ticket_id="PROJ-123",
    file_path="/path/to/file.pdf",
    description="Design mockup"
)

# List attachments
attachments = await ticket_attachments(ticket_id="PROJ-123")
```

### Using Linear Adapter Directly

```python
from mcp_ticketer.adapters.linear.adapter import LinearAdapter

adapter = LinearAdapter(config={
    "api_key": "lin_api_...",
    "team_key": "ENG"
})

# Upload file to Linear storage
file_url = await adapter.upload_file(
    file_path="/path/to/file.pdf",
    mime_type="application/pdf"
)

# Attach to issue
result = await adapter.attach_file_to_issue(
    issue_id="ISSUE-123",
    file_url=file_url,
    title="Design Mockup",
    subtitle="Updated design for homepage",
    comment_body="See attached mockup for discussion"
)
```

## Recommendations

### Option 1: Use Filesystem MCP (Current Approach)
**Pros:**
- Separates file operations from ticketing
- Allows using specialized filesystem MCP server
- Reduces mcp-ticketer complexity

**Cons:**
- Requires two-step process (upload via filesystem MCP, then reference in ticket)
- No direct attachment metadata in ticket system

### Option 2: Re-enable MCP Attachment Tools
**Pros:**
- One-step file attachment
- Native platform attachment support (Linear)
- Attachment metadata stored in ticket system

**Cons:**
- Increases mcp-ticketer token usage
- Duplicates functionality available in filesystem MCP
- Not all adapters support attachments

### Option 3: Hybrid Approach
**Pros:**
- Allow both methods
- Let user choose based on use case

**Cons:**
- More complex API surface
- Potential confusion about which method to use

## Decision History

**Phase 2 Sprint 1.3:** Attachment tools removed from MCP interface

**Rationale (from code comments):**
> "Use filesystem MCP for file operations"

This suggests the project deliberately moved away from built-in attachment support in favor of delegating file operations to specialized MCP servers.

## Conclusion

**mcp-ticketer has full attachment support infrastructure**, particularly for Linear. However, this functionality is deliberately NOT exposed via MCP tools. Users should use the CLI interface or integrate with filesystem MCP servers for file attachment workflows.

To restore MCP attachment support, the existing `attachment_tools.py` module can be re-enabled by uncommenting the import in `tools/__init__.py`. However, this goes against the architectural decision made in Phase 2 Sprint 1.3.

## References

- **Attachment Model:** `src/mcp_ticketer/core/models.py:389`
- **Base Adapter Interface:** `src/mcp_ticketer/core/adapter.py:554-584`
- **Linear Implementation:** `src/mcp_ticketer/adapters/linear/adapter.py:2756-2952`
- **Attachment Tools:** `src/mcp_ticketer/mcp/server/tools/attachment_tools.py`
- **Tool Registration:** `src/mcp_ticketer/mcp/server/tools/__init__.py`

## Memory Usage

Files analyzed: 5
Search queries: 8
Lines read: ~500 (strategic sampling)
Memory-efficient approach: Used grep and selective file reading

---

**Research Complete**
