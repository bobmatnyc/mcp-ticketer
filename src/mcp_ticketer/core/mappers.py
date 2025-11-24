"""Centralized mapping utilities for state and priority conversions."""

import logging
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any, Generic, TypeVar

from .models import Priority, TicketState

logger = logging.getLogger(__name__)

T = TypeVar("T")
U = TypeVar("U")


class BiDirectionalDict(Generic[T, U]):
    """Bidirectional dictionary for efficient lookups in both directions."""

    def __init__(self, mapping: dict[T, U]):
        """Initialize with forward mapping.

        Args:
            mapping: Forward mapping dictionary

        """
        self._forward: dict[T, U] = mapping.copy()
        self._reverse: dict[U, T] = {v: k for k, v in mapping.items()}
        self._cache: dict[str, Any] = {}

    def get_forward(self, key: T, default: U | None = None) -> U | None:
        """Get value by forward key."""
        return self._forward.get(key, default)

    def get_reverse(self, key: U, default: T | None = None) -> T | None:
        """Get value by reverse key."""
        return self._reverse.get(key, default)

    def contains_forward(self, key: T) -> bool:
        """Check if forward key exists."""
        return key in self._forward

    def contains_reverse(self, key: U) -> bool:
        """Check if reverse key exists."""
        return key in self._reverse

    def forward_keys(self) -> list[T]:
        """Get all forward keys."""
        return list(self._forward.keys())

    def reverse_keys(self) -> list[U]:
        """Get all reverse keys."""
        return list(self._reverse.keys())

    def items(self) -> list[tuple[T, U]]:
        """Get all key-value pairs."""
        return list(self._forward.items())


class BaseMapper(ABC):
    """Base class for mapping utilities."""

    def __init__(self, cache_size: int = 128):
        """Initialize mapper with caching.

        Args:
            cache_size: Size of LRU cache for mapping results

        """
        self.cache_size = cache_size
        self._cache: dict[str, Any] = {}

    @abstractmethod
    def get_mapping(self) -> BiDirectionalDict:
        """Get the bidirectional mapping."""
        pass

    def clear_cache(self) -> None:
        """Clear the mapping cache."""
        self._cache.clear()


class StateMapper(BaseMapper):
    """Universal state mapping utility."""

    def __init__(
        self, adapter_type: str, custom_mappings: dict[str, Any] | None = None
    ):
        """Initialize state mapper.

        Args:
            adapter_type: Type of adapter (github, jira, linear, etc.)
            custom_mappings: Custom state mappings to override defaults

        """
        super().__init__()
        self.adapter_type = adapter_type
        self.custom_mappings = custom_mappings or {}
        self._mapping: BiDirectionalDict | None = None

    @lru_cache(maxsize=1)
    def get_mapping(self) -> BiDirectionalDict[TicketState, str]:
        """Get cached bidirectional state mapping."""
        if self._mapping is not None:
            return self._mapping

        # Default mappings by adapter type
        default_mappings: dict[str, dict[TicketState, str]] = {
            "github": {
                TicketState.OPEN: "open",
                TicketState.IN_PROGRESS: "open",  # Uses labels
                TicketState.READY: "open",  # Uses labels
                TicketState.TESTED: "open",  # Uses labels
                TicketState.DONE: "closed",
                TicketState.WAITING: "open",  # Uses labels
                TicketState.BLOCKED: "open",  # Uses labels
                TicketState.CLOSED: "closed",
            },
            "jira": {
                TicketState.OPEN: "To Do",
                TicketState.IN_PROGRESS: "In Progress",
                TicketState.READY: "In Review",
                TicketState.TESTED: "Testing",
                TicketState.DONE: "Done",
                TicketState.WAITING: "Waiting",
                TicketState.BLOCKED: "Blocked",
                TicketState.CLOSED: "Closed",
            },
            "linear": {
                TicketState.OPEN: "backlog",
                TicketState.IN_PROGRESS: "started",
                TicketState.READY: "started",  # Uses labels
                TicketState.TESTED: "started",  # Uses labels
                TicketState.DONE: "completed",
                TicketState.WAITING: "unstarted",  # Uses labels
                TicketState.BLOCKED: "unstarted",  # Uses labels
                TicketState.CLOSED: "canceled",
            },
            "aitrackdown": {
                TicketState.OPEN: "open",
                TicketState.IN_PROGRESS: "in-progress",
                TicketState.READY: "ready",
                TicketState.TESTED: "tested",
                TicketState.DONE: "done",
                TicketState.WAITING: "waiting",
                TicketState.BLOCKED: "blocked",
                TicketState.CLOSED: "closed",
            },
        }

        mapping: dict[TicketState, str] = default_mappings.get(self.adapter_type, {})

        # Apply custom mappings (cast to proper type)
        if self.custom_mappings:
            # custom_mappings might have str keys, need to convert to TicketState
            for key, value in self.custom_mappings.items():
                if isinstance(key, TicketState):
                    mapping[key] = value

        self._mapping = BiDirectionalDict[TicketState, str](mapping)
        return self._mapping

    def to_system_state(self, adapter_state: str) -> TicketState:
        """Convert adapter-specific state to universal state.

        Args:
            adapter_state: State in adapter format

        Returns:
            Universal ticket state

        """
        cache_key = f"to_system_{adapter_state}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if isinstance(cached, TicketState):
                return cached

        mapping = self.get_mapping()
        result = mapping.get_reverse(adapter_state)

        if result is None:
            # Fallback: try case-insensitive matching
            adapter_state_lower = adapter_state.lower()
            for universal_state, system_state in mapping.items():
                if (
                    isinstance(system_state, str)
                    and system_state.lower() == adapter_state_lower
                ):
                    result = universal_state
                    break

        if result is None:
            logger.warning(
                f"Unknown {self.adapter_type} state: {adapter_state}, defaulting to OPEN"
            )
            result = TicketState.OPEN

        self._cache[cache_key] = result
        return result

    def from_system_state(self, system_state: TicketState) -> str:
        """Convert universal state to adapter-specific state.

        Args:
            system_state: Universal ticket state

        Returns:
            State in adapter format

        """
        cache_key = f"from_system_{system_state.value}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if isinstance(cached, str):
                return cached

        mapping = self.get_mapping()
        result = mapping.get_forward(system_state)

        if result is None:
            logger.warning(
                f"No {self.adapter_type} mapping for state: {system_state}, using default"
            )
            # Fallback to first available state
            available_states = mapping.reverse_keys()
            result = available_states[0] if available_states else "open"

        self._cache[cache_key] = result
        return result

    def get_available_states(self) -> list[str]:
        """Get all available adapter states."""
        return self.get_mapping().reverse_keys()

    def supports_state_labels(self) -> bool:
        """Check if adapter uses labels for extended states."""
        return self.adapter_type in ["github", "linear"]

    def get_state_label(self, state: TicketState) -> str | None:
        """Get label name for extended states that require labels.

        Args:
            state: Universal ticket state

        Returns:
            Label name if state requires a label, None otherwise

        """
        if not self.supports_state_labels():
            return None

        # States that require labels in GitHub and Linear
        state_labels = {
            TicketState.IN_PROGRESS: "in-progress",
            TicketState.READY: "ready",
            TicketState.TESTED: "tested",
            TicketState.WAITING: "waiting",
            TicketState.BLOCKED: "blocked",
        }

        return state_labels.get(state)


class PriorityMapper(BaseMapper):
    """Universal priority mapping utility."""

    def __init__(
        self, adapter_type: str, custom_mappings: dict[str, Any] | None = None
    ):
        """Initialize priority mapper.

        Args:
            adapter_type: Type of adapter (github, jira, linear, etc.)
            custom_mappings: Custom priority mappings to override defaults

        """
        super().__init__()
        self.adapter_type = adapter_type
        self.custom_mappings = custom_mappings or {}
        self._mapping: BiDirectionalDict | None = None

    @lru_cache(maxsize=1)
    def get_mapping(self) -> BiDirectionalDict[Priority, Any]:
        """Get cached bidirectional priority mapping."""
        if self._mapping is not None:
            return self._mapping

        # Default mappings by adapter type
        default_mappings: dict[str, dict[Priority, Any]] = {
            "github": {
                Priority.CRITICAL: "P0",
                Priority.HIGH: "P1",
                Priority.MEDIUM: "P2",
                Priority.LOW: "P3",
            },
            "jira": {
                Priority.CRITICAL: "Highest",
                Priority.HIGH: "High",
                Priority.MEDIUM: "Medium",
                Priority.LOW: "Low",
            },
            "linear": {
                Priority.CRITICAL: 1,
                Priority.HIGH: 2,
                Priority.MEDIUM: 3,
                Priority.LOW: 4,
            },
            "aitrackdown": {
                Priority.CRITICAL: "critical",
                Priority.HIGH: "high",
                Priority.MEDIUM: "medium",
                Priority.LOW: "low",
            },
        }

        mapping: dict[Priority, Any] = default_mappings.get(self.adapter_type, {})

        # Apply custom mappings (cast to proper type)
        if self.custom_mappings:
            # custom_mappings might have str keys, need to convert to Priority
            for key, value in self.custom_mappings.items():
                if isinstance(key, Priority):
                    mapping[key] = value

        self._mapping = BiDirectionalDict[Priority, Any](mapping)
        return self._mapping

    def to_system_priority(self, adapter_priority: Any) -> Priority:
        """Convert adapter-specific priority to universal priority.

        Args:
            adapter_priority: Priority in adapter format

        Returns:
            Universal priority

        """
        cache_key = f"to_system_{adapter_priority}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if isinstance(cached, Priority):
                return cached

        mapping = self.get_mapping()
        result = mapping.get_reverse(adapter_priority)

        if result is None:
            # Fallback: try parsing different formats
            if isinstance(adapter_priority, str):
                adapter_priority_lower = adapter_priority.lower()
                for universal_priority, system_priority in mapping.items():
                    if (
                        isinstance(system_priority, str)
                        and system_priority.lower() == adapter_priority_lower
                    ):
                        result = universal_priority
                        break
                    # Check for common priority patterns
                    elif (
                        "critical" in adapter_priority_lower
                        or "urgent" in adapter_priority_lower
                        or "highest" in adapter_priority_lower
                        or adapter_priority_lower in ["p0", "0"]
                    ):
                        result = Priority.CRITICAL
                        break
                    elif "high" in adapter_priority_lower or adapter_priority_lower in [
                        "p1",
                        "1",
                    ]:
                        result = Priority.HIGH
                        break
                    elif "low" in adapter_priority_lower or adapter_priority_lower in [
                        "p3",
                        "3",
                        "lowest",
                    ]:
                        result = Priority.LOW
                        break
            elif isinstance(adapter_priority, int | float):
                # Handle numeric priorities (Linear-style)
                if adapter_priority <= 1:
                    result = Priority.CRITICAL
                elif adapter_priority == 2:
                    result = Priority.HIGH
                elif adapter_priority >= 4:
                    result = Priority.LOW
                else:
                    result = Priority.MEDIUM

        if result is None:
            logger.warning(
                f"Unknown {self.adapter_type} priority: {adapter_priority}, defaulting to MEDIUM"
            )
            result = Priority.MEDIUM

        self._cache[cache_key] = result
        return result

    def from_system_priority(self, system_priority: Priority) -> Any:
        """Convert universal priority to adapter-specific priority.

        Args:
            system_priority: Universal priority

        Returns:
            Priority in adapter format

        """
        cache_key = f"from_system_{system_priority.value}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        mapping = self.get_mapping()
        result = mapping.get_forward(system_priority)

        if result is None:
            logger.warning(
                f"No {self.adapter_type} mapping for priority: {system_priority}"
            )
            # Fallback based on adapter type
            fallback_mappings = {
                "github": "P2",
                "jira": "Medium",
                "linear": 3,
                "aitrackdown": "medium",
            }
            result = fallback_mappings.get(self.adapter_type, "medium")

        self._cache[cache_key] = result
        return result

    def get_available_priorities(self) -> list[Any]:
        """Get all available adapter priorities."""
        return self.get_mapping().reverse_keys()

    def get_priority_labels(self, priority: Priority) -> list[str]:
        """Get possible label names for a priority (GitHub-style).

        Args:
            priority: Universal priority

        Returns:
            List of possible label names

        """
        if self.adapter_type != "github":
            return []

        # GitHub priority labels (including variations)
        priority_labels = {
            Priority.CRITICAL: ["P0", "critical", "urgent", "highest"],
            Priority.HIGH: ["P1", "high"],
            Priority.MEDIUM: ["P2", "medium"],
            Priority.LOW: ["P3", "low", "lowest"],
        }

        return priority_labels.get(priority, [])

    def detect_priority_from_labels(self, labels: list[str]) -> Priority:
        """Detect priority from issue labels (GitHub-style).

        Args:
            labels: List of label names

        Returns:
            Detected priority

        """
        if self.adapter_type != "github":
            return Priority.MEDIUM

        labels_lower = [label.lower() for label in labels]

        # Check each priority level
        for priority in [
            Priority.CRITICAL,
            Priority.HIGH,
            Priority.LOW,
            Priority.MEDIUM,
        ]:
            priority_labels = self.get_priority_labels(priority)
            for priority_label in priority_labels:
                if priority_label.lower() in labels_lower:
                    return priority

        return Priority.MEDIUM


class MapperRegistry:
    """Registry for managing mappers across different adapters."""

    _state_mappers: dict[str, StateMapper] = {}
    _priority_mappers: dict[str, PriorityMapper] = {}

    @classmethod
    def get_state_mapper(
        cls, adapter_type: str, custom_mappings: dict[str, Any] | None = None
    ) -> StateMapper:
        """Get or create state mapper for adapter type.

        Args:
            adapter_type: Adapter type
            custom_mappings: Custom mappings

        Returns:
            State mapper instance

        """
        cache_key = f"{adapter_type}_{hash(str(custom_mappings))}"
        if cache_key not in cls._state_mappers:
            cls._state_mappers[cache_key] = StateMapper(adapter_type, custom_mappings)
        return cls._state_mappers[cache_key]

    @classmethod
    def get_priority_mapper(
        cls, adapter_type: str, custom_mappings: dict[str, Any] | None = None
    ) -> PriorityMapper:
        """Get or create priority mapper for adapter type.

        Args:
            adapter_type: Adapter type
            custom_mappings: Custom mappings

        Returns:
            Priority mapper instance

        """
        cache_key = f"{adapter_type}_{hash(str(custom_mappings))}"
        if cache_key not in cls._priority_mappers:
            cls._priority_mappers[cache_key] = PriorityMapper(
                adapter_type, custom_mappings
            )
        return cls._priority_mappers[cache_key]

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all mapper caches."""
        for state_mapper in cls._state_mappers.values():
            state_mapper.clear_cache()
        for priority_mapper in cls._priority_mappers.values():
            priority_mapper.clear_cache()

    @classmethod
    def reset(cls) -> None:
        """Reset all mappers."""
        cls._state_mappers.clear()
        cls._priority_mappers.clear()
