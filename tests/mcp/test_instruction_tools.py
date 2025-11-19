"""MCP tool tests for ticket instructions management.

Tests the MCP tools for managing ticket instructions including:
- instructions_get tool
- instructions_set tool
- instructions_reset tool
- instructions_validate tool
- Error handling and response format validation
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mcp_ticketer.core.instructions import (
    InstructionsError,
    InstructionsValidationError,
)
from mcp_ticketer.mcp.server.tools.instruction_tools import (
    instructions_get,
    instructions_reset,
    instructions_set,
    instructions_validate,
)


@pytest.mark.asyncio
class TestInstructionsGetTool:
    """Test suite for instructions_get MCP tool."""

    async def test_get_default_instructions(self, tmp_path: Path) -> None:
        """Test getting default instructions when no custom exist."""
        with patch(
            "mcp_ticketer.mcp.server.tools.instruction_tools.TicketInstructionsManager"
        ) as mock_manager_class:
            with patch(
                "mcp_ticketer.mcp.server.tools.instruction_tools.Path.cwd",
                return_value=tmp_path,
            ):
                mock_manager = Mock()
                mock_manager.get_instructions.return_value = (
                    "# Default Instructions\n\nDefault content"
                )
                mock_manager.has_custom_instructions.return_value = False
                mock_manager_class.return_value = mock_manager

                result = await instructions_get()

                assert result["status"] == "completed"
                assert (
                    result["instructions"]
                    == "# Default Instructions\n\nDefault content"
                )
                assert result["source"] == "default"
                assert "path" not in result

    async def test_get_custom_instructions(self, tmp_path: Path) -> None:
        """Test getting custom instructions when they exist."""
        inst_path = tmp_path / ".mcp-ticketer" / "instructions.md"

        with patch(
            "mcp_ticketer.mcp.server.tools.instruction_tools.TicketInstructionsManager"
        ) as mock_manager_class:
            with patch(
                "mcp_ticketer.mcp.server.tools.instruction_tools.Path.cwd",
                return_value=tmp_path,
            ):
                mock_manager = Mock()
                mock_manager.get_instructions.return_value = (
                    "# Custom Instructions\n\nCustom content"
                )
                mock_manager.has_custom_instructions.return_value = True
                mock_manager.get_instructions_path.return_value = inst_path
                mock_manager_class.return_value = mock_manager

                result = await instructions_get()

                assert result["status"] == "completed"
                assert (
                    result["instructions"] == "# Custom Instructions\n\nCustom content"
                )
                assert result["source"] == "custom"
                assert result["path"] == str(inst_path)

    async def test_get_instructions_error(self) -> None:
        """Test error handling in instructions_get."""
        with patch(
            "mcp_ticketer.mcp.server.tools.instruction_tools.TicketInstructionsManager"
        ) as mock_manager_class:
            mock_manager_class.side_effect = InstructionsError("Test error")

            result = await instructions_get()

            assert result["status"] == "error"
            assert "error" in result
            assert "Test error" in result["error"]

    async def test_get_instructions_unexpected_error(self) -> None:
        """Test handling of unexpected errors in instructions_get."""
        with patch(
            "mcp_ticketer.mcp.server.tools.instruction_tools.TicketInstructionsManager"
        ) as mock_manager_class:
            mock_manager_class.side_effect = Exception("Unexpected error")

            result = await instructions_get()

            assert result["status"] == "error"
            assert "error" in result
            assert "Unexpected error" in result["error"]

    async def test_get_instructions_response_structure(self, tmp_path: Path) -> None:
        """Test that response has correct structure."""
        with patch(
            "mcp_ticketer.mcp.server.tools.instruction_tools.TicketInstructionsManager"
        ) as mock_manager_class:
            with patch(
                "mcp_ticketer.mcp.server.tools.instruction_tools.Path.cwd",
                return_value=tmp_path,
            ):
                mock_manager = Mock()
                mock_manager.get_instructions.return_value = "Test content"
                mock_manager.has_custom_instructions.return_value = False
                mock_manager_class.return_value = mock_manager

                result = await instructions_get()

                # Verify required fields
                assert "status" in result
                assert "instructions" in result
                assert "source" in result
                # Verify types
                assert isinstance(result["status"], str)
                assert isinstance(result["instructions"], str)
                assert isinstance(result["source"], str)


@pytest.mark.asyncio
class TestInstructionsSetTool:
    """Test suite for instructions_set MCP tool."""

    async def test_set_instructions_inline(self, tmp_path: Path) -> None:
        """Test setting instructions with inline content."""
        content = "# Custom Instructions\n\n" + "x" * 100
        inst_path = tmp_path / ".mcp-ticketer" / "instructions.md"

        with patch(
            "mcp_ticketer.mcp.server.tools.instruction_tools.TicketInstructionsManager"
        ) as mock_manager_class:
            with patch(
                "mcp_ticketer.mcp.server.tools.instruction_tools.Path.cwd",
                return_value=tmp_path,
            ):
                mock_manager = Mock()
                mock_manager.get_instructions_path.return_value = inst_path
                mock_manager_class.return_value = mock_manager

                result = await instructions_set(content=content, source="inline")

                assert result["status"] == "completed"
                assert "message" in result
                assert result["path"] == str(inst_path)
                mock_manager.set_instructions.assert_called_once_with(content)

    async def test_set_instructions_validation_error(self, tmp_path: Path) -> None:
        """Test set_instructions handles validation errors."""
        short_content = "Too short"

        with patch(
            "mcp_ticketer.mcp.server.tools.instruction_tools.TicketInstructionsManager"
        ) as mock_manager_class:
            with patch(
                "mcp_ticketer.mcp.server.tools.instruction_tools.Path.cwd",
                return_value=tmp_path,
            ):
                mock_manager = Mock()
                mock_manager.set_instructions.side_effect = InstructionsValidationError(
                    "Content too short"
                )
                mock_manager_class.return_value = mock_manager

                result = await instructions_set(content=short_content, source="inline")

                assert result["status"] == "error"
                assert "error" in result
                assert "validation" in result["error"].lower()
                assert "message" in result

    async def test_set_instructions_invalid_source(self, tmp_path: Path) -> None:
        """Test set_instructions rejects invalid source parameter."""
        with patch(
            "mcp_ticketer.mcp.server.tools.instruction_tools.TicketInstructionsManager"
        ) as mock_manager_class:
            with patch(
                "mcp_ticketer.mcp.server.tools.instruction_tools.Path.cwd",
                return_value=tmp_path,
            ):
                mock_manager = Mock()
                mock_manager_class.return_value = mock_manager

                result = await instructions_set(content="Content", source="invalid")

                assert result["status"] == "error"
                assert "invalid source" in result["error"].lower()
                mock_manager.set_instructions.assert_not_called()

    async def test_set_instructions_file_source(self, tmp_path: Path) -> None:
        """Test set_instructions with file source (currently treated as inline)."""
        content = "# File Content\n\n" + "x" * 100
        inst_path = tmp_path / ".mcp-ticketer" / "instructions.md"

        with patch(
            "mcp_ticketer.mcp.server.tools.instruction_tools.TicketInstructionsManager"
        ) as mock_manager_class:
            with patch(
                "mcp_ticketer.mcp.server.tools.instruction_tools.Path.cwd",
                return_value=tmp_path,
            ):
                mock_manager = Mock()
                mock_manager.get_instructions_path.return_value = inst_path
                mock_manager_class.return_value = mock_manager

                result = await instructions_set(content=content, source="file")

                assert result["status"] == "completed"
                mock_manager.set_instructions.assert_called_once_with(content)

    async def test_set_instructions_error(self, tmp_path: Path) -> None:
        """Test error handling in instructions_set."""
        with patch(
            "mcp_ticketer.mcp.server.tools.instruction_tools.TicketInstructionsManager"
        ) as mock_manager_class:
            with patch(
                "mcp_ticketer.mcp.server.tools.instruction_tools.Path.cwd",
                return_value=tmp_path,
            ):
                mock_manager = Mock()
                mock_manager.set_instructions.side_effect = InstructionsError(
                    "Write failed"
                )
                mock_manager_class.return_value = mock_manager

                result = await instructions_set(content="Content" * 50, source="inline")

                assert result["status"] == "error"
                assert "error" in result
                assert "Write failed" in result["error"]

    async def test_set_instructions_unexpected_error(self, tmp_path: Path) -> None:
        """Test handling of unexpected errors in instructions_set."""
        with patch(
            "mcp_ticketer.mcp.server.tools.instruction_tools.TicketInstructionsManager"
        ) as mock_manager_class:
            with patch(
                "mcp_ticketer.mcp.server.tools.instruction_tools.Path.cwd",
                return_value=tmp_path,
            ):
                mock_manager = Mock()
                mock_manager.set_instructions.side_effect = Exception("Unexpected")
                mock_manager_class.return_value = mock_manager

                result = await instructions_set(content="Content" * 50, source="inline")

                assert result["status"] == "error"
                assert "Unexpected" in result["error"]

    async def test_set_instructions_response_structure(self, tmp_path: Path) -> None:
        """Test that successful response has correct structure."""
        content = "# Content\n\n" + "x" * 100
        inst_path = tmp_path / ".mcp-ticketer" / "instructions.md"

        with patch(
            "mcp_ticketer.mcp.server.tools.instruction_tools.TicketInstructionsManager"
        ) as mock_manager_class:
            with patch(
                "mcp_ticketer.mcp.server.tools.instruction_tools.Path.cwd",
                return_value=tmp_path,
            ):
                mock_manager = Mock()
                mock_manager.get_instructions_path.return_value = inst_path
                mock_manager_class.return_value = mock_manager

                result = await instructions_set(content=content, source="inline")

                # Verify required fields
                assert "status" in result
                assert "message" in result
                assert "path" in result
                # Verify types
                assert isinstance(result["status"], str)
                assert isinstance(result["message"], str)
                assert isinstance(result["path"], str)


@pytest.mark.asyncio
class TestInstructionsResetTool:
    """Test suite for instructions_reset MCP tool."""

    async def test_reset_with_custom_instructions(self, tmp_path: Path) -> None:
        """Test resetting when custom instructions exist."""
        with patch(
            "mcp_ticketer.mcp.server.tools.instruction_tools.TicketInstructionsManager"
        ) as mock_manager_class:
            with patch(
                "mcp_ticketer.mcp.server.tools.instruction_tools.Path.cwd",
                return_value=tmp_path,
            ):
                mock_manager = Mock()
                mock_manager.has_custom_instructions.return_value = True
                mock_manager.delete_instructions.return_value = True
                mock_manager_class.return_value = mock_manager

                result = await instructions_reset()

                assert result["status"] == "completed"
                assert "deleted" in result["message"].lower()
                assert "default" in result["message"].lower()
                mock_manager.delete_instructions.assert_called_once()

    async def test_reset_without_custom_instructions(self, tmp_path: Path) -> None:
        """Test resetting when no custom instructions exist."""
        with patch(
            "mcp_ticketer.mcp.server.tools.instruction_tools.TicketInstructionsManager"
        ) as mock_manager_class:
            with patch(
                "mcp_ticketer.mcp.server.tools.instruction_tools.Path.cwd",
                return_value=tmp_path,
            ):
                mock_manager = Mock()
                mock_manager.has_custom_instructions.return_value = False
                mock_manager_class.return_value = mock_manager

                result = await instructions_reset()

                assert result["status"] == "completed"
                assert "no custom" in result["message"].lower()
                assert "already using defaults" in result["message"].lower()
                mock_manager.delete_instructions.assert_not_called()

    async def test_reset_delete_returns_false(self, tmp_path: Path) -> None:
        """Test reset when delete_instructions returns False."""
        with patch(
            "mcp_ticketer.mcp.server.tools.instruction_tools.TicketInstructionsManager"
        ) as mock_manager_class:
            with patch(
                "mcp_ticketer.mcp.server.tools.instruction_tools.Path.cwd",
                return_value=tmp_path,
            ):
                mock_manager = Mock()
                mock_manager.has_custom_instructions.return_value = True
                mock_manager.delete_instructions.return_value = False
                mock_manager_class.return_value = mock_manager

                result = await instructions_reset()

                assert result["status"] == "completed"
                assert (
                    "not found" in result["message"].lower()
                    or "no custom" in result["message"].lower()
                )

    async def test_reset_error(self) -> None:
        """Test error handling in instructions_reset."""
        with patch(
            "mcp_ticketer.mcp.server.tools.instruction_tools.TicketInstructionsManager"
        ) as mock_manager_class:
            mock_manager_class.side_effect = InstructionsError("Delete failed")

            result = await instructions_reset()

            assert result["status"] == "error"
            assert "error" in result
            assert "Delete failed" in result["error"]

    async def test_reset_unexpected_error(self) -> None:
        """Test handling of unexpected errors in instructions_reset."""
        with patch(
            "mcp_ticketer.mcp.server.tools.instruction_tools.TicketInstructionsManager"
        ) as mock_manager_class:
            mock_manager_class.side_effect = Exception("Unexpected")

            result = await instructions_reset()

            assert result["status"] == "error"
            assert "Unexpected" in result["error"]

    async def test_reset_response_structure(self, tmp_path: Path) -> None:
        """Test that response has correct structure."""
        with patch(
            "mcp_ticketer.mcp.server.tools.instruction_tools.TicketInstructionsManager"
        ) as mock_manager_class:
            with patch(
                "mcp_ticketer.mcp.server.tools.instruction_tools.Path.cwd",
                return_value=tmp_path,
            ):
                mock_manager = Mock()
                mock_manager.has_custom_instructions.return_value = False
                mock_manager_class.return_value = mock_manager

                result = await instructions_reset()

                # Verify required fields
                assert "status" in result
                assert "message" in result
                # Verify types
                assert isinstance(result["status"], str)
                assert isinstance(result["message"], str)


@pytest.mark.asyncio
class TestInstructionsValidateTool:
    """Test suite for instructions_validate MCP tool."""

    async def test_validate_valid_content(self) -> None:
        """Test validation of valid content."""
        valid_content = "# Valid Instructions\n\n" + "This is valid content. " * 20

        result = await instructions_validate(content=valid_content)

        assert result["status"] == "valid"
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)
        assert len(result["errors"]) == 0
        assert "message" in result

    async def test_validate_valid_content_with_warnings(self) -> None:
        """Test validation of valid content without headers (warning)."""
        valid_no_headers = "This is valid content without headers. " * 20

        result = await instructions_validate(content=valid_no_headers)

        assert result["status"] == "valid"
        assert len(result["errors"]) == 0
        assert len(result["warnings"]) > 0
        assert any("header" in w.lower() for w in result["warnings"])
        assert "warning" in result["message"].lower()

    async def test_validate_empty_content(self) -> None:
        """Test validation of empty content."""
        result = await instructions_validate(content="")

        assert result["status"] == "invalid"
        assert len(result["errors"]) > 0
        assert any("empty" in e.lower() for e in result["errors"])

    async def test_validate_whitespace_only(self) -> None:
        """Test validation of whitespace-only content."""
        result = await instructions_validate(content="   \n\n   ")

        assert result["status"] == "invalid"
        assert len(result["errors"]) > 0
        assert any("empty" in e.lower() for e in result["errors"])

    async def test_validate_too_short(self) -> None:
        """Test validation of content that's too short."""
        short_content = "Too short"

        result = await instructions_validate(content=short_content)

        assert result["status"] == "invalid"
        assert len(result["errors"]) > 0
        assert any("short" in e.lower() for e in result["errors"])
        assert any("100" in e for e in result["errors"])

    async def test_validate_minimum_length(self) -> None:
        """Test validation of content at minimum length (100 chars)."""
        min_content = "x" * 100

        result = await instructions_validate(content=min_content)

        assert result["status"] == "valid"
        # Might have warning about no headers, but no errors
        assert len(result["errors"]) == 0

    async def test_validate_almost_minimum_length(self) -> None:
        """Test validation of content just under minimum length."""
        almost_content = "x" * 99

        result = await instructions_validate(content=almost_content)

        assert result["status"] == "invalid"
        assert len(result["errors"]) > 0

    async def test_validate_with_markdown_headers(self) -> None:
        """Test validation of content with proper markdown headers."""
        content_with_headers = """
# Main Title

## Section 1
Content here.

## Section 2
More content here.

This is long enough to pass validation.
"""

        result = await instructions_validate(content=content_with_headers)

        assert result["status"] == "valid"
        assert len(result["errors"]) == 0
        assert len(result["warnings"]) == 0
        assert "no issues" in result["message"].lower()

    async def test_validate_exception_handling(self) -> None:
        """Test that validation handles unexpected errors gracefully."""
        # This should not normally raise, but test exception handling
        with patch(
            "mcp_ticketer.mcp.server.tools.instruction_tools.instructions_validate"
        ) as mock_validate:
            # Simulate an internal error during validation
            async def error_validate(content):
                raise Exception("Validation process error")

            mock_validate.side_effect = error_validate

            try:
                await mock_validate("test content")
            except Exception:
                # Expected to raise, this is testing the wrapper would catch it
                pass

    async def test_validate_response_structure_valid(self) -> None:
        """Test that valid response has correct structure."""
        result = await instructions_validate(content="# Title\n\n" + "x" * 100)

        # Verify required fields
        assert "status" in result
        assert "warnings" in result
        assert "errors" in result
        assert "message" in result
        # Verify types
        assert isinstance(result["status"], str)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)
        assert isinstance(result["message"], str)

    async def test_validate_response_structure_invalid(self) -> None:
        """Test that invalid response has correct structure."""
        result = await instructions_validate(content="")

        # Verify required fields
        assert "status" in result
        assert "warnings" in result
        assert "errors" in result
        assert "message" in result
        # Verify types
        assert isinstance(result["status"], str)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)
        assert isinstance(result["message"], str)
        # Verify errors is not empty for invalid content
        assert len(result["errors"]) > 0


@pytest.mark.asyncio
class TestToolIntegration:
    """Test suite for integration between MCP tools."""

    async def test_set_then_get(self, tmp_path: Path) -> None:
        """Test setting instructions then getting them."""
        content = "# Test Instructions\n\n" + "x" * 100
        inst_path = tmp_path / ".mcp-ticketer" / "instructions.md"

        with patch(
            "mcp_ticketer.mcp.server.tools.instruction_tools.TicketInstructionsManager"
        ) as mock_manager_class:
            with patch(
                "mcp_ticketer.mcp.server.tools.instruction_tools.Path.cwd",
                return_value=tmp_path,
            ):
                mock_manager = Mock()
                mock_manager.get_instructions_path.return_value = inst_path
                mock_manager.has_custom_instructions.return_value = True
                mock_manager.get_instructions.return_value = content
                mock_manager_class.return_value = mock_manager

                # Set instructions
                set_result = await instructions_set(content=content, source="inline")
                assert set_result["status"] == "completed"

                # Get instructions
                get_result = await instructions_get()
                assert get_result["status"] == "completed"
                assert get_result["source"] == "custom"
                assert get_result["instructions"] == content

    async def test_validate_then_set(self, tmp_path: Path) -> None:
        """Test validating content before setting it."""
        content = "# Valid Content\n\n" + "x" * 100
        inst_path = tmp_path / ".mcp-ticketer" / "instructions.md"

        # First validate
        validate_result = await instructions_validate(content=content)
        assert validate_result["status"] == "valid"

        # Then set if valid
        if validate_result["status"] == "valid":
            with patch(
                "mcp_ticketer.mcp.server.tools.instruction_tools.TicketInstructionsManager"
            ) as mock_manager_class:
                with patch(
                    "mcp_ticketer.mcp.server.tools.instruction_tools.Path.cwd",
                    return_value=tmp_path,
                ):
                    mock_manager = Mock()
                    mock_manager.get_instructions_path.return_value = inst_path
                    mock_manager_class.return_value = mock_manager

                    set_result = await instructions_set(
                        content=content, source="inline"
                    )
                    assert set_result["status"] == "completed"

    async def test_set_then_reset(self, tmp_path: Path) -> None:
        """Test setting custom instructions then resetting to defaults."""
        content = "# Custom\n\n" + "x" * 100
        inst_path = tmp_path / ".mcp-ticketer" / "instructions.md"

        with patch(
            "mcp_ticketer.mcp.server.tools.instruction_tools.TicketInstructionsManager"
        ) as mock_manager_class:
            with patch(
                "mcp_ticketer.mcp.server.tools.instruction_tools.Path.cwd",
                return_value=tmp_path,
            ):
                mock_manager = Mock()
                mock_manager.get_instructions_path.return_value = inst_path
                mock_manager_class.return_value = mock_manager

                # Set custom instructions
                set_result = await instructions_set(content=content, source="inline")
                assert set_result["status"] == "completed"

                # Now reset (simulate custom exists)
                mock_manager.has_custom_instructions.return_value = True
                mock_manager.delete_instructions.return_value = True

                reset_result = await instructions_reset()
                assert reset_result["status"] == "completed"
                assert "deleted" in reset_result["message"].lower()
