"""Hybrid adapter for multi-platform ticket synchronization.

This adapter enables synchronization across multiple ticketing systems
(Linear, JIRA, GitHub, AITrackdown) with configurable sync strategies.
"""

import builtins
import json
import logging
from pathlib import Path
from typing import Any, Optional, Union

from ..core.adapter import BaseAdapter
from ..core.models import Comment, Epic, SearchQuery, Task, TicketState
from ..core.registry import AdapterRegistry

logger = logging.getLogger(__name__)


class HybridAdapter(BaseAdapter):
    """Adapter that syncs tickets across multiple platforms.

    Supports multiple synchronization strategies:
    - PRIMARY_SOURCE: One adapter is source of truth, others are mirrors
    - BIDIRECTIONAL: Two-way sync between adapters
    - MIRROR: Clone tickets across all adapters

    Maintains mapping between ticket IDs across different systems.
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize hybrid adapter.

        Args:
            config: Hybrid configuration including:
                - adapters: List of adapter configs
                - primary_adapter: Name of primary adapter
                - sync_strategy: Sync strategy (primary_source, bidirectional, mirror)
                - mapping_file: Path to ID mapping file (optional)

        """
        super().__init__(config)

        self.adapters: dict[str, BaseAdapter] = {}
        self.primary_adapter_name = config.get("primary_adapter")
        self.sync_strategy = config.get("sync_strategy", "primary_source")

        # Initialize all adapters
        adapter_configs = config.get("adapter_configs", {})
        for name, adapter_config in adapter_configs.items():
            try:
                adapter_type = adapter_config.get("adapter")
                self.adapters[name] = AdapterRegistry.get_adapter(
                    adapter_type, adapter_config
                )
                logger.info(f"Initialized adapter: {name} ({adapter_type})")
            except Exception as e:
                logger.error(f"Failed to initialize adapter {name}: {e}")

        if not self.adapters:
            raise ValueError("No adapters successfully initialized")

        if self.primary_adapter_name not in self.adapters:
            raise ValueError(
                f"Primary adapter {self.primary_adapter_name} not found in adapters"
            )

        # Load or initialize ID mapping
        self.mapping_file = Path(
            config.get("mapping_file", ".mcp-ticketer/hybrid_mapping.json")
        )
        self.id_mapping = self._load_mapping()

    def _get_state_mapping(self) -> dict[TicketState, str]:
        """Get state mapping from primary adapter."""
        primary = self.adapters[self.primary_adapter_name]
        return primary._get_state_mapping()

    def _load_mapping(self) -> dict[str, dict[str, str]]:
        """Load ID mapping from file.

        Mapping format:
        {
            "ticket_uuid": {
                "linear": "LIN-123",
                "github": "456",
                "jira": "PROJ-789"
            }
        }

        Returns:
            Dictionary mapping universal ticket IDs to adapter-specific IDs

        """
        if self.mapping_file.exists():
            try:
                with open(self.mapping_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load mapping file: {e}")

        return {}

    def _save_mapping(self) -> None:
        """Save ID mapping to file."""
        try:
            self.mapping_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.mapping_file, "w") as f:
                json.dump(self.id_mapping, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save mapping file: {e}")

    def _store_ticket_mapping(
        self, universal_id: str, adapter_name: str, adapter_ticket_id: str
    ) -> None:
        """Store mapping between universal ID and adapter-specific ID.

        Args:
            universal_id: Universal ticket identifier
            adapter_name: Name of adapter
            adapter_ticket_id: Adapter-specific ticket ID

        """
        if universal_id not in self.id_mapping:
            self.id_mapping[universal_id] = {}

        self.id_mapping[universal_id][adapter_name] = adapter_ticket_id
        self._save_mapping()

    def _get_adapter_ticket_id(
        self, universal_id: str, adapter_name: str
    ) -> Optional[str]:
        """Get adapter-specific ticket ID from universal ID.

        Args:
            universal_id: Universal ticket identifier
            adapter_name: Name of adapter

        Returns:
            Adapter-specific ticket ID or None

        """
        return self.id_mapping.get(universal_id, {}).get(adapter_name)

    def _generate_universal_id(self) -> str:
        """Generate a universal ticket ID.

        Returns:
            UUID-like universal ticket identifier

        """
        import uuid

        return f"hybrid-{uuid.uuid4().hex[:12]}"

    async def create(self, ticket: Union[Task, Epic]) -> Union[Task, Epic]:
        """Create ticket in all configured adapters.

        Args:
            ticket: Ticket to create

        Returns:
            Created ticket with universal ID

        """
        universal_id = self._generate_universal_id()
        results = []

        # Create in primary adapter first
        primary = self.adapters[self.primary_adapter_name]
        try:
            primary_ticket = await primary.create(ticket)
            self._store_ticket_mapping(
                universal_id, self.primary_adapter_name, primary_ticket.id
            )
            results.append((self.primary_adapter_name, primary_ticket))
            logger.info(
                f"Created ticket in primary adapter {self.primary_adapter_name}: {primary_ticket.id}"
            )
        except Exception as e:
            logger.error(
                f"Failed to create ticket in primary adapter {self.primary_adapter_name}: {e}"
            )
            raise

        # Create in secondary adapters
        for name, adapter in self.adapters.items():
            if name == self.primary_adapter_name:
                continue

            try:
                # Clone ticket for this adapter
                adapter_ticket = await adapter.create(ticket)
                self._store_ticket_mapping(universal_id, name, adapter_ticket.id)
                results.append((name, adapter_ticket))
                logger.info(f"Created ticket in adapter {name}: {adapter_ticket.id}")
            except Exception as e:
                logger.error(f"Failed to create ticket in adapter {name}: {e}")
                # Continue with other adapters even if one fails

        # Return primary ticket with cross-references in description
        primary_ticket = results[0][1]
        self._add_cross_references(primary_ticket, results)

        # Set universal ID in ticket
        primary_ticket.id = universal_id

        return primary_ticket

    def _add_cross_references(
        self, ticket: Union[Task, Epic], results: list[tuple[str, Union[Task, Epic]]]
    ) -> None:
        """Add cross-references to ticket description.

        Args:
            ticket: Ticket to update
            results: List of (adapter_name, ticket) tuples

        """
        cross_refs = "\n\n---\n**Cross-Platform References:**\n"
        for adapter_name, adapter_ticket in results:
            cross_refs += f"- {adapter_name}: {adapter_ticket.id}\n"

        if ticket.description:
            ticket.description += cross_refs
        else:
            ticket.description = cross_refs.strip()

    async def read(self, ticket_id: str) -> Optional[Union[Task, Epic]]:
        """Read ticket from primary adapter.

        Args:
            ticket_id: Universal or adapter-specific ticket ID

        Returns:
            Ticket if found, None otherwise

        """
        # Check if this is a universal ID
        if ticket_id.startswith("hybrid-"):
            # Get primary adapter ticket ID
            primary_id = self._get_adapter_ticket_id(
                ticket_id, self.primary_adapter_name
            )
            if not primary_id:
                logger.warning(
                    f"No primary ticket ID found for universal ID: {ticket_id}"
                )
                return None
            ticket_id = primary_id

        # Read from primary adapter
        primary = self.adapters[self.primary_adapter_name]
        return await primary.read(ticket_id)

    async def update(
        self, ticket_id: str, updates: dict[str, Any]
    ) -> Optional[Union[Task, Epic]]:
        """Update ticket across all adapters.

        Args:
            ticket_id: Universal or adapter-specific ticket ID
            updates: Fields to update

        Returns:
            Updated ticket from primary adapter

        """
        universal_id = ticket_id
        if not ticket_id.startswith("hybrid-"):
            # Try to find universal ID by searching mapping
            universal_id = self._find_universal_id(ticket_id)
            if not universal_id:
                logger.warning(f"No universal ID found for ticket: {ticket_id}")
                # Fall back to primary adapter only
                primary = self.adapters[self.primary_adapter_name]
                return await primary.update(ticket_id, updates)

        # Update in all adapters
        results = []
        for adapter_name, adapter in self.adapters.items():
            adapter_ticket_id = self._get_adapter_ticket_id(universal_id, adapter_name)
            if not adapter_ticket_id:
                logger.warning(f"No ticket ID for adapter {adapter_name}")
                continue

            try:
                updated_ticket = await adapter.update(adapter_ticket_id, updates)
                results.append((adapter_name, updated_ticket))
                logger.info(
                    f"Updated ticket in adapter {adapter_name}: {adapter_ticket_id}"
                )
            except Exception as e:
                logger.error(f"Failed to update ticket in adapter {adapter_name}: {e}")

        # Return result from primary adapter
        for adapter_name, ticket in results:
            if adapter_name == self.primary_adapter_name:
                return ticket

        return None

    def _find_universal_id(self, adapter_ticket_id: str) -> Optional[str]:
        """Find universal ID for an adapter-specific ticket ID.

        Args:
            adapter_ticket_id: Adapter-specific ticket ID

        Returns:
            Universal ID if found, None otherwise

        """
        for universal_id, mapping in self.id_mapping.items():
            if adapter_ticket_id in mapping.values():
                return universal_id
        return None

    async def delete(self, ticket_id: str) -> bool:
        """Delete ticket from all adapters.

        Args:
            ticket_id: Universal or adapter-specific ticket ID

        Returns:
            True if deleted from at least one adapter

        """
        universal_id = ticket_id
        if not ticket_id.startswith("hybrid-"):
            universal_id = self._find_universal_id(ticket_id)
            if not universal_id:
                # Fall back to primary adapter
                primary = self.adapters[self.primary_adapter_name]
                return await primary.delete(ticket_id)

        # Delete from all adapters
        success_count = 0
        for adapter_name, adapter in self.adapters.items():
            adapter_ticket_id = self._get_adapter_ticket_id(universal_id, adapter_name)
            if not adapter_ticket_id:
                continue

            try:
                if await adapter.delete(adapter_ticket_id):
                    success_count += 1
                    logger.info(
                        f"Deleted ticket from adapter {adapter_name}: {adapter_ticket_id}"
                    )
            except Exception as e:
                logger.error(
                    f"Failed to delete ticket from adapter {adapter_name}: {e}"
                )

        # Remove from mapping
        if universal_id in self.id_mapping:
            del self.id_mapping[universal_id]
            self._save_mapping()

        return success_count > 0

    async def list(
        self, limit: int = 10, offset: int = 0, filters: Optional[dict[str, Any]] = None
    ) -> list[Union[Task, Epic]]:
        """List tickets from primary adapter.

        Args:
            limit: Maximum number of tickets
            offset: Skip this many tickets
            filters: Optional filter criteria

        Returns:
            List of tickets from primary adapter

        """
        primary = self.adapters[self.primary_adapter_name]
        return await primary.list(limit, offset, filters)

    async def search(self, query: SearchQuery) -> builtins.list[Union[Task, Epic]]:
        """Search tickets in primary adapter.

        Args:
            query: Search parameters

        Returns:
            List of tickets matching search criteria

        """
        primary = self.adapters[self.primary_adapter_name]
        return await primary.search(query)

    async def transition_state(
        self, ticket_id: str, target_state: TicketState
    ) -> Optional[Union[Task, Epic]]:
        """Transition ticket state across all adapters.

        Args:
            ticket_id: Universal or adapter-specific ticket ID
            target_state: Target state

        Returns:
            Updated ticket from primary adapter

        """
        universal_id = ticket_id
        if not ticket_id.startswith("hybrid-"):
            universal_id = self._find_universal_id(ticket_id)
            if not universal_id:
                # Fall back to primary adapter
                primary = self.adapters[self.primary_adapter_name]
                return await primary.transition_state(ticket_id, target_state)

        # Transition in all adapters
        results = []
        for adapter_name, adapter in self.adapters.items():
            adapter_ticket_id = self._get_adapter_ticket_id(universal_id, adapter_name)
            if not adapter_ticket_id:
                continue

            try:
                updated_ticket = await adapter.transition_state(
                    adapter_ticket_id, target_state
                )
                results.append((adapter_name, updated_ticket))
                logger.info(
                    f"Transitioned ticket in adapter {adapter_name}: {adapter_ticket_id}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to transition ticket in adapter {adapter_name}: {e}"
                )

        # Return result from primary adapter
        for adapter_name, ticket in results:
            if adapter_name == self.primary_adapter_name:
                return ticket

        return None

    async def add_comment(self, comment: Comment) -> Comment:
        """Add comment to ticket in all adapters.

        Args:
            comment: Comment to add

        Returns:
            Created comment from primary adapter

        """
        universal_id = comment.ticket_id
        if not comment.ticket_id.startswith("hybrid-"):
            universal_id = self._find_universal_id(comment.ticket_id)
            if not universal_id:
                # Fall back to primary adapter
                primary = self.adapters[self.primary_adapter_name]
                return await primary.add_comment(comment)

        # Add comment to all adapters
        results = []
        for adapter_name, adapter in self.adapters.items():
            adapter_ticket_id = self._get_adapter_ticket_id(universal_id, adapter_name)
            if not adapter_ticket_id:
                continue

            try:
                # Clone comment with adapter-specific ticket ID
                adapter_comment = Comment(
                    ticket_id=adapter_ticket_id,
                    content=comment.content,
                    author=comment.author,
                )
                created_comment = await adapter.add_comment(adapter_comment)
                results.append((adapter_name, created_comment))
                logger.info(
                    f"Added comment to adapter {adapter_name}: {adapter_ticket_id}"
                )
            except Exception as e:
                logger.error(f"Failed to add comment to adapter {adapter_name}: {e}")

        # Return result from primary adapter
        for adapter_name, created_comment in results:
            if adapter_name == self.primary_adapter_name:
                return created_comment

        # If no primary comment, return first successful one
        if results:
            return results[0][1]

        raise RuntimeError("Failed to add comment to any adapter")

    async def get_comments(
        self, ticket_id: str, limit: int = 10, offset: int = 0
    ) -> builtins.list[Comment]:
        """Get comments from primary adapter.

        Args:
            ticket_id: Universal or adapter-specific ticket ID
            limit: Maximum number of comments
            offset: Skip this many comments

        Returns:
            List of comments from primary adapter

        """
        if ticket_id.startswith("hybrid-"):
            # Get primary adapter ticket ID
            primary_id = self._get_adapter_ticket_id(
                ticket_id, self.primary_adapter_name
            )
            if not primary_id:
                return []
            ticket_id = primary_id

        primary = self.adapters[self.primary_adapter_name]
        return await primary.get_comments(ticket_id, limit, offset)

    async def close(self) -> None:
        """Close all adapters and cleanup resources."""
        for adapter in self.adapters.values():
            try:
                await adapter.close()
            except Exception as e:
                logger.error(f"Error closing adapter: {e}")

    async def sync_status(self) -> dict[str, Any]:
        """Get synchronization status across all adapters.

        Returns:
            Dictionary with sync status information

        """
        status = {
            "primary_adapter": self.primary_adapter_name,
            "sync_strategy": self.sync_strategy,
            "total_mapped_tickets": len(self.id_mapping),
            "adapters": {},
        }

        for adapter_name, adapter in self.adapters.items():
            try:
                # Count tickets in this adapter
                tickets = await adapter.list(limit=1000)
                ticket_count = len(tickets)

                status["adapters"][adapter_name] = {
                    "ticket_count": ticket_count,
                    "status": "connected",
                }
            except Exception as e:
                status["adapters"][adapter_name] = {"status": "error", "error": str(e)}

        return status
