"""Auggie CLI configuration for mcp-ticketer integration.

IMPORTANT: Auggie CLI ONLY supports global configuration at ~/.augment/settings.json.
There is no project-level configuration support.
"""

import json
from pathlib import Path
from typing import Any

from rich.console import Console

from .mcp_configure import load_project_config
from .python_detection import get_mcp_ticketer_python
from .utils import CommonPatterns

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
    python_path: str, project_config: dict[str, Any], project_path: str | None = None
) -> dict[str, Any]:
    """Create Auggie MCP server configuration for mcp-ticketer.

    Uses the CLI command (mcp-ticketer mcp) which implements proper
    Content-Length framing via FastMCP SDK, required for modern MCP clients.

    Args:
        python_path: Path to Python executable in mcp-ticketer venv
        project_config: Project configuration from .mcp-ticketer/config.json
        project_path: Project directory path (optional)

    Returns:
        Auggie MCP server configuration dict

    """
    # IMPORTANT: Use CLI command, NOT Python module invocation
    # The CLI uses FastMCP SDK which implements proper Content-Length framing
    # Legacy python -m mcp_ticketer.mcp.server uses line-delimited JSON (incompatible)
    from pathlib import Path

    # Get adapter configuration
    adapter = project_config.get("default_adapter", "aitrackdown")
    adapters_config = project_config.get("adapters", {})
    adapter_config = adapters_config.get(adapter, {})

    # Build environment variables
    env_vars = {}

    # Add PYTHONPATH for project context
    if project_path:
        env_vars["PYTHONPATH"] = project_path

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

    # Get mcp-ticketer CLI path using PATH resolution (reliable for all installations)
    cli_path = CommonPatterns.get_mcp_cli_path()

    # Build CLI arguments
    args = ["mcp"]
    if project_path:
        args.extend(["--path", project_path])

    # Create server configuration (simpler than Gemini - no timeout/trust)
    # NOTE: Environment variables below are optional fallbacks
    # The CLI loads config from .mcp-ticketer/config.json
    config = {
        "command": cli_path,
        "args": args,
        "env": env_vars,
    }

    return config


def remove_auggie_mcp(dry_run: bool = False) -> None:
    """Remove mcp-ticketer from Auggie CLI configuration.

    IMPORTANT: Auggie CLI ONLY supports global configuration.
    This will remove mcp-ticketer from ~/.augment/settings.json.

    Args:
        dry_run: Show what would be removed without making changes

    """
    # Step 1: Find Auggie config location
    console.print("[cyan]🔍 Removing Auggie CLI global configuration...[/cyan]")
    console.print(
        "[yellow]⚠ NOTE: Auggie only supports global configuration (affects all projects)[/yellow]"
    )

    auggie_config_path = find_auggie_config()
    console.print(f"[dim]Config location: {auggie_config_path}[/dim]")

    # Step 2: Check if config file exists
    if not auggie_config_path.exists():
        console.print(
            f"[yellow]⚠ No configuration found at {auggie_config_path}[/yellow]"
        )
        console.print("[dim]mcp-ticketer is not configured for Auggie[/dim]")
        return

    # Step 3: Load existing Auggie configuration
    auggie_config = load_auggie_config(auggie_config_path)

    # Step 4: Check if mcp-ticketer is configured
    if "mcp-ticketer" not in auggie_config.get("mcpServers", {}):
        console.print("[yellow]⚠ mcp-ticketer is not configured[/yellow]")
        console.print(f"[dim]No mcp-ticketer entry found in {auggie_config_path}[/dim]")
        return

    # Step 5: Show what would be removed (dry run or actual removal)
    if dry_run:
        console.print("\n[cyan]DRY RUN - Would remove:[/cyan]")
        console.print("  Server name: mcp-ticketer")
        console.print(f"  From: {auggie_config_path}")
        console.print("  Scope: Global (all projects)")
        return

    # Step 6: Remove mcp-ticketer from configuration
    del auggie_config["mcpServers"]["mcp-ticketer"]

    # Step 7: Save updated configuration
    try:
        save_auggie_config(auggie_config_path, auggie_config)
        console.print("\n[green]✓ Successfully removed mcp-ticketer[/green]")
        console.print(f"[dim]Configuration updated: {auggie_config_path}[/dim]")

        # Next steps
        console.print("\n[bold cyan]Next Steps:[/bold cyan]")
        console.print("1. Restart Auggie CLI for changes to take effect")
        console.print("2. mcp-ticketer will no longer be available via MCP")
        console.print(
            "\n[yellow]⚠ Note: This removes global configuration affecting all projects[/yellow]"
        )

    except Exception as e:
        console.print(f"\n[red]✗ Failed to update configuration:[/red] {e}")
        raise


def configure_auggie_mcp(force: bool = False) -> None:
    """Configure Auggie CLI to use mcp-ticketer.

    IMPORTANT: Auggie CLI ONLY supports global configuration.
    This will configure ~/.augment/settings.json for all projects.

    Args:
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
        ) from e

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
    project_path = str(Path.cwd())
    server_config = create_auggie_server_config(
        python_path=python_path,
        project_config=project_config,
        project_path=project_path,
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
        console.print(f"  Python: {python_path}")
        console.print("  Command: python -m mcp_ticketer.mcp.server")
        console.print("  Scope: Global (affects all projects)")
        console.print(f"  Project path: {project_path}")
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
