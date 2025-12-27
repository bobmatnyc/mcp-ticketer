"""Test that removed tools are not available in MCP server.

Phase 2 Sprint 1.3: Verify PR tools removed from MCP.
Note: Attachment tools have been RE-ENABLED as of recent updates.

Related ticket: 1M-484
"""

import pytest


@pytest.mark.asyncio
async def test_attachment_tools_in_mcp():
    """Verify attachment tools are present in MCP server (re-enabled)."""
    from mcp_ticketer.mcp.server import server_sdk

    # Get all registered MCP tools
    tools = await server_sdk.mcp.list_tools()
    tool_names = [tool.name for tool in tools]

    # Verify attachment tool is present (consolidated)
    assert (
        "attachment" in tool_names
    ), "attachment should be present in MCP (consolidated from ticket_attach and ticket_attachments)"


@pytest.mark.asyncio
async def test_pr_tools_not_in_mcp():
    """Verify PR tools removed from MCP server (Phase 2 Sprint 1.3)."""
    from mcp_ticketer.mcp.server import server_sdk

    # Get all registered MCP tools
    tools = await server_sdk.mcp.list_tools()
    tool_names = [tool.name for tool in tools]

    # Verify PR tools are NOT present
    assert (
        "ticket_create_pr" not in tool_names
    ), "ticket_create_pr should be removed from MCP (CLI-only as of v1.5.0)"
    assert (
        "ticket_link_pr" not in tool_names
    ), "ticket_link_pr should be removed from MCP (CLI-only as of v1.5.0)"


@pytest.mark.asyncio
async def test_removed_tools_count():
    """Verify only PR tools are removed (2 tools), attachments re-enabled."""
    from mcp_ticketer.mcp.server import server_sdk

    # Get all registered MCP tools
    tools = await server_sdk.mcp.list_tools()
    tool_names = [tool.name for tool in tools]

    # List of removed tools (PR tools only)
    removed_tools = [
        "ticket_create_pr",
        "ticket_link_pr",
    ]

    # List of consolidated tools (attachment tools)
    consolidated_tools = [
        "attachment",  # Consolidated from ticket_attach and ticket_attachments
    ]

    # Verify removed tools are NOT present
    present_removed_tools = [tool for tool in removed_tools if tool in tool_names]

    assert len(present_removed_tools) == 0, (
        f"Found {len(present_removed_tools)} removed tools still present: "
        f"{present_removed_tools}"
    )

    # Verify consolidated tools ARE present
    missing_consolidated_tools = [
        tool for tool in consolidated_tools if tool not in tool_names
    ]

    assert len(missing_consolidated_tools) == 0, (
        f"Found {len(missing_consolidated_tools)} consolidated tools missing: "
        f"{missing_consolidated_tools}"
    )


@pytest.mark.asyncio
async def test_alternative_tools_still_present():
    """Verify alternative tools for removed functionality still exist."""
    from mcp_ticketer.mcp.server import server_sdk

    # Get all registered MCP tools
    tools = await server_sdk.mcp.list_tools()
    tool_names = [tool.name for tool in tools]

    # Verify ticket_comment is still present (alternative for linking files/PRs)
    assert (
        "ticket_comment" in tool_names
    ), "ticket_comment should be present (used as alternative to removed tools)"


@pytest.mark.integration
def test_cli_tools_still_importable():
    """Verify attachment/PR tools still exist in codebase (CLI availability)."""
    # Import the tool modules directly (should not raise)
    from mcp_ticketer.mcp.server.tools import attachment_tools, pr_tools

    # Verify tools are defined in modules
    assert hasattr(attachment_tools, "attachment")
    assert hasattr(pr_tools, "ticket_create_pr")
    assert hasattr(pr_tools, "ticket_link_pr")

    # PR tools exist in code but are not registered with MCP
    # Attachment tool is registered with MCP (consolidated)


def test_migration_guide_exists():
    """Verify PR removal migration documentation exists in archive."""
    from pathlib import Path

    # Migration guide moved to archive since attachment tools were re-enabled
    migration_guide = (
        Path(__file__).parent.parent.parent
        / "docs"
        / "_archive"
        / "migrations"
        / "ATTACHMENT_PR_REMOVAL.md"
    )

    assert (
        migration_guide.exists()
    ), "Migration guide should exist at docs/_archive/migrations/ATTACHMENT_PR_REMOVAL.md"

    # Verify guide has content about PR removal
    content = migration_guide.read_text()
    content_lower = content.lower()
    assert "ticket_create_pr" in content
    assert "github" in content_lower and "mcp" in content_lower


def test_token_savings_documentation():
    """Verify PR tools token savings are documented in archive."""
    from pathlib import Path

    # Migration guide moved to archive since attachment tools were re-enabled
    migration_guide = (
        Path(__file__).parent.parent.parent
        / "docs"
        / "_archive"
        / "migrations"
        / "ATTACHMENT_PR_REMOVAL.md"
    )

    content = migration_guide.read_text()

    # Verify PR tool token costs are mentioned
    assert "828 tokens" in content  # ticket_create_pr
    assert "717 tokens" in content  # ticket_link_pr
