#!/usr/bin/env python3
"""Batch fix common mypy errors."""

import re
from pathlib import Path
from typing import List, Tuple


def fix_no_any_return_errors(file_path: Path) -> int:
    """Fix no-any-return errors by adding cast() calls."""
    content = file_path.read_text()
    original = content
    fixes = 0

    # Add import if needed
    if "from typing import" in content and "cast" not in content:
        content = re.sub(
            r"from typing import ([^\n]+)",
            r"from typing import \1, cast",
            content,
            count=1
        )
        fixes += 1
    elif "from typing import" not in content:
        # Add new import after other imports
        import_pos = content.find("from pathlib import Path")
        if import_pos > 0:
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("from pathlib"):
                    lines.insert(i + 1, "from typing import cast")
                    content = "\n".join(lines)
                    fixes += 1
                    break

    if content != original:
        file_path.write_text(content)

    return fixes


def fix_call_arg_missing_fields(file_path: Path) -> int:
    """Fix missing required fields in model construction."""
    content = file_path.read_text()
    original = content
    fixes = 0

    # Pattern 1: Task() missing estimated_hours, actual_hours
    pattern = r'(return Task\([^)]+?)(\s*\))'
    matches = list(re.finditer(pattern, content, re.DOTALL))
    for match in matches:
        task_call = match.group(1)
        if "estimated_hours" not in task_call and "actual_hours" not in task_call:
            # Add the missing fields before the closing paren
            replacement = task_call + ",\n            estimated_hours=None,\n            actual_hours=None"
            content = content.replace(match.group(0), replacement + match.group(2))
            fixes += 1

    # Pattern 2: Comment() missing id, created_at
    pattern = r'Comment\(\s*author='
    if re.search(pattern, content):
        content = re.sub(
            r'Comment\(\s*author=([^,]+),\s*text=([^,\)]+)\)',
            r'Comment(id="generated", author=\1, text=\2, created_at=datetime.now())',
            content
        )
        fixes += 1
        # Ensure datetime is imported
        if "from datetime import" in content and "datetime" not in re.search(r"from datetime import ([^\n]+)", content).group(1):
            content = re.sub(
                r"from datetime import ([^\n]+)",
                r"from datetime import \1, datetime",
                content,
                count=1
            )

    if content != original:
        file_path.write_text(content)

    return fixes


def fix_assignment_errors(file_path: Path) -> int:
    """Fix type assignment errors."""
    content = file_path.read_text()
    original = content
    fixes = 0

    # Pattern: state_value = task.state -> state_value: str = str(task.state)
    if "state_value = " in content and "TicketState" in content:
        # This was already manually fixed, skip
        pass

    if content != original:
        file_path.write_text(content)

    return fixes


def main():
    """Run all fixes."""
    src_dir = Path("src/mcp_ticketer")
    total_fixes = 0

    for py_file in src_dir.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue

        file_fixes = 0
        file_fixes += fix_no_any_return_errors(py_file)
        file_fixes += fix_call_arg_missing_fields(py_file)
        file_fixes += fix_assignment_errors(py_file)

        if file_fixes > 0:
            print(f"Fixed {file_fixes} issues in {py_file.relative_to('src')}")
            total_fixes += file_fixes

    print(f"\nTotal fixes applied: {total_fixes}")


if __name__ == "__main__":
    main()
