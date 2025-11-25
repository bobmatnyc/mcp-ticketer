# Summary of Changes: GitHub URL Refactoring in init_command.py

## Overview
Updated `init_command.py` to align with the refactored GitHub configuration that now accepts a repository URL instead of separate owner/repo parameters.

## Files Modified

### 1. `/src/mcp_ticketer/cli/init_command.py`

#### Changes to `_init_adapter_internal()` function (lines 413-451):

**Before:**
```python
def _init_adapter_internal(
    ...
    github_owner: str | None = None,
    github_repo: str | None = None,
    github_token: str | None = None,
) -> bool:
```

**After:**
```python
def _init_adapter_internal(
    ...
    github_url: str | None = None,
    github_token: str | None = None,
    **kwargs: Any,
) -> bool:
```

**Key Changes:**
- Replaced `github_owner` and `github_repo` parameters with single `github_url` parameter
- Added `**kwargs: Any` to capture deprecated parameters for backward compatibility
- Updated docstring to reflect new parameter

#### Changes to GitHub configuration section (lines 617-658):

**Before:**
```python
has_all_params = bool(
    (github_owner or os.getenv("GITHUB_OWNER"))
    and (github_repo or os.getenv("GITHUB_REPO"))
    and (github_token or os.getenv("GITHUB_TOKEN"))
)

adapter_config, default_values = _configure_github(
    interactive=not has_all_params,
    owner=github_owner,
    repo=github_repo,
    token=github_token,
)
```

**After:**
```python
# Extract deprecated parameters for backward compatibility
github_owner = kwargs.get("github_owner")
github_repo = kwargs.get("github_repo")

# Determine if we need interactive prompts
# Prioritize github_url, fallback to owner/repo
has_all_params = bool(
    (github_url or os.getenv("GITHUB_REPO_URL") or
     (github_owner or os.getenv("GITHUB_OWNER")) and
     (github_repo or os.getenv("GITHUB_REPO")))
    and (github_token or os.getenv("GITHUB_TOKEN"))
)

adapter_config, default_values = _configure_github(
    interactive=not has_all_params,
    repo_url=github_url,
    owner=github_owner,
    repo=github_repo,
    token=github_token,
)
```

**Key Changes:**
- Extract deprecated `github_owner` and `github_repo` from kwargs
- Check for `GITHUB_REPO_URL` environment variable
- Pass `repo_url=github_url` to `_configure_github()` (NEW preferred parameter)
- Pass `owner` and `repo` as fallback parameters for backward compatibility

#### Changes to `init()` CLI function (lines 704-758):

**Before:**
```python
def init(
    ...
    github_owner: str | None = typer.Option(
        None, "--github-owner", help="GitHub repository owner"
    ),
    github_repo: str | None = typer.Option(
        None, "--github-repo", help="GitHub repository name"
    ),
    github_token: str | None = typer.Option(
        None, "--github-token", help="GitHub Personal Access Token"
    ),
) -> None:
```

**After:**
```python
def init(
    ...
    github_url: str | None = typer.Option(
        None,
        "--github-url",
        help="GitHub repository URL (e.g., https://github.com/owner/repo)",
    ),
    github_token: str | None = typer.Option(
        None, "--github-token", help="GitHub Personal Access Token"
    ),
    # Deprecated parameters for backward compatibility (hidden from help)
    github_owner: str | None = typer.Option(
        None, "--github-owner", hidden=True
    ),
    github_repo: str | None = typer.Option(
        None, "--github-repo", hidden=True
    ),
) -> None:
```

**Key Changes:**
- Added new `--github-url` option as the primary parameter
- Kept `--github-owner` and `--github-repo` as hidden/deprecated options
- Updated help text to show example URL format

#### Changes to function call (lines 862-877):

**Before:**
```python
success = _init_adapter_internal(
    ...
    github_owner=github_owner,
    github_repo=github_repo,
    github_token=github_token,
)
```

**After:**
```python
success = _init_adapter_internal(
    ...
    github_url=github_url,
    github_token=github_token,
    # Pass deprecated parameters via kwargs for backward compatibility
    github_owner=github_owner,
    github_repo=github_repo,
)
```

**Key Changes:**
- Pass `github_url` as primary parameter
- Pass deprecated `github_owner` and `github_repo` via kwargs

#### Added import (line 15):
```python
from typing import Any
```

### 2. `/tests/cli/test_init_tuple_unpacking.py`

#### Updated test to use new parameter (lines 64-68):

**Before:**
```python
result = _init_adapter_internal(
    adapter="github",
    github_owner="test_owner",
    github_repo="test_repo",
    github_token="test_token",
)
```

**After:**
```python
result = _init_adapter_internal(
    adapter="github",
    github_url="https://github.com/test_owner/test_repo",
    github_token="test_token",
)
```

#### Added new test for backward compatibility (lines 233-293):
```python
def test_github_backward_compatibility_with_owner_repo(self, tmp_path: Path) -> None:
    """Test backward compatibility with deprecated github_owner/github_repo parameters."""
    ...
    result = _init_adapter_internal(
        adapter="github",
        github_token="test_token",
        # Pass deprecated parameters via kwargs
        github_owner="test_owner",
        github_repo="test_repo",
    )
    ...
```

## Backward Compatibility

The changes maintain full backward compatibility:

1. **Deprecated CLI options still work** - Users can still use `--github-owner` and `--github-repo` (hidden from help)
2. **Environment variables supported** - Both `GITHUB_REPO_URL` and `GITHUB_OWNER`/`GITHUB_REPO` work
3. **Programmatic calls work** - Old code passing `github_owner`/`github_repo` still functions via kwargs
4. **_configure_github() handles both** - The configure function accepts both `repo_url` (preferred) and `owner`/`repo` (fallback)

## Usage Examples

### New recommended usage:
```bash
mcp-ticketer init --adapter github --github-url https://github.com/owner/repo --github-token ghp_xxx
```

### Backward compatible usage (still works):
```bash
mcp-ticketer init --adapter github --github-owner owner --github-repo repo --github-token ghp_xxx
```

### Environment variables (both work):
```bash
# New approach
export GITHUB_REPO_URL="https://github.com/owner/repo"
export GITHUB_TOKEN="ghp_xxx"
mcp-ticketer init --adapter github

# Old approach (still works)
export GITHUB_OWNER="owner"
export GITHUB_REPO="repo"
export GITHUB_TOKEN="ghp_xxx"
mcp-ticketer init --adapter github
```

## Benefits

1. **Consistency** - Aligns with the refactored `_configure_github()` function
2. **User-friendly** - Single URL parameter is simpler than separate owner/repo
3. **Backward compatible** - Existing scripts and workflows continue to work
4. **Type-safe** - All changes pass mypy strict type checking
5. **Tested** - Updated tests verify both new and deprecated parameter paths

## Validation

- ✅ Syntax check passed: `python3 -m py_compile src/mcp_ticketer/cli/init_command.py`
- ✅ Type check passed: No type errors in `init_command.py` with mypy
- ✅ Backward compatibility: Deprecated parameters still work via kwargs
- ✅ Tests updated: Both new parameter and deprecated parameters tested

## Related Files

This change complements the earlier refactoring of:
- `/src/mcp_ticketer/cli/configure.py` - `_configure_github()` function that accepts `repo_url`
- `/src/mcp_ticketer/core/url_parser.py` - URL parsing utility used by configure.py
