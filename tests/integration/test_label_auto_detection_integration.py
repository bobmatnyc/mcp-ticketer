"""Integration tests for label auto-detection with Linear adapter.

This module tests the label auto-detection flow ensuring labels are correctly
detected and returned as names (not UUIDs).
"""

import pytest

from mcp_ticketer.mcp.server.tools.ticket_tools import detect_and_apply_labels


class MockAdapter:
    """Mock adapter with list_labels support."""

    def __init__(self, labels):
        self._labels = labels

    async def list_labels(self):
        return self._labels


@pytest.mark.asyncio
async def test_label_auto_detection_returns_names():
    """Test that auto-detection returns label names, not UUIDs."""
    labels = [
        {"id": "label-uuid-001", "name": "bug", "color": "#ff0000"},
        {"id": "label-uuid-002", "name": "feature", "color": "#00ff00"},
        {"id": "label-uuid-003", "name": "provider-management", "color": "#0000ff"},
        {"id": "label-uuid-004", "name": "filtering", "color": "#ffff00"},
        {"id": "label-uuid-005", "name": "security", "color": "#ff00ff"},
    ]
    adapter = MockAdapter(labels)

    title = "Fix bug in provider-management module"
    description = "Security issue with filtering"

    result = await detect_and_apply_labels(
        adapter, title, description, existing_labels=[]
    )

    # Should return names only
    assert "bug" in result
    assert "provider-management" in result
    assert "security" in result
    assert "filtering" in result

    # Should NOT return UUIDs
    assert "label-uuid-001" not in result
    assert "label-uuid-002" not in result
    assert "label-uuid-003" not in result


@pytest.mark.asyncio
async def test_label_detection_with_mixed_formats():
    """Test label detection works with both dict and string label formats."""
    # Test with dict format (typical for Linear/Jira)
    dict_labels = [
        {"id": "uuid-1", "name": "bug"},
        {"id": "uuid-2", "name": "feature"},
    ]
    adapter_dict = MockAdapter(dict_labels)

    result_dict = await detect_and_apply_labels(
        adapter_dict, "Fix bug in feature", "", existing_labels=[]
    )

    assert "bug" in result_dict
    assert "feature" in result_dict
    assert "uuid-1" not in result_dict
    assert "uuid-2" not in result_dict

    # Test with string format (typical for simple adapters)
    string_labels = ["bug", "feature", "enhancement"]
    adapter_string = MockAdapter(string_labels)

    result_string = await detect_and_apply_labels(
        adapter_string, "Add feature enhancement", "", existing_labels=[]
    )

    assert "feature" in result_string
    assert "enhancement" in result_string


@pytest.mark.asyncio
async def test_label_detection_combines_user_and_auto():
    """Test that user-provided labels are combined with auto-detected ones."""
    labels = [
        {"id": "uuid-1", "name": "bug"},
        {"id": "uuid-2", "name": "critical"},
    ]
    adapter = MockAdapter(labels)

    result = await detect_and_apply_labels(
        adapter, "Fix critical bug", "", existing_labels=["custom-tag", "team-alpha"]
    )

    # Should have both auto-detected and user-provided
    assert "bug" in result
    assert "critical" in result
    assert "custom-tag" in result
    assert "team-alpha" in result

    # Should not have UUIDs
    assert "uuid-1" not in result
    assert "uuid-2" not in result
