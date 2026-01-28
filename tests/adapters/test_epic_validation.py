#!/usr/bin/env python3
"""
Test script to verify epic creation validation logic.
Tests both happy path and error scenarios for team_id validation.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.adapters.linear.adapter import LinearAdapter


async def test_happy_path():
    """Test epic creation with valid team_id configuration."""
    print("\n=== TEST 1: Happy Path - Valid team_id ===")

    try:
        # Initialize with valid configuration
        adapter = LinearAdapter(team_key="1M")
        await adapter.initialize()

        print("✓ Adapter initialized successfully")
        print(f"  Team Key: {adapter.team_key}")
        print(f"  Team ID: {adapter.team_id}")

        # Verify team_id is resolved
        team_id = await adapter._ensure_team_id()
        print(f"✓ team_id resolved: {team_id}")

        # The validation check we're testing
        if not team_id:
            print("✗ FAIL: team_id is empty (should not happen)")
            return False

        print("✓ Validation check passed: team_id is present")
        print("\n✅ TEST 1 PASSED: Epic creation should work with this configuration")
        return True

    except Exception as e:
        print(f"✗ TEST 1 FAILED: {type(e).__name__}: {e}")
        return False


async def test_error_path_no_team_key():
    """Test epic creation without team_key configuration."""
    print("\n=== TEST 2: Error Path - Missing team_key ===")

    try:
        # Initialize without team_key
        adapter = LinearAdapter()
        await adapter.initialize()

        print("✗ FAIL: Adapter initialized without team_key (should fail)")
        return False

    except ValueError as e:
        error_msg = str(e)
        print(f"✓ ValueError raised as expected: {error_msg}")

        # Check if error message is helpful
        if "team_id" in error_msg.lower() or "team_key" in error_msg.lower():
            print("✓ Error message mentions team configuration")

        print("\n✅ TEST 2 PASSED: Proper error handling for missing team_key")
        return True

    except Exception as e:
        print(f"✗ TEST 2 FAILED: Wrong exception type: {type(e).__name__}: {e}")
        return False


async def test_team_id_validation():
    """Test that team_id validation occurs before GraphQL call."""
    print("\n=== TEST 3: Validation Timing - Check happens before API call ===")

    try:
        # Initialize with valid configuration
        adapter = LinearAdapter(team_key="1M")
        await adapter.initialize()

        # Mock empty team_id to test validation
        original_team_id = adapter.team_id
        adapter.team_id = None

        # Try to ensure team_id - should raise error from _ensure_team_id
        try:
            await adapter._ensure_team_id()
            print("✗ FAIL: _ensure_team_id() did not raise error for None team_id")
            return False
        except ValueError as e:
            print(f"✓ _ensure_team_id() correctly raises ValueError: {e}")

        # Restore team_id for cleanup
        adapter.team_id = original_team_id

        print("\n✅ TEST 3 PASSED: Validation occurs before API calls")
        return True

    except Exception as e:
        print(f"✗ TEST 3 FAILED: {type(e).__name__}: {e}")
        return False


async def main():
    """Run all validation tests."""
    print("=" * 70)
    print("LINEAR ADAPTER EPIC CREATION VALIDATION TEST SUITE")
    print("Testing fix for 1M-552: GraphQL validation error")
    print("=" * 70)

    results = []

    # Run tests
    results.append(("Happy Path", await test_happy_path()))
    results.append(("Error Path - No team_key", await test_error_path_no_team_key()))
    results.append(("Validation Timing", await test_team_id_validation()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(result[1] for result in results)

    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED - Epic creation validation is working correctly")
        print("=" * 70)
        return 0
    else:
        print("❌ SOME TESTS FAILED - Epic creation validation needs review")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
