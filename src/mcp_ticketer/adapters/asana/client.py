"""Asana HTTP client for REST API v1.0."""

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class AsanaClient:
    """HTTP client for Asana REST API v1.0.

    Handles:
    - Bearer token authentication
    - Rate limiting (429 with Retry-After)
    - Pagination (offset tokens)
    - Error handling for all status codes
    - Request/Response wrapping ({"data": {...}})
    """

    BASE_URL = "https://app.asana.com/api/1.0"

    def __init__(self, api_key: str, timeout: int = 30, max_retries: int = 3):
        """Initialize Asana client.

        Args:
            api_key: Asana Personal Access Token (PAT)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for rate limiting

        """
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries

        # Setup headers
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # HTTP client (will be created on first use)
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client.

        Returns:
            Configured async HTTP client

        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers=self.headers,
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client

    async def _handle_rate_limit(self, response: httpx.Response, attempt: int) -> None:
        """Handle rate limiting with exponential backoff.

        Args:
            response: HTTP response with 429 status
            attempt: Current retry attempt number

        Raises:
            ValueError: If max retries exceeded

        """
        if attempt >= self.max_retries:
            raise ValueError(
                f"Max retries ({self.max_retries}) exceeded for rate limiting"
            )

        # Get retry-after header (in seconds)
        retry_after = int(response.headers.get("Retry-After", 60))
        logger.warning(
            f"Rate limited (429). Waiting {retry_after}s before retry {attempt + 1}/{self.max_retries}"
        )
        await asyncio.sleep(retry_after)

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request with retry logic for rate limiting.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            params: URL query parameters
            json: Request body JSON data

        Returns:
            Response data (unwrapped from {"data": {...}})

        Raises:
            ValueError: If request fails or max retries exceeded

        """
        client = await self._get_client()
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"

        # Wrap request body in {"data": {...}} for POST/PUT
        if json is not None and method in ("POST", "PUT"):
            json = {"data": json}

        for attempt in range(self.max_retries + 1):
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                )

                # Handle rate limiting
                if response.status_code == 429:
                    await self._handle_rate_limit(response, attempt)
                    continue

                # Handle errors
                if response.status_code >= 400:
                    error_detail = response.text
                    try:
                        error_json = response.json()
                        error_detail = error_json.get("errors", [{}])[0].get(
                            "message", error_detail
                        )
                    except Exception:
                        pass

                    raise ValueError(
                        f"Asana API error ({response.status_code}): {error_detail}"
                    )

                # Success - unwrap response
                response_data = response.json()

                # Asana wraps responses in {"data": {...}}
                if isinstance(response_data, dict) and "data" in response_data:
                    return response_data["data"]

                return response_data

            except httpx.TimeoutException as e:
                logger.error(f"Request timeout for {method} {url}: {e}")
                if attempt < self.max_retries:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise ValueError(
                        f"Request timeout after {self.max_retries} retries"
                    ) from e

            except httpx.HTTPError as e:
                logger.error(f"HTTP error for {method} {url}: {e}")
                raise ValueError(f"HTTP error: {e}") from e

        raise ValueError("Request failed after all retry attempts")

    async def get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make GET request.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Response data

        """
        return await self._request("GET", endpoint, params=params)

    async def post(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make POST request.

        Args:
            endpoint: API endpoint
            data: Request body data

        Returns:
            Response data

        """
        return await self._request("POST", endpoint, json=data)

    async def put(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make PUT request.

        Args:
            endpoint: API endpoint
            data: Request body data

        Returns:
            Response data

        """
        return await self._request("PUT", endpoint, json=data)

    async def delete(self, endpoint: str) -> dict[str, Any]:
        """Make DELETE request.

        Args:
            endpoint: API endpoint

        Returns:
            Response data

        """
        return await self._request("DELETE", endpoint)

    async def get_paginated(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get all pages of results using offset-based pagination.

        Args:
            endpoint: API endpoint
            params: Query parameters
            limit: Items per page (max 100)

        Returns:
            List of all results from all pages

        """
        if params is None:
            params = {}

        all_results = []
        offset = None

        while True:
            # Set pagination params
            page_params = params.copy()
            page_params["limit"] = min(limit, 100)  # Max 100 per page
            if offset:
                page_params["offset"] = offset

            # Get page
            response = await self.get(endpoint, params=page_params)

            # Handle both array and object responses
            if isinstance(response, list):
                results = response
                next_page = None
            else:
                results = response.get("data", [])
                next_page = response.get("next_page")

            all_results.extend(results)

            # Check if more pages
            if not next_page or not next_page.get("offset"):
                break

            offset = next_page["offset"]

        return all_results

    async def test_connection(self) -> bool:
        """Test API connection and credentials.

        Returns:
            True if connection successful

        """
        try:
            await self.get("/users/me")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    async def close(self) -> None:
        """Close HTTP client and cleanup resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
