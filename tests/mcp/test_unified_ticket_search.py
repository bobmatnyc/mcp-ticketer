"""Tests for unified ticket_search tool.

Tests the consolidated ticket_search() MCP tool that unifies standard search
and hierarchical search under a single interface.

This test suite validates:
1. Standard search behavior (include_hierarchy=False)
2. Hierarchical search behavior (include_hierarchy=True)
3. Parameter validation
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ticketer.core.models import Priority, Task, TicketState
from mcp_ticketer.mcp.server.tools.search_tools import ticket_search


@pytest.fixture
def mock_adapter():
    """Create mock adapter with search support."""
    adapter = MagicMock()
    adapter.adapter_type = "test_adapter"
    adapter.adapter_display_name = "Test Adapter"
    adapter.search = AsyncMock()
    adapter.read = AsyncMock()
    return adapter


@pytest.fixture
def sample_tickets():
    """Create sample tickets for search results."""
    return [
        Task(
            id="TICKET-1",
            title="Bug in authentication",
            description="Users cannot login",
            state=TicketState.OPEN,
            priority=Priority.HIGH,
            tags=["bug", "auth"],
            assignee="user1",
        ),
        Task(
            id="TICKET-2",
            title="Feature request: OAuth",
            description="Add OAuth support",
            state=TicketState.IN_PROGRESS,
            priority=Priority.MEDIUM,
            tags=["feature", "auth"],
            assignee="user2",
            parent_epic="EPIC-1",
        ),
    ]


@pytest.fixture
def mock_config_resolver():
    """Mock ConfigResolver with default project."""
    resolver = MagicMock()
    config = MagicMock()
    config.default_project = "project-123"
    resolver.load_project_config.return_value = config
    return resolver


@pytest.mark.asyncio
class TestTicketSearchUnifiedTool:
    """Test suite for unified ticket_search() tool."""

    # =============================================================================
    # Standard Search Tests (include_hierarchy=False)
    # =============================================================================

    async def test_standard_search_basic(
        self, mock_adapter, sample_tickets, mock_config_resolver
    ):
        """Test basic search without hierarchy."""
        mock_adapter.search.return_value = sample_tickets

        with (
            patch(
                "mcp_ticketer.mcp.server.tools.search_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.core.project_config.ConfigResolver",
                return_value=mock_config_resolver,
            ),
        ):
            result = await ticket_search(
                query="authentication",
                state="open",
                limit=10,
            )

        assert result["status"] == "completed"
        assert "tickets" in result
        assert len(result["tickets"]) == 2
        assert result["count"] == 2
        assert "hierarchy" not in result["tickets"][0]

    async def test_standard_search_with_filters(
        self, mock_adapter, sample_tickets, mock_config_resolver
    ):
        """Test search with multiple filters."""
        mock_adapter.search.return_value = sample_tickets[:1]

        with (
            patch(
                "mcp_ticketer.mcp.server.tools.search_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.core.project_config.ConfigResolver",
                return_value=mock_config_resolver,
            ),
        ):
            result = await ticket_search(
                query="bug",
                state="open",
                priority="high",
                tags=["bug", "auth"],
                assignee="user1",
                project_id="project-123",
                limit=5,
            )

        assert result["status"] == "completed"
        assert len(result["tickets"]) == 1
        assert result["tickets"][0]["title"] == "Bug in authentication"

    async def test_standard_search_backward_compatible(
        self, mock_adapter, sample_tickets, mock_config_resolver
    ):
        """Test default behavior is unchanged (backward compatible)."""
        mock_adapter.search.return_value = sample_tickets

        with (
            patch(
                "mcp_ticketer.mcp.server.tools.search_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.core.project_config.ConfigResolver",
                return_value=mock_config_resolver,
            ),
        ):
            # Call without include_hierarchy parameter (defaults to False)
            result = await ticket_search(query="authentication")

        # Should return flat list without hierarchy
        assert "tickets" in result
        assert "results" not in result
        assert "hierarchy" not in result

    # =============================================================================
    # Hierarchical Search Tests (include_hierarchy=True)
    # =============================================================================

    async def test_hierarchical_search_basic(
        self, mock_adapter, sample_tickets, mock_config_resolver
    ):
        """Test search with hierarchy enabled."""
        mock_adapter.search.return_value = sample_tickets
        mock_adapter.read.return_value = Task(
            id="EPIC-1",
            title="Authentication Epic",
            description="All auth features",
            state=TicketState.IN_PROGRESS,
            priority=Priority.HIGH,
        )

        with (
            patch(
                "mcp_ticketer.mcp.server.tools.search_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.core.project_config.ConfigResolver",
                return_value=mock_config_resolver,
            ),
        ):
            result = await ticket_search(
                query="authentication",
                include_hierarchy=True,
            )

        assert result["status"] == "completed"
        assert "results" in result
        assert len(result["results"]) == 2
        assert "hierarchy" in result["results"][0]

    async def test_hierarchical_search_with_parent_epic(
        self, mock_adapter, sample_tickets, mock_config_resolver
    ):
        """Test hierarchy includes parent epic."""
        mock_adapter.search.return_value = [
            sample_tickets[1]
        ]  # Ticket with parent_epic
        parent_epic = Task(
            id="EPIC-1",
            title="Authentication Epic",
            description="All auth features",
            state=TicketState.IN_PROGRESS,
            priority=Priority.HIGH,
        )
        mock_adapter.read.return_value = parent_epic

        with (
            patch(
                "mcp_ticketer.mcp.server.tools.search_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.core.project_config.ConfigResolver",
                return_value=mock_config_resolver,
            ),
        ):
            result = await ticket_search(
                query="OAuth",
                include_hierarchy=True,
                max_depth=2,
            )

        assert result["status"] == "completed"
        assert "hierarchy" in result["results"][0]
        assert "parent_epic" in result["results"][0]["hierarchy"]
        assert result["results"][0]["hierarchy"]["parent_epic"]["id"] == "EPIC-1"

    async def test_hierarchical_search_max_depth_validation(
        self, mock_adapter, mock_config_resolver
    ):
        """Test max_depth validation."""
        mock_adapter.search.return_value = []

        with (
            patch(
                "mcp_ticketer.mcp.server.tools.search_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.core.project_config.ConfigResolver",
                return_value=mock_config_resolver,
            ),
        ):
            # Test max_depth too low
            result = await ticket_search(
                query="test",
                include_hierarchy=True,
                max_depth=0,
            )
            assert result["status"] == "error"
            assert "max_depth must be between 1 and 3" in result["error"]

            # Test max_depth too high
            result = await ticket_search(
                query="test",
                include_hierarchy=True,
                max_depth=4,
            )
            assert result["status"] == "error"
            assert "max_depth must be between 1 and 3" in result["error"]

    # =============================================================================
    # Parameter Validation Tests
    # =============================================================================

    async def test_invalid_state(self, mock_adapter, mock_config_resolver):
        """Test invalid state parameter."""
        with (
            patch(
                "mcp_ticketer.mcp.server.tools.search_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.core.project_config.ConfigResolver",
                return_value=mock_config_resolver,
            ),
        ):
            result = await ticket_search(
                query="test",
                state="invalid_state",
            )

        assert result["status"] == "error"
        assert "Invalid state" in result["error"]

    async def test_invalid_priority(self, mock_adapter, mock_config_resolver):
        """Test invalid priority parameter."""
        with (
            patch(
                "mcp_ticketer.mcp.server.tools.search_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.core.project_config.ConfigResolver",
                return_value=mock_config_resolver,
            ),
        ):
            result = await ticket_search(
                query="test",
                priority="invalid_priority",
            )

        assert result["status"] == "error"
        assert "Invalid priority" in result["error"]

    async def test_project_id_required(self, mock_adapter):
        """Test project_id is required when not configured."""
        resolver = MagicMock()
        resolver.load_project_config.return_value = None

        with (
            patch(
                "mcp_ticketer.mcp.server.tools.search_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.core.project_config.ConfigResolver",
                return_value=resolver,
            ),
        ):
            result = await ticket_search(query="test")

        assert result["status"] == "error"
        assert "project_id required" in result["error"]

    # =============================================================================
    # Edge Cases and Error Handling
    # =============================================================================

    async def test_search_with_no_results(self, mock_adapter, mock_config_resolver):
        """Test search returns empty results gracefully."""
        mock_adapter.search.return_value = []

        with (
            patch(
                "mcp_ticketer.mcp.server.tools.search_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.core.project_config.ConfigResolver",
                return_value=mock_config_resolver,
            ),
        ):
            result = await ticket_search(query="nonexistent")

        assert result["status"] == "completed"
        assert result["count"] == 0
        assert len(result["tickets"]) == 0

    async def test_hierarchy_with_missing_parent(
        self, mock_adapter, sample_tickets, mock_config_resolver
    ):
        """Test hierarchy handles missing parent gracefully."""
        mock_adapter.search.return_value = [sample_tickets[1]]
        mock_adapter.read.side_effect = Exception("Parent not found")

        with (
            patch(
                "mcp_ticketer.mcp.server.tools.search_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.core.project_config.ConfigResolver",
                return_value=mock_config_resolver,
            ),
        ):
            result = await ticket_search(
                query="OAuth",
                include_hierarchy=True,
            )

        # Should succeed even when parent lookup fails
        assert result["status"] == "completed"
        assert len(result["results"]) == 1

    async def test_adapter_error_handling(self, mock_adapter, mock_config_resolver):
        """Test error handling when adapter fails."""
        mock_adapter.search.side_effect = Exception("Database connection error")

        with (
            patch(
                "mcp_ticketer.mcp.server.tools.search_tools.get_adapter",
                return_value=mock_adapter,
            ),
            patch(
                "mcp_ticketer.core.project_config.ConfigResolver",
                return_value=mock_config_resolver,
            ),
        ):
            result = await ticket_search(query="test")

        assert result["status"] == "error"
        assert "Failed to search tickets" in result["error"]
