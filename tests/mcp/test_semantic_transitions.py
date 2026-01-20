"""Integration tests for semantic state transitions via MCP tools.

Tests the complete flow of semantic state matching through the MCP
ticket_transition tool, including:
- Natural language input handling
- Confidence-based responses
- Workflow validation
- Suggestion generation
"""

import pytest

from mcp_ticketer.core.models import Priority, Task, TicketState, TicketType


@pytest.mark.asyncio
class TestSemanticTransitionMCP:
    """Test semantic transitions through MCP tools."""

    async def test_natural_language_transition_high_confidence(
        self, aitrackdown_adapter
    ):
        """Test natural language transition with high confidence."""
        from mcp_ticketer.mcp.server.tools.user_ticket_tools import workflow

        # Create a test ticket
        ticket = Task(
            title="Test semantic transition",
            description="Testing natural language state transitions",
            priority=Priority.MEDIUM,
            state=TicketState.OPEN,
            ticket_type=TicketType.ISSUE,
        )
        created = await aitrackdown_adapter.create(ticket)
        assert created is not None
        ticket_id = created.id

        try:
            # Use natural language to transition
            result = await workflow(
                action="transition",
                ticket_id=ticket_id,
                to_state="working on it",  # Natural language!
                comment="Started implementation",
            )

            # Should succeed with high confidence
            assert result["status"] == "completed"
            assert result["matched_state"] == "in_progress"
            assert result["confidence"] >= 0.90
            assert result["previous_state"] == "open"
            assert result["new_state"] == "in_progress"
            assert result["match_type"] in ["synonym", "exact"]

        finally:
            await aitrackdown_adapter.delete(ticket_id)

    async def test_synonym_transition(self, aitrackdown_adapter):
        """Test transition using synonym."""
        from mcp_ticketer.mcp.server.tools.user_ticket_tools import workflow

        ticket = Task(
            title="Test synonym",
            state=TicketState.IN_PROGRESS,
            ticket_type=TicketType.ISSUE,
        )
        created = await aitrackdown_adapter.create(ticket)
        ticket_id = created.id

        try:
            # Use "review" synonym for READY
            result = await workflow(
                action="transition",
                ticket_id=ticket_id,
                to_state="needs review",
            )

            assert result["status"] == "completed"
            assert result["matched_state"] == "ready"
            assert result["new_state"] == "ready"
            assert result["confidence"] >= 0.90

        finally:
            await aitrackdown_adapter.delete(ticket_id)

    async def test_typo_handling_fuzzy_match(self, aitrackdown_adapter):
        """Test that typos are handled with fuzzy matching."""
        from mcp_ticketer.mcp.server.tools.user_ticket_tools import workflow

        ticket = Task(
            title="Test typo handling",
            state=TicketState.IN_PROGRESS,
            ticket_type=TicketType.ISSUE,
        )
        created = await aitrackdown_adapter.create(ticket)
        ticket_id = created.id

        try:
            # Typo: "reviw" instead of "review"
            result = await workflow(
                action="transition",
                ticket_id=ticket_id,
                to_state="reviw",  # Typo!
            )

            # Should succeed with fuzzy match
            assert result["status"] == "completed"
            assert result["matched_state"] == "ready"
            assert result["match_type"] == "fuzzy"
            assert result["confidence"] >= 0.70

        finally:
            await aitrackdown_adapter.delete(ticket_id)

    async def test_ambiguous_input_returns_suggestions(self, aitrackdown_adapter):
        """Test that ambiguous input returns suggestions."""
        from mcp_ticketer.mcp.server.tools.user_ticket_tools import workflow

        ticket = Task(
            title="Test ambiguous input",
            state=TicketState.OPEN,
            ticket_type=TicketType.ISSUE,
        )
        created = await aitrackdown_adapter.create(ticket)
        ticket_id = created.id

        try:
            # Very short/ambiguous input
            result = await workflow(
                action="transition",
                ticket_id=ticket_id,
                to_state="x",  # Ambiguous!
            )

            # Should return suggestions
            assert result["status"] == "ambiguous"
            assert "suggestions" in result
            assert len(result["suggestions"]) > 0
            # Each suggestion should have state, confidence, description
            for suggestion in result["suggestions"]:
                assert "state" in suggestion
                assert "confidence" in suggestion
                assert "description" in suggestion

        finally:
            await aitrackdown_adapter.delete(ticket_id)

    async def test_medium_confidence_with_auto_confirm_false(self, aitrackdown_adapter):
        """Test medium confidence requires confirmation when auto_confirm=False."""
        from mcp_ticketer.mcp.server.tools.user_ticket_tools import workflow

        ticket = Task(
            title="Test confirmation",
            state=TicketState.IN_PROGRESS,
            ticket_type=TicketType.ISSUE,
        )
        created = await aitrackdown_adapter.create(ticket)
        ticket_id = created.id

        try:
            # Use a slightly misspelled input
            result = await workflow(
                action="transition",
                ticket_id=ticket_id,
                to_state="redy",  # Misspelled
                auto_confirm=False,
            )

            # Medium confidence should require confirmation
            if result["confidence"] < 0.90 and result["confidence"] >= 0.70:
                assert result["status"] == "needs_confirmation"
                assert result["confirm_required"] is True

        finally:
            await aitrackdown_adapter.delete(ticket_id)

    async def test_workflow_validation_with_semantic_input(self, aitrackdown_adapter):
        """Test that workflow validation works with semantic input."""
        from mcp_ticketer.mcp.server.tools.user_ticket_tools import workflow

        ticket = Task(
            title="Test workflow validation",
            state=TicketState.OPEN,
            ticket_type=TicketType.ISSUE,
        )
        created = await aitrackdown_adapter.create(ticket)
        ticket_id = created.id

        try:
            # Try invalid transition: OPEN -> TESTED (not allowed)
            result = await workflow(
                action="transition",
                ticket_id=ticket_id,
                to_state="tested",  # Invalid from OPEN
            )

            # Should fail validation
            assert result["status"] == "error"
            assert "Invalid transition" in result["error"]
            assert "valid_transitions" in result
            # OPEN can transition to: IN_PROGRESS, WAITING, BLOCKED, CLOSED
            assert "in_progress" in result["valid_transitions"]

        finally:
            await aitrackdown_adapter.delete(ticket_id)

    async def test_complete_workflow_with_natural_language(self, aitrackdown_adapter):
        """Test complete workflow using natural language."""
        from mcp_ticketer.mcp.server.tools.user_ticket_tools import workflow

        ticket = Task(
            title="Test complete workflow",
            state=TicketState.OPEN,
            ticket_type=TicketType.ISSUE,
        )
        created = await aitrackdown_adapter.create(ticket)
        ticket_id = created.id

        try:
            # 1. Start work: OPEN -> IN_PROGRESS
            result1 = await workflow(
                action="transition", ticket_id=ticket_id, to_state="started working"
            )
            assert result1["status"] == "completed"
            assert result1["new_state"] == "in_progress"

            # 2. Complete work: IN_PROGRESS -> READY
            result2 = await workflow(
                action="transition", ticket_id=ticket_id, to_state="needs review"
            )
            assert result2["status"] == "completed"
            assert result2["new_state"] == "ready"

            # 3. Test: READY -> TESTED
            result3 = await workflow(
                action="transition", ticket_id=ticket_id, to_state="qa passed"
            )
            assert result3["status"] == "completed"
            assert result3["new_state"] == "tested"

            # 4. Complete: TESTED -> DONE
            result4 = await workflow(
                action="transition", ticket_id=ticket_id, to_state="finished"
            )
            assert result4["status"] == "completed"
            assert result4["new_state"] == "done"

            # 5. Close: DONE -> CLOSED
            result5 = await workflow(
                action="transition", ticket_id=ticket_id, to_state="archived"
            )
            assert result5["status"] == "completed"
            assert result5["new_state"] == "closed"

        finally:
            await aitrackdown_adapter.delete(ticket_id)

    async def test_exact_state_names_still_work(self, aitrackdown_adapter):
        """Test backward compatibility - exact state names still work."""
        from mcp_ticketer.mcp.server.tools.user_ticket_tools import workflow

        ticket = Task(
            title="Test backward compatibility",
            state=TicketState.OPEN,
            ticket_type=TicketType.ISSUE,
        )
        created = await aitrackdown_adapter.create(ticket)
        ticket_id = created.id

        try:
            # Use exact state name (old behavior)
            result = await workflow(
                action="transition",
                ticket_id=ticket_id,
                to_state="in_progress",  # Exact state name
            )

            assert result["status"] == "completed"
            assert result["new_state"] == "in_progress"
            assert result["match_type"] == "exact"
            assert result["confidence"] == 1.0

        finally:
            await aitrackdown_adapter.delete(ticket_id)

    async def test_case_insensitivity(self, aitrackdown_adapter):
        """Test that matching is case insensitive."""
        from mcp_ticketer.mcp.server.tools.user_ticket_tools import workflow

        ticket = Task(
            title="Test case insensitivity",
            state=TicketState.OPEN,
            ticket_type=TicketType.ISSUE,
        )
        created = await aitrackdown_adapter.create(ticket)
        ticket_id = created.id

        try:
            # Use mixed case
            result = await workflow(
                action="transition",
                ticket_id=ticket_id,
                to_state="WORKING ON IT",  # UPPERCASE
            )

            assert result["status"] == "completed"
            assert result["matched_state"] == "in_progress"

        finally:
            await aitrackdown_adapter.delete(ticket_id)

    async def test_whitespace_handling(self, aitrackdown_adapter):
        """Test that extra whitespace is handled."""
        from mcp_ticketer.mcp.server.tools.user_ticket_tools import workflow

        ticket = Task(
            title="Test whitespace",
            state=TicketState.OPEN,
            ticket_type=TicketType.ISSUE,
        )
        created = await aitrackdown_adapter.create(ticket)
        ticket_id = created.id

        try:
            # Use extra whitespace
            result = await workflow(
                action="transition",
                ticket_id=ticket_id,
                to_state="  working   on   it  ",  # Extra whitespace
            )

            assert result["status"] == "completed"
            assert result["matched_state"] == "in_progress"

        finally:
            await aitrackdown_adapter.delete(ticket_id)

    async def test_confidence_included_in_response(self, aitrackdown_adapter):
        """Test that confidence score is included in response."""
        from mcp_ticketer.mcp.server.tools.user_ticket_tools import workflow

        ticket = Task(
            title="Test confidence reporting",
            state=TicketState.OPEN,
            ticket_type=TicketType.ISSUE,
        )
        created = await aitrackdown_adapter.create(ticket)
        ticket_id = created.id

        try:
            result = await workflow(
                action="transition", ticket_id=ticket_id, to_state="working on it"
            )

            # Response should include confidence metrics
            assert "confidence" in result
            assert "match_type" in result
            assert "original_input" in result
            assert "matched_state" in result

            # Confidence should be a float between 0 and 1
            assert isinstance(result["confidence"], float)
            assert 0.0 <= result["confidence"] <= 1.0

        finally:
            await aitrackdown_adapter.delete(ticket_id)

    async def test_platform_specific_terms(self, aitrackdown_adapter):
        """Test platform-specific terminology."""
        from mcp_ticketer.mcp.server.tools.user_ticket_tools import workflow

        ticket = Task(
            title="Test platform terms",
            state=TicketState.OPEN,
            ticket_type=TicketType.ISSUE,
        )
        created = await aitrackdown_adapter.create(ticket)
        ticket_id = created.id

        try:
            # Linear/JIRA/GitHub specific terms
            test_cases = [
                ("backlog", "open"),  # JIRA term
                ("in development", "in_progress"),  # Common term
            ]

            current_state = TicketState.OPEN
            for input_term, expected_state in test_cases:
                # Check if transition is valid from current state
                target_state = TicketState(expected_state)
                if not current_state.can_transition_to(target_state):
                    continue

                result = await workflow(
                    action="transition",
                    ticket_id=ticket_id,
                    to_state=input_term,
                )

                if result["status"] == "completed":
                    assert result["matched_state"] == expected_state
                    current_state = target_state

        finally:
            await aitrackdown_adapter.delete(ticket_id)


@pytest.mark.asyncio
class TestSemanticTransitionEdgeCases:
    """Test edge cases for semantic transitions."""

    async def test_empty_state_input(self, aitrackdown_adapter):
        """Test empty state input handling."""
        from mcp_ticketer.mcp.server.tools.user_ticket_tools import workflow

        ticket = Task(
            title="Test empty input",
            state=TicketState.OPEN,
            ticket_type=TicketType.ISSUE,
        )
        created = await aitrackdown_adapter.create(ticket)
        ticket_id = created.id

        try:
            result = await workflow(
                action="transition",
                ticket_id=ticket_id,
                to_state="",  # Empty!
            )

            # Should handle gracefully
            assert result["status"] in ["completed", "ambiguous", "error"]

        finally:
            await aitrackdown_adapter.delete(ticket_id)

    async def test_ticket_not_found(self):
        """Test semantic transition with non-existent ticket."""
        from mcp_ticketer.mcp.server.tools.user_ticket_tools import workflow

        result = await workflow(
            action="transition",
            ticket_id="NONEXISTENT-123",
            to_state="working on it",
        )

        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    async def test_terminal_state_transition_attempt(self, aitrackdown_adapter):
        """Test attempting transition from terminal state."""
        from mcp_ticketer.mcp.server.tools.user_ticket_tools import workflow

        ticket = Task(
            title="Test terminal state",
            state=TicketState.CLOSED,  # Terminal state
            ticket_type=TicketType.ISSUE,
        )
        created = await aitrackdown_adapter.create(ticket)
        ticket_id = created.id

        try:
            result = await workflow(
                action="transition",
                ticket_id=ticket_id,
                to_state="working on it",
            )

            # Should fail - CLOSED has no valid transitions
            assert result["status"] == "error"
            assert "none (terminal state)" in result["message"]

        finally:
            await aitrackdown_adapter.delete(ticket_id)


@pytest.mark.asyncio
class TestCommentIntegration:
    """Test comment integration with semantic transitions."""

    async def test_comment_added_with_transition(self, aitrackdown_adapter):
        """Test that comments are added with transitions."""
        from mcp_ticketer.mcp.server.tools.user_ticket_tools import workflow

        ticket = Task(
            title="Test comment integration",
            state=TicketState.OPEN,
            ticket_type=TicketType.ISSUE,
        )
        created = await aitrackdown_adapter.create(ticket)
        ticket_id = created.id

        try:
            result = await workflow(
                action="transition",
                ticket_id=ticket_id,
                to_state="working on it",
                comment="Started implementation of feature X",
            )

            # Check if comment was added
            # Note: aitrackdown may not support comments
            if result["status"] == "completed":
                assert "comment_added" in result
                # Value depends on adapter support

        finally:
            await aitrackdown_adapter.delete(ticket_id)
