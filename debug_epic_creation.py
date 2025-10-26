#!/usr/bin/env python3
"""Debug script to trace epic creation flow."""

import sys
import asyncio
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.core.models import Epic
from mcp_ticketer.adapters.aitrackdown import AITrackdownAdapter


async def main():
    """Test epic creation flow."""
    print("=" * 80)
    print("EPIC CREATION DEBUG")
    print("=" * 80)

    # Setup test directory
    test_dir = Path("/tmp/test_epic")
    test_dir.mkdir(exist_ok=True)

    # Create adapter
    config = {"base_path": str(test_dir)}
    adapter = AITrackdownAdapter(config)

    print(f"\n1. Adapter initialized:")
    print(f"   base_path: {adapter.base_path}")
    print(f"   tickets_dir: {adapter.tickets_dir}")
    print(f"   tickets_dir exists: {adapter.tickets_dir.exists()}")
    print(f"   tracker: {adapter.tracker}")

    # Create epic
    print(f"\n2. Creating epic...")
    epic = Epic(title="Test Epic", description="Test Description")
    print(f"   Epic before create: id={epic.id}, title={epic.title}")

    # Call create
    print(f"\n3. Calling adapter.create(epic)...")
    result = await adapter.create(epic)

    print(f"\n4. Result from create:")
    print(f"   id: {result.id}")
    print(f"   title: {result.title}")
    print(f"   type: {type(result)}")

    # Check if file exists
    expected_file = adapter.tickets_dir / f"{result.id}.json"
    print(f"\n5. File system check:")
    print(f"   Expected file: {expected_file}")
    print(f"   File exists: {expected_file.exists()}")

    if expected_file.exists():
        import json
        with open(expected_file) as f:
            content = json.load(f)
        print(f"   File content: {json.dumps(content, indent=2)}")
    else:
        print(f"   ❌ FILE NOT FOUND!")
        print(f"\n   Files in tickets_dir:")
        for f in adapter.tickets_dir.iterdir():
            print(f"      - {f.name}")

    # Try to read back
    print(f"\n6. Reading back epic...")
    read_result = await adapter.read(result.id)
    print(f"   Read result: {read_result}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
