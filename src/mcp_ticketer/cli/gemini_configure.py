"""Gemini CLI configuration for mcp-ticketer integration."""

import json
from pathlib import Path
from typing import Literal, Optional

from rich.console import Console

from .mcp_configure import find_mcp_ticketer_binary, load_project_config

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
    binary_path: str, project_config: dict, cwd: Optional[str] = None
) -> dict:
    """Create Gemini MCP server configuration for mcp-ticketer.

    Args:
        binary_path: Path to mcp-ticketer binary
        project_config: Project configuration from .mcp-ticketer/config.json
        cwd: Working directory for server (optional)

    Returns:
        Gemini MCP server configuration dict

    """
    # Get adapter configuration
    adapter = project_config.get("default_adapter", "aitrackdown")
    adapters_config = project_config.get("adapters", {})
    adapter_config = adapters_config.get(adapter, {})

    # Build environment variables
    env_vars = {}

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

    # Create server configuration with Gemini-specific options
    config = {
        "command": binary_path,
        "args": ["serve"],
        "env": env_vars,
        "timeout": 15000,  # 15 seconds timeout
        "trust": False,  # Don't trust by default (security)
    }

    return config


def configure_gemini_mcp(
    scope: Literal["project", "user"] = "project", force: bool = False
) -> None:
    """Configure Gemini CLI to use mcp-ticketer.

    Args:
        scope: Configuration scope - "project" or "user"
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
    cwd = str(Path.cwd()) if scope == "project" else None
    server_config = create_gemini_server_config(
        binary_path=binary_path, project_config=project_config, cwd=cwd
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
        console.print(f"  Binary: {binary_path}")
        console.print(f"  Timeout: {server_config['timeout']}ms")
        console.print(f"  Trust: {server_config['trust']}")
        if cwd:
            console.print(f"  Working directory: {cwd}")
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
