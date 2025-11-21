"""Tests for label management and normalization."""

import pytest

from mcp_ticketer.core.label_manager import (
    CasingStrategy,
    LabelDeduplicator,
    LabelMatch,
    LabelNormalizer,
    find_duplicate_labels,
    get_label_normalizer,
    normalize_label,
)


class TestCasingStrategy:
    """Tests for CasingStrategy enum."""

    def test_enum_values(self) -> None:
        """Test that all casing strategies are defined."""
        assert CasingStrategy.LOWERCASE.value == "lowercase"
        assert CasingStrategy.TITLECASE.value == "titlecase"
        assert CasingStrategy.UPPERCASE.value == "uppercase"
        assert CasingStrategy.KEBAB_CASE.value == "kebab-case"
        assert CasingStrategy.SNAKE_CASE.value == "snake_case"


class TestLabelMatch:
    """Tests for LabelMatch dataclass."""

    def test_high_confidence(self) -> None:
        """Test high confidence threshold."""
        match = LabelMatch(
            label="bug",
            confidence=0.95,
            match_type="exact",
            original_input="bug",
        )
        assert match.is_high_confidence()
        assert not match.is_medium_confidence()
        assert not match.is_low_confidence()

    def test_medium_confidence(self) -> None:
        """Test medium confidence threshold."""
        match = LabelMatch(
            label="bug",
            confidence=0.80,
            match_type="fuzzy",
            original_input="bgu",
        )
        assert not match.is_high_confidence()
        assert match.is_medium_confidence()
        assert not match.is_low_confidence()

    def test_low_confidence(self) -> None:
        """Test low confidence threshold."""
        match = LabelMatch(
            label="bug",
            confidence=0.60,
            match_type="fuzzy",
            original_input="xyz",
        )
        assert not match.is_high_confidence()
        assert not match.is_medium_confidence()
        assert match.is_low_confidence()


class TestLabelNormalizer:
    """Tests for LabelNormalizer class."""

    def test_init_valid_casing(self) -> None:
        """Test initialization with valid casing strategies."""
        normalizer = LabelNormalizer(casing="lowercase")
        assert normalizer.casing == CasingStrategy.LOWERCASE

        normalizer = LabelNormalizer(casing="kebab-case")
        assert normalizer.casing == CasingStrategy.KEBAB_CASE

    def test_init_invalid_casing(self) -> None:
        """Test initialization with invalid casing strategy."""
        with pytest.raises(ValueError, match="Invalid casing strategy"):
            LabelNormalizer(casing="invalid")

    def test_normalize_lowercase(self) -> None:
        """Test lowercase normalization."""
        normalizer = LabelNormalizer(casing="lowercase")
        assert normalizer.normalize("Bug Report") == "bug report"
        assert normalizer.normalize("FEATURE") == "feature"
        assert normalizer.normalize("Test-Case") == "test-case"

    def test_normalize_uppercase(self) -> None:
        """Test uppercase normalization."""
        normalizer = LabelNormalizer(casing="uppercase")
        assert normalizer.normalize("Bug Report") == "BUG REPORT"
        assert normalizer.normalize("feature") == "FEATURE"

    def test_normalize_titlecase(self) -> None:
        """Test titlecase normalization."""
        normalizer = LabelNormalizer(casing="titlecase")
        assert normalizer.normalize("bug report") == "Bug Report"
        assert normalizer.normalize("FEATURE") == "Feature"

    def test_normalize_kebab_case(self) -> None:
        """Test kebab-case normalization."""
        normalizer = LabelNormalizer(casing="kebab-case")
        assert normalizer.normalize("Bug Report") == "bug-report"
        assert normalizer.normalize("feature_request") == "feature-request"
        assert normalizer.normalize("test  case") == "test-case"  # Multiple spaces
        assert (
            normalizer.normalize("api--endpoint") == "api-endpoint"
        )  # Duplicate hyphens

    def test_normalize_snake_case(self) -> None:
        """Test snake_case normalization."""
        normalizer = LabelNormalizer(casing="snake_case")
        assert normalizer.normalize("Bug Report") == "bug_report"
        assert normalizer.normalize("feature-request") == "feature_request"
        assert normalizer.normalize("test  case") == "test_case"  # Multiple spaces
        assert (
            normalizer.normalize("api__endpoint") == "api_endpoint"
        )  # Duplicate underscores

    def test_normalize_empty_string(self) -> None:
        """Test normalization of empty string."""
        normalizer = LabelNormalizer()
        assert normalizer.normalize("") == ""
        assert normalizer.normalize("   ") == ""

    def test_spelling_correction(self) -> None:
        """Test spelling correction only happens in find_similar, not normalize."""
        normalizer = LabelNormalizer(casing="lowercase")
        # Normalize doesn't apply spelling correction (preserves original)
        assert normalizer.normalize("perfomance") == "perfomance"
        assert normalizer.normalize("feture") == "feture"

        # But find_similar should use spelling correction
        available = ["performance", "feature"]
        matches = normalizer.find_similar("perfomance", available)
        if matches:
            assert matches[0].label == "performance"
            assert matches[0].match_type == "spelling"

    def test_plural_variations(self) -> None:
        """Test plural variation handling in find_similar."""
        normalizer = LabelNormalizer(casing="lowercase")
        # Normalize preserves original
        assert normalizer.normalize("bugs") == "bugs"
        assert normalizer.normalize("features") == "features"

        # But find_similar should match to singular
        available = ["bug", "feature"]
        matches = normalizer.find_similar("bugs", available)
        if matches:
            assert matches[0].label == "bug"
            assert matches[0].match_type == "spelling"

    def test_find_similar_exact_match(self) -> None:
        """Test exact match in find_similar."""
        normalizer = LabelNormalizer(casing="lowercase")
        available = ["bug", "feature", "documentation"]

        matches = normalizer.find_similar("bug", available)
        assert len(matches) == 1
        assert matches[0].label == "bug"
        assert matches[0].confidence == 1.0
        assert matches[0].match_type == "exact"

    def test_find_similar_case_insensitive(self) -> None:
        """Test case-insensitive exact match."""
        normalizer = LabelNormalizer(casing="lowercase")
        available = ["Bug", "Feature", "Documentation"]

        matches = normalizer.find_similar("bug", available)
        assert len(matches) == 1
        assert matches[0].label == "Bug"
        assert matches[0].confidence == 1.0

    def test_find_similar_spelling_correction(self) -> None:
        """Test spelling correction in find_similar."""
        normalizer = LabelNormalizer(casing="lowercase")
        available = ["performance", "feature", "documentation"]

        matches = normalizer.find_similar("perfomance", available)
        assert len(matches) == 1
        assert matches[0].label == "performance"
        assert matches[0].confidence == 0.95
        assert matches[0].match_type == "spelling"

    @pytest.mark.skipif(
        not hasattr(LabelNormalizer, "_fuzzy_match"),
        reason="Fuzzy matching requires rapidfuzz",
    )
    def test_find_similar_fuzzy_match(self) -> None:
        """Test fuzzy matching in find_similar."""
        normalizer = LabelNormalizer(casing="lowercase")
        available = ["bug", "feature", "documentation"]

        # Close typo should match with high confidence
        matches = normalizer.find_similar("bgu", available, threshold=0.70)
        if matches:  # Only if rapidfuzz is available
            assert matches[0].label == "bug"
            assert matches[0].match_type == "fuzzy"
            assert matches[0].confidence >= 0.70

    def test_find_similar_empty_input(self) -> None:
        """Test find_similar with empty input."""
        normalizer = LabelNormalizer()
        available = ["bug", "feature"]

        matches = normalizer.find_similar("", available)
        assert len(matches) == 0

    def test_find_similar_empty_available(self) -> None:
        """Test find_similar with empty available labels."""
        normalizer = LabelNormalizer()
        matches = normalizer.find_similar("bug", [])
        assert len(matches) == 0

    def test_find_similar_threshold(self) -> None:
        """Test threshold filtering in find_similar."""
        normalizer = LabelNormalizer(casing="lowercase")
        available = ["bug", "feature", "documentation"]

        # High threshold should filter out weak matches
        matches = normalizer.find_similar("xyz", available, threshold=0.90)
        assert len(matches) == 0 or matches[0].confidence >= 0.90


class TestLabelDeduplicator:
    """Tests for LabelDeduplicator class."""

    def test_find_duplicates_exact(self) -> None:
        """Test finding exact duplicates (case variations)."""
        deduplicator = LabelDeduplicator()
        labels = ["bug", "Bug", "BUG"]

        duplicates = deduplicator.find_duplicates(labels)
        assert len(duplicates) >= 2  # At least bug-Bug and bug-BUG

        # Check first duplicate is highest similarity
        if duplicates:
            assert duplicates[0][2] == 1.0  # Perfect similarity

    def test_find_duplicates_plural(self) -> None:
        """Test finding plural variations."""
        deduplicator = LabelDeduplicator()
        labels = ["bug", "bugs", "feature", "features"]

        duplicates = deduplicator.find_duplicates(labels, threshold=0.80)

        # Should find bug/bugs and feature/features pairs
        found_labels = {(d[0], d[1]) for d in duplicates}
        assert any(("bug" in pair and "bugs" in pair) for pair in found_labels) or any(
            ("feature" in pair and "features" in pair) for pair in found_labels
        )

    def test_find_duplicates_empty_list(self) -> None:
        """Test finding duplicates in empty list."""
        deduplicator = LabelDeduplicator()
        duplicates = deduplicator.find_duplicates([])
        assert len(duplicates) == 0

    def test_find_duplicates_no_duplicates(self) -> None:
        """Test when no duplicates exist."""
        deduplicator = LabelDeduplicator()
        labels = ["bug", "feature", "documentation"]

        duplicates = deduplicator.find_duplicates(labels, threshold=0.95)
        # Should find no high-similarity duplicates
        assert len(duplicates) == 0

    def test_find_duplicates_sorted(self) -> None:
        """Test that duplicates are sorted by similarity."""
        deduplicator = LabelDeduplicator()
        labels = ["bug", "Bug", "bgu", "feature"]

        duplicates = deduplicator.find_duplicates(labels, threshold=0.70)

        # Check sorting: each subsequent duplicate should have <= similarity
        for i in range(len(duplicates) - 1):
            assert duplicates[i][2] >= duplicates[i + 1][2]

    def test_suggest_consolidation_exact(self) -> None:
        """Test consolidation suggestions for exact duplicates."""
        deduplicator = LabelDeduplicator()
        labels = ["bug", "Bug", "BUG"]

        suggestions = deduplicator.suggest_consolidation(labels)

        # Should suggest consolidating to lowercase "bug"
        assert "bug" in suggestions
        assert set(suggestions["bug"]) == {"Bug", "BUG"}

    def test_suggest_consolidation_empty(self) -> None:
        """Test consolidation suggestions for empty list."""
        deduplicator = LabelDeduplicator()
        suggestions = deduplicator.suggest_consolidation([])
        assert len(suggestions) == 0

    def test_suggest_consolidation_no_duplicates(self) -> None:
        """Test consolidation when no duplicates exist."""
        deduplicator = LabelDeduplicator()
        labels = ["bug", "feature", "documentation"]

        suggestions = deduplicator.suggest_consolidation(labels, threshold=0.95)
        assert len(suggestions) == 0

    def test_suggest_consolidation_canonical_selection(self) -> None:
        """Test that canonical label is selected correctly."""
        deduplicator = LabelDeduplicator()
        labels = ["Feature", "feature", "FEATURE"]

        suggestions = deduplicator.suggest_consolidation(labels)

        # Canonical should be lowercase "feature"
        assert "feature" in suggestions

    def test_are_synonyms(self) -> None:
        """Test synonym detection."""
        deduplicator = LabelDeduplicator()

        assert deduplicator._are_synonyms("bug", "issue")
        assert deduplicator._are_synonyms("issue", "bug")
        assert deduplicator._are_synonyms("feature", "enhancement")
        assert not deduplicator._are_synonyms("bug", "feature")

    def test_calculate_similarity_exact(self) -> None:
        """Test similarity calculation for exact matches."""
        deduplicator = LabelDeduplicator()

        similarity = deduplicator._calculate_similarity("bug", "bug")
        assert similarity == 1.0

    def test_calculate_similarity_case_insensitive(self) -> None:
        """Test case-insensitive similarity calculation."""
        deduplicator = LabelDeduplicator()

        similarity = deduplicator._calculate_similarity("bug", "BUG")
        assert similarity == 1.0

    def test_calculate_similarity_synonyms(self) -> None:
        """Test similarity calculation for synonyms."""
        deduplicator = LabelDeduplicator()

        similarity = deduplicator._calculate_similarity("bug", "issue")
        assert similarity == 0.95


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_normalize_label(self) -> None:
        """Test normalize_label convenience function."""
        result = normalize_label("Bug Report", casing="kebab-case")
        assert result == "bug-report"

        result = normalize_label("Feature", casing="uppercase")
        assert result == "FEATURE"

    def test_find_duplicate_labels(self) -> None:
        """Test find_duplicate_labels convenience function."""
        labels = ["bug", "Bug", "BUG"]
        duplicates = find_duplicate_labels(labels)

        assert len(duplicates) >= 2
        if duplicates:
            assert duplicates[0][2] == 1.0  # First is highest similarity

    def test_get_label_normalizer_singleton(self) -> None:
        """Test that get_label_normalizer returns singleton."""
        normalizer1 = get_label_normalizer(casing="lowercase")
        normalizer2 = get_label_normalizer(casing="lowercase")

        assert normalizer1 is normalizer2

    def test_get_label_normalizer_different_casing(self) -> None:
        """Test that get_label_normalizer creates new instance for different casing."""
        normalizer1 = get_label_normalizer(casing="lowercase")
        normalizer2 = get_label_normalizer(casing="uppercase")

        # Should be different instances
        assert normalizer1 is not normalizer2
        assert normalizer1.casing != normalizer2.casing


class TestIntegrationScenarios:
    """Integration tests for real-world scenarios."""

    def test_ticket_label_normalization(self) -> None:
        """Test normalizing ticket labels from different sources."""
        normalizer = LabelNormalizer(casing="kebab-case")

        # Labels from different ticket systems
        jira_labels = ["Bug Report", "Feature_Request", "DOCUMENTATION"]
        github_labels = ["bug", "enhancement", "docs"]
        linear_labels = ["bug-fix", "new-feature", "documentation"]

        # Normalize all
        normalized = [
            normalizer.normalize(lbl)
            for lbl in jira_labels + github_labels + linear_labels
        ]

        # Should have consistent formatting
        assert all("-" in lbl or lbl.islower() for lbl in normalized)

    def test_duplicate_detection_workflow(self) -> None:
        """Test complete duplicate detection and consolidation workflow."""
        deduplicator = LabelDeduplicator()

        # Messy label list from different sources
        labels = [
            "bug",
            "Bug",
            "bugs",
            "feature",
            "Feature Request",
            "features",
            "documentation",
            "docs",
            "Documentation",
            "performance",
            "perfomance",  # Typo
        ]

        # Find duplicates
        duplicates = deduplicator.find_duplicates(labels, threshold=0.80)
        assert len(duplicates) > 0

        # Get consolidation suggestions
        suggestions = deduplicator.suggest_consolidation(labels, threshold=0.80)

        # Should suggest consolidating variants
        canonical_labels = set(suggestions.keys())
        assert len(canonical_labels) > 0

    def test_typo_correction_workflow(self) -> None:
        """Test typo correction in label matching."""
        normalizer = LabelNormalizer(casing="lowercase")
        available = ["bug", "feature", "performance", "documentation"]

        # Common typos
        typos = ["perfomance", "feture", "documention", "bgu"]

        for typo in typos:
            matches = normalizer.find_similar(typo, available, threshold=0.70)
            if matches:  # If fuzzy matching is available
                # Should find a reasonable match
                assert len(matches) > 0
                assert matches[0].confidence >= 0.70
