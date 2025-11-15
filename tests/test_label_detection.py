"""Tests for automatic label/tag detection functionality."""

import pytest

from mcp_ticketer.mcp.server.tools.ticket_tools import detect_and_apply_labels


class MockAdapter:
    """Mock adapter for testing label detection."""

    def __init__(self, labels: list[dict[str, str]]):
        """Initialize mock adapter with labels.

        Args:
            labels: List of label dicts with 'id' and 'name' keys

        """
        self.labels = labels

    async def list_labels(self) -> list[dict[str, str]]:
        """Return mock labels."""
        return self.labels


class MockAdapterNoLabels:
    """Mock adapter that doesn't support labels."""

    pass


@pytest.mark.asyncio
async def test_detect_labels_bug_keyword():
    """Test detection of bug-related labels."""
    adapter = MockAdapter(
        [
            {"id": "bug", "name": "bug"},
            {"id": "feature", "name": "feature"},
            {"id": "docs", "name": "documentation"},
        ]
    )

    labels = await detect_and_apply_labels(
        adapter, "Fix crash when opening file", "The app crashes unexpectedly"
    )

    assert "bug" in labels


@pytest.mark.asyncio
async def test_detect_labels_feature_keyword():
    """Test detection of feature-related labels."""
    adapter = MockAdapter(
        [
            {"id": "bug", "name": "bug"},
            {"id": "feature", "name": "feature"},
            {"id": "enhancement", "name": "enhancement"},
        ]
    )

    labels = await detect_and_apply_labels(
        adapter, "Add dark mode support", "Implement dark mode feature for UI"
    )

    assert "feature" in labels


@pytest.mark.asyncio
async def test_detect_labels_improvement_keyword():
    """Test detection of improvement-related labels."""
    adapter = MockAdapter(
        [
            {"id": "improvement", "name": "improvement"},
            {"id": "enhancement", "name": "enhancement"},
            {"id": "bug", "name": "bug"},
        ]
    )

    labels = await detect_and_apply_labels(
        adapter, "Optimize database queries", "Improve performance of slow queries"
    )

    assert "improvement" in labels or "enhancement" in labels


@pytest.mark.asyncio
async def test_detect_labels_performance_keyword():
    """Test detection of performance-related labels."""
    adapter = MockAdapter(
        [
            {"id": "perf", "name": "performance"},
            {"id": "bug", "name": "bug"},
        ]
    )

    labels = await detect_and_apply_labels(
        adapter, "Speed up loading time", "The page is loading very slow"
    )

    assert "perf" in labels


@pytest.mark.asyncio
async def test_detect_labels_security_keyword():
    """Test detection of security-related labels."""
    adapter = MockAdapter(
        [
            {"id": "sec", "name": "security"},
            {"id": "bug", "name": "bug"},
        ]
    )

    labels = await detect_and_apply_labels(
        adapter, "Fix authentication vulnerability", "Security issue with auth"
    )

    assert "sec" in labels


@pytest.mark.asyncio
async def test_detect_labels_documentation_keyword():
    """Test detection of documentation-related labels."""
    adapter = MockAdapter(
        [
            {"id": "docs", "name": "documentation"},
            {"id": "feature", "name": "feature"},
        ]
    )

    labels = await detect_and_apply_labels(
        adapter, "Update README", "Add documentation for new API"
    )

    assert "docs" in labels


@pytest.mark.asyncio
async def test_detect_labels_direct_match():
    """Test direct label name match in content."""
    adapter = MockAdapter(
        [
            {"id": "critical", "name": "critical"},
            {"id": "bug", "name": "bug"},
        ]
    )

    labels = await detect_and_apply_labels(
        adapter, "Critical bug in payment system", "This is a critical issue"
    )

    assert "critical" in labels
    assert "bug" in labels


@pytest.mark.asyncio
async def test_detect_labels_multiple_matches():
    """Test detection of multiple relevant labels."""
    adapter = MockAdapter(
        [
            {"id": "bug", "name": "bug"},
            {"id": "security", "name": "security"},
            {"id": "critical", "name": "critical"},
        ]
    )

    labels = await detect_and_apply_labels(
        adapter,
        "Fix critical security bug",
        "Security vulnerability causing crashes",
    )

    assert "bug" in labels
    assert "security" in labels
    assert "critical" in labels


@pytest.mark.asyncio
async def test_detect_labels_preserves_user_labels():
    """Test that user-specified labels are preserved."""
    adapter = MockAdapter(
        [
            {"id": "bug", "name": "bug"},
            {"id": "custom", "name": "custom-label"},
        ]
    )

    labels = await detect_and_apply_labels(
        adapter, "Fix error", "Bug in code", existing_labels=["custom"]
    )

    assert "custom" in labels
    assert "bug" in labels


@pytest.mark.asyncio
async def test_detect_labels_no_duplicates():
    """Test that duplicate labels are not added."""
    adapter = MockAdapter(
        [
            {"id": "bug", "name": "bug"},
        ]
    )

    labels = await detect_and_apply_labels(
        adapter, "Fix bug", "Bug fix needed", existing_labels=["bug"]
    )

    # Count occurrences of 'bug'
    assert labels.count("bug") == 1


@pytest.mark.asyncio
async def test_detect_labels_no_adapter_support():
    """Test graceful handling when adapter doesn't support labels."""
    adapter = MockAdapterNoLabels()

    labels = await detect_and_apply_labels(
        adapter, "Fix bug", "Bug description", existing_labels=["custom"]
    )

    # Should return only user-specified labels
    assert labels == ["custom"]


@pytest.mark.asyncio
async def test_detect_labels_empty_content():
    """Test with empty title and description."""
    adapter = MockAdapter(
        [
            {"id": "bug", "name": "bug"},
        ]
    )

    labels = await detect_and_apply_labels(adapter, "", "")

    assert labels == []


@pytest.mark.asyncio
async def test_detect_labels_no_matches():
    """Test when no labels match the content."""
    adapter = MockAdapter(
        [
            {"id": "unrelated", "name": "unrelated-label"},
        ]
    )

    labels = await detect_and_apply_labels(
        adapter, "Random content", "No matching keywords"
    )

    assert labels == []


@pytest.mark.asyncio
async def test_detect_labels_case_insensitive():
    """Test case-insensitive matching."""
    adapter = MockAdapter(
        [
            {"id": "bug", "name": "BUG"},
            {"id": "feature", "name": "Feature"},
        ]
    )

    labels = await detect_and_apply_labels(
        adapter, "fix BUG in feature", "Feature has bug"
    )

    assert "bug" in labels
    assert "feature" in labels


@pytest.mark.asyncio
async def test_detect_labels_ui_frontend():
    """Test UI/frontend label detection."""
    adapter = MockAdapter(
        [
            {"id": "ui", "name": "ui"},
            {"id": "frontend", "name": "frontend"},
        ]
    )

    labels = await detect_and_apply_labels(
        adapter, "Update interface design", "Frontend UI improvements"
    )

    assert "ui" in labels or "frontend" in labels


@pytest.mark.asyncio
async def test_detect_labels_backend_api():
    """Test backend/API label detection."""
    adapter = MockAdapter(
        [
            {"id": "backend", "name": "backend"},
            {"id": "api", "name": "api"},
        ]
    )

    labels = await detect_and_apply_labels(
        adapter, "Fix API endpoint", "Backend database optimization"
    )

    assert "api" in labels or "backend" in labels


@pytest.mark.asyncio
async def test_detect_labels_test_qa():
    """Test QA/testing label detection."""
    adapter = MockAdapter(
        [
            {"id": "test", "name": "testing"},
            {"id": "qa", "name": "qa"},
        ]
    )

    labels = await detect_and_apply_labels(
        adapter, "Add unit tests", "Testing and validation needed"
    )

    assert "test" in labels or "qa" in labels


@pytest.mark.asyncio
async def test_detect_labels_adapter_exception():
    """Test graceful handling when adapter.list_labels() raises exception."""

    class FailingAdapter:
        async def list_labels(self):
            raise Exception("Network error")

    adapter = FailingAdapter()

    labels = await detect_and_apply_labels(
        adapter, "Fix bug", "Bug fix", existing_labels=["custom"]
    )

    # Should return user labels when adapter fails
    assert labels == ["custom"]


@pytest.mark.asyncio
async def test_detect_labels_empty_adapter_labels():
    """Test when adapter returns empty label list."""
    adapter = MockAdapter([])

    labels = await detect_and_apply_labels(
        adapter, "Fix bug", "Bug description", existing_labels=["custom"]
    )

    # Should return only user-specified labels
    assert labels == ["custom"]


@pytest.mark.asyncio
async def test_detect_labels_string_format():
    """Test with labels as strings instead of dicts."""

    class StringLabelAdapter:
        async def list_labels(self):
            return ["bug", "feature", "documentation"]

    adapter = StringLabelAdapter()

    labels = await detect_and_apply_labels(
        adapter, "Fix bug in feature", "Documentation needed"
    )

    assert "bug" in labels
    assert "feature" in labels or "documentation" in labels
