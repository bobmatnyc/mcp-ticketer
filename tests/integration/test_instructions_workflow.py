"""Integration tests for ticket instructions management workflow.

Tests the complete workflow of instructions management across all interfaces:
- Core API, CLI, and MCP tools working together
- End-to-end scenarios
- Cross-interface consistency
- Real file system operations
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from mcp_ticketer.cli.instruction_commands import app
from mcp_ticketer.core.instructions import TicketInstructionsManager, get_instructions
from mcp_ticketer.mcp.server.tools.instruction_tools import (
    instructions_get,
    instructions_reset,
    instructions_set,
    instructions_validate,
)

runner = CliRunner()


@pytest.mark.integration
class TestCompleteWorkflow:
    """Test complete workflow across all interfaces."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, tmp_path: Path) -> None:
        """Test complete lifecycle: add, modify, delete instructions."""
        # Start with no custom instructions
        manager = TicketInstructionsManager(tmp_path)
        assert not manager.has_custom_instructions()

        # Step 1: Add custom instructions via API
        custom_content_v1 = """
# Custom Instructions v1

These are our initial custom instructions.

## Guidelines
- Write clear titles
- Add detailed descriptions

This content is long enough to pass validation checks.
"""
        manager.set_instructions(custom_content_v1)
        assert manager.has_custom_instructions()

        # Verify via API
        retrieved = manager.get_instructions()
        assert retrieved == custom_content_v1

        # Step 2: Verify via MCP tool (simulate working in same directory)
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            get_result = await instructions_get()
            assert get_result["status"] == "completed"
            assert get_result["source"] == "custom"
            assert get_result["instructions"] == custom_content_v1

            # Step 3: Update instructions via MCP
            custom_content_v2 = """
# Custom Instructions v2

These are our updated custom instructions.

## Updated Guidelines
- Write clear titles
- Add detailed descriptions
- Include acceptance criteria

This content is long enough to pass validation checks and has been updated.
"""
            set_result = await instructions_set(
                content=custom_content_v2, source="inline"
            )
            assert set_result["status"] == "completed"

            # Step 4: Verify update via API
            retrieved_v2 = manager.get_instructions()
            assert retrieved_v2 == custom_content_v2
            assert retrieved_v2 != custom_content_v1

            # Step 5: Delete via API
            deleted = manager.delete_instructions()
            assert deleted is True
            assert not manager.has_custom_instructions()

            # Step 6: Verify deletion via MCP
            get_result_after_delete = await instructions_get()
            assert get_result_after_delete["status"] == "completed"
            assert get_result_after_delete["source"] == "default"

            # Step 7: Verify we're back to defaults
            default_instructions = manager.get_default_instructions()
            assert manager.get_instructions() == default_instructions

        finally:
            os.chdir(original_cwd)

    def test_cross_interface_consistency(self, tmp_path: Path) -> None:
        """Test that all interfaces see the same instructions."""
        custom_content = "# Consistent Instructions\n\n" + "x" * 100

        # Set via API
        manager = TicketInstructionsManager(tmp_path)
        manager.set_instructions(custom_content)

        # Read via convenience function
        conv_instructions = get_instructions(tmp_path)
        assert conv_instructions == custom_content

        # Read via another manager instance
        manager2 = TicketInstructionsManager(tmp_path)
        manager2_instructions = manager2.get_instructions()
        assert manager2_instructions == custom_content

        # All should be identical
        assert conv_instructions == manager2_instructions == custom_content

    @pytest.mark.asyncio
    async def test_validation_workflow(self, tmp_path: Path) -> None:
        """Test validating content before setting it."""
        import os

        original_cwd = os.getcwd()

        try:
            os.chdir(tmp_path)

            # Try to validate invalid content
            invalid_content = "Too short"
            validate_result = await instructions_validate(content=invalid_content)
            assert validate_result["status"] == "invalid"
            assert len(validate_result["errors"]) > 0

            # Try to set it anyway (should fail via API)
            from mcp_ticketer.core.instructions import InstructionsValidationError

            manager = TicketInstructionsManager(tmp_path)
            with pytest.raises(
                InstructionsValidationError
            ):  # Should raise validation error
                manager.set_instructions(invalid_content)

            # Validate valid content
            valid_content = "# Valid Instructions\n\n" + "x" * 100
            validate_result = await instructions_validate(content=valid_content)
            assert validate_result["status"] == "valid"
            assert len(validate_result["errors"]) == 0

            # Set valid content
            set_result = await instructions_set(content=valid_content, source="inline")
            assert set_result["status"] == "completed"

            # Verify it was set
            get_result = await instructions_get()
            assert get_result["instructions"] == valid_content

        finally:
            os.chdir(original_cwd)

    def test_file_persistence(self, tmp_path: Path) -> None:
        """Test that instructions persist across process restarts."""
        custom_content = "# Persistent Instructions\n\n" + "x" * 100

        # Create and set instructions
        manager1 = TicketInstructionsManager(tmp_path)
        manager1.set_instructions(custom_content)

        # Verify file was created
        expected_path = tmp_path / ".mcp-ticketer" / "instructions.md"
        assert expected_path.exists()
        assert expected_path.read_text() == custom_content

        # Simulate process restart by creating new manager instance
        manager2 = TicketInstructionsManager(tmp_path)
        retrieved = manager2.get_instructions()
        assert retrieved == custom_content

        # Delete and verify file is gone
        manager2.delete_instructions()
        assert not expected_path.exists()

        # New instance should return defaults
        manager3 = TicketInstructionsManager(tmp_path)
        assert not manager3.has_custom_instructions()
        assert manager3.get_instructions() == manager3.get_default_instructions()


@pytest.mark.integration
class TestMCPToolWorkflow:
    """Test MCP tool workflow scenarios."""

    @pytest.mark.asyncio
    async def test_mcp_set_get_reset_cycle(self, tmp_path: Path) -> None:
        """Test complete MCP tool cycle."""
        import os

        original_cwd = os.getcwd()

        try:
            os.chdir(tmp_path)

            # Start with defaults
            get_result = await instructions_get()
            assert get_result["source"] == "default"
            default_content = get_result["instructions"]

            # Set custom via MCP
            custom_content = "# MCP Custom\n\n" + "x" * 100
            set_result = await instructions_set(content=custom_content, source="inline")
            assert set_result["status"] == "completed"

            # Verify custom is active
            get_result = await instructions_get()
            assert get_result["source"] == "custom"
            assert get_result["instructions"] == custom_content

            # Reset to defaults
            reset_result = await instructions_reset()
            assert reset_result["status"] == "completed"

            # Verify back to defaults
            get_result = await instructions_get()
            assert get_result["source"] == "default"
            assert get_result["instructions"] == default_content

        finally:
            os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_mcp_validation_before_set(self, tmp_path: Path) -> None:
        """Test validating with MCP before setting."""
        import os

        original_cwd = os.getcwd()

        try:
            os.chdir(tmp_path)

            # Content with warnings but no errors
            content_with_warnings = "Valid content without headers. " * 20

            # Validate
            validate_result = await instructions_validate(content=content_with_warnings)
            assert validate_result["status"] == "valid"
            assert len(validate_result["errors"]) == 0
            assert len(validate_result["warnings"]) > 0  # No headers warning

            # Still allowed to set
            set_result = await instructions_set(
                content=content_with_warnings, source="inline"
            )
            assert set_result["status"] == "completed"

            # Content with errors
            invalid_content = "x"  # Too short

            # Validate
            validate_result = await instructions_validate(content=invalid_content)
            assert validate_result["status"] == "invalid"
            assert len(validate_result["errors"]) > 0

            # Attempting to set should fail at API level
            # (MCP tool will pass it through, but manager will reject)
            set_result = await instructions_set(
                content=invalid_content, source="inline"
            )
            assert set_result["status"] == "error"

        finally:
            os.chdir(original_cwd)


@pytest.mark.integration
class TestCLIWorkflow:
    """Test CLI workflow scenarios."""

    def test_cli_add_show_delete(self, tmp_path: Path) -> None:
        """Test CLI add, show, delete workflow."""
        import os

        original_cwd = os.getcwd()

        try:
            os.chdir(tmp_path)

            # Create source file
            source_file = tmp_path / "custom.md"
            custom_content = "# CLI Custom\n\n" + "x" * 100
            source_file.write_text(custom_content)

            # Add via CLI
            from unittest.mock import patch

            with patch(
                "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
            ) as mock_cls:
                from unittest.mock import Mock

                mock_manager = Mock()
                mock_manager.has_custom_instructions.return_value = False
                mock_manager.get_instructions_path.return_value = (
                    tmp_path / ".mcp-ticketer" / "instructions.md"
                )
                mock_cls.return_value = mock_manager

                with patch(
                    "mcp_ticketer.cli.instruction_commands.Path"
                ) as mock_path_cls:
                    mock_path = Mock()
                    mock_path.exists.return_value = True
                    mock_path.read_text.return_value = custom_content
                    mock_path_cls.return_value = mock_path

                    result = runner.invoke(app, ["add", str(source_file)])
                    assert result.exit_code == 0

            # Verify via API
            manager = TicketInstructionsManager(tmp_path)
            # The actual file wasn't created because we mocked it,
            # so we'll set it for real now
            manager.set_instructions(custom_content)

            # Show via CLI
            with patch(
                "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
            ) as mock_cls:
                mock_manager = Mock()
                mock_manager.has_custom_instructions.return_value = True
                mock_manager.get_instructions.return_value = custom_content
                mock_manager.get_instructions_path.return_value = (
                    tmp_path / ".mcp-ticketer" / "instructions.md"
                )
                mock_cls.return_value = mock_manager

                result = runner.invoke(app, ["show"])
                assert result.exit_code == 0

            # Delete via CLI
            with patch(
                "mcp_ticketer.cli.instruction_commands.TicketInstructionsManager"
            ) as mock_cls:
                mock_manager = Mock()
                mock_manager.has_custom_instructions.return_value = True
                mock_manager.get_instructions_path.return_value = (
                    tmp_path / ".mcp-ticketer" / "instructions.md"
                )
                mock_cls.return_value = mock_manager

                result = runner.invoke(app, ["delete", "--yes"])
                assert result.exit_code == 0

        finally:
            os.chdir(original_cwd)


@pytest.mark.integration
class TestErrorRecovery:
    """Test error recovery scenarios."""

    def test_recovery_from_corrupted_file(self, tmp_path: Path) -> None:
        """Test recovery when custom instructions file is corrupted."""
        # Create a valid instructions file
        manager = TicketInstructionsManager(tmp_path)
        manager.set_instructions("# Valid\n\n" + "x" * 100)

        # Corrupt the file (make it unreadable)
        inst_path = manager.get_instructions_path()
        inst_path.chmod(0o000)  # Remove all permissions

        try:
            # Try to read (should fail gracefully)
            try:
                manager.get_instructions()
                pytest.fail("Should have raised an error")
            except Exception:
                pass  # Expected to fail

            # Restore permissions
            inst_path.chmod(0o644)

            # Should be readable again
            instructions = manager.get_instructions()
            assert instructions  # Should succeed

        finally:
            # Cleanup: restore permissions
            try:
                inst_path.chmod(0o644)
            except Exception:
                pass

    def test_recovery_from_missing_directory(self, tmp_path: Path) -> None:
        """Test that manager can create directory if it's missing."""
        # Ensure .mcp-ticketer doesn't exist
        config_dir = tmp_path / ".mcp-ticketer"
        assert not config_dir.exists()

        # Create manager and set instructions
        manager = TicketInstructionsManager(tmp_path)
        manager.set_instructions("# New\n\n" + "x" * 100)

        # Directory should have been created
        assert config_dir.exists()
        assert config_dir.is_dir()

        # Instructions should be readable
        instructions = manager.get_instructions()
        assert "# New" in instructions

    @pytest.mark.asyncio
    async def test_concurrent_access(self, tmp_path: Path) -> None:
        """Test concurrent access from multiple interfaces."""
        import os

        original_cwd = os.getcwd()

        try:
            os.chdir(tmp_path)

            # Create initial instructions via API
            manager = TicketInstructionsManager(tmp_path)
            content_v1 = "# Version 1\n\n" + "x" * 100
            manager.set_instructions(content_v1)

            # Read via MCP
            get_result = await instructions_get()
            assert get_result["instructions"] == content_v1

            # Update via MCP
            content_v2 = "# Version 2\n\n" + "x" * 100
            await instructions_set(content=content_v2, source="inline")

            # Read via API (should see update)
            retrieved = manager.get_instructions()
            assert retrieved == content_v2

            # Create another manager instance
            manager2 = TicketInstructionsManager(tmp_path)
            retrieved2 = manager2.get_instructions()
            assert retrieved2 == content_v2

            # All should see the same content
            assert retrieved == retrieved2 == content_v2

        finally:
            os.chdir(original_cwd)


@pytest.mark.integration
class TestEdgeCases:
    """Test edge cases in integrated workflow."""

    def test_unicode_content_across_interfaces(self, tmp_path: Path) -> None:
        """Test unicode content works across all interfaces."""
        unicode_content = """
# 日本語のタイトル

Instructions with unicode: café, naïve, emoji 🎯

## Guidelines
- Use clear titles ✅
- Avoid confusion ❌

This content contains unicode and is long enough to pass validation.
"""
        # Set via API
        manager = TicketInstructionsManager(tmp_path)
        manager.set_instructions(unicode_content)

        # Read via API
        retrieved = manager.get_instructions()
        assert retrieved == unicode_content
        assert "日本語" in retrieved
        assert "🎯" in retrieved

        # Verify file encoding
        inst_path = manager.get_instructions_path()
        file_content = inst_path.read_text(encoding="utf-8")
        assert file_content == unicode_content

    def test_very_large_instructions(self, tmp_path: Path) -> None:
        """Test handling of very large instructions file."""
        # Create 50KB of content
        large_content = "# Large Instructions\n\n" + ("Content line. " * 5000)

        manager = TicketInstructionsManager(tmp_path)
        manager.set_instructions(large_content)

        # Should handle large content
        retrieved = manager.get_instructions()
        assert len(retrieved) > 50000
        assert retrieved == large_content

    def test_empty_directory_initialization(self, tmp_path: Path) -> None:
        """Test initialization in completely empty directory."""
        # Create a subdirectory
        project_dir = tmp_path / "empty_project"
        project_dir.mkdir()

        # Initialize manager
        manager = TicketInstructionsManager(project_dir)

        # Should start with defaults
        assert not manager.has_custom_instructions()
        defaults = manager.get_instructions()
        assert len(defaults) > 0

        # Should be able to set custom
        custom = "# Custom\n\n" + "x" * 100
        manager.set_instructions(custom)
        assert manager.has_custom_instructions()

        # Config directory should exist now
        assert (project_dir / ".mcp-ticketer").exists()
