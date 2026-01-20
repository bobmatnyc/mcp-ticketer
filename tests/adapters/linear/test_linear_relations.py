"""Unit tests for Linear adapter relationship methods."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter
from mcp_ticketer.adapters.linear.types import (
    get_linear_relation_type,
    get_universal_relation_type,
)
from mcp_ticketer.core.models import RelationType, TicketRelation


@pytest.mark.asyncio
class TestLinearAdapterAddRelation:
    """Test LinearAdapter.add_relation method."""

    @pytest.fixture
    def linear_adapter(self) -> LinearAdapter:
        """Create a LinearAdapter instance with mocked client."""
        config = {
            "api_key": "lin_api_test1234567890",  # Valid Linear API key format
            "team_key": "TEST",
        }
        adapter = LinearAdapter(config=config)
        adapter.client = MagicMock()
        return adapter

    async def test_add_relation_blocks(self, linear_adapter: LinearAdapter) -> None:
        """Test creating a BLOCKS relationship."""
        # Mock GraphQL response
        mock_result = {
            "issueRelationCreate": {
                "success": True,
                "issueRelation": {
                    "id": "rel-123",
                    "type": "blocks",
                    "createdAt": "2024-01-15T10:00:00.000Z",
                    "issue": {
                        "id": "issue-source",
                        "identifier": "TEST-123",
                    },
                    "relatedIssue": {
                        "id": "issue-target",
                        "identifier": "TEST-456",
                    },
                },
            }
        }

        linear_adapter.client.execute_mutation = AsyncMock(return_value=mock_result)

        result = await linear_adapter.add_relation(
            "issue-source",
            "issue-target",
            RelationType.BLOCKS,
        )

        # Verify result
        assert isinstance(result, TicketRelation)
        assert result.id == "rel-123"
        assert result.source_ticket_id == "issue-source"
        assert result.target_ticket_id == "issue-target"
        assert result.relation_type == RelationType.BLOCKS
        assert result.created_at is not None
        assert "linear" in result.metadata
        assert result.metadata["linear"]["relation_id"] == "rel-123"

        # Verify GraphQL call
        linear_adapter.client.execute_mutation.assert_called_once()
        call_args = linear_adapter.client.execute_mutation.call_args
        # call_args is a tuple: (positional_args, keyword_args)
        # execute_mutation(query, variables) - so variables is positional arg [1]
        variables = call_args[0][1]
        assert variables["issueId"] == "issue-source"
        assert variables["relatedIssueId"] == "issue-target"
        assert variables["type"] == "blocks"

    async def test_add_relation_blocked_by(self, linear_adapter: LinearAdapter) -> None:
        """Test creating a BLOCKED_BY relationship."""
        mock_result = {
            "issueRelationCreate": {
                "success": True,
                "issueRelation": {
                    "id": "rel-456",
                    "type": "blockedBy",  # Linear uses camelCase
                    "createdAt": "2024-01-15T10:00:00.000Z",
                    "issue": {"id": "issue-1", "identifier": "TEST-1"},
                    "relatedIssue": {"id": "issue-2", "identifier": "TEST-2"},
                },
            }
        }

        linear_adapter.client.execute_mutation = AsyncMock(return_value=mock_result)

        result = await linear_adapter.add_relation(
            "issue-1",
            "issue-2",
            RelationType.BLOCKED_BY,
        )

        assert result.relation_type == RelationType.BLOCKED_BY

        # Verify type mapping - Linear uses camelCase
        call_args = linear_adapter.client.execute_mutation.call_args
        variables = call_args[0][1]
        assert variables["type"] == "blockedBy"

    async def test_add_relation_duplicates(self, linear_adapter: LinearAdapter) -> None:
        """Test creating a DUPLICATES relationship."""
        mock_result = {
            "issueRelationCreate": {
                "success": True,
                "issueRelation": {
                    "id": "rel-789",
                    "type": "duplicate",  # Linear uses "duplicate" not "duplicates"
                    "createdAt": "2024-01-15T10:00:00.000Z",
                    "issue": {"id": "issue-1", "identifier": "TEST-1"},
                    "relatedIssue": {"id": "issue-2", "identifier": "TEST-2"},
                },
            }
        }

        linear_adapter.client.execute_mutation = AsyncMock(return_value=mock_result)

        result = await linear_adapter.add_relation(
            "issue-1",
            "issue-2",
            RelationType.DUPLICATES,
        )

        assert result.relation_type == RelationType.DUPLICATES

        # Verify type mapping
        call_args = linear_adapter.client.execute_mutation.call_args
        variables = call_args[0][1]
        assert variables["type"] == "duplicate"  # Should be mapped to Linear type

    async def test_add_relation_relates_to(self, linear_adapter: LinearAdapter) -> None:
        """Test creating a RELATES_TO relationship."""
        mock_result = {
            "issueRelationCreate": {
                "success": True,
                "issueRelation": {
                    "id": "rel-999",
                    "type": "related",  # Linear uses "related" not "relates"
                    "createdAt": "2024-01-15T10:00:00.000Z",
                    "issue": {"id": "issue-1", "identifier": "TEST-1"},
                    "relatedIssue": {"id": "issue-2", "identifier": "TEST-2"},
                },
            }
        }

        linear_adapter.client.execute_mutation = AsyncMock(return_value=mock_result)

        result = await linear_adapter.add_relation(
            "issue-1",
            "issue-2",
            RelationType.RELATES_TO,
        )

        assert result.relation_type == RelationType.RELATES_TO

        # Verify type mapping
        call_args = linear_adapter.client.execute_mutation.call_args
        variables = call_args[0][1]
        assert variables["type"] == "related"

    async def test_add_relation_failure(self, linear_adapter: LinearAdapter) -> None:
        """Test add_relation when API returns failure."""
        mock_result = {
            "issueRelationCreate": {
                "success": False,
            }
        }

        linear_adapter.client.execute_mutation = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception) as exc_info:
            await linear_adapter.add_relation(
                "issue-1",
                "issue-2",
                RelationType.BLOCKS,
            )

        assert "Failed to create issue relation" in str(exc_info.value)

    async def test_add_relation_api_exception(
        self, linear_adapter: LinearAdapter
    ) -> None:
        """Test add_relation when API raises exception."""
        linear_adapter.client.execute_mutation = AsyncMock(
            side_effect=Exception("Network error")
        )

        with pytest.raises(Exception) as exc_info:
            await linear_adapter.add_relation(
                "issue-1",
                "issue-2",
                RelationType.BLOCKS,
            )

        assert "Network error" in str(exc_info.value)


@pytest.mark.asyncio
class TestLinearAdapterRemoveRelation:
    """Test LinearAdapter.remove_relation method."""

    @pytest.fixture
    def linear_adapter(self) -> LinearAdapter:
        """Create a LinearAdapter instance with mocked client."""
        config = {
            "api_key": "lin_api_test1234567890",  # Valid Linear API key format
            "team_key": "TEST",
        }
        adapter = LinearAdapter(config=config)
        adapter.client = MagicMock()
        return adapter

    async def test_remove_relation_success(self, linear_adapter: LinearAdapter) -> None:
        """Test successfully removing a relationship."""
        # Mock list_relations to return existing relation
        existing_relation = TicketRelation(
            id="rel-123",
            source_ticket_id="issue-1",
            target_ticket_id="issue-2",
            relation_type=RelationType.BLOCKS,
            metadata={"linear": {"relation_id": "rel-123"}},
        )
        linear_adapter.list_relations = AsyncMock(return_value=[existing_relation])

        # Mock delete mutation response
        mock_delete_result = {
            "issueRelationDelete": {
                "success": True,
            }
        }
        linear_adapter.client.execute_mutation = AsyncMock(
            return_value=mock_delete_result
        )

        result = await linear_adapter.remove_relation(
            "issue-1",
            "issue-2",
            RelationType.BLOCKS,
        )

        assert result is True

        # Verify list_relations was called
        linear_adapter.list_relations.assert_called_once_with(
            "issue-1", RelationType.BLOCKS
        )

        # Verify delete mutation was called with correct relation ID
        call_args = linear_adapter.client.execute_mutation.call_args
        variables = call_args[0][1]
        assert variables["id"] == "rel-123"

    async def test_remove_relation_not_found(
        self, linear_adapter: LinearAdapter
    ) -> None:
        """Test removing a relation that doesn't exist."""
        # Mock list_relations to return empty list
        linear_adapter.list_relations = AsyncMock(return_value=[])

        result = await linear_adapter.remove_relation(
            "issue-1",
            "issue-2",
            RelationType.BLOCKS,
        )

        assert result is False

        # Verify list_relations was called
        linear_adapter.list_relations.assert_called_once()

        # Verify delete mutation was NOT called (no execute_mutation attribute exists yet)
        assert (
            not hasattr(linear_adapter.client, "execute_mutation")
            or not linear_adapter.client.execute_mutation.called
        )

    async def test_remove_relation_wrong_target(
        self, linear_adapter: LinearAdapter
    ) -> None:
        """Test removing a relation with non-matching target."""
        # Mock list_relations to return relation with different target
        existing_relation = TicketRelation(
            id="rel-123",
            source_ticket_id="issue-1",
            target_ticket_id="issue-999",  # Different target
            relation_type=RelationType.BLOCKS,
        )
        linear_adapter.list_relations = AsyncMock(return_value=[existing_relation])

        result = await linear_adapter.remove_relation(
            "issue-1",
            "issue-2",  # Looking for this target
            RelationType.BLOCKS,
        )

        assert result is False

    async def test_remove_relation_api_exception(
        self, linear_adapter: LinearAdapter
    ) -> None:
        """Test remove_relation when API raises exception."""
        linear_adapter.list_relations = AsyncMock(side_effect=Exception("API error"))

        result = await linear_adapter.remove_relation(
            "issue-1",
            "issue-2",
            RelationType.BLOCKS,
        )

        assert result is False


@pytest.mark.asyncio
class TestLinearAdapterListRelations:
    """Test LinearAdapter.list_relations method."""

    @pytest.fixture
    def linear_adapter(self) -> LinearAdapter:
        """Create a LinearAdapter instance with mocked client."""
        config = {
            "api_key": "lin_api_test1234567890",  # Valid Linear API key format
            "team_key": "TEST",
        }
        adapter = LinearAdapter(config=config)
        adapter.client = MagicMock()
        return adapter

    async def test_list_relations_all(self, linear_adapter: LinearAdapter) -> None:
        """Test listing all relationships for an issue."""
        mock_result = {
            "issue": {
                "id": "issue-123",
                "identifier": "TEST-123",
                "relations": {
                    "nodes": [
                        {
                            "id": "rel-1",
                            "type": "blocks",
                            "relatedIssue": {
                                "id": "issue-456",
                                "identifier": "TEST-456",
                            },
                        },
                        {
                            "id": "rel-2",
                            "type": "related",
                            "relatedIssue": {
                                "id": "issue-789",
                                "identifier": "TEST-789",
                            },
                        },
                    ]
                },
            }
        }

        linear_adapter.client.execute_query = AsyncMock(return_value=mock_result)

        result = await linear_adapter.list_relations("issue-123")

        assert len(result) == 2
        assert result[0].id == "rel-1"
        assert result[0].source_ticket_id == "issue-123"
        assert result[0].target_ticket_id == "issue-456"
        assert result[0].relation_type == RelationType.BLOCKS

        assert result[1].id == "rel-2"
        assert result[1].target_ticket_id == "issue-789"
        assert result[1].relation_type == RelationType.RELATES_TO

        # Verify GraphQL call
        call_args = linear_adapter.client.execute_query.call_args
        variables = call_args[0][1]
        assert variables["issueId"] == "issue-123"

    async def test_list_relations_filtered(self, linear_adapter: LinearAdapter) -> None:
        """Test listing relationships filtered by type."""
        mock_result = {
            "issue": {
                "id": "issue-123",
                "identifier": "TEST-123",
                "relations": {
                    "nodes": [
                        {
                            "id": "rel-1",
                            "type": "blocks",
                            "relatedIssue": {
                                "id": "issue-456",
                                "identifier": "TEST-456",
                            },
                        },
                        {
                            "id": "rel-2",
                            "type": "related",
                            "relatedIssue": {
                                "id": "issue-789",
                                "identifier": "TEST-789",
                            },
                        },
                    ]
                },
            }
        }

        linear_adapter.client.execute_query = AsyncMock(return_value=mock_result)

        # Filter for BLOCKS only
        result = await linear_adapter.list_relations("issue-123", RelationType.BLOCKS)

        # Should only return BLOCKS relation
        assert len(result) == 1
        assert result[0].relation_type == RelationType.BLOCKS

    async def test_list_relations_empty(self, linear_adapter: LinearAdapter) -> None:
        """Test listing relationships when none exist."""
        mock_result = {
            "issue": {
                "id": "issue-123",
                "identifier": "TEST-123",
                "relations": {"nodes": []},
            }
        }

        linear_adapter.client.execute_query = AsyncMock(return_value=mock_result)

        result = await linear_adapter.list_relations("issue-123")

        assert len(result) == 0
        assert result == []

    async def test_list_relations_issue_not_found(
        self, linear_adapter: LinearAdapter
    ) -> None:
        """Test listing relationships when issue doesn't exist."""
        mock_result = {"issue": None}

        linear_adapter.client.execute_query = AsyncMock(return_value=mock_result)

        result = await linear_adapter.list_relations("nonexistent-issue")

        assert len(result) == 0
        assert result == []

    async def test_list_relations_api_exception(
        self, linear_adapter: LinearAdapter
    ) -> None:
        """Test list_relations when API raises exception.

        Note: The implementation catches exceptions and returns empty list
        instead of raising. This is intentional behavior.
        """
        linear_adapter.client.execute_query = AsyncMock(
            side_effect=Exception("GraphQL error")
        )

        result = await linear_adapter.list_relations("issue-123")

        # Implementation returns empty list on error instead of raising
        assert result == []


@pytest.mark.unit
class TestLinearTypeMappings:
    """Test Linear relation type mapping functions."""

    def test_get_linear_relation_type_blocks(self) -> None:
        """Test mapping BLOCKS to Linear type."""
        result = get_linear_relation_type(RelationType.BLOCKS)
        assert result == "blocks"

    def test_get_linear_relation_type_blocked_by(self) -> None:
        """Test mapping BLOCKED_BY to Linear type."""
        result = get_linear_relation_type(RelationType.BLOCKED_BY)
        assert result == "blockedBy"  # Linear uses camelCase

    def test_get_linear_relation_type_duplicates(self) -> None:
        """Test mapping DUPLICATES to Linear type."""
        result = get_linear_relation_type(RelationType.DUPLICATES)
        assert result == "duplicate"  # Linear uses "duplicate"

    def test_get_linear_relation_type_duplicated_by(self) -> None:
        """Test mapping DUPLICATED_BY to Linear type."""
        result = get_linear_relation_type(RelationType.DUPLICATED_BY)
        assert result == "duplicatedBy"  # Linear uses camelCase

    def test_get_linear_relation_type_relates_to(self) -> None:
        """Test mapping RELATES_TO to Linear type."""
        result = get_linear_relation_type(RelationType.RELATES_TO)
        assert result == "related"  # Linear uses "related"

    def test_get_universal_relation_type_blocks(self) -> None:
        """Test mapping Linear 'blocks' to universal type."""
        result = get_universal_relation_type("blocks")
        assert result == RelationType.BLOCKS

    def test_get_universal_relation_type_blocked_by(self) -> None:
        """Test mapping Linear 'blockedBy' to universal type."""
        result = get_universal_relation_type("blockedBy")
        assert result == RelationType.BLOCKED_BY

    def test_get_universal_relation_type_duplicate(self) -> None:
        """Test mapping Linear 'duplicate' to universal type."""
        result = get_universal_relation_type("duplicate")
        assert result == RelationType.DUPLICATES

    def test_get_universal_relation_type_duplicated_by(self) -> None:
        """Test mapping Linear 'duplicatedBy' to universal type."""
        result = get_universal_relation_type("duplicatedBy")
        assert result == RelationType.DUPLICATED_BY

    def test_get_universal_relation_type_relates(self) -> None:
        """Test mapping Linear 'related' to universal type."""
        result = get_universal_relation_type("related")
        assert result == RelationType.RELATES_TO

    def test_round_trip_mapping(self) -> None:
        """Test that type mappings are reversible."""
        for universal_type in RelationType:
            linear_type = get_linear_relation_type(universal_type)
            back_to_universal = get_universal_relation_type(linear_type)
            assert back_to_universal == universal_type
