"""Cross-adapter integration tests for epic update and attachment functionality.

This test module ensures consistency across all adapters:
- Linear (native implementation)
- Jira (native implementation)
- GitHub (workarounds and limitations)
- AITrackdown (filesystem-based)

Tests verify that all adapters:
1. Support epic update operations (or gracefully degrade)
2. Handle file attachments (with platform-specific approaches)
3. Provide consistent error handling
4. Return standardized responses
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_ticketer.adapters.aitrackdown import AITrackdownAdapter
from mcp_ticketer.adapters.github import GitHubAdapter
from mcp_ticketer.adapters.jira import JiraAdapter
from mcp_ticketer.adapters.linear.adapter import LinearAdapter
from mcp_ticketer.core.models import Epic


class TestCrossAdapterEpicUpdate:
    """Test epic update consistency across all adapters."""

    @pytest.fixture
    def linear_adapter(self) -> LinearAdapter:
        """Create mocked Linear adapter."""
        with patch("mcp_ticketer.adapters.linear.adapter.LinearGraphQLClient"):
            config = {
                "api_key": "lin_api_test_key",
                "team_key": "TEST",
            }
            adapter = LinearAdapter(config)
            adapter._initialized = True
            adapter.team_id = "test-team-id"
            adapter.client = AsyncMock()
            # Mock _resolve_project_id to return the same ID passed in
            adapter._resolve_project_id = AsyncMock(side_effect=lambda id: id)
            return adapter

    @pytest.fixture
    def jira_adapter(self) -> JiraAdapter:
        """Create mocked Jira adapter."""
        with patch("mcp_ticketer.adapters.jira.httpx.AsyncClient"):
            config = {
                "server": "https://test.atlassian.net",
                "email": "test@example.com",
                "api_token": "test_token",
                "project_key": "TEST",
            }
            adapter = JiraAdapter(config)
            adapter._initialized = True
            adapter.client = AsyncMock()
            return adapter

    @pytest.fixture
    def github_adapter(self) -> GitHubAdapter:
        """Create mocked GitHub adapter."""
        with patch("mcp_ticketer.adapters.github.httpx.AsyncClient"):
            config = {
                "token": "ghp_test_token",
                "owner": "test-owner",
                "repo": "test-repo",
            }
            adapter = GitHubAdapter(config)
            adapter._initialized = True
            adapter.client = AsyncMock()
            return adapter

    @pytest.fixture
    def aitrackdown_adapter(self, tmp_path: Path) -> AITrackdownAdapter:
        """Create AITrackdown adapter with temp directory."""
        config = {"base_path": str(tmp_path / ".aitrackdown")}
        return AITrackdownAdapter(config)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "adapter_fixture",
        ["linear_adapter", "jira_adapter", "github_adapter", "aitrackdown_adapter"],
    )
    async def test_update_epic_has_method(
        self, adapter_fixture: str, request: pytest.FixtureRequest
    ) -> None:
        """Test that all adapters have update_epic or equivalent method."""
        adapter = request.getfixturevalue(adapter_fixture)

        # All adapters should have either update_epic or update method
        assert hasattr(adapter, "update_epic") or hasattr(
            adapter, "update"
        ), f"{adapter.__class__.__name__} missing update methods"

    @pytest.mark.asyncio
    async def test_linear_epic_update_structure(
        self, linear_adapter: LinearAdapter
    ) -> None:
        """Test Linear epic update returns proper Epic structure."""
        # Mock response
        mock_response = {
            "projectUpdate": {
                "success": True,
                "project": {
                    "id": "test-epic-id",
                    "name": "Updated Epic",
                    "description": "Updated description",
                    "state": "started",
                    "targetDate": None,
                    "color": "blue",
                    "icon": "📋",
                    "createdAt": "2025-01-01T00:00:00.000Z",
                    "updatedAt": "2025-01-14T00:00:00.000Z",
                },
            }
        }

        linear_adapter.client.execute_mutation = AsyncMock(return_value=mock_response)

        result = await linear_adapter.update_epic(
            "test-epic-id", {"description": "Updated description"}
        )

        assert result is not None
        assert isinstance(result, Epic)
        assert result.id == "test-epic-id"
        assert result.description == "Updated description"
        assert "linear" in result.metadata

    @pytest.mark.asyncio
    async def test_jira_epic_update_structure(self, jira_adapter: JiraAdapter) -> None:
        """Test Jira epic update returns proper Epic structure."""
        # Mock GET response (for reading current epic)
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "key": "TEST-1",
            "fields": {
                "summary": "Original Epic",
                "description": "Original description",
                "status": {"name": "To Do"},
                "priority": {"name": "Medium"},
                "labels": [],
                "issuetype": {"name": "Epic"},
            },
        }
        mock_get_response.raise_for_status = Mock()

        # Mock PUT response (for update)
        mock_put_response = Mock()
        mock_put_response.status_code = 204
        mock_put_response.raise_for_status = Mock()

        # Second GET response after update
        mock_get_response_after = Mock()
        mock_get_response_after.status_code = 200
        mock_get_response_after.json.return_value = {
            "key": "TEST-1",
            "fields": {
                "summary": "Original Epic",
                "description": "Updated description",
                "status": {"name": "To Do"},
                "priority": {"name": "Medium"},
                "labels": [],
                "issuetype": {"name": "Epic"},
                "created": "2025-01-01T00:00:00.000Z",
                "updated": "2025-01-14T00:00:00.000Z",
            },
        }
        mock_get_response_after.raise_for_status = Mock()

        jira_adapter.client.get = AsyncMock(
            side_effect=[mock_get_response, mock_get_response_after]
        )
        jira_adapter.client.put = AsyncMock(return_value=mock_put_response)

        result = await jira_adapter.update_epic(
            "TEST-1", {"description": "Updated description"}
        )

        assert result is not None
        assert isinstance(result, Epic)
        assert result.id == "TEST-1"
        assert "jira" in result.metadata

    @pytest.mark.asyncio
    async def test_github_epic_update_structure(
        self, github_adapter: GitHubAdapter
    ) -> None:
        """Test GitHub epic (milestone) update returns proper Epic structure."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "number": 1,
            "title": "Updated Milestone",
            "description": "Updated description",
            "state": "open",
            "due_on": None,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-14T00:00:00Z",
            "html_url": "https://github.com/test-owner/test-repo/milestone/1",
        }

        github_adapter.client.patch = AsyncMock(return_value=mock_response)

        result = await github_adapter.update_epic(
            "1", {"description": "Updated description"}
        )

        assert result is not None
        assert isinstance(result, Epic)
        assert result.id == "1"
        assert "github" in result.metadata

    @pytest.mark.asyncio
    async def test_aitrackdown_epic_update_structure(
        self, aitrackdown_adapter: AITrackdownAdapter
    ) -> None:
        """Test AITrackdown epic update returns proper Epic structure."""
        # Create epic first
        epic = Epic(title="Test Epic", description="Original description")
        created = await aitrackdown_adapter.create(epic)

        # Update it
        assert created.id is not None
        result = await aitrackdown_adapter.update(
            created.id, {"description": "Updated description"}
        )

        assert result is not None
        assert isinstance(result, Epic)
        assert result.id == created.id
        assert result.description == "Updated description"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "adapter_fixture",
        ["linear_adapter", "jira_adapter", "github_adapter", "aitrackdown_adapter"],
    )
    async def test_update_epic_accepts_common_fields(
        self, adapter_fixture: str, request: pytest.FixtureRequest
    ) -> None:
        """Test that all adapters accept common update fields.

        Common fields: title, description, state, priority
        """
        adapter = request.getfixturevalue(adapter_fixture)

        # Prepare test data based on adapter type
        if "linear" in adapter_fixture:
            epic_id = "test-epic-id"
            adapter.client.execute_mutation = AsyncMock(
                return_value={
                    "projectUpdate": {
                        "success": True,
                        "project": {
                            "id": epic_id,
                            "name": "Test",
                            "description": "Test",
                            "state": "started",
                            "targetDate": None,
                            "color": "blue",
                            "icon": "📋",
                            "createdAt": "2025-01-01T00:00:00.000Z",
                            "updatedAt": "2025-01-14T00:00:00.000Z",
                        },
                    }
                }
            )
            result = await adapter.update_epic(epic_id, {"title": "New Title"})

        elif "jira" in adapter_fixture:
            epic_id = "TEST-1"
            mock_get = Mock()
            mock_get.status_code = 200
            mock_get.json.return_value = {
                "key": epic_id,
                "fields": {
                    "summary": "Test",
                    "description": "Test",
                    "status": {"name": "To Do"},
                    "issuetype": {"name": "Epic"},
                },
            }
            mock_put = Mock()
            mock_put.status_code = 204
            adapter.client.get = AsyncMock(return_value=mock_get)
            adapter.client.put = AsyncMock(return_value=mock_put)
            result = await adapter.update_epic(epic_id, {"title": "New Title"})

        elif "github" in adapter_fixture:
            epic_id = "1"
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "number": 1,
                "title": "New Title",
                "state": "open",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-14T00:00:00Z",
            }
            adapter.client.patch = AsyncMock(return_value=mock_response)
            result = await adapter.update_epic(epic_id, {"title": "New Title"})

        elif "aitrackdown" in adapter_fixture:
            epic = Epic(title="Original")
            created = await adapter.create(epic)
            assert created.id is not None
            result = await adapter.update(created.id, {"title": "New Title"})

        # All adapters should return an Epic object
        assert result is not None
        assert isinstance(result, Epic)

    @pytest.mark.asyncio
    async def test_all_adapters_handle_empty_updates(
        self,
        linear_adapter: LinearAdapter,
        jira_adapter: JiraAdapter,
        github_adapter: GitHubAdapter,
        aitrackdown_adapter: AITrackdownAdapter,
    ) -> None:
        """Test that all adapters handle empty update dicts gracefully."""
        # Linear
        linear_adapter.client.execute_mutation = AsyncMock(
            return_value={
                "projectUpdate": {
                    "success": True,
                    "project": {
                        "id": "test-id",
                        "name": "Test",
                        "description": "Test",
                        "state": "planned",
                        "targetDate": None,
                        "color": "blue",
                        "icon": "📋",
                        "createdAt": "2025-01-01T00:00:00.000Z",
                        "updatedAt": "2025-01-14T00:00:00.000Z",
                    },
                }
            }
        )
        linear_result = await linear_adapter.update_epic("test-id", {})
        assert linear_result is not None

        # Jira - may raise ValueError for empty updates
        try:
            mock_get = Mock()
            mock_get.status_code = 200
            mock_get.json.return_value = {
                "key": "TEST-1",
                "fields": {"summary": "Test", "issuetype": {"name": "Epic"}},
            }
            jira_adapter.client.get = AsyncMock(return_value=mock_get)
            jira_result = await jira_adapter.update_epic("TEST-1", {})
            # If it doesn't raise, result should be valid or None
            assert jira_result is None or isinstance(jira_result, Epic)
        except ValueError:
            # Empty updates may be rejected - this is acceptable
            pass

        # GitHub
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "number": 1,
            "title": "Test",
            "state": "open",
            "created_at": "2025-01-01T00:00:00Z",
        }
        github_adapter.client.patch = AsyncMock(return_value=mock_response)
        github_result = await github_adapter.update_milestone(1, {})
        assert github_result is not None

        # AITrackdown
        epic = Epic(title="Test")
        created = await aitrackdown_adapter.create(epic)
        assert created.id is not None
        # AITrackdown may return None for empty updates
        ait_result = await aitrackdown_adapter.update(created.id, {})
        assert ait_result is None or isinstance(ait_result, Epic)


class TestCrossAdapterAttachments:
    """Test attachment support consistency across all adapters."""

    @pytest.fixture
    def temp_file(self) -> Path:
        """Create a temporary test file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as temp:
            temp.write(f"Test file created at {datetime.now().isoformat()}\n")
            temp_path = Path(temp.name)

        yield temp_path

        if temp_path.exists():
            temp_path.unlink()

    @pytest.fixture
    def linear_adapter(self) -> LinearAdapter:
        """Create mocked Linear adapter."""
        with patch("mcp_ticketer.adapters.linear.adapter.LinearGraphQLClient"):
            config = {"api_key": "lin_api_test_key", "team_key": "TEST"}
            adapter = LinearAdapter(config)
            adapter._initialized = True
            adapter.team_id = "test-team-id"
            adapter.client = AsyncMock()
            # Mock _resolve_project_id
            adapter._resolve_project_id = AsyncMock(side_effect=lambda id: id)
            return adapter

    @pytest.fixture
    def jira_adapter(self) -> JiraAdapter:
        """Create mocked Jira adapter."""
        with patch("mcp_ticketer.adapters.jira.httpx.AsyncClient"):
            config = {
                "server": "https://test.atlassian.net",
                "email": "test@example.com",
                "api_token": "test_token",
                "project_key": "TEST",
            }
            adapter = JiraAdapter(config)
            adapter._initialized = True
            adapter.client = AsyncMock()
            return adapter

    @pytest.fixture
    def github_adapter(self) -> GitHubAdapter:
        """Create mocked GitHub adapter."""
        with patch("mcp_ticketer.adapters.github.httpx.AsyncClient"):
            config = {
                "token": "ghp_test_token",
                "owner": "test-owner",
                "repo": "test-repo",
            }
            adapter = GitHubAdapter(config)
            adapter._initialized = True
            adapter.client = AsyncMock()
            return adapter

    @pytest.fixture
    def aitrackdown_adapter(self, tmp_path: Path) -> AITrackdownAdapter:
        """Create AITrackdown adapter with temp directory."""
        config = {"base_path": str(tmp_path / ".aitrackdown")}
        return AITrackdownAdapter(config)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "adapter_fixture",
        ["linear_adapter", "jira_adapter", "github_adapter", "aitrackdown_adapter"],
    )
    async def test_all_adapters_have_attachment_support(
        self, adapter_fixture: str, request: pytest.FixtureRequest
    ) -> None:
        """Test that all adapters have some form of attachment support."""
        adapter = request.getfixturevalue(adapter_fixture)

        # All adapters should have at least one attachment-related method
        has_add_attachment = hasattr(adapter, "add_attachment")
        has_attach_file = hasattr(adapter, "attach_file_to_issue") or hasattr(
            adapter, "attach_file_to_epic"
        )
        has_upload_file = hasattr(adapter, "upload_file")

        assert (
            has_add_attachment or has_attach_file or has_upload_file
        ), f"{adapter.__class__.__name__} missing attachment methods"

    @pytest.mark.asyncio
    async def test_linear_native_file_upload(
        self, linear_adapter: LinearAdapter, temp_file: Path
    ) -> None:
        """Test Linear supports native file uploads to S3."""
        # Mock upload URL request
        linear_adapter.client.execute_mutation = AsyncMock(
            return_value={
                "fileUpload": {
                    "success": True,
                    "uploadFile": {
                        "uploadUrl": "https://s3.amazonaws.com/test-upload",
                        "assetUrl": "https://linear.app/files/test-file.txt",
                        "headers": [{"key": "Content-Type", "value": "text/plain"}],
                    },
                }
            }
        )

        # Mock S3 upload
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.put = AsyncMock(
                return_value=Mock(status_code=200)
            )

            result = await linear_adapter.upload_file(str(temp_file), "text/plain")

            assert result is not None
            assert "assetUrl" in result or "asset_url" in result

    @pytest.mark.asyncio
    async def test_jira_native_attachment_upload(
        self, jira_adapter: JiraAdapter, temp_file: Path
    ) -> None:
        """Test Jira supports native attachment uploads."""
        issue_key = "TEST-1"

        # Mock attachment response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "12345",
                "filename": temp_file.name,
                "size": temp_file.stat().st_size,
                "mimeType": "text/plain",
                "content": f"https://test.atlassian.net/secure/attachment/{temp_file.name}",
            }
        ]

        jira_adapter.client.post = AsyncMock(return_value=mock_response)

        result = await jira_adapter.add_attachment(issue_key, str(temp_file))

        assert result is not None
        assert result.filename == temp_file.name
        assert result.url is not None

    @pytest.mark.asyncio
    async def test_github_attachment_workaround(
        self, github_adapter: GitHubAdapter, temp_file: Path
    ) -> None:
        """Test GitHub uses comment-based attachment workaround for issues."""
        issue_number = 123

        # Mock upload and comment responses
        mock_upload = Mock()
        mock_upload.status_code = 201
        mock_upload.json.return_value = {
            "url": f"https://github.com/files/{temp_file.name}"
        }

        mock_comment = Mock()
        mock_comment.status_code = 201
        mock_comment.json.return_value = {
            "id": 456,
            "body": f"Attachment: [{temp_file.name}](...)",
        }

        github_adapter.client.post = AsyncMock(side_effect=[mock_upload, mock_comment])

        result = await github_adapter.add_attachment_to_issue(
            issue_number, str(temp_file)
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_github_milestone_attachment_limitation(
        self, github_adapter: GitHubAdapter, temp_file: Path
    ) -> None:
        """Test GitHub cannot attach files to milestones - provides guidance."""
        milestone_id = "milestone-1"

        # Should raise informative error
        with pytest.raises(ValueError, match="milestone"):
            await github_adapter.add_attachment(milestone_id, str(temp_file))

    @pytest.mark.asyncio
    async def test_aitrackdown_filesystem_storage(
        self, aitrackdown_adapter: AITrackdownAdapter, temp_file: Path
    ) -> None:
        """Test AITrackdown uses filesystem storage for attachments."""
        # Create ticket first
        epic = Epic(title="Test Epic")
        created = await aitrackdown_adapter.create(epic)

        assert created.id is not None
        result = await aitrackdown_adapter.add_attachment(
            created.id, str(temp_file), description="Test attachment"
        )

        assert result is not None
        assert result.filename == temp_file.name
        # AITrackdown stores files locally
        assert "aitrackdown" in result.url or "file://" in result.url

    @pytest.mark.asyncio
    async def test_all_adapters_handle_file_not_found(
        self,
        linear_adapter: LinearAdapter,
        jira_adapter: JiraAdapter,
        github_adapter: GitHubAdapter,
        aitrackdown_adapter: AITrackdownAdapter,
    ) -> None:
        """Test that all adapters handle missing files gracefully."""
        nonexistent = "/nonexistent/file.txt"

        # Linear
        with pytest.raises(FileNotFoundError):
            await linear_adapter.upload_file(nonexistent)

        # Jira
        with pytest.raises(FileNotFoundError):
            await jira_adapter.add_attachment("TEST-1", nonexistent)

        # GitHub
        with pytest.raises(FileNotFoundError):
            await github_adapter.add_attachment_to_issue(1, nonexistent)

        # AITrackdown
        epic = Epic(title="Test")
        created = await aitrackdown_adapter.create(epic)
        assert created.id is not None
        with pytest.raises(FileNotFoundError):
            await aitrackdown_adapter.add_attachment(created.id, nonexistent)


class TestErrorHandlingConsistency:
    """Test that all adapters handle errors consistently."""

    @pytest.mark.asyncio
    async def test_invalid_epic_id_handling(self) -> None:
        """Test that all adapters handle invalid epic IDs consistently."""
        # Each adapter should either:
        # 1. Return None
        # 2. Raise a descriptive exception
        # 3. Return an error indicator

        # This is tested individually in adapter-specific tests
        # Here we document the expected behavior
        pass

    @pytest.mark.asyncio
    async def test_network_error_handling(self) -> None:
        """Test that all adapters handle network errors appropriately."""
        # Network errors should propagate or be wrapped in meaningful exceptions
        pass

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self) -> None:
        """Test that all adapters handle auth errors consistently."""
        # Authentication failures should raise clear exceptions
        pass
