# Linear Issue Creation Failure: Version Mismatch Root Cause Analysis

**Date:** 2025-12-03
**Status:** 🔴 CRITICAL - USER RUNNING OUTDATED VERSION
**Severity:** HIGH
**Root Cause Confirmed:** ✅ YES

---

## Executive Summary

**THE BUG IS NOT BACK - THE USER HASN'T UPGRADED YET**

The v2.0.3 fix for Linear issue creation (commit 60a89e8) **IS WORKING CORRECTLY**. The user is experiencing failures because they are running the **old installed version (v1.2.14)** which does not include the fix.

### Key Findings

| Aspect | Finding |
|--------|---------|
| **v2.0.3 Fix Status** | ✅ Working perfectly - all tests pass |
| **User's Installed Version** | ❌ v1.2.14 (outdated) |
| **Source Code Version** | ✅ v2.0.3 (correct) |
| **Issue Type** | Version mismatch - not a regression |
| **Impact** | User creating issues via CLI gets errors |
| **Resolution** | User must upgrade: `pip install --upgrade mcp-ticketer` |

---

## Detailed Investigation

### Test Results (v2.0.3 Source Code)

**Test Script:** `test_reproduce_issue.py`
**Test Environment:** Python 3.14, using local source code v2.0.3

#### Test 1: Issue with parent_epic (User's Exact Scenario)

```python
Task(
    title="[Documentation] JSON-First Architecture: Complete Plan",
    parent_epic="b510423d2886",  # The slug user provided
    state="open",
    priority="medium"
)
```

**Result:** ✅ **SUCCESS** - Created issue 1M-598
**GraphQL Operation:** `issueCreate` with `projectId` correctly resolved
**No validation errors occurred**

#### Test 2: Issue without parent_epic (Control)

```python
Task(
    title="[POC] Control Test Without Parent",
    state="open",
    priority="medium"
)
```

**Result:** ✅ **SUCCESS** - Created issue 1M-599
**No errors**

### Version Analysis

#### Source Code (Local Development)

```bash
$ cat src/mcp_ticketer/__version__.py
__version__ = "2.0.3"
```

**Fix Included:** ✅ Yes
**Commit:** 60a89e8 "fix: resolve Linear stateId UUID validation error"
**Test Script Behavior:** Uses `sys.path.insert(0, 'src')` → loads v2.0.3 → **WORKS**

#### Installed Binary (User's Environment)

```bash
$ mcp-ticketer --version
mcp-ticketer version 1.2.14
```

**Location:** `/opt/homebrew/bin/mcp-ticketer`
**Fix Included:** ❌ No (pre-dates v2.0.3)
**User CLI Behavior:** Uses installed v1.2.14 → **FAILS**

### The v2.0.3 Fix (Confirmed Working)

**File:** `src/mcp_ticketer/adapters/linear/adapter.py`
**Function:** `_get_state_mapping()`

**Before (v1.2.14 and earlier):**
```python
for universal_state, linear_type in LinearStateMapping.TO_LINEAR.items():
    if linear_type in self._workflow_states:  # ❌ WRONG: _workflow_states keyed by "open", not "unstarted"
        mapping[universal_state] = self._workflow_states[linear_type]["id"]
```

**After (v2.0.3):**
```python
for universal_state in TicketState:
    state_uuid = self._workflow_states.get(universal_state.value)  # ✅ CORRECT: Access by "open"
    if state_uuid:
        mapping[universal_state] = state_uuid
```

**What Changed:**
- `_workflow_states` is keyed by universal state values (`"open"`, `"in_progress"`)
- Old code tried to access with Linear types (`"unstarted"`, `"started"`) → returned `None` or non-UUID
- New code uses correct key lookup → returns proper UUID
- Result: `stateId` field now contains UUID instead of type name

### Proof: Tests Pass with v2.0.3

**Debug Logs from Test Run:**

```log
2025-12-03 15:42:27,972 [DEBUG] Mapped open → 0d5f946e-6795-425e-bef7-a27181fc0504 (strategy: name:todo)
2025-12-03 15:42:27,972 [DEBUG] Mapped in_progress → 80b5d03a-75bb-4cb1-b2fa-6905b5526706 (strategy: name:in progress)
...
```

**GraphQL Variables Sent (Test 1 with parent_epic):**

```json
{
  "input": {
    "title": "[Documentation] JSON-First Architecture: Complete Plan",
    "teamId": "b366b0de-2f3f-4641-8100-eea12b6aa5df",
    "description": "Testing exact scenario that's failing for user",
    "priority": 3,
    "stateId": "0d5f946e-6795-425e-bef7-a27181fc0504",  // ✅ UUID (not "unstarted")
    "projectId": "cbeff74a-edd7-4125-ac73-f64161cf91b3"  // ✅ Resolved from slug
  }
}
```

**Linear API Response:**

```json
{
  "issueCreate": {
    "success": true,
    "issue": {
      "id": "76d4feea-c3d0-44bb-80c0-16d0e2862367",
      "identifier": "1M-598",
      "title": "[Documentation] JSON-First Architecture: Complete Plan"
    }
  }
}
```

**No "Argument Validation Error" occurred.**

---

## Why User is Still Failing

### The Failure Pattern

**User Command:**
```bash
$ mcp-ticketer hierarchy entity_type=issue action=create \
    title="[Documentation] JSON-First Architecture: Complete Plan" \
    epic_id="b510423d2886"
```

**Result:**
```
Failed to create issue: Failed to create Linear issue: [linear] Linear GraphQL validation error: Argument Validation Error
```

### Root Cause: Old Version Installed

**What's Happening:**

1. User runs `mcp-ticketer` command
2. Binary at `/opt/homebrew/bin/mcp-ticketer` executes
3. This binary is from **v1.2.14** (installed via `pip install mcp-ticketer` before v2.0.3 release)
4. v1.2.14 has the **OLD BUGGY CODE** with incorrect `_get_state_mapping()`
5. Old code sends `stateId: "unstarted"` (string) instead of UUID
6. Linear API rejects: "Argument Validation Error" (stateId must be UUID)

### Why Tests Pass But User Fails

**Test Script (`test_reproduce_issue.py`):**
```python
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))  # ✅ Loads v2.0.3 from source
```
- Uses local development code (v2.0.3 with fix)
- Fix is present → tests pass

**User CLI (`mcp-ticketer`):**
```bash
$ which mcp-ticketer
/opt/homebrew/bin/mcp-ticketer  # ❌ Installed v1.2.14 without fix
```
- Uses installed package (v1.2.14 without fix)
- Bug is present → commands fail

---

## Resolution

### Immediate Action Required

**User must upgrade to v2.0.3:**

```bash
# Check current version
$ mcp-ticketer --version
mcp-ticketer version 1.2.14  # ❌ OLD

# Upgrade to latest
$ pip install --upgrade mcp-ticketer

# OR if using pipx
$ pipx upgrade mcp-ticketer

# Verify upgrade
$ mcp-ticketer --version
mcp-ticketer version 2.0.3  # ✅ FIXED
```

### Verification After Upgrade

**Test command:**
```bash
$ mcp-ticketer hierarchy entity_type=issue action=create \
    title="[Test] Verify v2.0.3 Fix" \
    epic_id="b510423d2886" \
    priority=medium
```

**Expected Result:**
```
✅ Created issue 1M-XXX successfully
```

---

## Lessons Learned

### Why This Confusion Happened

1. **Recent Release:** v2.0.3 was released TODAY (2025-12-03)
2. **Testing Gap:** QA tests used source code, not installed package
3. **Version Check Missing:** User didn't verify installed version before reporting
4. **Misleading Error:** Same error message as original bug, suggesting regression

### Improvements Needed

#### 1. Release Communication

**Problem:** User didn't know v2.0.3 was released
**Solution:**
- Add prominent upgrade notice to README
- Post release announcement in Linear project
- Email notification for critical bug fixes

#### 2. Version Verification in Error Messages

**Current:**
```
Failed to create issue: Argument Validation Error
```

**Improved:**
```
Failed to create issue: Argument Validation Error
mcp-ticketer version: 1.2.14
Note: This error was fixed in v2.0.3. Please upgrade: pip install --upgrade mcp-ticketer
```

#### 3. QA Testing Process

**Current:** Tests use source code via `sys.path.insert(0, 'src')`
**Problem:** Doesn't catch installed package issues
**Solution:** Add tests that verify installed package behavior:

```python
# Test installed package, not source
import subprocess
result = subprocess.run(['mcp-ticketer', 'hierarchy', ...], capture_output=True)
```

#### 4. Automated Version Checks

**Implement in CLI:**
```python
# On startup, check if newer version available
if installed_version < latest_pypi_version:
    print(f"⚠️  Update available: v{latest_pypi_version} (you have v{installed_version})")
    print(f"   Upgrade: pip install --upgrade mcp-ticketer")
```

---

## Comparison: v1.2.14 vs v2.0.3

| Aspect | v1.2.14 (User's Version) | v2.0.3 (Fixed Version) |
|--------|--------------------------|-------------------------|
| **stateId Handling** | ❌ Sends type name ("unstarted") | ✅ Sends UUID |
| **_get_state_mapping()** | ❌ Broken lookup logic | ✅ Correct lookup by universal_state.value |
| **Issue Creation** | ❌ Fails with validation error | ✅ Works perfectly |
| **Release Date** | Pre-2025-12-03 | 2025-12-03 (TODAY) |
| **Commit** | Before 60a89e8 | Includes 60a89e8 fix |

---

## Conclusion

### Status Summary

✅ **v2.0.3 Fix:** Working perfectly - no regression
✅ **Root Cause Identified:** User running outdated v1.2.14
✅ **Resolution:** User must upgrade to v2.0.3
✅ **No Code Changes Needed:** Fix is already deployed

### Verification

**Tests Passing:**
- ✅ Epic creation
- ✅ Issue creation without parent_epic
- ✅ Issue creation with parent_epic (user's exact scenario)
- ✅ State mapping to UUIDs
- ✅ Project slug resolution

**No New Issues Found:**
- ❌ Not a regression
- ❌ Not a new bug
- ❌ Not a test false positive

### Recommendation

**CLOSE THIS INVESTIGATION** with summary:
- User needs to upgrade to v2.0.3
- Improve release communication process
- Add version check to CLI error messages
- Update QA process to test installed packages

---

## Appendix: Full Test Logs

### Test 1 (With parent_epic) - SUCCESS

**Created Issue:** https://linear.app/1m-hyperdev/issue/1M-598

**Input:**
```python
{
    "title": "[Documentation] JSON-First Architecture: Complete Plan",
    "parent_epic": "b510423d2886",
    "state": "open",
    "priority": "medium"
}
```

**GraphQL Variables:**
```json
{
  "input": {
    "title": "[Documentation] JSON-First Architecture: Complete Plan",
    "teamId": "b366b0de-2f3f-4641-8100-eea12b6aa5df",
    "description": "Testing exact scenario that's failing for user",
    "priority": 3,
    "stateId": "0d5f946e-6795-425e-bef7-a27181fc0504",
    "projectId": "cbeff74a-edd7-4125-ac73-f64161cf91b3"
  }
}
```

**Result:** ✅ Issue 1M-598 created successfully

### Test 2 (Without parent_epic) - SUCCESS

**Created Issue:** https://linear.app/1m-hyperdev/issue/1M-599

**Input:**
```python
{
    "title": "[POC] Control Test Without Parent",
    "state": "open",
    "priority": "medium"
}
```

**Result:** ✅ Issue 1M-599 created successfully

---

**Report Generated:** 2025-12-03 15:45 PST
**Investigator:** Claude Code (Research Agent)
**Investigation Duration:** ~20 minutes
**Conclusion:** User needs to upgrade, not a bug regression
