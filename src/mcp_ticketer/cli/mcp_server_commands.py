"""MCP server management commands for mcp-ticketer."""

import json
import sys
from pathlib import Path

import typer
from rich.console import Console

console = Console()

# Create MCP configuration command group
mcp_app = typer.Typer(
    name="mcp",
    help="Configure MCP integration for AI clients (Claude, Gemini, Codex, Auggie)",
    add_completion=False,
    invoke_without_command=True,
)


@mcp_app.callback()
def mcp_callback(
    ctx: typer.Context,
    project_path: str | None = typer.Option(
        None, "--path", "-p", help="Project directory path (default: current directory)"
    ),
) -> None:
    """MCP command group - runs MCP server if no subcommand provided.

    Examples:
    --------
        mcp-ticketer mcp              # Start server in current directory
        mcp-ticketer mcp --path /dir  # Start server in specific directory
        mcp-ticketer mcp -p /dir      # Start server (short form)
        mcp-ticketer mcp status       # Check MCP status
        mcp-ticketer mcp serve        # Explicitly start server

    """
    if ctx.invoked_subcommand is None:
        # No subcommand provided, run the serve command
        # Change to project directory if provided
        if project_path:
            import os

            os.chdir(project_path)
        # Invoke the serve command through context
        ctx.invoke(mcp_serve, adapter=None, base_path=None)


@mcp_app.command(name="serve")
def mcp_serve(
    adapter: str | None = typer.Option(
        None, "--adapter", "-a", help="Override default adapter type"
    ),
    base_path: str | None = typer.Option(
        None, "--base-path", help="Base path for AITrackdown adapter"
    ),
) -> None:
    """Start MCP server for JSON-RPC communication over stdio.

    This command is used by Claude Code/Desktop when connecting to the MCP server.
    You typically don't need to run this manually - use 'mcp-ticketer install add' to configure.

    Configuration Resolution:
    - When MCP server starts, it uses the current working directory (cwd)
    - The cwd is set by Claude Code/Desktop from the 'cwd' field in .mcp/config.json
    - Configuration is loaded with this priority:
      1. Project-specific: .mcp-ticketer/config.json in cwd
      2. Global: ~/.mcp-ticketer/config.json
      3. Default: aitrackdown adapter with .aitrackdown base path
    """
    # Local imports to avoid circular dependency
    from ..mcp.server.server_sdk import configure_adapter
    from ..mcp.server.server_sdk import main as sdk_main

    # Import load_config locally to avoid circular import
    # (main.py imports this module, so we can't import from main at module level)
    from .ticket_commands import load_config

    # Load configuration (respects project-specific config in cwd)
    config = load_config()

    # Determine adapter type with priority: CLI arg > config > .env files > default
    if adapter:
        # Priority 1: Command line argument
        adapter_type = adapter
        # Get base config from config file
        adapters_config = config.get("adapters", {})
        adapter_config = adapters_config.get(adapter_type, {})
    else:
        # Priority 2: Configuration file (project-specific)
        adapter_type = config.get("default_adapter")
        if adapter_type:
            adapters_config = config.get("adapters", {})
            adapter_config = adapters_config.get(adapter_type, {})
        else:
            # Priority 3: .env files (auto-detection fallback)
            from ..mcp.server.main import _load_env_configuration

            env_config = _load_env_configuration()
            if env_config:
                adapter_type = env_config["adapter_type"]
                adapter_config = env_config["adapter_config"]
            else:
                # Priority 4: Default fallback
                adapter_type = "aitrackdown"
                adapters_config = config.get("adapters", {})
                adapter_config = adapters_config.get(adapter_type, {})

    # Override with command line options if provided (highest priority)
    if base_path and adapter_type == "aitrackdown":
        adapter_config["base_path"] = base_path

    # Fallback to legacy config format
    if not adapter_config and "config" in config:
        adapter_config = config["config"]

    # MCP server uses stdio for JSON-RPC, so we can't print to stdout
    # Only print to stderr to avoid interfering with the protocol
    if sys.stderr.isatty():
        # Only print if stderr is a terminal (not redirected)
        console.file = sys.stderr
        console.print(
            f"[green]Starting MCP SDK server[/green] with {adapter_type} adapter"
        )
        console.print(
            "[dim]Server running on stdio. Send JSON-RPC requests via stdin.[/dim]"
        )

    # Configure adapter and run SDK server
    try:
        configure_adapter(adapter_type, adapter_config)
        sdk_main()
    except KeyboardInterrupt:
        # Send this to stderr
        if sys.stderr.isatty():
            console.print("\n[yellow]Server stopped by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        # Log error to stderr
        sys.stderr.write(f"MCP server error: {e}\n")
        sys.exit(1)


@mcp_app.command(name="claude")
def mcp_claude(
    global_config: bool = typer.Option(
        False,
        "--global",
        "-g",
        help="Configure Claude Desktop instead of project-level",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing configuration"
    ),
) -> None:
    """Configure Claude Code to use mcp-ticketer MCP server.

    Reads configuration from .mcp-ticketer/config.json and updates
    Claude Code's MCP settings accordingly.

    By default, configures project-level (.mcp/config.json).
    Use --global to configure Claude Desktop instead.

    Examples:
    --------
        # Configure for current project (default)
        mcp-ticketer mcp claude

        # Configure Claude Desktop globally
        mcp-ticketer mcp claude --global

        # Force overwrite existing configuration
        mcp-ticketer mcp claude --force

    """
    from ..cli.mcp_configure import configure_claude_mcp

    try:
        configure_claude_mcp(global_config=global_config, force=force)
    except Exception as e:
        console.print(f"[red]✗ Configuration failed:[/red] {e}")
        raise typer.Exit(1) from e


@mcp_app.command(name="gemini")
def mcp_gemini(
    scope: str = typer.Option(
        "project",
        "--scope",
        "-s",
        help="Configuration scope: 'project' (default) or 'user'",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing configuration"
    ),
) -> None:
    """Configure Gemini CLI to use mcp-ticketer MCP server.

    Reads configuration from .mcp-ticketer/config.json and creates
    Gemini CLI settings file with mcp-ticketer configuration.

    By default, configures project-level (.gemini/settings.json).
    Use --scope user to configure user-level (~/.gemini/settings.json).

    Examples:
    --------
        # Configure for current project (default)
        mcp-ticketer mcp gemini

        # Configure at user level
        mcp-ticketer mcp gemini --scope user

        # Force overwrite existing configuration
        mcp-ticketer mcp gemini --force

    """
    from ..cli.gemini_configure import configure_gemini_mcp

    # Validate scope parameter
    if scope not in ["project", "user"]:
        console.print(
            f"[red]✗ Invalid scope:[/red] '{scope}'. Must be 'project' or 'user'"
        )
        raise typer.Exit(1) from None

    try:
        configure_gemini_mcp(scope=scope, force=force)  # type: ignore
    except Exception as e:
        console.print(f"[red]✗ Configuration failed:[/red] {e}")
        raise typer.Exit(1) from e


@mcp_app.command(name="codex")
def mcp_codex(
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing configuration"
    ),
) -> None:
    """Configure Codex CLI to use mcp-ticketer MCP server.

    Reads configuration from .mcp-ticketer/config.json and creates
    Codex CLI config.toml with mcp-ticketer configuration.

    IMPORTANT: Codex CLI ONLY supports global configuration at ~/.codex/config.toml.
    There is no project-level configuration support. After configuration,
    you must restart Codex CLI for changes to take effect.

    Examples:
    --------
        # Configure Codex CLI globally
        mcp-ticketer mcp codex

        # Force overwrite existing configuration
        mcp-ticketer mcp codex --force

    """
    from ..cli.codex_configure import configure_codex_mcp

    try:
        configure_codex_mcp(force=force)
    except Exception as e:
        console.print(f"[red]✗ Configuration failed:[/red] {e}")
        raise typer.Exit(1) from e


@mcp_app.command(name="auggie")
def mcp_auggie(
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing configuration"
    ),
) -> None:
    """Configure Auggie CLI to use mcp-ticketer MCP server.

    Reads configuration from .mcp-ticketer/config.json and creates
    Auggie CLI settings.json with mcp-ticketer configuration.

    IMPORTANT: Auggie CLI ONLY supports global configuration at ~/.augment/settings.json.
    There is no project-level configuration support. After configuration,
    you must restart Auggie CLI for changes to take effect.

    Examples:
    --------
        # Configure Auggie CLI globally
        mcp-ticketer mcp auggie

        # Force overwrite existing configuration
        mcp-ticketer mcp auggie --force

    """
    from ..cli.auggie_configure import configure_auggie_mcp

    try:
        configure_auggie_mcp(force=force)
    except Exception as e:
        console.print(f"[red]✗ Configuration failed:[/red] {e}")
        raise typer.Exit(1) from e


@mcp_app.command(name="status")
def mcp_status() -> None:
    """Check MCP server status.

    Shows whether the MCP server is configured and running for various platforms.

    Examples:
    --------
        mcp-ticketer mcp status

    """
    console.print("[bold]MCP Server Status[/bold]\n")

    # Check project-level configuration
    project_config = Path.cwd() / ".mcp-ticketer" / "config.json"
    if project_config.exists():
        console.print(f"[green]✓[/green] Project config found: {project_config}")
        try:
            with open(project_config) as f:
                config = json.load(f)
                adapter = config.get("default_adapter", "aitrackdown")
                console.print(f"  Default adapter: [cyan]{adapter}[/cyan]")
        except Exception as e:
            console.print(f"  [yellow]Warning: Could not read config: {e}[/yellow]")
    else:
        console.print("[yellow]○[/yellow] No project config found")

    # Check Claude Code configuration
    claude_code_config = Path.cwd() / ".mcp" / "config.json"
    if claude_code_config.exists():
        console.print(
            f"\n[green]✓[/green] Claude Code configured: {claude_code_config}"
        )
    else:
        console.print("\n[yellow]○[/yellow] Claude Code not configured")

    # Check Claude Desktop configuration
    claude_desktop_config = (
        Path.home()
        / "Library"
        / "Application Support"
        / "Claude"
        / "claude_desktop_config.json"
    )
    if claude_desktop_config.exists():
        try:
            with open(claude_desktop_config) as f:
                config = json.load(f)
                if "mcpServers" in config and "mcp-ticketer" in config["mcpServers"]:
                    console.print(
                        f"[green]✓[/green] Claude Desktop configured: {claude_desktop_config}"
                    )
                else:
                    console.print(
                        "[yellow]○[/yellow] Claude Desktop config exists but mcp-ticketer not found"
                    )
        except Exception:
            console.print(
                "[yellow]○[/yellow] Claude Desktop config exists but could not be read"
            )
    else:
        console.print("[yellow]○[/yellow] Claude Desktop not configured")

    # Check Gemini configuration
    gemini_project_config = Path.cwd() / ".gemini" / "settings.json"
    gemini_user_config = Path.home() / ".gemini" / "settings.json"
    if gemini_project_config.exists():
        console.print(
            f"\n[green]✓[/green] Gemini (project) configured: {gemini_project_config}"
        )
    elif gemini_user_config.exists():
        console.print(
            f"\n[green]✓[/green] Gemini (user) configured: {gemini_user_config}"
        )
    else:
        console.print("\n[yellow]○[/yellow] Gemini not configured")

    # Check Codex configuration
    codex_config = Path.home() / ".codex" / "config.toml"
    if codex_config.exists():
        console.print(f"[green]✓[/green] Codex configured: {codex_config}")
    else:
        console.print("[yellow]○[/yellow] Codex not configured")

    # Check Auggie configuration
    auggie_config = Path.home() / ".augment" / "settings.json"
    if auggie_config.exists():
        console.print(f"[green]✓[/green] Auggie configured: {auggie_config}")
    else:
        console.print("[yellow]○[/yellow] Auggie not configured")

    console.print(
        "\n[dim]Run 'mcp-ticketer install <platform>' to configure a platform[/dim]"
    )


@mcp_app.command(name="stop")
def mcp_stop() -> None:
    """Stop MCP server (placeholder - MCP runs on-demand via stdio).

    Note: The MCP server runs on-demand when AI clients connect via stdio.
    It doesn't run as a persistent background service, so there's nothing to stop.
    This command is provided for consistency but has no effect.

    Examples:
    --------
        mcp-ticketer mcp stop

    """
    console.print(
        "[yellow]ℹ[/yellow]  MCP server runs on-demand via stdio (not as a background service)"
    )
    console.print("There is no persistent server process to stop.")
    console.print(
        "\n[dim]The server starts automatically when AI clients connect and stops when they disconnect.[/dim]"
    )
