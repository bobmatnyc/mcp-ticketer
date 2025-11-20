#!/usr/bin/env python3
"""Debug script to trace epic creation flow."""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.adapters.aitrackdown import AITrackdownAdapter
from mcp_ticketer.core.models import Epic


async def main():
    """Test epic creation flow."""
    # Setup test directory
    test_dir = Path("/tmp/test_epic")
    test_dir.mkdir(exist_ok=True)

    # Create adapter
    config = {"base_path": str(test_dir)}
    adapter = AITrackdownAdapter(config)


    # Create epic
    epic = Epic(title="Test Epic", description="Test Description")

    # Call create
    result = await adapter.create(epic)


    # Check if file exists
    expected_file = adapter.tickets_dir / f"{result.id}.json"

    if expected_file.exists():
        import json
        with open(expected_file) as f:
            json.load(f)
    else:
        for f in adapter.tickets_dir.iterdir():
            pass

    # Try to read back
    await adapter.read(result.id)



if __name__ == "__main__":
    asyncio.run(main())
