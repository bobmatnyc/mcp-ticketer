"""Test URL support in TicketerConfig for default_project field."""

from mcp_ticketer.core.project_config import TicketerConfig


class TestTicketerConfigURLSupport:
    """Test TicketerConfig URL parsing and normalization."""

    def test_plain_id_unchanged(self) -> None:
        """Test plain IDs remain unchanged."""
        config = TicketerConfig(default_adapter="linear", default_project="PROJ-123")
        assert config.default_project == "PROJ-123"

    def test_linear_project_url_normalization(self) -> None:
        """Test Linear project URL gets normalized to ID."""
        config = TicketerConfig(
            default_adapter="linear",
            default_project="https://linear.app/travel-bta/project/crm-system-f59a41",
        )
        assert config.default_project == "crm-system-f59a41"

    def test_linear_issue_url_normalization(self) -> None:
        """Test Linear issue URL gets normalized to ID."""
        config = TicketerConfig(
            default_adapter="linear",
            default_project="https://linear.app/myteam/issue/BTA-123",
        )
        assert config.default_project == "BTA-123"

    def test_jira_url_normalization(self) -> None:
        """Test JIRA URL gets normalized to project key."""
        config = TicketerConfig(
            default_adapter="jira",
            default_project="https://company.atlassian.net/browse/PROJ-456",
        )
        assert config.default_project == "PROJ-456"

    def test_github_url_normalization(self) -> None:
        """Test GitHub URL gets normalized to project number."""
        config = TicketerConfig(
            default_adapter="github",
            default_project="https://github.com/owner/repo/projects/1",
        )
        assert config.default_project == "1"

    def test_default_epic_normalization(self) -> None:
        """Test default_epic field also gets normalized."""
        config = TicketerConfig(
            default_adapter="linear",
            default_epic="https://linear.app/team/project/epic-abc123",
        )
        assert config.default_epic == "epic-abc123"

    def test_from_dict_normalizes_urls(self) -> None:
        """Test URLs are normalized when loading from dict."""
        config_data = {
            "default_adapter": "linear",
            "default_project": "https://linear.app/team/project/test-project-xyz789",
            "adapters": {},
            "project_configs": {},
        }
        config = TicketerConfig.from_dict(config_data)
        assert config.default_project == "test-project-xyz789"

    def test_to_dict_stores_normalized_id(self) -> None:
        """Test normalized IDs are stored in dict representation."""
        config = TicketerConfig(
            default_adapter="jira",
            default_project="https://company.atlassian.net/browse/ABC-999",
        )
        config_dict = config.to_dict()
        assert config_dict["default_project"] == "ABC-999"

    def test_round_trip_serialization(self) -> None:
        """Test config can be serialized and deserialized with URLs."""
        original_config = TicketerConfig(
            default_adapter="linear",
            default_project="https://linear.app/team/issue/TEST-100",
        )

        # Convert to dict and back
        config_dict = original_config.to_dict()
        restored_config = TicketerConfig.from_dict(config_dict)

        # Should have normalized ID (not original URL)
        assert restored_config.default_project == "TEST-100"
        assert restored_config.default_adapter == "linear"

    def test_numeric_id_unchanged(self) -> None:
        """Test numeric IDs (like GitHub project numbers) remain unchanged."""
        config = TicketerConfig(default_adapter="github", default_project="123")
        assert config.default_project == "123"

    def test_none_default_project(self) -> None:
        """Test None value for default_project doesn't cause errors."""
        config = TicketerConfig(default_adapter="linear", default_project=None)
        assert config.default_project is None

    def test_empty_string_default_project(self) -> None:
        """Test empty string for default_project doesn't cause errors."""
        config = TicketerConfig(default_adapter="linear", default_project="")
        # Empty string should be preserved (not normalized to None)
        assert config.default_project == ""

    def test_invalid_url_falls_back_to_original(self) -> None:
        """Test invalid URLs fall back to original value with warning."""
        # This URL doesn't match any known pattern
        invalid_url = "https://unknown.com/project/123"
        config = TicketerConfig(default_adapter="linear", default_project=invalid_url)
        # Should keep original value when normalization fails
        assert config.default_project == invalid_url

    def test_auto_detect_adapter_from_url(self) -> None:
        """Test adapter auto-detection from URL when using default adapter."""
        # Even with aitrackdown as default, should detect Linear URL
        config = TicketerConfig(
            default_adapter="aitrackdown",
            default_project="https://linear.app/team/project/abc-123",
        )
        # Should extract ID from Linear URL despite different default adapter
        assert config.default_project == "abc-123"


class TestBackwardCompatibility:
    """Test backward compatibility with existing configurations."""

    def test_existing_plain_ids_work(self) -> None:
        """Test existing configs with plain IDs continue to work."""
        test_cases = [
            ("linear", "BTA-123"),
            ("jira", "PROJ-456"),
            ("github", "789"),
            ("aitrackdown", "task-001"),
        ]

        for adapter, project_id in test_cases:
            config = TicketerConfig(default_adapter=adapter, default_project=project_id)
            assert config.default_project == project_id

    def test_config_without_default_project(self) -> None:
        """Test configs without default_project field work."""
        config = TicketerConfig(default_adapter="linear")
        assert config.default_project is None

    def test_minimal_config(self) -> None:
        """Test minimal config with only required fields."""
        config = TicketerConfig()
        assert config.default_adapter == "aitrackdown"
        assert config.default_project is None
        assert config.default_epic is None

    def test_load_existing_config_format(self) -> None:
        """Test loading config in existing format (no URLs)."""
        config_data = {
            "default_adapter": "jira",
            "project_configs": {},
            "adapters": {
                "jira": {
                    "adapter": "jira",
                    "server": "https://company.atlassian.net",
                    "email": "user@example.com",
                    "api_token": "token123",
                }
            },
            "default_project": "MYPROJ",
        }

        config = TicketerConfig.from_dict(config_data)
        assert config.default_project == "MYPROJ"
        assert config.default_adapter == "jira"


class TestURLExamples:
    """Test real-world URL examples."""

    def test_linear_workspace_url_variations(self) -> None:
        """Test various Linear workspace URL formats."""
        test_cases = [
            # Project URLs
            ("https://linear.app/1m-hyperdev/project/web-app-abc123", "web-app-abc123"),
            ("https://linear.app/company/project/feature-xyz/overview", "feature-xyz"),
            # Issue URLs
            ("https://linear.app/myteam/issue/ENG-100", "ENG-100"),
            ("https://linear.app/workspace/issue/BUG-42", "BUG-42"),
            # Team URLs
            ("https://linear.app/org/team/SALES", "SALES"),
            ("https://linear.app/company/team/ENG/active", "ENG"),
        ]

        for url, expected_id in test_cases:
            config = TicketerConfig(default_adapter="linear", default_project=url)
            assert config.default_project == expected_id, f"Failed for URL: {url}"

    def test_jira_url_variations(self) -> None:
        """Test various JIRA URL formats."""
        test_cases = [
            # Cloud JIRA
            ("https://mycompany.atlassian.net/browse/PROJ", "PROJ"),
            ("https://team.atlassian.net/browse/ISSUE-123", "ISSUE-123"),
            # Self-hosted JIRA
            ("https://jira.company.com/browse/ABC-456", "ABC-456"),
            # Projects page
            ("https://company.atlassian.net/projects/MYPROJ", "MYPROJ"),
        ]

        for url, expected_id in test_cases:
            config = TicketerConfig(default_adapter="jira", default_project=url)
            assert config.default_project == expected_id, f"Failed for URL: {url}"

    def test_github_url_variations(self) -> None:
        """Test various GitHub URL formats."""
        test_cases = [
            # Projects
            ("https://github.com/owner/repo/projects/1", "1"),
            ("https://github.com/my-org/my-repo/projects/42", "42"),
            # Issues
            ("https://github.com/user/project/issues/100", "100"),
            # Pull requests
            ("https://github.com/org/service/pull/999", "999"),
        ]

        for url, expected_id in test_cases:
            config = TicketerConfig(default_adapter="github", default_project=url)
            assert config.default_project == expected_id, f"Failed for URL: {url}"
