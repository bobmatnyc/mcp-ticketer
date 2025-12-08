## Summary

This PR contributes a production-ready Linear GraphQL API integration skill for Claude Code.

## Skill Details

- **Skill Name**: `platforms-linear-graphql`
- **Size**: 32KB (1,361 lines, ~4,700 tokens)
- **Source**: Battle-tested patterns from [mcp-ticketer](https://github.com/1mproject/mcp-ticketer) adapter (6,193 lines of production code)
- **Version**: 1.0.0

## Key Features

### Team-Scoped Architecture
- All operations require team context (Linear's fundamental design)
- Team-specific workflows, labels, and cycles
- Multi-team query patterns

### GraphQL Fragment Composition
- 10 reusable fragments (User, WorkflowState, Team, Cycle, Project, etc.)
- Production patterns for DRY query composition
- Performance optimization through selective field fetching

### Authentication (Critical Difference)
- **NO Bearer prefix** (most common mistake)
- Direct API key authentication
- Clear examples to avoid 401 errors

### Cycle Management
- Date-based state management with required dates
- Auto progress calculation
- Sprint workflow patterns

### Type System Quirks
- String! vs ID! distinction
- Type validation examples
- Common type mismatch fixes

## Use Cases

Load this skill when:
- Building Linear integrations
- Debugging Linear API issues
- Understanding team-scoped architecture
- Implementing cycle (sprint) management
- Migrating from GitHub/Jira
- Creating Linear bots or automation tools

## Prerequisites

Requires understanding of GraphQL fundamentals from:
- `toolchains-universal-data-graphql` skill

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
2. Should I add more migration examples (GitHub → Linear, Jira → Linear)?
3. Any formatting preferences for GraphQL-focused skills?

## License

MIT License (aligns with mcp-ticketer project).
