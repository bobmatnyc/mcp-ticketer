"""Centralized CLI utilities and common patterns."""

import asyncio
import json
import logging
import os
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..core import AdapterRegistry, Priority, Task, TicketState
from ..queue import Queue, QueueStatus, WorkerManager

# Type variable for async functions
T = TypeVar("T")

console = Console()
logger = logging.getLogger(__name__)

# Get version from package
try:
    from importlib.metadata import version

    __version__ = version("mcp-ticketer")
except Exception:
    __version__ = "2.2.2"  # Fallback to known version


def format_json_response(status: str, data: Any, message: str | None = None) -> str:
    """Format response as JSON with standard structure.

    Args:
        status: Response status - "success" or "error"
        data: Response data (dict, list, or any JSON-serializable type)
        message: Optional human-readable message

    Returns:
        JSON string with standard format

    Example:
        >>> format_json_response("success", {"id": "1M-123", "title": "Fix bug"})
        {
          "status": "success",
          "data": {"id": "1M-123", "title": "Fix bug"},
          "metadata": {
            "timestamp": "2025-12-05T10:30:00Z",
            "version": "2.2.2"
          }
        }
    """
    response = {
        "status": status,
        "data": data,
        "metadata": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": __version__,
        },
    }
    if message:
        response["message"] = message
    return json.dumps(response, indent=2, default=str)


def format_error_json(error: str | Exception, ticket_id: str | None = None) -> str:
    """Format error response as JSON.

    Args:
        error: Error message or exception
        ticket_id: Optional ticket ID that caused the error

    Returns:
        JSON error response
    """
    error_msg = str(error)
    data = {"error": error_msg}
    if ticket_id:
        data["ticket_id"] = ticket_id
    return format_json_response("error", data, message=error_msg)


def serialize_task(task: Task) -> dict[str, Any]:
    """Serialize Task object to JSON-compatible dict.

    Args:
        task: Task object to serialize

    Returns:
        Dictionary with task fields
    """
    task_dict = {
        "id": task.id,
        "title": task.title,
        "state": task.state,
        "priority": task.priority,
        "description": task.description,
        "tags": task.tags or [],
        "assignee": task.assignee,
    }

    # Add timestamps if available
    if task.created_at:
        task_dict["created_at"] = (
            task.created_at.isoformat()
            if hasattr(task.created_at, "isoformat")
            else str(task.created_at)
        )
    if task.updated_at:
        task_dict["updated_at"] = (
            task.updated_at.isoformat()
            if hasattr(task.updated_at, "isoformat")
            else str(task.updated_at)
        )

    # Add parent relationships
    if hasattr(task, "parent_epic") and task.parent_epic:
        task_dict["parent_epic"] = task.parent_epic
    if hasattr(task, "parent_issue") and task.parent_issue:
        task_dict["parent_issue"] = task.parent_issue

    # Add URL from metadata if available
    if task.metadata:
        if isinstance(task.metadata, dict):
            # Linear metadata structure
            if "linear" in task.metadata and "url" in task.metadata["linear"]:
                task_dict["url"] = task.metadata["linear"]["url"]
            # Generic url field
            elif "url" in task.metadata:
                task_dict["url"] = task.metadata["url"]

    return task_dict


class CommonPatterns:
    """Common CLI patterns and utilities."""

    # Configuration file management - PROJECT-LOCAL ONLY
    CONFIG_FILE = Path.cwd() / ".mcp-ticketer" / "config.json"

    @staticmethod
    def get_mcp_cli_path() -> str:
        """Get mcp-ticketer CLI path using PATH resolution.

        Uses shutil.which() for reliable resolution across all installation methods
        (Homebrew, pipx, venv, pip install).

        Returns:
            Absolute path to mcp-ticketer CLI executable

        Raises:
            FileNotFoundError: If mcp-ticketer is not found in PATH
        """
        import shutil

        cli_path = shutil.which("mcp-ticketer")
        if not cli_path:
            raise FileNotFoundError(
                "mcp-ticketer CLI not found in PATH. "
                "Ensure mcp-ticketer is installed and available in your PATH."
            )
        return cli_path

    @staticmethod
    def load_config() -> dict:
        """Load configuration from project-local config file with environment discovery fallback.

        SECURITY: This method ONLY reads from the current project directory
        to prevent configuration leakage across projects. It will NEVER read
        from user home directory or system-wide locations.

        Resolution order:
        1. Project-specific config (.mcp-ticketer/config.json in cwd)
        2. Environment discovery (environment variables and .env files in cwd)
        3. Default to aitrackdown adapter

        Returns:
            Configuration dictionary with adapter and config keys.
            Defaults to aitrackdown if no local config exists.

        """
        # ONLY check project-specific config in current working directory
        project_config = Path.cwd() / ".mcp-ticketer" / "config.json"
        if project_config.exists():
            # Validate that config file is actually in project directory
            try:
                if not project_config.resolve().is_relative_to(Path.cwd().resolve()):
                    logger.error(
                        f"Security violation: Config file {project_config} "
                        "is not within project directory"
                    )
                    raise ValueError(
                        f"Security violation: Config file {project_config} "
                        "is not within project directory"
                    )
            except (ValueError, RuntimeError):
                # is_relative_to may raise ValueError in some cases
                pass

            try:
                with open(project_config) as f:
                    config = json.load(f)
                    logger.info(
                        f"Loaded configuration from project-local: {project_config}"
                    )
                    return config
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"Could not load project config: {e}, using defaults")
                console.print(
                    f"[yellow]Warning: Could not load project config: {e}[/yellow]"
                )

        # Try environment discovery as fallback
        try:
            from ..core.config import ConfigurationManager

            config_manager = ConfigurationManager()
            app_config = config_manager.load_config()

            # Convert AppConfig to legacy dict format for CLI compatibility
            enabled_adapters = app_config.get_enabled_adapters()
            if enabled_adapters:
                # Use the first enabled adapter as default
                default_adapter = (
                    app_config.default_adapter or list(enabled_adapters.keys())[0]
                )

                # Convert to legacy format
                legacy_config = {"default_adapter": default_adapter, "adapters": {}}

                # Convert adapter configs to dict format
                for name, adapter_config in enabled_adapters.items():
                    if hasattr(adapter_config, "model_dump"):
                        legacy_config["adapters"][name] = adapter_config.model_dump(
                            exclude_none=False
                        )
                    elif hasattr(adapter_config, "dict"):
                        legacy_config["adapters"][name] = adapter_config.dict()
                    else:
                        legacy_config["adapters"][name] = adapter_config

                logger.info(
                    f"Loaded configuration from environment discovery: {list(enabled_adapters.keys())}"
                )
                return legacy_config

        except Exception as e:
            logger.warning(f"Environment discovery failed: {e}")

        # Default to aitrackdown with local base path
        logger.info("No project-local config found, defaulting to aitrackdown adapter")
        return {"adapter": "aitrackdown", "config": {"base_path": ".aitrackdown"}}

    @staticmethod
    def save_config(config: dict) -> None:
        """Save configuration to project-local config file ONLY.

        SECURITY: This method ONLY saves to the current project directory
        to prevent configuration leakage across projects.
        """
        project_config = Path.cwd() / ".mcp-ticketer" / "config.json"
        project_config.parent.mkdir(parents=True, exist_ok=True)
        with open(project_config, "w") as f:
            json.dump(config, f, indent=2)
        logger.info(f"Saved configuration to project-local: {project_config}")

    @staticmethod
    def merge_config(updates: dict) -> dict:
        """Merge updates into existing config."""
        config = CommonPatterns.load_config()

        # Handle default_adapter
        if "default_adapter" in updates:
            config["default_adapter"] = updates["default_adapter"]

        # Handle adapter-specific configurations
        if "adapters" in updates:
            if "adapters" not in config:
                config["adapters"] = {}
            for adapter_name, adapter_config in updates["adapters"].items():
                if adapter_name not in config["adapters"]:
                    config["adapters"][adapter_name] = {}
                config["adapters"][adapter_name].update(adapter_config)

        return config

    @staticmethod
    def get_adapter(
        override_adapter: str | None = None, override_config: dict | None = None
    ) -> Any:
        """Get configured adapter instance with environment variable support."""
        config = CommonPatterns.load_config()

        # Use override adapter if provided, otherwise use default
        if override_adapter:
            adapter_type = override_adapter
            # If we have a stored config for this adapter, use it
            adapters_config = config.get("adapters", {})
            adapter_config = adapters_config.get(adapter_type, {})
            # Override with provided config if any
            if override_config:
                adapter_config.update(override_config)
        else:
            # Use default adapter from config
            adapter_type = config.get("default_adapter", "aitrackdown")
            # Get config for the default adapter
            adapters_config = config.get("adapters", {})
            adapter_config = adapters_config.get(adapter_type, {})

        # Fallback to legacy config format for backward compatibility
        if not adapter_config and "config" in config:
            adapter_config = config["config"]

        # Add environment variables for authentication
        adapter_config = CommonPatterns._add_env_auth(adapter_type, adapter_config)

        return AdapterRegistry.get_adapter(adapter_type, adapter_config)

    @staticmethod
    def _add_env_auth(adapter_type: str, adapter_config: dict) -> dict:
        """Add environment variable authentication to adapter config."""
        auth_mapping = {
            "linear": [("api_key", "LINEAR_API_KEY")],
            "github": [("api_key", "GITHUB_TOKEN"), ("token", "GITHUB_TOKEN")],
            "jira": [("api_token", "JIRA_ACCESS_TOKEN"), ("email", "JIRA_ACCESS_USER")],
        }

        if adapter_type in auth_mapping:
            for config_key, env_var in auth_mapping[adapter_type]:
                if not adapter_config.get(config_key):
                    env_value = os.getenv(env_var)
                    if env_value:
                        adapter_config[config_key] = env_value

        return adapter_config

    @staticmethod
    def queue_operation(
        ticket_data: dict[str, Any],
        operation: str,
        adapter_name: str | None = None,
        show_progress: bool = True,
    ) -> str:
        """Queue an operation and optionally start the worker."""
        if not adapter_name:
            config = CommonPatterns.load_config()
            adapter_name = config.get("default_adapter", "aitrackdown")

        # Add to queue with explicit project directory
        from pathlib import Path

        queue = Queue()
        queue_id = queue.add(
            ticket_data=ticket_data,
            adapter=adapter_name,
            operation=operation,
            project_dir=str(Path.cwd()),  # Explicitly pass current project directory
        )

        if show_progress:
            console.print(f"[green]✓[/green] Queued {operation}: {queue_id}")
            console.print(
                "[dim]Use 'mcp-ticketer check {queue_id}' to check progress[/dim]"
            )

        # Start worker if needed
        manager = WorkerManager()
        if manager.start_if_needed():
            if show_progress:
                console.print("[dim]Worker started to process request[/dim]")

        return queue_id

    @staticmethod
    def display_ticket_table(tickets: list[Task], title: str = "Tickets") -> None:
        """Display tickets in a formatted table."""
        if not tickets:
            console.print("[yellow]No tickets found[/yellow]")
            return

        table = Table(title=title)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Title", style="white")
        table.add_column("State", style="green")
        table.add_column("Priority", style="yellow")
        table.add_column("Assignee", style="blue")

        for ticket in tickets:
            table.add_row(
                ticket.id or "N/A",
                ticket.title,
                ticket.state,
                ticket.priority,
                ticket.assignee or "-",
            )

        console.print(table)

    @staticmethod
    def display_ticket_details(ticket: Task, comments: list | None = None) -> None:
        """Display detailed ticket information."""
        console.print(f"\n[bold]Ticket: {ticket.id}[/bold]")
        console.print(f"Title: {ticket.title}")
        console.print(f"State: [green]{ticket.state}[/green]")
        console.print(f"Priority: [yellow]{ticket.priority}[/yellow]")

        if ticket.description:
            console.print("\n[dim]Description:[/dim]")
            console.print(ticket.description)

        if ticket.tags:
            console.print(f"\nTags: {', '.join(ticket.tags)}")

        if ticket.assignee:
            console.print(f"Assignee: {ticket.assignee}")

        # Display comments if provided
        if comments:
            console.print(f"\n[bold]Comments ({len(comments)}):[/bold]")
            for comment in comments:
                console.print(f"\n[dim]{comment.created_at} - {comment.author}:[/dim]")
                console.print(comment.content)

    @staticmethod
    def display_queue_status() -> None:
        """Display queue and worker status."""
        queue = Queue()
        manager = WorkerManager()

        # Get queue stats
        stats = queue.get_stats()
        pending = stats.get(QueueStatus.PENDING.value, 0)

        # Show queue status
        console.print("[bold]Queue Status:[/bold]")
        console.print(f"  Pending: {pending}")
        console.print(f"  Processing: {stats.get(QueueStatus.PROCESSING.value, 0)}")
        console.print(f"  Completed: {stats.get(QueueStatus.COMPLETED.value, 0)}")
        console.print(f"  Failed: {stats.get(QueueStatus.FAILED.value, 0)}")

        # Show worker status
        worker_status = manager.get_status()
        if worker_status["running"]:
            console.print(
                f"\n[green]● Worker is running[/green] (PID: {worker_status.get('pid')})"
            )
        else:
            console.print("\n[red]○ Worker is not running[/red]")
            if pending > 0:
                console.print(
                    "[yellow]Note: There are pending items. Start worker with 'mcp-ticketer queue start'[/yellow]"
                )


def async_command(f: Callable[..., Any]) -> Callable[..., Any]:
    """Handle async CLI commands via decorator."""

    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return asyncio.run(f(*args, **kwargs))

    return wrapper


def with_adapter(f: Callable[..., Any]) -> Callable[..., Any]:
    """Inject adapter instance into CLI commands via decorator."""

    @wraps(f)
    def wrapper(adapter: str | None = None, *args: Any, **kwargs: Any) -> Any:
        adapter_instance = CommonPatterns.get_adapter(override_adapter=adapter)
        return f(adapter_instance, *args, **kwargs)

    return wrapper


def with_progress(
    message: str = "Processing...",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Show progress spinner for long-running operations via decorator."""

    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description=message, total=None)
                return f(*args, **kwargs)

        return wrapper

    return decorator


def validate_required_fields(
    **field_map: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Validate required fields are provided via decorator."""

    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            missing_fields = []
            for field_name, display_name in field_map.items():
                if field_name in kwargs and kwargs[field_name] is None:
                    missing_fields.append(display_name)

            if missing_fields:
                console.print(
                    f"[red]Error:[/red] Missing required fields: {', '.join(missing_fields)}"
                )
                raise typer.Exit(1) from None

            return f(*args, **kwargs)

        return wrapper

    return decorator


def handle_adapter_errors(f: Callable[..., Any]) -> Callable[..., Any]:
    """Handle common adapter errors gracefully via decorator."""

    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return f(*args, **kwargs)
        except ConnectionError as e:
            console.print(f"[red]Connection Error:[/red] {e}")
            console.print("Check your network connection and adapter configuration")
            raise typer.Exit(1) from None
        except ValueError as e:
            console.print(f"[red]Configuration Error:[/red] {e}")
            console.print("Run 'mcp-ticketer init' to configure your adapter")
            raise typer.Exit(1) from None
        except Exception as e:
            console.print(f"[red]Unexpected Error:[/red] {e}")
            raise typer.Exit(1) from None

    return wrapper


class ConfigValidator:
    """Configuration validation utilities."""

    @staticmethod
    def validate_adapter_config(adapter_type: str, config: dict) -> list[str]:
        """Validate adapter configuration and return list of issues."""
        issues = []

        validation_rules = {
            "github": [
                ("token", "GitHub token"),
                ("owner", "Repository owner"),
                ("repo", "Repository name"),
            ],
            "jira": [
                ("server", "JIRA server URL"),
                ("email", "User email"),
                ("api_token", "API token"),
            ],
            "linear": [
                ("api_key", "API key"),
                ("team_key", "Team key"),
            ],
            "aitrackdown": [
                ("base_path", "Base path"),
            ],
        }

        if adapter_type in validation_rules:
            for field, display_name in validation_rules[adapter_type]:
                if not config.get(field):
                    env_var = ConfigValidator._get_env_var(adapter_type, field)
                    if env_var and not os.getenv(env_var):
                        issues.append(
                            f"Missing {display_name} (config.{field} or {env_var})"
                        )

        return issues

    @staticmethod
    def _get_env_var(adapter_type: str, field: str) -> str | None:
        """Get corresponding environment variable name for a config field."""
        env_mapping = {
            "github": {
                "token": "GITHUB_TOKEN",
                "owner": "GITHUB_OWNER",
                "repo": "GITHUB_REPO",
            },
            "jira": {
                "api_token": "JIRA_API_TOKEN",
                "email": "JIRA_EMAIL",
                "server": "JIRA_SERVER",
            },
            "linear": {"api_key": "LINEAR_API_KEY"},
        }
        return env_mapping.get(adapter_type, {}).get(field)


class CommandBuilder:
    """Builder for common CLI command patterns."""

    def __init__(self) -> None:
        self._validators: list[Callable[..., Any]] = []
        self._handlers: list[Callable[..., Any]] = []
        self._decorators: list[Callable[..., Any]] = []

    def with_adapter_validation(self) -> "CommandBuilder":
        """Add adapter configuration validation."""
        self._validators.append(self._validate_adapter)
        return self

    def with_async_support(self) -> "CommandBuilder":
        """Add async support to command."""
        self._decorators.append(async_command)
        return self

    def with_error_handling(self) -> "CommandBuilder":
        """Add error handling decorator."""
        self._decorators.append(handle_adapter_errors)
        return self

    def with_progress(self, message: str = "Processing...") -> "CommandBuilder":
        """Add progress spinner."""
        self._decorators.append(with_progress(message))
        return self

    def build(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Build the decorated function."""
        decorated_func = func
        for decorator in reversed(self._decorators):
            decorated_func = decorator(decorated_func)
        return decorated_func

    def _validate_adapter(self, *args: Any, **kwargs: Any) -> None:
        """Validate adapter configuration."""
        config = CommonPatterns.load_config()
        default_adapter = config.get("default_adapter", "aitrackdown")
        adapter_config = config.get("adapters", {}).get(default_adapter, {})

        issues = ConfigValidator.validate_adapter_config(
            default_adapter, adapter_config
        )
        if issues:
            console.print("[red]Configuration Issues:[/red]")
            for issue in issues:
                console.print(f"  • {issue}")
            console.print("Run 'mcp-ticketer init' to fix configuration")
            raise typer.Exit(1) from None


def create_standard_ticket_command(operation: str) -> Callable[..., str]:
    """Create a standard ticket operation command."""

    def command_template(
        ticket_id: str | None = None,
        title: str | None = None,
        description: str | None = None,
        priority: Priority | None = None,
        state: TicketState | None = None,
        assignee: str | None = None,
        tags: list[str] | None = None,
        adapter: str | None = None,
    ) -> str:
        """Template for ticket commands."""
        # Build ticket data
        ticket_data = {}
        if ticket_id:
            ticket_data["ticket_id"] = ticket_id
        if title:
            ticket_data["title"] = title
        if description:
            ticket_data["description"] = description
        if priority:
            ticket_data["priority"] = (
                priority.value if hasattr(priority, "value") else priority
            )
        if state:
            ticket_data["state"] = state.value if hasattr(state, "value") else state
        if assignee:
            ticket_data["assignee"] = assignee
        if tags:
            ticket_data["tags"] = tags

        # Queue the operation
        queue_id = CommonPatterns.queue_operation(ticket_data, operation, adapter)

        # Show confirmation
        console.print(f"[green]✓[/green] Queued {operation}: {queue_id}")
        return queue_id

    return command_template


# Reusable command components
class TicketCommands:
    """Reusable ticket command implementations."""

    @staticmethod
    @async_command
    @handle_adapter_errors
    async def list_tickets(
        adapter_instance: Any,
        state: TicketState | None = None,
        priority: Priority | None = None,
        limit: int = 10,
    ) -> None:
        """List tickets with filters."""
        filters = {}
        if state:
            filters["state"] = state
        if priority:
            filters["priority"] = priority

        tickets = await adapter_instance.list(limit=limit, filters=filters)
        CommonPatterns.display_ticket_table(tickets)

    @staticmethod
    @async_command
    @handle_adapter_errors
    async def show_ticket(
        adapter_instance: Any, ticket_id: str, show_comments: bool = False
    ) -> None:
        """Show ticket details."""
        ticket = await adapter_instance.read(ticket_id)
        if not ticket:
            console.print(f"[red]✗[/red] Ticket not found: {ticket_id}")
            raise typer.Exit(1) from None

        comments = None
        if show_comments:
            comments = await adapter_instance.get_comments(ticket_id)

        CommonPatterns.display_ticket_details(ticket, comments)

    @staticmethod
    def create_ticket(
        title: str,
        description: str | None = None,
        priority: Priority = Priority.MEDIUM,
        tags: list[str] | None = None,
        assignee: str | None = None,
        adapter: str | None = None,
    ) -> str:
        """Create a new ticket."""
        ticket_data = {
            "title": title,
            "description": description,
            "priority": priority.value if isinstance(priority, Priority) else priority,
            "tags": tags or [],
            "assignee": assignee,
        }

        return CommonPatterns.queue_operation(ticket_data, "create", adapter)

    @staticmethod
    def update_ticket(
        ticket_id: str, updates: dict[str, Any], adapter: str | None = None
    ) -> str:
        """Update a ticket."""
        if not updates:
            console.print("[yellow]No updates specified[/yellow]")
            raise typer.Exit(1) from None

        updates["ticket_id"] = ticket_id
        return CommonPatterns.queue_operation(updates, "update", adapter)

    @staticmethod
    def transition_ticket(
        ticket_id: str, state: TicketState, adapter: str | None = None
    ) -> str:
        """Transition ticket state."""
        ticket_data = {
            "ticket_id": ticket_id,
            "state": state.value if hasattr(state, "value") else state,
        }

        return CommonPatterns.queue_operation(ticket_data, "transition", adapter)
