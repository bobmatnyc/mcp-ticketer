"""HTTP and GraphQL client for GitHub API.

This module provides a unified client for both REST API v3 and GraphQL API v4,
with error handling, retry logic, and rate limiting support.

Design Decision: Dual API Client
---------------------------------
GitHub requires both REST and GraphQL APIs:
- REST API: For mutations (create/update/delete) and simple operations
- GraphQL API: For complex queries and efficient data fetching

Rationale:
- REST API is more stable and better documented for write operations
- GraphQL API reduces over-fetching and enables precise field selection
- Some features only available in one API (e.g., Projects V2 in GraphQL)

Trade-offs:
- Maintaining two client methods increases complexity
- GraphQL requires fragment management and query composition
- REST API can be chatty (multiple round trips for related data)

Error Handling Strategy:
-----------------------
- HTTP 401/403 → Authentication errors (fail fast)
- HTTP 429 → Rate limiting (could retry with backoff, currently fails fast)
- HTTP 5xx → Transient errors (fail fast, caller can retry)
- GraphQL errors → Validation errors (fail fast)
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class GitHubClient:
    """GitHub API client supporting both REST v3 and GraphQL v4.

    This client handles:
    - Authentication with Personal Access Tokens (PAT)
    - REST API requests with proper headers
    - GraphQL query execution
    - Error handling and HTTP status codes
    - Rate limit tracking (optional)

    Performance Notes:
    -----------------
    - Uses httpx.AsyncClient for async/await support
    - Connection pooling handled by httpx
    - Timeout: 30 seconds default
    - No automatic retries (caller should implement retry logic)

    Example:
    -------
        client = GitHubClient(
            token="ghp_xxxxx",
            owner="octocat",
            repo="hello-world"
        )

        # REST API
        response = await client.execute_rest("GET", "repos/octocat/hello-world")

        # GraphQL API
        data = await client.execute_graphql(query, variables)
    """

    def __init__(
        self,
        token: str,
        owner: str,
        repo: str,
        api_url: str = "https://api.github.com",
        timeout: float = 30.0,
    ):
        """Initialize GitHub API client.

        Args:
        ----
            token: GitHub Personal Access Token (PAT)
            owner: Repository owner (username or organization)
            repo: Repository name
            api_url: Base API URL (default: https://api.github.com)
            timeout: Request timeout in seconds (default: 30.0)
        """
        self.token = token
        self.owner = owner
        self.repo = repo
        self.api_url = api_url

        # GraphQL endpoint
        self.graphql_url = (
            f"{api_url}/graphql"
            if "github.com" in api_url
            else f"{api_url}/api/graphql"
        )

        # HTTP headers for authentication and API version
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        # Async HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            base_url=api_url,
            headers=self.headers,
            timeout=timeout,
        )

        # Rate limit tracking (optional, populated on API responses)
        self._rate_limit: dict[str, Any] = {}

    async def execute_rest(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Execute a REST API request.

        Args:
        ----
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint (e.g., "repos/owner/repo/issues")
            json_data: Optional JSON body for POST/PATCH requests
            params: Optional query parameters

        Returns:
        -------
            Parsed JSON response (dict or list)

        Raises:
        ------
            httpx.HTTPStatusError: On HTTP error status codes
            ValueError: On invalid JSON response

        Performance:
        -----------
            Time Complexity: O(1) for request, O(n) for JSON parsing
            Expected Latency: 100-500ms depending on GitHub API response time

        Example:
        -------
            # GET request
            issues = await client.execute_rest("GET", "repos/owner/repo/issues")

            # POST request
            issue = await client.execute_rest(
                "POST",
                "repos/owner/repo/issues",
                json_data={"title": "Bug", "body": "Description"}
            )
        """
        # Ensure endpoint starts with / for proper URL construction
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"

        logger.debug(f"REST {method} {endpoint}")

        try:
            response = await self.client.request(
                method=method,
                url=endpoint,
                json=json_data,
                params=params,
            )

            # Update rate limit information from headers
            self._update_rate_limit_from_headers(response.headers)

            # Raise for HTTP errors (4xx, 5xx)
            response.raise_for_status()

            # Parse JSON response
            if response.text:
                return response.json()
            return {}

        except httpx.HTTPStatusError as e:
            logger.error(
                f"REST API error: {method} {endpoint} -> "
                f"HTTP {e.response.status_code}: {e.response.text}"
            )
            # Let the error propagate - adapter should handle error translation
            raise

    async def execute_graphql(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a GraphQL query or mutation.

        Args:
        ----
            query: GraphQL query string (including fragments)
            variables: Optional query variables

        Returns:
        -------
            GraphQL response data (dict)

        Raises:
        ------
            httpx.HTTPStatusError: On HTTP error status codes
            ValueError: On GraphQL errors in response

        Performance:
        -----------
            Time Complexity: O(1) for request, O(n) for JSON parsing
            Expected Latency: 100-500ms depending on query complexity
            Token Usage: Depends on fragments used (compact vs. full)

        Example:
        -------
            data = await client.execute_graphql(
                query=GET_ISSUE,
                variables={"owner": "octocat", "repo": "hello-world", "number": 1}
            )
            issue = data["repository"]["issue"]
        """
        logger.debug(f"GraphQL query: {query[:100]}...")

        try:
            response = await self.client.post(
                self.graphql_url,
                json={"query": query, "variables": variables or {}},
            )

            # Update rate limit information
            self._update_rate_limit_from_headers(response.headers)

            # Raise for HTTP errors
            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            # Check for GraphQL-level errors
            if "errors" in data:
                error_messages = [
                    err.get("message", str(err)) for err in data["errors"]
                ]
                raise ValueError(f"GraphQL errors: {', '.join(error_messages)}")

            return data.get("data", {})

        except httpx.HTTPStatusError as e:
            logger.error(
                f"GraphQL API error: HTTP {e.response.status_code}: {e.response.text}"
            )
            raise

    async def test_connection(self) -> bool:
        """Test GitHub API connection and authentication.

        Returns:
        -------
            True if connection is valid, False otherwise

        Example:
        -------
            if await client.test_connection():
                print("GitHub connection successful")
        """
        try:
            await self.execute_rest("GET", "/user")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    async def get_rate_limit(self) -> dict[str, Any]:
        """Get current rate limit status.

        Returns:
        -------
            Rate limit information dict with keys:
            - limit: Maximum requests per hour
            - remaining: Remaining requests
            - reset: Unix timestamp when limit resets

        Example:
        -------
            rate_limit = await client.get_rate_limit()
            print(f"Remaining: {rate_limit['remaining']}/{rate_limit['limit']}")
        """
        response = await self.execute_rest("GET", "/rate_limit")
        return response.get("rate", {})

    def _update_rate_limit_from_headers(self, headers: httpx.Headers) -> None:
        """Extract rate limit info from response headers.

        GitHub includes rate limit information in response headers:
        - X-RateLimit-Limit: Maximum requests per hour
        - X-RateLimit-Remaining: Remaining requests
        - X-RateLimit-Reset: Unix timestamp when limit resets

        Args:
        ----
            headers: HTTP response headers
        """
        if "X-RateLimit-Limit" in headers:
            self._rate_limit = {
                "limit": int(headers["X-RateLimit-Limit"]),
                "remaining": int(headers.get("X-RateLimit-Remaining", 0)),
                "reset": int(headers.get("X-RateLimit-Reset", 0)),
            }

    async def close(self) -> None:
        """Close the HTTP client and cleanup resources.

        Should be called when adapter is no longer needed to avoid
        resource leaks.

        Example:
        -------
            await client.close()
        """
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - ensures cleanup."""
        await self.close()
