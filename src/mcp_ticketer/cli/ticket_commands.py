"""Ticket management commands."""

import asyncio
import json
import os
from enum import Enum
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from ..core import AdapterRegistry, Priority, TicketState
from ..core.models import Comment, SearchQuery
from ..queue import Queue, QueueStatus, WorkerManager
from ..queue.health_monitor import HealthStatus, QueueHealthMonitor
from ..queue.ticket_registry import TicketRegistry


# Moved from main.py to avoid circular import
class AdapterType(str, Enum):
    """Available adapter types."""

    AITRACKDOWN = "aitrackdown"
    LINEAR = "linear"
    JIRA = "jira"
    GITHUB = "github"


app = typer.Typer(
    name="ticket",
    help="Ticket management operations (create, list, update, search, etc.)",
)
console = Console()


# Configuration functions (moved from main.py to avoid circular import)
def load_config(project_dir: Path | None = None) -> dict:
    """Load configuration from project-local config file."""
    import logging

    logger = logging.getLogger(__name__)
    base_dir = project_dir or Path.cwd()
    project_config = base_dir / ".mcp-ticketer" / "config.json"

    if project_config.exists():
        try:
            with open(project_config) as f:
                config = json.load(f)
                logger.info(f"Loaded configuration from: {project_config}")
                return config
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load project config: {e}, using defaults")
            console.print(
                f"[yellow]Warning: Could not load project config: {e}[/yellow]"
            )

    logger.info("No project-local config found, defaulting to aitrackdown adapter")
    return {"adapter": "aitrackdown", "config": {"base_path": ".aitrackdown"}}


def save_config(config: dict) -> None:
    """Save configuration to project-local config file."""
    import logging

    logger = logging.getLogger(__name__)
    project_config = Path.cwd() / ".mcp-ticketer" / "config.json"
    project_config.parent.mkdir(parents=True, exist_ok=True)
    with open(project_config, "w") as f:
        json.dump(config, f, indent=2)
    logger.info(f"Saved configuration to: {project_config}")


def get_adapter(
    override_adapter: str | None = None, override_config: dict | None = None
) -> Any:
    """Get configured adapter instance."""
    config = load_config()

    if override_adapter:
        adapter_type = override_adapter
        adapters_config = config.get("adapters", {})
        adapter_config = adapters_config.get(adapter_type, {})
        if override_config:
            adapter_config.update(override_config)
    else:
        adapter_type = config.get("default_adapter", "aitrackdown")
        adapters_config = config.get("adapters", {})
        adapter_config = adapters_config.get(adapter_type, {})

    if not adapter_config and "config" in config:
        adapter_config = config["config"]

    # Add environment variables for authentication
    if adapter_type == "linear":
        if not adapter_config.get("api_key"):
            adapter_config["api_key"] = os.getenv("LINEAR_API_KEY")
    elif adapter_type == "github":
        if not adapter_config.get("api_key") and not adapter_config.get("token"):
            adapter_config["api_key"] = os.getenv("GITHUB_TOKEN")
    elif adapter_type == "jira":
        if not adapter_config.get("api_token"):
            adapter_config["api_token"] = os.getenv("JIRA_ACCESS_TOKEN")
        if not adapter_config.get("email"):
            adapter_config["email"] = os.getenv("JIRA_ACCESS_USER")

    return AdapterRegistry.get_adapter(adapter_type, adapter_config)


def _discover_from_env_files() -> str | None:
    """Discover adapter configuration from .env or .env.local files.

    Returns:
        Adapter name if discovered, None otherwise

    """
    import logging
    from pathlib import Path

    logger = logging.getLogger(__name__)

    # Check .env.local first, then .env
    env_files = [".env.local", ".env"]

    for env_file in env_files:
        env_path = Path.cwd() / env_file
        if env_path.exists():
            try:
                # Simple .env parsing (key=value format)
                env_vars = {}
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            env_vars[key.strip()] = value.strip().strip("\"'")

                # Check for adapter-specific variables
                if env_vars.get("LINEAR_API_KEY"):
                    logger.info(f"Discovered Linear configuration in {env_file}")
                    return "linear"
                elif env_vars.get("GITHUB_TOKEN"):
                    logger.info(f"Discovered GitHub configuration in {env_file}")
                    return "github"
                elif env_vars.get("JIRA_SERVER"):
                    logger.info(f"Discovered JIRA configuration in {env_file}")
                    return "jira"

            except Exception as e:
                logger.warning(f"Could not read {env_file}: {e}")

    return None


def _save_adapter_to_config(adapter_name: str) -> None:
    """Save adapter configuration to config file.

    Args:
        adapter_name: Name of the adapter to save as default

    """
    import logging

    from .main import save_config

    logger = logging.getLogger(__name__)

    try:
        config = load_config()
        config["default_adapter"] = adapter_name

        # Ensure adapters section exists
        if "adapters" not in config:
            config["adapters"] = {}

        # Add basic adapter config if not exists
        if adapter_name not in config["adapters"]:
            if adapter_name == "aitrackdown":
                config["adapters"][adapter_name] = {"base_path": ".aitrackdown"}
            else:
                config["adapters"][adapter_name] = {"type": adapter_name}

        save_config(config)
        logger.info(f"Saved {adapter_name} as default adapter")

    except Exception as e:
        logger.warning(f"Could not save adapter configuration: {e}")


@app.command()
def create(
    title: str = typer.Argument(..., help="Ticket title"),
    description: str | None = typer.Option(
        None, "--description", "-d", help="Ticket description"
    ),
    priority: Priority = typer.Option(
        Priority.MEDIUM, "--priority", "-p", help="Priority level"
    ),
    tags: list[str] | None = typer.Option(
        None,
        "--tags",  # PRIMARY (matches MCP)
        "--tag",  # ALIAS (backward compatibility)
        "-t",  # SHORT FORM
        help="Tags (can be specified multiple times)",
    ),
    assignee: str | None = typer.Option(
        None, "--assignee", "-a", help="Assignee username"
    ),
    parent_epic: str | None = typer.Option(
        None,
        "--parent-epic",  # PRIMARY (matches MCP)
        "--epic",  # ALIAS (backward compatibility)
        "--project",  # ALIAS (backward compatibility)
        "-e",  # SHORT FORM
        help="Parent epic/project ID",
    ),
    wait: bool = typer.Option(
        False,
        "--wait",
        "-w",
        help="Wait for operation to complete (synchronous mode, returns actual ticket ID)",
    ),
    timeout: float = typer.Option(
        30.0,
        "--timeout",
        help="Timeout in seconds for --wait mode (default: 30)",
    ),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    adapter: AdapterType | None = typer.Option(
        None, "--adapter", help="Override default adapter"
    ),
) -> None:
    """Create a new ticket with comprehensive health checks."""
    from .utils import format_error_json, format_json_response, serialize_task

    # IMMEDIATE HEALTH CHECK - Critical for reliability
    health_monitor = QueueHealthMonitor()
    health = health_monitor.check_health()

    # Display health status
    if health["status"] == HealthStatus.CRITICAL:
        console.print("[red]🚨 CRITICAL: Queue system has serious issues![/red]")
        for alert in health["alerts"]:
            if alert["level"] == "critical":
                console.print(f"[red]  • {alert['message']}[/red]")

        # Attempt auto-repair
        console.print("[yellow]Attempting automatic repair...[/yellow]")
        repair_result = health_monitor.auto_repair()

        if repair_result["actions_taken"]:
            for action in repair_result["actions_taken"]:
                console.print(f"[yellow]  ✓ {action}[/yellow]")

            # Re-check health after repair
            health = health_monitor.check_health()
            if health["status"] == HealthStatus.CRITICAL:
                console.print(
                    "[red]❌ Auto-repair failed. Manual intervention required.[/red]"
                )
                console.print(
                    "[red]Cannot safely create ticket. Please check system status.[/red]"
                )
                raise typer.Exit(1) from None
            else:
                console.print(
                    "[green]✓ Auto-repair successful. Proceeding with ticket creation.[/green]"
                )
        else:
            console.print(
                "[red]❌ No repair actions available. Manual intervention required.[/red]"
            )
            raise typer.Exit(1) from None

    elif health["status"] == HealthStatus.WARNING:
        console.print("[yellow]⚠️  Warning: Queue system has minor issues[/yellow]")
        for alert in health["alerts"]:
            if alert["level"] == "warning":
                console.print(f"[yellow]  • {alert['message']}[/yellow]")
        console.print("[yellow]Proceeding with ticket creation...[/yellow]")

    # Get the adapter name with priority: 1) argument, 2) config, 3) .env files, 4) default
    if adapter:
        # Priority 1: Command-line argument - save to config for future use
        adapter_name = adapter.value
        _save_adapter_to_config(adapter_name)
    else:
        # Priority 2: Check existing config
        config = load_config()
        adapter_name = config.get("default_adapter")

        if not adapter_name or adapter_name == "aitrackdown":
            # Priority 3: Check .env files and save if found
            env_adapter = _discover_from_env_files()
            if env_adapter:
                adapter_name = env_adapter
                _save_adapter_to_config(adapter_name)
            else:
                # Priority 4: Default
                adapter_name = "aitrackdown"

    # Create task data
    # Import Priority for type checking
    from ..core.models import Priority as PriorityEnum

    task_data = {
        "title": title,
        "description": description,
        "priority": priority.value if isinstance(priority, PriorityEnum) else priority,
        "tags": tags or [],
        "assignee": assignee,
        "parent_epic": parent_epic,
    }

    # WORKAROUND: Use direct operation for Linear adapter to bypass worker subprocess issue
    if adapter_name == "linear":
        console.print(
            "[yellow]⚠️[/yellow]  Using direct operation for Linear adapter (bypassing queue)"
        )
        try:
            # Load configuration and create adapter directly
            config = load_config()
            adapter_config = config.get("adapters", {}).get(adapter_name, {})

            # Import and create adapter
            from ..core.registry import AdapterRegistry

            adapter_instance = AdapterRegistry.get_adapter(adapter_name, adapter_config)

            # Create task directly
            from ..core.models import Priority, Task

            task = Task(
                title=task_data["title"],
                description=task_data.get("description"),
                priority=(
                    Priority(task_data["priority"])
                    if task_data.get("priority")
                    else Priority.MEDIUM
                ),
                tags=task_data.get("tags", []),
                assignee=task_data.get("assignee"),
                parent_epic=task_data.get("parent_epic"),
            )

            # Create ticket synchronously
            import asyncio

            result = asyncio.run(adapter_instance.create(task))

            if output_json:
                data = serialize_task(result)
                console.print(
                    format_json_response(
                        "success", data, message="Ticket created successfully"
                    )
                )
            else:
                console.print(
                    f"[green]✓[/green] Ticket created successfully: {result.id}"
                )
                console.print(f"  Title: {result.title}")
                console.print(f"  Priority: {result.priority}")
                console.print(f"  State: {result.state}")
                # Get URL from metadata if available
                if (
                    result.metadata
                    and "linear" in result.metadata
                    and "url" in result.metadata["linear"]
                ):
                    console.print(f"  URL: {result.metadata['linear']['url']}")

            return result.id

        except Exception as e:
            if output_json:
                console.print(format_error_json(e))
            else:
                console.print(f"[red]❌[/red] Failed to create ticket: {e}")
            raise

    # Use queue for other adapters
    queue = Queue()
    queue_id = queue.add(
        ticket_data=task_data,
        adapter=adapter_name,
        operation="create",
        project_dir=str(Path.cwd()),  # Explicitly pass current project directory
    )

    # Register in ticket registry for tracking
    registry = TicketRegistry()
    registry.register_ticket_operation(
        queue_id, adapter_name, "create", title, task_data
    )

    # Start worker if needed - must happen before polling
    manager = WorkerManager()
    worker_started = manager.start_if_needed()

    if worker_started:
        if not output_json:
            console.print("[dim]Worker started to process request[/dim]")

    # SYNCHRONOUS MODE: Poll until completion if --wait flag is set
    if wait:
        if not output_json:
            console.print(
                f"[yellow]⏳[/yellow] Waiting for operation to complete (timeout: {timeout}s)..."
            )

        try:
            # Poll the queue until operation completes
            completed_item = queue.poll_until_complete(queue_id, timeout=timeout)

            # Extract result data
            result = completed_item.result

            # Extract ticket ID from result
            ticket_id = result.get("id") if result else queue_id

            if output_json:
                # Return actual ticket data in JSON format
                data = result if result else {"queue_id": queue_id}
                console.print(
                    format_json_response(
                        "success", data, message="Ticket created successfully"
                    )
                )
            else:
                # Display ticket creation success with actual ID
                console.print(
                    f"[green]✓[/green] Ticket created successfully: {ticket_id}"
                )
                console.print(f"  Title: {title}")
                console.print(f"  Priority: {priority}")

                # Display additional metadata if available
                if result:
                    if "url" in result:
                        console.print(f"  URL: {result['url']}")
                    if "state" in result:
                        console.print(f"  State: {result['state']}")

            return ticket_id

        except TimeoutError as e:
            if output_json:
                console.print(format_error_json(str(e), queue_id=queue_id))
            else:
                console.print(f"[red]❌[/red] Operation timed out after {timeout}s")
                console.print(f"  Queue ID: {queue_id}")
                console.print(
                    f"  Use 'mcp-ticketer ticket check {queue_id}' to check status later"
                )
            raise typer.Exit(1) from None

        except RuntimeError as e:
            if output_json:
                console.print(format_error_json(str(e), queue_id=queue_id))
            else:
                console.print(f"[red]❌[/red] Operation failed: {e}")
                console.print(f"  Queue ID: {queue_id}")
            raise typer.Exit(1) from None

    # ASYNCHRONOUS MODE (default): Return queue ID immediately
    else:
        if output_json:
            data = {
                "queue_id": queue_id,
                "title": title,
                "priority": priority.value if hasattr(priority, "value") else priority,
                "adapter": adapter_name,
                "status": "queued",
            }
            console.print(
                format_json_response("success", data, message="Ticket creation queued")
            )
        else:
            console.print(f"[green]✓[/green] Queued ticket creation: {queue_id}")
            console.print(f"  Title: {title}")
            console.print(f"  Priority: {priority}")
            console.print(f"  Adapter: {adapter_name}")
            console.print(
                "[dim]Use 'mcp-ticketer ticket check {queue_id}' to check progress[/dim]"
            )

            # Give immediate feedback on processing
            import time

            time.sleep(1)  # Brief pause to let worker start

            # Check if item is being processed
            item = queue.get_item(queue_id)
            if item and item.status == QueueStatus.PROCESSING:
                console.print("[green]✓ Item is being processed by worker[/green]")
            elif item and item.status == QueueStatus.PENDING:
                console.print("[yellow]⏳ Item is queued for processing[/yellow]")
            else:
                console.print(
                    "[red]⚠️  Item status unclear - check with 'mcp-ticketer ticket check {queue_id}'[/red]"
                )


@app.command("list")
def list_tickets(
    state: TicketState | None = typer.Option(
        None, "--state", "-s", help="Filter by state"
    ),
    priority: Priority | None = typer.Option(
        None, "--priority", "-p", help="Filter by priority"
    ),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum number of tickets"),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    adapter: AdapterType | None = typer.Option(
        None, "--adapter", help="Override default adapter"
    ),
) -> None:
    """List tickets with optional filters."""
    from .utils import format_json_response, serialize_task

    async def _list() -> list[Any]:
        adapter_instance = get_adapter(
            override_adapter=adapter.value if adapter else None
        )
        filters = {}
        if state:
            filters["state"] = state
        if priority:
            filters["priority"] = priority
        return await adapter_instance.list(limit=limit, filters=filters)

    tickets = asyncio.run(_list())

    if not tickets:
        if output_json:
            console.print(
                format_json_response(
                    "success", {"tickets": [], "count": 0, "has_more": False}
                )
            )
        else:
            console.print("[yellow]No tickets found[/yellow]")
        return

    # JSON output
    if output_json:
        tickets_data = [serialize_task(t) for t in tickets]
        data = {
            "tickets": tickets_data,
            "count": len(tickets_data),
            "has_more": len(tickets)
            >= limit,  # Heuristic: if we got exactly limit, there might be more
        }
        console.print(format_json_response("success", data))
        return

    # Original table output
    table = Table(title="Tickets")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("State", style="green")
    table.add_column("Priority", style="yellow")
    table.add_column("Assignee", style="blue")

    for ticket in tickets:
        # Handle assignee field - Epic doesn't have assignee, Task does
        assignee = getattr(ticket, "assignee", None) or "-"

        table.add_row(
            ticket.id or "N/A",
            ticket.title,
            ticket.state,
            ticket.priority,
            assignee,
        )

    console.print(table)


@app.command()
def show(
    ticket_id: str = typer.Argument(..., help="Ticket ID"),
    no_comments: bool = typer.Option(
        False, "--no-comments", help="Hide comments (shown by default)"
    ),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    adapter: AdapterType | None = typer.Option(
        None, "--adapter", help="Override default adapter"
    ),
) -> None:
    """Show detailed ticket information with full context.

    By default, displays ticket details along with all comments to provide
    a holistic view of the ticket's history and context.

    Use --no-comments to display only ticket metadata without comments.
    Use --json to output in machine-readable JSON format.
    """
    from .utils import format_error_json, format_json_response, serialize_task

    async def _show() -> tuple[Any, Any, Any]:
        adapter_instance = get_adapter(
            override_adapter=adapter.value if adapter else None
        )
        ticket = await adapter_instance.read(ticket_id)
        ticket_comments = None
        attachments = None

        # Fetch comments by default (unless explicitly disabled)
        if not no_comments and ticket:
            try:
                ticket_comments = await adapter_instance.get_comments(ticket_id)
            except (NotImplementedError, AttributeError):
                # Adapter doesn't support comments
                pass

        # Try to fetch attachments if available
        if ticket and hasattr(adapter_instance, "list_attachments"):
            try:
                attachments = await adapter_instance.list_attachments(ticket_id)
            except (NotImplementedError, AttributeError):
                pass

        return ticket, ticket_comments, attachments

    try:
        ticket, ticket_comments, attachments = asyncio.run(_show())

        if not ticket:
            if output_json:
                console.print(
                    format_error_json(
                        f"Ticket not found: {ticket_id}", ticket_id=ticket_id
                    )
                )
            else:
                console.print(f"[red]✗[/red] Ticket not found: {ticket_id}")
            raise typer.Exit(1) from None

        # JSON output
        if output_json:
            data = serialize_task(ticket)

            # Add comments if available
            if ticket_comments:
                data["comments"] = [
                    {
                        "id": getattr(c, "id", None),
                        "text": c.content,
                        "author": c.author,
                        "created_at": (
                            c.created_at.isoformat()
                            if hasattr(c.created_at, "isoformat")
                            else str(c.created_at)
                        ),
                    }
                    for c in ticket_comments
                ]

            # Add attachments if available
            if attachments:
                data["attachments"] = attachments

            console.print(format_json_response("success", data))
            return

        # Original formatted output continues below...
    except Exception as e:
        if output_json:
            console.print(format_error_json(e, ticket_id=ticket_id))
            raise typer.Exit(1) from None
        raise

    # Display ticket header with metadata
    console.print(f"\n[bold cyan]┌─ Ticket: {ticket.id}[/bold cyan]")
    console.print(f"[bold]│ {ticket.title}[/bold]")
    console.print("└" + "─" * 60)

    # Display metadata in organized sections
    console.print("\n[bold]Status[/bold]")
    console.print(f"  State: [green]{ticket.state}[/green]")
    console.print(f"  Priority: [yellow]{ticket.priority}[/yellow]")

    if ticket.assignee:
        console.print(f"  Assignee: {ticket.assignee}")

    # Display timestamps if available
    if ticket.created_at or ticket.updated_at:
        console.print("\n[bold]Timeline[/bold]")
        if ticket.created_at:
            console.print(f"  Created: {ticket.created_at}")
        if ticket.updated_at:
            console.print(f"  Updated: {ticket.updated_at}")

    # Display tags
    if ticket.tags:
        console.print("\n[bold]Tags[/bold]")
        console.print(f"  {', '.join(ticket.tags)}")

    # Display description
    if ticket.description:
        console.print("\n[bold]Description[/bold]")
        console.print(f"  {ticket.description}")

    # Display parent/child relationships
    parent_info = []
    if hasattr(ticket, "parent_epic") and ticket.parent_epic:
        parent_info.append(f"Epic: {ticket.parent_epic}")
    if hasattr(ticket, "parent_issue") and ticket.parent_issue:
        parent_info.append(f"Parent Issue: {ticket.parent_issue}")

    if parent_info:
        console.print("\n[bold]Hierarchy[/bold]")
        for info in parent_info:
            console.print(f"  {info}")

    # Display attachments if available
    if attachments and len(attachments) > 0:
        console.print(f"\n[bold]Attachments ({len(attachments)})[/bold]")
        for att in attachments:
            att_title = att.get("title", "Untitled")
            att_url = att.get("url", "")
            console.print(f"  📎 {att_title}")
            if att_url:
                console.print(f"     {att_url}")

    # Display comments with enhanced formatting
    if ticket_comments:
        console.print(f"\n[bold]Activity & Comments ({len(ticket_comments)})[/bold]")
        for i, comment in enumerate(ticket_comments, 1):
            # Format timestamp
            timestamp = comment.created_at if comment.created_at else "Unknown time"
            author = comment.author if comment.author else "Unknown author"

            console.print(f"\n[dim]  {i}. {timestamp}[/dim]")
            console.print(f"  [cyan]@{author}[/cyan]")
            console.print(f"  {comment.content}")

    # Footer with hint
    if no_comments:
        console.print(
            "\n[dim]💡 Tip: Remove --no-comments to see activity and comments[/dim]"
        )


@app.command()
def comment(
    ticket_id: str = typer.Argument(..., help="Ticket ID"),
    content: str = typer.Argument(..., help="Comment content"),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    adapter: AdapterType | None = typer.Option(
        None, "--adapter", help="Override default adapter"
    ),
) -> None:
    """Add a comment to a ticket."""
    from .utils import format_error_json, format_json_response

    async def _comment() -> Comment:
        adapter_instance = get_adapter(
            override_adapter=adapter.value if adapter else None
        )

        # Create comment
        comment_obj = Comment(
            ticket_id=ticket_id,
            content=content,
            author="cli-user",  # Could be made configurable
        )

        result = await adapter_instance.add_comment(comment_obj)
        return result

    try:
        result = asyncio.run(_comment())

        if output_json:
            data = {
                "id": result.id,
                "ticket_id": ticket_id,
                "text": content,
                "author": result.author,
                "created_at": (
                    result.created_at.isoformat()
                    if hasattr(result.created_at, "isoformat")
                    else str(result.created_at)
                ),
            }
            console.print(
                format_json_response(
                    "success", data, message="Comment added successfully"
                )
            )
        else:
            console.print("[green]✓[/green] Comment added successfully")
            if result.id:
                console.print(f"Comment ID: {result.id}")
            console.print(f"Content: {content}")
    except Exception as e:
        if output_json:
            console.print(format_error_json(e, ticket_id=ticket_id))
        else:
            console.print(f"[red]✗[/red] Failed to add comment: {e}")
        raise typer.Exit(1) from None


@app.command()
def attach(
    ticket_id: str = typer.Argument(..., help="Ticket ID or URL"),
    file_path: Path = typer.Argument(..., help="Path to file to attach", exists=True),
    description: str | None = typer.Option(
        None, "--description", "-d", help="Attachment description or comment"
    ),
    adapter: AdapterType | None = typer.Option(
        None, "--adapter", help="Override default adapter"
    ),
) -> None:
    """Attach a file to a ticket.

    Examples:
        mcp-ticketer ticket attach 1M-157 docs/analysis.md
        mcp-ticketer ticket attach PROJ-123 screenshot.png -d "Error screenshot"
        mcp-ticketer ticket attach https://linear.app/.../issue/ABC-123 diagram.pdf
    """

    async def _attach() -> dict[str, Any]:
        import mimetypes

        adapter_instance = get_adapter(
            override_adapter=adapter.value if adapter else None
        )

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"

        # Method 1: Try Linear-specific upload (if available)
        if hasattr(adapter_instance, "upload_file") and hasattr(
            adapter_instance, "attach_file_to_issue"
        ):
            try:
                # Upload file to Linear's S3
                file_url = await adapter_instance.upload_file(
                    file_path=str(file_path), mime_type=mime_type
                )

                # Attach to issue
                attachment = await adapter_instance.attach_file_to_issue(
                    issue_id=ticket_id,
                    file_url=file_url,
                    title=file_path.name,
                    subtitle=description,
                )

                return {
                    "status": "completed",
                    "attachment": attachment,
                    "file_url": file_url,
                    "method": "linear_native_upload",
                }
            except Exception:
                # If Linear upload fails, fall through to next method
                pass

        # Method 2: Try generic add_attachment (if available)
        if hasattr(adapter_instance, "add_attachment"):
            try:
                attachment = await adapter_instance.add_attachment(
                    ticket_id=ticket_id,
                    file_path=str(file_path),
                    description=description or "",
                )
                return {
                    "status": "completed",
                    "attachment": attachment,
                    "method": "adapter_native",
                }
            except NotImplementedError:
                pass

        # Method 3: Fallback - Add file reference as comment
        from ..core.models import Comment

        comment_content = f"📎 File reference: {file_path.name}"
        if description:
            comment_content += f"\n\n{description}"

        comment_obj = Comment(
            ticket_id=ticket_id,
            content=comment_content,
            author="cli-user",
        )

        comment = await adapter_instance.add_comment(comment_obj)
        return {
            "status": "completed",
            "comment": comment,
            "method": "comment_reference",
            "note": "Adapter doesn't support attachments - added file reference as comment",
        }

    # Validate file before attempting upload
    if not file_path.exists():
        console.print(f"[red]✗[/red] File not found: {file_path}")
        raise typer.Exit(1) from None

    if not file_path.is_file():
        console.print(f"[red]✗[/red] Path is not a file: {file_path}")
        raise typer.Exit(1) from None

    # Display file info
    file_size = file_path.stat().st_size
    size_mb = file_size / (1024 * 1024)
    console.print(f"\n[dim]Attaching file to ticket {ticket_id}...[/dim]")
    console.print(f"  File: {file_path.name} ({size_mb:.2f} MB)")

    # Detect MIME type
    import mimetypes

    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type:
        console.print(f"  Type: {mime_type}")

    try:
        result = asyncio.run(_attach())

        if result["status"] == "completed":
            console.print(
                f"\n[green]✓[/green] File attached successfully to {ticket_id}"
            )

            # Display attachment details based on method used
            method = result.get("method", "unknown")

            if method == "linear_native_upload":
                console.print("  Method: Linear native upload")
                if "file_url" in result:
                    console.print(f"  URL: {result['file_url']}")
                if "attachment" in result and isinstance(result["attachment"], dict):
                    att = result["attachment"]
                    if "id" in att:
                        console.print(f"  ID: {att['id']}")
                    if "title" in att:
                        console.print(f"  Title: {att['title']}")

            elif method == "adapter_native":
                console.print("  Method: Adapter native")
                if "attachment" in result:
                    att = result["attachment"]
                    if isinstance(att, dict):
                        if "id" in att:
                            console.print(f"  ID: {att['id']}")
                        if "url" in att:
                            console.print(f"  URL: {att['url']}")

            elif method == "comment_reference":
                console.print("  Method: Comment reference")
                console.print(f"  [dim]{result.get('note', '')}[/dim]")
                if "comment" in result:
                    comment = result["comment"]
                    if isinstance(comment, dict) and "id" in comment:
                        console.print(f"  Comment ID: {comment['id']}")

        else:
            # Error case
            error_msg = result.get("error", "Unknown error")
            console.print(f"\n[red]✗[/red] Failed to attach file: {error_msg}")
            raise typer.Exit(1) from None

    except Exception as e:
        console.print(f"\n[red]✗[/red] Failed to attach file: {e}")
        raise typer.Exit(1) from None


@app.command()
def update(
    ticket_id: str = typer.Argument(..., help="Ticket ID"),
    title: str | None = typer.Option(None, "--title", help="New title"),
    description: str | None = typer.Option(
        None, "--description", "-d", help="New description"
    ),
    priority: Priority | None = typer.Option(
        None, "--priority", "-p", help="New priority"
    ),
    assignee: str | None = typer.Option(None, "--assignee", "-a", help="New assignee"),
    wait: bool = typer.Option(
        False,
        "--wait",
        "-w",
        help="Wait for operation to complete (synchronous mode)",
    ),
    timeout: float = typer.Option(
        30.0,
        "--timeout",
        help="Timeout in seconds for --wait mode (default: 30)",
    ),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    adapter: AdapterType | None = typer.Option(
        None, "--adapter", help="Override default adapter"
    ),
) -> None:
    """Update ticket fields."""
    from .utils import format_json_response

    updates = {}
    if title:
        updates["title"] = title
    if description:
        updates["description"] = description
    if priority:
        updates["priority"] = (
            priority.value if isinstance(priority, Priority) else priority
        )
    if assignee:
        updates["assignee"] = assignee

    if not updates:
        if output_json:
            console.print(
                format_json_response(
                    "error",
                    {"error": "No updates specified"},
                    message="No updates specified",
                )
            )
        else:
            console.print("[yellow]No updates specified[/yellow]")
        raise typer.Exit(1) from None

    # Get the adapter name
    config = load_config()
    adapter_name = (
        adapter.value if adapter else config.get("default_adapter", "aitrackdown")
    )

    # Add ticket_id to updates
    updates["ticket_id"] = ticket_id

    # Add to queue with explicit project directory
    queue = Queue()
    queue_id = queue.add(
        ticket_data=updates,
        adapter=adapter_name,
        operation="update",
        project_dir=str(Path.cwd()),  # Explicitly pass current project directory
    )

    # Start worker if needed
    manager = WorkerManager()
    if manager.start_if_needed():
        if not output_json:
            console.print("[dim]Worker started to process request[/dim]")

    # SYNCHRONOUS MODE: Poll until completion if --wait flag is set
    if wait:
        from .utils import format_error_json

        if not output_json:
            console.print(
                f"[yellow]⏳[/yellow] Waiting for update to complete (timeout: {timeout}s)..."
            )

        try:
            # Poll the queue until operation completes
            completed_item = queue.poll_until_complete(queue_id, timeout=timeout)
            result = completed_item.result

            if output_json:
                data = result if result else {"queue_id": queue_id, "id": ticket_id}
                console.print(
                    format_json_response(
                        "success", data, message="Ticket updated successfully"
                    )
                )
            else:
                console.print(
                    f"[green]✓[/green] Ticket updated successfully: {ticket_id}"
                )
                for key, value in updates.items():
                    if key != "ticket_id":
                        console.print(f"  {key}: {value}")

        except TimeoutError as e:
            if output_json:
                console.print(format_error_json(str(e), queue_id=queue_id))
            else:
                console.print(f"[red]❌[/red] Operation timed out after {timeout}s")
                console.print(f"  Queue ID: {queue_id}")
            raise typer.Exit(1) from None

        except RuntimeError as e:
            if output_json:
                console.print(format_error_json(str(e), queue_id=queue_id))
            else:
                console.print(f"[red]❌[/red] Operation failed: {e}")
            raise typer.Exit(1) from None

    # ASYNCHRONOUS MODE (default)
    else:
        if output_json:
            updated_fields = [k for k in updates.keys() if k != "ticket_id"]
            data = {
                "id": ticket_id,
                "queue_id": queue_id,
                "updated_fields": updated_fields,
                **{k: v for k, v in updates.items() if k != "ticket_id"},
            }
            console.print(
                format_json_response("success", data, message="Ticket update queued")
            )
        else:
            console.print(f"[green]✓[/green] Queued ticket update: {queue_id}")
            for key, value in updates.items():
                if key != "ticket_id":
                    console.print(f"  {key}: {value}")
            console.print(
                "[dim]Use 'mcp-ticketer ticket check {queue_id}' to check progress[/dim]"
            )


@app.command()
def transition(
    ticket_id: str = typer.Argument(..., help="Ticket ID"),
    state_positional: TicketState | None = typer.Argument(
        None, help="Target state (positional - deprecated, use --state instead)"
    ),
    state: TicketState | None = typer.Option(
        None, "--state", "-s", help="Target state (recommended)"
    ),
    wait: bool = typer.Option(
        False,
        "--wait",
        "-w",
        help="Wait for operation to complete (synchronous mode)",
    ),
    timeout: float = typer.Option(
        30.0,
        "--timeout",
        help="Timeout in seconds for --wait mode (default: 30)",
    ),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    adapter: AdapterType | None = typer.Option(
        None, "--adapter", help="Override default adapter"
    ),
) -> None:
    """Change ticket state with validation.

    Examples:
        # Recommended syntax with flag:
        mcp-ticketer ticket transition BTA-215 --state done
        mcp-ticketer ticket transition BTA-215 -s in_progress

        # Legacy positional syntax (still supported):
        mcp-ticketer ticket transition BTA-215 done

    """
    from .utils import format_json_response

    # Determine which state to use (prefer flag over positional)
    target_state = state if state is not None else state_positional

    if target_state is None:
        if output_json:
            console.print(
                format_json_response(
                    "error", {"error": "State is required"}, message="State is required"
                )
            )
        else:
            console.print("[red]Error: State is required[/red]")
            console.print(
                "Use either:\n"
                "  - Flag syntax (recommended): mcp-ticketer ticket transition TICKET-ID --state STATE\n"
                "  - Positional syntax: mcp-ticketer ticket transition TICKET-ID STATE"
            )
        raise typer.Exit(1) from None

    # Get the adapter name
    config = load_config()
    adapter_name = (
        adapter.value if adapter else config.get("default_adapter", "aitrackdown")
    )

    # Add to queue with explicit project directory
    queue = Queue()
    state_value = target_state.value if hasattr(target_state, "value") else target_state
    queue_id = queue.add(
        ticket_data={
            "ticket_id": ticket_id,
            "state": state_value,
        },
        adapter=adapter_name,
        operation="transition",
        project_dir=str(Path.cwd()),  # Explicitly pass current project directory
    )

    # Start worker if needed
    manager = WorkerManager()
    if manager.start_if_needed():
        if not output_json:
            console.print("[dim]Worker started to process request[/dim]")

    # SYNCHRONOUS MODE: Poll until completion if --wait flag is set
    if wait:
        from .utils import format_error_json

        if not output_json:
            console.print(
                f"[yellow]⏳[/yellow] Waiting for transition to complete (timeout: {timeout}s)..."
            )

        try:
            # Poll the queue until operation completes
            completed_item = queue.poll_until_complete(queue_id, timeout=timeout)
            result = completed_item.result

            if output_json:
                data = (
                    result
                    if result
                    else {
                        "id": ticket_id,
                        "new_state": state_value,
                        "matched_state": state_value,
                        "confidence": 1.0,
                    }
                )
                console.print(
                    format_json_response(
                        "success", data, message="State transition completed"
                    )
                )
            else:
                console.print(
                    f"[green]✓[/green] State transition completed: {ticket_id} → {target_state}"
                )

        except TimeoutError as e:
            if output_json:
                console.print(format_error_json(str(e), queue_id=queue_id))
            else:
                console.print(f"[red]❌[/red] Operation timed out after {timeout}s")
                console.print(f"  Queue ID: {queue_id}")
            raise typer.Exit(1) from None

        except RuntimeError as e:
            if output_json:
                console.print(format_error_json(str(e), queue_id=queue_id))
            else:
                console.print(f"[red]❌[/red] Operation failed: {e}")
            raise typer.Exit(1) from None

    # ASYNCHRONOUS MODE (default)
    else:
        if output_json:
            data = {
                "id": ticket_id,
                "queue_id": queue_id,
                "new_state": state_value,
                "matched_state": state_value,
                "confidence": 1.0,
            }
            console.print(
                format_json_response("success", data, message="State transition queued")
            )
        else:
            console.print(f"[green]✓[/green] Queued state transition: {queue_id}")
            console.print(f"  Ticket: {ticket_id} → {target_state}")
            console.print(
                "[dim]Use 'mcp-ticketer ticket check {queue_id}' to check progress[/dim]"
            )


@app.command()
def search(
    query: str | None = typer.Argument(None, help="Search query"),
    state: TicketState | None = typer.Option(None, "--state", "-s"),
    priority: Priority | None = typer.Option(None, "--priority", "-p"),
    assignee: str | None = typer.Option(None, "--assignee", "-a"),
    limit: int = typer.Option(10, "--limit", "-l"),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    adapter: AdapterType | None = typer.Option(
        None, "--adapter", help="Override default adapter"
    ),
) -> None:
    """Search tickets with advanced query."""
    from .utils import format_json_response, serialize_task

    async def _search() -> list[Any]:
        adapter_instance = get_adapter(
            override_adapter=adapter.value if adapter else None
        )
        search_query = SearchQuery(
            query=query,
            state=state,
            priority=priority,
            assignee=assignee,
            limit=limit,
        )
        return await adapter_instance.search(search_query)

    tickets = asyncio.run(_search())

    if not tickets:
        if output_json:
            console.print(
                format_json_response(
                    "success", {"tickets": [], "query": query, "count": 0}
                )
            )
        else:
            console.print("[yellow]No tickets found matching query[/yellow]")
        return

    # JSON output
    if output_json:
        tickets_data = [serialize_task(t) for t in tickets]
        data = {"tickets": tickets_data, "query": query, "count": len(tickets_data)}
        console.print(format_json_response("success", data))
        return

    # Display results
    console.print(f"\n[bold]Found {len(tickets)} ticket(s)[/bold]\n")

    for ticket in tickets:
        console.print(f"[cyan]{ticket.id}[/cyan]: {ticket.title}")
        console.print(f"  State: {ticket.state} | Priority: {ticket.priority}")
        if ticket.assignee:
            console.print(f"  Assignee: {ticket.assignee}")
        console.print()


@app.command()
def check(queue_id: str = typer.Argument(..., help="Queue ID to check")) -> None:
    """Check status of a queued operation."""
    queue = Queue()
    item = queue.get_item(queue_id)

    if not item:
        console.print(f"[red]Queue item not found: {queue_id}[/red]")
        raise typer.Exit(1) from None

    # Display status
    console.print(f"\n[bold]Queue Item: {item.id}[/bold]")
    console.print(f"Operation: {item.operation}")
    console.print(f"Adapter: {item.adapter}")

    # Status with color
    if item.status == QueueStatus.COMPLETED:
        console.print(f"Status: [green]{item.status}[/green]")
    elif item.status == QueueStatus.FAILED:
        console.print(f"Status: [red]{item.status}[/red]")
    elif item.status == QueueStatus.PROCESSING:
        console.print(f"Status: [yellow]{item.status}[/yellow]")
    else:
        console.print(f"Status: {item.status}")

    # Timestamps
    console.print(f"Created: {item.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    if item.processed_at:
        console.print(f"Processed: {item.processed_at.strftime('%Y-%m-%d %H:%M:%S')}")

    # Error or result
    if item.error_message:
        console.print(f"\n[red]Error:[/red] {item.error_message}")
    elif item.result:
        console.print("\n[green]Result:[/green]")
        for key, value in item.result.items():
            console.print(f"  {key}: {value}")

    if item.retry_count > 0:
        console.print(f"\nRetry Count: {item.retry_count}")
