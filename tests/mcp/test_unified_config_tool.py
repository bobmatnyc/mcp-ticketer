"""Tests for unified config tool.

Tests the consolidated config() MCP tool that unifies all configuration
operations under a single interface.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_ticketer.mcp.server.tools.config_tools import config


@pytest.mark.asyncio
class TestConfigUnifiedTool:
    """Test suite for unified config() tool."""

    async def test_config_get_action(self, tmp_path: Path) -> None:
        """Test config with action='get'."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config(action="get")

            assert result["status"] == "completed"
            assert "config" in result
            assert result["config"]["default_adapter"] == "aitrackdown"

    async def test_config_set_adapter_action(self, tmp_path: Path) -> None:
        """Test config with action='set' for adapter."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config(action="set", key="adapter", value="linear")

            assert result["status"] == "completed"
            assert result["new_adapter"] == "linear"

            # Verify config was saved
            config_path = tmp_path / ".mcp-ticketer" / "config.json"
            assert config_path.exists()
            with open(config_path) as f:
                config_data = json.load(f)
            assert config_data["default_adapter"] == "linear"

    async def test_config_set_project_action(self, tmp_path: Path) -> None:
        """Test config with action='set' for project."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config(action="set", key="project", value="PROJ-123")

            assert result["status"] == "completed"
            assert result["new_project"] == "PROJ-123"

    async def test_config_set_user_action(self, tmp_path: Path) -> None:
        """Test config with action='set' for user."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config(action="set", key="user", value="user@example.com")

            assert result["status"] == "completed"
            assert result["new_user"] == "user@example.com"

    async def test_config_set_tags_action(self, tmp_path: Path) -> None:
        """Test config with action='set' for tags."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config(action="set", key="tags", value=["bug", "high"])

            assert result["status"] == "completed"
            assert result["default_tags"] == ["bug", "high"]

    async def test_config_set_team_action(self, tmp_path: Path) -> None:
        """Test config with action='set' for team."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config(action="set", key="team", value="ENG")

            assert result["status"] == "completed"
            assert result["new_team"] == "ENG"

    async def test_config_set_cycle_action(self, tmp_path: Path) -> None:
        """Test config with action='set' for cycle."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config(action="set", key="cycle", value="Sprint 23")

            assert result["status"] == "completed"
            assert result["new_cycle"] == "Sprint 23"

    async def test_config_set_assignment_labels_action(self, tmp_path: Path) -> None:
        """Test config with action='set' for assignment_labels."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config(
                action="set", key="assignment_labels", value=["my-work", "active"]
            )

            assert result["status"] == "completed"
            assert result["assignment_labels"] == ["my-work", "active"]

    async def test_config_validate_action(self, tmp_path: Path) -> None:
        """Test config with action='validate'."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config(action="validate")

            assert result["status"] == "completed"
            assert "validation_results" in result
            assert "all_valid" in result

    async def test_config_test_action(self, tmp_path: Path) -> None:
        """Test config with action='test'."""
        # Mock health check
        mock_health_result = {
            "status": "completed",
            "adapters": {
                "aitrackdown": {
                    "status": "healthy",
                    "message": "Adapter initialized and API call successful",
                }
            },
        }

        with (
            patch(
                "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
                return_value=tmp_path,
            ),
            patch(
                "mcp_ticketer.mcp.server.tools.diagnostic_tools.check_adapter_health",
                return_value=mock_health_result,
            ),
        ):
            result = await config(action="test", adapter_name="aitrackdown")

            assert result["status"] == "completed"
            assert result["adapter"] == "aitrackdown"
            assert result["healthy"] is True

    async def test_config_list_adapters_action(self, tmp_path: Path) -> None:
        """Test config with action='list_adapters'."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config(action="list_adapters")

            assert result["status"] == "completed"
            assert "adapters" in result
            assert isinstance(result["adapters"], list)
            assert len(result["adapters"]) > 0

    async def test_config_get_requirements_action(self, tmp_path: Path) -> None:
        """Test config with action='get_requirements'."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config(action="get_requirements", adapter="linear")

            assert result["status"] == "completed"
            assert result["adapter"] == "linear"
            assert "requirements" in result
            assert "api_key" in result["requirements"]

    async def test_config_invalid_action(self, tmp_path: Path) -> None:
        """Test config with invalid action."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config(action="invalid_action")

            assert result["status"] == "error"
            assert "Invalid action" in result["error"]
            assert "valid_actions" in result

    async def test_config_set_missing_key(self, tmp_path: Path) -> None:
        """Test config action='set' without key parameter."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config(action="set", value="linear")

            assert result["status"] == "error"
            assert "key' is required" in result["error"]

    async def test_config_set_missing_value(self, tmp_path: Path) -> None:
        """Test config action='set' without value parameter."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config(action="set", key="adapter")

            assert result["status"] == "error"
            assert "value' is required" in result["error"]

    async def test_config_test_missing_adapter_name(self, tmp_path: Path) -> None:
        """Test config action='test' without adapter_name parameter."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config(action="test")

            assert result["status"] == "error"
            assert "adapter_name' is required" in result["error"]

    async def test_config_get_requirements_missing_adapter(
        self, tmp_path: Path
    ) -> None:
        """Test config action='get_requirements' without adapter parameter."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config(action="get_requirements")

            assert result["status"] == "error"
            assert "adapter' is required" in result["error"]

    async def test_config_case_insensitive_action(self, tmp_path: Path) -> None:
        """Test that action parameter is case-insensitive."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config(action="GET")

            assert result["status"] == "completed"
            assert "config" in result

    async def test_config_preserves_existing_config(self, tmp_path: Path) -> None:
        """Test that unified tool preserves other config when setting."""
        # Create initial config
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        initial_config = {
            "default_adapter": "linear",
            "default_user": "user@example.com",
            "default_project": "PROJ-123",
        }
        with open(config_path, "w") as f:
            json.dump(initial_config, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config(action="set", key="team", value="ENG")

            assert result["status"] == "completed"

            # Verify other fields preserved
            with open(config_path) as f:
                config_data = json.load(f)
            assert config_data["default_adapter"] == "linear"
            assert config_data["default_user"] == "user@example.com"
            assert config_data["default_project"] == "PROJ-123"
            assert config_data["default_team"] == "ENG"

    async def test_config_multiple_operations_sequence(self, tmp_path: Path) -> None:
        """Test sequential operations with unified tool."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            # Set adapter
            result1 = await config(action="set", key="adapter", value="linear")
            assert result1["status"] == "completed"

            # Set project
            result2 = await config(action="set", key="project", value="PROJ-123")
            assert result2["status"] == "completed"

            # Get config to verify both
            result3 = await config(action="get")
            assert result3["status"] == "completed"
            assert result3["config"]["default_adapter"] == "linear"
            assert result3["config"]["default_project"] == "PROJ-123"

    async def test_config_error_propagation(self, tmp_path: Path) -> None:
        """Test that errors from underlying functions are propagated."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            # Try to set invalid adapter
            result = await config(action="set", key="adapter", value="invalid_adapter")

            assert result["status"] == "error"
            assert "Invalid adapter" in result["error"]

    async def test_config_hint_messages(self, tmp_path: Path) -> None:
        """Test that helpful hint messages are provided."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            # Missing key for set action
            result = await config(action="set", value="test")
            assert "hint" in result
            assert "config(action='set'" in result["hint"]

            # Invalid action
            result = await config(action="invalid")
            assert "hint" in result
            assert "config(action='get')" in result["hint"]
