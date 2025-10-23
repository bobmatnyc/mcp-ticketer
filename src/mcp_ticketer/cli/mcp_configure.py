"""MCP configuration for Claude Code integration."""

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


def find_mcp_ticketer_binary() -> str:
    """Find the mcp-ticketer binary path.

    Returns:
        Path to mcp-ticketer binary

    Raises:
        FileNotFoundError: If binary not found

    """
    # Check if running from development environment
    import mcp_ticketer

    package_path = Path(mcp_ticketer.__file__).parent.parent.parent

    # Check for virtual environment bin
    possible_paths = [
        # Development paths
        package_path / "venv" / "bin" / "mcp-ticketer",
        package_path / ".venv" / "bin" / "mcp-ticketer",
        package_path / "test_venv" / "bin" / "mcp-ticketer",
        # System installation
        Path.home() / ".local" / "bin" / "mcp-ticketer",
        # pipx installation
        Path.home()
        / ".local"
        / "pipx"
        / "venvs"
        / "mcp-ticketer"
        / "bin"
        / "mcp-ticketer",
    ]

    # Check PATH
    which_result = shutil.which("mcp-ticketer")
    if which_result:
        return which_result

    # Check possible paths
    for path in possible_paths:
        if path.exists():
            return str(path.resolve())

    raise FileNotFoundError(
        "Could not find mcp-ticketer binary. Please ensure mcp-ticketer is installed.\n"
        "Install with: pip install mcp-ticketer"
    )


def load_project_config() -> dict:
    """Load mcp-ticketer project configuration.

    Returns:
        Project configuration dict

    Raises:
        FileNotFoundError: If config not found
        ValueError: If config is invalid

    """
    # Check for project-specific config first
    project_config_path = Path.cwd() / ".mcp-ticketer" / "config.json"

    if not project_config_path.exists():
        # Check global config
        global_config_path = Path.home() / ".mcp-ticketer" / "config.json"
        if global_config_path.exists():
            project_config_path = global_config_path
        else:
            raise FileNotFoundError(
                "No mcp-ticketer configuration found.\n"
                "Run 'mcp-ticketer init' to create configuration."
            )

    with open(project_config_path) as f:
        config = json.load(f)

    # Validate config
    if "default_adapter" not in config:
        raise ValueError("Invalid config: missing 'default_adapter'")

    return config


def find_claude_mcp_config(global_config: bool = False) -> Path:
    """Find or create Claude Code MCP configuration file.

    Args:
        global_config: If True, use Claude Desktop config instead of project-level

    Returns:
        Path to MCP configuration file

    """
    if global_config:
        # Claude Desktop configuration
        if sys.platform == "darwin":  # macOS
            config_path = (
                Path.home()
                / "Library"
                / "Application Support"
                / "Claude"
                / "claude_desktop_config.json"
            )
        elif sys.platform == "win32":  # Windows
            config_path = (
                Path(os.environ.get("APPDATA", ""))
                / "Claude"
                / "claude_desktop_config.json"
            )
        else:  # Linux
            config_path = (
                Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
            )
    else:
        # Project-level configuration
        config_path = Path.cwd() / ".mcp" / "config.json"

    return config_path


def load_claude_mcp_config(config_path: Path) -> dict:
    """Load existing Claude MCP configuration or return empty structure.

    Args:
        config_path: Path to MCP config file

    Returns:
        MCP configuration dict

    """
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)

    # Return empty structure
    return {"mcpServers": {}}


def save_claude_mcp_config(config_path: Path, config: dict) -> None:
    """Save Claude MCP configuration to file.

    Args:
        config_path: Path to MCP config file
        config: Configuration to save

    """
    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write with formatting
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def create_mcp_server_config(
    binary_path: str, project_config: dict, cwd: Optional[str] = None
) -> dict:
    """Create MCP server configuration for mcp-ticketer.

    Args:
        binary_path: Path to mcp-ticketer binary
        project_config: Project configuration from .mcp-ticketer/config.json
        cwd: Working directory for server (optional)

    Returns:
        MCP server configuration dict

    """
    config = {
        "command": binary_path,
        "args": ["serve"],  # Use 'serve' command to start MCP server
    }

    # Add working directory if provided
    if cwd:
        config["cwd"] = cwd

    # Add environment variables based on adapter
    adapter = project_config.get("default_adapter", "aitrackdown")
    adapters_config = project_config.get("adapters", {})
    adapter_config = adapters_config.get(adapter, {})

    env_vars = {}

    # Add adapter-specific environment variables
    if adapter == "linear" and "api_key" in adapter_config:
        env_vars["LINEAR_API_KEY"] = adapter_config["api_key"]
    elif adapter == "github" and "token" in adapter_config:
        env_vars["GITHUB_TOKEN"] = adapter_config["token"]
    elif adapter == "jira":
        if "api_token" in adapter_config:
            env_vars["JIRA_API_TOKEN"] = adapter_config["api_token"]
        if "email" in adapter_config:
            env_vars["JIRA_EMAIL"] = adapter_config["email"]

    if env_vars:
        config["env"] = env_vars

    return config


def configure_claude_mcp(global_config: bool = False, force: bool = False) -> None:
    """Configure Claude Code to use mcp-ticketer.

    Args:
        global_config: Configure Claude Desktop instead of project-level
        force: Overwrite existing configuration

    Raises:
        FileNotFoundError: If binary or project config not found
        ValueError: If configuration is invalid

    """
    # Step 1: Find mcp-ticketer binary
    console.print("[cyan]🔍 Finding mcp-ticketer binary...[/cyan]")
    try:
        binary_path = find_mcp_ticketer_binary()
        console.print(f"[green]✓[/green] Found: {binary_path}")
    except FileNotFoundError as e:
        console.print(f"[red]✗[/red] {e}")
        raise

    # Step 2: Load project configuration
    console.print("\n[cyan]📖 Reading project configuration...[/cyan]")
    try:
        project_config = load_project_config()
        adapter = project_config.get("default_adapter", "aitrackdown")
        console.print(f"[green]✓[/green] Adapter: {adapter}")
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]✗[/red] {e}")
        raise

    # Step 3: Find Claude MCP config location
    config_type = "Claude Desktop" if global_config else "project-level"
    console.print(f"\n[cyan]🔧 Configuring {config_type} MCP...[/cyan]")

    mcp_config_path = find_claude_mcp_config(global_config)
    console.print(f"[dim]Config location: {mcp_config_path}[/dim]")

    # Step 4: Load existing MCP configuration
    mcp_config = load_claude_mcp_config(mcp_config_path)

    # Step 5: Check if mcp-ticketer already configured
    if "mcp-ticketer" in mcp_config.get("mcpServers", {}):
        if not force:
            console.print("[yellow]⚠ mcp-ticketer is already configured[/yellow]")
            console.print("[dim]Use --force to overwrite existing configuration[/dim]")
            return
        else:
            console.print("[yellow]⚠ Overwriting existing configuration[/yellow]")

    # Step 6: Create mcp-ticketer server config
    cwd = str(Path.cwd()) if not global_config else None
    server_config = create_mcp_server_config(
        binary_path=binary_path, project_config=project_config, cwd=cwd
    )

    # Step 7: Update MCP configuration
    if "mcpServers" not in mcp_config:
        mcp_config["mcpServers"] = {}

    mcp_config["mcpServers"]["mcp-ticketer"] = server_config

    # Step 8: Save configuration
    try:
        save_claude_mcp_config(mcp_config_path, mcp_config)
        console.print("\n[green]✓ Successfully configured mcp-ticketer[/green]")
        console.print(f"[dim]Configuration saved to: {mcp_config_path}[/dim]")

        # Print configuration details
        console.print("\n[bold]Configuration Details:[/bold]")
        console.print("  Server name: mcp-ticketer")
        console.print(f"  Adapter: {adapter}")
        console.print(f"  Binary: {binary_path}")
        if cwd:
            console.print(f"  Working directory: {cwd}")
        if "env" in server_config:
            console.print(
                f"  Environment variables: {list(server_config['env'].keys())}"
            )

        # Next steps
        console.print("\n[bold cyan]Next Steps:[/bold cyan]")
        if global_config:
            console.print("1. Restart Claude Desktop")
            console.print("2. Open a conversation")
        else:
            console.print("1. Restart Claude Code")
            console.print("2. Open this project in Claude Code")
        console.print("3. mcp-ticketer tools will be available in the MCP menu")

    except Exception as e:
        console.print(f"\n[red]✗ Failed to save configuration:[/red] {e}")
        raise
