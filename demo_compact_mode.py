#!/usr/bin/env python3
"""Demonstration of token usage reduction with compact mode.

This script shows the difference in output size between standard and compact
modes when listing tickets.
"""

import json

from mcp_ticketer.core.models import Priority, Task, TicketState
from mcp_ticketer.mcp.server.tools.ticket_tools import _compact_ticket


def create_sample_ticket(i: int) -> Task:
    """Create a sample ticket with realistic data."""
    return Task(
        id=f"TICKET-{i:03d}",
        title=f"Implement feature {i}: User authentication system",
        description=f"""This is a detailed description for ticket {i}.

        We need to implement a comprehensive authentication system that includes:
        - OAuth 2.0 support for Google, GitHub, and Microsoft
        - JWT token generation and validation
        - Refresh token rotation
        - Multi-factor authentication (MFA) support
        - Password reset flow with email verification
        - Rate limiting for login attempts
        - Session management with Redis

        Technical Requirements:
        - Use bcrypt for password hashing
        - Implement PKCE for OAuth flows
        - Add comprehensive logging for security events
        - Write unit tests with >90% coverage
        - Add integration tests for all flows

        Acceptance Criteria:
        - Users can sign up with email/password
        - Users can log in with OAuth providers
        - MFA can be enabled/disabled by users
        - All security events are logged
        - Tests pass with full coverage
        """,
        state=TicketState.IN_PROGRESS,
        priority=Priority.HIGH,
        assignee="developer@example.com",
        tags=["feature", "authentication", "security", "backend", "high-priority"],
        parent_epic="EPIC-AUTH-001",
        estimated_hours=40.0,
        actual_hours=25.5,
    )


def count_tokens_approx(text: str) -> int:
    """Approximate token count (roughly 4 chars per token)."""
    return len(text) // 4


def main():
    """Demonstrate token usage differences."""
    # Create sample tickets
    tickets = [create_sample_ticket(i) for i in range(1, 101)]

    # Standard mode output
    standard_tickets = [t.model_dump() for t in tickets]
    standard_json = json.dumps(standard_tickets, indent=2)
    standard_size = len(standard_json)
    standard_tokens = count_tokens_approx(standard_json)

    # Compact mode output
    compact_tickets = [_compact_ticket(t.model_dump()) for t in tickets]
    compact_json = json.dumps(compact_tickets, indent=2)
    compact_size = len(compact_json)
    compact_tokens = count_tokens_approx(compact_json)

    # Calculate savings
    ((standard_size - compact_size) / standard_size) * 100
    ((standard_tokens - compact_tokens) / standard_tokens) * 100


    # Show sample output

    # Fields comparison
    standard_fields = set(standard_tickets[0].keys())
    compact_fields = set(compact_tickets[0].keys())
    standard_fields - compact_fields


    # Use case recommendations


if __name__ == "__main__":
    main()
