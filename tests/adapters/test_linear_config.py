#!/usr/bin/env python3
"""Test Linear adapter configuration and team_id usage."""

import asyncio
import os
import sys
from pathlib import Path

import pytest

# Load environment variables from .env.local
from dotenv import load_dotenv

load_dotenv(".env.local")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.adapters.linear import LinearAdapter
from mcp_ticketer.core.config import ConfigurationManager


@pytest.mark.asyncio
async def test_linear_config():
    """Test Linear adapter configuration."""
    print("🔍 Testing Linear adapter configuration...")

    # Check API key
    api_key = os.getenv("LINEAR_API_KEY")
    print(f"🔑 API Key: {'✅ Found' if api_key else '❌ Not found'}")
    if not api_key:
        print("❌ LINEAR_API_KEY not found in environment!")
        return

    # Load configuration
    config_manager = ConfigurationManager()
    config = config_manager.get_config()

    print("📋 Configuration loaded:")
    print(f"   Default adapter: {config.default_adapter}")

    linear_config = config.adapters.get("linear", {})
    print(f"   Linear config: {linear_config}")

    if not linear_config:
        print("❌ No Linear configuration found!")
        return

    # Create Linear adapter
    print("\n🔧 Creating Linear adapter...")
    # Convert Pydantic model to dict for adapter
    linear_config_dict = {
        "type": "linear",
        "team_id": linear_config.team_id,
        "team_key": linear_config.team_key,
        "api_key": os.getenv("LINEAR_API_KEY"),  # Add API key from environment
    }
    adapter = LinearAdapter(linear_config_dict)

    print(f"   Team ID (config): {getattr(adapter, 'team_id_config', 'Not set')}")
    print(f"   Team Key: {getattr(adapter, 'team_key', 'Not set')}")
    print(f"   Team ID (cached): {getattr(adapter, '_team_id', 'Not cached yet')}")

    # Test API connection
    print("\n🌐 Testing API connection...")
    try:
        # Try to list one ticket to verify connection and team
        tickets = await adapter.list(limit=1)
        print("✅ API connection successful!")
        print(f"   Found {len(tickets)} ticket(s)")

        if tickets:
            ticket = tickets[0]
            print(f"   Sample ticket: {ticket.id} - {ticket.title}")
            print(
                f"   Ticket prefix: {ticket.id.split('-')[0] if '-' in ticket.id else 'No prefix'}"
            )

    except Exception as e:
        print(f"❌ API connection failed: {e}")
        return

    # Test ticket creation to see what team it goes to
    print("\n🎫 Testing ticket creation...")
    try:
        from mcp_ticketer.core.models import Priority, Task

        test_task = Task(
            title="Linear Config Test",
            description="Testing which team this ticket gets created in",
            priority=Priority.LOW,
        )

        created_ticket = await adapter.create(test_task)
        print("✅ Ticket created successfully!")
        print(f"   Created ticket: {created_ticket.id} - {created_ticket.title}")
        print(
            f"   Ticket prefix: {created_ticket.id.split('-')[0] if '-' in created_ticket.id else 'No prefix'}"
        )

        # Check if prefix matches expected team key
        expected_prefix = linear_config.team_key or "1M"
        actual_prefix = (
            created_ticket.id.split("-")[0] if "-" in created_ticket.id else "Unknown"
        )

        if actual_prefix == expected_prefix:
            print(f"✅ Ticket prefix matches expected team key: {expected_prefix}")
        else:
            print("⚠️  Ticket prefix mismatch!")
            print(f"   Expected: {expected_prefix}")
            print(f"   Actual: {actual_prefix}")
            print("   This suggests the ticket was created in a different team")

    except Exception as e:
        print(f"❌ Ticket creation failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_linear_config())
