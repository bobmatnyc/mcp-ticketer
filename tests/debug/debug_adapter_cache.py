#!/usr/bin/env python3
"""Debug adapter registry caching."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import adapters to trigger registration
import mcp_ticketer.adapters  # noqa: F401
from mcp_ticketer.core.registry import AdapterRegistry


def debug_adapter_cache():
    """Debug adapter registry caching."""
    print("🔍 Debugging adapter registry caching...")

    # Check current registry state
    print("\n📋 Current registry state:")
    adapters = AdapterRegistry.list_adapters()
    print(f"   Registered adapters: {list(adapters.keys())}")

    # Check cached instances
    instances = AdapterRegistry._instances
    print(f"   Cached instances: {list(instances.keys())}")

    if "linear" in instances:
        linear_instance = instances["linear"]
        print("   Linear instance found!")
        print(
            f"   Team ID (config): {getattr(linear_instance, 'team_id_config', 'Not set')}"
        )
        print(f"   Team Key: {getattr(linear_instance, 'team_key', 'Not set')}")
        print(f"   Instance ID: {id(linear_instance)}")

        # Clear the cache and try again
        print("\n🧹 Clearing adapter cache...")
        AdapterRegistry._instances.clear()
        print("   Cache cleared!")

        # Now try to get adapter with correct config
        print("\n🔧 Creating new adapter with correct config...")
        correct_config = {
            "type": "linear",
            "team_id": "b366b0de-2f3f-4641-8100-eea12b6aa5df",
            "team_key": "1M",
        }

        try:
            new_adapter = AdapterRegistry.get_adapter("linear", correct_config)
            print("   New adapter created!")
            print(
                f"   Team ID (config): {getattr(new_adapter, 'team_id_config', 'Not set')}"
            )
            print(f"   Team Key: {getattr(new_adapter, 'team_key', 'Not set')}")
            print(f"   Instance ID: {id(new_adapter)}")

            # Check if it's different from the old one
            if id(new_adapter) != id(linear_instance):
                print("   ✅ New instance created (different from cached one)")
            else:
                print("   ⚠️  Same instance returned (caching issue)")

        except Exception as e:
            print(f"   ❌ Failed to create new adapter: {e}")
    else:
        print("   No Linear instance cached")


if __name__ == "__main__":
    debug_adapter_cache()
