"""CLI commands for project updates (Linear project status updates)."""

import asyncio
from datetime import datetime

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..core.models import ProjectUpdateHealth

app = typer.Typer(name="project-update", help="Project status update management")
console = Console()


def _format_health_indicator(health: ProjectUpdateHealth | str | None) -> str:
    """Format health status with color-coded indicators.

    Args:
        health: Health status enum or string value

    Returns:
        Formatted health indicator with color and icon
    """
    if not health:
        return "[dim]○ Not Set[/dim]"

    # Handle both enum and string values
    health_str = health.value if isinstance(health, ProjectUpdateHealth) else health

    health_indicators = {
        "on_track": "[green]✓ On Track[/green]",
        "at_risk": "[yellow]⚠ At Risk[/yellow]",
        "off_track": "[red]✗ Off Track[/red]",
        "complete": "[blue]✓ Complete[/blue]",
        "inactive": "[dim]○ Inactive[/dim]",
    }

    return health_indicators.get(health_str, f"[dim]{health_str}[/dim]")


def _format_relative_time(dt: datetime) -> str:
    """Format datetime as relative time string.

    Args:
        dt: Datetime to format

    Returns:
        Human-readable relative time (e.g., "2 hours ago")
    """
    try:
        from humanize import naturaltime

        return naturaltime(dt)
    except ImportError:
        # Fallback to ISO format if humanize not available
        return dt.strftime("%Y-%m-%d %H:%M:%S")


async def _create_update_async(
    project_id: str,
    body: str,
    health: ProjectUpdateHealth | None = None,
) -> None:
    """Async implementation of create command."""
    from .main import get_adapter

    try:
        adapter = get_adapter()

        # Check if adapter supports project updates
        if not hasattr(adapter, "create_project_update"):
            adapter_name = getattr(adapter, "adapter_name", type(adapter).__name__)
            console.print(
                f"[red]✗[/red] Adapter '{adapter_name}' does not support project updates"
            )
            console.print(
                "[dim]Project updates are supported by: Linear, GitHub V2, Asana[/dim]"
            )
            raise typer.Exit(1) from None

        # Validate body is not empty
        if not body or not body.strip():
            console.print("[red]✗[/red] Update body cannot be empty")
            raise typer.Exit(1) from None

        # Create the project update
        console.print(f"[dim]Creating project update for '{project_id}'...[/dim]")
        update = await adapter.create_project_update(
            project_id=project_id,
            body=body,
            health=health,
        )

        # Display success message with update details
        console.print("\n[green]✓[/green] Project update created successfully!")
        console.print(f"  Update ID: [cyan]{update.id}[/cyan]")
        console.print(
            f"  Project: [bold]{update.project_name or update.project_id}[/bold]"
        )
        console.print(f"  Health: {_format_health_indicator(update.health)}")
        console.print(f"  Created: {update.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

        if update.url:
            console.print(f"  URL: [link]{update.url}[/link]")

        # Show preview of body
        preview = body[:100] + "..." if len(body) > 100 else body
        console.print(f"  Body Preview: {preview}")

    except ValueError as e:
        console.print(f"[red]✗[/red] {str(e)}")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected error: {str(e)}")
        raise typer.Exit(1) from e


async def _list_updates_async(
    project_id: str,
    limit: int = 10,
) -> None:
    """Async implementation of list command."""
    from .main import get_adapter

    try:
        adapter = get_adapter()

        # Check if adapter supports project updates
        if not hasattr(adapter, "list_project_updates"):
            adapter_name = getattr(adapter, "adapter_name", type(adapter).__name__)
            console.print(
                f"[red]✗[/red] Adapter '{adapter_name}' does not support project updates"
            )
            raise typer.Exit(1) from None

        # List project updates
        console.print(f"[dim]Fetching updates for project '{project_id}'...[/dim]")
        updates = await adapter.list_project_updates(
            project_id=project_id,
            limit=limit,
        )

        if not updates:
            console.print(
                f"\n[yellow]No updates found for project '{project_id}'[/yellow]"
            )
            return

        # Create Rich table
        table = Table(title=f"Project Updates ({len(updates)} total)")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Date", style="dim")
        table.add_column("Health", no_wrap=True)
        table.add_column("Author", style="blue")
        table.add_column("Preview", style="white")

        for update in updates:
            # Format date
            date_str = (
                _format_relative_time(update.created_at)
                if update.created_at
                else "Unknown"
            )

            # Format health
            health_str = _format_health_indicator(update.health)

            # Format author
            author = update.author_name or update.author_id or "Unknown"

            # Preview (first 50 chars of body)
            preview = update.body[:50] + "..." if len(update.body) > 50 else update.body

            table.add_row(
                update.id[:8] + "..." if len(update.id) > 8 else update.id,
                date_str,
                health_str,
                author,
                preview,
            )

        console.print(table)

    except ValueError as e:
        console.print(f"[red]✗[/red] {str(e)}")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected error: {str(e)}")
        raise typer.Exit(1) from e


async def _get_update_async(update_id: str) -> None:
    """Async implementation of get command."""
    from .main import get_adapter

    try:
        adapter = get_adapter()

        # Check if adapter supports project updates
        if not hasattr(adapter, "get_project_update"):
            adapter_name = getattr(adapter, "adapter_name", type(adapter).__name__)
            console.print(
                f"[red]✗[/red] Adapter '{adapter_name}' does not support project updates"
            )
            raise typer.Exit(1) from None

        # Get project update
        console.print(f"[dim]Fetching update '{update_id}'...[/dim]")
        update = await adapter.get_project_update(update_id=update_id)

        # Build detailed display content
        content_lines = [
            f"[bold]Update ID:[/bold] {update.id}",
            f"[bold]Project:[/bold] {update.project_name or update.project_id}",
            f"[bold]Health:[/bold] {_format_health_indicator(update.health)}",
            f"[bold]Created:[/bold] {update.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        if update.author_name or update.author_id:
            author = update.author_name or update.author_id
            content_lines.append(f"[bold]Author:[/bold] {author}")

        if update.url:
            content_lines.append(f"[bold]URL:[/bold] [link]{update.url}[/link]")

        # Add body
        content_lines.append("")
        content_lines.append("[bold]Body:[/bold]")
        content_lines.append(update.body)

        # Add Linear-specific fields if present
        if update.diff_markdown:
            content_lines.append("")
            content_lines.append("[bold]Diff (Changes Since Last Update):[/bold]")
            content_lines.append(update.diff_markdown)

        if update.is_stale is not None:
            stale_indicator = (
                "[red]⚠ Stale[/red]" if update.is_stale else "[green]✓ Current[/green]"
            )
            content_lines.append("")
            content_lines.append(f"[bold]Freshness:[/bold] {stale_indicator}")

        # Display as Rich panel
        panel = Panel(
            "\n".join(content_lines),
            title="[bold]Project Update Details[/bold]",
            border_style="cyan",
            expand=False,
        )

        console.print(panel)

    except ValueError as e:
        console.print(f"[red]✗[/red] {str(e)}")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected error: {str(e)}")
        raise typer.Exit(1) from e


@app.command("create")
def create_update(
    project_id: str = typer.Argument(
        ...,
        help="Project identifier (UUID, slugId, short ID, or URL)",
    ),
    body: str = typer.Argument(
        ...,
        help="Update content (markdown formatted)",
    ),
    health: ProjectUpdateHealth | None = typer.Option(
        None,
        "--health",
        "-h",
        help="Project health status (on_track, at_risk, off_track, complete, inactive)",
    ),
) -> None:
    """Create a new project status update.

    Creates a status update for a project with optional health indicator.
    Linear projects will automatically generate a diff showing changes.

    Examples:
        # Create update with health status
        mcp-ticket project-update create "PROJ-123" "Sprint completed successfully" --health on_track

        # Create update using project URL
        mcp-ticket project-update create "https://linear.app/team/project/proj-slug" "Weekly update"

        # Create update without health indicator
        mcp-ticket project-update create "mcp-ticketer-eac28953c267" "Development ongoing"
    """
    asyncio.run(_create_update_async(project_id, body, health))


@app.command("list")
def list_updates(
    project_id: str = typer.Argument(
        ...,
        help="Project identifier (UUID, slugId, short ID, or URL)",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-l",
        help="Maximum number of updates to return",
        min=1,
        max=100,
    ),
) -> None:
    """List recent project updates.

    Retrieves recent status updates for a project, ordered by creation date (newest first).

    Examples:
        # List last 10 updates (default)
        mcp-ticket project-update list "PROJ-123"

        # List last 20 updates
        mcp-ticket project-update list "PROJ-123" --limit 20

        # List updates using project URL
        mcp-ticket project-update list "https://linear.app/team/project/proj-slug"
    """
    asyncio.run(_list_updates_async(project_id, limit))


@app.command("get")
def get_update(
    update_id: str = typer.Argument(
        ...,
        help="Project update identifier (UUID)",
    ),
) -> None:
    """Get detailed information about a specific project update.

    Retrieves full details including body, health status, author, and Linear-specific
    fields like auto-generated diffs and staleness indicators.

    Examples:
        # Get update details
        mcp-ticket project-update get "update-uuid-here"

        # View update with full diff
        mcp-ticket project-update get "abc123def456"
    """
    asyncio.run(_get_update_async(update_id))
