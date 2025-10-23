"""Codex CLI configuration for mcp-ticketer integration.

Codex CLI only supports global configuration at ~/.codex/config.toml.
Unlike Claude Code and Gemini CLI, there is no project-level configuration support.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w
from rich.console import Console

from .mcp_configure import find_mcp_ticketer_binary, load_project_config

console = Console()


def find_codex_config() -> Path:
    """Find Codex CLI configuration file location.

    Codex CLI ONLY supports global configuration at ~/.codex/config.toml.
    No project-level or user-scoped configuration is available.

    Returns:
        Path to Codex global config file at ~/.codex/config.toml

    """
    # Codex only supports global config (no project-level support)
    config_path = Path.home() / ".codex" / "config.toml"
    return config_path


def load_codex_config(config_path: Path) -> Dict[str, Any]:
    """Load existing Codex configuration or return empty structure.

    Args:
        config_path: Path to Codex config.toml file

    Returns:
        Codex configuration dict with mcp_servers section

    """
    if config_path.exists():
        try:
            with open(config_path, "rb") as f:
                return tomllib.load(f)
        except Exception as e:
            console.print(
                f"[yellow]⚠ Warning: Could not parse existing config: {e}[/yellow]"
            )
            console.print("[yellow]Creating new configuration...[/yellow]")

    # Return empty structure with mcp_servers section
    # NOTE: Use underscore mcp_servers, not camelCase mcpServers
    return {"mcp_servers": {}}


def save_codex_config(config_path: Path, config: Dict[str, Any]) -> None:
    """Save Codex configuration to TOML file.

    Args:
        config_path: Path to Codex config.toml file
        config: Configuration to save

    """
    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write TOML with proper formatting
    with open(config_path, "wb") as f:
        tomli_w.dump(config, f)


def create_codex_server_config(
    binary_path: str, project_config: dict, cwd: Optional[str] = None
) -> Dict[str, Any]:
    """Create Codex MCP server configuration for mcp-ticketer.

    Args:
        binary_path: Path to mcp-ticketer binary
        project_config: Project configuration from .mcp-ticketer/config.json
        cwd: Working directory for server (optional, not used for global config)

    Returns:
        Codex MCP server configuration dict

    """
    # Get adapter configuration
    adapter = project_config.get("default_adapter", "aitrackdown")
    adapters_config = project_config.get("adapters", {})
    adapter_config = adapters_config.get(adapter, {})

    # Build environment variables
    env_vars: Dict[str, str] = {}

    # Add PYTHONPATH if running from development environment
    if cwd:
        env_vars["PYTHONPATH"] = str(Path(cwd) / "src")

    # Add adapter type
    env_vars["MCP_TICKETER_ADAPTER"] = adapter

    # Add adapter-specific environment variables
    if adapter == "aitrackdown":
        # Set base path for local adapter
        base_path = adapter_config.get("base_path", ".aitrackdown")
        if cwd:
            # Use absolute path if cwd is provided
            env_vars["MCP_TICKETER_BASE_PATH"] = str(Path(cwd) / base_path)
        else:
            env_vars["MCP_TICKETER_BASE_PATH"] = base_path

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

    # Create server configuration with Codex-specific structure
    # NOTE: Codex uses nested dict structure for env vars
    config: Dict[str, Any] = {
        "command": binary_path,
        "args": ["serve"],
        "env": env_vars,
    }

    return config


def configure_codex_mcp(force: bool = False) -> None:
    """Configure Codex CLI to use mcp-ticketer.

    IMPORTANT: Codex CLI ONLY supports global configuration at ~/.codex/config.toml.
    There is no project-level or user-scoped configuration available.

    After configuration, you must restart Codex CLI for changes to take effect.

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

    # Step 3: Find Codex config location (always global)
    console.print("\n[cyan]🔧 Configuring Codex CLI (global-only)...[/cyan]")
    console.print(
        "[yellow]⚠ Note: Codex CLI only supports global configuration[/yellow]"
    )

    codex_config_path = find_codex_config()
    console.print(f"[dim]Config location: {codex_config_path}[/dim]")

    # Step 4: Load existing Codex configuration
    codex_config = load_codex_config(codex_config_path)

    # Step 5: Check if mcp-ticketer already configured
    # NOTE: Use underscore mcp_servers, not camelCase
    mcp_servers = codex_config.get("mcp_servers", {})
    if "mcp-ticketer" in mcp_servers:
        if not force:
            console.print("[yellow]⚠ mcp-ticketer is already configured[/yellow]")
            console.print("[dim]Use --force to overwrite existing configuration[/dim]")
            return
        else:
            console.print("[yellow]⚠ Overwriting existing configuration[/yellow]")

    # Step 6: Create mcp-ticketer server config
    # For global config, include current working directory for context
    cwd = str(Path.cwd())
    server_config = create_codex_server_config(
        binary_path=binary_path, project_config=project_config, cwd=cwd
    )

    # Step 7: Update Codex configuration
    if "mcp_servers" not in codex_config:
        codex_config["mcp_servers"] = {}

    codex_config["mcp_servers"]["mcp-ticketer"] = server_config

    # Step 8: Save configuration
    try:
        save_codex_config(codex_config_path, codex_config)
        console.print("\n[green]✓ Successfully configured mcp-ticketer[/green]")
        console.print(f"[dim]Configuration saved to: {codex_config_path}[/dim]")

        # Print configuration details
        console.print("\n[bold]Configuration Details:[/bold]")
        console.print("  Server name: mcp-ticketer")
        console.print(f"  Adapter: {adapter}")
        console.print(f"  Binary: {binary_path}")
        console.print("  Scope: global (Codex only supports global config)")
        console.print(f"  Working directory: {cwd}")
        if "env" in server_config:
            console.print(
                f"  Environment variables: {list(server_config['env'].keys())}"
            )

        # Next steps
        console.print("\n[bold cyan]Next Steps:[/bold cyan]")
        console.print("1. [bold]Restart Codex CLI[/bold] (required for changes)")
        console.print("2. Run 'codex' command from any directory")
        console.print("3. mcp-ticketer tools will be available via MCP")
        console.print(
            "\n[yellow]⚠ Warning: This is a global configuration that affects all Codex sessions[/yellow]"
        )
        console.print(
            "[yellow]   The configuration includes paths from your current project directory[/yellow]"
        )

    except Exception as e:
        console.print(f"\n[red]✗ Failed to save configuration:[/red] {e}")
        raise
