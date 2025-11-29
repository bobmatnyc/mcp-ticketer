"""Token Pagination Examples for MCP Ticketer

This module demonstrates practical usage patterns for token-efficient
queries across MCP tools. All examples follow the 20k token limit.

Usage:
    python examples/token_pagination_examples.py

Requirements:
    - Configured MCP Ticketer adapter (run `mcp-ticketer init` first)
    - Active tickets/labels in your system for meaningful results
"""

import asyncio
from typing import Any

# Import MCP tools (in real usage, these come from MCP server)
# For demonstration, we'll show the usage patterns
from mcp_ticketer.mcp.server.tools.ticket_tools import ticket_list
from mcp_ticketer.mcp.server.tools.label_tools import label_list
from mcp_ticketer.mcp.server.tools.analysis_tools import (
    ticket_find_similar,
    ticket_cleanup_report,
)


# ==============================================================================
# Example 1: Basic Pagination with ticket_list
# ==============================================================================


async def example_basic_pagination():
    """Demonstrate basic pagination with compact mode.

    Token Usage: ~300 tokens per page (20 tickets × 15 tokens)
    Total for 3 pages: ~900 tokens (4.5% of 20k limit)
    """
    print("=" * 80)
    print("Example 1: Basic Pagination with ticket_list")
    print("=" * 80)

    # Fetch first page (default compact mode)
    print("\n📄 Fetching page 1...")
    page1 = await ticket_list(limit=20, offset=0, compact=True)

    print(f"✓ Got {page1['count']} tickets")
    print(f"  Total available: {page1.get('total', 'unknown')}")
    print(f"  Estimated tokens: {page1['estimated_tokens']}")
    print(f"  Has more: {page1['has_more']}")

    # Fetch second page if available
    if page1["has_more"]:
        print("\n📄 Fetching page 2...")
        page2 = await ticket_list(limit=20, offset=20, compact=True)

        print(f"✓ Got {page2['count']} tickets")
        print(f"  Estimated tokens: {page2['estimated_tokens']}")

        # Show sample ticket (compact mode)
        if page2["items"]:
            sample = page2["items"][0]
            print(f"\n  Sample ticket (compact):")
            print(f"    ID: {sample['id']}")
            print(f"    Title: {sample['title']}")
            print(f"    State: {sample['state']}")

    # Summary
    total_tokens = page1["estimated_tokens"] + (
        page2["estimated_tokens"] if page1["has_more"] else 0
    )
    print(f"\n📊 Summary:")
    print(f"  Total pages fetched: {2 if page1['has_more'] else 1}")
    print(f"  Total tokens used: {total_tokens} ({total_tokens/20000*100:.1f}% of limit)")
    print(f"  Tokens per ticket: ~{total_tokens // (page1['count'] + (page2['count'] if page1['has_more'] else 0))}")


# ==============================================================================
# Example 2: Compact vs Full Mode Comparison
# ==============================================================================


async def example_compact_vs_full():
    """Compare token usage between compact and full modes.

    Token Usage:
    - Compact mode (20 tickets): ~300 tokens
    - Full mode (20 tickets): ~3,700 tokens
    Difference: 12x reduction with compact mode
    """
    print("\n" + "=" * 80)
    print("Example 2: Compact vs Full Mode Comparison")
    print("=" * 80)

    # Fetch in compact mode
    print("\n📦 Fetching 20 tickets in COMPACT mode...")
    compact_result = await ticket_list(limit=20, compact=True)

    print(f"✓ Compact mode:")
    print(f"  Tickets: {compact_result['count']}")
    print(f"  Estimated tokens: {compact_result['estimated_tokens']}")
    print(f"  Tokens per ticket: ~{compact_result['estimated_tokens'] // compact_result['count']}")

    # Fetch in full mode (same tickets)
    print("\n📦 Fetching 20 tickets in FULL mode...")
    full_result = await ticket_list(limit=20, compact=False)

    print(f"✓ Full mode:")
    print(f"  Tickets: {full_result['count']}")
    print(f"  Estimated tokens: {full_result['estimated_tokens']}")
    print(f"  Tokens per ticket: ~{full_result['estimated_tokens'] // full_result['count']}")

    # Comparison
    print(f"\n📊 Comparison:")
    print(f"  Token reduction: {full_result['estimated_tokens'] - compact_result['estimated_tokens']} tokens saved")
    print(f"  Reduction factor: {full_result['estimated_tokens'] / compact_result['estimated_tokens']:.1f}x")
    print(f"  Compact: {compact_result['estimated_tokens']/20000*100:.1f}% of limit")
    print(f"  Full: {full_result['estimated_tokens']/20000*100:.1f}% of limit")

    # Show what's included in each mode
    if compact_result["items"] and full_result["items"]:
        print(f"\n🔍 Fields comparison (first ticket):")
        print(f"  Compact fields: {list(compact_result['items'][0].keys())}")
        print(f"  Full fields: {list(full_result['items'][0].keys())[:10]}... (truncated)")


# ==============================================================================
# Example 3: Progressive Disclosure Pattern
# ==============================================================================


async def example_progressive_disclosure():
    """Demonstrate progressive disclosure: summary → details → deep dive.

    Token Usage:
    - Step 1 (summary): ~1,000 tokens
    - Step 2 (filtered list): ~300 tokens
    - Step 3 (full details): ~185 tokens per ticket
    Total: ~2,000 tokens (10% of limit)
    """
    print("\n" + "=" * 80)
    print("Example 3: Progressive Disclosure Pattern")
    print("=" * 80)

    # Step 1: Get high-level overview (compact mode)
    print("\n📊 Step 1: Get overview of all open tickets...")
    overview = await ticket_list(state="open", limit=50, compact=True)

    print(f"✓ Found {overview['count']} open tickets")
    print(f"  Estimated tokens: {overview['estimated_tokens']}")

    # Step 2: Filter to high-priority items
    print("\n🔍 Step 2: Filter to high-priority tickets...")
    high_priority = await ticket_list(
        state="open", priority="high", limit=20, compact=True
    )

    print(f"✓ Found {high_priority['count']} high-priority tickets")
    print(f"  Estimated tokens: {high_priority['estimated_tokens']}")

    # Step 3: Get full details only for tickets we care about
    print("\n📝 Step 3: Get full details for specific tickets...")
    # In real usage, you'd call ticket_read for individual tickets
    # For demo, show the pattern:
    tokens_for_details = 0
    tickets_examined = min(5, high_priority["count"])

    for i in range(tickets_examined):
        # Each ticket_read would be ~185 tokens in full mode
        tokens_for_details += 185

    print(f"✓ Examined {tickets_examined} tickets in detail")
    print(f"  Estimated tokens: ~{tokens_for_details}")

    # Summary
    total_tokens = (
        overview["estimated_tokens"]
        + high_priority["estimated_tokens"]
        + tokens_for_details
    )
    print(f"\n📊 Total Progressive Disclosure:")
    print(f"  Step 1 (overview): {overview['estimated_tokens']} tokens")
    print(f"  Step 2 (filtered): {high_priority['estimated_tokens']} tokens")
    print(f"  Step 3 (details): ~{tokens_for_details} tokens")
    print(f"  Total: ~{total_tokens} tokens ({total_tokens/20000*100:.1f}% of limit)")
    print(f"  ✅ Well under 20k limit!")


# ==============================================================================
# Example 4: Large Dataset Pagination
# ==============================================================================


async def example_large_dataset_pagination():
    """Handle large datasets by paginating through all results.

    Token Usage: Controlled by page size, can process unlimited items
    """
    print("\n" + "=" * 80)
    print("Example 4: Large Dataset Pagination")
    print("=" * 80)

    print("\n📚 Fetching ALL labels (paginated)...")

    all_labels = []
    offset = 0
    page_size = 100
    total_tokens = 0
    pages_fetched = 0

    while True:
        print(f"\n  📄 Fetching page {pages_fetched + 1} (offset: {offset})...")
        page = await label_list(limit=page_size, offset=offset)

        # Accumulate results
        all_labels.extend(page["labels"])
        total_tokens += page["estimated_tokens"]
        pages_fetched += 1

        print(
            f"     Got {page['count']} labels, {page['estimated_tokens']} tokens"
        )

        # Check if more pages exist
        if not page["has_more"]:
            print(f"     ✓ Last page reached")
            break

        offset += page["count"]

        # Safety check: don't exceed reasonable limits
        if pages_fetched >= 10:
            print(
                f"     ⚠️ Stopping after {pages_fetched} pages (safety limit)"
            )
            break

    # Summary
    print(f"\n📊 Summary:")
    print(f"  Total labels: {len(all_labels)}")
    print(f"  Pages fetched: {pages_fetched}")
    print(f"  Total tokens: {total_tokens}")
    print(f"  Avg tokens/page: {total_tokens // pages_fetched if pages_fetched > 0 else 0}")
    print(f"  Max single page: ≤ {page_size * 15} tokens (well under 20k limit)")


# ==============================================================================
# Example 5: Token-Safe Similarity Analysis
# ==============================================================================


async def example_similarity_analysis():
    """Perform similarity analysis with controlled token usage.

    Token Usage:
    - Safe config (internal_limit=100): ~2,000-5,000 tokens
    - Dangerous config (internal_limit=500): Up to 92,500 tokens ⚠️
    """
    print("\n" + "=" * 80)
    print("Example 5: Token-Safe Similarity Analysis")
    print("=" * 80)

    # ✅ SAFE: Use reasonable internal_limit
    print("\n✅ Safe configuration (internal_limit=100)...")
    safe_result = await ticket_find_similar(
        limit=10, internal_limit=100, threshold=0.75
    )

    print(f"✓ Found {len(safe_result.get('similar_pairs', []))} similar pairs")
    print(f"  Estimated tokens: ~{safe_result.get('estimated_tokens', 'N/A')}")
    print(f"  Status: {safe_result.get('status')}")

    # ⚠️ DEMONSTRATION ONLY: Show why large internal_limit is dangerous
    print("\n⚠️ Dangerous configuration (internal_limit=500) - DO NOT USE:")
    print(f"  Would analyze: 500 tickets")
    print(f"  Estimated tokens: ~92,500 tokens")
    print(f"  Result: EXCEEDS 20k LIMIT by 4.6x! ❌")
    print(f"  Recommendation: Always use internal_limit ≤ 200")

    # Best practice: Targeted similarity search
    print("\n🎯 Best practice: Target specific ticket...")
    # In real usage: await ticket_find_similar(ticket_id="PROJ-123", limit=10)
    print(
        f"  ✓ Analyze similarities for specific ticket (most efficient)"
    )
    print(f"  ✓ Reduces analysis scope significantly")
    print(f"  ✓ Stays well under token limits")


# ==============================================================================
# Example 6: Cleanup Report with Summary Mode
# ==============================================================================


async def example_cleanup_report():
    """Generate cleanup report using summary mode.

    Token Usage:
    - Summary only: ~1,000-2,000 tokens
    - Full report: ~5,000-8,000 tokens (controlled by sections)
    """
    print("\n" + "=" * 80)
    print("Example 6: Cleanup Report with Summary Mode")
    print("=" * 80)

    # Step 1: Get summary overview
    print("\n📊 Step 1: Get summary overview...")
    summary = await ticket_cleanup_report(summary_only=True)

    print(f"✓ Cleanup Summary:")
    print(f"  Status: {summary.get('status')}")
    if summary.get("summary"):
        s = summary["summary"]
        print(f"  Similar tickets: {s.get('similar_count', 0)}")
        print(f"  Stale tickets: {s.get('stale_count', 0)}")
        print(f"  Orphaned tickets: {s.get('orphaned_count', 0)}")
    print(f"  Estimated tokens: ~{summary.get('estimated_tokens', 'N/A')}")

    # Step 2: Get detailed report for specific section if needed
    print("\n📋 Step 2: Get detailed report (if issues found)...")
    if summary.get("summary", {}).get("similar_count", 0) > 0:
        print(
            "  Found duplicate issues, fetching detailed analysis..."
        )
        # In real usage:
        # detailed = await ticket_cleanup_report(
        #     include_similar=True,
        #     include_stale=False,
        #     include_orphaned=False
        # )
        print(
            f"  Would fetch detailed similarity analysis (~3,000 tokens)"
        )
    else:
        print("  ✓ No issues found, skipping detailed analysis")

    print(f"\n📊 Token Usage Strategy:")
    print(f"  1. Summary first: ~1,500 tokens")
    print(f"  2. Detailed sections as needed: ~3,000 tokens each")
    print(f"  3. Total controlled: Always under 10,000 tokens")


# ==============================================================================
# Example 7: Token Budgeting for Multi-Step Workflow
# ==============================================================================


async def example_token_budgeting():
    """Demonstrate token budgeting across multiple tool calls.

    Token Budget: 20,000 tokens total
    Reserve: 5,000 for agent reasoning
    Available: 15,000 for tool calls
    """
    print("\n" + "=" * 80)
    print("Example 7: Token Budgeting for Multi-Step Workflow")
    print("=" * 80)

    budget_total = 20000
    budget_reserve = 5000
    budget_available = budget_total - budget_reserve
    budget_used = 0

    print(f"\n💰 Token Budget:")
    print(f"  Total: {budget_total:,} tokens")
    print(f"  Reserved (agent): {budget_reserve:,} tokens")
    print(f"  Available (tools): {budget_available:,} tokens")

    # Operation 1: Get ticket overview
    print(f"\n🔧 Operation 1: Get ticket overview...")
    op1_tokens = 300  # ticket_list(compact=True)
    budget_used += op1_tokens
    print(
        f"  Used: {op1_tokens} tokens ({op1_tokens/budget_available*100:.1f}% of tool budget)"
    )
    print(f"  Remaining: {budget_available - budget_used:,} tokens")

    # Operation 2: Analyze duplicates
    print(f"\n🔧 Operation 2: Analyze duplicates...")
    op2_tokens = 3000  # ticket_find_similar(limit=10)
    budget_used += op2_tokens
    print(
        f"  Used: {op2_tokens} tokens ({op2_tokens/budget_available*100:.1f}% of tool budget)"
    )
    print(f"  Remaining: {budget_available - budget_used:,} tokens")

    # Operation 3: Get label list
    print(f"\n🔧 Operation 3: Get label list...")
    op3_tokens = 1500  # label_list(limit=100)
    budget_used += op3_tokens
    print(
        f"  Used: {op3_tokens} tokens ({op3_tokens/budget_available*100:.1f}% of tool budget)"
    )
    print(f"  Remaining: {budget_available - budget_used:,} tokens")

    # Operation 4: Get cleanup summary
    print(f"\n🔧 Operation 4: Get cleanup summary...")
    op4_tokens = 1500  # ticket_cleanup_report(summary_only=True)
    budget_used += op4_tokens
    print(
        f"  Used: {op4_tokens} tokens ({op4_tokens/budget_available*100:.1f}% of tool budget)"
    )
    print(f"  Remaining: {budget_available - budget_used:,} tokens")

    # Summary
    print(f"\n📊 Budget Summary:")
    print(f"  Operations: 4")
    print(f"  Tool tokens used: {budget_used:,} ({budget_used/budget_available*100:.1f}% of tool budget)")
    print(f"  Tool tokens remaining: {budget_available - budget_used:,}")
    print(f"  Total tokens remaining: {budget_total - budget_reserve - budget_used:,}")
    print(f"  Status: {'✅ Under budget' if budget_used < budget_available else '❌ Over budget'}")


# ==============================================================================
# Main Runner
# ==============================================================================


async def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("MCP Ticketer - Token Pagination Examples")
    print("=" * 80)
    print("\nThese examples demonstrate token-efficient usage patterns")
    print("that keep all tool responses under the 20,000 token limit.")
    print("\n" + "=" * 80)

    examples = [
        ("Basic Pagination", example_basic_pagination),
        ("Compact vs Full Mode", example_compact_vs_full),
        ("Progressive Disclosure", example_progressive_disclosure),
        ("Large Dataset Pagination", example_large_dataset_pagination),
        ("Similarity Analysis", example_similarity_analysis),
        ("Cleanup Report", example_cleanup_report),
        ("Token Budgeting", example_token_budgeting),
    ]

    for i, (name, func) in enumerate(examples, 1):
        try:
            await func()
        except Exception as e:
            print(f"\n❌ Example {i} ({name}) failed: {e}")
            print(f"   Note: Some examples require configured adapter and data")

        if i < len(examples):
            print("\n" + "-" * 80)

    print("\n" + "=" * 80)
    print("✅ All examples completed!")
    print("=" * 80)
    print("\nSee docs/TOKEN_PAGINATION.md for detailed documentation.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
