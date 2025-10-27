"""Reliable Python executable detection for mcp-ticketer.

This module provides reliable detection of the Python executable for mcp-ticketer
across different installation methods (pipx, pip, uv, direct venv).

The module follows the proven pattern from mcp-vector-search:
- Detect venv Python path reliably
- Use `python -m mcp_ticketer.mcp.server` instead of binary paths
- Support multiple installation methods transparently
"""

import os
import shutil
import sys
from pathlib import Path


def get_mcp_ticketer_python() -> str:
    """Get the correct Python executable for mcp-ticketer.

    This function reliably detects the Python executable across different
    installation methods (pipx, pip, uv, direct venv).

    Detection priority:
    1. Current Python executable if in pipx venv
    2. Python from mcp-ticketer binary shebang
    3. Current Python executable (fallback)

    Returns:
        Path to Python executable

    Examples:
        >>> python_path = get_mcp_ticketer_python()
        >>> # Returns: "/Users/user/.local/pipx/venvs/mcp-ticketer/bin/python"
    """
    current_executable = sys.executable

    # Priority 1: Check if we're in a pipx venv
    if "/pipx/venvs/" in current_executable:
        return current_executable

    # Priority 2: Check mcp-ticketer binary shebang
    mcp_ticketer_path = shutil.which("mcp-ticketer")
    if mcp_ticketer_path:
        try:
            with open(mcp_ticketer_path) as f:
                first_line = f.readline().strip()
                if first_line.startswith("#!") and "python" in first_line:
                    python_path = first_line[2:].strip()
                    if os.path.exists(python_path):
                        return python_path
        except OSError:
            pass

    # Priority 3: Fallback to current Python
    return current_executable


def get_mcp_server_command(project_path: str | None = None) -> tuple[str, list[str]]:
    """Get the complete command to run the MCP server.

    Args:
        project_path: Optional project path to pass as argument

    Returns:
        Tuple of (python_executable, args_list)
        Example: ("/path/to/python", ["-m", "mcp_ticketer.mcp.server", "/project/path"])

    Examples:
        >>> python, args = get_mcp_server_command("/home/user/project")
        >>> # python: "/Users/user/.local/pipx/venvs/mcp-ticketer/bin/python"
        >>> # args: ["-m", "mcp_ticketer.mcp.server", "/home/user/project"]
    """
    python_path = get_mcp_ticketer_python()
    args = ["-m", "mcp_ticketer.mcp.server"]

    if project_path:
        args.append(str(project_path))

    return python_path, args


def validate_python_executable(python_path: str) -> bool:
    """Validate that a Python executable can import mcp_ticketer.

    Args:
        python_path: Path to Python executable to validate

    Returns:
        True if Python can import mcp_ticketer, False otherwise

    Examples:
        >>> is_valid = validate_python_executable("/usr/bin/python3")
        >>> # Returns: False (system Python doesn't have mcp_ticketer)
    """
    try:
        import subprocess

        result = subprocess.run(
            [python_path, "-c", "import mcp_ticketer.mcp.server"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False
