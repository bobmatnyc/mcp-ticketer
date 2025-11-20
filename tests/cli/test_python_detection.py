"""Tests for Python executable detection logic."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from mcp_ticketer.cli.python_detection import (
    get_mcp_server_command,
    get_mcp_ticketer_python,
    validate_python_executable,
)


class TestGetMcpTicketerPython:
    """Test cases for get_mcp_ticketer_python function."""

    def test_project_venv_takes_priority(self, tmp_path: Path) -> None:
        """Test that project .venv/bin/python is detected and used first."""
        # Create project venv structure
        project_venv_python = tmp_path / ".venv" / "bin" / "python"
        project_venv_python.parent.mkdir(parents=True)
        project_venv_python.touch()

        # Call with project path
        result = get_mcp_ticketer_python(project_path=tmp_path)

        # Should return project venv python
        assert result == str(project_venv_python)
        assert ".venv/bin/python" in result

    def test_project_venv_not_exists_falls_back(self, tmp_path: Path) -> None:
        """Test fallback when project venv doesn't exist."""
        # Project path provided but no .venv
        result = get_mcp_ticketer_python(project_path=tmp_path)

        # Should fall back to current Python or pipx
        # The result could be a symlink while sys.executable is the target
        # So we check if they resolve to the same directory
        result_path = Path(result)
        sys_exec_path = Path(sys.executable)

        assert (
            result == sys.executable
            or result_path.parent == sys_exec_path.parent  # Same bin directory
            or "/pipx/venvs/" in result
        )

    def test_no_project_path_uses_pipx_venv(self) -> None:
        """Test that pipx venv is used when no project path provided."""
        with patch(
            "sys.executable", "/Users/test/.local/pipx/venvs/mcp-ticketer/bin/python"
        ):
            result = get_mcp_ticketer_python()
            assert "/pipx/venvs/" in result

    def test_no_project_path_no_pipx_uses_fallback(self) -> None:
        """Test fallback to current Python when no project path and not in pipx."""
        with patch("sys.executable", "/usr/bin/python3"):
            with patch("shutil.which", return_value=None):
                result = get_mcp_ticketer_python()
                assert result == "/usr/bin/python3"

    def test_shebang_detection_when_mcp_ticketer_binary_exists(self) -> None:
        """Test detection from mcp-ticketer binary shebang."""
        mock_shebang = "#!/usr/local/bin/python3\n"

        with patch("sys.executable", "/usr/bin/python3"):
            with patch("shutil.which", return_value="/usr/local/bin/mcp-ticketer"):
                with patch(
                    "builtins.open",
                    MagicMock(
                        return_value=MagicMock(
                            __enter__=MagicMock(
                                return_value=MagicMock(
                                    readline=MagicMock(return_value=mock_shebang)
                                )
                            ),
                            __exit__=MagicMock(),
                        )
                    ),
                ):
                    with patch("os.path.exists", return_value=True):
                        result = get_mcp_ticketer_python()
                        assert result == "/usr/local/bin/python3"


class TestGetMcpServerCommand:
    """Test cases for get_mcp_server_command function."""

    def test_command_with_project_path_uses_project_venv(self, tmp_path: Path) -> None:
        """Test that command uses project venv when available."""
        # Create project venv
        project_venv_python = tmp_path / ".venv" / "bin" / "python"
        project_venv_python.parent.mkdir(parents=True)
        project_venv_python.touch()

        # Get command
        python_path, args = get_mcp_server_command(project_path=str(tmp_path))

        # Verify project venv is used
        assert python_path == str(project_venv_python)
        assert args == ["-m", "mcp_ticketer.mcp.server", str(tmp_path)]

    def test_command_without_project_path_uses_fallback(self) -> None:
        """Test command without project path uses fallback Python."""
        python_path, args = get_mcp_server_command(project_path=None)

        # Should return current Python or pipx
        assert python_path
        assert args == ["-m", "mcp_ticketer.mcp.server"]

    def test_command_with_project_path_no_venv_falls_back(self, tmp_path: Path) -> None:
        """Test command with project path but no venv falls back correctly."""
        # No .venv in project
        python_path, args = get_mcp_server_command(project_path=str(tmp_path))

        # Should fall back but still include project path in args
        assert python_path
        assert args == ["-m", "mcp_ticketer.mcp.server", str(tmp_path)]


class TestValidatePythonExecutable:
    """Test cases for validate_python_executable function."""

    def test_valid_python_with_mcp_ticketer(self) -> None:
        """Test validation with valid Python that has mcp_ticketer."""
        # Current Python should have mcp_ticketer installed
        result = validate_python_executable(sys.executable)
        assert result is True

    def test_invalid_python_path(self) -> None:
        """Test validation with non-existent Python path."""
        result = validate_python_executable("/nonexistent/python")
        assert result is False

    @patch("subprocess.run")
    def test_python_without_mcp_ticketer(self, mock_run: MagicMock) -> None:
        """Test validation with Python that can't import mcp_ticketer."""
        mock_run.return_value = MagicMock(returncode=1)
        result = validate_python_executable("/usr/bin/python3")
        assert result is False

    @patch("subprocess.run")
    def test_timeout_handling(self, mock_run: MagicMock) -> None:
        """Test validation handles subprocess timeout."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("python", 5)
        result = validate_python_executable("/usr/bin/python3")
        assert result is False
