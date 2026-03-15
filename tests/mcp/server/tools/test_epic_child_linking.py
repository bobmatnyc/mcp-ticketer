"""Unit tests for epic child issue linking after creation.

Tests the post-creation loop in hierarchy_tools.py that calls
adapter.add_relation() for each child issue after an epic is created.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ticketer.core.models import Epic, RelationType
from mcp_ticketer.mcp.server.tools.hierarchy_tools import hierarchy


@pytest.fixture
def mock_adapter():
    """Create a mock adapter with full relationship support."""
    adapter = MagicMock()
    adapter.adapter_type = "github"
    adapter.adapter_display_name = "GitHub"
    return adapter


def _make_created_epic(epic_id: str = "EPIC-1") -> Epic:
    """Return a minimal Epic instance representing the adapter's return value."""
    return Epic(id=epic_id, title="Test Epic")


@pytest.mark.asyncio
class TestEpicChildLinking:
    """Tests for child issue linking after epic creation."""

    async def test_epic_create_with_child_issues_calls_add_relation(
        self, mock_adapter: MagicMock
    ) -> None:
        """Epic creation with child_issues should call add_relation for each child."""
        created_epic = _make_created_epic("EPIC-99")
        mock_adapter.create = AsyncMock(return_value=created_epic)
        mock_adapter.add_relation = AsyncMock(return_value=None)

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="epic",
                action="create",
                title="My Epic",
                child_issues=["6", "7"],
            )

        assert result["status"] == "completed"
        assert result["linked_children"] == ["6", "7"]
        assert "failed_children" not in result

        # add_relation called once per child
        assert mock_adapter.add_relation.call_count == 2
        mock_adapter.add_relation.assert_any_call("EPIC-99", "6", RelationType.CHILD)
        mock_adapter.add_relation.assert_any_call("EPIC-99", "7", RelationType.CHILD)

    async def test_epic_create_without_child_issues_no_add_relation_called(
        self, mock_adapter: MagicMock
    ) -> None:
        """Epic creation without child_issues should not call add_relation."""
        created_epic = _make_created_epic("EPIC-1")
        mock_adapter.create = AsyncMock(return_value=created_epic)
        mock_adapter.add_relation = AsyncMock(return_value=None)

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="epic",
                action="create",
                title="No Children Epic",
            )

        assert result["status"] == "completed"
        assert "linked_children" not in result
        assert "failed_children" not in result
        mock_adapter.add_relation.assert_not_called()

    async def test_epic_create_empty_child_issues_no_add_relation_called(
        self, mock_adapter: MagicMock
    ) -> None:
        """Epic creation with empty child_issues list should not call add_relation."""
        created_epic = _make_created_epic("EPIC-2")
        mock_adapter.create = AsyncMock(return_value=created_epic)
        mock_adapter.add_relation = AsyncMock(return_value=None)

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="epic",
                action="create",
                title="Empty Children Epic",
                child_issues=[],
            )

        assert result["status"] == "completed"
        assert "linked_children" not in result
        assert "failed_children" not in result
        mock_adapter.add_relation.assert_not_called()

    async def test_epic_create_partial_child_linking_failure(
        self, mock_adapter: MagicMock
    ) -> None:
        """When some child links fail, partial success is reported correctly."""
        created_epic = _make_created_epic("EPIC-10")
        mock_adapter.create = AsyncMock(return_value=created_epic)

        # child "6" succeeds, child "7" fails
        async def add_relation_side_effect(
            source: str, target: str, relation: RelationType
        ) -> None:
            if target == "7":
                raise Exception("API rate limit exceeded")

        mock_adapter.add_relation = AsyncMock(side_effect=add_relation_side_effect)

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="epic",
                action="create",
                title="Partial Link Epic",
                child_issues=["6", "7"],
            )

        assert result["status"] == "completed"
        assert result["linked_children"] == ["6"]
        assert len(result["failed_children"]) == 1
        assert result["failed_children"][0]["id"] == "7"
        assert "API rate limit exceeded" in result["failed_children"][0]["error"]

    async def test_epic_create_all_child_linking_failures(
        self, mock_adapter: MagicMock
    ) -> None:
        """When all child links fail, failed_children is populated and linked_children absent."""
        created_epic = _make_created_epic("EPIC-11")
        mock_adapter.create = AsyncMock(return_value=created_epic)
        mock_adapter.add_relation = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="epic",
                action="create",
                title="All Fail Epic",
                child_issues=["6", "7"],
            )

        assert result["status"] == "completed"
        # Epic itself was created successfully (adapter returns mock, id matches)
        assert result["epic"]["id"] == "EPIC-11"
        assert "linked_children" not in result
        assert len(result["failed_children"]) == 2
        ids_failed = {item["id"] for item in result["failed_children"]}
        assert ids_failed == {"6", "7"}

    async def test_epic_create_child_linking_not_implemented_graceful_degradation(
        self, mock_adapter: MagicMock
    ) -> None:
        """Adapter raising NotImplementedError for add_relation degrades gracefully."""
        created_epic = _make_created_epic("EPIC-12")
        mock_adapter.create = AsyncMock(return_value=created_epic)
        mock_adapter.add_relation = AsyncMock(side_effect=NotImplementedError())

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="epic",
                action="create",
                title="NotImpl Epic",
                child_issues=["42"],
            )

        # Epic creation still completes successfully
        assert result["status"] == "completed"
        assert "linked_children" not in result
        assert len(result["failed_children"]) == 1
        assert result["failed_children"][0]["id"] == "42"

    async def test_epic_create_result_contains_epic_data(
        self, mock_adapter: MagicMock
    ) -> None:
        """Epic model_dump is included in response alongside child linking info."""
        created_epic = _make_created_epic("EPIC-20")
        mock_adapter.create = AsyncMock(return_value=created_epic)
        mock_adapter.add_relation = AsyncMock(return_value=None)

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="epic",
                action="create",
                title="Data Epic",
                child_issues=["9"],
            )

        assert result["status"] == "completed"
        assert "epic" in result
        assert result["epic"]["id"] == "EPIC-20"
        assert result["adapter"] == "github"
        assert result["adapter_name"] == "GitHub"
        assert result["ticket_id"] == "EPIC-20"
        assert result["linked_children"] == ["9"]

    async def test_epic_create_single_child_issue(
        self, mock_adapter: MagicMock
    ) -> None:
        """Single child issue is linked correctly."""
        created_epic = _make_created_epic("EPIC-50")
        mock_adapter.create = AsyncMock(return_value=created_epic)
        mock_adapter.add_relation = AsyncMock(return_value=None)

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="epic",
                action="create",
                title="Single Child Epic",
                child_issues=["123"],
            )

        assert result["status"] == "completed"
        assert result["linked_children"] == ["123"]
        mock_adapter.add_relation.assert_called_once_with(
            "EPIC-50", "123", RelationType.CHILD
        )
