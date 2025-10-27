"""Security tests for AITrackdown adapter path traversal protection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from mcp_ticketer.adapters.aitrackdown import AITrackdownAdapter
from mcp_ticketer.core.models import Task

# Mark all tests in this module
pytestmark = [
    pytest.mark.adapter,
    pytest.mark.aitrackdown,
    pytest.mark.unit,
    pytest.mark.security,
]


@pytest.fixture
def adapter_config(aitrackdown_temp_dir: Path) -> dict[str, Any]:
    """Create adapter configuration with temp directory.

    Args:
        aitrackdown_temp_dir: Temporary directory for AITrackdown

    Returns:
        Configuration dictionary
    """
    return {"base_path": str(aitrackdown_temp_dir)}


@pytest.fixture
def aitrackdown_adapter(adapter_config: dict[str, Any]) -> AITrackdownAdapter:
    """Create AITrackdown adapter instance.

    Args:
        adapter_config: Adapter configuration

    Returns:
        AITrackdownAdapter instance
    """
    return AITrackdownAdapter(adapter_config)


@pytest.fixture
def test_ticket_with_attachment(
    aitrackdown_adapter: AITrackdownAdapter, tmp_path: Path
) -> tuple[AITrackdownAdapter, str, Path]:
    """Create setup for test ticket with attachment.

    Args:
        aitrackdown_adapter: AITrackdown adapter instance
        tmp_path: Temporary directory fixture

    Returns:
        Tuple of (adapter, ticket_id, test_file_path)
    """
    import asyncio

    # Create a test ticket
    task = Task(title="Test Ticket for Attachments")
    created = asyncio.run(aitrackdown_adapter.create(task))

    # Create a test file to attach
    test_file = tmp_path / "test_attachment.txt"
    test_file.write_text("This is a test attachment")

    # Add attachment to ticket
    asyncio.run(
        aitrackdown_adapter.add_attachment(
            created.id, str(test_file), "Test attachment"
        )
    )

    return aitrackdown_adapter, created.id, test_file


class TestGetAttachmentsPathTraversal:
    """Tests for get_attachments() path traversal protection."""

    @pytest.mark.asyncio
    async def test_get_attachments_normal_ticket_id(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test get_attachments with normal ticket_id (should work).

        Test 1: Normal ticket_id (should work)
        """
        # Create a valid ticket
        task = Task(title="Normal Ticket")
        created = await aitrackdown_adapter.create(task)

        # Get attachments - should return empty list, not error
        result = await aitrackdown_adapter.get_attachments(created.id)

        # Expected: Returns list of attachments (empty in this case)
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_attachments_path_traversal_dots(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test get_attachments blocks path traversal with dots.

        Test 2a: Path traversal in ticket_id using ../ (should fail)
        """
        # Try path traversal with ../
        with pytest.raises(ValueError) as exc_info:
            await aitrackdown_adapter.get_attachments("../../../etc")

        # Expected: ValueError raised with descriptive message
        assert "path traversal detected" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_attachments_path_traversal_absolute(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test get_attachments blocks absolute path traversal.

        Test 2b: Path traversal using absolute path (should fail)
        """
        # Try path traversal with absolute path
        with pytest.raises(ValueError) as exc_info:
            await aitrackdown_adapter.get_attachments("/etc/passwd")

        # Expected: ValueError raised with descriptive message
        assert "path traversal detected" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_attachments_path_traversal_encoded(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test get_attachments with URL-encoded path.

        Test 2c: Path with URL encoding (treated as literal filename)
        Note: Python's Path doesn't decode URLs, so this becomes a literal filename
        """
        # URL-encoded path is treated as a literal filename (not decoded)
        # This is safe - it won't traverse, just returns empty list for non-existent dir
        result = await aitrackdown_adapter.get_attachments("..%2F..%2F..%2Fetc")

        # Expected: Returns empty list (directory doesn't exist with that literal name)
        assert isinstance(result, list)
        assert len(result) == 0


class TestDeleteAttachmentPathTraversal:
    """Tests for delete_attachment() path traversal protection."""

    @pytest.mark.asyncio
    async def test_delete_attachment_normal(
        self, test_ticket_with_attachment: tuple[AITrackdownAdapter, str, Path]
    ) -> None:
        """Test normal attachment deletion (should work).

        Test 3: Normal deletion (should work)
        """
        adapter, ticket_id, _ = test_ticket_with_attachment

        # Get the actual attachment ID
        attachments = await adapter.get_attachments(ticket_id)
        assert len(attachments) > 0, "Should have at least one attachment"

        attachment_id = attachments[0].id

        # Delete the attachment - should work
        result = await adapter.delete_attachment(ticket_id, attachment_id)

        # Expected: True (attachment was deleted)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_attachment_nonexistent(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test deleting non-existent attachment returns False."""
        # Create a valid ticket
        task = Task(title="Test Ticket")
        created = await aitrackdown_adapter.create(task)

        # Try to delete non-existent attachment (should return False, not error)
        result = await aitrackdown_adapter.delete_attachment(
            created.id, "nonexistent_file.txt"
        )

        # Expected: False (attachment not found)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_attachment_path_traversal_in_attachment_id(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test delete_attachment blocks path traversal in attachment_id.

        Test 4: Path traversal in attachment_id (should fail)
        """
        # Create a valid ticket
        task = Task(title="Test Ticket")
        created = await aitrackdown_adapter.create(task)

        # Create attachments directory (required for security check to run)
        attachments_dir = aitrackdown_adapter.base_path / "attachments" / created.id
        attachments_dir.mkdir(parents=True, exist_ok=True)

        # Try path traversal in attachment_id
        with pytest.raises(ValueError) as exc_info:
            await aitrackdown_adapter.delete_attachment(created.id, "../../secret.txt")

        # Expected: ValueError raised with descriptive message
        assert "path traversal detected" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_delete_attachment_path_traversal_in_ticket_id(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test delete_attachment blocks path traversal in ticket_id.

        Test 5: Path traversal in ticket_id (should fail)
        """
        # Try path traversal in ticket_id
        # This should return False (directory doesn't exist) rather than raising error
        result = await aitrackdown_adapter.delete_attachment("../../../etc", "passwd")

        # Expected: False (directory doesn't exist due to path traversal)
        # Note: The security check happens when resolving paths
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_attachment_absolute_path_in_attachment_id(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test delete_attachment blocks absolute paths in attachment_id."""
        # Create a valid ticket
        task = Task(title="Test Ticket")
        created = await aitrackdown_adapter.create(task)

        # Create attachments directory (required for security check to run)
        attachments_dir = aitrackdown_adapter.base_path / "attachments" / created.id
        attachments_dir.mkdir(parents=True, exist_ok=True)

        # Try absolute path in attachment_id
        with pytest.raises(ValueError) as exc_info:
            await aitrackdown_adapter.delete_attachment(created.id, "/etc/passwd")

        # Expected: ValueError raised with descriptive message
        assert "path traversal detected" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_delete_attachment_symlink_traversal(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test delete_attachment blocks symlink-based traversal."""
        # Create a valid ticket
        task = Task(title="Test Ticket")
        created = await aitrackdown_adapter.create(task)

        # Create attachments directory
        attachments_dir = aitrackdown_adapter.base_path / "attachments" / created.id
        attachments_dir.mkdir(parents=True, exist_ok=True)

        # Try to use a symlink name that would traverse (even if symlink doesn't exist)
        # The security check should catch this before attempting to delete
        with pytest.raises(ValueError) as exc_info:
            await aitrackdown_adapter.delete_attachment(
                created.id, "../../../etc/passwd"
            )

        # Expected: ValueError raised
        assert "path traversal detected" in str(exc_info.value).lower()


class TestPathTraversalVectors:
    """Test various path traversal attack vectors."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "malicious_ticket_id",
        [
            "../../../etc",
            "../../..",
            "../../../etc/passwd",
            "/etc/passwd",
            "./../.../../etc",  # Mixed
        ],
    )
    async def test_get_attachments_blocks_various_traversals(
        self, aitrackdown_adapter: AITrackdownAdapter, malicious_ticket_id: str
    ) -> None:
        """Test get_attachments blocks various path traversal patterns."""
        with pytest.raises(ValueError) as exc_info:
            await aitrackdown_adapter.get_attachments(malicious_ticket_id)

        # All should be caught by the security check
        error_msg = str(exc_info.value).lower()
        assert "path traversal detected" in error_msg or "invalid" in error_msg

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "malicious_attachment_id",
        [
            "../../secret.txt",
            "../../../etc/passwd",
            "/etc/passwd",
            "./../../../etc/shadow",  # Mixed
        ],
    )
    async def test_delete_attachment_blocks_various_traversals(
        self, aitrackdown_adapter: AITrackdownAdapter, malicious_attachment_id: str
    ) -> None:
        """Test delete_attachment blocks various path traversal patterns."""
        # Create a valid ticket
        task = Task(title="Test Ticket")
        created = await aitrackdown_adapter.create(task)

        # Create attachments directory (required for security check to run)
        attachments_dir = aitrackdown_adapter.base_path / "attachments" / created.id
        attachments_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(ValueError) as exc_info:
            await aitrackdown_adapter.delete_attachment(
                created.id, malicious_attachment_id
            )

        # All should be caught by the security check
        error_msg = str(exc_info.value).lower()
        assert "path traversal detected" in error_msg
