"""Interactive configuration wizard for MCP Ticketer."""

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..core.project_config import (
    AdapterConfig,
    AdapterType,
    ConfigResolver,
    ConfigValidator,
    HybridConfig,
    SyncStrategy,
    TicketerConfig,
)

console = Console()


def _load_existing_adapter_config(adapter_type: str) -> dict[str, Any] | None:
    """Load existing adapter configuration from project config if available.

    Args:
    ----
        adapter_type: Type of adapter (linear, jira, github, aitrackdown)

    Returns:
    -------
        Dictionary with existing configuration if available, None otherwise

    """
    config_path = Path.cwd() / ".mcp-ticketer" / "config.json"
    if not config_path.exists():
        return None

    try:
        with open(config_path) as f:
            config = json.load(f)
        return config.get("adapters", {}).get(adapter_type)
    except (json.JSONDecodeError, OSError) as e:
        console.print(f"[yellow]Warning: Could not load existing config: {e}[/yellow]")
        return None


def _mask_sensitive_value(value: str, show_chars: int = 8) -> str:
    """Mask sensitive value for display.

    Args:
    ----
        value: The sensitive value to mask
        show_chars: Number of characters to show at start (default: 8)

    Returns:
    -------
        Masked string like "ghp_1234****" or "****" for short values

    """
    if not value:
        return "****"
    if len(value) <= show_chars:
        return "****"
    return f"{value[:show_chars]}****"


def _validate_api_credentials(
    adapter_type: str,
    credentials: dict[str, str],
    credential_prompter: Callable[[], dict[str, str]] | None = None,
    max_retries: int = 3,
) -> bool:
    """Validate API credentials with real API calls.

    Args:
    ----
        adapter_type: Type of adapter (linear, github, jira)
        credentials: Dictionary with adapter-specific credentials
        credential_prompter: Optional callback to re-prompt for credentials on failure
        max_retries: Maximum retry attempts on validation failure

    Returns:
    -------
        True if validation succeeds

    Raises:
    ------
        typer.Exit: If user gives up after max retries

    """
    for attempt in range(1, max_retries + 1):
        try:
            if adapter_type == "linear":
                # Test Linear API with viewer query
                response = httpx.post(
                    "https://api.linear.app/graphql",
                    headers={"Authorization": credentials["api_key"]},
                    json={"query": "{ viewer { id name email } }"},
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    if "data" in data and "viewer" in data["data"]:
                        viewer = data["data"]["viewer"]
                        console.print(
                            f"[green]✓ Linear API key verified (user: {viewer.get('name', viewer.get('email', 'Unknown'))})[/green]"
                        )
                        return True
                    else:
                        errors = data.get("errors", [])
                        if errors:
                            error_msg = errors[0].get("message", "Unknown error")
                            raise ValueError(f"API returned error: {error_msg}")
                        raise ValueError("Invalid API response format")
                else:
                    raise ValueError(
                        f"API returned status {response.status_code}: {response.text}"
                    )

            elif adapter_type == "github":
                # Test GitHub API with user endpoint
                response = httpx.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"Bearer {credentials['token']}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    user_data = response.json()
                    login = user_data.get("login", "Unknown")
                    console.print(
                        f"[green]✓ GitHub token verified (user: {login})[/green]"
                    )
                    return True
                elif response.status_code == 401:
                    raise ValueError("Invalid token or token has expired")
                elif response.status_code == 403:
                    raise ValueError(
                        "Token lacks required permissions (need 'repo' scope)"
                    )
                else:
                    raise ValueError(
                        f"GitHub API returned {response.status_code}: {response.text}"
                    )

            elif adapter_type == "jira":
                # Test JIRA API with myself endpoint
                response = httpx.get(
                    f"{credentials['server'].rstrip('/')}/rest/api/2/myself",
                    auth=(credentials["email"], credentials["api_token"]),
                    headers={"Accept": "application/json"},
                    timeout=10.0,
                )

                if response.status_code == 200:
                    user_data = response.json()
                    name = user_data.get("displayName", credentials["email"])
                    console.print(
                        f"[green]✓ JIRA credentials verified (user: {name})[/green]"
                    )
                    return True
                elif response.status_code == 401:
                    raise ValueError("Invalid credentials or API token has expired")
                elif response.status_code == 404:
                    raise ValueError(
                        f"Invalid JIRA server URL: {credentials['server']}"
                    )
                else:
                    raise ValueError(
                        f"JIRA API returned {response.status_code}: {response.text}"
                    )

            else:
                # Unknown adapter type, skip validation
                console.print(
                    f"[yellow]Warning: No validation available for adapter '{adapter_type}'[/yellow]"
                )
                return True

        except httpx.TimeoutException:
            console.print(
                f"[red]✗ API validation timed out (attempt {attempt}/{max_retries})[/red]"
            )
        except httpx.NetworkError as e:
            console.print(
                f"[red]✗ Network error during validation: {e} (attempt {attempt}/{max_retries})[/red]"
            )
        except ValueError as e:
            console.print(
                f"[red]✗ API validation failed: {e} (attempt {attempt}/{max_retries})[/red]"
            )
        except Exception as e:
            console.print(
                f"[red]✗ Unexpected error during validation: {e} (attempt {attempt}/{max_retries})[/red]"
            )

        # Ask user if they want to retry
        if attempt < max_retries:
            retry = Confirm.ask("Re-enter credentials and try again?", default=True)
            if retry and credential_prompter:
                # Re-prompt for fresh credentials
                new_credentials = credential_prompter()
                credentials.update(new_credentials)
            elif not retry:
                console.print(
                    "[yellow]Skipping validation. Configuration saved but may not work.[/yellow]"
                )
                return True  # Allow saving unvalidated config
        else:
            console.print("[red]Max retries exceeded[/red]")
            final_choice = Confirm.ask(
                "Save configuration anyway? (it may not work)", default=False
            )
            if final_choice:
                console.print("[yellow]Configuration saved without validation[/yellow]")
                return True
            raise typer.Exit(1) from None

    return False


def _retry_setting(
    setting_name: str,
    prompt_func: Callable[[], Any],
    validate_func: Callable[[Any], tuple[bool, str | None]],
    max_retries: int = 3,
) -> Any:
    """Retry a configuration setting with validation.

    Args:
    ----
        setting_name: Human-readable name of the setting
        prompt_func: Function that prompts for the setting value
        validate_func: Function that validates the value (returns tuple of success, error_msg)
        max_retries: Maximum number of retry attempts

    Returns:
    -------
        Validated setting value

    Raises:
    ------
        typer.Exit: If max retries exceeded

    """
    for attempt in range(1, max_retries + 1):
        try:
            value = prompt_func()
            is_valid, error = validate_func(value)

            if is_valid:
                return value
            console.print(f"[red]✗ {error}[/red]")
            if attempt < max_retries:
                console.print(
                    f"[yellow]Attempt {attempt}/{max_retries} - Please try again[/yellow]"
                )
            else:
                console.print(f"[red]Failed after {max_retries} attempts[/red]")
                retry = Confirm.ask("Retry this setting?", default=True)
                if retry:
                    # Extend attempts
                    max_retries += 3
                    console.print(
                        f"[yellow]Extending retries (new limit: {max_retries})[/yellow]"
                    )
                    continue
                raise typer.Exit(1) from None
        except KeyboardInterrupt:
            console.print("\n[yellow]Configuration cancelled[/yellow]")
            raise typer.Exit(0) from None

    console.print(f"[red]Could not configure {setting_name}[/red]")
    raise typer.Exit(1)


def configure_wizard() -> None:
    """Run interactive configuration wizard."""
    console.print(
        Panel.fit(
            "[bold cyan]MCP-Ticketer Configuration Wizard[/bold cyan]\n"
            "Configure your ticketing system integration",
            border_style="cyan",
        )
    )

    # Step 1: Choose integration mode
    console.print("\n[bold]Step 1: Integration Mode[/bold]")
    console.print("1. Single Adapter (recommended for most projects)")
    console.print("2. Hybrid Mode (sync across multiple platforms)")

    mode = Prompt.ask("Select mode", choices=["1", "2"], default="1")

    if mode == "1":
        config = _configure_single_adapter()
    else:
        config = _configure_hybrid_mode()

    # Step 2: Choose where to save
    console.print("\n[bold]Step 2: Configuration Scope[/bold]")
    console.print(
        "1. Project-specific (recommended): .mcp-ticketer/config.json in project root"
    )
    console.print("2. Legacy global (deprecated): saves to project config for security")

    scope = Prompt.ask("Save configuration as", choices=["1", "2"], default="1")

    resolver = ConfigResolver()

    # Always save to project config (global config removed for security)
    resolver.save_project_config(config)
    config_path = resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH

    if scope == "2":
        console.print(
            "[yellow]Note: Global config is deprecated for security. Saving to project config instead.[/yellow]"
        )

    console.print(f"\n[green]✓[/green] Configuration saved to {config_path}")

    # Show usage instructions
    console.print("\n[bold]Usage:[/bold]")
    console.print('  CLI: [cyan]mcp-ticketer create "Task title"[/cyan]')
    console.print("  MCP: Configure Claude Desktop to use this adapter")
    console.print(
        "\nRun [cyan]mcp-ticketer configure --show[/cyan] to view your configuration"
    )


def _configure_single_adapter() -> TicketerConfig:
    """Configure a single adapter."""
    console.print("\n[bold]Select Ticketing System:[/bold]")
    console.print("1. Linear (Modern project management)")
    console.print("2. JIRA (Enterprise issue tracking)")
    console.print("3. GitHub Issues (Code-integrated tracking)")
    console.print("4. Internal/AITrackdown (File-based, no API)")

    adapter_choice = Prompt.ask(
        "Select system", choices=["1", "2", "3", "4"], default="1"
    )

    adapter_type_map = {
        "1": AdapterType.LINEAR,
        "2": AdapterType.JIRA,
        "3": AdapterType.GITHUB,
        "4": AdapterType.AITRACKDOWN,
    }

    adapter_type = adapter_type_map[adapter_choice]

    # Configure the selected adapter
    default_values: dict[str, str] = {}
    if adapter_type == AdapterType.LINEAR:
        adapter_config, default_values = _configure_linear(interactive=True)
    elif adapter_type == AdapterType.JIRA:
        adapter_config, default_values = _configure_jira(interactive=True)
    elif adapter_type == AdapterType.GITHUB:
        adapter_config, default_values = _configure_github(interactive=True)
    else:
        adapter_config, default_values = _configure_aitrackdown(interactive=True)

    # Create config with default values
    config = TicketerConfig(
        default_adapter=adapter_type.value,
        adapters={adapter_type.value: adapter_config},
        default_user=default_values.get("default_user"),
        default_project=default_values.get("default_project"),
        default_epic=default_values.get("default_epic"),
        default_tags=default_values.get("default_tags"),
    )

    return config


def _configure_linear(
    existing_config: dict[str, Any] | None = None,
    interactive: bool = True,
    api_key: str | None = None,
    team_id: str | None = None,
    team_key: str | None = None,
    **kwargs: Any,
) -> tuple[AdapterConfig, dict[str, Any]]:
    """Configure Linear adapter with option to preserve existing settings.

    Supports both interactive (wizard) and programmatic (init command) modes.

    Args:
    ----
        existing_config: Optional existing configuration to preserve/update
        interactive: If True, prompt user for missing values (default: True)
        api_key: Pre-provided API key (optional, for programmatic mode)
        team_id: Pre-provided team ID (optional, for programmatic mode)
        team_key: Pre-provided team key (optional, for programmatic mode)
        **kwargs: Additional configuration parameters

    Returns:
    -------
        Tuple of (AdapterConfig, default_values_dict)
        - AdapterConfig: Configured Linear adapter configuration
        - default_values_dict: Dictionary containing default_user, default_epic, default_project, default_tags

    """
    if interactive:
        console.print("\n[bold cyan]Linear Configuration[/bold cyan]")

    # Load existing configuration if available
    if existing_config is None and interactive:
        existing_config = _load_existing_adapter_config("linear")

    # Check if we have existing config
    has_existing = (
        existing_config is not None and existing_config.get("adapter") == "linear"
    )

    config_dict: dict[str, Any] = {"adapter": AdapterType.LINEAR.value}

    if has_existing and interactive:
        preserve = Confirm.ask(
            "Existing Linear configuration found. Preserve current settings?",
            default=True,
        )
        if preserve:
            console.print("[green]✓[/green] Keeping existing configuration")
            config_dict = existing_config.copy()

            # Allow updating specific fields
            update_fields = Confirm.ask("Update specific fields?", default=False)
            if not update_fields:
                # Extract default values before returning
                default_values = {}
                if "user_email" in config_dict:
                    default_values["default_user"] = config_dict.pop("user_email")
                if "default_epic" in config_dict:
                    default_values["default_epic"] = config_dict.pop("default_epic")
                if "default_project" in config_dict:
                    default_values["default_project"] = config_dict.pop(
                        "default_project"
                    )
                if "default_tags" in config_dict:
                    default_values["default_tags"] = config_dict.pop("default_tags")
                return AdapterConfig.from_dict(config_dict), default_values

            console.print(
                "[yellow]Enter new values or press Enter to keep current[/yellow]"
            )

    # API Key with validation loop
    current_key = config_dict.get("api_key", "") if has_existing else ""
    final_api_key = api_key or os.getenv("LINEAR_API_KEY") or ""

    if interactive:
        # Interactive mode: prompt with retry
        if final_api_key and not current_key:
            console.print("[dim]Found LINEAR_API_KEY in environment[/dim]")
            use_env = Confirm.ask("Use this API key?", default=True)
            if use_env:
                current_key = final_api_key

        # Validation loop for API key
        api_key_validated = False
        while not api_key_validated:

            def prompt_api_key() -> str:
                if current_key:
                    masked = _mask_sensitive_value(current_key)
                    api_key_prompt = f"Linear API Key [current: {masked}]"
                    return Prompt.ask(
                        api_key_prompt, password=True, default=current_key
                    )
                return Prompt.ask("Linear API Key", password=True)

            def validate_api_key(key: str) -> tuple[bool, str | None]:
                if not key or len(key) < 10:
                    return False, "API key must be at least 10 characters"
                return True, None

            final_api_key = _retry_setting("API Key", prompt_api_key, validate_api_key)

            # Validate API key with real API call
            def prompt_new_api_key() -> dict[str, str]:
                """Re-prompt for API key on validation failure."""
                new_key = Prompt.ask("Linear API Key", password=True)
                return {"api_key": new_key}

            try:
                credentials = {"api_key": final_api_key}
                api_key_validated = _validate_api_credentials(
                    "linear",
                    credentials,
                    credential_prompter=prompt_new_api_key,
                )
                # Update final_api_key with potentially updated value
                final_api_key = credentials["api_key"]
            except typer.Exit:
                # User cancelled, propagate the exit
                raise
            except Exception as e:
                console.print(f"[red]Validation error: {e}[/red]")
                retry = Confirm.ask("Re-enter API key?", default=True)
                if not retry:
                    raise typer.Exit(1) from None

    elif not final_api_key:
        raise ValueError(
            "Linear API key is required (provide api_key parameter or set LINEAR_API_KEY environment variable)"
        )

    config_dict["api_key"] = final_api_key

    # Team Key/ID (programmatic mode: use provided values, interactive: prompt)
    current_team_key = config_dict.get("team_key", "") if has_existing else ""
    config_dict.get("team_id", "") if has_existing else ""
    final_team_key = team_key or os.getenv("LINEAR_TEAM_KEY") or ""
    final_team_id = team_id or os.getenv("LINEAR_TEAM_ID") or ""

    if interactive:
        # Interactive mode: prompt for team key (preferred over team_id)
        def prompt_team_key() -> str:
            if current_team_key:
                team_key_prompt = f"Linear Team Key [current: {current_team_key}]"
                return Prompt.ask(team_key_prompt, default=current_team_key)
            return Prompt.ask("Linear Team Key (e.g., 'ENG', 'BTA')")

        def validate_team_key(key: str) -> tuple[bool, str | None]:
            if not key or len(key) < 2:
                return False, "Team key must be at least 2 characters"
            return True, None

        final_team_key = _retry_setting("Team Key", prompt_team_key, validate_team_key)
        config_dict["team_key"] = final_team_key

        # Remove team_id if present (will be resolved from team_key)
        if "team_id" in config_dict:
            del config_dict["team_id"]
    else:
        # Programmatic mode: use whichever was provided
        if final_team_key:
            config_dict["team_key"] = final_team_key
        if final_team_id:
            config_dict["team_id"] = final_team_id
        if not final_team_key and not final_team_id:
            raise ValueError(
                "Linear requires either team_key or team_id (provide parameter or set LINEAR_TEAM_KEY/LINEAR_TEAM_ID environment variable)"
            )

    # User email configuration (optional, for default assignee) - only in interactive mode
    if interactive:
        current_user_email = config_dict.get("user_email", "") if has_existing else ""

        def prompt_user_email() -> str:
            if current_user_email:
                user_email_prompt = (
                    f"Your Linear email (optional, for auto-assignment) "
                    f"[current: {current_user_email}]"
                )
                return Prompt.ask(user_email_prompt, default=current_user_email)
            return Prompt.ask(
                "Your Linear email (optional, for auto-assignment)", default=""
            )

        def validate_user_email(email: str) -> tuple[bool, str | None]:
            if not email:  # Optional field
                return True, None
            import re

            email_pattern = re.compile(
                r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            )
            if not email_pattern.match(email):
                return False, f"Invalid email format: {email}"
            return True, None

        user_email = _retry_setting(
            "User Email", prompt_user_email, validate_user_email
        )
        if user_email:
            config_dict["user_email"] = user_email
            console.print(f"[green]✓[/green] Will use {user_email} as default assignee")

        # ============================================================
        # DEFAULT VALUES SECTION (for ticket creation)
        # ============================================================

        console.print("\n[bold cyan]Default Values (Optional)[/bold cyan]")
        console.print("Configure default values for ticket creation:")

        # Default epic/project
        current_default_epic = (
            config_dict.get("default_epic", "") if has_existing else ""
        )

        def prompt_default_epic() -> str:
            if current_default_epic:
                return Prompt.ask(
                    f"Default epic/project ID (optional) [current: {current_default_epic}]",
                    default=current_default_epic,
                )
            return Prompt.ask(
                "Default epic/project ID (optional, accepts project URLs or IDs like 'PROJ-123')",
                default="",
            )

        def validate_default_epic(epic_id: str) -> tuple[bool, str | None]:
            if not epic_id:  # Optional field
                return True, None
            # Basic validation - just check it's not empty when provided
            if len(epic_id.strip()) < 2:
                return False, "Epic/project ID must be at least 2 characters"
            return True, None

        default_epic = _retry_setting(
            "Default Epic/Project", prompt_default_epic, validate_default_epic
        )
        if default_epic:
            config_dict["default_epic"] = default_epic
            config_dict["default_project"] = default_epic  # Set both for compatibility
            console.print(
                f"[green]✓[/green] Will use '{default_epic}' as default epic/project"
            )

        # Default tags
        current_default_tags = (
            config_dict.get("default_tags", []) if has_existing else []
        )

        def prompt_default_tags() -> str:
            if current_default_tags:
                tags_str = ", ".join(current_default_tags)
                return Prompt.ask(
                    f"Default tags (optional, comma-separated) [current: {tags_str}]",
                    default=tags_str,
                )
            return Prompt.ask(
                "Default tags (optional, comma-separated, e.g., 'bug,urgent')",
                default="",
            )

        def validate_default_tags(tags_input: str) -> tuple[bool, str | None]:
            if not tags_input:  # Optional field
                return True, None
            # Parse and validate tags
            tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
            if not tags:
                return False, "Please provide at least one tag or leave empty"
            # Check each tag is reasonable
            for tag in tags:
                if len(tag) < 2:
                    return False, f"Tag '{tag}' must be at least 2 characters"
                if len(tag) > 50:
                    return False, f"Tag '{tag}' is too long (max 50 characters)"
            return True, None

        default_tags_input = _retry_setting(
            "Default Tags", prompt_default_tags, validate_default_tags
        )
        if default_tags_input:
            default_tags = [
                tag.strip() for tag in default_tags_input.split(",") if tag.strip()
            ]
            config_dict["default_tags"] = default_tags
            console.print(f"[green]✓[/green] Will use tags: {', '.join(default_tags)}")

    # Validate with detailed error reporting
    is_valid, error = ConfigValidator.validate_linear_config(config_dict)

    if not is_valid:
        console.print("\n[red]❌ Configuration Validation Failed[/red]")
        console.print(f"[red]Error: {error}[/red]\n")

        # Show which settings were problematic
        console.print("[yellow]Problematic settings:[/yellow]")
        if "api_key" not in config_dict or not config_dict["api_key"]:
            console.print("  • [red]API Key[/red] - Missing or empty")
        if "team_key" not in config_dict and "team_id" not in config_dict:
            console.print(
                "  • [red]Team Key/ID[/red] - Neither team_key nor team_id provided"
            )
        if "user_email" in config_dict:
            email = config_dict["user_email"]
            import re

            if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
                console.print(f"  • [red]User Email[/red] - Invalid format: {email}")

        # Offer to retry specific settings
        console.print("\n[cyan]Options:[/cyan]")
        console.print("  1. Retry configuration from scratch")
        console.print("  2. Fix specific settings")
        console.print("  3. Exit")

        choice = Prompt.ask("Choose an option", choices=["1", "2", "3"], default="2")

        if choice == "1":
            # Recursive retry
            return _configure_linear(existing_config=None)
        if choice == "2":
            # Fix specific settings
            return _configure_linear(existing_config=config_dict)
        raise typer.Exit(1) from None

    console.print("[green]✓ Configuration validated successfully[/green]")

    # Extract default values to return separately (not part of AdapterConfig)
    default_values = {}
    if "user_email" in config_dict:
        default_values["default_user"] = config_dict.pop("user_email")
    if "default_epic" in config_dict:
        default_values["default_epic"] = config_dict.pop("default_epic")
    if "default_project" in config_dict:
        default_values["default_project"] = config_dict.pop("default_project")
    if "default_tags" in config_dict:
        default_values["default_tags"] = config_dict.pop("default_tags")

    return AdapterConfig.from_dict(config_dict), default_values


def _configure_jira(
    interactive: bool = True,
    server: str | None = None,
    email: str | None = None,
    api_token: str | None = None,
    project_key: str | None = None,
    **kwargs: Any,
) -> tuple[AdapterConfig, dict[str, Any]]:
    """Configure JIRA adapter.

    Supports both interactive (wizard) and programmatic (init command) modes.

    Args:
    ----
        interactive: If True, prompt user for missing values (default: True)
        server: Pre-provided JIRA server URL (optional)
        email: Pre-provided JIRA user email (optional)
        api_token: Pre-provided JIRA API token (optional)
        project_key: Pre-provided default project key (optional)
        **kwargs: Additional configuration parameters

    Returns:
    -------
        Tuple of (AdapterConfig, default_values_dict)
        - AdapterConfig: Configured JIRA adapter configuration
        - default_values_dict: Dictionary containing default_user, default_epic, default_project, default_tags

    """
    if interactive:
        console.print("\n[bold]Configure JIRA Integration:[/bold]")

    # Load existing configuration if available
    existing_config = _load_existing_adapter_config("jira") if interactive else None
    has_existing = existing_config is not None

    # Server URL (with existing value as default)
    existing_server = existing_config.get("server", "") if has_existing else ""
    final_server = server or os.getenv("JIRA_SERVER") or ""

    if interactive:
        if not final_server and existing_server:
            final_server = Prompt.ask(
                f"JIRA Server URL [current: {existing_server}]",
                default=existing_server,
            )
        elif not final_server:
            final_server = Prompt.ask(
                "JIRA Server URL (e.g., https://company.atlassian.net)"
            )
    elif not interactive and not final_server:
        raise ValueError(
            "JIRA server URL is required (provide server parameter or set JIRA_SERVER environment variable)"
        )

    # Email (with existing value as default)
    existing_email = existing_config.get("email", "") if has_existing else ""
    final_email = email or os.getenv("JIRA_EMAIL") or ""

    if interactive:
        if not final_email and existing_email:
            final_email = Prompt.ask(
                f"JIRA User Email [current: {existing_email}]",
                default=existing_email,
            )
        elif not final_email:
            final_email = Prompt.ask("JIRA User Email")
    elif not interactive and not final_email:
        raise ValueError(
            "JIRA email is required (provide email parameter or set JIRA_EMAIL environment variable)"
        )

    # API Token with validation loop
    existing_token = existing_config.get("api_token", "") if has_existing else ""
    final_api_token = api_token or os.getenv("JIRA_API_TOKEN") or ""

    if interactive:
        # Validation loop for JIRA credentials
        jira_validated = False
        while not jira_validated:
            if not final_api_token and existing_token:
                masked = _mask_sensitive_value(existing_token)
                console.print(
                    "[dim]Generate token at: https://id.atlassian.com/manage/api-tokens[/dim]"
                )
                final_api_token = Prompt.ask(
                    f"JIRA API Token [current: {masked}]",
                    password=True,
                    default=existing_token,
                )
            elif not final_api_token:
                console.print(
                    "[dim]Generate token at: https://id.atlassian.com/manage/api-tokens[/dim]"
                )
                final_api_token = Prompt.ask("JIRA API Token", password=True)

            # Validate JIRA credentials with real API call
            def prompt_new_jira_credentials() -> dict[str, str]:
                """Re-prompt for JIRA credentials on validation failure."""
                console.print(
                    "[dim]Generate token at: https://id.atlassian.com/manage/api-tokens[/dim]"
                )
                new_token = Prompt.ask("JIRA API Token", password=True)
                return {"api_token": new_token}

            try:
                credentials = {
                    "server": final_server,
                    "email": final_email,
                    "api_token": final_api_token,
                }
                jira_validated = _validate_api_credentials(
                    "jira",
                    credentials,
                    credential_prompter=prompt_new_jira_credentials,
                )
                # Update final_api_token with potentially updated value
                final_api_token = credentials["api_token"]
            except typer.Exit:
                # User cancelled, propagate the exit
                raise
            except Exception as e:
                console.print(f"[red]Validation error: {e}[/red]")
                retry = Confirm.ask("Re-enter credentials?", default=True)
                if not retry:
                    raise typer.Exit(1) from None
                # Reset to prompt again
                final_api_token = ""

    elif not interactive and not final_api_token:
        raise ValueError(
            "JIRA API token is required (provide api_token parameter or set JIRA_API_TOKEN environment variable)"
        )

    # Project Key (optional, with existing value as default)
    existing_project_key = (
        existing_config.get("project_key", "") if has_existing else ""
    )
    final_project_key = project_key or os.getenv("JIRA_PROJECT_KEY") or ""

    if interactive:
        if not final_project_key and existing_project_key:
            final_project_key = Prompt.ask(
                f"Default Project Key (optional, e.g., PROJ) [current: {existing_project_key}]",
                default=existing_project_key,
            )
        elif not final_project_key:
            final_project_key = Prompt.ask(
                "Default Project Key (optional, e.g., PROJ)", default=""
            )

    config_dict = {
        "adapter": AdapterType.JIRA.value,
        "server": final_server.rstrip("/"),
        "email": final_email,
        "api_token": final_api_token,
    }

    if final_project_key:
        config_dict["project_key"] = final_project_key

    # Validate
    is_valid, error = ConfigValidator.validate_jira_config(config_dict)
    if not is_valid:
        if interactive:
            console.print(f"[red]Configuration error: {error}[/red]")
            raise typer.Exit(1) from None
        raise ValueError(f"JIRA configuration validation failed: {error}")

    # ============================================================
    # DEFAULT VALUES SECTION (for ticket creation)
    # ============================================================
    default_values = {}

    if interactive:
        console.print("\n[bold cyan]Default Values (Optional)[/bold cyan]")
        console.print("Configure default values for ticket creation:")

        # Default user/assignee
        existing_user = existing_config.get("user_email", "") if has_existing else ""
        if existing_user:
            user_input = Prompt.ask(
                f"Default assignee/user (optional, JIRA username or email) [current: {existing_user}]",
                default=existing_user,
            )
        else:
            user_input = Prompt.ask(
                "Default assignee/user (optional, JIRA username or email)",
                default="",
                show_default=False,
            )
        if user_input:
            default_values["default_user"] = user_input
            console.print(
                f"[green]✓[/green] Will use '{user_input}' as default assignee"
            )

        # Default epic/project
        existing_epic = existing_config.get("default_epic", "") if has_existing else ""
        if existing_epic:
            epic_input = Prompt.ask(
                f"Default epic/project ID (optional, e.g., 'PROJ-123') [current: {existing_epic}]",
                default=existing_epic,
            )
        else:
            epic_input = Prompt.ask(
                "Default epic/project ID (optional, e.g., 'PROJ-123')",
                default="",
                show_default=False,
            )
        if epic_input:
            default_values["default_epic"] = epic_input
            default_values["default_project"] = epic_input  # Compatibility
            console.print(
                f"[green]✓[/green] Will use '{epic_input}' as default epic/project"
            )

        # Default tags
        existing_tags = existing_config.get("default_tags", []) if has_existing else []
        existing_tags_str = ", ".join(existing_tags) if existing_tags else ""
        if existing_tags_str:
            tags_input = Prompt.ask(
                f"Default tags/labels (optional, comma-separated, e.g., 'bug,urgent') [current: {existing_tags_str}]",
                default=existing_tags_str,
            )
        else:
            tags_input = Prompt.ask(
                "Default tags/labels (optional, comma-separated, e.g., 'bug,urgent')",
                default="",
                show_default=False,
            )
        if tags_input:
            tags_list = [t.strip() for t in tags_input.split(",") if t.strip()]
            if tags_list:
                default_values["default_tags"] = tags_list
                console.print(f"[green]✓[/green] Will use tags: {', '.join(tags_list)}")

    return AdapterConfig.from_dict(config_dict), default_values


def _configure_github(
    interactive: bool = True,
    token: str | None = None,
    repo_url: str | None = None,
    owner: str | None = None,
    repo: str | None = None,
    **kwargs: Any,
) -> tuple[AdapterConfig, dict[str, Any]]:
    """Configure GitHub adapter.

    Supports both interactive (wizard) and programmatic (init command) modes.

    Args:
    ----
        interactive: If True, prompt user for missing values (default: True)
        token: Pre-provided GitHub Personal Access Token (optional)
        repo_url: Pre-provided GitHub repository URL (optional, preferred)
        owner: Pre-provided repository owner (optional, fallback)
        repo: Pre-provided repository name (optional, fallback)
        **kwargs: Additional configuration parameters

    Returns:
    -------
        Tuple of (AdapterConfig, default_values_dict)
        - AdapterConfig: Configured GitHub adapter configuration
        - default_values_dict: Dictionary containing default_user, default_epic, default_project, default_tags

    """
    if interactive:
        console.print("\n[bold]Configure GitHub Integration:[/bold]")

    # Load existing configuration if available
    existing_config = _load_existing_adapter_config("github") if interactive else None
    has_existing = existing_config is not None

    # Token with validation loop
    existing_token = existing_config.get("token", "") if has_existing else ""
    final_token = token or os.getenv("GITHUB_TOKEN") or ""

    if interactive:
        github_validated = False
        while not github_validated:
            if final_token and not existing_token:
                console.print("[dim]Found GITHUB_TOKEN in environment[/dim]")
                use_env = Confirm.ask("Use this token?", default=True)
                if not use_env:
                    final_token = ""

            if not final_token:
                if existing_token:
                    # Show masked existing token as default
                    masked = _mask_sensitive_value(existing_token)
                    console.print(
                        "[dim]Create token at: https://github.com/settings/tokens/new[/dim]"
                    )
                    console.print(
                        "[dim]Required scopes: repo (or public_repo for public repos)[/dim]"
                    )
                    final_token = Prompt.ask(
                        f"GitHub Personal Access Token [current: {masked}]",
                        password=True,
                        default=existing_token,
                    )
                else:
                    console.print(
                        "[dim]Create token at: https://github.com/settings/tokens/new[/dim]"
                    )
                    console.print(
                        "[dim]Required scopes: repo (or public_repo for public repos)[/dim]"
                    )
                    final_token = Prompt.ask(
                        "GitHub Personal Access Token", password=True
                    )

            # Validate GitHub token with real API call
            def prompt_new_github_token() -> dict[str, str]:
                """Re-prompt for GitHub token on validation failure."""
                console.print(
                    "[dim]Create token at: https://github.com/settings/tokens/new[/dim]"
                )
                console.print(
                    "[dim]Required scopes: repo (or public_repo for public repos)[/dim]"
                )
                new_token = Prompt.ask("GitHub Personal Access Token", password=True)
                return {"token": new_token}

            try:
                credentials = {"token": final_token}
                github_validated = _validate_api_credentials(
                    "github", credentials, credential_prompter=prompt_new_github_token
                )
                # Update final_token with potentially updated value
                final_token = credentials["token"]
            except typer.Exit:
                # User cancelled, propagate the exit
                raise
            except Exception as e:
                console.print(f"[red]Validation error: {e}[/red]")
                retry = Confirm.ask("Re-enter token?", default=True)
                if not retry:
                    raise typer.Exit(1) from None
                # Reset to prompt again
                final_token = ""

    elif not final_token:
        raise ValueError(
            "GitHub token is required (provide token parameter or set GITHUB_TOKEN environment variable)"
        )

    # Repository URL/Owner/Repo - Prioritize repo_url, fallback to owner/repo
    existing_owner = existing_config.get("owner", "") if has_existing else ""
    existing_repo = existing_config.get("repo", "") if has_existing else ""

    final_owner = ""
    final_repo = ""

    # Step 1: Try to get URL from parameter or environment
    url_input = repo_url or os.getenv("GITHUB_REPO_URL") or ""

    # Step 2: Parse URL if provided
    if url_input:
        from ..core.url_parser import parse_github_repo_url

        parsed_owner, parsed_repo, error = parse_github_repo_url(url_input)
        if parsed_owner and parsed_repo:
            final_owner = parsed_owner
            final_repo = parsed_repo
            if interactive:
                console.print(
                    f"[dim]✓ Extracted repository: {final_owner}/{final_repo}[/dim]"
                )
        else:
            # URL parsing failed
            if interactive:
                console.print(f"[yellow]Warning: {error}[/yellow]")
            else:
                raise ValueError(f"Failed to parse GitHub repository URL: {error}")

    # Step 3: Interactive mode - prompt for URL if not provided
    if interactive and not final_owner and not final_repo:
        console.print(
            "[dim]Enter your GitHub repository URL (e.g., https://github.com/owner/repo)[/dim]"
        )

        # Show existing as default if available
        if existing_owner and existing_repo:
            existing_url = f"https://github.com/{existing_owner}/{existing_repo}"
            console.print(f"[dim]Current repository: {existing_url}[/dim]")

        # Keep prompting until we get a valid URL
        while not final_owner or not final_repo:
            from ..core.url_parser import parse_github_repo_url

            default_prompt = (
                f"https://github.com/{existing_owner}/{existing_repo}"
                if existing_owner and existing_repo
                else "https://github.com/"
            )

            url_prompt = Prompt.ask(
                "GitHub Repository URL",
                default=default_prompt,
            )

            parsed_owner, parsed_repo, error = parse_github_repo_url(url_prompt)
            if parsed_owner and parsed_repo:
                final_owner = parsed_owner
                final_repo = parsed_repo
                console.print(f"[dim]✓ Repository: {final_owner}/{final_repo}[/dim]")
                break
            else:
                console.print(f"[red]Error: {error}[/red]")
                console.print(
                    "[yellow]Please enter a valid GitHub repository URL[/yellow]"
                )

    # Step 4: Non-interactive fallback - use individual owner/repo parameters
    if not final_owner or not final_repo:
        fallback_owner = owner or os.getenv("GITHUB_OWNER") or ""
        fallback_repo = repo or os.getenv("GITHUB_REPO") or ""

        # In non-interactive mode, both must be provided if URL wasn't
        if not interactive:
            if not fallback_owner or not fallback_repo:
                raise ValueError(
                    "GitHub repository is required. Provide either:\n"
                    "  - repo_url parameter or GITHUB_REPO_URL environment variable, OR\n"
                    "  - Both owner and repo parameters (or GITHUB_OWNER/GITHUB_REPO environment variables)"
                )
            final_owner = fallback_owner
            final_repo = fallback_repo
        else:
            # Interactive mode with fallback values
            if fallback_owner:
                final_owner = fallback_owner
            if fallback_repo:
                final_repo = fallback_repo

    config_dict = {
        "adapter": AdapterType.GITHUB.value,
        "token": final_token,
        "owner": final_owner,
        "repo": final_repo,
        "project_id": f"{final_owner}/{final_repo}",  # Convenience field
    }

    # Validate
    is_valid, error = ConfigValidator.validate_github_config(config_dict)
    if not is_valid:
        if interactive:
            console.print(f"[red]Configuration error: {error}[/red]")
            raise typer.Exit(1) from None
        raise ValueError(f"GitHub configuration validation failed: {error}")

    # ============================================================
    # DEFAULT VALUES SECTION (for ticket creation)
    # ============================================================
    default_values = {}

    if interactive:
        console.print("\n[bold cyan]Default Values (Optional)[/bold cyan]")
        console.print("Configure default values for ticket creation:")

        # Default user/assignee
        existing_user = existing_config.get("user_email", "") if has_existing else ""
        if existing_user:
            user_input = Prompt.ask(
                f"Default assignee/user (optional, GitHub username) [current: {existing_user}]",
                default=existing_user,
            )
        else:
            user_input = Prompt.ask(
                "Default assignee/user (optional, GitHub username)",
                default="",
                show_default=False,
            )
        if user_input:
            default_values["default_user"] = user_input
            console.print(
                f"[green]✓[/green] Will use '{user_input}' as default assignee"
            )

        # Default epic/project (milestone for GitHub)
        existing_epic = existing_config.get("default_epic", "") if has_existing else ""
        if existing_epic:
            epic_input = Prompt.ask(
                f"Default milestone/project (optional, e.g., 'v1.0' or milestone number) [current: {existing_epic}]",
                default=existing_epic,
            )
        else:
            epic_input = Prompt.ask(
                "Default milestone/project (optional, e.g., 'v1.0' or milestone number)",
                default="",
                show_default=False,
            )
        if epic_input:
            default_values["default_epic"] = epic_input
            default_values["default_project"] = epic_input  # Compatibility
            console.print(
                f"[green]✓[/green] Will use '{epic_input}' as default milestone/project"
            )

        # Default tags (labels for GitHub)
        existing_tags = existing_config.get("default_tags", []) if has_existing else []
        existing_tags_str = ", ".join(existing_tags) if existing_tags else ""
        if existing_tags_str:
            tags_input = Prompt.ask(
                f"Default labels (optional, comma-separated, e.g., 'bug,enhancement') [current: {existing_tags_str}]",
                default=existing_tags_str,
            )
        else:
            tags_input = Prompt.ask(
                "Default labels (optional, comma-separated, e.g., 'bug,enhancement')",
                default="",
                show_default=False,
            )
        if tags_input:
            tags_list = [t.strip() for t in tags_input.split(",") if t.strip()]
            if tags_list:
                default_values["default_tags"] = tags_list
                console.print(
                    f"[green]✓[/green] Will use labels: {', '.join(tags_list)}"
                )

    return AdapterConfig.from_dict(config_dict), default_values


def _configure_aitrackdown(
    interactive: bool = True, base_path: str | None = None, **kwargs: Any
) -> tuple[AdapterConfig, dict[str, Any]]:
    """Configure AITrackdown adapter.

    Supports both interactive (wizard) and programmatic (init command) modes.

    Args:
    ----
        interactive: If True, prompt user for missing values (default: True)
        base_path: Pre-provided base path for ticket storage (optional)
        **kwargs: Additional configuration parameters

    Returns:
    -------
        Tuple of (AdapterConfig, default_values_dict)
        - AdapterConfig: Configured AITrackdown adapter configuration
        - default_values_dict: Dictionary containing default_user, default_epic, default_project, default_tags

    """
    if interactive:
        console.print("\n[bold]Configure AITrackdown (File-based):[/bold]")

    # Load existing configuration if available
    existing_config = (
        _load_existing_adapter_config("aitrackdown") if interactive else None
    )
    has_existing = existing_config is not None

    # Base path with existing value as default
    existing_base_path = (
        existing_config.get("base_path", ".aitrackdown") if has_existing else ""
    )
    final_base_path = base_path or existing_base_path or ".aitrackdown"

    if interactive:
        if existing_base_path:
            final_base_path = Prompt.ask(
                f"Base path for ticket storage [current: {existing_base_path}]",
                default=existing_base_path,
            )
        else:
            final_base_path = Prompt.ask(
                "Base path for ticket storage", default=".aitrackdown"
            )

    config_dict = {
        "adapter": AdapterType.AITRACKDOWN.value,
        "base_path": final_base_path,
    }

    # ============================================================
    # DEFAULT VALUES SECTION (for ticket creation)
    # ============================================================
    default_values = {}

    if interactive:
        console.print("\n[bold cyan]Default Values (Optional)[/bold cyan]")
        console.print("Configure default values for ticket creation:")

        # Default user/assignee
        existing_user = existing_config.get("user_email", "") if has_existing else ""
        if existing_user:
            user_input = Prompt.ask(
                f"Default assignee/user (optional) [current: {existing_user}]",
                default=existing_user,
            )
        else:
            user_input = Prompt.ask(
                "Default assignee/user (optional)", default="", show_default=False
            )
        if user_input:
            default_values["default_user"] = user_input
            console.print(
                f"[green]✓[/green] Will use '{user_input}' as default assignee"
            )

        # Default epic/project
        existing_epic = existing_config.get("default_epic", "") if has_existing else ""
        if existing_epic:
            epic_input = Prompt.ask(
                f"Default epic/project ID (optional) [current: {existing_epic}]",
                default=existing_epic,
            )
        else:
            epic_input = Prompt.ask(
                "Default epic/project ID (optional)", default="", show_default=False
            )
        if epic_input:
            default_values["default_epic"] = epic_input
            default_values["default_project"] = epic_input  # Compatibility
            console.print(
                f"[green]✓[/green] Will use '{epic_input}' as default epic/project"
            )

        # Default tags
        existing_tags = existing_config.get("default_tags", []) if has_existing else []
        existing_tags_str = ", ".join(existing_tags) if existing_tags else ""
        if existing_tags_str:
            tags_input = Prompt.ask(
                f"Default tags (optional, comma-separated) [current: {existing_tags_str}]",
                default=existing_tags_str,
            )
        else:
            tags_input = Prompt.ask(
                "Default tags (optional, comma-separated)",
                default="",
                show_default=False,
            )
        if tags_input:
            tags_list = [t.strip() for t in tags_input.split(",") if t.strip()]
            if tags_list:
                default_values["default_tags"] = tags_list
                console.print(f"[green]✓[/green] Will use tags: {', '.join(tags_list)}")

    return AdapterConfig.from_dict(config_dict), default_values


def prompt_default_values(
    adapter_type: str,
    existing_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Prompt user for default values (for ticket creation).

    This is a standalone function that can be called independently of adapter configuration.
    Used when adapter credentials exist but default values need to be set or updated.

    Args:
    ----
        adapter_type: Type of adapter (linear, jira, github, aitrackdown)
        existing_values: Optional existing default values to show as current values

    Returns:
    -------
        Dictionary containing default_user, default_epic, default_project, default_tags
        (only includes keys that were provided by the user)

    """
    console.print("\n[bold cyan]Default Values (Optional)[/bold cyan]")
    console.print("Configure default values for ticket creation:")

    default_values = {}
    existing_values = existing_values or {}

    # Default user/assignee
    current_user = existing_values.get("default_user", "")
    if current_user:
        user_input = Prompt.ask(
            f"Default assignee/user (optional) [current: {current_user}]",
            default=current_user,
            show_default=False,
        )
    else:
        user_input = Prompt.ask(
            "Default assignee/user (optional)",
            default="",
            show_default=False,
        )
    if user_input:
        default_values["default_user"] = user_input
        console.print(f"[green]✓[/green] Will use '{user_input}' as default assignee")

    # Default epic/project
    current_epic = existing_values.get("default_epic") or existing_values.get(
        "default_project", ""
    )

    # Adapter-specific messaging
    if adapter_type == "github":
        epic_label = "milestone/project"
        epic_example = "e.g., 'v1.0' or milestone number"
    elif adapter_type == "linear":
        epic_label = "epic/project ID"
        epic_example = "e.g., 'PROJ-123' or UUID"
    else:
        epic_label = "epic/project ID"
        epic_example = "e.g., 'PROJ-123'"

    if current_epic:
        epic_input = Prompt.ask(
            f"Default {epic_label} (optional) [current: {current_epic}]",
            default=current_epic,
            show_default=False,
        )
    else:
        epic_input = Prompt.ask(
            f"Default {epic_label} (optional, {epic_example})",
            default="",
            show_default=False,
        )
    if epic_input:
        default_values["default_epic"] = epic_input
        default_values["default_project"] = epic_input  # Compatibility
        console.print(
            f"[green]✓[/green] Will use '{epic_input}' as default {epic_label}"
        )

    # Default tags
    current_tags = existing_values.get("default_tags", [])
    current_tags_str = ", ".join(current_tags) if current_tags else ""

    # Adapter-specific messaging
    tags_label = "labels" if adapter_type == "github" else "tags/labels"

    if current_tags_str:
        tags_input = Prompt.ask(
            f"Default {tags_label} (optional, comma-separated) [current: {current_tags_str}]",
            default=current_tags_str,
            show_default=False,
        )
    else:
        tags_input = Prompt.ask(
            f"Default {tags_label} (optional, comma-separated, e.g., 'bug,urgent')",
            default="",
            show_default=False,
        )
    if tags_input:
        tags_list = [t.strip() for t in tags_input.split(",") if t.strip()]
        if tags_list:
            default_values["default_tags"] = tags_list
            console.print(
                f"[green]✓[/green] Will use {tags_label}: {', '.join(tags_list)}"
            )

    return default_values


def _configure_hybrid_mode() -> TicketerConfig:
    """Configure hybrid mode with multiple adapters."""
    console.print("\n[bold]Hybrid Mode Configuration[/bold]")
    console.print("Sync tickets across multiple platforms")

    # Select adapters
    console.print("\n[bold]Select adapters to sync (comma-separated):[/bold]")
    console.print("1. Linear")
    console.print("2. JIRA")
    console.print("3. GitHub")
    console.print("4. AITrackdown")

    selections = Prompt.ask(
        "Select adapters (e.g., 1,3 for Linear and GitHub)", default="1,3"
    )

    adapter_choices = [s.strip() for s in selections.split(",")]

    adapter_type_map = {
        "1": AdapterType.LINEAR,
        "2": AdapterType.JIRA,
        "3": AdapterType.GITHUB,
        "4": AdapterType.AITRACKDOWN,
    }

    selected_adapters = [
        adapter_type_map[c] for c in adapter_choices if c in adapter_type_map
    ]

    if len(selected_adapters) < 2:
        console.print("[red]Hybrid mode requires at least 2 adapters[/red]")
        raise typer.Exit(1) from None

    # Configure each adapter
    adapters = {}
    default_values: dict[str, str] = {}
    for adapter_type in selected_adapters:
        console.print(f"\n[cyan]Configuring {adapter_type.value}...[/cyan]")

        if adapter_type == AdapterType.LINEAR:
            adapter_config, adapter_defaults = _configure_linear(interactive=True)
        elif adapter_type == AdapterType.JIRA:
            adapter_config, adapter_defaults = _configure_jira(interactive=True)
        elif adapter_type == AdapterType.GITHUB:
            adapter_config, adapter_defaults = _configure_github(interactive=True)
        else:
            adapter_config, adapter_defaults = _configure_aitrackdown(interactive=True)

        adapters[adapter_type.value] = adapter_config

        # Only save defaults from the first/primary adapter
        if not default_values:
            default_values = adapter_defaults

    # Select primary adapter
    console.print("\n[bold]Select primary adapter (source of truth):[/bold]")
    for idx, adapter_type in enumerate(selected_adapters, 1):
        console.print(f"{idx}. {adapter_type.value}")

    primary_idx = int(
        Prompt.ask(
            "Primary adapter",
            choices=[str(i) for i in range(1, len(selected_adapters) + 1)],
            default="1",
        )
    )

    primary_adapter = selected_adapters[primary_idx - 1].value

    # Select sync strategy
    console.print("\n[bold]Select sync strategy:[/bold]")
    console.print("1. Primary Source (one-way: primary → others)")
    console.print("2. Bidirectional (two-way sync)")
    console.print("3. Mirror (clone tickets across all)")

    strategy_choice = Prompt.ask("Sync strategy", choices=["1", "2", "3"], default="1")

    strategy_map = {
        "1": SyncStrategy.PRIMARY_SOURCE,
        "2": SyncStrategy.BIDIRECTIONAL,
        "3": SyncStrategy.MIRROR,
    }

    sync_strategy = strategy_map[strategy_choice]

    # Create hybrid config
    hybrid_config = HybridConfig(
        enabled=True,
        adapters=[a.value for a in selected_adapters],
        primary_adapter=primary_adapter,
        sync_strategy=sync_strategy,
    )

    # Create full config with default values
    config = TicketerConfig(
        default_adapter=primary_adapter,
        adapters=adapters,
        hybrid_mode=hybrid_config,
        default_user=default_values.get("default_user"),
        default_project=default_values.get("default_project"),
        default_epic=default_values.get("default_epic"),
        default_tags=default_values.get("default_tags"),
    )

    return config


def show_current_config() -> None:
    """Show current configuration."""
    resolver = ConfigResolver()

    # Try to load configs
    project_config = resolver.load_project_config()

    console.print("[bold]Current Configuration:[/bold]\n")

    # Note about global config deprecation
    console.print(
        "[dim]Note: Global config has been deprecated for security reasons.[/dim]"
    )
    console.print("[dim]All configuration is now project-specific only.[/dim]\n")

    # Project config
    project_config_path = resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH
    if project_config_path.exists():
        console.print(f"[cyan]Project:[/cyan] {project_config_path}")
        if project_config:
            console.print(f"  Default adapter: {project_config.default_adapter}")

            if project_config.adapters:
                table = Table(title="Project Adapters")
                table.add_column("Adapter", style="cyan")
                table.add_column("Configured", style="green")

                for name, config in project_config.adapters.items():
                    configured = "✓" if config.enabled else "✗"
                    table.add_row(name, configured)

                console.print(table)

            if project_config.hybrid_mode and project_config.hybrid_mode.enabled:
                console.print("\n[bold]Hybrid Mode:[/bold] Enabled")
                console.print(
                    f"  Adapters: {', '.join(project_config.hybrid_mode.adapters)}"
                )
                console.print(
                    f"  Primary: {project_config.hybrid_mode.primary_adapter}"
                )
                console.print(
                    f"  Strategy: {project_config.hybrid_mode.sync_strategy.value}"
                )
    else:
        console.print("[yellow]No project-specific configuration found[/yellow]")

    # Show resolved config for current project
    console.print("\n[bold]Resolved Configuration (for current project):[/bold]")
    resolved = resolver.resolve_adapter_config()

    table = Table()
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")

    for key, value in resolved.items():
        # Hide sensitive values
        if any(s in key.lower() for s in ["token", "key", "password"]) and value:
            value = "***"
        table.add_row(key, str(value))

    console.print(table)


def set_adapter_config(
    adapter: str | None = None,
    api_key: str | None = None,
    project_id: str | None = None,
    team_id: str | None = None,
    global_scope: bool = False,
    **kwargs: Any,
) -> None:
    """Set specific adapter configuration values.

    Args:
    ----
        adapter: Adapter type to set as default
        api_key: API key/token
        project_id: Project ID
        team_id: Team ID (Linear)
        global_scope: Save to global config instead of project
        **kwargs: Additional adapter-specific options

    """
    resolver = ConfigResolver()

    # Load appropriate config
    if global_scope:
        config = resolver.load_global_config()
    else:
        config = resolver.load_project_config() or TicketerConfig()

    # Update default adapter
    if adapter:
        config.default_adapter = adapter
        console.print(f"[green]✓[/green] Default adapter set to: {adapter}")

    # Update adapter-specific settings
    updates = {}
    if api_key:
        updates["api_key"] = api_key
    if project_id:
        updates["project_id"] = project_id
    if team_id:
        updates["team_id"] = team_id

    updates.update(kwargs)

    if updates:
        target_adapter = adapter or config.default_adapter

        # Get or create adapter config
        if target_adapter not in config.adapters:
            config.adapters[target_adapter] = AdapterConfig(
                adapter=target_adapter, **updates
            )
        else:
            # Update existing
            existing = config.adapters[target_adapter].to_dict()
            existing.update(updates)
            config.adapters[target_adapter] = AdapterConfig.from_dict(existing)

        console.print(f"[green]✓[/green] Updated {target_adapter} configuration")

    # Save config (always to project config for security)
    resolver.save_project_config(config)
    config_path = resolver.project_path / resolver.PROJECT_CONFIG_SUBPATH

    if global_scope:
        console.print(
            "[yellow]Note: Global config deprecated for security. Saved to project config instead.[/yellow]"
        )

    console.print(f"[dim]Saved to {config_path}[/dim]")
