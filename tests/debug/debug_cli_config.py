#!/usr/bin/env python3
"""Debug CLI configuration loading."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.cli.main import get_adapter, load_config


def debug_cli_config():
    """Debug CLI configuration loading."""
    print("🔍 Debugging CLI configuration loading...")

    # Load configuration using CLI method
    print("\n📋 Loading configuration using CLI method...")
    config = load_config()
    print(f"   Raw config: {config}")

    # Check adapters section
    adapters_config = config.get("adapters", {})
    print(f"   Adapters config: {adapters_config}")

    # Check linear adapter config specifically
    linear_config = adapters_config.get("linear", {})
    print(f"   Linear config: {linear_config}")

    # Get adapter using CLI method
    print("\n🔧 Getting adapter using CLI method...")
    try:
        adapter = get_adapter(override_adapter="linear")
        print("   Adapter created successfully!")
        print(f"   Adapter type: {type(adapter)}")
        print(f"   Team ID (config): {getattr(adapter, 'team_id_config', 'Not set')}")
        print(f"   Team Key: {getattr(adapter, 'team_key', 'Not set')}")

    except Exception as e:
        print(f"   ❌ Failed to create adapter: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    debug_cli_config()
