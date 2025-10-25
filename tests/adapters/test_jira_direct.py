#!/usr/bin/env python3
"""
Direct test of JIRA adapter with MT project to debug issues.
"""

import asyncio
import logging
import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import adapters to register them
from mcp_ticketer.core.env_loader import load_adapter_config, validate_adapter_config
from mcp_ticketer.core.models import Priority, Task
from mcp_ticketer.core.registry import AdapterRegistry

# Set up logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@pytest.mark.skip(
    reason="Standalone script, not a pytest test - run directly with python"
)
@pytest.mark.asyncio
async def test_jira_direct():
    """Test JIRA adapter directly with MT project."""
    print("🔍 Testing JIRA adapter directly with MT project...")

    try:
        # Load configuration
        config = load_adapter_config("jira", {})
        print("📋 Loaded configuration:")
        for key, value in config.items():
            if key in ["api_token"]:
                masked_value = (
                    value[:10] + "..." if value and len(value) > 10 else value
                )
                print(f"    {key}: {masked_value}")
            else:
                print(f"    {key}: {value}")

        # Validate configuration
        missing_keys = validate_adapter_config("jira", config)
        if missing_keys:
            print(f"❌ Missing required keys: {missing_keys}")
            return

        print("✅ All required configuration present")

        # Create adapter
        adapter = AdapterRegistry.get_adapter("jira", config)
        print("✅ JIRA adapter created successfully")

        # Test listing first
        print("\n🔍 Testing JIRA list operation...")
        try:
            tickets = await adapter.list(limit=3, offset=0)
            print(f"✅ List operation successful - found {len(tickets)} tickets")
        except Exception as e:
            print(f"❌ List operation failed: {e}")
            return

        # Test creating a ticket
        print("\n🔍 Testing JIRA ticket creation...")
        test_task = Task(
            title="🧪 Direct JIRA Test - MT Project",
            description="Testing JIRA adapter directly with MT project.\n\nThis should work now!",
            priority=Priority.MEDIUM,
            tags=["test", "jira", "mt-project"],
        )

        try:
            created_ticket = await adapter.create(test_task)
            print("✅ JIRA ticket created successfully!")
            print(f"    Ticket ID: {created_ticket.id}")
            print(f"    Title: {created_ticket.title}")
            print(f"    State: {created_ticket.state}")
            print(f"    Priority: {created_ticket.priority}")

            # Get the URL if available
            if hasattr(created_ticket, "metadata") and created_ticket.metadata:
                jira_meta = created_ticket.metadata.get("jira", {})
                if "url" in jira_meta:
                    print(f"    URL: {jira_meta['url']}")

            return created_ticket

        except Exception as e:
            print(f"❌ JIRA ticket creation failed: {e}")
            import traceback

            traceback.print_exc()
            return None

    except Exception as e:
        print(f"❌ JIRA adapter test failed: {e}")
        import traceback

        traceback.print_exc()


@pytest.mark.skip(
    reason="Standalone script, not a pytest test - run directly with python"
)
@pytest.mark.asyncio
async def test_jira_commenting(ticket):
    """Test JIRA commenting functionality."""
    if not ticket:
        print("⏭️  Skipping comment test - no ticket created")
        return

    print("\n💬 Testing JIRA commenting...")

    try:
        # Load configuration and create adapter
        config = load_adapter_config("jira", {})
        adapter = AdapterRegistry.get_adapter("jira", config)

        # Import Comment model
        from mcp_ticketer.core.models import Comment

        # Test adding a comment
        comment = Comment(
            ticket_id=ticket.id,
            content="🧪 Test comment added via direct JIRA adapter test!\n\nThis comment was added to verify commenting functionality.",
            author="test-user",
        )

        result = await adapter.add_comment(comment)
        print("✅ Comment added successfully!")
        print(f"    Comment ID: {result.id}")
        print(f"    Content: {result.content[:50]}...")

        # Test retrieving comments
        print("\n📖 Testing comment retrieval...")
        comments = await adapter.get_comments(ticket.id, limit=10, offset=0)
        print(f"✅ Retrieved {len(comments)} comments")

        if comments:
            for i, comment in enumerate(comments, 1):
                print(f"    Comment #{i}:")
                print(f"        ID: {comment.id}")
                print(f"        Author: {comment.author}")
                print(f"        Created: {comment.created_at}")
                print(f"        Content: {comment.content[:60]}...")

        return True

    except Exception as e:
        print(f"❌ JIRA commenting test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run the direct JIRA test."""
    print("🚀 Starting Direct JIRA Test with MT Project")
    print("=" * 60)

    # Test ticket creation
    ticket = await test_jira_direct()

    # Test commenting if ticket was created
    if ticket:
        await test_jira_commenting(ticket)

    print("\n" + "=" * 60)
    print("✅ Direct JIRA test complete!")


if __name__ == "__main__":
    asyncio.run(main())
