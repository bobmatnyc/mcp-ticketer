---
name: platforms-github-api
description: GitHub REST API v3 and GraphQL v4 integration patterns for ticket management and automation
---

# platforms-github-api Skill

## Overview

Comprehensive GitHub REST API v3 and GraphQL v4 integration skill for Claude Code, extracted from production battle-tested mcp-ticketer GitHub adapter (2,593 lines).

## Structure

- **Entry Point**: First ~100 lines (Quick Start, Authentication, Rate Limiting)
- **Full Content**: 15 comprehensive sections covering all GitHub-specific patterns
- **Total**: 1,260 lines, ~3,300 words, ~5,106 tokens

## Key Features

### Hybrid REST/GraphQL Patterns
- REST API for CRUD operations (issues, labels, milestones)
- GraphQL for complex queries (iterations, project boards)
- Performance optimization with ETag caching

### Label-Based State Management
- Solves GitHub's binary state limitation (open/closed)
- Prefix-based workflow states (status:in-progress, status:ready, etc.)
- Priority labels (priority:high, priority:critical)

### Rate Limiting Optimization
- 5,000 requests/hour for authenticated users
- ETag caching to preserve rate limit quota
- Exponential backoff for 429 responses

### Milestone Management
- Hybrid storage pattern (local labels + GitHub milestones)
- Progress tracking and completion percentages
- Epic-like functionality through labels

## Content Sections

1. Authentication Patterns
2. Rate Limiting and Quota Management
3. Label-Based State Management
4. Milestone Management
5. Pull Request Automation
6. GraphQL for Projects V2
7. Error Handling
8. Pagination Strategies
9. Best Practices
10. Common Pitfalls
11. Migration Patterns
12. Code Examples
13. Testing Strategies
14. Performance Optimization
15. Resources and References

## Source

Based on:
- **mcp-ticketer GitHub adapter**: 2,593 lines production code
- **Research**: docs/research/github-api-skill-research-2025-12-04.md
- **Documentation**: GitHub official docs + mcp-ticketer internal docs
- **Production patterns**: ETag caching, label management, hybrid milestones

## Usage

Load this skill in Claude Code when:
- Building GitHub Issues integrations
- Automating project boards and workflows
- Managing milestones and labels
- Implementing CI/CD with GitHub Actions
- Creating PR automation workflows
- Extending GitHub state management

## Version

- **Version**: 1.0.0
- **Created**: 2025-12-04
- **Based on**: mcp-ticketer v2.1.0

## License

MIT License - See mcp-ticketer project for details.
