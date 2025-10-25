#!/usr/bin/env python3
"""Simulate worker adapter creation to debug the CLU prefix issue."""

import asyncio
import os
import sys
from pathlib import Path

# Load environment variables from .env.local
from dotenv import load_dotenv

load_dotenv(".env.local")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import adapters to trigger registration
import mcp_ticketer.adapters  # noqa: F401
from mcp_ticketer.cli.main import load_config
from mcp_ticketer.core.models import Priority, Task
from mcp_ticketer.core.registry import AdapterRegistry


async def simulate_worker_adapter_creation():
    """Simulate exactly what the worker does to create an adapter."""
    print("🔍 Simulating worker adapter creation...")

    # Step 1: Load configuration exactly like the worker does
    print("\n📋 Step 1: Loading configuration like worker...")
    project_path = Path.cwd()
    print(f"   Project path: {project_path}")

    # Load environment variables from project directory's .env.local if it exists
    env_file = project_path / ".env.local"
    if env_file.exists():
        print(f"   Loading environment from {env_file}")
        load_dotenv(env_file)

    config = load_config(project_dir=project_path)
    print(f"   Config loaded: {config}")

    # Step 2: Get adapter config exactly like the worker does
    print("\n🔧 Step 2: Getting adapter config like worker...")
    adapter_name = "linear"
    adapters_config = config.get("adapters", {})
    adapter_config = adapters_config.get(adapter_name, {})
    print(f"   Initial adapter config: {adapter_config}")

    # Add environment variables for authentication exactly like the worker does
    if adapter_name == "linear":
        if not adapter_config.get("api_key"):
            adapter_config["api_key"] = os.getenv("LINEAR_API_KEY")

    print(f"   Final adapter config: {adapter_config}")

    # Step 3: Create adapter exactly like the worker does
    print("\n⚙️  Step 3: Creating adapter like worker...")
    adapter = AdapterRegistry.get_adapter(adapter_name, adapter_config)
    print(f"   Adapter created: {type(adapter)}")
    print(f"   Team ID (config): {getattr(adapter, 'team_id_config', 'Not set')}")
    print(f"   Team Key: {getattr(adapter, 'team_key', 'Not set')}")

    # Step 4: Test ticket creation exactly like the worker does
    print("\n🎫 Step 4: Creating ticket like worker...")
    try:
        # Create task exactly like the worker does
        task_data = {
            "title": "Worker Simulation Test",
            "description": "Testing worker adapter creation simulation",
            "priority": Priority.MEDIUM,
        }
        task = Task(**task_data)

        # Create ticket
        result = await adapter.create(task)
        print("   ✅ Ticket created successfully!")
        print(f"   Created ticket: {result.id} - {result.title}")
        print(
            f"   Ticket prefix: {result.id.split('-')[0] if '-' in result.id else 'No prefix'}"
        )

        # Check if prefix matches expected team key
        expected_prefix = adapter_config.get("team_key", "1M")
        actual_prefix = result.id.split("-")[0] if "-" in result.id else "Unknown"

        if actual_prefix == expected_prefix:
            print(f"   ✅ Ticket prefix matches expected team key: {expected_prefix}")
        else:
            print("   ⚠️  Ticket prefix mismatch!")
            print(f"      Expected: {expected_prefix}")
            print(f"      Actual: {actual_prefix}")
            print("      This suggests the ticket was created in a different team")

        return result

    except Exception as e:
        print(f"   ❌ Ticket creation failed: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    asyncio.run(simulate_worker_adapter_creation())
