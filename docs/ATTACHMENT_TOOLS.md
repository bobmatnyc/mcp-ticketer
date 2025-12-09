# Attachment Tools - MCP Interface

**Status:** ✅ Re-enabled as of 2025-12-09

## Overview

File attachment functionality is now available via MCP tools. The attachment infrastructure was previously removed from the MCP interface in Phase 2 Sprint 1.3 with a recommendation to use filesystem MCP instead. However, this has been re-enabled based on user request.

## Available Tools

### 1. `ticket_attach` - Attach a file to a ticket

Uploads a file and associates it with the specified ticket.

**Parameters:**
- `ticket_id` (str, required): Unique identifier of the ticket
- `file_path` (str, required): Absolute path to the file to attach
- `description` (str, optional): Optional description of the attachment

**Returns:**
```json
{
  "status": "completed",
  "ticket_id": "PROJ-123",
  "method": "linear_native_upload",
  "file_url": "https://linear.app/files/abc123...",
  "attachment": {
    "id": "attach-456",
    "title": "Design Mockup",
    "url": "https://linear.app/files/abc123..."
  }
}
```

**Example Usage:**
```python
result = await ticket_attach(
    ticket_id="PROJ-123",
    file_path="/Users/username/Documents/design.pdf",
    description="Updated design mockup for review"
)
```

**Implementation Strategy (Graceful Degradation):**
1. **Linear Native Upload** (Best): Uses Linear's native file upload and attachment APIs
   - Uploads file to Linear storage via `upload_file()`
   - Creates attachment record via `attach_file_to_issue()` or `attach_file_to_epic()`
   - Returns full attachment metadata with URL
2. **Legacy Adapter Method**: Falls back to adapter's `add_attachment()` method
3. **Comment Reference** (Fallback): Adds file path as comment if adapter doesn't support attachments

### 2. `ticket_attachments` - List attachments for a ticket

Retrieves all files attached to the specified ticket.

**Parameters:**
- `ticket_id` (str, required): Unique identifier of the ticket

**Returns:**
```json
{
  "status": "completed",
  "ticket_id": "PROJ-123",
  "attachments": [
    {
      "id": "attach-456",
      "filename": "design.pdf",
      "url": "https://linear.app/files/abc123...",
      "content_type": "application/pdf",
      "size_bytes": 245760,
      "created_at": "2025-12-09T10:30:00Z",
      "created_by": "user@example.com"
    }
  ],
  "count": 1
}
```

**Example Usage:**
```python
result = await ticket_attachments(ticket_id="PROJ-123")
for attachment in result["attachments"]:
    print(f"File: {attachment['filename']}, URL: {attachment['url']}")
```

## Adapter Support

| Adapter | Upload Support | Native Attachments | Fallback Method |
|---------|---------------|-------------------|-----------------|
| **Linear** | ✅ Full (via GraphQL) | ✅ Yes | Comment reference |
| **GitHub** | ❌ Not implemented | ❓ Possible via API | Comment reference |
| **Jira** | ❌ Not implemented | ❓ Possible via API | Comment reference |
| **Asana** | ❌ Not implemented | ❓ Possible via API | Comment reference |

### Linear Adapter Implementation

The Linear adapter has comprehensive attachment support:

1. **File Upload:** `upload_file(file_path, mime_type)`
   - Uses GraphQL `fileUpload` mutation
   - Uploads to Linear's managed storage
   - Returns asset URL

2. **Issue Attachment:** `attach_file_to_issue(issue_id, file_url, title, subtitle, comment_body)`
   - Uses GraphQL `attachmentCreate` mutation
   - Attaches uploaded file or external URL to issue
   - Optionally adds comment

3. **Epic Attachment:** `attach_file_to_epic(epic_id, file_url, title, subtitle)`
   - Uses GraphQL `attachmentCreate` mutation
   - Attaches to Linear project (epic)

## Important Considerations

### File Paths
- **MCP tools require absolute file paths** (e.g., `/Users/username/Documents/file.pdf`)
- The MCP server must have read access to the file location
- Relative paths may not work correctly

### File Access
- The file must exist and be readable at the specified path
- The MCP server runs in its own process and needs filesystem access
- If using Claude Desktop/Code, the MCP server has access to your local filesystem

### Security
- Be cautious about which files you attach to tickets
- File content is uploaded to the ticket platform (Linear, Jira, etc.)
- Consider data sensitivity and compliance requirements

### Token Usage
- Attachment tools add ~800 tokens to the MCP interface
- File uploads are handled server-side (not in token context)
- Attachment metadata is returned in responses

## Architecture

### Attachment Flow (Linear)

```
User Request via MCP
    ↓
ticket_attach(ticket_id, file_path, description)
    ↓
1. Validate ticket exists (adapter.read())
2. Check file exists at path
3. Determine MIME type
    ↓
LinearAdapter.upload_file(file_path, mime_type)
    ↓ GraphQL: fileUpload mutation
Linear Storage (returns asset URL)
    ↓
Determine ticket type (epic vs issue)
    ↓
LinearAdapter.attach_file_to_issue()
    OR
LinearAdapter.attach_file_to_epic()
    ↓ GraphQL: attachmentCreate mutation
Attachment created in Linear
    ↓
Return: {status, method, file_url, attachment}
```

### Graceful Degradation

If the primary attachment method fails:
1. Try adapter's generic `add_attachment()` method
2. If that fails, add file reference as a comment
3. Return appropriate error or fallback status

## Error Handling

### Common Errors

**File Not Found:**
```json
{
  "status": "error",
  "error": "File not found: /path/to/file.pdf",
  "ticket_id": "PROJ-123"
}
```

**Ticket Not Found:**
```json
{
  "status": "error",
  "error": "Ticket PROJ-123 not found"
}
```

**Adapter Not Supported:**
```json
{
  "status": "completed",
  "ticket_id": "PROJ-123",
  "method": "comment_reference",
  "file_path": "/path/to/file.pdf",
  "comment": {...},
  "note": "Adapter does not support direct file uploads. File reference added as comment."
}
```

**Upload Failed:**
```json
{
  "status": "error",
  "error": "Failed to attach file: [specific error message]",
  "ticket_id": "PROJ-123"
}
```

## Comparison: MCP Attachments vs Filesystem MCP

### Using MCP Attachment Tools (Current)

**Pros:**
- ✅ One-step attachment process
- ✅ Native platform integration (Linear)
- ✅ Attachment metadata stored in ticket system
- ✅ No need for separate filesystem MCP server

**Cons:**
- ❌ Not all adapters support attachments
- ❌ File must be accessible to MCP server
- ❌ Slightly higher token usage

### Using Filesystem MCP (Previous Approach)

**Pros:**
- ✅ Separates file operations from ticketing
- ✅ Works with any file storage system
- ✅ More flexible file management

**Cons:**
- ❌ Two-step process (upload via filesystem MCP, then reference)
- ❌ No native attachment metadata
- ❌ Requires additional MCP server

## Migration Guide

If you were using filesystem MCP for attachments, you can now use the built-in tools:

**Before (Filesystem MCP + Comment):**
```python
# 1. Upload file via filesystem MCP
file_url = await filesystem_upload("/path/to/file.pdf")

# 2. Reference in ticket comment
await ticket_comment(
    ticket_id="PROJ-123",
    operation="add",
    text=f"Attached file: {file_url}"
)
```

**After (Built-in Attachment):**
```python
# Single step with native attachment
result = await ticket_attach(
    ticket_id="PROJ-123",
    file_path="/path/to/file.pdf",
    description="Design mockup"
)
```

## Future Enhancements

Potential improvements for attachment support:

1. **GitHub Adapter:** Implement attachment via GitHub's release assets or gists
2. **Jira Adapter:** Implement attachment via Jira REST API
3. **Asana Adapter:** Implement attachment via Asana file upload API
4. **Base64 Support:** Accept file content as base64 for remote MCP scenarios
5. **URL Support:** Accept external URLs for linking instead of uploading
6. **Batch Upload:** Support multiple files in single operation

## References

- **Attachment Model:** `src/mcp_ticketer/core/models.py` (Attachment class)
- **Base Adapter Interface:** `src/mcp_ticketer/core/adapter.py` (add_attachment, get_attachments)
- **Linear Implementation:** `src/mcp_ticketer/adapters/linear/adapter.py` (upload_file, attach_file_to_issue, attach_file_to_epic)
- **MCP Tools:** `src/mcp_ticketer/mcp/server/tools/attachment_tools.py`
- **Research Document:** `docs/research/attachment-support-investigation-2025-12-09.md`

## Change History

- **Phase 2 Sprint 1.3 (2024):** Attachment tools removed from MCP interface
  - Rationale: "Use filesystem MCP for file operations"
  - Tools moved to CLI-only

- **2025-12-09:** Attachment tools re-enabled in MCP interface
  - Added `@mcp.tool()` decorators to `ticket_attach` and `ticket_attachments`
  - Re-enabled imports in `tools/__init__.py`
  - Rationale: User request for simplified attachment workflow

---

**Last Updated:** 2025-12-09
**Status:** ✅ Active and supported
