"""Comprehensive tests for Linear adapter file upload and attachment functionality.

This test module covers:
- File upload to Linear's S3 storage
- File attachment to issues and epics
- MIME type detection and handling
- Error handling and validation
- Edge cases (large files, special characters, etc.)
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter


class TestLinearFileUpload:
    """Test suite for Linear adapter file upload functionality."""

    @pytest.fixture
    def mock_config(self) -> dict[str, str]:
        """Mock configuration for Linear adapter."""
        return {
            "api_key": "lin_api_test_key_12345678901234567890",
            "team_key": "TEST",
            "workspace": "test-workspace",
        }

    @pytest.fixture
    def adapter(self, mock_config: dict[str, str]) -> LinearAdapter:
        """Create a LinearAdapter instance with mocked client."""
        with patch("mcp_ticketer.adapters.linear.adapter.LinearGraphQLClient"):
            adapter = LinearAdapter(mock_config)
            adapter._initialized = True
            adapter.team_id = "test-team-id"
            adapter._workflow_states = {}
            adapter._labels_cache = []
            adapter._users_cache = {}
            return adapter

    @pytest.fixture
    def temp_text_file(self) -> Path:
        """Create a temporary text file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("This is a test document for Linear file upload.")
            return Path(f.name)

    @pytest.fixture
    def temp_image_file(self) -> Path:
        """Create a temporary image file for testing."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".png", delete=False) as f:
            # Write a minimal PNG header
            f.write(b"\x89PNG\r\n\x1a\n")
            return Path(f.name)

    @pytest.fixture
    def temp_pdf_file(self) -> Path:
        """Create a temporary PDF file for testing."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as f:
            # Write a minimal PDF header
            f.write(b"%PDF-1.4\n")
            return Path(f.name)

    @pytest.mark.asyncio
    async def test_upload_text_file_success(
        self, adapter: LinearAdapter, temp_text_file: Path
    ) -> None:
        """Test uploading a text file successfully."""
        # Mock fileUpload mutation response
        mock_upload_response = {
            "fileUpload": {
                "success": True,
                "uploadFile": {
                    "assetUrl": "https://linear-assets.s3.amazonaws.com/test-file.txt",
                    "uploadUrl": "https://s3.amazonaws.com/presigned-upload-url",
                    "headers": [
                        {"key": "Content-Type", "value": "text/plain"},
                        {"key": "x-amz-acl", "value": "public-read"},
                    ],
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_upload_response)

        # Mock httpx PUT request
        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.put = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_client

            result = await adapter.upload_file(str(temp_text_file), "text/plain")

            assert result == "https://linear-assets.s3.amazonaws.com/test-file.txt"
            adapter.client.execute_mutation.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_image_file_success(
        self, adapter: LinearAdapter, temp_image_file: Path
    ) -> None:
        """Test uploading an image file (PNG)."""
        mock_upload_response = {
            "fileUpload": {
                "success": True,
                "uploadFile": {
                    "assetUrl": "https://linear-assets.s3.amazonaws.com/test-image.png",
                    "uploadUrl": "https://s3.amazonaws.com/presigned-upload-url",
                    "headers": [
                        {"key": "Content-Type", "value": "image/png"},
                    ],
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_upload_response)

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.put = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_client

            result = await adapter.upload_file(str(temp_image_file), "image/png")

            assert result == "https://linear-assets.s3.amazonaws.com/test-image.png"

    @pytest.mark.asyncio
    async def test_upload_pdf_file_success(
        self, adapter: LinearAdapter, temp_pdf_file: Path
    ) -> None:
        """Test uploading a PDF document."""
        mock_upload_response = {
            "fileUpload": {
                "success": True,
                "uploadFile": {
                    "assetUrl": "https://linear-assets.s3.amazonaws.com/test-doc.pdf",
                    "uploadUrl": "https://s3.amazonaws.com/presigned-upload-url",
                    "headers": [
                        {"key": "Content-Type", "value": "application/pdf"},
                    ],
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_upload_response)

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.put = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_client

            result = await adapter.upload_file(str(temp_pdf_file), "application/pdf")

            assert result == "https://linear-assets.s3.amazonaws.com/test-doc.pdf"

    @pytest.mark.asyncio
    async def test_upload_file_auto_detect_mime_type(
        self, adapter: LinearAdapter, temp_text_file: Path
    ) -> None:
        """Test auto-detecting MIME type when not provided."""
        mock_upload_response = {
            "fileUpload": {
                "success": True,
                "uploadFile": {
                    "assetUrl": "https://linear-assets.s3.amazonaws.com/test.txt",
                    "uploadUrl": "https://s3.amazonaws.com/presigned-upload-url",
                    "headers": [],
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_upload_response)

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.put = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_client

            # Call without mime_type - should auto-detect
            result = await adapter.upload_file(str(temp_text_file))

            assert result == "https://linear-assets.s3.amazonaws.com/test.txt"

    @pytest.mark.asyncio
    async def test_upload_file_not_found(self, adapter: LinearAdapter) -> None:
        """Test handling file not found error."""
        with pytest.raises(FileNotFoundError):
            await adapter.upload_file("/nonexistent/file.txt")

    @pytest.mark.asyncio
    async def test_upload_file_invalid_path(self, adapter: LinearAdapter) -> None:
        """Test handling invalid file path."""
        with pytest.raises((FileNotFoundError, ValueError)):
            await adapter.upload_file("")

    @pytest.mark.asyncio
    async def test_upload_file_s3_upload_failure(
        self, adapter: LinearAdapter, temp_text_file: Path
    ) -> None:
        """Test handling S3 upload failure."""
        mock_upload_response = {
            "fileUpload": {
                "success": True,
                "uploadFile": {
                    "assetUrl": "https://linear-assets.s3.amazonaws.com/test.txt",
                    "uploadUrl": "https://s3.amazonaws.com/presigned-upload-url",
                    "headers": [],
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_upload_response)

        with patch("httpx.AsyncClient") as mock_httpx:
            # Mock S3 upload failure
            mock_response = Mock()
            mock_response.status_code = 403
            mock_response.text = "Access Denied"
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.put = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_client

            with pytest.raises(ValueError, match="Failed to upload.*403"):
                await adapter.upload_file(str(temp_text_file))

    @pytest.mark.asyncio
    async def test_upload_file_graphql_error(
        self, adapter: LinearAdapter, temp_text_file: Path
    ) -> None:
        """Test handling GraphQL error during upload initialization."""
        adapter.client.execute_mutation = AsyncMock(
            side_effect=Exception("GraphQL error")
        )

        with pytest.raises(Exception, match="GraphQL error"):
            await adapter.upload_file(str(temp_text_file))

    @pytest.mark.asyncio
    async def test_upload_file_empty_file(self, adapter: LinearAdapter) -> None:
        """Test uploading an empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            empty_file = Path(f.name)

        mock_upload_response = {
            "fileUpload": {
                "success": True,
                "uploadFile": {
                    "assetUrl": "https://linear-assets.s3.amazonaws.com/empty.txt",
                    "uploadUrl": "https://s3.amazonaws.com/presigned-upload-url",
                    "headers": [],
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_upload_response)

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.put = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_client

            result = await adapter.upload_file(str(empty_file))

            assert result == "https://linear-assets.s3.amazonaws.com/empty.txt"

    @pytest.mark.asyncio
    async def test_upload_file_special_characters_in_name(
        self, adapter: LinearAdapter
    ) -> None:
        """Test uploading file with special characters in filename."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=" test (1).txt", delete=False
        ) as f:
            f.write("test content")
            special_file = Path(f.name)

        mock_upload_response = {
            "fileUpload": {
                "success": True,
                "uploadFile": {
                    "assetUrl": "https://linear-assets.s3.amazonaws.com/file.txt",
                    "uploadUrl": "https://s3.amazonaws.com/presigned-upload-url",
                    "headers": [],
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_upload_response)

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.put = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_client

            result = await adapter.upload_file(str(special_file))

            assert result == "https://linear-assets.s3.amazonaws.com/file.txt"

    @pytest.mark.asyncio
    async def test_upload_file_verify_asset_url_format(
        self, adapter: LinearAdapter, temp_text_file: Path
    ) -> None:
        """Test that returned asset URL has correct format."""
        mock_upload_response = {
            "fileUpload": {
                "success": True,
                "uploadFile": {
                    "assetUrl": "https://linear-assets.s3.amazonaws.com/abc123/test.txt",
                    "uploadUrl": "https://s3.amazonaws.com/presigned-upload-url",
                    "headers": [],
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_upload_response)

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.put = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_client

            result = await adapter.upload_file(str(temp_text_file))

            # Verify URL format
            assert result.startswith("https://")
            assert "linear-assets.s3.amazonaws.com" in result
            assert result.endswith(".txt")


class TestLinearFileAttachment:
    """Test suite for Linear adapter file attachment functionality."""

    @pytest.fixture
    def mock_config(self) -> dict[str, str]:
        """Mock configuration for Linear adapter."""
        return {
            "api_key": "lin_api_test_key_12345678901234567890",
            "team_key": "TEST",
            "workspace": "test-workspace",
        }

    @pytest.fixture
    def adapter(self, mock_config: dict[str, str]) -> LinearAdapter:
        """Create a LinearAdapter instance with mocked client."""
        with patch("mcp_ticketer.adapters.linear.adapter.LinearGraphQLClient"):
            adapter = LinearAdapter(mock_config)
            adapter._initialized = True
            adapter.team_id = "test-team-id"
            adapter._workflow_states = {}
            adapter._labels_cache = []
            adapter._users_cache = {}
            return adapter

    @pytest.mark.asyncio
    async def test_attach_file_to_issue_success(self, adapter: LinearAdapter) -> None:
        """Test attaching uploaded file to issue successfully."""
        issue_id = "TEST-123"

        # Mock issue resolution
        adapter._resolve_issue_id = AsyncMock(return_value="uuid-issue-123")
        file_url = "https://linear-assets.s3.amazonaws.com/test.txt"
        title = "Test Document"

        # Mock issue resolution
        adapter._resolve_issue_id = AsyncMock(return_value="uuid-issue-123")

        mock_response = {
            "attachmentCreate": {
                "success": True,
                "attachment": {
                    "id": "attachment-id-123",
                    "title": title,
                    "url": file_url,
                    "subtitle": None,
                    "createdAt": "2025-01-15T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_response)

        result = await adapter.attach_file_to_issue(issue_id, file_url, title)

        assert result is not None
        assert result["id"] == "attachment-id-123"
        assert result["title"] == title
        assert result["url"] == file_url
        adapter.client.execute_mutation.assert_called_once()

    @pytest.mark.asyncio
    async def test_attach_file_to_issue_with_subtitle(
        self, adapter: LinearAdapter
    ) -> None:
        """Test attaching file with subtitle."""
        issue_id = "TEST-123"

        # Mock issue resolution
        adapter._resolve_issue_id = AsyncMock(return_value="uuid-issue-123")
        file_url = "https://linear-assets.s3.amazonaws.com/test.txt"
        title = "Test Document"
        subtitle = "Uploaded via API"

        mock_response = {
            "attachmentCreate": {
                "success": True,
                "attachment": {
                    "id": "attachment-id-123",
                    "title": title,
                    "url": file_url,
                    "subtitle": subtitle,
                    "createdAt": "2025-01-15T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_response)

        result = await adapter.attach_file_to_issue(
            issue_id, file_url, title, subtitle=subtitle
        )

        assert result["subtitle"] == subtitle

    @pytest.mark.asyncio
    async def test_attach_file_to_issue_with_comment(
        self, adapter: LinearAdapter
    ) -> None:
        """Test attaching file with comment body."""
        issue_id = "TEST-123"

        # Mock issue resolution
        adapter._resolve_issue_id = AsyncMock(return_value="uuid-issue-123")
        file_url = "https://linear-assets.s3.amazonaws.com/test.txt"
        title = "Test Document"
        comment_body = "Please review this document"

        # Mock both attachment creation and comment creation
        mock_attach_response = {
            "attachmentCreate": {
                "success": True,
                "attachment": {
                    "id": "attachment-id-123",
                    "title": title,
                    "url": file_url,
                    "subtitle": None,
                    "createdAt": "2025-01-15T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_attach_response)

        result = await adapter.attach_file_to_issue(
            issue_id, file_url, title, comment_body=comment_body
        )

        assert result is not None
        assert result["id"] == "attachment-id-123"

    @pytest.mark.asyncio
    async def test_attach_external_url_to_issue(self, adapter: LinearAdapter) -> None:
        """Test attaching external URL without upload."""
        issue_id = "TEST-123"
        external_url = "https://example.com/document.pdf"
        title = "External Document"

        # Mock issue resolution
        adapter._resolve_issue_id = AsyncMock(return_value="uuid-issue-123")

        mock_response = {
            "attachmentCreate": {
                "success": True,
                "attachment": {
                    "id": "attachment-id-456",
                    "title": title,
                    "url": external_url,
                    "subtitle": None,
                    "createdAt": "2025-01-15T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_response)

        result = await adapter.attach_file_to_issue(issue_id, external_url, title)

        assert result["url"] == external_url

    @pytest.mark.asyncio
    async def test_attach_file_to_issue_invalid_issue_id(
        self, adapter: LinearAdapter
    ) -> None:
        """Test attaching file to invalid issue ID."""
        # Mock issue resolution to return None (issue not found)
        adapter._resolve_issue_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Issue.*not found"):
            await adapter.attach_file_to_issue(
                "INVALID-999",
                "https://example.com/file.txt",
                "Test",
            )

    @pytest.mark.asyncio
    async def test_attach_file_to_epic_success(self, adapter: LinearAdapter) -> None:
        """Test attaching uploaded file to epic successfully."""
        epic_id = "test-epic-id"
        file_url = "https://linear-assets.s3.amazonaws.com/test.txt"
        title = "Epic Documentation"

        # Mock epic resolution
        adapter._resolve_project_id = AsyncMock(return_value="uuid-epic-123")

        mock_response = {
            "attachmentCreate": {
                "success": True,
                "attachment": {
                    "id": "attachment-id-789",
                    "title": title,
                    "url": file_url,
                    "subtitle": None,
                    "createdAt": "2025-01-15T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_response)

        result = await adapter.attach_file_to_epic(epic_id, file_url, title)

        assert result is not None
        assert result["id"] == "attachment-id-789"
        assert result["title"] == title

    @pytest.mark.asyncio
    async def test_attach_file_to_epic_with_subtitle(
        self, adapter: LinearAdapter
    ) -> None:
        """Test attaching file to epic with subtitle."""
        epic_id = "test-epic-id"
        file_url = "https://linear-assets.s3.amazonaws.com/test.txt"
        title = "Project Spec"
        subtitle = "Version 1.0"

        # Mock epic resolution
        adapter._resolve_project_id = AsyncMock(return_value="uuid-epic-123")

        mock_response = {
            "attachmentCreate": {
                "success": True,
                "attachment": {
                    "id": "attachment-id-999",
                    "title": title,
                    "url": file_url,
                    "subtitle": subtitle,
                    "createdAt": "2025-01-15T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_response)

        result = await adapter.attach_file_to_epic(
            epic_id, file_url, title, subtitle=subtitle
        )

        assert result["subtitle"] == subtitle

    @pytest.mark.asyncio
    async def test_attach_file_to_epic_invalid_epic_id(
        self, adapter: LinearAdapter
    ) -> None:
        """Test attaching file to invalid epic ID."""
        # Mock epic resolution to return None (epic not found)
        adapter._resolve_project_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="(Project|Epic).*not found"):
            await adapter.attach_file_to_epic(
                "invalid-epic",
                "https://example.com/file.txt",
                "Test",
            )

    @pytest.mark.asyncio
    async def test_attachment_verify_record_created(
        self, adapter: LinearAdapter
    ) -> None:
        """Test that attachment record is properly created."""
        issue_id = "TEST-123"

        # Mock issue resolution
        adapter._resolve_issue_id = AsyncMock(return_value="uuid-issue-123")
        file_url = "https://linear-assets.s3.amazonaws.com/test.txt"
        title = "Test Document"

        mock_response = {
            "attachmentCreate": {
                "success": True,
                "attachment": {
                    "id": "attachment-id-123",
                    "title": title,
                    "url": file_url,
                    "subtitle": None,
                    "createdAt": "2025-01-15T00:00:00.000Z",
                    "issue": {
                        "id": issue_id,
                    },
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_response)

        result = await adapter.attach_file_to_issue(issue_id, file_url, title)

        # Verify attachment record structure
        assert "id" in result
        assert "title" in result
        assert "url" in result
        assert "createdAt" in result
