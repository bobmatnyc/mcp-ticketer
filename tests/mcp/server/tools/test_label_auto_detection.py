"""Tests for label auto-detection functionality.

This module tests the detect_and_apply_labels function to ensure it correctly
returns label names instead of UUIDs when auto-detecting labels from ticket content.
"""

import pytest

from mcp_ticketer.mcp.server.tools.ticket_tools import detect_and_apply_labels


class MockAdapter:
    """Mock adapter for testing label detection."""

    def __init__(self, labels):
        self._labels = labels

    async def list_labels(self):
        return self._labels


@pytest.mark.asyncio
async def test_detect_labels_uses_names_not_uuids():
    """Test that auto-detection returns label names, not UUIDs."""
    content_title = "This is about provider-management"
    content_description = "We need better filtering capabilities"
    available_labels = [
        {"id": "uuid-123", "name": "provider-management"},
        {"id": "uuid-456", "name": "filtering"},
        {"id": "uuid-789", "name": "unrelated"},
    ]
    adapter = MockAdapter(available_labels)

    result = await detect_and_apply_labels(
        adapter, content_title, content_description, existing_labels=[]
    )

    # Should return names, not UUIDs
    assert "provider-management" in result
    assert "filtering" in result
    assert "uuid-123" not in result  # Should NOT include UUID
    assert "uuid-456" not in result  # Should NOT include UUID
    assert "uuid-789" not in result  # Unrelated should not match


@pytest.mark.asyncio
async def test_detect_labels_with_string_format():
    """Test label detection when labels are strings (not dicts)."""
    content_title = "This needs the bug label"
    content_description = ""
    available_labels = ["bug", "feature", "enhancement"]
    adapter = MockAdapter(available_labels)

    result = await detect_and_apply_labels(
        adapter, content_title, content_description, existing_labels=[]
    )

    assert "bug" in result
    assert "feature" not in result
    assert "enhancement" not in result


@pytest.mark.asyncio
async def test_detect_labels_preserves_user_tags():
    """Test that user-specified tags are preserved and combined with auto-detected."""
    content_title = "This is about provider-management"
    content_description = ""
    available_labels = [{"id": "uuid-123", "name": "provider-management"}]
    adapter = MockAdapter(available_labels)
    user_tags = ["custom-tag", "another-tag"]

    result = await detect_and_apply_labels(
        adapter, content_title, content_description, existing_labels=user_tags
    )

    # User tags should be preserved
    assert "custom-tag" in result
    assert "another-tag" in result
    # Auto-detected should be added
    assert "provider-management" in result
    # Should not have duplicates
    assert len(result) == 3


@pytest.mark.asyncio
async def test_detect_labels_keyword_matching():
    """Test that keyword-based label detection works correctly."""
    content_title = "Fix critical bug in authentication"
    content_description = "This is a security vulnerability"
    available_labels = [
        {"id": "uuid-bug", "name": "bug"},
        {"id": "uuid-critical", "name": "critical"},
        {"id": "uuid-security", "name": "security"},
        {"id": "uuid-feature", "name": "feature"},
    ]
    adapter = MockAdapter(available_labels)

    result = await detect_and_apply_labels(
        adapter, content_title, content_description, existing_labels=[]
    )

    # Should match based on keywords
    assert "bug" in result
    assert "critical" in result
    assert "security" in result
    # Should not match unrelated
    assert "feature" not in result


@pytest.mark.asyncio
async def test_detect_labels_case_insensitive():
    """Test that label detection is case-insensitive."""
    content_title = "PROVIDER-MANAGEMENT issue"
    content_description = "FILTERING required"
    available_labels = [
        {"id": "uuid-1", "name": "provider-management"},
        {"id": "uuid-2", "name": "filtering"},
    ]
    adapter = MockAdapter(available_labels)

    result = await detect_and_apply_labels(
        adapter, content_title, content_description, existing_labels=[]
    )

    assert "provider-management" in result
    assert "filtering" in result


@pytest.mark.asyncio
async def test_detect_labels_no_duplicates():
    """Test that duplicate labels are not added."""
    content_title = "bug bug bug"
    content_description = "Another bug mention"
    available_labels = [{"id": "uuid-bug", "name": "bug"}]
    adapter = MockAdapter(available_labels)

    result = await detect_and_apply_labels(
        adapter, content_title, content_description, existing_labels=[]
    )

    # Should only have one instance of "bug"
    assert result.count("bug") == 1


@pytest.mark.asyncio
async def test_detect_labels_handles_empty_labels():
    """Test that function handles empty label list gracefully."""
    content_title = "Some ticket title"
    content_description = "Some description"
    available_labels = []
    adapter = MockAdapter(available_labels)
    user_tags = ["user-tag"]

    result = await detect_and_apply_labels(
        adapter, content_title, content_description, existing_labels=user_tags
    )

    # Should only have user tags
    assert result == ["user-tag"]


@pytest.mark.asyncio
async def test_detect_labels_adapter_without_list_labels():
    """Test that function handles adapters without list_labels method."""

    class AdapterWithoutLabels:
        """Mock adapter without label support."""

        pass

    content_title = "Some ticket"
    content_description = "Description"
    adapter = AdapterWithoutLabels()
    user_tags = ["user-tag"]

    result = await detect_and_apply_labels(
        adapter, content_title, content_description, existing_labels=user_tags
    )

    # Should return only user tags when adapter doesn't support labels
    assert result == ["user-tag"]
