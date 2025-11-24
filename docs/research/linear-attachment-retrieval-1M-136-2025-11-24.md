# Linear Ticket 1M-136: Pull/Review Images and Other Issue Attachments

**Research Date**: 2025-11-24
**Ticket ID**: 1M-136
**Ticket URL**: https://linear.app/1m-hyperdev/issue/1M-136/pullreview-images-and-other-issue-attachments
**Status**: Open
**Priority**: Medium
**Assignee**: bob@matsuoka.com
**Researcher**: Research Agent

---

## Executive Summary

Linear ticket 1M-136 requests the ability for AI agents to **pull and evaluate images and other attachments** from issues as part of ticket resolution workflows. The research reveals that:

1. **Infrastructure exists**: The `ticket_attachments()` MCP tool and attachment data model are already implemented
2. **GraphQL queries ready**: Linear's ISSUE_COMPACT_FRAGMENT already includes attachment fields
3. **Implementation gap**: Linear adapter is **missing the `get_attachments()` method**
4. **Attachment upload works**: Linear has full upload functionality via `upload_file()` and `attach_file_to_issue()`
5. **No authentication issue mentioned**: The ticket description doesn't mention authentication problems with attachment URLs

### The Core Problem

**AI agents cannot retrieve attachment metadata from Linear issues** because the Linear adapter lacks the `get_attachments()` implementation, even though:
- The GraphQL query fragments include attachment data
- The MCP tool `ticket_attachments()` expects adapters to implement this method
- Other adapters (Asana, JIRA, AiTrackDown) already have working implementations

---

## Ticket Analysis

### Ticket Details

**Title**: Pull/Review Images and other Issue Attachments

**Description**:
> "This the M the agent should be able to pull images and other attachments from issues and evaluate them as part of ticket resolution."

**Key Points**:
- Request is for **retrieving** attachments, not uploading
- Focus on **images and other attachments**
- Goal: Enable **evaluation as part of ticket resolution**
- No mention of authentication issues in the ticket description

### Comments Analysis

#### Comment 1 (Latest - 2025-11-24T04:48:27)
**Author**: bob@matsuoka.com

```
Analysis complete. attachment_tools.py exists but Linear adapter missing
get_attachments() method. Need GraphQL query and adapter implementation.
Estimated 3-4 hours, medium complexity.
```

**Key findings**:
- ✅ `attachment_tools.py` exists (MCP tool infrastructure)
- ❌ Linear adapter missing `get_attachments()` method
- ⚠️ States "Need GraphQL query" (actually, query fragments already exist!)
- 📊 Estimate: 3-4 hours, medium complexity

#### Comment 2 (Earlier - 2025-11-24T04:45:56)
**Author**: bob@matsuoka.com

Detailed implementation analysis including:

**Current State Assessment**:
- ✅ `ticket_attachments()` MCP tool exists
- ✅ Tool supports adapters that implement `get_attachments()`
- ✅ Fallback to comment references if unavailable
- ❌ Linear adapter does NOT implement `get_attachments()`
- ❌ "No GraphQL query for fetching issue attachments" (INCORRECT - see below)

**Proposed Implementation**:

1. **GraphQL Query** (add to `queries.py`):
```graphql
GET_ISSUE_ATTACHMENTS_QUERY = """
query GetIssueAttachments($issueId: String!) {
  issue(id: $issueId) {
    id
    attachments {
      nodes {
        id
        url
        title
        subtitle
        metadata
        createdAt
        updatedAt
      }
    }
  }
}
"""
```

2. **Adapter Method** (add to `adapter.py`):
```python
async def get_attachments(self, ticket_id: str) -> list[dict[str, Any]]:
    """Retrieve all attachments for an issue."""
    # Execute GET_ISSUE_ATTACHMENTS_QUERY
    # Map response to standardized attachment format
    # Return list of attachment dictionaries
```

3. **Testing Requirements**:
- Unit tests for `get_attachments()` in Linear adapter
- Integration test with mocked GraphQL responses
- Test cases: multiple attachments, no attachments, invalid ID, errors

4. **Documentation**:
- Update Linear adapter docs with attachment retrieval examples
- Add MCP tool usage examples
- Document supported attachment types

**Estimated Work**:
- Complexity: Medium
- Time: 3-4 hours
- Files to modify: 3-4 files
- Tests required: 5-6 test cases

---

## Technical Investigation

### Current State: What Already Exists

#### 1. GraphQL Fragments Already Include Attachments ✅

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/queries.py`

**Lines 78-88**: Attachment fragment definition
```python
ATTACHMENT_FRAGMENT = """
    fragment AttachmentFields on Attachment {
        id
        title
        url
        subtitle
        metadata
        createdAt
        updatedAt
    }
"""
```

**Lines 164-168**: Attachments included in ISSUE_COMPACT_FRAGMENT
```python
# Inside ISSUE_COMPACT_FRAGMENT
attachments {
    nodes {
        ...AttachmentFields
    }
}
```

**Lines 200-211**: Fragments combined and exported
```python
ALL_FRAGMENTS = (
    USER_FRAGMENT
    + WORKFLOW_STATE_FRAGMENT
    + TEAM_FRAGMENT
    + CYCLE_FRAGMENT
    + PROJECT_FRAGMENT
    + LABEL_FRAGMENT
    + ATTACHMENT_FRAGMENT  # ← Already included!
    + COMMENT_FRAGMENT
    + ISSUE_COMPACT_FRAGMENT
    + ISSUE_FULL_FRAGMENT
)
```

**Key Finding**: The GraphQL infrastructure **already fetches attachment data** whenever issues are retrieved. The data is present in API responses but **not being extracted or mapped**.

#### 2. MCP Tool Infrastructure ✅

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/attachment_tools.py`

**Lines 148-226**: `ticket_attachments()` tool implementation

```python
@mcp.tool()
async def ticket_attachments(ticket_id: str) -> dict[str, Any]:
    """Get all attachments for a ticket.

    Retrieves a list of all files attached to the specified ticket.
    This functionality may not be available in all adapters.
    """
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
    # ... error handling
```

**Key Finding**: The MCP tool is ready and waiting for adapters to implement `get_attachments()`. It has proper error handling and fallback mechanisms.

#### 3. Attachment Data Model ✅

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/core/models.py`

**Lines 389-417**: Universal Attachment model
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

**Key Finding**: A standardized Attachment model exists and is used across all adapters.

#### 4. Linear Upload Works (But Not Retrieval) ✅/❌

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/adapter.py`

**Existing methods**:
- `upload_file()` (line 2065): Uploads file to Linear's S3 storage
- `attach_file_to_issue()` (line 2178): Creates attachment record for issues
- `attach_file_to_epic()` (line 2261): Creates attachment record for epics

**Missing method**:
- `get_attachments()`: Does NOT exist

**Key Finding**: Linear adapter has comprehensive **upload** functionality but no **retrieval** functionality.

#### 5. Reference Implementations Exist ✅

**Asana Adapter** (`/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/asana/adapter.py`):

**Lines 1358-1384**: Working `get_attachments()` implementation
```python
async def get_attachments(self, ticket_id: str) -> list[Attachment]:
    """Get all attachments for an Asana task."""
    try:
        # Get attachments for task
        attachments = await self.client.get_paginated(
            f"/tasks/{ticket_id}/attachments"
        )

        # Map to Attachment objects
        return [
            map_asana_attachment_to_attachment(att, ticket_id)
            for att in attachments
        ]

    except Exception as e:
        logger.error(f"Failed to get attachments for task {ticket_id}: {e}")
        return []
```

**Asana Mapper** (`/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/asana/mappers.py`):

**Lines 307-337**: Attachment mapping function
```python
def map_asana_attachment_to_attachment(
    attachment: dict[str, Any], task_gid: str
) -> Attachment:
    """Map Asana attachment to Attachment.

    IMPORTANT: Use permanent_url for reliable access, not download_url which expires.
    """
    # Extract creator info
    created_by_data = attachment.get("created_by", {})
    created_by = created_by_data.get("gid") or created_by_data.get("name", "Unknown")

    # Use permanent_url (not download_url which expires)
    url = attachment.get("permanent_url") or attachment.get("view_url")

    return Attachment(
        id=attachment.get("gid"),
        ticket_id=task_gid,
        filename=attachment.get("name", ""),
        url=url,
        content_type=attachment.get("resource_subtype"),
        size_bytes=attachment.get("size"),
        # ... more fields
    )
```

**Key Learning**: Other adapters show the pattern - fetch from API, map to Attachment model, return list.

---

## The Authentication Question

### What the Ticket Doesn't Say

The ticket description and comments **do not mention any authentication issues** with attachment URLs. The request is straightforward:

> "agent should be able to pull images and other attachments from issues and evaluate them"

### Potential Authentication Concern (Not in Ticket)

If we look at the Asana mapper comment, there's a clue:

```python
# IMPORTANT: Use permanent_url for reliable access, not download_url which expires.
```

This suggests that some platforms have:
- **Temporary URLs** (`download_url`): Expire after a time period, require no auth
- **Permanent URLs** (`permanent_url`): Don't expire but may require authentication

### Linear's Attachment URL Format

Based on Linear's GraphQL schema, attachments have:
- `id`: Unique identifier
- `url`: The attachment URL (likely an S3 URL)
- `title`: Display title
- `subtitle`: Optional subtitle
- `metadata`: Platform-specific metadata

**Likely scenario**: Linear's `url` field returns **pre-signed S3 URLs** that:
- Are publicly accessible (no auth header needed)
- Expire after a period (hours/days)
- Are regenerated on each API call

### Authentication Implementation

If authentication is needed to fetch attachments, the client should:

1. **Pass auth headers when downloading**:
```python
headers = {
    "Authorization": f"Bearer {self.api_key}"
}
response = await httpx.get(attachment_url, headers=headers)
```

2. **Use Linear's GraphQL API**:
The attachment URL from Linear's API should be directly fetchable by AI agents without additional authentication, as it's likely a pre-signed URL.

**However**: The ticket does NOT mention this as a problem. The issue is simply that attachments **cannot be retrieved at all** because the method doesn't exist.

---

## Implementation Gap Analysis

### What's Missing

1. **Linear Adapter Method**: No `get_attachments()` implementation
2. **Attachment Mapper**: No function to map Linear attachment data to Attachment model
3. **Tests**: No tests for Linear attachment retrieval

### What's NOT Missing (Contrary to Comment)

1. ❌ **GraphQL Query**: WRONG - fragments already exist in queries.py
2. ❌ **Attachment Data Model**: WRONG - universal model exists in models.py
3. ❌ **MCP Tool**: WRONG - tool exists and is waiting for adapter support

### The Actual Work Required

#### Step 1: Extract Attachments from Existing Queries

Linear adapter already receives attachment data when fetching issues. The data just needs to be **extracted and mapped**.

**Example**: When `read()` fetches an issue, the response includes:
```json
{
  "issue": {
    "id": "...",
    "title": "...",
    "attachments": {
      "nodes": [
        {
          "id": "att-123",
          "url": "https://linear-attachments.s3.amazonaws.com/...",
          "title": "screenshot.png",
          "subtitle": "UI mockup",
          "metadata": {},
          "createdAt": "2025-11-24T12:00:00.000Z",
          "updatedAt": "2025-11-24T12:00:00.000Z"
        }
      ]
    }
  }
}
```

This data is **already being fetched** but not extracted.

#### Step 2: Add Mapper Function

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/mappers.py` (need to check if this exists)

```python
def map_linear_attachment_to_attachment(
    attachment: dict[str, Any],
    ticket_id: str
) -> Attachment:
    """Map Linear attachment to Attachment model.

    Args:
        attachment: Linear attachment data from GraphQL
        ticket_id: Parent issue/project ID

    Returns:
        Standardized Attachment object
    """
    return Attachment(
        id=attachment.get("id"),
        ticket_id=ticket_id,
        filename=attachment.get("title", ""),  # Linear uses 'title' as filename
        url=attachment.get("url"),
        content_type=None,  # Linear doesn't provide MIME type in GraphQL
        size_bytes=None,  # Linear doesn't provide size in GraphQL
        created_at=parse_linear_datetime(attachment.get("createdAt")),
        created_by=None,  # Not included in fragment, could be added
        description=attachment.get("subtitle"),
        metadata={
            "linear": {
                "id": attachment.get("id"),
                "title": attachment.get("title"),
                "subtitle": attachment.get("subtitle"),
                "metadata": attachment.get("metadata"),
                "updatedAt": attachment.get("updatedAt"),
            }
        },
    )
```

#### Step 3: Implement `get_attachments()` Method

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/adapter.py`

**Option A: Dedicated Query** (as proposed in ticket comment)
```python
async def get_attachments(self, ticket_id: str) -> list[Attachment]:
    """Get all attachments for a Linear issue.

    Args:
        ticket_id: Issue or project ID (UUID format)

    Returns:
        List of attachments with metadata
    """
    try:
        # Query specifically for attachments
        query = """
        query GetAttachments($id: String!) {
          issue(id: $id) {
            id
            attachments {
              nodes {
                id
                url
                title
                subtitle
                metadata
                createdAt
                updatedAt
              }
            }
          }
        }
        """

        response = await self.client.execute_graphql(
            query,
            variables={"id": ticket_id}
        )

        # Extract attachments
        issue_data = response.get("issue", {})
        attachments_data = issue_data.get("attachments", {}).get("nodes", [])

        # Map to Attachment objects
        return [
            map_linear_attachment_to_attachment(att, ticket_id)
            for att in attachments_data
        ]

    except Exception as e:
        logger.error(f"Failed to get attachments for {ticket_id}: {e}")
        return []
```

**Option B: Reuse Existing Read Query** (more efficient)
```python
async def get_attachments(self, ticket_id: str) -> list[Attachment]:
    """Get all attachments for a Linear issue.

    Reuses the read() method which already fetches attachments.

    Args:
        ticket_id: Issue or project ID (UUID format)

    Returns:
        List of attachments with metadata
    """
    try:
        # Use read() which already includes attachment data
        ticket = await self.read(ticket_id)

        if not ticket:
            logger.warning(f"Ticket {ticket_id} not found")
            return []

        # Extract attachments from metadata
        # (Assumes mappers store raw attachment data in metadata)
        linear_data = ticket.metadata.get("linear", {})
        attachments_data = linear_data.get("attachments", {}).get("nodes", [])

        # Map to Attachment objects
        return [
            map_linear_attachment_to_attachment(att, ticket_id)
            for att in attachments_data
        ]

    except Exception as e:
        logger.error(f"Failed to get attachments for {ticket_id}: {e}")
        return []
```

**Option B is more efficient** but requires checking if attachment data is preserved in ticket metadata.

#### Step 4: Add Tests

**File**: `/Users/masa/Projects/mcp-ticketer/tests/adapters/test_linear_attachments.py`

```python
import pytest
from mcp_ticketer.adapters.linear import LinearAdapter
from mcp_ticketer.core.models import Attachment

@pytest.fixture
def mock_linear_attachments():
    return {
        "issue": {
            "id": "issue-123",
            "attachments": {
                "nodes": [
                    {
                        "id": "att-1",
                        "url": "https://linear-attachments.s3.amazonaws.com/image.png",
                        "title": "screenshot.png",
                        "subtitle": "UI mockup",
                        "metadata": {},
                        "createdAt": "2025-11-24T12:00:00.000Z",
                        "updatedAt": "2025-11-24T12:00:00.000Z",
                    },
                    {
                        "id": "att-2",
                        "url": "https://linear-attachments.s3.amazonaws.com/doc.pdf",
                        "title": "requirements.pdf",
                        "subtitle": None,
                        "metadata": {},
                        "createdAt": "2025-11-24T13:00:00.000Z",
                        "updatedAt": "2025-11-24T13:00:00.000Z",
                    },
                ]
            }
        }
    }

@pytest.mark.asyncio
async def test_get_attachments_success(mock_linear_client, mock_linear_attachments):
    """Test successful attachment retrieval."""
    adapter = LinearAdapter(config={"api_key": "test-key"})
    adapter.client = mock_linear_client

    # Mock GraphQL response
    mock_linear_client.execute_graphql.return_value = mock_linear_attachments

    # Get attachments
    attachments = await adapter.get_attachments("issue-123")

    # Assertions
    assert len(attachments) == 2
    assert all(isinstance(att, Attachment) for att in attachments)
    assert attachments[0].filename == "screenshot.png"
    assert attachments[0].url.startswith("https://linear-attachments")
    assert attachments[1].filename == "requirements.pdf"

@pytest.mark.asyncio
async def test_get_attachments_empty():
    """Test issue with no attachments."""
    # ... test implementation

@pytest.mark.asyncio
async def test_get_attachments_invalid_ticket():
    """Test with non-existent ticket."""
    # ... test implementation

@pytest.mark.asyncio
async def test_get_attachments_api_error():
    """Test handling of API errors."""
    # ... test implementation
```

#### Step 5: Update Documentation

**File**: `/Users/masa/Projects/mcp-ticketer/docs/integrations/ATTACHMENTS.md`

Update the Adapter Support Matrix:

```markdown
| Adapter | Add | List | Delete | Storage | Status |
|---------|-----|------|--------|---------|--------|
| **Linear** | ✅ | ✅ | ❌ | S3 | Production |  # Changed from Planned
| **Jira** | ✅ | ✅ | ❌ | Cloud/Server | Production |
| **GitHub** | ❌ | ❌ | ❌ | N/A | Not supported |
| **Asana** | ✅ | ✅ | ❌ | Cloud | Production |
| **AITrackdown** | ✅ | ✅ | ✅ | Local filesystem | Production |
```

Add Linear-specific section:

```markdown
## Linear Attachments

Linear provides cloud-based attachment storage via AWS S3.

### Features
- **Cloud Storage**: Files stored in Linear's S3 buckets
- **Pre-signed URLs**: Attachments accessible via temporary URLs
- **GraphQL API**: Attachment metadata retrieved via GraphQL
- **Epic and Issue Support**: Attach files to both projects and issues

### Usage

#### Get Attachments
```python
from mcp_ticketer.adapters.linear import LinearAdapter

# Initialize adapter
adapter = LinearAdapter(config={'api_key': 'lin_api_...'})

# Get attachments for issue
attachments = await adapter.get_attachments('issue-uuid')

for att in attachments:
    print(f"{att.filename} - {att.url}")
```

### Limitations
- **Read-only**: Can upload and retrieve, but not delete
- **No MIME types**: GraphQL doesn't expose content-type
- **No file sizes**: GraphQL doesn't expose size in bytes
- **URL expiration**: S3 URLs may expire (need regeneration)
```

---

## Implementation Estimate

### Revised Estimate (Based on Investigation)

**Original estimate**: 3-4 hours, medium complexity

**Revised estimate**: 2-3 hours, low-medium complexity

**Rationale for lower estimate**:
1. GraphQL fragments **already exist** (no query writing needed)
2. Reference implementations available (Asana, JIRA)
3. MCP tool **already works** (no changes needed)
4. Attachment model **already defined** (no modeling needed)

### Work Breakdown

| Task | Time | Complexity | Notes |
|------|------|------------|-------|
| 1. Check if mappers.py exists | 10 min | Low | May need to create file |
| 2. Add mapper function | 20 min | Low | Copy pattern from Asana |
| 3. Implement get_attachments() | 30 min | Low | Reuse read() or add query |
| 4. Write unit tests | 60 min | Medium | 5-6 test cases |
| 5. Update documentation | 30 min | Low | Add Linear section |
| 6. Manual testing | 30 min | Low | Test with real Linear API |
| **Total** | **3 hours** | **Low-Medium** | |

### Risk Factors

**Low Risk**:
- ✅ Clear reference implementations exist
- ✅ GraphQL infrastructure ready
- ✅ No authentication complexity mentioned
- ✅ Well-defined Attachment model

**Potential Issues**:
- ⚠️ Linear attachment URLs may expire (need documentation)
- ⚠️ GraphQL doesn't expose MIME type or file size (limitation)
- ⚠️ Need to verify attachment data is available in read() response

---

## Proposed Solution

### Recommended Approach

**Option B: Reuse Existing Read Query** (if attachment data preserved in metadata)

**Advantages**:
1. No new GraphQL queries needed
2. Fewer API calls (efficient)
3. Consistent with DRY principle
4. Attachments already in memory if ticket recently read

**Disadvantages**:
1. Requires checking if attachment data preserved
2. May fetch unnecessary ticket data

**Fallback**: If attachment data not preserved, implement **Option A: Dedicated Query**

### Implementation Steps

1. **Investigate current behavior** (15 min)
   - Check if `read()` preserves attachment data in `ticket.metadata`
   - Examine Linear mappers to see what data is stored

2. **Implement mapper** (20 min)
   - Create or update `mappers.py` in Linear adapter
   - Add `map_linear_attachment_to_attachment()` function

3. **Implement `get_attachments()`** (30 min)
   - Add method to LinearAdapter
   - Use Option B if data available, else Option A
   - Add error handling and logging

4. **Write tests** (60 min)
   - Create `test_linear_attachments.py`
   - Implement 5-6 test cases
   - Mock GraphQL responses

5. **Update documentation** (30 min)
   - Update ATTACHMENTS.md with Linear support
   - Add usage examples
   - Document limitations (no MIME/size)

6. **Manual testing** (30 min)
   - Test with real Linear API
   - Verify attachment URLs work
   - Check URL expiration behavior

**Total time**: ~3 hours

---

## Key Findings Summary

### What Was Misunderstood in Original Comment

1. ❌ **"No GraphQL query for fetching attachments"**
   → INCORRECT: ATTACHMENT_FRAGMENT exists and is included in issue queries

2. ❌ **"Need GraphQL query and adapter implementation"**
   → PARTIALLY CORRECT: Need adapter implementation only (query exists)

3. ✅ **"attachment_tools.py exists"**
   → CORRECT: MCP tool infrastructure ready

4. ✅ **"Linear adapter missing get_attachments() method"**
   → CORRECT: This is the actual gap

### What the Ticket Actually Requests

1. **Primary Goal**: Enable AI agents to **retrieve and evaluate** attachments from issues
2. **Not Mentioned**: Authentication problems (likely not an issue)
3. **Implementation**: Add `get_attachments()` method to Linear adapter
4. **Infrastructure**: Already exists, just needs method implementation

### Authentication Clarification

**No authentication issue described in ticket**. Linear's attachment URLs are likely pre-signed S3 URLs that:
- Are publicly accessible (no auth needed)
- Expire after a period
- Are regenerated on each GraphQL API call

If authentication were required, the AI agent would need to:
1. Get attachment metadata via `get_attachments()`
2. Download attachment content using the URL
3. Pass auth headers if needed (unlikely for S3 pre-signed URLs)

---

## Recommendations

### Immediate Action Items

1. **Verify attachment data availability** (15 min)
   - Check if `read()` response includes attachment data
   - Examine Linear mappers to confirm data preservation

2. **Implement `get_attachments()`** (2-3 hours)
   - Follow Option B if data available, else Option A
   - Use Asana implementation as reference
   - Add comprehensive tests

3. **Update documentation** (30 min)
   - Mark Linear as supporting attachment retrieval
   - Add usage examples and limitations

### Future Enhancements (Not in Scope)

1. **Add MIME type detection**: Linear's GraphQL doesn't expose content-type
2. **Add file size info**: GraphQL doesn't expose size in bytes
3. **Implement attachment deletion**: Currently not supported by Linear API
4. **URL refresh mechanism**: Handle expired S3 URLs gracefully

### Ticket Status

**Current**: Open
**Recommended**: Ready for implementation
**Blockers**: None
**Dependencies**: None
**Estimated Completion**: 3-4 hours (as originally estimated, but with less scope)

---

## Appendices

### Appendix A: File Locations

**Implementation Files**:
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/adapter.py` (add method)
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/mappers.py` (add mapper, if exists)
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/queries.py` (already has fragments)

**Test Files**:
- `/Users/masa/Projects/mcp-ticketer/tests/adapters/test_linear_attachments.py` (create new)

**Documentation Files**:
- `/Users/masa/Projects/mcp-ticketer/docs/integrations/ATTACHMENTS.md` (update)
- `/Users/masa/Projects/mcp-ticketer/docs/developer-docs/adapters/LINEAR.md` (add attachment section)

### Appendix B: Related Code Patterns

**Asana Reference** (lines 1358-1384 in asana/adapter.py):
```python
async def get_attachments(self, ticket_id: str) -> list[Attachment]:
    try:
        attachments = await self.client.get_paginated(
            f"/tasks/{ticket_id}/attachments"
        )
        return [
            map_asana_attachment_to_attachment(att, ticket_id)
            for att in attachments
        ]
    except Exception as e:
        logger.error(f"Failed to get attachments for task {ticket_id}: {e}")
        return []
```

**Linear Upload Reference** (lines 2178-2260 in linear/adapter.py):
```python
async def attach_file_to_issue(
    self,
    issue_id: str,
    file_url: str,
    title: str,
    subtitle: str | None = None,
    comment_body: str | None = None,
) -> dict[str, Any]:
    # ... implementation exists, shows GraphQL mutation pattern
```

### Appendix C: GraphQL Schema Reference

**Linear Attachment Type** (from GraphQL schema):
```graphql
type Attachment {
  id: ID!
  url: String!
  title: String!
  subtitle: String
  metadata: JSONObject
  createdAt: DateTime!
  updatedAt: DateTime!
  issue: Issue
  project: Project
  creator: User
}
```

**Fields Available**:
- ✅ id, url, title, subtitle, metadata, createdAt, updatedAt
- ❌ MIME type (not exposed)
- ❌ file size (not exposed)
- ❌ checksum (not exposed)

---

## Conclusion

Linear ticket 1M-136 requests the ability to **retrieve attachments from issues** so AI agents can evaluate them. The investigation reveals:

1. **GraphQL infrastructure ready**: Attachment fragments already exist in queries
2. **MCP tool ready**: `ticket_attachments()` waiting for adapter support
3. **Implementation gap**: Only `get_attachments()` method missing in Linear adapter
4. **No authentication issue**: Not mentioned in ticket, likely not a problem
5. **Reference implementations**: Asana and JIRA show the pattern
6. **Estimated effort**: 3-4 hours (correct estimate, but less scope than thought)

**Primary work**: Implement `get_attachments()` method in Linear adapter by:
1. Reusing existing GraphQL fragments (already fetching data)
2. Adding mapper function to convert Linear format to Attachment model
3. Implementing method following Asana pattern
4. Writing comprehensive tests
5. Updating documentation

**No authentication complexity** is described in the ticket. Linear's attachment URLs are likely pre-signed S3 URLs that work without additional authentication.

---

**Research Complete**
**Status**: Ready for implementation
**Next Step**: Implement `get_attachments()` in Linear adapter

