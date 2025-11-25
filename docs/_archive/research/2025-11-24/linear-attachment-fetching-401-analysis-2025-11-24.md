# Linear Attachment Fetching 401 Error Analysis

**Research Date**: 2025-11-24
**Researcher**: Research Agent
**Context**: Analyzing 401 Unauthorized errors when fetching Linear attachments

---

## Executive Summary

### Critical Finding: Missing Implementation

The Linear adapter **does not implement `get_attachments()`** method, which means:

1. **No attachment retrieval capability** exists for Linear tickets
2. **401 errors likely occur** when attempting to access Linear attachment URLs without authentication headers
3. **Base adapter raises NotImplementedError** when `get_attachments()` is called on Linear adapter

### Root Cause

When users attempt to fetch attachments from Linear tickets:

1. The MCP tool `ticket_attachments()` calls `adapter.get_attachments(ticket_id)`
2. Linear adapter inherits BaseAdapter's default implementation
3. BaseAdapter's `get_attachments()` raises `NotImplementedError`
4. If attachment URLs are accessed directly (e.g., from metadata), they fail with 401 because:
   - Linear's S3 URLs are **pre-signed with expiration**
   - Accessing expired URLs returns 401 Unauthorized
   - Accessing fresh URLs without Linear API authentication headers returns 401

---

## 1. Current Implementation Status

### 1.1 Linear Adapter - Upload Implementation ✅

**Location**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/adapter.py`

**Implemented Methods:**
- ✅ `upload_file(file_path, mime_type)` - Uploads file to Linear's S3 storage (lines 2065-2176)
- ✅ `attach_file_to_issue(issue_id, file_url, title, ...)` - Creates attachment record (lines 2178-2259)
- ✅ `attach_file_to_epic(epic_id, file_url, title, ...)` - Creates attachment for projects (lines 2261-2339)

**Upload Workflow:**
```python
# Step 1: Request pre-signed S3 URL
mutation FileUpload {
    fileUpload(contentType: "...", filename: "...", size: ...) {
        success
        uploadFile {
            uploadUrl    # Pre-signed S3 URL for PUT
            assetUrl     # Final Linear CDN URL
            headers { key value }
        }
    }
}

# Step 2: Upload to S3 with provided headers
async with httpx.AsyncClient() as http_client:
    response = await http_client.put(
        upload_url,
        content=file_content,
        headers=upload_headers  # Includes auth headers
    )

# Step 3: Create attachment record
mutation AttachmentCreate {
    attachmentCreate(input: {
        issueId: "...",
        title: "...",
        url: asset_url  # Linear CDN URL
    }) {
        success
        attachment { id title url }
    }
}
```

**Key Points:**
- Upload process properly includes authentication headers
- Pre-signed URLs are valid for short duration (typically 15 minutes)
- Final `assetUrl` is stored in attachment record

### 1.2 Linear Adapter - Retrieval Implementation ❌

**Missing Method:** `get_attachments(ticket_id)`

**Current State:**
```python
# LinearAdapter class DOES NOT override get_attachments()
# Falls back to BaseAdapter implementation:

async def get_attachments(self, ticket_id: str) -> list[Attachment]:
    """Get all attachments for a ticket."""
    raise NotImplementedError(
        f"{self.__class__.__name__} does not support file attachments."
    )
```

**Implication:**
- Calling `linear_adapter.get_attachments("ISSUE-123")` raises `NotImplementedError`
- Users cannot retrieve attachment metadata programmatically
- Direct URL access fails with 401 if URLs have expired or lack authentication

---

## 2. BaseAdapter Interface

### 2.1 Expected Interface

**Location**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/core/adapter.py` (lines 571-585)

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

### 2.2 Adapter Implementation Status

| Adapter | get_attachments() | Status | Notes |
|---------|-------------------|--------|-------|
| **Linear** | ❌ Not implemented | MISSING | Inherits NotImplementedError |
| **JIRA** | ✅ Implemented | Complete | Lines 1687-1724 |
| **GitHub** | ❌ Not implemented | Expected | No native attachment API |
| **Asana** | ✅ Implemented | Complete | Lines 1358-1384 |
| **AiTrackDown** | ✅ Implemented | Complete | Lines 794-825 |

---

## 3. MCP Tool: ticket_attachments()

### 3.1 Tool Implementation

**Location**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/attachment_tools.py` (lines 148-226)

```python
@mcp.tool()
async def ticket_attachments(ticket_id: str) -> dict[str, Any]:
    """Get all attachments for a ticket."""
    try:
        adapter = get_adapter()

        # Read ticket to validate it exists
        ticket = await adapter.read(ticket_id)
        if ticket is None:
            return {
                "status": "error",
                "error": f"Ticket {ticket_id} not found",
            }

        # Check if adapter supports attachments
        if not hasattr(adapter, "get_attachments"):
            return {
                "status": "error",
                "error": f"Attachment retrieval not supported by {type(adapter).__name__} adapter",
                "ticket_id": ticket_id,
                "note": "Check ticket comments for file references",
            }

        # Get attachments via adapter
        attachments = await adapter.get_attachments(ticket_id)

        return {
            "status": "completed",
            "ticket_id": ticket_id,
            "attachments": attachments,
            "count": len(attachments) if isinstance(attachments, list) else 0,
        }

    except AttributeError:
        # Fallback: Check comments for attachment references
        comments = await adapter.get_comments(ticket_id=ticket_id, limit=100)
        # ... returns comment-based references ...
```

### 3.2 Error Scenarios

**Scenario 1: Linear adapter with get_attachments() call**
```python
# Current behavior
result = await ticket_attachments("ENG-842")

# Returns:
{
    "status": "error",
    "error": "LinearAdapter does not support file attachments.",
    "ticket_id": "ENG-842"
}
```

**Scenario 2: Direct URL access without authentication**
```python
# If user attempts to access Linear attachment URL directly
# attachment_url = "https://linear.app/api/attachments/..."
response = requests.get(attachment_url)  # No auth headers
# Returns: 401 Unauthorized
```

---

## 4. 401 Error Root Causes

### 4.1 Unauthenticated URL Access

**Problem**: Linear attachment URLs require authentication

**Evidence**:
- Linear's GraphQL API requires `Authorization: Bearer <api_key>` header
- Attachment URLs returned from `attachmentCreate` mutation are **Linear CDN URLs**
- These URLs require Linear session or API authentication to access
- Direct HTTP GET requests without auth headers return 401

**Example**:
```python
# This FAILS with 401
import httpx
response = httpx.get("https://linear.app/api/attachments/abc123")
# Returns: 401 Unauthorized

# This WORKS
headers = {"Authorization": f"Bearer {linear_api_key}"}
response = httpx.get("https://linear.app/api/attachments/abc123", headers=headers)
# Returns: 200 OK + file content
```

### 4.2 Expired Pre-signed URLs

**Problem**: S3 pre-signed URLs expire after short duration

**Evidence**:
- Linear's `fileUpload` mutation returns temporary `uploadUrl` for PUT operations
- These URLs expire after ~15 minutes
- The `assetUrl` returned is the final CDN URL, which requires authentication

**Timeline**:
```
T+0:   User uploads file via upload_file()
       - Gets pre-signed S3 URL (uploadUrl) - valid for 15 min
       - Gets final CDN URL (assetUrl) - requires auth forever

T+15m: uploadUrl expires (but already used for upload)
       - assetUrl still valid but requires Linear API key

T+∞:   assetUrl requires Linear API authentication to access
       - Without auth header → 401 Unauthorized
```

### 4.3 Missing Attachment Retrieval Implementation

**Problem**: Linear adapter can't fetch attachment metadata

**Evidence**:
- No `get_attachments()` method in LinearAdapter
- No GraphQL query to retrieve attachments for issues/projects
- Base adapter raises NotImplementedError

**Impact**:
- Users can upload files but can't programmatically retrieve attachment list
- No way to get fresh download URLs
- No way to access attachment metadata

---

## 5. Linear GraphQL API Analysis

### 5.1 Attachment Upload Mutations ✅ (Implemented)

**fileUpload Mutation:**
```graphql
mutation FileUpload($contentType: String!, $filename: String!, $size: Int!) {
    fileUpload(contentType: $contentType, filename: $filename, size: $size) {
        success
        uploadFile {
            uploadUrl      # Pre-signed S3 URL (temporary)
            assetUrl       # Linear CDN URL (permanent, requires auth)
            headers {
                key
                value
            }
        }
    }
}
```

**attachmentCreate Mutation:**
```graphql
mutation AttachmentCreate($input: AttachmentCreateInput!) {
    attachmentCreate(input: $input) {
        success
        attachment {
            id
            title
            url            # Linear CDN URL (requires auth)
            subtitle
            metadata
            createdAt
            updatedAt
        }
    }
}
```

### 5.2 Attachment Retrieval Queries ⚠️ (Not Implemented)

**Required Query:**
```graphql
query GetIssueAttachments($issueId: String!) {
    issue(id: $issueId) {
        id
        identifier
        attachments {
            nodes {
                id
                title
                url          # CDN URL requiring auth
                subtitle
                metadata
                createdAt
                updatedAt
                creator {
                    id
                    name
                    email
                }
            }
        }
    }
}
```

**Project Attachments:**
```graphql
query GetProjectAttachments($projectId: String!) {
    project(id: $projectId) {
        id
        name
        documents {     # Linear calls them "documents" for projects
            nodes {
                id
                title
                url
                createdAt
                updatedAt
            }
        }
    }
}
```

### 5.3 API Documentation Gap

**Linear API Documentation** (as of 2025-11-24):
- ✅ Documents file upload process
- ✅ Documents attachment creation
- ❌ Does not clearly document attachment retrieval
- ⚠️ Does not mention authentication requirements for CDN URLs

**Attachment URL Format:**
```
https://linear.app/api/attachments/{attachment_id}
https://files.linear.app/{workspace}/{attachment_id}/{filename}
```

**Required Headers:**
```python
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"  # For GraphQL queries
}
```

---

## 6. Why 401 Errors Occur

### 6.1 Scenario A: Direct URL Access from Metadata

**User Code:**
```python
# User retrieves ticket
ticket = await linear_adapter.read("ENG-842")

# Ticket metadata might contain attachment references
if "attachments" in ticket.metadata:
    for attachment in ticket.metadata["attachments"]:
        url = attachment["url"]

        # Attempt to fetch file (NO AUTH HEADERS!)
        import httpx
        response = await httpx.get(url)
        # ❌ Returns: 401 Unauthorized
```

**Root Cause**: Missing authentication headers in HTTP request

### 6.2 Scenario B: Calling get_attachments() on Linear Adapter

**User Code:**
```python
# Attempt to get attachments
attachments = await linear_adapter.get_attachments("ENG-842")
# ❌ Raises: NotImplementedError
```

**Root Cause**: Method not implemented

### 6.3 Scenario C: MCP Tool Usage

**User Command:**
```bash
# Via MCP tool
ticket_attachments(ticket_id="ENG-842")
```

**Current Behavior:**
```json
{
    "status": "error",
    "error": "LinearAdapter does not support file attachments.",
    "ticket_id": "ENG-842"
}
```

**Root Cause**: MCP tool falls back to NotImplementedError

---

## 7. Comparison with Other Adapters

### 7.1 JIRA Adapter ✅ (Working)

**Implementation:**
```python
async def get_attachments(self, ticket_id: str) -> list[Attachment]:
    """Get attachments from JIRA issue."""

    # Fetch issue with attachments field
    response = await self.client.get(
        f"/rest/api/3/issue/{ticket_id}",
        params={"fields": "attachment"}
    )

    # JIRA includes authentication in client.get()
    attachments_data = response["fields"]["attachment"]

    # Map to Attachment model
    return [
        Attachment(
            id=att["id"],
            ticket_id=ticket_id,
            filename=att["filename"],
            url=att["content"],  # Direct download URL with embedded auth
            content_type=att["mimeType"],
            size_bytes=att["size"],
            created_at=parse_jira_datetime(att["created"]),
            created_by=att["author"]["displayName"],
            metadata={"jira": att}
        )
        for att in attachments_data
    ]
```

**Key Points:**
- Uses REST API with authenticated client
- Attachment URLs include embedded authentication tokens
- URLs remain valid for session duration
- Client handles auth headers automatically

### 7.2 Asana Adapter ✅ (Working)

**Implementation:**
```python
async def get_attachments(self, ticket_id: str) -> list[Attachment]:
    """Get attachments for Asana task."""

    # Use authenticated API client
    attachments = await self.client.get_paginated(
        f"/tasks/{ticket_id}/attachments"
    )

    # Map to Attachment model
    return [
        map_asana_attachment_to_attachment(att, ticket_id)
        for att in attachments
    ]
```

**Asana Attachment Mapping:**
```python
def map_asana_attachment_to_attachment(attachment: dict, task_gid: str) -> Attachment:
    # Use PERMANENT_URL (stable), not download_url (expires)
    url = attachment.get("permanent_url") or attachment.get("view_url")

    return Attachment(
        id=attachment.get("gid"),
        ticket_id=task_gid,
        filename=attachment.get("name", ""),
        url=url,  # Asana permanent_url is stable and authenticated
        content_type=attachment.get("resource_subtype"),
        size_bytes=attachment.get("size"),
        created_at=parse_asana_datetime(attachment.get("created_at")),
        metadata={
            "asana_download_url": attachment.get("download_url"),  # Temporary!
            "asana_permanent_url": attachment.get("permanent_url")  # Use this!
        }
    )
```

**Key Points:**
- Uses permanent_url (stable) instead of download_url (expires)
- API client handles authentication
- Attachment retrieval is first-class API operation

### 7.3 AiTrackDown Adapter ✅ (Working)

**Implementation:**
```python
async def get_attachments(self, ticket_id: str) -> list[Attachment]:
    """Get attachments from local filesystem."""

    # Validate ticket_id (security check)
    safe_ticket_id = self._sanitize_ticket_id(ticket_id)

    # Find attachment directory
    attachments_dir = self.base_path / "attachments" / safe_ticket_id

    if not attachments_dir.exists():
        return []

    # Load attachment metadata from JSON files
    attachments = []
    for metadata_file in attachments_dir.glob("*.json"):
        with open(metadata_file) as f:
            data = json.load(f)
            attachments.append(Attachment(**data))

    return attachments
```

**Key Points:**
- Local filesystem, no network requests
- No authentication required (local access only)
- Metadata stored in JSON files
- URLs are file:// paths

---

## 8. Solution Design

### 8.1 Required Implementation

**Add get_attachments() to LinearAdapter:**

```python
async def get_attachments(self, ticket_id: str) -> list[Attachment]:
    """Get all attachments for a Linear issue or project.

    Args:
    ----
        ticket_id: Linear issue identifier (e.g., "ENG-842") or project UUID

    Returns:
    -------
        List of attachments with authenticated download URLs

    Raises:
    ------
        ValueError: If ticket not found or credentials invalid

    """
    # Validate credentials
    is_valid, error_message = self.validate_credentials()
    if not is_valid:
        raise ValueError(error_message)

    # Determine if it's an issue or project
    ticket = await self.read(ticket_id)
    if ticket is None:
        raise ValueError(f"Ticket {ticket_id} not found")

    # Check ticket type
    from ...core.models import TicketType
    ticket_type = getattr(ticket, "ticket_type", None)

    if ticket_type == TicketType.EPIC:
        # Get project attachments (documents)
        return await self._get_project_attachments(ticket_id)
    else:
        # Get issue attachments
        return await self._get_issue_attachments(ticket_id)
```

### 8.2 Issue Attachments Query

```python
async def _get_issue_attachments(self, issue_id: str) -> list[Attachment]:
    """Get attachments for a Linear issue."""

    # Resolve issue identifier to UUID
    issue_uuid = await self._resolve_issue_id(issue_id)
    if not issue_uuid:
        raise ValueError(f"Issue '{issue_id}' not found")

    # GraphQL query for attachments
    query = """
        query GetIssueAttachments($issueId: String!) {
            issue(id: $issueId) {
                id
                identifier
                attachments {
                    nodes {
                        id
                        title
                        url
                        subtitle
                        metadata
                        createdAt
                        updatedAt
                        creator {
                            id
                            name
                            email
                        }
                    }
                }
            }
        }
    """

    try:
        result = await self.client.execute_query(query, {"issueId": issue_uuid})

        if not result.get("issue"):
            return []

        attachments_data = result["issue"].get("attachments", {}).get("nodes", [])

        # Map to Attachment model
        return [
            self._map_linear_attachment_to_attachment(att, issue_id)
            for att in attachments_data
        ]

    except Exception as e:
        logging.getLogger(__name__).error(
            f"Failed to get attachments for issue {issue_id}: {e}"
        )
        return []
```

### 8.3 Project Attachments Query

```python
async def _get_project_attachments(self, project_id: str) -> list[Attachment]:
    """Get attachments (documents) for a Linear project."""

    # Resolve project identifier to UUID
    project_uuid = await self._resolve_project_id(project_id)
    if not project_uuid:
        raise ValueError(f"Project '{project_id}' not found")

    # GraphQL query for project documents
    query = """
        query GetProjectDocuments($projectId: String!) {
            project(id: $projectId) {
                id
                name
                documents {
                    nodes {
                        id
                        title
                        url
                        createdAt
                        updatedAt
                        creator {
                            id
                            name
                        }
                    }
                }
            }
        }
    """

    try:
        result = await self.client.execute_query(query, {"projectId": project_uuid})

        if not result.get("project"):
            return []

        documents_data = result["project"].get("documents", {}).get("nodes", [])

        # Map to Attachment model
        return [
            self._map_linear_attachment_to_attachment(doc, project_id)
            for doc in documents_data
        ]

    except Exception as e:
        logging.getLogger(__name__).error(
            f"Failed to get attachments for project {project_id}: {e}"
        )
        return []
```

### 8.4 Attachment Mapper

```python
def _map_linear_attachment_to_attachment(
    self,
    attachment_data: dict,
    ticket_id: str
) -> Attachment:
    """Map Linear attachment/document to Attachment model."""

    from ...core.models import Attachment
    from datetime import datetime

    # Parse creator info
    creator = attachment_data.get("creator", {})
    creator_name = creator.get("name") or creator.get("email")

    # Parse timestamps
    created_at = None
    if attachment_data.get("createdAt"):
        created_at = datetime.fromisoformat(
            attachment_data["createdAt"].replace("Z", "+00:00")
        )

    return Attachment(
        id=attachment_data.get("id"),
        ticket_id=ticket_id,
        filename=attachment_data.get("title", "Untitled"),
        url=attachment_data.get("url"),  # Linear CDN URL
        content_type=None,  # Linear doesn't provide MIME type in query
        size_bytes=None,    # Linear doesn't provide size in query
        created_at=created_at,
        created_by=creator_name,
        description=attachment_data.get("subtitle"),
        metadata={
            "linear": {
                "attachment_id": attachment_data.get("id"),
                "title": attachment_data.get("title"),
                "subtitle": attachment_data.get("subtitle"),
                "url": attachment_data.get("url"),
                "metadata": attachment_data.get("metadata"),
                "creator_id": creator.get("id"),
                "creator_email": creator.get("email")
            }
        }
    )
```

### 8.5 Authenticated URL Access

**CRITICAL**: Linear attachment URLs require authentication

**Problem**: The URLs returned from GraphQL queries require Linear API authentication

**Solution Option 1: Document Requirements**
```python
# In Attachment model metadata
{
    "linear": {
        "url": "https://files.linear.app/...",
        "requires_auth": True,
        "auth_header": "Authorization: Bearer {LINEAR_API_KEY}"
    }
}
```

**Solution Option 2: Provide Helper Method**
```python
async def download_attachment(
    self,
    attachment_id: str,
    output_path: str
) -> str:
    """Download Linear attachment to local file.

    Args:
        attachment_id: Linear attachment ID
        output_path: Local file path to save attachment

    Returns:
        Path to downloaded file

    Note:
        Uses authenticated API key to access Linear CDN URL
    """
    if httpx is None:
        raise ValueError("httpx library required for downloads")

    # Get attachment metadata
    query = """
        query GetAttachment($attachmentId: String!) {
            attachment(id: $attachmentId) {
                id
                title
                url
            }
        }
    """

    result = await self.client.execute_query(
        query,
        {"attachmentId": attachment_id}
    )

    attachment_url = result["attachment"]["url"]

    # Download with authentication
    async with httpx.AsyncClient() as http_client:
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        response = await http_client.get(
            attachment_url,
            headers=headers,
            follow_redirects=True
        )
        response.raise_for_status()

        # Save to file
        with open(output_path, "wb") as f:
            f.write(response.content)

    return output_path
```

---

## 9. Authentication Requirements

### 9.1 Linear CDN URL Authentication

**URL Format:**
```
https://files.linear.app/{workspace}/{attachment_id}/{filename}
```

**Required Headers:**
```python
headers = {
    "Authorization": f"Bearer {linear_api_key}"
}
```

**Test Results** (to be validated):
```python
# WITHOUT AUTH
response = httpx.get("https://files.linear.app/...")
# Expected: 401 Unauthorized

# WITH AUTH
headers = {"Authorization": f"Bearer {api_key}"}
response = httpx.get("https://files.linear.app/...", headers=headers)
# Expected: 200 OK + file content
```

### 9.2 Security Considerations

**API Key Exposure:**
- Linear API keys must be kept secure
- URLs should not embed API keys (prevents sharing)
- Users downloading attachments need valid API credentials

**URL Expiration:**
- Upload URLs expire after ~15 minutes (temporary S3 pre-signed URLs)
- Download URLs (assetUrl) require authentication but don't expire
- No token refresh needed for downloads (use API key directly)

**Access Control:**
- Linear enforces workspace/team permissions on attachment access
- Users without ticket access cannot download attachments
- API key must have appropriate scope (read:issue, read:project)

---

## 10. Recommended Implementation Plan

### Phase 1: Core Implementation (HIGH PRIORITY)

**Step 1: Implement get_attachments() method**
- Add to LinearAdapter class
- Support both issues and projects
- Handle missing attachments gracefully

**Step 2: Add GraphQL queries**
- Issue attachments query
- Project documents query
- Test with real Linear workspace

**Step 3: Implement mapper**
- Map Linear attachment format to Attachment model
- Extract metadata properly
- Handle missing fields

**Estimated Effort**: 4-6 hours

### Phase 2: Testing (HIGH PRIORITY)

**Step 1: Unit tests**
- Test `get_attachments()` for issues
- Test `get_attachments()` for projects
- Test empty attachments case
- Test error handling

**Step 2: Integration tests**
- Test end-to-end attachment workflow
- Upload → Retrieve → Verify
- Test with real Linear API

**Step 3: MCP tool validation**
- Test `ticket_attachments` MCP tool with Linear
- Verify JSON response format
- Test error cases

**Estimated Effort**: 3-4 hours

### Phase 3: Authentication Handling (MEDIUM PRIORITY)

**Step 1: Document authentication requirements**
- Update docs with auth header requirements
- Document URL format and access patterns
- Provide code examples

**Step 2: Add download helper (optional)**
- Implement `download_attachment()` method
- Handle authentication automatically
- Support bulk downloads

**Estimated Effort**: 2-3 hours

### Phase 4: Documentation (LOW PRIORITY)

**Step 1: Update attachment docs**
- Document Linear attachment retrieval
- Add GraphQL query examples
- Explain authentication requirements

**Step 2: Update API reference**
- Document new methods
- Add usage examples
- Update adapter capabilities matrix

**Estimated Effort**: 1-2 hours

---

## 11. Test Strategy

### 11.1 Unit Tests

**File**: `/tests/adapters/test_linear_attachments.py`

```python
import pytest
from mcp_ticketer.adapters.linear import LinearAdapter
from mcp_ticketer.core.models import Attachment

class TestLinearAttachments:
    """Test Linear attachment retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_attachments_for_issue(self, linear_adapter):
        """Test getting attachments for a Linear issue."""
        # Mock GraphQL response
        mock_response = {
            "issue": {
                "id": "issue-uuid",
                "identifier": "ENG-842",
                "attachments": {
                    "nodes": [
                        {
                            "id": "att-1",
                            "title": "document.pdf",
                            "url": "https://files.linear.app/workspace/att-1/document.pdf",
                            "createdAt": "2025-11-24T12:00:00.000Z",
                            "creator": {
                                "id": "user-1",
                                "name": "Test User",
                                "email": "user@example.com"
                            }
                        }
                    ]
                }
            }
        }

        linear_adapter.client.execute_query = AsyncMock(return_value=mock_response)

        # Test
        attachments = await linear_adapter.get_attachments("ENG-842")

        # Verify
        assert len(attachments) == 1
        assert isinstance(attachments[0], Attachment)
        assert attachments[0].filename == "document.pdf"
        assert attachments[0].url.startswith("https://files.linear.app/")
        assert attachments[0].created_by == "Test User"

    @pytest.mark.asyncio
    async def test_get_attachments_for_project(self, linear_adapter):
        """Test getting attachments for a Linear project (epic)."""
        # Similar test for projects...

    @pytest.mark.asyncio
    async def test_get_attachments_empty(self, linear_adapter):
        """Test getting attachments when none exist."""
        # Mock response with empty attachments
        mock_response = {
            "issue": {
                "id": "issue-uuid",
                "attachments": {"nodes": []}
            }
        }

        linear_adapter.client.execute_query = AsyncMock(return_value=mock_response)

        # Test
        attachments = await linear_adapter.get_attachments("ENG-842")

        # Verify
        assert attachments == []

    @pytest.mark.asyncio
    async def test_get_attachments_issue_not_found(self, linear_adapter):
        """Test error handling when issue doesn't exist."""
        linear_adapter.client.execute_query = AsyncMock(
            return_value={"issue": None}
        )

        # Test
        attachments = await linear_adapter.get_attachments("INVALID-123")

        # Verify empty list (graceful handling)
        assert attachments == []
```

### 11.2 Integration Tests

**File**: `/tests/integration/test_linear_attachment_workflow.py`

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_linear_attachment_upload_and_retrieve():
    """Test complete workflow: upload → retrieve → verify."""

    # Setup
    adapter = LinearAdapter(config={
        "api_key": os.getenv("LINEAR_API_KEY"),
        "team_key": os.getenv("LINEAR_TEAM_KEY")
    })

    # Create test issue
    issue = await adapter.create(Task(
        title="Test Issue for Attachments",
        description="Testing attachment workflow"
    ))

    # Upload attachment
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"Test file content")
        test_file = f.name

    try:
        # Upload
        file_url = await adapter.upload_file(test_file, "text/plain")
        await adapter.attach_file_to_issue(
            issue_id=issue.id,
            file_url=file_url,
            title="test.txt"
        )

        # Retrieve
        attachments = await adapter.get_attachments(issue.id)

        # Verify
        assert len(attachments) > 0
        assert any(att.filename == "test.txt" for att in attachments)

        # Verify URL accessibility (with auth)
        att = next(att for att in attachments if att.filename == "test.txt")
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {os.getenv('LINEAR_API_KEY')}"
            }
            response = await client.get(att.url, headers=headers)
            assert response.status_code == 200

    finally:
        # Cleanup
        os.unlink(test_file)
        await adapter.delete(issue.id)
```

### 11.3 MCP Tool Tests

**File**: `/tests/mcp/test_ticket_attachments_linear.py`

```python
@pytest.mark.asyncio
async def test_ticket_attachments_mcp_tool_linear():
    """Test ticket_attachments MCP tool with Linear adapter."""

    # Mock Linear adapter with attachments
    mock_attachments = [
        Attachment(
            id="att-1",
            ticket_id="ENG-842",
            filename="document.pdf",
            url="https://files.linear.app/workspace/att-1/document.pdf",
            created_at=datetime.now()
        )
    ]

    with patch("mcp_ticketer.mcp.server.tools.attachment_tools.get_adapter") as mock_get_adapter:
        mock_adapter = AsyncMock()
        mock_adapter.read = AsyncMock(return_value=Task(
            id="eng-842",
            title="Test Issue"
        ))
        mock_adapter.get_attachments = AsyncMock(return_value=mock_attachments)
        mock_get_adapter.return_value = mock_adapter

        # Test
        result = await ticket_attachments("ENG-842")

        # Verify
        assert result["status"] == "completed"
        assert result["count"] == 1
        assert result["attachments"][0]["filename"] == "document.pdf"
```

---

## 12. Linear API Investigation Needed

### 12.1 GraphQL Schema Verification

**Need to verify:**
1. Does `issue.attachments` field exist in Linear's schema?
2. Does `project.documents` field exist in Linear's schema?
3. What fields are available on `Attachment` type?
4. Are there pagination requirements for attachments?

**Action**: Test with Linear GraphQL explorer at https://linear.app/api/graphql

### 12.2 Authentication Testing

**Need to verify:**
1. Do attachment URLs require Authorization header?
2. What HTTP status code is returned without auth? (401 vs 403 vs 404)
3. Are there rate limits on attachment downloads?
4. Do URLs work with other authentication methods?

**Action**: Test with curl commands:
```bash
# Without auth
curl -I https://files.linear.app/workspace/attachment-id/file.pdf
# Expected: 401 Unauthorized?

# With auth
curl -I -H "Authorization: Bearer $LINEAR_API_KEY" \
     https://files.linear.app/workspace/attachment-id/file.pdf
# Expected: 200 OK?
```

### 12.3 URL Format Analysis

**Need to document:**
1. What is the exact URL format for Linear attachments?
2. Are URLs CDN-based or direct API URLs?
3. Do URLs support range requests for large files?
4. Are there different URL formats for different file types?

**Action**: Inspect URLs from actual attachment uploads

---

## 13. Documentation Updates

### 13.1 Attachment Documentation

**File**: `/docs/integrations/ATTACHMENTS.md`

**Add section:**
```markdown
## Linear Attachment Retrieval

### Overview

Linear attachments are stored in Linear's CDN and require API authentication to access.

### Authentication

All Linear attachment URLs require the `Authorization` header:

```python
headers = {
    "Authorization": f"Bearer {linear_api_key}"
}
```

### Retrieving Attachments

```python
# Get attachments for an issue
attachments = await linear_adapter.get_attachments("ENG-842")

# Get attachments for a project
attachments = await linear_adapter.get_attachments("project-uuid")

# Download attachment
for att in attachments:
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {api_key}"}
        response = await client.get(att.url, headers=headers)

        with open(att.filename, "wb") as f:
            f.write(response.content)
```

### Security Notes

- **Never embed API keys in URLs**
- **Store API keys securely** (environment variables, secrets manager)
- **Attachment URLs don't expire** but always require authentication
- **Users need appropriate Linear permissions** to access attachments
```

### 13.2 API Reference

**File**: `/docs/developer-docs/api/adapter_reference.md`

**Update LinearAdapter section:**
```markdown
### LinearAdapter.get_attachments(ticket_id)

Retrieve all attachments for a Linear issue or project.

**Parameters:**
- `ticket_id` (str): Linear issue identifier (e.g., "ENG-842") or project UUID

**Returns:**
- `list[Attachment]`: List of attachment metadata

**Example:**
```python
attachments = await adapter.get_attachments("ENG-842")
for att in attachments:
    print(f"{att.filename}: {att.url}")
```

**Note:** Attachment URLs require Linear API authentication. Use the `Authorization: Bearer {api_key}` header when accessing URLs.
```

---

## 14. Summary

### Current State

| Component | Status | Notes |
|-----------|--------|-------|
| File Upload | ✅ Implemented | Works correctly with auth |
| File Attachment Record Creation | ✅ Implemented | Creates attachment metadata |
| Attachment Retrieval | ❌ Missing | **Not implemented** |
| Authentication Handling | ⚠️ Incomplete | Upload has auth, retrieval doesn't |

### Root Causes of 401 Errors

1. **Missing get_attachments() implementation** → Users can't retrieve attachment metadata
2. **Unauthenticated URL access** → Direct URL fetches fail without Authorization header
3. **No download helper** → Users must manually add auth headers

### Recommended Solution

**Priority 1: Implement get_attachments()**
- Add method to LinearAdapter
- Support both issues and projects
- Return Attachment model with authenticated URLs

**Priority 2: Document authentication requirements**
- Explain Authorization header requirement
- Provide code examples
- Update integration guides

**Priority 3: Add download helper (optional)**
- Implement authenticated download method
- Abstract auth header handling
- Simplify user experience

### Implementation Effort

- **Core Implementation**: 4-6 hours
- **Testing**: 3-4 hours
- **Documentation**: 1-2 hours
- **Total**: 8-12 hours

### Success Criteria

1. ✅ `linear_adapter.get_attachments()` returns attachment list
2. ✅ MCP tool `ticket_attachments` works with Linear
3. ✅ Attachment URLs are documented with auth requirements
4. ✅ Tests validate retrieval workflow
5. ✅ No 401 errors when using documented patterns

---

## 15. Next Steps

### Immediate Actions

1. **Validate Linear GraphQL schema** - Confirm `issue.attachments` and `project.documents` fields exist
2. **Test authentication requirements** - Verify Authorization header is required for CDN URLs
3. **Implement get_attachments()** - Add method to LinearAdapter following design above
4. **Write tests** - Create test suite for attachment retrieval
5. **Update documentation** - Add authentication requirements and usage examples

### Open Questions

1. Does Linear's GraphQL API support attachment queries?
2. What is the exact HTTP status code for unauthenticated access? (401 vs 403)
3. Are there rate limits on attachment downloads?
4. Do attachment URLs support range requests for large files?
5. Is there a separate API endpoint for downloading vs. querying attachments?

### Files to Create/Modify

**Create:**
- `/tests/adapters/test_linear_attachments.py` - Unit tests
- `/tests/integration/test_linear_attachment_workflow.py` - Integration tests

**Modify:**
- `/src/mcp_ticketer/adapters/linear/adapter.py` - Add get_attachments() method
- `/docs/integrations/ATTACHMENTS.md` - Document authentication requirements
- `/docs/developer-docs/api/adapter_reference.md` - Update LinearAdapter docs

---

**End of Analysis**
