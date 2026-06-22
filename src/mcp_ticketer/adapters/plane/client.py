"""Plane HTTP client for the REST API v1.

Handles:
- ``X-API-Key`` header authentication (the key is never logged)
- Instance-URL validation (https required; cross-host redirects are not
  followed silently)
- Rate limiting (429 with Retry-After)
- Cursor / offset pagination
- Error handling that never leaks the API key
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

DEFAULT_INSTANCE_URL = "https://api.plane.so"


class PlaneClientError(ValueError):
    """Raised for Plane API and configuration errors.

    Subclasses ``ValueError`` to match the error-handling convention used by
    the other adapters in this project.
    """


def normalize_instance_url(instance_url: str | None) -> str:
    """Validate and normalise a user-supplied Plane instance URL.

    The instance URL is user-controlled, so it is validated to prevent SSRF and
    credential-leak vectors:

    - The scheme must be ``https`` (an http URL would send the API key in
      clear text).
    - A host must be present.

    Args:
        instance_url: User-supplied instance URL, or None for the default.

    Returns:
        The normalised base URL with any trailing slash removed.

    Raises:
        PlaneClientError: If the URL is not a valid https URL.

    """
    raw = (instance_url or DEFAULT_INSTANCE_URL).strip()
    parsed = urlparse(raw)

    if parsed.scheme != "https":
        raise PlaneClientError(
            f"Plane instance URL must use https (got '{parsed.scheme or 'no scheme'}')"
        )
    if not parsed.netloc:
        raise PlaneClientError("Plane instance URL is missing a host")

    host = (parsed.hostname or "").lower()
    # Block cloud-metadata + loopback/link-local — never a legitimate remote Plane and a
    # classic SSRF credential-exfil target (169.254.169.254 etc.). RFC-1918 private IPs are
    # ALLOWED: a self-hosted Plane on an internal corporate network is a primary use case.
    if host in {"localhost", "metadata", "instance-data", "metadata.google.internal"}:
        raise PlaneClientError(f"Plane instance URL host '{host}' is not allowed")
    blocked = False
    try:
        ip = ipaddress.ip_address(host)
        blocked = (
            ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified
        )
    except ValueError:
        blocked = False  # hostname literal (incl. internal DNS for self-host) — allowed
    if blocked:
        raise PlaneClientError(
            f"Plane instance URL must not point to a loopback/link-local address (got '{host}')"
        )

    return raw.rstrip("/")


class PlaneClient:
    """Async HTTP client for the Plane REST API v1.

    The client scopes requests to a single workspace and project. Endpoints
    passed to the request methods are relative to the project base URL, e.g.
    ``"/issues/"`` resolves to
    ``{instance}/api/v1/workspaces/{slug}/projects/{project}/issues/``.
    Workspace-level endpoints (e.g. members) use ``workspace_path``.
    """

    def __init__(
        self,
        api_key: str,
        workspace_slug: str,
        project_id: str,
        instance_url: str | None = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """Initialise the Plane client.

        Args:
            api_key: Plane personal API key (sent via the ``X-API-Key`` header).
            workspace_slug: Plane workspace slug.
            project_id: Plane project UUID.
            instance_url: Base instance URL (defaults to https://api.plane.so).
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts for rate limiting / timeouts.

        Raises:
            PlaneClientError: If the instance URL is invalid.

        """
        self.api_key = api_key
        self.workspace_slug = workspace_slug
        self.project_id = project_id
        self.instance_url = normalize_instance_url(instance_url)
        self.timeout = timeout
        self.max_retries = max_retries

        # Host the API key is bound to. Redirects to any other host are refused
        # so the key is never replayed to an attacker-controlled origin.
        self._allowed_host = urlparse(self.instance_url).netloc

        self.headers = {
            "X-API-Key": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        self._client: httpx.AsyncClient | None = None

    @property
    def api_base(self) -> str:
        """Base URL for the configured workspace API."""
        return f"{self.instance_url}/api/v1/workspaces/{self.workspace_slug}"

    @property
    def project_base(self) -> str:
        """Base URL for the configured project."""
        return f"{self.api_base}/projects/{self.project_id}"

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or lazily create the async HTTP client.

        ``follow_redirects`` is disabled: Plane's REST API does not rely on
        redirects, and following them automatically could replay the API key to
        a different host.

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
        """Sleep according to the Retry-After header for a 429 response.

        Args:
            response: HTTP response with a 429 status.
            attempt: Current retry attempt number.

        Raises:
            PlaneClientError: If the maximum retry count is exceeded.

        """
        if attempt >= self.max_retries:
            raise PlaneClientError(
                f"Max retries ({self.max_retries}) exceeded for rate limiting"
            )

        retry_after = min(int(response.headers.get("Retry-After", 60)), 3600)
        logger.warning(
            "Rate limited (429). Waiting %ss before retry %s/%s",
            retry_after,
            attempt + 1,
            self.max_retries,
        )
        await asyncio.sleep(retry_after)

    async def _request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        """Make an HTTP request with retry handling.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE).
            url: Fully-qualified request URL.
            params: URL query parameters.
            json: Request body JSON data.

        Returns:
            Parsed JSON response, or an empty dict for empty (e.g. 204) bodies.

        Raises:
            PlaneClientError: If the request fails. The error message never
                contains the API key.

        """
        client = await self._get_client()

        for attempt in range(self.max_retries + 1):
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                )

                if response.status_code == 429:
                    await self._handle_rate_limit(response, attempt)
                    continue

                # Refuse redirects to a different host (the API key must never
                # be sent off-origin). Same-host redirects are also surfaced as
                # errors rather than followed silently.
                if response.is_redirect:
                    location = response.headers.get("location", "")
                    raise PlaneClientError(
                        f"Refusing to follow redirect to '{location}' "
                        f"(expected host '{self._allowed_host}')"
                    )

                if response.status_code >= 400:
                    raise PlaneClientError(
                        f"Plane API error ({response.status_code}): "
                        f"{self._extract_error(response)}"
                    )

                if response.status_code == 204 or not response.content:
                    return {}

                return response.json()

            except httpx.TimeoutException as e:
                logger.error("Request timeout for %s %s", method, url)
                if attempt < self.max_retries:
                    wait_time = 2**attempt
                    logger.info("Retrying in %ss...", wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    raise PlaneClientError(
                        f"Request timeout after {self.max_retries} retries"
                    ) from e

            except httpx.HTTPError as e:
                # Note: str(e) from httpx contains the URL but never headers,
                # so the API key is not exposed here.
                logger.error("HTTP error for %s %s", method, url)
                raise PlaneClientError(f"HTTP error: {e}") from e

        raise PlaneClientError("Request failed after all retry attempts")

    @staticmethod
    def _extract_error(response: httpx.Response) -> str:
        """Extract a human-readable error message from a Plane error response.

        Args:
            response: HTTP error response.

        Returns:
            Best-effort error detail string.

        """
        try:
            payload = response.json()
        except Exception:
            # Never return the raw body — it can echo request details. Use status only.
            return response.reason_phrase or f"HTTP {response.status_code}"

        if isinstance(payload, dict):
            for key in ("error", "detail", "message"):
                if payload.get(key):
                    return str(payload[key])
        return str(payload)

    # Project-scoped helpers -------------------------------------------------

    async def get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """GET a project-scoped endpoint.

        Args:
            endpoint: Endpoint relative to the project base (e.g. "/issues/").
            params: Query parameters.

        Returns:
            Parsed JSON response.

        """
        return await self._request(
            "GET", f"{self.project_base}{endpoint}", params=params
        )

    async def post(self, endpoint: str, data: dict[str, Any]) -> Any:
        """POST to a project-scoped endpoint.

        Args:
            endpoint: Endpoint relative to the project base.
            data: Request body data.

        Returns:
            Parsed JSON response.

        """
        return await self._request("POST", f"{self.project_base}{endpoint}", json=data)

    async def patch(self, endpoint: str, data: dict[str, Any]) -> Any:
        """PATCH a project-scoped endpoint.

        Args:
            endpoint: Endpoint relative to the project base.
            data: Request body data.

        Returns:
            Parsed JSON response.

        """
        return await self._request("PATCH", f"{self.project_base}{endpoint}", json=data)

    async def delete(self, endpoint: str) -> Any:
        """DELETE a project-scoped endpoint.

        Args:
            endpoint: Endpoint relative to the project base.

        Returns:
            Parsed JSON response (usually empty).

        """
        return await self._request("DELETE", f"{self.project_base}{endpoint}")

    # Workspace-scoped helper ------------------------------------------------

    async def get_workspace(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> Any:
        """GET a workspace-scoped endpoint (e.g. "/members/").

        Args:
            endpoint: Endpoint relative to the workspace base.
            params: Query parameters.

        Returns:
            Parsed JSON response.

        """
        return await self._request("GET", f"{self.api_base}{endpoint}", params=params)

    # Pagination -------------------------------------------------------------

    async def get_paginated(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        workspace_scoped: bool = False,
        per_page: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch all pages from a paginated Plane list endpoint.

        Plane list responses are either a bare list or a paginated envelope of
        the form ``{"results": [...], "next_cursor": ..., "next_page_results":
        bool}``. This helper handles both.

        Args:
            endpoint: Endpoint to fetch.
            params: Base query parameters.
            workspace_scoped: If True, resolve against the workspace base
                instead of the project base.
            per_page: Items per page.

        Returns:
            Flattened list of all result items.

        """
        base_params = dict(params or {})
        base_params.setdefault("per_page", per_page)

        getter = self.get_workspace if workspace_scoped else self.get

        all_results: list[dict[str, Any]] = []
        cursor: str | None = None

        while True:
            page_params = dict(base_params)
            if cursor:
                page_params["cursor"] = cursor

            response = await getter(endpoint, params=page_params)

            if isinstance(response, list):
                all_results.extend(response)
                break

            if isinstance(response, dict):
                results = response.get("results", [])
                all_results.extend(results)

                if not response.get("next_page_results"):
                    break
                cursor = response.get("next_cursor")
                if not cursor:
                    break
            else:
                break

        return all_results

    async def test_connection(self) -> bool:
        """Verify the credentials and configuration by listing states.

        Returns:
            True if the project states endpoint responds successfully.

        """
        try:
            await self.get("/states/")
            return True
        except Exception:
            logger.error("Plane connection test failed")
            return False

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
