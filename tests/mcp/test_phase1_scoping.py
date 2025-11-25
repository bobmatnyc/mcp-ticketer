"""Comprehensive QA tests for Phase 1 ticket scoping implementation (1M-135).

Tests cover:
1. Config schema (default_team, default_cycle fields)
2. MCP tools (config_set_default_team, config_set_default_cycle)
3. Warning system (ticket_list, ticket_search)
4. Backwards compatibility
5. Integration scenarios

Implementation commits:
- 1397186: feat: implement ticket scoping Phase 1 MVP
- ec84bdd: docs: add comprehensive ticket scoping documentation
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from mcp_ticketer.core.project_config import TicketerConfig
from mcp_ticketer.mcp.server.tools.config_tools import (
    config_get,
    config_set_default_cycle,
    config_set_default_team,
)


@pytest.mark.asyncio
class TestConfigSchemaPhase1:
    """Test config schema with new Phase 1 fields."""

    async def test_load_config_without_new_fields(self, tmp_path: Path) -> None:
        """Test loading old config without default_team/default_cycle (backwards compat)."""
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        # Old config format (pre-Phase 1)
        old_config = {
            "default_adapter": "linear",
            "default_user": "user@example.com",
            "default_project": "PROJ-123",
        }
        with open(config_path, "w") as f:
            json.dump(old_config, f)

        # Load config
        with open(config_path) as f:
            data = json.load(f)
        config = TicketerConfig.from_dict(data)

        # Verify old fields preserved
        assert config.default_adapter == "linear"
        assert config.default_user == "user@example.com"
        assert config.default_project == "PROJ-123"

        # Verify new fields default to None
        assert config.default_team is None
        assert config.default_cycle is None

    async def test_load_config_with_default_team(self, tmp_path: Path) -> None:
        """Test loading config with default_team set."""
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        config_data = {
            "default_adapter": "linear",
            "default_team": "ENG",
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with open(config_path) as f:
            data = json.load(f)
        config = TicketerConfig.from_dict(data)

        assert config.default_team == "ENG"
        assert config.default_cycle is None

    async def test_load_config_with_default_cycle(self, tmp_path: Path) -> None:
        """Test loading config with default_cycle set."""
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        config_data = {
            "default_adapter": "linear",
            "default_cycle": "sprint-42",
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with open(config_path) as f:
            data = json.load(f)
        config = TicketerConfig.from_dict(data)

        assert config.default_cycle == "sprint-42"
        assert config.default_team is None

    async def test_load_config_with_both_fields(self, tmp_path: Path) -> None:
        """Test loading config with both default_team and default_cycle."""
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        config_data = {
            "default_adapter": "linear",
            "default_team": "ENG",
            "default_cycle": "sprint-42",
            "default_user": "user@example.com",
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with open(config_path) as f:
            data = json.load(f)
        config = TicketerConfig.from_dict(data)

        assert config.default_team == "ENG"
        assert config.default_cycle == "sprint-42"
        assert config.default_user == "user@example.com"

    async def test_serialize_deserialize_new_fields(self, tmp_path: Path) -> None:
        """Test that new fields serialize/deserialize correctly."""
        config = TicketerConfig(
            default_adapter="linear",
            default_team="ENG",
            default_cycle="sprint-42",
        )

        # Serialize
        config_dict = config.to_dict()
        assert config_dict["default_team"] == "ENG"
        assert config_dict["default_cycle"] == "sprint-42"

        # Deserialize
        restored = TicketerConfig.from_dict(config_dict)
        assert restored.default_team == "ENG"
        assert restored.default_cycle == "sprint-42"

    async def test_config_get_returns_new_fields(self, tmp_path: Path) -> None:
        """Test that config_get returns default_team and default_cycle."""
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        config_data = {
            "default_adapter": "linear",
            "default_team": "ENG",
            "default_cycle": "sprint-42",
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_get()

            assert result["status"] == "completed"
            assert result["config"]["default_team"] == "ENG"
            assert result["config"]["default_cycle"] == "sprint-42"


@pytest.mark.asyncio
class TestConfigSetDefaultTeam:
    """Test config_set_default_team MCP tool."""

    async def test_set_valid_team_id(self, tmp_path: Path) -> None:
        """Test setting a valid team ID."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_set_default_team("ENG")

            assert result["status"] == "completed"
            assert result["new_team"] == "ENG"
            assert result["previous_team"] is None
            assert "config_path" in result

            # Verify config persisted
            config_path = tmp_path / ".mcp-ticketer" / "config.json"
            assert config_path.exists()

            with open(config_path) as f:
                config_data = json.load(f)
            assert config_data["default_team"] == "ENG"

    async def test_set_empty_string_returns_error(self, tmp_path: Path) -> None:
        """Test that empty string returns validation error."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_set_default_team("")

            assert result["status"] == "error"
            assert "must be at least 1 character" in result["error"]

    async def test_set_team_persists_across_reads(self, tmp_path: Path) -> None:
        """Test that team ID persists when config is reloaded."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            # Set team
            result1 = await config_set_default_team("ENG")
            assert result1["status"] == "completed"

            # Read back config
            result2 = await config_get()
            assert result2["status"] == "completed"
            assert result2["config"]["default_team"] == "ENG"

    async def test_update_existing_team(self, tmp_path: Path) -> None:
        """Test updating existing team returns old and new values."""
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        # Set initial team
        initial_config = {"default_team": "OLD-TEAM"}
        with open(config_path, "w") as f:
            json.dump(initial_config, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_set_default_team("NEW-TEAM")

            assert result["status"] == "completed"
            assert result["previous_team"] == "OLD-TEAM"
            assert result["new_team"] == "NEW-TEAM"

    async def test_set_team_with_uuid_format(self, tmp_path: Path) -> None:
        """Test setting team with UUID format."""
        team_uuid = "550e8400-e29b-41d4-a716-446655440000"

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_set_default_team(team_uuid)

            assert result["status"] == "completed"
            assert result["new_team"] == team_uuid


@pytest.mark.asyncio
class TestConfigSetDefaultCycle:
    """Test config_set_default_cycle MCP tool."""

    async def test_set_valid_cycle_id(self, tmp_path: Path) -> None:
        """Test setting a valid cycle ID."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_set_default_cycle("Sprint 23")

            assert result["status"] == "completed"
            assert result["new_cycle"] == "Sprint 23"
            assert result["previous_cycle"] is None
            assert "config_path" in result

            # Verify config persisted
            config_path = tmp_path / ".mcp-ticketer" / "config.json"
            assert config_path.exists()

            with open(config_path) as f:
                config_data = json.load(f)
            assert config_data["default_cycle"] == "Sprint 23"

    async def test_set_empty_string_returns_error(self, tmp_path: Path) -> None:
        """Test that empty string returns validation error."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_set_default_cycle("")

            assert result["status"] == "error"
            assert "must be at least 1 character" in result["error"]

    async def test_set_cycle_persists_across_reads(self, tmp_path: Path) -> None:
        """Test that cycle ID persists when config is reloaded."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            # Set cycle
            result1 = await config_set_default_cycle("sprint-42")
            assert result1["status"] == "completed"

            # Read back config
            result2 = await config_get()
            assert result2["status"] == "completed"
            assert result2["config"]["default_cycle"] == "sprint-42"

    async def test_update_existing_cycle(self, tmp_path: Path) -> None:
        """Test updating existing cycle returns old and new values."""
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        # Set initial cycle
        initial_config = {"default_cycle": "sprint-41"}
        with open(config_path, "w") as f:
            json.dump(initial_config, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_set_default_cycle("sprint-42")

            assert result["status"] == "completed"
            assert result["previous_cycle"] == "sprint-41"
            assert result["new_cycle"] == "sprint-42"

    async def test_set_cycle_with_uuid_format(self, tmp_path: Path) -> None:
        """Test setting cycle with UUID format."""
        cycle_uuid = "660e8400-e29b-41d4-a716-446655440000"

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_set_default_cycle(cycle_uuid)

            assert result["status"] == "completed"
            assert result["new_cycle"] == cycle_uuid


@pytest.mark.asyncio
class TestWarningSystem:
    """Test warning system in ticket_list and ticket_search."""

    async def test_ticket_list_warns_on_large_unscoped_query(
        self, tmp_path: Path, caplog
    ) -> None:
        """Test that ticket_list warns when limit > 50 with no filters."""
        from mcp_ticketer.mcp.server.tools.ticket_tools import ticket_list

        # Mock adapter
        mock_adapter = AsyncMock()
        mock_adapter.list.return_value = []

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with caplog.at_level(logging.WARNING):
                await ticket_list(limit=100)  # No filters

                # Check warning was logged
                assert any(
                    "Large unscoped query" in record.message
                    for record in caplog.records
                )
                assert any(
                    "default_team" in record.message
                    or "default_project" in record.message
                    for record in caplog.records
                )

    async def test_ticket_list_no_warn_with_filter(
        self, tmp_path: Path, caplog
    ) -> None:
        """Test that ticket_list doesn't warn when filters are present."""
        from mcp_ticketer.mcp.server.tools.ticket_tools import ticket_list

        mock_adapter = AsyncMock()
        mock_adapter.list.return_value = []

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with caplog.at_level(logging.WARNING):
                await ticket_list(limit=100, state="open")

                # No warning should be logged
                assert not any(
                    "Large unscoped query" in record.message
                    for record in caplog.records
                )

    async def test_ticket_list_no_warn_with_small_limit(
        self, tmp_path: Path, caplog
    ) -> None:
        """Test that ticket_list doesn't warn when limit <= 50."""
        from mcp_ticketer.mcp.server.tools.ticket_tools import ticket_list

        mock_adapter = AsyncMock()
        mock_adapter.list.return_value = []

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with caplog.at_level(logging.WARNING):
                await ticket_list(limit=50)

                # No warning should be logged
                assert not any(
                    "Large unscoped query" in record.message
                    for record in caplog.records
                )

    async def test_ticket_search_warns_on_unscoped_search(
        self, tmp_path: Path, caplog
    ) -> None:
        """Test that ticket_search warns when no query or filters provided."""
        from mcp_ticketer.mcp.server.tools.search_tools import ticket_search

        mock_adapter = AsyncMock()
        mock_adapter.search.return_value = []

        with patch(
            "mcp_ticketer.mcp.server.tools.search_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with caplog.at_level(logging.WARNING):
                await ticket_search()  # No query, no filters

                # Check warning was logged
                assert any(
                    "Unscoped search" in record.message for record in caplog.records
                )
                assert any(
                    "default_project" in record.message
                    or "default_team" in record.message
                    for record in caplog.records
                )

    async def test_ticket_search_no_warn_with_query(
        self, tmp_path: Path, caplog
    ) -> None:
        """Test that ticket_search doesn't warn when query is provided."""
        from mcp_ticketer.mcp.server.tools.search_tools import ticket_search

        mock_adapter = AsyncMock()
        mock_adapter.search.return_value = []

        with patch(
            "mcp_ticketer.mcp.server.tools.search_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with caplog.at_level(logging.WARNING):
                await ticket_search(query="test")

                # No warning should be logged
                assert not any(
                    "Unscoped search" in record.message for record in caplog.records
                )

    async def test_ticket_search_no_warn_with_filters(
        self, tmp_path: Path, caplog
    ) -> None:
        """Test that ticket_search doesn't warn when filters are provided."""
        from mcp_ticketer.mcp.server.tools.search_tools import ticket_search

        mock_adapter = AsyncMock()
        mock_adapter.search.return_value = []

        with patch(
            "mcp_ticketer.mcp.server.tools.search_tools.get_adapter",
            return_value=mock_adapter,
        ):
            with caplog.at_level(logging.WARNING):
                await ticket_search(state="open")

                # No warning should be logged
                assert not any(
                    "Unscoped search" in record.message for record in caplog.records
                )


@pytest.mark.asyncio
class TestIntegrationWorkflow:
    """Integration tests for Phase 1 scoping workflow."""

    async def test_complete_phase1_workflow(self, tmp_path: Path) -> None:
        """Test complete workflow: set team, set cycle, verify config."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            # Step 1: Set default team
            result1 = await config_set_default_team("ENG")
            assert result1["status"] == "completed"
            assert result1["new_team"] == "ENG"

            # Step 2: Verify config persisted
            result2 = await config_get()
            assert result2["config"]["default_team"] == "ENG"
            # default_cycle should not be in dict when None (to_dict filters None values)
            assert "default_cycle" not in result2["config"]

            # Step 3: Set default cycle
            result3 = await config_set_default_cycle("sprint-42")
            assert result3["status"] == "completed"
            assert result3["new_cycle"] == "sprint-42"

            # Step 4: Verify both fields in config
            result4 = await config_get()
            assert result4["config"]["default_team"] == "ENG"
            assert result4["config"]["default_cycle"] == "sprint-42"

    async def test_phase1_preserves_existing_config(self, tmp_path: Path) -> None:
        """Test that Phase 1 fields don't affect existing config."""
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        # Existing config
        existing_config = {
            "default_adapter": "linear",
            "default_user": "user@example.com",
            "default_project": "PROJ-123",
            "default_tags": ["backend", "api"],
        }
        with open(config_path, "w") as f:
            json.dump(existing_config, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            # Add Phase 1 fields
            await config_set_default_team("ENG")
            await config_set_default_cycle("sprint-42")

            # Verify all fields present
            result = await config_get()
            assert result["config"]["default_adapter"] == "linear"
            assert result["config"]["default_user"] == "user@example.com"
            assert result["config"]["default_project"] == "PROJ-123"
            assert result["config"]["default_tags"] == ["backend", "api"]
            assert result["config"]["default_team"] == "ENG"
            assert result["config"]["default_cycle"] == "sprint-42"


@pytest.mark.asyncio
class TestBackwardsCompatibility:
    """Test backwards compatibility with pre-Phase 1 configs."""

    async def test_old_config_loads_without_errors(self, tmp_path: Path) -> None:
        """Test that configs from v1.1.5 or earlier load without errors."""
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        # v1.1.5 config format
        old_config = {
            "default_adapter": "linear",
            "default_user": "user@example.com",
            "default_project": "PROJ-123",
            "default_epic": "PROJ-123",
            "default_tags": ["bug", "urgent"],
            "adapters": {
                "linear": {
                    "adapter": "linear",
                    "api_key": "lin_api_key",
                    "team_id": "550e8400-e29b-41d4-a716-446655440000",
                }
            },
        }
        with open(config_path, "w") as f:
            json.dump(old_config, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_get()

            assert result["status"] == "completed"
            assert result["config"]["default_adapter"] == "linear"
            assert result["config"]["default_user"] == "user@example.com"
            # New fields not in dict when None (to_dict filters None values)
            assert "default_team" not in result["config"]
            assert "default_cycle" not in result["config"]

    async def test_default_behavior_unchanged(self, tmp_path: Path) -> None:
        """Test that default behavior is unchanged for ticket_list."""
        from mcp_ticketer.mcp.server.tools.ticket_tools import ticket_list

        mock_adapter = AsyncMock()
        mock_adapter.list.return_value = []

        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
            return_value=mock_adapter,
        ):
            # Default parameters should work as before
            result = await ticket_list()

            assert result["status"] == "completed"
            # Verify adapter.list was called with expected parameters
            mock_adapter.list.assert_called_once()
