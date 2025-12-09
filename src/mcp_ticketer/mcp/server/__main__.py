"""Main entry point for MCP server module invocation.

This module enables running the MCP server via:
    python -m mcp_ticketer.mcp.server [project_path]

This is the preferred invocation method for MCP configurations as it:
- Works reliably across installation methods (pipx, pip, uv)
- Doesn't depend on binary path detection
- Follows the proven mcp-vector-search pattern
"""

import asyncio
import sys
from pathlib import Path

from .main import main


def run_server() -> None:
    """Run the MCP server with optional project path argument.

    Usage:
        python -m mcp_ticketer.mcp.server
        python -m mcp_ticketer.mcp.server /path/to/project

    Arguments:
        project_path (optional): Path to project directory for context

    """
    # Check for project path argument
    if len(sys.argv) > 1:
        project_path = Path(sys.argv[1])

        # Validate project path exists
        if not project_path.exists():
            sys.stderr.write(f"Error: Project path does not exist: {project_path}\n")
            sys.exit(1)

        # Change to project directory for context
        try:
            import os

            os.chdir(project_path)
            sys.stderr.write(f"[MCP Server] Working directory: {project_path}\n")
        except OSError as e:
            sys.stderr.write(f"Error: Could not change to project directory: {e}\n")
            sys.exit(1)

    # Run the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.stderr.write("\n[MCP Server] Interrupted by user\n")
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"[MCP Server] Fatal error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    run_server()
