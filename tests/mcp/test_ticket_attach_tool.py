"""Comprehensive tests for MCP attachment tool.

Tests the attachment MCP tool endpoint including:
- Multi-tier attachment support (Linear native, adapter native, comment fallback)
- File validation and error handling
- Response format verification
- Ticket type detection (epic vs issue)
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter
from mcp_ticketer.core.models import Epic, Task, TicketType
from mcp_ticketer.mcp.server.tools.attachment_tools import attachment


class TestTicketAttachMCPTool:
    """Test suite for attachment MCP tool."""

    @pytest.fixture
    def temp_test_file(self) -> Path:
        """Create a temporary test file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test attachment content")
            return Path(f.name)

    @pytest.fixture
    def mock_linear_adapter(self) -> LinearAdapter:
        """Create a mock Linear adapter with full upload support."""
        adapter = Mock(spec=LinearAdapter)
        adapter.upload_file = AsyncMock()
        adapter.attach_file_to_issue = AsyncMock()
        adapter.attach_file_to_epic = AsyncMock()
        adapter.read = AsyncMock()
        return adapter

    @pytest.fixture
    def mock_adapter_native_only(self) -> Mock:
        """Create a mock adapter with adapter-native add_attachment support."""
        # Use spec to ensure only add_attachment is available (not Linear methods)
        adapter = Mock(spec=["read", "add_attachment", "add_comment"])
        adapter.add_attachment = AsyncMock()
        adapter.read = AsyncMock()
        return adapter

    @pytest.fixture
    def mock_adapter_comment_only(self) -> Mock:
        """Create a mock adapter with only comment support (no attachment methods)."""
        # Use spec to limit available attributes
        adapter = Mock(spec=["read", "add_comment", "get_comments"])
        adapter.read = AsyncMock()
        adapter.add_comment = AsyncMock()
        return adapter

    @pytest.mark.asyncio
    async def test_attach_file_to_issue_linear_native(
        self, mock_linear_adapter: LinearAdapter, temp_test_file: Path
    ) -> None:
        """Test attaching file to issue using Linear native upload."""
        ticket_id = "TEST-123"

        # Mock ticket read - return issue
        mock_task = Task(
            id=ticket_id,
            title="Test Issue",
            description="Test",
            ticket_type=TicketType.TASK,
        )
        mock_linear_adapter.read.return_value = mock_task

        # Mock file upload
        mock_linear_adapter.upload_file.return_value = (
            "https://linear-assets.s3.amazonaws.com/test.txt"
        )

        # Mock attachment
        mock_linear_adapter.attach_file_to_issue.return_value = {
            "id": "attachment-123",
            "title": temp_test_file.name,
            "url": "https://linear-assets.s3.amazonaws.com/test.txt",
        }

        with patch(
            "mcp_ticketer.mcp.server.tools.attachment_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await attachment(
                action="attach",
                ticket_id=ticket_id,
                file_path=str(temp_test_file),
            )

        assert result["status"] == "completed"
        assert result["ticket_id"] == ticket_id
        assert result["method"] == "linear_native_upload"
        assert "attachment" in result
        mock_linear_adapter.upload_file.assert_called_once()
        mock_linear_adapter.attach_file_to_issue.assert_called_once()

    @pytest.mark.asyncio
    async def test_attach_file_to_epic_linear_native(
        self, mock_linear_adapter: LinearAdapter, temp_test_file: Path
    ) -> None:
        """Test attaching file to epic using Linear native upload."""
        epic_id = "epic-456"

        # Mock ticket read - return epic
        mock_epic = Epic(
            id=epic_id,
            title="Test Epic",
            description="Test",
            ticket_type=TicketType.EPIC,
        )
        mock_linear_adapter.read.return_value = mock_epic

        # Mock file upload
        mock_linear_adapter.upload_file.return_value = (
            "https://linear-assets.s3.amazonaws.com/test.txt"
        )

        # Mock attachment
        mock_linear_adapter.attach_file_to_epic.return_value = {
            "id": "attachment-789",
            "title": temp_test_file.name,
            "url": "https://linear-assets.s3.amazonaws.com/test.txt",
        }

        with patch(
            "mcp_ticketer.mcp.server.tools.attachment_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await attachment(
                ticket_id=epic_id,
                file_path=str(temp_test_file),
            )

        assert result["status"] == "completed"
        assert result["method"] == "linear_native_upload"
        mock_linear_adapter.attach_file_to_epic.assert_called_once()

    @pytest.mark.asyncio
    async def test_attach_file_with_description(
        self, mock_linear_adapter: LinearAdapter, temp_test_file: Path
    ) -> None:
        """Test attaching file with description/comment."""
        ticket_id = "TEST-123"
        description = "Please review this document"

        mock_task = Task(
            id=ticket_id,
            title="Test Issue",
            description="Test",
            ticket_type=TicketType.TASK,
        )
        mock_linear_adapter.read.return_value = mock_task

        mock_linear_adapter.upload_file.return_value = (
            "https://linear-assets.s3.amazonaws.com/test.txt"
        )
        mock_linear_adapter.attach_file_to_issue.return_value = {
            "id": "attachment-123",
            "title": temp_test_file.name,
            "url": "https://linear-assets.s3.amazonaws.com/test.txt",
        }

        with patch(
            "mcp_ticketer.mcp.server.tools.attachment_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await attachment(
                action="attach",
                ticket_id=ticket_id,
                file_path=str(temp_test_file),
                description=description,
            )

        assert result["status"] == "completed"
        # Verify description was passed as comment_body
        call_kwargs = mock_linear_adapter.attach_file_to_issue.call_args[1]
        assert (
            call_kwargs.get("comment_body") == description
            or call_kwargs.get("subtitle") == description
        )

    @pytest.mark.asyncio
    async def test_attach_file_not_found(
        self, mock_linear_adapter: LinearAdapter
    ) -> None:
        """Test attaching non-existent file."""
        ticket_id = "TEST-123"
        nonexistent_file = "/nonexistent/file.txt"

        mock_task = Task(
            id=ticket_id,
            title="Test Issue",
            description="Test",
        )
        mock_linear_adapter.read.return_value = mock_task

        with patch(
            "mcp_ticketer.mcp.server.tools.attachment_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await attachment(
                action="attach",
                ticket_id=ticket_id,
                file_path=nonexistent_file,
            )

        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_attach_file_ticket_not_found(
        self, mock_linear_adapter: LinearAdapter, temp_test_file: Path
    ) -> None:
        """Test attaching file to non-existent ticket."""
        ticket_id = "INVALID-999"

        mock_linear_adapter.read.return_value = None

        with patch(
            "mcp_ticketer.mcp.server.tools.attachment_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await attachment(
                action="attach",
                ticket_id=ticket_id,
                file_path=str(temp_test_file),
            )

        assert result["status"] == "error"
        assert "not found" in result["error"].lower()
        assert ticket_id in result["error"]

    @pytest.mark.asyncio
    async def test_attach_file_adapter_native_fallback(
        self, mock_adapter_native_only: Mock, temp_test_file: Path
    ) -> None:
        """Test fallback to adapter native attach_file method."""
        ticket_id = "TEST-123"

        mock_task = Task(
            id=ticket_id,
            title="Test Issue",
            description="Test",
        )
        mock_adapter_native_only.read.return_value = mock_task

        mock_adapter_native_only.add_attachment.return_value = {
            "id": "attachment-native-123",
            "url": "https://example.com/file.txt",
        }

        with patch(
            "mcp_ticketer.mcp.server.tools.attachment_tools.get_adapter",
            return_value=mock_adapter_native_only,
        ):
            result = await attachment(
                action="attach",
                ticket_id=ticket_id,
                file_path=str(temp_test_file),
            )

        assert result["status"] == "completed"
        assert result["method"] == "adapter_native"
        mock_adapter_native_only.add_attachment.assert_called_once()

    @pytest.mark.asyncio
    async def test_attach_file_comment_fallback(
        self, mock_adapter_comment_only: Mock, temp_test_file: Path
    ) -> None:
        """Test fallback to comment with file reference."""
        ticket_id = "TEST-123"

        mock_task = Task(
            id=ticket_id,
            title="Test Issue",
            description="Test",
        )
        mock_adapter_comment_only.read.return_value = mock_task

        from mcp_ticketer.core.models import Comment

        mock_comment = Comment(
            id="comment-123",
            ticket_id=ticket_id,
            content=f"File attachment: {temp_test_file.name}",
        )
        mock_adapter_comment_only.add_comment.return_value = mock_comment

        with patch(
            "mcp_ticketer.mcp.server.tools.attachment_tools.get_adapter",
            return_value=mock_adapter_comment_only,
        ):
            result = await attachment(
                action="attach",
                ticket_id=ticket_id,
                file_path=str(temp_test_file),
            )

        assert result["status"] == "completed"
        assert result["method"] == "comment_reference"
        assert "note" in result
        mock_adapter_comment_only.add_comment.assert_called_once()

    @pytest.mark.asyncio
    async def test_attach_file_response_structure(
        self, mock_linear_adapter: LinearAdapter, temp_test_file: Path
    ) -> None:
        """Test that attachment returns proper MCP response structure."""
        ticket_id = "TEST-123"

        mock_task = Task(
            id=ticket_id,
            title="Test Issue",
            description="Test",
        )
        mock_linear_adapter.read.return_value = mock_task

        mock_linear_adapter.upload_file.return_value = (
            "https://linear-assets.s3.amazonaws.com/test.txt"
        )
        mock_linear_adapter.attach_file_to_issue.return_value = {
            "id": "attachment-123",
            "title": temp_test_file.name,
            "url": "https://linear-assets.s3.amazonaws.com/test.txt",
            "createdAt": "2025-01-15T00:00:00.000Z",
        }

        with patch(
            "mcp_ticketer.mcp.server.tools.attachment_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await attachment(
                action="attach",
                ticket_id=ticket_id,
                file_path=str(temp_test_file),
            )

        # Verify MCP response structure
        assert isinstance(result, dict)
        assert "status" in result
        assert "ticket_id" in result
        assert "method" in result
        assert "attachment" in result
        assert isinstance(result["attachment"], dict)

    @pytest.mark.asyncio
    async def test_attach_file_upload_failure(
        self, mock_linear_adapter: LinearAdapter, temp_test_file: Path
    ) -> None:
        """Test handling upload failure when all attachment methods fail."""
        ticket_id = "TEST-123"

        mock_task = Task(
            id=ticket_id,
            title="Test Issue",
            description="Test",
        )
        mock_linear_adapter.read.return_value = mock_task

        # Make all attachment methods fail to ensure error propagation
        mock_linear_adapter.upload_file.side_effect = Exception("S3 upload failed")
        mock_linear_adapter.add_attachment = AsyncMock(
            side_effect=Exception("Attachment failed")
        )
        mock_linear_adapter.add_comment = AsyncMock(
            side_effect=Exception("Comment failed")
        )

        with patch(
            "mcp_ticketer.mcp.server.tools.attachment_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await attachment(
                action="attach",
                ticket_id=ticket_id,
                file_path=str(temp_test_file),
            )

        assert result["status"] == "error"
        assert "failed to attach file" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_attach_file_attachment_failure(
        self, mock_linear_adapter: LinearAdapter, temp_test_file: Path
    ) -> None:
        """Test handling attachment creation failure when all methods fail."""
        ticket_id = "TEST-123"

        mock_task = Task(
            id=ticket_id,
            title="Test Issue",
            description="Test",
        )
        mock_linear_adapter.read.return_value = mock_task

        mock_linear_adapter.upload_file.return_value = (
            "https://linear-assets.s3.amazonaws.com/test.txt"
        )
        mock_linear_adapter.attach_file_to_issue.side_effect = Exception(
            "Attachment creation failed"
        )
        # Ensure fallback methods also fail
        mock_linear_adapter.add_attachment = AsyncMock(
            side_effect=Exception("Add attachment failed")
        )
        mock_linear_adapter.add_comment = AsyncMock(
            side_effect=Exception("Add comment failed")
        )

        with patch(
            "mcp_ticketer.mcp.server.tools.attachment_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await attachment(
                action="attach",
                ticket_id=ticket_id,
                file_path=str(temp_test_file),
            )

        assert result["status"] == "error"
        assert "failed to attach file" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_attach_file_empty_file(
        self, mock_linear_adapter: LinearAdapter
    ) -> None:
        """Test attaching an empty file."""
        ticket_id = "TEST-123"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            empty_file = Path(f.name)

        mock_task = Task(
            id=ticket_id,
            title="Test Issue",
            description="Test",
        )
        mock_linear_adapter.read.return_value = mock_task

        mock_linear_adapter.upload_file.return_value = (
            "https://linear-assets.s3.amazonaws.com/empty.txt"
        )
        mock_linear_adapter.attach_file_to_issue.return_value = {
            "id": "attachment-empty",
            "title": "empty.txt",
            "url": "https://linear-assets.s3.amazonaws.com/empty.txt",
        }

        with patch(
            "mcp_ticketer.mcp.server.tools.attachment_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await attachment(
                action="attach",
                ticket_id=ticket_id,
                file_path=str(empty_file),
            )

        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_attach_file_special_characters_filename(
        self, mock_linear_adapter: LinearAdapter
    ) -> None:
        """Test attaching file with special characters in filename."""
        ticket_id = "TEST-123"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=" test (1).txt", delete=False
        ) as f:
            f.write("test")
            special_file = Path(f.name)

        mock_task = Task(
            id=ticket_id,
            title="Test Issue",
            description="Test",
        )
        mock_linear_adapter.read.return_value = mock_task

        mock_linear_adapter.upload_file.return_value = (
            "https://linear-assets.s3.amazonaws.com/file.txt"
        )
        mock_linear_adapter.attach_file_to_issue.return_value = {
            "id": "attachment-special",
            "title": special_file.name,
            "url": "https://linear-assets.s3.amazonaws.com/file.txt",
        }

        with patch(
            "mcp_ticketer.mcp.server.tools.attachment_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await attachment(
                action="attach",
                ticket_id=ticket_id,
                file_path=str(special_file),
            )

        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_attach_file_method_field_in_response(
        self, mock_linear_adapter: LinearAdapter, temp_test_file: Path
    ) -> None:
        """Test that method field correctly identifies attachment strategy."""
        ticket_id = "TEST-123"

        mock_task = Task(
            id=ticket_id,
            title="Test Issue",
            description="Test",
        )
        mock_linear_adapter.read.return_value = mock_task

        mock_linear_adapter.upload_file.return_value = (
            "https://linear-assets.s3.amazonaws.com/test.txt"
        )
        mock_linear_adapter.attach_file_to_issue.return_value = {
            "id": "attachment-123",
            "title": temp_test_file.name,
            "url": "https://linear-assets.s3.amazonaws.com/test.txt",
        }

        with patch(
            "mcp_ticketer.mcp.server.tools.attachment_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await attachment(
                action="attach",
                ticket_id=ticket_id,
                file_path=str(temp_test_file),
            )

        # Verify method field indicates the strategy used
        assert "method" in result
        assert result["method"] in [
            "linear_native_upload",
            "adapter_native",
            "comment_reference",
        ]

    @pytest.mark.asyncio
    async def test_attach_file_authorization_error(
        self, mock_linear_adapter: LinearAdapter, temp_test_file: Path
    ) -> None:
        """Test handling authorization errors during attachment."""
        ticket_id = "TEST-123"

        mock_task = Task(
            id=ticket_id,
            title="Test Issue",
            description="Test",
        )
        mock_linear_adapter.read.return_value = mock_task

        mock_linear_adapter.upload_file.side_effect = PermissionError(
            "Insufficient permissions"
        )
        # Ensure fallback methods also fail
        mock_linear_adapter.add_attachment = AsyncMock(
            side_effect=PermissionError("Insufficient permissions")
        )
        mock_linear_adapter.add_comment = AsyncMock(
            side_effect=PermissionError("Insufficient permissions")
        )

        with patch(
            "mcp_ticketer.mcp.server.tools.attachment_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await attachment(
                action="attach",
                ticket_id=ticket_id,
                file_path=str(temp_test_file),
            )

        assert result["status"] == "error"
        assert "failed to attach file" in result["error"].lower()
