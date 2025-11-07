"""GraphQL client management for Linear API."""

from __future__ import annotations

import asyncio
from typing import Any

try:
    from gql import Client, gql
    from gql.transport.exceptions import TransportError
    from gql.transport.httpx import HTTPXAsyncTransport
except ImportError:
    # Handle missing gql dependency gracefully
    Client = None
    gql = None
    HTTPXAsyncTransport = None
    TransportError = Exception

from ...core.exceptions import AdapterError, AuthenticationError, RateLimitError


class LinearGraphQLClient:
    """GraphQL client for Linear API with error handling and retry logic."""

    def __init__(self, api_key: str, timeout: int = 30):
        """Initialize the Linear GraphQL client.

        Args:
            api_key: Linear API key
            timeout: Request timeout in seconds

        """
        self.api_key = api_key
        self.timeout = timeout
        self._base_url = "https://api.linear.app/graphql"

    def create_client(self) -> Client:
        """Create a new GraphQL client instance.

        Returns:
            Configured GraphQL client

        Raises:
            AuthenticationError: If API key is invalid
            AdapterError: If client creation fails

        """
        if Client is None:
            raise AdapterError(
                "gql library not installed. Install with: pip install gql[httpx]",
                "linear",
            )

        if not self.api_key:
            raise AuthenticationError("Linear API key is required", "linear")

        try:
            # Create transport with authentication
            # Linear API keys are passed directly (no Bearer prefix)
            # Only OAuth tokens use Bearer scheme
            transport = HTTPXAsyncTransport(
                url=self._base_url,
                headers={"Authorization": self.api_key},
                timeout=self.timeout,
            )

            # Create client
            client = Client(transport=transport, fetch_schema_from_transport=False)
            return client

        except Exception as e:
            raise AdapterError(f"Failed to create Linear client: {e}", "linear")

    async def execute_query(
        self,
        query_string: str,
        variables: dict[str, Any] | None = None,
        retries: int = 3,
    ) -> dict[str, Any]:
        """Execute a GraphQL query with error handling and retries.

        Args:
            query_string: GraphQL query string
            variables: Query variables
            retries: Number of retry attempts

        Returns:
            Query result data

        Raises:
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit is exceeded
            AdapterError: If query execution fails

        """
        query = gql(query_string)

        for attempt in range(retries + 1):
            try:
                client = self.create_client()
                async with client as session:
                    result = await session.execute(
                        query, variable_values=variables or {}
                    )
                return result

            except TransportError as e:
                # Handle HTTP errors
                if hasattr(e, "response") and e.response:
                    status_code = e.response.status

                    if status_code == 401:
                        raise AuthenticationError("Invalid Linear API key", "linear")
                    elif status_code == 403:
                        raise AuthenticationError("Insufficient permissions", "linear")
                    elif status_code == 429:
                        # Rate limit exceeded
                        retry_after = e.response.headers.get("Retry-After", "60")
                        raise RateLimitError(
                            "Linear API rate limit exceeded", "linear", retry_after
                        )
                    elif status_code >= 500:
                        # Server error - retry
                        if attempt < retries:
                            await asyncio.sleep(2**attempt)  # Exponential backoff
                            continue
                        raise AdapterError(
                            f"Linear API server error: {status_code}", "linear"
                        )

                # Network or other transport error
                if attempt < retries:
                    await asyncio.sleep(2**attempt)
                    continue
                raise AdapterError(f"Linear API transport error: {e}", "linear")

            except Exception as e:
                # GraphQL or other errors
                error_msg = str(e)

                # Check for specific GraphQL errors
                if (
                    "authentication" in error_msg.lower()
                    or "unauthorized" in error_msg.lower()
                ):
                    raise AuthenticationError(
                        f"Linear authentication failed: {error_msg}", "linear"
                    )
                elif "rate limit" in error_msg.lower():
                    raise RateLimitError("Linear API rate limit exceeded", "linear")

                # Generic error
                if attempt < retries:
                    await asyncio.sleep(2**attempt)
                    continue
                raise AdapterError(f"Linear GraphQL error: {error_msg}", "linear")

        # Should never reach here
        raise AdapterError("Maximum retries exceeded", "linear")

    async def execute_mutation(
        self,
        mutation_string: str,
        variables: dict[str, Any] | None = None,
        retries: int = 3,
    ) -> dict[str, Any]:
        """Execute a GraphQL mutation with error handling.

        Args:
            mutation_string: GraphQL mutation string
            variables: Mutation variables
            retries: Number of retry attempts

        Returns:
            Mutation result data

        Raises:
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit is exceeded
            AdapterError: If mutation execution fails

        """
        return await self.execute_query(mutation_string, variables, retries)

    async def test_connection(self) -> bool:
        """Test the connection to Linear API.

        Returns:
            True if connection is successful, False otherwise

        """
        try:
            # Simple query to test authentication
            test_query = """
                query TestConnection {
                    viewer {
                        id
                        name
                    }
                }
            """

            result = await self.execute_query(test_query)
            return bool(result.get("viewer"))

        except Exception:
            return False

    async def get_team_info(self, team_id: str) -> dict[str, Any] | None:
        """Get team information by ID.

        Args:
            team_id: Linear team ID

        Returns:
            Team information or None if not found

        """
        try:
            query = """
                query GetTeam($teamId: String!) {
                    team(id: $teamId) {
                        id
                        name
                        key
                        description
                    }
                }
            """

            result = await self.execute_query(query, {"teamId": team_id})
            return result.get("team")

        except Exception:
            return None

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        """Get user information by email.

        Args:
            email: User email address

        Returns:
            User information or None if not found

        """
        try:
            query = """
                query GetUserByEmail($email: String!) {
                    users(filter: { email: { eq: $email } }) {
                        nodes {
                            id
                            name
                            email
                            displayName
                            avatarUrl
                        }
                    }
                }
            """

            result = await self.execute_query(query, {"email": email})
            users = result.get("users", {}).get("nodes", [])
            return users[0] if users else None

        except Exception:
            return None

    async def close(self) -> None:
        """Close the client connection.

        Since we create fresh clients for each operation, there's no persistent
        connection to close. Each client's transport is automatically closed when
        the async context manager exits.
        """
        pass
