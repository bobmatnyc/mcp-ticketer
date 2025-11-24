"""Ticket instructions management commands.

This module implements CLI commands for managing ticket writing instructions,
allowing users to customize and view the guidelines that help create
well-structured, consistent tickets.
"""

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from ..core.instructions import (
    InstructionsError,
    InstructionsValidationError,
    TicketInstructionsManager,
)

app = typer.Typer(
    name="instructions",
    help="Manage ticket writing instructions for your project",
)
console = Console()


@app.command()
def show(
    default: bool = typer.Option(
        False,
        "--default",
        help="Show default instructions instead of custom",
    ),
    raw: bool = typer.Option(
        False,
        "--raw",
        help="Output raw markdown without formatting",
    ),
) -> None:
    """Display current ticket writing instructions.

    By default, shows custom instructions if they exist, otherwise shows defaults.
    Use --default to always show the default instructions.
    Use --raw to output raw markdown without Rich formatting (useful for piping).

    Examples:
    --------
        # Show current instructions (custom or default)
        mcp-ticketer instructions show

        # Always show default instructions
        mcp-ticketer instructions show --default

        # Output raw markdown for piping
        mcp-ticketer instructions show --raw > team_guide.md

    """
    try:
        manager = TicketInstructionsManager()

        if default:
            instructions = manager.get_default_instructions()
            source = "default"
        else:
            instructions = manager.get_instructions()
            source = "custom" if manager.has_custom_instructions() else "default"

        if raw:
            # Raw output for piping
            console.print(instructions)
        else:
            # Rich formatted output
            if source == "custom":
                title = f"[green]Custom Instructions[/green] ({manager.get_instructions_path()})"
            else:
                title = "[blue]Default Instructions[/blue]"

            panel = Panel(
                Markdown(instructions),
                title=title,
                border_style="cyan",
            )
            console.print(panel)

    except InstructionsError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command()
def add(
    file_path: str | None = typer.Argument(
        None,
        help="Path to markdown file with custom instructions",
    ),
    stdin: bool = typer.Option(
        False,
        "--stdin",
        help="Read instructions from stdin instead of file",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing custom instructions without confirmation",
    ),
) -> None:
    """Add custom ticket writing instructions for your project.

    You can provide instructions from a file or via stdin. If custom instructions
    already exist, you'll be prompted for confirmation unless --force is used.

    Examples:
    --------
        # Add from file
        mcp-ticketer instructions add team_guidelines.md

        # Add from stdin
        cat guidelines.md | mcp-ticketer instructions add --stdin

        # Force overwrite existing
        mcp-ticketer instructions add new_guide.md --force

    """
    try:
        manager = TicketInstructionsManager()

        # Check for existing custom instructions
        if manager.has_custom_instructions() and not force:
            path = manager.get_instructions_path()
            console.print(
                f"[yellow]Warning:[/yellow] Custom instructions already exist at {path}"
            )

            confirm = typer.confirm("Do you want to overwrite them?")
            if not confirm:
                console.print("[yellow]Operation cancelled[/yellow]")
                raise typer.Exit(0) from None

        # Get content from stdin or file
        if stdin:
            console.print("[dim]Reading from stdin... (Press Ctrl+D when done)[/dim]")
            content = sys.stdin.read()
            if not content.strip():
                console.print("[red]Error:[/red] No content provided on stdin")
                raise typer.Exit(1) from None
        elif file_path:
            source_path = Path(file_path)
            if not source_path.exists():
                console.print(f"[red]Error:[/red] File not found: {file_path}")
                raise typer.Exit(1) from None

            try:
                content = source_path.read_text(encoding="utf-8")
            except Exception as e:
                console.print(f"[red]Error:[/red] Failed to read file: {e}")
                raise typer.Exit(1) from None
        else:
            console.print("[red]Error:[/red] Either provide a file path or use --stdin")
            console.print("Example: mcp-ticketer instructions add guidelines.md")
            raise typer.Exit(1) from None

        # Set instructions
        manager.set_instructions(content)

        path = manager.get_instructions_path()
        console.print(f"[green]✓[/green] Custom instructions saved to: {path}")
        console.print("[dim]Use 'mcp-ticketer instructions show' to view them[/dim]")

    except InstructionsValidationError as e:
        console.print(f"[red]Validation Error:[/red] {e}")
        raise typer.Exit(1) from None
    except InstructionsError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command()
def update(
    file_path: str | None = typer.Argument(
        None,
        help="Path to markdown file with updated instructions",
    ),
    stdin: bool = typer.Option(
        False,
        "--stdin",
        help="Read instructions from stdin instead of file",
    ),
) -> None:
    """Update existing custom instructions (alias for 'add --force').

    This is a convenience command that overwrites existing custom instructions
    without prompting for confirmation.

    Examples:
    --------
        # Update from file
        mcp-ticketer instructions update new_guidelines.md

        # Update from stdin
        cat updated.md | mcp-ticketer instructions update --stdin

    """
    try:
        manager = TicketInstructionsManager()

        if not manager.has_custom_instructions():
            console.print("[yellow]Warning:[/yellow] No custom instructions exist yet")
            console.print("Use 'mcp-ticketer instructions add' to create them first")
            raise typer.Exit(1) from None

        # Get content from stdin or file
        if stdin:
            console.print("[dim]Reading from stdin... (Press Ctrl+D when done)[/dim]")
            content = sys.stdin.read()
            if not content.strip():
                console.print("[red]Error:[/red] No content provided on stdin")
                raise typer.Exit(1) from None
        elif file_path:
            source_path = Path(file_path)
            if not source_path.exists():
                console.print(f"[red]Error:[/red] File not found: {file_path}")
                raise typer.Exit(1) from None

            try:
                content = source_path.read_text(encoding="utf-8")
            except Exception as e:
                console.print(f"[red]Error:[/red] Failed to read file: {e}")
                raise typer.Exit(1) from None
        else:
            console.print("[red]Error:[/red] Either provide a file path or use --stdin")
            console.print("Example: mcp-ticketer instructions update guidelines.md")
            raise typer.Exit(1) from None

        # Update instructions (force overwrite)
        manager.set_instructions(content)

        path = manager.get_instructions_path()
        console.print(f"[green]✓[/green] Custom instructions updated: {path}")
        console.print("[dim]Use 'mcp-ticketer instructions show' to view them[/dim]")

    except InstructionsValidationError as e:
        console.print(f"[red]Validation Error:[/red] {e}")
        raise typer.Exit(1) from None
    except InstructionsError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command()
def delete(
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
) -> None:
    """Delete custom instructions and revert to defaults.

    This removes your project-specific instructions file. After deletion,
    the default instructions will be used.

    Examples:
    --------
        # Delete with confirmation prompt
        mcp-ticketer instructions delete

        # Skip confirmation
        mcp-ticketer instructions delete --yes

    """
    try:
        manager = TicketInstructionsManager()

        if not manager.has_custom_instructions():
            console.print("[yellow]No custom instructions to delete[/yellow]")
            console.print("[dim]Already using default instructions[/dim]")
            raise typer.Exit(0) from None

        path = manager.get_instructions_path()

        if not yes:
            console.print(f"[yellow]Warning:[/yellow] This will delete: {path}")
            console.print("After deletion, default instructions will be used.")

            confirm = typer.confirm("Are you sure?")
            if not confirm:
                console.print("[yellow]Operation cancelled[/yellow]")
                raise typer.Exit(0) from None

        # Delete instructions
        manager.delete_instructions()

        console.print("[green]✓[/green] Custom instructions deleted")
        console.print("[dim]Now using default instructions[/dim]")

    except InstructionsError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command()
def path() -> None:
    """Show path to custom instructions file.

    Displays the path where custom instructions are (or would be) stored
    for this project, along with status information.

    Examples:
    --------
        # Show instructions file path
        mcp-ticketer instructions path

        # Use in scripts
        INST_PATH=$(mcp-ticketer instructions path --quiet)

    """
    try:
        manager = TicketInstructionsManager()
        inst_path = manager.get_instructions_path()
        exists = manager.has_custom_instructions()

        console.print(f"[cyan]Instructions file:[/cyan] {inst_path}")

        if exists:
            console.print("[green]Status:[/green] Custom instructions exist")

            # Show file size
            try:
                size = inst_path.stat().st_size
                console.print(f"[dim]Size: {size} bytes[/dim]")
            except Exception:
                pass
        else:
            console.print(
                "[yellow]Status:[/yellow] No custom instructions (using defaults)"
            )
            console.print(
                "[dim]Create with: mcp-ticketer instructions add <file>[/dim]"
            )

    except InstructionsError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command()
def edit() -> None:
    """Open instructions in default editor.

    Opens the custom instructions file in your system's default text editor.
    If custom instructions don't exist yet, creates them with default content
    first.

    The editor is determined by the EDITOR environment variable, or falls back
    to sensible defaults (vim on Unix, notepad on Windows).

    Examples:
    --------
        # Edit instructions
        mcp-ticketer instructions edit

        # Use specific editor
        EDITOR=nano mcp-ticketer instructions edit

    """
    import os
    import platform
    import subprocess

    try:
        manager = TicketInstructionsManager()

        # If no custom instructions exist, create them with defaults
        if not manager.has_custom_instructions():
            console.print("[yellow]No custom instructions yet[/yellow]")
            console.print("[dim]Creating from defaults...[/dim]")

            # Copy defaults to custom location
            default_content = manager.get_default_instructions()
            manager.set_instructions(default_content)

            console.print(
                f"[green]✓[/green] Created custom instructions at: {manager.get_instructions_path()}"
            )

        inst_path = manager.get_instructions_path()

        # Determine editor
        editor = os.environ.get("EDITOR")

        if not editor:
            # Platform-specific defaults
            system = platform.system()
            if system == "Windows":
                editor = "notepad"
            else:
                # Unix-like: try common editors
                for candidate in ["vim", "vi", "nano", "emacs"]:
                    try:
                        result = subprocess.run(
                            ["which", candidate],
                            capture_output=True,
                            text=True,
                            timeout=1,
                        )
                        if result.returncode == 0:
                            editor = candidate
                            break
                    except Exception:
                        continue

                if not editor:
                    editor = "vi"  # Ultimate fallback

        console.print(f"[dim]Opening with {editor}...[/dim]")

        # Open editor
        try:
            subprocess.run([editor, str(inst_path)], check=True)
            console.print(f"[green]✓[/green] Finished editing: {inst_path}")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Error:[/red] Editor exited with code {e.returncode}")
            raise typer.Exit(1) from None
        except FileNotFoundError:
            console.print(f"[red]Error:[/red] Editor not found: {editor}")
            console.print("Set EDITOR environment variable to your preferred editor")
            raise typer.Exit(1) from None

    except InstructionsError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None
