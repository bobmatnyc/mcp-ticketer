# Linear Init Bug Fix Summary

## Problem Statement
When users ran `mcp-ticketer init` without any adapter detected and selected "Linear" from the interactive menu, they would receive an error:
```
Error: Linear requires both API key and team ID/key
```

Instead of being prompted interactively for credentials.

## Root Cause
In `/src/mcp_ticketer/cli/main.py` (lines 652-743), the Linear configuration logic had a premature validation check that would exit with an error BEFORE the interactive prompts had a chance to collect credentials.

The problematic flow was:
1. Lines 658-723: Collect credentials (prompts or environment variables)
2. Lines 731-740: **EARLY VALIDATION** - Check if `linear_config` has required fields
3. Line 743: Save config (never reached if validation failed)

The issue: When prompts completed successfully but the user provided valid input, the validation would check a partially-built `linear_config` dictionary and exit before saving.

## Solution Implemented

### Changes Made
Restructured the Linear configuration section (lines 652-741) to follow the same pattern as the JIRA adapter:

**Key Changes:**
1. **Removed premature config dict building** - Don't build `linear_config = {}` at the start
2. **Collect credentials first** - Keep all prompt and environment variable logic (lines 656-718)
3. **Validate AFTER collection** - Move validation to lines 720-727, AFTER all prompts complete
4. **Build config last** - Only construct `linear_config` dict after validation passes (lines 729-741)

### Code Structure (New Flow)
```python
elif adapter_type == "linear":
    if adapter_type not in config["adapters"]:
        # 1. Collect API key (prompt if missing)
        linear_api_key = api_key or os.getenv("LINEAR_API_KEY")
        if not linear_api_key and not discovered:
            # ... interactive prompt ...

        # 2. Collect team info (prompt if missing)
        linear_team_key = os.getenv("LINEAR_TEAM_KEY")
        linear_team_id = team_id or os.getenv("LINEAR_TEAM_ID")
        if not linear_team_key and not linear_team_id and not discovered:
            # ... interactive prompt ...

        # 3. VALIDATE (after collection complete)
        if not linear_api_key:
            console.print("[red]Error:[/red] Linear API key is required")
            raise typer.Exit(1)

        if not linear_team_id and not linear_team_key:
            console.print("[red]Error:[/red] Linear requires either team ID or team key")
            raise typer.Exit(1)

        # 4. BUILD config dict (only after validation passes)
        linear_config = {
            "api_key": linear_api_key,
            "type": "linear",
        }

        if linear_team_key:
            linear_config["team_key"] = linear_team_key
        if linear_team_id:
            linear_config["team_id"] = linear_team_id

        # 5. SAVE config
        config["adapters"]["linear"] = linear_config
```

## Test Scenarios

### Scenario 1: Interactive Menu Selection (PRIMARY FIX)
**Before:** Error immediately after selection
**After:** Prompts for API key and team info

Steps:
1. Run `mcp-ticketer init` with no LINEAR_* env vars
2. No adapter discovered
3. Select "Linear" from menu (option 1)
4. Should prompt: "Enter your Linear API key"
5. Should prompt: "Team URL, key, or ID"
6. Should save config successfully

### Scenario 2: Partial Environment Variables
**Before:** Same error
**After:** Prompts only for missing values

Example: If `LINEAR_API_KEY` exists but no team info:
- Should NOT prompt for API key
- Should prompt for team info
- Should save config with both values

### Scenario 3: CLI Parameter Usage
**Before:** Worked (not affected)
**After:** Still works

Example: `mcp-ticketer init --adapter linear --api-key KEY`
- Should work as before (no regression)

### Scenario 4: Empty Prompts (Validation)
**Before:** Would fail at wrong point
**After:** Fails with clear error after prompts

If user hits Enter without providing values:
- Prompts complete
- Validation catches missing values
- Clear error message displayed
- Exits with code 1

### Scenario 5: Discovery Flow
**Before:** Worked (not affected)
**After:** Still works

If credentials found in .env files:
- Discovery succeeds
- `discovered` is truthy
- Prompts are skipped (correct behavior)
- Config saved from discovered values

## Implementation Notes

### Design Principles Applied
1. **Follow JIRA Pattern** - JIRA adapter (lines 745-803) has the correct structure
2. **Validate After Collection** - Don't validate partial state
3. **Clear Error Messages** - Each validation error is specific
4. **Preserve Features** - Linear URL derivation still works
5. **Backward Compatibility** - CLI parameters still work

### Why This Pattern?
The JIRA adapter demonstrates the correct pattern:
- Collect all values (lines 748-778)
- Validate each required field (lines 781-791)
- Build config dict (lines 793-801)
- Save config (line 803)

This ensures:
- Prompts always execute when values are missing
- Validation happens on final collected values
- Config is only built/saved when valid

## Testing Recommendations

### Manual Testing
1. **Clean Environment Test:**
   ```bash
   unset LINEAR_API_KEY LINEAR_TEAM_KEY LINEAR_TEAM_ID
   rm -rf ~/.mcp_ticketer
   mcp-ticketer init
   # Select Linear from menu
   # Provide test credentials when prompted
   # Verify success message
   ```

2. **Partial Credentials Test:**
   ```bash
   export LINEAR_API_KEY="test_key"
   unset LINEAR_TEAM_KEY LINEAR_TEAM_ID
   mcp-ticketer init
   # Should prompt only for team info
   ```

3. **URL Derivation Test:**
   ```bash
   unset LINEAR_API_KEY LINEAR_TEAM_KEY LINEAR_TEAM_ID
   mcp-ticketer init
   # Provide Linear team URL when prompted
   # Should derive team ID automatically
   ```

### Automated Testing
Consider adding unit tests to `tests/cli/` that mock:
- `typer.prompt()` to simulate user input
- `os.getenv()` to control environment state
- File I/O to prevent actual config writes

## Net Impact

### Lines of Code
- **Removed:** 13 lines (premature dict building and early validation)
- **Added:** 15 lines (proper validation and config building)
- **Net:** +2 lines (minimal complexity increase)

### Code Quality
- ✅ **Follows existing patterns** (JIRA adapter)
- ✅ **No new dependencies**
- ✅ **Backward compatible**
- ✅ **Preserves all features** (URL derivation, discovery, etc.)
- ✅ **Clearer error messages**

## Related Files
- `/src/mcp_ticketer/cli/main.py` - Main fix location (lines 652-741)
- `/src/mcp_ticketer/cli/linear_commands.py` - Linear URL derivation (unchanged)
- No test files currently exist for this functionality

## Future Improvements
1. Add unit tests for `init` command with Linear adapter
2. Consider extracting adapter configuration to separate functions
3. Add integration tests for all adapter types
4. Document expected prompt flow in user documentation
