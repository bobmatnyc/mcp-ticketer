"""Unit tests for cache memory module."""

import asyncio
import time

import pytest

from mcp_ticketer.cache.memory import (
    CacheEntry,
    MemoryCache,
    cache_decorator,
    get_global_cache,
)


@pytest.mark.unit
class TestCacheEntry:
    """Test CacheEntry class."""

    def test_create_cache_entry(self) -> None:
        """Test creating a cache entry."""
        value = {"data": "test"}
        ttl = 60.0

        entry = CacheEntry(value, ttl)

        assert entry.value == value
        assert entry.expires_at > time.time()
        assert entry.expires_at <= time.time() + ttl + 1

    def test_cache_entry_with_zero_ttl(self) -> None:
        """Test cache entry with zero TTL never expires."""
        entry = CacheEntry("test", 0)

        assert entry.expires_at == float("inf")
        assert not entry.is_expired()

    def test_cache_entry_is_not_expired_initially(self) -> None:
        """Test that fresh entry is not expired."""
        entry = CacheEntry("test", 10)

        assert not entry.is_expired()

    @pytest.mark.asyncio
    async def test_cache_entry_expires_after_ttl(self):
        """Test that entry expires after TTL."""
        entry = CacheEntry("test", 0.1)  # 100ms TTL

        assert not entry.is_expired()
        await asyncio.sleep(0.15)
        assert entry.is_expired()


@pytest.mark.unit
class TestMemoryCache:
    """Test MemoryCache class."""

    @pytest.mark.asyncio
    async def test_create_memory_cache(self):
        """Test creating a memory cache."""
        cache = MemoryCache()

        assert cache.size() == 0
        assert cache._default_ttl == 300.0

    @pytest.mark.asyncio
    async def test_create_cache_with_custom_ttl(self):
        """Test creating cache with custom default TTL."""
        cache = MemoryCache(default_ttl=600.0)

        assert cache._default_ttl == 600.0

    @pytest.mark.asyncio
    async def test_set_and_get_value(self):
        """Test setting and getting a value."""
        cache = MemoryCache()

        await cache.set("key1", "value1")
        result = await cache.get("key1")

        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_nonexistent_key_returns_none(self):
        """Test getting a nonexistent key returns None."""
        cache = MemoryCache()

        result = await cache.get("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_multiple_values(self):
        """Test setting multiple values."""
        cache = MemoryCache()

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") == "value2"
        assert await cache.get("key3") == "value3"
        assert cache.size() == 3

    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(self):
        """Test setting value with custom TTL."""
        cache = MemoryCache(default_ttl=300.0)

        await cache.set("key1", "value1", ttl=0.1)

        assert await cache.get("key1") == "value1"
        await asyncio.sleep(0.15)
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_overwrite_existing_key(self):
        """Test overwriting an existing key."""
        cache = MemoryCache()

        await cache.set("key1", "value1")
        await cache.set("key1", "value2")

        result = await cache.get("key1")
        assert result == "value2"

    @pytest.mark.asyncio
    async def test_delete_existing_key(self):
        """Test deleting an existing key."""
        cache = MemoryCache()

        await cache.set("key1", "value1")
        result = await cache.delete("key1")

        assert result is True
        assert await cache.get("key1") is None
        assert cache.size() == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self):
        """Test deleting a nonexistent key returns False."""
        cache = MemoryCache()

        result = await cache.delete("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """Test clearing all cache entries."""
        cache = MemoryCache()

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")

        await cache.clear()

        assert cache.size() == 0
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None

    @pytest.mark.asyncio
    async def test_cleanup_expired_entries(self):
        """Test cleaning up expired entries."""
        cache = MemoryCache()

        # Set entries with different TTLs
        await cache.set("key1", "value1", ttl=0.1)
        await cache.set("key2", "value2", ttl=10.0)
        await cache.set("key3", "value3", ttl=0.1)

        # Wait for some to expire
        await asyncio.sleep(0.15)

        removed_count = await cache.cleanup_expired()

        assert removed_count == 2
        assert cache.size() == 1
        assert await cache.get("key2") == "value2"
        assert await cache.get("key1") is None
        assert await cache.get("key3") is None

    @pytest.mark.asyncio
    async def test_get_removes_expired_entry(self):
        """Test that get automatically removes expired entries."""
        cache = MemoryCache()

        await cache.set("key1", "value1", ttl=0.1)

        # Initially present
        assert await cache.get("key1") == "value1"
        assert cache.size() == 1

        # After expiry, should return None and remove entry
        await asyncio.sleep(0.15)
        assert await cache.get("key1") is None
        assert cache.size() == 0

    @pytest.mark.asyncio
    async def test_cache_with_complex_values(self):
        """Test caching complex data types."""
        cache = MemoryCache()

        test_dict = {"nested": {"data": [1, 2, 3]}}
        test_list = [1, "two", {"three": 3}]

        await cache.set("dict", test_dict)
        await cache.set("list", test_list)

        assert await cache.get("dict") == test_dict
        assert await cache.get("list") == test_list

    def test_generate_key_basic(self) -> None:
        """Test generating cache key from arguments."""
        key1 = MemoryCache.generate_key("arg1", "arg2")
        key2 = MemoryCache.generate_key("arg1", "arg2")
        key3 = MemoryCache.generate_key("arg1", "arg3")

        # Same arguments should generate same key
        assert key1 == key2
        # Different arguments should generate different key
        assert key1 != key3

    def test_generate_key_with_kwargs(self) -> None:
        """Test generating cache key with keyword arguments."""
        key1 = MemoryCache.generate_key(a=1, b=2)
        key2 = MemoryCache.generate_key(b=2, a=1)  # Different order
        key3 = MemoryCache.generate_key(a=1, b=3)

        # Same kwargs (different order) should generate same key
        assert key1 == key2
        # Different kwargs should generate different key
        assert key1 != key3

    def test_generate_key_mixed_args(self) -> None:
        """Test generating cache key with mixed args and kwargs."""
        key1 = MemoryCache.generate_key("pos1", "pos2", kwarg1="val1")
        key2 = MemoryCache.generate_key("pos1", "pos2", kwarg1="val1")
        key3 = MemoryCache.generate_key("pos1", "pos2", kwarg1="val2")

        assert key1 == key2
        assert key1 != key3

    def test_size_reflects_cache_content(self) -> None:
        """Test that size reflects actual cache size."""
        cache = MemoryCache()

        assert cache.size() == 0


@pytest.mark.unit
class TestCacheDecorator:
    """Test cache_decorator function."""

    @pytest.mark.asyncio
    async def test_decorator_caches_result(self):
        """Test that decorator caches function results."""
        call_count = 0
        cache = MemoryCache()

        @cache_decorator(ttl=10.0, key_prefix="test", cache_instance=cache)
        async def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call should execute function
        result1 = await expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call should use cache
        result2 = await expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Not incremented

    @pytest.mark.asyncio
    async def test_decorator_different_args_different_cache(self):
        """Test that different arguments use different cache entries."""
        call_count = 0
        cache = MemoryCache()

        @cache_decorator(ttl=10.0, cache_instance=cache)
        async def func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = await func(5)
        result2 = await func(10)

        assert result1 == 10
        assert result2 == 20
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_decorator_respects_ttl(self):
        """Test that decorator respects TTL."""
        call_count = 0
        cache = MemoryCache()

        @cache_decorator(ttl=0.1, cache_instance=cache)
        async def func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = await func(5)
        assert result1 == 10
        assert call_count == 1

        # Wait for TTL to expire
        await asyncio.sleep(0.15)

        result2 = await func(5)
        assert result2 == 10
        assert call_count == 2  # Function called again

    @pytest.mark.asyncio
    async def test_decorator_cache_clear(self):
        """Test cache_clear method on decorated function."""
        call_count = 0
        cache = MemoryCache()

        @cache_decorator(ttl=10.0, cache_instance=cache)
        async def func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        await func(5)
        assert call_count == 1

        # Clear cache
        await func.cache_clear()

        # Should call function again
        await func(5)
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_decorator_with_key_prefix(self):
        """Test decorator with key prefix."""
        cache = MemoryCache()

        @cache_decorator(ttl=10.0, key_prefix="prefix1", cache_instance=cache)
        async def func1(x):
            return x * 2

        @cache_decorator(ttl=10.0, key_prefix="prefix2", cache_instance=cache)
        async def func2(x):
            return x * 3

        result1 = await func1(5)
        result2 = await func2(5)

        assert result1 == 10
        assert result2 == 15
        # Both should be cached separately
        assert cache.size() == 2

    @pytest.mark.asyncio
    async def test_decorator_creates_own_cache_if_none(self):
        """Test that decorator creates its own cache if none provided."""
        call_count = 0

        @cache_decorator(ttl=10.0)
        async def func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        await func(5)
        await func(5)

        # Should still cache (call count = 1)
        assert call_count == 1


@pytest.mark.unit
class TestGlobalCache:
    """Test global cache instance."""

    @pytest.mark.asyncio
    async def test_get_global_cache(self):
        """Test getting global cache instance."""
        cache1 = get_global_cache()
        cache2 = get_global_cache()

        assert cache1 is cache2  # Same instance
        assert isinstance(cache1, MemoryCache)

    @pytest.mark.asyncio
    async def test_global_cache_is_shared(self):
        """Test that global cache is shared across calls."""
        cache = get_global_cache()

        await cache.set("shared_key", "shared_value")

        # Get global cache again
        cache2 = get_global_cache()
        result = await cache2.get("shared_key")

        assert result == "shared_value"


@pytest.mark.unit
class TestCacheConcurrency:
    """Test cache concurrency and thread safety."""

    @pytest.mark.asyncio
    async def test_concurrent_sets(self):
        """Test concurrent set operations."""
        cache = MemoryCache()

        async def set_value(key, value):
            await cache.set(key, value)

        # Set multiple values concurrently
        await asyncio.gather(
            set_value("key1", "value1"),
            set_value("key2", "value2"),
            set_value("key3", "value3"),
        )

        assert cache.size() == 3
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") == "value2"
        assert await cache.get("key3") == "value3"

    @pytest.mark.asyncio
    async def test_concurrent_gets(self):
        """Test concurrent get operations."""
        cache = MemoryCache()
        await cache.set("key", "value")

        # Get value concurrently
        results = await asyncio.gather(
            cache.get("key"),
            cache.get("key"),
            cache.get("key"),
        )

        assert all(r == "value" for r in results)
