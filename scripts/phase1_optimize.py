#!/usr/bin/env python3
"""Phase 1 MCP Profile Token Optimization - Remove verbose JSON examples."""

import re
from pathlib import Path


def optimize_docstring_examples(content: str) -> tuple[str, int]:
    """Optimize verbose JSON examples in docstrings.

    Returns:
        (optimized_content, examples_removed)
    """
    lines = content.split('\n')
    result = []
    i = 0
    examples_removed = 0

    while i < len(lines):
        line = lines[i]

        # Check if this is start of verbose example pattern
        if '>>> print(result)' in line:
            # Find the start of the Example: block
            example_start = i
            for j in range(i-1, max(0, i-20), -1):
                if 'Example:' in lines[j] and lines[j].strip().startswith('Example:'):
                    example_start = j
                    break

            # Find the JSON block end (matching closing brace)
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

            if json_end and example_start != i:
                # Extract function call from the example
                func_call = ''
                for j in range(example_start+1, i):
                    if '>>>' in lines[j] and 'result' in lines[j]:
                        match = re.search(r'(\w+\([^)]*\))', lines[j])
                        if match:
                            func_call = match.group(1)
                            break

                # Create concise replacement
                indent = len(lines[example_start]) - len(lines[example_start].lstrip())
                if func_call:
                    concise = ' ' * indent + f'Example: `{func_call}` → {{"status": "completed", ...}}'
                else:
                    concise = ' ' * indent + 'Example: See Returns section for response structure'

                # Add everything up to example_start
                if i > example_start + 1:
                    # Preserve any content between Example: and >>>
                    preamble = []
                    for j in range(example_start+1, i):
                        if lines[j].strip() and not lines[j].strip().startswith('>>>'):
                            preamble.append(lines[j])

                    if preamble:
                        result.extend(result[:(example_start - len(result))])
                        result.append(lines[example_start])
                        result.extend(preamble)
                        result.append(concise)
                    else:
                        result.extend(result[:(example_start - len(result))])
                        result.append(concise)
                else:
                    result.extend(result[:(example_start - len(result))])
                    result.append(concise)

                examples_removed += 1
                i = json_end + 1
                continue

        result.append(line)
        i += 1

    return '\n'.join(result), examples_removed


def optimize_file(filepath: Path) -> dict:
    """Optimize a single file."""
    content = filepath.read_text()
    optimized, removed = optimize_docstring_examples(content)

    # Calculate token savings (rough estimate: 4 chars = 1 token)
    before_tokens = len(content) // 4
    after_tokens = len(optimized) // 4
    saved = before_tokens - after_tokens

    filepath.write_text(optimized)

    return {
        'file': filepath.name,
        'examples_removed': removed,
        'before_tokens': before_tokens,
        'after_tokens': after_tokens,
        'tokens_saved': saved,
        'reduction_pct': (saved / before_tokens * 100) if before_tokens > 0 else 0
    }


def main():
    """Run Phase 1 optimization."""
    tools_dir = Path('src/mcp_ticketer/mcp/server/tools')
    files = [
        'config_tools.py',
        'label_tools.py',
        'user_ticket_tools.py',
        'project_update_tools.py',
    ]

    print("Phase 1: MCP Profile Token Optimization")
    print("=" * 80)

    total_removed = 0
    total_saved = 0

    for filename in files:
        filepath = tools_dir / filename
        if not filepath.exists():
            continue

        result = optimize_file(filepath)
        total_removed += result['examples_removed']
        total_saved += result['tokens_saved']

        print(f"\n{result['file']}:")
        print(f"  Examples optimized: {result['examples_removed']}")
        print(f"  Tokens saved: {result['tokens_saved']:,} ({result['reduction_pct']:.1f}%)")

    print(f"\n{'=' * 80}")
    print(f"TOTAL:")
    print(f"  Examples optimized: {total_removed}")
    print(f"  Estimated tokens saved: {total_saved:,}")
    print(f"\nTarget: ~40,000 tokens (Research estimate)")
    print(f"Achievement: {(total_saved / 40_000 * 100):.1f}% of target")


if __name__ == '__main__':
    main()
