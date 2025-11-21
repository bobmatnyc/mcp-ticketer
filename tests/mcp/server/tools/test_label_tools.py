"""Tests for label management MCP tools."""

import pytest

from mcp_ticketer.core.label_manager import LabelDeduplicator, LabelNormalizer


class TestLabelNormalization:
    """Test label normalization functionality."""

    def test_normalize_lowercase(self):
        """Test lowercase normalization."""
        normalizer = LabelNormalizer(casing="lowercase")
        assert normalizer.normalize("Bug Report") == "bug report"
        assert normalizer.normalize("FEATURE-REQUEST") == "feature-request"

    def test_normalize_kebab_case(self):
        """Test kebab-case normalization."""
        normalizer = LabelNormalizer(casing="kebab-case")
        assert normalizer.normalize("Bug Report") == "bug-report"
        assert normalizer.normalize("FEATURE REQUEST") == "feature-request"
        assert normalizer.normalize("snake_case_label") == "snake-case-label"

    def test_normalize_snake_case(self):
        """Test snake_case normalization."""
        normalizer = LabelNormalizer(casing="snake_case")
        assert normalizer.normalize("Bug Report") == "bug_report"
        assert normalizer.normalize("FEATURE-REQUEST") == "feature_request"

    def test_normalize_invalid_casing(self):
        """Test invalid casing strategy raises ValueError."""
        with pytest.raises(ValueError, match="Invalid casing strategy"):
            LabelNormalizer(casing="invalid-casing")


class TestLabelDeduplication:
    """Test label deduplication functionality."""

    def test_find_exact_duplicates(self):
        """Test finding exact duplicates with different cases."""
        deduplicator = LabelDeduplicator()
        labels = ["bug", "Bug", "BUG", "feature"]
        duplicates = deduplicator.find_duplicates(labels)

        # Should find duplicates between bug variants
        assert len(duplicates) >= 2  # At least "bug" vs "Bug" and others

        # Check that all bug variants are marked as duplicates
        bug_duplicates = [
            (l1, l2) for l1, l2, _ in duplicates if "bug" in l1.lower() and "bug" in l2.lower()
        ]
        assert len(bug_duplicates) >= 2

    def test_find_fuzzy_duplicates(self):
        """Test finding fuzzy duplicates with similar names."""
        deduplicator = LabelDeduplicator()
        labels = ["feature", "feture", "featrue", "bug"]
        duplicates = deduplicator.find_duplicates(labels, threshold=0.80)

        # Should find spelling variations
        feature_duplicates = [
            (l1, l2)
            for l1, l2, _ in duplicates
            if "featur" in l1.lower() or "featur" in l2.lower()
        ]
        assert len(feature_duplicates) >= 1

    def test_suggest_consolidation(self):
        """Test consolidation suggestions for similar labels."""
        deduplicator = LabelDeduplicator()
        labels = ["bug", "Bug", "bugs", "feature", "feture"]
        consolidations = deduplicator.suggest_consolidation(labels, threshold=0.85)

        # Should suggest consolidating bug variants
        assert len(consolidations) >= 1

        # Check that "bug" is canonical and has variants
        if "bug" in consolidations:
            variants = consolidations["bug"]
            assert "Bug" in variants or "bugs" in variants


class TestLabelMatcher:
    """Test label matching and similarity detection."""

    def test_find_similar_exact_match(self):
        """Test exact match has confidence 1.0."""
        normalizer = LabelNormalizer()
        available = ["bug", "feature", "performance"]
        matches = normalizer.find_similar("bug", available)

        assert len(matches) == 1
        assert matches[0].label == "bug"
        assert matches[0].confidence == 1.0
        assert matches[0].match_type == "exact"

    def test_find_similar_spelling_correction(self):
        """Test spelling correction match."""
        normalizer = LabelNormalizer()
        available = ["feature", "bug", "performance"]
        matches = normalizer.find_similar("feture", available)

        # Should find "feature" via spelling correction
        if matches:
            assert matches[0].label == "feature"
            assert matches[0].confidence >= 0.90

    def test_find_similar_no_match(self):
        """Test no match returns empty list."""
        normalizer = LabelNormalizer()
        available = ["bug", "feature"]
        matches = normalizer.find_similar("completely-different", available, threshold=0.95)

        # With high threshold, should find no matches
        assert len(matches) == 0


class TestSpellingCorrection:
    """Test spelling correction dictionary."""

    def test_common_misspellings(self):
        """Test known misspellings are corrected."""
        normalizer = LabelNormalizer()

        # Test some common misspellings
        assert normalizer._apply_spelling_correction("feture") == "feature"
        assert normalizer._apply_spelling_correction("perfomance") == "performance"
        assert normalizer._apply_spelling_correction("bugfix") == "bug-fix"
        assert normalizer._apply_spelling_correction("databse") == "database"

    def test_correct_spelling_unchanged(self):
        """Test correct spelling is not changed."""
        normalizer = LabelNormalizer()

        assert normalizer._apply_spelling_correction("bug") == "bug"
        assert normalizer._apply_spelling_correction("feature") == "feature"
        assert normalizer._apply_spelling_correction("performance") == "performance"


# Integration tests would require mock adapters
# These are covered in integration test files
