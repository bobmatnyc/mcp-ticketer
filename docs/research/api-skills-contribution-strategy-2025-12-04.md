# API Skills Contribution Strategy

**Research Date:** 2025-12-04
**Researcher:** Research Agent
**Context:** Identifying target repositories for GitHub, Jira, and Linear API skills
**Status:** Complete

## Executive Summary

We have created three production-ready Claude Code skills for platform API integrations (GitHub, Jira, Linear) in commit `acb5db5`. This research identifies the appropriate repositories for contributing these skills and provides PR submission strategies.

**Key Finding:** The official Anthropic skills repository (`anthropics/skills`) does not accept community contributions. The best target is the community-maintained `travisvn/awesome-claude-skills` repository, which actively accepts PRs and has 1,800+ stars.

## Skills Created

### 1. GitHub REST API Skill
- **Path:** `/Users/masa/Projects/mcp-ticketer/skills/platforms-github-api/SKILL.md`
- **Size:** 33KB (1,260 lines, ~5,106 tokens)
- **Description:** Hybrid REST/GraphQL patterns for GitHub Issues, milestones, labels, and PR automation
- **Key Features:**
  - Label-based state management (solves GitHub's binary limitation)
  - Rate limiting (5K/hr) with ETag optimization
  - Milestone hybrid storage pattern
  - PR automation workflows
  - Production patterns from mcp-ticketer adapter (2,593 lines)

### 2. Jira REST API Skill
- **Path:** `/Users/masa/Projects/mcp-ticketer/skills/platforms-jira-api/SKILL.md`
- **Size:** 50KB (2,093 lines, ~9,500 tokens)
- **Description:** Jira REST API v3 with JQL optimization and 2025 rate limiting updates
- **Key Features:**
  - 50+ JQL examples for common operations
  - JQL query optimization with performance tiers
  - 2025 rate limiting updates (10 req/sec strict enforcement)
  - Sprint/epic/board management
  - Bulk operations and pagination strategies
  - Production patterns from mcp-ticketer adapter (2,158 lines)

### 3. Linear GraphQL API Skill
- **Path:** `/Users/masa/Projects/mcp-ticketer/skills/platforms-linear-graphql/SKILL.md`
- **Size:** 32KB (1,361 lines, ~4,700 tokens)
- **Supporting Files:** `README.md`
- **Description:** Linear GraphQL API with team-scoped architecture and cycle management
- **Key Features:**
  - GraphQL fragment composition (10 reusable fragments)
  - Team-scoped architecture patterns
  - Authentication (NO Bearer prefix - critical!)
  - Cycle (sprint) management with date-based states
  - Type system quirks (String! vs ID!)
  - Migration patterns from GitHub/Jira
  - Production patterns from mcp-ticketer adapter (6,193 lines)

## Target Repository Analysis

### Option 1: anthropics/skills (Official) ❌

**URL:** https://github.com/anthropics/skills
**Stars:** 3,800+
**Status:** Reference/Educational Only

**Findings:**
- **No community contributions accepted**
- No CONTRIBUTING.md file
- README states skills are "provided for demonstration and educational purposes"
- Focus on showcasing partner skills (Notion, etc.)
- Reference repository for learning patterns only

**Verdict:** Not suitable for contribution.

---

### Option 2: travisvn/awesome-claude-skills (Community) ✅ RECOMMENDED

**URL:** https://github.com/travisvn/awesome-claude-skills
**Stars:** 1,800+
**Status:** Actively Maintained

**Findings:**
- **Actively accepts PRs** - "PRs Welcome" badge displayed
- Has CONTRIBUTING.md with submission guidelines
- Organized by categories (Document, Development, Creative, Communication)
- Already includes platform skills (Slack, Canvas, etc.)
- Submission process: "Submit to this awesome list via PR"
- Encourages testing locally before submission

**Directory Structure:**
```
my-skill/
├── SKILL.md (with YAML frontmatter)
├── scripts/ (optional executable scripts)
└── resources/ (optional supporting files)
```

**Existing Categories:**
- Document manipulation: docx, pdf, pptx, xlsx
- Creative/design: algorithmic-art, canvas-design, slack-gif-creator
- Development: artifacts-builder, mcp-builder, webapp-testing
- Communication: brand-guidelines, internal-comms

**Proposed Category:** **Platform Integrations** or **API Integrations**

**Verdict:** ✅ Best target for contribution.

---

### Option 3: obra/superpowers (Core Skills Library) ⚠️

**URL:** https://github.com/obra/superpowers
**Stars:** Unknown
**Status:** Active Development

**Findings:**
- Accepts contributions with structured process
- Focus on development workflow automation (TDD, debugging, code review)
- No existing platform API integration examples
- More focused on development practices than external service connectors
- Fork, create branch, follow `writing-skills` skill for guidance

**Directory Structure:**
```
├── skills/
├── agents/
├── commands/
├── docs/
├── lib/
└── tests/
```

**Verdict:** ⚠️ Possible but not ideal fit (focus is on dev practices, not API integrations).

---

### Option 4: alirezarezvani/claude-skills (Production Skills) ⚠️

**URL:** https://github.com/alirezarezvani/claude-skills
**Stars:** Unknown
**Status:** Active

**Findings:**
- Has CONTRIBUTING.md
- **Already includes Jira/Atlassian skills** (advanced JQL, project management)
- Organized by role (marketing, engineering, c-level, product-team, project-management)
- Production-ready standards with version tracking
- Includes Python CLI tools with each skill
- Quality metrics: "40%+ time savings, 30%+ quality improvements"

**Existing Platform Integrations:**
- Jira expertise (advanced JQL, workflow configuration, custom fields)
- Confluence mastery (space architecture, templates, macros)
- Atlassian MCP integration (sprint management)
- HubSpot (campaign tracking, lead scoring)
- GitHub (CI/CD automation)

**Directory Structure:**
```
├── marketing-skill/
├── c-level-advisor/
├── product-team/
├── engineering-team/
├── project-management/
├── commands/
├── agents/
└── templates/
```

**Proposed Category:** **engineering-team/** or **project-management/**

**Verdict:** ⚠️ Good fit for Jira skill (already has Atlassian focus), but may overlap with existing content.

---

## Contribution Strategy

### Primary Target: travisvn/awesome-claude-skills

**Why:**
1. Actively accepting community PRs
2. Largest community curated list (1,800+ stars)
3. No existing GitHub/Jira/Linear API skills
4. Clear submission process
5. Broad audience reach

**Submission Plan:**

#### PR 1: GitHub REST API Skill
- **Branch:** `feat/github-api-skill`
- **Directory:** `skills/platforms-github-api/`
- **Files:**
  - `SKILL.md` (33KB)
  - `README.md` (to be created with usage instructions)
- **Category:** Platform Integrations (new category)
- **Title:** "Add GitHub REST API v3/GraphQL v4 integration skill"
- **Description:**
  ```
  Production-ready GitHub API skill with:
  - Hybrid REST/GraphQL patterns
  - Label-based state management
  - Rate limiting (5K/hr) optimization
  - Milestone and PR automation
  - Battle-tested patterns from mcp-ticketer adapter (2,593 lines)

  Use when building GitHub Issues integrations, automating project boards,
  or creating PR workflows.
  ```

#### PR 2: Jira REST API Skill
- **Branch:** `feat/jira-api-skill`
- **Directory:** `skills/platforms-jira-api/`
- **Files:**
  - `SKILL.md` (50KB)
  - `README.md` (to be created with usage instructions)
- **Category:** Platform Integrations
- **Title:** "Add Jira REST API v3 integration skill with 2025 rate limiting"
- **Description:**
  ```
  Production-ready Jira API skill with:
  - 50+ JQL query examples
  - JQL optimization with performance tiers
  - 2025 rate limiting enforcement (10 req/sec)
  - Sprint/epic/board management
  - Bulk operations and pagination
  - Battle-tested patterns from mcp-ticketer adapter (2,158 lines)

  Use when building Jira integrations, optimizing JQL queries,
  or automating sprint workflows.
  ```

#### PR 3: Linear GraphQL API Skill
- **Branch:** `feat/linear-graphql-skill`
- **Directory:** `skills/platforms-linear-graphql/`
- **Files:**
  - `SKILL.md` (32KB)
  - `README.md` (already exists, 70 lines)
- **Category:** Platform Integrations
- **Title:** "Add Linear GraphQL API integration skill with team-scoped patterns"
- **Description:**
  ```
  Production-ready Linear GraphQL skill with:
  - Team-scoped architecture patterns
  - GraphQL fragment composition (10 reusable fragments)
  - Authentication (NO Bearer prefix - critical!)
  - Cycle (sprint) management with date-based states
  - Type system quirks (String! vs ID!)
  - Migration patterns from GitHub/Jira
  - Battle-tested patterns from mcp-ticketer adapter (6,193 lines)

  Use when building Linear integrations, understanding team-scoped architecture,
  or migrating from GitHub/Jira.
  ```

---

### Secondary Target: alirezarezvani/claude-skills

**Why:**
- Already has Atlassian/Jira focus (good fit for Jira skill)
- Production-ready standards align with our quality
- May have audience specifically interested in project management tools

**Submission Plan:**

Only submit **Jira API skill** here (avoid duplication).

- **Branch:** `feat/jira-rest-api-v3-skill`
- **Directory:** `engineering-team/jira-api/` or `project-management/jira-api/`
- **Files:**
  - `SKILL.md` (50KB)
  - `README.md` (to be created)
  - Optional: Python CLI tool (if aligns with repo standards)

**Note:** Check CONTRIBUTING.md for specific requirements before submission.

---

## Pre-Submission Checklist

### For All Skills:

- [ ] Verify SKILL.md formatting follows repository standards
- [ ] Create README.md for GitHub and Jira skills (Linear already has one)
- [ ] Add YAML frontmatter with `name` and `description`
- [ ] Test skills locally with Claude Code
- [ ] Add usage examples in README
- [ ] Include attribution to mcp-ticketer project
- [ ] Add MIT license notice (aligns with mcp-ticketer)
- [ ] Remove any sensitive information (API keys, internal URLs)

### YAML Frontmatter Format:

**GitHub:**
```yaml
---
name: platforms-github-api
description: GitHub REST API v3 and GraphQL v4 integration patterns for ticket management and automation
---
```

**Jira:**
```yaml
---
name: platforms-jira-api
description: Jira REST API v3 integration patterns for issue tracking, sprint management, and JQL query optimization. Production-ready patterns for 2025 rate limiting.
---
```

**Linear:**
```yaml
---
name: platforms-linear-graphql
description: Linear GraphQL API integration patterns for modern issue tracking with cycles, projects, and team-scoped workflows
---
```

---

## README.md Templates

### GitHub API Skill README

```markdown
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
```

---

### Jira API Skill README

```markdown
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
```

---

## PR Submission Timeline

### Week 1: Preparation
- [ ] Create README.md files for GitHub and Jira skills
- [ ] Test all three skills locally with Claude Code
- [ ] Verify YAML frontmatter formatting
- [ ] Remove any sensitive information
- [ ] Review CONTRIBUTING.md for travisvn/awesome-claude-skills

### Week 2: Primary Submissions (travisvn/awesome-claude-skills)
- [ ] Submit PR 1: GitHub REST API skill
- [ ] Submit PR 2: Jira REST API skill
- [ ] Submit PR 3: Linear GraphQL API skill

### Week 3: Secondary Submission (alirezarezvani/claude-skills)
- [ ] Review CONTRIBUTING.md for alirezarezvani/claude-skills
- [ ] Submit Jira API skill (if no overlap with existing content)

### Week 4: Follow-Up
- [ ] Address reviewer feedback
- [ ] Make requested changes
- [ ] Finalize merges

---

## Communication Templates

### Initial PR Comment (travisvn/awesome-claude-skills)

```markdown
## Summary

This PR contributes a production-ready {Platform} API integration skill for Claude Code.

## Skill Details

- **Skill Name**: `platforms-{platform}-api`
- **Size**: {size}KB ({lines} lines, ~{tokens} tokens)
- **Source**: Battle-tested patterns from [mcp-ticketer](https://github.com/1mproject/mcp-ticketer) adapter ({adapter_lines} lines of production code)
- **Version**: 1.0.0

## Key Features

{list key features}

## Testing

- ✅ Tested locally with Claude Code
- ✅ YAML frontmatter validated
- ✅ No sensitive information included
- ✅ Follows skill formatting standards

## Category

Proposing new category: **Platform Integrations** for API integration skills.

If there's a better existing category, happy to move the skill there.

## Questions for Maintainers

1. Does the "Platform Integrations" category make sense, or should this go under "Development & Technical"?
2. Should I add any additional examples or usage documentation?
3. Any formatting preferences for large skills (2,000+ lines)?

## License

MIT License (aligns with mcp-ticketer project).
```

---

### Follow-Up Response Template

```markdown
Thanks for the feedback! I've addressed the following:

- ✅ {Change 1}
- ✅ {Change 2}
- ✅ {Change 3}

Let me know if there's anything else you'd like me to adjust.
```

---

## Success Metrics

### Primary Goals:
1. **All three skills accepted** into travisvn/awesome-claude-skills
2. **Zero major revisions** required (indicates good quality)
3. **Community engagement**: At least 5 stars within first month

### Secondary Goals:
1. **Jira skill accepted** into alirezarezvani/claude-skills
2. **Reference citations**: Other projects reference our skills
3. **Feedback incorporation**: Use community feedback to improve mcp-ticketer

---

## Risk Assessment

### Low Risk:
- ✅ Skills are production-tested (from mcp-ticketer adapters)
- ✅ Clear formatting and structure
- ✅ Well-documented with examples
- ✅ No licensing conflicts (MIT)

### Medium Risk:
- ⚠️ Skills are large (2,000+ lines for Jira) - may exceed typical skill size
- ⚠️ May require splitting into multiple skills if size is an issue

### Mitigation:
- Highlight entry point (first 100 lines) for quick reference
- Offer to split into multiple skills if maintainers prefer
- Emphasize progressive disclosure structure

---

## Alternative: Split Large Skills

If maintainers prefer smaller skills, we can split:

### Jira Skill Split Option:
1. **platforms-jira-api-basics** (500 lines)
   - Authentication, rate limiting, basic CRUD
2. **platforms-jira-jql** (800 lines)
   - JQL optimization with 50+ examples
3. **platforms-jira-agile** (600 lines)
   - Sprint/epic/board management

### GitHub Skill Split Option:
1. **platforms-github-api-basics** (500 lines)
   - Authentication, rate limiting, issues CRUD
2. **platforms-github-labels** (400 lines)
   - Label-based state management patterns
3. **platforms-github-graphql** (360 lines)
   - GraphQL patterns for Projects V2

### Linear Skill:
- Keep as-is (1,361 lines is reasonable)

---

## Next Steps

1. **Review this research** with project maintainer
2. **Create README.md files** for GitHub and Jira skills
3. **Test skills locally** with Claude Code
4. **Fork travisvn/awesome-claude-skills**
5. **Submit PRs** according to timeline
6. **Monitor and respond** to reviewer feedback
7. **Update mcp-ticketer docs** with links to contributed skills

---

## References

- **Official Anthropic Skills**: https://github.com/anthropics/skills
- **Awesome Claude Skills**: https://github.com/travisvn/awesome-claude-skills
- **Superpowers Library**: https://github.com/obra/superpowers
- **Production Skills Collection**: https://github.com/alirezarezvani/claude-skills
- **mcp-ticketer Project**: https://github.com/1mproject/mcp-ticketer
- **Commit Reference**: acb5db5 (feat: add GitHub, Jira, and Linear API skills)

---

## Appendix: File Inventory

### Skills Created (Commit acb5db5)

| Skill | Path | Size | Lines | Tokens |
|-------|------|------|-------|--------|
| GitHub REST API | `/Users/masa/Projects/mcp-ticketer/skills/platforms-github-api/SKILL.md` | 33KB | 1,260 | ~5,106 |
| Jira REST API | `/Users/masa/Projects/mcp-ticketer/skills/platforms-jira-api/SKILL.md` | 50KB | 2,093 | ~9,500 |
| Linear GraphQL | `/Users/masa/Projects/mcp-ticketer/skills/platforms-linear-graphql/SKILL.md` | 32KB | 1,361 | ~4,700 |

### Supporting Files

| File | Path | Purpose |
|------|------|---------|
| Linear README | `/Users/masa/Projects/mcp-ticketer/skills/platforms-linear-graphql/README.md` | Usage documentation (70 lines) |
| GitHub Research | `/Users/masa/Projects/mcp-ticketer/docs/research/github-api-skill-research-2025-12-04.md` | Background research |
| Jira Research | `/Users/masa/Projects/mcp-ticketer/docs/research/jira-api-skill-research-2025-12-04.md` | Background research |
| Linear Research | `/Users/masa/Projects/mcp-ticketer/docs/research/linear-graphql-skill-review-2025-12-04.md` | Background research |
| PM Adapter Guide | `/Users/masa/Projects/mcp-ticketer/docs/pm-adapter-detection-guide.md` | Adapter detection guide for mcp-ticketer |

---

## Conclusion

**Primary Target**: Submit all three skills to `travisvn/awesome-claude-skills` (actively accepting PRs, 1,800+ stars).

**Secondary Target**: Consider submitting Jira skill to `alirezarezvani/claude-skills` (Atlassian focus).

**Timeline**: 4 weeks from preparation to final merge.

**Success Criteria**: All three skills accepted with minimal revisions and positive community engagement.

**Next Action**: Create README.md files for GitHub and Jira skills, then begin PR submission process.
