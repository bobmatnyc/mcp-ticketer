# platforms-linear-graphql Skill

## Overview

Comprehensive Linear GraphQL API integration skill for Claude Code, extracted from production battle-tested mcp-ticketer Linear adapter (6,193 lines).

## Structure

- **Entry Point**: First ~100 lines (Quick Start, Authentication, Error Handling)
- **Full Content**: 15 comprehensive sections covering all Linear-specific patterns
- **Total**: 1,361 lines, ~3,600 words, ~4,700 tokens

## Key Features

### Critical Differences from Standard GraphQL

1. **Authentication**: API keys passed directly (NO Bearer prefix) - #1 most common mistake
2. **Team-Scoped Architecture**: All operations require team context
3. **Fragment Composition**: Production patterns with 10 reusable fragments
4. **Rate Limiting**: 1,000 req/hr with exponential backoff
5. **Cycles (Milestones)**: Date-based state management with required dates
6. **Workflow States**: 4 immutable types with custom names per team
7. **Type System**: Strict String! vs ID! distinction

## Content Sections

1. Authentication and Setup (Bearer prefix warning!)
2. Team-Scoped Architecture
3. GraphQL Fragment Composition (Production patterns)
4. Linear Data Model (Projects/Issues/Tasks hierarchy)
5. Rate Limiting and Performance
6. Error Handling (TransportQueryError vs TransportError)
7. Cycle Management (Linear-specific)
8. Type System Quirks (String! vs ID!)
9. Best Practices
10. Common Pitfalls (with fixes)
11. Comparison with REST (GitHub/Jira)
12. Migration Patterns
13. Code Examples (Complete CRUD)
14. Testing Strategies
15. Resources and References

## Source

Based on:
- **mcp-ticketer Linear adapter**: 6,193 lines production code
- **Research**: docs/research/linear-graphql-skill-review-2025-12-04.md
- **Documentation**: Linear official docs + mcp-ticketer internal docs
- **Production patterns**: Fragment composition, error handling, retry logic

## Usage

Load this skill in Claude Code when:
- Building Linear integrations
- Debugging Linear API issues
- Understanding team-scoped architecture
- Implementing cycle (sprint) management
- Migrating from GitHub/Jira

## Prerequisites

Requires understanding of GraphQL fundamentals from:
- `toolchains-universal-data-graphql` skill

## Version

- **Version**: 1.0.0
- **Created**: 2025-12-04
- **Based on**: mcp-ticketer v2.1.0
