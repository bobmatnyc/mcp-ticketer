#!/usr/bin/env python3
"""
Add -> None return type annotations to test functions.

This script identifies test functions, mock functions, and fixtures that
don't return values and adds the -> None annotation.
"""

import re
from pathlib import Path
from typing import List, Tuple


def should_add_return_type(line: str, next_lines: List[str]) -> bool:
    """
    Determine if a function definition should get -> None annotation.

    Args:
        line: The function definition line
        next_lines: Following lines to check for return statements

    Returns:
        True if -> None should be added
    """
    # Already has return type annotation
    if '->' in line:
        return False

    # Check if function returns a value by examining the body
    # (Look ahead a few lines for return statements)
    for next_line in next_lines[:10]:
        # Skip empty lines and comments
        stripped = next_line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        # Found a return with value - don't add -> None
        if re.match(r'return\s+\S', stripped):
            return False

        # Break on next function definition
        if stripped.startswith('def '):
            break

    return True


def add_return_types_to_file(file_path: Path) -> Tuple[int, List[str]]:
    """
    Add -> None annotations to test functions in a file.

    Args:
        file_path: Path to the Python file

    Returns:
        Tuple of (number of changes, list of modified function names)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    modified_lines = []
    changes = 0
    modified_functions = []

    # Pattern for test/mock/fixture functions
    # Matches: def test_foo(...): or @pytest.fixture followed by def
    func_pattern = re.compile(
        r'^(\s*)(def\s+(test_|mock_|setup_|teardown_)\w+\s*\([^)]*\))\s*:\s*$'
    )

    # Pattern for any function without return type after @pytest.fixture
    fixture_func_pattern = re.compile(
        r'^(\s*)(def\s+\w+\s*\([^)]*\))\s*:\s*$'
    )

    i = 0
    is_fixture = False

    while i < len(lines):
        line = lines[i]

        # Check if this is a @pytest.fixture decorator
        if '@pytest.fixture' in line:
            is_fixture = True
            modified_lines.append(line)
            i += 1
            continue

        # If previous line was @pytest.fixture, apply to any function
        match = func_pattern.match(line) or (is_fixture and fixture_func_pattern.match(line))

        if match:
            indent = match.group(1)
            func_def = match.group(2)

            # Extract function name for tracking
            func_name_match = re.search(r'def\s+(\w+)', func_def)
            func_name = func_name_match.group(1) if func_name_match else "unknown"

            # Get next few lines to check for return statements
            next_lines = lines[i+1:i+11] if i+1 < len(lines) else []

            if should_add_return_type(line, next_lines):
                # Add -> None before the colon
                new_line = f"{indent}{func_def} -> None:\n"
                modified_lines.append(new_line)
                changes += 1
                modified_functions.append(func_name)
            else:
                modified_lines.append(line)

            is_fixture = False  # Reset after processing function
        else:
            modified_lines.append(line)
            # Reset fixture flag if we see a non-function line
            if line.strip() and not line.strip().startswith('#'):
                is_fixture = False

        i += 1

    # Only write if changes were made
    if changes > 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(modified_lines)

    return changes, modified_functions


def process_test_files(test_dir: Path) -> None:
    """
    Process all test files in the given directory.

    Args:
        test_dir: Path to the tests directory
    """
    total_changes = 0
    modified_files = []

    # Find all Python test files
    test_files = sorted(test_dir.rglob('*.py'))

    print(f"Processing {len(test_files)} test files...")
    print()

    for test_file in test_files:
        changes, functions = add_return_types_to_file(test_file)

        if changes > 0:
            relative_path = test_file.relative_to(test_dir.parent)
            print(f"✓ {relative_path}: {changes} function(s) updated")
            if functions and len(functions) <= 5:
                for func in functions:
                    print(f"  - {func}")
            total_changes += changes
            modified_files.append(relative_path)

    print()
    print("=" * 60)
    print(f"Summary:")
    print(f"  Files modified: {len(modified_files)}")
    print(f"  Functions annotated: {total_changes}")
    print("=" * 60)

    if modified_files:
        print()
        print("Modified files:")
        for file_path in modified_files:
            print(f"  - {file_path}")


def main() -> None:
    """Main entry point."""
    project_root = Path(__file__).parent.parent
    test_dir = project_root / 'tests'

    if not test_dir.exists():
        print(f"Error: Test directory not found: {test_dir}")
        return

    print("Adding -> None return type annotations to test functions")
    print("=" * 60)
    print()

    process_test_files(test_dir)

    print()
    print("Done! Next steps:")
    print("  1. Run: make mypy (verify error reduction)")
    print("  2. Run: make test (ensure tests still pass)")
    print("  3. Review changes: git diff")
    print("  4. Commit: git add tests/ && git commit -m 'fix: add return type annotations to test functions (1M-169)'")


if __name__ == '__main__':
    main()
