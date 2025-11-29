#!/usr/bin/env python3
"""
Optimize MCP tool docstrings by removing verbose JSON examples.

Phase 1: Remove verbose JSON response examples (29 occurrences across 4 files)
Target: ~40,000 token savings

This script:
1. Identifies verbose example blocks (>>> print(result) followed by multi-line JSON)
2. Replaces them with concise one-line examples
3. Preserves essential information for LLM understanding
4. Reports token savings
"""

import re
from pathlib import Path
from typing import Tuple


def estimate_tokens(text: str) -> int:
    """Estimate token count (rough approximation: 4 chars = 1 token)."""
    return len(text) // 4


def extract_example_block(lines: list[str], start_idx: int) -> Tuple[int, str]:
    """Extract the verbose example block starting at start_idx.

    Returns:
        (end_index, extracted_block)
    """
    # Find the start of the JSON block (line with {)
    json_start = None
    for i in range(start_idx, len(lines)):
        if lines[i].strip() == "{":
            json_start = i
            break

    if json_start is None:
        return start_idx, ""

    # Find the end of the JSON block (matching })
    brace_count = 0
    json_end = None
    for i in range(json_start, len(lines)):
        line = lines[i].strip()
        brace_count += line.count("{") - line.count("}")
        if brace_count == 0 and "}" in line:
            json_end = i
            break

    if json_end is None:
        return start_idx, ""

    # Extract the full block (from >>> to end of JSON)
    block = "\n".join(lines[start_idx:json_end + 1])
    return json_end + 1, block


def extract_function_name(docstring_lines: list[str], example_idx: int) -> str:
    """Extract function/tool name from the example call."""
    # Look backwards from example_idx to find the @mcp.tool() decorator
    for i in range(example_idx, max(0, example_idx - 100), -1):
        line = docstring_lines[i].strip()
        if line.startswith("async def ") or line.startswith("def "):
            # Extract function name
            func_match = re.match(r"(?:async )?def (\w+)", line)
            if func_match:
                return func_match.group(1)
    return "tool"


def create_concise_example(verbose_block: str, function_name: str) -> str:
    """Create a concise one-line example from verbose block.

    Pattern: Example: `function_name("arg")` → {"status": "completed", ...}
    """
    # Extract the function call from >>> line
    call_match = re.search(r'>>> (?:result = (?:await )?)?(\w+\([^)]*\))', verbose_block)
    if not call_match:
        return f'Example: `{function_name}(...)` → {{"status": "completed", ...}}'

    function_call = call_match.group(1)

    # Create concise version
    return f'Example: `{function_call}` → {{"status": "completed", ...}}'


def optimize_docstring(content: str, file_path: Path) -> Tuple[str, int, int]:
    """Optimize docstrings in a file by removing verbose JSON examples.

    Returns:
        (optimized_content, examples_removed, tokens_saved)
    """
    lines = content.split("\n")
    optimized_lines = []
    examples_removed = 0
    tokens_saved = 0
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this line contains verbose example pattern
        if ">>> print(result)" in line:
            # Extract the verbose block
            end_idx, verbose_block = extract_example_block(lines, i)

            if verbose_block:
                # Extract function name for context
                function_name = extract_function_name(lines, i)

                # Create concise replacement
                indent = len(line) - len(line.lstrip())
                concise = create_concise_example(verbose_block, function_name)
                concise_line = " " * indent + concise

                # Calculate savings
                before_tokens = estimate_tokens(verbose_block)
                after_tokens = estimate_tokens(concise)
                tokens_saved += (before_tokens - after_tokens)
                examples_removed += 1

                # Replace verbose block with concise version
                optimized_lines.append(concise_line)
                i = end_idx
                continue

        # Keep line as-is
        optimized_lines.append(line)
        i += 1

    return "\n".join(optimized_lines), examples_removed, tokens_saved


def optimize_file(file_path: Path) -> dict:
    """Optimize a single tool file.

    Returns:
        Dictionary with optimization statistics
    """
    print(f"\n{'='*80}")
    print(f"Optimizing: {file_path.name}")
    print(f"{'='*80}")

    # Read original content
    content = file_path.read_text()
    original_tokens = estimate_tokens(content)

    # Optimize
    optimized_content, examples_removed, tokens_saved = optimize_docstring(content, file_path)
    optimized_tokens = estimate_tokens(optimized_content)

    # Write optimized content
    file_path.write_text(optimized_content)

    # Report results
    result = {
        "file": file_path.name,
        "examples_removed": examples_removed,
        "original_tokens": original_tokens,
        "optimized_tokens": optimized_tokens,
        "tokens_saved": tokens_saved,
        "reduction_pct": (tokens_saved / original_tokens * 100) if original_tokens > 0 else 0,
    }

    print(f"  Examples removed: {examples_removed}")
    print(f"  Original tokens:  {original_tokens:,}")
    print(f"  Optimized tokens: {optimized_tokens:,}")
    print(f"  Tokens saved:     {tokens_saved:,} ({result['reduction_pct']:.1f}% reduction)")

    return result


def main():
    """Run Phase 1 optimization on all tool files."""
    # Target files with verbose examples (from analysis)
    tools_dir = Path("src/mcp_ticketer/mcp/server/tools")
    target_files = [
        "config_tools.py",      # 15 examples
        "label_tools.py",       # 7 examples
        "user_ticket_tools.py", # 4 examples
        "project_update_tools.py",  # 3 examples
    ]

    total_stats = {
        "files_processed": 0,
        "examples_removed": 0,
        "tokens_saved": 0,
        "original_tokens": 0,
        "optimized_tokens": 0,
    }

    results = []

    for filename in target_files:
        file_path = tools_dir / filename
        if not file_path.exists():
            print(f"WARNING: {filename} not found, skipping")
            continue

        result = optimize_file(file_path)
        results.append(result)

        total_stats["files_processed"] += 1
        total_stats["examples_removed"] += result["examples_removed"]
        total_stats["tokens_saved"] += result["tokens_saved"]
        total_stats["original_tokens"] += result["original_tokens"]
        total_stats["optimized_tokens"] += result["optimized_tokens"]

    # Print summary
    print(f"\n{'='*80}")
    print("PHASE 1 OPTIMIZATION SUMMARY")
    print(f"{'='*80}")
    print(f"Files processed:        {total_stats['files_processed']}")
    print(f"Verbose examples removed: {total_stats['examples_removed']}")
    print(f"Total original tokens:  {total_stats['original_tokens']:,}")
    print(f"Total optimized tokens: {total_stats['optimized_tokens']:,}")
    print(f"Total tokens saved:     {total_stats['tokens_saved']:,}")

    if total_stats["original_tokens"] > 0:
        reduction_pct = (total_stats["tokens_saved"] / total_stats["original_tokens"] * 100)
        print(f"Overall reduction:      {reduction_pct:.1f}%")

    # Compare to research target
    research_target = 40_000
    print(f"\nResearch target:        {research_target:,} tokens")
    print(f"Achievement:            {(total_stats['tokens_saved'] / research_target * 100):.1f}% of target")

    # Print per-file breakdown
    print(f"\n{'='*80}")
    print("PER-FILE BREAKDOWN")
    print(f"{'='*80}")
    print(f"{'File':<30} {'Examples':<10} {'Tokens Saved':<15} {'Reduction'}")
    print("-" * 80)
    for result in results:
        print(f"{result['file']:<30} {result['examples_removed']:<10} {result['tokens_saved']:<15,} {result['reduction_pct']:.1f}%")


if __name__ == "__main__":
    main()
