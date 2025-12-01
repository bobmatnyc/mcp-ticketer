"""Test that removed tools are not available in MCP server.

Phase 2 Sprint 1.3: Verify attachment and PR tools removed from MCP.

Related ticket: 1M-484
"""

import pytest


@pytest.mark.asyncio
async def test_attachment_tools_not_in_mcp():
    """Verify attachment tools removed from MCP server (Phase 2 Sprint 1.3)."""
    from mcp_ticketer.mcp.server import server_sdk

    # Get all registered MCP tools
    tools = await server_sdk.mcp.list_tools()
    tool_names = [tool.name for tool in tools]

    # Verify attachment tools are NOT present
    assert "ticket_attach" not in tool_names, (
        "ticket_attach should be removed from MCP (CLI-only as of v1.5.0)"
    )
    assert "ticket_attachments" not in tool_names, (
        "ticket_attachments should be removed from MCP (CLI-only as of v1.5.0)"
    )


@pytest.mark.asyncio
async def test_pr_tools_not_in_mcp():
    """Verify PR tools removed from MCP server (Phase 2 Sprint 1.3)."""
    from mcp_ticketer.mcp.server import server_sdk

    # Get all registered MCP tools
    tools = await server_sdk.mcp.list_tools()
    tool_names = [tool.name for tool in tools]

    # Verify PR tools are NOT present
    assert "ticket_create_pr" not in tool_names, (
        "ticket_create_pr should be removed from MCP (CLI-only as of v1.5.0)"
    )
    assert "ticket_link_pr" not in tool_names, (
        "ticket_link_pr should be removed from MCP (CLI-only as of v1.5.0)"
    )


@pytest.mark.asyncio
async def test_removed_tools_count():
    """Verify total count of removed tools (4 tools)."""
    from mcp_ticketer.mcp.server import server_sdk

    # Get all registered MCP tools
    tools = await server_sdk.mcp.list_tools()
    tool_names = [tool.name for tool in tools]

    # List of removed tools
    removed_tools = [
        "ticket_attach",
        "ticket_attachments",
        "ticket_create_pr",
        "ticket_link_pr",
    ]

    # Verify none are present
    present_removed_tools = [tool for tool in removed_tools if tool in tool_names]

    assert len(present_removed_tools) == 0, (
        f"Found {len(present_removed_tools)} removed tools still present: "
        f"{present_removed_tools}"
    )


@pytest.mark.asyncio
async def test_alternative_tools_still_present():
    """Verify alternative tools for removed functionality still exist."""
    from mcp_ticketer.mcp.server import server_sdk

    # Get all registered MCP tools
    tools = await server_sdk.mcp.list_tools()
    tool_names = [tool.name for tool in tools]

    # Verify ticket_comment is still present (alternative for linking files/PRs)
    assert "ticket_comment" in tool_names, (
        "ticket_comment should be present (used as alternative to removed tools)"
    )


@pytest.mark.integration
def test_cli_tools_still_importable():
    """Verify attachment/PR tools still exist in codebase (CLI availability)."""
    # Import the tool modules directly (should not raise)
    from mcp_ticketer.mcp.server.tools import attachment_tools, pr_tools

    # Verify tools are defined in modules
    assert hasattr(attachment_tools, "ticket_attach")
    assert hasattr(attachment_tools, "ticket_attachments")
    assert hasattr(pr_tools, "ticket_create_pr")
    assert hasattr(pr_tools, "ticket_link_pr")

    # These tools exist in code but are not registered with MCP


def test_migration_guide_exists():
    """Verify migration documentation exists."""
    from pathlib import Path

    migration_guide = (
        Path(__file__).parent.parent.parent
        / "docs"
        / "migrations"
        / "ATTACHMENT_PR_REMOVAL.md"
    )

    assert migration_guide.exists(), (
        "Migration guide should exist at docs/migrations/ATTACHMENT_PR_REMOVAL.md"
    )

    # Verify guide has content
    content = migration_guide.read_text()
    content_lower = content.lower()
    assert "ticket_attach" in content
    assert "ticket_create_pr" in content
    assert "filesystem" in content_lower and "mcp" in content_lower
    assert "github" in content_lower and "mcp" in content_lower


def test_token_savings_documentation():
    """Verify token savings are documented."""
    from pathlib import Path

    migration_guide = (
        Path(__file__).parent.parent.parent
        / "docs"
        / "migrations"
        / "ATTACHMENT_PR_REMOVAL.md"
    )

    content = migration_guide.read_text()

    # Verify token costs are mentioned
    assert "731 tokens" in content  # ticket_attach
    assert "664 tokens" in content  # ticket_attachments
    assert "828 tokens" in content  # ticket_create_pr
    assert "717 tokens" in content  # ticket_link_pr

    # Verify total savings mentioned
    assert "2,644 tokens" in content or "2644 tokens" in content
