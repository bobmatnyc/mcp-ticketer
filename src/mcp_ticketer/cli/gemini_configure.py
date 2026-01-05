"""Gemini CLI configuration for mcp-ticketer integration."""

import json
from pathlib import Path
from typing import Literal

from rich.console import Console

from .mcp_configure import load_project_config
from .python_detection import get_mcp_ticketer_python
from .utils import CommonPatterns

console = Console()


def find_gemini_config(scope: Literal["project", "user"] = "project") -> Path:
    """Find or create Gemini CLI configuration file.

    Args:
        scope: Configuration scope - "project" for .gemini/settings.json
               or "user" for ~/.gemini/settings.json

    Returns:
        Path to Gemini settings file

    """
    if scope == "user":
        # User-level configuration
        config_path = Path.home() / ".gemini" / "settings.json"
    else:
        # Project-level configuration
        config_path = Path.cwd() / ".gemini" / "settings.json"

    return config_path


def load_gemini_config(config_path: Path) -> dict:
    """Load existing Gemini configuration or return empty structure.

    Args:
        config_path: Path to Gemini settings file

    Returns:
        Gemini configuration dict

    """
    if config_path.exists():
        try:
            with open(config_path) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            console.print(
                f"[yellow]⚠ Warning: Could not parse existing config: {e}[/yellow]"
            )
            console.print("[yellow]Creating new configuration...[/yellow]")

    # Return empty structure with mcpServers section
    return {"mcpServers": {}}


def save_gemini_config(config_path: Path, config: dict) -> None:
    """Save Gemini configuration to file.

    Args:
        config_path: Path to Gemini settings file
        config: Configuration to save

    """
    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write with 2-space indentation (Gemini CLI standard)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def create_gemini_server_config(
    python_path: str, project_config: dict, project_path: str | None = None
) -> dict:
    """Create Gemini MCP server configuration for mcp-ticketer.

    Uses the CLI command (mcp-ticketer mcp) which implements proper
    Content-Length framing via FastMCP SDK, required for modern MCP clients.

    Args:
        python_path: Path to Python executable in mcp-ticketer venv
        project_config: Project configuration from .mcp-ticketer/config.json
        project_path: Project directory path (optional)

    Returns:
        Gemini MCP server configuration dict

    """
    # IMPORTANT: Use CLI command, NOT Python module invocation
    # The CLI uses FastMCP SDK which implements proper Content-Length framing
    # Legacy python -m mcp_ticketer.mcp.server uses line-delimited JSON (incompatible)

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
        if project_path:
            # Use absolute path if project_path is provided
            env_vars["MCP_TICKETER_BASE_PATH"] = str(Path(project_path) / base_path)
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

    # Get mcp-ticketer CLI path using PATH resolution (reliable for all installations)
    cli_path = CommonPatterns.get_mcp_cli_path()

    # Build CLI arguments
    args = ["mcp"]
    if project_path:
        args.extend(["--path", project_path])

    # Create server configuration with Gemini-specific options
    # NOTE: Environment variables below are optional fallbacks
    # The CLI loads config from .mcp-ticketer/config.json
    config = {
        "command": cli_path,
        "args": args,
        "env": env_vars,
        "timeout": 15000,  # 15 seconds timeout
        "trust": False,  # Don't trust by default (security)
    }

    return config


def remove_gemini_mcp(
    scope: Literal["project", "user"] = "project", dry_run: bool = False
) -> None:
    """Remove mcp-ticketer from Gemini CLI configuration.

    Args:
        scope: Configuration scope - "project" or "user"
        dry_run: Show what would be removed without making changes

    """
    # Step 1: Find Gemini config location
    config_type = "user-level" if scope == "user" else "project-level"
    console.print(f"[cyan]🔍 Removing {config_type} Gemini CLI configuration...[/cyan]")

    gemini_config_path = find_gemini_config(scope)
    console.print(f"[dim]Config location: {gemini_config_path}[/dim]")

    # Step 2: Check if config file exists
    if not gemini_config_path.exists():
        console.print(
            f"[yellow]⚠ No configuration found at {gemini_config_path}[/yellow]"
        )
        console.print("[dim]mcp-ticketer is not configured for Gemini CLI[/dim]")
        return

    # Step 3: Load existing Gemini configuration
    gemini_config = load_gemini_config(gemini_config_path)

    # Step 4: Check if mcp-ticketer is configured
    if "mcp-ticketer" not in gemini_config.get("mcpServers", {}):
        console.print("[yellow]⚠ mcp-ticketer is not configured[/yellow]")
        console.print(f"[dim]No mcp-ticketer entry found in {gemini_config_path}[/dim]")
        return

    # Step 5: Show what would be removed (dry run or actual removal)
    if dry_run:
        console.print("\n[cyan]DRY RUN - Would remove:[/cyan]")
        console.print("  Server name: mcp-ticketer")
        console.print(f"  From: {gemini_config_path}")
        console.print(f"  Scope: {config_type}")
        return

    # Step 6: Remove mcp-ticketer from configuration
    del gemini_config["mcpServers"]["mcp-ticketer"]

    # Step 7: Save updated configuration
    try:
        save_gemini_config(gemini_config_path, gemini_config)
        console.print("\n[green]✓ Successfully removed mcp-ticketer[/green]")
        console.print(f"[dim]Configuration updated: {gemini_config_path}[/dim]")

        # Next steps
        console.print("\n[bold cyan]Next Steps:[/bold cyan]")
        if scope == "user":
            console.print("1. Gemini CLI global configuration updated")
            console.print("2. mcp-ticketer will no longer be available in any project")
        else:
            console.print("1. Gemini CLI project configuration updated")
            console.print("2. mcp-ticketer will no longer be available in this project")
        console.print("3. Restart Gemini CLI if currently running")

    except Exception as e:
        console.print(f"\n[red]✗ Failed to update configuration:[/red] {e}")
        raise


def configure_gemini_mcp(
    scope: Literal["project", "user"] = "project", force: bool = False
) -> None:
    """Configure Gemini CLI to use mcp-ticketer.

    Args:
        scope: Configuration scope - "project" or "user"
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

    # Step 3: Find Gemini config location
    config_type = "user-level" if scope == "user" else "project-level"
    console.print(f"\n[cyan]🔧 Configuring {config_type} Gemini CLI...[/cyan]")

    gemini_config_path = find_gemini_config(scope)
    console.print(f"[dim]Config location: {gemini_config_path}[/dim]")

    # Step 4: Load existing Gemini configuration
    gemini_config = load_gemini_config(gemini_config_path)

    # Step 5: Check if mcp-ticketer already configured
    if "mcp-ticketer" in gemini_config.get("mcpServers", {}):
        if not force:
            console.print("[yellow]⚠ mcp-ticketer is already configured[/yellow]")
            console.print("[dim]Use --force to overwrite existing configuration[/dim]")
            return
        else:
            console.print("[yellow]⚠ Overwriting existing configuration[/yellow]")

    # Step 6: Create mcp-ticketer server config
    project_path = str(Path.cwd()) if scope == "project" else None
    server_config = create_gemini_server_config(
        python_path=python_path,
        project_config=project_config,
        project_path=project_path,
    )

    # Step 7: Update Gemini configuration
    if "mcpServers" not in gemini_config:
        gemini_config["mcpServers"] = {}

    gemini_config["mcpServers"]["mcp-ticketer"] = server_config

    # Step 8: Save configuration
    try:
        save_gemini_config(gemini_config_path, gemini_config)
        console.print("\n[green]✓ Successfully configured mcp-ticketer[/green]")
        console.print(f"[dim]Configuration saved to: {gemini_config_path}[/dim]")

        # Print configuration details
        console.print("\n[bold]Configuration Details:[/bold]")
        console.print("  Server name: mcp-ticketer")
        console.print(f"  Adapter: {adapter}")
        console.print(f"  Python: {python_path}")
        console.print("  Command: python -m mcp_ticketer.mcp.server")
        console.print(f"  Timeout: {server_config['timeout']}ms")
        console.print(f"  Trust: {server_config['trust']}")
        if project_path:
            console.print(f"  Project path: {project_path}")
        if "env" in server_config:
            console.print(
                f"  Environment variables: {list(server_config['env'].keys())}"
            )

        # Next steps
        console.print("\n[bold cyan]Next Steps:[/bold cyan]")
        if scope == "user":
            console.print("1. Gemini CLI will use this configuration globally")
            console.print("2. Run 'gemini' command in any directory")
        else:
            console.print("1. Run 'gemini' command in this project directory")
            console.print("2. Gemini CLI will detect project-level configuration")
        console.print("3. mcp-ticketer tools will be available via MCP")

        # Add .gemini to .gitignore for project-level config
        if scope == "project":
            gitignore_path = Path.cwd() / ".gitignore"
            if gitignore_path.exists():
                gitignore_content = gitignore_path.read_text()
                if ".gemini" not in gitignore_content:
                    with open(gitignore_path, "a") as f:
                        f.write("\n# Gemini CLI\n.gemini/\n")
                    console.print("\n[dim]✓ Added .gemini/ to .gitignore[/dim]")
            else:
                # Create .gitignore if it doesn't exist
                with open(gitignore_path, "w") as f:
                    f.write("# Gemini CLI\n.gemini/\n")
                console.print("\n[dim]✓ Created .gitignore with .gemini/[/dim]")

    except Exception as e:
        console.print(f"\n[red]✗ Failed to save configuration:[/red] {e}")
        raise
