# GitHub Projects V2 Integration Test

> **Quick Start**: Test the Phase 2 GitHub Projects V2 implementation against the real GitHub API

## Status: ✅ Ready to Run

All test infrastructure is complete. Just add a GitHub token and execute.

---

## Quick Start (3 Steps)

### 1. Get GitHub Token
Create a Personal Access Token at: https://github.com/settings/tokens/new

**Required scopes**:
- ✅ `repo` (Full control of repositories)
- ✅ `project` (Full control of projects)
- ✅ `read:project` (Read access to projects)

### 2. Configure Environment
```bash
echo "GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE" >> .env.local
```

### 3. Run Test
```bash
./tests/integration/run_github_projects_test.sh
```

**That's it!** The test will:
- Create a new project "Phase 2: GitHub Projects V2 Implementation"
- Add 4 issues (#36-39) to the project
- Calculate health metrics
- Display results and project URL

---

## What Gets Tested

All **9 GitHub Projects V2 methods** are validated:

| Method | What It Tests |
|--------|---------------|
| `project_list()` | List existing projects |
| `project_create()` | Create new project |
| `project_get()` | Get by ID and number (auto-detection) |
| `project_update()` | Update project README |
| `project_add_issue()` | Add 4 issues to project |
| `project_get_issues()` | Retrieve project issues |
| `project_get_statistics()` | Calculate health metrics |
| `project_delete()` | Available for cleanup |
| `project_remove_issue()` | Available for cleanup |

**Total**: 12 comprehensive tests across 9 phases

---

## Expected Output

```
============================================================
GitHub Projects V2 Integration Test
============================================================

✓ GitHub token found (length: 40)
✓ Adapter initialized successfully

...

============================================================
TEST RESULTS SUMMARY
============================================================

Total Tests: 12
✓ Passed: 12

All 12 tests passed!

Created Project Details
Title: Phase 2: GitHub Projects V2 Implementation
URL: https://github.com/bobmatnyc/mcp-ticketer/projects/5
```

---

## Documentation

Choose your documentation level:

### 📄 Quick Start (This File)
Start here if you just want to run the test.

### 📘 Full User Guide
**File**: `tests/integration/README_GITHUB_PROJECTS_INTEGRATION.md`
- Complete prerequisites and setup
- 3 different ways to run the test
- Detailed troubleshooting
- Alternative testing strategies

### 📊 Test Summary & Analysis
**File**: `docs/github-projects-integration-test-summary.md`
- Test coverage matrix
- Phase-by-phase breakdown
- Expected results
- Next steps

### 📋 Executive Summary
**File**: `QA_DELIVERABLES.md`
- Complete deliverables list
- Acceptance criteria
- File inventory
- Success metrics

### 🔍 Status Report
**File**: `INTEGRATION_TEST_STATUS.md`
- Current status
- Blocker analysis
- Alternative validation
- Quick reference

---

## Troubleshooting

### GITHUB_TOKEN not set
```bash
export GITHUB_TOKEN="ghp_YOUR_TOKEN_HERE"
```

### ModuleNotFoundError
The test runner handles this automatically. If running manually:
```bash
PYTHONPATH=src:$PYTHONPATH python3 tests/integration/test_github_projects_integration.py
```

### Permission denied (403)
Verify your token has the required scopes at: https://github.com/settings/tokens

See full troubleshooting guide: `tests/integration/README_GITHUB_PROJECTS_INTEGRATION.md`

---

## Cleanup

The test **does not** automatically delete the created project. This allows you to inspect it.

**To delete the project later**:
```python
from mcp_ticketer.adapters.github.adapter import GitHubAdapter

adapter = GitHubAdapter({
    'token': 'ghp_YOUR_TOKEN_HERE',
    'owner': 'bobmatnyc',
    'repo': 'mcp-ticketer',
    'use_projects_v2': True
})

# Use project ID from test output
adapter.project_delete('PVT_kwDOBGE5v84AXXXXX')
```

---

## Alternative: Unit Tests Only

If you can't get a GitHub token, you can still validate the implementation:

```bash
# Run the 82 unit tests (no token required)
pytest tests/adapters/github/test_github_projects.py -v
```

These tests use mocked GraphQL responses and don't require API access.

---

## Files and Sizes

| File | Type | Size | Description |
|------|------|------|-------------|
| `tests/integration/test_github_projects_integration.py` | Test Script | 17KB | Main integration test |
| `tests/integration/run_github_projects_test.sh` | Runner | 3.3KB | Automated test runner |
| `tests/integration/README_GITHUB_PROJECTS_INTEGRATION.md` | Docs | 10KB | Complete guide |
| `docs/INTEGRATION_TEST_INSTRUCTIONS.md` | Docs | 4.1KB | Quick start |
| `docs/github-projects-integration-test-summary.md` | Docs | 11KB | Test summary |
| `INTEGRATION_TEST_STATUS.md` | Report | 11KB | Status report |
| `QA_DELIVERABLES.md` | Report | 12KB | Deliverables |

**Total**: 7 files, 68.4KB, 2310 lines of code and documentation

---

## Repository

**Target Repository**: https://github.com/bobmatnyc/mcp-ticketer
**Issues**: #36, #37, #38, #39

---

## Support

For detailed instructions, see the full documentation suite:
- Quick Start: `docs/INTEGRATION_TEST_INSTRUCTIONS.md`
- Full Guide: `tests/integration/README_GITHUB_PROJECTS_INTEGRATION.md`
- Test Summary: `docs/github-projects-integration-test-summary.md`

---

**Created**: 2025-12-05
**QA Agent**: Claude Code
**Phase**: Phase 2 - GitHub Projects V2 Implementation
**Status**: ✅ Ready to Run
