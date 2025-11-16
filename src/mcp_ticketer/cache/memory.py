"""In-memory cache implementation with TTL support."""

import asyncio
import hashlib
import json
import time
from collections.abc import Callable
from functools import wraps
from typing import Any


class CacheEntry:
    """Single cache entry with TTL."""

    def __init__(self, value: Any, ttl: float):
        """Initialize cache entry.

        Args:
            value: Cached value
            ttl: Time to live in seconds

        """
        self.value = value
        self.expires_at = time.time() + ttl if ttl > 0 else float("inf")

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() > self.expires_at


class MemoryCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self, default_ttl: float = 300.0):
        """Initialize cache.

        Args:
            default_ttl: Default TTL in seconds (5 minutes)

        """
        self._cache: dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired

        """
        async with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired():
                return entry.value
            elif entry:
                # Remove expired entry
                del self._cache[key]
            return None

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override

        """
        async with self._lock:
            ttl = ttl if ttl is not None else self._default_ttl
            self._cache[key] = CacheEntry(value, ttl)

    async def delete(self, key: str) -> bool:
        """Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted

        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()

    async def cleanup_expired(self) -> int:
        """Remove expired entries.

        Returns:
            Number of entries removed

        """
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() if entry.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    def size(self) -> int:
        """Get number of entries in cache."""
        return len(self._cache)

    @staticmethod
    def generate_key(*args: Any, **kwargs: Any) -> str:
        """Generate cache key from arguments.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Hash-based cache key

        """
        # Create string representation of arguments
        key_data = {"args": args, "kwargs": sorted(kwargs.items())}
        key_str = json.dumps(key_data, sort_keys=True, default=str)

        # Generate hash
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]


def cache_decorator(
    ttl: float | None = None,
    key_prefix: str = "",
    cache_instance: MemoryCache | None = None,
) -> Callable:
    """Decorate async function to cache its results.

    Args:
        ttl: TTL for cached results
        key_prefix: Prefix for cache keys
        cache_instance: Cache instance to use (creates new if None)

    Returns:
        Decorated function

    """
    # Use shared cache instance or create new
    cache = cache_instance or MemoryCache()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate cache key
            base_key = MemoryCache.generate_key(*args, **kwargs)
            cache_key = f"{key_prefix}:{func.__name__}:{base_key}"

            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            await cache.set(cache_key, result, ttl)

            return result

        # Add cache control methods
        wrapper.cache_clear = lambda: cache.clear()
        wrapper.cache_delete = lambda *a, **k: cache.delete(
            f"{key_prefix}:{func.__name__}:{MemoryCache.generate_key(*a, **k)}"
        )

        return wrapper

    return decorator


# Global cache instance for shared use
_global_cache = MemoryCache()


def get_global_cache() -> MemoryCache:
    """Get global cache instance."""
    return _global_cache
