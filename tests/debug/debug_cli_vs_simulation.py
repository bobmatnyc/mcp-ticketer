#!/usr/bin/env python3
"""Compare CLI vs simulation configuration loading."""

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
from mcp_ticketer.cli.main import get_adapter, load_config
from mcp_ticketer.core.models import Priority, Task
from mcp_ticketer.core.registry import AdapterRegistry


async def compare_cli_vs_simulation():
    """Compare CLI vs simulation configuration loading."""
    print("🔍 Comparing CLI vs simulation configuration loading...")

    # Method 1: CLI get_adapter method
    print("\n📋 Method 1: CLI get_adapter method...")
    try:
        cli_adapter = get_adapter(override_adapter="linear")
        print("   ✅ CLI adapter created successfully!")
        print(
            f"   Team ID (config): {getattr(cli_adapter, 'team_id_config', 'Not set')}"
        )
        print(f"   Team Key: {getattr(cli_adapter, 'team_key', 'Not set')}")
        print(f"   Instance ID: {id(cli_adapter)}")

        # Test ticket creation with CLI adapter
        task_data = {
            "title": "CLI Method Test",
            "description": "Testing CLI adapter method",
            "priority": Priority.LOW,
        }
        task = Task(**task_data)
        cli_result = await cli_adapter.create(task)
        print(f"   Created ticket: {cli_result.id} - {cli_result.title}")
        print(
            f"   Ticket prefix: {cli_result.id.split('-')[0] if '-' in cli_result.id else 'No prefix'}"
        )

    except Exception as e:
        print(f"   ❌ CLI adapter failed: {e}")
        cli_adapter = None
        cli_result = None

    # Method 2: Direct registry method (like our simulation)
    print("\n🔧 Method 2: Direct registry method...")
    try:
        # Load config like simulation
        config = load_config()
        adapters_config = config.get("adapters", {})
        adapter_config = adapters_config.get("linear", {})

        # Add API key
        if not adapter_config.get("api_key"):
            adapter_config["api_key"] = os.getenv("LINEAR_API_KEY")

        print(f"   Config: {adapter_config}")

        # Create adapter directly
        direct_adapter = AdapterRegistry.get_adapter(
            "linear", adapter_config, force_new=True
        )
        print("   ✅ Direct adapter created successfully!")
        print(
            f"   Team ID (config): {getattr(direct_adapter, 'team_id_config', 'Not set')}"
        )
        print(f"   Team Key: {getattr(direct_adapter, 'team_key', 'Not set')}")
        print(f"   Instance ID: {id(direct_adapter)}")

        # Test ticket creation with direct adapter
        task_data = {
            "title": "Direct Method Test",
            "description": "Testing direct adapter method",
            "priority": Priority.LOW,
        }
        task = Task(**task_data)
        direct_result = await direct_adapter.create(task)
        print(f"   Created ticket: {direct_result.id} - {direct_result.title}")
        print(
            f"   Ticket prefix: {direct_result.id.split('-')[0] if '-' in direct_result.id else 'No prefix'}"
        )

    except Exception as e:
        print(f"   ❌ Direct adapter failed: {e}")
        direct_adapter = None
        direct_result = None

    # Compare results
    print("\n🔍 Comparison Results:")
    if cli_result and direct_result:
        cli_prefix = cli_result.id.split("-")[0] if "-" in cli_result.id else "Unknown"
        direct_prefix = (
            direct_result.id.split("-")[0] if "-" in direct_result.id else "Unknown"
        )

        print(f"   CLI prefix: {cli_prefix}")
        print(f"   Direct prefix: {direct_prefix}")

        if cli_prefix == direct_prefix:
            print(f"   ✅ Both methods create tickets with same prefix: {cli_prefix}")
        else:
            print("   ⚠️  Different prefixes detected!")
            print("      This suggests different team configurations")

        # Check if same adapter instance
        if cli_adapter and direct_adapter:
            if id(cli_adapter) == id(direct_adapter):
                print("   ⚠️  Same adapter instance (cached)")
            else:
                print("   ✅ Different adapter instances")

    # Check registry state
    print("\n📊 Registry State:")
    instances = AdapterRegistry._instances
    print(f"   Cached instances: {list(instances.keys())}")
    if "linear" in instances:
        linear_instance = instances["linear"]
        print(f"   Linear instance ID: {id(linear_instance)}")
        print(f"   Team ID: {getattr(linear_instance, 'team_id_config', 'Not set')}")
        print(f"   Team Key: {getattr(linear_instance, 'team_key', 'Not set')}")


if __name__ == "__main__":
    asyncio.run(compare_cli_vs_simulation())
