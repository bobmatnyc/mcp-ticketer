"""Install mcp-ticketer as an MCP server using py-mcp-installer-service."""

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()


def install_mcp_server(
    linear_key: str | None = typer.Option(
        None, "--linear-key", help="Linear API key", envvar="LINEAR_API_KEY"
    ),
    github_token: str | None = typer.Option(
        None, "--github-token", help="GitHub token", envvar="GITHUB_TOKEN"
    ),
    jira_token: str | None = typer.Option(
        None, "--jira-token", help="Jira token", envvar="JIRA_API_TOKEN"
    ),
    scope: str = typer.Option(
        "project", "--scope", help="Installation scope: project or global"
    ),
    method: str | None = typer.Option(
        None, "--method", help="Installation method: uv, pipx, direct, python"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview changes without applying"
    ),
    platform: str | None = typer.Option(
        None, "--platform", help="Target platform (auto-detect if not specified)"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Install mcp-ticketer as an MCP server on AI coding platforms.

    This command uses py-mcp-installer-service to install mcp-ticketer as an MCP
    server on detected AI coding platforms (Claude Desktop, Cline, Roo-Code, etc.).

    The installer will:
    1. Auto-detect available platforms (or use --platform)
    2. Choose optimal installation method (or use --method)
    3. Configure environment variables for API keys
    4. Update platform configuration files atomically

    Examples:
        # Auto-detect platform and install
        mcp-ticketer install-mcp-server

        # Install with API keys
        mcp-ticketer install-mcp-server --linear-key=... --github-token=...

        # Install globally instead of project-scoped
        mcp-ticketer install-mcp-server --scope global

        # Install with specific method
        mcp-ticketer install-mcp-server --method uv

        # Preview changes without applying
        mcp-ticketer install-mcp-server --dry-run

        # Install on specific platform
        mcp-ticketer install-mcp-server --platform claude-desktop

    Supported Platforms:
        - claude-desktop: Claude Desktop (global)
        - cline: Cline extension (project/global)
        - roo-code: Roo-Code extension (project)
        - continue: Continue extension (project/global)
        - zed: Zed editor (global)
        - windsurf: Windsurf editor (global)
        - cursor: Cursor editor (global)
        - void: Void editor (project/global)

    """
    try:
        # Import py_mcp_installer from services submodule
        # Add services path to sys.path if not already there
        services_path = (
            Path(__file__).parent.parent.parent
            / "services"
            / "py_mcp_installer"
            / "src"
        )
        if str(services_path) not in sys.path:
            sys.path.insert(0, str(services_path))

        from py_mcp_installer import InstallMethod, MCPInstaller, Platform, Scope
        from py_mcp_installer.exceptions import PyMCPInstallerError
    except ImportError as e:
        console.print(
            "[red]Error: py-mcp-installer not found. This should not happen.[/red]"
        )
        console.print(f"[yellow]ImportError: {e}[/yellow]")
        console.print(
            "[yellow]The installer is included as a submodule in this project.[/yellow]"
        )
        raise typer.Exit(1) from None

    console.print("[bold cyan]🚀 Installing mcp-ticketer as MCP Server[/bold cyan]\n")

    # Validate scope
    try:
        scope_enum = Scope(scope)
    except ValueError:
        console.print(f"[red]Invalid scope: {scope}. Use 'project' or 'global'[/red]")
        raise typer.Exit(1) from None

    # Validate method if specified
    install_method = None
    if method:
        try:
            install_method = InstallMethod(method)
        except ValueError:
            console.print(
                f"[red]Invalid method: {method}. Use 'uv', 'pipx', 'direct', or 'python'[/red]"
            )
            raise typer.Exit(1) from None

    # Validate platform if specified
    platform_enum = None
    if platform:
        try:
            platform_enum = Platform(platform)
        except ValueError:
            console.print(f"[red]Invalid platform: {platform}[/red]")
            console.print("[yellow]Supported platforms:[/yellow]")
            for p in Platform:
                console.print(f"  - {p.value}")
            raise typer.Exit(1) from None

    try:
        # Create installer
        if platform_enum:
            installer = MCPInstaller(
                platform=platform_enum, dry_run=dry_run, verbose=verbose
            )
            console.print(f"[green]Platform: {platform_enum.value}[/green]\n")
        else:
            installer = MCPInstaller.auto_detect(dry_run=dry_run, verbose=verbose)
            console.print(
                f"[green]Detected platform: {installer.platform.value}[/green]\n"
            )

        # Build environment variables from API keys
        env = {}
        if linear_key:
            env["LINEAR_API_KEY"] = linear_key
        if github_token:
            env["GITHUB_TOKEN"] = github_token
        if jira_token:
            env["JIRA_API_TOKEN"] = jira_token

        if env:
            console.print("[cyan]Environment variables configured:[/cyan]")
            for key in env:
                console.print(f"  • {key}")
            console.print()

        # Determine command and args based on installation method
        if install_method == InstallMethod.UV_RUN or (
            not install_method and _is_uv_available()
        ):
            command = "uv"
            args = ["run", "mcp-ticketer", "mcp"]
            if not install_method:
                install_method = InstallMethod.UV_RUN
        else:
            command = "mcp-ticketer"
            args = ["mcp"]

        # Install server
        console.print("[cyan]Installing mcp-ticketer...[/cyan]\n")
        result = installer.install_server(
            name="mcp-ticketer",
            command=command,
            args=args,
            env=env if env else None,
            description="Universal ticket management interface for AI agents",
            scope=scope_enum,
            method=install_method,
        )

        # Display results
        if result.success:
            console.print("[bold green]✅ Installation Successful![/bold green]\n")

            # Show installation details in table
            table = Table(title="Installation Details", show_header=False)
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")

            table.add_row("Platform", result.platform.value)
            table.add_row("Method", result.method.value)
            table.add_row("Scope", scope)
            table.add_row("Config Path", str(result.config_path))
            table.add_row("Command", f"{result.command} {' '.join(result.args or [])}")

            if dry_run:
                table.add_row("Mode", "[yellow]DRY RUN - No changes made[/yellow]")

            console.print(table)
            console.print()

            # Next steps
            if not dry_run:
                console.print("[bold]Next Steps:[/bold]")
                console.print(
                    "1. Restart your AI coding platform to load the new MCP server"
                )
                console.print(
                    "2. The mcp-ticketer commands will be available in your AI assistant"
                )
                console.print(
                    "3. Configure adapter credentials with: mcp-ticketer setup\n"
                )
            else:
                console.print(
                    "[yellow]This was a dry run. Run without --dry-run to apply changes.[/yellow]\n"
                )

        else:
            console.print("[bold red]❌ Installation Failed[/bold red]\n")
            console.print(f"[red]Error: {result.message}[/red]")
            if result.error:
                console.print(f"[dim]{result.error}[/dim]")
            raise typer.Exit(1)

    except PyMCPInstallerError as e:
        console.print("[bold red]❌ Installation Error[/bold red]\n")
        console.print(f"[red]{e}[/red]")
        if verbose:
            import traceback

            console.print(f"\n[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print("[bold red]❌ Unexpected Error[/bold red]\n")
        console.print(f"[red]{e}[/red]")
        if verbose:
            import traceback

            console.print(f"\n[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1) from None


def _is_uv_available() -> bool:
    """Check if uv is available on the system.

    Returns:
        True if uv is available, False otherwise

    """
    import shutil

    return shutil.which("uv") is not None


def list_mcp_servers(
    platform: str | None = typer.Option(
        None, "--platform", help="Target platform (auto-detect if not specified)"
    ),
) -> None:
    """List installed MCP servers on detected platform.

    Examples:
        # List servers on auto-detected platform
        mcp-ticketer list-mcp-servers

        # List servers on specific platform
        mcp-ticketer list-mcp-servers --platform claude-desktop

    """
    try:
        # Import py_mcp_installer from services submodule
        services_path = (
            Path(__file__).parent.parent.parent
            / "services"
            / "py_mcp_installer"
            / "src"
        )
        if str(services_path) not in sys.path:
            sys.path.insert(0, str(services_path))

        from py_mcp_installer import MCPInstaller, Platform
        from py_mcp_installer.exceptions import PyMCPInstallerError
    except ImportError as e:
        console.print("[red]Error: py-mcp-installer not found[/red]")
        console.print(f"[yellow]ImportError: {e}[/yellow]")
        raise typer.Exit(1) from None

    console.print("[bold cyan]📋 Installed MCP Servers[/bold cyan]\n")

    try:
        # Create installer
        if platform:
            try:
                platform_enum = Platform(platform)
                installer = MCPInstaller(platform=platform_enum)
                console.print(f"[green]Platform: {platform_enum.value}[/green]\n")
            except ValueError:
                console.print(f"[red]Invalid platform: {platform}[/red]")
                raise typer.Exit(1) from None
        else:
            installer = MCPInstaller.auto_detect()
            console.print(
                f"[green]Detected platform: {installer.platform.value}[/green]\n"
            )

        # List servers
        servers = installer.list_servers()

        if not servers:
            console.print("[yellow]No MCP servers installed[/yellow]")
            return

        # Display in table
        table = Table(title=f"MCP Servers ({len(servers)} total)")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Command", style="white")
        table.add_column("Description", style="dim")

        for server in servers:
            cmd = f"{server.command} {' '.join(server.args or [])}"
            desc = server.description or ""
            table.add_row(server.name, cmd, desc)

        console.print(table)

    except PyMCPInstallerError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1) from None


def uninstall_mcp_server(
    platform: str | None = typer.Option(
        None, "--platform", help="Target platform (auto-detect if not specified)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview changes without applying"
    ),
) -> None:
    """Uninstall mcp-ticketer MCP server from platform.

    Examples:
        # Uninstall from auto-detected platform
        mcp-ticketer uninstall-mcp-server

        # Uninstall from specific platform
        mcp-ticketer uninstall-mcp-server --platform claude-desktop

        # Preview uninstall without applying
        mcp-ticketer uninstall-mcp-server --dry-run

    """
    try:
        # Import py_mcp_installer from services submodule
        services_path = (
            Path(__file__).parent.parent.parent
            / "services"
            / "py_mcp_installer"
            / "src"
        )
        if str(services_path) not in sys.path:
            sys.path.insert(0, str(services_path))

        from py_mcp_installer import MCPInstaller, Platform
        from py_mcp_installer.exceptions import PyMCPInstallerError
    except ImportError as e:
        console.print("[red]Error: py-mcp-installer not found[/red]")
        console.print(f"[yellow]ImportError: {e}[/yellow]")
        raise typer.Exit(1) from None

    console.print("[bold cyan]🗑️  Uninstalling mcp-ticketer MCP Server[/bold cyan]\n")

    try:
        # Create installer
        if platform:
            try:
                platform_enum = Platform(platform)
                installer = MCPInstaller(platform=platform_enum, dry_run=dry_run)
                console.print(f"[green]Platform: {platform_enum.value}[/green]\n")
            except ValueError:
                console.print(f"[red]Invalid platform: {platform}[/red]")
                raise typer.Exit(1) from None
        else:
            installer = MCPInstaller.auto_detect(dry_run=dry_run)
            console.print(
                f"[green]Detected platform: {installer.platform.value}[/green]\n"
            )

        # Uninstall
        success = installer.uninstall_server(name="mcp-ticketer")

        if success:
            if dry_run:
                console.print("[yellow]DRY RUN: Would uninstall mcp-ticketer[/yellow]")
            else:
                console.print("[green]✅ Successfully uninstalled mcp-ticketer[/green]")
                console.print(
                    "\n[dim]Restart your AI coding platform to apply changes[/dim]"
                )
        else:
            console.print(
                "[yellow]mcp-ticketer not found or already uninstalled[/yellow]"
            )

    except PyMCPInstallerError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1) from None
