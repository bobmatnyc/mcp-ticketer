"""Test that config_set_* functions preserve adapter configurations.

This test suite verifies the fix for the critical bug where setting
default values (adapter, project, user, etc.) would wipe out all
existing adapter configurations.

The bug occurred because the pattern:
    config = resolver.load_project_config() or TicketerConfig()

Would create an empty config if load_project_config() returned None
(which can happen on file read/parse errors), wiping all adapters.

The fix uses _safe_load_config() which:
1. Tries to load existing config
2. If file doesn't exist: creates new config (first-time setup OK)
3. If file exists but fails to load: raises error (prevents data loss)
"""

import json

import pytest

from mcp_ticketer.core.project_config import AdapterConfig, TicketerConfig
from mcp_ticketer.mcp.server.tools.config_tools import (
    config_set_assignment_labels,
    config_set_default_cycle,
    config_set_default_epic,
    config_set_default_project,
    config_set_default_tags,
    config_set_default_team,
    config_set_default_user,
    config_set_primary_adapter,
)


@pytest.fixture
def temp_project_dir(tmp_path, monkeypatch):
    """Create temporary project directory with config."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Change to project directory
    monkeypatch.chdir(project_dir)

    return project_dir


@pytest.fixture
def config_with_adapters(temp_project_dir):
    """Create config file with multiple adapters configured."""
    config_dir = temp_project_dir / ".mcp-ticketer"
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "config.json"

    # Create config with multiple adapters
    config = TicketerConfig(
        default_adapter="linear",
        adapters={
            "linear": AdapterConfig(
                adapter="linear",
                api_key="lin_api_test_key_1234567890",
                team_key="ENG",
                team_id="abc-123-def-456",
            ),
            "github": AdapterConfig(
                adapter="github",
                token="ghp_test_token_1234567890",
                owner="testorg",
                repo="testrepo",
            ),
            "jira": AdapterConfig(
                adapter="jira",
                server="https://test.atlassian.net",
                email="test@example.com",
                api_token="jira_test_token_1234567890",
                project_key="TEST",
            ),
        },
        default_project="project-123",
        default_user="user@example.com",
        default_tags=["tag1", "tag2"],
    )

    # Write config to file
    with open(config_path, "w") as f:
        json.dump(config.to_dict(), f, indent=2)

    return config_path


@pytest.mark.asyncio
async def test_config_set_primary_adapter_preserves_adapters(config_with_adapters):
    """Test that setting default adapter preserves all adapter configs."""
    # Load initial config to verify adapters exist
    with open(config_with_adapters) as f:
        initial_config = json.load(f)

    assert "linear" in initial_config["adapters"]
    assert "github" in initial_config["adapters"]
    assert "jira" in initial_config["adapters"]

    # Set primary adapter to github
    result = await config_set_primary_adapter("github")

    assert result["status"] == "completed"
    assert result["new_adapter"] == "github"

    # Verify adapters are preserved
    with open(config_with_adapters) as f:
        updated_config = json.load(f)

    assert "linear" in updated_config["adapters"], "Linear adapter was lost!"
    assert "github" in updated_config["adapters"], "GitHub adapter was lost!"
    assert "jira" in updated_config["adapters"], "JIRA adapter was lost!"

    # Verify adapter details are intact
    assert (
        updated_config["adapters"]["linear"]["api_key"] == "lin_api_test_key_1234567890"
    )
    assert updated_config["adapters"]["github"]["token"] == "ghp_test_token_1234567890"
    assert updated_config["adapters"]["jira"]["server"] == "https://test.atlassian.net"

    # Verify default_adapter was updated
    assert updated_config["default_adapter"] == "github"


@pytest.mark.asyncio
async def test_config_set_default_project_preserves_adapters(config_with_adapters):
    """Test that setting default project preserves all adapter configs."""
    # Set default project
    result = await config_set_default_project("new-project-456")

    assert result["status"] == "completed"
    assert result["new_project"] == "new-project-456"

    # Verify adapters are preserved
    with open(config_with_adapters) as f:
        updated_config = json.load(f)

    assert "linear" in updated_config["adapters"], "Linear adapter was lost!"
    assert "github" in updated_config["adapters"], "GitHub adapter was lost!"
    assert "jira" in updated_config["adapters"], "JIRA adapter was lost!"

    # Verify default_project was updated
    assert updated_config["default_project"] == "new-project-456"


@pytest.mark.asyncio
async def test_config_set_default_user_preserves_adapters(config_with_adapters):
    """Test that setting default user preserves all adapter configs."""
    # Set default user
    result = await config_set_default_user("newuser@example.com")

    assert result["status"] == "completed"
    assert result["new_user"] == "newuser@example.com"

    # Verify adapters are preserved
    with open(config_with_adapters) as f:
        updated_config = json.load(f)

    assert "linear" in updated_config["adapters"], "Linear adapter was lost!"
    assert "github" in updated_config["adapters"], "GitHub adapter was lost!"
    assert "jira" in updated_config["adapters"], "JIRA adapter was lost!"

    # Verify default_user was updated
    assert updated_config["default_user"] == "newuser@example.com"


@pytest.mark.asyncio
async def test_config_set_default_tags_preserves_adapters(config_with_adapters):
    """Test that setting default tags preserves all adapter configs."""
    # Set default tags
    result = await config_set_default_tags(["newtag1", "newtag2", "newtag3"])

    assert result["status"] == "completed"
    assert result["default_tags"] == ["newtag1", "newtag2", "newtag3"]

    # Verify adapters are preserved
    with open(config_with_adapters) as f:
        updated_config = json.load(f)

    assert "linear" in updated_config["adapters"], "Linear adapter was lost!"
    assert "github" in updated_config["adapters"], "GitHub adapter was lost!"
    assert "jira" in updated_config["adapters"], "JIRA adapter was lost!"

    # Verify default_tags was updated
    assert updated_config["default_tags"] == ["newtag1", "newtag2", "newtag3"]


@pytest.mark.asyncio
async def test_config_set_default_team_preserves_adapters(config_with_adapters):
    """Test that setting default team preserves all adapter configs."""
    # Set default team
    result = await config_set_default_team("NEWTEAM")

    assert result["status"] == "completed"
    assert result["new_team"] == "NEWTEAM"

    # Verify adapters are preserved
    with open(config_with_adapters) as f:
        updated_config = json.load(f)

    assert "linear" in updated_config["adapters"], "Linear adapter was lost!"
    assert "github" in updated_config["adapters"], "GitHub adapter was lost!"
    assert "jira" in updated_config["adapters"], "JIRA adapter was lost!"

    # Verify default_team was updated
    assert updated_config["default_team"] == "NEWTEAM"


@pytest.mark.asyncio
async def test_config_set_default_cycle_preserves_adapters(config_with_adapters):
    """Test that setting default cycle preserves all adapter configs."""
    # Set default cycle
    result = await config_set_default_cycle("Sprint 42")

    assert result["status"] == "completed"
    assert result["new_cycle"] == "Sprint 42"

    # Verify adapters are preserved
    with open(config_with_adapters) as f:
        updated_config = json.load(f)

    assert "linear" in updated_config["adapters"], "Linear adapter was lost!"
    assert "github" in updated_config["adapters"], "GitHub adapter was lost!"
    assert "jira" in updated_config["adapters"], "JIRA adapter was lost!"

    # Verify default_cycle was updated
    assert updated_config["default_cycle"] == "Sprint 42"


@pytest.mark.asyncio
async def test_config_set_default_epic_preserves_adapters(config_with_adapters):
    """Test that setting default epic preserves all adapter configs."""
    # Set default epic
    result = await config_set_default_epic("epic-789")

    assert result["status"] == "completed"
    assert result["default_epic"] == "epic-789"

    # Verify adapters are preserved
    with open(config_with_adapters) as f:
        updated_config = json.load(f)

    assert "linear" in updated_config["adapters"], "Linear adapter was lost!"
    assert "github" in updated_config["adapters"], "GitHub adapter was lost!"
    assert "jira" in updated_config["adapters"], "JIRA adapter was lost!"

    # Verify default_epic was updated
    assert updated_config["default_epic"] == "epic-789"


@pytest.mark.asyncio
async def test_config_set_assignment_labels_preserves_adapters(config_with_adapters):
    """Test that setting assignment labels preserves all adapter configs."""
    # Set assignment labels
    result = await config_set_assignment_labels(["my-work", "in-progress"])

    assert result["status"] == "completed"
    assert result["assignment_labels"] == ["my-work", "in-progress"]

    # Verify adapters are preserved
    with open(config_with_adapters) as f:
        updated_config = json.load(f)

    assert "linear" in updated_config["adapters"], "Linear adapter was lost!"
    assert "github" in updated_config["adapters"], "GitHub adapter was lost!"
    assert "jira" in updated_config["adapters"], "JIRA adapter was lost!"

    # Verify assignment_labels was updated
    assert updated_config["assignment_labels"] == ["my-work", "in-progress"]


@pytest.mark.asyncio
async def test_corrupted_config_file_raises_error(temp_project_dir):
    """Test that corrupted config file raises error instead of wiping data."""
    config_dir = temp_project_dir / ".mcp-ticketer"
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "config.json"

    # Create corrupted JSON file
    with open(config_path, "w") as f:
        f.write('{"adapters": {"linear": {invalid json')

    # Attempt to set default adapter should fail
    result = await config_set_primary_adapter("github")

    assert result["status"] == "error"
    assert (
        "failed to load" in result["error"].lower()
        or "corrupted" in result["error"].lower()
    )


@pytest.mark.asyncio
async def test_first_time_setup_creates_new_config(temp_project_dir):
    """Test that first-time setup (no config file) creates new config."""
    # No config file exists yet
    config_path = temp_project_dir / ".mcp-ticketer" / "config.json"
    assert not config_path.exists()

    # Set default adapter should create new config
    result = await config_set_primary_adapter("linear")

    assert result["status"] == "completed"
    assert result["new_adapter"] == "linear"

    # Verify config file was created
    assert config_path.exists()

    with open(config_path) as f:
        config = json.load(f)

    assert config["default_adapter"] == "linear"


@pytest.mark.asyncio
async def test_multiple_sequential_updates_preserve_adapters(config_with_adapters):
    """Test that multiple sequential config updates all preserve adapters."""
    # Update 1: Set default adapter
    await config_set_primary_adapter("github")

    # Update 2: Set default project
    await config_set_default_project("new-project")

    # Update 3: Set default user
    await config_set_default_user("newuser@example.com")

    # Update 4: Set default tags
    await config_set_default_tags(["tag3", "tag4"])

    # Verify all adapters are still present
    with open(config_with_adapters) as f:
        final_config = json.load(f)

    assert "linear" in final_config["adapters"], "Linear adapter was lost!"
    assert "github" in final_config["adapters"], "GitHub adapter was lost!"
    assert "jira" in final_config["adapters"], "JIRA adapter was lost!"

    # Verify all updates were applied
    assert final_config["default_adapter"] == "github"
    assert final_config["default_project"] == "new-project"
    assert final_config["default_user"] == "newuser@example.com"
    assert final_config["default_tags"] == ["tag3", "tag4"]
