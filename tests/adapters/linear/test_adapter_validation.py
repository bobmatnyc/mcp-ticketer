"""Unit tests for Linear adapter configuration validation."""

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter


@pytest.mark.unit
class TestLinearAdapterAPIKeyValidation:
    """Test Linear adapter API key validation and cleaning."""

    def test_api_key_with_linear_api_key_prefix(self) -> None:
        """Test that API key with LINEAR_API_KEY= prefix is stripped."""
        config = {
            "api_key": "LINEAR_API_KEY=lin_api_test123",
            "team_id": "test-team-id",
        }

        adapter = LinearAdapter(config)

        assert adapter.api_key == "lin_api_test123"

    def test_api_key_with_api_key_prefix(self) -> None:
        """Test that API key with API_KEY= prefix is stripped."""
        config = {
            "api_key": "API_KEY=lin_api_test456",
            "team_id": "test-team-id",
        }

        adapter = LinearAdapter(config)

        assert adapter.api_key == "lin_api_test456"

    def test_api_key_with_bearer_prefix(self) -> None:
        """Test that API key with Bearer prefix is stripped."""
        config = {
            "api_key": "Bearer lin_api_test789",
            "team_id": "test-team-id",
        }

        adapter = LinearAdapter(config)

        assert adapter.api_key == "lin_api_test789"

    def test_api_key_with_multiple_prefixes(self) -> None:
        """Test that API key with multiple prefixes is cleaned."""
        # Bearer is removed first, then env var prefix
        config = {
            "api_key": "Bearer LINEAR_API_KEY=lin_api_multi",
            "team_id": "test-team-id",
        }

        adapter = LinearAdapter(config)

        assert adapter.api_key == "lin_api_multi"

    def test_invalid_api_key_format_raises_error(self) -> None:
        """Test that invalid API key format raises ValueError."""
        config = {
            "api_key": "invalid_key_format",
            "team_id": "test-team-id",
        }

        with pytest.raises(ValueError) as exc_info:
            LinearAdapter(config)

        assert "Invalid Linear API key format" in str(exc_info.value)
        assert "lin_api_" in str(exc_info.value)

    def test_invalid_key_with_env_var_prefix_raises_error(self) -> None:
        """Test that invalid key format with env var prefix still raises error."""
        config = {
            "api_key": "LINEAR_API_KEY=invalid_format",
            "team_id": "test-team-id",
        }

        with pytest.raises(ValueError) as exc_info:
            LinearAdapter(config)

        assert "Invalid Linear API key format" in str(exc_info.value)

    def test_clean_api_key_unchanged(self) -> None:
        """Test that clean API key is not modified."""
        config = {
            "api_key": "lin_api_clean_key_12345",
            "team_id": "test-team-id",
        }

        adapter = LinearAdapter(config)

        assert adapter.api_key == "lin_api_clean_key_12345"

    def test_api_key_with_other_env_var_name_not_stripped(self) -> None:
        """Test that env var prefix other than API_KEY/LINEAR_API_KEY is not stripped."""
        # This should fail validation since OTHER_VAR= won't be stripped
        config = {
            "api_key": "OTHER_VAR=lin_api_test",
            "team_id": "test-team-id",
        }

        with pytest.raises(ValueError) as exc_info:
            LinearAdapter(config)

        assert "Invalid Linear API key format" in str(exc_info.value)

    def test_case_insensitive_env_var_prefix_stripping(self) -> None:
        """Test that env var prefix stripping is case-insensitive."""
        config = {
            "api_key": "linear_api_key=lin_api_lowercase",
            "team_id": "test-team-id",
        }

        adapter = LinearAdapter(config)

        assert adapter.api_key == "lin_api_lowercase"

    def test_api_key_with_equals_in_value(self) -> None:
        """Test that equals sign in actual key value is preserved."""
        # If there's an equals sign that's not part of an env var prefix
        # it should be kept (though this is unlikely in real Linear keys)
        config = {
            "api_key": "lin_api_key_with=equals",
            "team_id": "test-team-id",
        }

        adapter = LinearAdapter(config)

        # The key starts with lin_api_ so it passes validation
        # The equals is not part of a recognized env var prefix so it's kept
        assert adapter.api_key == "lin_api_key_with=equals"


@pytest.mark.unit
class TestLinearAdapterTeamConfiguration:
    """Test Linear adapter team configuration validation."""

    def test_missing_team_key_and_team_id_raises_error(self) -> None:
        """Test that missing both team_key and team_id raises ValueError."""
        config = {
            "api_key": "lin_api_test123",
        }

        with pytest.raises(ValueError) as exc_info:
            LinearAdapter(config)

        assert "team_key or team_id must be provided" in str(exc_info.value)

    def test_team_key_only(self) -> None:
        """Test that team_key alone is sufficient."""
        config = {
            "api_key": "lin_api_test123",
            "team_key": "TEST",
        }

        adapter = LinearAdapter(config)

        assert adapter.team_key == "TEST"
        assert adapter.team_id is None

    def test_team_id_only(self) -> None:
        """Test that team_id alone is sufficient."""
        config = {
            "api_key": "lin_api_test123",
            "team_id": "test-uuid-123",
        }

        adapter = LinearAdapter(config)

        assert adapter.team_id == "test-uuid-123"
        assert adapter.team_key is None

    def test_both_team_key_and_team_id(self) -> None:
        """Test that both team_key and team_id can be provided."""
        config = {
            "api_key": "lin_api_test123",
            "team_key": "TEST",
            "team_id": "test-uuid-123",
        }

        adapter = LinearAdapter(config)

        assert adapter.team_key == "TEST"
        assert adapter.team_id == "test-uuid-123"
