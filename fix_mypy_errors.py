#!/usr/bin/env python3
"""Script to systematically fix mypy type errors."""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


def get_mypy_errors() -> List[str]:
    """Run mypy and get all errors."""
    result = subprocess.run(
        ["mypy", "src/", "--config-file", "pyproject.toml", "--no-error-summary"],
        capture_output=True,
        text=True,
    )
    return [
        line
        for line in result.stdout.strip().split("\n")
        if line.startswith("src/")
    ]


def parse_error(line: str) -> Tuple[str, int, str, str] | None:
    """Parse mypy error line into components."""
    match = re.match(r"^(src/[^:]+):(\d+): error: (.+?) \[([^\]]+)\]", line)
    if match:
        return match.group(1), int(match.group(2)), match.group(3), match.group(4)
    return None


def main():
    """Main function to fix errors."""
    errors = get_mypy_errors()
    print(f"Total errors: {len(errors)}")

    # Group errors by type
    by_type: Dict[str, List[Tuple[str, int, str]]] = {}
    for error_line in errors:
        parsed = parse_error(error_line)
        if parsed:
            file_path, line_num, message, error_type = parsed
            if error_type not in by_type:
                by_type[error_type] = []
            by_type[error_type].append((file_path, line_num, message))

    # Print error summary
    print("\nError breakdown by type:")
    for error_type, instances in sorted(by_type.items(), key=lambda x: -len(x[1])):
        print(f"  {error_type}: {len(instances)}")

    # Show files with most errors
    by_file: Dict[str, int] = {}
    for error_line in errors:
        parsed = parse_error(error_line)
        if parsed:
            file_path = parsed[0]
            by_file[file_path] = by_file.get(file_path, 0) + 1

    print("\nFiles with most errors:")
    for file_path, count in sorted(by_file.items(), key=lambda x: -x[1])[:15]:
        print(f"  {count:3d} {file_path}")


if __name__ == "__main__":
    main()
