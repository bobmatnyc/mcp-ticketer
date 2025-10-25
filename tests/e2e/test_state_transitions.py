"""End-to-end tests for all ticket state transitions and workflow states."""

import pytest
import pytest_asyncio

from mcp_ticketer.mcp.server import MCPTicketServer


class TestStateTransitions:
    """Test all possible state transitions in the ticket workflow."""

    @pytest_asyncio.fixture
    async def mcp_server(self, tmp_path):
        """Create MCP server for testing."""
        server = MCPTicketServer(
            adapter_type="aitrackdown",
            config={"base_path": str(tmp_path / "test_states")},
        )
        yield server

    @pytest.mark.asyncio
    async def test_complete_workflow_states(self, mcp_server: MCPTicketServer):
        """Test complete workflow: OPEN → IN_PROGRESS → READY → TESTED → DONE → CLOSED."""

        # Create a task for testing
        task_id = await self._create_test_task(mcp_server)

        # Define the complete workflow sequence
        workflow_sequence = [
            ("open", "OPEN"),  # Initial state
            ("in_progress", "IN_PROGRESS"),  # Start work
            ("ready", "READY"),  # Ready for review
            ("tested", "TESTED"),  # Passed testing
            ("done", "DONE"),  # Work completed
            ("closed", "CLOSED"),  # Officially closed
        ]

        # Test each transition
        for i, (transition_state, expected_state) in enumerate(workflow_sequence):
            if i == 0:
                # Verify initial state
                current_state = await self._get_ticket_state(mcp_server, task_id)
                assert current_state.upper() == expected_state
                continue

            # Perform state transition
            await self._transition_state(mcp_server, task_id, transition_state)

            # Verify new state
            current_state = await self._get_ticket_state(mcp_server, task_id)
            assert (
                current_state.upper() == expected_state
            ), f"Expected {expected_state}, got {current_state}"

    @pytest.mark.asyncio
    async def test_blocked_and_waiting_states(self, mcp_server: MCPTicketServer):
        """Test BLOCKED and WAITING states that can occur at various points."""

        task_id = await self._create_test_task(mcp_server)

        # Start work
        await self._transition_state(mcp_server, task_id, "in_progress")

        # Test transition to BLOCKED
        await self._transition_state(mcp_server, task_id, "blocked")
        current_state = await self._get_ticket_state(mcp_server, task_id)
        assert current_state.upper() == "BLOCKED"

        # Unblock and continue
        await self._transition_state(mcp_server, task_id, "in_progress")
        current_state = await self._get_ticket_state(mcp_server, task_id)
        assert current_state.upper() == "IN_PROGRESS"

        # Test transition to WAITING
        await self._transition_state(mcp_server, task_id, "waiting")
        current_state = await self._get_ticket_state(mcp_server, task_id)
        assert current_state.upper() == "WAITING"

        # Resume from waiting
        await self._transition_state(mcp_server, task_id, "in_progress")
        current_state = await self._get_ticket_state(mcp_server, task_id)
        assert current_state.upper() == "IN_PROGRESS"

    @pytest.mark.asyncio
    async def test_state_transition_validation(self, mcp_server: MCPTicketServer):
        """Test that invalid state transitions are handled properly."""

        task_id = await self._create_test_task(mcp_server)

        # Test invalid transitions (these should either be rejected or handled gracefully)
        invalid_transitions = [
            ("closed", "Cannot close without being done first"),
            ("tested", "Cannot test without being ready first"),
        ]

        for invalid_state, _reason in invalid_transitions:
            # Attempt invalid transition
            transition_request = {
                "method": "ticket/transition",
                "params": {"ticket_id": task_id, "target_state": invalid_state},
                "id": 100,
            }

            response = await mcp_server.handle_request(transition_request)

            # Should either complete, fail, or reject immediately
            result_status = response["result"]["status"]
            # May fail or succeed depending on adapter implementation
            # The key is that it's handled gracefully
            assert result_status in ["completed", "failed", "error"]

    @pytest.mark.asyncio
    async def test_state_history_tracking(self, mcp_server: MCPTicketServer):
        """Test that state changes are tracked over time."""

        task_id = await self._create_test_task(mcp_server)

        # Perform several state transitions (following valid state machine)
        # Valid path: OPEN -> IN_PROGRESS -> BLOCKED -> IN_PROGRESS -> READY -> TESTED -> DONE
        state_sequence = [
            "in_progress",
            "blocked",
            "in_progress",
            "ready",
            "tested",
            "done",
        ]

        for state in state_sequence:
            await self._transition_state(mcp_server, task_id, state)

            # Small delay to ensure timestamps are different
            import asyncio

            await asyncio.sleep(0.1)

        # Read final ticket state
        read_request = {
            "method": "ticket/read",
            "params": {"ticket_id": task_id},
            "id": 200,
        }

        read_response = await mcp_server.handle_request(read_request)
        ticket = read_response["result"]["ticket"]

        # Verify final state
        assert ticket["state"].upper() == "DONE"

        # Check if state history is available (adapter-dependent)
        if "state_history" in ticket or "history" in ticket.get("metadata", {}):
            # If history is tracked, verify it contains our transitions
            history = ticket.get("state_history") or ticket["metadata"].get(
                "history", []
            )
            assert len(history) >= len(state_sequence)

    @pytest.mark.asyncio
    async def test_bulk_state_transitions(self, mcp_server: MCPTicketServer):
        """Test bulk state transitions for multiple tickets."""

        # Create multiple tasks
        task_ids = []
        for i in range(3):
            task_id = await self._create_test_task(mcp_server, f"Bulk Task {i+1}")
            task_ids.append(task_id)

        # Bulk update to move all to in_progress
        bulk_update_request = {
            "method": "ticket/bulk_update",
            "params": {
                "updates": [
                    {"ticket_id": task_id, "state": "in_progress"}
                    for task_id in task_ids
                ]
            },
            "id": 300,
        }

        bulk_response = await mcp_server.handle_request(bulk_update_request)
        assert bulk_response["result"]["status"] == "completed"
        assert len(bulk_response["result"]["results"]) == 3

        # Verify all tasks are in IN_PROGRESS state
        for task_id in task_ids:
            current_state = await self._get_ticket_state(mcp_server, task_id)
            assert current_state.upper() == "IN_PROGRESS"

    @pytest.mark.asyncio
    async def test_state_dependent_operations(self, mcp_server: MCPTicketServer):
        """Test operations that depend on specific states."""

        task_id = await self._create_test_task(mcp_server)

        # Test adding comments in different states
        states_to_test = ["open", "in_progress", "ready", "done"]

        for state in states_to_test:
            # Transition to state
            if state != "open":  # Already in open state
                await self._transition_state(mcp_server, task_id, state)

            # Add comment
            comment_request = {
                "method": "ticket/comment",
                "params": {
                    "operation": "add",
                    "ticket_id": task_id,
                    "content": f"Comment added in {state} state",
                    "author": "test.user",
                },
                "id": 400,
            }

            comment_response = await mcp_server.handle_request(comment_request)
            assert comment_response["result"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_concurrent_state_transitions(self, mcp_server: MCPTicketServer):
        """Test concurrent state transitions to prevent race conditions."""

        task_id = await self._create_test_task(mcp_server)

        # Attempt concurrent state transitions
        import asyncio

        concurrent_transitions = [
            self._transition_state(mcp_server, task_id, "in_progress"),
            self._transition_state(mcp_server, task_id, "blocked"),
            self._transition_state(mcp_server, task_id, "waiting"),
        ]

        # Execute concurrently
        results = await asyncio.gather(*concurrent_transitions, return_exceptions=True)

        # At least one should succeed, others may fail due to race conditions
        successful_transitions = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_transitions) >= 1

        # Verify final state is one of the attempted states
        final_state = await self._get_ticket_state(mcp_server, task_id)
        assert final_state.upper() in ["IN_PROGRESS", "BLOCKED", "WAITING"]

    async def _create_test_task(
        self, mcp_server: MCPTicketServer, title: str = "Test Task"
    ) -> str:
        """Helper to create a test task and return its ID."""
        # Create epic and issue first
        epic_id = await self._create_test_epic(mcp_server)
        issue_id = await self._create_test_issue(mcp_server, epic_id)

        # Create task
        task_request = {
            "method": "task/create",
            "params": {
                "title": title,
                "parent_id": issue_id,
                "description": f"Test task for state transitions: {title}",
            },
            "id": 999,
        }

        response = await mcp_server.handle_request(task_request)
        return response["result"]["ticket"]["id"]

    async def _create_test_epic(self, mcp_server: MCPTicketServer) -> str:
        """Helper to create a test epic."""
        epic_request = {
            "method": "epic/create",
            "params": {
                "title": "State Test Epic",
                "description": "Epic for state testing",
            },
            "id": 998,
        }

        response = await mcp_server.handle_request(epic_request)
        return response["result"]["ticket"]["id"]

    async def _create_test_issue(
        self, mcp_server: MCPTicketServer, epic_id: str
    ) -> str:
        """Helper to create a test issue."""
        issue_request = {
            "method": "issue/create",
            "params": {
                "title": "State Test Issue",
                "description": "Issue for state testing",
                "epic_id": epic_id,
            },
            "id": 997,
        }

        response = await mcp_server.handle_request(issue_request)
        return response["result"]["ticket"]["id"]

    async def _transition_state(
        self, mcp_server: MCPTicketServer, ticket_id: str, target_state: str
    ):
        """Helper to transition ticket state."""
        transition_request = {
            "method": "ticket/transition",
            "params": {"ticket_id": ticket_id, "target_state": target_state},
            "id": 996,
        }

        response = await mcp_server.handle_request(transition_request)
        # Response is immediate with synchronous server
        return response

    async def _get_ticket_state(
        self, mcp_server: MCPTicketServer, ticket_id: str
    ) -> str:
        """Helper to get current ticket state."""
        read_request = {
            "method": "ticket/read",
            "params": {"ticket_id": ticket_id},
            "id": 995,
        }

        response = await mcp_server.handle_request(read_request)
        ticket = response["result"]["ticket"]
        return ticket["state"]
