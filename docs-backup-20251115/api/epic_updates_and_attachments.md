# Epic Updates and File Attachments API

Complete API documentation for epic update and file attachment capabilities across all mcp-ticketer adapters.

## Table of Contents

- [Overview](#overview)
- [Epic Update Capabilities](#epic-update-capabilities)
- [File Attachment Capabilities](#file-attachment-capabilities)
- [Adapter Comparison Matrix](#adapter-comparison-matrix)
- [MCP Tools](#mcp-tools)
- [Common Patterns and Best Practices](#common-patterns-and-best-practices)
- [Error Handling](#error-handling)
- [Platform-Specific Limitations](#platform-specific-limitations)

## Overview

MCP Ticketer now provides comprehensive epic (project/milestone) update and file attachment capabilities across all supported adapters. Each adapter implements these features according to the capabilities and constraints of the underlying platform.

### Feature Summary

| Feature | Linear | Jira | GitHub | AITrackdown |
|---------|--------|------|--------|-------------|
| Epic Update | ✅ Native | ✅ Native | ✅ Milestones | ✅ File-based |
| Description Update | ✅ Full | ✅ ADF Format | ✅ Full | ✅ Full |
| State Management | ✅ Full | ✅ Workflow | ✅ Open/Closed | ✅ Full |
| Target Date | ✅ Native | ✅ Native | ✅ Due Date | ✅ Metadata |
| File Attachments | ✅ S3 Upload | ✅ Native API | ⚠️ Workaround | ✅ Filesystem |
| Epic Attachments | ✅ Native | ✅ Native | ⚠️ URL Only | ✅ Filesystem |
| Issue Attachments | ✅ Native | ✅ Native | ⚠️ Via Comments | ✅ Filesystem |

**Legend:**
- ✅ **Full Support**: Native platform API with complete functionality
- ⚠️ **Partial/Workaround**: Limited or workaround implementation
- ❌ **Not Supported**: Feature not available

## Epic Update Capabilities

### Universal Interface

All adapters implement a common `update_epic()` method:

```python
async def update_epic(
    self,
    epic_id: str,
    updates: dict[str, Any]
) -> Epic | None:
    """Update an epic with specified fields.

    Args:
        epic_id: Epic identifier (platform-specific format)
        updates: Dictionary of fields to update

    Returns:
        Updated Epic object or None if not found
    """
```

### Supported Update Fields

| Field | Type | Linear | Jira | GitHub | AITrackdown |
|-------|------|--------|------|--------|-------------|
| `title` | `str` | ✅ | ✅ | ✅ | ✅ |
| `description` | `str` | ✅ | ✅ (ADF) | ✅ | ✅ |
| `state` | `str` | ✅ | ✅ | ✅ | ✅ |
| `target_date` | `str` | ✅ | ✅ | ✅ | ✅ |
| `priority` | `str` | ❌ | ✅ | ❌ | ✅ |
| `color` | `str` | ✅ | ❌ | ❌ | ✅ |
| `icon` | `str` | ✅ | ❌ | ❌ | ❌ |

### Linear Adapter

#### Epic Update

```python
from mcp_ticketer.adapters.linear import LinearAdapter

adapter = LinearAdapter(config)

# Update project (epic) details
updated_epic = await adapter.update_epic(
    epic_id="proj_abc123def456",
    updates={
        "title": "Q1 Product Roadmap",
        "description": "Updated roadmap with new priorities",
        "state": "started",  # planned, started, completed, canceled
        "target_date": "2025-03-31",
        "color": "blue",
        "icon": "🚀"
    }
)
```

#### Features
- **Native GraphQL Mutations**: Direct API support via `projectUpdate` mutation
- **Project States**: `planned`, `started`, `completed`, `canceled`
- **Target Dates**: ISO format (YYYY-MM-DD)
- **Visual Customization**: Custom colors and emoji icons
- **Markdown Support**: Full markdown in descriptions

#### Implementation Details
- Uses `projectUpdate` GraphQL mutation
- Resolves project ID from UUID or slug-shortid
- Supports partial updates (only specified fields)
- Returns updated Epic object with all fields

### Jira Adapter

#### Epic Update

```python
from mcp_ticketer.adapters.jira import JiraAdapter

adapter = JiraAdapter(config)

# Update epic with ADF description
updated_epic = await adapter.update_epic(
    epic_id="PROJ-123",
    updates={
        "title": "Customer Portal Redesign",
        "description": "# Overview\n\nComplete redesign of customer portal",
        "state": "in_progress",
        "tags": ["ux", "frontend", "priority:high"],
        "priority": "high"
    }
)
```

#### Features
- **REST API v3**: Native Jira issue update endpoint
- **ADF Conversion**: Automatic Markdown to Atlassian Document Format
- **Workflow Transitions**: State changes via Jira workflows
- **Custom Fields**: Support for epic-specific custom fields
- **Rich Formatting**: Full ADF formatting capabilities

#### Implementation Details
- Uses `/rest/api/3/issue/{issueIdOrKey}` PUT endpoint
- Automatically converts Markdown to ADF for descriptions
- Handles workflow transitions with `doTransition` endpoint
- Supports epic name and color (instance-dependent)
- Returns updated Epic with Jira-specific metadata

### GitHub Adapter

#### Epic Update (Milestones)

```python
from mcp_ticketer.adapters.github import GitHubAdapter

adapter = GitHubAdapter(config)

# Update milestone (epic equivalent)
updated_epic = await adapter.update_epic(
    epic_id="milestone-5",  # or just "5"
    updates={
        "title": "v2.0 Release",
        "description": "Major version release with breaking changes",
        "state": "open",  # open or closed
        "target_date": "2025-06-01"  # due_on in GitHub
    }
)

# Alternative: Direct milestone update
updated_milestone = await adapter.update_milestone(
    milestone_number=5,
    title="v2.0 Release",
    description="Updated description",
    state="open",
    due_on="2025-06-01T00:00:00Z"
)
```

#### Features
- **REST API v4**: GitHub milestones API
- **Binary States**: Only `open` or `closed`
- **Due Dates**: ISO 8601 datetime format
- **Markdown**: Native markdown support
- **Issue Linking**: Automatic issue association

#### Implementation Details
- Uses `/repos/{owner}/{repo}/milestones/{number}` PATCH endpoint
- Maps universal states to open/closed
- Supports both milestone number and epic ID formats
- Returns Epic object with GitHub-specific metadata
- Limited to open/closed state transitions

#### Limitations
- **No Priority**: GitHub milestones don't have priority
- **No Color/Icon**: No visual customization
- **Binary State**: Only open or closed states

### AITrackdown Adapter

#### Epic Update

```python
from mcp_ticketer.adapters.aitrackdown import AITrackdownAdapter

adapter = AITrackdownAdapter(config)

# Update file-based epic
updated_epic = await adapter.update_epic(
    epic_id="epic-20250114",
    updates={
        "title": "Infrastructure Modernization",
        "description": "Complete overhaul of infrastructure",
        "state": "in_progress",
        "target_date": "2025-12-31",
        "priority": "high",
        "tags": ["infrastructure", "devops"]
    }
)
```

#### Features
- **File-Based Storage**: JSON file updates
- **Full Field Support**: All epic fields supported
- **Offline Operation**: No network required
- **Version Control**: Git-friendly JSON files
- **Instant Updates**: No API latency

#### Implementation Details
- Reads epic from `.aitrackdown/tickets/{epic_id}.json`
- Updates specified fields in JSON structure
- Writes updated epic back to file
- Maintains file timestamps and metadata
- Returns updated Epic object

## File Attachment Capabilities

### Multi-Tier Attachment Support

MCP Ticketer implements a three-tier attachment strategy:

#### Tier 1: Native Upload (Best Experience)
- **Linear**: S3 pre-signed URL upload with attachment record
- **Jira**: Direct multipart/form-data API upload
- **AITrackdown**: Local filesystem storage with security

#### Tier 2: Workaround (Limited Functionality)
- **GitHub Issues**: Guidance for manual upload + comment
- **GitHub Milestones**: URL reference in description

#### Tier 3: Fallback (Reference Only)
- Comment with file path reference for unsupported adapters

### Linear Adapter

#### File Upload Process

Linear uses a three-step upload process:

```python
# Step 1: Upload file to Linear's S3 storage
asset_url = await adapter.upload_file(
    file_path="/path/to/document.pdf",
    mime_type="application/pdf"  # Optional, auto-detected
)

# Step 2: Attach to issue
await adapter.attach_file_to_issue(
    issue_id="issue-abc123",
    asset_url=asset_url,
    title="Requirements Document",
    subtitle="Product requirements for Q2"
)

# Step 3: Attach to project/epic
await adapter.attach_file_to_epic(
    project_id="proj-def456",
    asset_url=asset_url,
    title="Project Charter"
)
```

#### Methods

**`upload_file(file_path, mime_type=None)`**
- Requests pre-signed S3 URL via `fileUpload` mutation
- Uploads file to S3 using pre-signed URL
- Returns asset URL for attachment creation

**`attach_file_to_issue(issue_id, asset_url, title, subtitle=None)`**
- Creates attachment record linked to issue
- Uses `attachmentCreate` mutation
- Returns Attachment object

**`attach_file_to_epic(project_id, asset_url, title, subtitle=None)`**
- Creates attachment record linked to project
- Uses `attachmentCreate` mutation with project context
- Returns Attachment object

#### Features
- **Secure Upload**: Pre-signed URLs with expiration
- **S3 Storage**: Linear-managed cloud storage
- **Rich Metadata**: Title, subtitle, and auto-detected properties
- **Authentication**: Requires Linear API authentication to access
- **MIME Detection**: Automatic content-type detection

#### Limitations
- **File Size**: No explicit limit documented (typically ~100MB)
- **Access Control**: Files accessible to all team members
- **No Direct Download**: Must use Linear's download API

### Jira Adapter

#### File Upload Process

```python
# Direct upload to Jira
attachment = await adapter.add_attachment(
    ticket_id="PROJ-123",
    file_path="/path/to/screenshot.png",
    description="UI bug screenshot"
)

# List attachments
attachments = await adapter.get_attachments("PROJ-123")

# Delete attachment
deleted = await adapter.delete_attachment(
    ticket_id="PROJ-123",
    attachment_id="10001"
)
```

#### Methods

**`add_attachment(ticket_id, file_path, description=None)`**
- Direct multipart/form-data upload
- Uses `/rest/api/3/issue/{issueIdOrKey}/attachments` POST
- Requires `X-Atlassian-Token: no-check` header
- Returns Attachment object with Jira metadata

**`get_attachments(ticket_id)`**
- Lists all attachments for issue
- Returns list of Attachment objects
- Includes download URLs and metadata

**`delete_attachment(ticket_id, attachment_id)`**
- Removes attachment by ID
- Uses `/rest/api/3/attachment/{id}` DELETE
- Returns success boolean

#### Features
- **Direct Upload**: Single API call upload
- **Full CRUD**: Create, read, list, delete operations
- **Epic Support**: Works with all issue types including Epics
- **Download URLs**: Direct download links in response
- **Thumbnails**: Automatic thumbnail generation for images

#### Limitations
- **File Size Limit**: Instance-configurable (typically 10-100MB)
- **MIME Types**: All types supported, instance rules may apply
- **Permissions**: Respects Jira project permissions
- **Storage**: Counts against Jira instance storage quota

### GitHub Adapter

#### File Attachment Workarounds

GitHub Issues does not have a native file attachment API. The adapter provides guidance:

```python
# For issues: Manual upload guidance
try:
    attachment = await adapter.add_attachment_to_issue(
        issue_number=123,
        file_path="/path/to/file.pdf",
        comment="Attaching requirements document"
    )
except NotImplementedError as e:
    # Adapter provides instructions:
    # 1. Drag-and-drop file into issue comment
    # 2. GitHub generates markdown link
    # 3. Save comment with file reference
    pass

# For milestones: URL reference
await adapter.add_attachment_reference_to_milestone(
    milestone_number=5,
    url="https://drive.google.com/file/d/...",
    description="Project charter (Google Drive)"
)

# Unified interface with automatic fallback
result = await adapter.add_attachment(
    ticket_id="123",
    file_path="/path/to/file.pdf",
    description="Requirements"
)
# Creates comment with file reference
```

#### Methods

**`add_attachment_to_issue(issue_number, file_path, comment)`**
- Returns NotImplementedError with instructions
- Guidance for manual drag-and-drop upload
- Creates comment with file reference as fallback

**`add_attachment_reference_to_milestone(milestone_number, url, description)`**
- Adds URL reference to milestone description
- Appends attachment section to description
- Returns Epic with updated description

**`add_attachment(ticket_id, file_path, description=None)`**
- Unified interface with automatic fallback
- Creates comment with file path reference
- Returns Attachment-like object with metadata

#### Features
- **Manual Upload Support**: Clear instructions for drag-and-drop
- **URL References**: Link to external file storage
- **Comment Integration**: File references in comments
- **Markdown Links**: Native markdown file links

#### Limitations
- **No Native API**: GitHub Issues lacks attachment API
- **Manual Process**: Requires manual file upload
- **25 MB Limit**: Per-file limit for issue comments
- **No Milestone Attachments**: Milestones can only reference URLs
- **External Storage**: Requires external file hosting

### AITrackdown Adapter

#### File Attachment

```python
# Add attachment
attachment = await adapter.add_attachment(
    ticket_id="epic-20250114",
    file_path="/path/to/document.pdf",
    description="Project requirements"
)

# List attachments
attachments = await adapter.get_attachments("epic-20250114")

# Delete attachment
deleted = await adapter.delete_attachment(
    ticket_id="epic-20250114",
    attachment_id="20250114120000-document.pdf"
)
```

#### Methods

**`add_attachment(ticket_id, file_path, description=None)`**
- Copies file to `.aitrackdown/attachments/{ticket_id}/`
- Sanitizes filename for security
- Generates SHA256 checksum
- Returns Attachment with file:// URL

**`get_attachments(ticket_id)`**
- Lists all files in ticket's attachment directory
- Returns list of Attachment objects
- Includes checksums and metadata

**`delete_attachment(ticket_id, attachment_id)`**
- Removes file from filesystem
- Returns success boolean

#### Features
- **Local Storage**: Files stored in project directory
- **Security**: Filename sanitization, path traversal protection
- **Integrity**: SHA256 checksums for verification
- **Organized**: Per-ticket directory structure
- **Version Control**: Can be committed to Git (with caution)

#### Limitations
- **File Size**: 100 MB default limit (configurable)
- **Local Only**: No cloud storage
- **No Thumbnails**: No automatic preview generation
- **Manual Cleanup**: Files persist until explicitly deleted

## Adapter Comparison Matrix

### Epic Update Features

| Feature | Linear | Jira | GitHub | AITrackdown |
|---------|--------|------|--------|-------------|
| **Native API** | ✅ GraphQL | ✅ REST | ✅ REST | ✅ Filesystem |
| **Title Update** | ✅ | ✅ | ✅ | ✅ |
| **Description Update** | ✅ Markdown | ✅ ADF/Markdown | ✅ Markdown | ✅ Markdown |
| **State Management** | ✅ 4 states | ✅ Workflow | ⚠️ 2 states | ✅ Full |
| **Target Date** | ✅ Date only | ✅ Date+Time | ✅ DateTime | ✅ String |
| **Priority** | ❌ | ✅ | ❌ | ✅ |
| **Visual Customization** | ✅ Color+Icon | ❌ | ❌ | ✅ Metadata |
| **Partial Updates** | ✅ | ✅ | ✅ | ✅ |
| **Validation** | ✅ Schema | ✅ Schema | ✅ Schema | ✅ Pydantic |

### File Attachment Features

| Feature | Linear | Jira | GitHub | AITrackdown |
|---------|--------|------|--------|-------------|
| **Upload Method** | ✅ S3 Pre-signed | ✅ Multipart | ⚠️ Manual | ✅ Filesystem |
| **File Size Limit** | ~100 MB | 10-100 MB | 25 MB | 100 MB |
| **Epic Attachments** | ✅ Native | ✅ Native | ⚠️ URL Ref | ✅ Native |
| **Issue Attachments** | ✅ Native | ✅ Native | ⚠️ Comment | ✅ Native |
| **List Attachments** | ✅ | ✅ | ❌ | ✅ |
| **Delete Attachments** | ✅ | ✅ | ❌ | ✅ |
| **Download URLs** | ✅ Secure | ✅ Public | ✅ GitHub | ✅ file:// |
| **Thumbnails** | ✅ Auto | ✅ Auto | ❌ | ❌ |
| **Checksums** | ❌ | ❌ | ❌ | ✅ SHA256 |
| **Storage** | Cloud (S3) | Cloud (Jira) | GitHub | Local FS |
| **API Complexity** | Medium (3-step) | Low (Direct) | High (Manual) | Trivial |

## MCP Tools

### epic_update Tool

Update an existing epic's metadata and description.

#### Parameters

```json
{
  "epic_id": "epic-123",          // Required: Epic identifier
  "title": "Updated Title",       // Optional: New epic title
  "description": "New desc",      // Optional: New description
  "state": "in_progress",         // Optional: New state
  "target_date": "2025-12-31"     // Optional: Target date (ISO format)
}
```

#### Adapter Support

| Adapter | Support | Notes |
|---------|---------|-------|
| Linear | ✅ Full | Projects API, 4 states, visual customization |
| Jira | ✅ Full | Epic issue type, ADF conversion, workflow |
| GitHub | ✅ Full | Milestones API, open/closed only |
| AITrackdown | ✅ Full | File-based, all fields supported |

#### Response

```json
{
  "id": "epic-123",
  "title": "Updated Title",
  "description": "New description",
  "state": "in_progress",
  "target_date": "2025-12-31",
  "updated_at": "2025-01-14T12:00:00Z",
  "metadata": {
    "adapter": "linear",
    "project_id": "proj-abc123"
  }
}
```

#### Example Usage

```python
# Via MCP client (Claude, Auggie, etc.)
result = await mcp_client.call_tool(
    "epic_update",
    {
        "epic_id": "proj-abc123",
        "description": "Updated project charter with Q2 goals",
        "state": "started",
        "target_date": "2025-06-30"
    }
)
```

### ticket_attach Tool

Attach a file to a ticket (epic, issue, or task) with multi-tier fallback.

#### Parameters

```json
{
  "ticket_id": "PROJ-123",                    // Required: Ticket identifier
  "file_path": "/path/to/document.pdf",      // Required: File path
  "description": "Requirements document"      // Optional: Description
}
```

#### Multi-Tier Strategy

**Tier 1 - Native Upload (Best)**
- **Linear**: Uploads to S3, creates attachment record
- **Jira**: Direct API upload with multipart/form-data
- **AITrackdown**: Filesystem storage with security features

**Tier 2 - Workaround**
- **GitHub Issues**: Creates comment with file reference
- **GitHub Milestones**: Adds URL to description (manual upload required)

**Tier 3 - Fallback**
- Comment with file path reference for any adapter

#### Response Format

```json
{
  "success": true,
  "method": "linear_native_upload",
  "attachment": {
    "id": "att-abc123",
    "filename": "document.pdf",
    "url": "https://linear-assets.s3.amazonaws.com/...",
    "content_type": "application/pdf",
    "size_bytes": 524288,
    "created_at": "2025-01-14T12:00:00Z"
  }
}
```

#### Adapter-Specific Behavior

##### Linear

```json
{
  "method": "linear_native_upload",
  "attachment": {
    "id": "att-abc123",
    "url": "https://linear-assets.s3.amazonaws.com/...",
    "title": "document.pdf"
  }
}
```

- Three-step process: request URL → upload to S3 → create attachment
- Returns asset URL for future reference
- Files stored in Linear's private S3 bucket

##### Jira

```json
{
  "method": "jira_native_upload",
  "attachment": {
    "id": "10001",
    "filename": "document.pdf",
    "self": "https://company.atlassian.net/rest/api/3/attachment/10001",
    "content": "https://company.atlassian.net/secure/attachment/10001/document.pdf"
  }
}
```

- Direct multipart upload to Jira API
- Works for all issue types including Epics
- Requires `X-Atlassian-Token: no-check` header

##### GitHub

```json
{
  "method": "github_comment_reference",
  "message": "File attachment not supported. Created comment with file reference.",
  "comment": {
    "id": 123456,
    "body": "📎 Attachment: document.pdf\nDescription: Requirements document"
  }
}
```

- Issues: Creates comment with file reference
- Milestones: Adds URL to description (requires manual upload)
- Provides guidance for manual drag-and-drop

##### AITrackdown

```json
{
  "method": "aitrackdown_filesystem",
  "attachment": {
    "id": "20250114120000-document.pdf",
    "filename": "document.pdf",
    "url": "file:///project/.aitrackdown/attachments/PROJ-123/document.pdf",
    "size_bytes": 524288,
    "metadata": {
      "checksum": "sha256:abc123..."
    }
  }
}
```

- Stores in `.aitrackdown/attachments/{ticket_id}/`
- Generates SHA256 checksum
- 100 MB file size limit

## Common Patterns and Best Practices

### Epic Update Patterns

#### Progressive Enhancement

```python
# Start with basic epic
epic = await adapter.create_epic(
    title="Q1 Initiative",
    description="Initial planning"
)

# Update as details emerge
await adapter.update_epic(
    epic_id=epic.id,
    updates={
        "description": "# Q1 Initiative\n\n## Goals\n- Goal 1\n- Goal 2",
        "target_date": "2025-03-31"
    }
)

# Update state as work progresses
await adapter.update_epic(
    epic_id=epic.id,
    updates={"state": "in_progress"}
)

# Final update on completion
await adapter.update_epic(
    epic_id=epic.id,
    updates={
        "state": "done",
        "description": "# Q1 Initiative [COMPLETED]\n\n..."
    }
)
```

#### Batch Epic Updates

```python
# Update multiple epics efficiently
epic_updates = [
    {"epic_id": "epic-1", "updates": {"priority": "high"}},
    {"epic_id": "epic-2", "updates": {"priority": "high"}},
    {"epic_id": "epic-3", "updates": {"priority": "medium"}},
]

import asyncio
results = await asyncio.gather(
    *[adapter.update_epic(u["epic_id"], u["updates"]) for u in epic_updates]
)
```

### File Attachment Patterns

#### Attach Documentation to Epic

```python
# Linear
asset_url = await adapter.upload_file("/docs/charter.pdf")
await adapter.attach_file_to_epic(
    project_id="proj-abc123",
    asset_url=asset_url,
    title="Project Charter",
    subtitle="Approved 2025-01-14"
)

# Jira
await adapter.add_attachment(
    ticket_id="PROJ-123",
    file_path="/docs/charter.pdf",
    description="Project Charter"
)

# AITrackdown
await adapter.add_attachment(
    ticket_id="epic-20250114",
    file_path="/docs/charter.pdf",
    description="Project Charter"
)
```

#### Attach Screenshots to Issues

```python
# Capture and attach screenshot
screenshot_path = capture_screenshot()

# Works across all adapters with appropriate fallback
await adapter.add_attachment(
    ticket_id="ISSUE-456",
    file_path=screenshot_path,
    description="Bug reproduction screenshot"
)
```

#### Organize Attachments

```python
# List and categorize attachments
attachments = await adapter.get_attachments("PROJ-123")

documents = [a for a in attachments if a.content_type.startswith("application/")]
images = [a for a in attachments if a.content_type.startswith("image/")]

print(f"Documents: {len(documents)}")
print(f"Images: {len(images)}")
```

### Cross-Adapter Patterns

#### Adapter-Agnostic Epic Updates

```python
def update_epic_safely(adapter, epic_id, **updates):
    """Update epic with error handling."""
    try:
        return await adapter.update_epic(epic_id, updates)
    except NotImplementedError:
        print(f"Epic update not supported by {adapter.name}")
        return None
    except Exception as e:
        print(f"Epic update failed: {e}")
        return None

# Works with any adapter
updated = await update_epic_safely(
    adapter,
    "epic-123",
    description="Updated description",
    state="in_progress"
)
```

#### Attachment with Fallback

```python
async def attach_with_fallback(adapter, ticket_id, file_path, description):
    """Attach file with automatic fallback."""
    try:
        # Try native attachment
        return await adapter.add_attachment(ticket_id, file_path, description)
    except NotImplementedError:
        # Fall back to comment
        comment = f"📎 {file_path}\n{description}"
        return await adapter.add_comment(
            Comment(ticket_id=ticket_id, content=comment)
        )

# Works with all adapters
attachment = await attach_with_fallback(
    adapter,
    "TICKET-123",
    "/path/to/file.pdf",
    "Important document"
)
```

## Error Handling

### Common Error Scenarios

#### Epic Not Found

```python
try:
    epic = await adapter.update_epic("invalid-id", {"title": "New Title"})
except ValueError as e:
    print(f"Epic not found: {e}")
```

#### Invalid State Transition

```python
try:
    epic = await adapter.update_epic(
        "epic-123",
        {"state": "invalid_state"}
    )
except ValueError as e:
    print(f"Invalid state: {e}")
```

#### File Size Exceeded

```python
import os

file_path = "/path/to/large_file.zip"
max_size = 100 * 1024 * 1024  # 100 MB

if os.path.getsize(file_path) > max_size:
    print("File too large. Please compress or split.")
else:
    await adapter.add_attachment("TICKET-123", file_path)
```

#### Permission Denied

```python
try:
    attachment = await adapter.add_attachment(
        "PROJ-123",
        "/protected/file.pdf"
    )
except PermissionError as e:
    print(f"Permission denied: {e}")
```

### Retry Logic

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def update_epic_with_retry(adapter, epic_id, updates):
    """Update epic with automatic retries."""
    return await adapter.update_epic(epic_id, updates)

# Automatically retries on transient failures
epic = await update_epic_with_retry(
    adapter,
    "epic-123",
    {"description": "Updated"}
)
```

## Platform-Specific Limitations

### Linear

#### Epic Updates
- **State Values**: Limited to `planned`, `started`, `completed`, `canceled`
- **Target Date**: Date only, no time component
- **Color/Icon**: Requires emoji or hex color codes

#### Attachments
- **File Size**: No documented limit, typically ~100MB practical limit
- **Access**: Requires Linear API authentication
- **Storage**: Linear-managed S3, cannot self-host

### Jira

#### Epic Updates
- **ADF Conversion**: Complex markdown may lose formatting
- **Workflow Dependency**: States depend on project workflow configuration
- **Custom Fields**: Epic-specific fields vary by instance

#### Attachments
- **File Size**: Instance-configurable (typically 10-100MB)
- **Storage Quota**: Counts against Jira instance storage
- **Permissions**: Respects project-level permissions

### GitHub

#### Epic Updates (Milestones)
- **Binary State**: Only `open` or `closed`, no intermediate states
- **No Priority**: Milestones don't support priority levels
- **No Customization**: No colors, icons, or visual customization

#### Attachments
- **No Native API**: Must use manual drag-and-drop
- **25 MB Limit**: Per-file limit in issue comments
- **Milestone Limitations**: Cannot attach files to milestones directly

### AITrackdown

#### Epic Updates
- **No Validation**: Offline storage, minimal validation
- **File-Based**: Requires filesystem access
- **Manual Sync**: No automatic synchronization

#### Attachments
- **Local Only**: No cloud storage option
- **100 MB Limit**: Default maximum file size
- **No Thumbnails**: No automatic preview generation
- **Git Caution**: Large files can bloat repository

---

## See Also

- [Linear Adapter Documentation](../adapters/linear.md)
- [Jira Adapter Documentation](../adapters/jira.md)
- [GitHub Adapter Documentation](../adapters/github.md)
- [AITrackdown Adapter Documentation](../adapters/aitrackdown.md)
- [File Attachments Guide](../ATTACHMENTS.md)
- [Quick Start Guide](../quickstart/epic_attachments.md)
- [API Reference](../API_REFERENCE.md)

**Last Updated**: 2025-01-14
**Version**: 0.6.5+
