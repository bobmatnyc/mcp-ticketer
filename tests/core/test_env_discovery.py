"""Tests for environment file auto-discovery."""

from pathlib import Path
from unittest.mock import Mock, patch

from mcp_ticketer.core.env_discovery import (
    DiscoveredAdapter,
    DiscoveryResult,
    EnvDiscovery,
    discover_config,
)
from mcp_ticketer.core.project_config import AdapterType


class TestEnvDiscovery:
    """Test environment file discovery functionality."""

    def test_discover_linear_complete(self, tmp_path: Path) -> None:
        """Test discovering complete Linear configuration.

        NOTE: The auto-detection logic correctly identifies short identifiers
        (like 'team-abc-123') as team_key, not team_id. Only UUID-format
        identifiers are stored as team_id.
        """
        # Create .env file
        env_content = """
LINEAR_API_KEY=lin_api_test123456789012345678
LINEAR_TEAM_ID=team-abc-123
LINEAR_PROJECT_ID=proj-xyz-456
"""
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        # Discover
        discovery = EnvDiscovery(tmp_path)
        result = discovery.discover()

        # Assertions
        assert len(result.adapters) >= 1
        linear = result.get_adapter_by_type(AdapterType.LINEAR.value)
        assert linear is not None
        assert linear.adapter_type == AdapterType.LINEAR.value
        assert linear.config["api_key"] == "lin_api_test123456789012345678"
        # Short identifier is correctly detected as team_key
        assert linear.config["team_key"] == "team-abc-123"
        assert linear.config["project_id"] == "proj-xyz-456"
        assert linear.is_complete()
        assert linear.confidence >= 0.9

    def test_discover_linear_incomplete(self, tmp_path: Path) -> None:
        """Test discovering incomplete Linear configuration."""
        # Create .env file with only API key
        env_content = "LINEAR_API_KEY=lin_api_test123"
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        # Discover
        discovery = EnvDiscovery(tmp_path)
        result = discovery.discover()

        # Assertions
        linear = result.get_adapter_by_type(AdapterType.LINEAR.value)
        assert linear is not None
        assert linear.config["api_key"] == "lin_api_test123"
        assert not linear.is_complete()
        assert "team_id" in linear.missing_fields[0]

    def test_discover_github_complete(self, tmp_path: Path) -> None:
        """Test discovering complete GitHub configuration."""
        # Create .env file
        env_content = """
GITHUB_TOKEN=ghp_test1234567890123456789012
GITHUB_OWNER=testuser
GITHUB_REPO=testrepo
"""
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        # Discover
        discovery = EnvDiscovery(tmp_path)
        result = discovery.discover()

        # Assertions
        github = result.get_adapter_by_type(AdapterType.GITHUB.value)
        assert github is not None
        assert github.config["token"] == "ghp_test1234567890123456789012"
        assert github.config["owner"] == "testuser"
        assert github.config["repo"] == "testrepo"
        assert github.is_complete()

    def test_discover_github_combined_repo(self, tmp_path: Path) -> None:
        """Test discovering GitHub with combined owner/repo format."""
        # Create .env file
        env_content = """
GITHUB_TOKEN=ghp_test1234567890123456789012
GITHUB_REPOSITORY=testuser/testrepo
"""
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        # Discover
        discovery = EnvDiscovery(tmp_path)
        result = discovery.discover()

        # Assertions
        github = result.get_adapter_by_type(AdapterType.GITHUB.value)
        assert github is not None
        assert github.config["owner"] == "testuser"
        assert github.config["repo"] == "testrepo"
        assert github.is_complete()

    def test_discover_jira_complete(self, tmp_path: Path) -> None:
        """Test discovering complete JIRA configuration."""
        # Create .env file
        env_content = """
JIRA_SERVER=https://company.atlassian.net
JIRA_EMAIL=user@company.com
JIRA_API_TOKEN=test_token_12345
JIRA_PROJECT_KEY=PROJ
"""
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        # Discover
        discovery = EnvDiscovery(tmp_path)
        result = discovery.discover()

        # Assertions
        jira = result.get_adapter_by_type(AdapterType.JIRA.value)
        assert jira is not None
        assert jira.config["server"] == "https://company.atlassian.net"
        assert jira.config["email"] == "user@company.com"
        assert jira.config["api_token"] == "test_token_12345"
        assert jira.config["project_key"] == "PROJ"
        assert jira.is_complete()

    def test_discover_aitrackdown_with_env(self, tmp_path: Path) -> None:
        """Test discovering AITrackdown with environment variable."""
        # Create .env file
        env_content = "AITRACKDOWN_PATH=.custom-trackdown"
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        # Discover
        discovery = EnvDiscovery(tmp_path)
        result = discovery.discover()

        # Assertions
        aitrackdown = result.get_adapter_by_type(AdapterType.AITRACKDOWN.value)
        assert aitrackdown is not None
        assert aitrackdown.config["base_path"] == ".custom-trackdown"

    def test_discover_aitrackdown_with_directory(self, tmp_path: Path) -> None:
        """Test discovering AITrackdown by directory existence."""
        # Create .aitrackdown directory
        aitrackdown_dir = tmp_path / ".aitrackdown"
        aitrackdown_dir.mkdir()

        # Discover (no .env file)
        discovery = EnvDiscovery(tmp_path)
        result = discovery.discover()

        # Assertions
        aitrackdown = result.get_adapter_by_type(AdapterType.AITRACKDOWN.value)
        assert aitrackdown is not None
        assert aitrackdown.config["base_path"] == ".aitrackdown"
        assert aitrackdown.confidence == 0.8  # Directory exists (medium confidence)

    def test_discover_multiple_adapters(self, tmp_path: Path) -> None:
        """Test discovering multiple adapters in one file."""
        # Create .env file with multiple adapters
        env_content = """
LINEAR_API_KEY=lin_api_test123456789012345678
LINEAR_TEAM_ID=team-abc

GITHUB_TOKEN=ghp_test1234567890123456789012
GITHUB_REPOSITORY=user/repo

JIRA_SERVER=https://company.atlassian.net
JIRA_EMAIL=user@company.com
JIRA_API_TOKEN=jira_token_123
"""
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        # Discover
        discovery = EnvDiscovery(tmp_path)
        result = discovery.discover()

        # Assertions
        assert len(result.adapters) == 3
        assert result.get_adapter_by_type(AdapterType.LINEAR.value) is not None
        assert result.get_adapter_by_type(AdapterType.GITHUB.value) is not None
        assert result.get_adapter_by_type(AdapterType.JIRA.value) is not None

    def test_env_local_overrides_env(self, tmp_path: Path) -> None:
        """Test that .env.local overrides .env values."""
        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("LINEAR_API_KEY=old_key\nLINEAR_TEAM_ID=team-old")

        # Create .env.local file
        env_local = tmp_path / ".env.local"
        env_local.write_text("LINEAR_API_KEY=new_key")

        # Discover
        discovery = EnvDiscovery(tmp_path)
        result = discovery.discover()

        # Assertions
        linear = result.get_adapter_by_type(AdapterType.LINEAR.value)
        assert linear is not None
        assert linear.config["api_key"] == "new_key"
        assert (
            linear.config["team_key"] == "team-old"
        )  # Not overridden (short identifier)
        assert linear.found_in == ".env.local"  # Highest priority file

    def test_get_primary_adapter(self, tmp_path: Path) -> None:
        """Test getting primary (recommended) adapter."""
        # Create .env with multiple adapters (different completeness)
        env_content = """
# Complete Linear config
LINEAR_API_KEY=lin_api_test123456789012345678
LINEAR_TEAM_ID=team-abc

# Incomplete GitHub (missing repo)
GITHUB_TOKEN=ghp_test1234567890123456789012
GITHUB_OWNER=user
"""
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        # Discover
        discovery = EnvDiscovery(tmp_path)
        result = discovery.discover()

        # Primary should be Linear (complete)
        primary = result.get_primary_adapter()
        assert primary is not None
        assert primary.adapter_type == AdapterType.LINEAR.value
        assert primary.is_complete()

    def test_validate_discovered_config_github_token(self, tmp_path: Path) -> None:
        """Test validation of GitHub token format."""
        # Create .env with invalid GitHub token
        env_content = "GITHUB_TOKEN=invalid_token\nGITHUB_REPOSITORY=user/repo"
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        # Discover
        discovery = EnvDiscovery(tmp_path)
        result = discovery.discover()

        # Validate
        github = result.get_adapter_by_type(AdapterType.GITHUB.value)
        assert github is not None
        warnings = discovery.validate_discovered_config(github)

        # Should have warning about token format
        assert any("doesn't match expected format" in w for w in warnings)

    def test_validate_discovered_config_jira_server(self, tmp_path: Path) -> None:
        """Test validation of JIRA server URL."""
        # Create .env with invalid server URL
        env_content = """
JIRA_SERVER=invalid-url
JIRA_EMAIL=user@company.com
JIRA_API_TOKEN=token123
"""
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        # Discover
        discovery = EnvDiscovery(tmp_path)
        result = discovery.discover()

        # Validate
        jira = result.get_adapter_by_type(AdapterType.JIRA.value)
        assert jira is not None
        warnings = discovery.validate_discovered_config(jira)

        # Should have warning about URL format
        assert any("should start with http" in w.lower() for w in warnings)

    def test_no_env_files(self, tmp_path: Path) -> None:
        """Test discovery when no .env files exist.

        NOTE: The discovery may still find 'environment' if actual environment
        variables are present, but no .env files should be found.
        """
        # Discover (no .env files)
        discovery = EnvDiscovery(tmp_path)
        result = discovery.discover()

        # Assertions
        # May have 'environment' if actual env vars exist
        env_files = [f for f in result.env_files_found if f != "environment"]
        assert len(env_files) == 0, "No .env files should be found"
        # Warning should indicate no .env files were found (only if no env vars either)
        if len(result.env_files_found) == 0:
            assert any("No .env files found" in w for w in result.warnings)

    def test_alternative_naming_conventions(self, tmp_path: Path) -> None:
        """Test that alternative naming conventions are detected."""
        # Create .env with alternative names
        env_content = """
# Linear alternative
LINEAR_TOKEN=lin_api_test123456789012345678
MCP_TICKETER_LINEAR_TEAM_ID=team-abc

# GitHub alternative
GH_TOKEN=ghp_test1234567890123456789012
GH_REPO=user/repo

# JIRA alternative
JIRA_URL=https://company.atlassian.net
JIRA_USER=user@company.com
JIRA_TOKEN=token123
"""
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        # Discover
        discovery = EnvDiscovery(tmp_path)
        result = discovery.discover()

        # Assertions
        linear = result.get_adapter_by_type(AdapterType.LINEAR.value)
        assert linear is not None
        assert linear.config["api_key"] == "lin_api_test123456789012345678"
        assert linear.config["team_key"] == "team-abc"  # Short identifier

        github = result.get_adapter_by_type(AdapterType.GITHUB.value)
        assert github is not None
        assert github.config["token"] == "ghp_test1234567890123456789012"

        jira = result.get_adapter_by_type(AdapterType.JIRA.value)
        assert jira is not None
        assert jira.config["server"] == "https://company.atlassian.net"

    @patch("subprocess.run")
    def test_security_warning_tracked_in_git(
        self, mock_run: Mock, tmp_path: Path
    ) -> None:
        """Test security warning when .env is tracked in git."""
        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("LINEAR_API_KEY=test123")

        # Mock git ls-files to return success (file is tracked)
        mock_run.return_value = Mock(returncode=0)

        # Discover
        discovery = EnvDiscovery(tmp_path)
        result = discovery.discover()

        # Should have security warning
        assert any(".env is tracked in git" in w for w in result.warnings)

    @patch("subprocess.run")
    def test_no_security_warning_not_tracked(
        self, mock_run: Mock, tmp_path: Path
    ) -> None:
        """Test no security warning when .env is not tracked."""
        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("LINEAR_API_KEY=test123")

        # Mock git ls-files to return error (file not tracked)
        mock_run.return_value = Mock(returncode=1)

        # Discover
        discovery = EnvDiscovery(tmp_path)
        result = discovery.discover()

        # Should NOT have tracking warning (but may have other warnings)
        assert not any(".env is tracked in git" in w for w in result.warnings)

    def test_discover_config_convenience_function(self, tmp_path: Path) -> None:
        """Test the convenience function for discovery."""
        # Create .env file
        env_content = (
            "LINEAR_API_KEY=lin_api_test123456789012345678\nLINEAR_TEAM_ID=team-abc"
        )
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        # Use convenience function
        result = discover_config(tmp_path)

        # Assertions
        assert isinstance(result, DiscoveryResult)
        assert len(result.adapters) > 0


class TestDiscoveredAdapter:
    """Test DiscoveredAdapter dataclass."""

    def test_is_complete_true(self) -> None:
        """Test is_complete when no missing fields."""
        adapter = DiscoveredAdapter(
            adapter_type=AdapterType.LINEAR.value,
            config={"api_key": "test", "team_id": "team1"},
            confidence=1.0,
            missing_fields=[],
        )
        assert adapter.is_complete()

    def test_is_complete_false(self) -> None:
        """Test is_complete when has missing fields."""
        adapter = DiscoveredAdapter(
            adapter_type=AdapterType.GITHUB.value,
            config={"token": "test"},
            confidence=0.5,
            missing_fields=["owner", "repo"],
        )
        assert not adapter.is_complete()


class TestDiscoveryResult:
    """Test DiscoveryResult dataclass."""

    def test_get_primary_adapter_complete_first(self) -> None:
        """Test that complete adapters are preferred."""
        result = DiscoveryResult()

        # Add incomplete adapter
        incomplete = DiscoveredAdapter(
            adapter_type=AdapterType.GITHUB.value,
            config={"token": "test"},
            confidence=0.8,
            missing_fields=["owner"],
        )
        result.adapters.append(incomplete)

        # Add complete adapter
        complete = DiscoveredAdapter(
            adapter_type=AdapterType.LINEAR.value,
            config={"api_key": "test", "team_id": "team1"},
            confidence=0.6,
            missing_fields=[],
        )
        result.adapters.append(complete)

        # Complete adapter should be primary (even with lower confidence)
        primary = result.get_primary_adapter()
        assert primary is not None
        assert primary.adapter_type == AdapterType.LINEAR.value

    def test_get_primary_adapter_highest_confidence(self) -> None:
        """Test that highest confidence is used when completeness is equal."""
        result = DiscoveryResult()

        # Add adapters with different confidence
        low_conf = DiscoveredAdapter(
            adapter_type=AdapterType.LINEAR.value,
            config={"api_key": "test"},
            confidence=0.5,
            missing_fields=["team_id"],
        )
        result.adapters.append(low_conf)

        high_conf = DiscoveredAdapter(
            adapter_type=AdapterType.GITHUB.value,
            config={"token": "test"},
            confidence=0.8,
            missing_fields=["owner"],
        )
        result.adapters.append(high_conf)

        # Higher confidence should be primary
        primary = result.get_primary_adapter()
        assert primary is not None
        assert primary.adapter_type == AdapterType.GITHUB.value

    def test_get_adapter_by_type(self) -> None:
        """Test getting adapter by type."""
        result = DiscoveryResult()

        linear = DiscoveredAdapter(
            adapter_type=AdapterType.LINEAR.value,
            config={"api_key": "test"},
            confidence=1.0,
        )
        result.adapters.append(linear)

        # Should find Linear
        found = result.get_adapter_by_type(AdapterType.LINEAR.value)
        assert found is not None
        assert found.adapter_type == AdapterType.LINEAR.value

        # Should not find GitHub
        not_found = result.get_adapter_by_type(AdapterType.GITHUB.value)
        assert not_found is None
