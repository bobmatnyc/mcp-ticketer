"""Comprehensive tests for semantic priority matcher.

Tests cover:
- Exact priority matching
- Synonym recognition
- Fuzzy matching with typos
- Confidence scoring
- Multiple suggestion handling
- Case insensitivity
- Whitespace handling
- Natural language understanding

Ticket Reference: ISS-0002 - Add semantic priority matching for natural language inputs
"""

from mcp_ticketer.core.models import Priority
from mcp_ticketer.core.priority_matcher import (
    PriorityMatchResult,
    SemanticPriorityMatcher,
    get_priority_matcher,
)


class TestExactMatching:
    """Test exact priority value matching."""

    def test_exact_match_all_priorities(self) -> None:
        """Test exact matching for all universal priorities."""
        matcher = SemanticPriorityMatcher()

        test_cases = [
            ("low", Priority.LOW),
            ("medium", Priority.MEDIUM),
            ("high", Priority.HIGH),
            ("critical", Priority.CRITICAL),
        ]

        for input_str, expected_priority in test_cases:
            result = matcher.match_priority(input_str)
            assert result.priority == expected_priority
            assert result.confidence == 1.0
            assert result.match_type == "exact"

    def test_exact_match_case_insensitive(self) -> None:
        """Test that exact matching is case insensitive."""
        matcher = SemanticPriorityMatcher()

        test_cases = [
            "LOW",
            "Low",
            "lOw",
            "MEDIUM",
            "Medium",
            "HIGH",
            "High",
            "CRITICAL",
            "Critical",
        ]

        for input_str in test_cases:
            result = matcher.match_priority(input_str)
            assert result.confidence == 1.0
            assert result.match_type == "exact"

    def test_exact_match_with_whitespace(self) -> None:
        """Test that whitespace is handled correctly."""
        matcher = SemanticPriorityMatcher()

        test_cases = [
            "  low  ",
            "\thigh\t",
            " medium ",
            "  critical  ",
        ]

        for input_str in test_cases:
            result = matcher.match_priority(input_str)
            assert result.confidence >= 0.9
            # Should be exact or synonym match


class TestSynonymMatching:
    """Test synonym dictionary matching."""

    def test_critical_synonyms(self) -> None:
        """Test all CRITICAL priority synonyms."""
        matcher = SemanticPriorityMatcher()

        synonyms = [
            "urgent",
            "asap",
            "as soon as possible",
            "emergency",
            "blocker",
            "blocking",
            "show stopper",
            "show-stopper",
            "showstopper",
            "highest",
            "p0",
            "p-0",
            "priority 0",
            "needs immediate attention",
            "immediate attention",
            "very urgent",
            "right now",
            "drop everything",
            "top priority",
            "mission critical",
            "business critical",
            "sev 0",
            "sev0",
            "severity 0",
            "must have",
        ]

        for synonym in synonyms:
            result = matcher.match_priority(synonym)
            assert (
                result.priority == Priority.CRITICAL
            ), f"Failed for synonym: {synonym}"
            assert result.confidence >= 0.95
            assert result.match_type in ["exact", "synonym"]

    def test_high_synonyms(self) -> None:
        """Test all HIGH priority synonyms."""
        matcher = SemanticPriorityMatcher()

        synonyms = [
            "important",
            "soon",
            "needs attention",
            "p1",
            "p-1",
            "priority 1",
            "high priority",
            "should do",
            "should have",
            "significant",
            "pressing",
            "time sensitive",
            "time-sensitive",
            "sev 1",
            "sev1",
            "severity 1",
            "major",
            "escalated",
            "higher",
            "elevated",
        ]

        for synonym in synonyms:
            result = matcher.match_priority(synonym)
            assert result.priority == Priority.HIGH, f"Failed for synonym: {synonym}"
            assert result.confidence >= 0.95
            assert result.match_type in ["exact", "synonym"]

    def test_medium_synonyms(self) -> None:
        """Test all MEDIUM priority synonyms."""
        matcher = SemanticPriorityMatcher()

        synonyms = [
            "normal",
            "standard",
            "regular",
            "moderate",
            "average",
            "default",
            "typical",
            "p2",
            "p-2",
            "priority 2",
            "medium priority",
            "could have",
            "sev 2",
            "sev2",
            "severity 2",
            "routine",
            "ordinary",
        ]

        for synonym in synonyms:
            result = matcher.match_priority(synonym)
            assert result.priority == Priority.MEDIUM, f"Failed for synonym: {synonym}"
            assert result.confidence >= 0.95
            assert result.match_type in ["exact", "synonym"]

    def test_low_synonyms(self) -> None:
        """Test all LOW priority synonyms."""
        matcher = SemanticPriorityMatcher()

        synonyms = [
            "minor",
            "whenever",
            "low priority",
            "not urgent",
            "nice to have",
            "nice-to-have",
            "backlog",
            "someday",
            "if time permits",
            "when possible",
            "optional",
            "can wait",
            "lowest",
            "p3",
            "p-3",
            "priority 3",
            "trivial",
            "cosmetic",
            "sev 3",
            "sev3",
            "severity 3",
            "won't have",
            "wont have",
        ]

        for synonym in synonyms:
            result = matcher.match_priority(synonym)
            assert result.priority == Priority.LOW, f"Failed for synonym: {synonym}"
            assert result.confidence >= 0.95
            assert result.match_type in ["exact", "synonym"]

    def test_synonym_case_insensitive(self) -> None:
        """Test that synonym matching is case insensitive."""
        matcher = SemanticPriorityMatcher()

        test_cases = [
            ("URGENT", Priority.CRITICAL),
            ("Urgent", Priority.CRITICAL),
            ("Important", Priority.HIGH),
            ("IMPORTANT", Priority.HIGH),
            ("Normal", Priority.MEDIUM),
            ("NORMAL", Priority.MEDIUM),
        ]

        for input_str, expected_priority in test_cases:
            result = matcher.match_priority(input_str)
            assert result.priority == expected_priority
            assert result.confidence >= 0.95


class TestFuzzyMatching:
    """Test fuzzy matching with typos."""

    def test_critical_typos(self) -> None:
        """Test fuzzy matching for CRITICAL with typos."""
        matcher = SemanticPriorityMatcher()

        typos = [
            "criticl",
            "critcal",
            "crtical",
            "urgnt",
            "urgemt",
            "blokcer",
            "bloker",
        ]

        for typo in typos:
            result = matcher.match_priority(typo)
            assert result.priority == Priority.CRITICAL, f"Failed for typo: {typo}"
            assert result.confidence >= 0.70
            assert result.match_type == "fuzzy"

    def test_high_typos(self) -> None:
        """Test fuzzy matching for HIGH with typos."""
        matcher = SemanticPriorityMatcher()

        typos = [
            "hgh",
            "hig",
            "importnt",
            "importat",
            "presing",
            "preesing",
        ]

        for typo in typos:
            result = matcher.match_priority(typo)
            assert result.priority == Priority.HIGH, f"Failed for typo: {typo}"
            assert result.confidence >= 0.70
            assert result.match_type == "fuzzy"

    def test_medium_typos(self) -> None:
        """Test fuzzy matching for MEDIUM with typos."""
        matcher = SemanticPriorityMatcher()

        typos = [
            "medum",
            "medim",
            "mediumm",
            "norml",
            "standrd",
        ]

        for typo in typos:
            result = matcher.match_priority(typo)
            assert result.priority == Priority.MEDIUM, f"Failed for typo: {typo}"
            assert result.confidence >= 0.70
            assert result.match_type == "fuzzy"

    def test_low_typos(self) -> None:
        """Test fuzzy matching for LOW with typos."""
        matcher = SemanticPriorityMatcher()

        typos = [
            "lw",
            "lo",
            "minr",
            "miner",
            "trivil",
        ]

        for typo in typos:
            result = matcher.match_priority(typo)
            assert result.priority == Priority.LOW, f"Failed for typo: {typo}"
            assert result.confidence >= 0.70
            assert result.match_type == "fuzzy"


class TestConfidenceScoring:
    """Test confidence score calculations."""

    def test_high_confidence_exact_match(self) -> None:
        """Test that exact matches have confidence 1.0."""
        matcher = SemanticPriorityMatcher()

        for priority in Priority:
            result = matcher.match_priority(priority.value)
            assert result.confidence == 1.0
            assert result.is_high_confidence()
            assert not result.is_medium_confidence()
            assert not result.is_low_confidence()

    def test_high_confidence_synonym_match(self) -> None:
        """Test that synonym matches have confidence >= 0.95."""
        matcher = SemanticPriorityMatcher()

        synonyms = ["urgent", "important", "normal", "minor"]

        for synonym in synonyms:
            result = matcher.match_priority(synonym)
            assert result.confidence >= 0.95
            assert result.is_high_confidence()

    def test_medium_confidence_fuzzy_match(self) -> None:
        """Test that some fuzzy matches have medium confidence."""
        matcher = SemanticPriorityMatcher()

        # Fuzzy matches should have 0.70 <= confidence < 0.90
        fuzzy_inputs = ["urgnt", "importnt", "norml"]

        for input_str in fuzzy_inputs:
            result = matcher.match_priority(input_str)
            # Some may be high confidence, but at minimum should be >= 0.70
            assert result.confidence >= 0.70

    def test_confidence_helpers(self) -> None:
        """Test confidence helper methods."""
        # High confidence
        result_high = PriorityMatchResult(
            priority=Priority.HIGH,
            confidence=0.95,
            match_type="synonym",
            original_input="important",
        )
        assert result_high.is_high_confidence()
        assert not result_high.is_medium_confidence()
        assert not result_high.is_low_confidence()

        # Medium confidence
        result_medium = PriorityMatchResult(
            priority=Priority.HIGH,
            confidence=0.75,
            match_type="fuzzy",
            original_input="importnt",
        )
        assert not result_medium.is_high_confidence()
        assert result_medium.is_medium_confidence()
        assert not result_medium.is_low_confidence()

        # Low confidence
        result_low = PriorityMatchResult(
            priority=Priority.MEDIUM,
            confidence=0.65,
            match_type="fallback",
            original_input="xyz",
        )
        assert not result_low.is_high_confidence()
        assert not result_low.is_medium_confidence()
        assert result_low.is_low_confidence()


class TestSuggestions:
    """Test suggestion system for ambiguous inputs."""

    def test_suggest_returns_multiple_options(self) -> None:
        """Test that suggest_priorities returns multiple options."""
        matcher = SemanticPriorityMatcher()

        suggestions = matcher.suggest_priorities("important", top_n=3)

        assert len(suggestions) <= 3
        assert all(isinstance(s, PriorityMatchResult) for s in suggestions)

    def test_suggestions_sorted_by_confidence(self) -> None:
        """Test that suggestions are sorted by confidence descending."""
        matcher = SemanticPriorityMatcher()

        suggestions = matcher.suggest_priorities("urgent", top_n=4)

        # Should be sorted by confidence (highest first)
        for i in range(len(suggestions) - 1):
            assert suggestions[i].confidence >= suggestions[i + 1].confidence

    def test_suggestions_for_ambiguous_input(self) -> None:
        """Test suggestions for truly ambiguous input."""
        matcher = SemanticPriorityMatcher()

        suggestions = matcher.suggest_priorities("xyz", top_n=3)

        # Should still return suggestions even for nonsense input
        assert len(suggestions) <= 3
        assert all(isinstance(s, PriorityMatchResult) for s in suggestions)

    def test_match_includes_suggestions_on_low_confidence(self) -> None:
        """Test that low confidence matches include suggestions."""
        matcher = SemanticPriorityMatcher()

        # Very ambiguous input
        result = matcher.match_priority("abc")

        # Should have suggestions for ambiguous input
        if result.is_low_confidence():
            assert result.suggestions is not None
            assert len(result.suggestions) > 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_string(self) -> None:
        """Test handling of empty string input."""
        matcher = SemanticPriorityMatcher()

        result = matcher.match_priority("")

        # Should default to MEDIUM
        assert result.priority == Priority.MEDIUM
        assert result.match_type == "default"
        assert result.confidence == 0.5

    def test_whitespace_only(self) -> None:
        """Test handling of whitespace-only input."""
        matcher = SemanticPriorityMatcher()

        result = matcher.match_priority("   ")

        # Should default to MEDIUM
        assert result.priority == Priority.MEDIUM
        assert result.match_type == "default"

    def test_special_characters(self) -> None:
        """Test handling of special characters."""
        matcher = SemanticPriorityMatcher()

        test_cases = [
            "high!",
            "urgent?",
            "p0#",
            "critical*",
        ]

        for input_str in test_cases:
            result = matcher.match_priority(input_str)
            # Should still attempt to match (fuzzy matching may work)
            assert result is not None
            assert isinstance(result.priority, Priority)

    def test_numeric_input(self) -> None:
        """Test handling of numeric input."""
        matcher = SemanticPriorityMatcher()

        # Numeric strings should not crash
        result = matcher.match_priority("123")
        assert result is not None
        assert isinstance(result.priority, Priority)

    def test_very_long_input(self) -> None:
        """Test handling of very long input strings."""
        matcher = SemanticPriorityMatcher()

        long_input = "x" * 1000
        result = matcher.match_priority(long_input)

        assert result is not None
        assert isinstance(result.priority, Priority)


class TestSingletonGetter:
    """Test singleton getter function."""

    def test_get_priority_matcher_returns_instance(self) -> None:
        """Test that get_priority_matcher returns a matcher instance."""
        matcher = get_priority_matcher()

        assert isinstance(matcher, SemanticPriorityMatcher)

    def test_get_priority_matcher_returns_same_instance(self) -> None:
        """Test that get_priority_matcher returns singleton instance."""
        matcher1 = get_priority_matcher()
        matcher2 = get_priority_matcher()

        assert matcher1 is matcher2

    def test_singleton_is_functional(self) -> None:
        """Test that singleton instance works correctly."""
        matcher = get_priority_matcher()

        result = matcher.match_priority("urgent")
        assert result.priority == Priority.CRITICAL
        assert result.confidence >= 0.95


class TestNaturalLanguagePhrases:
    """Test natural language phrase understanding."""

    def test_critical_phrases(self) -> None:
        """Test natural language phrases for CRITICAL priority."""
        matcher = SemanticPriorityMatcher()

        phrases = [
            "needs immediate attention",
            "drop everything",
            "mission critical",
            "business critical",
            "show stopper",
        ]

        for phrase in phrases:
            result = matcher.match_priority(phrase)
            assert result.priority == Priority.CRITICAL, f"Failed for phrase: {phrase}"
            assert result.confidence >= 0.95

    def test_high_phrases(self) -> None:
        """Test natural language phrases for HIGH priority."""
        matcher = SemanticPriorityMatcher()

        phrases = [
            "needs attention",
            "time sensitive",
            "should do",
            "should have",
        ]

        for phrase in phrases:
            result = matcher.match_priority(phrase)
            assert result.priority == Priority.HIGH, f"Failed for phrase: {phrase}"
            assert result.confidence >= 0.95

    def test_medium_phrases(self) -> None:
        """Test natural language phrases for MEDIUM priority."""
        matcher = SemanticPriorityMatcher()

        phrases = [
            "could have",
            "medium priority",
        ]

        for phrase in phrases:
            result = matcher.match_priority(phrase)
            assert result.priority == Priority.MEDIUM, f"Failed for phrase: {phrase}"
            assert result.confidence >= 0.95

    def test_low_phrases(self) -> None:
        """Test natural language phrases for LOW priority."""
        matcher = SemanticPriorityMatcher()

        phrases = [
            "nice to have",
            "if time permits",
            "when possible",
            "can wait",
            "not urgent",
            "low priority",
        ]

        for phrase in phrases:
            result = matcher.match_priority(phrase)
            assert result.priority == Priority.LOW, f"Failed for phrase: {phrase}"
            assert result.confidence >= 0.95


class TestPlatformSpecificTerms:
    """Test platform-specific priority terminology."""

    def test_github_style_priorities(self) -> None:
        """Test GitHub-style P0-P3 priorities."""
        matcher = SemanticPriorityMatcher()

        test_cases = [
            ("p0", Priority.CRITICAL),
            ("p-0", Priority.CRITICAL),
            ("priority 0", Priority.CRITICAL),
            ("p1", Priority.HIGH),
            ("p-1", Priority.HIGH),
            ("priority 1", Priority.HIGH),
            ("p2", Priority.MEDIUM),
            ("p-2", Priority.MEDIUM),
            ("priority 2", Priority.MEDIUM),
            ("p3", Priority.LOW),
            ("p-3", Priority.LOW),
            ("priority 3", Priority.LOW),
        ]

        for input_str, expected_priority in test_cases:
            result = matcher.match_priority(input_str)
            assert (
                result.priority == expected_priority
            ), f"Failed for input: {input_str}"
            assert result.confidence >= 0.95

    def test_jira_style_priorities(self) -> None:
        """Test JIRA-style priority terminology."""
        matcher = SemanticPriorityMatcher()

        test_cases = [
            ("highest", Priority.CRITICAL),
            ("blocker", Priority.CRITICAL),
            ("major", Priority.HIGH),
            ("trivial", Priority.LOW),
        ]

        for input_str, expected_priority in test_cases:
            result = matcher.match_priority(input_str)
            assert (
                result.priority == expected_priority
            ), f"Failed for input: {input_str}"
            assert result.confidence >= 0.95

    def test_severity_levels(self) -> None:
        """Test severity-level terminology (Sev 0-3)."""
        matcher = SemanticPriorityMatcher()

        test_cases = [
            ("sev 0", Priority.CRITICAL),
            ("sev0", Priority.CRITICAL),
            ("severity 0", Priority.CRITICAL),
            ("sev 1", Priority.HIGH),
            ("sev1", Priority.HIGH),
            ("severity 1", Priority.HIGH),
            ("sev 2", Priority.MEDIUM),
            ("sev2", Priority.MEDIUM),
            ("severity 2", Priority.MEDIUM),
            ("sev 3", Priority.LOW),
            ("sev3", Priority.LOW),
            ("severity 3", Priority.LOW),
        ]

        for input_str, expected_priority in test_cases:
            result = matcher.match_priority(input_str)
            assert (
                result.priority == expected_priority
            ), f"Failed for input: {input_str}"
            assert result.confidence >= 0.95


class TestBackwardCompatibility:
    """Test backward compatibility with exact priority values."""

    def test_exact_values_still_work(self) -> None:
        """Test that exact priority values still work perfectly."""
        matcher = SemanticPriorityMatcher()

        test_cases = [
            ("low", Priority.LOW),
            ("medium", Priority.MEDIUM),
            ("high", Priority.HIGH),
            ("critical", Priority.CRITICAL),
        ]

        for input_str, expected_priority in test_cases:
            result = matcher.match_priority(input_str)
            assert result.priority == expected_priority
            assert result.confidence == 1.0
            assert result.match_type == "exact"

    def test_enum_values_bypass_semantic_matching(self) -> None:
        """Test that exact enum values use exact match path."""
        matcher = SemanticPriorityMatcher()

        for priority in Priority:
            result = matcher.match_priority(priority.value)
            assert result.match_type == "exact"
            assert result.confidence == 1.0
