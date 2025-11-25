# Ticket Attachment Implementation Analysis for 1M-157

**Research Date**: 2025-11-24
**Ticket**: 1M-157
**Researcher**: Research Agent
**Context**: Implementing file attachment functionality across all adapters

---

## Executive Summary

This research provides a comprehensive analysis of the ticket_attach() implementation requirements across all five adapters (Linear, GitHub, JIRA, Asana, AiTrackDown). The investigation reveals that **all adapters already have attachment functionality implemented**, but with varying levels of maturity and API capabilities.

### Key Findings

1. **BaseAdapter Interface**: Defines three attachment methods with proper error handling
2. **Implementation Status**: All 5 adapters have `add_attachment()` and `get_attachments()` implemented
3. **MCP Tool**: Multi-tier attachment strategy already implemented with fallback mechanisms
4. **Test Coverage**: Good coverage for Linear, JIRA, GitHub; **gaps exist for Asana and AiTrackDown**
5. **API Capabilities**: Vary significantly by platform

### Implementation Priority Matrix

| Adapter | Status | API Support | Test Coverage | Priority |
|---------|--------|-------------|---------------|----------|
| **Linear** | ✅ Complete | Native S3 upload + attachment records | Excellent (13+ tests) | Low (maintenance) |
| **JIRA** | ✅ Complete | Native multipart upload | Good (multiple test suites) | Low (maintenance) |
| **GitHub** | ✅ Complete | Comment reference workaround | Good (20+ tests) | Low (maintenance) |
| **Asana** | ✅ Complete | Native multipart upload | **Missing** | **High (add tests)** |
| **AiTrackDown** | ✅ Complete | Local filesystem storage | Partial (security tests only) | **High (add tests)** |

---

## 1. BaseAdapter Interface Analysis

### Location
`/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/core/adapter.py`

### Method Signatures

#### 1.1 `add_attachment()` Method

```python
async def add_attachment(
    self,
    ticket_id: str,
    file_path: str,
    description: str | None = None,
) -> Attachment:
    """Attach a file to a ticket.

    Args:
    ----
        ticket_id: Ticket identifier
        file_path: Local file path to upload
        description: Optional attachment description

    Returns:
    -------
        Created Attachment with metadata

    Raises:
    ------
        NotImplementedError: If adapter doesn't support attachments
        FileNotFoundError: If file doesn't exist
        ValueError: If ticket doesn't exist or upload fails

    """
    raise NotImplementedError(
        f"{self.__class__.__name__} does not support file attachments. "
        "Use comments to reference external files instead."
    )
```

**Key Points:**
- Default implementation raises `NotImplementedError`
- Requires all adapters to explicitly opt-in by overriding
- Returns standardized `Attachment` model
- Comprehensive error handling contract

#### 1.2 `get_attachments()` Method

```python
async def get_attachments(self, ticket_id: str) -> list[Attachment]:
    """Get all attachments for a ticket.

    Args:
    ----
        ticket_id: Ticket identifier

    Returns:
    -------
        List of attachments (empty if none or not supported)

    """
    raise NotImplementedError(
        f"{self.__class__.__name__} does not support file attachments."
    )
```

**Key Points:**
- Returns empty list if not supported
- Standardized across all adapters
- No pagination (retrieves all attachments)

#### 1.3 `delete_attachment()` Method (Optional)

```python
async def delete_attachment(
    self,
    ticket_id: str,
    attachment_id: str,
) -> bool:
    """Delete an attachment (optional implementation).

    Args:
    ----
        ticket_id: Ticket identifier
        attachment_id: Attachment identifier

    Returns:
    -------
        True if deleted, False otherwise

    Raises:
    ------
        NotImplementedError: If adapter doesn't support deletion

    """
    raise NotImplementedError(
        f"{self.__class__.__name__} does not support attachment deletion."
    )
```

**Key Points:**
- Optional method (not required for all adapters)
- Currently **NOT implemented by any adapter**
- Future enhancement opportunity

---

## 2. Attachment Model

### Location
`/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/core/models.py` (lines 389-417)

### Model Structure

```python
class Attachment(BaseModel):
    """File attachment metadata for tickets."""

    model_config = ConfigDict(use_enum_values=True)

    id: str | None = Field(None, description="Attachment unique identifier")
    ticket_id: str = Field(..., description="Parent ticket identifier")
    filename: str = Field(..., description="Original filename")
    url: str | None = Field(None, description="Download URL or file path")
    content_type: str | None = Field(
        None, description="MIME type (e.g., 'application/pdf', 'image/png')"
    )
    size_bytes: int | None = Field(None, description="File size in bytes")
    created_at: datetime | None = Field(None, description="Upload timestamp")
    created_by: str | None = Field(None, description="User who uploaded the attachment")
    description: str | None = Field(None, description="Attachment description or notes")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Adapter-specific attachment metadata"
    )
```

**Key Points:**
- Universal model used across all adapters
- Required fields: `ticket_id`, `filename`
- Optional fields allow for adapter-specific capabilities
- `metadata` field for platform-specific extensions

---

## 3. MCP Tool Implementation

### Location
`/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/attachment_tools.py`

### Three-Tier Attachment Strategy

The MCP tool implements a sophisticated multi-tier fallback strategy:

#### Tier 1: Linear Native Upload (Most Advanced)
```python
if hasattr(adapter, "upload_file") and hasattr(adapter, "attach_file_to_issue"):
    # 1. Upload file to Linear's S3 storage
    file_url = await adapter.upload_file(file_path, mime_type)

    # 2. Create attachment record
    if ticket_type == TicketType.EPIC:
        result = await adapter.attach_file_to_epic(...)
    else:
        result = await adapter.attach_file_to_issue(...)
```

**Supports:**
- Linear adapter only
- Direct S3 upload with pre-signed URLs
- Separate methods for epics vs. issues
- Comment body integration

#### Tier 2: Adapter Native Method
```python
if hasattr(adapter, "add_attachment"):
    attachment = await adapter.add_attachment(
        ticket_id=ticket_id,
        file_path=file_path,
        description=description
    )
```

**Supports:**
- JIRA: Multipart upload to `/issue/{key}/attachments`
- Asana: Multipart upload to `/tasks/{gid}/attachments`
- AiTrackDown: Local filesystem copy
- GitHub: Comment reference creation

#### Tier 3: Comment Reference Fallback
```python
# Create comment with file reference
comment_text = f"Attachment: {file_path}"
if description:
    comment_text += f"\nDescription: {description}"

comment = Comment(ticket_id=ticket_id, content=comment_text)
created_comment = await adapter.add_comment(comment)
```

**Supports:**
- Any adapter with comment support
- Last resort fallback
- User notification about limitation

### Tool Response Format

```python
{
    "status": "completed" | "error",
    "ticket_id": str,
    "method": "linear_native_upload" | "adapter_native" | "comment_reference",
    "attachment": dict | None,  # Attachment metadata
    "file_url": str | None,     # Linear S3 URL
    "comment": dict | None,     # Comment reference
    "note": str | None,         # User notification
    "error": str | None         # Error message
}
```

---

## 4. Adapter-Specific Implementation Details

### 4.1 Linear Adapter ✅

**Status**: Fully implemented, most advanced

**Implementation Files:**
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/adapter.py`
- Lines 2162-2310 (attachment methods)

**Methods:**
1. `upload_file(file_path, mime_type)` → Returns S3 URL
2. `attach_file_to_issue(issue_id, file_url, title, subtitle, comment_body)`
3. `attach_file_to_epic(epic_id, file_url, title, subtitle)`

**API Workflow:**
```
1. fileUpload mutation → Get pre-signed S3 URL + headers
2. PUT file to S3 with provided headers
3. attachmentCreate mutation → Create attachment record
   - For issues: Use issueId field
   - For epics: Use projectId field
```

**GraphQL Mutations:**
```graphql
# Step 1: Get upload URL
mutation FileUpload($size: Int!, $contentType: String!, $filename: String!) {
  fileUpload(size: $size, contentType: $contentType, filename: $filename) {
    success
    uploadFile {
      assetUrl
      uploadUrl
      headers {
        key
        value
      }
    }
  }
}

# Step 3: Create attachment
mutation AttachmentCreate($input: AttachmentCreateInput!) {
  attachmentCreate(input: $input) {
    success
    attachment {
      id
      title
      url
      subtitle
      metadata
      createdAt
      updatedAt
    }
  }
}
```

**Limitations:**
- File size limits imposed by Linear's S3 configuration
- Requires Linear Pro plan for attachment storage

**Test Coverage:**
- `/tests/adapters/test_linear_file_upload.py` (13+ test methods)
- `/tests/integration/test_linear_epic_file_workflow.py` (workflow tests)
- `/tests/mcp/test_ticket_attach_tool.py` (MCP tool integration)

---

### 4.2 JIRA Adapter ✅

**Status**: Fully implemented

**Implementation Files:**
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/jira.py`
- Lines 1619-1724 (attachment methods)

**Methods:**
1. `add_attachment(ticket_id, file_path, description)` → Returns `Attachment`
2. `get_attachments(ticket_id)` → Returns `list[Attachment]`

**API Workflow:**
```python
# JIRA requires special header
headers = {
    "X-Atlassian-Token": "no-check",
}

# Multipart upload
with open(file_path, "rb") as f:
    files = {"file": (filename, f, "application/octet-stream")}
    response = await client.post(
        f"{api_base}/issue/{ticket_id}/attachments",
        files=files,
        headers={**self.headers, **headers}
    )
```

**REST API Endpoint:**
- `POST /rest/api/3/issue/{issueIdOrKey}/attachments`
- Returns array with single attachment object

**Response Mapping:**
```python
attachment_data = response.json()[0]  # JIRA returns array

return Attachment(
    id=attachment_data["id"],
    ticket_id=ticket_id,
    filename=attachment_data["filename"],
    url=attachment_data["content"],
    content_type=attachment_data["mimeType"],
    size_bytes=attachment_data["size"],
    created_at=parse_jira_datetime(attachment_data["created"]),
    created_by=attachment_data["author"]["displayName"],
    description=description,
    metadata={"jira": attachment_data},
)
```

**Limitations:**
- Max file size: 10MB (JIRA Cloud default, configurable)
- Requires JIRA attachment permissions
- Works for both Issues and Epics (epics are special issue types)

**Test Coverage:**
- `/tests/adapters/test_jira_epic_attachments.py` (multiple test suites)
- Tests both epic and issue attachments
- Validates JIRA-specific metadata

---

### 4.3 GitHub Adapter ✅

**Status**: Implemented with workarounds

**Implementation Files:**
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/github.py`
- Lines 1562-1712 (attachment methods)

**Methods:**
1. `add_attachment_to_issue(issue_number, file_path, comment)`
2. `add_attachment_reference_to_milestone(milestone_number, file_url, description)`
3. `add_attachment(ticket_id, file_path, description)` → Router method

**API Limitation:**
GitHub Issues **does not have a native file attachment API**. The adapter provides workarounds:

#### For Issues:
```python
# Creates comment with file reference
comment_body = f"📎 Attached: `{filename}`"
comment_body += (
    f"\n\n*Note: File `{filename}` ({file_size} bytes) "
    "needs to be manually uploaded through GitHub UI or referenced via URL.*"
)

response = await client.post(
    f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
    json={"body": comment_body}
)
```

**Returns:**
```python
{
    "comment_id": comment_data["id"],
    "comment_url": comment_data["html_url"],
    "filename": filename,
    "file_size": file_size,
    "note": "File reference created. Upload file manually through GitHub UI."
}
```

#### For Milestones (Epics):
```python
# Appends markdown link to milestone description
attachment_markdown = f"\n\n📎 [{description}]({file_url})"
new_description = current_desc + attachment_markdown

await update_milestone(milestone_number, {"description": new_description})
```

**Limitations:**
- **No direct upload API** - files must be uploaded manually
- File size limit: 25MB (GitHub's drag-and-drop limit)
- Milestones: Only supports URL references (not file uploads)
- Requires manual user action to complete attachment

**Workaround Strategy:**
1. Validate file exists and size < 25MB
2. Create comment/description placeholder
3. Return metadata with instructions for manual upload
4. User uploads file through GitHub web UI
5. File becomes inline attachment in comment

**Test Coverage:**
- `/tests/adapters/test_github_epic_attachments.py` (20+ test methods)
- Tests milestone attachment reference
- Tests issue attachment comment creation
- Tests error handling for unsupported operations

---

### 4.4 Asana Adapter ✅

**Status**: Fully implemented, **MISSING TESTS**

**Implementation Files:**
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/asana/adapter.py`
- Lines 1293-1380 (attachment methods)

**Methods:**
1. `add_attachment(ticket_id, file_path, description)` → Returns `Attachment`
2. `get_attachments(ticket_id)` → Returns `list[Attachment]`

**API Workflow:**
```python
# Direct multipart upload (no {"data": {...}} wrapping)
async with httpx.AsyncClient(timeout=60.0) as upload_client:
    with open(file_path, "rb") as f:
        files = {"file": (filename, f, mime_type)}
        headers = {"Authorization": f"Bearer {self.api_key}"}

        response = await upload_client.post(
            f"{BASE_URL}/tasks/{ticket_id}/attachments",
            files=files,
            headers=headers
        )
```

**REST API Endpoint:**
- `POST /api/1.0/tasks/{task_gid}/attachments`
- Returns attachment object in `data` field

**Response Mapping:**
```python
# Uses helper function
return map_asana_attachment_to_attachment(attachment_data, ticket_id)

# Helper extracts:
# - gid → id
# - name → filename
# - permanent_url → url (important: use permanent_url, not download_url)
# - size → size_bytes
# - created_at → created_at
```

**Limitations:**
- Max file size: 100MB (Asana default)
- Requires Asana attachment permissions
- Works for tasks only (not projects/portfolios)

**Test Coverage:**
- ⚠️ **MISSING**: No dedicated attachment tests for Asana
- `/tests/adapters/test_asana_custom_fields.py` exists but no attachment tests
- **Gap identified**: Need to create test suite

---

### 4.5 AiTrackDown Adapter ✅

**Status**: Fully implemented, **PARTIAL TESTS**

**Implementation Files:**
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/aitrackdown.py`
- Lines 714-825 (attachment methods)

**Methods:**
1. `add_attachment(ticket_id, file_path, description)` → Returns `Attachment`
2. `get_attachments(ticket_id)` → Returns `list[Attachment]`

**Local Storage Strategy:**
```python
# Create attachment directory per ticket
attachments_dir = base_path / "attachments" / ticket_id
attachments_dir.mkdir(parents=True, exist_ok=True)

# Generate unique filename with timestamp
timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
attachment_id = f"{timestamp}-{safe_filename}"
dest_path = attachments_dir / attachment_id

# Copy file with metadata
shutil.copy2(source_path, dest_path)
```

**Metadata Storage:**
```python
# Save metadata to JSON file
metadata_file = attachments_dir / f"{attachment_id}.json"
with open(metadata_file, "w") as f:
    data = attachment.model_dump()
    json.dump(data, f, indent=2, default=str)
```

**Security Features:**
- Path traversal protection (validates `ticket_id`)
- Filename sanitization
- File size limit: 100MB
- SHA-256 checksum calculation
- Resolves symlinks before validation

**Attachment Structure:**
```
.aitrackdown/
  attachments/
    TICKET-123/
      20251124120000000000-document.pdf
      20251124120000000000-document.pdf.json
      20251124120500000000-image.png
      20251124120500000000-image.png.json
```

**Limitations:**
- Local filesystem only (no cloud storage)
- 100MB file size limit
- Requires local disk space
- No built-in file versioning

**Test Coverage:**
- ⚠️ **PARTIAL**: Only security tests exist
- `/tests/adapters/test_aitrackdown_security.py` (path traversal tests)
- `/tests/e2e/test_comments_and_attachments.py` (basic attachment test)
- **Gap identified**: Need comprehensive attachment test suite

---

## 5. Test Coverage Analysis

### 5.1 Existing Test Files

| Test File | Adapter | Coverage | Status |
|-----------|---------|----------|--------|
| `test_linear_file_upload.py` | Linear | Excellent | ✅ Complete |
| `test_jira_epic_attachments.py` | JIRA | Good | ✅ Complete |
| `test_github_epic_attachments.py` | GitHub | Good | ✅ Complete |
| `test_asana_custom_fields.py` | Asana | N/A (no attachments) | ⚠️ Missing |
| `test_aitrackdown_security.py` | AiTrackDown | Security only | ⚠️ Partial |
| `test_ticket_attach_tool.py` | MCP Tool | Excellent | ✅ Complete |
| `test_adapter_epic_attachments.py` | Integration | Good | ✅ Complete |
| `test_comments_and_attachments.py` | E2E | Basic | ⚠️ Minimal |

### 5.2 Test Coverage Gaps

#### Gap 1: Asana Attachment Tests (HIGH PRIORITY)
**Missing tests:**
- `add_attachment()` basic functionality
- File validation (exists, size, permissions)
- Multipart upload handling
- MIME type detection
- `get_attachments()` retrieval
- Error handling (API errors, network issues)
- Asana-specific response mapping

**Recommended test file:**
`/Users/masa/Projects/mcp-ticketer/tests/adapters/test_asana_attachments.py`

**Test cases needed:**
```python
class TestAsanaAttachments:
    async def test_add_attachment_success()
    async def test_add_attachment_file_not_found()
    async def test_add_attachment_file_too_large()
    async def test_add_attachment_invalid_ticket()
    async def test_add_attachment_api_error()
    async def test_get_attachments_success()
    async def test_get_attachments_empty()
    async def test_get_attachments_multiple()
    async def test_attachment_metadata_mapping()
    async def test_attachment_mime_type_detection()
```

#### Gap 2: AiTrackDown Attachment Tests (HIGH PRIORITY)
**Missing tests:**
- Comprehensive `add_attachment()` testing
- `get_attachments()` with multiple files
- Metadata JSON persistence
- Checksum validation
- Storage cleanup
- Edge cases (empty files, special characters)

**Recommended test file:**
`/Users/masa/Projects/mcp-ticketer/tests/adapters/test_aitrackdown_attachments.py`

**Test cases needed:**
```python
class TestAiTrackDownAttachments:
    async def test_add_attachment_creates_directory()
    async def test_add_attachment_copies_file()
    async def test_add_attachment_saves_metadata()
    async def test_add_attachment_calculates_checksum()
    async def test_get_attachments_reads_metadata()
    async def test_attachment_filename_sanitization()
    async def test_attachment_size_limit()
    async def test_attachment_storage_structure()
```

#### Gap 3: Integration Tests (MEDIUM PRIORITY)
**Current state:**
- `/tests/integration/test_adapter_epic_attachments.py` exists
- Tests JIRA and GitHub
- **Missing**: Asana and AiTrackDown integration tests

**Recommended additions:**
```python
# In test_adapter_epic_attachments.py
class TestAsanaAdapterAttachments:
    async def test_asana_task_attachment_workflow()

class TestAiTrackDownAttachments:
    async def test_local_storage_attachment_workflow()
```

---

## 6. Implementation Recommendations

### 6.1 Current State Assessment

**Summary**: All adapters have attachment functionality implemented. The primary gap is **test coverage**, not implementation.

**Implementation Matrix:**

| Component | Status | Recommendation |
|-----------|--------|----------------|
| BaseAdapter interface | ✅ Complete | No changes needed |
| Attachment model | ✅ Complete | No changes needed |
| MCP tool | ✅ Complete | No changes needed |
| Linear adapter | ✅ Complete | Maintenance only |
| JIRA adapter | ✅ Complete | Maintenance only |
| GitHub adapter | ✅ Complete | Maintenance only |
| Asana adapter | ✅ Complete | **Add tests** |
| AiTrackDown adapter | ✅ Complete | **Add tests** |

### 6.2 Test Development Priority

#### Priority 1: Asana Adapter Tests (CRITICAL)
**Rationale**: Fully functional implementation with zero test coverage

**Action items:**
1. Create `/tests/adapters/test_asana_attachments.py`
2. Implement 10-15 test cases covering:
   - Happy path (upload, retrieve)
   - Error handling (file not found, API errors)
   - Edge cases (large files, special characters)
   - Metadata mapping validation
3. Mock Asana API responses
4. Test MIME type detection
5. Validate permanent_url vs download_url usage

**Estimated effort**: 4-6 hours

#### Priority 2: AiTrackDown Adapter Tests (HIGH)
**Rationale**: Partial coverage (security only), needs comprehensive tests

**Action items:**
1. Create `/tests/adapters/test_aitrackdown_attachments.py`
2. Expand existing security tests
3. Add storage workflow tests
4. Test metadata persistence
5. Validate checksum calculation
6. Test file size limits

**Estimated effort**: 3-5 hours

#### Priority 3: Integration Test Expansion (MEDIUM)
**Rationale**: Ensure end-to-end workflows work across adapters

**Action items:**
1. Add Asana integration tests to `test_adapter_epic_attachments.py`
2. Add AiTrackDown workflow tests
3. Test cross-adapter attachment retrieval
4. Validate MCP tool routing for all adapters

**Estimated effort**: 2-3 hours

### 6.3 Documentation Updates

**Current documentation:**
- `/docs/integrations/ATTACHMENTS.md` - Good coverage
- `/docs/developer-docs/api/epic_updates_and_attachments.md` - Comprehensive
- Adapter-specific docs exist

**Recommendations:**
- ✅ Documentation is comprehensive
- Update with test file locations
- Add Asana-specific notes about permanent_url
- Document AiTrackDown storage structure

---

## 7. Adapter API Capability Matrix

| Capability | Linear | JIRA | GitHub | Asana | AiTrackDown |
|------------|--------|------|--------|-------|-------------|
| **Native Upload API** | ✅ S3 | ✅ REST | ❌ No | ✅ REST | ✅ Local |
| **Direct Attachment** | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes | ✅ Yes |
| **Max File Size** | ~100MB | 10MB | 25MB* | 100MB | 100MB |
| **MIME Detection** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Metadata Storage** | ✅ GraphQL | ✅ REST | ❌ Comments | ✅ REST | ✅ JSON |
| **Epic Attachments** | ✅ Yes | ✅ Yes | ⚠️ URL only | ✅ Yes | ✅ Yes |
| **Issue Attachments** | ✅ Yes | ✅ Yes | ⚠️ Reference | ✅ Yes | ✅ Yes |
| **Attachment Deletion** | ❌ Not impl | ❌ Not impl | ❌ Not impl | ❌ Not impl | ❌ Not impl |
| **Retrieval API** | ✅ Yes | ✅ Yes | ⚠️ Comments | ✅ Yes | ✅ Yes |

*GitHub: 25MB is UI limit, no programmatic upload

---

## 8. API Endpoint Reference

### Linear GraphQL

**Upload File:**
```graphql
mutation FileUpload($size: Int!, $contentType: String!, $filename: String!) {
  fileUpload(size: $size, contentType: $contentType, filename: $filename) {
    success
    uploadFile {
      assetUrl
      uploadUrl
      headers { key value }
    }
  }
}
```

**Create Attachment:**
```graphql
mutation AttachmentCreate($input: AttachmentCreateInput!) {
  attachmentCreate(input: $input) {
    success
    attachment {
      id
      title
      url
      subtitle
      metadata
      createdAt
    }
  }
}
```

**Input Types:**
- For issues: `{ issueId: UUID, title: String, url: String, subtitle?: String, commentBody?: String }`
- For epics: `{ projectId: UUID, title: String, url: String, subtitle?: String }`

### JIRA REST API

**Upload Attachment:**
```
POST /rest/api/3/issue/{issueIdOrKey}/attachments
Content-Type: multipart/form-data
X-Atlassian-Token: no-check

file: <binary data>
```

**Response:**
```json
[
  {
    "id": "10001",
    "filename": "document.pdf",
    "author": { "displayName": "User Name" },
    "created": "2025-11-24T12:00:00.000+0000",
    "size": 12345,
    "mimeType": "application/pdf",
    "content": "https://jira.example.com/download/10001",
    "thumbnail": "https://jira.example.com/thumbnail/10001"
  }
]
```

**Get Attachments:**
```
GET /rest/api/3/issue/{issueIdOrKey}
```
Attachments are in `fields.attachment` array.

### GitHub REST API

**No direct attachment endpoint**. Workaround:

**Create Comment:**
```
POST /repos/{owner}/{repo}/issues/{issue_number}/comments
{
  "body": "📎 Attached: `filename.pdf`\n\n*Note: Upload manually*"
}
```

**Update Milestone Description:**
```
PATCH /repos/{owner}/{repo}/milestones/{milestone_number}
{
  "description": "Current description\n\n📎 [File](https://url)"
}
```

### Asana REST API

**Upload Attachment:**
```
POST /api/1.0/tasks/{task_gid}/attachments
Content-Type: multipart/form-data
Authorization: Bearer <token>

file: <binary data>
```

**Response:**
```json
{
  "data": {
    "gid": "12345",
    "name": "document.pdf",
    "resource_type": "attachment",
    "created_at": "2025-11-24T12:00:00.000Z",
    "download_url": "https://s3.amazonaws.com/...",
    "permanent_url": "https://app.asana.com/...",
    "size": 12345,
    "view_url": "https://app.asana.com/..."
  }
}
```

**Get Attachments:**
```
GET /api/1.0/tasks/{task_gid}/attachments
```

**Important**: Use `permanent_url`, not `download_url` (expires).

### AiTrackDown (Local)

**Storage Path:**
```
{base_path}/attachments/{ticket_id}/{timestamp}-{filename}
{base_path}/attachments/{ticket_id}/{timestamp}-{filename}.json
```

**Metadata JSON:**
```json
{
  "id": "20251124120000000000-document.pdf",
  "ticket_id": "TICKET-123",
  "filename": "document.pdf",
  "url": "file:///path/to/attachments/TICKET-123/20251124120000000000-document.pdf",
  "content_type": "application/pdf",
  "size_bytes": 12345,
  "created_at": "2025-11-24T12:00:00",
  "description": "Optional description",
  "metadata": {
    "original_path": "/path/to/source/document.pdf",
    "storage_path": "/path/to/attachments/TICKET-123/20251124120000000000-document.pdf",
    "checksum": "sha256:abcdef..."
  }
}
```

---

## 9. Error Handling Patterns

### Common Error Scenarios

#### 1. File Not Found
```python
# All adapters handle this consistently
if not file_path.exists():
    raise FileNotFoundError(f"File not found: {file_path}")
```

#### 2. Ticket Not Found
```python
# Validate ticket exists before upload
ticket = await adapter.read(ticket_id)
if not ticket:
    raise ValueError(f"Ticket {ticket_id} not found")
```

#### 3. File Too Large
```python
# Adapter-specific limits
size_mb = file_path.stat().st_size / (1024 * 1024)
if size_mb > MAX_SIZE:
    raise ValueError(f"File too large: {size_mb:.2f}MB (max: {MAX_SIZE}MB)")
```

#### 4. API Upload Failure
```python
# Handle HTTP errors
try:
    response = await client.post(url, files=files)
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    raise ValueError(f"Upload failed: {e.response.status_code}")
```

#### 5. Insufficient Permissions
```python
# JIRA: Check credentials first
is_valid, error_message = self.validate_credentials()
if not is_valid:
    raise ValueError(error_message)
```

### MCP Tool Error Responses

```python
# Consistent error format
{
    "status": "error",
    "error": "Descriptive error message",
    "ticket_id": ticket_id,
    "note": "Optional guidance for user"
}
```

---

## 10. Implementation Notes for 1M-157

### What's Already Done ✅

1. **BaseAdapter Interface**: Complete with all required methods
2. **Attachment Model**: Universal model defined and used across all adapters
3. **MCP Tool**: Sophisticated three-tier fallback strategy implemented
4. **Linear Adapter**: Full S3 upload + attachment creation
5. **JIRA Adapter**: Native multipart upload
6. **GitHub Adapter**: Comment reference workaround
7. **Asana Adapter**: Native multipart upload
8. **AiTrackDown Adapter**: Local filesystem storage

### What Needs to Be Done ⚠️

1. **Asana Tests**: Create comprehensive test suite (10-15 tests)
2. **AiTrackDown Tests**: Expand beyond security tests (10-15 tests)
3. **Integration Tests**: Add Asana and AiTrackDown to integration suite
4. **Documentation**: Update with test file locations

### No Code Changes Required ✅

The attachment functionality is **fully implemented** across all adapters. The ticket 1M-157 should focus on:

1. **Test development** (primary focus)
2. **Documentation updates** (secondary)
3. **Code review** (verify existing implementations)

### Recommended Implementation Approach

**Phase 1: Asana Tests (Week 1)**
- Create `test_asana_attachments.py`
- Implement 10-15 test cases
- Mock Asana API responses
- Validate all code paths

**Phase 2: AiTrackDown Tests (Week 1)**
- Create `test_aitrackdown_attachments.py`
- Expand security tests
- Add storage workflow tests
- Validate metadata persistence

**Phase 3: Integration Tests (Week 2)**
- Add Asana integration tests
- Add AiTrackDown workflow tests
- Validate cross-adapter behavior

**Phase 4: Documentation (Week 2)**
- Update ATTACHMENTS.md with test locations
- Add adapter-specific notes
- Update API reference

---

## 11. Code Quality Observations

### Strengths

1. **Consistent Interface**: All adapters follow BaseAdapter contract
2. **Universal Model**: Single Attachment model works across platforms
3. **Graceful Degradation**: MCP tool has three-tier fallback strategy
4. **Error Handling**: Comprehensive error handling across adapters
5. **Security**: Path traversal protection, file validation
6. **MIME Detection**: Consistent across all adapters
7. **Documentation**: Well-documented adapter-specific behavior

### Areas for Improvement

1. **Delete Support**: No adapters implement `delete_attachment()`
2. **Pagination**: `get_attachments()` has no pagination
3. **Test Coverage**: Asana and AiTrackDown need tests
4. **File Versioning**: No version control for attachments
5. **Progress Tracking**: No upload progress callbacks

---

## 12. Future Enhancement Opportunities

### Short-term (Next Release)

1. **Test Coverage**: Complete Asana and AiTrackDown test suites
2. **Documentation**: Add test file references
3. **Error Messages**: Improve user-facing error messages in MCP tool

### Medium-term (Future Releases)

1. **Delete Support**: Implement `delete_attachment()` for all adapters
2. **Pagination**: Add pagination to `get_attachments()`
3. **Progress Callbacks**: Upload progress tracking for large files
4. **File Validation**: Enhanced MIME type validation
5. **Retry Logic**: Automatic retry for transient failures

### Long-term (Roadmap)

1. **File Versioning**: Track attachment versions
2. **Thumbnails**: Generate thumbnails for images
3. **Virus Scanning**: Optional malware scanning integration
4. **CDN Integration**: Optional CDN for faster attachment delivery
5. **Bulk Operations**: Upload multiple files at once

---

## 13. Conclusion

### Summary

The ticket_attach() implementation is **functionally complete** across all five adapters. Each adapter has working `add_attachment()` and `get_attachments()` methods that follow the BaseAdapter interface contract. The MCP tool provides a sophisticated three-tier fallback strategy ensuring attachment functionality works across all platforms.

### Primary Gap: Test Coverage

The main gap is **test coverage** for Asana and AiTrackDown adapters:

- **Asana**: Zero attachment tests despite full implementation
- **AiTrackDown**: Only security tests, missing comprehensive coverage

### Recommended Actions for 1M-157

**Priority 1: Testing (85% of effort)**
1. Create comprehensive Asana attachment test suite
2. Expand AiTrackDown attachment tests
3. Add integration tests for both adapters

**Priority 2: Documentation (10% of effort)**
1. Update docs with test file locations
2. Add adapter-specific notes
3. Document test coverage status

**Priority 3: Code Review (5% of effort)**
1. Review existing implementations
2. Validate error handling
3. Ensure consistent behavior

### No Implementation Work Needed

All adapters have working attachment functionality. The ticket should **NOT** involve writing new adapter code, only:
- Writing tests
- Updating documentation
- Validating existing behavior

---

## Appendices

### Appendix A: Test File Locations

```
tests/
├── adapters/
│   ├── test_linear_file_upload.py          ✅ Complete
│   ├── test_jira_epic_attachments.py       ✅ Complete
│   ├── test_github_epic_attachments.py     ✅ Complete
│   ├── test_asana_attachments.py           ⚠️ NEEDS CREATION
│   └── test_aitrackdown_attachments.py     ⚠️ NEEDS CREATION
├── mcp/
│   └── test_ticket_attach_tool.py          ✅ Complete
├── integration/
│   ├── test_adapter_epic_attachments.py    ✅ Complete (needs Asana/AiTrackDown)
│   └── test_linear_epic_file_workflow.py   ✅ Complete
└── e2e/
    └── test_comments_and_attachments.py    ✅ Basic coverage
```

### Appendix B: Adapter Implementation Files

```
src/mcp_ticketer/adapters/
├── linear/
│   └── adapter.py                          Lines 2162-2310 (attachments)
├── jira.py                                 Lines 1619-1724 (attachments)
├── github.py                               Lines 1562-1712 (attachments)
├── asana/
│   └── adapter.py                          Lines 1293-1380 (attachments)
└── aitrackdown.py                          Lines 714-825 (attachments)
```

### Appendix C: Key Model Files

```
src/mcp_ticketer/core/
├── adapter.py                              Lines 540-610 (BaseAdapter methods)
└── models.py                               Lines 389-417 (Attachment model)
```

### Appendix D: MCP Tool Files

```
src/mcp_ticketer/mcp/server/tools/
└── attachment_tools.py                     Lines 1-227 (ticket_attach, ticket_attachments)
```

---

**End of Research Document**
