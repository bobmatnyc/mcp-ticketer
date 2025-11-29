#!/usr/bin/env python3
"""Bulk optimize remaining verbose JSON examples."""

import re
from pathlib import Path


def extract_function_call(lines, start_idx, end_idx):
    """Extract the function call from verbose example block."""
    for line in lines[start_idx:end_idx]:
        if '>>> ' in line and '(' in line:
            # Extract function name and call
            match = re.search(r'(\w+)\([^)]*\)', line)
            if match:
                return match.group(0)
    return None


def optimize_file(filepath):
    """Optimize all verbose examples in a file."""
    content = filepath.read_text()
    lines = content.split('\n')
    result_lines = []
    i = 0
    optimized_count = 0

    while i < len(lines):
        line = lines[i]

        # Check for verbose example pattern
        if '>>> print(result)' in line:
            # Find Example: start (look back up to 20 lines)
            example_start = None
            for j in range(i-1, max(0, i-20), -1):
                if lines[j].strip().startswith('Example:'):
                    example_start = j
                    break

            if example_start is None:
                result_lines.append(line)
                i += 1
                continue

            # Find JSON block end
            json_end = None
            brace_count = 0
            started = False
            for j in range(i+1, min(len(lines), i+50)):
                stripped = lines[j].strip()
                if '{' in stripped:
                    started = True
                if started:
                    brace_count += stripped.count('{') - stripped.count('}')
                    if brace_count == 0 and '}' in stripped:
                        json_end = j
                        break

            if json_end:
                # Extract function call
                func_call = extract_function_call(lines, example_start, i)

                # Get indent
                indent = len(lines[example_start]) - len(lines[example_start].lstrip())

                # Create concise replacement
                if func_call:
                    concise = ' ' * indent + f'Example: `{func_call}` → {{"status": "completed", ...}}'
                else:
                    concise = ' ' * indent + 'Example: See Returns section'

                # Add everything before example block
                # Skip the verbose block, add concise version
                result_lines.append(concise)
                optimized_count += 1

                # Skip to after JSON block
                i = json_end + 1
                continue

        result_lines.append(line)
        i += 1

    # Write optimized content
    filepath.write_text('\n'.join(result_lines))

    return optimized_count


def main():
    """Optimize remaining files."""
    tools_dir = Path('src/mcp_ticketer/mcp/server/tools')

    files = [
        'config_tools.py',
        'label_tools.py',
        'project_update_tools.py',
    ]

    total_optimized = 0
    for filename in files:
        filepath = tools_dir / filename
        if not filepath.exists():
            print(f"SKIP: {filename}")
            continue

        before_size = filepath.stat().st_size
        count = optimize_file(filepath)
        after_size = filepath.stat().st_size

        saved = before_size - after_size
        total_optimized += count

        print(f"{filename}: {count} examples optimized, {saved:,} bytes saved (~{saved//4:,} tokens)")

    print(f"\nTotal: {total_optimized} examples optimized")


if __name__ == '__main__':
    main()
