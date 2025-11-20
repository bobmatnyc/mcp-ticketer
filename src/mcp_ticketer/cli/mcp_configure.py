"""MCP configuration for Claude Code integration."""

import json
import os
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
        # Claude Code configuration - check both locations
        # Priority 1: New global location ~/.config/claude/mcp.json
        new_config_path = Path.home() / ".config" / "claude" / "mcp.json"
        if new_config_path.exists():
            return new_config_path

        # Priority 2: Legacy project-specific location ~/.claude.json
        config_path = Path.home() / ".claude.json"

    return config_path


def load_claude_mcp_config(config_path: Path, is_claude_code: bool = False) -> dict:
    """Load existing Claude MCP configuration or return empty structure.

    Args:
        config_path: Path to MCP config file
        is_claude_code: If True, return Claude Code structure with projects

    Returns:
        MCP configuration dict

    """
    # Detect if this is the new global config location
    is_global_mcp_config = str(config_path).endswith(".config/claude/mcp.json")

    if config_path.exists():
        try:
            with open(config_path) as f:
                content = f.read().strip()
                if not content:
                    # Empty file, return default structure based on location
                    if is_global_mcp_config:
                        return {"mcpServers": {}}  # Flat structure
                    return {"projects": {}} if is_claude_code else {"mcpServers": {}}

                config = json.loads(content)

                # Auto-detect structure format based on content
                if "projects" in config:
                    # This is the old nested project structure
                    return config
                elif "mcpServers" in config:
                    # This is flat mcpServers structure
                    return config
                else:
                    # Empty or unknown structure, return default
                    if is_global_mcp_config:
                        return {"mcpServers": {}}
                    return {"projects": {}} if is_claude_code else {"mcpServers": {}}

        except json.JSONDecodeError as e:
            console.print(
                f"[yellow]⚠ Warning: Invalid JSON in {config_path}, creating new config[/yellow]"
            )
            console.print(f"[dim]Error: {e}[/dim]")
            # Return default structure on parse error
            if is_global_mcp_config:
                return {"mcpServers": {}}
            return {"projects": {}} if is_claude_code else {"mcpServers": {}}

    # Return empty structure based on config type and location
    if is_global_mcp_config:
        return {"mcpServers": {}}  # New location always uses flat structure
    if is_claude_code:
        return {"projects": {}}
    else:
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
    python_path: str,
    project_config: dict,
    project_path: str | None = None,
    is_global_config: bool = False,
) -> dict:
    """Create MCP server configuration for mcp-ticketer.

    Args:
        python_path: Path to Python executable in mcp-ticketer venv
        project_config: Project configuration from .mcp-ticketer/config.json
        project_path: Project directory path (optional)
        is_global_config: If True, create config for global location (no project path in args)

    Returns:
        MCP server configuration dict matching Claude Code stdio pattern

    """
    # Use Python module invocation pattern (works regardless of where package is installed)
    args = ["-m", "mcp_ticketer.mcp.server"]

    # Add project path if provided and not global config
    if project_path and not is_global_config:
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

    # Add PYTHONPATH for project context (only for project-specific configs)
    if project_path and not is_global_config:
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
    config_type = "Claude Desktop" if global_config else "Claude Code"
    console.print(f"[cyan]🔍 Removing {config_type} MCP configuration...[/cyan]")

    # Get absolute project path for Claude Code
    absolute_project_path = str(Path.cwd().resolve()) if not global_config else None

    # Check both locations for Claude Code
    config_paths_to_check = []
    if not global_config:
        # Check both new and old locations
        new_config = Path.home() / ".config" / "claude" / "mcp.json"
        old_config = Path.home() / ".claude.json"
        legacy_config = Path.cwd() / ".claude" / "mcp.local.json"

        if new_config.exists():
            config_paths_to_check.append(
                (new_config, True)
            )  # True = is_global_mcp_config
        if old_config.exists():
            config_paths_to_check.append((old_config, False))
        if legacy_config.exists():
            config_paths_to_check.append((legacy_config, False))
    else:
        mcp_config_path = find_claude_mcp_config(global_config)
        if mcp_config_path.exists():
            config_paths_to_check.append((mcp_config_path, False))

    if not config_paths_to_check:
        console.print("[yellow]⚠ No configuration files found[/yellow]")
        console.print("[dim]mcp-ticketer is not configured for this platform[/dim]")
        return

    # Step 2-7: Process each config file
    removed_count = 0
    for config_path, is_global_mcp_config in config_paths_to_check:
        console.print(f"[dim]Checking: {config_path}[/dim]")

        # Load existing MCP configuration
        is_claude_code = not global_config
        mcp_config = load_claude_mcp_config(config_path, is_claude_code=is_claude_code)

        # Check if mcp-ticketer is configured
        is_configured = False
        if is_global_mcp_config:
            # Global mcp.json uses flat structure
            is_configured = "mcp-ticketer" in mcp_config.get("mcpServers", {})
        elif is_claude_code:
            # Check Claude Code structure: .projects[path].mcpServers["mcp-ticketer"]
            if absolute_project_path:
                projects = mcp_config.get("projects", {})
                project_config_entry = projects.get(absolute_project_path, {})
                is_configured = "mcp-ticketer" in project_config_entry.get(
                    "mcpServers", {}
                )
            else:
                # Check flat structure for backward compatibility
                is_configured = "mcp-ticketer" in mcp_config.get("mcpServers", {})
        else:
            # Check Claude Desktop structure: .mcpServers["mcp-ticketer"]
            is_configured = "mcp-ticketer" in mcp_config.get("mcpServers", {})

        if not is_configured:
            continue

        # Show what would be removed (dry run)
        if dry_run:
            console.print(f"\n[cyan]DRY RUN - Would remove from: {config_path}[/cyan]")
            console.print("  Server name: mcp-ticketer")
            if absolute_project_path and not is_global_mcp_config:
                console.print(f"  Project: {absolute_project_path}")
            continue

        # Remove mcp-ticketer from configuration
        if is_global_mcp_config:
            # Global mcp.json uses flat structure
            del mcp_config["mcpServers"]["mcp-ticketer"]
        elif is_claude_code and absolute_project_path and "projects" in mcp_config:
            # Remove from Claude Code nested structure
            del mcp_config["projects"][absolute_project_path]["mcpServers"][
                "mcp-ticketer"
            ]

            # Clean up empty structures
            if not mcp_config["projects"][absolute_project_path]["mcpServers"]:
                del mcp_config["projects"][absolute_project_path]["mcpServers"]
            if not mcp_config["projects"][absolute_project_path]:
                del mcp_config["projects"][absolute_project_path]
        else:
            # Remove from flat structure (legacy or Claude Desktop)
            if "mcp-ticketer" in mcp_config.get("mcpServers", {}):
                del mcp_config["mcpServers"]["mcp-ticketer"]

        # Save updated configuration
        try:
            save_claude_mcp_config(config_path, mcp_config)
            console.print(f"[green]✓ Removed from: {config_path}[/green]")
            removed_count += 1
        except Exception as e:
            console.print(f"[red]✗ Failed to update {config_path}:[/red] {e}")

    if dry_run:
        return

    if removed_count > 0:
        console.print("\n[green]✓ Successfully removed mcp-ticketer[/green]")
        console.print(f"[dim]Updated {removed_count} configuration file(s)[/dim]")

        # Next steps
        console.print("\n[bold cyan]Next Steps:[/bold cyan]")
        if global_config:
            console.print("1. Restart Claude Desktop")
            console.print("2. mcp-ticketer will no longer be available in MCP menu")
        else:
            console.print("1. Restart Claude Code")
            console.print("2. mcp-ticketer will no longer be available in this project")
    else:
        console.print(
            "\n[yellow]⚠ mcp-ticketer was not found in any configuration[/yellow]"
        )


def configure_claude_mcp(global_config: bool = False, force: bool = False) -> None:
    """Configure Claude Code to use mcp-ticketer.

    Args:
        global_config: Configure Claude Desktop instead of project-level
        force: Overwrite existing configuration

    Raises:
        FileNotFoundError: If Python executable or project config not found
        ValueError: If configuration is invalid

    """
    # Determine project path for venv detection
    project_path = Path.cwd() if not global_config else None

    # Step 1: Find Python executable (project-specific if available)
    console.print("[cyan]🔍 Finding mcp-ticketer Python executable...[/cyan]")
    try:
        python_path = get_mcp_ticketer_python(project_path=project_path)
        console.print(f"[green]✓[/green] Found: {python_path}")

        # Show if using project venv or fallback
        if project_path and str(project_path / ".venv") in python_path:
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
        project_config = load_project_config()
        adapter = project_config.get("default_adapter", "aitrackdown")
        console.print(f"[green]✓[/green] Adapter: {adapter}")
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]✗[/red] {e}")
        raise

    # Step 3: Find Claude MCP config location
    config_type = "Claude Desktop" if global_config else "Claude Code"
    console.print(f"\n[cyan]🔧 Configuring {config_type} MCP...[/cyan]")

    mcp_config_path = find_claude_mcp_config(global_config)
    console.print(f"[dim]Primary config: {mcp_config_path}[/dim]")

    # Get absolute project path for Claude Code
    absolute_project_path = str(Path.cwd().resolve()) if not global_config else None

    # Step 4: Load existing MCP configuration
    is_claude_code = not global_config
    mcp_config = load_claude_mcp_config(mcp_config_path, is_claude_code=is_claude_code)

    # Detect if using new global config location
    is_global_mcp_config = str(mcp_config_path).endswith(".config/claude/mcp.json")

    # Step 5: Check if mcp-ticketer already configured
    already_configured = False
    if is_global_mcp_config:
        # New global config uses flat structure
        already_configured = "mcp-ticketer" in mcp_config.get("mcpServers", {})
    elif is_claude_code:
        # Check Claude Code structure: .projects[path].mcpServers["mcp-ticketer"]
        if absolute_project_path and "projects" in mcp_config:
            projects = mcp_config.get("projects", {})
            project_config_entry = projects.get(absolute_project_path, {})
            already_configured = "mcp-ticketer" in project_config_entry.get(
                "mcpServers", {}
            )
        elif "mcpServers" in mcp_config:
            # Check flat structure for backward compatibility
            already_configured = "mcp-ticketer" in mcp_config.get("mcpServers", {})
    else:
        # Check Claude Desktop structure: .mcpServers["mcp-ticketer"]
        already_configured = "mcp-ticketer" in mcp_config.get("mcpServers", {})

    if already_configured:
        if not force:
            console.print("[yellow]⚠ mcp-ticketer is already configured[/yellow]")
            console.print("[dim]Use --force to overwrite existing configuration[/dim]")
            return
        else:
            console.print("[yellow]⚠ Overwriting existing configuration[/yellow]")

    # Step 6: Create mcp-ticketer server config
    server_config = create_mcp_server_config(
        python_path=python_path,
        project_config=project_config,
        project_path=absolute_project_path,
        is_global_config=is_global_mcp_config,
    )

    # Step 7: Update MCP configuration based on platform
    if is_global_mcp_config:
        # New global location: ~/.config/claude/mcp.json uses flat structure
        if "mcpServers" not in mcp_config:
            mcp_config["mcpServers"] = {}
        mcp_config["mcpServers"]["mcp-ticketer"] = server_config
    elif is_claude_code:
        # Claude Code: Write to ~/.claude.json with project-specific path
        if absolute_project_path:
            # Ensure projects structure exists
            if "projects" not in mcp_config:
                mcp_config["projects"] = {}

            # Ensure project entry exists
            if absolute_project_path not in mcp_config["projects"]:
                mcp_config["projects"][absolute_project_path] = {}

            # Ensure mcpServers for this project exists
            if "mcpServers" not in mcp_config["projects"][absolute_project_path]:
                mcp_config["projects"][absolute_project_path]["mcpServers"] = {}

            # Add mcp-ticketer configuration
            mcp_config["projects"][absolute_project_path]["mcpServers"][
                "mcp-ticketer"
            ] = server_config

            # Also write to backward-compatible location for older Claude Code versions
            legacy_config_path = Path.cwd() / ".claude" / "mcp.local.json"
            console.print(f"[dim]Legacy config: {legacy_config_path}[/dim]")

            try:
                legacy_config = load_claude_mcp_config(
                    legacy_config_path, is_claude_code=False
                )
                if "mcpServers" not in legacy_config:
                    legacy_config["mcpServers"] = {}
                legacy_config["mcpServers"]["mcp-ticketer"] = server_config
                save_claude_mcp_config(legacy_config_path, legacy_config)
                console.print("[dim]✓ Backward-compatible config also written[/dim]")
            except Exception as e:
                console.print(
                    f"[dim]⚠ Could not write legacy config (non-fatal): {e}[/dim]"
                )
    else:
        # Claude Desktop: Write to platform-specific config
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
        console.print("  Command: python -m mcp_ticketer.mcp.server")
        if absolute_project_path:
            console.print(f"  Project path: {absolute_project_path}")
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
