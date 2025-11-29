#!/usr/bin/env python3
"""Manual optimization script for remaining files with systematic pattern matching."""

import re
from pathlib import Path


def find_and_replace_verbose_examples(filepath: Path) -> int:
    """Find and replace verbose JSON examples with concise ones.

    Returns number of examples replaced.
    """
    content = filepath.read_text()
    original_content = content
    replacements = 0

    # Pattern: >>> print(result) followed by multi-line JSON
    # We'll use a regex to find and replace these blocks
    pattern = r'(\n\s+Example:.*?\n.*?)(\n\s+>>> .*?print\(result\).*?\n\s+\{.*?\n(?:\s+.*?\n)*?\s+\})'

    def replace_verbose_block(match):
        nonlocal replacements
        preamble = match.group(1)
        verbose_block = match.group(2)

        # Extract function name from verbose block
        func_match = re.search(r'>>> (?:result = (?:await )?)?(\w+)\(', verbose_block)
        if func_match:
            func_name = func_match.group(1)
            # Get indent level
            indent_match = re.match(r'(\s+)', preamble.split('\n')[-1] if '\n' in preamble else preamble)
            indent = indent_match.group(1) if indent_match else '    '

            # Create concise replacement
            concise = f'\n{indent}Example: `{func_name}(...)` → {{"status": "completed", ...}}'
            replacements += 1
            return preamble.split('\n')[0] + '\n' + concise
        return match.group(0)

    # Apply replacements
    content = re.sub(pattern, replace_verbose_block, content, flags=re.DOTALL)

    if content != original_content:
        filepath.write_text(content)

    return replacements


def main():
    tools_dir = Path('src/mcp_ticketer/mcp/server/tools')

    files_to_process = [
        ('config_tools.py', 15),
        ('label_tools.py', 7),
        ('project_update_tools.py', 3),
    ]

    print("Manual Optimization Script")
    print("=" * 80)

    for filename, expected_count in files_to_process:
        filepath = tools_dir / filename
        if not filepath.exists():
            print(f"SKIP: {filename} not found")
            continue

        before_size = filepath.stat().st_size
        replacements = find_and_replace_verbose_examples(filepath)
        after_size = filepath.stat().st_size

        saved = before_size - after_size
        saved_tokens = saved // 4

        print(f"\n{filename}:")
        print(f"  Expected examples: {expected_count}")
        print(f"  Replacements made: {replacements}")
        print(f"  Bytes saved: {saved:,}")
        print(f"  Est. tokens saved: {saved_tokens:,}")


if __name__ == '__main__':
    main()
