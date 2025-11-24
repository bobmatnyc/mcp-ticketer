"""Adapter diagnostics and configuration validation."""

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from ..core import AdapterRegistry
from ..core.env_discovery import discover_config


def diagnose_adapter_configuration(console: Console) -> None:
    """Diagnose adapter configuration and provide recommendations.

    Args:
    ----
        console: Rich console for output

    """
    console.print(
        "\n[bold blue]🔍 MCP Ticketer Adapter Configuration Diagnostics[/bold blue]\n"
    )

    # 1. Check .env files
    _check_env_files(console)

    # 2. Check configuration files
    _check_configuration_files(console)

    # 3. Check adapter discovery
    _check_adapter_discovery(console)

    # 4. Test adapter instantiation
    _test_adapter_instantiation(console)

    # 5. Provide recommendations
    _provide_recommendations(console)


def _check_env_files(console: Console) -> None:
    """Check .env files for configuration."""
    console.print("[bold]1. .env File Configuration[/bold]")

    # Load .env files
    from ..mcp.server import _load_env_configuration

    env_config = _load_env_configuration()

    # Check for .env files
    env_files = [".env.local", ".env"]

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("File", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Variables Found", style="yellow")

    for env_file in env_files:
        env_path = Path.cwd() / env_file
        if env_path.exists():
            try:
                # Count variables in file
                var_count = 0
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            var_count += 1

                status = "✅ Found"
                variables = f"{var_count} variables"
            except Exception:
                status = "⚠️ Error reading"
                variables = "Unknown"
        else:
            status = "❌ Missing"
            variables = "N/A"

        table.add_row(env_file, status, variables)

    console.print(table)

    # Show discovered configuration
    if env_config:
        console.print(
            f"\n[green]✅ Discovered adapter: {env_config['adapter_type']}[/green]"
        )
        config_keys = list(env_config["adapter_config"].keys())
        console.print(f"[dim]Configuration keys: {config_keys}[/dim]")
    else:
        console.print(
            "\n[yellow]⚠️ No adapter configuration found in .env files[/yellow]"
        )

    console.print()


def _check_configuration_files(console: Console) -> None:
    """Check configuration files."""
    console.print("[bold]2. Configuration Files[/bold]")

    config_files = [
        (".env.local", "Local environment file (highest priority)"),
        (".env", "Environment file"),
        (".mcp-ticketer/config.json", "Project configuration"),
        (str(Path.home() / ".mcp-ticketer" / "config.json"), "Global configuration"),
    ]

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("File", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Status", style="green")
    table.add_column("Size", style="yellow")

    for file_path, description in config_files:
        path = Path(file_path)
        if path.exists():
            try:
                size = path.stat().st_size
                status = "✅ Found"
                size_str = f"{size} bytes"
            except Exception:
                status = "⚠️ Error"
                size_str = "Unknown"
        else:
            status = "❌ Missing"
            size_str = "N/A"

        table.add_row(str(path), description, status, size_str)

    console.print(table)
    console.print()


def _check_adapter_discovery(console: Console) -> None:
    """Check adapter discovery from configuration."""
    console.print("[bold]3. Adapter Discovery[/bold]")

    try:
        # Discover configuration
        discovered = discover_config(Path.cwd())

        if discovered and discovered.adapters:
            primary = discovered.get_primary_adapter()

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Adapter", style="cyan")
            table.add_column("Confidence", style="white")
            table.add_column("Source", style="green")
            table.add_column("Status", style="yellow")

            for adapter_info in discovered.adapters:
                confidence = f"{adapter_info.confidence:.0%}"
                status = "✅ Primary" if adapter_info == primary else "⚪ Available"

                table.add_row(
                    adapter_info.adapter_type, confidence, adapter_info.found_in, status
                )

            console.print(table)

            if primary:
                console.print(
                    f"\n[green]✅ Primary adapter detected: {primary.adapter_type}[/green]"
                )
                console.print(f"[dim]Source: {primary.found_in}[/dim]")
                console.print(f"[dim]Confidence: {primary.confidence:.0%}[/dim]")
            else:
                console.print("\n[yellow]⚠️ No primary adapter detected[/yellow]")
        else:
            console.print("[red]❌ No adapters discovered[/red]")
            console.print("[dim]This usually means no credentials are configured[/dim]")

    except Exception as e:
        console.print(f"[red]❌ Error during discovery: {e}[/red]")

    console.print()


def _test_adapter_instantiation(console: Console) -> None:
    """Test adapter instantiation."""
    console.print("[bold]4. Adapter Instantiation Test[/bold]")

    # Determine which adapter to test from .env files
    from ..mcp.server import _load_env_configuration

    env_config = _load_env_configuration()

    if env_config:
        adapter_type = env_config["adapter_type"]
        config = env_config["adapter_config"]
    else:
        # Try to discover from existing discovery system
        try:
            discovered = discover_config(Path.cwd())
            if discovered and discovered.adapters:
                primary = discovered.get_primary_adapter()
                if primary:
                    adapter_type = primary.adapter_type
                    # Build config from discovery
                    from ..mcp.server import _build_adapter_config_from_env_vars

                    config = _build_adapter_config_from_env_vars(adapter_type, {})
                else:
                    adapter_type = "aitrackdown"
                    config = {"base_path": ".aitrackdown"}
            else:
                adapter_type = "aitrackdown"
                config = {"base_path": ".aitrackdown"}
        except Exception:
            adapter_type = "aitrackdown"
            config = {"base_path": ".aitrackdown"}

    console.print(f"Testing adapter: [cyan]{adapter_type}[/cyan]")
    console.print(f"Configuration keys: [yellow]{list(config.keys())}[/yellow]")

    try:
        # Try to instantiate adapter
        adapter = AdapterRegistry.get_adapter(adapter_type, config)

        console.print(
            f"[green]✅ Adapter instantiated successfully: {adapter.__class__.__name__}[/green]"
        )

        # Test basic functionality
        if hasattr(adapter, "validate_credentials"):
            try:
                is_valid, error_msg = adapter.validate_credentials()
                if is_valid:
                    console.print("[green]✅ Credentials validation passed[/green]")
                else:
                    console.print(
                        f"[red]❌ Credentials validation failed: {error_msg}[/red]"
                    )
            except Exception as e:
                console.print(f"[yellow]⚠️ Credentials validation error: {e}[/yellow]")

    except Exception as e:
        console.print(f"[red]❌ Adapter instantiation failed: {e}[/red]")

        # Provide specific guidance based on adapter type
        if adapter_type == "linear":
            console.print(
                "\n[yellow]Linear adapter requires in .env/.env.local:[/yellow]"
            )
            console.print("• LINEAR_API_KEY=your_api_key")
            console.print(
                "• LINEAR_TEAM_ID=your_team_id (or LINEAR_TEAM_KEY=your_team_key)"
            )
        elif adapter_type == "github":
            console.print(
                "\n[yellow]GitHub adapter requires in .env/.env.local:[/yellow]"
            )
            console.print("• GITHUB_TOKEN=your_token")
            console.print("• GITHUB_OWNER=your_username")
            console.print("• GITHUB_REPO=your_repository")
        elif adapter_type == "jira":
            console.print(
                "\n[yellow]JIRA adapter requires in .env/.env.local:[/yellow]"
            )
            console.print("• JIRA_SERVER=your_server_url")
            console.print("• JIRA_EMAIL=your_email")
            console.print("• JIRA_API_TOKEN=your_token")

    console.print()


def _provide_recommendations(console: Console) -> None:
    """Provide configuration recommendations."""
    console.print("[bold]5. Recommendations[/bold]")

    # Check .env configuration
    from ..mcp.server import _load_env_configuration

    env_config = _load_env_configuration()

    recommendations = []

    if not env_config:
        recommendations.append(
            "Create .env.local or .env file with adapter configuration"
        )
        recommendations.append(
            "Add MCP_TICKETER_ADAPTER=linear (or github, jira) to specify adapter type"
        )
    else:
        adapter_type = env_config["adapter_type"]
        config = env_config["adapter_config"]

        # Check for incomplete configurations
        if adapter_type == "linear":
            if not config.get("api_key"):
                recommendations.append("Add LINEAR_API_KEY to .env file")
            if not config.get("team_id") and not config.get("team_key"):
                recommendations.append(
                    "Add LINEAR_TEAM_ID or LINEAR_TEAM_KEY to .env file"
                )

        elif adapter_type == "github":
            missing = []
            if not config.get("token"):
                missing.append("GITHUB_TOKEN")
            if not config.get("owner"):
                missing.append("GITHUB_OWNER")
            if not config.get("repo"):
                missing.append("GITHUB_REPO")
            if missing:
                recommendations.append(
                    f"Add missing GitHub variables to .env: {', '.join(missing)}"
                )

        elif adapter_type == "jira":
            missing = []
            if not config.get("server"):
                missing.append("JIRA_SERVER")
            if not config.get("email"):
                missing.append("JIRA_EMAIL")
            if not config.get("api_token"):
                missing.append("JIRA_API_TOKEN")
            if missing:
                recommendations.append(
                    f"Add missing JIRA variables to .env: {', '.join(missing)}"
                )

    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            console.print(f"{i}. [yellow]{rec}[/yellow]")
    else:
        console.print("[green]✅ Configuration looks good![/green]")

    # Show .env file examples
    console.print("\n[bold].env File Examples:[/bold]")
    console.print(
        "• Linear: [cyan]echo 'MCP_TICKETER_ADAPTER=linear\\nLINEAR_API_KEY=your_key\\nLINEAR_TEAM_ID=your_team' > .env.local[/cyan]"
    )
    console.print(
        "• GitHub: [cyan]echo 'MCP_TICKETER_ADAPTER=github\\nGITHUB_TOKEN=your_token\\nGITHUB_OWNER=user\\nGITHUB_REPO=repo' > .env.local[/cyan]"
    )

    console.print("\n[bold]Quick Setup Commands:[/bold]")
    console.print("• For Linear: [cyan]mcp-ticketer init linear[/cyan]")
    console.print("• For GitHub: [cyan]mcp-ticketer init github[/cyan]")
    console.print("• For JIRA: [cyan]mcp-ticketer init jira[/cyan]")
    console.print("• For local files: [cyan]mcp-ticketer init aitrackdown[/cyan]")

    console.print("\n[bold]Test Configuration:[/bold]")
    console.print("• Run diagnostics: [cyan]mcp-ticketer doctor[/cyan]")
    console.print(
        "• Test ticket creation: [cyan]mcp-ticketer create 'Test ticket'[/cyan]"
    )
    console.print("• List tickets: [cyan]mcp-ticketer list[/cyan]")


def get_adapter_status() -> dict[str, Any]:
    """Get current adapter status for programmatic use.

    Returns:
    -------
        Dictionary with adapter status information

    """
    status: dict[str, Any] = {
        "adapter_type": None,
        "configuration_source": None,
        "credentials_valid": False,
        "error_message": None,
        "recommendations": [],
    }

    try:
        # Check .env files first
        from ..mcp.server import _load_env_configuration

        env_config = _load_env_configuration()

        if env_config:
            adapter_type = env_config["adapter_type"]
            config = env_config["adapter_config"]
            status["configuration_source"] = ".env files"
        else:
            # Try discovery system
            discovered = discover_config(Path.cwd())
            if discovered and discovered.adapters:
                primary = discovered.get_primary_adapter()
                if primary:
                    adapter_type = primary.adapter_type
                    status["configuration_source"] = primary.found_in
                    # Build basic config
                    from ..mcp.server import _build_adapter_config_from_env_vars

                    config = _build_adapter_config_from_env_vars(adapter_type, {})
                else:
                    adapter_type = "aitrackdown"
                    config = {"base_path": ".aitrackdown"}
                    status["configuration_source"] = "default"
            else:
                adapter_type = "aitrackdown"
                config = {"base_path": ".aitrackdown"}
                status["configuration_source"] = "default"

        status["adapter_type"] = adapter_type

        # Test adapter instantiation
        adapter = AdapterRegistry.get_adapter(adapter_type, config)

        # Test credentials if possible
        if hasattr(adapter, "validate_credentials"):
            is_valid, error_msg = adapter.validate_credentials()
            status["credentials_valid"] = is_valid
            if not is_valid:
                status["error_message"] = error_msg
        else:
            status["credentials_valid"] = True  # Assume valid if no validation method

    except Exception as e:
        status["error_message"] = str(e)
        status["recommendations"].append(
            "Check .env file configuration and credentials"
        )

    return status
