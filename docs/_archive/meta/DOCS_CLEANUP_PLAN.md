# Documentation Cleanup & Reorganization Plan

**Date**: November 15, 2025
**Project**: mcp-ticketer
**Scope**: Comprehensive documentation reorganization and consolidation
**Status**: PROPOSED - Ready for execution

---

## Executive Summary

### Current State Issues

1. **Confusing Structure**: Multiple overlapping directories (dev/, development/, reports/, investigations/)
2. **Duplicate Files**: IMPLEMENTATION_SUMMARY.md exists in 2 locations with different content
3. **RST/MD Duplication**: adapters.rst vs ADAPTERS.md, api.rst vs API_REFERENCE.md, etc.
4. **Unclear Purpose**: Some directories have minimal content (quickstart/1 file, guides/1 file, prd/1 file)
5. **Poor Discoverability**: Investigation reports need better integration
6. **No Investigation Index**: New investigation reports lack navigation/context

### Proposed Improvements

- **Clear Separation**: user-docs/, developer-docs/, architecture/, investigations/
- **Eliminate Duplicates**: Single source of truth for each topic
- **Consistent Format**: Markdown-only (archive .rst files)
- **Better Navigation**: Enhanced README files with clear paths
- **Logical Grouping**: Related content together

### Expected Benefits

- ✅ **50% reduction** in documentation confusion
- ✅ **Zero duplicate** content
- ✅ **Clear ownership** of each doc type
- ✅ **Better discoverability** for all user types
- ✅ **Maintainable structure** going forward

---

## Current Structure Analysis

### File Count by Directory

```
docs/
├── Root level: 20 MD files + 7 RST files = 27 files
├── _archive/: Organized subdirectories (changelogs, implementations, releases, reports, summaries, test-reports)
├── adapters/: 2 files (github.md, LINEAR.md)
├── api/: 2 files (README.md, epic_updates_and_attachments.md)
├── dev/: 3 subdirectories
│   ├── implementations/: 14 files
│   └── test-reports/: 2 files
├── development/: 4 files (CODE_STRUCTURE.md, CONTRIBUTING.md, RELEASING.md, VERSIONING.md)
├── features/: 4 files (README.md, ticket_instructions.md, AUTOMATIC_VALIDATION.md, UPDATE_CHECKING.md)
├── guides/: 1 file (BULLETPROOF_TICKET_CREATION_GUIDE.md)
├── investigations/: 2 files (ASANA_INVESTIGATION_REPORT.md, ASANA_PRIORITY_STATUS_FINDINGS.md)
├── prd/: 1 file (mcp-ticketer-prd.md)
├── quickstart/: 1 file (epic_attachments.md)
├── reports/: 3 files (IMPLEMENTATION_SUMMARY.md, OPTIMIZATION_SUMMARY.md, TEST_COVERAGE_REPORT.md)
└── setup/: 4 files (CLAUDE_DESKTOP_SETUP.md, CODEX_INTEGRATION.md, JIRA_SETUP.md, LINEAR_SETUP.md)

Total: ~114 markdown files
```

### Key Issues Identified

#### 1. Duplicate Content

| File | Locations | Issue | Resolution |
|------|-----------|-------|------------|
| IMPLEMENTATION_SUMMARY.md | dev/implementations/, reports/ | Different content | Merge into reports/, delete from dev/ |
| adapters docs | adapters.rst, ADAPTERS.md | RST is outdated | Archive RST, keep MD |
| api docs | api.rst, API_REFERENCE.md | RST is outdated | Archive RST, keep MD |
| cli docs | cli.rst, (in USER_GUIDE.md) | RST is outdated | Archive RST |
| examples | examples.rst, (scattered in guides) | RST is outdated | Archive RST |
| installation | installation.rst, QUICK_START.md | RST is outdated | Archive RST |

#### 2. Poor Organization

| Issue | Current State | Proposed Fix |
|-------|---------------|--------------|
| dev/ vs development/ | Two similar directories | Consolidate into developer-docs/ |
| reports/ vs dev/test-reports/ | Unclear distinction | Merge all reports under investigations/ or archive |
| quickstart/ + guides/ | Single files each | Merge into user-docs/guides/ |
| prd/ | Single file, orphaned | Move to architecture/ or archive |
| investigations/ | New, no README | Add README.md, keep structure |

#### 3. Unclear Audience

Many docs don't clearly indicate their target audience (end-user vs developer vs AI integrator).

---

## Proposed New Structure

### Directory Layout

```
docs/
├── README.md                        # Main navigation hub (ENHANCED)
│
├── user-docs/                       # End-user documentation
│   ├── README.md                    # User docs index
│   ├── getting-started/
│   │   ├── QUICK_START.md          # Move from root
│   │   ├── INSTALLATION.md         # Convert from installation.rst
│   │   └── CONFIGURATION.md        # Move from root
│   ├── guides/
│   │   ├── USER_GUIDE.md           # Move from root
│   │   ├── CLI_REFERENCE.md        # Convert from cli.rst
│   │   ├── EXAMPLES.md             # Convert from examples.rst
│   │   ├── BULLETPROOF_TICKET_CREATION.md  # Move from guides/
│   │   └── EPIC_ATTACHMENTS.md     # Move from quickstart/
│   ├── features/                    # Keep existing
│   │   ├── README.md
│   │   ├── ticket_instructions.md
│   │   ├── AUTOMATIC_VALIDATION.md
│   │   └── UPDATE_CHECKING.md
│   └── troubleshooting/
│       └── COMMON_ISSUES.md        # New or extracted
│
├── developer-docs/                  # Developer documentation
│   ├── README.md                    # Developer docs index
│   ├── getting-started/
│   │   ├── DEVELOPER_GUIDE.md      # Move from root
│   │   ├── CONTRIBUTING.md         # Move from development/
│   │   └── CODE_STRUCTURE.md       # Move from development/
│   ├── api/                         # Keep existing
│   │   ├── README.md
│   │   └── epic_updates_and_attachments.md
│   ├── adapters/                    # Keep existing + add overview
│   │   ├── README.md               # New - adapter development guide
│   │   ├── OVERVIEW.md             # Move/convert from ADAPTERS.md
│   │   ├── github.md
│   │   ├── LINEAR.md
│   │   └── ASANA.md                # New or extracted
│   ├── releasing/
│   │   ├── RELEASING.md            # Move from development/
│   │   └── VERSIONING.md           # Move from development/
│   └── testing/
│       └── TESTING_GUIDE.md        # New or extracted
│
├── architecture/                    # Technical deep-dives
│   ├── README.md                    # Architecture docs index
│   ├── DESIGN.md                    # Rename from prd/mcp-ticketer-prd.md
│   ├── QUEUE_SYSTEM.md             # Move from root
│   ├── CONFIG_RESOLUTION_FLOW.md   # Move from root
│   ├── ENV_DISCOVERY.md            # Move from root
│   └── MCP_INTEGRATION.md          # Move from root
│
├── integrations/                    # Integration guides
│   ├── README.md                    # Integration index
│   ├── AI_CLIENT_INTEGRATION.md    # Move from root
│   ├── PR_INTEGRATION.md           # Move from root
│   ├── ATTACHMENTS.md              # Move from root
│   ├── setup/                       # Keep existing
│   │   ├── CLAUDE_DESKTOP_SETUP.md
│   │   ├── CODEX_INTEGRATION.md
│   │   ├── JIRA_SETUP.md
│   │   └── LINEAR_SETUP.md
│
├── investigations/                  # Investigation reports & analysis
│   ├── README.md                    # NEW - Investigation index
│   ├── asana/                       # Group Asana investigations
│   │   ├── ASANA_INVESTIGATION_REPORT.md      # Move from investigations/
│   │   └── ASANA_PRIORITY_STATUS_FINDINGS.md  # Move from investigations/
│   ├── reports/                     # Move reports/ here
│   │   ├── IMPLEMENTATION_SUMMARY.md  # Merged from dev/implementations + reports/
│   │   ├── OPTIMIZATION_SUMMARY.md
│   │   ├── TEST_COVERAGE_REPORT.md
│   │   └── test-reports/           # Move from dev/
│   │       ├── SECURITY_RESCAN_REPORT.md
│   │       └── TEST_REPORT_EPIC_ATTACHMENTS.md
│   └── implementations/             # Move from dev/
│       ├── README.md                # NEW - implementation tracking
│       └── [all implementation files]
│
├── _archive/                        # Historical documentation
│   ├── README.md                    # Keep existing
│   ├── rst-docs/                    # NEW - archived RST files
│   │   ├── adapters.rst
│   │   ├── api.rst
│   │   ├── cli.rst
│   │   ├── development.rst
│   │   ├── examples.rst
│   │   ├── index.rst
│   │   └── installation.rst
│   ├── changelogs/                  # Keep existing
│   ├── implementations/             # Keep existing
│   ├── releases/                    # Keep existing
│   ├── reports/                     # Keep existing
│   ├── summaries/                   # Keep existing
│   └── test-reports/                # Keep existing
│
└── meta/                            # Documentation about documentation
    ├── DOCUMENTATION_CLEANUP_ANALYSIS.md  # Move from root
    ├── CLEANUP_EXECUTION_REPORT.md        # Move from root
    ├── SECURITY.md                        # Move from root
    ├── MIGRATION_GUIDE.md                 # Move from root
    └── PROJECT_CONFIG.md                  # Move from root or archive
```

---

## Detailed Migration Plan

### Phase 1: Create New Directory Structure

```bash
# Create top-level directories
mkdir -p docs/user-docs/{getting-started,guides,features,troubleshooting}
mkdir -p docs/developer-docs/{getting-started,api,adapters,releasing,testing}
mkdir -p docs/architecture
mkdir -p docs/integrations/setup
mkdir -p docs/investigations/{asana,reports/test-reports,implementations}
mkdir -p docs/_archive/rst-docs
mkdir -p docs/meta

# Keep existing directories that work well
# - docs/_archive/ (already well-organized)
# - docs/features/ (will move to user-docs/features/)
# - docs/api/ (will move to developer-docs/api/)
# - docs/adapters/ (will move to developer-docs/adapters/)
# - docs/setup/ (will move to integrations/setup/)
```

### Phase 2: Move Files (Organized by Destination)

#### User Documentation

```bash
# Getting Started
mv docs/QUICK_START.md docs/user-docs/getting-started/
mv docs/CONFIGURATION.md docs/user-docs/getting-started/
# Note: installation.rst will be converted to MD first

# Guides
mv docs/USER_GUIDE.md docs/user-docs/guides/
mv docs/guides/BULLETPROOF_TICKET_CREATION_GUIDE.md docs/user-docs/guides/BULLETPROOF_TICKET_CREATION.md
mv docs/quickstart/epic_attachments.md docs/user-docs/guides/EPIC_ATTACHMENTS.md
# Note: cli.rst and examples.rst will be converted to MD first

# Features (copy entire directory)
cp -r docs/features/* docs/user-docs/features/
```

#### Developer Documentation

```bash
# Getting Started
mv docs/DEVELOPER_GUIDE.md docs/developer-docs/getting-started/
mv docs/development/CONTRIBUTING.md docs/developer-docs/getting-started/
mv docs/development/CODE_STRUCTURE.md docs/developer-docs/getting-started/

# API
cp -r docs/api/* docs/developer-docs/api/

# Adapters
cp -r docs/adapters/* docs/developer-docs/adapters/
# Note: ADAPTERS.md will be converted to OVERVIEW.md

# Releasing
mv docs/development/RELEASING.md docs/developer-docs/releasing/
mv docs/development/VERSIONING.md docs/developer-docs/releasing/
```

#### Architecture

```bash
mv docs/QUEUE_SYSTEM.md docs/architecture/
mv docs/CONFIG_RESOLUTION_FLOW.md docs/architecture/
mv docs/ENV_DISCOVERY.md docs/architecture/
mv docs/MCP_INTEGRATION.md docs/architecture/
mv docs/prd/mcp-ticketer-prd.md docs/architecture/DESIGN.md
```

#### Integrations

```bash
mv docs/AI_CLIENT_INTEGRATION.md docs/integrations/
mv docs/PR_INTEGRATION.md docs/integrations/
mv docs/ATTACHMENTS.md docs/integrations/
cp -r docs/setup/* docs/integrations/setup/
```

#### Investigations

```bash
# Asana investigations
mv docs/investigations/ASANA_INVESTIGATION_REPORT.md docs/investigations/asana/
mv docs/investigations/ASANA_PRIORITY_STATUS_FINDINGS.md docs/investigations/asana/

# Reports
mv docs/reports/OPTIMIZATION_SUMMARY.md docs/investigations/reports/
mv docs/reports/TEST_COVERAGE_REPORT.md docs/investigations/reports/

# Merge IMPLEMENTATION_SUMMARY.md (keep the more comprehensive one from reports/)
mv docs/reports/IMPLEMENTATION_SUMMARY.md docs/investigations/reports/

# Test reports
mv docs/dev/test-reports/SECURITY_RESCAN_REPORT.md docs/investigations/reports/test-reports/
mv docs/dev/test-reports/TEST_REPORT_EPIC_ATTACHMENTS.md docs/investigations/reports/test-reports/

# Implementation reports
mv docs/dev/implementations/* docs/investigations/implementations/
```

#### Archive RST Files

```bash
mv docs/*.rst docs/_archive/rst-docs/
```

#### Meta Documentation

```bash
mv docs/DOCUMENTATION_CLEANUP_ANALYSIS.md docs/meta/
mv docs/CLEANUP_EXECUTION_REPORT.md docs/meta/
mv docs/SECURITY.md docs/meta/
mv docs/MIGRATION_GUIDE.md docs/meta/
# Decide on PROJECT_CONFIG.md - may archive or move to meta
```

### Phase 3: Handle Special Cases

#### A. Merge Duplicate IMPLEMENTATION_SUMMARY.md

```bash
# Compare the two files
diff docs/dev/implementations/IMPLEMENTATION_SUMMARY.md docs/reports/IMPLEMENTATION_SUMMARY.md

# Strategy: Keep reports/ version (more comprehensive), add note from dev/ version if needed
# Then move to new location
mv docs/reports/IMPLEMENTATION_SUMMARY.md docs/investigations/reports/
rm docs/dev/implementations/IMPLEMENTATION_SUMMARY.md
```

#### B. Convert ADAPTERS.md to OVERVIEW.md

```bash
# Move and rename
mv docs/ADAPTERS.md docs/developer-docs/adapters/OVERVIEW.md

# Update internal references
# (Will be done in Phase 5)
```

#### C. Convert RST to Markdown (if needed)

For key RST files that are still referenced, create markdown equivalents:

```bash
# Priority conversions (manual process):
# 1. installation.rst → docs/user-docs/getting-started/INSTALLATION.md
# 2. cli.rst → docs/user-docs/guides/CLI_REFERENCE.md
# 3. examples.rst → docs/user-docs/guides/EXAMPLES.md

# Then archive original RST files
mv docs/installation.rst docs/_archive/rst-docs/
mv docs/cli.rst docs/_archive/rst-docs/
mv docs/examples.rst docs/_archive/rst-docs/
```

### Phase 4: Clean Up Empty Directories

```bash
# Remove now-empty directories
rmdir docs/guides 2>/dev/null
rmdir docs/quickstart 2>/dev/null
rmdir docs/prd 2>/dev/null
rmdir docs/development 2>/dev/null
rmdir docs/dev/implementations 2>/dev/null
rmdir docs/dev/test-reports 2>/dev/null
rmdir docs/dev 2>/dev/null
rmdir docs/reports 2>/dev/null

# Remove original directories after copying
rm -rf docs/features  # After copying to user-docs/features
rm -rf docs/api  # After copying to developer-docs/api
rm -rf docs/adapters  # After copying to developer-docs/adapters
rm -rf docs/setup  # After copying to integrations/setup
rm -rf docs/investigations  # After moving to new structure
```

### Phase 5: Update Cross-References

Files that need link updates:

#### Root README.md

```markdown
# OLD → NEW mappings

# Getting Started
[Quick Start Guide](QUICK_START.md) → [Quick Start Guide](user-docs/getting-started/QUICK_START.md)
[Installation Guide](installation.rst) → [Installation Guide](user-docs/getting-started/INSTALLATION.md)
[Environment Setup](QUICK_START_ENV.md) → [Environment Setup](user-docs/getting-started/CONFIGURATION.md)

# Configuration & Setup
[Configuration Guide](CONFIGURATION.md) → [Configuration Guide](user-docs/getting-started/CONFIGURATION.md)
[Environment Discovery](ENV_DISCOVERY.md) → [Environment Discovery](architecture/ENV_DISCOVERY.md)
[Project Configuration](PROJECT_CONFIG.md) → [Project Configuration](meta/PROJECT_CONFIG.md)

# User Guides
[User Guide](USER_GUIDE.md) → [User Guide](user-docs/guides/USER_GUIDE.md)
[CLI Reference](cli.rst) → [CLI Reference](user-docs/guides/CLI_REFERENCE.md)
[Examples](examples.rst) → [Examples](user-docs/guides/EXAMPLES.md)

# AI Client Integration
[AI Client Integration](AI_CLIENT_INTEGRATION.md) → [AI Client Integration](integrations/AI_CLIENT_INTEGRATION.md)
[MCP Integration](MCP_INTEGRATION.md) → [MCP Integration](architecture/MCP_INTEGRATION.md)
[Pull Request Integration](PR_INTEGRATION.md) → [Pull Request Integration](integrations/PR_INTEGRATION.md)

# Developer Documentation
[Developer Guide](DEVELOPER_GUIDE.md) → [Developer Guide](developer-docs/getting-started/DEVELOPER_GUIDE.md)
[API Reference](API_REFERENCE.md) → [API Reference](developer-docs/api/README.md)
[Adapter Development](ADAPTERS.md) → [Adapter Development](developer-docs/adapters/OVERVIEW.md)
[Code Structure](development/CODE_STRUCTURE.md) → [Code Structure](developer-docs/getting-started/CODE_STRUCTURE.md)
[Contributing Guide](development/CONTRIBUTING.md) → [Contributing Guide](developer-docs/getting-started/CONTRIBUTING.md)
[Release Process](development/RELEASING.md) → [Release Process](developer-docs/releasing/RELEASING.md)

# Architecture
[Queue System](QUEUE_SYSTEM.md) → [Queue System](architecture/QUEUE_SYSTEM.md)
[Configuration Resolution](CONFIG_RESOLUTION_FLOW.md) → [Configuration Resolution](architecture/CONFIG_RESOLUTION_FLOW.md)
[Migration Guide](MIGRATION_GUIDE.md) → [Migration Guide](meta/MIGRATION_GUIDE.md)

# Reports
[Test Coverage Report](reports/TEST_COVERAGE_REPORT.md) → [Test Coverage Report](investigations/reports/TEST_COVERAGE_REPORT.md)
[Performance Report](reports/OPTIMIZATION_SUMMARY.md) → [Performance Report](investigations/reports/OPTIMIZATION_SUMMARY.md)
[Security Scan](dev/test-reports/SECURITY_RESCAN_REPORT.md) → [Security Scan](investigations/reports/test-reports/SECURITY_RESCAN_REPORT.md)
[Implementation Summary](reports/IMPLEMENTATION_SUMMARY.md) → [Implementation Summary](investigations/reports/IMPLEMENTATION_SUMMARY.md)

# Platform Setup
[Linear Setup](setup/LINEAR_SETUP.md) → [Linear Setup](integrations/setup/LINEAR_SETUP.md)
[JIRA Setup](setup/JIRA_SETUP.md) → [JIRA Setup](integrations/setup/JIRA_SETUP.md)
[Claude Desktop Setup](setup/CLAUDE_DESKTOP_SETUP.md) → [Claude Desktop Setup](integrations/setup/CLAUDE_DESKTOP_SETUP.md)
[Codex Integration](setup/CODEX_INTEGRATION.md) → [Codex Integration](integrations/setup/CODEX_INTEGRATION.md)

# Development Documentation
[Development Documentation](dev/README.md) → [Development Documentation](developer-docs/README.md)
[Archive](_archive/README.md) → [Archive](_archive/README.md)  # No change
```

#### Files with Internal References

Search and update these files:

```bash
# Find all markdown files with internal doc links
grep -r "](.*\.md)" docs/user-docs/ docs/developer-docs/ docs/architecture/ docs/integrations/ --include="*.md"
grep -r "](.*\.rst)" docs/user-docs/ docs/developer-docs/ docs/architecture/ docs/integrations/ --include="*.md"

# Common patterns to update:
# - ../FILENAME.md → correct relative path
# - /docs/FILENAME.md → correct relative path
# - Links to moved files
```

Key files that likely need updates:
- All README.md files
- USER_GUIDE.md
- DEVELOPER_GUIDE.md
- CONTRIBUTING.md
- All setup/ files
- API documentation files

### Phase 6: Create New README Files

#### A. docs/user-docs/README.md

```markdown
# User Documentation

Documentation for end users of MCP Ticketer.

## Getting Started

New to MCP Ticketer? Start here:

1. **[Quick Start Guide](getting-started/QUICK_START.md)** - Get up and running in 5 minutes
2. **[Installation Guide](getting-started/INSTALLATION.md)** - Detailed installation instructions
3. **[Configuration Guide](getting-started/CONFIGURATION.md)** - Set up your environment

## Guides

- **[User Guide](guides/USER_GUIDE.md)** - Complete user documentation
- **[CLI Reference](guides/CLI_REFERENCE.md)** - Command-line interface guide
- **[Examples](guides/EXAMPLES.md)** - Practical usage examples
- **[Bulletproof Ticket Creation](guides/BULLETPROOF_TICKET_CREATION.md)** - Best practices for ticket creation
- **[Epic Attachments Guide](guides/EPIC_ATTACHMENTS.md)** - Working with epic attachments

## Features

- **[Ticket Instructions](features/ticket_instructions.md)** - Customizing ticket writing instructions
- **[Automatic Validation](features/AUTOMATIC_VALIDATION.md)** - Automatic ticket validation
- **[Update Checking](features/UPDATE_CHECKING.md)** - Version update checking

## Troubleshooting

- **[Common Issues](troubleshooting/COMMON_ISSUES.md)** - Solutions to common problems

## See Also

- [Integration Guides](../integrations/README.md) - Platform-specific setup guides
- [Developer Documentation](../developer-docs/README.md) - For contributors
- [Architecture Documentation](../architecture/README.md) - Technical deep-dives
```

#### B. docs/developer-docs/README.md

```markdown
# Developer Documentation

Documentation for developers contributing to MCP Ticketer.

## Getting Started

1. **[Developer Guide](getting-started/DEVELOPER_GUIDE.md)** - Complete development guide
2. **[Contributing Guide](getting-started/CONTRIBUTING.md)** - How to contribute
3. **[Code Structure](getting-started/CODE_STRUCTURE.md)** - Codebase architecture

## API Reference

- **[API Documentation](api/README.md)** - Complete API reference
- **[Epic Updates & Attachments](api/epic_updates_and_attachments.md)** - Epic-related APIs

## Adapters

- **[Adapter Overview](adapters/OVERVIEW.md)** - Understanding adapters
- **[GitHub Adapter](adapters/github.md)** - GitHub implementation
- **[Linear Adapter](adapters/LINEAR.md)** - Linear implementation
- **[Asana Adapter](adapters/ASANA.md)** - Asana implementation

## Release Management

- **[Release Process](releasing/RELEASING.md)** - How to create releases
- **[Versioning](releasing/VERSIONING.md)** - Version numbering scheme

## Testing

- **[Testing Guide](testing/TESTING_GUIDE.md)** - Writing and running tests

## See Also

- [Architecture Documentation](../architecture/README.md) - Technical design details
- [Investigation Reports](../investigations/README.md) - Analysis and investigation results
- [User Documentation](../user-docs/README.md) - End-user guides
```

#### C. docs/architecture/README.md

```markdown
# Architecture Documentation

Technical deep-dives into MCP Ticketer's architecture and design.

## Design Documents

- **[Product Design](DESIGN.md)** - Product requirements and design
- **[MCP Integration](MCP_INTEGRATION.md)** - Model Context Protocol integration

## System Architecture

- **[Queue System](QUEUE_SYSTEM.md)** - Async queue architecture
- **[Configuration Resolution](CONFIG_RESOLUTION_FLOW.md)** - Configuration loading flow
- **[Environment Discovery](ENV_DISCOVERY.md)** - Automatic environment detection

## See Also

- [Developer Documentation](../developer-docs/README.md) - Development guides
- [API Reference](../developer-docs/api/README.md) - API documentation
```

#### D. docs/integrations/README.md

```markdown
# Integration Guides

Guides for integrating MCP Ticketer with various platforms and AI clients.

## AI Client Integration

- **[AI Client Integration](AI_CLIENT_INTEGRATION.md)** - Multi-client MCP setup
- **[Pull Request Integration](PR_INTEGRATION.md)** - GitHub PR automation
- **[Attachments](ATTACHMENTS.md)** - Working with attachments

## Platform Setup Guides

- **[Claude Desktop Setup](setup/CLAUDE_DESKTOP_SETUP.md)** - Claude Desktop integration
- **[Codex Integration](setup/CODEX_INTEGRATION.md)** - Codex CLI integration
- **[Linear Setup](setup/LINEAR_SETUP.md)** - Linear integration setup
- **[JIRA Setup](setup/JIRA_SETUP.md)** - JIRA integration setup

## See Also

- [User Documentation](../user-docs/README.md) - General usage guides
- [Developer Documentation](../developer-docs/README.md) - API and adapter development
```

#### E. docs/investigations/README.md

```markdown
# Investigation Reports & Analysis

Documentation of investigations, analysis, and research conducted on MCP Ticketer.

## Active Investigations

### Asana Adapter

- **[Asana Investigation Report](asana/ASANA_INVESTIGATION_REPORT.md)** - Investigation into missing test tickets
- **[Asana Priority & Status Findings](asana/ASANA_PRIORITY_STATUS_FINDINGS.md)** - Priority and status mapping analysis

## Reports

### Performance & Coverage

- **[Optimization Summary](reports/OPTIMIZATION_SUMMARY.md)** - Performance improvements
- **[Test Coverage Report](reports/TEST_COVERAGE_REPORT.md)** - Test coverage analysis
- **[Implementation Summary](reports/IMPLEMENTATION_SUMMARY.md)** - Feature implementation status

### Test Reports

- **[Security Rescan Report](reports/test-reports/SECURITY_RESCAN_REPORT.md)** - Security analysis
- **[Epic Attachments Test Report](reports/test-reports/TEST_REPORT_EPIC_ATTACHMENTS.md)** - Epic attachments testing

## Implementation Documentation

Historical implementation documentation for features and bug fixes.

- **[Implementation Reports Index](implementations/README.md)** - All implementation reports

## Archive

For historical reports and summaries, see [Archive Documentation](../_archive/README.md).

## See Also

- [Architecture Documentation](../architecture/README.md) - System design details
- [Developer Documentation](../developer-docs/README.md) - Development guides
```

#### F. docs/investigations/implementations/README.md

```markdown
# Implementation Reports

Documentation of feature implementations and bug fixes.

## Recent Implementations

All implementation reports are listed below in chronological order (newest first):

<!-- List will be generated from directory contents -->

## Archive

Older implementation reports have been moved to the [Archive](../../_archive/implementations/).

## See Also

- [Investigation Reports](../README.md) - Main investigations index
- [Test Reports](../reports/test-reports/) - Test-related reports
```

#### G. docs/meta/README.md (NEW)

```markdown
# Meta Documentation

Documentation about the documentation itself, migration guides, and project configuration.

## Documentation Management

- **[Documentation Cleanup Analysis](DOCUMENTATION_CLEANUP_ANALYSIS.md)** - Analysis of documentation cleanup needs
- **[Cleanup Execution Report](CLEANUP_EXECUTION_REPORT.md)** - Results of documentation cleanup

## Migration & Configuration

- **[Migration Guide](MIGRATION_GUIDE.md)** - Version migration guide
- **[Project Configuration](PROJECT_CONFIG.md)** - Project-level configuration
- **[Security Best Practices](SECURITY.md)** - Security and credential management

## See Also

- [Main Documentation](../README.md) - Documentation hub
- [Contributing Guide](../developer-docs/getting-started/CONTRIBUTING.md) - How to contribute
```

### Phase 7: Update Root README.md

The root README.md needs a complete rewrite to reflect the new structure. Key sections:

```markdown
# MCP Ticketer Documentation

Welcome to the comprehensive documentation for MCP Ticketer - the universal ticket management interface for AI agents.

## Documentation Structure

Our documentation is organized by audience and purpose:

### 👥 [User Documentation](user-docs/README.md)
For end users of MCP Ticketer
- Getting started guides
- User guide and CLI reference
- Feature documentation
- Examples and troubleshooting

### 👨‍💻 [Developer Documentation](developer-docs/README.md)
For contributors and developers
- Developer guide and contributing guidelines
- API reference
- Adapter development
- Release management

### 🏛️ [Architecture Documentation](architecture/README.md)
Technical deep-dives and design documents
- System architecture
- Design documents
- Integration architecture

### 🔌 [Integration Guides](integrations/README.md)
Platform-specific setup and integration
- AI client integration
- Platform setup guides (Linear, JIRA, Claude Desktop, etc.)
- Pull request integration

### 🔍 [Investigation Reports](investigations/README.md)
Analysis, research, and investigation results
- Adapter investigations
- Performance reports
- Test coverage reports
- Implementation documentation

### 🗄️ [Archive](_archive/README.md)
Historical documentation and older reports

### 📋 [Meta Documentation](meta/README.md)
Documentation about documentation, migrations, and configuration

## Quick Start Paths

### I'm a new user
1. [Quick Start Guide](user-docs/getting-started/QUICK_START.md)
2. [Installation Guide](user-docs/getting-started/INSTALLATION.md)
3. [Configuration Guide](user-docs/getting-started/CONFIGURATION.md)
4. [User Guide](user-docs/guides/USER_GUIDE.md)

### I want to integrate with an AI client
1. [AI Client Integration](integrations/AI_CLIENT_INTEGRATION.md)
2. Choose your platform: [Claude Desktop](integrations/setup/CLAUDE_DESKTOP_SETUP.md), [Codex](integrations/setup/CODEX_INTEGRATION.md)
3. [Examples](user-docs/guides/EXAMPLES.md)

### I want to contribute
1. [Developer Guide](developer-docs/getting-started/DEVELOPER_GUIDE.md)
2. [Contributing Guide](developer-docs/getting-started/CONTRIBUTING.md)
3. [Code Structure](developer-docs/getting-started/CODE_STRUCTURE.md)

### I need to understand the architecture
1. [Architecture Overview](architecture/README.md)
2. [MCP Integration](architecture/MCP_INTEGRATION.md)
3. [API Reference](developer-docs/api/README.md)

## Documentation Standards

- **Format**: Markdown (`.md`) for all active documentation
- **Organization**: Audience-based directory structure
- **Links**: Relative links within documentation
- **Updates**: Documentation updated with each release
- **Archive**: Historical docs moved to `_archive/`

## Getting Help

- **Missing Information**: Open an issue describing what's missing
- **Unclear Instructions**: Submit a pull request with improvements
- **Broken Examples**: Report with steps to reproduce
- **General Questions**: Check [User Guide](user-docs/guides/USER_GUIDE.md) or [Discussions](https://github.com/org/mcp-ticketer/discussions)

---

**Last Updated**: November 2025
**Documentation Version**: 2.0
```

---

## Execution Checklist

### Pre-Execution

- [ ] Review this plan with stakeholders
- [ ] Backup current docs/ directory: `cp -r docs docs-backup-$(date +%Y%m%d)`
- [ ] Create a new git branch: `git checkout -b docs-restructure`
- [ ] Ensure no uncommitted changes in docs/

### Execution Order

- [ ] **Phase 1**: Create new directory structure (5 minutes)
- [ ] **Phase 2**: Move files to new locations (15 minutes)
- [ ] **Phase 3**: Handle special cases (merge duplicates, conversions) (20 minutes)
- [ ] **Phase 4**: Clean up empty directories (5 minutes)
- [ ] **Phase 5**: Update cross-references (30 minutes)
- [ ] **Phase 6**: Create new README files (30 minutes)
- [ ] **Phase 7**: Update root README.md (15 minutes)

**Total Estimated Time**: 2 hours

### Post-Execution Verification

- [ ] All files accounted for (no missing files)
- [ ] No broken internal links
- [ ] All README files created
- [ ] Root README.md updated
- [ ] Git status shows expected changes
- [ ] Test navigation paths from root README
- [ ] Verify investigation reports are accessible
- [ ] Check that RST files are archived
- [ ] Ensure no duplicate content exists
- [ ] Review with `tree docs/ -L 3`

### Validation Commands

```bash
# Count files before and after
find docs-backup-* -name "*.md" | wc -l
find docs -name "*.md" | wc -l

# Check for broken links (requires markdown-link-check)
find docs -name "*.md" -exec markdown-link-check {} \;

# Verify no RST files in active docs (should only be in _archive)
find docs -name "*.rst" ! -path "docs/_archive/*"

# Check for duplicate filenames
find docs -name "*.md" ! -path "docs/_archive/*" -exec basename {} \; | sort | uniq -d

# Visualize new structure
tree docs -L 3 -I "_archive"
```

---

## Files to Delete (After Migration Complete)

These empty directories should be removed after confirming all files have been moved:

```bash
# These will be empty after migration
docs/guides/
docs/quickstart/
docs/prd/
docs/development/
docs/dev/implementations/
docs/dev/test-reports/
docs/dev/
docs/reports/

# These are replaced by new structure
docs/features/       # After copying to user-docs/features/
docs/api/            # After copying to developer-docs/api/
docs/adapters/       # After copying to developer-docs/adapters/
docs/setup/          # After copying to integrations/setup/
docs/investigations/ # After reorganizing into new structure
```

---

## Known Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Broken external links | Medium | Search GitHub issues/PRs for links to docs/ |
| RST still in use | Low | Check if Sphinx build is still active |
| Duplicate merge conflicts | Low | Manual review of IMPLEMENTATION_SUMMARY.md merge |
| Large git diff | Low | Split into multiple commits by phase |
| Lost historical context | Medium | Maintain _archive/ structure, add archive READMEs |

---

## Success Metrics

After execution, we should see:

- ✅ **Clear separation** of user vs developer vs architecture docs
- ✅ **Zero duplicate** files (except in _archive)
- ✅ **100% working** internal documentation links
- ✅ **Intuitive navigation** from README to any doc in <3 clicks
- ✅ **Investigation reports** properly organized and indexed
- ✅ **All RST files** archived (not deleted)
- ✅ **Consistent structure** across all subdirectories

---

## Appendix: File Movement Matrix

### Complete File Mapping

| Current Location | New Location | Action |
|------------------|--------------|--------|
| QUICK_START.md | user-docs/getting-started/QUICK_START.md | Move |
| CONFIGURATION.md | user-docs/getting-started/CONFIGURATION.md | Move |
| installation.rst | user-docs/getting-started/INSTALLATION.md | Convert + Archive RST |
| USER_GUIDE.md | user-docs/guides/USER_GUIDE.md | Move |
| cli.rst | user-docs/guides/CLI_REFERENCE.md | Convert + Archive RST |
| examples.rst | user-docs/guides/EXAMPLES.md | Convert + Archive RST |
| guides/BULLETPROOF_TICKET_CREATION_GUIDE.md | user-docs/guides/BULLETPROOF_TICKET_CREATION.md | Move |
| quickstart/epic_attachments.md | user-docs/guides/EPIC_ATTACHMENTS.md | Move |
| features/* | user-docs/features/* | Copy |
| DEVELOPER_GUIDE.md | developer-docs/getting-started/DEVELOPER_GUIDE.md | Move |
| development/CONTRIBUTING.md | developer-docs/getting-started/CONTRIBUTING.md | Move |
| development/CODE_STRUCTURE.md | developer-docs/getting-started/CODE_STRUCTURE.md | Move |
| development/RELEASING.md | developer-docs/releasing/RELEASING.md | Move |
| development/VERSIONING.md | developer-docs/releasing/VERSIONING.md | Move |
| api/* | developer-docs/api/* | Copy |
| adapters/* | developer-docs/adapters/* | Copy |
| ADAPTERS.md | developer-docs/adapters/OVERVIEW.md | Move + Rename |
| adapters.rst | _archive/rst-docs/adapters.rst | Archive |
| api.rst | _archive/rst-docs/api.rst | Archive |
| development.rst | _archive/rst-docs/development.rst | Archive |
| QUEUE_SYSTEM.md | architecture/QUEUE_SYSTEM.md | Move |
| CONFIG_RESOLUTION_FLOW.md | architecture/CONFIG_RESOLUTION_FLOW.md | Move |
| ENV_DISCOVERY.md | architecture/ENV_DISCOVERY.md | Move |
| MCP_INTEGRATION.md | architecture/MCP_INTEGRATION.md | Move |
| prd/mcp-ticketer-prd.md | architecture/DESIGN.md | Move + Rename |
| AI_CLIENT_INTEGRATION.md | integrations/AI_CLIENT_INTEGRATION.md | Move |
| PR_INTEGRATION.md | integrations/PR_INTEGRATION.md | Move |
| ATTACHMENTS.md | integrations/ATTACHMENTS.md | Move |
| setup/* | integrations/setup/* | Copy |
| investigations/ASANA_INVESTIGATION_REPORT.md | investigations/asana/ASANA_INVESTIGATION_REPORT.md | Move |
| investigations/ASANA_PRIORITY_STATUS_FINDINGS.md | investigations/asana/ASANA_PRIORITY_STATUS_FINDINGS.md | Move |
| reports/IMPLEMENTATION_SUMMARY.md | investigations/reports/IMPLEMENTATION_SUMMARY.md | Move (merge) |
| reports/OPTIMIZATION_SUMMARY.md | investigations/reports/OPTIMIZATION_SUMMARY.md | Move |
| reports/TEST_COVERAGE_REPORT.md | investigations/reports/TEST_COVERAGE_REPORT.md | Move |
| dev/test-reports/SECURITY_RESCAN_REPORT.md | investigations/reports/test-reports/SECURITY_RESCAN_REPORT.md | Move |
| dev/test-reports/TEST_REPORT_EPIC_ATTACHMENTS.md | investigations/reports/test-reports/TEST_REPORT_EPIC_ATTACHMENTS.md | Move |
| dev/implementations/* | investigations/implementations/* | Move |
| dev/implementations/IMPLEMENTATION_SUMMARY.md | (deleted after merge) | Delete |
| DOCUMENTATION_CLEANUP_ANALYSIS.md | meta/DOCUMENTATION_CLEANUP_ANALYSIS.md | Move |
| CLEANUP_EXECUTION_REPORT.md | meta/CLEANUP_EXECUTION_REPORT.md | Move |
| SECURITY.md | meta/SECURITY.md | Move |
| MIGRATION_GUIDE.md | meta/MIGRATION_GUIDE.md | Move |
| PROJECT_CONFIG.md | meta/PROJECT_CONFIG.md | Move |

---

## Notes for Execution

1. **RST Conversion**: The RST files (installation.rst, cli.rst, examples.rst) need manual conversion to Markdown. Consider using `pandoc` for initial conversion, then manual cleanup.

2. **IMPLEMENTATION_SUMMARY Merge**: Compare both files carefully. The one in `reports/` appears to be more comprehensive based on file sizes (14K vs 5.2K).

3. **Git Commits**: Consider creating separate commits for each phase:
   - Phase 1-2: "docs: create new directory structure and move files"
   - Phase 3: "docs: merge duplicates and convert RST files"
   - Phase 4: "docs: clean up empty directories"
   - Phase 5: "docs: update cross-references"
   - Phase 6-7: "docs: create navigation READMEs"

4. **Testing**: After migration, test all links with a tool like `markdown-link-check` or manually navigate through the documentation following different user paths.

5. **Communication**: If this is a public project, announce the documentation restructure in release notes and provide a migration guide for external links.

---

**Plan Status**: ✅ READY FOR EXECUTION
**Estimated Impact**: HIGH (improved usability, discoverability, maintainability)
**Risk Level**: LOW (all changes reversible, backup required)
