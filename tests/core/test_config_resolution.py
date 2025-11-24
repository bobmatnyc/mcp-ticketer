"""Test configuration resolution order for project-specific vs global config."""

import json
import tempfile
from pathlib import Path
from unittest import mock

# Import the function we're testing
from mcp_ticketer.cli.main import load_config


def test_project_specific_config_takes_precedence() -> None:
    """Test that project-specific config is loaded when it exists."""
    # Create a temporary directory structure
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create project-specific config
        project_config_dir = tmpdir_path / ".mcp-ticketer"
        project_config_dir.mkdir(parents=True, exist_ok=True)
        project_config_file = project_config_dir / "config.json"

        project_config_data = {
            "default_adapter": "linear",
            "adapters": {"linear": {"team_key": "PROJECT-SPECIFIC"}},
        }

        with open(project_config_file, "w") as f:
            json.dump(project_config_data, f)

        # Create global config
        global_config_dir = Path.home() / ".mcp-ticketer"
        global_config_dir.mkdir(parents=True, exist_ok=True)
        global_config_file = global_config_dir / "config.json"

        global_config_data = {
            "default_adapter": "github",
            "adapters": {"github": {"owner": "GLOBAL-CONFIG"}},
        }

        # Backup existing global config if it exists
        backup_config = None
        if global_config_file.exists():
            with open(global_config_file) as f:
                backup_config = f.read()

        try:
            # Write temporary global config
            with open(global_config_file, "w") as f:
                json.dump(global_config_data, f)

            # Mock Path.cwd() to return our temp directory
            with mock.patch("pathlib.Path.cwd", return_value=tmpdir_path):
                # Load config - should prefer project-specific
                config = load_config()

                # Verify project-specific config was loaded
                assert (
                    config["default_adapter"] == "linear"
                ), f"Expected 'linear', got '{config['default_adapter']}'"
                assert (
                    "linear" in config["adapters"]
                ), "Expected 'linear' adapter in config"
                assert (
                    config["adapters"]["linear"]["team_key"] == "PROJECT-SPECIFIC"
                ), "Expected project-specific config values"

                print("✓ Test passed: Project-specific config takes precedence")

        finally:
            # Restore original global config
            if backup_config is not None:
                with open(global_config_file, "w") as f:
                    f.write(backup_config)
            elif global_config_file.exists():
                global_config_file.unlink()


def test_global_config_fallback() -> None:
    """Test that default config is used when project-specific doesn't exist.

    NOTE: Global config loading has been removed for security reasons.
    The load_config() function now only reads from project-local directories.
    When no project config exists, it defaults to aitrackdown adapter.
    """
    # Create a temporary directory without project config
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Mock Path.cwd() to return temp directory (no project config)
        with mock.patch("pathlib.Path.cwd", return_value=tmpdir_path):
            # Load config - should use default (aitrackdown)
            config = load_config()

            # Verify default config was loaded (aitrackdown fallback)
            assert (
                config["adapter"] == "aitrackdown"
            ), f"Expected 'aitrackdown', got '{config.get('adapter')}'"
            assert "config" in config, "Expected 'config' key in default config"
            assert (
                config["config"]["base_path"] == ".aitrackdown"
            ), "Expected default base_path"

            print("✓ Test passed: Default config used when project config missing")


def test_default_fallback() -> None:
    """Test that default config is used when neither project nor global exists."""
    # Create a temporary directory without any config
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Backup and remove global config if it exists
        global_config_file = Path.home() / ".mcp-ticketer" / "config.json"
        backup_config = None
        if global_config_file.exists():
            with open(global_config_file) as f:
                backup_config = f.read()
            global_config_file.unlink()

        try:
            # Mock Path.cwd() to return temp directory
            with mock.patch("pathlib.Path.cwd", return_value=tmpdir_path):
                # Load config - should use defaults
                config = load_config()

                # Verify default config was loaded
                assert (
                    config["adapter"] == "aitrackdown"
                ), f"Expected 'aitrackdown', got '{config.get('adapter')}'"
                assert "config" in config, "Expected default config structure"
                assert (
                    config["config"]["base_path"] == ".aitrackdown"
                ), "Expected default base_path"

                print("✓ Test passed: Default config used when no configs exist")

        finally:
            # Restore original global config
            if backup_config is not None:
                global_config_file.parent.mkdir(parents=True, exist_ok=True)
                with open(global_config_file, "w") as f:
                    f.write(backup_config)


if __name__ == "__main__":
    print("Testing configuration resolution order...")
    print()

    test_project_specific_config_takes_precedence()
    test_global_config_fallback()
    test_default_fallback()

    print()
    print("All tests passed! ✓")
