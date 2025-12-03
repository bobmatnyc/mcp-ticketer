#!/usr/bin/env python3
"""Test semantic state name matching for Linear adapter (1M-552).

This test verifies that the Linear adapter correctly handles workflows with
multiple states of the same type using semantic name matching.
"""

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter
from mcp_ticketer.adapters.linear.types import LinearStateMapping
from mcp_ticketer.core.models import TicketState


@pytest.fixture
def mock_workflow_states():
    """Mock Linear workflow states with multiple states per type."""
    return {
        "team": {
            "states": {
                "nodes": [
                    # Multiple "unstarted" states
                    {
                        "id": "state-todo-id",
                        "name": "Todo",
                        "type": "unstarted",
                        "position": 0,
                    },
                    {
                        "id": "state-backlog-id",
                        "name": "Backlog",
                        "type": "unstarted",
                        "position": 1,
                    },
                    {
                        "id": "state-ready-id",
                        "name": "Ready",
                        "type": "unstarted",
                        "position": 2,
                    },
                    # Multiple "started" states
                    {
                        "id": "state-in-progress-id",
                        "name": "In Progress",
                        "type": "started",
                        "position": 3,
                    },
                    {
                        "id": "state-in-review-id",
                        "name": "In Review",
                        "type": "started",
                        "position": 4,
                    },
                    # Single states for other types
                    {
                        "id": "state-done-id",
                        "name": "Done",
                        "type": "completed",
                        "position": 5,
                    },
                    {
                        "id": "state-canceled-id",
                        "name": "Canceled",
                        "type": "canceled",
                        "position": 6,
                    },
                ]
            }
        }
    }


@pytest.fixture
def mock_simple_workflow_states():
    """Mock Linear workflow states with single state per type (backward compat)."""
    return {
        "team": {
            "states": {
                "nodes": [
                    {
                        "id": "state-todo-id",
                        "name": "Todo",
                        "type": "unstarted",
                        "position": 0,
                    },
                    {
                        "id": "state-in-progress-id",
                        "name": "In Progress",
                        "type": "started",
                        "position": 1,
                    },
                    {
                        "id": "state-done-id",
                        "name": "Done",
                        "type": "completed",
                        "position": 2,
                    },
                    {
                        "id": "state-canceled-id",
                        "name": "Canceled",
                        "type": "canceled",
                        "position": 3,
                    },
                ]
            }
        }
    }


class TestLinearSemanticStateMatching:
    """Test semantic state name matching for multi-state workflows."""

    @pytest.mark.asyncio
    async def test_multi_state_workflow_semantic_matching(
        self, mock_workflow_states, monkeypatch
    ):
        """Test state transitions in workflows with multiple states of same type.

        This is the core test for 1M-552: verifies that semantic name matching
        correctly resolves states like "Ready" instead of always picking "Todo"
        for the "unstarted" type.
        """

        # Mock the GraphQL query
        async def mock_execute_query(query, variables):
            return mock_workflow_states

        # Create adapter with mocked client (use valid API key format)
        adapter = LinearAdapter(
            config={
                "api_key": "lin_api_test123456789",
                "team_id": "test-team",
            }
        )

        # Mock the client's execute_query method
        monkeypatch.setattr(adapter.client, "execute_query", mock_execute_query)

        # Load workflow states
        await adapter._load_workflow_states("test-team")

        # Verify state mappings use semantic names, not just lowest position

        # READY should map to "Ready" state, NOT "Todo"
        assert adapter._workflow_states[TicketState.READY.value] == "state-ready-id"
        assert (
            adapter._workflow_states[TicketState.READY.value] != "state-todo-id"
        )  # ✅ Not lowest position

        # TESTED should map to "In Review" state, NOT "In Progress"
        assert (
            adapter._workflow_states[TicketState.TESTED.value] == "state-in-review-id"
        )
        assert (
            adapter._workflow_states[TicketState.TESTED.value] != "state-in-progress-id"
        )  # ✅ Not lowest position

        # OPEN should map to "Todo" (first semantic match)
        assert adapter._workflow_states[TicketState.OPEN.value] == "state-todo-id"

        # IN_PROGRESS should map to "In Progress"
        assert (
            adapter._workflow_states[TicketState.IN_PROGRESS.value]
            == "state-in-progress-id"
        )

        # DONE and CLOSED should map correctly (single states)
        assert adapter._workflow_states[TicketState.DONE.value] == "state-done-id"
        assert adapter._workflow_states[TicketState.CLOSED.value] == "state-canceled-id"

    @pytest.mark.asyncio
    async def test_simple_workflow_backward_compatibility(
        self, mock_simple_workflow_states, monkeypatch
    ):
        """Test that simple workflows (1 state per type) still work correctly.

        Verifies backward compatibility: when there's only one state per type,
        the behavior should be the same as before (type-based matching).
        """

        # Mock the GraphQL query
        async def mock_execute_query(query, variables):
            return mock_simple_workflow_states

        # Create adapter with mocked client (use valid API key format)
        adapter = LinearAdapter(
            config={
                "api_key": "lin_api_test123456789",
                "team_id": "test-team",
            }
        )

        # Mock the client's execute_query method
        monkeypatch.setattr(adapter.client, "execute_query", mock_execute_query)

        # Load workflow states
        await adapter._load_workflow_states("test-team")

        # All "unstarted" states should map to "Todo" (only unstarted state)
        assert adapter._workflow_states[TicketState.OPEN.value] == "state-todo-id"
        assert adapter._workflow_states[TicketState.READY.value] == "state-todo-id"
        # WAITING and BLOCKED are "unstarted" type, should also map to "Todo"
        # (they won't be in the mapping if no semantic name matches, falls back to type)

        # All "started" states should map to "In Progress"
        assert (
            adapter._workflow_states[TicketState.IN_PROGRESS.value]
            == "state-in-progress-id"
        )
        # TESTED is "started" type, should also map to "In Progress"
        # (same fallback behavior)

        # Single states should work correctly
        assert adapter._workflow_states[TicketState.DONE.value] == "state-done-id"
        assert adapter._workflow_states[TicketState.CLOSED.value] == "state-canceled-id"

    @pytest.mark.asyncio
    async def test_semantic_name_priority_over_type(
        self, mock_workflow_states, monkeypatch
    ):
        """Test that semantic name matching takes priority over type matching.

        Even if there are multiple states of the same type, semantic names
        should be matched first before falling back to type-based selection.
        """

        # Mock the GraphQL query
        async def mock_execute_query(query, variables):
            return mock_workflow_states

        adapter = LinearAdapter(
            config={
                "api_key": "lin_api_test123456789",
                "team_id": "test-team",
            }
        )

        monkeypatch.setattr(adapter.client, "execute_query", mock_execute_query)

        await adapter._load_workflow_states("test-team")

        # Verify semantic names in SEMANTIC_NAMES constant are being used
        semantic_names = LinearStateMapping.SEMANTIC_NAMES

        # READY has semantic names like "ready", "triage", etc.
        assert TicketState.READY in semantic_names
        assert "ready" in semantic_names[TicketState.READY]

        # TESTED has semantic names like "in review", "qa", etc.
        assert TicketState.TESTED in semantic_names
        assert "in review" in semantic_names[TicketState.TESTED]

        # Verify the matching worked correctly (already tested above, but good to be explicit)
        assert adapter._workflow_states[TicketState.READY.value] == "state-ready-id"
        assert (
            adapter._workflow_states[TicketState.TESTED.value] == "state-in-review-id"
        )

    @pytest.mark.asyncio
    async def test_custom_state_names_case_insensitive(self, monkeypatch):
        """Test that state name matching is case-insensitive.

        Teams might use different casing like "READY", "Ready", "ready", etc.
        """
        custom_workflow = {
            "team": {
                "states": {
                    "nodes": [
                        {
                            "id": "state-ready-uppercase",
                            "name": "READY",  # Uppercase
                            "type": "unstarted",
                            "position": 0,
                        },
                        {
                            "id": "state-in-review-mixed",
                            "name": "In Review",  # Mixed case
                            "type": "started",
                            "position": 1,
                        },
                        {
                            "id": "state-done-id",
                            "name": "Done",
                            "type": "completed",
                            "position": 2,
                        },
                    ]
                }
            }
        }

        async def mock_execute_query(query, variables):
            return custom_workflow

        adapter = LinearAdapter(
            config={
                "api_key": "lin_api_test123456789",
                "team_id": "test-team",
            }
        )

        monkeypatch.setattr(adapter.client, "execute_query", mock_execute_query)

        await adapter._load_workflow_states("test-team")

        # Should match "READY" to READY state (case-insensitive)
        assert (
            adapter._workflow_states[TicketState.READY.value] == "state-ready-uppercase"
        )

        # Should match "In Review" to TESTED state (case-insensitive)
        assert (
            adapter._workflow_states[TicketState.TESTED.value]
            == "state-in-review-mixed"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
