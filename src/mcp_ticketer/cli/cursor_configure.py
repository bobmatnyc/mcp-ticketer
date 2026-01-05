"""Cursor code editor configuration for mcp-ticketer integration.

Cursor uses project-level MCP configuration at ~/.cursor/mcp.json
with a flat mcpServers structure (similar to Claude Code's global config).
"""

import json
from pathlib import Path
from typing import Any

from rich.console import Console

from .mcp_configure import load_project_config
from .python_detection import get_mcp_ticketer_python
from .utils import CommonPatterns

console = Console()


def find_cursor_config() -> Path:
    """Find or create Cursor MCP configuration file.

    Cursor uses global MCP configuration with flat structure.

    Returns:
        Path to Cursor MCP config file at ~/.cursor/mcp.json

    """
    config_path = Path.home() / ".cursor" / "mcp.json"
    return config_path


def load_cursor_config(config_path: Path) -> dict[str, Any]:
    """Load existing Cursor configuration or return empty structure.

    Args:
        config_path: Path to Cursor MCP config file

    Returns:
        Cursor MCP configuration dict

    """
    if config_path.exists():
        try:
            with open(config_path) as f:
                content = f.read().strip()
                if not content:
                    return {"mcpServers": {}}
                config: dict[str, Any] = json.load(f)
                return config
        except json.JSONDecodeError as e:
            console.print(
                f"[yellow]⚠ Warning: Invalid JSON in {config_path}, creating new config[/yellow]"
            )
            console.print(f"[dim]Error: {e}[/dim]")

    # Return empty structure with mcpServers section
    return {"mcpServers": {}}


def save_cursor_config(config_path: Path, config: dict[str, Any]) -> None:
    """Save Cursor MCP configuration to file.

    Args:
        config_path: Path to Cursor MCP config file
        config: Configuration to save

    """
    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write with 2-space indentation (JSON standard)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def create_cursor_server_config(
    python_path: str,
    project_config: dict[str, Any],
    project_path: str | None = None,
) -> dict[str, Any]:
    """Create Cursor MCP server configuration for mcp-ticketer.

    Uses the CLI command (mcp-ticketer mcp) which implements proper
    Content-Length framing via FastMCP SDK, required for modern MCP clients.

    Args:
        python_path: Path to Python executable in mcp-ticketer venv
        project_config: Project configuration from .mcp-ticketer/config.json
        project_path: Project directory path (optional, for project-specific config)

    Returns:
        Cursor MCP server configuration dict

    """
    # IMPORTANT: Use CLI command, NOT Python module invocation
    # The CLI uses FastMCP SDK which implements proper Content-Length framing

    # Get adapter configuration
    adapter = project_config.get("default_adapter", "aitrackdown")
    adapters_config = project_config.get("adapters", {})
    adapter_config = adapters_config.get(adapter, {})

    # Get mcp-ticketer CLI path using PATH resolution (reliable for all installations)
    cli_path = CommonPatterns.get_mcp_cli_path()

    # Build CLI arguments
    args = ["mcp"]
    if project_path:
        args.extend(["--path", project_path])

    # Build environment variables
    env_vars = {}

    # Add PYTHONPATH for project context
    if project_path:
        env_vars["PYTHONPATH"] = project_path

    # Add adapter type
    env_vars["MCP_TICKETER_ADAPTER"] = adapter

    # Add adapter-specific environment variables
    if adapter == "linear" and "api_key" in adapter_config:
        env_vars["LINEAR_API_KEY"] = adapter_config["api_key"]
        if "team_id" in adapter_config:
            env_vars["LINEAR_TEAM_ID"] = adapter_config["team_id"]
    elif adapter == "github" and "token" in adapter_config:
        env_vars["GITHUB_TOKEN"] = adapter_config["token"]
        if "owner" in adapter_config:
            env_vars["GITHUB_OWNER"] = adapter_config["owner"]
        if "repo" in adapter_config:
            env_vars["GITHUB_REPO"] = adapter_config["repo"]
    elif adapter == "jira":
        if "api_token" in adapter_config:
            env_vars["JIRA_API_TOKEN"] = adapter_config["api_token"]
        if "email" in adapter_config:
            env_vars["JIRA_EMAIL"] = adapter_config["email"]

    # Create server configuration with Cursor-specific fields
    config = {
        "type": "stdio",  # Cursor requires explicit type
        "command": cli_path,
        "args": args,
        "env": env_vars,
    }

    # Add working directory for project-specific configs
    if project_path:
        config["cwd"] = project_path

    return config


def remove_cursor_mcp(dry_run: bool = False) -> None:
    """Remove mcp-ticketer from Cursor configuration.

    Args:
        dry_run: Show what would be removed without making changes

    """
    # Step 1: Find Cursor config location
    console.print("[cyan]🔍 Removing Cursor MCP configuration...[/cyan]")

    cursor_config_path = find_cursor_config()
    console.print(f"[dim]Config location: {cursor_config_path}[/dim]")

    # Step 2: Check if config file exists
    if not cursor_config_path.exists():
        console.print(
            f"[yellow]⚠ No configuration found at {cursor_config_path}[/yellow]"
        )
        console.print("[dim]mcp-ticketer is not configured for Cursor[/dim]")
        return

    # Step 3: Load existing Cursor configuration
    cursor_config = load_cursor_config(cursor_config_path)

    # Step 4: Check if mcp-ticketer is configured
    if "mcp-ticketer" not in cursor_config.get("mcpServers", {}):
        console.print("[yellow]⚠ mcp-ticketer is not configured[/yellow]")
        console.print(f"[dim]No mcp-ticketer entry found in {cursor_config_path}[/dim]")
        return

    # Show what would be removed (dry run)
    if dry_run:
        console.print(
            f"\n[cyan]DRY RUN - Would remove from: {cursor_config_path}[/cyan]"
        )
        console.print("  Server name: mcp-ticketer")
        return

    # Step 5: Remove mcp-ticketer from configuration
    del cursor_config["mcpServers"]["mcp-ticketer"]

    # Step 6: Save updated configuration
    try:
        save_cursor_config(cursor_config_path, cursor_config)
        console.print("\n[green]✓ Successfully removed mcp-ticketer[/green]")
        console.print(f"[dim]Updated {cursor_config_path}[/dim]")

        # Next steps
        console.print("\n[bold cyan]Next Steps:[/bold cyan]")
        console.print("1. Restart Cursor editor")
        console.print("2. mcp-ticketer will no longer be available in MCP menu")
    except Exception as e:
        console.print(f"\n[red]✗ Failed to save configuration:[/red] {e}")
        raise


def configure_cursor_mcp(force: bool = False) -> None:
    """Configure Cursor to use mcp-ticketer.

    Args:
        force: Overwrite existing configuration

    Raises:
        FileNotFoundError: If Python executable or project config not found
        ValueError: If configuration is invalid

    """
    # Determine project path
    project_path = Path.cwd()

    # Step 1: Find Python executable
    console.print("[cyan]🔍 Finding mcp-ticketer Python executable...[/cyan]")
    try:
        python_path = get_mcp_ticketer_python(project_path=project_path)
        console.print(f"[green]✓[/green] Found: {python_path}")

        # Show if using project venv or fallback
        if str(project_path / ".venv") in python_path:
            console.print("[dim]Using project-specific venv[/dim]")
        else:
            console.print("[dim]Using pipx/system Python[/dim]")
    except Exception as e:
        console.print(f"[red]✗[/red] Could not find Python executable: {e}")
        raise FileNotFoundError(
            "Could not find mcp-ticketer Python executable. "
            "Please ensure mcp-ticketer is installed.\n"
            "Install with: pip install mcp-ticketer or pipx install mcp-ticketer"
        ) from e

    # Step 2: Load project configuration
    console.print("\n[cyan]📖 Reading project configuration...[/cyan]")
    try:
        mcp_project_config = load_project_config()
        adapter = mcp_project_config.get("default_adapter", "aitrackdown")
        console.print(f"[green]✓[/green] Adapter: {adapter}")
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]✗[/red] {e}")
        raise

    # Step 3: Find Cursor MCP config location
    console.print("\n[cyan]🔧 Configuring Cursor MCP...[/cyan]")

    cursor_config_path = find_cursor_config()
    console.print(f"[dim]Config path: {cursor_config_path}[/dim]")

    # Step 4: Load existing MCP configuration
    cursor_config = load_cursor_config(cursor_config_path)

    # Step 5: Check if mcp-ticketer already configured
    already_configured = "mcp-ticketer" in cursor_config.get("mcpServers", {})

    if already_configured:
        if not force:
            console.print("[yellow]⚠ mcp-ticketer is already configured[/yellow]")
            console.print("[dim]Use --force to overwrite existing configuration[/dim]")
            return
        else:
            console.print("[yellow]⚠ Overwriting existing configuration[/yellow]")

    # Step 6: Create mcp-ticketer server config
    server_config = create_cursor_server_config(
        python_path=python_path,
        project_config=mcp_project_config,
        project_path=str(project_path.resolve()),
    )

    # Step 7: Update MCP configuration
    if "mcpServers" not in cursor_config:
        cursor_config["mcpServers"] = {}
    cursor_config["mcpServers"]["mcp-ticketer"] = server_config

    # Step 8: Save configuration
    try:
        save_cursor_config(cursor_config_path, cursor_config)
        console.print("\n[green]✓ Successfully configured mcp-ticketer[/green]")
        console.print(f"[dim]Configuration saved to: {cursor_config_path}[/dim]")

        # Print configuration details
        console.print("\n[bold]Configuration Details:[/bold]")
        console.print("  Server name: mcp-ticketer")
        console.print(f"  Adapter: {adapter}")
        console.print(f"  Python: {python_path}")
        console.print(f"  Command: {server_config.get('command')}")
        console.print(f"  Args: {server_config.get('args')}")
        console.print("  Protocol: Content-Length framing (FastMCP SDK)")
        console.print(f"  Project path: {project_path}")
        if "env" in server_config:
            console.print(
                f"  Environment variables: {list(server_config['env'].keys())}"
            )

        # Next steps
        console.print("\n[bold cyan]Next Steps:[/bold cyan]")
        console.print("1. Restart Cursor editor")
        console.print("2. Open this project in Cursor")
        console.print("3. mcp-ticketer tools will be available in the MCP menu")

    except Exception as e:
        console.print(f"\n[red]✗ Failed to save configuration:[/red] {e}")
        raise
