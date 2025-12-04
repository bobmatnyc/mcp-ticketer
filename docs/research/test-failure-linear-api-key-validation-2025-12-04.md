# Test Failure Investigation: Linear API Key Validation (2025-12-04)

## Executive Summary

**Pre-existing test failure identified during QA testing of config tool fix (1M-652).**

- **Test**: `test_config_setup_wizard_linear_with_team_key`
- **Location**: `tests/mcp/test_config_tools.py:1344`
- **Issue**: Test API key is 37 characters instead of required 40 characters
- **Root Cause**: Validation pattern in `config_get_adapter_requirements` requires exactly 40 alphanumeric characters after `lin_api_` prefix
- **Impact**: Test fails validation before reaching mock health check
- **Fix Required**: Update test API keys to have exactly 40 characters after prefix

## Investigation Details

### 1. Validation Pattern Location

**File**: `src/mcp_ticketer/mcp/server/tools/config_tools.py`
**Line**: 1050

```python
"linear": {
    "api_key": {
        "type": "string",
        "required": True,
        "description": "Linear API key (get from Linear Settings > API)",
        "env_var": "LINEAR_API_KEY",
        "validation": "^lin_api_[a-zA-Z0-9]{40}$",  # <-- Requires EXACTLY 40 chars
    },
    ...
}
```

### 2. Current Test API Keys (Failing)

**Test**: `test_config_setup_wizard_linear_with_team_key` (line 1372)
**Test**: `test_config_setup_wizard_linear_with_team_id` (line 1417)

```python
# Current failing API key (38 chars after prefix, 46 total)
"api_key": "lin_api_[REDACTED_40_CHARS]"
#          ^^^^^^^^ prefix
#                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ 38 chars (WRONG - need 40)
```

**Character Count Analysis:**
- Full key: `lin_api_[REDACTED_40_CHARS]`
- Full length: 46 characters
- Prefix: `lin_api_` (8 characters)
- After prefix: `TESTKEY0000000000000000000000000000000` (38 characters)
- **Required**: 40 characters after prefix
- **Shortfall**: 2 characters

### 3. Validation Enforcement

The 40-character validation is **ONLY** enforced in:
- `config_setup_wizard()` via `config_get_adapter_requirements()` regex validation (line 1050-1262)

It is **NOT** enforced in:
- `LinearAdapter.__init__()` - only checks prefix `lin_api_` (src/mcp_ticketer/adapters/linear/adapter.py:146)
- Other adapter initialization paths

This explains why many existing tests use shorter API keys (they bypass `config_setup_wizard`).

### 4. Other Tests with Short API Keys

**Tests bypassing validation** (no config_setup_wizard):
```
tests/core/test_env_discovery.py:
  - lin_api_test123456789012345678 (22 chars)
  - lin_api_test123 (7 chars)

tests/integration/test_adapter_epic_attachments.py:
  - lin_api_test_key (8 chars)

tests/integration/test_linear_epic_file_workflow.py:
  - lin_api_test_key_12345678901234567890 (29 chars)

tests/mcp/test_phase1_scoping.py:
  - lin_api_key (3 chars)

tests/mcp/test_config_tools.py:
  - lin_api_existing (8 chars) [line 1548, 1575]
```

These tests work because they don't call `config_setup_wizard()` which enforces the regex.

## Recommended Fix

### Option 1: Update Test API Keys (RECOMMENDED)

Update the two failing tests to use a 40-character suffix:

```python
# CORRECT: 40 chars after prefix (48 total)
"api_key": "lin_api_[REDACTED_40_CHARS]00"
#          ^^^^^^^^ prefix (8 chars)
#                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ 40 chars ✅
```

**Affected Tests:**
1. `test_config_setup_wizard_linear_with_team_key` (line 1372)
2. `test_config_setup_wizard_linear_with_team_id` (line 1417)

**Changes Required:**
```python
# Line 1372 - OLD
"api_key": "lin_api_[REDACTED_40_CHARS]",

# Line 1372 - NEW (add 2 zeros)
"api_key": "lin_api_[REDACTED_40_CHARS]00",

# Line 1417 - OLD
"api_key": "lin_api_[REDACTED_40_CHARS]",

# Line 1417 - NEW (add 2 zeros)
"api_key": "lin_api_[REDACTED_40_CHARS]00",
```

### Option 2: Relax Validation Pattern (NOT RECOMMENDED)

Change validation pattern to allow any length:
```python
"validation": "^lin_api_[a-zA-Z0-9]+$",  # Allow any length
```

**Reasons NOT to do this:**
- Real Linear API keys are exactly 40 characters after prefix
- Validation should match actual API key format
- Tests should validate realistic scenarios
- Other adapters may rely on strict format validation

## Verification

### Test the Fix

```bash
# Run the failing tests
pytest tests/mcp/test_config_tools.py::TestConfigSetupWizard::test_config_setup_wizard_linear_with_team_key -v
pytest tests/mcp/test_config_tools.py::TestConfigSetupWizard::test_config_setup_wizard_linear_with_team_id -v

# Or run all config setup wizard tests
pytest tests/mcp/test_config_tools.py::TestConfigSetupWizard -v
```

### Validation Script

```python
import re

# Validation pattern from config_tools.py
pattern = r"^lin_api_[a-zA-Z0-9]{40}$"

# Corrected test key
test_key = "lin_api_[REDACTED_40_CHARS]00"

# Verify
assert len(test_key) == 48, f"Expected 48 chars, got {len(test_key)}"
assert len(test_key[8:]) == 40, f"Expected 40 chars after prefix, got {len(test_key[8:])}"
assert re.match(pattern, test_key), "Key doesn't match validation pattern"

print("✅ Test key is valid!")
```

## Implementation Summary

**Files to Update:**
- `tests/mcp/test_config_tools.py` (2 occurrences at lines 1372 and 1417)

**Changes:**
- Add 2 zeros to each test API key (from 38 to 40 chars after prefix)

**No Changes Needed:**
- `src/mcp_ticketer/mcp/server/tools/config_tools.py` (validation is correct)
- Other test files (they bypass config_setup_wizard validation)

**Related Ticket:**
- This issue is separate from 1M-652 (config tool kwargs fix)
- Pre-existing failure, not caused by recent changes

## Conclusion

The test failure is due to an incorrect test API key length. The validation pattern is correct and matches real Linear API key format (40 alphanumeric characters after `lin_api_` prefix).

**Recommended Action**: Update test API keys by adding 2 zeros to match the 40-character requirement.

**Estimated Effort**: 5 minutes (2 line changes)

**Risk**: Very low - only affects test data, no production code changes
