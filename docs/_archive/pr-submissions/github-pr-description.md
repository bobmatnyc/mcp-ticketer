## Summary

This PR contributes a production-ready GitHub API integration skill for Claude Code.

## Skill Details

- **Skill Name**: `platforms-github-api`
- **Size**: 33KB (1,260 lines, ~5,106 tokens)
- **Source**: Battle-tested patterns from [mcp-ticketer](https://github.com/1mproject/mcp-ticketer) adapter (2,593 lines of production code)
- **Version**: 1.0.0

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

## Use Cases

Load this skill when:
- Building GitHub Issues integrations
- Automating project boards and workflows
- Managing milestones and labels
- Implementing CI/CD with GitHub Actions
- Creating PR automation workflows
- Extending GitHub state management

## Testing

- ✅ Tested locally with Claude Code
- ✅ YAML frontmatter validated
- ✅ No sensitive information included
- ✅ Follows skill formatting standards
- ✅ Entry point structure for progressive disclosure

## Category

Proposing new category: **Platform Integrations** for API integration skills.

If there's a better existing category, happy to move the skill there (possibly "Development & Technical").

## Questions for Maintainers

1. Does the "Platform Integrations" category make sense, or should this go under "Development & Technical"?
2. Should I add any additional examples or usage documentation?
3. Any formatting preferences for large skills (1,000+ lines)?

## License

MIT License (aligns with mcp-ticketer project).
