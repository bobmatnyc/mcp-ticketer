# Issue #53 Implementation Summary

## Feature: Setup command credential update without full re-init

### Implementation Details

**Files Modified:**
- `src/mcp_ticketer/cli/setup_command.py`
  - Added `_prompt_and_update_credentials()` function (lines 496-706)
  - Integrated credential update into existing setup flow (line 343)
  - Reuses existing validation logic from `configure.py`

**Files Created:**
- `tests/cli/test_setup_credential_update.py` (456 lines)
  - 13 comprehensive test cases covering all adapters
  - Tests for success, decline, validation failure, error handling, and masking

### User Experience

When running `mcp-ticketer setup` with existing configuration:

```
✓ Configuration detected
  Adapter: github
  Location: .mcp-ticketer/config.json

Configuration already exists. Keep existing settings? [Y/n]: y

Would you like to update your credentials? [y/N]: y
Create token at: https://github.com/settings/tokens/new
Required scopes: repo (or public_repo for public repos)
GitHub Token [current: ghp_oldt****]: [user enters new token]
✓ GitHub token verified (user: username)

✓ Credentials updated
```

### Features Implemented

1. **Credential Update Prompt** (line 516-517)
   - Non-intrusive: Defaults to "No" to avoid forcing updates
   - Only prompts if user keeps existing settings

2. **Adapter-Specific Handling** (lines 529-680)
   - **Linear**: API key with validation
   - **GitHub**: Token with validation and helpful instructions
   - **JIRA**: API token (required), server URL (optional), email (optional)
   - **AITrackdown**: Appropriate message (no credentials needed)

3. **Credential Validation** (lines 544-597)
   - Reuses `_validate_api_credentials()` from `configure.py`
   - Retry on failure with re-prompting
   - Preserves existing retry/validation UX

4. **Credential Masking** (lines 533, 559, 638)
   - Uses `_mask_sensitive_value()` to show first 8 chars + ****
   - Improves security by not displaying full credentials

5. **Error Handling** (lines 693-705)
   - JSON decode errors
   - File I/O errors
   - Unexpected exceptions with helpful recovery messages

### Test Coverage

**13 Test Cases** covering:

1. **GitHub Adapter** (3 tests)
   - Successful credential update
   - User declining update
   - Validation failure handling

2. **Linear Adapter** (2 tests)
   - Successful credential update
   - User declining update

3. **JIRA Adapter** (3 tests)
   - Successful token-only update
   - Update all fields (server, email, token)
   - User declining update

4. **AITrackdown Adapter** (1 test)
   - Appropriate message for no-credential adapter

5. **Error Handling** (2 tests)
   - Invalid JSON configuration
   - Missing configuration file

6. **Credential Masking** (2 tests)
   - GitHub token masking
   - Linear API key masking

### Integration Points

- **Line 343**: Inserted between "Keep existing settings" and "Update default values"
- **Imports**: Reuses `_mask_sensitive_value` and `_validate_api_credentials` from `configure.py`
- **Config Update**: Updates `.mcp-ticketer/config.json` in place
- **MCP Sync**: Existing `_update_mcp_json_credentials()` call (line 350) syncs to `.mcp.json`

### Backward Compatibility

- ✅ No breaking changes to existing setup flow
- ✅ Existing configurations continue to work
- ✅ Default behavior unchanged (user must opt-in to update)
- ✅ All existing tests pass (19/19 credential tests)

### Security Considerations

- ✅ Credentials masked in prompts (first 8 chars + ****)
- ✅ Password input mode (`hide_input=True`) for sensitive fields
- ✅ Validation before saving to prevent invalid credentials
- ✅ Config file remains in `.mcp-ticketer/` (gitignored directory)

### Performance Impact

- Minimal: Only runs when user opts in to update
- No additional API calls unless user chooses to update
- Validation happens during update (same as init flow)

### Testing Results

```
✓ 13/13 new tests pass
✓ 19/19 credential-related tests pass
✓ No regressions in existing CLI tests
```

### Lines of Code Delta

```
LOC Delta:
- Added: 211 lines (implementation)
- Added: 456 lines (tests)
- Removed: 0 lines
- Net Change: +667 lines
- Phase: Enhancement (credential management)
```

### Related Issues

- Issue #53: Setup command should allow updating credentials without full re-init
- Addresses user feedback about cumbersome re-initialization process
