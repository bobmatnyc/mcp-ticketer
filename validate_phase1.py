#!/usr/bin/env python3
"""Validation script for Phase 1 milestone support implementation.

This script validates that all Phase 1 deliverables are properly implemented:
1. Milestone model exists and validates correctly
2. BaseAdapter has milestone methods
3. MilestoneManager handles local storage
4. All components are properly exported

"""

import sys
from datetime import datetime
from pathlib import Path
import tempfile

# Test 1: Import all components
print("✓ Test 1: Importing components...")
try:
    from mcp_ticketer.core import Milestone, MilestoneManager, BaseAdapter
    print("  ✓ All imports successful")
except ImportError as e:
    print(f"  ✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Validate Milestone model
print("\n✓ Test 2: Validating Milestone model...")
try:
    milestone = Milestone(
        id="test-001",
        name="Test Milestone",
        target_date=datetime(2025, 12, 31),
        state="open",
        description="Test milestone for validation",
        labels=["test", "validation"],
        project_id="proj-123",
        total_issues=10,
        closed_issues=5,
        progress_pct=50.0
    )
    assert milestone.id == "test-001"
    assert milestone.name == "Test Milestone"
    assert len(milestone.labels) == 2
    assert milestone.progress_pct == 50.0
    print("  ✓ Milestone model validates correctly")
except Exception as e:
    print(f"  ✗ Milestone validation failed: {e}")
    sys.exit(1)

# Test 3: Validate MilestoneManager
print("\n✓ Test 3: Validating MilestoneManager...")
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".mcp-ticketer"
        manager = MilestoneManager(config_dir)

        # Test save
        saved = manager.save_milestone(milestone)
        assert saved.id == milestone.id
        print("  ✓ Save milestone works")

        # Test get
        retrieved = manager.get_milestone("test-001")
        assert retrieved is not None
        assert retrieved.name == "Test Milestone"
        print("  ✓ Get milestone works")

        # Test list
        milestones = manager.list_milestones()
        assert len(milestones) == 1
        print("  ✓ List milestones works")

        # Test delete
        deleted = manager.delete_milestone("test-001")
        assert deleted is True
        assert manager.get_milestone("test-001") is None
        print("  ✓ Delete milestone works")

except Exception as e:
    print(f"  ✗ MilestoneManager validation failed: {e}")
    sys.exit(1)

# Test 4: Validate BaseAdapter has milestone methods
print("\n✓ Test 4: Validating BaseAdapter milestone methods...")
try:
    milestone_methods = [
        "milestone_create",
        "milestone_get",
        "milestone_list",
        "milestone_update",
        "milestone_delete",
        "milestone_get_issues"
    ]

    for method in milestone_methods:
        assert hasattr(BaseAdapter, method), f"Missing method: {method}"
        assert callable(getattr(BaseAdapter, method)), f"Not callable: {method}"

    print(f"  ✓ All {len(milestone_methods)} milestone methods present")
except Exception as e:
    print(f"  ✗ BaseAdapter validation failed: {e}")
    sys.exit(1)

# Test 5: Validate model serialization
print("\n✓ Test 5: Validating model serialization...")
try:
    milestone = Milestone(
        name="Serialization Test",
        target_date=datetime(2025, 6, 30),
        labels=["test"]
    )

    # Test JSON serialization
    json_data = milestone.model_dump_json()
    assert isinstance(json_data, str)
    assert "Serialization Test" in json_data
    print("  ✓ JSON serialization works")

    # Test dict serialization
    dict_data = milestone.model_dump(mode="json")
    assert isinstance(dict_data, dict)
    assert dict_data["name"] == "Serialization Test"
    print("  ✓ Dict serialization works")

except Exception as e:
    print(f"  ✗ Serialization validation failed: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("✓ ALL PHASE 1 VALIDATIONS PASSED!")
print("="*60)
print("\nPhase 1 Implementation Summary:")
print("  • Milestone data model: COMPLETE")
print("  • BaseAdapter milestone methods: COMPLETE")
print("  • MilestoneManager local storage: COMPLETE")
print("  • Component exports: COMPLETE")
print("  • Type safety: VALIDATED")
print("\nNext: Phase 2 - Linear Adapter Implementation")
