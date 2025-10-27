#!/usr/bin/env python3
"""
Test script for the unified environment loading system.
This tests that all adapters can load their configuration consistently
from environment variables using multiple naming conventions.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.core.env_loader import (
    get_env_loader,
    load_adapter_config,
    validate_adapter_config,
)
from mcp_ticketer.core.registry import AdapterRegistry

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_unified_env_loading():
    """Test the unified environment loading system."""
    print("🚀 Testing Unified Environment Loading System")
    print("=" * 60)

    # Get the environment loader
    env_loader = get_env_loader()

    # Show debug info
    debug_info = env_loader.get_debug_info()
    print(f"📁 Project Root: {debug_info['project_root']}")
    print("📄 Environment Files Checked:")
    for env_file in debug_info["env_files_checked"]:
        exists = "✅" if Path(env_file).exists() else "❌"
        print(f"    {exists} {env_file}")

    print(f"🔑 Loaded Environment Keys: {len(debug_info['loaded_keys'])}")
    for key in sorted(debug_info["loaded_keys"]):
        print(f"    - {key}")

    print(f"\n🔧 Available Configuration Keys: {len(debug_info['available_configs'])}")
    for key in sorted(debug_info["available_configs"]):
        print(f"    - {key}")

    print("\n" + "=" * 60)

    # Test each adapter
    adapters_to_test = ["linear", "jira", "github"]

    for adapter_name in adapters_to_test:
        print(f"\n🔍 Testing {adapter_name.upper()} Adapter Configuration")
        print("-" * 40)

        # Load configuration
        config = load_adapter_config(adapter_name, {})

        print("📋 Loaded Configuration:")
        for key, value in config.items():
            if key in ["api_key", "api_token", "token"]:
                # Mask sensitive values
                masked_value = (
                    value[:10] + "..." if value and len(value) > 10 else value
                )
                print(f"    {key}: {masked_value}")
            else:
                print(f"    {key}: {value}")

        # Validate configuration
        missing_keys = validate_adapter_config(adapter_name, config)
        if missing_keys:
            print(f"❌ Missing Required Keys: {missing_keys}")
        else:
            print("✅ All required configuration present")

        # Test adapter creation
        try:
            adapter = AdapterRegistry.get_adapter(adapter_name, config)
            print(f"✅ {adapter_name.capitalize()} adapter created successfully")

            # Test basic functionality
            if hasattr(adapter, "api_key") and adapter.api_key:
                print(f"✅ API key loaded: {adapter.api_key[:10]}...")
            elif hasattr(adapter, "token") and adapter.token:
                print(f"✅ Token loaded: {adapter.token[:10]}...")
            elif hasattr(adapter, "api_token") and adapter.api_token:
                print(f"✅ API token loaded: {adapter.api_token[:10]}...")

        except Exception as e:
            print(f"❌ {adapter_name.capitalize()} adapter creation failed: {e}")

    print("\n" + "=" * 60)
    print("🧪 Testing Environment Variable Aliases")
    print("-" * 40)

    # Test different naming conventions
    test_cases = [
        ("linear_api_key", ["LINEAR_API_KEY", "LINEAR_TOKEN", "LINEAR_ACCESS_TOKEN"]),
        ("jira_api_token", ["JIRA_API_TOKEN", "JIRA_TOKEN", "JIRA_ACCESS_TOKEN"]),
        ("github_token", ["GITHUB_TOKEN", "GITHUB_ACCESS_TOKEN", "GITHUB_API_TOKEN"]),
    ]

    for config_key, env_keys in test_cases:
        print(f"\n🔑 Testing {config_key}:")

        # Clear all related env vars first
        for env_key in env_keys:
            if env_key in os.environ:
                del os.environ[env_key]

        # Test each alias
        test_value = "test_value_12345"
        for env_key in env_keys:
            # Set the environment variable
            os.environ[env_key] = test_value

            # Test if it's found
            value = env_loader.get_value(config_key)
            if value == test_value:
                print(f"    ✅ {env_key} -> {config_key}")
            else:
                print(f"    ❌ {env_key} -> {config_key} (got: {value})")

            # Clean up
            del os.environ[env_key]

    print("\n" + "=" * 60)
    print("🎯 Testing Real Adapter Operations")
    print("-" * 40)

    # Test actual adapter operations with loaded configuration
    for adapter_name in adapters_to_test:
        print(f"\n🔧 Testing {adapter_name.upper()} Operations:")

        try:
            config = load_adapter_config(adapter_name, {})
            missing_keys = validate_adapter_config(adapter_name, config)

            if missing_keys:
                print(f"    ⏭️  Skipping - missing required keys: {missing_keys}")
                continue

            adapter = AdapterRegistry.get_adapter(adapter_name, config)

            # Test list operation (should work if authentication is valid)
            try:
                tickets = await adapter.list(limit=1, offset=0)
                print(
                    f"    ✅ List operation successful - found {len(tickets)} tickets"
                )
            except Exception as e:
                print(f"    ⚠️  List operation failed: {e}")

        except Exception as e:
            print(f"    ❌ Adapter setup failed: {e}")

    print("\n" + "=" * 60)
    print("✅ Unified Environment Loading Test Complete!")


if __name__ == "__main__":
    asyncio.run(test_unified_env_loading())
