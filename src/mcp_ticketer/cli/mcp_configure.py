"""MCP configuration for Claude Code integration."""

import json
import os
import subprocess
import sys
from pathlib import Path

from rich.console import Console

from .python_detection import get_mcp_ticketer_python

console = Console()


def is_claude_cli_available() -> bool:
    """Check if Claude CLI is available in PATH.

    Returns:
        True if 'claude' command is available, False otherwise

    """
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return False


def build_claude_mcp_command(
    project_config: dict,
    project_path: str | None = None,
    global_config: bool = False,
) -> list[str]:
    """Build 'claude mcp add' command arguments.

    Args:
        project_config: Project configuration dict
        project_path: Path to project (for --path arg)
        global_config: If True, use --scope user (global), else --scope local

    Returns:
        List of command arguments for subprocess

    """
    cmd = ["claude", "mcp", "add"]

    # Scope: user (global) or local (project)
    scope = "user" if global_config else "local"
    cmd.extend(["--scope", scope])

    # Transport: always stdio
    cmd.extend(["--transport", "stdio"])

    # Environment variables (credentials)
    adapters = project_config.get("adapters", {})

    # Linear adapter
    if "linear" in adapters:
        linear_config = adapters["linear"]
        if "api_key" in linear_config:
            cmd.extend(["--env", f"LINEAR_API_KEY={linear_config['api_key']}"])
        if "team_id" in linear_config:
            cmd.extend(["--env", f"LINEAR_TEAM_ID={linear_config['team_id']}"])
        if "team_key" in linear_config:
            cmd.extend(["--env", f"LINEAR_TEAM_KEY={linear_config['team_key']}"])

    # GitHub adapter
    if "github" in adapters:
        github_config = adapters["github"]
        if "token" in github_config:
            cmd.extend(["--env", f"GITHUB_TOKEN={github_config['token']}"])
        if "owner" in github_config:
            cmd.extend(["--env", f"GITHUB_OWNER={github_config['owner']}"])
        if "repo" in github_config:
            cmd.extend(["--env", f"GITHUB_REPO={github_config['repo']}"])

    # JIRA adapter
    if "jira" in adapters:
        jira_config = adapters["jira"]
        if "api_token" in jira_config:
            cmd.extend(["--env", f"JIRA_API_TOKEN={jira_config['api_token']}"])
        if "email" in jira_config:
            cmd.extend(["--env", f"JIRA_EMAIL={jira_config['email']}"])
        if "url" in jira_config:
            cmd.extend(["--env", f"JIRA_URL={jira_config['url']}"])

    # Add default adapter
    default_adapter = project_config.get("default_adapter", "aitrackdown")
    cmd.extend(["--env", f"MCP_TICKETER_ADAPTER={default_adapter}"])

    # Server label
    cmd.append("mcp-ticketer")

    # Command separator
    cmd.append("--")

    # Server command and args
    cmd.extend(["mcp-ticketer", "mcp"])

    # Project path (for local scope)
    if project_path and not global_config:
        cmd.extend(["--path", project_path])

    return cmd


def configure_claude_mcp_native(
    project_config: dict,
    project_path: str | None = None,
    global_config: bool = False,
    force: bool = False,
) -> None:
    """Configure Claude Code using native 'claude mcp add' command.

    Args:
        project_config: Project configuration dict
        project_path: Path to project directory
        global_config: If True, install globally (--scope user)
        force: If True, force reinstallation by removing existing config first

    Raises:
        RuntimeError: If claude mcp add command fails
        subprocess.TimeoutExpired: If command times out

    """
    # Auto-remove before re-adding when force=True
    if force:
        console.print("[cyan]🗑️  Force mode: Removing existing configuration...[/cyan]")
        try:
            removal_success = remove_claude_mcp_native(
                global_config=global_config, dry_run=False
            )
            if removal_success:
                console.print("[green]✓[/green] Existing configuration removed")
            else:
                console.print(
                    "[yellow]⚠[/yellow] Could not remove existing configuration"
                )
                console.print("[yellow]Proceeding with installation anyway...[/yellow]")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Removal error: {e}")
            console.print("[yellow]Proceeding with installation anyway...[/yellow]")

        console.print()  # Blank line for visual separation

    # Build command
    cmd = build_claude_mcp_command(
        project_config=project_config,
        project_path=project_path,
        global_config=global_config,
    )

    # Show command to user (mask sensitive values)
    masked_cmd = []
    for i, arg in enumerate(cmd):
        if arg.startswith("--env=") or (i > 0 and cmd[i - 1] == "--env"):
            # Mask environment variable values
            if "=" in arg:
                key, _ = arg.split("=", 1)
                masked_cmd.append(f"{key}=***")
            else:
                masked_cmd.append(arg)
        else:
            masked_cmd.append(arg)

    console.print(f"[cyan]Executing:[/cyan] {' '.join(masked_cmd)}")

    try:
        # Execute native command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            scope_label = (
                "globally" if global_config else f"for project: {project_path}"
            )
            console.print(f"[green]✓[/green] Claude Code configured {scope_label}")
            console.print("[dim]Restart Claude Code to load the MCP server[/dim]")

            # Show adapter information
            adapter = project_config.get("default_adapter", "aitrackdown")
            console.print("\n[bold]Configuration Details:[/bold]")
            console.print("  Server name: mcp-ticketer")
            console.print(f"  Adapter: {adapter}")
            console.print("  Protocol: Content-Length framing (FastMCP SDK)")
            if project_path and not global_config:
                console.print(f"  Project path: {project_path}")

            # Next steps
            console.print("\n[bold cyan]Next Steps:[/bold cyan]")
            if global_config:
                console.print("1. Restart Claude Desktop")
                console.print("2. Open a conversation")
            else:
                console.print("1. Restart Claude Code")
                console.print("2. Open this project in Claude Code")
            console.print("3. mcp-ticketer tools will be available in the MCP menu")
        else:
            console.print("[red]✗[/red] Failed to configure Claude Code")
            console.print(f"[red]Error:[/red] {result.stderr}")
            raise RuntimeError(f"claude mcp add failed: {result.stderr}")

    except subprocess.TimeoutExpired:
        console.print("[red]✗[/red] Claude CLI command timed out")
        raise
    except Exception as e:
        console.print(f"[red]✗[/red] Error executing Claude CLI: {e}")
        raise


def load_env_file(env_path: Path) -> dict[str, str]:
    """Load environment variables from .env file.

    Args:
        env_path: Path to .env file

    Returns:
        Dict of environment variable key-value pairs

    """
    env_vars: dict[str, str] = {}
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

    Uses the CLI command (mcp-ticketer mcp) which implements proper
    Content-Length framing via FastMCP SDK, required for modern MCP clients.

    Args:
        python_path: Path to Python executable in mcp-ticketer venv
        project_config: Project configuration from .mcp-ticketer/config.json
        project_path: Project directory path (optional)
        is_global_config: If True, create config for global location (no project path in args)

    Returns:
        MCP server configuration dict matching Claude Code stdio pattern

    """
    # IMPORTANT: Use CLI command, NOT Python module invocation
    # The CLI uses FastMCP SDK which implements proper Content-Length framing
    # Legacy python -m mcp_ticketer.mcp.server uses line-delimited JSON (incompatible)

    # Get mcp-ticketer CLI path from Python path
    # If python_path is /path/to/venv/bin/python, CLI is /path/to/venv/bin/mcp-ticketer
    python_dir = Path(python_path).parent
    cli_path = str(python_dir / "mcp-ticketer")

    # Build CLI arguments
    args = ["mcp"]

    # Add project path if provided and not global config
    if project_path and not is_global_config:
        args.extend(["--path", project_path])

    # REQUIRED: Add "type": "stdio" for Claude Code compatibility
    config = {
        "type": "stdio",
        "command": cli_path,
        "args": args,
    }

    # NOTE: The CLI command loads configuration from .mcp-ticketer/config.json
    # Environment variables below are optional fallbacks for backward compatibility
    # The FastMCP SDK server will automatically load config from the project directory

    adapter = project_config.get("default_adapter", "aitrackdown")
    adapters_config = project_config.get("adapters", {})
    adapter_config = adapters_config.get(adapter, {})

    env_vars = {}

    # Add PYTHONPATH for project context (only for project-specific configs)
    if project_path and not is_global_config:
        env_vars["PYTHONPATH"] = project_path

    # Add MCP_TICKETER_ADAPTER to identify which adapter to use (optional fallback)
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


def detect_legacy_claude_config(
    config_path: Path, is_claude_code: bool = True, project_path: str | None = None
) -> tuple[bool, dict | None]:
    """Detect if existing Claude config uses legacy Python module invocation.

    Args:
    ----
        config_path: Path to Claude configuration file
        is_claude_code: Whether this is Claude Code (project-level) or Claude Desktop (global)
        project_path: Project path for Claude Code configs

    Returns:
    -------
        Tuple of (is_legacy, server_config):
        - is_legacy: True if config uses 'python -m mcp_ticketer.mcp.server'
        - server_config: The legacy server config dict, or None if not legacy

    """
    if not config_path.exists():
        return False, None

    try:
        mcp_config = load_claude_mcp_config(config_path, is_claude_code=is_claude_code)
    except Exception:
        return False, None

    # For Claude Code, check project-specific config
    if is_claude_code and project_path:
        projects = mcp_config.get("projects", {})
        project_config = projects.get(project_path, {})
        mcp_servers = project_config.get("mcpServers", {})
    else:
        # For Claude Desktop, check global config
        mcp_servers = mcp_config.get("mcpServers", {})

    if "mcp-ticketer" in mcp_servers:
        server_config = mcp_servers["mcp-ticketer"]
        args = server_config.get("args", [])

        # Check for legacy pattern: ["-m", "mcp_ticketer.mcp.server", ...]
        if len(args) >= 2 and args[0] == "-m" and "mcp_ticketer.mcp.server" in args[1]:
            return True, server_config

    return False, None


def remove_claude_mcp_native(
    global_config: bool = False,
    dry_run: bool = False,
) -> bool:
    """Remove mcp-ticketer using native 'claude mcp remove' command.

    This function attempts to use the Claude CLI's native remove command
    first, falling back to JSON manipulation if the native command fails.

    Args:
        global_config: If True, remove from Claude Desktop (--scope user)
                      If False, remove from Claude Code (--scope local)
        dry_run: If True, only show what would be removed without making changes

    Returns:
        bool: True if removal was successful, False if failed or skipped

    Raises:
        Does not raise exceptions - all errors are caught and handled gracefully
        with fallback to JSON manipulation

    Example:
        >>> # Remove from local Claude Code configuration
        >>> remove_claude_mcp_native(global_config=False, dry_run=False)
        True

        >>> # Preview removal without making changes
        >>> remove_claude_mcp_native(global_config=False, dry_run=True)
        True

    Notes:
        - Automatically falls back to remove_claude_mcp_json() if native fails
        - Designed to be non-blocking for auto-remove scenarios
        - Uses --scope flag for backward compatibility with Claude CLI

    """
    scope = "user" if global_config else "local"
    cmd = ["claude", "mcp", "remove", "--scope", scope, "mcp-ticketer"]

    config_type = "Claude Desktop" if global_config else "Claude Code"

    if dry_run:
        console.print(f"[cyan]DRY RUN - Would execute:[/cyan] {' '.join(cmd)}")
        console.print(f"[dim]Target: {config_type}[/dim]")
        return True

    try:
        # Execute native remove command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            console.print("[green]✓[/green] Removed mcp-ticketer via native CLI")
            console.print(f"[dim]Target: {config_type}[/dim]")
            return True
        else:
            # Native command failed, fallback to JSON
            console.print(
                f"[yellow]⚠[/yellow] Native remove failed: {result.stderr.strip()}"
            )
            console.print(
                "[yellow]Falling back to JSON configuration removal...[/yellow]"
            )
            return remove_claude_mcp_json(global_config=global_config, dry_run=dry_run)

    except subprocess.TimeoutExpired:
        console.print("[yellow]⚠[/yellow] Native remove command timed out")
        console.print("[yellow]Falling back to JSON configuration removal...[/yellow]")
        return remove_claude_mcp_json(global_config=global_config, dry_run=dry_run)

    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Error executing native remove: {e}")
        console.print("[yellow]Falling back to JSON configuration removal...[/yellow]")
        return remove_claude_mcp_json(global_config=global_config, dry_run=dry_run)


def remove_claude_mcp_json(global_config: bool = False, dry_run: bool = False) -> bool:
    """Remove mcp-ticketer from Claude Code/Desktop configuration using JSON.

    This is a fallback method when native 'claude mcp remove' is unavailable
    or fails. It directly manipulates the JSON configuration files.

    Args:
        global_config: Remove from Claude Desktop instead of project-level
        dry_run: Show what would be removed without making changes

    Returns:
        bool: True if removal was successful (or files not found),
              False if an error occurred during JSON manipulation

    Notes:
        - Handles multiple config file locations (new, old, legacy)
        - Supports both flat and nested configuration structures
        - Cleans up empty structures after removal
        - Provides detailed logging of actions taken

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

    # Return True even if not found (successful removal)
    return True


def remove_claude_mcp(
    global_config: bool = False,
    dry_run: bool = False,
) -> bool:
    """Remove mcp-ticketer from Claude Code/Desktop configuration.

    Automatically detects if Claude CLI is available and uses the native
    'claude mcp remove' command if possible, falling back to JSON configuration
    manipulation when necessary.

    Args:
        global_config: Remove from Claude Desktop instead of project-level
        dry_run: Show what would be removed without making changes

    Returns:
        bool: True if removal was successful, False if failed

    Example:
        >>> # Remove from Claude Code (project-level)
        >>> remove_claude_mcp(global_config=False)
        True

        >>> # Remove from Claude Desktop (global)
        >>> remove_claude_mcp(global_config=True)
        True

    Notes:
        - Uses native CLI when available for better reliability
        - Automatically falls back to JSON manipulation if needed
        - Safe to call even if mcp-ticketer is not configured

    """
    # Check for native CLI availability
    if is_claude_cli_available():
        console.print("[green]✓[/green] Claude CLI found - using native remove command")
        return remove_claude_mcp_native(global_config=global_config, dry_run=dry_run)

    # Fall back to JSON manipulation
    console.print(
        "[yellow]⚠[/yellow] Claude CLI not found - using JSON configuration removal"
    )
    return remove_claude_mcp_json(global_config=global_config, dry_run=dry_run)


def configure_claude_mcp(global_config: bool = False, force: bool = False) -> None:
    """Configure Claude Code to use mcp-ticketer.

    Automatically detects if Claude CLI is available and uses native
    'claude mcp add' command if possible, falling back to JSON configuration.

    Args:
        global_config: Configure Claude Desktop instead of project-level
        force: Overwrite existing configuration

    Raises:
        FileNotFoundError: If Python executable or project config not found
        ValueError: If configuration is invalid

    """
    # Load project configuration early (needed for both native and JSON methods)
    console.print("[cyan]📖 Reading project configuration...[/cyan]")
    try:
        project_config = load_project_config()
        adapter = project_config.get("default_adapter", "aitrackdown")
        console.print(f"[green]✓[/green] Adapter: {adapter}")
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]✗[/red] {e}")
        raise

    # Check for native CLI availability
    console.print("\n[cyan]🔍 Checking for Claude CLI...[/cyan]")
    if is_claude_cli_available():
        console.print("[green]✓[/green] Claude CLI found - using native command")
        console.print(
            "[dim]This provides better integration and automatic updates[/dim]"
        )

        # Get absolute project path for local scope
        absolute_project_path = str(Path.cwd().resolve()) if not global_config else None

        return configure_claude_mcp_native(
            project_config=project_config,
            project_path=absolute_project_path,
            global_config=global_config,
            force=force,
        )

    # Fall back to JSON manipulation
    console.print(
        "[yellow]⚠[/yellow] Claude CLI not found - using legacy JSON configuration"
    )
    console.print(
        "[dim]For better experience, install Claude CLI: https://docs.claude.ai/cli[/dim]"
    )

    # Auto-remove before re-adding when force=True
    if force:
        console.print(
            "\n[cyan]🗑️  Force mode: Removing existing configuration...[/cyan]"
        )
        try:
            removal_success = remove_claude_mcp_json(
                global_config=global_config, dry_run=False
            )
            if removal_success:
                console.print("[green]✓[/green] Existing configuration removed")
            else:
                console.print(
                    "[yellow]⚠[/yellow] Could not remove existing configuration"
                )
                console.print("[yellow]Proceeding with installation anyway...[/yellow]")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Removal error: {e}")
            console.print("[yellow]Proceeding with installation anyway...[/yellow]")

        console.print()  # Blank line for visual separation

    # Determine project path for venv detection
    project_path = Path.cwd() if not global_config else None

    # Step 1: Find Python executable (project-specific if available)
    console.print("\n[cyan]🔍 Finding mcp-ticketer Python executable...[/cyan]")
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

    # Step 4.5: Check for legacy configuration (DETECTION & MIGRATION)
    is_legacy, legacy_config = detect_legacy_claude_config(
        mcp_config_path,
        is_claude_code=is_claude_code,
        project_path=absolute_project_path,
    )
    if is_legacy:
        console.print("\n[yellow]⚠ LEGACY CONFIGURATION DETECTED[/yellow]")
        console.print(
            "[yellow]Your current configuration uses the legacy line-delimited JSON server:[/yellow]"
        )
        console.print(f"[dim]  Command: {legacy_config.get('command')}[/dim]")
        console.print(f"[dim]  Args: {legacy_config.get('args')}[/dim]")
        console.print(
            f"\n[red]This legacy server is incompatible with modern MCP clients ({config_type}).[/red]"
        )
        console.print(
            "[red]The legacy server uses line-delimited JSON instead of Content-Length framing.[/red]"
        )
        console.print(
            "\n[cyan]✨ Automatically migrating to modern FastMCP-based server...[/cyan]"
        )
        force = True  # Auto-enable force mode for migration

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
        console.print(f"  Command: {server_config.get('command')}")
        console.print(f"  Args: {server_config.get('args')}")
        console.print("  Protocol: Content-Length framing (FastMCP SDK)")
        if absolute_project_path:
            console.print(f"  Project path: {absolute_project_path}")
        if "env" in server_config:
            console.print(
                f"  Environment variables: {list(server_config['env'].keys())}"
            )

        # Migration success message (if legacy config was detected)
        if is_legacy:
            console.print("\n[green]✅ Migration Complete![/green]")
            console.print(
                "[green]Your configuration has been upgraded from legacy line-delimited JSON[/green]"
            )
            console.print(
                "[green]to modern Content-Length framing (FastMCP SDK).[/green]"
            )
            console.print(
                f"\n[cyan]This fixes MCP connection issues with {config_type}.[/cyan]"
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
