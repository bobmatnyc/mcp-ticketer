"""Tests for environment configuration loading."""

import os
from unittest.mock import mock_open, patch

import pytest

from mcp_ticketer.mcp.server.main import _load_env_configuration


@pytest.fixture
def mock_env_vars():
    """Fixture to provide mock environment variables."""
    return {
        "MCP_TICKETER_ADAPTER": "linear",
        "LINEAR_API_KEY": "test_api_key_123",
        "LINEAR_TEAM_ID": "team_test_456",
    }


@pytest.fixture
def mock_env_file_content():
    """Fixture for .env file content."""
    return """
# MCP Ticketer Configuration
MCP_TICKETER_ADAPTER=jira
JIRA_SERVER=https://test.atlassian.net
JIRA_EMAIL=test@example.com
JIRA_API_TOKEN=file_token_789
"""


def test_load_from_os_environ(mock_env_vars) -> None:
    """Test loading configuration from os.environ (highest priority)."""
    with patch.dict(os.environ, mock_env_vars, clear=False):
        with patch("pathlib.Path.exists", return_value=False):
            result = _load_env_configuration()

    assert result is not None
    assert result["adapter_type"] == "linear"
    assert result["adapter_config"]["api_key"] == "test_api_key_123"
    assert result["adapter_config"]["team_id"] == "team_test_456"


def test_os_environ_overrides_env_file(mock_env_vars, mock_env_file_content) -> None:
    """Test that os.environ takes priority over .env files."""
    with patch.dict(os.environ, mock_env_vars, clear=False):
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=mock_env_file_content)):
                result = _load_env_configuration()

    # Should use os.environ (linear), not .env file (jira)
    assert result is not None
    assert result["adapter_type"] == "linear"
    assert result["adapter_config"]["api_key"] == "test_api_key_123"


def test_load_from_env_file_when_no_environ() -> None:
    """Test loading from .env file when os.environ is empty."""
    env_content = """
MCP_TICKETER_ADAPTER=github
GITHUB_TOKEN=ghp_test_token
GITHUB_REPO=owner/repo
"""
    with patch.dict(os.environ, {}, clear=True):
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=env_content)):
                result = _load_env_configuration()

    assert result is not None
    assert result["adapter_type"] == "github"
    assert result["adapter_config"]["token"] == "ghp_test_token"
    assert result["adapter_config"]["repo"] == "owner/repo"


def test_no_configuration_returns_none() -> None:
    """Test that None is returned when no configuration found."""
    with patch.dict(os.environ, {}, clear=True):
        with patch("pathlib.Path.exists", return_value=False):
            result = _load_env_configuration()

    assert result is None


def test_missing_adapter_type_returns_none() -> None:
    """Test that None is returned when MCP_TICKETER_ADAPTER is missing."""
    env_vars = {
        "SOME_OTHER_VAR": "test_value",
        # Missing MCP_TICKETER_ADAPTER and no adapter-specific keys
    }
    with patch.dict(os.environ, env_vars, clear=False):
        with patch("pathlib.Path.exists", return_value=False):
            result = _load_env_configuration()

    assert result is None


def test_linear_missing_api_key_returns_none() -> None:
    """Test that None is returned when Linear adapter missing API key."""
    env_vars = {
        "MCP_TICKETER_ADAPTER": "linear",
        # Missing LINEAR_API_KEY
    }
    with patch.dict(os.environ, env_vars, clear=False):
        with patch("pathlib.Path.exists", return_value=False):
            result = _load_env_configuration()

    assert result is None


def test_jira_configuration() -> None:
    """Test JIRA adapter configuration."""
    env_vars = {
        "MCP_TICKETER_ADAPTER": "jira",
        "JIRA_SERVER": "https://test.atlassian.net",
        "JIRA_EMAIL": "test@example.com",
        "JIRA_API_TOKEN": "test_token",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        with patch("pathlib.Path.exists", return_value=False):
            result = _load_env_configuration()

    assert result is not None
    assert result["adapter_type"] == "jira"
    assert result["adapter_config"]["server"] == "https://test.atlassian.net"
    assert result["adapter_config"]["email"] == "test@example.com"
    assert result["adapter_config"]["api_token"] == "test_token"


def test_aitrackdown_configuration() -> None:
    """Test aitrackdown adapter configuration."""
    env_vars = {
        "MCP_TICKETER_ADAPTER": "aitrackdown",
        "MCP_TICKETER_BASE_PATH": "/custom/path",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        with patch("pathlib.Path.exists", return_value=False):
            result = _load_env_configuration()

    assert result is not None
    assert result["adapter_type"] == "aitrackdown"
    assert result["adapter_config"]["base_path"] == "/custom/path"


def test_unknown_adapter_type_returns_none() -> None:
    """Test that unknown adapter types return None."""
    env_vars = {
        "MCP_TICKETER_ADAPTER": "unknown_adapter",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        with patch("pathlib.Path.exists", return_value=False):
            result = _load_env_configuration()

    assert result is None


def test_auto_detect_linear_from_env_keys() -> None:
    """Test auto-detection of Linear adapter from LINEAR_* environment keys."""
    env_vars = {
        # No MCP_TICKETER_ADAPTER specified
        "LINEAR_API_KEY": "test_key",
        "LINEAR_TEAM_ID": "test_team",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        with patch("pathlib.Path.exists", return_value=False):
            result = _load_env_configuration()

    assert result is not None
    assert result["adapter_type"] == "linear"
    assert result["adapter_config"]["api_key"] == "test_key"


def test_auto_detect_github_from_env_keys() -> None:
    """Test auto-detection of GitHub adapter from GITHUB_* environment keys."""
    env_vars = {
        # No MCP_TICKETER_ADAPTER specified
        "GITHUB_TOKEN": "ghp_test",
        "GITHUB_REPO": "owner/repo",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        with patch("pathlib.Path.exists", return_value=False):
            result = _load_env_configuration()

    assert result is not None
    assert result["adapter_type"] == "github"
    assert result["adapter_config"]["token"] == "ghp_test"


def test_env_file_provides_fallback_values() -> None:
    """Test that .env file provides fallback values for keys not in os.environ."""
    env_content = """
MCP_TICKETER_ADAPTER=linear
LINEAR_API_KEY=file_key
LINEAR_TEAM_ID=file_team
LINEAR_TEAM_KEY=file_team_key
"""
    env_vars = {
        "MCP_TICKETER_ADAPTER": "linear",
        "LINEAR_API_KEY": "env_key",
        # LINEAR_TEAM_ID not in os.environ - should come from file
    }

    with patch.dict(os.environ, env_vars, clear=False):
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=env_content)):
                result = _load_env_configuration()

    assert result is not None
    assert result["adapter_type"] == "linear"
    # os.environ takes priority
    assert result["adapter_config"]["api_key"] == "env_key"
    # Fallback to .env file for missing keys
    assert result["adapter_config"]["team_id"] == "file_team"
    assert result["adapter_config"]["team_key"] == "file_team_key"


def test_github_with_owner_and_repo() -> None:
    """Test GitHub configuration with owner and repo."""
    env_vars = {
        "MCP_TICKETER_ADAPTER": "github",
        "GITHUB_TOKEN": "ghp_test",
        "GITHUB_OWNER": "test_owner",
        "GITHUB_REPO": "test_repo",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        with patch("pathlib.Path.exists", return_value=False):
            result = _load_env_configuration()

    assert result is not None
    assert result["adapter_type"] == "github"
    assert result["adapter_config"]["token"] == "ghp_test"
    assert result["adapter_config"]["owner"] == "test_owner"
    assert result["adapter_config"]["repo"] == "test_repo"
