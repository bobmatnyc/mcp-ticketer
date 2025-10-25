#!/usr/bin/env python3
"""Test script for PR creation and linking functionality."""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.adapters.github import GitHubAdapter
from mcp_ticketer.adapters.linear import LinearAdapter
from mcp_ticketer.core.models import Priority, Task, TicketState


async def test_github_pr_creation():
    """Test GitHub PR creation functionality."""
    print("\n=== Testing GitHub PR Creation ===")

    # Initialize GitHub adapter
    config = {
        "token": os.getenv("GITHUB_TOKEN"),
        "owner": os.getenv("GITHUB_OWNER", "test-owner"),
        "repo": os.getenv("GITHUB_REPO", "test-repo"),
    }

    if not config["token"]:
        print("⚠️  GITHUB_TOKEN not set, skipping GitHub tests")
        return

    try:
        adapter = GitHubAdapter(config)

        # Create a test issue first
        test_issue = Task(
            title="Test Issue for PR Creation",
            description="This is a test issue to verify PR creation functionality",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
            tags=["test", "pr-creation"],
        )

        print("Creating test issue...")
        created_issue = await adapter.create(test_issue)
        print(f"✅ Created issue #{created_issue.id}")

        # Create a PR for the issue
        print(f"Creating PR for issue #{created_issue.id}...")
        pr_result = await adapter.create_pull_request(
            ticket_id=created_issue.id,
            base_branch="main",
            title=f"Test PR for issue #{created_issue.id}",
            body="This is a test pull request",
            draft=True,
        )

        print(f"✅ Created PR #{pr_result['number']}: {pr_result['url']}")
        print(f"   Branch: {pr_result['branch']}")
        print(f"   Linked to issue: #{pr_result['linked_issue']}")

        # Test linking an existing PR
        print("\nTesting PR linking...")
        link_result = await adapter.link_existing_pull_request(
            ticket_id=created_issue.id,
            pr_url=pr_result["url"],
        )

        if link_result["success"]:
            print("✅ Successfully linked PR to issue")
            print(f"   {link_result['message']}")
        else:
            print(f"❌ Failed to link PR: {link_result.get('error', 'Unknown error')}")

        # Close the test issue
        await adapter.delete(created_issue.id)
        print(f"✅ Closed test issue #{created_issue.id}")

    except Exception as e:
        print(f"❌ GitHub test failed: {e}")
        import traceback

        traceback.print_exc()


async def test_linear_pr_linking():
    """Test Linear PR linking functionality."""
    print("\n=== Testing Linear PR Linking ===")

    # Initialize Linear adapter
    config = {
        "api_key": os.getenv("LINEAR_API_KEY"),
        "team_key": os.getenv("LINEAR_TEAM_KEY", "ENG"),
    }

    if not config["api_key"]:
        print("⚠️  LINEAR_API_KEY not set, skipping Linear tests")
        return

    try:
        adapter = LinearAdapter(config)
        await adapter.initialize()

        # Create a test issue
        test_issue = Task(
            title="Test Issue for PR Linking",
            description="This is a test issue to verify PR linking functionality",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
            tags=["test", "pr-linking"],
        )

        print("Creating test issue...")
        created_issue = await adapter.create(test_issue)
        print(f"✅ Created issue {created_issue.id}")

        # Prepare for PR creation (sets branch name)
        print(f"Preparing issue {created_issue.id} for PR creation...")
        github_config = {
            "owner": "test-owner",
            "repo": "test-repo",
            "base_branch": "main",
        }

        pr_metadata = await adapter.create_pull_request_for_issue(
            ticket_id=created_issue.id,
            github_config=github_config,
        )

        print("✅ Prepared issue for PR:")
        print(f"   Branch name: {pr_metadata['branch_name']}")
        print(f"   {pr_metadata['message']}")

        # Test linking to a PR (using a dummy URL for testing)
        print("\nTesting PR linking...")
        test_pr_url = "https://github.com/test-owner/test-repo/pull/123"

        link_result = await adapter.link_to_pull_request(
            ticket_id=created_issue.id,
            pr_url=test_pr_url,
        )

        if link_result["success"]:
            print("✅ Successfully linked PR to Linear issue")
            print(f"   {link_result['message']}")
            print(f"   Attachment ID: {link_result['attachment_id']}")
        else:
            print(f"⚠️  PR linking returned: {link_result['message']}")

        # Clean up - transition issue to closed
        await adapter.transition_state(created_issue.id, TicketState.CLOSED)
        print(f"✅ Closed test issue {created_issue.id}")

    except Exception as e:
        print(f"❌ Linear test failed: {e}")
        import traceback

        traceback.print_exc()


async def test_mcp_server_pr_tools():
    """Test MCP server PR tools."""
    print("\n=== Testing MCP Server PR Tools ===")

    from mcp_ticketer.mcp.server import MCPTicketServer

    # Test with GitHub adapter
    if os.getenv("GITHUB_TOKEN"):
        print("\nTesting with GitHub adapter...")
        server = MCPTicketServer(
            adapter_type="github",
            config={
                "token": os.getenv("GITHUB_TOKEN"),
                "owner": os.getenv("GITHUB_OWNER", "test-owner"),
                "repo": os.getenv("GITHUB_REPO", "test-repo"),
            },
        )

        # Test tools list
        tools_response = await server._handle_tools_list()
        pr_tools = [t for t in tools_response["tools"] if "pr" in t["name"].lower()]

        print(f"✅ Found {len(pr_tools)} PR-related tools:")
        for tool in pr_tools:
            print(f"   - {tool['name']}: {tool['description']}")

    # Test with Linear adapter
    if os.getenv("LINEAR_API_KEY"):
        print("\nTesting with Linear adapter...")
        server = MCPTicketServer(
            adapter_type="linear",
            config={
                "api_key": os.getenv("LINEAR_API_KEY"),
                "team_key": os.getenv("LINEAR_TEAM_KEY", "ENG"),
            },
        )

        # Test tools list
        tools_response = await server._handle_tools_list()
        pr_tools = [t for t in tools_response["tools"] if "pr" in t["name"].lower()]

        print(f"✅ Found {len(pr_tools)} PR-related tools:")
        for tool in pr_tools:
            print(f"   - {tool['name']}: {tool['description']}")


async def main():
    """Run all tests."""
    print("=" * 50)
    print("Testing PR Creation and Linking Functionality")
    print("=" * 50)

    # Run tests
    await test_github_pr_creation()
    await test_linear_pr_linking()
    await test_mcp_server_pr_tools()

    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
