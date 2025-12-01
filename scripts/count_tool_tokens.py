#!/usr/bin/env python3
"""Calculate token counts for MCP tools.

This script estimates the token count for MCP tool definitions,
including docstrings, parameters, and schema information.
"""

import inspect


def estimate_tokens(text: str) -> int:
    """Estimate token count (rough approximation: 1 token ~= 4 characters)."""
    return len(text) // 4


def get_tool_definition_size(func) -> dict:
    """Get full tool definition including docstring, signature, and parameters."""
    # Get docstring
    docstring = inspect.getdoc(func) or ""

    # Get signature
    sig = inspect.signature(func)
    signature_str = f"{func.__name__}{sig}"

    # Get source (for full context)
    try:
        source = inspect.getsource(func)
        # Only count the decorator and definition, not implementation
        source_lines = source.split('\n')
        definition_lines = []
        in_docstring = False
        docstring_delim_count = 0

        for line in source_lines:
            if '"""' in line or "'''" in line:
                docstring_delim_count += 1
                in_docstring = not in_docstring
                definition_lines.append(line)
                if docstring_delim_count == 2:
                    break
            elif in_docstring or '@' in line or 'def ' in line or 'async def' in line:
                definition_lines.append(line)

        definition = '\n'.join(definition_lines)
    except:
        definition = f"{signature_str}\n{docstring}"

    return {
        "name": func.__name__,
        "docstring": docstring,
        "signature": signature_str,
        "definition": definition,
        "docstring_tokens": estimate_tokens(docstring),
        "signature_tokens": estimate_tokens(signature_str),
        "full_tokens": estimate_tokens(definition),
    }


if __name__ == "__main__":
    from mcp_ticketer.mcp.server.tools.session_tools import (
        get_session_info,
        user_session,
    )
    from mcp_ticketer.mcp.server.tools.user_ticket_tools import get_my_tickets

    print("=" * 70)
    print("MCP TOOL TOKEN ANALYSIS - Phase 2 Sprint 2.2")
    print("=" * 70)
    print()

    # Analyze original tools
    print("BEFORE CONSOLIDATION:")
    print("-" * 70)

    my_tickets = get_tool_definition_size(get_my_tickets)
    print(f"get_my_tickets:")
    print(f"  Docstring: {my_tickets['docstring_tokens']} tokens")
    print(f"  Signature: {my_tickets['signature_tokens']} tokens")
    print(f"  Full definition: {my_tickets['full_tokens']} tokens")
    print()

    session_info = get_tool_definition_size(get_session_info)
    print(f"get_session_info:")
    print(f"  Docstring: {session_info['docstring_tokens']} tokens")
    print(f"  Signature: {session_info['signature_tokens']} tokens")
    print(f"  Full definition: {session_info['full_tokens']} tokens")
    print()

    original_total = my_tickets['full_tokens'] + session_info['full_tokens']
    print(f"TOTAL (2 tools): {original_total} tokens")
    print()

    # Analyze unified tool
    print("AFTER CONSOLIDATION:")
    print("-" * 70)

    unified = get_tool_definition_size(user_session)
    print(f"user_session (unified):")
    print(f"  Docstring: {unified['docstring_tokens']} tokens")
    print(f"  Signature: {unified['signature_tokens']} tokens")
    print(f"  Full definition: {unified['full_tokens']} tokens")
    print()

    # In v2.0.0, the deprecated tools will be removed
    print("NOTE: Deprecated tools (get_my_tickets, get_session_info) will be")
    print("      removed in v2.0.0, leaving only the unified user_session tool.")
    print()

    consolidated_total = unified['full_tokens']
    print(f"TOTAL (1 unified tool): {consolidated_total} tokens")
    print()

    # Calculate savings
    print("TOKEN SAVINGS:")
    print("-" * 70)
    savings = original_total - consolidated_total
    percentage = (savings / original_total * 100) if original_total > 0 else 0

    print(f"Original (2 tools):     {original_total:4d} tokens")
    print(f"Consolidated (1 tool):  {consolidated_total:4d} tokens")
    print(f"Savings:                {savings:4d} tokens ({percentage:.1f}% reduction)")
    print()

    # Show practical impact
    print("PRACTICAL IMPACT:")
    print("-" * 70)
    print(f"• Reduces tool count by 50% (2 → 1 tools)")
    print(f"• Saves ~{savings} tokens per tool discovery/listing")
    print(f"• Unified interface improves discoverability")
    print(f"• Backward compatible until v2.0.0")
    print()
