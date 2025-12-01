"""Tests for label management MCP tools."""

import warnings

import pytest

from mcp_ticketer.core.label_manager import LabelDeduplicator, LabelNormalizer
from mcp_ticketer.mcp.server.tools.label_tools import (
    label,
    label_cleanup_report,
    label_find_duplicates,
    label_list,
    label_merge,
    label_normalize,
    label_rename,
    label_suggest_merge,
)


class TestLabelNormalization:
    """Test label normalization functionality."""

    def test_normalize_lowercase(self) -> None:
        """Test lowercase normalization."""
        normalizer = LabelNormalizer(casing="lowercase")
        assert normalizer.normalize("Bug Report") == "bug report"
        assert normalizer.normalize("FEATURE-REQUEST") == "feature-request"

    def test_normalize_kebab_case(self) -> None:
        """Test kebab-case normalization."""
        normalizer = LabelNormalizer(casing="kebab-case")
        assert normalizer.normalize("Bug Report") == "bug-report"
        assert normalizer.normalize("FEATURE REQUEST") == "feature-request"
        assert normalizer.normalize("snake_case_label") == "snake-case-label"

    def test_normalize_snake_case(self) -> None:
        """Test snake_case normalization."""
        normalizer = LabelNormalizer(casing="snake_case")
        assert normalizer.normalize("Bug Report") == "bug_report"
        assert normalizer.normalize("FEATURE-REQUEST") == "feature_request"

    def test_normalize_invalid_casing(self) -> None:
        """Test invalid casing strategy raises ValueError."""
        with pytest.raises(ValueError, match="Invalid casing strategy"):
            LabelNormalizer(casing="invalid-casing")


class TestLabelDeduplication:
    """Test label deduplication functionality."""

    def test_find_exact_duplicates(self) -> None:
        """Test finding exact duplicates with different cases."""
        deduplicator = LabelDeduplicator()
        labels = ["bug", "Bug", "BUG", "feature"]
        duplicates = deduplicator.find_duplicates(labels)

        # Should find duplicates between bug variants
        assert len(duplicates) >= 2  # At least "bug" vs "Bug" and others

        # Check that all bug variants are marked as duplicates
        bug_duplicates = [
            (l1, l2)
            for l1, l2, _ in duplicates
            if "bug" in l1.lower() and "bug" in l2.lower()
        ]
        assert len(bug_duplicates) >= 2

    def test_find_fuzzy_duplicates(self) -> None:
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

    def test_suggest_consolidation(self) -> None:
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

    def test_find_similar_exact_match(self) -> None:
        """Test exact match has confidence 1.0."""
        normalizer = LabelNormalizer()
        available = ["bug", "feature", "performance"]
        matches = normalizer.find_similar("bug", available)

        assert len(matches) == 1
        assert matches[0].label == "bug"
        assert matches[0].confidence == 1.0
        assert matches[0].match_type == "exact"

    def test_find_similar_spelling_correction(self) -> None:
        """Test spelling correction match."""
        normalizer = LabelNormalizer()
        available = ["feature", "bug", "performance"]
        matches = normalizer.find_similar("feture", available)

        # Should find "feature" via spelling correction
        if matches:
            assert matches[0].label == "feature"
            assert matches[0].confidence >= 0.90

    def test_find_similar_no_match(self) -> None:
        """Test no match returns empty list."""
        normalizer = LabelNormalizer()
        available = ["bug", "feature"]
        matches = normalizer.find_similar(
            "completely-different", available, threshold=0.95
        )

        # With high threshold, should find no matches
        assert len(matches) == 0


class TestSpellingCorrection:
    """Test spelling correction dictionary."""

    def test_common_misspellings(self) -> None:
        """Test known misspellings are corrected."""
        normalizer = LabelNormalizer()

        # Test some common misspellings
        assert normalizer._apply_spelling_correction("feture") == "feature"
        assert normalizer._apply_spelling_correction("perfomance") == "performance"
        assert normalizer._apply_spelling_correction("bugfix") == "bug-fix"
        assert normalizer._apply_spelling_correction("databse") == "database"

    def test_correct_spelling_unchanged(self) -> None:
        """Test correct spelling is not changed."""
        normalizer = LabelNormalizer()

        assert normalizer._apply_spelling_correction("bug") == "bug"
        assert normalizer._apply_spelling_correction("feature") == "feature"
        assert normalizer._apply_spelling_correction("performance") == "performance"


class TestUnifiedLabelTool:
    """Test unified label() tool with action-based routing."""

    @pytest.mark.asyncio
    async def test_label_invalid_action(self) -> None:
        """Test that invalid action returns error."""
        result = await label(action="invalid_action")

        assert result["status"] == "error"
        assert "invalid_action" in result["error"].lower()
        assert "valid_actions" in result
        assert len(result["valid_actions"]) == 7

    @pytest.mark.asyncio
    async def test_label_normalize_missing_params(self) -> None:
        """Test that normalize action requires label_name."""
        result = await label(action="normalize")

        assert result["status"] == "error"
        assert "label_name is required" in result["error"]

    @pytest.mark.asyncio
    async def test_label_suggest_merge_missing_params(self) -> None:
        """Test that suggest_merge requires source and target."""
        result = await label(action="suggest_merge", source_label="bug")

        assert result["status"] == "error"
        assert "target_label are required" in result["error"]

    @pytest.mark.asyncio
    async def test_label_merge_missing_params(self) -> None:
        """Test that merge requires source and target."""
        result = await label(action="merge", target_label="bugfix")

        assert result["status"] == "error"
        assert "source_label and target_label are required" in result["error"]

    @pytest.mark.asyncio
    async def test_label_rename_missing_params(self) -> None:
        """Test that rename requires old_name and new_name."""
        result = await label(action="rename", old_name="old")

        assert result["status"] == "error"
        assert "new_name are required" in result["error"]


class TestDeprecationWarnings:
    """Test that deprecated tools emit warnings."""

    @pytest.mark.asyncio
    async def test_label_list_deprecation_warning(self, mocker) -> None:
        """Test label_list emits deprecation warning."""
        # Mock adapter to prevent actual calls
        mock_adapter = mocker.MagicMock()
        mock_adapter.list_labels = mocker.AsyncMock(return_value=[])
        mocker.patch(
            "mcp_ticketer.mcp.server.tools.label_tools.get_adapter",
            return_value=mock_adapter,
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            await label_list()

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "label_list is deprecated" in str(w[0].message)
            assert "label(action='list'" in str(w[0].message)

    @pytest.mark.asyncio
    async def test_label_normalize_deprecation_warning(self) -> None:
        """Test label_normalize emits deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            await label_normalize(label_name="test")

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "label_normalize is deprecated" in str(w[0].message)

    @pytest.mark.asyncio
    async def test_label_find_duplicates_deprecation_warning(self, mocker) -> None:
        """Test label_find_duplicates emits deprecation warning."""
        # Mock adapter to prevent actual calls
        mock_adapter = mocker.MagicMock()
        mock_adapter.list_labels = mocker.AsyncMock(return_value=[])
        mocker.patch(
            "mcp_ticketer.mcp.server.tools.label_tools.get_adapter",
            return_value=mock_adapter,
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            await label_find_duplicates()

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "label_find_duplicates is deprecated" in str(w[0].message)

    @pytest.mark.asyncio
    async def test_label_suggest_merge_deprecation_warning(self, mocker) -> None:
        """Test label_suggest_merge emits deprecation warning."""
        # Mock adapter to prevent actual calls
        mock_adapter = mocker.MagicMock()
        mock_adapter.list = mocker.AsyncMock(return_value=[])
        mocker.patch(
            "mcp_ticketer.mcp.server.tools.label_tools.get_adapter",
            return_value=mock_adapter,
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            await label_suggest_merge(source_label="bug", target_label="bugfix")

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "label_suggest_merge is deprecated" in str(w[0].message)

    @pytest.mark.asyncio
    async def test_label_merge_deprecation_warning(self, mocker) -> None:
        """Test label_merge emits deprecation warning."""
        # Mock adapter to prevent actual calls
        mock_adapter = mocker.MagicMock()
        mock_adapter.list = mocker.AsyncMock(return_value=[])
        mocker.patch(
            "mcp_ticketer.mcp.server.tools.label_tools.get_adapter",
            return_value=mock_adapter,
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            await label_merge(source_label="bug", target_label="bugfix")

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "label_merge is deprecated" in str(w[0].message)

    @pytest.mark.asyncio
    async def test_label_rename_deprecation_warning(self, mocker) -> None:
        """Test label_rename emits deprecation warning."""
        # Mock adapter to prevent actual calls
        mock_adapter = mocker.MagicMock()
        mock_adapter.list = mocker.AsyncMock(return_value=[])
        mocker.patch(
            "mcp_ticketer.mcp.server.tools.label_tools.get_adapter",
            return_value=mock_adapter,
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # First call to label_rename triggers its deprecation warning
            # Second call to label_merge (from rename) triggers merge's warning
            await label_rename(old_name="old", new_name="new")

            # Should have 2 warnings: one from rename, one from merge
            assert len(w) == 2
            assert issubclass(w[0].category, DeprecationWarning)
            assert "label_rename is deprecated" in str(w[0].message)

    @pytest.mark.asyncio
    async def test_label_cleanup_report_deprecation_warning(self, mocker) -> None:
        """Test label_cleanup_report emits deprecation warning."""
        # Mock adapter to prevent actual calls
        mock_adapter = mocker.MagicMock()
        mock_adapter.list_labels = mocker.AsyncMock(return_value=[])
        mock_adapter.list = mocker.AsyncMock(return_value=[])
        mocker.patch(
            "mcp_ticketer.mcp.server.tools.label_tools.get_adapter",
            return_value=mock_adapter,
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            await label_cleanup_report()

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "label_cleanup_report is deprecated" in str(w[0].message)


# Integration tests would require mock adapters
# These are covered in integration test files
