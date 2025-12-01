"""Ticket instructions management tools.

This module implements MCP tools for managing ticket writing instructions,
allowing AI agents to query and customize the guidelines that help create
well-structured, consistent tickets.
"""

from pathlib import Path
from typing import Any

from ....core.instructions import (
    InstructionsError,
    InstructionsValidationError,
    TicketInstructionsManager,
)


async def instructions_get() -> dict[str, Any]:
    """Get current ticket writing instructions.

    Retrieves the active instructions for the current project, which may be
    custom project-specific instructions or the default embedded instructions.

    Returns:
    -------
        A dictionary containing:
        - status: "completed" or "error"
        - instructions: The full instruction text (if successful)
        - source: "custom" or "default" indicating which instructions are active
        - path: Path to custom instructions file (if exists)
        - error: Error message (if failed)

    Example response:
        {
            "status": "completed",
            "instructions": "# Ticket Writing Guidelines...",
            "source": "custom",
            "path": "/path/to/project/.mcp-ticketer/instructions.md"
        }

    """
    try:
        # Use current working directory as project directory
        manager = TicketInstructionsManager(project_dir=Path.cwd())

        # Get instructions
        instructions = manager.get_instructions()

        # Determine source
        source = "custom" if manager.has_custom_instructions() else "default"

        # Build response
        response: dict[str, Any] = {
            "status": "completed",
            "instructions": instructions,
            "source": source,
        }

        # Add path if custom instructions exist
        if source == "custom":
            response["path"] = str(manager.get_instructions_path())

        return response

    except InstructionsError as e:
        return {
            "status": "error",
            "error": f"Failed to get instructions: {str(e)}",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
        }


async def instructions_set(content: str, source: str = "inline") -> dict[str, Any]:
    r"""Set custom ticket writing instructions for the project.

    Creates or overwrites custom instructions with the provided content.
    The content is validated before saving.

    Args:
    ----
        content: The custom instructions content (markdown text)
        source: Source type - "inline" for direct content or "file" for file path
            (currently only "inline" is supported by MCP tools)

    Returns:
    -------
        A dictionary containing:
        - status: "completed" or "error"
        - message: Success or error message
        - path: Path where instructions were saved (if successful)
        - error: Detailed error message (if failed)

    Example:
    -------
        To set custom instructions:
        instructions_set(
            content="# Our Team's Ticket Guidelines\\n\\n...",
            source="inline"
        )

    """
    try:
        # Validate source parameter
        if source not in ["inline", "file"]:
            return {
                "status": "error",
                "error": f"Invalid source '{source}'. Must be 'inline' or 'file'",
            }

        # Use current working directory as project directory
        manager = TicketInstructionsManager(project_dir=Path.cwd())

        # Set instructions
        manager.set_instructions(content)

        # Get path where instructions were saved
        inst_path = manager.get_instructions_path()

        return {
            "status": "completed",
            "message": "Custom instructions saved successfully",
            "path": str(inst_path),
        }

    except InstructionsValidationError as e:
        return {
            "status": "error",
            "error": f"Validation failed: {str(e)}",
            "message": "Instructions content did not pass validation checks",
        }
    except InstructionsError as e:
        return {
            "status": "error",
            "error": f"Failed to set instructions: {str(e)}",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
        }


async def instructions_reset() -> dict[str, Any]:
    """Reset to default instructions by deleting custom instructions.

    Removes any custom project-specific instructions, causing the system
    to revert to using the default embedded instructions.

    Returns:
    -------
        A dictionary containing:
        - status: "completed" or "error"
        - message: Description of what happened
        - error: Error message (if failed)

    Example response (when custom instructions existed):
        {
            "status": "completed",
            "message": "Custom instructions deleted. Now using defaults."
        }

    Example response (when no custom instructions):
        {
            "status": "completed",
            "message": "No custom instructions to delete. Already using defaults."
        }

    """
    try:
        # Use current working directory as project directory
        manager = TicketInstructionsManager(project_dir=Path.cwd())

        # Check if custom instructions exist
        if not manager.has_custom_instructions():
            return {
                "status": "completed",
                "message": "No custom instructions to delete. Already using defaults.",
            }

        # Delete custom instructions
        deleted = manager.delete_instructions()

        if deleted:
            return {
                "status": "completed",
                "message": "Custom instructions deleted. Now using defaults.",
            }
        else:
            return {
                "status": "completed",
                "message": "No custom instructions found to delete.",
            }

    except InstructionsError as e:
        return {
            "status": "error",
            "error": f"Failed to reset instructions: {str(e)}",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
        }


async def instructions_validate(content: str) -> dict[str, Any]:
    """Validate ticket instructions content without saving.

    Checks if the provided content meets validation requirements:
    - Not empty
    - Minimum length (100 characters)
    - Contains markdown headers (warning only)

    This allows AI agents to validate content before attempting to save it.

    Args:
    ----
        content: The instructions content to validate (markdown text)

    Returns:
    -------
        A dictionary containing:
        - status: "valid" or "invalid"
        - warnings: List of non-critical issues (e.g., missing headers)
        - errors: List of critical validation failures
        - message: Summary message

    Example response (valid):
        {
            "status": "valid",
            "warnings": ["No markdown headers found"],
            "errors": [],
            "message": "Content is valid but has 1 warning"
        }

    Example response (invalid):
        {
            "status": "invalid",
            "warnings": [],
            "errors": ["Content too short (50 characters). Minimum 100 required."],
            "message": "Content validation failed"
        }

    """
    warnings: list[str] = []
    errors: list[str] = []

    try:
        # Check for empty content
        if not content or not content.strip():
            errors.append("Instructions content cannot be empty")
        else:
            # Check minimum length
            if len(content.strip()) < 100:
                errors.append(
                    f"Content too short ({len(content)} characters). "
                    "Minimum 100 characters required for meaningful guidelines."
                )

            # Check for markdown headers (warning only)
            if not any(line.strip().startswith("#") for line in content.split("\n")):
                warnings.append(
                    "No markdown headers found. "
                    "Consider using headers for better structure."
                )

        # Determine status
        if errors:
            status = "invalid"
            message = "Content validation failed"
        elif warnings:
            status = "valid"
            message = f"Content is valid but has {len(warnings)} warning(s)"
        else:
            status = "valid"
            message = "Content is valid with no issues"

        return {
            "status": status,
            "warnings": warnings,
            "errors": errors,
            "message": message,
        }

    except Exception as e:
        return {
            "status": "error",
            "warnings": [],
            "errors": [f"Validation error: {str(e)}"],
            "message": "Validation process failed",
        }
