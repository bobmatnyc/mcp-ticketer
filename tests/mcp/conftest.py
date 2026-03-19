"""MCP test fixtures.

Provides fixtures for MCP tool tests that need an adapter configured
in the MCP server.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def reset_adapter_state():
    """Reset adapter state and CWD before and after each test.

    This prevents adapter instances and working directory changes from leaking
    between tests. Without this:
    - Adapter instances pointing to deleted temp dirs cause subsequent test failures
    - Tests calling os.chdir() (e.g. test_main_entry.py) break tests that depend
      on the project root's .mcp-ticketer/config.json being found via Path.cwd()

    Resets:
    - AdapterRegistry._instances (aitrackdown)
    - server_sdk._adapters (aitrackdown)
    - server_sdk._adapter (unconditionally)
    - server_sdk._active_github_connection
    - Current working directory (restores to original)
    """
    import mcp_ticketer.mcp.server.server_sdk as sdk
    from mcp_ticketer.core.registry import AdapterRegistry

    # Save current working directory
    original_cwd = os.getcwd()

    # Clear before test
    AdapterRegistry._instances.pop("aitrackdown", None)
    sdk._adapters.pop("aitrackdown", None)
    sdk._adapter = None
    sdk._active_github_connection = None

    yield

    # Clear after test
    AdapterRegistry._instances.pop("aitrackdown", None)
    sdk._adapters.pop("aitrackdown", None)
    sdk._adapter = None
    sdk._active_github_connection = None

    # Restore working directory (in case test called os.chdir)
    try:
        os.chdir(original_cwd)
    except OSError:
        pass  # Original dir may have been deleted; stay in current location


@pytest.fixture
def aitrackdown_adapter(aitrackdown_temp_dir: Path):
    """Create AITrackdown adapter and configure it in the MCP server.

    This overrides the base conftest fixture to also configure the MCP
    server to use the same adapter instance, enabling integration tests
    between direct adapter calls and MCP tool calls.

    Args:
        aitrackdown_temp_dir: Temporary directory for AITrackdown

    Returns:
        AITrackdownAdapter instance (also configured in MCP server)
    """
    from mcp_ticketer.adapters.aitrackdown import AITrackdownAdapter
    from mcp_ticketer.mcp.server.server_sdk import configure_adapter

    config = {"base_path": str(aitrackdown_temp_dir)}
    configure_adapter("aitrackdown", config)
    return AITrackdownAdapter(config)
