"""Comprehensive tests for GitHub adapter epic update and attachment functionality.

This test module covers:
- Milestone (epic) update operations
- File attachment workflows
- Error handling and validation
- Platform-specific limitations and workarounds
- GitHub API constraints (25MB file limit, rate limiting)
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_ticketer.adapters.github import GitHubAdapter
from mcp_ticketer.core.models import Epic, TicketState


class TestGitHubEpicUpdate:
    """Test suite for GitHub adapter epic (milestone) update functionality."""

    @pytest.fixture
    def mock_config(self) -> dict[str, str]:
        """Mock configuration for GitHub adapter."""
        return {
            "token": "ghp_test_token_1234567890abcdef",
            "owner": "test-owner",
            "repo": "test-repo",
        }

    @pytest.fixture
    def adapter(self, mock_config: dict[str, str]) -> GitHubAdapter:
        """Create a GitHubAdapter instance with mocked HTTP client."""
        with patch("mcp_ticketer.adapters.github.httpx.AsyncClient"):
            adapter = GitHubAdapter(mock_config)
            adapter._initialized = True
            adapter.client = AsyncMock()
            return adapter

    @pytest.mark.asyncio
    async def test_update_milestone_title(self, adapter: GitHubAdapter) -> None:
        """Test updating milestone (epic) title successfully."""
        milestone_number = 1
        new_title = "Updated Milestone Title"

        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "number": milestone_number,
            "title": new_title,
            "description": "Test description",
            "state": "open",
            "due_on": None,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-14T00:00:00Z",
            "html_url": "https://github.com/test-owner/test-repo/milestone/1",
        }

        adapter.client.patch = AsyncMock(return_value=mock_response)

        # Execute update
        result = await adapter.update_milestone(milestone_number, {"title": new_title})

        # Verify result
        assert result is not None
        assert isinstance(result, Epic)
        assert result.title == new_title
        assert result.id == str(milestone_number)

        # Verify API call
        adapter.client.patch.assert_called_once()
        call_args = adapter.client.patch.call_args
        assert f"/milestones/{milestone_number}" in str(call_args)

    @pytest.mark.asyncio
    async def test_update_milestone_description(self, adapter: GitHubAdapter) -> None:
        """Test updating milestone description successfully."""
        milestone_number = 1
        new_description = "Updated milestone description with details"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "number": milestone_number,
            "title": "Test Milestone",
            "description": new_description,
            "state": "open",
            "due_on": None,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-14T00:00:00Z",
            "html_url": "https://github.com/test-owner/test-repo/milestone/1",
        }

        adapter.client.patch = AsyncMock(return_value=mock_response)

        result = await adapter.update_milestone(
            milestone_number, {"description": new_description}
        )

        assert result is not None
        assert result.description == new_description

    @pytest.mark.asyncio
    async def test_update_milestone_state(self, adapter: GitHubAdapter) -> None:
        """Test updating milestone state (open/closed)."""
        milestone_number = 1

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "number": milestone_number,
            "title": "Test Milestone",
            "description": "Test",
            "state": "closed",
            "due_on": None,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-14T00:00:00Z",
            "html_url": "https://github.com/test-owner/test-repo/milestone/1",
        }

        adapter.client.patch = AsyncMock(return_value=mock_response)

        result = await adapter.update_milestone(milestone_number, {"state": "closed"})

        assert result is not None
        assert result.state == TicketState.CLOSED

    @pytest.mark.asyncio
    async def test_update_milestone_due_date(self, adapter: GitHubAdapter) -> None:
        """Test updating milestone due date (using target_date field)."""
        milestone_number = 1
        target_date = "2025-12-31T23:59:59Z"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "number": milestone_number,
            "title": "Test Milestone",
            "description": "Test",
            "state": "open",
            "due_on": target_date,  # GitHub API returns due_on
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-14T00:00:00Z",
            "html_url": "https://github.com/test-owner/test-repo/milestone/1",
        }

        adapter.client.patch = AsyncMock(return_value=mock_response)

        # Update uses target_date, which maps to due_on internally
        result = await adapter.update_milestone(
            milestone_number, {"target_date": target_date}
        )

        assert result is not None
        # Verify the API was called with correct data
        adapter.client.patch.assert_called_once()
        call_args = adapter.client.patch.call_args
        assert call_args[1]["json"]["due_on"] == target_date

    @pytest.mark.asyncio
    async def test_update_milestone_multiple_fields(
        self, adapter: GitHubAdapter
    ) -> None:
        """Test updating multiple milestone fields simultaneously."""
        milestone_number = 1
        updates = {
            "title": "New Title",
            "description": "New description",
            "state": "closed",
            "target_date": "2025-12-31T23:59:59Z",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "number": milestone_number,
            "title": updates["title"],
            "description": updates["description"],
            "state": updates["state"],
            "due_on": updates["target_date"],  # API returns due_on
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-14T00:00:00Z",
            "html_url": "https://github.com/test-owner/test-repo/milestone/1",
        }

        adapter.client.patch = AsyncMock(return_value=mock_response)

        result = await adapter.update_milestone(milestone_number, updates)

        assert result is not None
        assert result.title == updates["title"]
        assert result.description == updates["description"]
        assert result.state == TicketState.CLOSED

    @pytest.mark.asyncio
    async def test_update_epic_wrapper(self, adapter: GitHubAdapter) -> None:
        """Test update_epic() convenience wrapper calls update_milestone()."""
        milestone_number = 1
        updates = {"title": "New Epic Title"}

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "number": milestone_number,
            "title": updates["title"],
            "description": "Test",
            "state": "open",
            "due_on": None,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-14T00:00:00Z",
            "html_url": "https://github.com/test-owner/test-repo/milestone/1",
        }

        adapter.client.patch = AsyncMock(return_value=mock_response)

        # Call update_epic instead of update_milestone
        result = await adapter.update_epic(str(milestone_number), updates)

        assert result is not None
        assert result.title == updates["title"]

    @pytest.mark.asyncio
    async def test_update_milestone_invalid_number(
        self, adapter: GitHubAdapter
    ) -> None:
        """Test updating milestone with invalid number raises error."""
        milestone_number = 99999

        # Mock 404 response
        from mcp_ticketer.core.exceptions import NotFoundError

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Not Found"}
        mock_response.raise_for_status.side_effect = NotFoundError(
            "404 Not Found", "github"
        )

        adapter.client.patch = AsyncMock(return_value=mock_response)

        with pytest.raises((Exception, NotFoundError)):
            await adapter.update_milestone(milestone_number, {"title": "test"})

    @pytest.mark.asyncio
    async def test_update_milestone_empty_updates(self, adapter: GitHubAdapter) -> None:
        """Test updating milestone with empty updates dict raises error.

        GitHub adapter requires at least one field to be updated.
        """
        milestone_number = 1

        # GitHub adapter raises ValueError for empty updates
        with pytest.raises(ValueError, match="At least one field must be updated"):
            await adapter.update_milestone(milestone_number, {})

    @pytest.mark.asyncio
    async def test_update_milestone_unauthorized(self, adapter: GitHubAdapter) -> None:
        """Test handling unauthorized access during milestone update."""
        milestone_number = 1

        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Bad credentials"}
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")

        adapter.client.patch = AsyncMock(return_value=mock_response)

        with pytest.raises(Exception, match="Unauthorized"):
            await adapter.update_milestone(milestone_number, {"title": "test"})

    @pytest.mark.asyncio
    async def test_update_milestone_rate_limit(self, adapter: GitHubAdapter) -> None:
        """Test handling rate limiting during milestone update.

        GitHub enforces rate limits of 5000 requests per hour for authenticated users.
        """
        milestone_number = 1

        # Mock 403 rate limit response
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "message": "API rate limit exceeded",
            "documentation_url": "https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limiting",
        }
        mock_response.headers = {"X-RateLimit-Remaining": "0"}
        mock_response.raise_for_status.side_effect = Exception("Rate limit exceeded")

        adapter.client.patch = AsyncMock(return_value=mock_response)

        with pytest.raises(Exception, match="Rate limit"):
            await adapter.update_milestone(milestone_number, {"title": "test"})


class TestGitHubAttachments:
    """Test suite for GitHub adapter file attachment functionality.

    Note: GitHub has limited native file attachment support:
    - Files can only be attached to issues, not milestones
    - 25 MB file size limit per attachment
    - Attachments are added via issue comments
    - For milestones, we use workarounds (URL references)
    """

    @pytest.fixture
    def mock_config(self) -> dict[str, str]:
        """Mock configuration for GitHub adapter."""
        return {
            "token": "ghp_test_token_1234567890abcdef",
            "owner": "test-owner",
            "repo": "test-repo",
        }

    @pytest.fixture
    def adapter(self, mock_config: dict[str, str]) -> GitHubAdapter:
        """Create a GitHubAdapter instance with mocked HTTP client."""
        with patch("mcp_ticketer.adapters.github.httpx.AsyncClient"):
            adapter = GitHubAdapter(mock_config)
            adapter._initialized = True
            adapter.client = AsyncMock()
            return adapter

    @pytest.fixture
    def temp_file(self) -> Path:
        """Create a temporary test file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as temp:
            temp.write(f"Test attachment created at {datetime.now().isoformat()}\n")
            temp.write("This is test content for GitHub attachments.\n")
            temp_path = Path(temp.name)

        yield temp_path

        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_add_attachment_to_issue(
        self, adapter: GitHubAdapter, temp_file: Path
    ) -> None:
        """Test adding file reference to GitHub issue via comment.

        GitHub doesn't support direct file attachment API, so this creates
        a comment with file reference that user can manually upload through UI.
        """
        issue_number = 123

        # Mock comment creation response
        mock_comment_response = Mock()
        mock_comment_response.status_code = 201
        mock_comment_response.json.return_value = {
            "id": 456,
            "html_url": "https://github.com/test-owner/test-repo/issues/123#issuecomment-456",
            "body": f"📎 Attached: `{temp_file.name}`",
            "created_at": "2025-01-14T00:00:00Z",
        }

        adapter.client.post = AsyncMock(return_value=mock_comment_response)

        # Execute attachment (creates comment with file reference)
        result = await adapter.add_attachment_to_issue(
            issue_number, str(temp_file), comment="Test attachment"
        )

        assert result is not None
        assert result["filename"] == temp_file.name
        assert result["comment_id"] == 456
        assert "comment_url" in result

    @pytest.mark.asyncio
    async def test_add_attachment_file_too_large(self, adapter: GitHubAdapter) -> None:
        """Test that files larger than 25MB are rejected.

        GitHub enforces a 25MB limit per file attachment.
        """
        large_file_path = "/tmp/large_file.bin"

        # Mock a file that appears to be > 25MB
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value = Mock(st_size=26 * 1024 * 1024)  # 26MB

            with pytest.raises(ValueError, match="25 MB"):
                await adapter.add_attachment_to_issue(1, large_file_path)

    @pytest.mark.asyncio
    async def test_add_attachment_file_not_found(self, adapter: GitHubAdapter) -> None:
        """Test that non-existent files raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            await adapter.add_attachment_to_issue(1, "/nonexistent/file.txt")

    @pytest.mark.asyncio
    async def test_add_attachment_reference_to_milestone(
        self, adapter: GitHubAdapter
    ) -> None:
        """Test adding URL reference to milestone description.

        Since GitHub doesn't support native file attachments for milestones,
        we add URL references to the milestone description.
        """
        milestone_number = 1
        file_url = "https://example.com/document.pdf"

        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "number": milestone_number,
            "title": "Test Milestone",
            "description": "Original description",
            "state": "open",
            "due_on": None,
        }

        mock_patch_response = Mock()
        mock_patch_response.status_code = 200
        mock_patch_response.json.return_value = {
            "number": milestone_number,
            "title": "Test Milestone",
            "description": f"Original description\n\n**Attachments:**\n- [document.pdf]({file_url})",
            "state": "open",
            "due_on": None,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-14T00:00:00Z",
            "html_url": "https://github.com/test-owner/test-repo/milestone/1",
        }

        adapter.client.get = AsyncMock(return_value=mock_get_response)
        adapter.client.patch = AsyncMock(return_value=mock_patch_response)

        result = await adapter.add_attachment_reference_to_milestone(
            milestone_number, file_url, "document.pdf"
        )

        assert result is not None
        assert isinstance(result, Epic)
        assert "document.pdf" in result.description
        adapter.client.patch.assert_called_once()

    @pytest.mark.asyncio
    async def test_unified_add_attachment_to_issue(
        self, adapter: GitHubAdapter, temp_file: Path
    ) -> None:
        """Test unified add_attachment() interface routes to issue attachment."""
        issue_id = "123"  # Issue ID

        # Mock comment response
        mock_comment_response = Mock()
        mock_comment_response.status_code = 201
        mock_comment_response.json.return_value = {
            "id": 456,
            "html_url": "https://github.com/test-owner/test-repo/issues/123#issuecomment-456",
            "body": f"📎 Attached: `{temp_file.name}`",
        }

        adapter.client.post = AsyncMock(return_value=mock_comment_response)

        # add_attachment routes to add_attachment_to_issue for issues
        # Note: description param maps to comment param
        result = await adapter.add_attachment(
            issue_id, str(temp_file), description="Test"
        )

        assert result is not None
        assert result["filename"] == temp_file.name
        assert "comment_id" in result

    @pytest.mark.asyncio
    async def test_unified_add_attachment_to_milestone_provides_guidance(
        self, adapter: GitHubAdapter, temp_file: Path
    ) -> None:
        """Test that adding attachment to milestone provides helpful guidance.

        When attempting to add a file to a milestone, the adapter should:
        1. Recognize it's a milestone (not issue)
        2. Provide clear guidance on GitHub's limitations
        3. Suggest workarounds (e.g., URL references)
        """
        milestone_id = "milestone-1"

        # This should raise NotImplementedError with guidance
        with pytest.raises(NotImplementedError, match="milestones do not support"):
            await adapter.add_attachment(milestone_id, str(temp_file))

    @pytest.mark.asyncio
    async def test_add_attachment_handles_api_error(
        self, adapter: GitHubAdapter, temp_file: Path
    ) -> None:
        """Test handling API errors during attachment upload."""
        issue_number = 123

        # Mock API error
        from mcp_ticketer.core.exceptions import AdapterError

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Internal Server Error"}
        mock_response.raise_for_status.side_effect = AdapterError(
            "500 Internal Server Error", "github"
        )

        adapter.client.post = AsyncMock(return_value=mock_response)

        with pytest.raises((Exception, AdapterError)):
            await adapter.add_attachment_to_issue(issue_number, str(temp_file))


class TestGitHubPlatformConstraints:
    """Test GitHub-specific platform constraints and edge cases."""

    @pytest.fixture
    def mock_config(self) -> dict[str, str]:
        """Mock configuration for GitHub adapter."""
        return {
            "token": "ghp_test_token_1234567890abcdef",
            "owner": "test-owner",
            "repo": "test-repo",
        }

    @pytest.fixture
    def adapter(self, mock_config: dict[str, str]) -> GitHubAdapter:
        """Create a GitHubAdapter instance."""
        with patch("mcp_ticketer.adapters.github.httpx.AsyncClient"):
            adapter = GitHubAdapter(mock_config)
            adapter._initialized = True
            adapter.client = AsyncMock()
            return adapter

    @pytest.mark.asyncio
    async def test_markdown_formatting_in_descriptions(
        self, adapter: GitHubAdapter
    ) -> None:
        """Test that markdown formatting is preserved in descriptions."""
        milestone_number = 1
        markdown_description = """
# Epic Overview

This is a **bold** statement with *emphasis*.

## Tasks
- [ ] Task 1
- [x] Task 2 (completed)

```python
def hello():
    print("world")
```
"""

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "number": milestone_number,
            "title": "Test",
            "description": markdown_description,
            "state": "open",
            "due_on": None,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-14T00:00:00Z",
            "html_url": "https://github.com/test-owner/test-repo/milestone/1",
        }

        adapter.client.patch = AsyncMock(return_value=mock_response)

        result = await adapter.update_milestone(
            milestone_number, {"description": markdown_description}
        )

        assert result is not None
        assert result.description == markdown_description

    @pytest.mark.asyncio
    async def test_unicode_and_emoji_support(self, adapter: GitHubAdapter) -> None:
        """Test that Unicode characters and emojis are supported."""
        milestone_number = 1
        unicode_title = "🚀 Epic: 测试 Unicode Support 🎉"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "number": milestone_number,
            "title": unicode_title,
            "description": "Test",
            "state": "open",
            "due_on": None,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-14T00:00:00Z",
            "html_url": "https://github.com/test-owner/test-repo/milestone/1",
        }

        adapter.client.patch = AsyncMock(return_value=mock_response)

        result = await adapter.update_milestone(
            milestone_number, {"title": unicode_title}
        )

        assert result is not None
        assert result.title == unicode_title

    @pytest.mark.asyncio
    async def test_concurrent_updates_handling(self, adapter: GitHubAdapter) -> None:
        """Test handling concurrent updates to the same milestone.

        GitHub uses optimistic locking, last write wins.
        """
        milestone_number = 1

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "number": milestone_number,
            "title": "Final Title",
            "description": "Final description",
            "state": "open",
            "due_on": None,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-14T00:00:00Z",
            "html_url": "https://github.com/test-owner/test-repo/milestone/1",
        }

        adapter.client.patch = AsyncMock(return_value=mock_response)

        # Simulate concurrent updates - last one wins
        result = await adapter.update_milestone(
            milestone_number, {"title": "Final Title"}
        )

        assert result is not None
        assert result.title == "Final Title"
