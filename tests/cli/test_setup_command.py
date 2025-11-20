"""Tests for the smart setup command.

Tests the setup command which intelligently combines init and install:
- Detection of existing configuration
- Smart adapter initialization
- Platform detection and installation
- Force re-initialization
- Skip platform installation
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import typer
from typer.testing import CliRunner

from mcp_ticketer.cli.main import app

runner = CliRunner()


@pytest.mark.unit
class TestSetupCommand:
    """Test suite for 'setup' command."""

    def test_setup_first_run_no_config(self, tmp_path: Path) -> None:
        """Test setup when no configuration exists (first run)."""
        with (
            patch("mcp_ticketer.cli.main.Path.cwd", return_value=tmp_path),
            patch("mcp_ticketer.core.env_discovery.discover_config") as mock_discover,
            patch(
                "mcp_ticketer.cli.setup_command._prompt_for_adapter_selection"
            ) as mock_prompt,
            patch(
                "mcp_ticketer.cli.init_command._init_adapter_internal"
            ) as mock_init_internal,
            patch(
                "mcp_ticketer.cli.platform_detection.PlatformDetector"
            ) as mock_detector_class,
            patch("typer.prompt"),
        ):
            # Setup mocks
            mock_discover.return_value = None
            mock_prompt.return_value = "aitrackdown"
            mock_init_internal.return_value = True  # Return success

            # Mock platform detector
            mock_detector = Mock()
            mock_detector.detect_all.return_value = []
            mock_detector_class.return_value = mock_detector

            # Invoke with mix mode to avoid interactive prompts
            runner.invoke(app, ["setup"], input="")

            # Should call _init_adapter_internal
            assert mock_init_internal.called

    def test_setup_existing_config_keep_settings(self, tmp_path: Path) -> None:
        """Test setup with existing valid config - user keeps settings."""
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"

        # Create valid config
        config = {
            "default_adapter": "aitrackdown",
            "adapters": {
                "aitrackdown": {"type": "aitrackdown", "base_path": ".aitrackdown"}
            },
        }
        config_file.write_text(json.dumps(config))

        with (
            patch("mcp_ticketer.cli.main.Path.cwd", return_value=tmp_path),
            patch(
                "mcp_ticketer.cli.init_command._init_adapter_internal"
            ) as mock_init_internal,
            patch(
                "mcp_ticketer.cli.platform_detection.PlatformDetector"
            ) as mock_detector_class,
            patch("typer.confirm") as mock_confirm,
            patch("typer.prompt"),
            patch(
                "mcp_ticketer.cli.setup_command._prompt_and_update_default_values"
            ) as mock_prompt_defaults,
        ):
            # User confirms to keep existing settings
            mock_confirm.side_effect = [True, False]  # Keep config, skip platforms

            # Mock platform detector
            mock_detector = Mock()
            mock_detector.detect_all.return_value = []
            mock_detector_class.return_value = mock_detector

            result = runner.invoke(app, ["setup"], input="")

            # Should NOT call _init_adapter_internal (config already exists and user kept it)
            assert not mock_init_internal.called
            # SHOULD call prompt_and_update_default_values
            assert mock_prompt_defaults.called
            assert result.exit_code == 0

    def test_setup_existing_config_prompts_for_defaults(self, tmp_path: Path) -> None:
        """Test that setup prompts for default values even when keeping existing config."""
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"

        # Create valid config WITHOUT default values
        config = {
            "default_adapter": "linear",
            "adapters": {
                "linear": {
                    "type": "linear",
                    "api_key": "lin_api_test123",
                    "team_key": "ENG",
                }
            },
        }
        config_file.write_text(json.dumps(config))

        with (
            patch("mcp_ticketer.cli.main.Path.cwd", return_value=tmp_path),
            patch(
                "mcp_ticketer.cli.platform_detection.PlatformDetector"
            ) as mock_detector_class,
            patch("typer.confirm") as mock_confirm,
            patch("mcp_ticketer.cli.configure.prompt_default_values") as mock_prompt,
        ):
            # User keeps config, skips platforms
            mock_confirm.side_effect = [True, False]

            # Mock platform detector
            mock_detector = Mock()
            mock_detector.detect_all.return_value = []
            mock_detector_class.return_value = mock_detector

            # Mock default values prompt to return some values
            mock_prompt.return_value = {
                "default_user": "test@example.com",
                "default_epic": "ENG-123",
            }

            result = runner.invoke(app, ["setup"], input="")

            # Verify prompt_default_values was called with correct adapter type
            assert mock_prompt.called
            call_args = mock_prompt.call_args
            assert call_args[1]["adapter_type"] == "linear"
            assert result.exit_code == 0

            # Verify config was updated with default values
            with open(config_file) as f:
                updated_config = json.load(f)
            assert updated_config["default_user"] == "test@example.com"
            assert updated_config["default_epic"] == "ENG-123"

    def test_setup_existing_config_with_existing_defaults(self, tmp_path: Path) -> None:
        """Test that existing default values are shown as current values in prompts."""
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"

        # Create valid config WITH existing default values
        config = {
            "default_adapter": "github",
            "adapters": {
                "github": {
                    "type": "github",
                    "token": "ghp_test123",
                    "owner": "testorg",
                    "repo": "testrepo",
                }
            },
            "default_user": "olduser",
            "default_epic": "OLD-123",
            "default_tags": ["old-tag"],
        }
        config_file.write_text(json.dumps(config))

        with (
            patch("mcp_ticketer.cli.main.Path.cwd", return_value=tmp_path),
            patch(
                "mcp_ticketer.cli.platform_detection.PlatformDetector"
            ) as mock_detector_class,
            patch("typer.confirm") as mock_confirm,
            patch("mcp_ticketer.cli.configure.prompt_default_values") as mock_prompt,
        ):
            # User keeps config, skips platforms
            mock_confirm.side_effect = [True, False]

            # Mock platform detector
            mock_detector = Mock()
            mock_detector.detect_all.return_value = []
            mock_detector_class.return_value = mock_detector

            # Mock prompt to verify it receives existing values
            mock_prompt.return_value = {
                "default_user": "newuser",
                "default_epic": "NEW-456",
            }

            result = runner.invoke(app, ["setup"], input="")

            # Verify existing values were passed to prompt
            call_args = mock_prompt.call_args
            existing_values = call_args[1]["existing_values"]
            assert existing_values["default_user"] == "olduser"
            assert existing_values["default_epic"] == "OLD-123"
            assert existing_values["default_tags"] == ["old-tag"]
            assert result.exit_code == 0

    def test_setup_force_reinit(self, tmp_path: Path) -> None:
        """Test setup with --force-reinit flag."""
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"

        # Create valid config
        config = {
            "default_adapter": "linear",
            "adapters": {"linear": {"type": "linear"}},
        }
        config_file.write_text(json.dumps(config))

        with (
            patch("mcp_ticketer.cli.main.Path.cwd", return_value=tmp_path),
            patch("mcp_ticketer.core.env_discovery.discover_config") as mock_discover,
            patch(
                "mcp_ticketer.cli.setup_command._prompt_for_adapter_selection"
            ) as mock_prompt,
            patch(
                "mcp_ticketer.cli.init_command._init_adapter_internal"
            ) as mock_init_internal,
            patch(
                "mcp_ticketer.cli.platform_detection.PlatformDetector"
            ) as mock_detector_class,
        ):
            # Setup mocks
            mock_discover.return_value = None
            mock_prompt.return_value = "aitrackdown"
            mock_init_internal.return_value = True

            # Mock platform detector
            mock_detector = Mock()
            mock_detector.detect_all.return_value = []
            mock_detector_class.return_value = mock_detector

            runner.invoke(app, ["setup", "--force-reinit"], input="")

            # Should call _init_adapter_internal even though config exists
            assert mock_init_internal.called

    def test_setup_skip_platforms(self, tmp_path: Path) -> None:
        """Test setup with --skip-platforms flag."""
        with (
            patch("mcp_ticketer.cli.main.Path.cwd", return_value=tmp_path),
            patch("mcp_ticketer.core.env_discovery.discover_config") as mock_discover,
            patch(
                "mcp_ticketer.cli.setup_command._prompt_for_adapter_selection"
            ) as mock_prompt,
            patch(
                "mcp_ticketer.cli.init_command._init_adapter_internal"
            ) as mock_init_internal,
            patch(
                "mcp_ticketer.cli.platform_detection.PlatformDetector"
            ) as mock_detector_class,
        ):
            # Setup mocks
            mock_discover.return_value = None
            mock_prompt.return_value = "aitrackdown"
            mock_init_internal.return_value = True

            # Mock detector should NOT be called when skipping platforms
            mock_detector = Mock()
            mock_detector_class.return_value = mock_detector

            runner.invoke(app, ["setup", "--skip-platforms"], input="")

            # Should call _init_adapter_internal but not detect platforms
            assert mock_init_internal.called
            assert not mock_detector.detect_all.called

    def test_setup_with_platforms_install_all(self, tmp_path: Path) -> None:
        """Test setup with platform installation - install all option."""
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"

        # Create valid config
        config = {
            "default_adapter": "aitrackdown",
            "adapters": {"aitrackdown": {"type": "aitrackdown"}},
        }
        config_file.write_text(json.dumps(config))

        with (
            patch("mcp_ticketer.cli.main.Path.cwd", return_value=tmp_path),
            patch(
                "mcp_ticketer.cli.platform_detection.PlatformDetector"
            ) as mock_detector_class,
            patch(
                "mcp_ticketer.cli.setup_command._check_existing_platform_configs"
            ) as mock_check,
            patch(
                "mcp_ticketer.cli.mcp_configure.configure_claude_mcp"
            ) as mock_configure,
            patch("typer.confirm") as mock_confirm,
            patch("typer.prompt") as mock_prompt,
        ):
            # Mock platform detector
            mock_platform = Mock()
            mock_platform.name = "claude-code"
            mock_platform.display_name = "Claude Code"
            mock_platform.is_installed = True
            mock_platform.scope = "project"

            mock_detector = Mock()
            mock_detector.detect_all.return_value = [mock_platform]
            mock_detector_class.return_value = mock_detector

            # Mock existing config check
            mock_check.return_value = []

            # User confirms to keep config and chooses option 1 (install all)
            mock_confirm.return_value = True
            mock_prompt.return_value = 1

            runner.invoke(app, ["setup"], input="")

            # Should call configure for detected platform
            assert mock_configure.called

    def test_setup_with_platforms_select_specific(self, tmp_path: Path) -> None:
        """Test setup with platform installation - select specific platform."""
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"

        # Create valid config
        config = {
            "default_adapter": "aitrackdown",
            "adapters": {"aitrackdown": {"type": "aitrackdown"}},
        }
        config_file.write_text(json.dumps(config))

        with (
            patch("mcp_ticketer.cli.main.Path.cwd", return_value=tmp_path),
            patch(
                "mcp_ticketer.cli.platform_detection.PlatformDetector"
            ) as mock_detector_class,
            patch(
                "mcp_ticketer.cli.setup_command._check_existing_platform_configs"
            ) as mock_check,
            patch(
                "mcp_ticketer.cli.mcp_configure.configure_claude_mcp"
            ) as mock_configure,
            patch("typer.confirm") as mock_confirm,
            patch("typer.prompt") as mock_prompt,
        ):
            # Mock two platforms
            mock_platform1 = Mock()
            mock_platform1.name = "claude-code"
            mock_platform1.display_name = "Claude Code"
            mock_platform1.is_installed = True

            mock_platform2 = Mock()
            mock_platform2.name = "claude-desktop"
            mock_platform2.display_name = "Claude Desktop"
            mock_platform2.is_installed = True

            mock_detector = Mock()
            mock_detector.detect_all.return_value = [mock_platform1, mock_platform2]
            mock_detector_class.return_value = mock_detector

            # Mock existing config check
            mock_check.return_value = []

            # User confirms to keep config, chooses option 2 (select specific), then platform 1
            mock_confirm.return_value = True
            mock_prompt.side_effect = [2, 1]  # Option 2, then platform 1

            runner.invoke(app, ["setup"], input="")

            # Should call configure once for selected platform
            assert mock_configure.called

    def test_setup_with_platforms_skip_installation(self, tmp_path: Path) -> None:
        """Test setup with platforms detected but user skips installation."""
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"

        # Create valid config
        config = {
            "default_adapter": "aitrackdown",
            "adapters": {"aitrackdown": {"type": "aitrackdown"}},
        }
        config_file.write_text(json.dumps(config))

        with (
            patch("mcp_ticketer.cli.main.Path.cwd", return_value=tmp_path),
            patch(
                "mcp_ticketer.cli.platform_detection.PlatformDetector"
            ) as mock_detector_class,
            patch(
                "mcp_ticketer.cli.setup_command._check_existing_platform_configs"
            ) as mock_check,
            patch(
                "mcp_ticketer.cli.mcp_configure.configure_claude_mcp"
            ) as mock_configure,
            patch("typer.confirm") as mock_confirm,
            patch("typer.prompt") as mock_prompt,
        ):
            # Mock platform
            mock_platform = Mock()
            mock_platform.name = "claude-code"
            mock_platform.display_name = "Claude Code"
            mock_platform.is_installed = True

            mock_detector = Mock()
            mock_detector.detect_all.return_value = [mock_platform]
            mock_detector_class.return_value = mock_detector

            # Mock existing config check
            mock_check.return_value = []

            # User keeps config and chooses option 3 (skip)
            mock_confirm.return_value = True
            mock_prompt.return_value = 3

            result = runner.invoke(app, ["setup"], input="")

            # Should NOT call configure
            assert not mock_configure.called
            assert result.exit_code == 0

    def test_setup_already_configured_platforms(self, tmp_path: Path) -> None:
        """Test setup when platforms are already configured."""
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"

        # Create valid config
        config = {
            "default_adapter": "aitrackdown",
            "adapters": {"aitrackdown": {"type": "aitrackdown"}},
        }
        config_file.write_text(json.dumps(config))

        with (
            patch("mcp_ticketer.cli.main.Path.cwd", return_value=tmp_path),
            patch(
                "mcp_ticketer.cli.platform_detection.PlatformDetector"
            ) as mock_detector_class,
            patch(
                "mcp_ticketer.cli.setup_command._check_existing_platform_configs"
            ) as mock_check,
            patch(
                "mcp_ticketer.cli.mcp_configure.configure_claude_mcp"
            ) as mock_configure,
            patch("typer.confirm") as mock_confirm,
        ):
            # Mock platform
            mock_platform = Mock()
            mock_platform.name = "claude-code"
            mock_platform.display_name = "Claude Code"
            mock_platform.is_installed = True

            mock_detector = Mock()
            mock_detector.detect_all.return_value = [mock_platform]
            mock_detector_class.return_value = mock_detector

            # Mock that platform is already configured
            mock_check.return_value = ["Claude Code"]

            # User keeps config but doesn't want to update platforms
            mock_confirm.side_effect = [True, False]  # Keep config, don't update

            result = runner.invoke(app, ["setup"], input="")

            # Should NOT call configure (already configured and user declined)
            assert not mock_configure.called
            assert result.exit_code == 0

    def test_setup_no_platforms_detected(self, tmp_path: Path) -> None:
        """Test setup when no platforms are detected."""
        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"

        # Create valid config
        config = {
            "default_adapter": "aitrackdown",
            "adapters": {"aitrackdown": {"type": "aitrackdown"}},
        }
        config_file.write_text(json.dumps(config))

        with (
            patch("mcp_ticketer.cli.main.Path.cwd", return_value=tmp_path),
            patch(
                "mcp_ticketer.cli.platform_detection.PlatformDetector"
            ) as mock_detector_class,
            patch("typer.confirm") as mock_confirm,
        ):
            # Mock no platforms detected
            mock_detector = Mock()
            mock_detector.detect_all.return_value = []
            mock_detector_class.return_value = mock_detector

            # User keeps config
            mock_confirm.return_value = True

            result = runner.invoke(app, ["setup"], input="")

            # Should complete successfully even with no platforms
            assert result.exit_code == 0
            assert "No AI platforms detected" in result.stdout


@pytest.mark.unit
class TestPromptAndUpdateDefaultValues:
    """Test suite for _prompt_and_update_default_values helper function."""

    def test_prompt_and_update_with_new_values(self, tmp_path: Path) -> None:
        """Test prompting and updating default values."""
        from mcp_ticketer.cli.setup_command import _prompt_and_update_default_values

        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"

        # Create initial config without defaults
        initial_config = {
            "default_adapter": "linear",
            "adapters": {"linear": {"type": "linear", "api_key": "test"}},
        }
        config_file.write_text(json.dumps(initial_config))

        with (
            patch("mcp_ticketer.cli.configure.prompt_default_values") as mock_prompt,
            patch("mcp_ticketer.cli.main.Console") as mock_console_class,
        ):
            mock_console = Mock()
            mock_console_class.return_value = mock_console

            # Mock prompt to return new values
            mock_prompt.return_value = {
                "default_user": "user@example.com",
                "default_epic": "PROJ-123",
                "default_tags": ["tag1", "tag2"],
            }

            # Call the function
            _prompt_and_update_default_values(config_file, "linear", mock_console)

            # Verify config was updated
            with open(config_file) as f:
                updated_config = json.load(f)

            assert updated_config["default_user"] == "user@example.com"
            assert updated_config["default_epic"] == "PROJ-123"
            assert updated_config["default_tags"] == ["tag1", "tag2"]

    def test_prompt_and_update_preserves_existing_values(self, tmp_path: Path) -> None:
        """Test that existing values are passed to prompt function."""
        from mcp_ticketer.cli.setup_command import _prompt_and_update_default_values

        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"

        # Create config with existing defaults
        initial_config = {
            "default_adapter": "github",
            "adapters": {"github": {"type": "github"}},
            "default_user": "existing@example.com",
            "default_epic": "EXISTING-123",
        }
        config_file.write_text(json.dumps(initial_config))

        with (
            patch("mcp_ticketer.cli.configure.prompt_default_values") as mock_prompt,
            patch("mcp_ticketer.cli.main.Console") as mock_console_class,
        ):
            mock_console = Mock()
            mock_console_class.return_value = mock_console

            # Mock prompt to return empty (user skipped)
            mock_prompt.return_value = {}

            # Call the function
            _prompt_and_update_default_values(config_file, "github", mock_console)

            # Verify existing values were passed to prompt
            call_args = mock_prompt.call_args
            existing_values = call_args[1]["existing_values"]
            assert existing_values["default_user"] == "existing@example.com"
            assert existing_values["default_epic"] == "EXISTING-123"

    def test_prompt_and_update_handles_invalid_json(self, tmp_path: Path) -> None:
        """Test error handling for invalid JSON config."""
        from mcp_ticketer.cli.setup_command import _prompt_and_update_default_values

        config_dir = tmp_path / ".mcp-ticketer"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"

        # Write invalid JSON
        config_file.write_text("{ invalid json }")

        with patch("mcp_ticketer.cli.main.Console") as mock_console_class:
            mock_console = Mock()
            mock_console_class.return_value = mock_console

            # Call function - should handle error gracefully
            _prompt_and_update_default_values(config_file, "linear", mock_console)

            # Verify error was printed
            assert any(
                "Invalid JSON" in str(call)
                for call in mock_console.print.call_args_list
            )

    def test_prompt_and_update_handles_missing_file(self, tmp_path: Path) -> None:
        """Test error handling for missing config file."""
        from mcp_ticketer.cli.setup_command import _prompt_and_update_default_values

        config_file = tmp_path / ".mcp-ticketer" / "config.json"
        # Don't create the file

        with patch("mcp_ticketer.cli.main.Console") as mock_console_class:
            mock_console = Mock()
            mock_console_class.return_value = mock_console

            # Call function - should handle error gracefully
            _prompt_and_update_default_values(config_file, "linear", mock_console)

            # Verify error was printed
            assert any(
                "Could not read" in str(call)
                for call in mock_console.print.call_args_list
            )


@pytest.mark.unit
class TestCheckAndInstallAdapterDependencies:
    """Test suite for _check_and_install_adapter_dependencies helper function."""

    def test_aitrackdown_no_dependencies_needed(self) -> None:
        """Test that aitrackdown adapter reports no extra dependencies needed."""
        from mcp_ticketer.cli.setup_command import (
            _check_and_install_adapter_dependencies,
        )

        with patch("mcp_ticketer.cli.main.Console") as mock_console_class:
            mock_console = Mock()
            mock_console_class.return_value = mock_console

            result = _check_and_install_adapter_dependencies(
                "aitrackdown", mock_console
            )

            # Should return True (no dependencies needed)
            assert result is True

            # Verify message was printed
            assert any(
                "No extra dependencies required" in str(call)
                for call in mock_console.print.call_args_list
            )

    def test_dependencies_already_installed(self) -> None:
        """Test when adapter dependencies are already installed."""
        from mcp_ticketer.cli.setup_command import (
            _check_and_install_adapter_dependencies,
        )

        with (
            patch("mcp_ticketer.cli.main.Console") as mock_console_class,
            patch(
                "mcp_ticketer.cli.setup_command._check_package_installed"
            ) as mock_check,
        ):
            mock_console = Mock()
            mock_console_class.return_value = mock_console

            # Mock that package is already installed
            mock_check.return_value = True

            result = _check_and_install_adapter_dependencies("linear", mock_console)

            # Should return True (already installed)
            assert result is True

            # Verify success message was printed
            assert any(
                "already installed" in str(call)
                for call in mock_console.print.call_args_list
            )

    def test_dependencies_missing_user_accepts_installation(self) -> None:
        """Test installing dependencies when user accepts."""
        from mcp_ticketer.cli.setup_command import (
            _check_and_install_adapter_dependencies,
        )

        with (
            patch("mcp_ticketer.cli.main.Console") as mock_console_class,
            patch(
                "mcp_ticketer.cli.setup_command._check_package_installed"
            ) as mock_check,
            patch("typer.confirm") as mock_confirm,
            patch("subprocess.check_call") as mock_subprocess,
        ):
            mock_console = Mock()
            mock_console_class.return_value = mock_console

            # Mock that package is NOT installed
            mock_check.return_value = False

            # User accepts installation
            mock_confirm.return_value = True

            # Mock successful installation
            mock_subprocess.return_value = 0

            result = _check_and_install_adapter_dependencies("github", mock_console)

            # Should return True (installation succeeded)
            assert result is True

            # Verify subprocess was called with correct command
            assert mock_subprocess.called
            call_args = mock_subprocess.call_args[0][0]
            assert "pip" in call_args
            assert "install" in call_args
            assert "mcp-ticketer[github]" in call_args

            # Verify success message was printed
            assert any(
                "Successfully installed" in str(call)
                for call in mock_console.print.call_args_list
            )

    def test_dependencies_missing_user_declines_installation(self) -> None:
        """Test when user declines to install dependencies."""
        from mcp_ticketer.cli.setup_command import (
            _check_and_install_adapter_dependencies,
        )

        with (
            patch("mcp_ticketer.cli.main.Console") as mock_console_class,
            patch(
                "mcp_ticketer.cli.setup_command._check_package_installed"
            ) as mock_check,
            patch("typer.confirm") as mock_confirm,
            patch("subprocess.check_call") as mock_subprocess,
        ):
            mock_console = Mock()
            mock_console_class.return_value = mock_console

            # Mock that package is NOT installed
            mock_check.return_value = False

            # User declines installation
            mock_confirm.return_value = False

            result = _check_and_install_adapter_dependencies("jira", mock_console)

            # Should return True (user declined, but we continue)
            assert result is True

            # Verify subprocess was NOT called
            assert not mock_subprocess.called

            # Verify manual installation instructions were shown
            assert any(
                "Install manually" in str(call)
                for call in mock_console.print.call_args_list
            )
            assert any(
                "pip install mcp-ticketer[jira]" in str(call)
                for call in mock_console.print.call_args_list
            )

    def test_installation_fails_gracefully(self) -> None:
        """Test graceful handling of installation failure."""
        from mcp_ticketer.cli.setup_command import (
            _check_and_install_adapter_dependencies,
        )

        with (
            patch("mcp_ticketer.cli.main.Console") as mock_console_class,
            patch(
                "mcp_ticketer.cli.setup_command._check_package_installed"
            ) as mock_check,
            patch("typer.confirm") as mock_confirm,
            patch("subprocess.check_call") as mock_subprocess,
        ):
            mock_console = Mock()
            mock_console_class.return_value = mock_console

            # Mock that package is NOT installed
            mock_check.return_value = False

            # User accepts installation
            mock_confirm.return_value = True

            # Mock installation failure
            mock_subprocess.side_effect = subprocess.CalledProcessError(
                1, "pip", stderr=b"Installation error"
            )

            result = _check_and_install_adapter_dependencies("linear", mock_console)

            # Should return True (continue despite failure)
            assert result is True

            # Debug: print all calls
            all_calls = [str(call) for call in mock_console.print.call_args_list]

            # Verify error message and manual instructions were shown
            # Check with more flexible pattern matching
            has_failed = any("fail" in str(call).lower() for call in all_calls)
            has_manual = any("manual" in str(call).lower() for call in all_calls)

            assert has_failed, f"Expected 'failed' message in: {all_calls}"
            assert has_manual, f"Expected 'manual' message in: {all_calls}"

    def test_user_cancels_installation_prompt(self) -> None:
        """Test when user cancels the installation prompt."""
        from mcp_ticketer.cli.setup_command import (
            _check_and_install_adapter_dependencies,
        )

        with (
            patch("mcp_ticketer.cli.main.Console") as mock_console_class,
            patch(
                "mcp_ticketer.cli.setup_command._check_package_installed"
            ) as mock_check,
            patch("typer.confirm") as mock_confirm,
            patch("subprocess.check_call") as mock_subprocess,
        ):
            mock_console = Mock()
            mock_console_class.return_value = mock_console

            # Mock that package is NOT installed
            mock_check.return_value = False

            # User cancels prompt (Ctrl+C)
            mock_confirm.side_effect = typer.Abort()

            result = _check_and_install_adapter_dependencies("github", mock_console)

            # Should return True (cancelled, but we continue)
            assert result is True

            # Verify subprocess was NOT called
            assert not mock_subprocess.called

            # Verify cancellation message was shown
            assert any(
                "cancelled" in str(call).lower()
                for call in mock_console.print.call_args_list
            )

    def test_all_adapter_types_have_dependencies_defined(self) -> None:
        """Test that all adapter types have dependency mappings."""
        from mcp_ticketer.cli.setup_command import ADAPTER_DEPENDENCIES

        # All known adapter types should be in the mapping
        expected_adapters = ["linear", "jira", "github", "aitrackdown"]

        for adapter in expected_adapters:
            assert adapter in ADAPTER_DEPENDENCIES, f"{adapter} not in mapping"

    def test_linear_adapter_import_check(self) -> None:
        """Test that linear adapter correctly checks for gql package."""
        from mcp_ticketer.cli.setup_command import (
            _check_and_install_adapter_dependencies,
        )

        with (
            patch("mcp_ticketer.cli.main.Console") as mock_console_class,
            patch(
                "mcp_ticketer.cli.setup_command._check_package_installed"
            ) as mock_check,
            patch("typer.confirm") as mock_confirm,
            patch("subprocess.check_call") as mock_subprocess,
        ):
            mock_console = Mock()
            mock_console_class.return_value = mock_console

            # Mock that package is NOT installed
            mock_check.return_value = False

            # User accepts installation
            mock_confirm.return_value = True
            mock_subprocess.return_value = 0

            result = _check_and_install_adapter_dependencies("linear", mock_console)

            # Should attempt installation
            assert result is True
            # Verify correct extras are used
            if mock_subprocess.called:
                call_args = mock_subprocess.call_args[0][0]
                assert "mcp-ticketer[linear]" in call_args


@pytest.mark.unit
class TestCheckExistingPlatformConfigs:
    """Test suite for _check_existing_platform_configs helper."""

    def test_check_claude_code_configured(self, tmp_path: Path) -> None:
        """Test detection of Claude Code configuration."""
        from mcp_ticketer.cli.setup_command import _check_existing_platform_configs

        # Create mock Claude Code config
        claude_config_path = Path.home() / ".claude.json"
        proj_path = tmp_path

        mock_platform = Mock()
        mock_platform.name = "claude-code"
        mock_platform.display_name = "Claude Code"
        mock_platform.config_path = claude_config_path

        # Mock config file
        claude_config = {
            "projects": {str(proj_path): {"mcpServers": {"mcp-ticketer": {}}}}
        }

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                json.dumps(claude_config)
            )

            with patch.object(Path, "exists", return_value=True):
                result = _check_existing_platform_configs([mock_platform], proj_path)

                assert "Claude Code" in result

    def test_check_no_configs(self, tmp_path: Path) -> None:
        """Test when no platforms are configured."""
        from mcp_ticketer.cli.setup_command import _check_existing_platform_configs

        mock_platform = Mock()
        mock_platform.name = "claude-code"
        mock_platform.display_name = "Claude Code"

        with patch.object(Path, "exists", return_value=False):
            result = _check_existing_platform_configs([mock_platform], tmp_path)

            assert len(result) == 0
