"""Base HTTP client with retry, rate limiting, and error handling."""

import asyncio
import logging
import time
from enum import Enum
from typing import Any

import httpx
from httpx import AsyncClient, TimeoutException

logger = logging.getLogger(__name__)


class HTTPMethod(str, Enum):
    """HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class RetryConfig:
    """Configuration for retry logic."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_on_status: list[int] | None = None,
        retry_on_exceptions: list[type] | None = None,
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on_status = retry_on_status or [429, 502, 503, 504]
        self.retry_on_exceptions = retry_on_exceptions or [
            TimeoutException,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
        ]


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, max_requests: int, time_window: float):
        """Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds

        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.tokens = max_requests
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire a token for making a request."""
        async with self._lock:
            now = time.time()

            # Refill tokens based on time passed
            time_passed = now - self.last_update
            self.tokens = min(
                self.max_requests,
                self.tokens + (time_passed / self.time_window) * self.max_requests,
            )
            self.last_update = now

            if self.tokens >= 1:
                self.tokens -= 1
                return

            # Wait until we can get a token
            wait_time = (1 - self.tokens) * (self.time_window / self.max_requests)
            await asyncio.sleep(wait_time)
            self.tokens = 0


class BaseHTTPClient:
    """Base HTTP client with retry logic, rate limiting, and error handling."""

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
        auth: httpx.Auth | tuple | None = None,
        timeout: float = 30.0,
        retry_config: RetryConfig | None = None,
        rate_limiter: RateLimiter | None = None,
        verify_ssl: bool = True,
        follow_redirects: bool = True,
    ):
        """Initialize HTTP client.

        Args:
            base_url: Base URL for requests
            headers: Default headers
            auth: Authentication (httpx.Auth or (username, password) tuple)
            timeout: Request timeout in seconds
            retry_config: Retry configuration
            rate_limiter: Rate limiter instance
            verify_ssl: Whether to verify SSL certificates
            follow_redirects: Whether to follow redirects

        """
        self.base_url = base_url.rstrip("/")
        self.default_headers = headers or {}
        self.auth = auth
        self.timeout = timeout
        self.retry_config = retry_config or RetryConfig()
        self.rate_limiter = rate_limiter
        self.verify_ssl = verify_ssl
        self.follow_redirects = follow_redirects

        # Statistics
        self.stats = {
            "requests_made": 0,
            "retries_performed": 0,
            "rate_limit_waits": 0,
            "errors": 0,
        }

        self._client: AsyncClient | None = None

    async def _get_client(self) -> AsyncClient:
        """Get or create HTTP client instance."""
        if self._client is None:
            self._client = AsyncClient(
                base_url=self.base_url,
                headers=self.default_headers,
                auth=self.auth,
                timeout=self.timeout,
                verify=self.verify_ssl,
                follow_redirects=self.follow_redirects,
            )
        return self._client

    async def _calculate_delay(
        self, attempt: int, response: httpx.Response | None = None
    ) -> float:
        """Calculate delay for retry attempt."""
        if response and response.status_code == 429:
            # Use Retry-After header if available
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return float(retry_after)
                except ValueError:
                    # Retry-After might be a date
                    pass

        # Exponential backoff
        delay = self.retry_config.initial_delay * (
            self.retry_config.exponential_base ** (attempt - 1)
        )
        delay = min(delay, self.retry_config.max_delay)

        # Add jitter to prevent thundering herd
        if self.retry_config.jitter:
            import random

            delay *= 0.5 + random.random() * 0.5

        return delay

    def _should_retry(
        self,
        exception: Exception,
        response: httpx.Response | None = None,
        attempt: int = 1,
    ) -> bool:
        """Determine if request should be retried."""
        if attempt >= self.retry_config.max_retries:
            return False

        # Check response status codes
        if response and response.status_code in self.retry_config.retry_on_status:
            return True

        # Check exception types
        for exc_type in self.retry_config.retry_on_exceptions:
            if isinstance(exception, exc_type):
                return True

        return False

    async def request(
        self,
        method: HTTPMethod | str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        retry_count: int = 0,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make HTTP request with retry and rate limiting.

        Args:
            method: HTTP method
            endpoint: API endpoint (relative to base_url)
            data: Form data
            json: JSON data
            params: Query parameters
            headers: Additional headers
            timeout: Request timeout override
            retry_count: Current retry attempt
            **kwargs: Additional httpx arguments

        Returns:
            HTTP response

        Raises:
            HTTPStatusError: On HTTP errors
            TimeoutException: On timeout

        """
        # Rate limiting
        if self.rate_limiter:
            await self.rate_limiter.acquire()
            if retry_count == 0:  # Only count first attempts
                self.stats["rate_limit_waits"] += 1

        # Prepare request
        url = f"{self.base_url}/{endpoint.lstrip('/')}" if endpoint else self.base_url

        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)

        client = await self._get_client()

        try:
            response = await client.request(
                method=str(method),
                url=url,
                data=data,
                json=json,
                params=params,
                headers=request_headers,
                timeout=timeout or self.timeout,
                **kwargs,
            )

            # Update stats
            self.stats["requests_made"] += 1
            if retry_count > 0:
                self.stats["retries_performed"] += 1

            response.raise_for_status()
            return response

        except Exception as e:
            self.stats["errors"] += 1

            # Check if we should retry
            response = getattr(e, "response", None)
            if self._should_retry(e, response, retry_count + 1):
                delay = await self._calculate_delay(retry_count + 1, response)

                logger.warning(
                    f"Request failed (attempt {retry_count + 1}/{self.retry_config.max_retries}), "
                    f"retrying in {delay:.2f}s: {e}"
                )

                await asyncio.sleep(delay)
                return await self.request(
                    method,
                    endpoint,
                    data,
                    json,
                    params,
                    headers,
                    timeout,
                    retry_count + 1,
                    **kwargs,
                )

            # No more retries, re-raise the exception
            raise

    async def get(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        """Make GET request."""
        return await self.request(HTTPMethod.GET, endpoint, **kwargs)

    async def post(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        """Make POST request."""
        return await self.request(HTTPMethod.POST, endpoint, **kwargs)

    async def put(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        """Make PUT request."""
        return await self.request(HTTPMethod.PUT, endpoint, **kwargs)

    async def patch(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        """Make PATCH request."""
        return await self.request(HTTPMethod.PATCH, endpoint, **kwargs)

    async def delete(self, endpoint: str, **kwargs: Any) -> httpx.Response:
        """Make DELETE request."""
        return await self.request(HTTPMethod.DELETE, endpoint, **kwargs)

    async def get_json(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """Make GET request and return JSON response."""
        response = await self.get(endpoint, **kwargs)

        # Handle empty responses
        if response.status_code == 204 or not response.content:
            return {}

        return response.json()

    async def post_json(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """Make POST request and return JSON response."""
        response = await self.post(endpoint, **kwargs)

        # Handle empty responses
        if response.status_code == 204 or not response.content:
            return {}

        return response.json()

    async def put_json(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """Make PUT request and return JSON response."""
        response = await self.put(endpoint, **kwargs)

        # Handle empty responses
        if response.status_code == 204 or not response.content:
            return {}

        return response.json()

    async def patch_json(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """Make PATCH request and return JSON response."""
        response = await self.patch(endpoint, **kwargs)

        # Handle empty responses
        if response.status_code == 204 or not response.content:
            return {}

        return response.json()

    def get_stats(self) -> dict[str, Any]:
        """Get client statistics."""
        return self.stats.copy()

    def reset_stats(self) -> None:
        """Reset client statistics."""
        self.stats = {
            "requests_made": 0,
            "retries_performed": 0,
            "rate_limit_waits": 0,
            "errors": 0,
        }

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


class GitHubHTTPClient(BaseHTTPClient):
    """GitHub-specific HTTP client with rate limiting."""

    def __init__(self, token: str, api_url: str = "https://api.github.com"):
        """Initialize GitHub HTTP client.

        Args:
            token: GitHub API token
            api_url: GitHub API URL

        """
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        # GitHub rate limiting: 5000 requests per hour for authenticated requests
        rate_limiter = RateLimiter(max_requests=5000, time_window=3600)

        super().__init__(
            base_url=api_url,
            headers=headers,
            rate_limiter=rate_limiter,
            retry_config=RetryConfig(
                max_retries=3, retry_on_status=[429, 502, 503, 504, 522, 524]
            ),
        )


class JiraHTTPClient(BaseHTTPClient):
    """JIRA-specific HTTP client with authentication and retry logic."""

    def __init__(
        self,
        email: str,
        api_token: str,
        server_url: str,
        is_cloud: bool = True,
        verify_ssl: bool = True,
    ):
        """Initialize JIRA HTTP client.

        Args:
            email: User email
            api_token: API token
            server_url: JIRA server URL
            is_cloud: Whether this is JIRA Cloud
            verify_ssl: Whether to verify SSL certificates

        """
        api_base = (
            f"{server_url}/rest/api/3" if is_cloud else f"{server_url}/rest/api/2"
        )

        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        auth = httpx.BasicAuth(email, api_token)

        # JIRA rate limiting varies by plan, using conservative limits
        rate_limiter = RateLimiter(max_requests=100, time_window=60)

        super().__init__(
            base_url=api_base,
            headers=headers,
            auth=auth,
            rate_limiter=rate_limiter,
            verify_ssl=verify_ssl,
            retry_config=RetryConfig(
                max_retries=3, retry_on_status=[429, 502, 503, 504]
            ),
        )
