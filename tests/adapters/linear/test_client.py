"""Unit tests for Linear GraphQL client."""

from unittest.mock import AsyncMock, patch

import pytest

from mcp_ticketer.adapters.linear.client import LinearGraphQLClient
from mcp_ticketer.core.exceptions import (
    AdapterError,
    AuthenticationError,
    RateLimitError,
)


@pytest.mark.unit
class TestLinearGraphQLClient:
    """Test Linear GraphQL client functionality."""

    def test_init(self) -> None:
        """Test client initialization."""
        client = LinearGraphQLClient("lin_api_test_key_12345")

        assert client.api_key == "lin_api_test_key_12345"
        assert client.timeout == 30
        assert client._base_url == "https://api.linear.app/graphql"

    def test_init_with_custom_timeout(self) -> None:
        """Test client initialization with custom timeout."""
        client = LinearGraphQLClient("lin_api_test_key_12345", timeout=60)

        assert client.timeout == 60

    @patch("mcp_ticketer.adapters.linear.client.Client")
    @patch("mcp_ticketer.adapters.linear.client.HTTPXAsyncTransport")
    def test_create_client_success(self, mock_transport, mock_client) -> None:
        """Test successful client creation."""
        client = LinearGraphQLClient("lin_api_test_key_12345")

        result = client.create_client()

        # Verify transport was created with correct parameters
        mock_transport.assert_called_once_with(
            url="https://api.linear.app/graphql",
            headers={"Authorization": "lin_api_test_key_12345"},
            timeout=30,
        )

        # Verify client was created
        mock_client.assert_called_once()
        assert result == mock_client.return_value

    def test_create_client_no_api_key(self) -> None:
        """Test client creation without API key."""
        client = LinearGraphQLClient("")

        with pytest.raises(AuthenticationError) as exc_info:
            client.create_client()

        assert "Linear API key is required" in str(exc_info.value)
        assert exc_info.value.adapter_name == "linear"

    @patch("mcp_ticketer.adapters.linear.client.Client", None)
    def test_create_client_missing_gql(self) -> None:
        """Test client creation when gql library is missing."""
        client = LinearGraphQLClient("lin_api_test_key_12345")

        with pytest.raises(AdapterError) as exc_info:
            client.create_client()

        assert "gql library not installed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_query_success(self):
        """Test successful query execution."""
        client = LinearGraphQLClient("lin_api_test_key_12345")

        # Mock the GraphQL client and session
        mock_session = AsyncMock()
        mock_session.execute.return_value = {"data": "test"}

        mock_gql_client = AsyncMock()
        mock_gql_client.__aenter__.return_value = mock_session

        with patch.object(client, "create_client", return_value=mock_gql_client):
            with patch("mcp_ticketer.adapters.linear.client.gql") as mock_gql:
                mock_gql.return_value = "parsed_query"

                result = await client.execute_query("query { test }", {"var": "value"})

                assert result == {"data": "test"}
                mock_session.execute.assert_called_once_with(
                    "parsed_query", variable_values={"var": "value"}
                )

    @pytest.mark.asyncio
    async def test_execute_query_with_retries(self):
        """Test query execution with retries on failure."""
        client = LinearGraphQLClient("lin_api_test_key_12345")

        # Mock the GraphQL client and session
        mock_session = AsyncMock()
        # First call fails, second succeeds
        mock_session.execute.side_effect = [
            Exception("Network error"),
            {"data": "test"},
        ]

        mock_gql_client = AsyncMock()
        mock_gql_client.__aenter__.return_value = mock_session

        with patch.object(client, "create_client", return_value=mock_gql_client):
            with patch("mcp_ticketer.adapters.linear.client.gql") as mock_gql:
                with patch("asyncio.sleep") as mock_sleep:
                    mock_gql.return_value = "parsed_query"

                    result = await client.execute_query("query { test }", retries=1)

                    assert result == {"data": "test"}
                    assert mock_session.execute.call_count == 2
                    mock_sleep.assert_called_once_with(1)  # 2^0 = 1

    @pytest.mark.asyncio
    async def test_execute_query_authentication_error(self):
        """Test query execution with authentication error."""
        client = LinearGraphQLClient("lin_api_test_key_12345")

        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("authentication failed")

        mock_gql_client = AsyncMock()
        mock_gql_client.__aenter__.return_value = mock_session

        with patch.object(client, "create_client", return_value=mock_gql_client):
            with patch("mcp_ticketer.adapters.linear.client.gql"):
                with pytest.raises(AuthenticationError) as exc_info:
                    await client.execute_query("query { test }")

                assert "Linear authentication failed" in str(exc_info.value)
                assert exc_info.value.adapter_name == "linear"

    @pytest.mark.asyncio
    async def test_execute_query_rate_limit_error(self):
        """Test query execution with rate limit error."""
        client = LinearGraphQLClient("lin_api_test_key_12345")

        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("rate limit exceeded")

        mock_gql_client = AsyncMock()
        mock_gql_client.__aenter__.return_value = mock_session

        with patch.object(client, "create_client", return_value=mock_gql_client):
            with patch("mcp_ticketer.adapters.linear.client.gql"):
                with pytest.raises(RateLimitError) as exc_info:
                    await client.execute_query("query { test }")

                assert "Linear API rate limit exceeded" in str(exc_info.value)
                assert exc_info.value.adapter_name == "linear"

    @pytest.mark.asyncio
    async def test_execute_query_max_retries_exceeded(self):
        """Test query execution when max retries are exceeded."""
        client = LinearGraphQLClient("lin_api_test_key_12345")

        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Network error")

        mock_gql_client = AsyncMock()
        mock_gql_client.__aenter__.return_value = mock_session

        with patch.object(client, "create_client", return_value=mock_gql_client):
            with patch("mcp_ticketer.adapters.linear.client.gql"):
                with patch("asyncio.sleep"):
                    with pytest.raises(AdapterError) as exc_info:
                        await client.execute_query("query { test }", retries=2)

                    assert "Linear GraphQL error" in str(exc_info.value)
                    assert mock_session.execute.call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_execute_mutation(self):
        """Test mutation execution."""
        client = LinearGraphQLClient("lin_api_test_key_12345")

        with patch.object(client, "execute_query") as mock_execute:
            mock_execute.return_value = {"mutation": "result"}

            result = await client.execute_mutation(
                "mutation { test }", {"var": "value"}, retries=2
            )

            assert result == {"mutation": "result"}
            mock_execute.assert_called_once_with(
                "mutation { test }", {"var": "value"}, 2
            )

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful connection test."""
        client = LinearGraphQLClient("lin_api_test_key_12345")

        with patch.object(client, "execute_query") as mock_execute:
            mock_execute.return_value = {"viewer": {"id": "user-123"}}

            result = await client.test_connection()

            assert result is True
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """Test connection test failure."""
        client = LinearGraphQLClient("lin_api_test_key_12345")

        with patch.object(client, "execute_query") as mock_execute:
            mock_execute.side_effect = Exception("Connection failed")

            result = await client.test_connection()

            assert result is False

    @pytest.mark.asyncio
    async def test_get_team_info_success(self):
        """Test successful team info retrieval."""
        client = LinearGraphQLClient("lin_api_test_key_12345")

        expected_team = {
            "id": "team-123",
            "name": "Test Team",
            "key": "TEST",
            "description": "Test team description",
        }

        with patch.object(client, "execute_query") as mock_execute:
            mock_execute.return_value = {"team": expected_team}

            result = await client.get_team_info("team-123")

            assert result == expected_team

    @pytest.mark.asyncio
    async def test_get_team_info_not_found(self):
        """Test team info retrieval when team not found."""
        client = LinearGraphQLClient("lin_api_test_key_12345")

        with patch.object(client, "execute_query") as mock_execute:
            mock_execute.side_effect = Exception("Team not found")

            result = await client.get_team_info("nonexistent-team")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_user_by_email_success(self):
        """Test successful user retrieval by email."""
        client = LinearGraphQLClient("lin_api_test_key_12345")

        expected_user = {
            "id": "user-123",
            "name": "Test User",
            "email": "test@example.com",
            "displayName": "Test User",
            "avatarUrl": "https://example.com/avatar.jpg",
        }

        with patch.object(client, "execute_query") as mock_execute:
            mock_execute.return_value = {"users": {"nodes": [expected_user]}}

            result = await client.get_user_by_email("test@example.com")

            assert result == expected_user

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self):
        """Test user retrieval when user not found."""
        client = LinearGraphQLClient("lin_api_test_key_12345")

        with patch.object(client, "execute_query") as mock_execute:
            mock_execute.return_value = {"users": {"nodes": []}}

            result = await client.get_user_by_email("nonexistent@example.com")

            assert result is None

    @pytest.mark.asyncio
    async def test_close(self):
        """Test client close method."""
        client = LinearGraphQLClient("lin_api_test_key_12345")

        # Should not raise any exceptions
        await client.close()
