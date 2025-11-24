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

from mcp_ticketer.mcp.server.tools.config_tools import (
    config_get,
    config_set_assignment_labels,
    config_set_default_project,
    config_set_default_user,
    config_set_primary_adapter,
    config_test_adapter,
    config_validate,
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


@pytest.mark.asyncio
class TestConfigValidate:
    """Test suite for config_validate MCP tool."""

    async def test_config_validate_no_adapters(self, tmp_path: Path) -> None:
        """Test validation with no adapters configured."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_validate()

            assert result["status"] == "completed"
            assert result["all_valid"] is True
            assert result["validation_results"] == {}
            assert result["issues"] == []
            assert result["message"] == "No adapters configured"

    async def test_config_validate_all_valid(self, tmp_path: Path) -> None:
        """Test validation with all valid adapter configurations."""
        # Create config with valid adapters
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        config_data = {
            "default_adapter": "linear",
            "adapters": {
                "linear": {
                    "adapter": "linear",
                    "api_key": "test_key_12345",
                    "team_key": "ENG",
                },
                "aitrackdown": {
                    "adapter": "aitrackdown",
                    "base_path": str(tmp_path / "tickets"),
                },
            },
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_validate()

            assert result["status"] == "completed"
            assert result["all_valid"] is True
            assert len(result["validation_results"]) == 2
            assert result["validation_results"]["linear"]["valid"] is True
            assert result["validation_results"]["linear"]["error"] is None
            assert result["validation_results"]["aitrackdown"]["valid"] is True
            assert result["issues"] == []
            assert result["message"] == "All configurations valid"

    async def test_config_validate_with_errors(self, tmp_path: Path) -> None:
        """Test validation with invalid adapter configurations."""
        # Create config with invalid Linear adapter (missing api_key and team info)
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        config_data = {
            "default_adapter": "linear",
            "adapters": {
                "linear": {
                    "adapter": "linear",
                    # Missing api_key and team_key/team_id
                },
            },
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_validate()

            assert result["status"] == "completed"
            assert result["all_valid"] is False
            assert len(result["validation_results"]) == 1
            assert result["validation_results"]["linear"]["valid"] is False
            assert result["validation_results"]["linear"]["error"] is not None
            assert len(result["issues"]) == 1
            assert "linear:" in result["issues"][0]
            assert "validation issue(s)" in result["message"]

    async def test_config_validate_multiple_adapters(self, tmp_path: Path) -> None:
        """Test validation with mixed valid and invalid adapters."""
        # Create config with one valid and one invalid adapter
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        config_data = {
            "default_adapter": "linear",
            "adapters": {
                "linear": {
                    "adapter": "linear",
                    # Invalid: missing api_key
                },
                "aitrackdown": {
                    "adapter": "aitrackdown",
                    "base_path": str(tmp_path / "tickets"),
                },
                "github": {
                    "adapter": "github",
                    # Invalid: missing token, owner, repo
                },
            },
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_validate()

            assert result["status"] == "completed"
            assert result["all_valid"] is False
            assert len(result["validation_results"]) == 3
            # Linear should be invalid
            assert result["validation_results"]["linear"]["valid"] is False
            # AITrackdown should be valid
            assert result["validation_results"]["aitrackdown"]["valid"] is True
            # GitHub should be invalid
            assert result["validation_results"]["github"]["valid"] is False
            # Should have 2 issues
            assert len(result["issues"]) == 2
            assert any("linear:" in issue for issue in result["issues"])
            assert any("github:" in issue for issue in result["issues"])


@pytest.mark.asyncio
class TestConfigTestAdapter:
    """Test suite for config_test_adapter MCP tool."""

    async def test_config_test_adapter_success(self, tmp_path: Path) -> None:
        """Test adapter health check when adapter is healthy."""
        # Mock check_adapter_health to return healthy status
        mock_health_result = {
            "status": "completed",
            "adapters": {
                "aitrackdown": {
                    "status": "healthy",
                    "message": "Adapter initialized and API call successful",
                }
            },
        }

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ), patch(
            "mcp_ticketer.mcp.server.tools.diagnostic_tools.check_adapter_health",
            return_value=mock_health_result,
        ):
            result = await config_test_adapter("aitrackdown")

            assert result["status"] == "completed"
            assert result["adapter"] == "aitrackdown"
            assert result["healthy"] is True
            assert "successful" in result["message"].lower()

    async def test_config_test_adapter_failure(self, tmp_path: Path) -> None:
        """Test adapter health check when adapter is unhealthy."""
        # Mock check_adapter_health to return unhealthy status
        mock_health_result = {
            "status": "completed",
            "adapters": {
                "linear": {
                    "status": "unhealthy",
                    "error": "Invalid API credentials",
                    "error_type": "authentication",
                }
            },
        }

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ), patch(
            "mcp_ticketer.mcp.server.tools.diagnostic_tools.check_adapter_health",
            return_value=mock_health_result,
        ):
            result = await config_test_adapter("linear")

            assert result["status"] == "completed"
            assert result["adapter"] == "linear"
            assert result["healthy"] is False
            assert "credentials" in result["message"].lower()
            assert result["error_type"] == "authentication"

    async def test_config_test_adapter_invalid_name(self, tmp_path: Path) -> None:
        """Test adapter health check with invalid adapter name."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_test_adapter("invalid_adapter")

            assert result["status"] == "error"
            assert "Invalid adapter" in result["error"]
            assert "valid_adapters" in result
            assert isinstance(result["valid_adapters"], list)
            # Should contain valid adapter names
            assert "linear" in result["valid_adapters"]
            assert "github" in result["valid_adapters"]
            assert "jira" in result["valid_adapters"]
            assert "aitrackdown" in result["valid_adapters"]

    async def test_config_test_adapter_not_configured(self, tmp_path: Path) -> None:
        """Test adapter health check when adapter is not configured."""
        # Mock check_adapter_health to return not configured error
        mock_health_result = {
            "status": "error",
            "error": "Adapter 'github' is not configured",
        }

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ), patch(
            "mcp_ticketer.mcp.server.tools.diagnostic_tools.check_adapter_health",
            return_value=mock_health_result,
        ):
            result = await config_test_adapter("github")

            assert result["status"] == "error"
            assert "not configured" in result["error"].lower()


@pytest.mark.asyncio
class TestConfigSetAssignmentLabels:
    """Test suite for config_set_assignment_labels MCP tool."""

    async def test_config_set_assignment_labels_success(self, tmp_path: Path) -> None:
        """Test setting valid assignment labels."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            labels = ["my-work", "in-progress", "assigned-to-me"]
            result = await config_set_assignment_labels(labels)

            assert result["status"] == "completed"
            assert result["assignment_labels"] == labels
            assert "my-work, in-progress, assigned-to-me" in result["message"]
            assert "config_path" in result

            # Verify config was saved
            config_path = tmp_path / ".mcp-ticketer" / "config.json"
            assert config_path.exists()

            with open(config_path) as f:
                config_data = json.load(f)
            assert config_data["assignment_labels"] == labels

    async def test_config_set_assignment_labels_empty_list(
        self, tmp_path: Path
    ) -> None:
        """Test that empty list clears assignment labels."""
        # First set some labels
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        initial_config = {"assignment_labels": ["my-work", "active"]}
        with open(config_path, "w") as f:
            json.dump(initial_config, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_set_assignment_labels([])

            assert result["status"] == "completed"
            assert result["assignment_labels"] == []
            assert "cleared" in result["message"].lower()

            # Verify labels were cleared in config
            with open(config_path) as f:
                config_data = json.load(f)
            # Empty list should result in None in the config
            assert config_data.get("assignment_labels") is None

    async def test_config_set_assignment_labels_validation(
        self, tmp_path: Path
    ) -> None:
        """Test label validation for length constraints."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            # Test label too short (< 2 chars)
            result = await config_set_assignment_labels(["a"])
            assert result["status"] == "error"
            assert "must be 2-50 characters" in result["error"]

            # Test label too long (> 50 chars)
            long_label = "a" * 51
            result = await config_set_assignment_labels([long_label])
            assert result["status"] == "error"
            assert "must be 2-50 characters" in result["error"]

            # Test empty string
            result = await config_set_assignment_labels([""])
            assert result["status"] == "error"
            assert "must be 2-50 characters" in result["error"]

    async def test_config_set_assignment_labels_persistence(
        self, tmp_path: Path
    ) -> None:
        """Test that labels persist correctly to config file."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            # Set initial labels
            labels1 = ["work-item", "active"]
            result1 = await config_set_assignment_labels(labels1)
            assert result1["status"] == "completed"

            # Update with different labels
            labels2 = ["my-tasks", "urgent", "sprint-active"]
            result2 = await config_set_assignment_labels(labels2)
            assert result2["status"] == "completed"

            # Verify final state
            config_path = tmp_path / ".mcp-ticketer" / "config.json"
            with open(config_path) as f:
                config_data = json.load(f)
            assert config_data["assignment_labels"] == labels2

            # Verify labels from first set were replaced
            assert "work-item" not in config_data["assignment_labels"]
            assert "my-tasks" in config_data["assignment_labels"]

    async def test_config_set_assignment_labels_preserves_other_config(
        self, tmp_path: Path
    ) -> None:
        """Test that setting labels preserves other configuration."""
        # Create initial config with other fields
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
            result = await config_set_assignment_labels(["my-work"])
            assert result["status"] == "completed"

            # Verify other fields preserved
            with open(config_path) as f:
                config_data = json.load(f)
            assert config_data["default_adapter"] == "linear"
            assert config_data["default_user"] == "user@example.com"
            assert config_data["default_project"] == "PROJ-123"
            assert config_data["assignment_labels"] == ["my-work"]
