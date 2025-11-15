"""Unit tests for ticket instructions management.

Tests the TicketInstructionsManager class and related functionality including:
- Getting default and custom instructions
- Setting and validating instructions
- Deleting custom instructions
- File path management
- Error handling
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_ticketer.core.instructions import (
    InstructionsError,
    InstructionsNotFoundError,
    InstructionsValidationError,
    TicketInstructionsManager,
    get_instructions,
)


@pytest.mark.unit
class TestTicketInstructionsManager:
    """Test suite for TicketInstructionsManager."""

    def test_init_with_valid_directory(self, tmp_path: Path) -> None:
        """Test initialization with a valid directory."""
        manager = TicketInstructionsManager(tmp_path)
        assert manager.project_dir == tmp_path.resolve()

    def test_init_with_none_uses_cwd(self) -> None:
        """Test initialization with None uses current working directory."""
        manager = TicketInstructionsManager(None)
        assert manager.project_dir == Path.cwd().resolve()

    def test_init_with_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test initialization with non-existent directory raises error."""
        nonexistent = tmp_path / "does_not_exist"
        with pytest.raises(InstructionsError, match="does not exist"):
            TicketInstructionsManager(nonexistent)

    def test_init_with_file_path(self, tmp_path: Path) -> None:
        """Test initialization with file path raises error."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")
        with pytest.raises(InstructionsError, match="not a directory"):
            TicketInstructionsManager(file_path)

    def test_get_default_instructions(self, tmp_path: Path) -> None:
        """Test getting default instructions successfully."""
        manager = TicketInstructionsManager(tmp_path)
        instructions = manager.get_default_instructions()

        # Verify default instructions are not empty
        assert instructions
        assert len(instructions) > 100
        assert isinstance(instructions, str)

        # Verify it contains expected content
        assert "ticket" in instructions.lower() or "issue" in instructions.lower()

    def test_get_instructions_without_custom(self, tmp_path: Path) -> None:
        """Test get_instructions returns defaults when no custom exist."""
        manager = TicketInstructionsManager(tmp_path)
        instructions = manager.get_instructions()
        defaults = manager.get_default_instructions()

        # Should return the same as defaults
        assert instructions == defaults
        assert not manager.has_custom_instructions()

    def test_set_and_get_custom_instructions(self, tmp_path: Path) -> None:
        """Test setting and getting custom instructions."""
        manager = TicketInstructionsManager(tmp_path)

        custom_content = """
# Custom Ticket Instructions

This is a custom set of instructions for our team.

## Guidelines
- Write clear titles
- Add detailed descriptions
- Use proper labels

These instructions are at least 100 characters long to pass validation.
"""

        # Set custom instructions
        manager.set_instructions(custom_content)

        # Verify custom instructions exist
        assert manager.has_custom_instructions()

        # Verify get_instructions returns custom content
        retrieved = manager.get_instructions()
        assert retrieved == custom_content

        # Verify file was created at correct path
        expected_path = tmp_path / ".mcp-ticketer" / "instructions.md"
        assert expected_path.exists()
        assert expected_path.read_text() == custom_content

    def test_set_instructions_creates_directory(self, tmp_path: Path) -> None:
        """Test that setting instructions creates .mcp-ticketer directory."""
        manager = TicketInstructionsManager(tmp_path)

        config_dir = tmp_path / ".mcp-ticketer"
        assert not config_dir.exists()

        custom_content = "# Custom Instructions\n\n" + "x" * 100
        manager.set_instructions(custom_content)

        # Verify directory was created
        assert config_dir.exists()
        assert config_dir.is_dir()

    def test_set_instructions_from_file(self, tmp_path: Path) -> None:
        """Test setting instructions from a file."""
        manager = TicketInstructionsManager(tmp_path)

        # Create source file
        source_file = tmp_path / "source_instructions.md"
        source_content = "# Source Instructions\n\n" + "Content " * 50
        source_file.write_text(source_content)

        # Set instructions from file
        manager.set_instructions_from_file(source_file)

        # Verify custom instructions match source file
        assert manager.has_custom_instructions()
        assert manager.get_instructions() == source_content

    def test_set_instructions_from_missing_file(self, tmp_path: Path) -> None:
        """Test setting instructions from non-existent file raises error."""
        manager = TicketInstructionsManager(tmp_path)

        missing_file = tmp_path / "missing.md"
        with pytest.raises(InstructionsNotFoundError, match="not found"):
            manager.set_instructions_from_file(missing_file)

    def test_set_instructions_from_directory(self, tmp_path: Path) -> None:
        """Test setting instructions from directory path raises error."""
        manager = TicketInstructionsManager(tmp_path)

        directory = tmp_path / "subdir"
        directory.mkdir()

        with pytest.raises(InstructionsError, match="not a file"):
            manager.set_instructions_from_file(directory)

    def test_delete_custom_instructions(self, tmp_path: Path) -> None:
        """Test deleting custom instructions."""
        manager = TicketInstructionsManager(tmp_path)

        # Set custom instructions
        custom_content = "# Custom\n\n" + "x" * 100
        manager.set_instructions(custom_content)
        assert manager.has_custom_instructions()

        # Delete custom instructions
        result = manager.delete_instructions()
        assert result is True

        # Verify they're gone
        assert not manager.has_custom_instructions()

        # Verify get_instructions returns defaults
        instructions = manager.get_instructions()
        assert instructions == manager.get_default_instructions()

    def test_delete_when_no_custom_exist(self, tmp_path: Path) -> None:
        """Test deleting when no custom instructions exist returns False."""
        manager = TicketInstructionsManager(tmp_path)

        assert not manager.has_custom_instructions()

        # Try to delete non-existent custom instructions
        result = manager.delete_instructions()
        assert result is False

    def test_validate_empty_content(self, tmp_path: Path) -> None:
        """Test validation fails for empty content."""
        manager = TicketInstructionsManager(tmp_path)

        with pytest.raises(InstructionsValidationError, match="cannot be empty"):
            manager.set_instructions("")

        with pytest.raises(InstructionsValidationError, match="cannot be empty"):
            manager.set_instructions("   ")

    def test_validate_too_short_content(self, tmp_path: Path) -> None:
        """Test validation fails for content that's too short."""
        manager = TicketInstructionsManager(tmp_path)

        short_content = "Too short"
        with pytest.raises(InstructionsValidationError, match="too short"):
            manager.set_instructions(short_content)

        # Content with exactly 99 characters should fail
        almost_content = "x" * 99
        with pytest.raises(InstructionsValidationError, match="too short"):
            manager.set_instructions(almost_content)

    def test_validate_minimum_valid_length(self, tmp_path: Path) -> None:
        """Test that content with exactly 100 characters passes validation."""
        manager = TicketInstructionsManager(tmp_path)

        # Content with exactly 100 characters should pass
        valid_content = "x" * 100
        manager.set_instructions(valid_content)  # Should not raise

        assert manager.has_custom_instructions()

    def test_get_instructions_path(self, tmp_path: Path) -> None:
        """Test getting instructions file path."""
        manager = TicketInstructionsManager(tmp_path)

        expected_path = tmp_path / ".mcp-ticketer" / "instructions.md"
        assert manager.get_instructions_path() == expected_path

    def test_has_custom_instructions_false(self, tmp_path: Path) -> None:
        """Test has_custom_instructions returns False when no custom exist."""
        manager = TicketInstructionsManager(tmp_path)
        assert not manager.has_custom_instructions()

    def test_has_custom_instructions_true(self, tmp_path: Path) -> None:
        """Test has_custom_instructions returns True when custom exist."""
        manager = TicketInstructionsManager(tmp_path)

        # Set custom instructions
        custom_content = "# Custom\n\n" + "x" * 100
        manager.set_instructions(custom_content)

        assert manager.has_custom_instructions()

    def test_instructions_persistence(self, tmp_path: Path) -> None:
        """Test that instructions persist across manager instances."""
        custom_content = "# Persistent Instructions\n\n" + "x" * 100

        # Create first manager and set instructions
        manager1 = TicketInstructionsManager(tmp_path)
        manager1.set_instructions(custom_content)

        # Create second manager instance
        manager2 = TicketInstructionsManager(tmp_path)

        # Verify instructions are available in new instance
        assert manager2.has_custom_instructions()
        assert manager2.get_instructions() == custom_content

    def test_validation_warning_for_no_headers(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that instructions without markdown headers trigger a warning."""
        manager = TicketInstructionsManager(tmp_path)

        # Content without any markdown headers
        content_no_headers = "This is content without headers. " * 20

        manager.set_instructions(content_no_headers)

        # Check that a warning was logged
        assert any("headers" in record.message.lower() for record in caplog.records)

    def test_instructions_with_headers_no_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that instructions with markdown headers don't trigger warning."""
        manager = TicketInstructionsManager(tmp_path)

        # Content with markdown headers
        content_with_headers = (
            """
# Main Header

Some content here.

## Subheader

More content to make it long enough.
"""
            + "x" * 50
        )

        caplog.clear()
        manager.set_instructions(content_with_headers)

        # No warning should be logged (only check WARNING level, not INFO)
        header_warnings = [
            record
            for record in caplog.records
            if "headers" in record.message.lower() and record.levelname == "WARNING"
        ]
        assert len(header_warnings) == 0


@pytest.mark.unit
class TestGetInstructionsConvenience:
    """Test suite for get_instructions() convenience function."""

    def test_get_instructions_default(self, tmp_path: Path) -> None:
        """Test convenience function returns default instructions."""
        instructions = get_instructions(tmp_path)

        # Should return default instructions
        assert instructions
        assert len(instructions) > 100

    def test_get_instructions_custom(self, tmp_path: Path) -> None:
        """Test convenience function returns custom instructions when they exist."""
        # Set custom instructions first
        manager = TicketInstructionsManager(tmp_path)
        custom_content = "# Custom\n\n" + "x" * 100
        manager.set_instructions(custom_content)

        # Use convenience function
        instructions = get_instructions(tmp_path)

        # Should return custom instructions
        assert instructions == custom_content

    def test_get_instructions_with_none_path(self) -> None:
        """Test convenience function works with None path (uses cwd)."""
        instructions = get_instructions(None)

        # Should return some instructions (default or custom)
        assert instructions
        assert isinstance(instructions, str)


@pytest.mark.unit
class TestInstructionsExceptions:
    """Test suite for instruction-related exceptions."""

    def test_instructions_error_inheritance(self) -> None:
        """Test that InstructionsError inherits from MCPTicketerError."""
        from mcp_ticketer.core.exceptions import MCPTicketerError

        error = InstructionsError("test")
        assert isinstance(error, MCPTicketerError)

    def test_instructions_not_found_error_inheritance(self) -> None:
        """Test that InstructionsNotFoundError inherits from InstructionsError."""
        error = InstructionsNotFoundError("test")
        assert isinstance(error, InstructionsError)

    def test_instructions_validation_error_inheritance(self) -> None:
        """Test that InstructionsValidationError inherits from InstructionsError."""
        error = InstructionsValidationError("test")
        assert isinstance(error, InstructionsError)

    def test_error_messages(self) -> None:
        """Test that exceptions preserve error messages."""
        message = "Custom error message"

        error1 = InstructionsError(message)
        assert str(error1) == message

        error2 = InstructionsNotFoundError(message)
        assert str(error2) == message

        error3 = InstructionsValidationError(message)
        assert str(error3) == message


@pytest.mark.unit
class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    def test_unicode_content(self, tmp_path: Path) -> None:
        """Test handling of unicode content in instructions."""
        manager = TicketInstructionsManager(tmp_path)

        # Content with unicode characters
        unicode_content = (
            """
# Ticket Guidelines 🎯

Use emojis sparingly: ✅ ❌ ⚠️

Special characters: café, naïve, 日本語

This is long enough to pass validation.
"""
            + "x" * 50
        )

        manager.set_instructions(unicode_content)
        retrieved = manager.get_instructions()

        assert retrieved == unicode_content
        assert "🎯" in retrieved
        assert "日本語" in retrieved

    def test_very_long_content(self, tmp_path: Path) -> None:
        """Test handling of very long instruction content."""
        manager = TicketInstructionsManager(tmp_path)

        # Create very long content (10KB)
        long_content = "# Long Instructions\n\n" + ("Content " * 2000)

        manager.set_instructions(long_content)
        retrieved = manager.get_instructions()

        assert retrieved == long_content
        assert len(retrieved) > 10000

    def test_multiline_content_preservation(self, tmp_path: Path) -> None:
        """Test that multiline content is preserved correctly."""
        manager = TicketInstructionsManager(tmp_path)

        multiline_content = """# Title

Paragraph 1

Paragraph 2

- List item 1
- List item 2

```code
example
```

End content with extra newlines.


"""

        manager.set_instructions(multiline_content)
        retrieved = manager.get_instructions()

        assert retrieved == multiline_content

    def test_instructions_path_components(self, tmp_path: Path) -> None:
        """Test that instructions path uses correct directory and filename."""
        manager = TicketInstructionsManager(tmp_path)

        path = manager.get_instructions_path()

        # Verify path components
        assert path.parent.name == ".mcp-ticketer"
        assert path.name == "instructions.md"
        assert path.parent.parent == tmp_path

    def test_concurrent_manager_instances(self, tmp_path: Path) -> None:
        """Test multiple manager instances don't interfere with each other."""
        manager1 = TicketInstructionsManager(tmp_path)
        manager2 = TicketInstructionsManager(tmp_path)

        content = "# Instructions\n\n" + "x" * 100

        # Set via manager1
        manager1.set_instructions(content)

        # Should be visible via manager2
        assert manager2.has_custom_instructions()
        assert manager2.get_instructions() == content

        # Delete via manager2
        manager2.delete_instructions()

        # Should be gone for manager1
        assert not manager1.has_custom_instructions()
