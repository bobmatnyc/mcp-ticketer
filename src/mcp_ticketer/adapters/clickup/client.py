"""ClickUp HTTP client for REST API v2."""

import asyncio
import logging
from typing import Any

import httpx

from .types import CLICKUP_BASE_URL

logger = logging.getLogger(__name__)


class ClickUpClient:
    """HTTP client for ClickUp REST API v2.

    Handles:
    - Personal-token authentication (``Authorization: <token>``; no "Bearer").
    - Rate limiting (429 with Retry-After) with bounded retries.
    - Error handling for all status codes (raised as ``ValueError``).
    - Timeout retries with exponential backoff.

    Security:
        The personal token is held on the instance and sent as the
        ``Authorization`` header. It is never included in any log line or
        exception message; only the request method, URL, and status are logged.
    """

    BASE_URL = CLICKUP_BASE_URL

    def __init__(self, api_token: str, timeout: int = 30, max_retries: int = 3):
        """Initialize ClickUp client.

        Args:
            api_token: ClickUp personal API token (format ``pk_...``).
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts for rate limiting / timeouts.

        """
        self.api_token = api_token
        self.timeout = timeout
        self.max_retries = max_retries

        # ClickUp authenticates with the raw token (NOT "Bearer <token>").
        self.headers = {
            "Authorization": api_token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # HTTP client (created lazily on first use).
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client.

        Returns:
            Configured async HTTP client.

        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers=self.headers,
                timeout=self.timeout,
                follow_redirects=False,
            )
        return self._client

    async def _handle_rate_limit(self, response: httpx.Response, attempt: int) -> None:
        """Handle rate limiting with Retry-After backoff.

        Args:
            response: HTTP response with 429 status.
            attempt: Current retry attempt number.

        Raises:
            ValueError: If max retries exceeded.

        """
        if attempt >= self.max_retries:
            raise ValueError(
                f"Max retries ({self.max_retries}) exceeded for rate limiting"
            )

        # ClickUp returns Retry-After in seconds; default to 60 if absent.
        try:
            retry_after = min(int(response.headers.get("Retry-After", "60")), 3600)
        except (ValueError, TypeError):
            retry_after = 60
        logger.warning(
            "Rate limited (429). Waiting %ss before retry %s/%s",
            retry_after,
            attempt + 1,
            self.max_retries,
        )
        await asyncio.sleep(retry_after)

    def _extract_error_detail(self, response: httpx.Response) -> str:
        """Extract a human-readable error message from a ClickUp error response.

        ClickUp errors are shaped ``{"err": "...", "ECODE": "..."}``.

        Args:
            response: HTTP response with a >= 400 status.

        Returns:
            Error message string (never contains the auth token).

        """
        # Never start from the raw body (it can echo request details); use
        # the parsed ClickUp 'err' field when present, else a status-only message.
        detail = response.reason_phrase or f"HTTP {response.status_code}"
        try:
            error_json = response.json()
            if isinstance(error_json, dict):
                detail = error_json.get("err") or error_json.get("error") or detail
                ecode = error_json.get("ECODE")
                if ecode:
                    detail = f"{detail} (ECODE: {ecode})"
        except Exception:
            pass
        return detail

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request with retry logic for rate limiting and timeouts.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            endpoint: API endpoint (without base URL).
            params: URL query parameters.
            json: Request body JSON data.

        Returns:
            Parsed JSON response body (ClickUp does not wrap responses).

        Raises:
            ValueError: If the request fails or max retries are exceeded. The
                error message never includes the authentication token.

        """
        client = await self._get_client()
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"

        for attempt in range(self.max_retries + 1):
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                )

                # Refuse redirects: the base host is fixed (api.clickup.com); a 3xx
                # could bounce the Authorization header to another host (xander review).
                if response.is_redirect:
                    raise ValueError(
                        f"ClickUp API returned an unexpected redirect "
                        f"(status {response.status_code}); refusing to follow"
                    )

                # Handle rate limiting.
                if response.status_code == 429:
                    await self._handle_rate_limit(response, attempt)
                    continue

                # Handle errors.
                if response.status_code >= 400:
                    detail = self._extract_error_detail(response)
                    raise ValueError(
                        f"ClickUp API error ({response.status_code}): {detail}"
                    )

                # Success. ClickUp returns the body directly (no {"data": ...}).
                if not response.content:
                    return {}
                parsed = response.json()
                if isinstance(parsed, dict):
                    return parsed
                # Some endpoints (rare) return a bare list; wrap for the typed signature.
                return {"_list": parsed}

            except httpx.TimeoutException as e:
                # Do not interpolate the exception object that could carry headers;
                # log only the method/url and a short reason.
                logger.error("Request timeout for %s %s: %s", method, url, e)
                if attempt < self.max_retries:
                    wait_time = 2**attempt
                    logger.info("Retrying in %ss...", wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    raise ValueError(
                        f"Request timeout after {self.max_retries} retries"
                    ) from None

            except httpx.HTTPError as e:
                logger.error("HTTP error for %s %s: %s", method, url, e)
                raise ValueError(f"HTTP error: {e}") from None

        raise ValueError("Request failed after all retry attempts")

    async def get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make a GET request.

        Args:
            endpoint: API endpoint.
            params: Query parameters.

        Returns:
            Parsed response body.

        """
        return await self._request("GET", endpoint, params=params)

    async def post(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make a POST request.

        Args:
            endpoint: API endpoint.
            data: Request body data.

        Returns:
            Parsed response body.

        """
        return await self._request("POST", endpoint, json=data)

    async def put(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make a PUT request.

        Args:
            endpoint: API endpoint.
            data: Request body data.

        Returns:
            Parsed response body.

        """
        return await self._request("PUT", endpoint, json=data)

    async def delete(self, endpoint: str) -> dict[str, Any]:
        """Make a DELETE request.

        Args:
            endpoint: API endpoint.

        Returns:
            Parsed response body (often empty for ClickUp deletes).

        """
        return await self._request("DELETE", endpoint)

    async def test_connection(self) -> bool:
        """Test API connection and credentials via ``GET /user``.

        Returns:
            True if the connection succeeds, False otherwise.

        """
        try:
            await self.get("/user")
            return True
        except Exception as e:
            # ``e`` is a ValueError raised by _request; it never carries the token.
            logger.error("ClickUp connection test failed: %s", e)
            return False

    async def close(self) -> None:
        """Close the HTTP client and cleanup resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
