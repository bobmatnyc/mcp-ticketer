"""Ticket writing instructions management.

This module provides a unified interface for managing ticket writing instructions
that guide AI agents and users in creating well-structured, consistent tickets.

The instructions can be:
- Default (embedded in the package)
- Custom (project-specific, stored in .mcp-ticketer/instructions.md)

Example:
    >>> from mcp_ticketer.core.instructions import get_instructions
    >>> instructions = get_instructions()
    >>> print(instructions)

    >>> # For project-specific management
    >>> from mcp_ticketer.core.instructions import TicketInstructionsManager
    >>> manager = TicketInstructionsManager(project_dir="/path/to/project")
    >>> manager.set_instructions("Custom instructions here...")
    >>> if manager.has_custom_instructions():
    ...     print("Using custom instructions")

"""

from __future__ import annotations

import logging
from pathlib import Path

from .exceptions import MCPTicketerError

logger = logging.getLogger(__name__)


class InstructionsError(MCPTicketerError):
    """Base exception for instructions-related errors.

    Raised when there are issues loading, saving, or validating ticket
    writing instructions.
    """

    pass


class InstructionsNotFoundError(InstructionsError):
    """Exception raised when instructions file cannot be found.

    This typically occurs when trying to load custom instructions from a
    file path that doesn't exist, or when the default instructions file
    is missing from the package.
    """

    pass


class InstructionsValidationError(InstructionsError):
    """Exception raised when instructions content is invalid.

    Raised when instructions content fails validation rules such as:
    - Empty content
    - Content too short (< 100 characters)
    - Invalid encoding
    """

    pass


class TicketInstructionsManager:
    """Manages ticket writing instructions for a project.

    This class handles loading, saving, and validating ticket writing instructions.
    It supports both default (embedded) instructions and custom project-specific
    instructions.

    The default instructions are embedded in the package at:
        src/mcp_ticketer/defaults/ticket_instructions.md

    Custom instructions are stored in the project directory at:
        {project_dir}/.mcp-ticketer/instructions.md

    Attributes:
        project_dir: Path to the project root directory

    Example:
        >>> manager = TicketInstructionsManager("/path/to/project")
        >>> instructions = manager.get_instructions()
        >>> print(f"Using {'custom' if manager.has_custom_instructions() else 'default'}")

        >>> # Set custom instructions
        >>> manager.set_instructions("My custom guidelines...")
        >>> assert manager.has_custom_instructions()

        >>> # Revert to defaults
        >>> manager.delete_instructions()
        >>> assert not manager.has_custom_instructions()

    """

    # Class-level constant for custom instructions filename
    INSTRUCTIONS_FILENAME = "instructions.md"
    DEFAULT_INSTRUCTIONS_FILENAME = "ticket_instructions.md"
    CONFIG_DIR = ".mcp-ticketer"

    def __init__(self, project_dir: str | Path | None = None):
        """Initialize the instructions manager.

        Args:
            project_dir: Path to the project root directory. If None, uses current
                working directory. The project directory is where the .mcp-ticketer
                folder will be created for custom instructions.

        Raises:
            InstructionsError: If project_dir is invalid or inaccessible

        """
        if project_dir is None:
            project_dir = Path.cwd()
        else:
            project_dir = Path(project_dir)

        if not project_dir.exists():
            raise InstructionsError(f"Project directory does not exist: {project_dir}")

        if not project_dir.is_dir():
            raise InstructionsError(f"Project path is not a directory: {project_dir}")

        self.project_dir = project_dir.resolve()
        logger.debug(f"Initialized TicketInstructionsManager for: {self.project_dir}")

    def get_instructions(self) -> str:
        """Get the current ticket writing instructions.

        Returns custom instructions if they exist, otherwise returns the default
        embedded instructions.

        Returns:
            The ticket writing instructions as a string

        Raises:
            InstructionsError: If instructions cannot be loaded
            InstructionsNotFoundError: If default instructions are missing (package error)

        Example:
            >>> manager = TicketInstructionsManager()
            >>> instructions = manager.get_instructions()
            >>> # Use instructions to guide ticket creation
            >>> print(instructions[:100])

        """
        if self.has_custom_instructions():
            logger.debug("Loading custom instructions")
            custom_path = self.get_instructions_path()
            try:
                return custom_path.read_text(encoding="utf-8")
            except Exception as e:
                raise InstructionsError(
                    f"Failed to read custom instructions from {custom_path}: {e}"
                ) from e
        else:
            logger.debug("Loading default instructions")
            return self.get_default_instructions()

    def get_default_instructions(self) -> str:
        """Get the default embedded ticket writing instructions.

        The default instructions are shipped with the package and provide
        comprehensive guidelines for ticket creation.

        Returns:
            The default ticket writing instructions as a string

        Raises:
            InstructionsNotFoundError: If the default instructions file is missing
                from the package (indicates package corruption or installation issue)

        Example:
            >>> manager = TicketInstructionsManager()
            >>> defaults = manager.get_default_instructions()
            >>> # Always returns the same content regardless of project

        """
        # Get the path to the defaults directory (sibling to core)
        package_root = Path(__file__).parent.parent
        default_path = package_root / "defaults" / self.DEFAULT_INSTRUCTIONS_FILENAME

        if not default_path.exists():
            raise InstructionsNotFoundError(
                f"Default instructions file not found at: {default_path}. "
                "This indicates a package installation issue."
            )

        try:
            content = default_path.read_text(encoding="utf-8")
            logger.debug(f"Loaded default instructions from {default_path}")
            return content
        except Exception as e:
            raise InstructionsError(
                f"Failed to read default instructions from {default_path}: {e}"
            ) from e

    def set_instructions(self, content: str) -> None:
        r"""Set custom ticket writing instructions for the project.

        Creates or overwrites the custom instructions file in the project's
        .mcp-ticketer directory. The content is validated before saving.

        Args:
            content: The custom instructions content to save

        Raises:
            InstructionsValidationError: If content fails validation
            InstructionsError: If instructions cannot be written to disk

        Example:
            >>> manager = TicketInstructionsManager()
            >>> custom = "# My Team's Ticket Guidelines\n\n..."
            >>> manager.set_instructions(custom)
            >>> assert manager.has_custom_instructions()

        """
        # Validate content
        self._validate_instructions(content)

        # Ensure config directory exists
        config_dir = self.project_dir / self.CONFIG_DIR
        config_dir.mkdir(exist_ok=True, parents=True)

        # Write instructions file
        instructions_path = self.get_instructions_path()
        try:
            instructions_path.write_text(content, encoding="utf-8")
            logger.info(f"Saved custom instructions to {instructions_path}")
        except Exception as e:
            raise InstructionsError(
                f"Failed to write instructions to {instructions_path}: {e}"
            ) from e

    def set_instructions_from_file(self, file_path: str | Path) -> None:
        """Load and set custom instructions from a file.

        Reads instructions from the specified file and sets them as custom
        instructions for the project. The file content is validated before saving.

        Args:
            file_path: Path to the file containing instructions

        Raises:
            InstructionsNotFoundError: If the source file doesn't exist
            InstructionsValidationError: If file content fails validation
            InstructionsError: If instructions cannot be loaded or saved

        Example:
            >>> manager = TicketInstructionsManager()
            >>> manager.set_instructions_from_file("team_guidelines.md")
            >>> assert manager.has_custom_instructions()

        """
        source_path = Path(file_path)

        if not source_path.exists():
            raise InstructionsNotFoundError(
                f"Instructions file not found: {source_path}"
            )

        if not source_path.is_file():
            raise InstructionsError(f"Path is not a file: {source_path}")

        try:
            content = source_path.read_text(encoding="utf-8")
            logger.debug(f"Read instructions from {source_path}")
        except Exception as e:
            raise InstructionsError(
                f"Failed to read instructions from {source_path}: {e}"
            ) from e

        # Use set_instructions to validate and save
        self.set_instructions(content)

    def delete_instructions(self) -> bool:
        """Delete custom instructions and revert to defaults.

        Removes the custom instructions file if it exists. After deletion,
        get_instructions() will return the default instructions.

        Returns:
            True if custom instructions were deleted, False if they didn't exist

        Raises:
            InstructionsError: If instructions file cannot be deleted

        Example:
            >>> manager = TicketInstructionsManager()
            >>> manager.set_instructions("Custom instructions")
            >>> assert manager.delete_instructions()  # Returns True
            >>> assert not manager.has_custom_instructions()
            >>> assert not manager.delete_instructions()  # Returns False

        """
        instructions_path = self.get_instructions_path()

        if not instructions_path.exists():
            logger.debug("No custom instructions to delete")
            return False

        try:
            instructions_path.unlink()
            logger.info(f"Deleted custom instructions at {instructions_path}")
            return True
        except Exception as e:
            raise InstructionsError(
                f"Failed to delete instructions at {instructions_path}: {e}"
            ) from e

    def has_custom_instructions(self) -> bool:
        """Check if custom instructions exist for this project.

        Returns:
            True if custom instructions file exists, False otherwise

        Example:
            >>> manager = TicketInstructionsManager()
            >>> if manager.has_custom_instructions():
            ...     print("Using project-specific guidelines")
            ... else:
            ...     print("Using default guidelines")

        """
        return self.get_instructions_path().exists()

    def get_instructions_path(self) -> Path:
        """Get the path to the custom instructions file.

        Returns:
            Path object pointing to where custom instructions are (or would be) stored

        Note:
            This returns the path even if the file doesn't exist yet. Use
            has_custom_instructions() to check if the file exists.

        Example:
            >>> manager = TicketInstructionsManager("/path/to/project")
            >>> path = manager.get_instructions_path()
            >>> print(path)  # /path/to/project/.mcp-ticketer/instructions.md

        """
        return self.project_dir / self.CONFIG_DIR / self.INSTRUCTIONS_FILENAME

    def _validate_instructions(self, content: str) -> None:
        """Validate instructions content.

        Performs validation checks on instructions content:
        - Not empty
        - Minimum length (100 characters)
        - Contains markdown headers (warning only)

        Args:
            content: The instructions content to validate

        Raises:
            InstructionsValidationError: If content fails validation

        """
        if not content or not content.strip():
            raise InstructionsValidationError("Instructions content cannot be empty")

        if len(content.strip()) < 100:
            raise InstructionsValidationError(
                f"Instructions content too short ({len(content)} characters). "
                "Minimum 100 characters required for meaningful guidelines."
            )

        # Warn if no markdown headers (not an error, just a quality check)
        if not any(line.strip().startswith("#") for line in content.split("\n")):
            logger.warning(
                "Instructions don't contain markdown headers. "
                "Consider using headers for better structure."
            )


def get_instructions(project_dir: str | Path | None = None) -> str:
    """Get ticket writing instructions for a project.

    This is a shorthand for creating a TicketInstructionsManager and calling
    get_instructions(). Useful for simple cases where you just need the content.

    Args:
        project_dir: Path to the project root directory. If None, uses current
            working directory.

    Returns:
        The ticket writing instructions (custom if available, otherwise default)

    Raises:
        InstructionsError: If instructions cannot be loaded

    Example:
        >>> from mcp_ticketer.core.instructions import get_instructions
        >>> instructions = get_instructions()
        >>> # Use instructions to guide ticket creation

        >>> # For specific project
        >>> instructions = get_instructions("/path/to/project")

    """
    manager = TicketInstructionsManager(project_dir)
    return manager.get_instructions()
