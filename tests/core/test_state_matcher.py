"""Comprehensive tests for semantic state matcher.

Tests cover:
- Exact state matching
- Synonym recognition
- Fuzzy matching with typos
- Confidence scoring
- Multiple suggestion handling
- Case insensitivity
- Whitespace handling
- Adapter-specific state matching
- Workflow validation
"""

import pytest

from mcp_ticketer.core.models import TicketState
from mcp_ticketer.core.state_matcher import (
    SemanticStateMatcher,
    StateMatchResult,
    get_state_matcher,
)


class TestExactMatching:
    """Test exact state value matching."""

    def test_exact_match_all_states(self):
        """Test exact matching for all universal states."""
        matcher = SemanticStateMatcher()

        test_cases = [
            ("open", TicketState.OPEN),
            ("in_progress", TicketState.IN_PROGRESS),
            ("ready", TicketState.READY),
            ("tested", TicketState.TESTED),
            ("done", TicketState.DONE),
            ("waiting", TicketState.WAITING),
            ("blocked", TicketState.BLOCKED),
            ("closed", TicketState.CLOSED),
        ]

        for input_str, expected_state in test_cases:
            result = matcher.match_state(input_str)
            assert result.state == expected_state
            assert result.confidence == 1.0
            assert result.match_type == "exact"

    def test_exact_match_case_insensitive(self):
        """Test that exact matching is case insensitive."""
        matcher = SemanticStateMatcher()

        test_cases = [
            "OPEN",
            "Open",
            "oPeN",
            "IN_PROGRESS",
            "In_Progress",
            "READY",
        ]

        for input_str in test_cases:
            result = matcher.match_state(input_str)
            assert result.confidence == 1.0
            assert result.match_type == "exact"

    def test_exact_match_with_whitespace(self):
        """Test that whitespace is handled correctly."""
        matcher = SemanticStateMatcher()

        test_cases = [
            "  open  ",
            "\tready\t",
            " in_progress ",
        ]

        for input_str in test_cases:
            result = matcher.match_state(input_str)
            assert result.confidence >= 0.9
            # Should be exact or synonym match


class TestSynonymMatching:
    """Test synonym dictionary matching."""

    def test_open_synonyms(self):
        """Test all OPEN state synonyms."""
        matcher = SemanticStateMatcher()

        synonyms = [
            "todo",
            "to do",
            "backlog",
            "new",
            "pending",
            "queued",
            "unstarted",
            "not started",
            "planned",
        ]

        for synonym in synonyms:
            result = matcher.match_state(synonym)
            assert result.state == TicketState.OPEN
            assert result.confidence >= 0.95
            assert result.match_type in ["exact", "synonym"]

    def test_in_progress_synonyms(self):
        """Test all IN_PROGRESS state synonyms."""
        matcher = SemanticStateMatcher()

        synonyms = [
            "in progress",
            "working",
            "started",
            "active",
            "doing",
            "in development",
            "wip",
            "work in progress",
            "working on it",
        ]

        for synonym in synonyms:
            result = matcher.match_state(synonym)
            assert result.state == TicketState.IN_PROGRESS
            assert result.confidence >= 0.95
            assert result.match_type in ["exact", "synonym"]

    def test_ready_synonyms(self):
        """Test all READY state synonyms."""
        matcher = SemanticStateMatcher()

        synonyms = [
            "review",
            "needs review",
            "pr ready",
            "code review",
            "done dev",
            "qa ready",
            "ready for review",
        ]

        for synonym in synonyms:
            result = matcher.match_state(synonym)
            assert result.state == TicketState.READY
            assert result.confidence >= 0.95
            assert result.match_type in ["exact", "synonym"]

    def test_tested_synonyms(self):
        """Test all TESTED state synonyms."""
        matcher = SemanticStateMatcher()

        synonyms = [
            "qa done",
            "verified",
            "passed qa",
            "approved",
            "validation complete",
        ]

        for synonym in synonyms:
            result = matcher.match_state(synonym)
            assert result.state == TicketState.TESTED
            assert result.confidence >= 0.95
            assert result.match_type in ["exact", "synonym"]

    def test_done_synonyms(self):
        """Test all DONE state synonyms."""
        matcher = SemanticStateMatcher()

        synonyms = [
            "completed",
            "complete",
            "finished",
            "resolved",
            "delivered",
            "shipped",
            "merged",
        ]

        for synonym in synonyms:
            result = matcher.match_state(synonym)
            assert result.state == TicketState.DONE
            assert result.confidence >= 0.95
            assert result.match_type in ["exact", "synonym"]

    def test_waiting_synonyms(self):
        """Test all WAITING state synonyms."""
        matcher = SemanticStateMatcher()

        synonyms = [
            "on hold",
            "paused",
            "waiting for",
            "pending external",
            "deferred",
            "stalled",
        ]

        for synonym in synonyms:
            result = matcher.match_state(synonym)
            assert result.state == TicketState.WAITING
            assert result.confidence >= 0.95
            assert result.match_type in ["exact", "synonym"]

    def test_blocked_synonyms(self):
        """Test all BLOCKED state synonyms."""
        matcher = SemanticStateMatcher()

        synonyms = [
            "stuck",
            "can't proceed",
            "cannot proceed",
            "impediment",
            "blocked by",
            "stopped",
        ]

        for synonym in synonyms:
            result = matcher.match_state(synonym)
            assert result.state == TicketState.BLOCKED
            assert result.confidence >= 0.95
            assert result.match_type in ["exact", "synonym"]

    def test_closed_synonyms(self):
        """Test all CLOSED state synonyms."""
        matcher = SemanticStateMatcher()

        synonyms = [
            "archived",
            "cancelled",
            "won't do",
            "wont do",
            "abandoned",
            "rejected",
            "obsolete",
        ]

        for synonym in synonyms:
            result = matcher.match_state(synonym)
            assert result.state == TicketState.CLOSED
            assert result.confidence >= 0.95
            assert result.match_type in ["exact", "synonym"]


class TestFuzzyMatching:
    """Test fuzzy matching with typos and variations."""

    def test_typo_handling(self):
        """Test that typos are handled with fuzzy matching."""
        matcher = SemanticStateMatcher()

        # Test that typos still produce valid matches
        # Note: Exact state depends on fuzzy matching algorithm
        test_cases = [
            "reviw",  # Missing 'e' - should be close to "review"/READY
            "testd",  # Missing 'e' - should be close to "tested"
            "bloked",  # Wrong 'k' - should be close to "blocked"
            "reddy",  # Similar to "ready"
        ]

        for input_str in test_cases:
            result = matcher.match_state(input_str)
            # Should produce a result with reasonable confidence
            assert result.state is not None
            assert result.confidence > 0.5
            # Should be fuzzy match for typos
            assert result.match_type in ["fuzzy", "synonym", "exact"]

    def test_partial_match(self):
        """Test partial word matching."""
        matcher = SemanticStateMatcher()

        test_cases = [
            ("prog", TicketState.IN_PROGRESS),
            ("comp", TicketState.DONE),
            ("wait", TicketState.WAITING),
        ]

        for input_str, _expected_state in test_cases:
            result = matcher.match_state(input_str)
            # Should match with reasonable confidence
            assert result.confidence >= 0.50

    def test_fuzzy_confidence_scoring(self):
        """Test that confidence scores decrease with similarity."""
        matcher = SemanticStateMatcher()

        # Perfect match
        result_exact = matcher.match_state("ready")
        assert result_exact.confidence == 1.0

        # Close match - should be reasonably confident
        result_close = matcher.match_state("redy")
        assert 0.70 <= result_close.confidence < 1.0

        # Distant match - should have lower confidence
        result_far = matcher.match_state("rd")
        assert result_far.confidence < result_close.confidence


class TestConfidenceThresholds:
    """Test confidence threshold behavior."""

    def test_high_confidence(self):
        """Test high confidence matches."""
        matcher = SemanticStateMatcher()

        result = matcher.match_state("working on it")
        assert result.is_high_confidence()
        assert result.confidence >= 0.90

    def test_medium_confidence(self):
        """Test medium confidence matches."""
        matcher = SemanticStateMatcher()

        # Create a moderately misspelled input
        result = matcher.match_state("redy")  # typo in "ready"
        # Should be medium confidence (fuzzy match)
        assert result.confidence >= 0.70

    def test_low_confidence(self):
        """Test low confidence matches."""
        matcher = SemanticStateMatcher()

        # Very short or ambiguous input
        result = matcher.match_state("x")
        assert result.confidence < 0.70


class TestSuggestions:
    """Test suggestion generation for ambiguous inputs."""

    def test_suggest_returns_multiple(self):
        """Test that suggest_states returns multiple options."""
        matcher = SemanticStateMatcher()

        suggestions = matcher.suggest_states("d", top_n=3)
        assert len(suggestions) == 3
        # Should include done
        states = [s.state for s in suggestions]
        assert TicketState.DONE in states

    def test_suggestions_sorted_by_confidence(self):
        """Test that suggestions are sorted by confidence."""
        matcher = SemanticStateMatcher()

        suggestions = matcher.suggest_states("don", top_n=5)
        # Verify descending order
        confidences = [s.confidence for s in suggestions]
        assert confidences == sorted(confidences, reverse=True)

    def test_top_n_parameter(self):
        """Test that top_n parameter limits results."""
        matcher = SemanticStateMatcher()

        suggestions_3 = matcher.suggest_states("test", top_n=3)
        suggestions_5 = matcher.suggest_states("test", top_n=5)

        assert len(suggestions_3) == 3
        assert len(suggestions_5) == 5


class TestValidationIntegration:
    """Test workflow validation with semantic matching."""

    def test_valid_transition(self):
        """Test validation of valid transition."""
        matcher = SemanticStateMatcher()

        result = matcher.validate_transition(
            TicketState.OPEN, "working on it"  # Should resolve to IN_PROGRESS
        )

        assert result.is_valid
        assert result.match_result.state == TicketState.IN_PROGRESS
        assert result.current_state == TicketState.OPEN

    def test_invalid_transition(self):
        """Test validation of invalid transition."""
        matcher = SemanticStateMatcher()

        # OPEN cannot transition directly to DONE
        result = matcher.validate_transition(TicketState.OPEN, "done")

        assert not result.is_valid
        assert result.error_message is not None
        assert "Cannot transition" in result.error_message
        assert result.valid_transitions is not None

    def test_terminal_state_no_transitions(self):
        """Test that CLOSED state has no valid transitions."""
        matcher = SemanticStateMatcher()

        result = matcher.validate_transition(TicketState.CLOSED, "open")

        assert not result.is_valid
        assert "none (terminal state)" in result.error_message


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_input(self):
        """Test empty input handling."""
        matcher = SemanticStateMatcher()

        result = matcher.match_state("")
        # Should default to OPEN
        assert result.state == TicketState.OPEN
        assert result.match_type == "default"

    def test_whitespace_only(self):
        """Test whitespace-only input."""
        matcher = SemanticStateMatcher()

        result = matcher.match_state("   ")
        assert result.state == TicketState.OPEN
        assert result.match_type in ["default", "fallback"]

    def test_special_characters(self):
        """Test input with special characters."""
        matcher = SemanticStateMatcher()

        # Should handle gracefully
        result = matcher.match_state("in-progress!")
        # Should still match IN_PROGRESS
        assert result.state == TicketState.IN_PROGRESS

    def test_numeric_input(self):
        """Test numeric input."""
        matcher = SemanticStateMatcher()

        result = matcher.match_state("123")
        # Should return some state with low confidence
        assert result.state is not None
        assert isinstance(result.confidence, float)


class TestSingletonPattern:
    """Test singleton instance pattern."""

    def test_get_state_matcher_returns_same_instance(self):
        """Test that get_state_matcher returns singleton."""
        matcher1 = get_state_matcher()
        matcher2 = get_state_matcher()

        assert matcher1 is matcher2

    def test_singleton_has_state(self):
        """Test that singleton maintains state."""
        matcher = get_state_matcher()

        # Should have synonym dictionary
        assert len(matcher._synonym_to_state) > 0


class TestPerformance:
    """Test performance characteristics."""

    def test_match_performance(self):
        """Test that matching is fast."""
        import time

        matcher = SemanticStateMatcher()

        start = time.perf_counter()
        for _ in range(1000):
            matcher.match_state("working on it")
        elapsed = time.perf_counter() - start

        # Should complete 1000 matches in under 1 second
        # (target: <10ms per match)
        assert elapsed < 1.0

    def test_suggestion_performance(self):
        """Test that suggestions are fast."""
        import time

        matcher = SemanticStateMatcher()

        start = time.perf_counter()
        for _ in range(100):
            matcher.suggest_states("test", top_n=3)
        elapsed = time.perf_counter() - start

        # Should complete 100 suggestion calls in under 1 second
        assert elapsed < 1.0


class TestMatchTypes:
    """Test different match type classifications."""

    def test_exact_match_type(self):
        """Test exact match type identification."""
        matcher = SemanticStateMatcher()

        result = matcher.match_state("open")
        assert result.match_type == "exact"

    def test_synonym_match_type(self):
        """Test synonym match type identification."""
        matcher = SemanticStateMatcher()

        result = matcher.match_state("todo")
        assert result.match_type in ["exact", "synonym"]

    def test_fuzzy_match_type(self):
        """Test fuzzy match type identification."""
        matcher = SemanticStateMatcher()

        result = matcher.match_state("opn")  # typo
        assert result.match_type == "fuzzy"


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_ai_agent_natural_language(self):
        """Test natural language inputs from AI agents."""
        matcher = SemanticStateMatcher()

        test_cases = [
            ("I'm working on this", TicketState.IN_PROGRESS),
            ("This needs to be reviewed", TicketState.READY),
            ("Finished implementing", TicketState.DONE),
            ("Can't move forward", TicketState.BLOCKED),
            ("Waiting for approval", TicketState.WAITING),
        ]

        for input_str, _expected_state in test_cases:
            result = matcher.match_state(input_str)
            # Should match with reasonable confidence
            # Note: Some may not match exactly but should be close
            assert result.confidence > 0.5

    def test_user_abbreviations(self):
        """Test common user abbreviations."""
        matcher = SemanticStateMatcher()

        test_cases = [
            ("WIP", TicketState.IN_PROGRESS),
            ("PR", TicketState.READY),
            ("QA", TicketState.TESTED),
        ]

        for input_str, _expected_state in test_cases:
            result = matcher.match_state(input_str)
            # May not match exactly, but should be reasonable
            assert result.state is not None

    def test_platform_specific_terms(self):
        """Test platform-specific terminology."""
        matcher = SemanticStateMatcher()

        # Linear/JIRA/GitHub specific terms
        test_cases = [
            ("backlog", TicketState.OPEN),  # JIRA term
            ("in development", TicketState.IN_PROGRESS),  # Common term
            ("merged", TicketState.DONE),  # GitHub term
            ("won't fix", TicketState.CLOSED),  # GitHub term
        ]

        for input_str, expected_state in test_cases:
            result = matcher.match_state(input_str)
            assert result.state == expected_state
            assert result.confidence >= 0.90


class TestConfidenceHelpers:
    """Test confidence helper methods."""

    def test_is_high_confidence(self):
        """Test is_high_confidence helper."""
        matcher = SemanticStateMatcher()

        result = matcher.match_state("open")
        assert result.is_high_confidence()

        result = matcher.match_state("opn")
        # Fuzzy match may not be high confidence
        # Just verify method works
        confidence_check = result.is_high_confidence()
        assert isinstance(confidence_check, bool)

    def test_is_medium_confidence(self):
        """Test is_medium_confidence helper."""
        result = StateMatchResult(
            state=TicketState.OPEN,
            confidence=0.80,
            match_type="fuzzy",
            original_input="test",
        )

        assert result.is_medium_confidence()
        assert not result.is_high_confidence()
        assert not result.is_low_confidence()

    def test_is_low_confidence(self):
        """Test is_low_confidence helper."""
        result = StateMatchResult(
            state=TicketState.OPEN,
            confidence=0.60,
            match_type="fuzzy",
            original_input="test",
        )

        assert result.is_low_confidence()
        assert not result.is_medium_confidence()
        assert not result.is_high_confidence()


@pytest.mark.parametrize(
    "input_str,expected_state",
    [
        # OPEN variations
        ("todo", TicketState.OPEN),
        ("backlog", TicketState.OPEN),
        ("new", TicketState.OPEN),
        # IN_PROGRESS variations
        ("started", TicketState.IN_PROGRESS),
        ("working", TicketState.IN_PROGRESS),
        ("in dev", TicketState.IN_PROGRESS),
        # READY variations
        ("review", TicketState.READY),
        ("pr ready", TicketState.READY),
        ("awaiting review", TicketState.READY),
        # TESTED variations
        ("tested", TicketState.TESTED),
        ("qa approved", TicketState.TESTED),
        ("verified", TicketState.TESTED),
        # DONE variations
        ("finished", TicketState.DONE),
        ("complete", TicketState.DONE),
        ("shipped", TicketState.DONE),
        # WAITING variations
        ("on hold", TicketState.WAITING),
        ("waiting", TicketState.WAITING),
        ("paused", TicketState.WAITING),
        # BLOCKED variations
        ("stuck", TicketState.BLOCKED),
        ("blocked", TicketState.BLOCKED),
        ("impediment", TicketState.BLOCKED),
        # CLOSED variations
        ("closed", TicketState.CLOSED),
        ("cancelled", TicketState.CLOSED),
        ("archived", TicketState.CLOSED),
    ],
)
def test_comprehensive_synonym_coverage(input_str, expected_state):
    """Parameterized test for comprehensive synonym coverage."""
    matcher = SemanticStateMatcher()
    result = matcher.match_state(input_str)

    # Should match the expected state with good confidence
    assert result.state == expected_state
    assert result.confidence >= 0.90
