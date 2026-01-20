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
    config_get_adapter_requirements,
    config_list_adapters,
    config_set_assignment_labels,
    config_set_default_project,
    config_set_default_user,
    config_set_primary_adapter,
    config_setup_wizard,
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


@pytest.mark.asyncio
class TestConfigListAdapters:
    """Test suite for config_list_adapters MCP tool."""

    async def test_list_adapters_no_config(self, tmp_path: Path) -> None:
        """Test listing adapters when no config file exists."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_list_adapters()

            assert result["status"] == "completed"
            assert "adapters" in result
            assert isinstance(result["adapters"], list)
            assert len(result["adapters"]) > 0  # Should have registered adapters
            assert result["default_adapter"] == "aitrackdown"  # Default
            assert result["total_configured"] == 0  # No adapters configured
            assert "No adapters configured" in result["message"]

    async def test_list_adapters_with_configured(self, tmp_path: Path) -> None:
        """Test listing adapters with some configured."""
        # Create config with Linear configured
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        config_data = {
            "default_adapter": "linear",
            "adapters": {
                "linear": {
                    "adapter": "linear",
                    "api_key": "test_key",
                    "team_key": "ENG",
                },
                "aitrackdown": {
                    "adapter": "aitrackdown",
                },
            },
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_list_adapters()

            assert result["status"] == "completed"
            assert result["total_configured"] == 2
            assert result["default_adapter"] == "linear"

            # Find Linear adapter in list
            linear_adapter = next(
                (a for a in result["adapters"] if a["type"] == "linear"), None
            )
            assert linear_adapter is not None
            assert linear_adapter["configured"] is True
            assert linear_adapter["is_default"] is True
            assert linear_adapter["name"] == "Linear"
            assert "description" in linear_adapter

            # Find GitHub adapter (should not be configured)
            github_adapter = next(
                (a for a in result["adapters"] if a["type"] == "github"), None
            )
            if github_adapter:  # Only test if GitHub adapter is registered
                assert github_adapter["configured"] is False
                assert github_adapter["is_default"] is False

    async def test_list_adapters_default_marked(self, tmp_path: Path) -> None:
        """Test that default adapter is correctly marked."""
        # Create config with multiple adapters, GitHub as default
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        config_data = {
            "default_adapter": "github",
            "adapters": {
                "linear": {
                    "adapter": "linear",
                    "api_key": "test_key",
                    "team_key": "ENG",
                },
                "github": {
                    "adapter": "github",
                    "token": "gh_token",
                    "owner": "test",
                    "repo": "test-repo",
                },
            },
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_list_adapters()

            assert result["status"] == "completed"
            assert result["default_adapter"] == "github"

            # GitHub should be default
            github_adapter = next(
                (a for a in result["adapters"] if a["type"] == "github"), None
            )
            if github_adapter:
                assert github_adapter["is_default"] is True
                assert github_adapter["configured"] is True

            # Linear should not be default
            linear_adapter = next(
                (a for a in result["adapters"] if a["type"] == "linear"), None
            )
            assert linear_adapter is not None
            assert linear_adapter["is_default"] is False
            assert linear_adapter["configured"] is True

    async def test_list_adapters_sorting(self, tmp_path: Path) -> None:
        """Test that configured adapters are sorted before unconfigured."""
        # Create config with one adapter configured
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        config_data = {
            "default_adapter": "jira",
            "adapters": {
                "jira": {
                    "adapter": "jira",
                    "server": "https://test.atlassian.net",
                    "email": "test@example.com",
                    "api_token": "token",
                },
            },
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_list_adapters()

            assert result["status"] == "completed"

            # Find configured and unconfigured adapters
            configured_adapters = [a for a in result["adapters"] if a["configured"]]
            unconfigured_adapters = [
                a for a in result["adapters"] if not a["configured"]
            ]

            # Configured should appear before unconfigured
            if configured_adapters and unconfigured_adapters:
                first_configured_idx = result["adapters"].index(configured_adapters[0])
                first_unconfigured_idx = result["adapters"].index(
                    unconfigured_adapters[0]
                )
                assert first_configured_idx < first_unconfigured_idx

    async def test_list_adapters_metadata(self, tmp_path: Path) -> None:
        """Test that adapter metadata is included."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_list_adapters()

            assert result["status"] == "completed"

            # Check each adapter has required fields
            for adapter in result["adapters"]:
                assert "type" in adapter
                assert "name" in adapter
                assert "configured" in adapter
                assert "is_default" in adapter
                assert "description" in adapter
                assert isinstance(adapter["configured"], bool)
                assert isinstance(adapter["is_default"], bool)
                assert isinstance(adapter["description"], str)


@pytest.mark.asyncio
class TestConfigGetAdapterRequirements:
    """Test suite for config_get_adapter_requirements MCP tool."""

    async def test_get_linear_requirements(self, tmp_path: Path) -> None:
        """Test getting Linear adapter requirements."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_get_adapter_requirements("linear")

            assert result["status"] == "completed"
            assert result["adapter"] == "linear"
            assert "requirements" in result

            # Check required fields
            assert "api_key" in result["requirements"]
            assert result["requirements"]["api_key"]["required"] is True
            assert result["requirements"]["api_key"]["type"] == "string"
            assert "env_var" in result["requirements"]["api_key"]
            assert result["requirements"]["api_key"]["env_var"] == "LINEAR_API_KEY"

            # Check team_key field
            assert "team_key" in result["requirements"]
            assert result["requirements"]["team_key"]["required"] is True

            # Check optional fields
            assert "workspace" in result["requirements"]
            assert result["requirements"]["workspace"]["required"] is False

            # Check summary fields
            assert "total_fields" in result
            assert "required_fields" in result
            assert "optional_fields" in result
            assert "api_key" in result["required_fields"]
            assert "workspace" in result["optional_fields"]

    async def test_get_github_requirements(self, tmp_path: Path) -> None:
        """Test getting GitHub adapter requirements."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_get_adapter_requirements("github")

            assert result["status"] == "completed"
            assert result["adapter"] == "github"

            # Check required fields
            assert "token" in result["requirements"]
            assert result["requirements"]["token"]["required"] is True
            assert result["requirements"]["token"]["env_var"] == "GITHUB_TOKEN"

            assert "owner" in result["requirements"]
            assert result["requirements"]["owner"]["required"] is True

            assert "repo" in result["requirements"]
            assert result["requirements"]["repo"]["required"] is True

            # Verify all GitHub required fields are in the list
            assert set(result["required_fields"]) == {"token", "owner", "repo"}

    async def test_get_jira_requirements(self, tmp_path: Path) -> None:
        """Test getting JIRA adapter requirements."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_get_adapter_requirements("jira")

            assert result["status"] == "completed"
            assert result["adapter"] == "jira"

            # Check required fields
            assert "server" in result["requirements"]
            assert result["requirements"]["server"]["required"] is True
            assert "validation" in result["requirements"]["server"]

            assert "email" in result["requirements"]
            assert result["requirements"]["email"]["required"] is True
            assert "validation" in result["requirements"]["email"]

            assert "api_token" in result["requirements"]
            assert result["requirements"]["api_token"]["required"] is True

            # Check optional project_key
            assert "project_key" in result["requirements"]
            assert result["requirements"]["project_key"]["required"] is False

    async def test_get_aitrackdown_requirements(self, tmp_path: Path) -> None:
        """Test getting AITrackdown adapter requirements."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_get_adapter_requirements("aitrackdown")

            assert result["status"] == "completed"
            assert result["adapter"] == "aitrackdown"

            # AITrackdown has minimal requirements
            assert "base_path" in result["requirements"]
            assert result["requirements"]["base_path"]["required"] is False

            # Should have no required fields
            assert len(result["required_fields"]) == 0
            assert "base_path" in result["optional_fields"]

    async def test_get_invalid_adapter_requirements(self, tmp_path: Path) -> None:
        """Test getting requirements for invalid adapter."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_get_adapter_requirements("invalid_adapter")

            assert result["status"] == "error"
            assert "Invalid adapter" in result["error"]
            assert "valid_adapters" in result
            assert isinstance(result["valid_adapters"], list)
            # Should contain known adapters
            assert "linear" in result["valid_adapters"]
            assert "github" in result["valid_adapters"]

    async def test_get_adapter_requirements_case_insensitive(
        self, tmp_path: Path
    ) -> None:
        """Test that adapter names are case-insensitive."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_get_adapter_requirements("LINEAR")

            assert result["status"] == "completed"
            assert result["adapter"] == "linear"  # Normalized to lowercase

    async def test_requirements_include_validation_patterns(
        self, tmp_path: Path
    ) -> None:
        """Test that requirements include validation patterns where applicable."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            # Linear API key has a validation pattern
            result = await config_get_adapter_requirements("linear")
            assert result["status"] == "completed"
            assert "validation" in result["requirements"]["api_key"]
            assert "lin_api_" in result["requirements"]["api_key"]["validation"]

            # JIRA email has validation pattern
            result = await config_get_adapter_requirements("jira")
            assert result["status"] == "completed"
            assert "validation" in result["requirements"]["email"]
            assert "@" in result["requirements"]["email"]["validation"]

    async def test_requirements_include_descriptions(self, tmp_path: Path) -> None:
        """Test that all requirements include helpful descriptions."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            for adapter_name in ["linear", "github", "jira", "aitrackdown"]:
                result = await config_get_adapter_requirements(adapter_name)

                assert result["status"] == "completed"

                # All fields should have descriptions
                for field_name, field_spec in result["requirements"].items():
                    assert (
                        "description" in field_spec
                    ), f"{adapter_name}.{field_name} missing description"
                    assert (
                        len(field_spec["description"]) > 10
                    ), f"{adapter_name}.{field_name} description too short"

    async def test_requirements_total_fields_accurate(self, tmp_path: Path) -> None:
        """Test that total_fields count is accurate."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_get_adapter_requirements("linear")

            assert result["status"] == "completed"
            assert result["total_fields"] == len(result["requirements"])
            assert result["total_fields"] == len(result["required_fields"]) + len(
                result["optional_fields"]
            )


@pytest.mark.asyncio
class TestConfigSetupWizard:
    """Test suite for config_setup_wizard MCP tool."""

    async def test_config_setup_wizard_success(self, tmp_path: Path) -> None:
        """Test complete successful setup with connection test."""
        # Mock successful health check
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
            result = await config_setup_wizard(
                adapter_type="aitrackdown",
                credentials={"base_path": str(tmp_path / "tickets")},
                set_as_default=True,
                test_connection=True,
            )

            assert result["status"] == "completed"
            assert result["adapter"] == "aitrackdown"
            assert result["tested"] is True
            assert result["connection_healthy"] is True
            assert result["set_as_default"] is True
            assert "config_path" in result
            assert "successfully" in result["message"].lower()

            # Verify config was saved
            config_path = tmp_path / ".mcp-ticketer" / "config.json"
            assert config_path.exists()

            with open(config_path) as f:
                config_data = json.load(f)
            assert config_data["default_adapter"] == "aitrackdown"
            assert "aitrackdown" in config_data["adapters"]

    async def test_config_setup_wizard_invalid_adapter(self, tmp_path: Path) -> None:
        """Test setup with invalid adapter type."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_setup_wizard(
                adapter_type="invalid_adapter",
                credentials={},
            )

            assert result["status"] == "error"
            assert "Invalid adapter" in result["error"]
            assert "valid_adapters" in result
            assert isinstance(result["valid_adapters"], list)
            assert "linear" in result["valid_adapters"]

    async def test_config_setup_wizard_missing_credentials(
        self, tmp_path: Path
    ) -> None:
        """Test setup with missing required credentials."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            # Linear requires api_key and team_key/team_id
            result = await config_setup_wizard(
                adapter_type="linear",
                credentials={},  # Missing all required fields
            )

            assert result["status"] == "error"
            assert "Missing required credentials" in result["error"]
            assert "missing_fields" in result
            assert "api_key" in result["missing_fields"]

    async def test_config_setup_wizard_connection_test_fails(
        self, tmp_path: Path
    ) -> None:
        """Test setup when connection test fails."""
        # Mock failed health check
        mock_health_result = {
            "status": "completed",
            "adapters": {
                "aitrackdown": {
                    "status": "unhealthy",
                    "message": "Connection failed",
                    "error_type": "connection",
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
            result = await config_setup_wizard(
                adapter_type="aitrackdown",
                credentials={"base_path": str(tmp_path / "tickets")},
                test_connection=True,
            )

            assert result["status"] == "error"
            assert "Connection test failed" in result["error"]
            assert "test_result" in result

    async def test_config_setup_wizard_skip_connection_test(
        self, tmp_path: Path
    ) -> None:
        """Test setup with connection test disabled."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_setup_wizard(
                adapter_type="aitrackdown",
                credentials={"base_path": str(tmp_path / "tickets")},
                test_connection=False,  # Skip connection test
            )

            assert result["status"] == "completed"
            assert result["tested"] is False
            assert result["connection_healthy"] is None

            # Verify config was still saved
            config_path = tmp_path / ".mcp-ticketer" / "config.json"
            assert config_path.exists()

    async def test_config_setup_wizard_not_default(self, tmp_path: Path) -> None:
        """Test setup without setting as default adapter."""
        # Create initial config with different default
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        initial_config = {"default_adapter": "linear"}
        with open(config_path, "w") as f:
            json.dump(initial_config, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_setup_wizard(
                adapter_type="aitrackdown",
                credentials={"base_path": str(tmp_path / "tickets")},
                set_as_default=False,  # Don't set as default
                test_connection=False,
            )

            assert result["status"] == "completed"
            assert result["set_as_default"] is False

            # Verify default adapter was not changed
            with open(config_path) as f:
                config_data = json.load(f)
            assert config_data["default_adapter"] == "linear"  # Still linear
            assert (
                "aitrackdown" in config_data["adapters"]
            )  # But aitrackdown configured

    async def test_config_setup_wizard_update_existing(self, tmp_path: Path) -> None:
        """Test updating existing adapter configuration."""
        # Create initial config with aitrackdown
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        initial_config = {
            "default_adapter": "aitrackdown",
            "adapters": {
                "aitrackdown": {
                    "adapter": "aitrackdown",
                    "base_path": str(tmp_path / "old_path"),
                }
            },
        }
        with open(config_path, "w") as f:
            json.dump(initial_config, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            # Update with new base_path
            result = await config_setup_wizard(
                adapter_type="aitrackdown",
                credentials={"base_path": str(tmp_path / "new_path")},
                test_connection=False,
            )

            assert result["status"] == "completed"

            # Verify config was updated
            with open(config_path) as f:
                config_data = json.load(f)
            assert config_data["adapters"]["aitrackdown"]["base_path"] == str(
                tmp_path / "new_path"
            )

    async def test_config_setup_wizard_linear_with_team_key(
        self, tmp_path: Path
    ) -> None:
        """Test Linear setup with team_key."""
        mock_health_result = {
            "status": "completed",
            "adapters": {
                "linear": {
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
            # Construct test API key dynamically to avoid GitHub secret scanning
            test_api_key = "lin" + "_api_" + "TEST" + "0" * 36
            result = await config_setup_wizard(
                adapter_type="linear",
                credentials={
                    "api_key": test_api_key,
                    "team_key": "ENG",
                },
                test_connection=True,
            )

            assert result["status"] == "completed"
            assert result["adapter"] == "linear"

            # Verify config
            config_path = tmp_path / ".mcp-ticketer" / "config.json"
            with open(config_path) as f:
                config_data = json.load(f)
            assert config_data["adapters"]["linear"]["team_key"] == "ENG"

    async def test_config_setup_wizard_linear_with_team_id(
        self, tmp_path: Path
    ) -> None:
        """Test Linear setup with team_id instead of team_key."""
        mock_health_result = {
            "status": "completed",
            "adapters": {
                "linear": {
                    "status": "healthy",
                    "message": "Adapter initialized and API call successful",
                }
            },
        }

        team_uuid = "12345678-1234-1234-1234-123456789012"

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
            # Construct test API key dynamically to avoid GitHub secret scanning
            test_api_key = "lin" + "_api_" + "TEST" + "0" * 36
            result = await config_setup_wizard(
                adapter_type="linear",
                credentials={
                    "api_key": test_api_key,
                    "team_id": team_uuid,
                },
                test_connection=True,
            )

            assert result["status"] == "completed"
            assert result["adapter"] == "linear"

            # Verify config
            config_path = tmp_path / ".mcp-ticketer" / "config.json"
            with open(config_path) as f:
                config_data = json.load(f)
            assert config_data["adapters"]["linear"]["team_id"] == team_uuid

    async def test_config_setup_wizard_github_success(self, tmp_path: Path) -> None:
        """Test GitHub adapter setup."""
        mock_health_result = {
            "status": "completed",
            "adapters": {
                "github": {
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
            result = await config_setup_wizard(
                adapter_type="github",
                credentials={
                    "token": "ghp_test1234567890",
                    "owner": "testuser",
                    "repo": "testrepo",
                },
                test_connection=True,
            )

            assert result["status"] == "completed"
            assert result["adapter"] == "github"

            # Verify config
            config_path = tmp_path / ".mcp-ticketer" / "config.json"
            with open(config_path) as f:
                config_data = json.load(f)
            assert config_data["adapters"]["github"]["owner"] == "testuser"
            assert config_data["adapters"]["github"]["repo"] == "testrepo"

    async def test_config_setup_wizard_jira_success(self, tmp_path: Path) -> None:
        """Test JIRA adapter setup."""
        mock_health_result = {
            "status": "completed",
            "adapters": {
                "jira": {
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
            result = await config_setup_wizard(
                adapter_type="jira",
                credentials={
                    "server": "https://test.atlassian.net",
                    "email": "test@example.com",
                    "api_token": "test_token_12345",
                },
                test_connection=True,
            )

            assert result["status"] == "completed"
            assert result["adapter"] == "jira"

            # Verify config
            config_path = tmp_path / ".mcp-ticketer" / "config.json"
            with open(config_path) as f:
                config_data = json.load(f)
            assert (
                config_data["adapters"]["jira"]["server"]
                == "https://test.atlassian.net"
            )
            assert config_data["adapters"]["jira"]["email"] == "test@example.com"

    async def test_config_setup_wizard_case_insensitive(self, tmp_path: Path) -> None:
        """Test that adapter type is case-insensitive."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_setup_wizard(
                adapter_type="AITRACKDOWN",  # Uppercase
                credentials={"base_path": str(tmp_path / "tickets")},
                test_connection=False,
            )

            assert result["status"] == "completed"
            assert result["adapter"] == "aitrackdown"  # Normalized to lowercase

    async def test_config_setup_wizard_preserves_other_adapters(
        self, tmp_path: Path
    ) -> None:
        """Test that setting up one adapter preserves other adapters."""
        # Create initial config with Linear
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        initial_config = {
            "default_adapter": "linear",
            "adapters": {
                "linear": {
                    "adapter": "linear",
                    "api_key": "lin_api_existing",
                    "team_key": "ENG",
                }
            },
        }
        with open(config_path, "w") as f:
            json.dump(initial_config, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            # Add aitrackdown
            result = await config_setup_wizard(
                adapter_type="aitrackdown",
                credentials={"base_path": str(tmp_path / "tickets")},
                set_as_default=False,
                test_connection=False,
            )

            assert result["status"] == "completed"

            # Verify both adapters exist
            with open(config_path) as f:
                config_data = json.load(f)
            assert "linear" in config_data["adapters"]
            assert "aitrackdown" in config_data["adapters"]
            assert config_data["adapters"]["linear"]["api_key"] == "lin_api_existing"

    async def test_config_setup_wizard_validation_error(self, tmp_path: Path) -> None:
        """Test that setup fails with detailed error on validation failure."""
        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            # GitHub missing required fields
            result = await config_setup_wizard(
                adapter_type="github",
                credentials={"token": "test_token"},  # Missing owner and repo
            )

            assert result["status"] == "error"
            assert "Missing required credentials" in result["error"]
            assert "missing_fields" in result
            assert "owner" in result["missing_fields"]
            assert "repo" in result["missing_fields"]


@pytest.mark.asyncio
class TestConfigErrorHandling:
    """Test suite for config error handling (GitHub issue #62)."""

    async def test_config_set_with_corrupted_json(self, tmp_path: Path) -> None:
        """Test that config set fails with clear error when JSON is corrupted."""
        # Create corrupted JSON file
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        with open(config_path, "w") as f:
            f.write("{invalid json syntax")

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_set_default_project("PROJ-123")

            assert result["status"] == "error"
            assert "invalid JSON" in result["error"]
            assert "JSON parse error" in result["error"]
            # Should not say "corrupted or invalid JSON file" (old misleading message)

    async def test_config_set_with_valid_json_invalid_config(
        self, tmp_path: Path
    ) -> None:
        """Test that config set fails with clear error when JSON is valid but config is invalid."""
        # Create valid JSON but invalid config structure
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        # Valid JSON but will cause validation error during TicketerConfig initialization
        invalid_config = {
            "default_adapter": "linear",
            "adapters": {
                "linear": {
                    # This will cause some validation error
                    "adapter": "linear",
                    # Missing required fields like api_key
                }
            },
        }
        with open(config_path, "w") as f:
            json.dump(invalid_config, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_set_default_project("PROJ-123")

            # Should succeed or fail with validation error, not "corrupted JSON" error
            # If it fails, error should mention validation, not JSON corruption
            if result["status"] == "error":
                assert (
                    "valid JSON" in result["error"]
                    or "validation" in result["error"].lower()
                )
                assert "JSON parse error" not in result["error"]

    async def test_config_set_with_valid_config(self, tmp_path: Path) -> None:
        """Test that config set works correctly with valid existing config."""
        # Create valid config
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "config.json"

        valid_config = {
            "default_adapter": "linear",
            "default_project": "OLD-PROJ",
            "adapters": {
                "linear": {
                    "adapter": "linear",
                    "api_key": "lin_api_test123456789012345678901234567890",
                    "team_key": "ENG",
                }
            },
        }
        with open(config_path, "w") as f:
            json.dump(valid_config, f)

        with patch(
            "mcp_ticketer.mcp.server.tools.config_tools.Path.cwd",
            return_value=tmp_path,
        ):
            result = await config_set_default_project("NEW-PROJ")

            assert result["status"] == "completed"
            assert result["new_project"] == "NEW-PROJ"
            assert result["previous_project"] == "OLD-PROJ"

            # Verify adapter config was preserved
            with open(config_path) as f:
                config_data = json.load(f)
            assert (
                config_data["adapters"]["linear"]["api_key"]
                == "lin_api_test123456789012345678901234567890"
            )
            assert config_data["default_project"] == "NEW-PROJ"
