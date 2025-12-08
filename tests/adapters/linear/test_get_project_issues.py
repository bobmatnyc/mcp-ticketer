"""Unit tests for Linear adapter _get_project_issues method.

This test suite verifies that project issues are fetched correctly
with proper project ID resolution (bug fix for empty epic_issues).
"""

from unittest.mock import AsyncMock, patch

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter
from mcp_ticketer.core.models import Task


@pytest.mark.unit
class TestGetProjectIssues:
    """Test _get_project_issues method with various project ID formats."""

    @pytest.fixture
    def adapter(self) -> LinearAdapter:
        """Create a LinearAdapter instance for testing."""
        config = {
            "api_key": "lin_api_test_key_12345",
            "team_id": "12345678-1234-1234-1234-123456789abc",
        }
        return LinearAdapter(config)

    @pytest.fixture
    def mock_issues_data(self) -> list[dict]:
        """Mock Linear API response for issues query."""
        return [
            {
                "id": "issue-uuid-1",
                "identifier": "TEST-1",
                "title": "Test Issue 1",
                "description": "Description 1",
                "state": {"type": "started", "name": "In Progress"},
                "priority": 1,
                "assignee": None,
                "labels": {"nodes": []},
                "project": {"id": "project-uuid"},
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": "2024-01-01T00:00:00Z",
            },
            {
                "id": "issue-uuid-2",
                "identifier": "TEST-2",
                "title": "Test Issue 2",
                "description": "Description 2",
                "state": {"type": "unstarted", "name": "To Do"},
                "priority": 2,
                "assignee": None,
                "labels": {"nodes": []},
                "project": {"id": "project-uuid"},
                "createdAt": "2024-01-02T00:00:00Z",
                "updatedAt": "2024-01-02T00:00:00Z",
            },
        ]

    @pytest.mark.asyncio
    async def test_get_project_issues_with_short_id(
        self, adapter: LinearAdapter, mock_issues_data: list[dict]
    ) -> None:
        """Test fetching project issues with short ID (12 hex chars).

        This tests that project ID is passed correctly to the filter.
        """
        short_id = "13ddc89e7271"  # Short ID from URL

        # Mock client.execute_query to return issues
        with patch.object(
            adapter.client, "execute_query", new_callable=AsyncMock
        ) as mock_query:
            mock_query.return_value = {"issues": {"nodes": mock_issues_data}}

            # Call method with short ID
            issues = await adapter._get_project_issues(short_id)

            # Verify GraphQL query was called with the project ID
            mock_query.assert_called_once()
            call_args = mock_query.call_args
            filter_arg = call_args[0][1]["filter"]
            assert filter_arg["project"]["id"]["eq"] == short_id

            # Verify issues were returned
            assert len(issues) == 2
            assert all(isinstance(issue, Task) for issue in issues)
            assert issues[0].id == "TEST-1"
            assert issues[1].id == "TEST-2"

    @pytest.mark.asyncio
    async def test_get_project_issues_with_slug_id(
        self, adapter: LinearAdapter, mock_issues_data: list[dict]
    ) -> None:
        """Test fetching project issues with slug-id format."""
        slug_id = "epstein-island-13ddc89e7271"  # From URL

        with patch.object(
            adapter.client, "execute_query", new_callable=AsyncMock
        ) as mock_query:
            mock_query.return_value = {"issues": {"nodes": mock_issues_data}}

            issues = await adapter._get_project_issues(slug_id)

            # Verify the slug ID was passed through to the filter
            call_args = mock_query.call_args
            filter_arg = call_args[0][1]["filter"]
            assert filter_arg["project"]["id"]["eq"] == slug_id
            assert len(issues) == 2

    @pytest.mark.asyncio
    async def test_get_project_issues_with_full_uuid(
        self, adapter: LinearAdapter, mock_issues_data: list[dict]
    ) -> None:
        """Test fetching project issues with full UUID."""
        full_uuid = "12345678-1234-1234-1234-123456789abc"

        with patch.object(
            adapter.client, "execute_query", new_callable=AsyncMock
        ) as mock_query:
            mock_query.return_value = {"issues": {"nodes": mock_issues_data}}

            issues = await adapter._get_project_issues(full_uuid)

            # Verify the UUID was passed through to the filter
            call_args = mock_query.call_args
            filter_arg = call_args[0][1]["filter"]
            assert filter_arg["project"]["id"]["eq"] == full_uuid
            assert len(issues) == 2

    @pytest.mark.asyncio
    async def test_get_project_issues_empty_result(
        self, adapter: LinearAdapter
    ) -> None:
        """Test behavior when no issues are found for the project."""
        project_id = "12345678-1234-1234-1234-123456789abc"

        with patch.object(
            adapter.client, "execute_query", new_callable=AsyncMock
        ) as mock_query:
            mock_query.return_value = {"issues": {"nodes": []}}

            issues = await adapter._get_project_issues(project_id)

            # Should return empty list when no issues found
            assert issues == []

    @pytest.mark.asyncio
    async def test_get_project_issues_query_failure(
        self, adapter: LinearAdapter
    ) -> None:
        """Test behavior when GraphQL query fails."""
        project_id = "12345678-1234-1234-1234-123456789abc"

        with patch.object(
            adapter.client, "execute_query", new_callable=AsyncMock
        ) as mock_query:
            mock_query.side_effect = Exception("GraphQL query failed")

            issues = await adapter._get_project_issues(project_id)

            # Should return empty list on query failure (not raise)
            assert issues == []

    @pytest.mark.asyncio
    async def test_get_project_issues_with_limit(
        self, adapter: LinearAdapter, mock_issues_data: list[dict]
    ) -> None:
        """Test fetching project issues with custom limit."""
        project_id = "12345678-1234-1234-1234-123456789abc"
        custom_limit = 50

        with patch.object(
            adapter.client, "execute_query", new_callable=AsyncMock
        ) as mock_query:
            mock_query.return_value = {"issues": {"nodes": mock_issues_data}}

            await adapter._get_project_issues(project_id, limit=custom_limit)

            # Verify limit was passed to query
            call_args = mock_query.call_args
            variables = call_args[0][1]
            assert variables["first"] == custom_limit

    @pytest.mark.asyncio
    async def test_get_project_issues_max_limit_capped(
        self, adapter: LinearAdapter, mock_issues_data: list[dict]
    ) -> None:
        """Test that limit is capped at Linear API maximum (250)."""
        project_id = "12345678-1234-1234-1234-123456789abc"
        excessive_limit = 1000  # More than Linear API max

        with patch.object(
            adapter.client, "execute_query", new_callable=AsyncMock
        ) as mock_query:
            mock_query.return_value = {"issues": {"nodes": mock_issues_data}}

            await adapter._get_project_issues(project_id, limit=excessive_limit)

            # Verify limit was capped at 250
            call_args = mock_query.call_args
            variables = call_args[0][1]
            assert variables["first"] == 250


@pytest.mark.integration
class TestGetProjectIssuesIntegration:
    """Integration tests for _get_project_issues with real Linear project formats.

    These tests verify the end-to-end flow of project ID resolution and issue fetching.
    """

    @pytest.fixture
    def adapter(self) -> LinearAdapter:
        """Create a LinearAdapter instance for integration testing."""
        config = {
            "api_key": "lin_api_test_key_12345",
            "team_id": "12345678-1234-1234-1234-123456789abc",
        }
        return LinearAdapter(config)

    @pytest.mark.asyncio
    async def test_epic_issues_integration_flow(self, adapter: LinearAdapter) -> None:
        """Test the complete flow: epic_issues tool -> read() -> _get_project_issues().

        This simulates the actual user flow that was failing:
        1. User calls epic_issues("13ddc89e7271")
        2. epic_issues calls adapter.read("13ddc89e7271")
        3. read() fetches project and calls _get_project_issues()
        4. _get_project_issues() resolves ID and queries issues
        """
        short_id = "13ddc89e7271"
        full_uuid = "12345678-1234-1234-1234-123456789abc"

        # Mock project data
        mock_project = {
            "id": full_uuid,
            "name": "Test Project",
            "description": "Test Description",
            "state": "started",
            "teams": {"nodes": []},
        }

        # Mock issue data
        mock_issues = [
            {
                "id": "issue-1",
                "identifier": "TEST-1",
                "title": "Issue 1",
                "state": {"type": "started"},
                "priority": 1,
                "labels": {"nodes": []},
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": "2024-01-01T00:00:00Z",
            }
        ]

        with patch.object(
            adapter, "_resolve_project_id", new_callable=AsyncMock
        ) as mock_resolve:
            mock_resolve.return_value = full_uuid

            with patch.object(
                adapter, "get_project", new_callable=AsyncMock
            ) as mock_get_project:
                mock_get_project.return_value = mock_project

                with patch.object(
                    adapter.client, "execute_query", new_callable=AsyncMock
                ) as mock_query:
                    mock_query.return_value = {"issues": {"nodes": mock_issues}}

                    # Simulate read() call (which epic_issues uses)
                    epic = await adapter.read(short_id)

                    # Verify epic was returned with child_issues populated
                    assert epic is not None
                    assert hasattr(epic, "child_issues")
                    assert len(epic.child_issues) == 1
                    assert epic.child_issues[0] == "TEST-1"
