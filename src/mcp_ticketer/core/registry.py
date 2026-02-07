"""Adapter registry for dynamic adapter management."""

from typing import Any

from .adapter import BaseAdapter


class AdapterRegistry:
    """Registry for managing ticket system adapters.

    Supports connection-based caching for multi-account scenarios.
    Cache keys use format: "adapter_type" or "adapter_type:connection_name"

    Examples:
        - "github" - default GitHub connection
        - "github:work" - work GitHub account
        - "github:personal" - personal GitHub account
    """

    _adapters: dict[str, type[BaseAdapter]] = {}
    _instances: dict[str, BaseAdapter] = {}

    @classmethod
    def _get_cache_key(
        cls, adapter_type: str, connection_name: str | None = None
    ) -> str:
        """Generate cache key for adapter instance.

        Args:
            adapter_type: Base adapter type (e.g., "github", "linear")
            connection_name: Optional connection name for multi-account support

        Returns:
            Cache key string (e.g., "github" or "github:work")

        """
        if connection_name and connection_name != adapter_type:
            return f"{adapter_type}:{connection_name}"
        return adapter_type

    @classmethod
    def register(cls, name: str, adapter_class: type[BaseAdapter]) -> None:
        """Register an adapter class.

        Args:
            name: Unique name for the adapter
            adapter_class: Adapter class to register

        """
        if not issubclass(adapter_class, BaseAdapter):
            raise TypeError(f"{adapter_class} must be a subclass of BaseAdapter")
        cls._adapters[name] = adapter_class

    @classmethod
    def unregister(cls, name: str) -> None:
        """Unregister an adapter.

        Args:
            name: Name of adapter to unregister

        """
        cls._adapters.pop(name, None)
        # Remove all instances with this adapter type (including connections)
        keys_to_remove = [
            key
            for key in cls._instances.keys()
            if key == name or key.startswith(f"{name}:")
        ]
        for key in keys_to_remove:
            cls._instances.pop(key, None)

    @classmethod
    def get_adapter(
        cls,
        name: str,
        config: dict[str, Any] | None = None,
        force_new: bool = False,
        connection_name: str | None = None,
    ) -> BaseAdapter:
        """Get or create an adapter instance.

        Uses factory pattern for adapter instantiation with caching.
        Supports connection-based caching for multi-account scenarios.

        Args:
            name: Name of the registered adapter (e.g., "github", "linear")
            config: Configuration for the adapter
            force_new: Force creation of new instance
            connection_name: Optional connection name for multi-account support
                           (e.g., "work", "personal" for different GitHub accounts)

        Returns:
            Adapter instance

        Raises:
            ValueError: If adapter not registered

        """
        if name not in cls._adapters:
            available = ", ".join(cls._adapters.keys())
            raise ValueError(
                f"Adapter '{name}' not registered. " f"Available adapters: {available}"
            )

        # Generate cache key (supports connection-based caching)
        cache_key = cls._get_cache_key(name, connection_name)

        # Return cached instance if exists and not forcing new
        if cache_key in cls._instances and not force_new:
            return cls._instances[cache_key]

        # Create new instance
        adapter_class = cls._adapters[name]
        config = config or {}
        instance = adapter_class(config)

        # Cache the instance with connection-aware key
        cls._instances[cache_key] = instance
        return instance

    @classmethod
    def list_adapters(cls) -> dict[str, type[BaseAdapter]]:
        """List all registered adapters.

        Returns:
            Dictionary of adapter names to classes

        """
        return cls._adapters.copy()

    @classmethod
    def list_connections(cls, adapter_type: str) -> list[str]:
        """List all cached connections for a specific adapter type.

        Args:
            adapter_type: Base adapter type (e.g., "github")

        Returns:
            List of connection names (e.g., ["github", "github:work", "github:personal"])

        """
        connections = []
        for key in cls._instances.keys():
            if key == adapter_type or key.startswith(f"{adapter_type}:"):
                connections.append(key)
        return sorted(connections)

    @classmethod
    def get_connection_instance(
        cls, adapter_type: str, connection_name: str
    ) -> BaseAdapter | None:
        """Get a specific connection instance if cached.

        Args:
            adapter_type: Base adapter type (e.g., "github")
            connection_name: Connection name (e.g., "work")

        Returns:
            Cached adapter instance or None if not cached

        """
        cache_key = cls._get_cache_key(adapter_type, connection_name)
        return cls._instances.get(cache_key)

    @classmethod
    def remove_connection(cls, adapter_type: str, connection_name: str) -> bool:
        """Remove a specific connection from cache.

        Args:
            adapter_type: Base adapter type (e.g., "github")
            connection_name: Connection name (e.g., "work")

        Returns:
            True if connection was removed, False if not found

        """
        cache_key = cls._get_cache_key(adapter_type, connection_name)
        if cache_key in cls._instances:
            del cls._instances[cache_key]
            return True
        return False

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if an adapter is registered.

        Args:
            name: Adapter name to check

        Returns:
            True if registered

        """
        return name in cls._adapters

    @classmethod
    async def close_all(cls) -> None:
        """Close all adapter instances and clear cache."""
        for instance in cls._instances.values():
            await instance.close()
        cls._instances.clear()

    @classmethod
    def clear_registry(cls) -> None:
        """Clear all registrations and instances.

        Useful for testing or reinitialization.
        """
        cls._adapters.clear()
        cls._instances.clear()


def adapter_factory(
    adapter_type: str,
    config: dict[str, Any],
    connection_name: str | None = None,
) -> BaseAdapter:
    """Create adapter instance using factory pattern.

    Args:
        adapter_type: Type of adapter to create
        config: Configuration for the adapter
        connection_name: Optional connection name for multi-account support

    Returns:
        Configured adapter instance

    """
    return AdapterRegistry.get_adapter(
        adapter_type, config, connection_name=connection_name
    )
