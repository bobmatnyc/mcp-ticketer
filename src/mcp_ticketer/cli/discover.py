"""CLI command for auto-discovering configuration from .env files."""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..core.env_discovery import DiscoveredAdapter, EnvDiscovery
from ..core.onepassword_secrets import (
    OnePasswordConfig,
    OnePasswordSecretsLoader,
    check_op_cli_status,
)
from ..core.project_config import (
    AdapterConfig,
    ConfigResolver,
    ConfigValidator,
    TicketerConfig,
)

console = Console()
app = typer.Typer(help="Auto-discover configuration from .env files")


def _mask_sensitive(value: str, key: str) -> str:
    """Mask sensitive values for display.

    Args:
    ----
        value: Value to potentially mask
        key: Key name to determine if masking needed

    Returns:
    -------
        Masked or original value

    """
    sensitive_keys = ["token", "key", "password", "secret", "api_token"]

    # Check if key contains any sensitive pattern
    key_lower = key.lower()
    is_sensitive = any(pattern in key_lower for pattern in sensitive_keys)

    # Don't mask team_id, team_key, project_key, etc.
    if "team" in key_lower or "project" in key_lower:
        is_sensitive = False

    if is_sensitive and value:
        # Show first 4 and last 4 characters
        if len(value) > 12:
            return f"{value[:4]}...{value[-4:]}"
        else:
            return "***"

    return value


def _display_discovered_adapter(
    adapter: DiscoveredAdapter, discovery: EnvDiscovery
) -> None:
    """Display information about a discovered adapter.

    Args:
    ----
        adapter: Discovered adapter to display
        discovery: EnvDiscovery instance for validation

    """
    # Header
    completeness = "✅ Complete" if adapter.is_complete() else "⚠️  Incomplete"
    confidence_percent = int(adapter.confidence * 100)

    console.print(
        f"\n[bold cyan]{adapter.adapter_type.upper()}[/bold cyan] "
        f"({completeness}, {confidence_percent}% confidence)"
    )

    # Configuration details
    console.print(f"  [dim]Found in: {adapter.found_in}[/dim]")

    for key, value in adapter.config.items():
        if key == "adapter":
            continue

        display_value = _mask_sensitive(str(value), key)
        console.print(f"  {key}: [green]{display_value}[/green]")

    # Missing fields
    if adapter.missing_fields:
        console.print(
            f"  [yellow]Missing:[/yellow] {', '.join(adapter.missing_fields)}"
        )

    # Validation warnings
    warnings = discovery.validate_discovered_config(adapter)
    if warnings:
        for warning in warnings:
            console.print(f"  {warning}")


@app.command()
def show(
    project_path: Path | None = typer.Option(
        None,
        "--path",
        "-p",
        help="Project path to scan (defaults to current directory)",
    ),
) -> None:
    """Show discovered configuration without saving."""
    proj_path = project_path or Path.cwd()

    console.print(f"\n[bold]🔍 Auto-discovering configuration in:[/bold] {proj_path}\n")

    # Discover
    discovery = EnvDiscovery(proj_path)
    result = discovery.discover()

    # Show env files found
    if result.env_files_found:
        console.print("[bold]Environment files found:[/bold]")
        for env_file in result.env_files_found:
            console.print(f"  ✅ {env_file}")
    else:
        console.print("[yellow]No .env files found[/yellow]")
        return

    # Show discovered adapters
    if result.adapters:
        console.print("\n[bold]Detected adapter configurations:[/bold]")
        for adapter in sorted(
            result.adapters, key=lambda a: a.confidence, reverse=True
        ):
            _display_discovered_adapter(adapter, discovery)

        # Show recommended adapter
        primary = result.get_primary_adapter()
        if primary:
            console.print(
                f"\n[bold green]Recommended adapter:[/bold green] {primary.adapter_type} "
                f"(most complete configuration)"
            )
    else:
        console.print("\n[yellow]No adapter configurations detected[/yellow]")
        console.print(
            "[dim]Make sure your .env file contains adapter credentials[/dim]"
        )

    # Show warnings
    if result.warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for warning in result.warnings:
            console.print(f"  {warning}")


@app.command()
def save(
    adapter: str | None = typer.Option(
        None, "--adapter", "-a", help="Which adapter to save (defaults to recommended)"
    ),
    global_config: bool = typer.Option(
        False, "--global", "-g", help="Save to global config instead of project config"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be saved without saving"
    ),
    project_path: Path | None = typer.Option(
        None,
        "--path",
        "-p",
        help="Project path to scan (defaults to current directory)",
    ),
) -> None:
    """Discover configuration and save to config file.

    By default, saves to project-specific config (.mcp-ticketer/config.json).
    Use --global to save to global config (~/.mcp-ticketer/config.json).
    """
    proj_path = project_path or Path.cwd()

    console.print(f"\n[bold]🔍 Auto-discovering configuration in:[/bold] {proj_path}\n")

    # Discover
    discovery = EnvDiscovery(proj_path)
    result = discovery.discover()

    if not result.adapters:
        console.print("[red]No adapter configurations detected[/red]")
        console.print(
            "[dim]Make sure your .env file contains adapter credentials[/dim]"
        )
        raise typer.Exit(1) from None

    # Determine which adapter to save
    if adapter:
        discovered_adapter = result.get_adapter_by_type(adapter)
        if not discovered_adapter:
            console.print(f"[red]No configuration found for adapter: {adapter}[/red]")
            console.print(
                f"[dim]Available: {', '.join(a.adapter_type for a in result.adapters)}[/dim]"
            )
            raise typer.Exit(1) from None
    else:
        # Use recommended adapter
        discovered_adapter = result.get_primary_adapter()
        if not discovered_adapter:
            console.print("[red]Could not determine recommended adapter[/red]")
            raise typer.Exit(1) from None

        console.print(
            f"[bold]Using recommended adapter:[/bold] {discovered_adapter.adapter_type}"
        )

    # Display what will be saved
    _display_discovered_adapter(discovered_adapter, discovery)

    # Validate configuration
    is_valid, error_msg = ConfigValidator.validate(
        discovered_adapter.adapter_type, discovered_adapter.config
    )

    if not is_valid:
        console.print(f"\n[red]Configuration validation failed:[/red] {error_msg}")
        console.print(
            "[dim]Fix the configuration in your .env file and try again[/dim]"
        )
        raise typer.Exit(1) from None

    if dry_run:
        console.print("\n[yellow]Dry run - no changes made[/yellow]")
        return

    # Load or create config
    resolver = ConfigResolver(proj_path)

    if global_config:
        config = resolver.load_global_config()
    else:
        config = resolver.load_project_config() or TicketerConfig()

    # Set default adapter
    config.default_adapter = discovered_adapter.adapter_type

    # Create adapter config
    adapter_config = AdapterConfig.from_dict(discovered_adapter.config)

    # Add to config
    config.adapters[discovered_adapter.adapter_type] = adapter_config

    # Save (always to project config for security)
    try:
        resolver.save_project_config(config, proj_path)
        config_location = proj_path / resolver.PROJECT_CONFIG_SUBPATH

        if global_config:
            console.print(
                "[yellow]Note: Global config deprecated for security. Saved to project config instead.[/yellow]"
            )

        console.print(f"\n[green]✅ Configuration saved to:[/green] {config_location}")
        console.print(
            f"[green]✅ Default adapter set to:[/green] {discovered_adapter.adapter_type}"
        )

    except Exception as e:
        console.print(f"\n[red]Failed to save configuration:[/red] {e}")
        raise typer.Exit(1) from None


@app.command()
def interactive(
    project_path: Path | None = typer.Option(
        None,
        "--path",
        "-p",
        help="Project path to scan (defaults to current directory)",
    ),
) -> None:
    """Interactive mode for discovering and saving configuration."""
    proj_path = project_path or Path.cwd()

    console.print(f"\n[bold]🔍 Auto-discovering configuration in:[/bold] {proj_path}\n")

    # Discover
    discovery = EnvDiscovery(proj_path)
    result = discovery.discover()

    # Show env files
    if result.env_files_found:
        console.print("[bold]Environment files found:[/bold]")
        for env_file in result.env_files_found:
            console.print(f"  ✅ {env_file}")
    else:
        console.print("[red]No .env files found[/red]")
        raise typer.Exit(1) from None

    # Show discovered adapters
    if not result.adapters:
        console.print("\n[red]No adapter configurations detected[/red]")
        console.print(
            "[dim]Make sure your .env file contains adapter credentials[/dim]"
        )
        raise typer.Exit(1) from None

    console.print("\n[bold]Detected adapter configurations:[/bold]")
    for i, adapter in enumerate(result.adapters, 1):
        completeness = "✅" if adapter.is_complete() else "⚠️ "
        console.print(
            f"  {i}. {completeness} [cyan]{adapter.adapter_type}[/cyan] "
            f"({int(adapter.confidence * 100)}% confidence)"
        )

    # Show warnings
    if result.warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for warning in result.warnings:
            console.print(f"  {warning}")

    # Ask user which adapter to save
    primary = result.get_primary_adapter()
    console.print(
        f"\n[bold]Recommended:[/bold] {primary.adapter_type if primary else 'None'}"
    )

    # Prompt for selection
    console.print("\n[bold]Select an option:[/bold]")
    console.print("  1. Save recommended adapter to project config")
    console.print("  2. Save recommended adapter to global config")
    console.print("  3. Choose different adapter")
    console.print("  4. Save all adapters")
    console.print("  5. Cancel")

    choice = typer.prompt("Enter choice", type=int, default=1)

    if choice == 5:
        console.print("[yellow]Cancelled[/yellow]")
        return

    # Determine adapters to save
    if choice in [1, 2]:
        if not primary:
            console.print("[red]No recommended adapter found[/red]")
            raise typer.Exit(1) from None
        adapters_to_save = [primary]
        default_adapter = primary.adapter_type
    elif choice == 3:
        # Let user choose
        console.print("\n[bold]Available adapters:[/bold]")
        for i, adapter in enumerate(result.adapters, 1):
            console.print(f"  {i}. {adapter.adapter_type}")

        adapter_choice = typer.prompt("Select adapter", type=int, default=1)
        if 1 <= adapter_choice <= len(result.adapters):
            selected = result.adapters[adapter_choice - 1]
            adapters_to_save = [selected]
            default_adapter = selected.adapter_type
        else:
            console.print("[red]Invalid choice[/red]")
            raise typer.Exit(1) from None
    else:  # choice == 4
        adapters_to_save = result.adapters
        default_adapter = (
            primary.adapter_type if primary else result.adapters[0].adapter_type
        )

    # Determine save location
    save_global = choice == 2

    # Load or create config
    resolver = ConfigResolver(proj_path)

    if save_global:
        config = resolver.load_global_config()
    else:
        config = resolver.load_project_config() or TicketerConfig()

    # Set default adapter
    config.default_adapter = default_adapter

    # Add adapters
    for discovered_adapter in adapters_to_save:
        # Validate
        is_valid, error_msg = ConfigValidator.validate(
            discovered_adapter.adapter_type, discovered_adapter.config
        )

        if not is_valid:
            console.print(
                f"\n[yellow]Warning:[/yellow] {discovered_adapter.adapter_type} "
                f"validation failed: {error_msg}"
            )
            continue

        # Create adapter config
        adapter_config = AdapterConfig.from_dict(discovered_adapter.config)
        config.adapters[discovered_adapter.adapter_type] = adapter_config

        console.print(f"  ✅ Added {discovered_adapter.adapter_type}")

    # Save (always to project config for security)
    try:
        resolver.save_project_config(config, proj_path)
        config_location = proj_path / resolver.PROJECT_CONFIG_SUBPATH

        if save_global:
            console.print(
                "[yellow]Note: Global config deprecated for security. Saved to project config instead.[/yellow]"
            )

        console.print(f"\n[green]✅ Configuration saved to:[/green] {config_location}")
        console.print(f"[green]✅ Default adapter:[/green] {config.default_adapter}")

    except Exception as e:
        console.print(f"\n[red]Failed to save configuration:[/red] {e}")
        raise typer.Exit(1) from None


@app.command(name="1password-status")
def onepassword_status() -> None:
    """Check 1Password CLI installation and authentication status."""
    console.print(
        Panel.fit(
            "[bold cyan]1Password CLI Status[/bold cyan]\n"
            "Checking 1Password integration...",
            border_style="cyan",
        )
    )

    status = check_op_cli_status()

    # Create status table
    table = Table(title="1Password CLI Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="white")

    # CLI installed
    if status["installed"]:
        table.add_row(
            "CLI Installed", f"[green]✓ Yes[/green] (version {status['version']})"
        )
    else:
        table.add_row("CLI Installed", "[red]✗ No[/red]")
        console.print(table)
        console.print(
            "\n[yellow]Install 1Password CLI:[/yellow]\n"
            "  macOS: brew install 1password-cli\n"
            "  Linux: See https://developer.1password.com/docs/cli/get-started/\n"
            "  Windows: See https://developer.1password.com/docs/cli/get-started/"
        )
        return

    # Authentication
    if status["authenticated"]:
        table.add_row("Authentication", "[green]✓ Signed in[/green]")

        # Show accounts
        if status["accounts"]:
            for account in status["accounts"]:
                account_url = account.get("url", "N/A")
                account_email = account.get("email", "N/A")
                table.add_row("  Account", f"{account_email} ({account_url})")
    else:
        table.add_row("Authentication", "[yellow]⚠ Not signed in[/yellow]")

    console.print(table)

    if not status["authenticated"]:
        console.print("\n[yellow]Sign in to 1Password:[/yellow]\n" "  Run: op signin\n")
    else:
        console.print(
            "\n[green]✓ 1Password CLI is ready to use![/green]\n\n"
            "You can now use .env files with op:// secret references.\n"
            "Run 'mcp-ticketer discover 1password-template' to create template files."
        )


@app.command(name="1password-template")
def onepassword_template(
    adapter: str = typer.Argument(
        ...,
        help="Adapter type (linear, github, jira, aitrackdown)",
    ),
    vault: str = typer.Option(
        "Development",
        "--vault",
        "-v",
        help="1Password vault name for secret references",
    ),
    item: str | None = typer.Option(
        None,
        "--item",
        "-i",
        help="1Password item name (defaults to adapter name)",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (defaults to .env.1password)",
    ),
) -> None:
    """Create a .env template file with 1Password secret references.

    This creates a template file that uses op:// secret references,
    which can be used with: op run --env-file=.env.1password -- <command>

    Examples:
    --------
        # Create Linear template
        mcp-ticketer discover 1password-template linear

        # Create GitHub template with custom vault
        mcp-ticketer discover 1password-template github --vault=Production

        # Create template with custom item name
        mcp-ticketer discover 1password-template jira --item="JIRA API Keys"

    """
    # Check if op CLI is available
    status = check_op_cli_status()
    if not status["installed"]:
        console.print(
            "[red]1Password CLI not installed.[/red]\n\n"
            "Install it first:\n"
            "  macOS: brew install 1password-cli\n"
            "  Other: https://developer.1password.com/docs/cli/get-started/"
        )
        raise typer.Exit(1)

    # Set default output path
    if output is None:
        output = Path(f".env.1password.{adapter.lower()}")

    # Create loader and generate template
    loader = OnePasswordSecretsLoader(OnePasswordConfig())
    loader.create_template_file(output, adapter, vault, item)

    console.print(
        Panel.fit(
            f"[bold green]✓ Template created![/bold green]\n\n"
            f"File: {output}\n"
            f"Vault: {vault}\n"
            f"Item: {item or adapter.upper()}\n\n"
            f"[bold]Next steps:[/bold]\n"
            f"1. Create item '{item or adapter.upper()}' in 1Password vault '{vault}'\n"
            f"2. Add the required fields to the item\n"
            f"3. Test with: op run --env-file={output} -- mcp-ticketer discover show\n"
            f"4. Save config: op run --env-file={output} -- mcp-ticketer discover save",
            border_style="green",
        )
    )

    # Show template contents
    console.print("\n[bold]Template contents:[/bold]\n")
    console.print(Panel(output.read_text(), border_style="dim"))


@app.command(name="1password-test")
def onepassword_test(
    env_file: Path = typer.Option(
        ".env.1password",
        "--file",
        "-f",
        help="Path to .env file with op:// references",
    ),
) -> None:
    """Test 1Password secret resolution from .env file.

    This command loads secrets from the specified .env file and
    displays the resolved values (with sensitive data masked).

    Example:
    -------
        mcp-ticketer discover 1password-test --file=.env.1password.linear

    """
    # Check if file exists
    if not env_file.exists():
        console.print(f"[red]File not found:[/red] {env_file}")
        raise typer.Exit(1)

    # Check if op CLI is available and authenticated
    status = check_op_cli_status()
    if not status["installed"]:
        console.print("[red]1Password CLI not installed.[/red]")
        raise typer.Exit(1)

    if not status["authenticated"]:
        console.print(
            "[red]1Password CLI not authenticated.[/red]\n\n" "Run: op signin"
        )
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            f"[bold cyan]Testing 1Password Secret Resolution[/bold cyan]\n"
            f"File: {env_file}",
            border_style="cyan",
        )
    )

    # Load secrets
    loader = OnePasswordSecretsLoader(OnePasswordConfig())

    try:
        secrets = loader.load_secrets_from_env_file(env_file)

        # Display resolved secrets
        table = Table(title="Resolved Secrets")
        table.add_column("Variable", style="cyan")
        table.add_column("Value", style="green")

        for key, value in secrets.items():
            # Mask sensitive values
            display_value = _mask_sensitive(value, key)
            table.add_row(key, display_value)

        console.print(table)

        console.print(
            f"\n[green]✓ Successfully resolved {len(secrets)} secrets![/green]"
        )

        # Test discovery with these secrets
        console.print("\n[bold]Testing configuration discovery...[/bold]")
        EnvDiscovery(enable_1password=False)  # Already resolved

        # Temporarily write resolved secrets to test discovery
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as tmp:
            for key, value in secrets.items():
                tmp.write(f"{key}={value}\n")
            tmp_path = Path(tmp.name)

        try:
            # Mock the env file loading by directly providing secrets
            from ..core.env_discovery import DiscoveryResult

            DiscoveryResult()

            # Try to detect adapters from the resolved secrets
            from ..core.env_discovery import EnvDiscovery as ED

            ed = ED(enable_1password=False)
            ed.project_path = Path.cwd()

            # Manually detect from secrets dict
            linear_adapter = ed._detect_linear(secrets, str(env_file))
            if linear_adapter:
                console.print("\n[green]✓ Detected Linear configuration[/green]")
                _display_discovered_adapter(linear_adapter, ed)

            github_adapter = ed._detect_github(secrets, str(env_file))
            if github_adapter:
                console.print("\n[green]✓ Detected GitHub configuration[/green]")
                _display_discovered_adapter(github_adapter, ed)

            jira_adapter = ed._detect_jira(secrets, str(env_file))
            if jira_adapter:
                console.print("\n[green]✓ Detected JIRA configuration[/green]")
                _display_discovered_adapter(jira_adapter, ed)
        finally:
            tmp_path.unlink()

    except Exception as e:
        console.print(f"\n[red]Failed to resolve secrets:[/red] {e}")
        console.print(
            "\n[yellow]Troubleshooting:[/yellow]\n"
            "1. Check that the item exists in 1Password\n"
            "2. Verify the vault name is correct\n"
            "3. Ensure all field names match\n"
            f"4. Run: op inject --in-file={env_file} (to see detailed errors)"
        )
        raise typer.Exit(1) from None


if __name__ == "__main__":
    app()
