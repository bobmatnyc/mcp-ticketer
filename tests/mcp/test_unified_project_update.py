"""Tests for unified project_update tool.

Tests the consolidated project_update() MCP tool that unifies all project update
operations under a single interface.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ticketer.core.models import ProjectUpdate, ProjectUpdateHealth
from mcp_ticketer.mcp.server.tools.project_update_tools import (
    project_update,
    project_update_create,
    project_update_get,
    project_update_list,
)


@pytest.fixture
def mock_adapter():
    """Create mock adapter with project update support."""
    adapter = MagicMock()
    adapter.adapter_type = "test_adapter"
    adapter.adapter_display_name = "Test Adapter"
    adapter.create_project_update = AsyncMock()
    adapter.get_project_update = AsyncMock()
    adapter.list_project_updates = AsyncMock()
    return adapter


@pytest.fixture
def mock_update():
    """Create mock ProjectUpdate instance."""
    return ProjectUpdate(
        id="update-123",
        project_id="project-456",
        body="Test update",
        health=ProjectUpdateHealth.ON_TRACK,
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        url="https://example.com/update/123",
    )


@pytest.mark.asyncio
class TestProjectUpdateUnifiedTool:
    """Test suite for unified project_update() tool."""

    # =============================================================================
    # Action Validation Tests
    # =============================================================================

    async def test_invalid_action(self):
        """Test project_update with invalid action."""
        result = await project_update(action="invalid_action")

        assert result["status"] == "error"
        assert "Invalid action 'invalid_action'" in result["error"]
        assert "create" in result["error"]
        assert "get" in result["error"]
        assert "list" in result["error"]

    # =============================================================================
    # Create Action Tests
    # =============================================================================

    async def test_create_action_success(self, mock_adapter, mock_update):
        """Test project_update with action='create'."""
        mock_adapter.create_project_update.return_value = mock_update

        with patch(
            "mcp_ticketer.mcp.server.tools.project_update_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await project_update(
                action="create",
                project_id="project-456",
                body="Test update",
                health="on_track",
            )

        assert result["status"] == "completed"
        assert result["adapter"] == "test_adapter"
        assert result["adapter_name"] == "Test Adapter"
        assert result["project_id"] == "project-456"
        assert "update" in result
        assert result["update"]["id"] == "update-123"

        # Verify adapter was called correctly
        mock_adapter.create_project_update.assert_called_once_with(
            project_id="project-456",
            body="Test update",
            health=ProjectUpdateHealth.ON_TRACK,
        )

    async def test_create_action_missing_project_id(self):
        """Test project_update with action='create' but missing project_id."""
        result = await project_update(
            action="create",
            body="Test update",
        )

        assert result["status"] == "error"
        assert "project_id" in result["error"]
        assert "required" in result["error"]

    async def test_create_action_missing_body(self):
        """Test project_update with action='create' but missing body."""
        result = await project_update(
            action="create",
            project_id="project-456",
        )

        assert result["status"] == "error"
        assert "body" in result["error"]
        assert "required" in result["error"]

    async def test_create_action_with_invalid_health(self, mock_adapter):
        """Test project_update with action='create' and invalid health."""
        with patch(
            "mcp_ticketer.mcp.server.tools.project_update_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await project_update(
                action="create",
                project_id="project-456",
                body="Test update",
                health="invalid_health",
            )

        assert result["status"] == "error"
        assert "Invalid health status" in result["error"]
        assert "on_track" in result["error"]

    # =============================================================================
    # Get Action Tests
    # =============================================================================

    async def test_get_action_success(self, mock_adapter, mock_update):
        """Test project_update with action='get'."""
        mock_adapter.get_project_update.return_value = mock_update

        with patch(
            "mcp_ticketer.mcp.server.tools.project_update_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await project_update(
                action="get",
                update_id="update-123",
            )

        assert result["status"] == "completed"
        assert result["adapter"] == "test_adapter"
        assert result["adapter_name"] == "Test Adapter"
        assert "update" in result
        assert result["update"]["id"] == "update-123"

        # Verify adapter was called correctly
        mock_adapter.get_project_update.assert_called_once_with(update_id="update-123")

    async def test_get_action_missing_update_id(self):
        """Test project_update with action='get' but missing update_id."""
        result = await project_update(action="get")

        assert result["status"] == "error"
        assert "update_id" in result["error"]
        assert "required" in result["error"]

    async def test_get_action_not_found(self, mock_adapter):
        """Test project_update with action='get' when update not found."""
        mock_adapter.get_project_update.return_value = None

        with patch(
            "mcp_ticketer.mcp.server.tools.project_update_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await project_update(
                action="get",
                update_id="nonexistent-update",
            )

        assert result["status"] == "error"
        assert "not found" in result["error"]

    # =============================================================================
    # List Action Tests
    # =============================================================================

    async def test_list_action_success(self, mock_adapter, mock_update):
        """Test project_update with action='list'."""
        mock_adapter.list_project_updates.return_value = [mock_update]

        with patch(
            "mcp_ticketer.mcp.server.tools.project_update_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await project_update(
                action="list",
                project_id="project-456",
                limit=5,
            )

        assert result["status"] == "completed"
        assert result["adapter"] == "test_adapter"
        assert result["adapter_name"] == "Test Adapter"
        assert result["project_id"] == "project-456"
        assert result["count"] == 1
        assert "updates" in result
        assert len(result["updates"]) == 1
        assert result["updates"][0]["id"] == "update-123"

        # Verify adapter was called correctly
        mock_adapter.list_project_updates.assert_called_once_with(
            project_id="project-456",
            limit=5,
        )

    async def test_list_action_missing_project_id(self):
        """Test project_update with action='list' but missing project_id."""
        result = await project_update(action="list")

        assert result["status"] == "error"
        assert "project_id" in result["error"]
        assert "required" in result["error"]

    async def test_list_action_default_limit(self, mock_adapter, mock_update):
        """Test project_update with action='list' uses default limit."""
        mock_adapter.list_project_updates.return_value = [mock_update]

        with patch(
            "mcp_ticketer.mcp.server.tools.project_update_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await project_update(
                action="list",
                project_id="project-456",
            )

        assert result["status"] == "completed"
        # Verify default limit of 10 was used
        mock_adapter.list_project_updates.assert_called_once_with(
            project_id="project-456",
            limit=10,
        )

    # =============================================================================
    # Backward Compatibility Tests (Deprecated Tools)
    # =============================================================================

    async def test_deprecated_create_still_works(self, mock_adapter, mock_update):
        """Test deprecated project_update_create still works with warning."""
        mock_adapter.create_project_update.return_value = mock_update

        with patch(
            "mcp_ticketer.mcp.server.tools.project_update_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with pytest.warns(
                DeprecationWarning, match="project_update_create is deprecated"
            ):
                result = await project_update_create(
                    project_id="project-456",
                    body="Test update",
                    health="on_track",
                )

        assert result["status"] == "completed"
        assert result["update"]["id"] == "update-123"

    async def test_deprecated_get_still_works(self, mock_adapter, mock_update):
        """Test deprecated project_update_get still works with warning."""
        mock_adapter.get_project_update.return_value = mock_update

        with patch(
            "mcp_ticketer.mcp.server.tools.project_update_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with pytest.warns(
                DeprecationWarning, match="project_update_get is deprecated"
            ):
                result = await project_update_get(update_id="update-123")

        assert result["status"] == "completed"
        assert result["update"]["id"] == "update-123"

    async def test_deprecated_list_still_works(self, mock_adapter, mock_update):
        """Test deprecated project_update_list still works with warning."""
        mock_adapter.list_project_updates.return_value = [mock_update]

        with patch(
            "mcp_ticketer.mcp.server.tools.project_update_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with pytest.warns(
                DeprecationWarning, match="project_update_list is deprecated"
            ):
                result = await project_update_list(
                    project_id="project-456",
                    limit=5,
                )

        assert result["status"] == "completed"
        assert result["count"] == 1

    # =============================================================================
    # Error Handling Tests
    # =============================================================================

    async def test_create_adapter_not_supported(self, mock_adapter):
        """Test project_update when adapter doesn't support project updates."""
        # Remove method to simulate unsupported adapter
        delattr(mock_adapter, "create_project_update")

        with patch(
            "mcp_ticketer.mcp.server.tools.project_update_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await project_update(
                action="create",
                project_id="project-456",
                body="Test update",
            )

        assert result["status"] == "error"
        assert "does not support project updates" in result["error"]

    async def test_create_adapter_error(self, mock_adapter):
        """Test project_update when adapter raises exception."""
        mock_adapter.create_project_update.side_effect = Exception("Adapter error")

        with patch(
            "mcp_ticketer.mcp.server.tools.project_update_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await project_update(
                action="create",
                project_id="project-456",
                body="Test update",
            )

        assert result["status"] == "error"
        assert "Failed to create project update" in result["error"]

    async def test_list_invalid_limit(self, mock_adapter):
        """Test project_update with action='list' and invalid limit."""
        with patch(
            "mcp_ticketer.mcp.server.tools.project_update_tools.get_adapter",
            return_value=mock_adapter,
        ):
            # Test limit too low
            result = await project_update(
                action="list",
                project_id="project-456",
                limit=0,
            )

        assert result["status"] == "error"
        assert "Limit must be between 1 and 50" in result["error"]

    # =============================================================================
    # Integration Tests
    # =============================================================================

    async def test_create_with_optional_health(self, mock_adapter, mock_update):
        """Test project_update create without health parameter."""
        mock_update.health = None
        mock_adapter.create_project_update.return_value = mock_update

        with patch(
            "mcp_ticketer.mcp.server.tools.project_update_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await project_update(
                action="create",
                project_id="project-456",
                body="Test update",
                # health not provided
            )

        assert result["status"] == "completed"
        # Verify adapter was called with health=None
        mock_adapter.create_project_update.assert_called_once_with(
            project_id="project-456",
            body="Test update",
            health=None,
        )

    async def test_multiple_updates_list(self, mock_adapter):
        """Test project_update list with multiple updates."""
        mock_updates = [
            ProjectUpdate(
                id=f"update-{i}",
                project_id="project-456",
                body=f"Update {i}",
                health=ProjectUpdateHealth.ON_TRACK,
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                url=f"https://example.com/update/{i}",
            )
            for i in range(3)
        ]
        mock_adapter.list_project_updates.return_value = mock_updates

        with patch(
            "mcp_ticketer.mcp.server.tools.project_update_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await project_update(
                action="list",
                project_id="project-456",
                limit=10,
            )

        assert result["status"] == "completed"
        assert result["count"] == 3
        assert len(result["updates"]) == 3
        assert result["updates"][0]["id"] == "update-0"
        assert result["updates"][1]["id"] == "update-1"
        assert result["updates"][2]["id"] == "update-2"
