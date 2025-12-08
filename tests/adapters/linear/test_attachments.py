"""Unit tests for Linear adapter get_attachments() method."""

from unittest.mock import AsyncMock, Mock

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter
from mcp_ticketer.core.models import Attachment


@pytest.fixture
def mock_linear_client():
    """Create a mock Linear GraphQL client."""
    client = Mock()
    client.execute_query = AsyncMock()
    client.test_connection = AsyncMock(return_value=True)
    return client


@pytest.fixture
def linear_adapter(mock_linear_client):
    """Create LinearAdapter with mocked client."""
    config = {
        "api_key": "lin_api_test_key_12345",
        "team_key": "TEST",
    }
    adapter = LinearAdapter(config)
    adapter.client = mock_linear_client
    adapter._initialized = True
    adapter._workflow_states = {
        "unstarted": {"id": "state-1", "type": "unstarted", "position": 0}
    }
    adapter._labels_cache = []
    return adapter


@pytest.mark.asyncio
async def test_get_attachments_for_issue_success(linear_adapter, mock_linear_client):
    """Test successful attachment retrieval for an issue."""
    # Mock issue UUID resolution
    linear_adapter._resolve_issue_id = AsyncMock(return_value="issue-uuid-12345")

    # Mock GraphQL response with attachments
    mock_linear_client.execute_query.return_value = {
        "issue": {
            "id": "issue-uuid-12345",
            "identifier": "TEST-123",
            "attachments": {
                "nodes": [
                    {
                        "id": "att-1",
                        "title": "screenshot.png",
                        "url": "https://files.linear.app/workspace/att-1/screenshot.png",
                        "subtitle": "UI mockup",
                        "metadata": {},
                        "createdAt": "2025-11-24T12:00:00.000Z",
                        "updatedAt": "2025-11-24T12:00:00.000Z",
                    },
                    {
                        "id": "att-2",
                        "title": "document.pdf",
                        "url": "https://files.linear.app/workspace/att-2/document.pdf",
                        "subtitle": None,
                        "metadata": {},
                        "createdAt": "2025-11-24T13:00:00.000Z",
                        "updatedAt": "2025-11-24T13:00:00.000Z",
                    },
                ]
            },
        }
    }

    # Call get_attachments
    attachments = await linear_adapter.get_attachments("TEST-123")

    # Verify results
    assert len(attachments) == 2
    assert all(isinstance(att, Attachment) for att in attachments)

    # Check first attachment
    assert attachments[0].id == "att-1"
    assert attachments[0].filename == "screenshot.png"
    assert (
        attachments[0].url == "https://files.linear.app/workspace/att-1/screenshot.png"
    )
    assert attachments[0].description == "UI mockup"
    assert attachments[0].ticket_id == "TEST-123"

    # Check second attachment
    assert attachments[1].id == "att-2"
    assert attachments[1].filename == "document.pdf"
    assert attachments[1].ticket_id == "TEST-123"

    # Verify query was called correctly
    mock_linear_client.execute_query.assert_called_once()
    call_args = mock_linear_client.execute_query.call_args
    assert "GetIssueAttachments" in call_args[0][0]
    assert call_args[0][1]["issueId"] == "issue-uuid-12345"


@pytest.mark.asyncio
async def test_get_attachments_for_issue_empty(linear_adapter, mock_linear_client):
    """Test attachment retrieval for issue with no attachments."""
    linear_adapter._resolve_issue_id = AsyncMock(return_value="issue-uuid-12345")

    mock_linear_client.execute_query.return_value = {
        "issue": {
            "id": "issue-uuid-12345",
            "identifier": "TEST-123",
            "attachments": {"nodes": []},
        }
    }

    attachments = await linear_adapter.get_attachments("TEST-123")

    assert attachments == []


@pytest.mark.asyncio
async def test_get_attachments_for_project_success(linear_adapter, mock_linear_client):
    """Test successful attachment retrieval for a project."""
    # Issue resolution returns None (not an issue)
    linear_adapter._resolve_issue_id = AsyncMock(return_value=None)

    # Project resolution returns UUID
    linear_adapter._resolve_project_id = AsyncMock(return_value="project-uuid-67890")

    # Mock GraphQL response with project documents
    mock_linear_client.execute_query.return_value = {
        "project": {
            "id": "project-uuid-67890",
            "name": "Test Project",
            "documents": {
                "nodes": [
                    {
                        "id": "doc-1",
                        "title": "project-spec.pdf",
                        "url": "https://files.linear.app/workspace/doc-1/project-spec.pdf",
                        "createdAt": "2025-11-24T14:00:00.000Z",
                        "updatedAt": "2025-11-24T14:00:00.000Z",
                    }
                ]
            },
        }
    }

    # Call get_attachments with project ID
    attachments = await linear_adapter.get_attachments("project-uuid-67890")

    # Verify results
    assert len(attachments) == 1
    assert attachments[0].id == "doc-1"
    assert attachments[0].filename == "project-spec.pdf"
    assert attachments[0].ticket_id == "project-uuid-67890"

    # Verify correct query was used
    call_args = mock_linear_client.execute_query.call_args
    assert "GetProjectAttachments" in call_args[0][0]
    assert call_args[0][1]["projectId"] == "project-uuid-67890"


@pytest.mark.asyncio
async def test_get_attachments_not_found(linear_adapter, mock_linear_client):
    """Test attachment retrieval for non-existent ticket."""
    linear_adapter._resolve_issue_id = AsyncMock(return_value=None)
    linear_adapter._resolve_project_id = AsyncMock(return_value=None)

    attachments = await linear_adapter.get_attachments("INVALID-999")

    assert attachments == []


@pytest.mark.asyncio
async def test_get_attachments_api_error(linear_adapter, mock_linear_client):
    """Test error handling when API call fails."""
    linear_adapter._resolve_issue_id = AsyncMock(return_value="issue-uuid-12345")

    # Simulate API error
    mock_linear_client.execute_query.side_effect = Exception("GraphQL error")

    attachments = await linear_adapter.get_attachments("TEST-123")

    # Should return empty list on error, not raise exception
    assert attachments == []


@pytest.mark.asyncio
async def test_get_attachments_missing_credentials(linear_adapter):
    """Test that missing credentials raise ValueError."""
    # Remove API key to simulate invalid credentials
    linear_adapter.api_key = None

    with pytest.raises(ValueError, match="Linear API key is required"):
        await linear_adapter.get_attachments("TEST-123")


@pytest.mark.asyncio
async def test_attachment_metadata_preservation(linear_adapter, mock_linear_client):
    """Test that Linear-specific metadata is preserved."""
    linear_adapter._resolve_issue_id = AsyncMock(return_value="issue-uuid-12345")

    mock_linear_client.execute_query.return_value = {
        "issue": {
            "id": "issue-uuid-12345",
            "identifier": "TEST-123",
            "attachments": {
                "nodes": [
                    {
                        "id": "att-1",
                        "title": "test.png",
                        "url": "https://files.linear.app/workspace/att-1/test.png",
                        "subtitle": "Test subtitle",
                        "metadata": {"custom": "data"},
                        "createdAt": "2025-11-24T12:00:00.000Z",
                        "updatedAt": "2025-11-24T13:00:00.000Z",
                    }
                ]
            },
        }
    }

    attachments = await linear_adapter.get_attachments("TEST-123")

    assert len(attachments) == 1
    assert "linear" in attachments[0].metadata
    assert attachments[0].metadata["linear"]["id"] == "att-1"
    assert attachments[0].metadata["linear"]["subtitle"] == "Test subtitle"
    assert attachments[0].metadata["linear"]["metadata"] == {"custom": "data"}
