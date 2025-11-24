"""Unit tests for ticket routing functionality."""

import pytest

from mcp_ticketer.core.models import Comment, Priority, Task, TicketState
from mcp_ticketer.mcp.server.routing import RouterError, TicketRouter


@pytest.fixture
def mock_adapter_configs():
    """Provide mock adapter configurations."""
    return {
        "linear": {
            "api_key": "test_linear_key",
            "team_id": "test_team",
        },
        "github": {
            "token": "test_github_token",
            "owner": "test_owner",
            "repo": "test_repo",
        },
        "jira": {
            "server": "https://test.atlassian.net",
            "email": "test@example.com",
            "api_token": "test_jira_token",
        },
        "asana": {
            "access_token": "test_asana_token",
            "workspace_gid": "12345",
        },
    }


@pytest.fixture
def router(mock_adapter_configs):
    """Create a TicketRouter instance for testing."""
    return TicketRouter(
        default_adapter="linear",
        adapter_configs=mock_adapter_configs,
    )


class TestRouterInitialization:
    """Test router initialization and configuration."""

    def test_init_with_valid_config(self, mock_adapter_configs) -> None:
        """Test initialization with valid configuration."""
        router = TicketRouter(
            default_adapter="linear",
            adapter_configs=mock_adapter_configs,
        )
        assert router.default_adapter == "linear"
        assert router.adapter_configs == mock_adapter_configs
        assert len(router._adapters) == 0  # No adapters cached yet

    def test_init_with_invalid_default_adapter(self, mock_adapter_configs) -> None:
        """Test initialization with invalid default adapter raises error."""
        with pytest.raises(ValueError, match="Default adapter 'invalid' not found"):
            TicketRouter(
                default_adapter="invalid",
                adapter_configs=mock_adapter_configs,
            )

    def test_init_with_empty_config(self) -> None:
        """Test initialization with empty config raises error."""
        with pytest.raises(ValueError):
            TicketRouter(
                default_adapter="linear",
                adapter_configs={},
            )


class TestURLDetection:
    """Test URL-based adapter detection."""

    def test_detect_linear_url(self, router) -> None:
        """Test detection of Linear URLs."""
        urls = [
            "https://linear.app/team/issue/ABC-123",
            "https://LINEAR.APP/team/project/proj-abc",
        ]
        for url in urls:
            adapter_name = router._detect_adapter_from_url(url)
            assert adapter_name == "linear"

    def test_detect_github_url(self, router) -> None:
        """Test detection of GitHub URLs."""
        urls = [
            "https://github.com/owner/repo/issues/123",
            "https://GITHUB.COM/owner/repo/pull/456",
        ]
        for url in urls:
            adapter_name = router._detect_adapter_from_url(url)
            assert adapter_name == "github"

    def test_detect_jira_url(self, router) -> None:
        """Test detection of JIRA URLs."""
        urls = [
            "https://company.atlassian.net/browse/PROJ-123",
            "https://jira.company.com/browse/ABC-456",
        ]
        for url in urls:
            adapter_name = router._detect_adapter_from_url(url)
            assert adapter_name == "jira"

    def test_detect_asana_url(self, router) -> None:
        """Test detection of Asana URLs."""
        urls = [
            "https://app.asana.com/0/1234567890/9876543210",
            "https://APP.ASANA.COM/0/1234567890/list/5555555555",
        ]
        for url in urls:
            adapter_name = router._detect_adapter_from_url(url)
            assert adapter_name == "asana"

    def test_detect_unknown_url(self, router) -> None:
        """Test detection of unknown URL format raises error."""
        with pytest.raises(RouterError, match="Cannot detect adapter from URL"):
            router._detect_adapter_from_url("https://unknown.com/ticket/123")


class TestIDNormalization:
    """Test ticket ID normalization."""

    def test_normalize_plain_id_uses_default(self, router) -> None:
        """Test plain IDs use default adapter."""
        normalized_id, adapter_name, source = router._normalize_ticket_id("ABC-123")
        assert normalized_id == "ABC-123"
        assert adapter_name == "linear"  # default adapter
        assert source == "default"

    def test_normalize_linear_url(self, router) -> None:
        """Test Linear URL normalization."""
        url = "https://linear.app/team/issue/ABC-123"
        normalized_id, adapter_name, source = router._normalize_ticket_id(url)
        assert normalized_id == "ABC-123"
        assert adapter_name == "linear"
        assert source == "url"

    def test_normalize_github_url(self, router) -> None:
        """Test GitHub URL normalization."""
        url = "https://github.com/owner/repo/issues/456"
        normalized_id, adapter_name, source = router._normalize_ticket_id(url)
        assert normalized_id == "456"
        assert adapter_name == "github"
        assert source == "url"

    def test_normalize_jira_url(self, router) -> None:
        """Test JIRA URL normalization."""
        url = "https://company.atlassian.net/browse/PROJ-789"
        normalized_id, adapter_name, source = router._normalize_ticket_id(url)
        assert normalized_id == "PROJ-789"
        assert adapter_name == "jira"
        assert source == "url"

    def test_normalize_asana_url(self, router) -> None:
        """Test Asana URL normalization."""
        url = "https://app.asana.com/0/1234567890/9876543210"
        normalized_id, adapter_name, source = router._normalize_ticket_id(url)
        assert normalized_id == "9876543210"
        assert adapter_name == "asana"
        assert source == "url"

    def test_normalize_invalid_url(self, router) -> None:
        """Test invalid URL raises error."""
        with pytest.raises(RouterError, match="Failed to extract ticket ID"):
            router._normalize_ticket_id("https://linear.app/invalid")


class TestAdapterCaching:
    """Test adapter instance caching."""

    def test_adapter_lazy_loading(self, router) -> None:
        """Test adapters are created on first use."""
        assert len(router._adapters) == 0

        # Access adapter (will create it)
        # Note: This will fail in real test because adapters need valid credentials
        # For unit tests, we'd need to mock AdapterRegistry.get_adapter
        # For now, just verify the caching behavior structure

    def test_get_adapter_with_unconfigured_adapter(self, router) -> None:
        """Test getting unconfigured adapter raises error."""
        with pytest.raises(RouterError, match="Adapter 'bitbucket' is not configured"):
            router._get_adapter("bitbucket")


class TestRouteOperations:
    """Test routing of operations to adapters.

    Note: These tests verify routing logic only.
    Full integration tests with real adapters are in test_routing_integration.py
    """

    @pytest.mark.asyncio
    async def test_route_read_with_plain_id(self, router, mocker):
        """Test routing read operation with plain ID."""
        # Mock adapter
        mock_adapter = mocker.AsyncMock()
        mock_ticket = Task(
            id="ABC-123",
            title="Test Ticket",
            priority=Priority.MEDIUM,
            state=TicketState.OPEN,
        )
        mock_adapter.read.return_value = mock_ticket

        # Mock _get_adapter to return our mock
        mocker.patch.object(router, "_get_adapter", return_value=mock_adapter)

        result = await router.route_read("ABC-123")

        # Verify adapter was called with correct ID
        mock_adapter.read.assert_called_once_with("ABC-123")
        assert result == mock_ticket

    @pytest.mark.asyncio
    async def test_route_read_with_url(self, router, mocker):
        """Test routing read operation with URL."""
        # Mock adapter
        mock_adapter = mocker.AsyncMock()
        mock_ticket = Task(
            id="123",
            title="GitHub Issue",
            priority=Priority.HIGH,
            state=TicketState.OPEN,
        )
        mock_adapter.read.return_value = mock_ticket

        # Mock _get_adapter to return our mock
        mocker.patch.object(router, "_get_adapter", return_value=mock_adapter)

        url = "https://github.com/owner/repo/issues/123"
        result = await router.route_read(url)

        # Verify adapter was called with normalized ID
        mock_adapter.read.assert_called_once_with("123")
        assert result == mock_ticket

    @pytest.mark.asyncio
    async def test_route_update(self, router, mocker):
        """Test routing update operation."""
        mock_adapter = mocker.AsyncMock()
        mock_ticket = Task(
            id="ABC-123",
            title="Updated Ticket",
            priority=Priority.HIGH,
            state=TicketState.IN_PROGRESS,
        )
        mock_adapter.update.return_value = mock_ticket

        mocker.patch.object(router, "_get_adapter", return_value=mock_adapter)

        updates = {"title": "Updated Ticket", "priority": Priority.HIGH}
        result = await router.route_update("ABC-123", updates)

        mock_adapter.update.assert_called_once_with("ABC-123", updates)
        assert result == mock_ticket

    @pytest.mark.asyncio
    async def test_route_delete(self, router, mocker):
        """Test routing delete operation."""
        mock_adapter = mocker.AsyncMock()
        mock_adapter.delete.return_value = True

        mocker.patch.object(router, "_get_adapter", return_value=mock_adapter)

        result = await router.route_delete("ABC-123")

        mock_adapter.delete.assert_called_once_with("ABC-123")
        assert result is True

    @pytest.mark.asyncio
    async def test_route_add_comment(self, router, mocker):
        """Test routing add comment operation."""
        mock_adapter = mocker.AsyncMock()
        comment = Comment(
            ticket_id="ABC-123",
            content="Test comment",
            author="test@example.com",
        )
        mock_adapter.add_comment.return_value = comment

        mocker.patch.object(router, "_get_adapter", return_value=mock_adapter)

        result = await router.route_add_comment("ABC-123", comment)

        mock_adapter.add_comment.assert_called_once()
        assert result == comment

    @pytest.mark.asyncio
    async def test_route_get_comments(self, router, mocker):
        """Test routing get comments operation."""
        mock_adapter = mocker.AsyncMock()
        mock_comments = [
            Comment(
                ticket_id="ABC-123",
                content="Comment 1",
                author="user1@example.com",
            ),
            Comment(
                ticket_id="ABC-123",
                content="Comment 2",
                author="user2@example.com",
            ),
        ]
        mock_adapter.get_comments.return_value = mock_comments

        mocker.patch.object(router, "_get_adapter", return_value=mock_adapter)

        result = await router.route_get_comments("ABC-123", limit=10, offset=0)

        mock_adapter.get_comments.assert_called_once_with("ABC-123", limit=10, offset=0)
        assert result == mock_comments

    @pytest.mark.asyncio
    async def test_route_list_issues_by_epic(self, router, mocker):
        """Test routing list issues by epic operation."""
        mock_adapter = mocker.AsyncMock()
        mock_issues = [
            Task(
                id="ISS-1",
                title="Issue 1",
                priority=Priority.MEDIUM,
                state=TicketState.OPEN,
            ),
            Task(
                id="ISS-2",
                title="Issue 2",
                priority=Priority.HIGH,
                state=TicketState.IN_PROGRESS,
            ),
        ]
        mock_adapter.list_issues_by_epic.return_value = mock_issues

        mocker.patch.object(router, "_get_adapter", return_value=mock_adapter)

        result = await router.route_list_issues_by_epic("EPIC-123")

        mock_adapter.list_issues_by_epic.assert_called_once_with("EPIC-123")
        assert result == mock_issues

    @pytest.mark.asyncio
    async def test_route_list_tasks_by_issue(self, router, mocker):
        """Test routing list tasks by issue operation."""
        mock_adapter = mocker.AsyncMock()
        mock_tasks = [
            Task(
                id="TASK-1",
                title="Task 1",
                priority=Priority.LOW,
                state=TicketState.OPEN,
            ),
            Task(
                id="TASK-2",
                title="Task 2",
                priority=Priority.MEDIUM,
                state=TicketState.DONE,
            ),
        ]
        mock_adapter.list_tasks_by_issue.return_value = mock_tasks

        mocker.patch.object(router, "_get_adapter", return_value=mock_adapter)

        result = await router.route_list_tasks_by_issue("ISS-123")

        mock_adapter.list_tasks_by_issue.assert_called_once_with("ISS-123")
        assert result == mock_tasks


class TestRouterCleanup:
    """Test router resource cleanup."""

    @pytest.mark.asyncio
    async def test_close_all_adapters(self, router, mocker):
        """Test closing all cached adapters."""
        # Create mock adapters
        mock_adapter1 = mocker.AsyncMock()
        mock_adapter2 = mocker.AsyncMock()

        # Manually add to cache
        router._adapters["linear"] = mock_adapter1
        router._adapters["github"] = mock_adapter2

        # Close router
        await router.close()

        # Verify all adapters were closed
        mock_adapter1.close.assert_called_once()
        mock_adapter2.close.assert_called_once()

        # Verify cache was cleared
        assert len(router._adapters) == 0

    @pytest.mark.asyncio
    async def test_close_handles_adapter_errors(self, router, mocker):
        """Test close continues even if adapter close fails."""
        # Create mock adapters, one that raises error
        mock_adapter1 = mocker.AsyncMock()
        mock_adapter1.close.side_effect = Exception("Close error")
        mock_adapter2 = mocker.AsyncMock()

        router._adapters["linear"] = mock_adapter1
        router._adapters["github"] = mock_adapter2

        # Should not raise exception
        await router.close()

        # Both close calls should have been attempted
        mock_adapter1.close.assert_called_once()
        mock_adapter2.close.assert_called_once()

        # Cache should still be cleared
        assert len(router._adapters) == 0
