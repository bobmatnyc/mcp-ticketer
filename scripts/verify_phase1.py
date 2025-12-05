#!/usr/bin/env python3
"""Verification script for Phase 1: Unified Projects Foundation.

This script demonstrates and verifies all Phase 1 functionality:
- Project model creation and validation
- ProjectStatistics calculation
- Epic to Project conversion
- Project to Epic conversion
- Round-trip conversion integrity
- State mapping correctness

Run with: PYTHONPATH=./src python3 scripts/verify_phase1.py
"""

from datetime import datetime, timezone

from mcp_ticketer.core.models import (
    Epic,
    Priority,
    Project,
    ProjectScope,
    ProjectState,
    ProjectStatistics,
    ProjectVisibility,
    TicketState,
)
from mcp_ticketer.core.project_utils import (
    epic_to_project,
    project_to_epic,
)


def test_project_creation():
    """Test Project model creation and validation."""
    print("\n" + "=" * 60)
    print("TEST 1: Project Creation and Validation")
    print("=" * 60)

    # Minimal project
    minimal = Project(
        id="proj-min",
        platform="linear",
        platform_id="abc123",
        scope=ProjectScope.TEAM,
        name="Minimal Project",
    )
    print(f"✓ Created minimal project: {minimal.name}")
    print(f"  - State: {minimal.state} (default)")
    print(f"  - Visibility: {minimal.visibility} (default)")

    # Full project
    full = Project(
        id="proj-full",
        platform="github",
        platform_id="GH_kwDO123",
        scope=ProjectScope.ORGANIZATION,
        name="Full Featured Project",
        description="A comprehensive project",
        state=ProjectState.ACTIVE,
        visibility=ProjectVisibility.PUBLIC,
        url="https://github.com/orgs/acme/projects/42",
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        owner_id="user-123",
        owner_name="Alice Developer",
        team_id="team-eng",
        team_name="Engineering",
        child_issues=["issue-1", "issue-2", "issue-3"],
        issue_count=10,
        completed_count=7,
        in_progress_count=2,
        extra_data={"priority": "high", "custom_field": "value"},
    )
    print(f"✓ Created full project: {full.name}")
    print(f"  - Platform: {full.platform}")
    print(f"  - State: {full.state}")
    print(f"  - Owner: {full.owner_name}")
    print(f"  - Team: {full.team_name}")
    print(f"  - Issues: {len(full.child_issues)} child issues")
    print(f"  - Extra data: {list(full.extra_data.keys())}")


def test_progress_calculation():
    """Test progress calculation from issue counts."""
    print("\n" + "=" * 60)
    print("TEST 2: Progress Calculation")
    print("=" * 60)

    test_cases = [
        (10, 7, 70.0, "Partial completion"),
        (20, 20, 100.0, "All completed"),
        (0, 0, 0.0, "No issues"),
        (30, 10, 33.33, "One third complete"),
    ]

    for total, completed, expected, description in test_cases:
        project = Project(
            id=f"proj-{total}-{completed}",
            platform="linear",
            platform_id="test",
            scope=ProjectScope.TEAM,
            name="Test Project",
            issue_count=total,
            completed_count=completed,
        )
        progress = project.calculate_progress()
        status = "✓" if abs(progress - expected) < 0.01 else "✗"
        print(f"{status} {description}: {progress:.2f}% (expected {expected}%)")
        assert abs(progress - expected) < 0.01, f"Expected {expected}, got {progress}"


def test_project_statistics():
    """Test ProjectStatistics model."""
    print("\n" + "=" * 60)
    print("TEST 3: Project Statistics")
    print("=" * 60)

    stats = ProjectStatistics(
        project_id="proj-123",
        total_issues=50,
        completed_issues=30,
        in_progress_issues=15,
        open_issues=5,
        blocked_issues=2,
        progress_percentage=60.0,
        velocity=8.5,
        estimated_completion=datetime(2025, 12, 31, tzinfo=timezone.utc),
    )

    print(f"✓ Created statistics for project: {stats.project_id}")
    print(f"  - Total issues: {stats.total_issues}")
    print(f"  - Completed: {stats.completed_issues} ({stats.progress_percentage}%)")
    print(f"  - In progress: {stats.in_progress_issues}")
    print(f"  - Open: {stats.open_issues}")
    print(f"  - Blocked: {stats.blocked_issues}")
    print(f"  - Velocity: {stats.velocity} issues/week")


def test_epic_to_project_conversion():
    """Test Epic to Project conversion."""
    print("\n" + "=" * 60)
    print("TEST 4: Epic to Project Conversion")
    print("=" * 60)

    # Create epic
    epic = Epic(
        id="epic-123",
        title="User Authentication System",
        description="Complete overhaul of authentication",
        state=TicketState.IN_PROGRESS,
        priority=Priority.HIGH,
        tags=["feature", "security"],
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        child_issues=["issue-1", "issue-2", "issue-3"],
        metadata={
            "platform": "linear",
            "url": "https://linear.app/team/epic/123",
            "team_id": "team-eng",
        },
    )

    print(f"Epic: {epic.title}")
    print(f"  - State: {epic.state}")
    print(f"  - Priority: {epic.priority}")
    print(f"  - Tags: {', '.join(epic.tags)}")
    print(f"  - Child issues: {len(epic.child_issues)}")

    # Convert to project
    project = epic_to_project(epic)

    print(f"\n✓ Converted to Project: {project.name}")
    print(f"  - State: {project.state} (mapped from {epic.state})")
    print(f"  - Scope: {project.scope} (default TEAM)")
    print(f"  - Platform: {project.platform}")
    print(f"  - Child issues: {len(project.child_issues)} (preserved)")
    print(f"  - Extra data: {list(project.extra_data.keys())}")

    # Verify field mappings
    assert project.name == epic.title
    assert project.description == epic.description
    assert project.created_at == epic.created_at
    assert project.child_issues == epic.child_issues
    assert project.platform == "linear"
    # Note: Pydantic serializes enums to strings with use_enum_values=True
    assert project.state == "active" or project.state == ProjectState.ACTIVE


def test_project_to_epic_conversion():
    """Test Project to Epic conversion."""
    print("\n" + "=" * 60)
    print("TEST 5: Project to Epic Conversion")
    print("=" * 60)

    # Create project
    project = Project(
        id="proj-456",
        platform="github",
        platform_id="GH_kwDO456",
        scope=ProjectScope.ORGANIZATION,
        name="API Redesign",
        description="RESTful API v2.0",
        state=ProjectState.ACTIVE,
        visibility=ProjectVisibility.PUBLIC,
        url="https://github.com/orgs/acme/projects/1",
        created_at=datetime(2025, 2, 1, tzinfo=timezone.utc),
        owner_id="user-alice",
        owner_name="Alice Developer",
        team_id="team-backend",
        team_name="Backend Team",
        child_issues=["issue-10", "issue-20"],
        extra_data={"sprint": "Q1-2025", "priority": "high"},
    )

    print(f"Project: {project.name}")
    print(f"  - Platform: {project.platform}")
    print(f"  - State: {project.state}")
    print(f"  - Scope: {project.scope}")
    print(f"  - Owner: {project.owner_name}")
    print(f"  - Team: {project.team_name}")

    # Convert to epic
    epic = project_to_epic(project)

    print(f"\n✓ Converted to Epic: {epic.title}")
    print(f"  - State: {epic.state} (mapped from {project.state})")
    print(f"  - Child issues: {len(epic.child_issues)} (preserved)")
    print(f"  - Metadata platform: {epic.metadata['platform']}")
    print(f"  - Metadata URL: {epic.metadata['url']}")
    print(f"  - Project data keys: {list(epic.metadata['project_data'].keys())}")

    # Verify field mappings
    assert epic.title == project.name
    assert epic.description == project.description
    assert epic.created_at == project.created_at
    assert epic.child_issues == project.child_issues
    # Note: Pydantic serializes enums to strings with use_enum_values=True
    assert epic.state == "in_progress" or epic.state == TicketState.IN_PROGRESS
    assert epic.metadata["platform"] == "github"
    assert epic.metadata["project_data"]["owner_name"] == "Alice Developer"


def test_round_trip_conversion():
    """Test round-trip conversion preserves data."""
    print("\n" + "=" * 60)
    print("TEST 6: Round-Trip Conversion")
    print("=" * 60)

    # Original epic
    original = Epic(
        id="epic-roundtrip",
        title="Round Trip Test",
        description="Testing data preservation",
        created_at=datetime(2025, 3, 1, tzinfo=timezone.utc),
        child_issues=["issue-a", "issue-b", "issue-c"],
        metadata={
            "platform": "jira",
            "custom_field": "custom_value",
            "nested": {"key": "value"},
        },
    )

    print(f"Original Epic: {original.title}")
    print(f"  - ID: {original.id}")
    print(f"  - Child issues: {len(original.child_issues)}")
    print(f"  - Metadata keys: {list(original.metadata.keys())}")

    # Convert Epic -> Project -> Epic
    project = epic_to_project(original)
    final = project_to_epic(project)

    print(f"\n✓ Round-trip complete:")
    print(f"  - Title preserved: {final.title == original.title}")
    print(f"  - ID preserved: {final.id == original.id}")
    print(f"  - Child issues preserved: {final.child_issues == original.child_issues}")
    print(f"  - Metadata preserved: {'custom_field' in final.metadata}")

    # Verify data integrity
    assert final.id == original.id
    assert final.title == original.title
    assert final.description == original.description
    assert final.child_issues == original.child_issues
    assert final.metadata["platform"] == "jira"
    assert final.metadata["custom_field"] == "custom_value"


def test_state_mappings():
    """Test all state mapping combinations."""
    print("\n" + "=" * 60)
    print("TEST 7: State Mappings")
    print("=" * 60)

    print("\nProjectState -> TicketState mappings:")
    state_mappings = [
        (ProjectState.PLANNED, TicketState.OPEN),
        (ProjectState.ACTIVE, TicketState.IN_PROGRESS),
        (ProjectState.COMPLETED, TicketState.DONE),
        (ProjectState.ARCHIVED, TicketState.CLOSED),
        (ProjectState.CANCELLED, TicketState.CLOSED),
    ]

    for project_state, expected_ticket_state in state_mappings:
        project = Project(
            id="test",
            platform="test",
            platform_id="test",
            scope=ProjectScope.TEAM,
            name="Test",
            state=project_state,
        )
        epic = project_to_epic(project)
        # Note: Pydantic serializes enums to strings with use_enum_values=True
        expected_str = expected_ticket_state.value if hasattr(expected_ticket_state, 'value') else expected_ticket_state
        actual_str = epic.state.value if hasattr(epic.state, 'value') else epic.state
        status = "✓" if actual_str == expected_str else "✗"
        proj_state_str = project_state.value if hasattr(project_state, 'value') else project_state
        print(f"{status} {proj_state_str:12} -> {actual_str:12} (expected {expected_str})")
        assert actual_str == expected_str


def test_json_serialization():
    """Test JSON serialization and deserialization."""
    print("\n" + "=" * 60)
    print("TEST 8: JSON Serialization")
    print("=" * 60)

    # Create project
    original = Project(
        id="proj-json",
        platform="linear",
        platform_id="abc123",
        scope=ProjectScope.TEAM,
        name="JSON Test Project",
        state=ProjectState.ACTIVE,
        issue_count=10,
        completed_count=5,
        extra_data={"custom": "data"},
    )

    # Serialize to JSON
    json_str = original.model_dump_json()
    print(f"✓ Serialized to JSON ({len(json_str)} bytes)")

    # Deserialize from JSON
    reconstructed = Project.model_validate_json(json_str)
    print(f"✓ Deserialized from JSON")

    # Verify integrity
    assert reconstructed.id == original.id
    assert reconstructed.name == original.name
    assert reconstructed.state == original.state
    assert reconstructed.issue_count == original.issue_count
    assert reconstructed.extra_data == original.extra_data

    print("  - All fields preserved correctly")


def main():
    """Run all verification tests."""
    print("\n" + "=" * 60)
    print("PHASE 1 VERIFICATION: Unified Projects Foundation")
    print("=" * 60)

    try:
        test_project_creation()
        test_progress_calculation()
        test_project_statistics()
        test_epic_to_project_conversion()
        test_project_to_epic_conversion()
        test_round_trip_conversion()
        test_state_mappings()
        test_json_serialization()

        print("\n" + "=" * 60)
        print("✅ ALL VERIFICATION TESTS PASSED")
        print("=" * 60)
        print("\nPhase 1 implementation is complete and verified!")
        print("Ready for Phase 2: GitHub Projects V2 Adapter\n")

    except AssertionError as e:
        print("\n" + "=" * 60)
        print("❌ VERIFICATION FAILED")
        print("=" * 60)
        print(f"\nError: {e}\n")
        raise


if __name__ == "__main__":
    main()
