"""Test that serve command respects project-specific configuration."""

import json
import tempfile
from pathlib import Path
from unittest import mock

# Import the necessary modules
from mcp_ticketer.cli.main import load_config


def test_serve_command_respects_project_config() -> None:
    """Test that the serve command uses project-specific config when available."""

    # Create a temporary project directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create project-specific config
        project_config_dir = tmpdir_path / ".mcp-ticketer"
        project_config_dir.mkdir(parents=True, exist_ok=True)
        project_config_file = project_config_dir / "config.json"

        project_config_data = {
            "default_adapter": "aitrackdown",
            "adapters": {"aitrackdown": {"base_path": ".aitrackdown-project"}},
        }

        with open(project_config_file, "w") as f:
            json.dump(project_config_data, f, indent=2)

        # Create global config with different settings
        global_config_dir = Path.home() / ".mcp-ticketer"
        global_config_dir.mkdir(parents=True, exist_ok=True)
        global_config_file = global_config_dir / "config.json"

        global_config_data = {
            "default_adapter": "aitrackdown",
            "adapters": {"aitrackdown": {"base_path": ".aitrackdown-global"}},
        }

        # Backup existing global config
        backup_config = None
        if global_config_file.exists():
            with open(global_config_file) as f:
                backup_config = f.read()

        try:
            # Write temporary global config
            with open(global_config_file, "w") as f:
                json.dump(global_config_data, f, indent=2)

            # Simulate what the serve command does
            # It changes working directory based on MCP config
            with mock.patch("pathlib.Path.cwd", return_value=tmpdir_path):
                # Load config as serve command would
                config = load_config()

                # Verify project-specific config was loaded
                adapter_type = config.get("default_adapter", "aitrackdown")
                adapters_config = config.get("adapters", {})
                adapter_config = adapters_config.get(adapter_type, {})
                base_path = adapter_config.get("base_path")

                assert (
                    base_path == ".aitrackdown-project"
                ), f"Expected '.aitrackdown-project', got '{base_path}'"

                print("✓ Test passed: serve command would use project config")
                print(f"  Adapter: {adapter_type}")
                print(f"  Base path: {base_path}")
                print(f"  Config loaded from: {project_config_file}")

        finally:
            # Restore original global config
            if backup_config is not None:
                with open(global_config_file, "w") as f:
                    f.write(backup_config)
            elif global_config_file.exists():
                global_config_file.unlink()


def test_mcp_server_cwd_scenario() -> None:
    """
    Test the real-world scenario where MCP server is started with a specific cwd.

    When Claude Code/Desktop starts the MCP server, it sets the working directory
    based on the 'cwd' field in .mcp/config.json. This test simulates that scenario.
    """

    # Simulate a project at /path/to/project
    with tempfile.TemporaryDirectory() as project_root:
        project_path = Path(project_root)

        # Create project-specific config (what user would run: mcp-ticketer init)
        project_config_dir = project_path / ".mcp-ticketer"
        project_config_dir.mkdir(parents=True, exist_ok=True)
        project_config_file = project_config_dir / "config.json"

        project_config_data = {
            "default_adapter": "linear",
            "adapters": {
                "linear": {"team_key": "PROJ", "api_key": "project-specific-key"}
            },
        }

        with open(project_config_file, "w") as f:
            json.dump(project_config_data, f, indent=2)

        # MCP server starts with cwd set to project_root
        # (as configured in .mcp/config.json)
        with mock.patch("pathlib.Path.cwd", return_value=project_path):
            # This is what happens inside the serve command
            config = load_config()

            # Verify correct config was loaded
            assert (
                config["default_adapter"] == "linear"
            ), "Expected project's default adapter"
            assert (
                config["adapters"]["linear"]["team_key"] == "PROJ"
            ), "Expected project-specific team_key"

            print("✓ Test passed: MCP server cwd scenario")
            print(f"  Project root: {project_path}")
            print(f"  Config file: {project_config_file}")
            print(f"  Default adapter: {config['default_adapter']}")


if __name__ == "__main__":
    print("Testing serve command configuration resolution...")
    print()

    test_serve_command_respects_project_config()
    print()
    test_mcp_server_cwd_scenario()
    print()

    print("All serve command tests passed! ✓")
    print()
    print("Summary:")
    print("- The serve command will now respect project-specific config")
    print("- MCP server started via Claude Code/Desktop will use the correct config")
    print("- Config resolution order: project > global > default")
