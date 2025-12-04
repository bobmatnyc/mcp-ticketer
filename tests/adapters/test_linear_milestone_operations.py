#!/usr/bin/env python3
"""Integration tests for Linear adapter milestone operations (1M-607 Phase 2).

These tests verify that Linear Cycles are correctly mapped to the universal
Milestone model, with proper state transitions, progress calculation, and
issue management.

Test Coverage:
- Milestone creation with target dates
- Milestone retrieval with progress
- Milestone listing with filters
- Milestone updates (name, date, state)
- Milestone deletion (archiving)
- Issue retrieval for milestones
- Error handling (not found, invalid dates)

"""

import asyncio
import os
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from dotenv import load_dotenv

from mcp_ticketer.core import AdapterRegistry

# Load environment variables
load_dotenv()


@pytest_asyncio.fixture
async def linear_adapter():
    """Create Linear adapter instance for testing."""
    api_key = os.getenv("LINEAR_API_KEY")
    team_id = os.getenv("LINEAR_TEAM_ID")

    if not api_key or not team_id:
        pytest.skip("LINEAR_API_KEY and LINEAR_TEAM_ID must be set")

    config = {"api_key": api_key, "team_id": team_id}
    adapter = AdapterRegistry.get_adapter("linear", config)
    await adapter.initialize()

    yield adapter

    # Cleanup
    await adapter.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_milestone_create_with_target_date(linear_adapter):
    """Test milestone creation with a target date."""
    target_date = datetime.now(timezone.utc) + timedelta(days=14)

    milestone = await linear_adapter.milestone_create(
        name=f"Test Milestone {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        description="Test milestone for Linear integration",
        target_date=target_date,
        labels=["test", "milestone"],
    )

    assert milestone is not None
    assert milestone.id is not None
    assert milestone.name.startswith("Test Milestone")
    assert milestone.state in ["open", "active"]
    assert milestone.target_date is not None
    assert len(milestone.labels) == 2
    assert "test" in milestone.labels

    print(f"✅ Created milestone: {milestone.id} - {milestone.name}")
    print(f"   State: {milestone.state}")
    print(f"   Target: {milestone.target_date}")

    # Cleanup: Archive the test milestone
    await linear_adapter.milestone_delete(milestone.id)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_milestone_create_default_duration(linear_adapter):
    """Test milestone creation with default 2-week duration."""
    milestone = await linear_adapter.milestone_create(
        name=f"Default Duration Test {datetime.now().strftime('%H:%M')}",
        description="Testing default cycle duration",
    )

    assert milestone is not None
    assert milestone.id is not None
    assert milestone.target_date is not None

    # Check that target date is roughly 2 weeks from now
    now = datetime.now(timezone.utc)
    target = milestone.target_date
    days_diff = (target - now).days

    assert 13 <= days_diff <= 15, f"Expected ~14 days, got {days_diff}"

    print(f"✅ Created milestone with default duration: {days_diff} days")

    # Cleanup
    await linear_adapter.milestone_delete(milestone.id)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_milestone_get_with_progress(linear_adapter):
    """Test milestone retrieval with progress calculation."""
    # Create a test milestone
    milestone = await linear_adapter.milestone_create(
        name=f"Progress Test {datetime.now().strftime('%H:%M')}",
        description="Testing progress calculation",
    )

    # Retrieve the milestone
    retrieved = await linear_adapter.milestone_get(milestone.id)

    assert retrieved is not None
    assert retrieved.id == milestone.id
    assert retrieved.name == milestone.name
    assert retrieved.total_issues >= 0
    assert retrieved.closed_issues >= 0
    assert 0 <= retrieved.progress_pct <= 100

    print(f"✅ Retrieved milestone: {retrieved.name}")
    print(f"   Progress: {retrieved.progress_pct:.1f}%")
    print(f"   Issues: {retrieved.closed_issues}/{retrieved.total_issues}")

    # Cleanup
    await linear_adapter.milestone_delete(milestone.id)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_milestone_list_with_filters(linear_adapter):
    """Test milestone listing with state filters."""
    # Create a test milestone
    milestone = await linear_adapter.milestone_create(
        name=f"List Test {datetime.now().strftime('%H:%M')}",
        description="Testing milestone listing",
    )

    # List all milestones
    all_milestones = await linear_adapter.milestone_list()
    assert len(all_milestones) > 0
    assert any(m.id == milestone.id for m in all_milestones)

    # List active milestones only
    active_milestones = await linear_adapter.milestone_list(state="active")
    print(f"✅ Listed {len(active_milestones)} active milestones")

    # List completed milestones only
    completed_milestones = await linear_adapter.milestone_list(state="completed")
    print(f"✅ Listed {len(completed_milestones)} completed milestones")

    # Cleanup
    await linear_adapter.milestone_delete(milestone.id)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_milestone_update(linear_adapter):
    """Test milestone property updates."""
    # Create a test milestone
    milestone = await linear_adapter.milestone_create(
        name=f"Update Test {datetime.now().strftime('%H:%M')}",
        description="Original description",
    )

    # Update name and description
    updated = await linear_adapter.milestone_update(
        milestone.id,
        name="Updated Milestone Name",
        description="Updated description",
    )

    assert updated is not None
    assert updated.name == "Updated Milestone Name"
    assert updated.description == "Updated description"

    print("✅ Updated milestone name and description")

    # Update target date
    new_target = datetime.now(timezone.utc) + timedelta(days=30)
    updated = await linear_adapter.milestone_update(
        milestone.id, target_date=new_target
    )

    assert updated is not None
    assert updated.target_date is not None
    target_diff = (updated.target_date - new_target).total_seconds()
    assert abs(target_diff) < 60, "Target date should be within 1 minute"

    print("✅ Updated milestone target date")

    # Cleanup
    await linear_adapter.milestone_delete(milestone.id)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_milestone_delete(linear_adapter):
    """Test milestone deletion (archiving)."""
    # Create a test milestone
    milestone = await linear_adapter.milestone_create(
        name=f"Delete Test {datetime.now().strftime('%H:%M')}",
        description="Testing deletion",
    )

    milestone_id = milestone.id

    # Delete the milestone
    success = await linear_adapter.milestone_delete(milestone_id)
    assert success is True

    # Verify it's no longer retrievable
    deleted = await linear_adapter.milestone_get(milestone_id)
    # Linear may still return archived cycles, so we just verify deletion succeeded
    assert deleted is None or deleted.state == "closed"

    print(f"✅ Successfully deleted (archived) milestone {milestone_id}")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_milestone_get_issues(linear_adapter):
    """Test retrieving issues from a milestone."""
    # Create a test milestone
    milestone = await linear_adapter.milestone_create(
        name=f"Issues Test {datetime.now().strftime('%H:%M')}",
        description="Testing issue retrieval",
    )

    # Get issues (may be empty for a new milestone)
    issues = await linear_adapter.milestone_get_issues(milestone.id)
    assert isinstance(issues, list)
    assert len(issues) >= 0

    print(f"✅ Retrieved {len(issues)} issues from milestone")

    # Cleanup
    await linear_adapter.milestone_delete(milestone.id)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_milestone_not_found(linear_adapter):
    """Test handling of non-existent milestone."""
    # Try to get a non-existent milestone
    milestone = await linear_adapter.milestone_get("non-existent-id-12345")
    assert milestone is None

    print("✅ Correctly handled non-existent milestone")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_milestone_state_transitions(linear_adapter):
    """Test milestone state transitions based on dates."""
    # Create a milestone that should be active
    now = datetime.now(timezone.utc)
    target_date = now + timedelta(days=7)

    milestone = await linear_adapter.milestone_create(
        name=f"State Test {datetime.now().strftime('%H:%M')}",
        description="Testing state transitions",
        target_date=target_date,
    )

    # Should be active (between start and end dates)
    assert milestone.state in ["active", "open"]

    print(f"✅ Milestone state: {milestone.state}")
    print(f"   Target date: {milestone.target_date}")

    # Cleanup
    await linear_adapter.milestone_delete(milestone.id)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cycle_to_milestone_conversion(linear_adapter):
    """Test that Linear Cycle data is correctly converted to Milestone model."""
    milestone = await linear_adapter.milestone_create(
        name=f"Conversion Test {datetime.now().strftime('%H:%M')}",
        description="Testing conversion logic",
        labels=["test", "conversion"],
    )

    # Verify all Milestone fields are populated
    assert milestone.id is not None
    assert milestone.name is not None
    assert milestone.state in ["open", "active", "completed", "closed"]
    assert milestone.target_date is not None
    assert isinstance(milestone.total_issues, int)
    assert isinstance(milestone.closed_issues, int)
    assert 0 <= milestone.progress_pct <= 100

    # Verify platform_data contains Linear-specific info
    assert "linear" in milestone.platform_data
    linear_data = milestone.platform_data["linear"]
    assert "cycle_id" in linear_data
    assert "starts_at" in linear_data
    assert "ends_at" in linear_data

    print("✅ Cycle to Milestone conversion successful")
    print(f"   Cycle ID: {linear_data['cycle_id']}")
    print(f"   State: {milestone.state}")
    print(f"   Progress: {milestone.progress_pct:.1f}%")

    # Cleanup
    await linear_adapter.milestone_delete(milestone.id)


if __name__ == "__main__":
    # Run tests manually for debugging
    print("Running Linear Milestone Integration Tests...\n")

    async def run_all_tests():
        """Run all tests sequentially."""
        adapter = None
        try:
            # Setup
            api_key = os.getenv("LINEAR_API_KEY")
            team_id = os.getenv("LINEAR_TEAM_ID")

            if not api_key or not team_id:
                print("❌ LINEAR_API_KEY and LINEAR_TEAM_ID must be set")
                return

            config = {"api_key": api_key, "team_id": team_id}
            adapter = AdapterRegistry.get_adapter("linear", config)
            await adapter.initialize()

            print("✅ Adapter initialized\n")

            # Run tests
            await test_milestone_create_with_target_date(adapter)
            await test_milestone_create_default_duration(adapter)
            await test_milestone_get_with_progress(adapter)
            await test_milestone_list_with_filters(adapter)
            await test_milestone_update(adapter)
            await test_milestone_delete(adapter)
            await test_milestone_get_issues(adapter)
            await test_milestone_not_found(adapter)
            await test_milestone_state_transitions(adapter)
            await test_cycle_to_milestone_conversion(adapter)

            print("\n✅ All tests passed!")

        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback

            traceback.print_exc()
        finally:
            if adapter:
                await adapter.close()

    asyncio.run(run_all_tests())
