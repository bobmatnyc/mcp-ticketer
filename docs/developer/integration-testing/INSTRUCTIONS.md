# GitHub Projects V2 Integration Test - Quick Start Guide

## Quick Start

This integration test validates all 9 GitHub Projects V2 methods against the real GitHub API.

### 1. Set Up GitHub Token

Create a GitHub Personal Access Token at: https://github.com/settings/tokens/new

**Required scopes**:
- ✅ `repo` (or `public_repo` for public repos)
- ✅ `project` (full control of projects)
- ✅ `read:project` (read access to projects)

### 2. Configure Environment

**Option A: Using .env.local** (Recommended)
```bash
cd /Users/masa/Projects/mcp-ticketer
echo "GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE" >> .env.local
```

**Option B: Export environment variable**
```bash
export GITHUB_TOKEN="ghp_YOUR_TOKEN_HERE"
```

### 3. Run the Test

**Simplest method** (uses test runner):
```bash
cd /Users/masa/Projects/mcp-ticketer
./tests/integration/run_github_projects_test.sh
```

**Manual method**:
```bash
cd /Users/masa/Projects/mcp-ticketer
export GITHUB_TOKEN="ghp_YOUR_TOKEN_HERE"
PYTHONPATH=src:$PYTHONPATH python3 tests/integration/test_github_projects_integration.py
```

### 4. Review Results

The test will:
- ✅ Create a new project "Phase 2: GitHub Projects V2 Implementation"
- ✅ Add 4 issues (#36, #37, #38, #39) to the project
- ✅ Calculate health metrics and statistics
- ✅ Update project README
- ✅ Display project URL for manual inspection

**Project will be created at**: https://github.com/bobmatnyc/mcp-ticketer/projects/

### 5. Verify in GitHub UI

After the test completes:
1. Visit the project URL shown in the test output
2. Verify all 4 issues are associated with the project
3. Check the project README was updated
4. Review health metrics and statistics

### 6. Cleanup (Optional)

The test **does not** automatically delete the project. To clean up:

```python
from mcp_ticketer.adapters.github.adapter import GitHubAdapter

adapter = GitHubAdapter({
    'token': 'ghp_YOUR_TOKEN_HERE',
    'owner': 'bobmatnyc',
    'repo': 'mcp-ticketer',
    'use_projects_v2': True
})

# Use the project ID from test output
adapter.project_delete('PVT_kwDOBGE5v84AXXXXX')
```

## What Gets Tested

The integration test validates all **9 GitHub Projects V2 methods**:

| Method | Test Phase | What It Tests |
|--------|-----------|---------------|
| `project_list()` | Phase 2 | List existing projects |
| `project_create()` | Phase 3 | Create new project |
| `project_get()` | Phase 4 | Get project by ID and number |
| `project_add_issue()` | Phase 5 | Add 4 issues to project |
| `project_get_issues()` | Phase 6 | Retrieve project issues |
| `project_get_statistics()` | Phase 7 | Calculate health metrics |
| `project_update()` | Phase 8 | Update project README |
| `project_delete()` | Manual | Cleanup (not automated) |
| `project_remove_issue()` | Manual | Cleanup (not automated) |

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

============================================================
Created Project Details
============================================================

Title: Phase 2: GitHub Projects V2 Implementation
URL: https://github.com/bobmatnyc/mcp-ticketer/projects/5
Number: 5
Node ID: PVT_kwDOBGE5v84A1234
```

## Troubleshooting

### GITHUB_TOKEN not set
```bash
export GITHUB_TOKEN="ghp_YOUR_TOKEN_HERE"
```

### ModuleNotFoundError
```bash
PYTHONPATH=src:$PYTHONPATH python3 tests/integration/test_github_projects_integration.py
```

### Permission denied (403)
Verify your token has the required scopes at: https://github.com/settings/tokens

## Full Documentation

For detailed information, see:
- **Complete Guide**: `/Users/masa/Projects/mcp-ticketer/tests/integration/README_GITHUB_PROJECTS_INTEGRATION.md`
- **Test Summary**: `/Users/masa/Projects/mcp-ticketer/docs/github-projects-integration-test-summary.md`
