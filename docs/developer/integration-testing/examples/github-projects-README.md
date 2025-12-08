# GitHub Projects V2 Integration Test

## Overview

This integration test validates all 9 implemented GitHub Projects V2 methods against the real GitHub API.

**Test Script**: `test_github_projects_integration.py`

**Repository**: https://github.com/bobmatnyc/mcp-ticketer

## Prerequisites

### 1. GitHub Personal Access Token

You need a GitHub Personal Access Token with the following scopes:

- **repo**: Full control of private repositories (or **public_repo** for public repos only)
- **project**: Full control of organization projects (read/write)
- **read:project**: Read access to projects

**Create token at**: https://github.com/settings/tokens/new

### 2. Environment Setup

Set the GitHub token as an environment variable:

```bash
export GITHUB_TOKEN="ghp_YOUR_TOKEN_HERE"
```

Or add to `.env.local`:

```bash
echo "GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE" >> .env.local
```

### 3. Repository Access

Ensure you have access to the repository:
- **Owner**: bobmatnyc
- **Repo**: mcp-ticketer
- **URL**: https://github.com/bobmatnyc/mcp-ticketer

## Running the Test

### Option 1: With Environment Variable

```bash
export GITHUB_TOKEN="ghp_YOUR_TOKEN_HERE"
PYTHONPATH=/Users/masa/Projects/mcp-ticketer/src:$PYTHONPATH \
  python3 tests/integration/test_github_projects_integration.py
```

### Option 2: With .env.local

1. Add GitHub token to `.env.local`:
   ```bash
   GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE
   ```

2. Load environment and run:
   ```bash
   source <(cat .env.local | grep -v '^#' | sed 's/^/export /')
   PYTHONPATH=/Users/masa/Projects/mcp-ticketer/src:$PYTHONPATH \
     python3 tests/integration/test_github_projects_integration.py
   ```

### Option 3: Direct Python Execution

```python
import os
os.environ['GITHUB_TOKEN'] = 'ghp_YOUR_TOKEN_HERE'

# Run the test script
exec(open('tests/integration/test_github_projects_integration.py').read())
```

## Test Phases

The integration test validates all 9 implemented methods:

### Phase 1: Setup and Authentication
- ✅ Initialize GitHubAdapter with credentials
- ✅ Verify connection to GitHub API

### Phase 2: List Existing Projects
- ✅ `project_list()` - List projects in repository
- ✅ Display existing projects

### Phase 3: Create New Project
- ✅ `project_create()` - Create "Phase 2: GitHub Projects V2 Implementation"
- ✅ Capture project ID, number, URL

### Phase 4: Get Project Details
- ✅ `project_get()` by node ID
- ✅ `project_get()` by number (auto-detection)
- ✅ Verify both methods return same project

### Phase 5: Add Issues to Project
- ✅ `project_add_issue()` - Add issue #36 (Phase 2 Parent)
- ✅ `project_add_issue()` - Add issue #37 (Week 2 Implementation)
- ✅ `project_add_issue()` - Add issue #38 (Week 3 Implementation)
- ✅ `project_add_issue()` - Add issue #39 (Week 4 Implementation)

### Phase 6: Get Project Issues
- ✅ `project_get_issues()` - List all issues in project
- ✅ Verify all 4 issues were added
- ✅ Check issue metadata (project_item_id)

### Phase 7: Calculate Project Statistics
- ✅ `project_get_statistics()` - Get health metrics
- ✅ Verify health status (on_track/at_risk/off_track)
- ✅ Check issue counts and progress percentage
- ✅ Validate priority distribution

### Phase 8: Update Project
- ✅ `project_update()` - Update project README
- ✅ Add implementation summary and test results

### Phase 9: Summary and Cleanup
- ✅ Print test results summary
- ✅ Provide manual cleanup instructions
- ✅ Display project URL for inspection

## Expected Output

### Successful Test Run

```
============================================================
GitHub Projects V2 Integration Test
============================================================

ℹ Testing all 9 implemented methods against real GitHub API
ℹ Repository: https://github.com/bobmatnyc/mcp-ticketer

============================================================
Phase 1: Setup and Authentication
============================================================

✓ GitHub token found (length: 40)
✓ Adapter initialized successfully

============================================================
Phase 2: List Existing Projects
============================================================

✓ Found 3 existing projects
ℹ   - Project Alpha (ID: PVT_..., State: open)
ℹ   - Project Beta (ID: PVT_..., State: closed)
ℹ   - Project Gamma (ID: PVT_..., State: open)

============================================================
Phase 3: Create New Project for Work Session
============================================================

✓ Created project: Phase 2: GitHub Projects V2 Implementation
ℹ   ID: PVT_kwDOBGE5v84A1234
ℹ   Number: 5
ℹ   URL: https://github.com/bobmatnyc/mcp-ticketer/projects/5

... [additional phases] ...

============================================================
TEST RESULTS SUMMARY
============================================================

Total Tests: 12
✓ Passed: 12
✗ Failed: 0

Detailed Results:
✓ Adapter initialization
✓ project_list() - Found 3 projects
✓ project_create() - Created project #5
✓ project_get() by node ID
✓ project_get() by number
✓ ID auto-detection verification
✓ project_add_issue() - Added 4/4 issues
✓ project_get_issues() - Retrieved 4 issues
✓ project_get_statistics() - Health: on_track, 4 issues
✓ project_update() - Updated project readme

============================================================
INTEGRATION TEST COMPLETE
============================================================

All 12 tests passed!
```

## Verification Steps

After running the integration test:

1. **Visit Project URL**
   - Navigate to the project URL shown in test output
   - Example: https://github.com/bobmatnyc/mcp-ticketer/projects/5

2. **Verify Issues Associated**
   - Check that all 4 issues (#36, #37, #38, #39) are visible in the project
   - Verify issue metadata and states

3. **Review Project README**
   - Check that the project README was updated with implementation summary
   - Verify markdown formatting is correct

4. **Check Statistics**
   - View project health metrics
   - Verify issue counts and progress percentage

5. **Optional: Take Screenshots**
   - Capture project overview for documentation
   - Screenshot issue list in project
   - Save health metrics display

## Cleanup

The test **does not** automatically delete the created project. This allows manual inspection.

To delete the project after verification:

```python
from mcp_ticketer.adapters.github.adapter import GitHubAdapter

adapter = GitHubAdapter({
    'token': 'ghp_YOUR_TOKEN_HERE',
    'owner': 'bobmatnyc',
    'repo': 'mcp-ticketer',
    'use_projects_v2': True
})

# Delete by node ID (from test output)
adapter.project_delete('PVT_kwDOBGE5v84A1234')
```

Or via GraphQL API directly:

```bash
curl -X POST -H "Authorization: Bearer ghp_YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { deleteProjectV2(input: {projectId: \"PVT_kwDOBGE5v84A1234\"}) { projectV2 { id } } }"}' \
  https://api.github.com/graphql
```

## Troubleshooting

### Issue: GITHUB_TOKEN not set

**Error**: `GITHUB_TOKEN environment variable not set`

**Solution**: Export the token before running:
```bash
export GITHUB_TOKEN="ghp_YOUR_TOKEN_HERE"
```

### Issue: ModuleNotFoundError: No module named 'mcp_ticketer'

**Error**: `ModuleNotFoundError: No module named 'mcp_ticketer'`

**Solution**: Run with PYTHONPATH set:
```bash
PYTHONPATH=/Users/masa/Projects/mcp-ticketer/src:$PYTHONPATH python3 tests/integration/test_github_projects_integration.py
```

### Issue: Permission denied (403)

**Error**: `GraphQL query failed: 403 Forbidden`

**Solution**: Verify token has required scopes:
- Go to https://github.com/settings/tokens
- Check that token has `repo` and `project` scopes
- Regenerate token if needed

### Issue: Project not found

**Error**: `Project with ID '123' not found`

**Solution**:
- Verify you have access to the repository
- Check that `owner` and `repo` are correct
- Ensure you're a collaborator on the repository

### Issue: Issues not found

**Error**: `Issue #36 not found`

**Solution**:
- Verify issues #36, #37, #38, #39 exist in the repository
- Check issue numbers are correct
- Use different issue numbers if needed

## Alternative Testing (Without GitHub Token)

If you don't have a GitHub token, you can still validate the implementation:

### Option 1: Unit Tests

Run the comprehensive unit test suite:

```bash
pytest tests/adapters/github/test_github_projects.py -v
```

This tests all methods with mocked GraphQL responses.

### Option 2: Manual API Testing

Use the GitHub GraphQL Explorer:
- Visit: https://docs.github.com/en/graphql/overview/explorer
- Manually execute queries from `src/mcp_ticketer/adapters/github/graphql/projects.py`
- Verify responses match expected format

### Option 3: Dry Run Mode

Run the test script in documentation mode to see what it would do:

```bash
# This shows the test flow without executing
python3 -c "import ast; print(ast.get_docstring(ast.parse(open('tests/integration/test_github_projects_integration.py').read())))"
```

## Test Evidence

For complete validation, collect the following evidence:

1. **Terminal Output**
   - Full test execution output
   - Pass/fail status for each test
   - Project URL and metadata

2. **Screenshots**
   - Project overview page
   - Issue list in project
   - Project README
   - Health metrics/statistics

3. **API Responses**
   - Example GraphQL responses (sanitized)
   - Project metadata JSON
   - Issue metadata JSON

4. **Test Metrics**
   - Total tests run
   - Pass/fail counts
   - Execution time
   - API call count

## Related Documentation

- **Implementation**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/github/adapter.py`
- **Unit Tests**: `/Users/masa/Projects/mcp-ticketer/tests/adapters/github/test_github_projects.py`
- **GraphQL Queries**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/github/graphql/projects.py`
- **Phase 2 Summary**: `/Users/masa/Projects/mcp-ticketer/docs/phase1-implementation-summary.md`

## Success Criteria

Integration test is considered successful when:

- ✅ All 12 tests pass (100% pass rate)
- ✅ Project created and visible in GitHub UI
- ✅ All 4 issues associated with project
- ✅ Project README updated correctly
- ✅ Health metrics calculated accurately
- ✅ No API errors or exceptions
- ✅ Project can be retrieved by both ID formats
- ✅ Cleanup instructions provided

## Next Steps

After successful integration test:

1. Document test results in Phase 2 summary
2. Create screenshots for evidence
3. Update implementation documentation
4. Tag release candidate
5. Plan Phase 3 implementation
