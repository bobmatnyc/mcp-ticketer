"""Dependency graph analysis for tickets.

This module parses ticket descriptions and builds dependency graphs to:
- Identify ticket dependencies (blocks/depends on)
- Find critical paths (longest dependency chains)
- Detect circular dependencies
- Recommend optimal work order
"""

import re
from collections import defaultdict
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from ..core.models import Task


class DependencyNode(BaseModel):
    """A node in the dependency graph.

    Attributes:
        ticket_id: ID of the ticket
        blocks: List of ticket IDs that this ticket blocks
        blocked_by: List of ticket IDs that block this ticket
        depth: Depth in the dependency tree (0 = leaf, higher = more dependencies)

    """

    ticket_id: str
    blocks: list[str] = []
    blocked_by: list[str] = []
    depth: int = 0


class DependencyGraph:
    """Build and analyze ticket dependency graphs.

    Parses ticket descriptions to identify references to other tickets
    and builds a directed graph of dependencies.

    Supported patterns:
    - "Related to TICKET-123"
    - "Depends on 1M-315"
    - "Blocks #456"
    - "1M-316: Feature name"
    - "Blocked by PROJ-789"
    """

    # Regex patterns for dependency detection
    DEPENDENCY_PATTERNS = [
        (r"depends\s+on\s+([A-Z0-9]+-\d+)\b", "blocked_by"),
        (r"depends\s+on\s+#(\d+)\b", "blocked_by"),
        (r"blocked\s+by\s+([A-Z0-9]+-\d+)\b", "blocked_by"),
        (r"blocked\s+by\s+#(\d+)\b", "blocked_by"),
        (r"blocks\s+([A-Z0-9]+-\d+)\b", "blocks"),
        (r"blocks\s+#(\d+)\b", "blocks"),
        (r"related\s+to\s+([A-Z0-9]+-\d+)\b", "related"),
        (r"related\s+to\s+#(\d+)\b", "related"),
        # Inline references like "1M-316:" or "TICKET-123:"
        (r"\b([A-Z0-9]+-\d+):", "related"),
    ]

    def __init__(self) -> None:
        """Initialize the dependency graph."""
        self.nodes: dict[str, DependencyNode] = {}
        self.edges: dict[str, set[str]] = defaultdict(set)  # ticket_id -> blocks set
        self.reverse_edges: dict[str, set[str]] = defaultdict(
            set
        )  # ticket_id -> blocked_by set

    def add_ticket(self, ticket: "Task") -> None:
        """Add a ticket to the graph and extract its dependencies.

        Args:
            ticket: The ticket to add

        """
        ticket_id = ticket.id or ""
        if not ticket_id:
            return

        # Initialize node if not exists
        if ticket_id not in self.nodes:
            self.nodes[ticket_id] = DependencyNode(ticket_id=ticket_id)

        # Parse description and title for dependencies
        text = f"{ticket.title or ''}\n{ticket.description or ''}"
        dependencies = self._extract_dependencies(text, ticket_id)

        # Update graph edges
        for dep_type, dep_id in dependencies:
            if dep_type == "blocks":
                self.edges[ticket_id].add(dep_id)
                self.reverse_edges[dep_id].add(ticket_id)
            elif dep_type == "blocked_by":
                self.edges[dep_id].add(ticket_id)
                self.reverse_edges[ticket_id].add(dep_id)
            elif dep_type == "related":
                # For related, add bidirectional soft dependency
                # (lower priority in recommendations)
                pass

    def _extract_dependencies(self, text: str, ticket_id: str) -> list[tuple[str, str]]:
        """Extract dependencies from ticket text.

        Args:
            text: The text to parse (title + description)
            ticket_id: ID of the ticket being parsed (to avoid self-references)

        Returns:
            List of (dependency_type, ticket_id) tuples

        """
        dependencies = []
        text_lower = text.lower()

        for pattern, dep_type in self.DEPENDENCY_PATTERNS:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                dep_id = match.group(1)
                # Normalize ticket ID (handle both "1M-123" and "123" formats)
                if not re.match(r"[A-Z0-9]+-\d+", dep_id, re.IGNORECASE):
                    # If just a number, try to infer project prefix from current ticket
                    if "-" in ticket_id:
                        prefix = ticket_id.split("-")[0]
                        dep_id = f"{prefix}-{dep_id}"

                # Avoid self-references
                if dep_id.upper() != ticket_id.upper():
                    dependencies.append((dep_type, dep_id.upper()))

        return dependencies

    def calculate_depths(self) -> None:
        """Calculate depth of each node in the dependency tree.

        Depth is the longest path from this node to a leaf node.
        Higher depth means more dependencies downstream.
        """
        # Build adjacency list from edges
        visited = set()

        def dfs(node_id: str) -> int:
            """DFS to calculate max depth."""
            if node_id in visited:
                return 0  # Avoid cycles

            visited.add(node_id)

            # Get all tickets this one blocks
            blocked_tickets = self.edges.get(node_id, set())
            if not blocked_tickets:
                depth = 0
            else:
                # Depth is 1 + max depth of any blocked ticket
                depth = 1 + max(
                    (dfs(blocked) for blocked in blocked_tickets), default=0
                )

            if node_id in self.nodes:
                self.nodes[node_id].depth = depth

            visited.remove(node_id)
            return depth

        # Calculate depth for all nodes
        for node_id in list(self.nodes.keys()):
            if node_id not in visited:
                dfs(node_id)

    def get_critical_path(self) -> list[str]:
        """Get the critical path (longest dependency chain).

        Returns:
            List of ticket IDs in the critical path, ordered from
            start to end

        """
        if not self.nodes:
            return []

        # Find node with maximum depth
        max_depth_node = max(self.nodes.values(), key=lambda n: n.depth)

        if max_depth_node.depth == 0:
            return [max_depth_node.ticket_id]

        # Trace back the critical path
        path = [max_depth_node.ticket_id]
        current = max_depth_node.ticket_id

        while True:
            blocked_tickets = self.edges.get(current, set())
            if not blocked_tickets:
                break

            # Find the blocked ticket with maximum depth
            next_ticket = max(
                blocked_tickets,
                key=lambda tid: self.nodes[tid].depth if tid in self.nodes else 0,
                default=None,
            )

            if next_ticket and next_ticket not in path:
                path.append(next_ticket)
                current = next_ticket
            else:
                break

        return path

    def get_blocked_tickets(self) -> dict[str, list[str]]:
        """Get all blocked tickets and their blockers.

        Returns:
            Dictionary mapping ticket_id -> list of blocker ticket IDs

        """
        blocked = {}
        for ticket_id, blockers in self.reverse_edges.items():
            if blockers:
                blocked[ticket_id] = list(blockers)
        return blocked

    def get_high_impact_tickets(self) -> list[tuple[str, int]]:
        """Get tickets that block the most other tickets.

        Returns:
            List of (ticket_id, count) tuples sorted by impact (descending)

        """
        impact = []
        for ticket_id, blocked_set in self.edges.items():
            if blocked_set:
                impact.append((ticket_id, len(blocked_set)))

        return sorted(impact, key=lambda x: x[1], reverse=True)

    def finalize(self) -> None:
        """Finalize the graph by calculating all metrics.

        Call this after adding all tickets to compute depths and
        other derived metrics.
        """
        # Update nodes with edge information
        for ticket_id in self.nodes:
            self.nodes[ticket_id].blocks = list(self.edges.get(ticket_id, set()))
            self.nodes[ticket_id].blocked_by = list(
                self.reverse_edges.get(ticket_id, set())
            )

        # Calculate depths
        self.calculate_depths()
