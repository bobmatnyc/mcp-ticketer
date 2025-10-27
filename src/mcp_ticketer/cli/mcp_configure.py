"""MCP configuration for Claude Code integration."""

import json
import os
import shutil
import sys
from pathlib import Path

from rich.console import Console

from .python_detection import get_mcp_ticketer_python

console = Console()


def load_env_file(env_path: Path) -> dict[str, str]:
    """Load environment variables from .env file.

    Args:
        env_path: Path to .env file

    Returns:
        Dict of environment variable key-value pairs

    """
    env_vars = {}
    if not env_path.exists():
        return env_vars

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue

            # Parse KEY=VALUE format
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

    return env_vars


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
        # Project-level configuration for Claude Code
        config_path = Path.cwd() / ".claude" / "settings.local.json"

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

    # Return empty structure (Claude Code uses mcpServers key)
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
    python_path: str, project_config: dict, project_path: str | None = None
) -> dict:
    """Create MCP server configuration for mcp-ticketer.

    Args:
        python_path: Path to Python executable in mcp-ticketer venv
        project_config: Project configuration from .mcp-ticketer/config.json
        project_path: Project directory path (optional)

    Returns:
        MCP server configuration dict matching Claude Code stdio pattern

    """
    # Ensure python3 is used (not python)
    if python_path.endswith("/python"):
        python_path = python_path.replace("/python", "/python3")

    # Use module invocation pattern: python -m mcp_ticketer.mcp.server
    args = ["-m", "mcp_ticketer.mcp.server"]

    # Add project path if provided
    if project_path:
        args.append(project_path)

    # REQUIRED: Add "type": "stdio" for Claude Code compatibility
    config = {
        "type": "stdio",
        "command": python_path,
        "args": args,
    }

    # Add environment variables based on adapter
    adapter = project_config.get("default_adapter", "aitrackdown")
    adapters_config = project_config.get("adapters", {})
    adapter_config = adapters_config.get(adapter, {})

    env_vars = {}

    # Add PYTHONPATH for project context
    if project_path:
        env_vars["PYTHONPATH"] = project_path

    # Add MCP_TICKETER_ADAPTER to identify which adapter to use
    env_vars["MCP_TICKETER_ADAPTER"] = adapter

    # Load environment variables from .env.local if it exists
    if project_path:
        env_file_path = Path(project_path) / ".env.local"
        env_file_vars = load_env_file(env_file_path)

        # Add relevant adapter-specific vars from .env.local
        adapter_env_keys = {
            "linear": ["LINEAR_API_KEY", "LINEAR_TEAM_ID", "LINEAR_TEAM_KEY"],
            "github": ["GITHUB_TOKEN", "GITHUB_OWNER", "GITHUB_REPO"],
            "jira": [
                "JIRA_ACCESS_USER",
                "JIRA_ACCESS_TOKEN",
                "JIRA_ORGANIZATION_ID",
                "JIRA_URL",
                "JIRA_EMAIL",
                "JIRA_API_TOKEN",
            ],
            "aitrackdown": [],  # No specific env vars needed
        }

        # Include adapter-specific env vars from .env.local
        for key in adapter_env_keys.get(adapter, []):
            if key in env_file_vars:
                env_vars[key] = env_file_vars[key]

    # Fallback: Add adapter-specific environment variables from project config
    if adapter == "linear" and "api_key" in adapter_config:
        if "LINEAR_API_KEY" not in env_vars:
            env_vars["LINEAR_API_KEY"] = adapter_config["api_key"]
    elif adapter == "github" and "token" in adapter_config:
        if "GITHUB_TOKEN" not in env_vars:
            env_vars["GITHUB_TOKEN"] = adapter_config["token"]
    elif adapter == "jira":
        if "api_token" in adapter_config and "JIRA_API_TOKEN" not in env_vars:
            env_vars["JIRA_API_TOKEN"] = adapter_config["api_token"]
        if "email" in adapter_config and "JIRA_EMAIL" not in env_vars:
            env_vars["JIRA_EMAIL"] = adapter_config["email"]

    if env_vars:
        config["env"] = env_vars

    return config


def remove_claude_mcp(global_config: bool = False, dry_run: bool = False) -> None:
    """Remove mcp-ticketer from Claude Code/Desktop configuration.

    Args:
        global_config: Remove from Claude Desktop instead of project-level
        dry_run: Show what would be removed without making changes

    """
    # Step 1: Find Claude MCP config location
    config_type = "Claude Desktop" if global_config else "project-level"
    console.print(f"[cyan]🔍 Removing {config_type} MCP configuration...[/cyan]")

    mcp_config_path = find_claude_mcp_config(global_config)
    console.print(f"[dim]Config location: {mcp_config_path}[/dim]")

    # Step 2: Check if config file exists
    if not mcp_config_path.exists():
        console.print(f"[yellow]⚠ No configuration found at {mcp_config_path}[/yellow]")
        console.print("[dim]mcp-ticketer is not configured for this platform[/dim]")
        return

    # Step 3: Load existing MCP configuration
    mcp_config = load_claude_mcp_config(mcp_config_path)

    # Step 4: Check if mcp-ticketer is configured
    if "mcp-ticketer" not in mcp_config.get("mcpServers", {}):
        console.print("[yellow]⚠ mcp-ticketer is not configured[/yellow]")
        console.print(f"[dim]No mcp-ticketer entry found in {mcp_config_path}[/dim]")
        return

    # Step 5: Show what would be removed (dry run or actual removal)
    if dry_run:
        console.print("\n[cyan]DRY RUN - Would remove:[/cyan]")
        console.print("  Server name: mcp-ticketer")
        console.print(f"  From: {mcp_config_path}")
        return

    # Step 6: Remove mcp-ticketer from configuration
    del mcp_config["mcpServers"]["mcp-ticketer"]

    # Step 7: Save updated configuration
    try:
        save_claude_mcp_config(mcp_config_path, mcp_config)
        console.print("\n[green]✓ Successfully removed mcp-ticketer[/green]")
        console.print(f"[dim]Configuration updated: {mcp_config_path}[/dim]")

        # Next steps
        console.print("\n[bold cyan]Next Steps:[/bold cyan]")
        if global_config:
            console.print("1. Restart Claude Desktop")
            console.print("2. mcp-ticketer will no longer be available in MCP menu")
        else:
            console.print("1. Restart Claude Code")
            console.print("2. mcp-ticketer will no longer be available in this project")

    except Exception as e:
        console.print(f"\n[red]✗ Failed to update configuration:[/red] {e}")
        raise


def configure_claude_mcp(global_config: bool = False, force: bool = False) -> None:
    """Configure Claude Code to use mcp-ticketer.

    Args:
        global_config: Configure Claude Desktop instead of project-level
        force: Overwrite existing configuration

    Raises:
        FileNotFoundError: If Python executable or project config not found
        ValueError: If configuration is invalid

    """
    # Step 1: Find Python executable
    console.print("[cyan]🔍 Finding mcp-ticketer Python executable...[/cyan]")
    try:
        python_path = get_mcp_ticketer_python()
        console.print(f"[green]✓[/green] Found: {python_path}")
    except Exception as e:
        console.print(f"[red]✗[/red] Could not find Python executable: {e}")
        raise FileNotFoundError(
            "Could not find mcp-ticketer Python executable. "
            "Please ensure mcp-ticketer is installed.\n"
            "Install with: pip install mcp-ticketer or pipx install mcp-ticketer"
        )

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
    project_path = str(Path.cwd()) if not global_config else None
    server_config = create_mcp_server_config(
        python_path=python_path, project_config=project_config, project_path=project_path
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
        console.print(f"  Python: {python_path}")
        console.print(f"  Command: python -m mcp_ticketer.mcp.server")
        if project_path:
            console.print(f"  Project path: {project_path}")
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
