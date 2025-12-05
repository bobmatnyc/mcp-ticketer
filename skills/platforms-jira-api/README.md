---
name: platforms-jira-api
description: Jira REST API v3 integration patterns for issue tracking, sprint management, and JQL query optimization. Production-ready patterns for 2025 rate limiting.
---

# platforms-jira-api Skill

## Overview

Comprehensive Jira REST API v3 integration skill for Claude Code, extracted from production battle-tested mcp-ticketer Jira adapter (2,158 lines). Includes 2025 rate limiting updates and 50+ JQL query examples.

## Structure

- **Entry Point**: First ~100 lines (Quick Start, Authentication, Rate Limiting)
- **Full Content**: 18 comprehensive sections covering all Jira-specific patterns
- **Total**: 2,093 lines, ~6,800 words, ~9,500 tokens

## Key Features

### JQL Query Optimization
- 50+ production-ready JQL examples
- Performance tier classification (Fast/Moderate/Slow)
- Field-specific search patterns
- Complex boolean logic optimization

### 2025 Rate Limiting Enforcement
- **Critical Update**: Strict 10 requests/second enforcement (effective Nov 22, 2025)
- Rate limit header monitoring (X-RateLimit-Limit, X-RateLimit-Remaining)
- Exponential backoff with Retry-After header
- Pagination strategies to minimize API calls

### Sprint and Epic Management
- Agile API endpoints (/rest/agile/1.0/)
- Sprint creation, activation, and completion
- Epic-to-issue linking and hierarchy
- Board configuration and filtering

### Bulk Operations
- Bulk create (up to 50 issues per request)
- Bulk update with JQL filters
- Bulk delete strategies
- Pagination for large datasets

## Content Sections

1. Authentication Patterns
2. Base URL and Version Selection
3. Critical 2025 Rate Limiting Updates
4. JQL Query Fundamentals
5. JQL Performance Optimization (50+ examples)
6. Issue CRUD Operations
7. Sprint Management (Agile API)
8. Epic and Hierarchy Management
9. Workflow Transitions
10. Custom Fields and Field Expansion
11. Bulk Operations and Pagination
12. Error Handling
13. Best Practices
14. Common Pitfalls
15. Migration from Server/Data Center to Cloud
16. Code Examples
17. Testing Strategies
18. Resources and References

## Source

Based on:
- **mcp-ticketer Jira adapter**: 2,158 lines production code
- **Research**: docs/research/jira-api-skill-research-2025-12-04.md
- **Documentation**: Jira Cloud REST API v3 official docs
- **2025 Updates**: Rate limiting enforcement and deprecation notices
- **Production patterns**: JQL optimization, bulk operations, error recovery

## Usage

Load this skill in Claude Code when:
- Building Jira issue integrations
- Optimizing JQL queries for performance
- Handling 2025 rate limiting enforcement
- Automating Jira workflows and transitions
- Managing sprint/epic/backlog operations
- Migrating from Jira Server/Data Center to Cloud

## Version

- **Version**: 1.0.0
- **Created**: 2025-12-04
- **Based on**: mcp-ticketer v2.1.0

## License

MIT License - See mcp-ticketer project for details.
