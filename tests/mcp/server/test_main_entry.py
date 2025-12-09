"""Tests for MCP server __main__.py entry point.

Tests verify the fix for GitHub issue #50 where os.chdir() failures
should cause the server to exit with error code 1 instead of continuing
with a warning.
"""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest


@pytest.fixture
def mock_asyncio_run():
    """Mock asyncio.run to prevent actual server startup."""
    with patch("asyncio.run") as mock:
        yield mock


class TestMainEntryPoint:
    """Test suite for __main__.py entry point behavior."""

    def test_nonexistent_path_exits_with_error(self, mock_asyncio_run, capsys):
        """Test that non-existent project path causes exit with code 1.

        This is the core fix for GitHub issue #50.
        """
        from mcp_ticketer.mcp.server.__main__ import run_server

        nonexistent_path = "/nonexistent/test/path/that/does/not/exist"

        with patch.object(sys, "argv", ["script", nonexistent_path]):
            with pytest.raises(SystemExit) as exc_info:
                run_server()

            # Verify exit code is 1
            assert exc_info.value.code == 1

            # Verify error message was written to stderr
            captured = capsys.readouterr()
            assert "Error: Project path does not exist" in captured.err
            assert nonexistent_path in captured.err

            # Verify server was NOT started
            mock_asyncio_run.assert_not_called()

    def test_os_chdir_failure_exits_with_error(self, mock_asyncio_run, capsys):
        """Test that os.chdir() OSError causes exit with code 1.

        Tests the specific error handling for os.chdir() failures.
        """
        from mcp_ticketer.mcp.server.__main__ import run_server

        # Create a real path that exists
        with patch("pathlib.Path.exists", return_value=True):
            with patch("os.chdir", side_effect=OSError("Permission denied")):
                with patch.object(sys, "argv", ["script", "/some/path"]):
                    with pytest.raises(SystemExit) as exc_info:
                        run_server()

                    # Verify exit code is 1
                    assert exc_info.value.code == 1

                    # Verify error message includes os.chdir context
                    captured = capsys.readouterr()
                    assert (
                        "Error: Could not change to project directory" in captured.err
                    )
                    assert "Permission denied" in captured.err

                    # Verify server was NOT started
                    mock_asyncio_run.assert_not_called()

    def test_valid_path_continues_execution(self, mock_asyncio_run, capsys, tmp_path):
        """Test that valid project path allows server to start."""
        from mcp_ticketer.mcp.server.__main__ import run_server

        # Use a real temporary directory
        test_path = tmp_path / "test_project"
        test_path.mkdir()

        with patch.object(sys, "argv", ["script", str(test_path)]):
            # Mock successful execution
            mock_asyncio_run.return_value = None

            run_server()

            # Verify working directory message was written
            captured = capsys.readouterr()
            assert "[MCP Server] Working directory:" in captured.err
            assert str(test_path) in captured.err

            # Verify server was started
            mock_asyncio_run.assert_called_once()

    def test_no_path_argument_starts_server(self, mock_asyncio_run):
        """Test that server starts without project path argument."""
        from mcp_ticketer.mcp.server.__main__ import run_server

        with patch.object(sys, "argv", ["script"]):
            # Mock successful execution
            mock_asyncio_run.return_value = None

            run_server()

            # Verify server was started
            mock_asyncio_run.assert_called_once()

    def test_keyboard_interrupt_exits_gracefully(self, capsys):
        """Test that KeyboardInterrupt exits with code 0."""
        from mcp_ticketer.mcp.server.__main__ import run_server

        with patch("asyncio.run", side_effect=KeyboardInterrupt):
            with patch.object(sys, "argv", ["script"]):
                with pytest.raises(SystemExit) as exc_info:
                    run_server()

                # Verify exit code is 0 for user interruption
                assert exc_info.value.code == 0

                # Verify interrupt message was written
                captured = capsys.readouterr()
                assert "[MCP Server] Interrupted by user" in captured.err

    def test_server_exception_exits_with_error(self, capsys):
        """Test that server exceptions exit with code 1."""
        from mcp_ticketer.mcp.server.__main__ import run_server

        with patch("asyncio.run", side_effect=RuntimeError("Server startup failed")):
            with patch.object(sys, "argv", ["script"]):
                with pytest.raises(SystemExit) as exc_info:
                    run_server()

                # Verify exit code is 1 for errors
                assert exc_info.value.code == 1

                # Verify error message was written
                captured = capsys.readouterr()
                assert "[MCP Server] Fatal error:" in captured.err
                assert "Server startup failed" in captured.err

    def test_error_message_format(self, capsys):
        """Test that error messages are properly formatted."""
        from mcp_ticketer.mcp.server.__main__ import run_server

        test_path = "/test/bad/path"

        with patch.object(sys, "argv", ["script", test_path]):
            with pytest.raises(SystemExit):
                run_server()

            # Verify error message format
            captured = capsys.readouterr()
            message = captured.err

            # Should be a single line error message
            assert message.startswith("Error: ")
            assert message.endswith("\n")

    def test_path_validation_before_chdir(self, capsys):
        """Test that path existence is validated before attempting chdir."""
        from mcp_ticketer.mcp.server.__main__ import run_server

        with patch("pathlib.Path.exists", return_value=False) as mock_exists:
            with patch("os.chdir") as mock_chdir:
                with patch.object(sys, "argv", ["script", "/test/path"]):
                    with pytest.raises(SystemExit) as exc_info:
                        run_server()

                    # Verify path existence was checked
                    mock_exists.assert_called_once()

                    # Verify chdir was NOT attempted
                    mock_chdir.assert_not_called()

                    # Verify proper error
                    assert exc_info.value.code == 1


class TestIntegrationScenarios:
    """Integration tests for real-world scenarios."""

    def test_relative_path_conversion(self, mock_asyncio_run, tmp_path):
        """Test that relative paths work correctly."""
        from mcp_ticketer.mcp.server.__main__ import run_server

        # Create test directory
        test_dir = tmp_path / "project"
        test_dir.mkdir()

        # Use relative path
        with patch.object(sys, "argv", ["script", str(test_dir)]):
            mock_asyncio_run.return_value = None
            run_server()

            # Verify server started
            mock_asyncio_run.assert_called_once()

    def test_path_with_spaces(self, mock_asyncio_run, tmp_path):
        """Test that paths with spaces are handled correctly."""
        from mcp_ticketer.mcp.server.__main__ import run_server

        # Create directory with spaces
        test_dir = tmp_path / "test project with spaces"
        test_dir.mkdir()

        with patch.object(sys, "argv", ["script", str(test_dir)]):
            mock_asyncio_run.return_value = None
            run_server()

            # Verify server started
            mock_asyncio_run.assert_called_once()

    def test_symlink_path(self, mock_asyncio_run, tmp_path):
        """Test that symlink paths work correctly."""
        from mcp_ticketer.mcp.server.__main__ import run_server

        # Create real directory and symlink
        real_dir = tmp_path / "real_project"
        real_dir.mkdir()
        link_dir = tmp_path / "link_project"

        import os

        os.symlink(real_dir, link_dir)

        with patch.object(sys, "argv", ["script", str(link_dir)]):
            mock_asyncio_run.return_value = None
            run_server()

            # Verify server started
            mock_asyncio_run.assert_called_once()
