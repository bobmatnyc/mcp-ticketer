"""Tests for label auto-detection limits and hierarchical label filtering.

This module tests the bug fixes for Issue #56:
1. max_auto_labels parameter limits the number of auto-detected labels
2. Hierarchical labels (with "/") are filtered unless exact match
"""

import pytest

from mcp_ticketer.mcp.server.tools.ticket_tools import detect_and_apply_labels

# Use anyio backend for async tests (compatible with project setup)
pytestmark = pytest.mark.anyio


class MockAdapter:
    """Mock adapter for testing label detection."""

    def __init__(self, labels):
        self._labels = labels

    async def list_labels(self):
        return self._labels


async def test_max_auto_labels_default():
    """Test that max_auto_labels defaults to 4."""
    content_title = "Fix critical security bug"
    content_description = "This is a high-priority bug with security implications"

    # Create labels that will all match
    available_labels = [
        {"id": "1", "name": "bug"},
        {"id": "2", "name": "critical"},
        {"id": "3", "name": "security"},
        {"id": "4", "name": "high-priority"},
        {"id": "5", "name": "fix"},  # This should match "fix" in title
    ]
    adapter = MockAdapter(available_labels)

    # Should default to max 4 auto-detected labels
    result = await detect_and_apply_labels(
        adapter, content_title, content_description, existing_labels=[]
    )

    # Should have exactly 4 labels (default limit)
    assert len(result) == 4
    # Should include the first 4 matched labels
    assert all(
        label in ["bug", "critical", "security", "high-priority", "fix"]
        for label in result
    )


async def test_max_auto_labels_explicit_limit():
    """Test that max_auto_labels parameter limits auto-detected labels."""
    content_title = "Fix critical security bug"
    content_description = "This is a high-priority bug with security implications"

    available_labels = [
        {"id": "1", "name": "bug"},
        {"id": "2", "name": "critical"},
        {"id": "3", "name": "security"},
        {"id": "4", "name": "high-priority"},
        {"id": "5", "name": "fix"},
    ]
    adapter = MockAdapter(available_labels)

    # Set explicit limit of 2
    result = await detect_and_apply_labels(
        adapter,
        content_title,
        content_description,
        existing_labels=[],
        max_auto_labels=2,
    )

    # Should have exactly 2 labels
    assert len(result) == 2


async def test_max_auto_labels_does_not_limit_user_labels():
    """Test that max_auto_labels only limits auto-detected, not user-specified labels."""
    content_title = "Fix bug"
    content_description = "Critical security issue"

    available_labels = [
        {"id": "1", "name": "bug"},
        {"id": "2", "name": "critical"},
        {"id": "3", "name": "security"},
    ]
    adapter = MockAdapter(available_labels)

    # User provides 3 labels + 3 auto-detected, but max_auto_labels=2
    user_labels = ["user-tag-1", "user-tag-2", "user-tag-3"]
    result = await detect_and_apply_labels(
        adapter,
        content_title,
        content_description,
        existing_labels=user_labels,
        max_auto_labels=2,
    )

    # Should have all 3 user labels + max 2 auto-detected = 5 total
    assert len(result) == 5
    # All user labels should be preserved
    assert all(tag in result for tag in user_labels)


async def test_hierarchical_labels_filtered_unless_exact_match():
    """Test that hierarchical labels (with '/') are filtered unless exact match."""
    content_title = "Add test for authentication"
    content_description = "Testing the auth module"

    # Mix of hierarchical and non-hierarchical labels
    available_labels = [
        {"id": "1", "name": "test"},  # Should match
        {
            "id": "2",
            "name": "Test Suite/Unit Tests",
        },  # Should NOT match (has "/" and not exact)
        {"id": "3", "name": "Test Suite/Integration Tests"},  # Should NOT match
        {"id": "4", "name": "Test Suite/Authentication"},  # Should NOT match
        {"id": "5", "name": "authentication"},  # Should match
        {"id": "6", "name": "Feature/Auth/OAuth"},  # Should NOT match
    ]
    adapter = MockAdapter(available_labels)

    result = await detect_and_apply_labels(
        adapter, content_title, content_description, existing_labels=[]
    )

    # Should only include non-hierarchical labels
    assert "test" in result
    assert "authentication" in result
    # Hierarchical labels should be filtered out
    assert "Test Suite/Unit Tests" not in result
    assert "Test Suite/Integration Tests" not in result
    assert "Test Suite/Authentication" not in result
    assert "Feature/Auth/OAuth" not in result


async def test_hierarchical_labels_exact_match_included():
    """Test that hierarchical labels ARE included if exact match in content."""
    content_title = "Fix Test Suite/Authentication"
    content_description = "Broken test suite/authentication module"

    available_labels = [
        {
            "id": "1",
            "name": "Test Suite/Authentication",
        },  # Should match (exact in title)
        {"id": "2", "name": "Test Suite/Unit Tests"},  # Should NOT match
        {"id": "3", "name": "authentication"},  # Should match
    ]
    adapter = MockAdapter(available_labels)

    result = await detect_and_apply_labels(
        adapter, content_title, content_description, existing_labels=[]
    )

    # Exact match hierarchical label should be included
    assert "Test Suite/Authentication" in result
    # Partial match hierarchical label should NOT be included
    assert "Test Suite/Unit Tests" not in result
    # Non-hierarchical should match
    assert "authentication" in result


async def test_hierarchical_labels_case_insensitive_exact_match():
    """Test that hierarchical exact match is case-insensitive."""
    content_title = "Fix test suite/authentication"
    content_description = ""

    available_labels = [
        {
            "id": "1",
            "name": "Test Suite/Authentication",
        },  # Should match (case-insensitive exact)
        {"id": "2", "name": "Test Suite/Integration"},  # Should NOT match
    ]
    adapter = MockAdapter(available_labels)

    result = await detect_and_apply_labels(
        adapter, content_title, content_description, existing_labels=[]
    )

    # Case-insensitive exact match should work
    assert "Test Suite/Authentication" in result
    assert "Test Suite/Integration" not in result


async def test_max_auto_labels_zero():
    """Test that max_auto_labels=0 disables auto-detection."""
    content_title = "Fix critical bug"
    content_description = "Security issue"

    available_labels = [
        {"id": "1", "name": "bug"},
        {"id": "2", "name": "critical"},
        {"id": "3", "name": "security"},
    ]
    adapter = MockAdapter(available_labels)

    result = await detect_and_apply_labels(
        adapter,
        content_title,
        content_description,
        existing_labels=[],
        max_auto_labels=0,
    )

    # Should have no auto-detected labels
    assert len(result) == 0


async def test_max_auto_labels_with_user_labels():
    """Test max_auto_labels=0 still preserves user labels."""
    content_title = "Fix critical bug"
    content_description = "Security issue"

    available_labels = [
        {"id": "1", "name": "bug"},
        {"id": "2", "name": "critical"},
    ]
    adapter = MockAdapter(available_labels)

    user_labels = ["my-custom-tag"]
    result = await detect_and_apply_labels(
        adapter,
        content_title,
        content_description,
        existing_labels=user_labels,
        max_auto_labels=0,
    )

    # Should have user label but no auto-detected
    assert len(result) == 1
    assert "my-custom-tag" in result


async def test_combined_hierarchical_filter_and_max_labels():
    """Test that both hierarchical filtering AND max_auto_labels work together."""
    content_title = "test bug fix"
    content_description = "critical security feature"

    available_labels = [
        {"id": "1", "name": "bug"},
        {
            "id": "2",
            "name": "Test Suite/Unit",
        },  # Filtered (hierarchical, no exact match)
        {"id": "3", "name": "critical"},
        {
            "id": "4",
            "name": "Feature/Security",
        },  # Filtered (hierarchical, no exact match)
        {"id": "5", "name": "security"},
        {"id": "6", "name": "test"},
        {"id": "7", "name": "feature"},
    ]
    adapter = MockAdapter(available_labels)

    # Set max to 3, but hierarchical labels should already be filtered
    result = await detect_and_apply_labels(
        adapter,
        content_title,
        content_description,
        existing_labels=[],
        max_auto_labels=3,
    )

    # Should have max 3 non-hierarchical labels
    assert len(result) == 3
    # No hierarchical labels should be included
    assert "Test Suite/Unit" not in result
    assert "Feature/Security" not in result
    # Only non-hierarchical labels
    assert all("/" not in label for label in result)


async def test_string_format_labels_with_hierarchy():
    """Test hierarchical filtering with string format labels (not dicts)."""
    content_title = "test feature"
    content_description = ""

    # String format labels (some with hierarchy)
    available_labels = [
        "test",
        "Feature/Backend",  # Should be filtered
        "bug",
    ]
    adapter = MockAdapter(available_labels)

    result = await detect_and_apply_labels(
        adapter, content_title, content_description, existing_labels=[]
    )

    # Should only match non-hierarchical
    assert "test" in result
    assert "Feature/Backend" not in result


async def test_backward_compatibility_no_max_param():
    """Test that existing code works without max_auto_labels parameter (backward compat)."""
    content_title = "Fix bug"
    content_description = ""

    available_labels = [
        {"id": "1", "name": "bug"},
        {"id": "2", "name": "fix"},
    ]
    adapter = MockAdapter(available_labels)

    # Old code calling without max_auto_labels parameter should use default (4)
    result = await detect_and_apply_labels(
        adapter,
        content_title,
        content_description,
        existing_labels=[],
        # No max_auto_labels parameter - should use default
    )

    # Should work with default limit
    assert len(result) <= 4
    assert "bug" in result
