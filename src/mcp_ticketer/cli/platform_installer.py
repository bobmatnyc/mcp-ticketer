"""Platform installation commands for mcp-ticketer MCP server.

This module provides commands for installing and removing mcp-ticketer
MCP server configuration for various AI platforms (Claude, Gemini, Codex, Auggie).
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

# Import for typing compatibility
from .init_command import init
from .platform_detection import PlatformDetector, get_platform_by_name
from .setup_command import _update_mcp_json_credentials

console = Console()


def install(
    platform: str | None = typer.Argument(
        None,
        help="Platform to install (claude-code, cursor, gemini, codex, auggie). Use claude-desktop for desktop AI assistant.",
    ),
    auto_detect: bool = typer.Option(
        False,
        "--auto-detect",
        "-d",
        help="Auto-detect and show all code editors (excludes desktop AI assistants by default)",
    ),
    install_all: bool = typer.Option(
        False,
        "--all",
        help="Install for all detected code editors (excludes Claude Desktop unless --include-desktop specified)",
    ),
    include_desktop: bool = typer.Option(
        False,
        "--include-desktop",
        help="Include Claude Desktop in auto-detection and --all installation",
    ),
    adapter: str | None = typer.Option(
        None,
        "--adapter",
        "-a",
        help="Adapter type to use (interactive prompt if not specified)",
    ),
    project_path: str | None = typer.Option(
        None, "--path", help="Project path (default: current directory)"
    ),
    global_config: bool = typer.Option(
        False,
        "--global",
        "-g",
        help="Save to global config instead of project-specific",
    ),
    base_path: str | None = typer.Option(
        None,
        "--base-path",
        "-p",
        help="Base path for ticket storage (AITrackdown only)",
    ),
    api_key: str | None = typer.Option(
        None, "--api-key", help="API key for Linear or API token for JIRA"
    ),
    team_id: str | None = typer.Option(
        None, "--team-id", help="Linear team ID (required for Linear adapter)"
    ),
    jira_server: str | None = typer.Option(
        None,
        "--jira-server",
        help="JIRA server URL (e.g., https://company.atlassian.net)",
    ),
    jira_email: str | None = typer.Option(
        None, "--jira-email", help="JIRA user email for authentication"
    ),
    jira_project: str | None = typer.Option(
        None, "--jira-project", help="Default JIRA project key"
    ),
    github_owner: str | None = typer.Option(
        None, "--github-owner", help="GitHub repository owner"
    ),
    github_repo: str | None = typer.Option(
        None, "--github-repo", help="GitHub repository name"
    ),
    github_token: str | None = typer.Option(
        None, "--github-token", help="GitHub Personal Access Token"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be done without making changes (for platform installation)",
    ),
) -> None:
    """Install MCP server configuration for AI platforms.

    This command configures mcp-ticketer as an MCP server for various AI
    platforms. It updates platform-specific configuration files to enable
    mcp-ticketer integration.

    RECOMMENDED: Use 'mcp-ticketer setup' for first-time setup, which
    handles both adapter configuration and platform installation together.

    Platform Installation:
        # Auto-detect and prompt for platform selection
        mcp-ticketer install

        # Show all detected platforms
        mcp-ticketer install --auto-detect

        # Install for all detected platforms
        mcp-ticketer install --all

        # Install for specific platform
        mcp-ticketer install claude-code     # Claude Code (project-level)
        mcp-ticketer install claude-desktop  # Claude Desktop (global)
        mcp-ticketer install gemini          # Gemini CLI
        mcp-ticketer install codex           # Codex
        mcp-ticketer install auggie          # Auggie

    Legacy Usage (adapter setup, deprecated - use 'init' or 'setup' instead):
        mcp-ticketer install --adapter linear  # Use 'init' or 'setup' instead

    """
    detector = PlatformDetector()

    # Handle auto-detect flag (just show detected platforms and exit)
    if auto_detect:
        detected = detector.detect_all(
            project_path=Path(project_path) if project_path else Path.cwd(),
            exclude_desktop=not include_desktop,
        )

        if not detected:
            console.print("[yellow]No code editors detected.[/yellow]")
            console.print("\n[bold]Supported code editors:[/bold]")
            console.print("  • Claude Code - Project-level AI code assistant")
            console.print("  • Cursor - AI-powered code editor")
            console.print("  • Auggie - CLI code assistant")
            console.print("  • Codex - CLI code assistant")
            console.print("  • Gemini - CLI code assistant")
            if not include_desktop:
                console.print(
                    "\n[dim]Use --include-desktop to also detect Claude Desktop (desktop AI assistant)[/dim]"
                )
            console.print(
                "\n[dim]Install these platforms to use them with mcp-ticketer.[/dim]"
            )
            return

        console.print("[bold]Detected AI platforms:[/bold]\n")
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Platform", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Scope", style="blue")
        table.add_column("Config Path", style="dim")

        for plat in detected:
            status = "✓ Installed" if plat.is_installed else "⚠ Config Issue"
            table.add_row(plat.display_name, status, plat.scope, str(plat.config_path))

        console.print(table)
        console.print(
            "\n[dim]Run 'mcp-ticketer install <platform>' to configure a specific platform[/dim]"
        )
        console.print(
            "[dim]Run 'mcp-ticketer install --all' to configure all detected platforms[/dim]"
        )
        return

    # Handle --all flag (install for all detected platforms)
    if install_all:
        detected = detector.detect_all(
            project_path=Path(project_path) if project_path else Path.cwd(),
            exclude_desktop=not include_desktop,
        )

        if not detected:
            console.print("[yellow]No AI platforms detected.[/yellow]")
            console.print(
                "Run 'mcp-ticketer install --auto-detect' to see supported platforms."
            )
            return

        # Handle dry-run mode - show what would be installed without actually installing
        if dry_run:
            console.print(
                "\n[yellow]DRY RUN - The following platforms would be configured:[/yellow]\n"
            )

            installable_count = 0
            for plat in detected:
                if plat.is_installed:
                    console.print(f"  ✓ {plat.display_name} ({plat.scope})")
                    installable_count += 1
                else:
                    console.print(
                        f"  ⚠ {plat.display_name} ({plat.scope}) - would be skipped (configuration issue)"
                    )

            console.print(
                f"\n[dim]Would configure {installable_count} platform(s)[/dim]"
            )
            return

        console.print(
            f"[bold]Installing for {len(detected)} detected platform(s)...[/bold]\n"
        )

        # Import configuration functions
        from .auggie_configure import configure_auggie_mcp
        from .codex_configure import configure_codex_mcp
        from .cursor_configure import configure_cursor_mcp
        from .gemini_configure import configure_gemini_mcp
        from .mcp_configure import configure_claude_mcp

        # Map platform names to configuration functions
        platform_mapping = {
            "claude-code": lambda: configure_claude_mcp(
                global_config=False, force=True
            ),
            "claude-desktop": lambda: configure_claude_mcp(
                global_config=True, force=True
            ),
            "cursor": lambda: configure_cursor_mcp(force=True),
            "auggie": lambda: configure_auggie_mcp(force=True),
            "gemini": lambda: configure_gemini_mcp(scope="project", force=True),
            "codex": lambda: configure_codex_mcp(force=True),
        }

        success_count = 0
        failed = []

        for plat in detected:
            if not plat.is_installed:
                console.print(
                    f"[yellow]⚠[/yellow]  Skipping {plat.display_name} (configuration issue)"
                )
                continue

            config_func = platform_mapping.get(plat.name)
            if not config_func:
                console.print(
                    f"[yellow]⚠[/yellow]  No installer for {plat.display_name}"
                )
                continue

            try:
                console.print(f"[cyan]Installing for {plat.display_name}...[/cyan]")
                config_func()
                success_count += 1

                # Update credentials in parent .mcp.json for Claude platforms
                if plat.name in ("claude-code", "claude-desktop"):
                    _update_mcp_json_credentials(Path.cwd(), console)
            except Exception as e:
                console.print(
                    f"[red]✗[/red]  Failed to install for {plat.display_name}: {e}"
                )
                failed.append(plat.display_name)

        console.print(
            f"\n[bold]Installation complete:[/bold] {success_count} succeeded"
        )
        if failed:
            console.print(f"[red]Failed:[/red] {', '.join(failed)}")
        return

    # If no platform argument and no adapter flag, auto-detect and prompt
    if platform is None and adapter is None:
        detected = detector.detect_all(
            project_path=Path(project_path) if project_path else Path.cwd()
        )

        # Filter to only installed platforms
        installed = [p for p in detected if p.is_installed]

        if not installed:
            console.print("[yellow]No AI platforms detected.[/yellow]")
            console.print("\n[bold]To see supported platforms:[/bold]")
            console.print("  mcp-ticketer install --auto-detect")
            console.print("\n[bold]Or run legacy adapter setup:[/bold]")
            console.print("  mcp-ticketer install --adapter <adapter-type>")
            return

        # Show detected platforms and prompt for selection
        console.print("[bold]Detected AI platforms:[/bold]\n")
        for idx, plat in enumerate(installed, 1):
            console.print(f"  {idx}. {plat.display_name} ({plat.scope})")

        console.print(
            "\n[dim]Enter the number of the platform to configure, or 'q' to quit:[/dim]"
        )
        choice = typer.prompt("Select platform")

        if choice.lower() == "q":
            console.print("Installation cancelled.")
            return

        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(installed):
                console.print("[red]Invalid selection.[/red]")
                raise typer.Exit(1) from None
            platform = installed[idx].name
        except ValueError as e:
            console.print("[red]Invalid input. Please enter a number.[/red]")
            raise typer.Exit(1) from e

    # If platform argument is provided, handle MCP platform installation (NEW SYNTAX)
    if platform is not None:
        # Validate that the platform is actually installed
        platform_info = get_platform_by_name(
            platform, project_path=Path(project_path) if project_path else Path.cwd()
        )

        if platform_info and not platform_info.is_installed:
            console.print(
                f"[yellow]⚠[/yellow]  {platform_info.display_name} was detected but has a configuration issue."
            )
            console.print(f"[dim]Config path: {platform_info.config_path}[/dim]\n")

            proceed = typer.confirm(
                "Do you want to proceed with installation anyway?", default=False
            )
            if not proceed:
                console.print("Installation cancelled.")
                return

        elif not platform_info:
            # Platform not detected at all - warn but allow proceeding
            console.print(
                f"[yellow]⚠[/yellow]  Platform '{platform}' not detected on this system."
            )
            console.print(
                "[dim]Run 'mcp-ticketer install --auto-detect' to see detected platforms.[/dim]\n"
            )

            proceed = typer.confirm(
                "Do you want to proceed with installation anyway?", default=False
            )
            if not proceed:
                console.print("Installation cancelled.")
                return

        # Import configuration functions
        from .auggie_configure import configure_auggie_mcp
        from .codex_configure import configure_codex_mcp
        from .cursor_configure import configure_cursor_mcp
        from .gemini_configure import configure_gemini_mcp
        from .mcp_configure import configure_claude_mcp

        # Map platform names to configuration functions
        platform_mapping = {
            "claude-code": {
                "func": lambda: configure_claude_mcp(global_config=False, force=True),
                "name": "Claude Code",
            },
            "claude-desktop": {
                "func": lambda: configure_claude_mcp(global_config=True, force=True),
                "name": "Claude Desktop",
            },
            "cursor": {
                "func": lambda: configure_cursor_mcp(force=True),
                "name": "Cursor",
            },
            "auggie": {
                "func": lambda: configure_auggie_mcp(force=True),
                "name": "Auggie",
            },
            "gemini": {
                "func": lambda: configure_gemini_mcp(scope="project", force=True),
                "name": "Gemini CLI",
            },
            "codex": {
                "func": lambda: configure_codex_mcp(force=True),
                "name": "Codex",
            },
        }

        if platform not in platform_mapping:
            console.print(f"[red]Unknown platform: {platform}[/red]")
            console.print("\n[bold]Available platforms:[/bold]")
            for p in platform_mapping.keys():
                console.print(f"  • {p}")
            raise typer.Exit(1) from None

        config = platform_mapping[platform]

        if dry_run:
            console.print(f"[cyan]DRY RUN - Would install for {config['name']}[/cyan]")
            return

        try:
            config["func"]()

            # Update credentials in parent .mcp.json for Claude platforms
            if platform in ("claude-code", "claude-desktop"):
                _update_mcp_json_credentials(Path.cwd(), console)
        except Exception as e:
            console.print(f"[red]Installation failed: {e}[/red]")
            raise typer.Exit(1) from e
        return

    # Otherwise, delegate to init for adapter initialization (LEGACY BEHAVIOR)
    # This makes 'install' and 'init' synonymous when called without platform argument
    init(
        adapter=adapter,
        project_path=project_path,
        global_config=global_config,
        base_path=base_path,
        api_key=api_key,
        team_id=team_id,
        jira_server=jira_server,
        jira_email=jira_email,
        jira_project=jira_project,
        github_owner=github_owner,
        github_repo=github_repo,
        github_token=github_token,
    )


def remove(
    platform: str | None = typer.Argument(
        None,
        help="Platform to remove (claude-code, claude-desktop, cursor, auggie, gemini, codex)",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be done without making changes"
    ),
) -> None:
    """Remove mcp-ticketer from AI platforms.

    Without arguments, shows help and available platforms.
    With a platform argument, removes MCP configuration for that platform.

    Examples:
        # Remove from Claude Code (project-level)
        mcp-ticketer remove claude-code

        # Remove from Claude Desktop (global)
        mcp-ticketer remove claude-desktop

        # Remove from Auggie
        mcp-ticketer remove auggie

        # Dry run to preview changes
        mcp-ticketer remove claude-code --dry-run

    """
    # If no platform specified, show help message
    if platform is None:
        console.print("[bold]Remove mcp-ticketer from AI platforms[/bold]\n")
        console.print("Usage: mcp-ticketer remove <platform>\n")
        console.print("[bold]Available platforms:[/bold]")
        console.print("  • claude-code     - Claude Code (project-level)")
        console.print("  • claude-desktop  - Claude Desktop (global)")
        console.print("  • auggie          - Auggie (global)")
        console.print("  • gemini          - Gemini CLI (project-level by default)")
        console.print("  • codex           - Codex (global)")
        return

    # Import removal functions
    from .auggie_configure import remove_auggie_mcp
    from .codex_configure import remove_codex_mcp
    from .cursor_configure import remove_cursor_mcp
    from .gemini_configure import remove_gemini_mcp
    from .mcp_configure import remove_claude_mcp

    # Map platform names to removal functions
    platform_mapping = {
        "claude-code": {
            "func": lambda: remove_claude_mcp(global_config=False, dry_run=dry_run),
            "name": "Claude Code",
        },
        "claude-desktop": {
            "func": lambda: remove_claude_mcp(global_config=True, dry_run=dry_run),
            "name": "Claude Desktop",
        },
        "cursor": {
            "func": lambda: remove_cursor_mcp(dry_run=dry_run),
            "name": "Cursor",
        },
        "auggie": {
            "func": lambda: remove_auggie_mcp(dry_run=dry_run),
            "name": "Auggie",
        },
        "gemini": {
            "func": lambda: remove_gemini_mcp(scope="project", dry_run=dry_run),
            "name": "Gemini CLI",
        },
        "codex": {
            "func": lambda: remove_codex_mcp(dry_run=dry_run),
            "name": "Codex",
        },
    }

    if platform not in platform_mapping:
        console.print(f"[red]Unknown platform: {platform}[/red]")
        console.print("\n[bold]Available platforms:[/bold]")
        for p in platform_mapping.keys():
            console.print(f"  • {p}")
        raise typer.Exit(1) from None

    config = platform_mapping[platform]

    try:
        config["func"]()
    except Exception as e:
        console.print(f"[red]Removal failed: {e}[/red]")
        raise typer.Exit(1) from e


def uninstall(
    platform: str | None = typer.Argument(
        None,
        help="Platform to uninstall (claude-code, claude-desktop, auggie, gemini, codex)",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be done without making changes"
    ),
) -> None:
    """Uninstall mcp-ticketer from AI platforms (alias for remove).

    This is an alias for the 'remove' command.

    Without arguments, shows help and available platforms.
    With a platform argument, removes MCP configuration for that platform.

    Examples:
        # Uninstall from Claude Code (project-level)
        mcp-ticketer uninstall claude-code

        # Uninstall from Claude Desktop (global)
        mcp-ticketer uninstall claude-desktop

        # Uninstall from Auggie
        mcp-ticketer uninstall auggie

        # Dry run to preview changes
        mcp-ticketer uninstall claude-code --dry-run

    """
    # Call the remove command with the same parameters
    remove(platform=platform, dry_run=dry_run)
