"""Auggie CLI configuration for mcp-ticketer integration.

IMPORTANT: Auggie CLI ONLY supports global configuration at ~/.augment/settings.json.
There is no project-level configuration support.
"""

import json
from pathlib import Path
from typing import Any

from rich.console import Console

from .mcp_configure import find_mcp_ticketer_binary, load_project_config

console = Console()


def find_auggie_config() -> Path:
    """Find or create Auggie CLI configuration file.

    Auggie CLI only supports global user-level configuration.

    Returns:
        Path to Auggie settings file at ~/.augment/settings.json

    """
    # Global user-level configuration (ONLY option for Auggie)
    config_path = Path.home() / ".augment" / "settings.json"
    return config_path


def load_auggie_config(config_path: Path) -> dict[str, Any]:
    """Load existing Auggie configuration or return empty structure.

    Args:
        config_path: Path to Auggie settings file

    Returns:
        Auggie configuration dict

    """
    if config_path.exists():
        try:
            with open(config_path) as f:
                config: dict[str, Any] = json.load(f)
                return config
        except json.JSONDecodeError as e:
            console.print(
                f"[yellow]⚠ Warning: Could not parse existing config: {e}[/yellow]"
            )
            console.print("[yellow]Creating new configuration...[/yellow]")

    # Return empty structure with mcpServers section
    return {"mcpServers": {}}


def save_auggie_config(config_path: Path, config: dict[str, Any]) -> None:
    """Save Auggie configuration to file.

    Args:
        config_path: Path to Auggie settings file
        config: Configuration to save

    """
    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write with 2-space indentation (JSON standard)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def create_auggie_server_config(
    binary_path: str, project_config: dict[str, Any]
) -> dict[str, Any]:
    """Create Auggie MCP server configuration for mcp-ticketer.

    Args:
        binary_path: Path to mcp-ticketer binary
        project_config: Project configuration from .mcp-ticketer/config.json

    Returns:
        Auggie MCP server configuration dict

    """
    # Get adapter configuration
    adapter = project_config.get("default_adapter", "aitrackdown")
    adapters_config = project_config.get("adapters", {})
    adapter_config = adapters_config.get(adapter, {})

    # Build environment variables
    env_vars = {}

    # Add adapter type
    env_vars["MCP_TICKETER_ADAPTER"] = adapter

    # Add adapter-specific environment variables
    if adapter == "aitrackdown":
        # Set base path for local adapter
        base_path = adapter_config.get("base_path", ".aitrackdown")
        # Use absolute path to home directory for global config
        # Since Auggie is global, we can't rely on project-specific paths
        env_vars["MCP_TICKETER_BASE_PATH"] = str(
            Path.home() / ".mcp-ticketer" / base_path
        )

    elif adapter == "linear":
        if "api_key" in adapter_config:
            env_vars["LINEAR_API_KEY"] = adapter_config["api_key"]
        if "team_id" in adapter_config:
            env_vars["LINEAR_TEAM_ID"] = adapter_config["team_id"]

    elif adapter == "github":
        if "token" in adapter_config:
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
        if "server" in adapter_config:
            env_vars["JIRA_SERVER"] = adapter_config["server"]
        if "project_key" in adapter_config:
            env_vars["JIRA_PROJECT_KEY"] = adapter_config["project_key"]

    # Create server configuration (simpler than Gemini - no timeout/trust)
    config = {
        "command": binary_path,
        "args": ["serve"],
        "env": env_vars,
    }

    return config


def configure_auggie_mcp(force: bool = False) -> None:
    """Configure Auggie CLI to use mcp-ticketer.

    IMPORTANT: Auggie CLI ONLY supports global configuration.
    This will configure ~/.augment/settings.json for all projects.

    Args:
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

    # Step 3: Find Auggie config location
    console.print("\n[cyan]🔧 Configuring global Auggie CLI...[/cyan]")
    console.print(
        "[yellow]⚠ NOTE: Auggie only supports global configuration (affects all projects)[/yellow]"
    )

    auggie_config_path = find_auggie_config()
    console.print(f"[dim]Config location: {auggie_config_path}[/dim]")

    # Step 4: Load existing Auggie configuration
    auggie_config = load_auggie_config(auggie_config_path)

    # Step 5: Check if mcp-ticketer already configured
    if "mcp-ticketer" in auggie_config.get("mcpServers", {}):
        if not force:
            console.print("[yellow]⚠ mcp-ticketer is already configured[/yellow]")
            console.print("[dim]Use --force to overwrite existing configuration[/dim]")
            return
        else:
            console.print("[yellow]⚠ Overwriting existing configuration[/yellow]")

    # Step 6: Create mcp-ticketer server config
    server_config = create_auggie_server_config(
        binary_path=binary_path, project_config=project_config
    )

    # Step 7: Update Auggie configuration
    if "mcpServers" not in auggie_config:
        auggie_config["mcpServers"] = {}

    auggie_config["mcpServers"]["mcp-ticketer"] = server_config

    # Step 8: Save configuration
    try:
        save_auggie_config(auggie_config_path, auggie_config)
        console.print("\n[green]✓ Successfully configured mcp-ticketer[/green]")
        console.print(f"[dim]Configuration saved to: {auggie_config_path}[/dim]")

        # Print configuration details
        console.print("\n[bold]Configuration Details:[/bold]")
        console.print("  Server name: mcp-ticketer")
        console.print(f"  Adapter: {adapter}")
        console.print(f"  Binary: {binary_path}")
        console.print("  Scope: Global (affects all projects)")
        if "env" in server_config:
            console.print(
                f"  Environment variables: {list(server_config['env'].keys())}"
            )

        # Next steps
        console.print("\n[bold cyan]Next Steps:[/bold cyan]")
        console.print("1. Restart Auggie CLI for changes to take effect")
        console.print("2. Run 'auggie' command in any directory")
        console.print("3. mcp-ticketer tools will be available via MCP")
        console.print(
            "\n[yellow]⚠ Warning: This is a global configuration affecting all projects[/yellow]"
        )
        console.print(
            "[dim]If you need project-specific configuration, use Claude or Gemini instead[/dim]"
        )

    except Exception as e:
        console.print(f"\n[red]✗ Failed to save configuration:[/red] {e}")
        raise
