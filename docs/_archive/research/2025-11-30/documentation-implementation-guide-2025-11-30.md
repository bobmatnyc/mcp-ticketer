# Documentation Restructuring Implementation Guide

**Companion to**: documentation-architecture-proposal-2025-11-30.md
**Purpose**: Step-by-step commands for executing the documentation restructure
**Date**: 2025-11-30

---

## Quick Reference

### Before/After Comparison

#### Current State (Before)
```
docs/
├── 11 files in root (CLUTTERED)
├── 40+ directories (TOO MANY)
├── 19 active research files (BLOAT)
├── 4 duplicate directories (REDUNDANT)
├── Max 4+ level depth (TOO DEEP)
└── 225 total markdown files
```

#### Target State (After)
```
docs/
├── 2 files in root (CLEAN: README.md, RELEASE.md)
├── ~25 directories (STREAMLINED)
├── 0 active research files (ARCHIVED)
├── 0 duplicate directories (CONSOLIDATED)
├── Max 3 level depth (FLAT)
└── 225 total markdown files (REORGANIZED)
```

### Improvement Summary

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Root files | 11 | 2 | **-82%** |
| Directories | 40+ | ~25 | **-38%** |
| Research bloat | 19 | 0 | **-100%** |
| Duplicates | 4 | 0 | **-100%** |
| Max depth | 4+ | 3 | **Flatter** |

---

## Visual Decision Tree

### Where Should This File Go?

```
                    ┌──────────────────────────────────┐
                    │  START: Categorizing a file      │
                    └──────────────────────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
                    ▼                                 ▼
        ┌─────────────────────┐         ┌─────────────────────┐
        │ Is it timestamped?  │         │ Is it version-      │
        │ (YYYY-MM-DD)        │         │ specific (vX.Y.Z)?  │
        └─────────────────────┘         └─────────────────────┘
                    │                                 │
                    │ YES                             │ YES
                    ▼                                 ▼
        ┌─────────────────────┐         ┌─────────────────────┐
        │ Archive to:         │         │ Version age?        │
        │ _archive/research/  │         └─────────────────────┘
        │ YYYY-MM-DD/         │                     │
        └─────────────────────┘         ┌───────────┴───────────┐
                                        │                       │
                                        ▼                       ▼
                            ┌──────────────────┐  ┌──────────────────┐
                            │ Current or       │  │ 2+ versions old? │
                            │ previous major?  │  │                  │
                            └──────────────────┘  └──────────────────┘
                                        │                       │
                                        │ YES                   │ YES
                                        ▼                       ▼
                            ┌──────────────────┐  ┌──────────────────┐
                            │ Keep in:         │  │ Archive to:      │
                            │ migration/       │  │ _archive/        │
                            │                  │  │ releases/vX.Y.x/ │
                            └──────────────────┘  └──────────────────┘

        ┌─────────────────────────────────────────────────────┐
        │ NO (not timestamped, not version-specific)          │
        └─────────────────────────────────────────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
                    ▼                                 ▼
        ┌─────────────────────┐         ┌─────────────────────┐
        │ Is it for end       │         │ Is it for           │
        │ users/AI agents?    │         │ developers?         │
        └─────────────────────┘         └─────────────────────┘
                    │                                 │
                    │ YES                             │ YES
                    ▼                                 ▼
        ┌─────────────────────┐         ┌─────────────────────┐
        │ Topic?              │         │ Topic?              │
        └─────────────────────┘         └─────────────────────┘
                    │                                 │
        ┌───────────┴──────────┐          ┌──────────┴──────────┐
        │                      │          │                     │
        ▼                      ▼          ▼                     ▼
┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────────┐
│Getting started│  │Feature docs │  │API docs  │  │Adapter dev   │
│              │  │             │  │          │  │              │
│user-docs/    │  │user-docs/   │  │developer-│  │developer-    │
│getting-      │  │features/    │  │docs/api/ │  │docs/adapters/│
│started/      │  │             │  │          │  │              │
└──────────────┘  └──────────────┘  └──────────┘  └──────────────┘

        ▼                      ▼          ▼                     ▼
┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────────┐
│How-to guides │  │Troubleshoot  │  │Testing   │  │Release mgmt  │
│              │  │              │  │          │  │              │
│user-docs/    │  │user-docs/    │  │developer-│  │developer-    │
│guides/       │  │troubleshoot/ │  │docs/     │  │docs/         │
│              │  │              │  │testing/  │  │releasing/    │
└──────────────┘  └──────────────┘  └──────────┘  └──────────────┘

                            ┌─────────────────────┐
                            │ Neither user nor    │
                            │ developer focused?  │
                            └─────────────────────┘
                                        │
                        ┌───────────────┴───────────────┐
                        │                               │
                        ▼                               ▼
            ┌─────────────────────┐     ┌─────────────────────┐
            │ System design/      │     │ Platform-specific   │
            │ architecture?       │     │ integration?        │
            └─────────────────────┘     └─────────────────────┘
                        │                               │
                        │ YES                           │ YES
                        ▼                               ▼
            ┌─────────────────────┐     ┌─────────────────────┐
            │ architecture/       │     │ integrations/       │
            │                     │     │ setup/              │
            └─────────────────────┘     └─────────────────────┘
```

### Archive Decision Tree

```
                    ┌──────────────────────────────────┐
                    │  Should this file be archived?   │
                    └──────────────────────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
                    ▼                                 ▼
        ┌─────────────────────┐         ┌─────────────────────┐
        │ Is it a ticket-     │         │ Is it timestamped   │
        │ specific impl       │         │ research?           │
        │ summary?            │         └─────────────────────┘
        └─────────────────────┘                     │
                    │                               │ YES
                    │ YES                           ▼
                    ▼                   ┌─────────────────────┐
        ┌─────────────────────┐         │ >30 days old?       │
        │ Archive immediately │         └─────────────────────┘
        │ to:                 │                     │
        │ _archive/           │         ┌───────────┴───────────┐
        │ implementations/    │         │ YES                   │ NO
        │ YYYY-MM-DD/         │         ▼                       ▼
        └─────────────────────┘ ┌──────────────┐   ┌─────────────────┐
                                │Archive to:   │   │Keep in:         │
                                │_archive/     │   │investigations/  │
                                │research/     │   │(active research)│
                                │YYYY-MM-DD/   │   └─────────────────┘
                                └──────────────┘

                    ┌─────────────────────┐
                    │ Is it a release     │
                    │ verification/test?  │
                    └─────────────────────┘
                                │
                                │ YES
                                ▼
                    ┌─────────────────────┐
                    │ Version age?        │
                    └─────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
                ▼                               ▼
    ┌──────────────────┐          ┌──────────────────┐
    │ 2+ versions old? │          │ Current/previous │
    │                  │          │ major version?   │
    └──────────────────┘          └──────────────────┘
                │                               │
                │ YES                           │ YES
                ▼                               ▼
    ┌──────────────────┐          ┌──────────────────┐
    │ Archive to:      │          │ Keep in:         │
    │ _archive/        │          │ migration/ or    │
    │ releases/vX.Y.x/ │          │ releases/        │
    └──────────────────┘          └──────────────────┘
```

---

## Phase-by-Phase Commands

### Phase 1: Archive Research Files (19 files)

**Risk**: ✅ LOW | **Impact**: 🔥 HIGH | **Duration**: 15 minutes

#### Step 1.1: Create Archive Directories

```bash
cd /Users/masa/Projects/mcp-ticketer

# Create dated research archive directories
mkdir -p docs/_archive/research/2025-11-26
mkdir -p docs/_archive/research/2025-11-28
mkdir -p docs/_archive/research/2025-11-29
mkdir -p docs/_archive/research/2025-11-30
```

#### Step 1.2: Archive November 26 Research (2 files)

```bash
# Move 2025-11-26 files
git mv docs/research/linear-workflow-script-analysis-2025-11-26.md \
  docs/_archive/research/2025-11-26/

git mv docs/research/project-updates-cross-platform-investigation-2025-11-26.md \
  docs/_archive/research/2025-11-26/

# Commit
git commit -m "docs: archive research files from November 26, 2025 (Phase 1a)"
```

#### Step 1.3: Archive November 28 Research (3 files)

```bash
# Move 2025-11-28 files
git mv docs/research/priority-semantic-mapping-analysis-2025-11-28.md \
  docs/_archive/research/2025-11-28/

git mv docs/research/token-usage-analysis-20k-pagination-2025-11-28.md \
  docs/_archive/research/2025-11-28/

git mv docs/research/workflow-state-handling-fix-analysis-2025-11-28.md \
  docs/_archive/research/2025-11-28/

# Commit
git commit -m "docs: archive research files from November 28, 2025 (Phase 1b)"
```

#### Step 1.4: Archive November 29 Research (6 files)

```bash
# Move 2025-11-29 files
git mv docs/research/documentation-gap-analysis-2025-11-29.md \
  docs/_archive/research/2025-11-29/

git mv docs/research/linear-label-creation-silent-failure-1M-398-2025-11-29.md \
  docs/_archive/research/2025-11-29/

git mv docs/research/linear-label-update-failure-analysis-2025-11-29.md \
  docs/_archive/research/2025-11-29/

git mv docs/research/linear-url-structure-analysis-2025-11-29.md \
  docs/_archive/research/2025-11-29/

git mv docs/research/mcp-profile-token-optimization-2025-11-29.md \
  docs/_archive/research/2025-11-29/

git mv docs/research/project-filtering-gap-analysis-2025-11-29.md \
  docs/_archive/research/2025-11-29/

# Commit
git commit -m "docs: archive research files from November 29, 2025 (Phase 1c)"
```

#### Step 1.5: Archive November 30 Research (8 files)

```bash
# Move 2025-11-30 files
git mv docs/research/auto-remove-implementation-design-2025-11-30.md \
  docs/_archive/research/2025-11-30/

git mv docs/research/auto-remove-implementation-summary.md \
  docs/_archive/research/2025-11-30/

git mv docs/research/claude-code-native-mcp-setup-2025-11-30.md \
  docs/_archive/research/2025-11-30/

git mv docs/research/label-duplicate-error-investigation-1M-443-2025-11-30.md \
  docs/_archive/research/2025-11-30/

git mv docs/research/label-duplicate-error-root-cause-2025-11-30.md \
  docs/_archive/research/2025-11-30/

git mv docs/research/linear-api-connection-failure-analysis-2025-11-30.md \
  docs/_archive/research/2025-11-30/

git mv docs/research/linear-state-transitions-investigation-2025-11-30.md \
  docs/_archive/research/2025-11-30/

git mv docs/research/mcp-installation-setup-analysis-2025-11-30.md \
  docs/_archive/research/2025-11-30/

# Commit
git commit -m "docs: archive research files from November 30, 2025 (Phase 1d)"
```

#### Step 1.6: Remove Empty Research Directory

```bash
# Verify research/ is empty (except this proposal)
ls docs/research/

# If empty (or only contains this proposal), delete it
# (Or keep if we want to continue using it for future research)

# Commit if deleted
# git commit -m "docs: remove empty research directory (Phase 1 complete)"
```

#### Step 1.7: Validation

```bash
# Verify all files archived
ls docs/_archive/research/2025-11-26/
ls docs/_archive/research/2025-11-28/
ls docs/_archive/research/2025-11-29/
ls docs/_archive/research/2025-11-30/

# Check for any references to old paths
grep -r "docs/research/" /Users/masa/Projects/mcp-ticketer/docs/ \
  --exclude-dir=_archive \
  --exclude-dir=.git

# Count: Should be 19 files in archive
find docs/_archive/research/2025-11-* -type f -name "*.md" | wc -l
```

---

### Phase 2: Archive Root Implementation Files (4 files)

**Risk**: ✅ LOW | **Impact**: 🔥 MEDIUM | **Duration**: 10 minutes

#### Step 2.1: Create Archive Directory

```bash
cd /Users/masa/Projects/mcp-ticketer

# Create implementations archive directory
mkdir -p docs/_archive/implementations/2025-11-30
```

#### Step 2.2: Archive Implementation Summaries

```bash
# Move implementation files
git mv docs/implementation-summary-1M-443.md \
  docs/_archive/implementations/2025-11-30/

git mv docs/DOCSTRING_OPTIMIZATION_COMPLETION.md \
  docs/_archive/implementations/2025-11-30/

git mv docs/github_url_refactor_changes.md \
  docs/_archive/implementations/2025-11-30/

git mv docs/phase1-optimization-results.md \
  docs/_archive/implementations/2025-11-30/

# Commit
git commit -m "docs: archive implementation summaries to _archive/implementations (Phase 2)"
```

#### Step 2.3: Validation

```bash
# Verify all files archived
ls docs/_archive/implementations/2025-11-30/

# Check for any references (exclude archive and git)
grep -r "implementation-summary-1M-443" /Users/masa/Projects/mcp-ticketer/ \
  --exclude-dir=_archive \
  --exclude-dir=.git

# Count: Should be 4 files
find docs/_archive/implementations/2025-11-30/ -type f -name "*.md" | wc -l
```

---

### Phase 3: Move Root Files to Sections (5 files)

**Risk**: ⚠️ MEDIUM | **Impact**: 🔥 HIGH | **Duration**: 20 minutes

#### Step 3.1: Create New Directories

```bash
cd /Users/masa/Projects/mcp-ticketer

# Create reference directory (new)
mkdir -p docs/reference
```

#### Step 3.2: Move Feature Docs to user-docs/features/

```bash
# Move semantic priority matching
git mv docs/SEMANTIC_PRIORITY_MATCHING.md \
  docs/user-docs/features/semantic-priority-matching.md

# Move token pagination
git mv docs/TOKEN_PAGINATION.md \
  docs/user-docs/features/token-pagination.md

# Commit
git commit -m "docs: move feature docs from root to user-docs/features/ (Phase 3a)"
```

#### Step 3.3: Move API Reference to developer-docs/api/

```bash
# Move MCP API reference
git mv docs/mcp-api-reference.md \
  docs/developer-docs/api/mcp-api-reference.md

# Commit
git commit -m "docs: move API reference from root to developer-docs/api/ (Phase 3b)"
```

#### Step 3.4: Move Adapter Docs to developer-docs/adapters/

```bash
# Move Linear URL documentation summary
git mv docs/LINEAR_URL_DOCUMENTATION_SUMMARY.md \
  docs/developer-docs/adapters/linear-url-summary.md

# Commit
git commit -m "docs: move adapter docs from root to developer-docs/adapters/ (Phase 3c)"
```

#### Step 3.5: Move Reference Docs to reference/

```bash
# Move project status
git mv docs/PROJECT_STATUS.md \
  docs/reference/project-status.md

# Commit
git commit -m "docs: move reference docs from root to reference/ (Phase 3d)"
```

#### Step 3.6: Update README Indexes

**Create/Update**: `docs/user-docs/features/README.md`

Add to file:
```markdown
- **[Semantic Priority Matching](semantic-priority-matching.md)** - Natural language priority mapping
- **[Token Pagination](token-pagination.md)** - Efficient token usage for large result sets
```

**Create/Update**: `docs/developer-docs/api/README.md`

Add to file:
```markdown
- **[MCP API Reference](mcp-api-reference.md)** - Complete MCP tool reference
```

**Create/Update**: `docs/developer-docs/adapters/README.md`

Add to file:
```markdown
- **[Linear URL Summary](linear-url-summary.md)** - Linear URL parsing and handling
```

**Create**: `docs/reference/README.md`

```markdown
# Reference Documentation

Technical specifications and reference material.

## Contents

- **[Project Status](project-status.md)** - Current project status and metrics

---

**Last Updated**: 2025-11-30
```

Commit README updates:
```bash
git add docs/user-docs/features/README.md
git add docs/developer-docs/api/README.md
git add docs/developer-docs/adapters/README.md
git add docs/reference/README.md

git commit -m "docs: update section README files for Phase 3 moves"
```

#### Step 3.7: Validation

```bash
# Verify files moved
ls docs/user-docs/features/semantic-priority-matching.md
ls docs/user-docs/features/token-pagination.md
ls docs/developer-docs/api/mcp-api-reference.md
ls docs/developer-docs/adapters/linear-url-summary.md
ls docs/reference/project-status.md

# Check for broken references
grep -r "SEMANTIC_PRIORITY_MATCHING.md" /Users/masa/Projects/mcp-ticketer/docs/ \
  --exclude-dir=_archive

grep -r "TOKEN_PAGINATION.md" /Users/masa/Projects/mcp-ticketer/docs/ \
  --exclude-dir=_archive

grep -r "mcp-api-reference.md" /Users/masa/Projects/mcp-ticketer/docs/ \
  --exclude-dir=_archive

# Verify root is clean (should only have README.md, RELEASE.md, CHANGELOG.md)
ls docs/*.md
```

---

### Phase 4: Consolidate Duplicate Directories (4 files)

**Risk**: ⚠️ MEDIUM | **Impact**: 🔥 MEDIUM | **Duration**: 15 minutes

#### Step 4.1: Merge dev/ into developer-docs/

```bash
cd /Users/masa/Projects/mcp-ticketer

# Read current dev/README.md to see if content should be merged
cat docs/dev/README.md

# If content is valuable, merge it into developer-docs/README.md or create new file
# Otherwise, just move it
git mv docs/dev/README.md \
  docs/developer-docs/dev-guide.md

# Remove empty directory
rmdir docs/dev/

# Commit
git commit -m "docs: consolidate dev/ into developer-docs/ (Phase 4a)"
```

#### Step 4.2: Merge development/ into developer-docs/getting-started/

```bash
# Move LOCAL_MCP_SETUP.md
git mv docs/development/LOCAL_MCP_SETUP.md \
  docs/developer-docs/getting-started/LOCAL_MCP_SETUP.md

# Remove empty directory
rmdir docs/development/

# Commit
git commit -m "docs: consolidate development/ into developer-docs/getting-started/ (Phase 4b)"
```

#### Step 4.3: Merge release/ into _archive/releases/

```bash
# Create v1.1.x archive directory
mkdir -p docs/_archive/releases/v1.1.x

# Move old release verification
git mv docs/release/v1.1.5-verification-report.md \
  docs/_archive/releases/v1.1.x/v1.1.5-verification-report.md

# Remove empty directory
rmdir docs/release/

# Commit
git commit -m "docs: archive release/ into _archive/releases/v1.1.x/ (Phase 4c)"
```

#### Step 4.4: Merge verification/ into _archive/releases/

```bash
# Create v1.4.x archive directory
mkdir -p docs/_archive/releases/v1.4.x

# Move v1.4.4 verification
git mv docs/verification/v1.4.4-verification-report.md \
  docs/_archive/releases/v1.4.x/v1.4.4-verification-report.md

# Remove empty directory
rmdir docs/verification/

# Commit
git commit -m "docs: archive verification/ into _archive/releases/v1.4.x/ (Phase 4d)"
```

#### Step 4.5: Update developer-docs/getting-started/README.md

Add to file:
```markdown
- **[Local MCP Setup](LOCAL_MCP_SETUP.md)** - Local development MCP configuration
```

Commit:
```bash
git add docs/developer-docs/getting-started/README.md
git commit -m "docs: update developer getting-started README for LOCAL_MCP_SETUP"
```

#### Step 4.6: Validation

```bash
# Verify directories removed
ls -ld docs/dev/ 2>/dev/null          # Should not exist
ls -ld docs/development/ 2>/dev/null  # Should not exist
ls -ld docs/release/ 2>/dev/null      # Should not exist
ls -ld docs/verification/ 2>/dev/null # Should not exist

# Verify files moved
ls docs/developer-docs/dev-guide.md
ls docs/developer-docs/getting-started/LOCAL_MCP_SETUP.md
ls docs/_archive/releases/v1.1.x/v1.1.5-verification-report.md
ls docs/_archive/releases/v1.4.x/v1.4.4-verification-report.md

# Count directories eliminated: Should be 4
```

---

### Phase 5: Archive Old Releases (11 files)

**Risk**: ✅ LOW | **Impact**: 🔥 MEDIUM | **Duration**: 15 minutes

#### Step 5.1: Ensure Archive Directory Exists

```bash
cd /Users/masa/Projects/mcp-ticketer

# Already created in Phase 4, but verify
mkdir -p docs/_archive/releases/v1.1.x
```

#### Step 5.2: Archive v1.1.6 Documentation (8 files)

```bash
# Move all v1.1.6 files
git mv docs/releases/v1.1.6-bugfix-url-extraction.md \
  docs/_archive/releases/v1.1.x/

git mv docs/releases/v1.1.6-phase1-qa-report.md \
  docs/_archive/releases/v1.1.x/

git mv docs/releases/v1.1.6-quality-gate.md \
  docs/_archive/releases/v1.1.x/

git mv docs/releases/v1.1.6-router-valueerror-test-report.md \
  docs/_archive/releases/v1.1.x/

git mv docs/releases/v1.1.6-security-scan-report.md \
  docs/_archive/releases/v1.1.x/

git mv docs/releases/v1.1.6-security-summary.md \
  docs/_archive/releases/v1.1.x/

git mv docs/releases/v1.1.6-test-report.md \
  docs/_archive/releases/v1.1.x/

git mv docs/releases/v1.1.6-ticket-scoping-docs.md \
  docs/_archive/releases/v1.1.x/

# Commit
git commit -m "docs: archive v1.1.6 release documentation (Phase 5a)"
```

#### Step 5.3: Archive v1.1.7 Documentation (3 files)

```bash
# Move all v1.1.7 files
git mv docs/releases/v1.1.7-quality-gate-complete-output.md \
  docs/_archive/releases/v1.1.x/

git mv docs/releases/v1.1.7-quality-gate-summary.md \
  docs/_archive/releases/v1.1.x/

git mv docs/releases/v1.1.7-quality-gate.md \
  docs/_archive/releases/v1.1.x/

# Commit
git commit -m "docs: archive v1.1.7 release documentation (Phase 5b)"
```

#### Step 5.4: Handle v1.4.2 Documentation

```bash
# Create migration directory if not exists
mkdir -p docs/migration

# Move v1.4.2 verification to migration (still relevant)
git mv docs/releases/v1.4.2-verification.md \
  docs/migration/v1.4.2-verification.md

# Commit
git commit -m "docs: move v1.4.2 verification to migration/ (Phase 5c)"
```

#### Step 5.5: Remove Empty Releases Directory

```bash
# Verify releases/ is empty
ls docs/releases/

# If empty, remove it (or keep for future use)
rmdir docs/releases/ 2>/dev/null

# Commit if removed
git commit -m "docs: remove empty releases/ directory (Phase 5 complete)"
```

#### Step 5.6: Validation

```bash
# Verify archived files
ls docs/_archive/releases/v1.1.x/ | wc -l  # Should be 12 (11 + 1 from Phase 4)

# Verify migration file
ls docs/migration/v1.4.2-verification.md

# Verify releases/ removed or empty
ls docs/releases/ 2>/dev/null

# Check for any references to old release paths
grep -r "docs/releases/v1.1" /Users/masa/Projects/mcp-ticketer/docs/ \
  --exclude-dir=_archive
```

---

### Phase 6: Archive Testing Files (1 file)

**Risk**: ✅ LOW | **Impact**: 🔥 LOW | **Duration**: 5 minutes

#### Step 6.1: Archive Test Report

```bash
cd /Users/masa/Projects/mcp-ticketer

# Ensure v1.4.x archive exists (created in Phase 4)
mkdir -p docs/_archive/releases/v1.4.x

# Move auto-remove test report
git mv docs/testing/auto-remove-test-report-2025-11-30.md \
  docs/_archive/releases/v1.4.x/auto-remove-test-report-2025-11-30.md

# Remove empty testing directory
rmdir docs/testing/

# Commit
git commit -m "docs: archive testing/ into _archive/releases/v1.4.x/ (Phase 6)"
```

#### Step 6.2: Validation

```bash
# Verify testing/ removed
ls -ld docs/testing/ 2>/dev/null  # Should not exist

# Verify file archived
ls docs/_archive/releases/v1.4.x/auto-remove-test-report-2025-11-30.md

# Count v1.4.x archive files: Should be 2 (v1.4.4 verification + test report)
ls docs/_archive/releases/v1.4.x/ | wc -l
```

---

### Phase 7: Consolidate Features Directory (3 files)

**Risk**: ⚠️ MEDIUM | **Impact**: 🔥 MEDIUM | **Duration**: 10 minutes

#### Step 7.1: Move Features to user-docs/features/

```bash
cd /Users/masa/Projects/mcp-ticketer

# Move AUTO_PROJECT_UPDATES.md
git mv docs/features/AUTO_PROJECT_UPDATES.md \
  docs/user-docs/features/AUTO_PROJECT_UPDATES.md

# Move claude-code-native-cli.md
git mv docs/features/claude-code-native-cli.md \
  docs/user-docs/features/claude-code-native-cli.md

# Move DEFAULT_VALUES.md
git mv docs/features/DEFAULT_VALUES.md \
  docs/user-docs/features/DEFAULT_VALUES.md

# Remove empty features directory
rmdir docs/features/

# Commit
git commit -m "docs: consolidate features/ into user-docs/features/ (Phase 7)"
```

#### Step 7.2: Update user-docs/features/README.md

Add to file:
```markdown
- **[Auto Project Updates](AUTO_PROJECT_UPDATES.md)** - Automatic project update creation
- **[Claude Code Native CLI](claude-code-native-cli.md)** - Native Claude Code CLI integration
- **[Default Values](DEFAULT_VALUES.md)** - Default configuration values
```

Commit:
```bash
git add docs/user-docs/features/README.md
git commit -m "docs: update user-docs/features/README for consolidated features"
```

#### Step 7.3: Validation

```bash
# Verify features/ removed
ls -ld docs/features/ 2>/dev/null  # Should not exist

# Verify files moved
ls docs/user-docs/features/AUTO_PROJECT_UPDATES.md
ls docs/user-docs/features/claude-code-native-cli.md
ls docs/user-docs/features/DEFAULT_VALUES.md

# Count user-docs/features/ files
ls docs/user-docs/features/*.md | wc -l  # Should include all feature docs
```

---

## Final Validation

### After All Phases Complete

#### Directory Count Check

```bash
# Count active directories (excluding _archive)
find docs -type d -not -path "*/._archive/*" -not -path "*/.git/*" | wc -l

# Expected: ~25 directories (down from 40+)
```

#### Root Files Check

```bash
# List root markdown files
ls docs/*.md

# Expected output:
# docs/README.md
# docs/RELEASE.md
# (Maybe docs/CHANGELOG.md if moved from project root)
```

#### Broken Links Check

```bash
# Search for any references to old paths
grep -r "docs/research/" docs/ --exclude-dir=_archive --exclude-dir=.git
grep -r "docs/features/" docs/ --exclude-dir=_archive --exclude-dir=.git
grep -r "docs/releases/" docs/ --exclude-dir=_archive --exclude-dir=.git
grep -r "docs/dev/" docs/ --exclude-dir=_archive --exclude-dir=.git
grep -r "docs/development/" docs/ --exclude-dir=_archive --exclude-dir=.git
grep -r "docs/release/" docs/ --exclude-dir=_archive --exclude-dir=.git
grep -r "docs/verification/" docs/ --exclude-dir=_archive --exclude-dir=.git
grep -r "docs/testing/" docs/ --exclude-dir=_archive --exclude-dir=.git

# All should return no results (or only from this guide)
```

#### File Count Check

```bash
# Count all markdown files
find docs -name "*.md" -type f | wc -l

# Should still be ~225 (same as before, just reorganized)
```

#### Archive Organization Check

```bash
# List archive structure
tree docs/_archive/ -L 2

# Expected structure:
# docs/_archive/
# ├── implementations/
# │   ├── 2025-11-30/          (4 files)
# ├── releases/
# │   ├── v1.1.x/              (12 files)
# │   └── v1.4.x/              (2 files)
# ├── research/
# │   ├── 2025-11-26/          (2 files)
# │   ├── 2025-11-28/          (3 files)
# │   ├── 2025-11-29/          (6 files)
# │   └── 2025-11-30/          (8 files)
# └── [existing archive directories]
```

---

## Rollback Procedures

### Rollback Single Phase (Before Push)

If you need to undo a phase **before pushing**:

```bash
# Soft reset (keeps changes as unstaged)
git reset --soft HEAD~N  # N = number of commits to undo

# Or hard reset (discards all changes)
git reset --hard HEAD~N

# Example: Undo last 3 commits from Phase 1
git reset --hard HEAD~3
```

### Rollback Single File (Before Push)

```bash
# Restore file to previous location
git mv docs/_archive/research/2025-11-30/file.md docs/research/

# Or use git restore (if not committed)
git restore --source=HEAD~1 docs/research/file.md
```

### Rollback After Push

If changes are already pushed:

```bash
# Create revert commit
git revert <commit-hash>

# For multiple commits, revert in reverse order
git revert <newest-hash> <older-hash> <oldest-hash>
```

### Emergency Full Rollback

If everything goes wrong:

```bash
# Find the commit before restructuring started
git log --oneline | grep -B5 "Phase 1"

# Hard reset to that commit
git reset --hard <commit-hash-before-restructure>

# Force push (CAUTION: Only if no one else has pulled)
git push --force origin main
```

---

## Post-Implementation Checklist

After completing all phases:

- [ ] **Verify file counts match**
  - [ ] 225 total markdown files (same as before)
  - [ ] 2 root files (README.md, RELEASE.md)
  - [ ] ~25 active directories
  - [ ] 47 files moved to archive

- [ ] **Verify no broken links**
  - [ ] All internal links work
  - [ ] All README indexes updated
  - [ ] No references to old paths

- [ ] **Verify archive organization**
  - [ ] Research files in dated directories
  - [ ] Implementation summaries archived
  - [ ] Old releases archived
  - [ ] All archive README files created

- [ ] **Update documentation metadata**
  - [ ] Update `docs/meta/DOCUMENTATION_STATUS.md`
  - [ ] Update `docs/meta/STRUCTURE.md`
  - [ ] Update CLAUDE.md if references changed

- [ ] **Test documentation site**
  - [ ] If using mkdocs/sphinx, rebuild and test
  - [ ] Check navigation works
  - [ ] Verify search finds all docs

- [ ] **Announce changes**
  - [ ] Create summary issue/announcement
  - [ ] Update CHANGELOG.md
  - [ ] Notify team of new structure

---

## Quick Command Summary

### Complete Restructure (All Phases)

**WARNING**: This runs all phases in sequence. Review each phase first!

```bash
#!/bin/bash
# docs-restructure.sh - Complete documentation restructure

cd /Users/masa/Projects/mcp-ticketer

# Phase 1: Archive research (19 files)
mkdir -p docs/_archive/research/{2025-11-26,2025-11-28,2025-11-29,2025-11-30}
git mv docs/research/*-2025-11-26.md docs/_archive/research/2025-11-26/
git mv docs/research/*-2025-11-28.md docs/_archive/research/2025-11-28/
git mv docs/research/*-2025-11-29.md docs/_archive/research/2025-11-29/
git mv docs/research/*-2025-11-30.md docs/_archive/research/2025-11-30/
git commit -m "docs: archive research files (Phase 1)"

# Phase 2: Archive implementations (4 files)
mkdir -p docs/_archive/implementations/2025-11-30
git mv docs/implementation-summary-1M-443.md docs/_archive/implementations/2025-11-30/
git mv docs/DOCSTRING_OPTIMIZATION_COMPLETION.md docs/_archive/implementations/2025-11-30/
git mv docs/github_url_refactor_changes.md docs/_archive/implementations/2025-11-30/
git mv docs/phase1-optimization-results.md docs/_archive/implementations/2025-11-30/
git commit -m "docs: archive implementation summaries (Phase 2)"

# Phase 3: Move root files (5 files)
mkdir -p docs/reference
git mv docs/SEMANTIC_PRIORITY_MATCHING.md docs/user-docs/features/semantic-priority-matching.md
git mv docs/TOKEN_PAGINATION.md docs/user-docs/features/token-pagination.md
git mv docs/mcp-api-reference.md docs/developer-docs/api/mcp-api-reference.md
git mv docs/LINEAR_URL_DOCUMENTATION_SUMMARY.md docs/developer-docs/adapters/linear-url-summary.md
git mv docs/PROJECT_STATUS.md docs/reference/project-status.md
git commit -m "docs: move root files to appropriate sections (Phase 3)"

# Phase 4: Consolidate duplicates (4 files)
mkdir -p docs/_archive/releases/{v1.1.x,v1.4.x}
git mv docs/dev/README.md docs/developer-docs/dev-guide.md
rmdir docs/dev/
git mv docs/development/LOCAL_MCP_SETUP.md docs/developer-docs/getting-started/LOCAL_MCP_SETUP.md
rmdir docs/development/
git mv docs/release/v1.1.5-verification-report.md docs/_archive/releases/v1.1.x/
rmdir docs/release/
git mv docs/verification/v1.4.4-verification-report.md docs/_archive/releases/v1.4.x/
rmdir docs/verification/
git commit -m "docs: consolidate duplicate directories (Phase 4)"

# Phase 5: Archive old releases (11 files)
mkdir -p docs/migration
git mv docs/releases/v1.1.* docs/_archive/releases/v1.1.x/
git mv docs/releases/v1.4.2-verification.md docs/migration/
rmdir docs/releases/ 2>/dev/null
git commit -m "docs: archive old releases (Phase 5)"

# Phase 6: Archive testing (1 file)
git mv docs/testing/auto-remove-test-report-2025-11-30.md docs/_archive/releases/v1.4.x/
rmdir docs/testing/
git commit -m "docs: archive testing files (Phase 6)"

# Phase 7: Consolidate features (3 files)
git mv docs/features/*.md docs/user-docs/features/
rmdir docs/features/
git commit -m "docs: consolidate features directory (Phase 7)"

echo "Restructure complete! Review changes before pushing."
```

**DO NOT RUN THIS SCRIPT BLINDLY**. Execute each phase manually and validate before proceeding.

---

**Implementation Guide Complete**
**Companion Document**: documentation-architecture-proposal-2025-11-30.md
**Last Updated**: 2025-11-30
