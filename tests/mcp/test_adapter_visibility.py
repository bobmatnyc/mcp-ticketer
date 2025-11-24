"""Tests for adapter visibility in MCP tool responses.

This module tests that all MCP tools properly include adapter metadata
in their responses to provide visibility into which adapter handled each operation.
"""

import pytest

from mcp_ticketer.adapters.aitrackdown import AITrackdownAdapter


class TestBaseAdapterProperties:
    """Test adapter_type and adapter_display_name properties."""

    def test_aitrackdown_adapter_type(self, temp_dir) -> None:
        """Test AITrackdown adapter_type property."""
        config = {"project_path": str(temp_dir)}
        adapter = AITrackdownAdapter(config)

        assert adapter.adapter_type == "aitrackdown"
        assert adapter.adapter_display_name == "Aitrackdown"

    def test_adapter_type_from_class_name(self, temp_dir) -> None:
        """Test that adapter_type is correctly extracted from class name."""
        config = {"project_path": str(temp_dir)}
        adapter = AITrackdownAdapter(config)

        # Verify the property correctly strips "Adapter" suffix and lowercases
        assert adapter.adapter_type == "aitrackdown"
        assert isinstance(adapter.adapter_type, str)
        assert adapter.adapter_type.islower()


class TestToolResponseMetadata:
    """Test that MCP tools include adapter metadata in responses."""

    @pytest.mark.asyncio
    async def test_ticket_create_includes_adapter_metadata(self, temp_dir):
        """Test that ticket_create includes adapter info."""
        from mcp_ticketer.mcp.server.server_sdk import configure_adapter
        from mcp_ticketer.mcp.server.tools.ticket_tools import ticket_create

        # Configure adapter
        config = {"project_path": str(temp_dir)}
        configure_adapter("aitrackdown", config)

        # Create ticket
        result = await ticket_create(
            title="Test ticket",
            description="Test description",
            auto_detect_labels=False,
        )

        # Verify adapter metadata present
        assert result["status"] == "completed"
        assert "adapter" in result
        assert "adapter_name" in result
        assert result["adapter"] == "aitrackdown"
        assert result["adapter_name"] == "Aitrackdown"
        assert "ticket_id" in result

    @pytest.mark.asyncio
    async def test_ticket_list_includes_adapter_metadata(self, temp_dir):
        """Test that ticket_list includes adapter info."""
        from mcp_ticketer.mcp.server.server_sdk import configure_adapter
        from mcp_ticketer.mcp.server.tools.ticket_tools import ticket_list

        # Configure adapter
        config = {"project_path": str(temp_dir)}
        configure_adapter("aitrackdown", config)

        # List tickets
        result = await ticket_list(limit=10)

        # Verify adapter metadata present
        assert result["status"] == "completed"
        assert "adapter" in result
        assert "adapter_name" in result
        assert result["adapter"] == "aitrackdown"
        assert result["adapter_name"] == "Aitrackdown"

    @pytest.mark.asyncio
    async def test_epic_create_includes_adapter_metadata(self, temp_dir):
        """Test that epic_create includes adapter info."""
        from mcp_ticketer.mcp.server.server_sdk import configure_adapter
        from mcp_ticketer.mcp.server.tools.hierarchy_tools import epic_create

        # Configure adapter
        config = {"project_path": str(temp_dir)}
        configure_adapter("aitrackdown", config)

        # Create epic
        result = await epic_create(
            title="Test Epic",
            description="Test epic description",
        )

        # Verify adapter metadata present
        assert result["status"] == "completed"
        assert "adapter" in result
        assert "adapter_name" in result
        assert result["adapter"] == "aitrackdown"
        assert result["adapter_name"] == "Aitrackdown"
        assert "ticket_id" in result


class TestAdapterMetadataConsistency:
    """Test that adapter metadata is consistent across all tools."""

    @pytest.mark.asyncio
    async def test_adapter_metadata_format_consistent(self, temp_dir):
        """Test that all tools use same metadata format."""
        from mcp_ticketer.mcp.server.server_sdk import configure_adapter
        from mcp_ticketer.mcp.server.tools.ticket_tools import (
            ticket_create,
            ticket_list,
        )

        # Configure adapter
        config = {"project_path": str(temp_dir)}
        configure_adapter("aitrackdown", config)

        # Create ticket
        create_result = await ticket_create(
            title="Test",
            auto_detect_labels=False,
        )

        # List tickets
        list_result = await ticket_list(limit=5)

        # Both should have same metadata structure
        assert "adapter" in create_result
        assert "adapter" in list_result
        assert create_result["adapter"] == list_result["adapter"]
        assert create_result["adapter_name"] == list_result["adapter_name"]


@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory for testing."""
    return tmp_path
