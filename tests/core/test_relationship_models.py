"""Unit tests for ticket relationship models (RelationType and TicketRelation)."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from mcp_ticketer.core.models import RelationType, TicketRelation


@pytest.mark.unit
class TestRelationType:
    """Test RelationType enum."""

    def test_relation_type_values(self) -> None:
        """Test all relation type enum values."""
        assert RelationType.BLOCKS.value == "blocks"
        assert RelationType.BLOCKED_BY.value == "blocked_by"
        assert RelationType.RELATES_TO.value == "relates_to"
        assert RelationType.DUPLICATES.value == "duplicates"
        assert RelationType.DUPLICATED_BY.value == "duplicated_by"

    def test_relation_type_equality(self) -> None:
        """Test relation type enum equality."""
        assert RelationType.BLOCKS == RelationType.BLOCKS
        assert RelationType.BLOCKS != RelationType.BLOCKED_BY
        assert RelationType.BLOCKS == "blocks"

    def test_all_relation_types_exist(self) -> None:
        """Test that all expected relation types exist."""
        expected_types = {
            "blocks",
            "blocked_by",
            "relates_to",
            "duplicates",
            "duplicated_by",
        }
        actual_types = {rt.value for rt in RelationType}
        assert actual_types == expected_types


@pytest.mark.unit
class TestTicketRelation:
    """Test TicketRelation model."""

    def test_create_relation_minimal(self) -> None:
        """Test creating a relation with minimal required data."""
        relation = TicketRelation(
            source_ticket_id="ISSUE-123",
            target_ticket_id="ISSUE-456",
            relation_type=RelationType.BLOCKS,
        )

        assert relation.source_ticket_id == "ISSUE-123"
        assert relation.target_ticket_id == "ISSUE-456"
        assert relation.relation_type == RelationType.BLOCKS
        assert relation.id is None
        assert relation.created_at is None
        assert relation.created_by is None
        assert relation.metadata == {}

    def test_create_relation_full(self) -> None:
        """Test creating a relation with all fields."""
        now = datetime.now()
        metadata = {"platform": "linear", "relation_id": "rel-123"}

        relation = TicketRelation(
            id="REL-1",
            source_ticket_id="ISSUE-123",
            target_ticket_id="ISSUE-456",
            relation_type=RelationType.BLOCKS,
            created_at=now,
            created_by="user-1",
            metadata=metadata,
        )

        assert relation.id == "REL-1"
        assert relation.source_ticket_id == "ISSUE-123"
        assert relation.target_ticket_id == "ISSUE-456"
        assert relation.relation_type == RelationType.BLOCKS
        assert relation.created_at == now
        assert relation.created_by == "user-1"
        assert relation.metadata == metadata

    def test_create_relation_with_string_type(self) -> None:
        """Test creating a relation with string relation_type."""
        relation = TicketRelation(
            source_ticket_id="ISSUE-123",
            target_ticket_id="ISSUE-456",
            relation_type="blocks",
        )

        # Pydantic should convert string to enum
        assert relation.relation_type == RelationType.BLOCKS

    def test_create_relation_missing_required_fields(self) -> None:
        """Test that creating a relation without required fields raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TicketRelation(source_ticket_id="ISSUE-123")

        error_str = str(exc_info.value)
        assert "target_ticket_id" in error_str
        assert "relation_type" in error_str

    def test_create_relation_invalid_type(self) -> None:
        """Test that creating a relation with invalid relation_type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TicketRelation(
                source_ticket_id="ISSUE-123",
                target_ticket_id="ISSUE-456",
                relation_type="invalid_type",
            )

        assert "relation_type" in str(exc_info.value)

    def test_get_inverse_type_blocks(self) -> None:
        """Test get_inverse_type for BLOCKS relationship."""
        relation = TicketRelation(
            source_ticket_id="A",
            target_ticket_id="B",
            relation_type=RelationType.BLOCKS,
        )

        inverse = relation.get_inverse_type()
        assert inverse == RelationType.BLOCKED_BY

    def test_get_inverse_type_blocked_by(self) -> None:
        """Test get_inverse_type for BLOCKED_BY relationship."""
        relation = TicketRelation(
            source_ticket_id="A",
            target_ticket_id="B",
            relation_type=RelationType.BLOCKED_BY,
        )

        inverse = relation.get_inverse_type()
        assert inverse == RelationType.BLOCKS

    def test_get_inverse_type_duplicates(self) -> None:
        """Test get_inverse_type for DUPLICATES relationship."""
        relation = TicketRelation(
            source_ticket_id="A",
            target_ticket_id="B",
            relation_type=RelationType.DUPLICATES,
        )

        inverse = relation.get_inverse_type()
        assert inverse == RelationType.DUPLICATED_BY

    def test_get_inverse_type_duplicated_by(self) -> None:
        """Test get_inverse_type for DUPLICATED_BY relationship."""
        relation = TicketRelation(
            source_ticket_id="A",
            target_ticket_id="B",
            relation_type=RelationType.DUPLICATED_BY,
        )

        inverse = relation.get_inverse_type()
        assert inverse == RelationType.DUPLICATES

    def test_get_inverse_type_relates_to(self) -> None:
        """Test get_inverse_type for RELATES_TO (symmetric relationship)."""
        relation = TicketRelation(
            source_ticket_id="A",
            target_ticket_id="B",
            relation_type=RelationType.RELATES_TO,
        )

        inverse = relation.get_inverse_type()
        # RELATES_TO is symmetric - inverse is same type
        assert inverse == RelationType.RELATES_TO

    def test_create_inverse_blocks(self) -> None:
        """Test create_inverse for BLOCKS relationship."""
        relation = TicketRelation(
            id="REL-1",
            source_ticket_id="ISSUE-123",
            target_ticket_id="ISSUE-456",
            relation_type=RelationType.BLOCKS,
            created_at=datetime.now(),
            created_by="user-1",
            metadata={"key": "value"},
        )

        inverse = relation.create_inverse()

        assert inverse.source_ticket_id == "ISSUE-456"
        assert inverse.target_ticket_id == "ISSUE-123"
        assert inverse.relation_type == RelationType.BLOCKED_BY
        assert inverse.created_at == relation.created_at
        assert inverse.created_by == relation.created_by
        assert inverse.metadata == relation.metadata
        # ID should not be copied to inverse
        assert inverse.id is None

    def test_create_inverse_relates_to(self) -> None:
        """Test create_inverse for RELATES_TO (symmetric)."""
        relation = TicketRelation(
            source_ticket_id="ISSUE-123",
            target_ticket_id="ISSUE-456",
            relation_type=RelationType.RELATES_TO,
        )

        inverse = relation.create_inverse()

        assert inverse.source_ticket_id == "ISSUE-456"
        assert inverse.target_ticket_id == "ISSUE-123"
        assert inverse.relation_type == RelationType.RELATES_TO

    def test_create_inverse_preserves_metadata(self) -> None:
        """Test that create_inverse preserves metadata."""
        metadata = {"platform": "linear", "extra": "data"}
        relation = TicketRelation(
            source_ticket_id="A",
            target_ticket_id="B",
            relation_type=RelationType.DUPLICATES,
            metadata=metadata,
        )

        inverse = relation.create_inverse()

        # Metadata should be copied (not same object)
        assert inverse.metadata == metadata
        assert inverse.metadata is not metadata

    def test_create_inverse_duplicates(self) -> None:
        """Test create_inverse for DUPLICATES relationship."""
        relation = TicketRelation(
            source_ticket_id="ISSUE-123",
            target_ticket_id="ISSUE-456",
            relation_type=RelationType.DUPLICATES,
        )

        inverse = relation.create_inverse()

        assert inverse.source_ticket_id == "ISSUE-456"
        assert inverse.target_ticket_id == "ISSUE-123"
        assert inverse.relation_type == RelationType.DUPLICATED_BY

    def test_model_dump(self) -> None:
        """Test that relation can be serialized to dict."""
        relation = TicketRelation(
            source_ticket_id="ISSUE-123",
            target_ticket_id="ISSUE-456",
            relation_type=RelationType.BLOCKS,
        )

        data = relation.model_dump()

        assert isinstance(data, dict)
        assert data["source_ticket_id"] == "ISSUE-123"
        assert data["target_ticket_id"] == "ISSUE-456"
        assert data["relation_type"] == "blocks"  # Enum should be serialized as value

    def test_model_dump_json(self) -> None:
        """Test that relation can be serialized to JSON."""
        relation = TicketRelation(
            source_ticket_id="ISSUE-123",
            target_ticket_id="ISSUE-456",
            relation_type=RelationType.BLOCKS,
        )

        json_str = relation.model_dump_json()

        assert isinstance(json_str, str)
        assert "ISSUE-123" in json_str
        assert "ISSUE-456" in json_str
        assert "blocks" in json_str

    def test_relation_with_empty_metadata(self) -> None:
        """Test that relation works with explicitly empty metadata."""
        relation = TicketRelation(
            source_ticket_id="ISSUE-123",
            target_ticket_id="ISSUE-456",
            relation_type=RelationType.BLOCKS,
            metadata={},
        )

        assert relation.metadata == {}

    def test_relation_metadata_default_factory(self) -> None:
        """Test that metadata uses default factory (not shared dict)."""
        relation1 = TicketRelation(
            source_ticket_id="A",
            target_ticket_id="B",
            relation_type=RelationType.BLOCKS,
        )
        relation2 = TicketRelation(
            source_ticket_id="C",
            target_ticket_id="D",
            relation_type=RelationType.BLOCKS,
        )

        # Modify one relation's metadata
        relation1.metadata["key"] = "value"

        # Should not affect the other relation
        assert "key" in relation1.metadata
        assert "key" not in relation2.metadata
