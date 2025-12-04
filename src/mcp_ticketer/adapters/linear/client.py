"""GraphQL client management for Linear API."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

try:
    from gql import Client, gql
    from gql.transport.exceptions import TransportError, TransportQueryError
    from gql.transport.httpx import HTTPXAsyncTransport
except ImportError:
    # Handle missing gql dependency gracefully
    Client = None
    gql = None
    HTTPXAsyncTransport = None
    TransportError = Exception
    TransportQueryError = Exception

from ...core.exceptions import AdapterError, AuthenticationError, RateLimitError

logger = logging.getLogger(__name__)


class LinearGraphQLClient:
    """GraphQL client for Linear API with error handling and retry logic."""

    def __init__(self, api_key: str, timeout: int = 30):
        """Initialize the Linear GraphQL client.

        Args:
        ----
            api_key: Linear API key
            timeout: Request timeout in seconds

        """
        self.api_key = api_key
        self.timeout = timeout
        self._base_url = "https://api.linear.app/graphql"

    def create_client(self) -> Client:
        """Create a new GraphQL client instance.

        Returns:
        -------
            Configured GraphQL client

        Raises:
        ------
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
            raise AdapterError(f"Failed to create Linear client: {e}", "linear") from e

    async def execute_query(
        self,
        query_string: str,
        variables: dict[str, Any] | None = None,
        retries: int = 3,
    ) -> dict[str, Any]:
        """Execute a GraphQL query with error handling and retries.

        Args:
        ----
            query_string: GraphQL query string
            variables: Query variables
            retries: Number of retry attempts

        Returns:
        -------
            Query result data

        Raises:
        ------
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit is exceeded
            AdapterError: If query execution fails

        """
        query = gql(query_string)

        # Extract operation name from query for logging
        operation_name = "unknown"
        try:
            # Simple extraction - look for 'query' or 'mutation' keyword
            query_lower = query_string.strip().lower()
            if query_lower.startswith("mutation"):
                operation_name = (
                    query_string.split("{")[0].strip().replace("mutation", "").strip()
                )
            elif query_lower.startswith("query"):
                operation_name = (
                    query_string.split("{")[0].strip().replace("query", "").strip()
                )
        except Exception:
            pass  # Use default 'unknown' if extraction fails

        for attempt in range(retries + 1):
            try:
                # Log request details before execution
                logger.debug(
                    f"[Linear GraphQL] Executing operation: {operation_name}\n"
                    f"Variables:\n{json.dumps(variables or {}, indent=2, default=str)}"
                )

                client = self.create_client()
                async with client as session:
                    result = await session.execute(
                        query, variable_values=variables or {}
                    )

                # Log successful response
                logger.debug(
                    f"[Linear GraphQL] Operation successful: {operation_name}\n"
                    f"Response:\n{json.dumps(result, indent=2, default=str)}"
                )

                return result

            except TransportQueryError as e:
                """
                Handle GraphQL validation errors (e.g., duplicate label names).
                TransportQueryError is a subclass of TransportError with .errors attribute.

                Related: 1M-398 - Label duplicate error handling
                """
                # Log detailed error information
                logger.error(
                    f"[Linear GraphQL] TransportQueryError occurred\n"
                    f"Operation: {operation_name}\n"
                    f"Variables:\n{json.dumps(variables or {}, indent=2, default=str)}\n"
                    f"Error: {e}\n"
                    f"Error details: {e.errors if hasattr(e, 'errors') else 'No error details'}"
                )

                if e.errors:
                    error = e.errors[0]
                    error_msg = error.get("message", "Unknown GraphQL error")

                    # Parse extensions for field-specific details (enhanced debugging)
                    extensions = error.get("extensions", {})

                    # Check for user-presentable message (clearer error for users)
                    user_message = extensions.get("userPresentableMessage")
                    if user_message:
                        error_msg = user_message

                    # Check for argument path (which field failed validation)
                    arg_path = extensions.get("argumentPath")
                    if arg_path:
                        field_path = ".".join(str(p) for p in arg_path)
                        error_msg = f"{error_msg} (field: {field_path})"

                    # Check for validation errors (additional context)
                    validation_errors = extensions.get("validationErrors")
                    if validation_errors:
                        error_msg = (
                            f"{error_msg}\nValidation errors: {validation_errors}"
                        )

                    # Log full error context for debugging
                    logger.error(
                        "Linear GraphQL error: %s (extensions: %s)",
                        error_msg,
                        extensions,
                    )

                    # Check for duplicate label errors specifically
                    if (
                        "duplicate" in error_msg.lower()
                        and "label" in error_msg.lower()
                    ):
                        raise AdapterError(
                            f"Label already exists: {error_msg}", "linear"
                        ) from e

                    # Other validation errors
                    raise AdapterError(
                        f"Linear GraphQL validation error: {error_msg}", "linear"
                    ) from e

                # Fallback if no errors attribute
                raise AdapterError(f"Linear GraphQL error: {e}", "linear") from e

            except TransportError as e:
                # Log transport error details
                logger.error(
                    f"[Linear GraphQL] TransportError occurred\n"
                    f"Operation: {operation_name}\n"
                    f"Variables:\n{json.dumps(variables or {}, indent=2, default=str)}\n"
                    f"Error: {e}\n"
                    f"Status code: {e.response.status if hasattr(e, 'response') and e.response else 'N/A'}"
                )

                # Handle HTTP errors
                if hasattr(e, "response") and e.response:
                    status_code = e.response.status

                    if status_code == 401:
                        raise AuthenticationError(
                            "Invalid Linear API key", "linear"
                        ) from e
                    elif status_code == 403:
                        raise AuthenticationError(
                            "Insufficient permissions", "linear"
                        ) from e
                    elif status_code == 429:
                        # Rate limit exceeded
                        retry_after = e.response.headers.get("Retry-After", "60")
                        raise RateLimitError(
                            "Linear API rate limit exceeded", "linear", retry_after
                        ) from e
                    elif status_code >= 500:
                        # Server error - retry
                        if attempt < retries:
                            await asyncio.sleep(2**attempt)  # Exponential backoff
                            continue
                        raise AdapterError(
                            f"Linear API server error: {status_code}", "linear"
                        ) from e

                # Network or other transport error
                if attempt < retries:
                    await asyncio.sleep(2**attempt)
                    continue
                raise AdapterError(f"Linear API transport error: {e}", "linear") from e

            except Exception as e:
                # Log generic error details
                logger.error(
                    f"[Linear GraphQL] Unexpected error occurred\n"
                    f"Operation: {operation_name}\n"
                    f"Variables:\n{json.dumps(variables or {}, indent=2, default=str)}\n"
                    f"Error type: {type(e).__name__}\n"
                    f"Error: {e}",
                    exc_info=True,
                )

                # GraphQL or other errors
                error_msg = str(e)

                # Check for specific GraphQL errors
                if (
                    "authentication" in error_msg.lower()
                    or "unauthorized" in error_msg.lower()
                ):
                    raise AuthenticationError(
                        f"Linear authentication failed: {error_msg}", "linear"
                    ) from e
                elif "rate limit" in error_msg.lower():
                    raise RateLimitError(
                        "Linear API rate limit exceeded", "linear"
                    ) from e

                # Generic error
                if attempt < retries:
                    await asyncio.sleep(2**attempt)
                    continue
                raise AdapterError(
                    f"Linear GraphQL error: {error_msg}", "linear"
                ) from e

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
        ----
            mutation_string: GraphQL mutation string
            variables: Mutation variables
            retries: Number of retry attempts

        Returns:
        -------
            Mutation result data

        Raises:
        ------
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit is exceeded
            AdapterError: If mutation execution fails

        """
        return await self.execute_query(mutation_string, variables, retries)

    async def test_connection(self) -> bool:
        """Test the connection to Linear API.

        Returns:
        -------
            True if connection is successful, False otherwise

        Design Decision: Enhanced Debug Logging (1M-431)
        -------------------------------------------------
        Added comprehensive logging to diagnose connection failures.
        Logs API key preview, query results, and specific failure reasons
        to help users troubleshoot authentication and configuration issues.

        """
        import logging

        logger = logging.getLogger(__name__)

        try:
            # Simple query to test authentication
            test_query = """
                query TestConnection {
                    viewer {
                        id
                        name
                        email
                    }
                }
            """

            logger.debug(
                f"Testing Linear API connection with API key: {self.api_key[:20]}..."
            )
            result = await self.execute_query(test_query)

            # Log the actual response for debugging
            logger.debug(f"Linear API test response: {result}")

            viewer = result.get("viewer")

            if not viewer:
                logger.warning(
                    f"Linear test connection query succeeded but returned no viewer data. "
                    f"Response: {result}"
                )
                return False

            if not viewer.get("id"):
                logger.warning(f"Linear viewer missing id field. Viewer data: {viewer}")
                return False

            logger.info(
                f"Linear API connected successfully as: {viewer.get('name')} ({viewer.get('email')})"
            )
            return True

        except Exception as e:
            logger.error(
                f"Linear connection test failed: {type(e).__name__}: {e}",
                exc_info=True,
            )
            return False

    async def get_team_info(self, team_id: str) -> dict[str, Any] | None:
        """Get team information by ID.

        Args:
        ----
            team_id: Linear team ID

        Returns:
        -------
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
        ----
            email: User email address

        Returns:
        -------
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

    async def get_users_by_name(self, name: str) -> list[dict[str, Any]]:
        """Search users by display name or full name.

        Args:
        ----
            name: Display name or full name to search for

        Returns:
        -------
            List of matching users (may be empty)

        """
        import logging

        try:
            query = """
                query SearchUsers($nameFilter: String!) {
                    users(
                        filter: {
                            or: [
                                { displayName: { containsIgnoreCase: $nameFilter } }
                                { name: { containsIgnoreCase: $nameFilter } }
                            ]
                        }
                        first: 10
                    ) {
                        nodes {
                            id
                            name
                            email
                            displayName
                            avatarUrl
                            active
                        }
                    }
                }
            """

            result = await self.execute_query(query, {"nameFilter": name})
            users = result.get("users", {}).get("nodes", [])
            return [u for u in users if u.get("active", True)]  # Filter active users

        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to search users by name: {e}")
            return []

    async def close(self) -> None:
        """Close the client connection.

        Since we create fresh clients for each operation, there's no persistent
        connection to close. Each client's transport is automatically closed when
        the async context manager exits.
        """
        pass
