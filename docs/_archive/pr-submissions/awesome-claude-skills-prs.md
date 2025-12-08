# Awesome Claude Skills PR Submission Guide

This document provides all materials needed for submitting the three API skills to the awesome-claude-skills repository.

## Target Repository

- **Repository**: https://github.com/travisvn/awesome-claude-skills
- **Category**: Platform Integrations (new category proposal)
- **Contributing Guide**: https://github.com/travisvn/awesome-claude-skills/blob/main/CONTRIBUTING.md

## Fork and Branch Setup

### 1. Fork Repository

```bash
# Fork via GitHub UI or CLI
gh repo fork travisvn/awesome-claude-skills --clone=false

# Clone your fork
git clone https://github.com/YOUR_USERNAME/awesome-claude-skills.git
cd awesome-claude-skills
```

### 2. Create Feature Branches

Each skill gets its own branch for separate PRs:

```bash
# GitHub API skill
git checkout -b feat/github-api-skill

# Jira API skill
git checkout main
git checkout -b feat/jira-api-skill

# Linear GraphQL skill
git checkout main
git checkout -b feat/linear-graphql-skill
```

## PR 1: GitHub REST API Skill

### Branch: `feat/github-api-skill`

### Files to Copy

```bash
# From mcp-ticketer repository
cp -r /Users/masa/Projects/mcp-ticketer/skills/platforms-github-api \
      awesome-claude-skills/skills/

# Verify files
ls -la awesome-claude-skills/skills/platforms-github-api/
# Should show: SKILL.md, README.md
```

### PR Title

```
Add GitHub REST API v3/GraphQL v4 integration skill
```

### PR Description

```markdown
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
```

### Commit and Push

```bash
git checkout feat/github-api-skill
git add skills/platforms-github-api/
git commit -m "feat: add GitHub REST API v3/GraphQL v4 integration skill

Production-ready GitHub API skill with:
- Hybrid REST/GraphQL patterns
- Label-based state management
- Rate limiting (5K/hr) optimization
- Milestone and PR automation
- Battle-tested patterns from mcp-ticketer adapter (2,593 lines)

Use when building GitHub Issues integrations, automating project boards,
or creating PR workflows."

git push origin feat/github-api-skill
```

### Create PR

```bash
gh pr create \
  --repo travisvn/awesome-claude-skills \
  --base main \
  --head YOUR_USERNAME:feat/github-api-skill \
  --title "Add GitHub REST API v3/GraphQL v4 integration skill" \
  --body-file github-pr-description.md
```

---

## PR 2: Jira REST API Skill

### Branch: `feat/jira-api-skill`

### Files to Copy

```bash
# From mcp-ticketer repository
git checkout feat/jira-api-skill
cp -r /Users/masa/Projects/mcp-ticketer/skills/platforms-jira-api \
      awesome-claude-skills/skills/

# Verify files
ls -la awesome-claude-skills/skills/platforms-jira-api/
# Should show: SKILL.md, README.md
```

### PR Title

```
Add Jira REST API v3 integration skill with 2025 rate limiting
```

### PR Description

```markdown
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
```

### Commit and Push

```bash
git checkout feat/jira-api-skill
git add skills/platforms-jira-api/
git commit -m "feat: add Jira REST API v3 integration skill with 2025 rate limiting

Production-ready Jira API skill with:
- 50+ JQL query examples
- JQL optimization with performance tiers
- 2025 rate limiting enforcement (10 req/sec)
- Sprint/epic/board management
- Bulk operations and pagination
- Battle-tested patterns from mcp-ticketer adapter (2,158 lines)

Use when building Jira integrations, optimizing JQL queries,
or automating sprint workflows."

git push origin feat/jira-api-skill
```

### Create PR

```bash
gh pr create \
  --repo travisvn/awesome-claude-skills \
  --base main \
  --head YOUR_USERNAME:feat/jira-api-skill \
  --title "Add Jira REST API v3 integration skill with 2025 rate limiting" \
  --body-file jira-pr-description.md
```

---

## PR 3: Linear GraphQL API Skill

### Branch: `feat/linear-graphql-skill`

### Files to Copy

```bash
# From mcp-ticketer repository
git checkout feat/linear-graphql-skill
cp -r /Users/masa/Projects/mcp-ticketer/skills/platforms-linear-graphql \
      awesome-claude-skills/skills/

# Verify files
ls -la awesome-claude-skills/skills/platforms-linear-graphql/
# Should show: SKILL.md, README.md
```

### PR Title

```
Add Linear GraphQL API integration skill with team-scoped patterns
```

### PR Description

```markdown
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
```

### Commit and Push

```bash
git checkout feat/linear-graphql-skill
git add skills/platforms-linear-graphql/
git commit -m "feat: add Linear GraphQL API integration skill with team-scoped patterns

Production-ready Linear GraphQL skill with:
- Team-scoped architecture patterns
- GraphQL fragment composition (10 reusable fragments)
- Authentication (NO Bearer prefix - critical!)
- Cycle (sprint) management with date-based states
- Type system quirks (String! vs ID!)
- Migration patterns from GitHub/Jira
- Battle-tested patterns from mcp-ticketer adapter (6,193 lines)

Use when building Linear integrations, understanding team-scoped architecture,
or migrating from GitHub/Jira."

git push origin feat/linear-graphql-skill
```

### Create PR

```bash
gh pr create \
  --repo travisvn/awesome-claude-skills \
  --base main \
  --head YOUR_USERNAME:feat/linear-graphql-skill \
  --title "Add Linear GraphQL API integration skill with team-scoped patterns" \
  --body-file linear-pr-description.md
```

---

## Submission Timeline

### Week 1: Preparation (Current)
- [x] Create README.md files for GitHub and Jira skills
- [x] Verify YAML frontmatter formatting
- [ ] Test all three skills locally with Claude Code
- [ ] Review CONTRIBUTING.md for awesome-claude-skills

### Week 2: PR Submissions
- [ ] Fork travisvn/awesome-claude-skills
- [ ] Submit PR 1: GitHub REST API skill
- [ ] Submit PR 2: Jira REST API skill
- [ ] Submit PR 3: Linear GraphQL API skill

### Week 3-4: Follow-Up
- [ ] Address reviewer feedback
- [ ] Make requested changes
- [ ] Finalize merges

## Post-Submission Checklist

After each PR is created:

1. **Monitor PR Comments**
   - Respond to reviewer feedback within 24 hours
   - Make requested changes promptly
   - Test any suggested modifications

2. **Update Local Documentation**
   - Add PR links to mcp-ticketer docs
   - Update CHANGELOG if skills are referenced elsewhere

3. **Community Engagement**
   - Thank reviewers for their time
   - Provide additional context if requested
   - Offer to make further improvements

## Success Metrics

### Primary Goals
1. ✅ All three skills accepted into awesome-claude-skills
2. ✅ Zero major revisions required
3. ✅ Community engagement (5+ stars within first month)

### Secondary Goals
1. ✅ Skills referenced by other projects
2. ✅ Feedback incorporated to improve mcp-ticketer
3. ✅ "Platform Integrations" category established

## Additional Notes

### Skill Size Considerations

If maintainers express concerns about skill size:

**GitHub Skill Split Option** (1,260 lines):
1. `platforms-github-api-basics` (500 lines) - Auth, rate limiting, basic CRUD
2. `platforms-github-labels` (400 lines) - Label-based state management
3. `platforms-github-graphql` (360 lines) - GraphQL patterns for Projects V2

**Jira Skill Split Option** (2,093 lines):
1. `platforms-jira-api-basics` (500 lines) - Auth, rate limiting, basic CRUD
2. `platforms-jira-jql` (800 lines) - JQL optimization with 50+ examples
3. `platforms-jira-agile` (600 lines) - Sprint/epic/board management

**Linear Skill** (1,361 lines):
- Keep as-is (reasonable size)

### Alternative Category Suggestions

If "Platform Integrations" doesn't fit:
- "Development & Technical"
- "API & Service Integrations"
- "Project Management Tools"
- "Issue Tracking Systems"

## Contact

For questions or assistance:
- **Project**: https://github.com/1mproject/mcp-ticketer
- **Research Doc**: docs/research/api-skills-contribution-strategy-2025-12-04.md
- **Commit Reference**: acb5db5 (feat: add GitHub, Jira, and Linear API skills)

---

**Last Updated**: 2025-12-04
**Status**: Ready for submission
