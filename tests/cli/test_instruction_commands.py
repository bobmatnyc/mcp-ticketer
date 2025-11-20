"""CLI tests for ticket instructions commands.

Tests the CLI commands for managing ticket instructions including:
- show command (default, raw output)
- add command (from file, stdin)
- update command
- delete command (with confirmation)
- path command
- edit command
- Error handling
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from mcp_ticketer.cli.instruction_commands import app

runner = CliRunner()


@pytest.mark.unit
class TestShowCommand:
    """Test suite for 'instructions show' command."""

    def test_show_default_instructions(self, tmp_path: Path) -> None:
        """Test showing default instructions when no custom exist."""
        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.has_custom_instructions.return_value = False
            mock_manager.get_instructions.return_value = (
                "# Default Instructions\n\nDefault content"
            )
            mock_manager.get_default_instructions.return_value = (
                "# Default Instructions\n\nDefault content"
            )
            mock_cls.return_value = mock_manager

            result = runner.invoke(app, ["show"])

            assert result.exit_code == 0
            assert "Default Instructions" in result.stdout

    def test_show_custom_instructions(self, tmp_path: Path) -> None:
        """Test showing custom instructions when they exist."""
        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.has_custom_instructions.return_value = True
            mock_manager.get_instructions.return_value = (
                "# Custom Instructions\n\nCustom content"
            )
            mock_manager.get_instructions_path.return_value = Path(
                "/test/instructions.md"
            )
            mock_cls.return_value = mock_manager

            result = runner.invoke(app, ["show"])

            assert result.exit_code == 0
            assert "Custom" in result.stdout

    def test_show_default_flag(self, tmp_path: Path) -> None:
        """Test showing default instructions with --default flag."""
        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.get_default_instructions.return_value = (
                "# Default\n\nDefault content"
            )
            mock_cls.return_value = mock_manager

            result = runner.invoke(app, ["show", "--default"])

            assert result.exit_code == 0
            mock_manager.get_default_instructions.assert_called_once()

    def test_show_raw_output(self, tmp_path: Path) -> None:
        """Test showing raw markdown output with --raw flag."""
        raw_content = "# Raw Instructions\n\nRaw markdown content"

        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.has_custom_instructions.return_value = False
            mock_manager.get_instructions.return_value = raw_content
            mock_cls.return_value = mock_manager

            result = runner.invoke(app, ["show", "--raw"])

            assert result.exit_code == 0
            assert raw_content in result.stdout

    def test_show_error_handling(self) -> None:
        """Test error handling in show command."""
        from mcp_ticketer.core.instructions import InstructionsError

        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_cls.side_effect = InstructionsError("Test error")

            result = runner.invoke(app, ["show"])

            assert result.exit_code == 1
            assert "Error" in result.stdout or "Test error" in result.stdout


@pytest.mark.unit
class TestAddCommand:
    """Test suite for 'instructions add' command."""

    def test_add_from_file(self, tmp_path: Path) -> None:
        """Test adding instructions from a file."""
        # Create source file
        source_file = tmp_path / "source.md"
        source_content = "# Custom Instructions\n\n" + "x" * 100
        source_file.write_text(source_content)

        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.has_custom_instructions.return_value = False
            mock_manager.get_instructions_path.return_value = (
                tmp_path / "instructions.md"
            )
            mock_cls.return_value = mock_manager

            # Mock Path operations
            with patch("mcp_ticketer.cli.instruction_commands.Path") as mock_path_cls:
                mock_path = Mock()
                mock_path.exists.return_value = True
                mock_path.read_text.return_value = source_content
                mock_path_cls.return_value = mock_path

                result = runner.invoke(app, ["add", str(source_file)])

                assert result.exit_code == 0
                assert "saved" in result.stdout.lower()
                mock_manager.set_instructions.assert_called_once_with(source_content)

    def test_add_from_missing_file(self, tmp_path: Path) -> None:
        """Test adding from non-existent file shows error."""
        missing_file = tmp_path / "missing.md"

        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.has_custom_instructions.return_value = False
            mock_cls.return_value = mock_manager

            with patch("mcp_ticketer.cli.instruction_commands.Path") as mock_path_cls:
                mock_path = Mock()
                mock_path.exists.return_value = False
                mock_path_cls.return_value = mock_path

                result = runner.invoke(app, ["add", str(missing_file)])

                assert result.exit_code == 1
                assert "not found" in result.stdout.lower()

    def test_add_from_stdin(self, tmp_path: Path) -> None:
        """Test adding instructions from stdin."""
        stdin_content = "# Stdin Instructions\n\n" + "x" * 100

        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.has_custom_instructions.return_value = False
            mock_manager.get_instructions_path.return_value = (
                tmp_path / "instructions.md"
            )
            mock_cls.return_value = mock_manager

            # Simulate stdin input
            result = runner.invoke(app, ["add", "--stdin"], input=stdin_content)

            assert result.exit_code == 0
            assert "saved" in result.stdout.lower()
            mock_manager.set_instructions.assert_called_once_with(stdin_content)

    def test_add_with_empty_stdin(self) -> None:
        """Test adding with empty stdin shows error."""
        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.has_custom_instructions.return_value = False
            mock_cls.return_value = mock_manager

            result = runner.invoke(app, ["add", "--stdin"], input="   ")

            assert result.exit_code == 1
            assert "no content" in result.stdout.lower()

    def test_add_without_file_or_stdin(self) -> None:
        """Test add without file or stdin shows error."""
        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.has_custom_instructions.return_value = (
                False  # No existing custom
            )
            mock_cls.return_value = mock_manager

            result = runner.invoke(app, ["add"])

            assert result.exit_code == 1
            assert "error" in result.stdout.lower()

    def test_add_with_existing_instructions_confirmation(self, tmp_path: Path) -> None:
        """Test add with existing instructions prompts for confirmation."""
        source_file = tmp_path / "source.md"
        source_content = "# New Content\n\n" + "x" * 100
        source_file.write_text(source_content)

        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.has_custom_instructions.return_value = True
            mock_manager.get_instructions_path.return_value = tmp_path / "existing.md"
            mock_cls.return_value = mock_manager

            with patch("mcp_ticketer.cli.instruction_commands.Path") as mock_path_cls:
                mock_path = Mock()
                mock_path.exists.return_value = True
                mock_path.read_text.return_value = source_content
                mock_path_cls.return_value = mock_path

                # User confirms overwrite
                result = runner.invoke(app, ["add", str(source_file)], input="y\n")

                assert result.exit_code == 0
                assert "warning" in result.stdout.lower()
                mock_manager.set_instructions.assert_called_once()

    def test_add_with_existing_instructions_cancel(self, tmp_path: Path) -> None:
        """Test add with existing instructions can be cancelled."""
        source_file = tmp_path / "source.md"
        source_file.write_text("# Content\n\n" + "x" * 100)

        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.has_custom_instructions.return_value = True
            mock_manager.get_instructions_path.return_value = tmp_path / "existing.md"
            mock_cls.return_value = mock_manager

            with patch("mcp_ticketer.cli.instruction_commands.Path") as mock_path_cls:
                mock_path = Mock()
                mock_path.exists.return_value = True
                mock_path_cls.return_value = mock_path

                # User cancels
                result = runner.invoke(app, ["add", str(source_file)], input="n\n")

                assert result.exit_code == 0
                assert "cancelled" in result.stdout.lower()
                mock_manager.set_instructions.assert_not_called()

    def test_add_with_force_flag(self, tmp_path: Path) -> None:
        """Test add with --force flag skips confirmation."""
        source_file = tmp_path / "source.md"
        source_content = "# Content\n\n" + "x" * 100
        source_file.write_text(source_content)

        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.has_custom_instructions.return_value = True
            mock_manager.get_instructions_path.return_value = (
                tmp_path / "instructions.md"
            )
            mock_cls.return_value = mock_manager

            with patch("mcp_ticketer.cli.instruction_commands.Path") as mock_path_cls:
                mock_path = Mock()
                mock_path.exists.return_value = True
                mock_path.read_text.return_value = source_content
                mock_path_cls.return_value = mock_path

                result = runner.invoke(app, ["add", str(source_file), "--force"])

                assert result.exit_code == 0
                # Should not prompt for confirmation
                assert "overwrite" not in result.stdout.lower()
                mock_manager.set_instructions.assert_called_once()

    def test_add_validation_error(self, tmp_path: Path) -> None:
        """Test add with validation error shows error message."""
        from mcp_ticketer.core.instructions import InstructionsValidationError

        source_file = tmp_path / "source.md"
        source_file.write_text("Short")

        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.has_custom_instructions.return_value = False
            mock_manager.set_instructions.side_effect = InstructionsValidationError(
                "Too short"
            )
            mock_cls.return_value = mock_manager

            with patch("mcp_ticketer.cli.instruction_commands.Path") as mock_path_cls:
                mock_path = Mock()
                mock_path.exists.return_value = True
                mock_path.read_text.return_value = "Short"
                mock_path_cls.return_value = mock_path

                result = runner.invoke(app, ["add", str(source_file)])

                assert result.exit_code == 1
                assert "validation" in result.stdout.lower()


@pytest.mark.unit
class TestUpdateCommand:
    """Test suite for 'instructions update' command."""

    def test_update_from_file(self, tmp_path: Path) -> None:
        """Test updating instructions from a file."""
        source_file = tmp_path / "updated.md"
        source_content = "# Updated Instructions\n\n" + "x" * 100
        source_file.write_text(source_content)

        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.has_custom_instructions.return_value = True
            mock_manager.get_instructions_path.return_value = (
                tmp_path / "instructions.md"
            )
            mock_cls.return_value = mock_manager

            with patch("mcp_ticketer.cli.instruction_commands.Path") as mock_path_cls:
                mock_path = Mock()
                mock_path.exists.return_value = True
                mock_path.read_text.return_value = source_content
                mock_path_cls.return_value = mock_path

                result = runner.invoke(app, ["update", str(source_file)])

                assert result.exit_code == 0
                assert "updated" in result.stdout.lower()
                mock_manager.set_instructions.assert_called_once_with(source_content)

    def test_update_without_existing_custom(self) -> None:
        """Test update without existing custom instructions shows warning."""
        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.has_custom_instructions.return_value = False
            mock_cls.return_value = mock_manager

            result = runner.invoke(app, ["update", "file.md"])

            assert result.exit_code == 1
            assert "warning" in result.stdout.lower()
            assert "no custom" in result.stdout.lower()

    def test_update_from_stdin(self, tmp_path: Path) -> None:
        """Test updating instructions from stdin."""
        stdin_content = "# Updated\n\n" + "x" * 100

        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.has_custom_instructions.return_value = True
            mock_manager.get_instructions_path.return_value = (
                tmp_path / "instructions.md"
            )
            mock_cls.return_value = mock_manager

            result = runner.invoke(app, ["update", "--stdin"], input=stdin_content)

            assert result.exit_code == 0
            assert "updated" in result.stdout.lower()
            mock_manager.set_instructions.assert_called_once_with(stdin_content)


@pytest.mark.unit
class TestDeleteCommand:
    """Test suite for 'instructions delete' command."""

    def test_delete_with_confirmation(self, tmp_path: Path) -> None:
        """Test deleting instructions with confirmation."""
        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.has_custom_instructions.return_value = True
            mock_manager.get_instructions_path.return_value = (
                tmp_path / "instructions.md"
            )
            mock_cls.return_value = mock_manager

            # User confirms deletion
            result = runner.invoke(app, ["delete"], input="y\n")

            assert result.exit_code == 0
            assert "deleted" in result.stdout.lower()
            mock_manager.delete_instructions.assert_called_once()

    def test_delete_with_cancel(self) -> None:
        """Test cancelling deletion."""
        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.has_custom_instructions.return_value = True
            mock_manager.get_instructions_path.return_value = Path(
                "/test/instructions.md"
            )
            mock_cls.return_value = mock_manager

            # User cancels
            result = runner.invoke(app, ["delete"], input="n\n")

            assert result.exit_code == 0
            assert "cancelled" in result.stdout.lower()
            mock_manager.delete_instructions.assert_not_called()

    def test_delete_with_yes_flag(self) -> None:
        """Test delete with --yes flag skips confirmation."""
        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.has_custom_instructions.return_value = True
            mock_manager.get_instructions_path.return_value = Path(
                "/test/instructions.md"
            )
            mock_cls.return_value = mock_manager

            result = runner.invoke(app, ["delete", "--yes"])

            assert result.exit_code == 0
            assert "deleted" in result.stdout.lower()
            # Should not show confirmation prompt
            assert "are you sure" not in result.stdout.lower()
            mock_manager.delete_instructions.assert_called_once()

    def test_delete_when_no_custom_exist(self) -> None:
        """Test delete when no custom instructions exist."""
        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.has_custom_instructions.return_value = False
            mock_cls.return_value = mock_manager

            result = runner.invoke(app, ["delete"])

            assert result.exit_code == 0
            assert "no custom" in result.stdout.lower()
            mock_manager.delete_instructions.assert_not_called()


@pytest.mark.unit
class TestPathCommand:
    """Test suite for 'instructions path' command."""

    def test_path_with_custom_instructions(self, tmp_path: Path) -> None:
        """Test path command when custom instructions exist."""
        inst_path = tmp_path / ".mcp-ticketer" / "instructions.md"

        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.get_instructions_path.return_value = inst_path
            mock_manager.has_custom_instructions.return_value = True
            mock_cls.return_value = mock_manager

            # Mock stat for file size
            with patch.object(Path, "stat") as mock_stat:
                mock_stat.return_value.st_size = 1024

                result = runner.invoke(app, ["path"])

                assert result.exit_code == 0
                # Path might be wrapped across lines in output, so check for filename
                assert "instructions.md" in result.stdout
                assert "custom instructions exist" in result.stdout.lower()

    def test_path_without_custom_instructions(self, tmp_path: Path) -> None:
        """Test path command when no custom instructions exist."""
        inst_path = tmp_path / ".mcp-ticketer" / "instructions.md"

        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_manager = Mock()
            mock_manager.get_instructions_path.return_value = inst_path
            mock_manager.has_custom_instructions.return_value = False
            mock_cls.return_value = mock_manager

            result = runner.invoke(app, ["path"])

            assert result.exit_code == 0
            assert "instructions.md" in result.stdout
            assert "no custom" in result.stdout.lower()


@pytest.mark.unit
class TestEditCommand:
    """Test suite for 'instructions edit' command."""

    def test_edit_error_handling(self, tmp_path: Path) -> None:
        """Test edit command error handling."""
        from mcp_ticketer.core.instructions import InstructionsError

        with patch(
            "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
        ) as mock_cls:
            mock_cls.side_effect = InstructionsError("Test error")

            result = runner.invoke(app, ["edit"])

            assert result.exit_code == 1
            assert "error" in result.stdout.lower()

    # Note: Full edit workflow testing is covered in integration tests
    # due to complexity of mocking subprocess and environment
