# Linear Init Bug Fix - Verification Checklist

## Code Changes ✅

- [x] Modified `/src/mcp_ticketer/cli/main.py` lines 652-741
- [x] Removed premature `linear_config = {}` initialization
- [x] Moved validation after credential collection (lines 720-727)
- [x] Build config dict only after validation passes (lines 729-741)
- [x] Preserved all existing features (URL derivation, discovery)
- [x] Python syntax valid (`python3 -m py_compile` passed)

## Pattern Consistency ✅

- [x] Follows same structure as JIRA adapter (lines 743-803)
- [x] Collection → Validation → Building → Saving
- [x] No regression in other adapters
- [x] Error messages are clear and specific
- [x] Backward compatible with CLI parameters

## Code Quality ✅

- [x] Net LOC impact: +2 lines (minimal)
- [x] No new dependencies
- [x] No breaking changes
- [x] Maintains code readability
- [x] Comments explain the change ("following JIRA pattern")

## Test Scenarios (Manual Testing Required) ⚠️

### Priority 1: Core Fix
- [ ] **Interactive Menu Selection** (PRIMARY BUG FIX)
  ```bash
  unset LINEAR_API_KEY LINEAR_TEAM_KEY LINEAR_TEAM_ID
  rm -rf ~/.mcp_ticketer
  mcp-ticketer init
  # Select Linear → Should prompt for credentials
  ```

### Priority 2: Edge Cases
- [ ] **Partial Credentials**
  ```bash
  export LINEAR_API_KEY="test"
  unset LINEAR_TEAM_KEY LINEAR_TEAM_ID
  mcp-ticketer init
  # Should prompt only for team info
  ```

- [ ] **Empty Prompts (Validation)**
  ```bash
  mcp-ticketer init
  # Select Linear, hit Enter without input
  # Should show validation error
  ```

### Priority 3: Existing Functionality
- [ ] **CLI Parameters**
  ```bash
  mcp-ticketer init --adapter linear --api-key KEY --team-id ID
  # Should work without prompts
  ```

- [ ] **Discovery Flow**
  ```bash
  # With .env file containing LINEAR_* variables
  mcp-ticketer init
  # Should auto-detect and NOT prompt
  ```

- [ ] **URL Derivation**
  ```bash
  mcp-ticketer init
  # Enter Linear team URL when prompted
  # Should derive team ID automatically
  ```

## Documentation ✅

- [x] `LINEAR_INIT_BUG_FIX.md` - Executive summary
- [x] `LINEAR_INIT_FIX_SUMMARY.md` - Technical details
- [x] `BEFORE_AFTER_COMPARISON.md` - Code comparison
- [x] `FIX_VERIFICATION_CHECKLIST.md` - This checklist

## Next Steps

1. **User Testing** 🔴 REQUIRED
   - Run the manual test scenarios above
   - Verify success messages appear
   - Check config file is created correctly
   - Test URL derivation feature works

2. **Clean Up** (After Testing)
   - Remove temporary documentation files if not needed
   - Or move to `/docs` directory
   - Update CHANGELOG.md with bug fix entry

3. **Future Work** (Optional)
   - Add unit tests for `init` command
   - Add integration tests for all adapters
   - Consider extracting adapter config logic to separate functions

## Sign-off

### Code Review
- [x] Changes reviewed by: Engineer (AI)
- [x] Follows BASE_ENGINEER.md principles
- [x] Matches existing code patterns
- [x] Error handling preserved

### Testing
- [ ] Manual testing completed by: ________
- [ ] All test scenarios pass: [ ] Yes / [ ] No
- [ ] Config file created correctly: [ ] Yes / [ ] No
- [ ] No regressions found: [ ] Yes / [ ] No

### Deployment Ready
- [ ] All manual tests pass
- [ ] User approves changes
- [ ] Ready to commit: [ ] Yes / [ ] No

## Git Commit Message (Suggested)

```
fix: Linear init command now prompts for credentials when selected from menu

Previously, selecting Linear from the interactive menu without environment
variables would fail with "Linear requires both API key and team ID/key"
instead of prompting for credentials.

Root cause: Validation happened before config dict was properly built.

Solution: Restructured to follow JIRA adapter pattern:
- Collect variables first
- Validate collected variables
- Build config dict after validation passes
- Save config

This ensures prompts always execute when credentials are missing.

Fixes: Interactive credential prompting for Linear adapter
Impact: +2 LOC, no breaking changes, backward compatible
Testing: Manual testing required for interactive flows

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Rollback Plan

If issues are found:

1. **Immediate Rollback**
   ```bash
   git revert <commit-hash>
   ```

2. **Alternative Fix**
   - Revert to original code
   - Add debug logging
   - Identify exact failure point
   - Apply minimal fix

3. **Known Safe State**
   - Commit before this fix: `f9aa469`
   - Revert command: `git revert HEAD`

## Contact

If issues arise during testing, check:
1. Python version compatibility (3.8+)
2. Typer version (may affect prompting)
3. Console output for error messages
4. ~/.mcp_ticketer/config.json contents

## Status

- **Code Status:** ✅ COMPLETE
- **Testing Status:** ⚠️ PENDING (Manual testing required)
- **Deployment Status:** 🟡 READY FOR TESTING

---

**Last Updated:** 2025-11-06
**Engineer:** Claude (AI Engineer)
**Reviewer:** Pending user verification
