"""Test that instruction tools are not available in MCP server.

Phase 2 Sprint 2.3: Verify instruction tools removed from MCP but available in CLI.

Related ticket: 1M-484
"""

import pytest


@pytest.mark.asyncio
async def test_instructions_get_not_in_mcp():
    """Verify instructions_get removed from MCP server (Phase 2 Sprint 2.3)."""
    from mcp_ticketer.mcp.server import server_sdk

    # Get all registered MCP tools
    tools = await server_sdk.mcp.list_tools()
    tool_names = [tool.name for tool in tools]

    # Verify instructions_get is NOT present
    assert (
        "instructions_get" not in tool_names
    ), "instructions_get should be removed from MCP (CLI-only as of v1.5.0)"


@pytest.mark.asyncio
async def test_instructions_set_not_in_mcp():
    """Verify instructions_set removed from MCP server (Phase 2 Sprint 2.3)."""
    from mcp_ticketer.mcp.server import server_sdk

    # Get all registered MCP tools
    tools = await server_sdk.mcp.list_tools()
    tool_names = [tool.name for tool in tools]

    # Verify instructions_set is NOT present
    assert (
        "instructions_set" not in tool_names
    ), "instructions_set should be removed from MCP (CLI-only as of v1.5.0)"


@pytest.mark.asyncio
async def test_instructions_reset_not_in_mcp():
    """Verify instructions_reset removed from MCP server (Phase 2 Sprint 2.3)."""
    from mcp_ticketer.mcp.server import server_sdk

    # Get all registered MCP tools
    tools = await server_sdk.mcp.list_tools()
    tool_names = [tool.name for tool in tools]

    # Verify instructions_reset is NOT present
    assert (
        "instructions_reset" not in tool_names
    ), "instructions_reset should be removed from MCP (CLI-only as of v1.5.0)"


@pytest.mark.asyncio
async def test_instructions_validate_not_in_mcp():
    """Verify instructions_validate removed from MCP server (Phase 2 Sprint 2.3)."""
    from mcp_ticketer.mcp.server import server_sdk

    # Get all registered MCP tools
    tools = await server_sdk.mcp.list_tools()
    tool_names = [tool.name for tool in tools]

    # Verify instructions_validate is NOT present
    assert (
        "instructions_validate" not in tool_names
    ), "instructions_validate should be removed from MCP (CLI-only as of v1.5.0)"


@pytest.mark.asyncio
async def test_instructions_tools_count():
    """Verify total count of removed instruction tools (4 tools)."""
    from mcp_ticketer.mcp.server import server_sdk

    # Get all registered MCP tools
    tools = await server_sdk.mcp.list_tools()
    tool_names = [tool.name for tool in tools]

    # List of removed instruction tools
    removed_tools = [
        "instructions_get",
        "instructions_set",
        "instructions_reset",
        "instructions_validate",
    ]

    # Verify none are present
    present_removed_tools = [tool for tool in removed_tools if tool in tool_names]

    assert len(present_removed_tools) == 0, (
        f"Found {len(present_removed_tools)} removed tools still present: "
        f"{present_removed_tools}"
    )


@pytest.mark.integration
def test_cli_instructions_module_exists():
    """Verify CLI instructions module exists."""
    from mcp_ticketer.cli import instruction_commands

    assert instruction_commands is not None
    assert hasattr(instruction_commands, "app")


@pytest.mark.integration
def test_cli_instructions_show_exists():
    """Verify CLI has instructions show command."""
    from mcp_ticketer.cli.instruction_commands import show

    assert callable(show)


@pytest.mark.integration
def test_cli_instructions_add_exists():
    """Verify CLI has instructions add command."""
    from mcp_ticketer.cli.instruction_commands import add

    assert callable(add)


@pytest.mark.integration
def test_cli_instructions_update_exists():
    """Verify CLI has instructions update command."""
    from mcp_ticketer.cli.instruction_commands import update

    assert callable(update)


@pytest.mark.integration
def test_cli_instructions_delete_exists():
    """Verify CLI has instructions delete command."""
    from mcp_ticketer.cli.instruction_commands import delete

    assert callable(delete)


@pytest.mark.integration
def test_cli_instructions_path_exists():
    """Verify CLI has instructions path command."""
    from mcp_ticketer.cli.instruction_commands import path

    assert callable(path)


@pytest.mark.integration
def test_cli_instructions_edit_exists():
    """Verify CLI has instructions edit command."""
    from mcp_ticketer.cli.instruction_commands import edit

    assert callable(edit)


def test_migration_guide_exists():
    """Verify migration documentation exists for instructions removal."""
    from pathlib import Path

    migration_guide = (
        Path(__file__).parent.parent.parent
        / "docs"
        / "migrations"
        / "INSTRUCTIONS_TOOLS_REMOVAL.md"
    )

    assert migration_guide.exists(), (
        "Migration guide should exist at "
        "docs/migrations/INSTRUCTIONS_TOOLS_REMOVAL.md"
    )

    # Verify guide has content
    content = migration_guide.read_text()
    content_lower = content.lower()

    # Check for key tool names
    assert "instructions_get" in content
    assert "instructions_set" in content
    assert "instructions_reset" in content
    assert "instructions_validate" in content

    # Check for filesystem MCP references
    assert "filesystem" in content_lower and "mcp" in content_lower

    # Check for CLI alternatives
    assert "aitrackdown instructions" in content or "cli" in content_lower


def test_token_savings_documentation():
    """Verify token savings are documented for instructions removal."""
    from pathlib import Path

    migration_guide = (
        Path(__file__).parent.parent.parent
        / "docs"
        / "migrations"
        / "INSTRUCTIONS_TOOLS_REMOVAL.md"
    )

    content = migration_guide.read_text()

    # Verify token costs are mentioned
    assert "750 tokens" in content  # instructions_get
    assert "800 tokens" in content  # instructions_set
    assert "740 tokens" in content  # instructions_reset
    assert "710 tokens" in content  # instructions_validate

    # Verify total savings mentioned (flexible format)
    assert "3,000 tokens" in content or "3000 tokens" in content


def test_all_cli_commands_documented():
    """Verify all CLI commands are documented in migration guide."""
    from pathlib import Path

    migration_guide = (
        Path(__file__).parent.parent.parent
        / "docs"
        / "migrations"
        / "INSTRUCTIONS_TOOLS_REMOVAL.md"
    )

    content = migration_guide.read_text()

    # Check for all CLI commands
    cli_commands = [
        "instructions show",
        "instructions add",
        "instructions update",
        "instructions delete",
        "instructions path",
        "instructions edit",
    ]

    for cmd in cli_commands:
        assert cmd in content, f"CLI command '{cmd}' should be documented"


@pytest.mark.integration
def test_instructions_tools_still_importable():
    """Verify instruction tools still exist in codebase (not deleted)."""
    # Import the tool module directly (should not raise)
    from mcp_ticketer.mcp.server.tools import instruction_tools

    # Verify tools are defined in module
    assert hasattr(instruction_tools, "instructions_get")
    assert hasattr(instruction_tools, "instructions_set")
    assert hasattr(instruction_tools, "instructions_reset")
    assert hasattr(instruction_tools, "instructions_validate")

    # These tools exist in code but are not registered with MCP


def test_init_file_documents_removal():
    """Verify __init__.py documents instructions removal."""
    from pathlib import Path

    init_file = (
        Path(__file__).parent.parent.parent
        / "src"
        / "mcp_ticketer"
        / "mcp"
        / "server"
        / "tools"
        / "__init__.py"
    )

    content = init_file.read_text()

    # Check for removal documentation
    assert "instruction_tools" in content.lower()
    assert "removed" in content.lower() or "cli-only" in content.lower()
