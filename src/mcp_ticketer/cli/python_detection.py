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


def get_mcp_ticketer_python(project_path: Path | None = None) -> str:
    """Get the correct Python executable for mcp-ticketer MCP server.

    This function follows the mcp-vector-search pattern of using project-specific
    venv Python for proper project isolation and dependency management.

    Detection priority:
    1. Project-local venv (.venv/bin/python) if project_path provided
    2. Current Python executable if in pipx venv
    3. Python from mcp-ticketer binary shebang
    4. Current Python executable (fallback)

    Args:
        project_path: Optional project directory path to check for local venv

    Returns:
        Path to Python executable

    Examples:
        >>> # With project venv
        >>> python_path = get_mcp_ticketer_python(Path("/home/user/my-project"))
        >>> # Returns: "/home/user/my-project/.venv/bin/python"

        >>> # Without project path (fallback to pipx)
        >>> python_path = get_mcp_ticketer_python()
        >>> # Returns: "/Users/user/.local/pipx/venvs/mcp-ticketer/bin/python"

    """
    # Priority 1: Check for project-local venv
    if project_path:
        project_venv_python = project_path / ".venv" / "bin" / "python"
        if project_venv_python.exists():
            return str(project_venv_python)

    current_executable = sys.executable

    # Priority 2: Check if we're in a pipx venv
    if "/pipx/venvs/" in current_executable:
        return current_executable

    # Priority 3: Check mcp-ticketer binary shebang
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

    # Priority 4: Fallback to current Python
    return current_executable


def get_mcp_server_command(project_path: str | None = None) -> tuple[str, list[str]]:
    """Get the complete command to run the MCP server.

    Args:
        project_path: Optional project path to pass as argument and check for venv

    Returns:
        Tuple of (python_executable, args_list)
        Example: ("/path/to/python", ["-m", "mcp_ticketer.mcp.server", "/project/path"])

    Examples:
        >>> python, args = get_mcp_server_command("/home/user/project")
        >>> # python: "/home/user/project/.venv/bin/python" (if .venv exists)
        >>> # args: ["-m", "mcp_ticketer.mcp.server", "/home/user/project"]

    """
    # Convert project_path to Path object for venv detection
    project_path_obj = Path(project_path) if project_path else None
    python_path = get_mcp_ticketer_python(project_path=project_path_obj)
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
