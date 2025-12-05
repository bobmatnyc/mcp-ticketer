"""Unit tests for adapter registry module."""

import builtins
from typing import Any

import pytest

from mcp_ticketer.core.adapter import BaseAdapter
from mcp_ticketer.core.models import Comment, SearchQuery, Task, TicketState
from mcp_ticketer.core.registry import AdapterRegistry, adapter_factory


class MockAdapter(BaseAdapter[Task]):
    """Mock adapter for testing."""

    def __init__(self, config: dict[str, Any]):
        """Initialize mock adapter."""
        super().__init__(config)
        self.config = config
        self.closed = False

    def _get_state_mapping(self) -> dict[TicketState, str]:
        """Return mock state mapping."""
        return {state: state.value for state in TicketState}

    async def create(self, ticket: Task) -> Task:
        """Mock create method."""
        return ticket

    async def read(self, ticket_id: str) -> Task | None:
        """Mock read method."""
        return None

    async def update(self, ticket_id: str, updates: dict[str, Any]) -> Task | None:
        """Mock update method."""
        return None

    async def delete(self, ticket_id: str) -> bool:
        """Mock delete method."""
        return True

    async def list(
        self, limit: int = 10, offset: int = 0, filters: dict | None = None
    ) -> list[Task]:
        """Mock list method."""
        return []

    async def search(self, query: SearchQuery) -> builtins.list[Task]:
        """Mock search method."""
        return []

    async def transition_state(
        self, ticket_id: str, target_state: TicketState
    ) -> Task | None:
        """Mock transition state method."""
        return None

    async def add_comment(self, comment: Comment) -> Comment:
        """Mock add comment method."""
        return comment

    async def get_comments(
        self, ticket_id: str, limit: int = 10, offset: int = 0
    ) -> builtins.list[Comment]:
        """Mock get comments method."""
        return []

    async def close(self):
        """Mock close method."""
        self.closed = True

    async def validate_credentials(self) -> bool:
        """Mock validate credentials method."""
        return True

    async def milestone_create(
        self, name: str, target_date=None, labels=None, description=""
    ):
        """Mock milestone create method."""
        return None

    async def milestone_get(self, milestone_id: str):
        """Mock milestone get method."""
        return None

    async def milestone_list(self, project_id=None, state=None):
        """Mock milestone list method."""
        return []

    async def milestone_update(
        self, milestone_id: str, name=None, target_date=None, state=None
    ):
        """Mock milestone update method."""
        return None

    async def milestone_delete(self, milestone_id: str) -> bool:
        """Mock milestone delete method."""
        return True

    async def milestone_get_issues(self, milestone_id: str, state=None):
        """Mock milestone get issues method."""
        return []


class InvalidAdapter:
    """Invalid adapter that doesn't inherit from BaseAdapter."""

    def __init__(self, config: dict[str, Any]):
        """Initialize invalid adapter."""
        self.config = config


@pytest.fixture(autouse=True)
def clear_registry() -> None:
    """Clear registry before and after each test."""
    AdapterRegistry.clear_registry()
    yield
    AdapterRegistry.clear_registry()


@pytest.mark.unit
class TestAdapterRegistry:
    """Test AdapterRegistry class."""

    def test_register_valid_adapter(self) -> None:
        """Test registering a valid adapter."""
        AdapterRegistry.register("mock", MockAdapter)

        assert AdapterRegistry.is_registered("mock")
        adapters = AdapterRegistry.list_adapters()
        assert "mock" in adapters
        assert adapters["mock"] == MockAdapter

    def test_register_invalid_adapter_raises_error(self) -> None:
        """Test that registering an invalid adapter raises TypeError."""
        with pytest.raises(TypeError) as exc_info:
            AdapterRegistry.register("invalid", InvalidAdapter)

        assert "must be a subclass of BaseAdapter" in str(exc_info.value)

    def test_unregister_adapter(self) -> None:
        """Test unregistering an adapter."""
        AdapterRegistry.register("mock", MockAdapter)
        assert AdapterRegistry.is_registered("mock")

        AdapterRegistry.unregister("mock")

        assert not AdapterRegistry.is_registered("mock")
        adapters = AdapterRegistry.list_adapters()
        assert "mock" not in adapters

    def test_unregister_nonexistent_adapter_no_error(self) -> None:
        """Test that unregistering a nonexistent adapter doesn't raise error."""
        # Should not raise any error
        AdapterRegistry.unregister("nonexistent")

    def test_is_registered_returns_false_for_nonexistent(self) -> None:
        """Test that is_registered returns False for nonexistent adapters."""
        assert not AdapterRegistry.is_registered("nonexistent")

    def test_list_adapters_returns_copy(self) -> None:
        """Test that list_adapters returns a copy, not the original dict."""
        AdapterRegistry.register("mock1", MockAdapter)
        AdapterRegistry.register("mock2", MockAdapter)

        adapters1 = AdapterRegistry.list_adapters()
        adapters2 = AdapterRegistry.list_adapters()

        assert adapters1 == adapters2
        assert adapters1 is not adapters2  # Different objects

    def test_list_adapters_empty(self) -> None:
        """Test listing adapters when none are registered."""
        adapters = AdapterRegistry.list_adapters()

        assert adapters == {}
        assert isinstance(adapters, dict)

    def test_get_adapter_creates_instance(self) -> None:
        """Test getting an adapter creates an instance."""
        AdapterRegistry.register("mock", MockAdapter)
        config = {"key": "value"}

        adapter = AdapterRegistry.get_adapter("mock", config)

        assert isinstance(adapter, MockAdapter)
        assert adapter.config == config

    def test_get_adapter_caches_instance(self) -> None:
        """Test that get_adapter caches instances."""
        AdapterRegistry.register("mock", MockAdapter)
        config = {"key": "value"}

        adapter1 = AdapterRegistry.get_adapter("mock", config)
        adapter2 = AdapterRegistry.get_adapter("mock", config)

        assert adapter1 is adapter2  # Same instance

    def test_get_adapter_force_new_creates_new_instance(self) -> None:
        """Test that force_new creates a new instance."""
        AdapterRegistry.register("mock", MockAdapter)
        config = {"key": "value"}

        adapter1 = AdapterRegistry.get_adapter("mock", config)
        adapter2 = AdapterRegistry.get_adapter("mock", config, force_new=True)

        assert adapter1 is not adapter2  # Different instances
        assert isinstance(adapter1, MockAdapter)
        assert isinstance(adapter2, MockAdapter)

    def test_get_adapter_unregistered_raises_error(self) -> None:
        """Test that getting an unregistered adapter raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            AdapterRegistry.get_adapter("nonexistent")

        assert "not registered" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)

    def test_get_adapter_error_shows_available_adapters(self) -> None:
        """Test that error message shows available adapters."""
        AdapterRegistry.register("mock1", MockAdapter)
        AdapterRegistry.register("mock2", MockAdapter)

        with pytest.raises(ValueError) as exc_info:
            AdapterRegistry.get_adapter("nonexistent")

        error_msg = str(exc_info.value)
        assert "Available adapters:" in error_msg
        assert "mock1" in error_msg
        assert "mock2" in error_msg

    def test_get_adapter_with_no_config(self) -> None:
        """Test getting an adapter with no config."""
        AdapterRegistry.register("mock", MockAdapter)

        adapter = AdapterRegistry.get_adapter("mock")

        assert isinstance(adapter, MockAdapter)
        assert adapter.config == {}

    @pytest.mark.asyncio
    async def test_close_all_closes_instances(self):
        """Test that close_all closes all adapter instances."""
        AdapterRegistry.register("mock", MockAdapter)

        adapter = AdapterRegistry.get_adapter("mock", {"key": "value"})
        assert not adapter.closed

        await AdapterRegistry.close_all()

        assert adapter.closed

    @pytest.mark.asyncio
    async def test_close_all_clears_instances(self):
        """Test that close_all clears the instances cache."""
        AdapterRegistry.register("mock", MockAdapter)

        adapter1 = AdapterRegistry.get_adapter("mock", {"key": "value"})
        await AdapterRegistry.close_all()

        # Getting adapter again should create new instance
        adapter2 = AdapterRegistry.get_adapter("mock", {"key": "value"})
        assert adapter1 is not adapter2

    def test_clear_registry_removes_all(self) -> None:
        """Test that clear_registry removes all registrations and instances."""
        AdapterRegistry.register("mock1", MockAdapter)
        AdapterRegistry.register("mock2", MockAdapter)
        AdapterRegistry.get_adapter("mock1", {"key": "value"})

        AdapterRegistry.clear_registry()

        assert not AdapterRegistry.is_registered("mock1")
        assert not AdapterRegistry.is_registered("mock2")
        assert AdapterRegistry.list_adapters() == {}

    def test_unregister_removes_instance_cache(self) -> None:
        """Test that unregister also removes cached instances."""
        AdapterRegistry.register("mock", MockAdapter)
        adapter1 = AdapterRegistry.get_adapter("mock", {"key": "value"})

        AdapterRegistry.unregister("mock")

        # Re-register and get - should be new instance
        AdapterRegistry.register("mock", MockAdapter)
        adapter2 = AdapterRegistry.get_adapter("mock", {"key": "value"})

        assert adapter1 is not adapter2


@pytest.mark.unit
class TestAdapterFactory:
    """Test adapter_factory function."""

    def test_adapter_factory_creates_adapter(self) -> None:
        """Test that adapter_factory creates an adapter."""
        AdapterRegistry.register("mock", MockAdapter)
        config = {"key": "value"}

        adapter = adapter_factory("mock", config)

        assert isinstance(adapter, MockAdapter)
        assert adapter.config == config

    def test_adapter_factory_uses_registry(self) -> None:
        """Test that adapter_factory uses the registry."""
        AdapterRegistry.register("mock", MockAdapter)

        adapter1 = adapter_factory("mock", {"key": "value"})
        adapter2 = adapter_factory("mock", {"key": "value"})

        # Should use cached instance from registry
        assert adapter1 is adapter2

    def test_adapter_factory_unregistered_raises_error(self) -> None:
        """Test that adapter_factory raises error for unregistered adapters."""
        with pytest.raises(ValueError) as exc_info:
            adapter_factory("nonexistent", {})

        assert "not registered" in str(exc_info.value)


@pytest.mark.unit
class TestRegistryMultipleAdapters:
    """Test registry with multiple adapters."""

    def test_register_multiple_adapters(self) -> None:
        """Test registering multiple different adapters."""
        AdapterRegistry.register("mock1", MockAdapter)
        AdapterRegistry.register("mock2", MockAdapter)

        assert AdapterRegistry.is_registered("mock1")
        assert AdapterRegistry.is_registered("mock2")

        adapters = AdapterRegistry.list_adapters()
        assert len(adapters) == 2

    def test_get_different_adapters(self) -> None:
        """Test getting different adapters."""
        AdapterRegistry.register("mock1", MockAdapter)
        AdapterRegistry.register("mock2", MockAdapter)

        adapter1 = AdapterRegistry.get_adapter("mock1", {"id": 1})
        adapter2 = AdapterRegistry.get_adapter("mock2", {"id": 2})

        assert adapter1 is not adapter2
        assert adapter1.config == {"id": 1}
        assert adapter2.config == {"id": 2}

    def test_unregister_one_keeps_others(self) -> None:
        """Test that unregistering one adapter keeps others."""
        AdapterRegistry.register("mock1", MockAdapter)
        AdapterRegistry.register("mock2", MockAdapter)

        AdapterRegistry.unregister("mock1")

        assert not AdapterRegistry.is_registered("mock1")
        assert AdapterRegistry.is_registered("mock2")
