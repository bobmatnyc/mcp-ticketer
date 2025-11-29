#!/usr/bin/env python3
"""
Token optimization script for MCP tool documentation.

This script applies Phases 2-4 of the token optimization strategy:
- Phase 2: Replace verbose "Dictionary containing:" with standard response references
- Phase 3: Replace verbose parameter documentation with glossary references
- Phase 4: Remove redundant usage notes and error conditions

Token savings:
- Phase 2: ~3,780 tokens (27 tools x ~140 tokens/tool)
- Phase 3: ~2,040 tokens (68 parameters x ~30 tokens/param)
- Phase 4: ~2,850 tokens (targeted tool optimization)
"""

import re
from pathlib import Path

# Phase 2: Standard response patterns to replace
RESPONSE_PATTERNS = {
    # ConfigResponse pattern
    r'''Dictionary containing:\s*
        -\s*status:\s*"completed"\s*or\s*"error"\s*
        -\s*message:\s*Success\s*or\s*error\s*message\s*
        -\s*previous_\w+:.*?\(if\s*\w+\)\s*
        -\s*new_\w+:.*?\s*
        -\s*error:.*?\(if\s*failed\)''':
        'ConfigResponse with previous/new values and message',

    # StandardResponse pattern (various ticket operations)
    r'''Dictionary containing:\s*
        -\s*status:\s*"completed"\s*or\s*"error"\s*
        -\s*\w+:\s*.*?\s*
        -\s*adapter:\s*.*?\s*
        -\s*error:.*?\(if\s*failed\)''':
        'StandardResponse with [entity] and adapter info',

    # ListResponse pattern
    r'''Dictionary containing:\s*
        -\s*status:\s*"completed"\s*or\s*"error"\s*
        -\s*(tickets|labels|issues|epics):\s*List.*?\s*
        -\s*count:.*?\s*
        -\s*.*?filter.*?\s*
        -\s*error:.*?''':
        'ListResponse with [entities], count, filters',
}

# Phase 3: Parameter glossary references
PARAM_REPLACEMENTS = {
    r'ticket_id:\s*Unique\s*identifier\s*of\s*the\s*ticket.*?(?=\n\s{8}\w+:|$)':
        'ticket_id: See glossary',

    r'state:\s*(?:Filter\s*by\s*state\s*-\s*)?must\s*be\s*one\s*of:\s*open,\s*in_progress,.*?(?=\n\s{8}\w+:|$)':
        'state: Workflow state (see glossary for valid values)',

    r'priority:\s*(?:Filter\s*by\s*)?priority(?:\s*level)?.*?(?:low,\s*medium,\s*high,\s*critical).*?(?=\n\s{8}\w+:|$)':
        'priority: Priority level (see glossary for semantic matching)',

    r'tags:\s*List\s*of\s*tags.*?categorize.*?(?=\n\s{8}\w+:|$)':
        'tags: See glossary',

    r'assignee:\s*User\s*(?:ID\s*or\s*)?email.*?assign.*?(?=\n\s{8}\w+:|$)':
        'assignee: See glossary',
}

# Phase 4: Sections to remove (redundant with API reference)
REMOVE_SECTIONS = [
    r'Error Conditions:.*?(?=\n\s{4}(?:Usage|Example|\w+:)|""")',
    r'Usage Notes:.*?(?=\n\s{4}(?:Error|Example|\w+:)|""")',
]


def optimize_docstring(docstring: str, tool_name: str) -> str:
    """Optimize a single tool's docstring.

    Args:
        docstring: The docstring to optimize
        tool_name: Name of the tool (for context-aware optimization)

    Returns:
        Optimized docstring
    """
    original = docstring

    # Phase 2: Replace verbose "Dictionary containing:" patterns
    for pattern, replacement in RESPONSE_PATTERNS.items():
        if re.search(pattern, docstring, re.VERBOSE | re.MULTILINE):
            # Extract the entity type from the list in the pattern
            match = re.search(r'Dictionary containing:.*?(?=\n\n|\n    Example)',
                            docstring, re.DOTALL)
            if match:
                block = match.group(0)
                # Determine response type based on content
                if 'tickets' in block.lower() or 'list' in block.lower():
                    response_type = 'ListResponse'
                elif 'config' in tool_name or 'message' in block:
                    response_type = 'ConfigResponse'
                elif 'transition' in tool_name or 'confidence' in block:
                    response_type = 'TransitionResponse'
                else:
                    response_type = 'StandardResponse'

                # Replace the entire "Dictionary containing:" block
                docstring = docstring.replace(match.group(0),
                    f'Returns: {response_type} (see docs/mcp-api-reference.md)')

    # Phase 3: Replace verbose parameter docs with glossary references
    for pattern, replacement in PARAM_REPLACEMENTS.items():
        docstring = re.sub(pattern, replacement, docstring, flags=re.DOTALL)

    # Phase 4: Remove redundant sections
    for pattern in REMOVE_SECTIONS:
        docstring = re.sub(pattern, '', docstring, flags=re.DOTALL)

    # Clean up extra whitespace
    docstring = re.sub(r'\n\n\n+', '\n\n', docstring)

    # Add reference to API docs if not present
    if 'mcp-api-reference.md' not in docstring and docstring != original:
        # Find the best place to add the reference
        if 'Example:' in docstring:
            docstring = re.sub(
                r'(Example:.*?)(\n\n|\s*""")',
                r'\1\n\n    See: docs/mcp-api-reference.md for standard formats\2',
                docstring,
                flags=re.DOTALL
            )
        else:
            # Add before closing """
            docstring = re.sub(
                r'(\s*""")',
                r'\n    See: docs/mcp-api-reference.md for standard formats\1',
                docstring
            )

    return docstring


def optimize_file(filepath: Path) -> tuple[int, int]:
    """Optimize all tool docstrings in a file.

    Args:
        filepath: Path to the Python file

    Returns:
        Tuple of (original_length, new_length) in characters
    """
    content = filepath.read_text()
    original_length = len(content)

    # Find all @mcp.tool() decorated functions
    pattern = r'(@mcp\.tool\(\))\s*async\s*def\s*(\w+)\(.*?\):\s*"""(.*?)"""'

    def replace_docstring(match):
        decorator = match.group(1)
        func_name = match.group(2)
        docstring = match.group(3)

        optimized = optimize_docstring(docstring, func_name)

        return f'{decorator}\nasync def {func_name}({match.group(0).split("(", 1)[1].split("):", 1)[0]}):\n    """{optimized}"""'

    new_content = re.sub(pattern, replace_docstring, content, flags=re.DOTALL)

    filepath.write_text(new_content)

    return (original_length, len(new_content))


def main():
    """Run optimization on all tool files."""
    tools_dir = Path('/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools')

    total_original = 0
    total_new = 0
    files_optimized = 0

    print("MCP Tool Documentation Optimization")
    print("=" * 60)

    for tool_file in sorted(tools_dir.glob('*_tools.py')):
        original, new = optimize_file(tool_file)

        if original != new:
            savings = original - new
            pct = (savings / original) * 100

            print(f"\n{tool_file.name}:")
            print(f"  Original: {original:,} chars")
            print(f"  Optimized: {new:,} chars")
            print(f"  Saved: {savings:,} chars ({pct:.1f}%)")

            total_original += original
            total_new += new
            files_optimized += 1

    if files_optimized > 0:
        total_savings = total_original - total_new
        total_pct = (total_savings / total_original) * 100

        # Estimate token savings (rough: 1 token ≈ 4 characters)
        token_savings = total_savings // 4

        print("\n" + "=" * 60)
        print("TOTAL OPTIMIZATION RESULTS:")
        print(f"  Files optimized: {files_optimized}")
        print(f"  Original size: {total_original:,} chars")
        print(f"  Optimized size: {total_new:,} chars")
        print(f"  Total saved: {total_savings:,} chars ({total_pct:.1f}%)")
        print(f"  Estimated token savings: ~{token_savings:,} tokens")
        print("=" * 60)
    else:
        print("\nNo changes needed - files already optimized!")


if __name__ == '__main__':
    main()
