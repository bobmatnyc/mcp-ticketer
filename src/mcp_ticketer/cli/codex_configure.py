"""Codex CLI configuration for mcp-ticketer integration.

Codex CLI only supports global configuration at ~/.codex/config.toml.
Unlike Claude Code and Gemini CLI, there is no project-level configuration support.
"""

from pathlib import Path
from typing import Any

import tomli_w
import tomllib
from rich.console import Console

from .mcp_configure import load_project_config
from .python_detection import get_mcp_ticketer_python
from .utils import CommonPatterns

console = Console()


def find_codex_config() -> Path:
    """Find Codex CLI configuration file location.

    Codex CLI ONLY supports global configuration at ~/.codex/config.toml.
    No project-level or user-scoped configuration is available.

    Returns:
    -------
        Path to Codex global config file at ~/.codex/config.toml

    """
    # Codex only supports global config (no project-level support)
    config_path = Path.home() / ".codex" / "config.toml"
    return config_path


def load_codex_config(config_path: Path) -> dict[str, Any]:
    """Load existing Codex configuration or return empty structure.

    Args:
    ----
        config_path: Path to Codex config.toml file

    Returns:
    -------
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


def save_codex_config(config_path: Path, config: dict[str, Any]) -> None:
    """Save Codex configuration to TOML file.

    Args:
    ----
        config_path: Path to Codex config.toml file
        config: Configuration to save

    """
    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write TOML with proper formatting
    with open(config_path, "wb") as f:
        tomli_w.dump(config, f)


def create_codex_server_config(
    python_path: str, project_config: dict, project_path: str | None = None
) -> dict[str, Any]:
    """Create Codex MCP server configuration for mcp-ticketer.

    Uses the CLI command (mcp-ticketer mcp) which implements proper
    Content-Length framing via FastMCP SDK, required for modern MCP clients.

    Args:
    ----
        python_path: Path to Python executable in mcp-ticketer venv
        project_config: Project configuration from .mcp-ticketer/config.json
        project_path: Project directory path (optional)

    Returns:
    -------
        Codex MCP server configuration dict

    """
    # IMPORTANT: Use CLI command, NOT Python module invocation
    # The CLI uses FastMCP SDK which implements proper Content-Length framing
    # Legacy python -m mcp_ticketer.mcp.server uses line-delimited JSON (incompatible)

    # Get mcp-ticketer CLI path using PATH resolution (reliable for all installations)
    cli_path = CommonPatterns.get_mcp_cli_path()

    # Build CLI arguments
    args = ["mcp"]
    if project_path:
        args.extend(["--path", project_path])

    # Create server configuration with Codex-specific structure
    # No environment variables needed - config loaded from .mcp-ticketer/config.json
    config: dict[str, Any] = {
        "command": cli_path,
        "args": args,
    }

    return config


def _test_configuration(adapter: str, project_config: dict) -> bool:
    """Test the configuration by validating adapter credentials.

    Args:
    ----
        adapter: Adapter type (linear, github, jira, aitrackdown)
        project_config: Project configuration dict

    Returns:
    -------
        True if validation passed, False otherwise

    """
    try:
        from ..core import AdapterRegistry

        # Get adapter configuration
        adapters_config = project_config.get("adapters", {})
        adapter_config = adapters_config.get(adapter, {})

        # Test adapter instantiation
        console.print(f"  Testing {adapter} adapter...")

        try:
            adapter_instance = AdapterRegistry.get_adapter(adapter, adapter_config)
            console.print("  [green]✓[/green] Adapter instantiated successfully")

            # Test credentials if validation method exists
            if hasattr(adapter_instance, "validate_credentials"):
                console.print(f"  Validating {adapter} credentials...")
                is_valid, error_msg = adapter_instance.validate_credentials()

                if is_valid:
                    console.print("  [green]✓[/green] Credentials are valid")
                    return True
                else:
                    console.print(
                        f"  [red]✗[/red] Credential validation failed: {error_msg}"
                    )
                    return False
            else:
                # No validation method, assume valid
                console.print(
                    f"  [yellow]○[/yellow] No credential validation available for {adapter}"
                )
                return True

        except Exception as e:
            console.print(f"  [red]✗[/red] Adapter instantiation failed: {e}")

            # Provide helpful error messages based on adapter type
            if adapter == "linear":
                console.print(
                    "\n  [yellow]Linear requires:[/yellow] LINEAR_API_KEY and LINEAR_TEAM_ID"
                )
            elif adapter == "github":
                console.print(
                    "\n  [yellow]GitHub requires:[/yellow] GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO"
                )
            elif adapter == "jira":
                console.print(
                    "\n  [yellow]JIRA requires:[/yellow] JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN"
                )

            return False

    except Exception as e:
        console.print(f"  [red]✗[/red] Configuration test error: {e}")
        return False


def detect_legacy_config(config_path: Path) -> tuple[bool, dict[str, Any] | None]:
    """Detect if existing config uses legacy Python module invocation.

    Args:
    ----
        config_path: Path to Codex config.toml file

    Returns:
    -------
        Tuple of (is_legacy, server_config):
        - is_legacy: True if config uses 'python -m mcp_ticketer.mcp.server'
        - server_config: The legacy server config dict, or None if not legacy

    """
    if not config_path.exists():
        return False, None

    codex_config = load_codex_config(config_path)
    mcp_servers = codex_config.get("mcp_servers", {})

    if "mcp-ticketer" in mcp_servers:
        server_config = mcp_servers["mcp-ticketer"]
        args = server_config.get("args", [])

        # Check for legacy pattern: ["-m", "mcp_ticketer.mcp.server", ...]
        if len(args) >= 2 and args[0] == "-m" and "mcp_ticketer.mcp.server" in args[1]:
            return True, server_config

    return False, None


def remove_codex_mcp(dry_run: bool = False) -> None:
    """Remove mcp-ticketer from Codex CLI configuration.

    IMPORTANT: Codex CLI ONLY supports global configuration at ~/.codex/config.toml.
    This will remove mcp-ticketer from the global configuration.

    Args:
    ----
        dry_run: Show what would be removed without making changes

    """
    # Step 1: Find Codex config location (always global)
    console.print("[cyan]🔍 Removing Codex CLI global configuration...[/cyan]")
    console.print(
        "[yellow]⚠ Note: Codex CLI only supports global configuration[/yellow]"
    )

    codex_config_path = find_codex_config()
    console.print(f"[dim]Config location: {codex_config_path}[/dim]")

    # Step 2: Check if config file exists
    if not codex_config_path.exists():
        console.print(
            f"[yellow]⚠ No configuration found at {codex_config_path}[/yellow]"
        )
        console.print("[dim]mcp-ticketer is not configured for Codex CLI[/dim]")
        return

    # Step 3: Load existing Codex configuration
    codex_config = load_codex_config(codex_config_path)

    # Step 4: Check if mcp-ticketer is configured
    # NOTE: Use underscore mcp_servers, not camelCase
    mcp_servers = codex_config.get("mcp_servers", {})
    if "mcp-ticketer" not in mcp_servers:
        console.print("[yellow]⚠ mcp-ticketer is not configured[/yellow]")
        console.print(f"[dim]No mcp-ticketer entry found in {codex_config_path}[/dim]")
        return

    # Step 5: Show what would be removed (dry run or actual removal)
    if dry_run:
        console.print("\n[cyan]DRY RUN - Would remove:[/cyan]")
        console.print("  Server name: mcp-ticketer")
        console.print(f"  From: {codex_config_path}")
        console.print("  Scope: Global (all sessions)")
        return

    # Step 6: Remove mcp-ticketer from configuration
    del codex_config["mcp_servers"]["mcp-ticketer"]

    # Step 7: Save updated configuration
    try:
        save_codex_config(codex_config_path, codex_config)
        console.print("\n[green]✓ Successfully removed mcp-ticketer[/green]")
        console.print(f"[dim]Configuration updated: {codex_config_path}[/dim]")

        # Next steps
        console.print("\n[bold cyan]Next Steps:[/bold cyan]")
        console.print("1. [bold]Restart Codex CLI[/bold] (required for changes)")
        console.print("2. mcp-ticketer will no longer be available via MCP")
        console.print(
            "\n[yellow]⚠ Note: This removes global configuration affecting all Codex sessions[/yellow]"
        )

    except Exception as e:
        console.print(f"\n[red]✗ Failed to update configuration:[/red] {e}")
        raise


def configure_codex_mcp(force: bool = False) -> None:
    """Configure Codex CLI to use mcp-ticketer.

    IMPORTANT: Codex CLI ONLY supports global configuration at ~/.codex/config.toml.
    There is no project-level or user-scoped configuration available.

    After configuration, you must restart Codex CLI for changes to take effect.

    Args:
    ----
        force: Overwrite existing configuration

    Raises:
    ------
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

    # Step 3: Find Codex config location (always global)
    console.print("\n[cyan]🔧 Configuring Codex CLI (global-only)...[/cyan]")
    console.print(
        "[yellow]⚠ Note: Codex CLI only supports global configuration[/yellow]"
    )

    codex_config_path = find_codex_config()
    console.print(f"[dim]Config location: {codex_config_path}[/dim]")

    # Step 3.5: Check for legacy configuration (DETECTION & MIGRATION)
    is_legacy, legacy_config = detect_legacy_config(codex_config_path)
    if is_legacy:
        console.print("\n[yellow]⚠ LEGACY CONFIGURATION DETECTED[/yellow]")
        console.print(
            "[yellow]Your current configuration uses the legacy line-delimited JSON server:[/yellow]"
        )
        console.print(f"[dim]  Command: {legacy_config.get('command')}[/dim]")
        console.print(f"[dim]  Args: {legacy_config.get('args')}[/dim]")
        console.print(
            "\n[red]This legacy server is incompatible with modern MCP clients (Codex, Claude Desktop/Code).[/red]"
        )
        console.print(
            "[red]The legacy server uses line-delimited JSON instead of Content-Length framing.[/red]"
        )
        console.print(
            "\n[cyan]✨ Automatically migrating to modern FastMCP-based server...[/cyan]"
        )
        force = True  # Auto-enable force mode for migration

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
            if not is_legacy:
                console.print("[yellow]⚠ Overwriting existing configuration[/yellow]")
            # If is_legacy, we already printed migration message above

    # Step 6: Create mcp-ticketer server config
    # For global config, include current working directory for context
    project_path = str(Path.cwd())
    server_config = create_codex_server_config(
        python_path=python_path,
        project_config=project_config,
        project_path=project_path,
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
        console.print(f"  Python: {python_path}")
        console.print(f"  Command: {server_config.get('command')}")
        console.print(f"  Args: {server_config.get('args')}")
        console.print("  Protocol: Content-Length framing (FastMCP SDK)")
        console.print("  Scope: global (Codex only supports global config)")
        console.print(f"  Project path: {project_path}")

        # Step 9: Test configuration
        console.print("\n[cyan]🧪 Testing configuration...[/cyan]")
        test_success = _test_configuration(adapter, project_config)

        if not test_success:
            console.print(
                "[yellow]⚠ Configuration saved but validation failed. "
                "Please check your credentials and settings.[/yellow]"
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
                "\n[cyan]This fixes MCP connection issues with Codex and other modern clients.[/cyan]"
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
