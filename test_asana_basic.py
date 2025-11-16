#!/usr/bin/env python3
"""Basic test script for Asana adapter functionality."""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.adapters.asana import AsanaAdapter
from mcp_ticketer.core.models import Priority, Task, TicketState, TicketType


async def test_asana_connection():
    """Test basic Asana connection and operations."""
    print("=" * 60)
    print("ASANA ADAPTER - BASIC CONNECTION TEST")
    print("=" * 60)

    # Get API key from environment
    api_key = os.getenv("ASANA_PAT")
    if not api_key:
        print("ERROR: ASANA_PAT environment variable not set")
        print("Please set it in .env.local file")
        return False

    print("\n1. Initializing Asana adapter...")
    print(f"   API Key: {api_key[:10]}...{api_key[-5:]}")

    try:
        # Initialize adapter
        adapter = AsanaAdapter({"api_key": api_key})

        # Validate credentials
        is_valid, error_msg = adapter.validate_credentials()
        if not is_valid:
            print(f"   ERROR: Credential validation failed: {error_msg}")
            return False

        print("   ✓ Credentials validated")

        # Initialize adapter (connects and resolves workspace)
        print("\n2. Connecting to Asana API and resolving workspace...")
        await adapter.initialize()
        print("   ✓ Connected successfully")
        print(f"   Workspace GID: {adapter._workspace_gid}")

        # Test connection
        print("\n3. Testing API connection...")
        connection_ok = await adapter.client.test_connection()
        if connection_ok:
            print("   ✓ Connection test passed")
        else:
            print("   ERROR: Connection test failed")
            return False

        # List existing projects (epics)
        print("\n4. Fetching existing projects (epics)...")
        epics = await adapter.list_epics()
        print(f"   Found {len(epics)} projects:")
        for epic in epics[:5]:  # Show first 5
            print(f"   - {epic.title} (GID: {epic.id})")

        # List existing tasks
        print("\n5. Fetching existing tasks...")
        tasks = await adapter.list(limit=5)
        print(f"   Found {len(tasks)} tasks:")
        for task in tasks:
            print(f"   - {task.title} (GID: {task.id}, Type: {task.ticket_type})")

        # Test read operation
        if tasks:
            print("\n6. Testing read operation on first task...")
            task = await adapter.read(tasks[0].id)
            if task:
                print(f"   ✓ Successfully read task: {task.title}")
                print(f"   State: {task.state}")
                print(f"   Priority: {task.priority}")
                print(f"   Tags: {task.tags}")
            else:
                print("   ERROR: Failed to read task")

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

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Load environment variables from .env.local
    env_file = Path(__file__).parent / ".env.local"
    if env_file.exists():
        print(f"Loading environment from {env_file}")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

    # Run test
    success = asyncio.run(test_asana_connection())
    sys.exit(0 if success else 1)
