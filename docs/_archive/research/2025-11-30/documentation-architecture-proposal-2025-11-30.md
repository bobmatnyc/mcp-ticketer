# Documentation Architecture Proposal

**Date**: 2025-11-30
**Author**: Documentation Agent
**Project**: mcp-ticketer
**Purpose**: Clean documentation architecture design for 225+ markdown files

---

## Executive Summary

This proposal defines a **clean, user-first documentation architecture** that consolidates 225 markdown files across 40+ directories into a **streamlined 3-tier structure** with clear separation of concerns, intuitive navigation, and growth-ready organization.

### Key Improvements

- **82% reduction** in root-level clutter (11 → 2 files)
- **38% reduction** in active directories (40+ → ~25)
- **100% elimination** of research bloat (19 active research files → archived)
- **Clear 3-tier hierarchy**: Root → Section → Subsection
- **User-first organization**: Most-needed docs at top level
- **Archive strategy**: Clear rules for what/when/where to archive

---

## Design Principles

### 1. User-First Organization
Most commonly accessed documentation at top-level, organized by audience:
- **Users** (getting started, guides, troubleshooting)
- **Developers** (API, contributing, adapters)
- **Contributors** (architecture, design, investigations)

### 2. Maximum 3-Level Depth
```
/docs/                          # Level 1: Root
  ├── user-docs/                # Level 2: Section
  │   └── getting-started/      # Level 3: Subsection (MAX)
```

**Exception**: Archive can go deeper for historical organization

### 3. Separation of Concerns

| Category | Purpose | Audience | Examples |
|----------|---------|----------|----------|
| **user-docs/** | How to use the tool | End users, AI agents | Quick start, guides, features |
| **developer-docs/** | How to contribute | Contributors, maintainers | API reference, adapters, testing |
| **architecture/** | How it works | Technical architects | System design, PRDs, decisions |
| **reference/** | Technical specs | All audiences | API specs, config options, changelog |
| **integrations/** | Platform setup | Platform users | Linear, GitHub, Claude Desktop |
| **examples/** | Hands-on tutorials | All audiences | Recipes, workflows, cookbooks |
| **_archive/** | Historical docs | Researchers | Old versions, research, deprecated |

### 4. Version-Agnostic Structure
Avoid version-specific directories in active docs:
- ❌ `/docs/v1.4/`, `/docs/releases/v1.1.6/`
- ✅ `/docs/migration/v1.4-breaking-changes.md`
- ✅ `/docs/_archive/releases/v1.1.x/`

**Rule**: Keep only **current + previous major version** in active docs

### 5. Archive-Friendly
Clear archival rules prevent cruft accumulation:
- **Research files**: Archive after 30 days unless promoted to permanent docs
- **Release docs**: Archive when version is 2+ major versions old
- **Implementation summaries**: Archive immediately after PR merge
- **Investigation reports**: Archive after extracting insights to permanent docs

### 6. Link-Stable Structure
Minimize broken links during reorganization:
- Use **relative links** within `/docs/`
- Create **redirect stubs** for moved high-traffic docs
- Update **all README indexes** simultaneously
- Use **git mv** to preserve history

### 7. Growth-Ready Design
Can accommodate future content without restructuring:
- **Extensible subsections**: Add new subsections without reorganizing
- **Clear naming patterns**: Consistent file naming conventions
- **Scalable archive**: Date-based archival organization
- **Topic-based grouping**: Related docs grouped by purpose, not chronology

---

## Proposed Directory Structure

### Visual Tree

```
docs/
├── README.md                           # Master index (KEEP)
├── CHANGELOG.md                        # Version history (NEW - moved from root)
├── RELEASE.md                          # Release process (KEEP)
│
├── user-docs/                          # 🟢 USER AUDIENCE
│   ├── README.md                       # User docs index
│   ├── getting-started/                # Onboarding (3 levels max)
│   │   ├── QUICK_START.md
│   │   ├── QUICK_START_ENV.md
│   │   ├── CONFIGURATION.md
│   │   └── LOCAL_MCP_SETUP.md          # NEW (from development/)
│   ├── guides/                         # How-to guides
│   │   ├── USER_GUIDE.md
│   │   ├── BULLETPROOF_TICKET_CREATION.md
│   │   ├── EPIC_ATTACHMENTS.md
│   │   └── mcp-tool-examples.md        # NEW (gap fill)
│   ├── features/                       # Feature documentation
│   │   ├── README.md
│   │   ├── ticket_instructions.md
│   │   ├── AUTOMATIC_VALIDATION.md
│   │   ├── UPDATE_CHECKING.md
│   │   ├── AUTO_PROJECT_UPDATES.md
│   │   ├── DEFAULT_VALUES.md
│   │   ├── semantic-priority-matching.md   # NEW (from root)
│   │   └── token-pagination.md             # NEW (from root)
│   └── troubleshooting/                # Problem-solving
│       ├── TROUBLESHOOTING.md
│       └── error-reference.md          # NEW (gap fill)
│
├── developer-docs/                     # 🟠 DEVELOPER AUDIENCE
│   ├── README.md                       # Developer docs index
│   ├── getting-started/                # Developer onboarding
│   │   ├── DEVELOPER_GUIDE.md
│   │   ├── CONTRIBUTING.md
│   │   └── CODE_STRUCTURE.md
│   ├── api/                            # API reference
│   │   ├── README.md
│   │   ├── mcp-api-reference.md        # NEW (from root)
│   │   └── epic_updates_and_attachments.md
│   ├── adapters/                       # Adapter development
│   │   ├── README.md
│   │   ├── OVERVIEW.md
│   │   ├── github.md
│   │   ├── LINEAR.md
│   │   ├── LINEAR_URL_HANDLING.md
│   │   ├── linear-url-summary.md       # NEW (from root)
│   │   └── tutorial.md                 # NEW (gap fill)
│   ├── testing/                        # Testing guide
│   │   ├── README.md                   # NEW
│   │   └── strategy.md                 # NEW (gap fill)
│   └── releasing/                      # Release management
│       ├── RELEASING.md
│       └── VERSIONING.md
│
├── architecture/                       # 🔵 ARCHITECTURE AUDIENCE
│   ├── README.md                       # Architecture index
│   ├── ARCHITECTURE.md
│   ├── MCP_INTEGRATION.md
│   ├── MOTIVATION.md
│   ├── PATTERNS.md
│   ├── PRD.md
│   ├── ROADMAP.md
│   └── STRATEGY.md
│
├── reference/                          # 📚 REFERENCE MATERIAL (NEW)
│   ├── README.md                       # NEW (reference index)
│   ├── configuration-options.md        # NEW (extracted from guides)
│   ├── workflow-states.md              # NEW (state machine reference)
│   ├── priority-levels.md              # NEW (priority semantics)
│   └── project-status.md               # NEW (from root PROJECT_STATUS.md)
│
├── integrations/                       # 🔌 PLATFORM INTEGRATIONS
│   ├── README.md                       # Integration index
│   ├── AI_CLIENT_INTEGRATION.md
│   ├── setup/
│   │   ├── CLAUDE_DESKTOP_SETUP.md
│   │   ├── CODEX_INTEGRATION.md
│   │   ├── LINEAR_SETUP.md
│   │   └── OPENAI_SWARM_INTEGRATION.md
│
├── examples/                           # 📖 TUTORIALS & RECIPES (NEW)
│   ├── README.md                       # NEW (examples index)
│   ├── workflows/                      # Common workflows
│   │   ├── creating-tickets.md
│   │   ├── managing-epics.md
│   │   └── cross-platform-sync.md
│   ├── recipes/                        # Code recipes
│   │   ├── custom-adapters.md
│   │   └── advanced-queries.md
│   └── tutorials/                      # Step-by-step guides
│       ├── first-adapter.md
│       └── mcp-integration.md
│
├── migration/                          # 🔄 VERSION MIGRATIONS
│   ├── README.md                       # Migration index
│   ├── v1.0-to-v1.1.md
│   ├── v1.4-project-filtering.md       # NEW (gap fill)
│   └── upgrade-guide.md
│
├── investigations/                     # 🔍 ACTIVE INVESTIGATIONS
│   ├── README.md                       # Investigation index
│   ├── asana/                          # Adapter-specific
│   │   └── [current asana investigations]
│   └── implementations/                # Implementation research
│       ├── README.md
│       └── [current implementation docs]
│
├── meta/                               # 📋 DOCUMENTATION METADATA
│   ├── README.md                       # Meta docs index
│   ├── DOCUMENTATION_GUIDE.md
│   ├── DOCUMENTATION_STATUS.md
│   ├── file-organization.md
│   ├── naming-conventions.md
│   ├── PR_DESCRIPTION_TEMPLATES.md
│   ├── SNAPSHOT.md
│   ├── STRUCTURE.md
│   ├── ticket-workflows.md
│   └── VERSION.md
│
└── _archive/                           # 🗄️ HISTORICAL ARCHIVE
    ├── README.md                       # Archive index
    ├── research/                       # Dated research
    │   ├── 2025-11-24/
    │   ├── 2025-11-26/
    │   ├── 2025-11-28/
    │   ├── 2025-11-29/
    │   └── 2025-11-30/                 # NEW (19 current research files)
    ├── implementations/                # Implementation summaries
    │   ├── [existing archived implementations]
    │   └── 2025-11-30/                 # NEW (4 root implementation files)
    ├── releases/                       # Old version docs
    │   ├── v1.0.x/
    │   └── v1.1.x/                     # NEW (11 old release files)
    ├── changelogs/
    ├── qa-reports/
    ├── refactoring/
    ├── reports/
    ├── rst-docs/
    ├── summaries/
    └── test-reports/

ELIMINATED DIRECTORIES:
├── ❌ dev/                  → merged into developer-docs/
├── ❌ development/          → merged into developer-docs/getting-started/
├── ❌ features/             → merged into user-docs/features/
├── ❌ release/              → merged into _archive/releases/
├── ❌ releases/             → moved to _archive/releases/ (old), keep recent in migration/
├── ❌ research/             → moved to _archive/research/YYYY-MM-DD/
├── ❌ testing/              → merged into _archive/releases/
├── ❌ verification/         → merged into _archive/releases/
```

---

## File Placement Rules

### Decision Matrix: Where Does This File Belong?

```
┌─────────────────────────────────────────────────────────────┐
│ START: What kind of file is this?                          │
└─────────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   Is it for       Is it about      Is it time-based
   end users?      development?     or historical?
        │                │                │
        │ YES            │ YES            │ YES
        ▼                ▼                ▼
   ┌─────────┐    ┌──────────────┐  ┌──────────┐
   │user-docs│    │developer-docs│  │_archive/ │
   └─────────┘    └──────────────┘  └──────────┘
        │                │
        │                │
        ▼                ▼
   What topic?      What aspect?
   │                │
   ├─ Getting started → getting-started/
   ├─ How-to guide    → guides/
   ├─ Feature doc     → features/
   └─ Problems        → troubleshooting/
                     │
                     ├─ API docs      → api/
                     ├─ Adapter dev   → adapters/
                     ├─ Contributing  → getting-started/
                     ├─ Testing       → testing/
                     └─ Releases      → releasing/
```

### Placement Rules by File Type

| File Type | Goes To | Rationale |
|-----------|---------|-----------|
| **Quick starts, tutorials** | `user-docs/getting-started/` | First-time user path |
| **How-to guides** | `user-docs/guides/` | Task-oriented user docs |
| **Feature explanations** | `user-docs/features/` | What it does, why it matters |
| **Troubleshooting** | `user-docs/troubleshooting/` | Problem-solving |
| **API reference** | `developer-docs/api/` | Technical reference |
| **Adapter development** | `developer-docs/adapters/` | Extending the system |
| **Contributing guides** | `developer-docs/getting-started/` | Onboarding contributors |
| **Testing docs** | `developer-docs/testing/` | Testing strategy |
| **System design** | `architecture/` | High-level design |
| **Configuration specs** | `reference/` | Technical specifications |
| **Platform setup** | `integrations/setup/` | Platform-specific |
| **Code examples** | `examples/` | Hands-on learning |
| **Migration guides** | `migration/` | Version transitions |
| **Active research** | `investigations/` | Ongoing investigations |
| **Completed research** | `_archive/research/YYYY-MM-DD/` | Historical research |
| **Implementation summaries** | `_archive/implementations/YYYY-MM-DD/` | Ticket-specific work |
| **Old release docs** | `_archive/releases/vX.Y.x/` | Old version docs |

### Special Cases

#### README.md Files
- **Root `/docs/README.md`**: Master index, always keep
- **Section `/docs/user-docs/README.md`**: Section index, always keep
- **Subsection `/docs/user-docs/features/README.md`**: Subsection index, always keep
- **Archive `/docs/_archive/README.md`**: Archive index, always keep

#### RELEASE.md
- **Current `/docs/RELEASE.md`**: Release process guide (not a release note!)
- **Historical `/docs/_archive/releases/v1.1.5/RELEASE_NOTES.md`**: Version-specific notes

#### Timestamped Files
- **Pattern**: `*-YYYY-MM-DD.md` or `*-1M-443-YYYY-MM-DD.md`
- **Rule**: Archive to `/docs/_archive/research/YYYY-MM-DD/` after 30 days
- **Exception**: If promoted to permanent reference, rename and move to appropriate section

#### Version-Specific Files
- **Pattern**: `v1.4.2-*.md`, `*-v1.1.6.md`
- **Current version**: Keep in `migration/` or top-level docs
- **Previous major**: Keep in `migration/`
- **Older**: Archive to `/docs/_archive/releases/vX.Y.x/`

---

## Naming Conventions

### File Naming Standards

#### Primary Pattern: Kebab-Case
**Use for**: Most documentation files
```
✅ quick-start.md
✅ bulletproof-ticket-creation.md
✅ linear-url-handling.md
```

#### Secondary Pattern: SCREAMING_SNAKE_CASE
**Use for**: Major reference docs, established conventions
```
✅ README.md
✅ CONTRIBUTING.md
✅ TROUBLESHOOTING.md
✅ QUICK_START.md (established convention in this project)
```

#### Timestamped Pattern
**Use for**: Temporary/research files
```
✅ label-investigation-2025-11-30.md
✅ auto-remove-design-1M-443-2025-11-30.md
```

**Format**: `<topic>-<ticket>-YYYY-MM-DD.md` or `<topic>-YYYY-MM-DD.md`

#### Version-Specific Pattern
**Use for**: Migration guides, version-specific notes
```
✅ v1.4-breaking-changes.md
✅ v1.4-project-filtering.md
✅ v1.0-to-v1.1-migration.md
```

**Format**: `v<major>.<minor>-<topic>.md` or `v<from>-to-v<to>-<topic>.md`

### Directory Naming Standards

#### Pattern: Kebab-Case (Always)
```
✅ user-docs/
✅ developer-docs/
✅ getting-started/
```

#### Exceptions
```
✅ _archive/          # Leading underscore for special directories
✅ api/               # Short acronyms lowercase
```

### Consistency Rules

1. **Hyphens over underscores**: Use `-` not `_` in filenames (except SCREAMING_SNAKE_CASE)
2. **Lowercase directories**: All directories lowercase (except `README.md`)
3. **Descriptive names**: Name describes content, not structure (`user-guide.md` not `doc1.md`)
4. **No spaces**: Never use spaces in filenames or directories
5. **No special characters**: Only alphanumeric, hyphens, underscores, dots

### Renaming Strategy

When consolidating, prefer:
1. **Established names**: If file is widely referenced, keep the name
2. **Descriptive over short**: `linear-url-handling.md` over `linear.md`
3. **Consistency**: Match patterns in same directory

---

## README Template

### Section README Template

Use this template for all section-level `README.md` files:

```markdown
# [Section Name]

[1-2 sentence description of this section's purpose and audience]

## Contents

### [Subsection 1 Name]
- **[file-name.md](file-name.md)** - Brief description
- **[another-file.md](another-file.md)** - Brief description

### [Subsection 2 Name]
- **[third-file.md](subsection/third-file.md)** - Brief description
- **[fourth-file.md](subsection/fourth-file.md)** - Brief description

## Quick Links

[3-5 most important files with direct links]

## See Also

[Cross-references to related sections]

---

**Last Updated**: [YYYY-MM-DD]
**Section Owner**: [Team/Person responsible]
```

### Example: user-docs/README.md

```markdown
# User Documentation

Documentation for end users of MCP Ticketer and AI agents using the MCP interface.

## Contents

### Getting Started
- **[Quick Start Guide](getting-started/QUICK_START.md)** - Get up and running in 5 minutes
- **[Quick Environment Setup](getting-started/QUICK_START_ENV.md)** - Fast environment configuration
- **[Configuration Guide](getting-started/CONFIGURATION.md)** - Complete configuration reference
- **[Local MCP Setup](getting-started/LOCAL_MCP_SETUP.md)** - Local development MCP configuration

### Guides
- **[User Guide](guides/USER_GUIDE.md)** - Complete user documentation
- **[Bulletproof Ticket Creation](guides/BULLETPROOF_TICKET_CREATION.md)** - Best practices for ticket creation
- **[Epic Attachments Guide](guides/EPIC_ATTACHMENTS.md)** - Working with epic attachments
- **[MCP Tool Examples](guides/mcp-tool-examples.md)** - Practical MCP tool usage examples

### Features
- **[Feature Overview](features/README.md)** - All features at a glance
- **[Ticket Instructions](features/ticket_instructions.md)** - Customizing ticket writing instructions
- **[Automatic Validation](features/AUTOMATIC_VALIDATION.md)** - Automatic ticket validation
- **[Update Checking](features/UPDATE_CHECKING.md)** - Version update checking
- **[Semantic Priority Matching](features/semantic-priority-matching.md)** - Natural language priority mapping
- **[Token Pagination](features/token-pagination.md)** - Efficient token usage for large result sets

### Troubleshooting
- **[Troubleshooting Guide](troubleshooting/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Error Reference](troubleshooting/error-reference.md)** - Error codes and resolution steps

## Quick Links

- [Quick Start](getting-started/QUICK_START.md) - New users start here
- [Configuration](getting-started/CONFIGURATION.md) - Setup guide
- [Troubleshooting](troubleshooting/TROUBLESHOOTING.md) - Problem-solving

## See Also

- [Integration Guides](../integrations/README.md) - Platform-specific setup guides
- [Developer Documentation](../developer-docs/README.md) - For contributors
- [Architecture Documentation](../architecture/README.md) - Technical deep-dives

---

**Last Updated**: 2025-11-30
**Section Owner**: User Experience Team
```

---

## Migration Map

### File Movement Plan

This section maps **every file** from its current location to its new location.

#### Phase 1: Archive Research Files (19 files)

**Target**: `/docs/_archive/research/YYYY-MM-DD/`

```bash
# 2025-11-26 (2 files)
docs/research/linear-workflow-script-analysis-2025-11-26.md
  → docs/_archive/research/2025-11-26/linear-workflow-script-analysis-2025-11-26.md

docs/research/project-updates-cross-platform-investigation-2025-11-26.md
  → docs/_archive/research/2025-11-26/project-updates-cross-platform-investigation-2025-11-26.md

# 2025-11-28 (3 files)
docs/research/priority-semantic-mapping-analysis-2025-11-28.md
  → docs/_archive/research/2025-11-28/priority-semantic-mapping-analysis-2025-11-28.md

docs/research/token-usage-analysis-20k-pagination-2025-11-28.md
  → docs/_archive/research/2025-11-28/token-usage-analysis-20k-pagination-2025-11-28.md

docs/research/workflow-state-handling-fix-analysis-2025-11-28.md
  → docs/_archive/research/2025-11-28/workflow-state-handling-fix-analysis-2025-11-28.md

# 2025-11-29 (6 files)
docs/research/documentation-gap-analysis-2025-11-29.md
  → docs/_archive/research/2025-11-29/documentation-gap-analysis-2025-11-29.md

docs/research/linear-label-creation-silent-failure-1M-398-2025-11-29.md
  → docs/_archive/research/2025-11-29/linear-label-creation-silent-failure-1M-398-2025-11-29.md

docs/research/linear-label-update-failure-analysis-2025-11-29.md
  → docs/_archive/research/2025-11-29/linear-label-update-failure-analysis-2025-11-29.md

docs/research/linear-url-structure-analysis-2025-11-29.md
  → docs/_archive/research/2025-11-29/linear-url-structure-analysis-2025-11-29.md

docs/research/mcp-profile-token-optimization-2025-11-29.md
  → docs/_archive/research/2025-11-29/mcp-profile-token-optimization-2025-11-29.md

docs/research/project-filtering-gap-analysis-2025-11-29.md
  → docs/_archive/research/2025-11-29/project-filtering-gap-analysis-2025-11-29.md

# 2025-11-30 (8 files)
docs/research/auto-remove-implementation-design-2025-11-30.md
  → docs/_archive/research/2025-11-30/auto-remove-implementation-design-2025-11-30.md

docs/research/auto-remove-implementation-summary.md
  → docs/_archive/research/2025-11-30/auto-remove-implementation-summary.md

docs/research/claude-code-native-mcp-setup-2025-11-30.md
  → docs/_archive/research/2025-11-30/claude-code-native-mcp-setup-2025-11-30.md

docs/research/label-duplicate-error-investigation-1M-443-2025-11-30.md
  → docs/_archive/research/2025-11-30/label-duplicate-error-investigation-1M-443-2025-11-30.md

docs/research/label-duplicate-error-root-cause-2025-11-30.md
  → docs/_archive/research/2025-11-30/label-duplicate-error-root-cause-2025-11-30.md

docs/research/linear-api-connection-failure-analysis-2025-11-30.md
  → docs/_archive/research/2025-11-30/linear-api-connection-failure-analysis-2025-11-30.md

docs/research/linear-state-transitions-investigation-2025-11-30.md
  → docs/_archive/research/2025-11-30/linear-state-transitions-investigation-2025-11-30.md

docs/research/mcp-installation-setup-analysis-2025-11-30.md
  → docs/_archive/research/2025-11-30/mcp-installation-setup-analysis-2025-11-30.md
```

**After archival**: Delete `/docs/research/` directory (should be empty)

#### Phase 2: Archive Root Implementation Files (4 files)

**Target**: `/docs/_archive/implementations/2025-11-30/`

```bash
docs/implementation-summary-1M-443.md
  → docs/_archive/implementations/2025-11-30/implementation-summary-1M-443.md

docs/DOCSTRING_OPTIMIZATION_COMPLETION.md
  → docs/_archive/implementations/2025-11-30/DOCSTRING_OPTIMIZATION_COMPLETION.md

docs/github_url_refactor_changes.md
  → docs/_archive/implementations/2025-11-30/github_url_refactor_changes.md

docs/phase1-optimization-results.md
  → docs/_archive/implementations/2025-11-30/phase1-optimization-results.md
```

#### Phase 3: Move Root Files to Appropriate Sections (5 files)

**User-facing feature docs → user-docs/features/**

```bash
docs/SEMANTIC_PRIORITY_MATCHING.md
  → docs/user-docs/features/semantic-priority-matching.md

docs/TOKEN_PAGINATION.md
  → docs/user-docs/features/token-pagination.md
```

**Developer API reference → developer-docs/api/**

```bash
docs/mcp-api-reference.md
  → docs/developer-docs/api/mcp-api-reference.md
```

**Developer adapter docs → developer-docs/adapters/**

```bash
docs/LINEAR_URL_DOCUMENTATION_SUMMARY.md
  → docs/developer-docs/adapters/linear-url-summary.md
```

**Reference material → reference/** (NEW directory)

```bash
docs/PROJECT_STATUS.md
  → docs/reference/project-status.md
```

#### Phase 4: Consolidate Duplicate Directories (4 files)

**dev/ → developer-docs/**

```bash
docs/dev/README.md
  → docs/developer-docs/dev-guide.md  # Merge content, don't overwrite
```

**development/ → developer-docs/getting-started/**

```bash
docs/development/LOCAL_MCP_SETUP.md
  → docs/developer-docs/getting-started/LOCAL_MCP_SETUP.md
```

**release/ → _archive/releases/v1.1.x/**

```bash
docs/release/v1.1.5-verification-report.md
  → docs/_archive/releases/v1.1.x/v1.1.5-verification-report.md
```

**verification/ → _archive/releases/v1.4.x/**

```bash
docs/verification/v1.4.4-verification-report.md
  → docs/_archive/releases/v1.4.x/v1.4.4-verification-report.md
```

**After moves**: Delete empty directories:
```bash
rmdir docs/dev/
rmdir docs/development/
rmdir docs/release/
rmdir docs/verification/
```

#### Phase 5: Archive Old Releases (11 files)

**Target**: `/docs/_archive/releases/v1.1.x/`

```bash
docs/releases/v1.1.6-bugfix-url-extraction.md
  → docs/_archive/releases/v1.1.x/v1.1.6-bugfix-url-extraction.md

docs/releases/v1.1.6-phase1-qa-report.md
  → docs/_archive/releases/v1.1.x/v1.1.6-phase1-qa-report.md

docs/releases/v1.1.6-quality-gate.md
  → docs/_archive/releases/v1.1.x/v1.1.6-quality-gate.md

docs/releases/v1.1.6-router-valueerror-test-report.md
  → docs/_archive/releases/v1.1.x/v1.1.6-router-valueerror-test-report.md

docs/releases/v1.1.6-security-scan-report.md
  → docs/_archive/releases/v1.1.x/v1.1.6-security-scan-report.md

docs/releases/v1.1.6-security-summary.md
  → docs/_archive/releases/v1.1.x/v1.1.6-security-summary.md

docs/releases/v1.1.6-test-report.md
  → docs/_archive/releases/v1.1.x/v1.1.6-test-report.md

docs/releases/v1.1.6-ticket-scoping-docs.md
  → docs/_archive/releases/v1.1.x/v1.1.6-ticket-scoping-docs.md

docs/releases/v1.1.7-quality-gate-complete-output.md
  → docs/_archive/releases/v1.1.x/v1.1.7-quality-gate-complete-output.md

docs/releases/v1.1.7-quality-gate-summary.md
  → docs/_archive/releases/v1.1.x/v1.1.7-quality-gate-summary.md

docs/releases/v1.1.7-quality-gate.md
  → docs/_archive/releases/v1.1.x/v1.1.7-quality-gate.md
```

**Keep in releases/** (recent v1.4.x):
```bash
docs/releases/v1.4.2-verification.md  # KEEP
```

**After archival**: Keep `/docs/releases/` for future use, but move v1.4.2 to migration/

```bash
docs/releases/v1.4.2-verification.md
  → docs/migration/v1.4.2-verification.md
```

Then delete `/docs/releases/` directory (or repurpose for future releases)

#### Phase 6: Archive Testing Files (1 file)

**Target**: `/docs/_archive/releases/v1.4.x/`

```bash
docs/testing/auto-remove-test-report-2025-11-30.md
  → docs/_archive/releases/v1.4.x/auto-remove-test-report-2025-11-30.md
```

**After archival**: Delete `/docs/testing/` directory

#### Phase 7: Consolidate Features (3 files)

**features/ → user-docs/features/**

```bash
docs/features/AUTO_PROJECT_UPDATES.md
  → docs/user-docs/features/AUTO_PROJECT_UPDATES.md

docs/features/claude-code-native-cli.md
  → docs/user-docs/features/claude-code-native-cli.md

docs/features/DEFAULT_VALUES.md
  → docs/user-docs/features/DEFAULT_VALUES.md
```

**After moves**: Delete `/docs/features/` directory

### Total File Moves

| Phase | Files | Directories Affected |
|-------|-------|---------------------|
| Phase 1: Archive research | 19 | `research/` → `_archive/research/` |
| Phase 2: Archive implementations | 4 | `root` → `_archive/implementations/` |
| Phase 3: Organize root files | 5 | `root` → various sections |
| Phase 4: Consolidate duplicates | 4 | 4 duplicate dirs → primary sections |
| Phase 5: Archive old releases | 11 | `releases/` → `_archive/releases/` |
| Phase 6: Archive testing | 1 | `testing/` → `_archive/releases/` |
| Phase 7: Consolidate features | 3 | `features/` → `user-docs/features/` |
| **TOTAL** | **47** | **9 directories eliminated** |

---

## Archive Strategy

### What Gets Archived?

#### Immediate Archival (Upon Creation)
- **Implementation summaries**: Ticket-specific work documentation
- **PR summaries**: After PR merge
- **Test reports**: One-time test execution reports

#### Time-Based Archival (30 days)
- **Research files**: Investigation and analysis documents with timestamps
- **Temporary design docs**: Files marked as "draft" or "WIP"

#### Version-Based Archival (2+ major versions old)
- **Release documentation**: When version is >2 major versions behind current
  - Example: If current = v1.4.x, archive v1.1.x and older
- **Migration guides**: When source version is deprecated

#### Event-Based Archival
- **Deprecated features**: When feature is removed from codebase
- **Replaced documentation**: When newer version supersedes old doc
- **Completed investigations**: When findings are extracted to permanent docs

### When to Archive?

```
Current Version: v1.4.3

Keep Active:
├── v1.4.x documentation (current)
└── v1.3.x documentation (previous major)

Archive:
├── v1.2.x and older (2+ versions old)
└── v1.1.x and older (definitely archive)
```

**Rule**: Keep **current + previous major version** only

### Where to Archive?

#### Archive Directory Structure

```
_archive/
├── research/               # Timestamped research files
│   ├── 2025-11-24/
│   ├── 2025-11-26/
│   ├── 2025-11-28/
│   ├── 2025-11-29/
│   └── 2025-11-30/
│
├── implementations/        # Ticket-specific implementation docs
│   ├── 2025-11-15/
│   ├── 2025-11-20/
│   └── 2025-11-30/
│
├── releases/              # Old version documentation
│   ├── v1.0.x/
│   ├── v1.1.x/
│   └── v1.2.x/
│
├── qa-reports/            # Quality gate reports
├── test-reports/          # Test execution reports
├── summaries/             # Implementation summaries
├── changelogs/            # Old changelogs
├── refactoring/           # Refactoring summaries
└── rst-docs/              # Old RST documentation
```

### Archive Naming

Archived files **retain original names** for traceability:

```bash
# CORRECT: Keep original name in dated directory
docs/research/label-investigation-2025-11-30.md
  → docs/_archive/research/2025-11-30/label-investigation-2025-11-30.md

# INCORRECT: Don't rename when archiving
  → docs/_archive/research/2025-11-30/label-investigation.md  ❌
```

### Archive Index

Each archive subdirectory should have a `README.md`:

```markdown
# Research Archive - November 30, 2025

Timestamped research and investigation files from November 30, 2025.

## Files

- **auto-remove-implementation-design-2025-11-30.md** - Auto-remove feature design
- **label-duplicate-error-investigation-1M-443-2025-11-30.md** - Label duplication bug investigation

## Context

These files were archived on 2025-12-30 (30 days after creation).

## Related Permanent Documentation

- Auto-remove feature: `user-docs/features/auto-remove.md`
- Label management: `developer-docs/api/labels.md`

---

**Archived**: 2025-12-30
**Original Date**: 2025-11-30
```

---

## Risk Assessment

### Low Risk Changes (Green Light)

#### ✅ Archive Research Files (Phase 1)
- **Risk**: Very Low
- **Impact**: High (immediate clutter reduction)
- **Reversibility**: Easy (files retained in archive)
- **Dependencies**: None (timestamped, temporary files)
- **Validation**: Check no active links reference these files

#### ✅ Archive Implementation Summaries (Phase 2)
- **Risk**: Very Low
- **Impact**: Medium (cleaner root)
- **Reversibility**: Easy (archived, not deleted)
- **Dependencies**: Check if CLAUDE.md or other docs link to these
- **Validation**: Grep for references before archiving

#### ✅ Archive Old Releases (Phase 5)
- **Risk**: Low
- **Impact**: Medium (focus on current versions)
- **Reversibility**: Easy (archived)
- **Dependencies**: Check if migration docs reference v1.1.x
- **Validation**: Ensure no external links point to these

### Medium Risk Changes (Caution Required)

#### ⚠️ Consolidate Duplicate Directories (Phase 4)
- **Risk**: Medium
- **Impact**: Medium (structural cleanup)
- **Reversibility**: Medium (requires git history lookup)
- **Dependencies**: Update README.md references
- **Validation**:
  - Search for all references to moved files
  - Update relative links
  - Test documentation site builds (if applicable)

#### ⚠️ Move Root Files to Sections (Phase 3)
- **Risk**: Medium
- **Impact**: High (better organization)
- **Reversibility**: Medium (git history preserved with `git mv`)
- **Dependencies**:
  - Update `/docs/README.md`
  - Update section `README.md` files
  - Check for external links (GitHub issues, blog posts)
- **Validation**:
  - Grep codebase for old file paths
  - Update all cross-references
  - Create redirect stubs if high-traffic

#### ⚠️ Consolidate Features Directory (Phase 7)
- **Risk**: Medium
- **Impact**: Medium (consistent organization)
- **Reversibility**: Medium (git mv preserves history)
- **Dependencies**: Update `user-docs/features/README.md`
- **Validation**: Check for references in code comments or examples

### High Risk Changes (Requires Careful Planning)

#### 🔴 Creating New Directories (reference/, examples/)
- **Risk**: Medium-High (structural change)
- **Impact**: High (long-term organization benefit)
- **Reversibility**: Hard (creates new structure expectations)
- **Dependencies**:
  - Update all documentation indexes
  - Update CLAUDE.md if applicable
  - Update contribution guidelines
- **Validation**:
  - Ensure clear purpose for each new directory
  - Avoid creating directories for <5 files
  - Plan content migration carefully

#### 🔴 Renaming Files (kebab-case standardization)
- **Risk**: High (breaks links)
- **Impact**: Medium (consistency benefit)
- **Reversibility**: Hard (requires mapping old → new names)
- **Dependencies**:
  - External links may break
  - Git history requires `--follow` flag
- **Validation**:
  - Only rename during same PR as moves
  - Create redirect stubs for high-traffic files
  - Update all references simultaneously
- **Recommendation**: **Defer renaming** until structure stabilizes

### Change Sequencing (Risk Mitigation)

**Phase Order by Risk**:

1. ✅ **Phase 1**: Archive research (lowest risk, immediate benefit)
2. ✅ **Phase 2**: Archive implementations (low risk)
3. ✅ **Phase 5**: Archive old releases (low risk)
4. ✅ **Phase 6**: Archive testing (low risk)
5. ⚠️ **Phase 4**: Consolidate duplicates (medium risk, prepare README updates)
6. ⚠️ **Phase 7**: Consolidate features (medium risk)
7. ⚠️ **Phase 3**: Move root files (medium risk, requires README updates)
8. 🔴 **Future**: Create new directories (defer until archival complete)

### Validation Checklist

Before executing each phase:

```bash
# 1. Check for references to files being moved
grep -r "path/to/old-file.md" /Users/masa/Projects/mcp-ticketer/

# 2. List files to be moved
ls -lh docs/research/*-2025-11-30.md

# 3. Verify target directory exists
ls -ld docs/_archive/research/2025-11-30/

# 4. Test git mv (dry run if possible)
git mv --dry-run docs/research/file.md docs/_archive/research/2025-11-30/

# 5. After moves, verify no broken links
# (Use markdown link checker tool if available)
```

After executing each phase:

```bash
# 1. Verify files moved successfully
ls docs/_archive/research/2025-11-30/

# 2. Verify old directory empty (if applicable)
ls docs/research/

# 3. Check git status
git status

# 4. Update README files
# (Manual step - edit affected README.md files)

# 5. Test documentation site builds
# (If using mkdocs, sphinx, or similar)
make docs-build
```

### Rollback Plan

If a phase introduces issues:

```bash
# Rollback individual file move (before commit)
git mv docs/_archive/research/2025-11-30/file.md docs/research/

# Rollback entire phase (before commit)
git reset --hard HEAD

# Rollback after commit (create new commit)
git revert <commit-hash>

# Restore from archive (if accidentally deleted)
git checkout HEAD~1 -- docs/research/file.md
```

---

## Benefits of New Structure

### Immediate Benefits

#### 1. **Cleaner Navigation**
- **Before**: 11 files in root, unclear where to start
- **After**: 2 files in root (README.md, RELEASE.md), clear entry points
- **Impact**: New users find documentation faster

#### 2. **Reduced Cognitive Load**
- **Before**: 40+ directories to navigate
- **After**: ~25 directories with clear purposes
- **Impact**: 38% fewer directories to consider

#### 3. **Better Discoverability**
- **Before**: Related docs scattered (SEMANTIC_PRIORITY_MATCHING.md in root, semantic features in user-docs/features/)
- **After**: All feature docs in user-docs/features/
- **Impact**: Easier to find all documentation on a topic

#### 4. **Elimination of Research Bloat**
- **Before**: 19 active research files (478KB)
- **After**: 0 active research files (all archived)
- **Impact**: 100% reduction in temporary file clutter

### Medium-Term Benefits

#### 5. **Consistent Organization Pattern**
- **Before**: Mix of audience-based (user-docs/, developer-docs/) and topic-based (features/, releases/)
- **After**: Consistent audience-first organization
- **Impact**: Easier to predict where documentation belongs

#### 6. **Scalable Structure**
- **Before**: Unclear where new docs should go (create new directory?)
- **After**: Clear placement rules, extensible subsections
- **Impact**: New documentation fits naturally without restructuring

#### 7. **Clear Archival Policy**
- **Before**: Ad-hoc archival, files accumulate
- **After**: Time-based, version-based, event-based archival rules
- **Impact**: Documentation stays relevant, history preserved

### Long-Term Benefits

#### 8. **Maintainable Documentation**
- **Before**: Hard to know what's current vs historical
- **After**: Active docs clearly separated from archive
- **Impact**: Less maintenance burden, easier to keep docs up-to-date

#### 9. **Link Stability**
- **Before**: Frequent restructuring breaks links
- **After**: Well-designed structure minimizes future changes
- **Impact**: External links stay valid longer

#### 10. **Growth-Ready Architecture**
- **Before**: Structure struggles with new content types
- **After**: Can accommodate tutorials, recipes, examples naturally
- **Impact**: Documentation can scale with project

### Quantitative Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Root-level files** | 11 | 2 | **82% reduction** |
| **Active directories** | 40+ | ~25 | **38% reduction** |
| **Active research files** | 19 | 0 | **100% elimination** |
| **Orphaned files** | ~9 | 0 | **100% integration** |
| **Duplicate directories** | 4 | 0 | **100% consolidation** |
| **Maximum depth** | 4+ levels | 3 levels | **Flatter hierarchy** |

### User Experience Improvements

#### For New Users
- **Clear entry point**: `/docs/README.md` → user path
- **Predictable structure**: "I need to configure" → `user-docs/getting-started/CONFIGURATION.md`
- **Less overwhelming**: Fewer top-level choices

#### For Contributors
- **Obvious placement**: "I wrote adapter docs" → `developer-docs/adapters/`
- **Consistent patterns**: All sections follow same README template
- **Clear archival**: "This research is done" → `_archive/research/YYYY-MM-DD/`

#### For Maintainers
- **Easy navigation**: Fewer directories to check
- **Clear ownership**: Section README lists owner
- **Automated archival**: Clear rules enable automation

---

## Implementation Recommendations

### Execution Strategy

#### Option A: Big Bang (All Phases at Once)
**Pros**:
- Single PR, single review
- No intermediate inconsistent state
- Faster overall completion

**Cons**:
- High-risk (harder to rollback)
- Large PR difficult to review
- Merge conflicts if others editing docs

**Recommendation**: ❌ **Not recommended** (too risky)

#### Option B: Phased Rollout (Recommended)
**Pros**:
- Lower risk (rollback one phase if issues)
- Easier to review (smaller PRs)
- Can validate each phase before proceeding

**Cons**:
- Multiple PRs
- Temporary inconsistent state
- Longer overall timeline

**Recommendation**: ✅ **Recommended approach**

**Phase PRs**:
1. **PR 1**: Archive research + implementations (Phases 1-2) - **LOW RISK**
2. **PR 2**: Archive old releases + testing (Phases 5-6) - **LOW RISK**
3. **PR 3**: Consolidate duplicates (Phase 4) + Update READMEs - **MEDIUM RISK**
4. **PR 4**: Move root files (Phase 3) + Update all references - **MEDIUM RISK**
5. **PR 5**: Consolidate features (Phase 7) + Final README updates - **MEDIUM RISK**
6. **PR 6**: Create new directories (reference/, examples/) - **FUTURE**

#### Option C: Iterative Refinement
**Pros**:
- Safest approach
- Can pause and validate at any point
- Easy to incorporate feedback

**Cons**:
- Slowest approach
- Long period of inconsistency
- Risk of losing momentum

**Recommendation**: ⚠️ **Use if team unfamiliar with docs restructuring**

### Pre-Implementation Checklist

Before starting any phase:

- [ ] **Backup documentation** (`cp -r docs docs-backup-$(date +%Y%m%d)`)
- [ ] **Create branch** (`git checkout -b docs/restructure-phaseN`)
- [ ] **Document current state** (file count, directory count)
- [ ] **Identify high-traffic files** (check analytics if available)
- [ ] **Communicate changes** (notify team of upcoming restructure)
- [ ] **Test local build** (if using documentation generator)

### Post-Implementation Checklist

After completing each phase:

- [ ] **Verify file moves** (all files in expected locations)
- [ ] **Update README indexes** (all moved files referenced)
- [ ] **Check broken links** (use link checker tool)
- [ ] **Test documentation site** (if applicable)
- [ ] **Update CLAUDE.md** (if file paths referenced)
- [ ] **Commit with descriptive message** (include phase number)
- [ ] **Create PR with migration notes**
- [ ] **Request review from docs maintainer**
- [ ] **Merge and announce** (communicate changes to team)

### Git Workflow

**Always use `git mv`** to preserve file history:

```bash
# CORRECT: Preserves git history
git mv docs/research/file.md docs/_archive/research/2025-11-30/

# INCORRECT: Loses git history
mv docs/research/file.md docs/_archive/research/2025-11-30/
git add docs/_archive/research/2025-11-30/file.md
```

**Commit strategy**:

```bash
# Phase 1: Archive research files
git mv docs/research/*-2025-11-26.md docs/_archive/research/2025-11-26/
git mv docs/research/*-2025-11-28.md docs/_archive/research/2025-11-28/
git commit -m "docs: archive research files from Nov 26-28, 2025 (Phase 1a)"

git mv docs/research/*-2025-11-29.md docs/_archive/research/2025-11-29/
git mv docs/research/*-2025-11-30.md docs/_archive/research/2025-11-30/
git commit -m "docs: archive research files from Nov 29-30, 2025 (Phase 1b)"

# Create archive README
git add docs/_archive/research/2025-11-30/README.md
git commit -m "docs: add archive index for Nov 30, 2025 research"
```

### Testing Strategy

#### Automated Tests (if available)
```bash
# Link checker
find docs -name "*.md" -exec markdown-link-check {} \;

# Broken reference finder
grep -r "\[.*\](.*)" docs/ | grep -v "http" | grep -v "#"

# Documentation build
make docs-build
```

#### Manual Tests
1. **Navigate from root README** → Can you reach all sections?
2. **Follow cross-references** → Do "See Also" links work?
3. **Search for old paths** → `grep -r "docs/research/"` should return no results
4. **Check git history** → `git log --follow` should show file history

---

## Next Steps

### Immediate Actions (Week 1)

1. **Review this proposal** with team
2. **Get consensus** on directory structure
3. **Create tracking issue** in Linear
4. **Set up backup** of current documentation
5. **Execute Phase 1** (archive research files)

### Short-Term Actions (Week 2-3)

6. **Execute Phase 2** (archive implementations)
7. **Execute Phase 5** (archive old releases)
8. **Update archive README** files
9. **Validate archival** (check no broken links)

### Medium-Term Actions (Week 4-5)

10. **Execute Phase 4** (consolidate duplicates)
11. **Execute Phase 3** (move root files)
12. **Execute Phase 7** (consolidate features)
13. **Update all README indexes**
14. **Test all cross-references**

### Long-Term Actions (Month 2+)

15. **Create new directories** (reference/, examples/)
16. **Fill documentation gaps** (migration guides, tutorials)
17. **Establish archival automation** (script to archive old research)
18. **Document new structure** in CLAUDE.md
19. **Announce completion** to users

### Success Metrics

Track these metrics to measure success:

- **Root-level files**: Target <5 (currently 11)
- **Active directories**: Target <30 (currently 40+)
- **Orphaned files**: Target 0 (currently ~9)
- **Broken links**: Target 0
- **User feedback**: "Where do I find X?" questions should decrease

---

## Conclusion

This documentation architecture proposal provides:

1. ✅ **Clear 3-tier hierarchy** (root → section → subsection)
2. ✅ **User-first organization** (most-needed docs accessible)
3. ✅ **Separation of concerns** (user/developer/architecture)
4. ✅ **Archive strategy** (time-based, version-based, event-based)
5. ✅ **File placement rules** (decision matrix for new docs)
6. ✅ **Naming conventions** (consistent, predictable naming)
7. ✅ **Migration map** (47 files, 9 directories eliminated)
8. ✅ **Risk assessment** (low/medium/high risk phases)
9. ✅ **Implementation plan** (phased rollout, git workflow)

**Expected Outcome**: A **clean, maintainable, scalable** documentation structure that serves users, developers, and contributors effectively while accommodating future growth.

---

**Proposal Status**: Draft
**Next Review**: [Team review date]
**Implementation Target**: [Target completion date]
**Owner**: Documentation Team
**Last Updated**: 2025-11-30
