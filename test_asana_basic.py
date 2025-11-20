#!/usr/bin/env python3
"""Basic test script for Asana adapter functionality."""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.adapters.asana import AsanaAdapter


async def test_asana_connection():
    """Test basic Asana connection and operations."""
    # Get API key from environment
    api_key = os.getenv("ASANA_PAT")
    if not api_key:
        return False


    try:
        # Initialize adapter
        adapter = AsanaAdapter({"api_key": api_key})

        # Validate credentials
        is_valid, error_msg = adapter.validate_credentials()
        if not is_valid:
            return False


        # Initialize adapter (connects and resolves workspace)
        await adapter.initialize()

        # Test connection
        connection_ok = await adapter.client.test_connection()
        if connection_ok:
            pass
        else:
            return False

        # List existing projects (epics)
        epics = await adapter.list_epics()
        for _epic in epics[:5]:  # Show first 5
            pass

        # List existing tasks
        tasks = await adapter.list(limit=5)
        for task in tasks:
            pass

        # Test read operation
        if tasks:
            task = await adapter.read(tasks[0].id)
            if task:
                pass
            else:
                pass

        # Test create operation (optional - uncomment to test)
        # print(f"\n7. Testing create operation...")
        # new_task = Task(
        #     title="Test Task from MCP Ticketer",
        #     description="This is a test task created by the Asana adapter",
        #     priority=Priority.MEDIUM,
        #     state=TicketState.OPEN,
        #     ticket_type=TicketType.ISSUE,
        #     tags=["test", "mcp-ticketer"],
        # )
        # created = await adapter.create(new_task)
        # if created:
        #     print(f"   ✓ Created task: {created.title} (GID: {created.id})")
        #     print(f"   URL: {created.metadata.get('asana_permalink_url')}")
        #
        #     # Clean up - delete the test task
        #     print(f"\n8. Cleaning up test task...")
        #     deleted = await adapter.delete(created.id)
        #     if deleted:
        #         print(f"   ✓ Deleted test task")
        # else:
        #     print("   ERROR: Failed to create task")

        # Close adapter
        await adapter.close()

        return True

    except Exception:
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Load environment variables from .env.local
    env_file = Path(__file__).parent / ".env.local"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

    # Run test
    success = asyncio.run(test_asana_connection())
    sys.exit(0 if success else 1)
