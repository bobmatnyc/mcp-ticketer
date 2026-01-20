"""Unit tests for hierarchy tool relationship actions.

This test file validates that the hierarchy tool properly handles relationship
actions (add_relation, remove_relation, list_relations) which are now checked
BEFORE entity_type branches, making them entity_type independent.

Previous Bug (FIXED):
======================
Relationship actions were previously unreachable because they were checked
AFTER entity_type branches that had else clauses returning errors. This has
been fixed by moving relationship action checks to the beginning of the function.

Current Structure (FIXED):
==========================
    # Relationship operations (entity_type independent) - check FIRST
    if action_lower == "add_relation":
        # handle action
    elif action_lower == "remove_relation":
        # handle action
    elif action_lower == "list_relations":
        # handle action

    # Entity-specific operations
    if entity_type_lower == "epic":
        # handle epic actions
    elif entity_type_lower == "issue":
        # handle issue actions
    elif entity_type_lower == "task":
        # handle task actions
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ticketer.core.models import RelationType, TicketRelation
from mcp_ticketer.mcp.server.tools.hierarchy_tools import hierarchy


@pytest.fixture
def mock_adapter():
    """Create a mock adapter with relationship support."""
    adapter = MagicMock()
    adapter.adapter_type = "linear"
    adapter.adapter_display_name = "Linear"
    return adapter


@pytest.mark.asyncio
class TestAddRelation:
    """Test suite for add_relation action."""

    async def test_add_relation_success(self, mock_adapter: MagicMock) -> None:
        """Test successful add_relation operation."""
        # Mock successful relation creation
        mock_adapter.add_relation = AsyncMock(
            return_value=TicketRelation(
                source_ticket_id="SRC-1",
                target_ticket_id="TGT-2",
                relation_type=RelationType.BLOCKS,
            )
        )

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="epic",
                action="add_relation",
                source_id="SRC-1",
                target_id="TGT-2",
                relation_type="blocks",
            )

        assert result["status"] == "completed"
        assert result["operation"] == "add_relation"
        assert result["adapter"] == "linear"
        assert result["adapter_name"] == "Linear"
        assert "relation" in result
        assert result["relation"]["source_ticket_id"] == "SRC-1"
        assert result["relation"]["target_ticket_id"] == "TGT-2"
        assert result["relation"]["relation_type"] == "blocks"

        # Verify adapter method was called correctly
        mock_adapter.add_relation.assert_called_once_with(
            "SRC-1", "TGT-2", RelationType.BLOCKS
        )

    async def test_add_relation_works_with_issue(self, mock_adapter: MagicMock) -> None:
        """Test add_relation works with entity_type='issue'."""
        mock_adapter.add_relation = AsyncMock(
            return_value=TicketRelation(
                source_ticket_id="ISSUE-123",
                target_ticket_id="ISSUE-456",
                relation_type=RelationType.RELATES_TO,
            )
        )

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="issue",
                action="add_relation",
                source_id="ISSUE-123",
                target_id="ISSUE-456",
                relation_type="relates_to",
            )

        assert result["status"] == "completed"
        assert result["operation"] == "add_relation"

    async def test_add_relation_works_with_task(self, mock_adapter: MagicMock) -> None:
        """Test add_relation works with entity_type='task'."""
        mock_adapter.add_relation = AsyncMock(
            return_value=TicketRelation(
                source_ticket_id="TASK-1",
                target_ticket_id="TASK-2",
                relation_type=RelationType.DUPLICATES,
            )
        )

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="task",
                action="add_relation",
                source_id="TASK-1",
                target_id="TASK-2",
                relation_type="duplicates",
            )

        assert result["status"] == "completed"

    async def test_add_relation_missing_source_id(
        self, mock_adapter: MagicMock
    ) -> None:
        """Test error when source_id is missing."""
        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="epic",
                action="add_relation",
                target_id="TGT-2",
                relation_type="blocks",
            )

        assert result["status"] == "error"
        assert "source_id, target_id, and relation_type required" in result["error"]
        assert "hint" in result

    async def test_add_relation_missing_target_id(
        self, mock_adapter: MagicMock
    ) -> None:
        """Test error when target_id is missing."""
        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="epic",
                action="add_relation",
                source_id="SRC-1",
                relation_type="blocks",
            )

        assert result["status"] == "error"
        assert "source_id, target_id, and relation_type required" in result["error"]

    async def test_add_relation_missing_relation_type(
        self, mock_adapter: MagicMock
    ) -> None:
        """Test error when relation_type is missing."""
        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="epic",
                action="add_relation",
                source_id="SRC-1",
                target_id="TGT-2",
            )

        assert result["status"] == "error"
        assert "source_id, target_id, and relation_type required" in result["error"]

    async def test_add_relation_invalid_relation_type(
        self, mock_adapter: MagicMock
    ) -> None:
        """Test error when relation_type is invalid."""
        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="epic",
                action="add_relation",
                source_id="SRC-1",
                target_id="TGT-2",
                relation_type="invalid_type",
            )

        assert result["status"] == "error"
        assert "Invalid relation_type 'invalid_type'" in result["error"]
        assert "blocks" in result["error"]  # Should list valid types

    async def test_add_relation_not_implemented(self, mock_adapter: MagicMock) -> None:
        """Test handling when adapter doesn't support relationships."""
        mock_adapter.add_relation = AsyncMock(side_effect=NotImplementedError())

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="epic",
                action="add_relation",
                source_id="SRC-1",
                target_id="TGT-2",
                relation_type="blocks",
            )

        assert result["status"] == "error"
        assert "not supported by Linear adapter" in result["error"]
        assert result["adapter"] == "linear"
        assert "note" in result

    async def test_add_relation_adapter_error(self, mock_adapter: MagicMock) -> None:
        """Test handling of adapter errors during add_relation."""
        mock_adapter.add_relation = AsyncMock(
            side_effect=Exception("API connection failed")
        )

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="epic",
                action="add_relation",
                source_id="SRC-1",
                target_id="TGT-2",
                relation_type="blocks",
            )

        assert result["status"] == "error"
        assert "Failed to add relation" in result["error"]
        assert "API connection failed" in result["error"]


@pytest.mark.asyncio
class TestRemoveRelation:
    """Test suite for remove_relation action."""

    async def test_remove_relation_success(self, mock_adapter: MagicMock) -> None:
        """Test successful remove_relation operation."""
        mock_adapter.remove_relation = AsyncMock(return_value=True)

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="issue",
                action="remove_relation",
                source_id="ISSUE-123",
                target_id="ISSUE-456",
                relation_type="blocks",
            )

        assert result["status"] == "completed"
        assert result["operation"] == "remove_relation"
        assert result["removed"] is True
        assert result["adapter"] == "linear"

        # Verify adapter method was called correctly
        mock_adapter.remove_relation.assert_called_once_with(
            "ISSUE-123", "ISSUE-456", RelationType.BLOCKS
        )

    async def test_remove_relation_missing_params(
        self, mock_adapter: MagicMock
    ) -> None:
        """Test error when parameters are missing."""
        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="epic",
                action="remove_relation",
                source_id="SRC-1",
                # Missing target_id and relation_type
            )

        assert result["status"] == "error"
        assert "source_id, target_id, and relation_type required" in result["error"]

    async def test_remove_relation_invalid_type(self, mock_adapter: MagicMock) -> None:
        """Test error for invalid relation_type."""
        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="task",
                action="remove_relation",
                source_id="TASK-1",
                target_id="TASK-2",
                relation_type="not_a_real_type",
            )

        assert result["status"] == "error"
        assert "Invalid relation_type 'not_a_real_type'" in result["error"]

    async def test_remove_relation_not_implemented(
        self, mock_adapter: MagicMock
    ) -> None:
        """Test handling when adapter doesn't support relationships."""
        mock_adapter.remove_relation = AsyncMock(side_effect=NotImplementedError())

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="epic",
                action="remove_relation",
                source_id="SRC-1",
                target_id="TGT-2",
                relation_type="blocks",
            )

        assert result["status"] == "error"
        assert "not supported by Linear adapter" in result["error"]


@pytest.mark.asyncio
class TestListRelations:
    """Test suite for list_relations action."""

    async def test_list_relations_success(self, mock_adapter: MagicMock) -> None:
        """Test successful list_relations operation."""
        mock_relations = [
            TicketRelation(
                source_ticket_id="ISSUE-123",
                target_ticket_id="ISSUE-456",
                relation_type=RelationType.BLOCKS,
            ),
            TicketRelation(
                source_ticket_id="ISSUE-123",
                target_ticket_id="ISSUE-789",
                relation_type=RelationType.RELATES_TO,
            ),
        ]
        mock_adapter.list_relations = AsyncMock(return_value=mock_relations)

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="epic",
                action="list_relations",
                entity_id="ISSUE-123",
            )

        assert result["status"] == "completed"
        assert result["operation"] == "list_relations"
        assert result["count"] == 2
        assert len(result["relations"]) == 2
        assert result["filter_applied"] is None
        assert result["ticket_id"] == "ISSUE-123"

        # Verify adapter method was called correctly
        mock_adapter.list_relations.assert_called_once_with("ISSUE-123", None)

    async def test_list_relations_with_filter(self, mock_adapter: MagicMock) -> None:
        """Test list_relations with relation_type filter."""
        mock_relations = [
            TicketRelation(
                source_ticket_id="ISSUE-123",
                target_ticket_id="ISSUE-456",
                relation_type=RelationType.BLOCKS,
            ),
        ]
        mock_adapter.list_relations = AsyncMock(return_value=mock_relations)

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="issue",
                action="list_relations",
                entity_id="ISSUE-123",
                relation_type="blocks",
            )

        assert result["status"] == "completed"
        assert result["count"] == 1
        assert result["filter_applied"] == "blocks"

        # Verify adapter method was called with filter
        mock_adapter.list_relations.assert_called_once_with(
            "ISSUE-123", RelationType.BLOCKS
        )

    async def test_list_relations_empty_result(self, mock_adapter: MagicMock) -> None:
        """Test list_relations with no relations found."""
        mock_adapter.list_relations = AsyncMock(return_value=[])

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="task",
                action="list_relations",
                entity_id="TASK-999",
            )

        assert result["status"] == "completed"
        assert result["count"] == 0
        assert result["relations"] == []

    async def test_list_relations_missing_entity_id(
        self, mock_adapter: MagicMock
    ) -> None:
        """Test error when entity_id is missing."""
        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="epic",
                action="list_relations",
            )

        assert result["status"] == "error"
        assert "entity_id required for list_relations" in result["error"]
        assert "hint" in result

    async def test_list_relations_invalid_filter_type(
        self, mock_adapter: MagicMock
    ) -> None:
        """Test error for invalid relation_type filter."""
        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="epic",
                action="list_relations",
                entity_id="ISSUE-123",
                relation_type="invalid_filter",
            )

        assert result["status"] == "error"
        assert "Invalid relation_type 'invalid_filter'" in result["error"]

    async def test_list_relations_not_implemented(
        self, mock_adapter: MagicMock
    ) -> None:
        """Test handling when adapter doesn't support relationships."""
        mock_adapter.list_relations = AsyncMock(side_effect=NotImplementedError())

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="epic",
                action="list_relations",
                entity_id="ISSUE-123",
            )

        assert result["status"] == "error"
        assert "not supported by Linear adapter" in result["error"]
        assert result["ticket_id"] == "ISSUE-123"

    async def test_list_relations_adapter_error(self, mock_adapter: MagicMock) -> None:
        """Test handling of adapter errors during list_relations."""
        mock_adapter.list_relations = AsyncMock(
            side_effect=Exception("Network timeout")
        )

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            result = await hierarchy(
                entity_type="issue",
                action="list_relations",
                entity_id="ISSUE-123",
            )

        assert result["status"] == "error"
        assert "Failed to list relations" in result["error"]
        assert "Network timeout" in result["error"]


@pytest.mark.asyncio
class TestRelationshipActionIntegration:
    """Integration tests verifying relationship actions work across all entity types."""

    async def test_all_relation_types_supported(self, mock_adapter: MagicMock) -> None:
        """Test that all RelationType values are supported."""
        for rel_type in RelationType:
            mock_adapter.add_relation = AsyncMock(
                return_value=TicketRelation(
                    source_ticket_id="SRC-1",
                    target_ticket_id="TGT-2",
                    relation_type=rel_type,
                )
            )

            with patch(
                "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
                return_value=mock_adapter,
            ):
                result = await hierarchy(
                    entity_type="epic",
                    action="add_relation",
                    source_id="SRC-1",
                    target_id="TGT-2",
                    relation_type=rel_type.value,
                )

            assert result["status"] == "completed", f"Failed for {rel_type.value}"

    async def test_relationship_actions_entity_type_independent(
        self, mock_adapter: MagicMock
    ) -> None:
        """Test that relationship actions work with any entity_type."""
        entity_types = ["epic", "issue", "task"]
        actions = [
            (
                "add_relation",
                {"source_id": "A", "target_id": "B", "relation_type": "blocks"},
            ),
            (
                "remove_relation",
                {"source_id": "A", "target_id": "B", "relation_type": "blocks"},
            ),
            ("list_relations", {"entity_id": "A"}),
        ]

        # Mock all adapter methods
        mock_adapter.add_relation = AsyncMock(
            return_value=TicketRelation(
                source_ticket_id="A",
                target_ticket_id="B",
                relation_type=RelationType.BLOCKS,
            )
        )
        mock_adapter.remove_relation = AsyncMock(return_value=True)
        mock_adapter.list_relations = AsyncMock(return_value=[])

        with patch(
            "mcp_ticketer.mcp.server.tools.hierarchy_tools.get_adapter",
            return_value=mock_adapter,
        ):
            for entity_type in entity_types:
                for action, params in actions:
                    result = await hierarchy(
                        entity_type=entity_type, action=action, **params
                    )

                    assert (
                        result["status"] == "completed"
                    ), f"Failed for entity_type={entity_type}, action={action}"
                    assert result["operation"] == action


@pytest.mark.unit
class TestRelationshipCodeStructure:
    """Tests documenting the fixed code structure."""

    def test_relationship_actions_checked_first(self) -> None:
        """Verify relationship action checks come BEFORE entity_type branches.

        This test documents the fixed code structure where relationship actions
        are checked at the beginning of the function, making them reachable
        regardless of entity_type.

        Structure (FIXED):
        - Line ~292: Relationship operations check FIRST
        - Line ~293: if action_lower == "add_relation":
        - Line ~330: elif action_lower == "remove_relation":
        - Line ~367: elif action_lower == "list_relations":
        - Line ~406: Entity-specific operations (epic/issue/task)
        """
        import inspect
        from pathlib import Path

        from mcp_ticketer.mcp.server.tools import hierarchy_tools

        source_file = Path(inspect.getfile(hierarchy_tools))
        assert source_file.exists()

        with open(source_file) as f:
            content = f.read()

        # Verify relationship action checks exist
        assert 'if action_lower == "add_relation":' in content
        assert 'elif action_lower == "remove_relation":' in content
        assert 'elif action_lower == "list_relations":' in content

        # Verify comment showing they're checked first
        assert (
            "# Relationship operations (entity_type independent) - check FIRST"
            in content
        )

        lines = content.split("\n")

        # Find line numbers
        relationship_comment_line = next(
            i
            for i, line in enumerate(lines, 1)
            if "# Relationship operations (entity_type independent) - check FIRST"
            in line
        )
        add_relation_line = next(
            i
            for i, line in enumerate(lines, 1)
            if 'if action_lower == "add_relation":' in line
        )
        entity_epic_line = next(
            i
            for i, line in enumerate(lines, 1)
            if 'if entity_type_lower == "epic":' in line
        )

        # Relationship checks come BEFORE entity checks (fixed!)
        assert (
            add_relation_line < entity_epic_line
        ), "Relationship actions should be checked before entity_type branches"
        assert relationship_comment_line < add_relation_line
        assert add_relation_line < entity_epic_line

    def test_valid_actions_include_relationship_operations(self) -> None:
        """Verify that valid_actions lists include relationship operations."""
        import inspect
        from pathlib import Path

        from mcp_ticketer.mcp.server.tools import hierarchy_tools

        source_file = Path(inspect.getfile(hierarchy_tools))
        with open(source_file) as f:
            content = f.read()

        # Relationship actions should be in valid_actions lists
        assert '"add_relation"' in content
        assert '"remove_relation"' in content
        assert '"list_relations"' in content

        # They should appear in the main action enum/list
        lines = content.split("\n")
        action_list_started = False
        actions_in_list = []

        for line in lines:
            if "action: Literal[" in line or action_list_started:
                action_list_started = True
                if '"add_relation"' in line:
                    actions_in_list.append("add_relation")
                if '"remove_relation"' in line:
                    actions_in_list.append("remove_relation")
                if '"list_relations"' in line:
                    actions_in_list.append("list_relations")
                if "]" in line and action_list_started:
                    break

        assert "add_relation" in actions_in_list
        assert "remove_relation" in actions_in_list
        assert "list_relations" in actions_in_list
