## Summary

This PR contributes a production-ready Jira REST API v3 integration skill for Claude Code.

## Skill Details

- **Skill Name**: `platforms-jira-api`
- **Size**: 50KB (2,093 lines, ~9,500 tokens)
- **Source**: Battle-tested patterns from [mcp-ticketer](https://github.com/1mproject/mcp-ticketer) adapter (2,158 lines of production code)
- **Version**: 1.0.0

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

## Use Cases

Load this skill when:
- Building Jira issue integrations
- Optimizing JQL queries for performance
- Handling 2025 rate limiting enforcement
- Automating Jira workflows and transitions
- Managing sprint/epic/backlog operations
- Migrating from Jira Server/Data Center to Cloud

## Testing

- ✅ Tested locally with Claude Code
- ✅ YAML frontmatter validated
- ✅ No sensitive information included
- ✅ Follows skill formatting standards
- ✅ Entry point structure for progressive disclosure
- ✅ 2025 API updates verified

## Category

Proposing new category: **Platform Integrations** for API integration skills.

If there's a better existing category, happy to move the skill there (possibly "Development & Technical").

## Questions for Maintainers

1. Does the "Platform Integrations" category make sense, or should this go under "Development & Technical"?
2. Should I split this into multiple smaller skills (e.g., Jira Basics, JQL Optimization, Agile APIs)?
3. Any concerns about the skill size (2,000+ lines)?

## License

MIT License (aligns with mcp-ticketer project).
