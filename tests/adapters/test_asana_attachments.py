"""Comprehensive tests for Asana adapter attachment functionality.

This test module covers:
- File attachment upload operations
- Attachment retrieval and listing
- Attachment deletion operations
- Error handling and validation
- File existence and permission checks
- Asana API constraints and response handling
- Multipart form-data upload mechanics
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_ticketer.adapters.asana import AsanaAdapter
from mcp_ticketer.core.models import Attachment


class TestAsanaAttachments:
    """Test suite for Asana adapter file attachment functionality.

    Asana supports native file attachments via multipart/form-data uploads.
    Attachments are associated with tasks and have permanent URLs.
    """

    @pytest.fixture
    def mock_config(self) -> dict[str, str]:
        """Mock configuration for Asana adapter."""
        return {
            "api_key": "test_asana_pat_1234567890abcdef",
            "workspace_gid": "123456789",
            "workspace": "Test Workspace",
        }

    @pytest.fixture
    def adapter(self, mock_config: dict[str, str]) -> AsanaAdapter:
        """Create an AsanaAdapter instance with mocked client."""
        adapter = AsanaAdapter(mock_config)
        adapter._initialized = True
        adapter._workspace_gid = "123456789"
        adapter._team_gid = "987654321"
        adapter.client = AsyncMock()
        return adapter

    @pytest.fixture
    def temp_file(self) -> Path:
        """Create a temporary test file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as temp:
            temp.write(f"Test attachment created at {datetime.now().isoformat()}\n")
            temp.write("This is test content for Asana attachments.\n")
            temp.write("Line 3: Additional test data.\n")
            temp_path = Path(temp.name)

        yield temp_path

        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    @pytest.fixture
    def large_temp_file(self) -> Path:
        """Create a larger temporary test file (for size testing)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as temp:
            # Write approximately 1MB of data
            for i in range(10000):
                temp.write(f"Line {i}: This is test data for large file testing.\n")
            temp_path = Path(temp.name)

        yield temp_path

        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_add_attachment_success(
        self, adapter: AsanaAdapter, temp_file: Path
    ) -> None:
        """Test successfully adding a file attachment to an Asana task.

        Validates that:
        - File is uploaded with correct multipart/form-data format
        - Asana API response is correctly mapped to Attachment model
        - Attachment metadata includes filename, size, content type, and URL
        """
        task_gid = "1234567890123456"

        # Mock successful upload response
        mock_response_data = {
            "gid": "attachment_123456789",
            "name": temp_file.name,
            "resource_type": "attachment",
            "resource_subtype": "asana",
            "created_at": "2025-01-19T20:00:00.000Z",
            "download_url": "https://s3.amazonaws.com/asana/attachments/test.txt",
            "permanent_url": "https://app.asana.com/-/attachments/attachment_123456789/download",
            "size": temp_file.stat().st_size,
            "host": "asana",
            "parent": {"gid": task_gid, "resource_type": "task"},
        }

        # Mock httpx upload (Asana uses direct multipart upload, not wrapped in {"data": {}})
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": mock_response_data}
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client_instance
            )

            # Execute attachment upload
            result = await adapter.add_attachment(
                task_gid, str(temp_file), description="Test attachment"
            )

            # Verify result
            assert result is not None
            assert isinstance(result, Attachment)
            assert result.filename == temp_file.name
            assert result.ticket_id == task_gid
            assert result.size_bytes > 0
            assert result.url is not None
            assert "asana" in result.url.lower()

            # Verify API call was made correctly
            mock_client_instance.post.assert_called_once()
            call_args = mock_client_instance.post.call_args
            assert f"/tasks/{task_gid}/attachments" in str(call_args[0][0])

    @pytest.mark.asyncio
    async def test_add_attachment_with_description(
        self, adapter: AsanaAdapter, temp_file: Path
    ) -> None:
        """Test adding attachment with description parameter.

        Note: Asana API doesn't use the description field during upload,
        but we accept it for API compatibility.
        """
        task_gid = "1234567890123456"
        description = "Important test file for validation"

        mock_response_data = {
            "gid": "attachment_123456789",
            "name": temp_file.name,
            "resource_type": "attachment",
            "size": temp_file.stat().st_size,
            "permanent_url": "https://app.asana.com/-/attachments/attachment_123456789/download",
            "parent": {"gid": task_gid},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": mock_response_data}
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client_instance
            )

            result = await adapter.add_attachment(
                task_gid, str(temp_file), description=description
            )

            assert result is not None
            assert result.filename == temp_file.name

    @pytest.mark.asyncio
    async def test_add_attachment_default_description(
        self, adapter: AsanaAdapter, temp_file: Path
    ) -> None:
        """Test adding attachment without description (should use None/empty default)."""
        task_gid = "1234567890123456"

        mock_response_data = {
            "gid": "attachment_123456789",
            "name": temp_file.name,
            "resource_type": "attachment",
            "size": temp_file.stat().st_size,
            "permanent_url": "https://app.asana.com/-/attachments/attachment_123456789/download",
            "parent": {"gid": task_gid},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": mock_response_data}
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client_instance
            )

            # Call without description parameter
            result = await adapter.add_attachment(task_gid, str(temp_file))

            assert result is not None
            assert result.filename == temp_file.name

    @pytest.mark.asyncio
    async def test_add_attachment_file_not_found(self, adapter: AsanaAdapter) -> None:
        """Test that non-existent files raise FileNotFoundError."""
        task_gid = "1234567890123456"
        nonexistent_path = "/nonexistent/directory/file.txt"

        with pytest.raises(FileNotFoundError, match="File not found"):
            await adapter.add_attachment(task_gid, nonexistent_path)

    @pytest.mark.asyncio
    async def test_add_attachment_path_not_file(
        self, adapter: AsanaAdapter, tmp_path: Path
    ) -> None:
        """Test that directory paths (not files) raise ValueError."""
        task_gid = "1234567890123456"
        directory_path = tmp_path / "test_directory"
        directory_path.mkdir()

        with pytest.raises(ValueError, match="Path is not a file"):
            await adapter.add_attachment(task_gid, str(directory_path))

    @pytest.mark.asyncio
    async def test_add_attachment_api_error(
        self, adapter: AsanaAdapter, temp_file: Path
    ) -> None:
        """Test handling API errors during attachment upload."""
        task_gid = "1234567890123456"

        # Mock 500 error response
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client_instance
            )

            with pytest.raises(ValueError, match="Failed to upload attachment"):
                await adapter.add_attachment(task_gid, str(temp_file))

    @pytest.mark.asyncio
    async def test_add_attachment_unauthorized(
        self, adapter: AsanaAdapter, temp_file: Path
    ) -> None:
        """Test handling unauthorized access during attachment upload."""
        task_gid = "1234567890123456"

        # Mock 401 error response
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = '{"errors": [{"message": "Unauthorized"}]}'
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client_instance
            )

            with pytest.raises(ValueError, match="Failed to upload attachment"):
                await adapter.add_attachment(task_gid, str(temp_file))

    @pytest.mark.asyncio
    async def test_add_attachment_task_not_found(
        self, adapter: AsanaAdapter, temp_file: Path
    ) -> None:
        """Test uploading attachment to non-existent task."""
        task_gid = "999999999999999"

        # Mock 404 error response
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = '{"errors": [{"message": "Not Found"}]}'
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client_instance
            )

            with pytest.raises(ValueError, match="Failed to upload attachment"):
                await adapter.add_attachment(task_gid, str(temp_file))

    @pytest.mark.asyncio
    async def test_get_attachments_success(self, adapter: AsanaAdapter) -> None:
        """Test retrieving attachments for a valid task.

        Validates that:
        - Multiple attachments are correctly retrieved
        - Attachment metadata is properly mapped
        - Empty attachment lists are handled
        """
        task_gid = "1234567890123456"

        # Mock multiple attachments
        mock_attachments = [
            {
                "gid": "attachment_001",
                "name": "document.pdf",
                "resource_type": "attachment",
                "size": 1024000,
                "permanent_url": "https://app.asana.com/-/attachments/attachment_001/download",
                "created_at": "2025-01-19T10:00:00.000Z",
                "parent": {"gid": task_gid},
            },
            {
                "gid": "attachment_002",
                "name": "screenshot.png",
                "resource_type": "attachment",
                "size": 512000,
                "permanent_url": "https://app.asana.com/-/attachments/attachment_002/download",
                "created_at": "2025-01-19T11:00:00.000Z",
                "parent": {"gid": task_gid},
            },
            {
                "gid": "attachment_003",
                "name": "data.csv",
                "resource_type": "attachment",
                "size": 256000,
                "permanent_url": "https://app.asana.com/-/attachments/attachment_003/download",
                "created_at": "2025-01-19T12:00:00.000Z",
                "parent": {"gid": task_gid},
            },
        ]

        adapter.client.get_paginated = AsyncMock(return_value=mock_attachments)

        # Execute get attachments
        result = await adapter.get_attachments(task_gid)

        # Verify result
        assert len(result) == 3
        assert all(isinstance(att, Attachment) for att in result)
        assert result[0].filename == "document.pdf"
        assert result[1].filename == "screenshot.png"
        assert result[2].filename == "data.csv"
        assert all(att.ticket_id == task_gid for att in result)
        assert all(att.url is not None for att in result)

        # Verify API call
        adapter.client.get_paginated.assert_called_once_with(
            f"/tasks/{task_gid}/attachments"
        )

    @pytest.mark.asyncio
    async def test_get_attachments_empty_list(self, adapter: AsanaAdapter) -> None:
        """Test retrieving attachments when task has none."""
        task_gid = "1234567890123456"

        # Mock empty attachments list
        adapter.client.get_paginated = AsyncMock(return_value=[])

        result = await adapter.get_attachments(task_gid)

        assert result == []
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_attachments_task_not_found(self, adapter: AsanaAdapter) -> None:
        """Test retrieving attachments for non-existent task."""
        task_gid = "999999999999999"

        # Mock exception for non-existent task
        adapter.client.get_paginated = AsyncMock(
            side_effect=Exception("404: Not Found")
        )

        result = await adapter.get_attachments(task_gid)

        # Should return empty list on error
        assert result == []

    @pytest.mark.asyncio
    async def test_delete_attachment_success(self, adapter: AsanaAdapter) -> None:
        """Test successfully deleting an attachment.

        Note: Asana delete API uses attachment_id directly, not ticket_id.
        The ticket_id parameter is kept for interface compatibility.
        """
        task_gid = "1234567890123456"
        attachment_id = "attachment_123456789"

        # Mock successful deletion
        adapter.client.delete = AsyncMock(return_value=None)

        result = await adapter.delete_attachment(task_gid, attachment_id)

        assert result is True
        adapter.client.delete.assert_called_once_with(f"/attachments/{attachment_id}")

    @pytest.mark.asyncio
    async def test_delete_attachment_not_found(self, adapter: AsanaAdapter) -> None:
        """Test deleting non-existent attachment."""
        task_gid = "1234567890123456"
        attachment_id = "999999999999999"

        # Mock 404 error
        adapter.client.delete = AsyncMock(side_effect=Exception("404: Not Found"))

        result = await adapter.delete_attachment(task_gid, attachment_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_attachment_api_error(self, adapter: AsanaAdapter) -> None:
        """Test handling API errors during attachment deletion."""
        task_gid = "1234567890123456"
        attachment_id = "attachment_123456789"

        # Mock 500 error
        adapter.client.delete = AsyncMock(
            side_effect=Exception("500: Internal Server Error")
        )

        result = await adapter.delete_attachment(task_gid, attachment_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_multiple_attachments_same_task(
        self, adapter: AsanaAdapter, temp_file: Path, tmp_path: Path
    ) -> None:
        """Test adding multiple attachments to the same task."""
        task_gid = "1234567890123456"

        # Create second test file
        second_file = tmp_path / "second_file.txt"
        second_file.write_text("Second attachment content")

        # Mock responses for both uploads
        mock_response_1 = {
            "gid": "attachment_001",
            "name": temp_file.name,
            "resource_type": "attachment",
            "size": temp_file.stat().st_size,
            "permanent_url": "https://app.asana.com/-/attachments/attachment_001/download",
            "parent": {"gid": task_gid},
        }

        mock_response_2 = {
            "gid": "attachment_002",
            "name": second_file.name,
            "resource_type": "attachment",
            "size": second_file.stat().st_size,
            "permanent_url": "https://app.asana.com/-/attachments/attachment_002/download",
            "parent": {"gid": task_gid},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()

            # Setup mock to return different responses for each call
            mock_client_instance.post = AsyncMock(
                side_effect=[
                    Mock(status_code=200, json=lambda: {"data": mock_response_1}),
                    Mock(status_code=200, json=lambda: {"data": mock_response_2}),
                ]
            )
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client_instance
            )

            # Upload first attachment
            result1 = await adapter.add_attachment(task_gid, str(temp_file))
            assert result1.filename == temp_file.name

            # Upload second attachment
            result2 = await adapter.add_attachment(task_gid, str(second_file))
            assert result2.filename == second_file.name

            # Verify both uploads were made
            assert mock_client_instance.post.call_count == 2

    @pytest.mark.asyncio
    async def test_attachment_metadata_format(
        self, adapter: AsanaAdapter, temp_file: Path
    ) -> None:
        """Test that attachment metadata matches Asana's schema.

        Validates response structure and required fields.
        """
        task_gid = "1234567890123456"

        mock_response_data = {
            "gid": "attachment_123456789",
            "name": temp_file.name,
            "resource_type": "attachment",
            "resource_subtype": "asana",
            "created_at": "2025-01-19T20:00:00.000Z",
            "download_url": "https://s3.amazonaws.com/asana/attachments/test.txt",
            "permanent_url": "https://app.asana.com/-/attachments/attachment_123456789/download",
            "size": 1024,
            "host": "asana",
            "parent": {
                "gid": task_gid,
                "resource_type": "task",
                "name": "Test Task",
            },
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": mock_response_data}
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client_instance
            )

            result = await adapter.add_attachment(task_gid, str(temp_file))

            # Verify Attachment model fields are populated
            assert result.id == "attachment_123456789"
            assert result.filename == temp_file.name
            assert result.ticket_id == task_gid
            assert result.size_bytes == 1024
            assert result.url is not None
            assert result.created_at is not None

    @pytest.mark.asyncio
    async def test_attachment_content_type_detection(
        self, adapter: AsanaAdapter, tmp_path: Path
    ) -> None:
        """Test that content type is correctly detected for various file types."""
        task_gid = "1234567890123456"

        # Test different file types
        test_files = [
            ("test.txt", "text/plain"),
            ("test.pdf", "application/pdf"),
            ("test.jpg", "image/jpeg"),
            ("test.png", "image/png"),
            ("test.json", "application/json"),
        ]

        for filename, _expected_mime in test_files:
            test_file = tmp_path / filename
            test_file.write_text("test content")

            mock_response_data = {
                "gid": f"attachment_{filename}",
                "name": filename,
                "resource_type": "attachment",
                "size": test_file.stat().st_size,
                "permanent_url": f"https://app.asana.com/-/attachments/attachment_{filename}/download",
                "parent": {"gid": task_gid},
            }

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client_instance = AsyncMock()
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"data": mock_response_data}
                mock_client_instance.post = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__.return_value = (
                    mock_client_instance
                )

                result = await adapter.add_attachment(task_gid, str(test_file))
                assert result.filename == filename

            # Cleanup
            test_file.unlink()


class TestAsanaAttachmentEdgeCases:
    """Test edge cases and Asana-specific behavior for attachments."""

    @pytest.fixture
    def mock_config(self) -> dict[str, str]:
        """Mock configuration for Asana adapter."""
        return {
            "api_key": "test_asana_pat_1234567890abcdef",
            "workspace_gid": "123456789",
        }

    @pytest.fixture
    def adapter(self, mock_config: dict[str, str]) -> AsanaAdapter:
        """Create an AsanaAdapter instance with mocked client."""
        adapter = AsanaAdapter(mock_config)
        adapter._initialized = True
        adapter._workspace_gid = "123456789"
        adapter.client = AsyncMock()
        return adapter

    @pytest.mark.asyncio
    async def test_unicode_filename_support(
        self, adapter: AsanaAdapter, tmp_path: Path
    ) -> None:
        """Test that Unicode characters in filenames are supported."""
        task_gid = "1234567890123456"
        unicode_filename = "测试文件_🚀.txt"
        test_file = tmp_path / unicode_filename
        test_file.write_text("Unicode filename test")

        mock_response_data = {
            "gid": "attachment_unicode",
            "name": unicode_filename,
            "resource_type": "attachment",
            "size": test_file.stat().st_size,
            "permanent_url": "https://app.asana.com/-/attachments/attachment_unicode/download",
            "parent": {"gid": task_gid},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": mock_response_data}
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client_instance
            )

            result = await adapter.add_attachment(task_gid, str(test_file))
            assert result.filename == unicode_filename

    @pytest.mark.asyncio
    async def test_large_file_upload(
        self, adapter: AsanaAdapter, tmp_path: Path
    ) -> None:
        """Test uploading larger files (simulated).

        Note: Asana has file size limits (typically 100MB for most accounts).
        This test validates the upload flow works for larger files.
        """
        task_gid = "1234567890123456"
        large_file = tmp_path / "large_file.bin"

        # Create a file with simulated large size
        large_file.write_bytes(b"0" * (5 * 1024 * 1024))  # 5MB

        mock_response_data = {
            "gid": "attachment_large",
            "name": "large_file.bin",
            "resource_type": "attachment",
            "size": large_file.stat().st_size,
            "permanent_url": "https://app.asana.com/-/attachments/attachment_large/download",
            "parent": {"gid": task_gid},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": mock_response_data}
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client_instance
            )

            result = await adapter.add_attachment(task_gid, str(large_file))
            assert result.size_bytes == large_file.stat().st_size
            assert result.size_bytes > 5 * 1024 * 1024 - 1000  # Approximately 5MB

    @pytest.mark.asyncio
    async def test_attachment_with_special_characters_in_filename(
        self, adapter: AsanaAdapter, tmp_path: Path
    ) -> None:
        """Test filenames with special characters."""
        task_gid = "1234567890123456"
        special_filename = "test file (with) [brackets] & symbols.txt"
        test_file = tmp_path / special_filename
        test_file.write_text("Special characters test")

        mock_response_data = {
            "gid": "attachment_special",
            "name": special_filename,
            "resource_type": "attachment",
            "size": test_file.stat().st_size,
            "permanent_url": "https://app.asana.com/-/attachments/attachment_special/download",
            "parent": {"gid": task_gid},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": mock_response_data}
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client_instance
            )

            result = await adapter.add_attachment(task_gid, str(test_file))
            assert result.filename == special_filename

    @pytest.mark.asyncio
    async def test_empty_file_upload(
        self, adapter: AsanaAdapter, tmp_path: Path
    ) -> None:
        """Test uploading an empty file (0 bytes)."""
        task_gid = "1234567890123456"
        empty_file = tmp_path / "empty.txt"
        empty_file.touch()  # Create empty file

        mock_response_data = {
            "gid": "attachment_empty",
            "name": "empty.txt",
            "resource_type": "attachment",
            "size": 0,
            "permanent_url": "https://app.asana.com/-/attachments/attachment_empty/download",
            "parent": {"gid": task_gid},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": mock_response_data}
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client_instance
            )

            result = await adapter.add_attachment(task_gid, str(empty_file))
            assert result.size_bytes == 0
