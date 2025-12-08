"""Integration tests for GitHub milestone operations.

Tests the 6 new milestone methods:
- milestone_create()
- milestone_get()
- milestone_list()
- milestone_update()
- milestone_delete()
- milestone_get_issues()

Uses mocked GitHub API responses to avoid real API calls.
"""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ticketer.adapters.github import GitHubAdapter


@pytest.fixture
def mock_github_milestone():
    """Mock GitHub milestone response."""
    return {
        "number": 42,
        "title": "v1.0.0 Release",
        "description": "First major release",
        "state": "open",
        "open_issues": 5,
        "closed_issues": 10,
        "due_on": "2025-12-31T23:59:59Z",
        "html_url": "https://github.com/owner/repo/milestone/42",
        "created_at": "2025-12-01T00:00:00Z",
        "updated_at": "2025-12-03T12:00:00Z",
    }


@pytest.fixture
def github_adapter():
    """Create GitHub adapter with mock configuration."""
    config = {
        "token": "test_token",
        "owner": "test-owner",
        "repo": "test-repo",
    }
    return GitHubAdapter(config)


@pytest.mark.asyncio
@patch("mcp_ticketer.core.milestone_manager.MilestoneManager")
async def test_milestone_create(
    mock_manager_class, github_adapter, mock_github_milestone
):
    """Test creating a GitHub milestone."""
    # Mock HTTP response
    mock_response = MagicMock()
    mock_response.json.return_value = mock_github_milestone
    mock_response.raise_for_status = MagicMock()

    github_adapter.client.post = AsyncMock(return_value=mock_response)

    # Mock MilestoneManager
    mock_manager = MagicMock()
    mock_manager.save_milestone.return_value = None
    mock_manager_class.return_value = mock_manager

    # Create milestone
    milestone = await github_adapter.milestone_create(
        name="v1.0.0 Release",
        target_date=datetime.date(2025, 12, 31),
        labels=["release", "v1.0"],
        description="First major release",
    )

    # Verify API call
    github_adapter.client.post.assert_called_once()
    call_args = github_adapter.client.post.call_args
    assert "/milestones" in call_args[0][0]
    assert call_args[1]["json"]["title"] == "v1.0.0 Release"
    assert call_args[1]["json"]["description"] == "First major release"
    assert "due_on" in call_args[1]["json"]

    # Verify returned milestone
    assert milestone.name == "v1.0.0 Release"
    assert milestone.id == "42"
    assert milestone.total_issues == 15
    assert milestone.closed_issues == 10
    assert milestone.progress_pct == pytest.approx(66.67, rel=0.01)
    assert milestone.labels == ["release", "v1.0"]

    # Verify local storage was called
    mock_manager.save_milestone.assert_called_once()


@pytest.mark.asyncio
@patch("mcp_ticketer.core.milestone_manager.MilestoneManager")
async def test_milestone_get(mock_manager_class, github_adapter, mock_github_milestone):
    """Test getting a GitHub milestone by ID."""
    # Mock HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_github_milestone
    mock_response.raise_for_status = MagicMock()

    github_adapter.client.get = AsyncMock(return_value=mock_response)

    # Mock MilestoneManager
    mock_manager = MagicMock()
    mock_local_milestone = MagicMock()
    mock_local_milestone.labels = ["release", "v1.0"]
    mock_manager.get_milestone.return_value = mock_local_milestone
    mock_manager_class.return_value = mock_manager

    # Get milestone
    milestone = await github_adapter.milestone_get("42")

    # Verify API call
    github_adapter.client.get.assert_called_once()
    call_args = github_adapter.client.get.call_args
    assert "/milestones/42" in call_args[0][0]

    # Verify returned milestone
    assert milestone is not None
    assert milestone.id == "42"
    assert milestone.name == "v1.0.0 Release"
    assert milestone.labels == ["release", "v1.0"]


@pytest.mark.asyncio
@patch("mcp_ticketer.core.milestone_manager.MilestoneManager")
async def test_milestone_get_not_found(mock_manager_class, github_adapter):
    """Test getting a non-existent milestone."""
    # Mock HTTP 404 response
    mock_response = MagicMock()
    mock_response.status_code = 404

    github_adapter.client.get = AsyncMock(return_value=mock_response)

    # Mock MilestoneManager
    mock_manager = MagicMock()
    mock_manager_class.return_value = mock_manager

    # Get milestone
    milestone = await github_adapter.milestone_get("999")

    # Verify None returned
    assert milestone is None


@pytest.mark.asyncio
@patch("mcp_ticketer.core.milestone_manager.MilestoneManager")
async def test_milestone_list(
    mock_manager_class, github_adapter, mock_github_milestone
):
    """Test listing GitHub milestones."""
    # Mock HTTP response with multiple milestones
    milestone1 = mock_github_milestone.copy()
    milestone1["number"] = 1
    milestone1["title"] = "v1.0.0"

    milestone2 = mock_github_milestone.copy()
    milestone2["number"] = 2
    milestone2["title"] = "v2.0.0"

    mock_response = MagicMock()
    mock_response.json.return_value = [milestone1, milestone2]
    mock_response.raise_for_status = MagicMock()

    github_adapter.client.get = AsyncMock(return_value=mock_response)

    # Mock MilestoneManager
    mock_manager = MagicMock()
    mock_manager.get_milestone.return_value = None  # No local labels
    mock_manager_class.return_value = mock_manager

    # List milestones
    milestones = await github_adapter.milestone_list(state="open")

    # Verify API call
    github_adapter.client.get.assert_called_once()
    call_args = github_adapter.client.get.call_args
    assert "/milestones" in call_args[0][0]
    assert call_args[1]["params"]["state"] == "open"

    # Verify returned milestones
    assert len(milestones) == 2
    assert milestones[0].id == "1"
    assert milestones[0].name == "v1.0.0"
    assert milestones[1].id == "2"
    assert milestones[1].name == "v2.0.0"


@pytest.mark.asyncio
@patch("mcp_ticketer.core.milestone_manager.MilestoneManager")
async def test_milestone_list_state_filter(mock_manager_class, github_adapter):
    """Test listing milestones with state filter."""
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = MagicMock()

    github_adapter.client.get = AsyncMock(return_value=mock_response)

    # Mock MilestoneManager
    mock_manager = MagicMock()
    mock_manager_class.return_value = mock_manager

    # Test different state filters
    await github_adapter.milestone_list(state="open")
    call_args = github_adapter.client.get.call_args
    assert call_args[1]["params"]["state"] == "open"

    await github_adapter.milestone_list(state="closed")
    call_args = github_adapter.client.get.call_args
    assert call_args[1]["params"]["state"] == "closed"

    await github_adapter.milestone_list(state="completed")
    call_args = github_adapter.client.get.call_args
    assert call_args[1]["params"]["state"] == "closed"


@pytest.mark.asyncio
@patch("mcp_ticketer.core.milestone_manager.MilestoneManager")
async def test_milestone_update(
    mock_manager_class, github_adapter, mock_github_milestone
):
    """Test updating a GitHub milestone."""
    # Mock HTTP response
    updated_milestone = mock_github_milestone.copy()
    updated_milestone["title"] = "v1.0.1 Release"
    updated_milestone["description"] = "Bug fix release"

    mock_response = MagicMock()
    mock_response.json.return_value = updated_milestone
    mock_response.raise_for_status = MagicMock()

    github_adapter.client.patch = AsyncMock(return_value=mock_response)

    # Mock MilestoneManager
    mock_manager = MagicMock()
    mock_manager.get_milestone.return_value = None
    mock_manager_class.return_value = mock_manager

    # Update milestone
    milestone = await github_adapter.milestone_update(
        milestone_id="42",
        name="v1.0.1 Release",
        description="Bug fix release",
        state="closed",
    )

    # Verify API call
    github_adapter.client.patch.assert_called_once()
    call_args = github_adapter.client.patch.call_args
    assert "/milestones/42" in call_args[0][0]
    assert call_args[1]["json"]["title"] == "v1.0.1 Release"
    assert call_args[1]["json"]["description"] == "Bug fix release"
    assert call_args[1]["json"]["state"] == "closed"

    # Verify returned milestone
    assert milestone.name == "v1.0.1 Release"
    assert milestone.description == "Bug fix release"


@pytest.mark.asyncio
@patch("mcp_ticketer.core.milestone_manager.MilestoneManager")
async def test_milestone_update_labels_only(
    mock_manager_class, github_adapter, mock_github_milestone
):
    """Test updating only milestone labels (stored locally)."""
    # Mock HTTP response for GET
    mock_get_response = MagicMock()
    mock_get_response.json.return_value = mock_github_milestone
    mock_get_response.raise_for_status = MagicMock()

    github_adapter.client.get = AsyncMock(return_value=mock_get_response)

    # Mock MilestoneManager
    mock_manager = MagicMock()
    mock_manager.save_milestone.return_value = None
    mock_manager_class.return_value = mock_manager

    # Update labels
    await github_adapter.milestone_update(
        milestone_id="42",
        labels=["release", "critical", "hotfix"],
    )

    # Verify GET was called (no PATCH since only labels changed)
    github_adapter.client.get.assert_called_once()

    # Verify local storage was updated
    mock_manager.save_milestone.assert_called_once()
    saved_milestone = mock_manager.save_milestone.call_args[0][0]
    assert saved_milestone.labels == ["release", "critical", "hotfix"]


@pytest.mark.asyncio
@patch("mcp_ticketer.core.milestone_manager.MilestoneManager")
async def test_milestone_delete(mock_manager_class, github_adapter):
    """Test deleting a GitHub milestone."""
    # Mock HTTP 204 response (success)
    mock_response = MagicMock()
    mock_response.status_code = 204

    github_adapter.client.delete = AsyncMock(return_value=mock_response)

    # Mock MilestoneManager
    mock_manager = MagicMock()
    mock_manager.delete_milestone.return_value = True
    mock_manager_class.return_value = mock_manager

    # Delete milestone
    success = await github_adapter.milestone_delete("42")

    # Verify API call
    github_adapter.client.delete.assert_called_once()
    call_args = github_adapter.client.delete.call_args
    assert "/milestones/42" in call_args[0][0]

    # Verify success
    assert success is True

    # Verify local storage deletion
    mock_manager.delete_milestone.assert_called_once_with("42")


@pytest.mark.asyncio
@patch("mcp_ticketer.core.milestone_manager.MilestoneManager")
async def test_milestone_delete_not_found(mock_manager_class, github_adapter):
    """Test deleting a non-existent milestone."""
    # Mock HTTP 404 response
    mock_response = MagicMock()
    mock_response.status_code = 404

    github_adapter.client.delete = AsyncMock(return_value=mock_response)

    # Mock MilestoneManager
    mock_manager = MagicMock()
    mock_manager_class.return_value = mock_manager

    # Delete milestone
    success = await github_adapter.milestone_delete("999")

    # Verify failure
    assert success is False


@pytest.mark.asyncio
async def test_milestone_get_issues(github_adapter):
    """Test getting issues in a milestone."""
    # Mock HTTP response with issues
    mock_issues = [
        {
            "number": 101,
            "title": "Bug fix #1",
            "state": "open",
            "labels": [{"name": "bug"}, {"name": "high"}],
            "created_at": "2025-12-01T00:00:00Z",
            "updated_at": "2025-12-02T00:00:00Z",
        },
        {
            "number": 102,
            "title": "Feature request",
            "state": "closed",
            "labels": [{"name": "enhancement"}],
            "created_at": "2025-12-01T00:00:00Z",
            "updated_at": "2025-12-03T00:00:00Z",
        },
        {
            "number": 103,
            "title": "Pull request (should be excluded)",
            "state": "open",
            "labels": [],
            "pull_request": {"url": "https://github.com/owner/repo/pull/103"},
            "created_at": "2025-12-01T00:00:00Z",
            "updated_at": "2025-12-02T00:00:00Z",
        },
    ]

    mock_response = MagicMock()
    mock_response.json.return_value = mock_issues
    mock_response.raise_for_status = MagicMock()

    github_adapter.client.get = AsyncMock(return_value=mock_response)

    # Get issues
    issues = await github_adapter.milestone_get_issues("42", state="all")

    # Verify API call
    github_adapter.client.get.assert_called_once()
    call_args = github_adapter.client.get.call_args
    assert "/issues" in call_args[0][0]
    assert call_args[1]["params"]["milestone"] == "42"
    assert call_args[1]["params"]["state"] == "all"

    # Verify returned issues (PR excluded)
    assert len(issues) == 2
    assert issues[0]["id"] == "101"
    assert issues[0]["title"] == "Bug fix #1"
    assert issues[0]["state"] == "open"
    assert issues[0]["labels"] == ["bug", "high"]
    assert issues[1]["id"] == "102"
    assert issues[1]["title"] == "Feature request"


@pytest.mark.asyncio
async def test_milestone_operations_require_repo(github_adapter):
    """Test that milestone operations fail without repo configuration."""
    # Remove repo configuration
    github_adapter.repo = None

    # Test all operations raise ValueError
    with pytest.raises(ValueError, match="Repository required"):
        await github_adapter.milestone_create(name="Test")

    with pytest.raises(ValueError, match="Repository required"):
        await github_adapter.milestone_get("1")

    with pytest.raises(ValueError, match="Repository required"):
        await github_adapter.milestone_list()

    with pytest.raises(ValueError, match="Repository required"):
        await github_adapter.milestone_update("1", name="Test")

    with pytest.raises(ValueError, match="Repository required"):
        await github_adapter.milestone_delete("1")

    with pytest.raises(ValueError, match="Repository required"):
        await github_adapter.milestone_get_issues("1")


@pytest.mark.asyncio
@patch("mcp_ticketer.core.milestone_manager.MilestoneManager")
async def test_github_milestone_to_milestone_conversion(
    mock_manager_class, github_adapter, mock_github_milestone
):
    """Test GitHub milestone to Milestone model conversion."""
    # Test conversion with labels
    milestone = github_adapter._github_milestone_to_milestone(
        mock_github_milestone,
        labels=["release", "v1.0"],
    )

    assert milestone.id == "42"
    assert milestone.name == "v1.0.0 Release"
    assert milestone.description == "First major release"
    assert milestone.state in ["open", "active"]  # State depends on target date
    assert milestone.labels == ["release", "v1.0"]
    assert milestone.total_issues == 15
    assert milestone.closed_issues == 10
    assert milestone.progress_pct == pytest.approx(66.67, rel=0.01)
    assert milestone.project_id == "test-repo"
    assert "github" in milestone.platform_data
    assert milestone.platform_data["github"]["milestone_number"] == 42


@pytest.mark.asyncio
@patch("mcp_ticketer.core.milestone_manager.MilestoneManager")
async def test_milestone_state_mapping(mock_manager_class, github_adapter):
    """Test milestone state mapping logic."""
    # Test open milestone with future due date
    future_milestone = {
        "number": 1,
        "title": "Future Release",
        "description": "",
        "state": "open",
        "open_issues": 5,
        "closed_issues": 0,
        "due_on": "2099-12-31T23:59:59Z",
        "html_url": "https://github.com/owner/repo/milestone/1",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }

    milestone = github_adapter._github_milestone_to_milestone(future_milestone)
    assert milestone.state == "active"

    # Test open milestone with past due date
    past_milestone = future_milestone.copy()
    past_milestone["due_on"] = "2020-01-01T23:59:59Z"

    milestone = github_adapter._github_milestone_to_milestone(past_milestone)
    assert milestone.state == "closed"

    # Test closed milestone
    closed_milestone = future_milestone.copy()
    closed_milestone["state"] = "closed"

    milestone = github_adapter._github_milestone_to_milestone(closed_milestone)
    assert milestone.state == "closed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
