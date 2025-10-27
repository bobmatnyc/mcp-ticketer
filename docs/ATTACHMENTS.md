# Ticket Attachments

mcp-ticketer supports file attachments for tickets. Support varies by adapter.

## Adapter Support Matrix

| Adapter | Add | List | Delete | Storage | Status |
|---------|-----|------|--------|---------|--------|
| **AITrackdown** | ✅ | ✅ | ✅ | Local filesystem | Production |
| **Jira** | ❌ | ❌ | ❌ | Cloud/Server | Planned |
| **Linear** | ❌ | ❌ | ❌ | Cloud | Planned |
| **GitHub** | ❌ | ❌ | ❌ | N/A | Not supported |

**Note**: GitHub Issues does not support file attachments directly. GitHub only supports inline images and links in issue descriptions and comments.

## AITrackdown Attachments

AITrackdown provides full local filesystem-based attachment support with comprehensive security features.

### Features

- **Local Filesystem Storage**: Files stored in `.aitrackdown/attachments/<ticket-id>/` directory
- **Automatic Checksumming**: SHA256 hash for file integrity verification
- **MIME Type Detection**: Automatic content-type detection based on file extension
- **Filename Sanitization**: Removes dangerous characters and prevents path traversal
- **Size Validation**: Maximum file size of 100MB (configurable)
- **Organized Storage**: Each ticket has its own isolated attachment directory
- **Metadata Tracking**: Created timestamp, size, checksum, and description

### Usage

#### Add Attachment

```python
from mcp_ticketer.adapters.aitrackdown import AITrackdownAdapter

# Initialize adapter
adapter = AITrackdownAdapter({'base_path': '.aitrackdown'})

# Add attachment
attachment = await adapter.add_attachment(
    ticket_id='task-20250101123456',
    file_path='/path/to/document.pdf',
    description='Project specification'
)

print(f"Attached: {attachment.filename}")
print(f"Size: {attachment.size_bytes} bytes")
print(f"URL: {attachment.url}")
print(f"Checksum: {attachment.metadata['checksum']}")
```

**Output:**
```
Attached: document.pdf
Size: 1048576 bytes
URL: file:///Users/user/project/.aitrackdown/attachments/task-20250101123456/document.pdf
Checksum: a3c7f8d2...
```

#### List Attachments

```python
# Get all attachments for a ticket
attachments = await adapter.get_attachments('task-20250101123456')

for att in attachments:
    print(f"{att.filename} - {att.size_bytes} bytes")
    print(f"  Created: {att.created_at}")
    print(f"  URL: {att.url}")
    print(f"  Type: {att.content_type}")
    if att.description:
        print(f"  Description: {att.description}")
```

**Output:**
```
document.pdf - 1048576 bytes
  Created: 2025-01-27 14:30:00
  URL: file:///Users/user/project/.aitrackdown/attachments/task-20250101123456/document.pdf
  Type: application/pdf
  Description: Project specification

screenshot.png - 245678 bytes
  Created: 2025-01-27 15:45:00
  URL: file:///Users/user/project/.aitrackdown/attachments/task-20250101123456/screenshot.png
  Type: image/png
```

#### Delete Attachment

```python
# Delete by attachment ID
deleted = await adapter.delete_attachment(
    ticket_id='task-20250101123456',
    attachment_id='20250101123456-document.pdf'
)

if deleted:
    print("Attachment deleted successfully")
else:
    print("Attachment not found or deletion failed")
```

### Security Features

AITrackdown implements several security measures to protect against common file upload vulnerabilities:

#### 1. Filename Sanitization
- Removes dangerous characters: `..`, `/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|`
- Prevents directory traversal attacks
- Preserves file extension for MIME type detection
- Maximum filename length: 255 characters

```python
# Example sanitization
"../../../etc/passwd" → "etc_passwd"
"file:name?.txt" → "filename.txt"
"document (1).pdf" → "document_1.pdf"
```

#### 2. Path Resolution
- All file paths resolved to absolute paths
- Prevents symbolic link attacks
- Validates files stay within attachment directory
- Rejects paths outside the ticket's attachment folder

#### 3. Size Limits
- Default maximum: 100MB per file
- Configurable via adapter settings
- Prevents disk space exhaustion
- Returns clear error message on size violations

```python
# Configure custom size limit (50MB)
adapter = AITrackdownAdapter({
    'base_path': '.aitrackdown',
    'max_attachment_size': 50 * 1024 * 1024  # 50MB in bytes
})
```

#### 4. Checksum Verification
- SHA256 checksums calculated on upload
- Stored in attachment metadata
- Can be used to verify file integrity
- Detects file corruption or tampering

```python
# Verify checksum
import hashlib

def verify_attachment(file_path: str, expected_checksum: str) -> bool:
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest() == expected_checksum
```

#### 5. Isolated Storage
- Each ticket has its own attachment directory
- Directory structure: `.aitrackdown/attachments/<ticket-id>/`
- Prevents cross-ticket file access
- Simplifies cleanup when tickets are deleted

### MCP Tools

Attachments are accessible via MCP tools with automatic fallback for unsupported adapters.

#### `ticket_attach` - Add Attachment

Add a file attachment to a ticket.

**Parameters:**
```json
{
  "ticket_id": "task-123",
  "file_path": "/path/to/file.pdf",
  "description": "Optional description"
}
```

**Response:**
```json
{
  "id": "20250101123456-file.pdf",
  "ticket_id": "task-123",
  "filename": "file.pdf",
  "url": "file:///project/.aitrackdown/attachments/task-123/file.pdf",
  "content_type": "application/pdf",
  "size_bytes": 1048576,
  "created_at": "2025-01-27T14:30:00Z",
  "description": "Optional description",
  "metadata": {
    "checksum": "a3c7f8d2..."
  }
}
```

**Fallback Behavior**: If the adapter doesn't support attachments (Jira, Linear, GitHub), the tool automatically falls back to creating a comment with a file reference:

```
Comment added to ticket task-123:
📎 Attachment reference: /path/to/file.pdf
Description: Optional description
```

#### `ticket_attachments` - List Attachments

List all attachments for a ticket.

**Parameters:**
```json
{
  "ticket_id": "task-123"
}
```

**Response:**
```json
[
  {
    "id": "20250101123456-file1.pdf",
    "filename": "file1.pdf",
    "size_bytes": 1048576,
    "content_type": "application/pdf",
    "url": "file:///.../file1.pdf",
    "created_at": "2025-01-27T14:30:00Z"
  },
  {
    "id": "20250101143000-image.png",
    "filename": "image.png",
    "size_bytes": 245678,
    "content_type": "image/png",
    "url": "file:///.../image.png",
    "created_at": "2025-01-27T15:45:00Z"
  }
]
```

**Fallback Behavior**: Returns empty array `[]` if adapter doesn't support attachments.

#### `ticket_delete_attachment` - Delete Attachment

Delete a specific attachment from a ticket.

**Parameters:**
```json
{
  "ticket_id": "task-123",
  "attachment_id": "20250101123456-file.pdf"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Attachment deleted successfully"
}
```

**Fallback Behavior**: Returns error message if adapter doesn't support attachments.

### CLI Usage

Currently, attachment operations are primarily available through MCP tools. CLI support is planned for future releases.

```bash
# Add attachment (via MCP call)
mcp-ticketer mcp call ticket_attach '{
  "ticket_id": "task-123",
  "file_path": "/path/to/file.pdf",
  "description": "Project specification"
}'

# List attachments (via MCP call)
mcp-ticketer mcp call ticket_attachments '{
  "ticket_id": "task-123"
}'

# Delete attachment (via MCP call)
mcp-ticketer mcp call ticket_delete_attachment '{
  "ticket_id": "task-123",
  "attachment_id": "20250101123456-file.pdf"
}'
```

### File Organization

AITrackdown organizes attachments in a clear directory structure:

```
.aitrackdown/
├── attachments/
│   ├── task-20250101123456/
│   │   ├── document.pdf
│   │   ├── screenshot.png
│   │   └── spec.docx
│   ├── task-20250102143000/
│   │   ├── design.fig
│   │   └── mockup.png
│   └── epic-20250103100000/
│       └── roadmap.xlsx
└── tickets/
    ├── task-20250101123456.json
    ├── task-20250102143000.json
    └── epic-20250103100000.json
```

**Benefits:**
- Easy to find attachments for a specific ticket
- Simple to backup or archive with version control
- Attachments are automatically cleaned up if ticket directory is removed
- File paths are predictable and consistent

### Best Practices

#### 1. Use Descriptive Filenames
```python
# Good
await adapter.add_attachment(
    ticket_id='task-123',
    file_path='/downloads/user-flow-diagram-v2.png',
    description='Updated user flow after sprint review'
)

# Less useful
await adapter.add_attachment(
    ticket_id='task-123',
    file_path='/downloads/image.png',
    description='Diagram'
)
```

#### 2. Add Descriptions
Descriptions help team members understand the attachment's purpose without downloading it.

```python
await adapter.add_attachment(
    ticket_id='task-123',
    file_path='/docs/api-spec.pdf',
    description='REST API specification v3.2 - approved by architecture team'
)
```

#### 3. Check Size Before Upload
```python
import os

file_path = '/large/file.zip'
max_size = 100 * 1024 * 1024  # 100MB

if os.path.getsize(file_path) > max_size:
    print(f"File too large. Please compress or split the file.")
else:
    await adapter.add_attachment(ticket_id='task-123', file_path=file_path)
```

#### 4. Verify Important Attachments
```python
# Store checksum for critical files
attachment = await adapter.add_attachment(
    ticket_id='task-123',
    file_path='/contracts/signed-agreement.pdf',
    description='Signed vendor agreement - DO NOT MODIFY'
)

# Save checksum for later verification
checksum = attachment.metadata['checksum']
print(f"Agreement checksum: {checksum}")
```

#### 5. Clean Up Old Attachments
```python
# List attachments to find outdated ones
attachments = await adapter.get_attachments('task-123')

# Delete old drafts
for att in attachments:
    if 'draft' in att.filename.lower() and is_old(att.created_at):
        await adapter.delete_attachment('task-123', att.id)
        print(f"Deleted old draft: {att.filename}")
```

## Coming Soon

### Jira Attachments

Planned features for Jira adapter:
- REST API v3 integration with multipart upload
- Support for both Cloud and Server deployments
- Attachment download and metadata retrieval
- Integration with Jira's attachment permissions

```python
# Planned API (not yet implemented)
adapter = JiraAdapter(config)
attachment = await adapter.add_attachment(
    ticket_id='PROJ-123',
    file_path='/path/to/file.pdf',
    description='Requirements document'
)
```

### Linear Attachments

Planned features for Linear adapter:
- GraphQL mutation for file uploads
- Base64-encoded file transfer
- Integration with Linear's attachment system
- Support for images and documents

```python
# Planned API (not yet implemented)
adapter = LinearAdapter(config)
attachment = await adapter.add_attachment(
    ticket_id='LIN-456',
    file_path='/path/to/image.png',
    description='UI mockup'
)
```

### Future Enhancements

#### Attachment Thumbnails
- Automatic thumbnail generation for images
- Preview thumbnails in CLI and MCP tools
- Configurable thumbnail sizes

#### Compression Support
- Automatic compression for large files
- Configurable compression thresholds
- Multiple compression formats (gzip, brotli)

#### Bulk Operations
- Upload multiple attachments at once
- Bulk delete by pattern or date
- Export all attachments for a ticket

#### Version Control
- Track attachment versions
- Restore previous versions
- Compare versions with diff

#### Advanced Search
- Search attachments by content type
- Find attachments by size or date
- Full-text search in document content

## Error Handling

### Common Errors

#### File Not Found
```python
try:
    await adapter.add_attachment(
        ticket_id='task-123',
        file_path='/nonexistent/file.pdf'
    )
except FileNotFoundError as e:
    print(f"Error: File not found - {e}")
```

#### Size Limit Exceeded
```python
try:
    await adapter.add_attachment(
        ticket_id='task-123',
        file_path='/huge/file.zip'
    )
except ValueError as e:
    if 'size' in str(e).lower():
        print(f"Error: File too large - {e}")
```

#### Invalid Ticket ID
```python
try:
    await adapter.add_attachment(
        ticket_id='invalid-ticket',
        file_path='/file.pdf'
    )
except ValueError as e:
    print(f"Error: Invalid ticket ID - {e}")
```

#### Permission Denied
```python
try:
    await adapter.add_attachment(
        ticket_id='task-123',
        file_path='/protected/file.pdf'
    )
except PermissionError as e:
    print(f"Error: Permission denied - {e}")
```

## API Reference

See [API_REFERENCE.md](API_REFERENCE.md#attachment-model) for the complete Attachment model specification.

### Attachment Model Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `str` | No | Unique attachment identifier |
| `ticket_id` | `str` | Yes | Parent ticket ID |
| `filename` | `str` | Yes | Original filename |
| `url` | `str` | No | Download URL or file:// path |
| `content_type` | `str` | No | MIME type (e.g., 'application/pdf') |
| `size_bytes` | `int` | No | File size in bytes |
| `created_at` | `datetime` | No | Upload timestamp |
| `created_by` | `str` | No | User who uploaded |
| `description` | `str` | No | Attachment description |
| `metadata` | `dict` | No | Adapter-specific metadata |

### BaseAdapter Methods

All adapters inherit these attachment methods (may return NotImplementedError):

```python
async def add_attachment(
    self,
    ticket_id: str,
    file_path: str,
    description: Optional[str] = None
) -> Attachment:
    """Add a file attachment to a ticket."""

async def get_attachments(
    self,
    ticket_id: str
) -> List[Attachment]:
    """Get all attachments for a ticket."""

async def delete_attachment(
    self,
    ticket_id: str,
    attachment_id: str
) -> bool:
    """Delete a specific attachment."""
```

## Support and Feedback

Having issues with attachments? Please:

1. Check this documentation for common solutions
2. Review the [API Reference](API_REFERENCE.md) for detailed specifications
3. Search existing [GitHub Issues](https://github.com/mcp-ticketer/mcp-ticketer/issues)
4. Create a new issue with reproduction steps

For feature requests related to attachments, please open an issue with:
- Use case description
- Desired adapter (Jira, Linear, etc.)
- Expected behavior
- Any relevant examples or mockups

---

**Last Updated**: 2025-01-27
**Version**: 0.4.1+
