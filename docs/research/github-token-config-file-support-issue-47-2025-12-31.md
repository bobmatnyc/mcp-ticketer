# GitHub Adapter Token Handling Research - Issue #47

**Research Date:** 2025-12-31
**Issue:** #47 - Support GITHUB_TOKEN from config file (not just env var)
**Current Status:** GitHub adapter only checks environment variable
**Desired Behavior:** Check env var first, then fall back to config file

---

## Executive Summary

The GitHub adapter currently supports token retrieval from config files through multiple layers of configuration resolution, but the Pydantic validator in `src/mcp_ticketer/core/config.py` **only checks environment variables** and raises an error if not found. This prevents users from storing tokens exclusively in config files.

**Key Finding:** The issue is NOT in the GitHub adapter itself, but in the `GitHubConfig` Pydantic model validator at lines 48-56 of `config.py`.

---

## Current Implementation Analysis

### 1. GitHub Adapter Token Retrieval Flow

**File:** `src/mcp_ticketer/adapters/github/adapter.py` (lines 64-97)

```python
def __init__(self, config: dict[str, Any]):
    # Load configuration with environment variable resolution
    full_config = load_adapter_config("github", config)

    # Get authentication token - support 'api_key' and 'token'
    self.token = (
        full_config.get("api_key")
        or full_config.get("token")
        or full_config.get("token")  # Note: duplicate check
    )
```

**Token Sources (in order of precedence):**
1. `full_config["api_key"]` - from config file or env loader
2. `full_config["token"]` - from config file or env loader
3. Duplicate check (likely a typo)

**Issue:** The adapter correctly accepts tokens from `full_config`, which includes both config file and environment variables. However, the Pydantic validator prevents this from working.

---

### 2. Configuration Resolution System

The project uses a **hierarchical configuration system** with multiple layers:

#### Layer 1: Pydantic Config Model (BLOCKING LAYER)

**File:** `src/mcp_ticketer/core/config.py` (lines 37-77)

```python
class GitHubConfig(BaseAdapterConfig):
    """GitHub adapter configuration."""

    type: AdapterType = AdapterType.GITHUB
    token: str | None = Field(default=None)
    owner: str | None = Field(default=None)
    repo: str | None = Field(default=None)

    @field_validator("token", mode="before")
    @classmethod
    def validate_token(cls, v: Any) -> str:
        """Validate GitHub token from config or environment."""
        if not v:
            v = os.getenv("GITHUB_TOKEN")  # ❌ ONLY checks env var
        if not v:
            raise ValueError("GitHub token is required")  # ❌ Raises error
        return cast(str, v)
```

**Problem:**
- Line 53: Only checks `os.getenv("GITHUB_TOKEN")` if `v` is not provided
- Line 55: Raises `ValueError` if token not found in env var
- Does NOT check config file before raising error

#### Layer 2: Project Configuration Resolution

**File:** `src/mcp_ticketer/core/project_config.py` (lines 596-764)

```python
def resolve_adapter_config(
    self,
    adapter_name: str | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve adapter configuration with hierarchical precedence.

    Resolution order (highest to lowest priority):
    1. CLI overrides
    2. Environment variables (os.getenv)
    3. Project-specific config (.mcp-ticketer/config.json)
    4. Auto-discovered .env files
    5. Global config (~/.mcp-ticketer/config.json)
    """
```

**Environment Variable Overrides (lines 691-764):**

```python
def _get_env_overrides(self, adapter_type: str) -> dict[str, Any]:
    """Get configuration overrides from environment variables."""
    overrides = {}

    if adapter_type == AdapterType.GITHUB.value:
        if os.getenv("MCP_TICKETER_GITHUB_TOKEN"):
            overrides["token"] = os.getenv("MCP_TICKETER_GITHUB_TOKEN")
        if os.getenv("GITHUB_TOKEN"):
            overrides["token"] = os.getenv("GITHUB_TOKEN")

    return overrides
```

**Supports:**
- `MCP_TICKETER_GITHUB_TOKEN` env var (higher priority)
- `GITHUB_TOKEN` env var (standard)
- Config file values (base config)

#### Layer 3: Environment Loader

**File:** `src/mcp_ticketer/core/env_loader.py` (lines 87-94, 233-265)

```python
# Key configuration
"github_token": EnvKeyConfig(
    primary_key="GITHUB_TOKEN",
    aliases=["GITHUB_ACCESS_TOKEN", "GITHUB_API_TOKEN", "GITHUB_AUTH_TOKEN"],
    description="GitHub access token",
    required=True,
)

def get_adapter_config(
    self, adapter_name: str, base_config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Get complete configuration for an adapter with environment variable resolution."""
    config = base_config.copy() if base_config else {}

    # Only set if not already in config or if config value is empty
    if simple_key not in config or not config[simple_key]:
        value = self.get_value(config_key, config)
        if value:
            config[simple_key] = value

    return config
```

**Key Logic:**
- Line 260: Only fetches from env if `simple_key not in config or not config[simple_key]`
- Respects config file values when present
- Falls back to environment variables only if config is empty

---

### 3. Config File Structure

**Example:** `.mcp-ticketer/config.json`

```json
{
  "default_adapter": "linear",
  "adapters": {
    "github": {
      "adapter": "github",
      "enabled": true,
      "token": "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",
      "owner": "bobmatnyc",
      "repo": "mcp-ticketer",
      "additional_config": {}
    }
  }
}
```

**Token Storage:** Config file already supports storing `token` field directly.

---

### 4. Comparison with Linear and JIRA Adapters

#### Linear Adapter Pattern

**File:** `src/mcp_ticketer/adapters/linear/adapter.py` (line 127)

```python
self.api_key = config.get("api_key") or os.getenv("LINEAR_API_KEY")
if not self.api_key:
    raise ValueError(
        "Linear API key is required (api_key or LINEAR_API_KEY env var)"
    )
```

**Pattern:** Checks config first, then env var, then raises error.

#### Linear Pydantic Config

**File:** `src/mcp_ticketer/core/config.py` (lines 121-147)

```python
class LinearConfig(BaseAdapterConfig):
    """Linear adapter configuration."""

    api_key: str | None = Field(default=None)

    @field_validator("api_key", mode="before")
    @classmethod
    def validate_api_key(cls, v: Any) -> str:
        """Validate Linear API key from config or environment."""
        if not v:
            v = os.getenv("LINEAR_API_KEY")
        if not v:
            raise ValueError("Linear API key is required")
        return cast(str, v)
```

**Same Problem:** Linear has identical pattern - only checks env var if config value is missing.

#### JIRA Adapter Pattern

**File:** `src/mcp_ticketer/adapters/jira/adapter.py` (line 83)

```python
self.api_token = full_config.get("api_token", "")
```

**Pattern:** Gets token directly from `full_config`, no env var fallback in adapter.

#### JIRA Pydantic Config

**File:** `src/mcp_ticketer/core/config.py` (lines 110-118)

```python
@field_validator("api_token", mode="before")
@classmethod
def validate_api_token(cls, v: Any) -> str:
    """Validate JIRA API token from config or environment."""
    if not v:
        v = os.getenv("JIRA_API_TOKEN")
    if not v:
        raise ValueError("JIRA API token is required")
    return cast(str, v)
```

**Same Problem:** JIRA also has identical pattern.

---

## Root Cause Analysis

### Problem Location

**File:** `src/mcp_ticketer/core/config.py`
**Lines:** 48-56 (GitHubConfig.validate_token)
**Lines:** 138-146 (LinearConfig.validate_api_key)
**Lines:** 110-118 (JiraConfig.validate_api_token)

### Issue

The Pydantic `@field_validator` decorators in these config classes **only check environment variables** when the config value is `None`. They do NOT attempt to load from config files before raising a `ValueError`.

This is problematic because:

1. **Config file values are loaded AFTER Pydantic validation** in the configuration resolution chain
2. **Pydantic validators run during model instantiation**, before project config resolution
3. **Validators raise errors**, preventing the config file value from ever being used

### Configuration Flow Sequence

```
User provides config file with token
    ↓
ConfigurationManager.load_config() called
    ↓
Pydantic model instantiation (GitHubConfig(**adapter_config))
    ↓
@field_validator("token") runs
    ↓
Checks: token in dict? No → Check os.getenv("GITHUB_TOKEN")? No → ❌ RAISE ERROR
    ↓
❌ Never gets to project config resolution
❌ Never gets to env_loader resolution
❌ Config file value never used
```

**Expected Flow:**

```
User provides config file with token
    ↓
ConfigurationManager.load_config() called
    ↓
Pydantic model instantiation (GitHubConfig(**adapter_config))
    ↓
@field_validator("token") runs
    ↓
Checks: token in dict? YES → ✅ Use config file value
    ↓
✅ Success - config file value used
```

---

## Recommended Implementation

### Option 1: Fix Pydantic Validators (RECOMMENDED)

**Modify validators to make tokens optional** and move validation to adapter initialization.

**File:** `src/mcp_ticketer/core/config.py`

**Current (lines 48-56):**

```python
@field_validator("token", mode="before")
@classmethod
def validate_token(cls, v: Any) -> str:
    """Validate GitHub token from config or environment."""
    if not v:
        v = os.getenv("GITHUB_TOKEN")
    if not v:
        raise ValueError("GitHub token is required")
    return cast(str, v)
```

**Recommended Change:**

```python
@field_validator("token", mode="before")
@classmethod
def validate_token(cls, v: Any) -> str | None:
    """Resolve GitHub token from config or environment.

    Priority:
    1. Config file value (v parameter)
    2. GITHUB_TOKEN environment variable

    Note: Actual validation happens in GitHubAdapter.__init__()
    """
    if not v:
        v = os.getenv("GITHUB_TOKEN")
    # Return None if not found - let adapter handle validation
    return cast(str, v) if v else None
```

**Key Changes:**
1. **Remove `raise ValueError`** - Allow `None` values through
2. **Return type:** `str | None` instead of `str`
3. **Move validation to adapter:** GitHub adapter already validates in `validate_credentials()` method

**Adapter Validation (already exists):**

**File:** `src/mcp_ticketer/adapters/github/adapter.py` (lines 141-147)

```python
def validate_credentials(self) -> tuple[bool, str]:
    """Validate GitHub credentials."""
    if not self.token:
        return (
            False,
            "GITHUB_TOKEN is required. Set it in .env.local or environment.",
        )
```

### Option 2: Load Config File Before Pydantic

**Restructure `ConfigurationManager.load_config()` to resolve config values before Pydantic validation.**

**Pros:**
- More explicit config file → env var precedence
- Keeps validation in Pydantic models

**Cons:**
- More complex implementation
- Breaks existing Pydantic validation flow
- May introduce ordering issues

### Option 3: Remove Pydantic Validators Entirely

**Let adapters handle all credential validation.**

**Pros:**
- Simplest implementation
- Adapters already have validation logic
- No config ordering issues

**Cons:**
- Loses Pydantic validation benefits
- Validation happens later in initialization
- Less declarative configuration

---

## Implementation Plan (Option 1)

### Step 1: Update Pydantic Config Models

**Files to modify:**
1. `src/mcp_ticketer/core/config.py` - Update `GitHubConfig`, `LinearConfig`, `JiraConfig`

**Changes:**
- Make validators return `str | None` instead of `str`
- Remove `raise ValueError` from validators
- Update docstrings to clarify validation happens in adapters

### Step 2: Verify Adapter Validation

**Verify these files have proper validation:**
1. `src/mcp_ticketer/adapters/github/adapter.py` - `validate_credentials()` ✅ (already present)
2. `src/mcp_ticketer/adapters/linear/adapter.py` - `validate_credentials()` ✅ (already present)
3. `src/mcp_ticketer/adapters/jira/adapter.py` - `validate_credentials()` ✅ (already present)

### Step 3: Update Error Messages

**Update adapter error messages to clarify both config and env var options:**

**Current:** `"GITHUB_TOKEN is required. Set it in .env.local or environment."`

**Recommended:** `"GitHub token is required. Provide 'token' in config file or set GITHUB_TOKEN environment variable."`

### Step 4: Add Tests

**Test cases needed:**
1. Token from config file only (no env var)
2. Token from env var only (no config file)
3. Token from both (env var should take precedence via project_config.py)
4. No token anywhere (should fail validation)

### Step 5: Update Documentation

**Files to update:**
1. Configuration guide - Add config file token examples
2. Setup guides - Clarify config vs env var options
3. TROUBLESHOOTING.md - Add config file token setup

---

## Precedence Verification

**After fix, token resolution order will be:**

1. **CLI overrides** (via `resolve_adapter_config(cli_overrides=...)`)
2. **Environment variables:**
   - `MCP_TICKETER_GITHUB_TOKEN`
   - `GITHUB_TOKEN`
3. **Project-specific config:** `.mcp-ticketer/config.json`
4. **Auto-discovered .env files**
5. **Pydantic validator:** Falls back to `os.getenv("GITHUB_TOKEN")` if all above fail

This matches the documented precedence in `project_config.py` (lines 603-608).

---

## Testing Strategy

### Unit Tests

**File:** `tests/adapters/test_github.py`

```python
def test_github_token_from_config_file():
    """Test that GitHub adapter accepts token from config file."""
    config = {
        "token": "ghp_test_token_from_config",
        "owner": "test-owner",
        "repo": "test-repo"
    }
    adapter = GitHubAdapter(config)
    assert adapter.token == "ghp_test_token_from_config"

def test_github_token_precedence():
    """Test that env var takes precedence over config file."""
    os.environ["GITHUB_TOKEN"] = "ghp_env_token"
    config = {
        "token": "ghp_config_token",
        "owner": "test-owner",
        "repo": "test-repo"
    }
    # Should use env var due to project_config resolution
    # Exact behavior depends on project_config.resolve_adapter_config()
```

### Integration Tests

**File:** `tests/integration/test_github_config_file.py` (new)

Test full config file → adapter initialization flow.

---

## Related Files

### Configuration System

| File | Lines | Purpose |
|------|-------|---------|
| `src/mcp_ticketer/core/config.py` | 48-56 | **MAIN ISSUE** - GitHubConfig validator |
| `src/mcp_ticketer/core/config.py` | 138-146 | LinearConfig validator (same issue) |
| `src/mcp_ticketer/core/config.py` | 110-118 | JiraConfig validator (same issue) |
| `src/mcp_ticketer/core/project_config.py` | 596-764 | Config resolution with precedence |
| `src/mcp_ticketer/core/env_loader.py` | 233-265 | Environment variable loading |

### Adapters

| File | Lines | Purpose |
|------|-------|---------|
| `src/mcp_ticketer/adapters/github/adapter.py` | 64-97 | GitHub adapter initialization |
| `src/mcp_ticketer/adapters/github/adapter.py` | 141-147 | GitHub credential validation |
| `src/mcp_ticketer/adapters/linear/adapter.py` | 127-131 | Linear API key loading |
| `src/mcp_ticketer/adapters/jira/adapter.py` | 83 | JIRA token loading |

### Config File Locations

| Path | Purpose |
|------|---------|
| `.mcp-ticketer/config.json` | Project-specific config (primary) |
| `mcp-ticketer.yaml` | Alternative YAML config |
| `mcp-ticketer.yml` | Alternative YML config |

---

## Conclusion

**The fix is straightforward:**

1. **Modify three Pydantic validators** in `config.py` to allow `None` values
2. **Remove `raise ValueError`** from validators
3. **Rely on existing adapter validation** in `validate_credentials()` methods
4. **Add tests** to verify config file token support
5. **Update documentation** to clarify config vs env var options

**Impact:**
- Fixes issue #47 for GitHub adapter
- Also fixes same issue for Linear and JIRA adapters
- Minimal code changes (3 validator functions)
- No breaking changes (env var behavior unchanged)
- Improves UX by supporting config file tokens

**Estimated Effort:** 2-3 hours (coding + testing + documentation)

**Risk Level:** Low (adapter validation already exists as safety net)

---

## Example Config After Fix

**`.mcp-ticketer/config.json`:**

```json
{
  "default_adapter": "github",
  "adapters": {
    "github": {
      "adapter": "github",
      "enabled": true,
      "token": "ghp_YourPersonalAccessTokenHere",
      "owner": "your-username",
      "repo": "your-repo"
    }
  }
}
```

**No environment variable needed!** ✅

---

**End of Research Document**
