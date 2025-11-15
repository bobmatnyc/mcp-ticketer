"""Comprehensive tests for MCP epic_update tool.

Tests the epic_update MCP tool endpoint including:
- Valid parameter combinations
- Error handling and validation
- Adapter support detection
- Response format verification
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter
from mcp_ticketer.core.models import Epic
from mcp_ticketer.mcp.server.tools.hierarchy_tools import epic_update


class TestEpicUpdateMCPTool:
    """Test suite for epic_update MCP tool."""

    @pytest.fixture
    def mock_linear_adapter(self) -> LinearAdapter:
        """Create a mock Linear adapter with epic update support."""
        adapter = Mock(spec=LinearAdapter)
        adapter.update_epic = AsyncMock()
        return adapter

    @pytest.fixture
    def mock_unsupported_adapter(self) -> Mock:
        """Create a mock adapter without epic update support."""
        adapter = Mock()
        # Explicitly remove update_epic attribute
        if hasattr(adapter, "update_epic"):
            delattr(adapter, "update_epic")
        return adapter

    @pytest.mark.asyncio
    async def test_epic_update_with_valid_parameters(
        self, mock_linear_adapter: LinearAdapter
    ) -> None:
        """Test epic_update tool with valid parameters."""
        epic_id = "test-epic-123"
        new_description = "Updated epic description"

        # Mock the update_epic response
        mock_epic = Epic(
            id=epic_id,
            title="Test Epic",
            description=new_description,
            state="open",
        )
        mock_linear_adapter.update_epic.return_value = mock_epic

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await epic_update(
                epic_id=epic_id,
                description=new_description,
            )

        assert result["status"] == "completed"
        assert result["epic_id"] == epic_id
        assert "epic" in result
        mock_linear_adapter.update_epic.assert_called_once()

    @pytest.mark.asyncio
    async def test_epic_update_with_title(
        self, mock_linear_adapter: LinearAdapter
    ) -> None:
        """Test updating epic title."""
        epic_id = "test-epic-123"
        new_title = "Updated Epic Title"

        mock_epic = Epic(
            id=epic_id,
            title=new_title,
            description="Description",
            state="open",
        )
        mock_linear_adapter.update_epic.return_value = mock_epic

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await epic_update(
                epic_id=epic_id,
                title=new_title,
            )

        assert result["status"] == "completed"
        assert result["epic"]["title"] == new_title

    @pytest.mark.asyncio
    async def test_epic_update_with_state(
        self, mock_linear_adapter: LinearAdapter
    ) -> None:
        """Test updating epic state."""
        epic_id = "test-epic-123"
        new_state = "in_progress"

        mock_epic = Epic(
            id=epic_id,
            title="Test Epic",
            description="Description",
            state=new_state,
        )
        mock_linear_adapter.update_epic.return_value = mock_epic

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await epic_update(
                epic_id=epic_id,
                state=new_state,
            )

        assert result["status"] == "completed"
        assert result["epic"]["state"] == new_state

    @pytest.mark.asyncio
    async def test_epic_update_with_target_date(
        self, mock_linear_adapter: LinearAdapter
    ) -> None:
        """Test updating epic with valid ISO date format."""
        epic_id = "test-epic-123"
        target_date = (date.today() + timedelta(days=30)).isoformat()

        mock_epic = Epic(
            id=epic_id,
            title="Test Epic",
            description="Description",
            state="open",
            metadata={"linear": {"target_date": target_date}},
        )
        mock_linear_adapter.update_epic.return_value = mock_epic

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await epic_update(
                epic_id=epic_id,
                target_date=target_date,
            )

        assert result["status"] == "completed"
        # Verify date was included in updates
        call_args = mock_linear_adapter.update_epic.call_args[0]
        assert call_args[0] == epic_id
        assert "target_date" in call_args[1]

    @pytest.mark.asyncio
    async def test_epic_update_with_multiple_fields(
        self, mock_linear_adapter: LinearAdapter
    ) -> None:
        """Test updating multiple epic fields simultaneously."""
        epic_id = "test-epic-123"

        mock_epic = Epic(
            id=epic_id,
            title="New Title",
            description="New Description",
            state="in_progress",
            metadata={"linear": {"target_date": "2025-12-31"}},
        )
        mock_linear_adapter.update_epic.return_value = mock_epic

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await epic_update(
                epic_id=epic_id,
                title="New Title",
                description="New Description",
                state="in_progress",
                target_date="2025-12-31",
            )

        assert result["status"] == "completed"
        # Verify all fields were passed to adapter
        call_args = mock_linear_adapter.update_epic.call_args[0]
        updates = call_args[1]
        assert len(updates) == 4  # All fields provided

    @pytest.mark.asyncio
    async def test_epic_update_missing_epic_id(
        self, mock_linear_adapter: LinearAdapter
    ) -> None:
        """Test epic_update fails when epic_id is missing."""
        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            # This should be caught by type checking, but test runtime behavior
            with pytest.raises(TypeError):
                await epic_update(description="test")  # type: ignore

    @pytest.mark.asyncio
    async def test_epic_update_no_updates_provided(
        self, mock_linear_adapter: LinearAdapter
    ) -> None:
        """Test epic_update with no update fields fails with helpful message."""
        epic_id = "test-epic-123"

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await epic_update(epic_id=epic_id)

        # Should return error status when no updates provided
        assert result["status"] == "error"
        assert "no updates" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_epic_update_invalid_date_format(
        self, mock_linear_adapter: LinearAdapter
    ) -> None:
        """Test epic_update with invalid date format provides guidance."""
        epic_id = "test-epic-123"
        invalid_date = "not-a-date"

        mock_linear_adapter.update_epic.side_effect = ValueError("Invalid date format")

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await epic_update(
                epic_id=epic_id,
                target_date=invalid_date,
            )

        assert result["status"] == "error"
        assert (
            "invalid date" in result["error"].lower()
            or "date" in result["error"].lower()
        )

    @pytest.mark.asyncio
    async def test_epic_update_unsupported_adapter(
        self, mock_unsupported_adapter: Mock
    ) -> None:
        """Test epic_update with unsupported adapter suggests ticket_update."""
        epic_id = "test-epic-123"

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_unsupported_adapter,
        ):
            result = await epic_update(
                epic_id=epic_id,
                description="test",
            )

        assert result["status"] == "error"
        assert "not supported" in result["error"].lower()
        assert "ticket_update" in result.get("note", "").lower()

    @pytest.mark.asyncio
    async def test_epic_update_adapter_error(
        self, mock_linear_adapter: LinearAdapter
    ) -> None:
        """Test handling adapter errors during epic update."""
        epic_id = "test-epic-123"

        mock_linear_adapter.update_epic.side_effect = Exception(
            "Database connection failed"
        )

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await epic_update(
                epic_id=epic_id,
                description="test",
            )

        assert result["status"] == "error"
        assert "database connection" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_epic_update_epic_not_found(
        self, mock_linear_adapter: LinearAdapter
    ) -> None:
        """Test epic_update with non-existent epic ID."""
        epic_id = "nonexistent-epic"

        mock_linear_adapter.update_epic.return_value = None

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await epic_update(
                epic_id=epic_id,
                description="test",
            )

        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_epic_update_response_structure(
        self, mock_linear_adapter: LinearAdapter
    ) -> None:
        """Test that epic_update returns proper MCP response structure."""
        epic_id = "test-epic-123"

        mock_epic = Epic(
            id=epic_id,
            title="Test Epic",
            description="Updated description",
            state="open",
        )
        mock_linear_adapter.update_epic.return_value = mock_epic

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await epic_update(
                epic_id=epic_id,
                description="Updated description",
            )

        # Verify MCP response format
        assert isinstance(result, dict)
        assert "status" in result
        assert "epic_id" in result
        assert "epic" in result
        assert isinstance(result["epic"], dict)

        # Verify epic data structure
        epic_data = result["epic"]
        assert "id" in epic_data
        assert "title" in epic_data
        assert "description" in epic_data
        assert "state" in epic_data

    @pytest.mark.asyncio
    async def test_epic_update_preserves_metadata(
        self, mock_linear_adapter: LinearAdapter
    ) -> None:
        """Test that epic metadata is preserved in response."""
        epic_id = "test-epic-123"

        mock_epic = Epic(
            id=epic_id,
            title="Test Epic",
            description="Description",
            state="open",
            metadata={
                "linear": {
                    "url": "https://linear.app/test/epic/123",
                    "color": "blue",
                    "icon": "📋",
                }
            },
        )
        mock_linear_adapter.update_epic.return_value = mock_epic

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await epic_update(
                epic_id=epic_id,
                description="Updated",
            )

        assert result["status"] == "completed"
        assert "metadata" in result["epic"]
        assert "linear" in result["epic"]["metadata"]

    @pytest.mark.asyncio
    async def test_epic_update_state_validation(
        self, mock_linear_adapter: LinearAdapter
    ) -> None:
        """Test that invalid state values are handled."""
        epic_id = "test-epic-123"
        invalid_state = "invalid_state"

        mock_linear_adapter.update_epic.side_effect = ValueError("Invalid state value")

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await epic_update(
                epic_id=epic_id,
                state=invalid_state,
            )

        assert result["status"] == "error"
        assert (
            "invalid" in result["error"].lower() or "state" in result["error"].lower()
        )

    @pytest.mark.asyncio
    async def test_epic_update_authorization_error(
        self, mock_linear_adapter: LinearAdapter
    ) -> None:
        """Test handling authorization errors during epic update."""
        epic_id = "test-epic-123"

        mock_linear_adapter.update_epic.side_effect = PermissionError(
            "Insufficient permissions"
        )

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_linear_adapter,
        ):
            result = await epic_update(
                epic_id=epic_id,
                description="test",
            )

        assert result["status"] == "error"
        assert "permission" in result["error"].lower()
