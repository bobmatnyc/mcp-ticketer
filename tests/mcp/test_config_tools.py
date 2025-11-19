"""Tests for configuration management MCP tools.

Tests the MCP tools for managing project-local configuration including:
- config_set_primary_adapter: Setting default adapter
- config_set_default_project: Setting default project/epic
- config_set_default_user: Setting default assignee
- config_get: Retrieving current configuration
- Error handling and validation
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_ticketer.core.project_config import AdapterType, TicketerConfig
from mcp_ticketer.mcp.server.tools.config_tools import (
    config_get,
    config_set_default_project,
    config_set_default_user,
    config_set_primary_adapter,
)


@pytest.mark.asyncio
class TestConfigSetPrimaryAdapter:
    """Test suite for config_set_primary_adapter MCP tool."""

    async def test_set_valid_adapter(self, tmp_path: Path) -> None:
        """Test setting a valid adapter."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_set_primary_adapter("linear")

            assert result["status"] == "completed"
            assert result["new_adapter"] == "linear"
            assert result["previous_adapter"] == "aitrackdown"
            assert "config_path" in result

            # Verify config was saved
            config_path = tmp_path / ".mcp-ticketer" / "config.json"
            assert config_path.exists()

            with open(config_path) as f:
                config_data = json.load(f)
            assert config_data["default_adapter"] == "linear"

    async def test_set_invalid_adapter(self, tmp_path: Path) -> None:
        """Test setting an invalid adapter name."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_set_primary_adapter("invalid_adapter")

            assert result["status"] == "error"
            assert "Invalid adapter" in result["error"]
            assert "valid_adapters" in result

    async def test_adapter_case_insensitive(self, tmp_path: Path) -> None:
        """Test that adapter names are case-insensitive."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_set_primary_adapter("LINEAR")

            assert result["status"] == "completed"
            assert result["new_adapter"] == "linear"

    async def test_preserves_existing_config(self) -> None:
        """Test that setting adapter preserves other configuration."""
        import tempfile

        # Use a unique temp directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create initial config
            config_dir = tmp_path / ".mcp-ticketer"
            config_dir.mkdir(parents=True)
            config_path = config_dir / "config.json"

            initial_config = {
                "default_adapter": "github",
                "default_user": "user@example.com",
                "default_project": "PROJ-123",
            }
            with open(config_path, "w") as f:
                json.dump(initial_config, f)

            with patch(
                "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
                return_value=tmp_path,
            ):
                result = await config_set_primary_adapter("linear")

                assert result["status"] == "completed"
                assert result["previous_adapter"] == "github"

                # Verify other fields preserved
                with open(config_path) as f:
                    config_data = json.load(f)
                assert config_data["default_user"] == "user@example.com"
                assert config_data["default_project"] == "PROJ-123"


@pytest.mark.asyncio
class TestConfigSetDefaultProject:
    """Test suite for config_set_default_project MCP tool."""

    async def test_set_default_project(self, tmp_path: Path) -> None:
        """Test setting a default project."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_set_default_project("PROJ-123")

            assert result["status"] == "completed"
            assert result["new_project"] == "PROJ-123"
            assert result["previous_project"] is None

            # Verify config was saved
            config_path = tmp_path / ".mcp-ticketer" / "config.json"
            assert config_path.exists()

            with open(config_path) as f:
                config_data = json.load(f)
            assert config_data["default_project"] == "PROJ-123"
            assert config_data["default_epic"] == "PROJ-123"  # Backward compat

    async def test_update_existing_project(self, tmp_path: Path) -> None:
        """Test updating an existing default project."""
        # Create initial config
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        initial_config = {"default_project": "OLD-PROJ"}
        with open(config_path, "w") as f:
            json.dump(initial_config, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_set_default_project("NEW-PROJ")

            assert result["status"] == "completed"
            assert result["previous_project"] == "OLD-PROJ"
            assert result["new_project"] == "NEW-PROJ"

    async def test_clear_default_project(self, tmp_path: Path) -> None:
        """Test clearing the default project."""
        # Create initial config
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        initial_config = {"default_project": "PROJ-123"}
        with open(config_path, "w") as f:
            json.dump(initial_config, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_set_default_project("")

            assert result["status"] == "completed"
            assert "cleared" in result["message"].lower()

            with open(config_path) as f:
                config_data = json.load(f)
            assert "default_project" not in config_data


@pytest.mark.asyncio
class TestConfigSetDefaultUser:
    """Test suite for config_set_default_user MCP tool."""

    async def test_set_default_user(self, tmp_path: Path) -> None:
        """Test setting a default user."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_set_default_user("user@example.com")

            assert result["status"] == "completed"
            assert result["new_user"] == "user@example.com"
            assert result["previous_user"] is None

            # Verify config was saved
            config_path = tmp_path / ".mcp-ticketer" / "config.json"
            assert config_path.exists()

            with open(config_path) as f:
                config_data = json.load(f)
            assert config_data["default_user"] == "user@example.com"

    async def test_set_user_by_id(self, tmp_path: Path) -> None:
        """Test setting default user by UUID."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            user_id = "550e8400-e29b-41d4-a716-446655440000"
            result = await config_set_default_user(user_id)

            assert result["status"] == "completed"
            assert result["new_user"] == user_id

            with open(tmp_path / ".mcp-ticketer" / "config.json") as f:
                config_data = json.load(f)
            assert config_data["default_user"] == user_id

    async def test_update_existing_user(self, tmp_path: Path) -> None:
        """Test updating an existing default user."""
        # Create initial config
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        initial_config = {"default_user": "old@example.com"}
        with open(config_path, "w") as f:
            json.dump(initial_config, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_set_default_user("new@example.com")

            assert result["status"] == "completed"
            assert result["previous_user"] == "old@example.com"
            assert result["new_user"] == "new@example.com"

    async def test_clear_default_user(self, tmp_path: Path) -> None:
        """Test clearing the default user."""
        # Create initial config
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        initial_config = {"default_user": "user@example.com"}
        with open(config_path, "w") as f:
            json.dump(initial_config, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_set_default_user("")

            assert result["status"] == "completed"
            assert "cleared" in result["message"].lower()


@pytest.mark.asyncio
class TestConfigGet:
    """Test suite for config_get MCP tool."""

    async def test_get_default_config(self, tmp_path: Path) -> None:
        """Test getting default configuration when no config file exists."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_get()

            assert result["status"] == "completed"
            assert result["config_exists"] is False
            assert "defaults" in result["message"].lower()
            assert result["config"]["default_adapter"] == "aitrackdown"

    async def test_get_existing_config(self, tmp_path: Path) -> None:
        """Test getting existing configuration."""
        # Create config
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        config_data = {
            "default_adapter": "linear",
            "default_user": "user@example.com",
            "default_project": "PROJ-123",
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_get()

            assert result["status"] == "completed"
            assert result["config_exists"] is True
            assert result["config"]["default_adapter"] == "linear"
            assert result["config"]["default_user"] == "user@example.com"
            assert result["config"]["default_project"] == "PROJ-123"

    async def test_masks_sensitive_values(self, tmp_path: Path) -> None:
        """Test that sensitive values are masked in response."""
        # Create config with sensitive data
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        config_data = {
            "default_adapter": "linear",
            "adapters": {
                "linear": {
                    "adapter": "linear",
                    "api_key": "secret_key_12345",
                    "team_id": "team-uuid",
                }
            },
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_get()

            assert result["status"] == "completed"
            # Check that API key is masked
            assert result["config"]["adapters"]["linear"]["api_key"] == "***"
            # Check that non-sensitive values are preserved
            assert result["config"]["adapters"]["linear"]["team_id"] == "team-uuid"

    async def test_config_path_in_response(self, tmp_path: Path) -> None:
        """Test that config path is included in response."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_get()

            assert result["status"] == "completed"
            assert "config_path" in result
            assert ".mcp-ticketer/config.json" in result["config_path"]
