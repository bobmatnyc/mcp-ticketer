"""HTTP client for Jira REST API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from httpx import AsyncClient, HTTPStatusError, TimeoutException

logger = logging.getLogger(__name__)


class JiraClient:
    """HTTP client for JIRA REST API with authentication and retry logic."""

    def __init__(
        self,
        server: str,
        email: str,
        api_token: str,
        is_cloud: bool = True,
        verify_ssl: bool = True,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """Initialize JIRA API client.

        Args:
        ----
            server: JIRA server URL (e.g., https://company.atlassian.net)
            email: User email for authentication
            api_token: API token for authentication
            is_cloud: Whether this is JIRA Cloud (default: True)
            verify_ssl: Whether to verify SSL certificates (default: True)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum retry attempts (default: 3)

        """
        # Clean up server URL
        self.server = server.rstrip("/")

        # API base URL
        self.api_base = (
            f"{self.server}/rest/api/3" if is_cloud else f"{self.server}/rest/api/2"
        )

        # Configuration
        self.email = email
        self.api_token = api_token
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.max_retries = max_retries

        # HTTP client setup - only create auth if credentials are present
        # (validate_credentials() will check for missing credentials)
        self.auth = (
            httpx.BasicAuth(self.email, self.api_token)
            if self.email and self.api_token
            else None
        )
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _get_client(self) -> AsyncClient:
        """Get configured async HTTP client.

        Returns:
        -------
            Configured AsyncClient instance

        """
        return AsyncClient(
            auth=self.auth,
            headers=self.headers,
            timeout=self.timeout,
            verify=self.verify_ssl,
        )

    async def request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        retry_count: int = 0,
    ) -> dict[str, Any]:
        """Make HTTP request to JIRA API with retry logic.

        Args:
        ----
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (relative to api_base)
            data: Request body data
            params: Query parameters
            retry_count: Current retry attempt

        Returns:
        -------
            Response data as dictionary

        Raises:
        ------
            HTTPStatusError: On API errors
            TimeoutException: On timeout

        """
        url = f"{self.api_base}/{endpoint.lstrip('/')}"

        async with await self._get_client() as client:
            try:
                response = await client.request(
                    method=method, url=url, json=data, params=params
                )
                response.raise_for_status()

                # Handle empty responses
                if response.status_code == 204:
                    return {}

                return response.json()

            except TimeoutException as e:
                if retry_count < self.max_retries:
                    await asyncio.sleep(2**retry_count)  # Exponential backoff
                    return await self.request(
                        method, endpoint, data, params, retry_count + 1
                    )
                raise e

            except HTTPStatusError as e:
                # Handle rate limiting
                if e.response.status_code == 429 and retry_count < self.max_retries:
                    retry_after = int(e.response.headers.get("Retry-After", 5))
                    await asyncio.sleep(retry_after)
                    return await self.request(
                        method, endpoint, data, params, retry_count + 1
                    )

                # Log error details
                logger.error(
                    f"JIRA API error: {e.response.status_code} - {e.response.text}"
                )
                raise e

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make GET request.

        Args:
        ----
            endpoint: API endpoint
            params: Query parameters

        Returns:
        -------
            Response data

        """
        return await self.request("GET", endpoint, params=params)

    async def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make POST request.

        Args:
        ----
            endpoint: API endpoint
            data: Request body data
            params: Query parameters

        Returns:
        -------
            Response data

        """
        return await self.request("POST", endpoint, data=data, params=params)

    async def put(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make PUT request.

        Args:
        ----
            endpoint: API endpoint
            data: Request body data

        Returns:
        -------
            Response data

        """
        return await self.request("PUT", endpoint, data=data)

    async def delete(
        self,
        endpoint: str,
    ) -> dict[str, Any]:
        """Make DELETE request.

        Args:
        ----
            endpoint: API endpoint

        Returns:
        -------
            Response data (usually empty)

        """
        return await self.request("DELETE", endpoint)

    async def upload_file(
        self,
        endpoint: str,
        file_path: str,
        filename: str,
    ) -> dict[str, Any]:
        """Upload file with multipart/form-data.

        Args:
        ----
            endpoint: API endpoint
            file_path: Path to file to upload
            filename: Name for the uploaded file

        Returns:
        -------
            Response data

        """
        # JIRA requires special header for attachment upload
        headers = {
            "X-Atlassian-Token": "no-check",
            # Don't set Content-Type - let httpx handle multipart
        }

        url = f"{self.api_base}/{endpoint.lstrip('/')}"

        # Prepare multipart file upload
        with open(file_path, "rb") as f:
            files = {"file": (filename, f, "application/octet-stream")}

            # Use existing client infrastructure
            async with await self._get_client() as client:
                response = await client.post(
                    url, files=files, headers={**self.headers, **headers}
                )
                response.raise_for_status()
                return response.json()

    def get_browse_url(self, issue_key: str) -> str:
        """Get browser URL for an issue.

        Args:
        ----
            issue_key: Issue key (e.g., PROJ-123)

        Returns:
        -------
            Full URL to view issue in browser

        """
        return f"{self.server}/browse/{issue_key}"
