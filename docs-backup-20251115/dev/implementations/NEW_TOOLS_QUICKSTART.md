# New MCP Tools Quick Start Guide

## Quick Reference

### Epic Update Tool

**Tool Name**: `epic_update`

**Purpose**: Update epic metadata and descriptions (Linear adapter)

**Basic Usage**:
```python
# Via MCP client
{
  "tool": "epic_update",
  "arguments": {
    "epic_id": "PRJ-123",
    "title": "Updated Title",
    "description": "New description",
    "state": "in_progress",
    "target_date": "2025-12-31"
  }
}
```

**Response**:
```json
{
  "status": "completed",
  "epic": {
    "id": "PRJ-123",
    "title": "Updated Title",
    // ... full epic object
  }
}
```

### Enhanced File Attachment Tool

**Tool Name**: `ticket_attach`

**Purpose**: Attach files to tickets with native Linear upload support

**Basic Usage**:
```python
# Via MCP client
{
  "tool": "ticket_attach",
  "arguments": {
    "ticket_id": "ISS-456",
    "file_path": "/path/to/file.pdf",
    "description": "Design specs"
  }
}
```

**Response (Linear Native)**:
```json
{
  "status": "completed",
  "ticket_id": "ISS-456",
  "method": "linear_native_upload",
  "file_url": "https://linear-uploads.s3.amazonaws.com/...",
  "attachment": {
    // Attachment details
  }
}
```

## Implementation Details

### File Locations
- Epic update: `src/mcp_ticketer/mcp/server/tools/hierarchy_tools.py`
- File attachment: `src/mcp_ticketer/mcp/server/tools/attachment_tools.py`

### Key Features

#### Epic Update
- ✅ Optional field updates (only specify fields to change)
- ✅ ISO date format validation
- ✅ Adapter capability detection
- ✅ Graceful error messages

#### File Attachment
- ✅ Multi-tier fallback (Linear S3 → Legacy → Comment)
- ✅ Automatic MIME type detection
- ✅ Ticket type awareness (Epic vs Issue/Task)
- ✅ File existence validation
- ✅ S3 upload for Linear adapter

## Testing

### Quick Test
```bash
# Verify tools are registered
uv run python -c "
from src.mcp_ticketer.mcp.server.tools.hierarchy_tools import epic_update
from src.mcp_ticketer.mcp.server.tools.attachment_tools import ticket_attach
print('✅ Tools imported successfully')
"
```

### Unit Tests
```bash
# Run all unit tests
uv run pytest tests/unit/ -v

# Run specific tool tests (when available)
uv run pytest tests/unit/test_tools.py -v -k "epic_update or ticket_attach"
```

## Error Handling

### Epic Update Errors

**Adapter not supported**:
```json
{
  "status": "error",
  "error": "Epic updates not supported by GithubAdapter adapter",
  "note": "Use ticket_update instead for basic field updates"
}
```

**No updates provided**:
```json
{
  "status": "error",
  "error": "No updates provided. At least one field must be specified."
}
```

**Invalid date format**:
```json
{
  "status": "error",
  "error": "Invalid date format '2025-13-01'. Use ISO format: YYYY-MM-DD"
}
```

### File Attachment Errors

**File not found**:
```json
{
  "status": "error",
  "error": "File not found: /path/to/missing.pdf",
  "ticket_id": "ISS-456"
}
```

**Ticket not found**:
```json
{
  "status": "error",
  "error": "Ticket ISS-456 not found"
}
```

## Common Patterns

### Update Only Description
```json
{
  "epic_id": "PRJ-123",
  "description": "Updated description text"
}
```

### Update State and Date
```json
{
  "epic_id": "PRJ-123",
  "state": "completed",
  "target_date": "2025-11-14"
}
```

### Attach Multiple Files
```python
# Attach files sequentially
for file_path in ["/doc1.pdf", "/doc2.png", "/doc3.txt"]:
    result = await client.call_tool("ticket_attach", {
        "ticket_id": "ISS-456",
        "file_path": file_path,
        "description": f"Attachment: {Path(file_path).name}"
    })
```

### Check Attachment Method Used
```python
result = await client.call_tool("ticket_attach", {...})
method = result.get("method")

if method == "linear_native_upload":
    print(f"File uploaded to: {result['file_url']}")
elif method == "adapter_native":
    print("Used adapter's native attachment method")
elif method == "comment_reference":
    print("File reference added as comment")
```

## Integration Examples

### Claude Desktop Integration

Add to your Claude Desktop MCP settings:
```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "uv",
      "args": ["run", "mcp-ticketer", "mcp"],
      "cwd": "/path/to/mcp-ticketer"
    }
  }
}
```

### Usage in Claude
```
User: "Update epic PRJ-123 to mark it as in_progress"

Claude: *uses epic_update tool*
{
  "epic_id": "PRJ-123",
  "state": "in_progress"
}

Result: ✅ Epic updated successfully
```

## Troubleshooting

### Tool Not Found
**Symptom**: "Unknown tool: epic_update"
**Solution**: Ensure mcp-ticketer is properly installed and tools are imported

### Adapter Not Supported
**Symptom**: "Epic updates not supported by X adapter"
**Solution**: Use `ticket_update` for basic field updates, or switch to Linear adapter

### File Upload Fails
**Symptom**: File upload fails silently
**Solution**: Check response `method` field - if it's "comment_reference", file upload failed but fallback succeeded

### Invalid Date Format
**Symptom**: "Invalid date format"
**Solution**: Use ISO format: YYYY-MM-DD (e.g., "2025-12-31")

## See Also

- [MCP_TOOLS_IMPLEMENTATION_SUMMARY.md](./MCP_TOOLS_IMPLEMENTATION_SUMMARY.md) - Full implementation details
- [Linear Adapter Documentation](./docs/adapters/linear.md) - Linear-specific features
- [MCP Server Documentation](./docs/mcp-server.md) - MCP server configuration
