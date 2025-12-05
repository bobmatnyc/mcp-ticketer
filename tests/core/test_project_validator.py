"""Tests for project URL validation functionality.

This test suite verifies the ProjectValidator handles all validation scenarios:
- Valid URLs for all platforms (Linear, GitHub, Jira, Asana)
- Invalid URL formats
- Missing adapter configuration
- Invalid adapter credentials
- Project accessibility testing

Test Coverage:
- URL parsing and platform detection
- Adapter configuration validation
- Credential validation
- Error message clarity and suggestions
"""

from unittest.mock import patch

import pytest

from mcp_ticketer.core.project_config import AdapterConfig, TicketerConfig
from mcp_ticketer.core.project_validator import (
    ProjectValidationResult,
    ProjectValidator,
)


class TestProjectValidator:
    """Test suite for ProjectValidator class."""

    @pytest.fixture
    def mock_config_with_linear(self):
        """Mock configuration with Linear adapter configured."""
        config = TicketerConfig()
        config.adapters["linear"] = AdapterConfig(
            adapter="linear",
            api_key="lin_api_test123456789012345678901234567890",
            team_key="ENG",
        )
        config.default_adapter = "linear"
        return config

    @pytest.fixture
    def mock_config_with_github(self):
        """Mock configuration with GitHub adapter configured."""
        config = TicketerConfig()
        config.adapters["github"] = AdapterConfig(
            adapter="github",
            token="ghp_test1234567890",
            owner="testorg",
            repo="testrepo",
        )
        config.default_adapter = "github"
        return config

    @pytest.fixture
    def mock_config_empty(self):
        """Mock configuration with no adapters configured."""
        return TicketerConfig()

    def test_validate_linear_url_success(self, tmp_path, mock_config_with_linear):
        """Test successful validation of Linear project URL."""
        # Setup
        with patch(
            "mcp_ticketer.core.project_validator.ConfigResolver.load_project_config"
        ) as mock_load:
            mock_load.return_value = mock_config_with_linear

            validator = ProjectValidator(project_path=tmp_path)

            # Execute
            result = validator.validate_project_url(
                "https://linear.app/testteam/project/test-project-abc123",
                test_connection=False,
            )

            # Verify
            assert result.valid is True
            assert result.platform == "linear"
            assert result.project_id == "test-project-abc123"
            assert result.adapter_configured is True
            assert result.adapter_valid is True
            assert result.error is None

    def test_validate_github_url_success(self, tmp_path, mock_config_with_github):
        """Test successful validation of GitHub project URL."""
        # Setup
        with patch(
            "mcp_ticketer.core.project_validator.ConfigResolver.load_project_config"
        ) as mock_load:
            mock_load.return_value = mock_config_with_github

            validator = ProjectValidator(project_path=tmp_path)

            # Execute
            result = validator.validate_project_url(
                "https://github.com/testorg/testrepo/projects/1", test_connection=False
            )

            # Verify
            assert result.valid is True
            assert result.platform == "github"
            assert result.project_id == "1"
            assert result.adapter_configured is True
            assert result.adapter_valid is True

    def test_validate_jira_url_success(self, tmp_path):
        """Test successful validation of JIRA project URL."""
        # Setup
        config = TicketerConfig()
        config.adapters["jira"] = AdapterConfig(
            adapter="jira",
            server="https://company.atlassian.net",
            email="test@example.com",
            api_token="test_token_12345",
        )

        with patch(
            "mcp_ticketer.core.project_validator.ConfigResolver.load_project_config"
        ) as mock_load:
            mock_load.return_value = config

            validator = ProjectValidator(project_path=tmp_path)

            # Execute
            result = validator.validate_project_url(
                "https://company.atlassian.net/browse/PROJ-123", test_connection=False
            )

            # Verify
            assert result.valid is True
            assert result.platform == "jira"
            assert result.project_id == "PROJ-123"

    def test_invalid_url_format(self, tmp_path):
        """Test validation fails for invalid URL format."""
        validator = ProjectValidator(project_path=tmp_path)

        # Execute
        result = validator.validate_project_url(
            "not-a-valid-url", test_connection=False
        )

        # Verify
        assert result.valid is False
        assert result.error_type == "url_parse"
        assert "Invalid URL format" in result.error
        assert result.suggestions is not None
        assert any("https://" in s for s in result.suggestions)

    def test_empty_url(self, tmp_path):
        """Test validation fails for empty URL."""
        validator = ProjectValidator(project_path=tmp_path)

        # Execute
        result = validator.validate_project_url("", test_connection=False)

        # Verify
        assert result.valid is False
        assert result.error_type == "url_parse"
        assert "Empty or non-string value" in result.error

    def test_unsupported_platform(self, tmp_path):
        """Test validation fails for unsupported platform URL."""
        validator = ProjectValidator(project_path=tmp_path)

        # Execute
        result = validator.validate_project_url(
            "https://unsupported-platform.com/project/123", test_connection=False
        )

        # Verify
        assert result.valid is False
        assert result.error_type == "url_parse"
        assert "Cannot detect platform" in result.error
        assert "Supported platforms" in str(result.suggestions)

    def test_adapter_not_configured(self, tmp_path, mock_config_empty):
        """Test validation fails when adapter is not configured."""
        # Setup
        with patch(
            "mcp_ticketer.core.project_validator.ConfigResolver.load_project_config"
        ) as mock_load:
            mock_load.return_value = mock_config_empty

            validator = ProjectValidator(project_path=tmp_path)

            # Execute
            result = validator.validate_project_url(
                "https://linear.app/team/project/abc-123", test_connection=False
            )

            # Verify
            assert result.valid is False
            assert result.error_type == "adapter_missing"
            assert result.platform == "linear"
            assert result.project_id == "abc-123"
            assert result.adapter_configured is False
            assert "not configured" in result.error.lower()
            assert result.suggestions is not None
            assert any("setup_wizard" in s for s in result.suggestions)

    def test_invalid_adapter_credentials(self, tmp_path):
        """Test validation fails for invalid adapter credentials."""
        # Setup - Linear config missing required team_key
        config = TicketerConfig()
        config.adapters["linear"] = AdapterConfig(
            adapter="linear",
            api_key="lin_api_test123456789012345678901234567890",
            # team_key missing - should fail validation
        )

        with patch(
            "mcp_ticketer.core.project_validator.ConfigResolver.load_project_config"
        ) as mock_load:
            mock_load.return_value = config

            validator = ProjectValidator(project_path=tmp_path)

            # Execute
            result = validator.validate_project_url(
                "https://linear.app/team/project/abc-123", test_connection=False
            )

            # Verify
            assert result.valid is False
            assert result.error_type == "credentials_invalid"
            assert result.platform == "linear"
            assert result.adapter_configured is True
            assert result.adapter_valid is False
            assert "configuration invalid" in result.error.lower()

    def test_url_parse_error(self, tmp_path, mock_config_with_linear):
        """Test validation handles URL parsing errors gracefully."""
        # Setup
        with patch(
            "mcp_ticketer.core.project_validator.ConfigResolver.load_project_config"
        ) as mock_load:
            mock_load.return_value = mock_config_with_linear

            validator = ProjectValidator(project_path=tmp_path)

            # Execute - malformed Linear URL
            result = validator.validate_project_url(
                "https://linear.app/malformed/url", test_connection=False
            )

            # Verify
            assert result.valid is False
            assert result.error_type == "url_parse"
            assert result.platform == "linear"

    def test_platform_detection_linear(self, tmp_path):
        """Test platform detection for Linear URLs."""
        validator = ProjectValidator(project_path=tmp_path)

        platform = validator._detect_platform("https://linear.app/team/project/abc")
        assert platform == "linear"

    def test_platform_detection_github(self, tmp_path):
        """Test platform detection for GitHub URLs."""
        validator = ProjectValidator(project_path=tmp_path)

        platform = validator._detect_platform(
            "https://github.com/owner/repo/projects/1"
        )
        assert platform == "github"

    def test_platform_detection_jira(self, tmp_path):
        """Test platform detection for JIRA URLs."""
        validator = ProjectValidator(project_path=tmp_path)

        # Test both domain and path-based detection
        platform1 = validator._detect_platform(
            "https://company.atlassian.net/browse/PROJ"
        )
        platform2 = validator._detect_platform("https://jira.company.com/browse/PROJ")

        assert platform1 == "jira"
        assert platform2 == "jira"

    def test_platform_detection_asana(self, tmp_path):
        """Test platform detection for Asana URLs."""
        validator = ProjectValidator(project_path=tmp_path)

        platform = validator._detect_platform("https://app.asana.com/0/123456/987654")
        assert platform == "asana"

    def test_sensitive_config_masking(self, tmp_path):
        """Test that sensitive configuration values are masked."""
        validator = ProjectValidator(project_path=tmp_path)

        config = {
            "api_key": "lin_api_secret123456789012345678901234567890",
            "token": "ghp_secrettoken1234567890",
            "team_key": "ENG",  # Not sensitive
        }

        masked = validator._mask_sensitive_config(config)

        assert "***" in masked["api_key"]
        assert "***" in masked["token"]
        assert masked["team_key"] == "ENG"  # Should not be masked

    def test_example_url_generation(self, tmp_path):
        """Test example URL generation for all platforms."""
        validator = ProjectValidator(project_path=tmp_path)

        linear_example = validator._get_example_url("linear")
        github_example = validator._get_example_url("github")
        jira_example = validator._get_example_url("jira")
        asana_example = validator._get_example_url("asana")

        assert "linear.app" in linear_example
        assert "github.com" in github_example
        assert "atlassian.net" in jira_example
        assert "app.asana.com" in asana_example

    def test_validation_result_dataclass(self):
        """Test ProjectValidationResult dataclass structure."""
        result = ProjectValidationResult(
            valid=True,
            platform="linear",
            project_id="abc-123",
            adapter_configured=True,
            adapter_valid=True,
        )

        assert result.valid is True
        assert result.platform == "linear"
        assert result.project_id == "abc-123"
        assert result.error is None
        assert result.suggestions is None

    def test_validation_result_with_error(self):
        """Test ProjectValidationResult with error information."""
        result = ProjectValidationResult(
            valid=False,
            platform="github",
            error="Adapter not configured",
            error_type="adapter_missing",
            suggestions=["Run setup wizard", "Configure adapter"],
        )

        assert result.valid is False
        assert result.error == "Adapter not configured"
        assert result.error_type == "adapter_missing"
        assert len(result.suggestions) == 2
