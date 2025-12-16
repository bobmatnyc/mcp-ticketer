# Bug Fix: Credential Re-Entry on Validation Failure

## Issue
**Bug ID**: Credential Re-Entry Bug in Setup Wizard
**Branch**: `bugfix/credential-reentry-prompt`
**Status**: Fixed ✅

## Problem Statement

When running `mcp-ticketer setup`, if API credential validation fails and the user chooses to retry, the wizard would loop back and retry validation with the **same invalid credentials** instead of prompting for new ones.

### Broken Flow (Before Fix)
```
1. User enters token: ghp_bad_token
2. API Validation: 401 Unauthorized ❌
3. Prompt: "Re-enter credentials and try again?" → User says YES
4. BUG: Retries with same ghp_bad_token (never prompts for new input)
5. API Validation: 401 Unauthorized ❌ (infinite loop)
```

### Root Cause
The `_validate_api_credentials` function in `src/mcp_ticketer/cli/configure.py` (lines 74-225) had a retry loop that asked "Re-enter credentials?" but never actually prompted for new credentials. It just looped back with the same `credentials` dict.

## Solution

### Implementation
Added a **credential prompter callback pattern** to enable re-prompting on retry:

1. **Added callback parameter** to `_validate_api_credentials`:
   ```python
   def _validate_api_credentials(
       adapter_type: str,
       credentials: dict[str, str],
       credential_prompter: Callable[[], dict[str, str]] | None = None,  # NEW
       max_retries: int = 3,
   ) -> bool:
   ```

2. **Call prompter on retry** to get fresh credentials:
   ```python
   if attempt < max_retries:
       retry = Confirm.ask("Re-enter credentials and try again?", default=True)
       if retry and credential_prompter:
           # Re-prompt for fresh credentials
           new_credentials = credential_prompter()
           credentials.update(new_credentials)  # Update in-place
   ```

3. **Updated all callers** to pass appropriate prompter functions:
   - `_configure_linear()` - prompts for new Linear API key
   - `_configure_github()` - prompts for new GitHub token with scopes hint
   - `_configure_jira()` - prompts for new JIRA API token with generation link

### Fixed Flow (After Fix)
```
1. User enters token: ghp_bad_token
2. API Validation: 401 Unauthorized ❌
3. Prompt: "Re-enter credentials and try again?" → User says YES
4. FIX: Prompts for new token
   > GitHub Personal Access Token: [password input]
5. User enters: ghp_good_token
6. API Validation: 200 OK ✅
```

## Testing

### Test Coverage
Created comprehensive test suite in `tests/cli/test_credential_validation.py`:

| Test Case | Description | Status |
|-----------|-------------|--------|
| `test_linear_retry_with_credential_prompter` | Linear API key retry with fresh credentials | ✅ PASS |
| `test_github_retry_with_credential_prompter` | GitHub token retry with fresh credentials | ✅ PASS |
| `test_jira_retry_with_credential_prompter` | JIRA credentials retry with fresh credentials | ✅ PASS |
| `test_retry_without_prompter_skips_validation` | Graceful handling when no prompter provided | ✅ PASS |
| `test_user_declines_retry` | User can decline retry and skip validation | ✅ PASS |
| `test_max_retries_exhausted_saves_anyway` | Max retries allows saving unvalidated config | ✅ PASS |

### Test Results
```bash
$ pytest tests/cli/test_credential_validation.py -v
================================ 6 passed in 0.12s ================================
```

## Files Changed

| File | LOC Added | LOC Removed | Net Change |
|------|-----------|-------------|------------|
| `src/mcp_ticketer/cli/configure.py` | +42 | -8 | +34 |
| `tests/cli/test_credential_validation.py` | +245 | 0 | +245 |
| **Total** | **+287** | **-8** | **+279** |

## Verification Steps

To verify the fix works:

1. **Checkout the branch**:
   ```bash
   git checkout bugfix/credential-reentry-prompt
   ```

2. **Run the setup wizard**:
   ```bash
   mcp-ticketer setup --force-reinit
   ```

3. **Test credential retry**:
   - Select GitHub adapter
   - Enter an **invalid token** (e.g., `ghp_invalid_token_test`)
   - Wait for validation to fail (401 Unauthorized)
   - When prompted "Re-enter credentials and try again?", say **YES**
   - **Expected**: Should prompt for a new token
   - Enter a **valid token**
   - **Expected**: Validation should succeed

4. **Expected output**:
   ```
   ✗ API validation failed: Invalid token or token has expired (attempt 1/3)
   Re-enter credentials and try again? [Y/n]: y
   Create token at: https://github.com/settings/tokens/new
   Required scopes: repo (or public_repo for public repos)
   GitHub Personal Access Token: [password input]  ← NEW PROMPT!
   ✓ GitHub token verified (user: your_username)
   ```

## Backward Compatibility

✅ **Fully backward compatible**
- `credential_prompter` parameter is optional with default `None`
- Existing behavior preserved when prompter not provided
- No breaking changes to public API

## Related Issues

- Primary Project: https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267/issues
- Bug Report: User-reported credential re-entry issue in setup wizard

## Next Steps

1. ✅ Create bugfix branch
2. ✅ Implement credential prompter callback
3. ✅ Update all callers (Linear, GitHub, JIRA)
4. ✅ Add comprehensive test coverage
5. ✅ Verify all tests pass
6. ✅ Apply code formatting (black)
7. ✅ Commit changes with descriptive message
8. ⏳ Create pull request to `main`
9. ⏳ Merge after review

## Summary

This fix resolves a critical UX bug where users couldn't recover from entering invalid credentials during setup. The credential prompter callback pattern enables proper re-prompting on validation failure while maintaining backward compatibility.

**Impact**: Improves setup wizard usability and reduces user frustration when entering credentials.

---
*Generated: 2025-12-16*
*Branch: `bugfix/credential-reentry-prompt`*
*Commit: `18bcf7a`*
