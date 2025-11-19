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
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
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
            patch("mcp_ticketer.cli.main._prompt_for_adapter_selection") as mock_prompt,
            patch("mcp_ticketer.cli.main.init") as mock_init,
            patch(
                "mcp_ticketer.cli.platform_detection.PlatformDetector"
            ) as mock_detector_class,
            patch("typer.prompt"),
        ):
            # Setup mocks
            mock_discover.return_value = None
            mock_prompt.return_value = "aitrackdown"

            # Mock platform detector
            mock_detector = Mock()
            mock_detector.detect_all.return_value = []
            mock_detector_class.return_value = mock_detector

            # Invoke with mix mode to avoid interactive prompts
            runner.invoke(app, ["setup"], input="")

            # Should call init
            assert mock_init.called

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
            patch("mcp_ticketer.cli.main.init") as mock_init,
            patch(
                "mcp_ticketer.cli.platform_detection.PlatformDetector"
            ) as mock_detector_class,
            patch("typer.confirm") as mock_confirm,
            patch("typer.prompt"),
        ):
            # User confirms to keep existing settings
            mock_confirm.side_effect = [True, False]  # Keep config, skip platforms

            # Mock platform detector
            mock_detector = Mock()
            mock_detector.detect_all.return_value = []
            mock_detector_class.return_value = mock_detector

            result = runner.invoke(app, ["setup"], input="")

            # Should NOT call init (config already exists and user kept it)
            assert not mock_init.called
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
            patch("mcp_ticketer.cli.main._prompt_for_adapter_selection") as mock_prompt,
            patch("mcp_ticketer.cli.main.init") as mock_init,
            patch(
                "mcp_ticketer.cli.platform_detection.PlatformDetector"
            ) as mock_detector_class,
        ):
            # Setup mocks
            mock_discover.return_value = None
            mock_prompt.return_value = "aitrackdown"

            # Mock platform detector
            mock_detector = Mock()
            mock_detector.detect_all.return_value = []
            mock_detector_class.return_value = mock_detector

            runner.invoke(app, ["setup", "--force-reinit"], input="")

            # Should call init even though config exists
            assert mock_init.called

    def test_setup_skip_platforms(self, tmp_path: Path) -> None:
        """Test setup with --skip-platforms flag."""
        with (
            patch("mcp_ticketer.cli.main.Path.cwd", return_value=tmp_path),
            patch("mcp_ticketer.core.env_discovery.discover_config") as mock_discover,
            patch("mcp_ticketer.cli.main._prompt_for_adapter_selection") as mock_prompt,
            patch("mcp_ticketer.cli.main.init") as mock_init,
            patch(
                "mcp_ticketer.cli.platform_detection.PlatformDetector"
            ) as mock_detector_class,
        ):
            # Setup mocks
            mock_discover.return_value = None
            mock_prompt.return_value = "aitrackdown"

            # Mock detector should NOT be called when skipping platforms
            mock_detector = Mock()
            mock_detector_class.return_value = mock_detector

            runner.invoke(app, ["setup", "--skip-platforms"], input="")

            # Should call init but not detect platforms
            assert mock_init.called
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
                "mcp_ticketer.cli.main._check_existing_platform_configs"
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
                "mcp_ticketer.cli.main._check_existing_platform_configs"
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
                "mcp_ticketer.cli.main._check_existing_platform_configs"
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
                "mcp_ticketer.cli.main._check_existing_platform_configs"
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
class TestCheckExistingPlatformConfigs:
    """Test suite for _check_existing_platform_configs helper."""

    def test_check_claude_code_configured(self, tmp_path: Path) -> None:
        """Test detection of Claude Code configuration."""
        from mcp_ticketer.cli.main import _check_existing_platform_configs

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
        from mcp_ticketer.cli.main import _check_existing_platform_configs

        mock_platform = Mock()
        mock_platform.name = "claude-code"
        mock_platform.display_name = "Claude Code"

        with patch.object(Path, "exists", return_value=False):
            result = _check_existing_platform_configs([mock_platform], tmp_path)

            assert len(result) == 0
