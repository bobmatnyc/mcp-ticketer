"""Platform-specific command groups."""

import typer

# Import platform-specific command modules
from .linear_commands import app as linear_app

# Create main platform command group
app = typer.Typer(
    name="platform",
    help="Platform-specific commands (Linear, JIRA, GitHub, AITrackdown)",
)

# Register Linear commands
app.add_typer(linear_app, name="linear")

# Create placeholder apps for other platforms

# JIRA platform commands (placeholder)
jira_app = typer.Typer(
    name="jira",
    help="JIRA-specific workspace and project management",
)


@jira_app.command("projects")
def jira_list_projects() -> None:
    """List JIRA projects (placeholder - not yet implemented)."""
    from rich.console import Console

    console = Console()
    console.print("[yellow]JIRA platform commands are not yet implemented.[/yellow]")
    console.print(
        "Use the generic ticket commands for JIRA operations:\n"
        "  mcp-ticketer ticket create 'My ticket'\n"
        "  mcp-ticketer ticket list"
    )


@jira_app.command("configure")
def jira_configure() -> None:
    """Configure JIRA adapter (placeholder - not yet implemented)."""
    from rich.console import Console

    console = Console()
    console.print("[yellow]JIRA platform commands are not yet implemented.[/yellow]")
    console.print("Use 'mcp-ticketer init --adapter jira' to configure JIRA adapter.")


# GitHub platform commands (placeholder)
github_app = typer.Typer(
    name="github",
    help="GitHub-specific repository and issue management",
)


@github_app.command("repos")
def github_list_repos() -> None:
    """List GitHub repositories (placeholder - not yet implemented)."""
    from rich.console import Console

    console = Console()
    console.print("[yellow]GitHub platform commands are not yet implemented.[/yellow]")
    console.print(
        "Use the generic ticket commands for GitHub operations:\n"
        "  mcp-ticketer ticket create 'My issue'\n"
        "  mcp-ticketer ticket list"
    )


@github_app.command("configure")
def github_configure() -> None:
    """Configure GitHub adapter (placeholder - not yet implemented)."""
    from rich.console import Console

    console = Console()
    console.print("[yellow]GitHub platform commands are not yet implemented.[/yellow]")
    console.print(
        "Use 'mcp-ticketer init --adapter github' to configure GitHub adapter."
    )


# AITrackdown platform commands (placeholder)
aitrackdown_app = typer.Typer(
    name="aitrackdown",
    help="AITrackdown-specific local file management",
)


@aitrackdown_app.command("info")
def aitrackdown_info() -> None:
    """Show AITrackdown storage information (placeholder - not yet implemented)."""
    from rich.console import Console

    console = Console()
    console.print(
        "[yellow]AITrackdown platform commands are not yet implemented.[/yellow]"
    )
    console.print(
        "Use the generic ticket commands for AITrackdown operations:\n"
        "  mcp-ticketer ticket create 'My ticket'\n"
        "  mcp-ticketer ticket list"
    )


@aitrackdown_app.command("configure")
def aitrackdown_configure() -> None:
    """Configure AITrackdown adapter (placeholder - not yet implemented)."""
    from rich.console import Console

    console = Console()
    console.print(
        "[yellow]AITrackdown platform commands are not yet implemented.[/yellow]"
    )
    console.print(
        "Use 'mcp-ticketer init --adapter aitrackdown' to configure AITrackdown adapter."
    )


# Register all platform command groups
app.add_typer(jira_app, name="jira")
app.add_typer(github_app, name="github")
app.add_typer(aitrackdown_app, name="aitrackdown")
