"""Example usage of label management module.

This file demonstrates practical usage patterns for the label management
functionality in mcp-ticketer.
"""

from mcp_ticketer.core.label_manager import (
    LabelDeduplicator,
    LabelNormalizer,
    find_duplicate_labels,
    get_label_normalizer,
    normalize_label,
)


def example_1_basic_normalization() -> None:
    """Example 1: Basic label normalization."""
    print("=" * 60)
    print("Example 1: Basic Label Normalization")
    print("=" * 60)

    # Create normalizer with kebab-case strategy
    normalizer = LabelNormalizer(casing="kebab-case")

    # Normalize various label formats
    labels = [
        "Bug Report",
        "Feature_Request",
        "DOCUMENTATION",
        "performance issue",
        "UI Bug",
    ]

    print("\nNormalizing labels to kebab-case:")
    for label in labels:
        normalized = normalizer.normalize(label)
        print(f"  {label:30} → {normalized}")

    # Try different casing strategies
    print("\n\nSame labels with different casing strategies:")
    strategies = ["lowercase", "uppercase", "titlecase", "snake_case"]

    for strategy in strategies:
        norm = LabelNormalizer(casing=strategy)
        print(f"\n  {strategy}:")
        for label in labels[:3]:
            print(f"    {label:30} → {norm.normalize(label)}")


def example_2_fuzzy_matching() -> None:
    """Example 2: Fuzzy label matching with typos."""
    print("\n\n" + "=" * 60)
    print("Example 2: Fuzzy Label Matching")
    print("=" * 60)

    normalizer = LabelNormalizer(casing="lowercase")

    # Available labels in the system
    available_labels = [
        "bug",
        "feature",
        "performance",
        "documentation",
        "security",
        "testing",
    ]

    # User inputs with typos
    typo_inputs = [
        "perfomance",  # Common typo
        "feture",  # Missing letter
        "documention",  # Extra letter
        "bgu",  # Transposition
        "secuirty",  # Letter swap
    ]

    print("\nMatching typos to correct labels:")
    print(f"Available labels: {', '.join(available_labels)}\n")

    for typo in typo_inputs:
        matches = normalizer.find_similar(typo, available_labels, threshold=0.70)
        if matches:
            best_match = matches[0]
            print(
                f"  {typo:20} → {best_match.label:15} "
                f"(confidence: {best_match.confidence:.2f}, "
                f"type: {best_match.match_type})"
            )
        else:
            print(f"  {typo:20} → No match found")


def example_3_spelling_correction() -> None:
    """Example 3: Automatic spelling correction."""
    print("\n\n" + "=" * 60)
    print("Example 3: Spelling Correction")
    print("=" * 60)

    normalizer = LabelNormalizer(casing="lowercase")

    # Labels with common misspellings
    available_labels = ["bug", "feature", "performance", "documentation", "database"]

    # Known misspellings that should be corrected
    misspellings = {
        "perfomance": "performance",
        "feture": "feature",
        "documention": "documentation",
        "databse": "database",
        "bugs": "bug",  # Plural variation
        "features": "feature",
    }

    print("\nAutomatic spelling correction:")
    for wrong, expected in misspellings.items():
        matches = normalizer.find_similar(wrong, available_labels)
        if matches:
            actual = matches[0].label
            status = "✓" if actual == expected else "✗"
            print(
                f"  {status} {wrong:20} → {actual:15} "
                f"(expected: {expected}, match: {matches[0].match_type})"
            )


def example_4_duplicate_detection() -> None:
    """Example 4: Finding duplicate labels."""
    print("\n\n" + "=" * 60)
    print("Example 4: Duplicate Label Detection")
    print("=" * 60)

    deduplicator = LabelDeduplicator()

    # Messy label list with duplicates
    messy_labels = [
        "bug",
        "Bug",
        "BUG",
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

    print("\nChecking labels for duplicates:")
    print(f"Labels: {', '.join(messy_labels)}\n")

    # Find duplicates
    duplicates = deduplicator.find_duplicates(messy_labels, threshold=0.85)

    print(f"Found {len(duplicates)} duplicate pairs:")
    for label1, label2, similarity in duplicates[:10]:  # Show first 10
        print(f"  {label1:20} ≈ {label2:20} (similarity: {similarity:.2f})")


def example_5_consolidation_suggestions() -> None:
    """Example 5: Label consolidation suggestions."""
    print("\n\n" + "=" * 60)
    print("Example 5: Label Consolidation Suggestions")
    print("=" * 60)

    deduplicator = LabelDeduplicator()

    # Labels from multiple sources with inconsistent formatting
    labels = [
        "bug",
        "Bug",
        "bugs",
        "BUG",
        "feature",
        "Feature Request",
        "features",
        "new feature",
        "documentation",
        "docs",
        "Documentation",
        "readme",
        "performance",
        "perfomance",
        "optimization",
    ]

    print("\nAnalyzing labels for consolidation:")
    print(f"Total unique labels: {len(labels)}\n")

    # Get consolidation suggestions
    suggestions = deduplicator.suggest_consolidation(labels, threshold=0.85)

    print(f"Consolidation recommendations ({len(suggestions)} groups):\n")
    for canonical, variants in suggestions.items():
        print(f"  Use '{canonical}' instead of:")
        for variant in variants:
            print(f"    - {variant}")
        print()


def example_6_real_world_workflow() -> None:
    """Example 6: Real-world label management workflow."""
    print("\n\n" + "=" * 60)
    print("Example 6: Real-World Label Management Workflow")
    print("=" * 60)

    # Step 1: Collect labels from different sources
    print("\n1. Collecting labels from different ticket systems:")

    jira_labels = ["Bug Report", "Feature_Request", "DOCUMENTATION", "HIGH PRIORITY"]
    github_labels = ["bug", "enhancement", "docs", "high-priority"]
    linear_labels = ["bug-fix", "new-feature", "documentation", "urgent"]

    print(f"  JIRA:   {', '.join(jira_labels)}")
    print(f"  GitHub: {', '.join(github_labels)}")
    print(f"  Linear: {', '.join(linear_labels)}")

    # Step 2: Normalize all labels
    print("\n2. Normalizing labels to kebab-case:")

    normalizer = LabelNormalizer(casing="kebab-case")
    all_labels = jira_labels + github_labels + linear_labels
    normalized_labels = [normalizer.normalize(lbl) for lbl in all_labels]

    print(f"  Normalized: {', '.join(set(normalized_labels))}")

    # Step 3: Find duplicates
    print("\n3. Detecting duplicates:")

    deduplicator = LabelDeduplicator()
    duplicates = deduplicator.find_duplicates(normalized_labels, threshold=0.85)

    print(f"  Found {len(duplicates)} duplicate pairs")

    # Step 4: Get consolidation suggestions
    print("\n4. Consolidation suggestions:")

    suggestions = deduplicator.suggest_consolidation(normalized_labels, threshold=0.85)

    if suggestions:
        for canonical, variants in list(suggestions.items())[:3]:
            print(f"  - Use '{canonical}' (instead of: {', '.join(variants)})")
    else:
        print("  No consolidation needed!")

    # Step 5: Create clean label set
    print("\n5. Final clean label set:")

    clean_labels = set()
    replaced_labels = set()

    for label in normalized_labels:
        # Check if this label should be replaced
        for canonical, variants in suggestions.items():
            if label in variants:
                clean_labels.add(canonical)
                replaced_labels.add(label)
                break
        else:
            clean_labels.add(label)

    print(f"  Clean labels: {', '.join(sorted(clean_labels))}")
    print(f"  Reduced from {len(all_labels)} to {len(clean_labels)} unique labels")


def example_7_convenience_functions() -> None:
    """Example 7: Using convenience functions."""
    print("\n\n" + "=" * 60)
    print("Example 7: Convenience Functions")
    print("=" * 60)

    # Quick normalization
    print("\n1. Quick label normalization:")
    result = normalize_label("Bug Report", casing="kebab-case")
    print(f"  normalize_label('Bug Report', 'kebab-case') → {result}")

    # Quick duplicate detection
    print("\n2. Quick duplicate detection:")
    labels = ["bug", "Bug", "bugs", "feature", "Feature"]
    duplicates = find_duplicate_labels(labels)
    print(f"  Labels: {', '.join(labels)}")
    print(f"  Duplicates found: {len(duplicates)}")
    for label1, label2, score in duplicates[:3]:
        print(f"    - {label1} ≈ {label2} ({score:.2f})")

    # Singleton normalizer
    print("\n3. Singleton normalizer pattern:")
    norm1 = get_label_normalizer(casing="lowercase")
    norm2 = get_label_normalizer(casing="lowercase")
    print(f"  Same instance: {norm1 is norm2}")
    print(f"  Result: {norm1.normalize('Bug Report')}")


def main() -> None:
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "MCP-TICKETER LABEL MANAGEMENT EXAMPLES" + " " * 10 + "║")
    print("╚" + "=" * 58 + "╝")

    example_1_basic_normalization()
    example_2_fuzzy_matching()
    example_3_spelling_correction()
    example_4_duplicate_detection()
    example_5_consolidation_suggestions()
    example_6_real_world_workflow()
    example_7_convenience_functions()

    print("\n\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
