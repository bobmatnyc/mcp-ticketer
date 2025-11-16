"""Adapter registry for dynamic adapter management."""

from typing import Any

from .adapter import BaseAdapter


class AdapterRegistry:
    """Registry for managing ticket system adapters."""

    _adapters: dict[str, type[BaseAdapter]] = {}
    _instances: dict[str, BaseAdapter] = {}

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
        cls._instances.pop(name, None)

    @classmethod
    def get_adapter(
        cls, name: str, config: dict[str, Any] | None = None, force_new: bool = False
    ) -> BaseAdapter:
        """Get or create an adapter instance.

        Uses factory pattern for adapter instantiation with caching.

        Args:
            name: Name of the registered adapter
            config: Configuration for the adapter
            force_new: Force creation of new instance

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

        # Return cached instance if exists and not forcing new
        if name in cls._instances and not force_new:
            return cls._instances[name]

        # Create new instance
        adapter_class = cls._adapters[name]
        config = config or {}
        instance = adapter_class(config)

        # Cache the instance
        cls._instances[name] = instance
        return instance

    @classmethod
    def list_adapters(cls) -> dict[str, type[BaseAdapter]]:
        """List all registered adapters.

        Returns:
            Dictionary of adapter names to classes

        """
        return cls._adapters.copy()

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


def adapter_factory(adapter_type: str, config: dict[str, Any]) -> BaseAdapter:
    """Create adapter instance using factory pattern.

    Args:
        adapter_type: Type of adapter to create
        config: Configuration for the adapter

    Returns:
        Configured adapter instance

    """
    return AdapterRegistry.get_adapter(adapter_type, config)
