# Issue Resolution: Pytest Configuration Error

**Issue ID**: Pytest Plugin Configuration Error
**Date**: 2025-11-24
**Status**: ✅ Resolved
**Impact**: Development workflow blocked - pytest could not run

## Problem Statement

Pytest was failing with the following error:

```
ERROR: usage: pytest [options] [file_or_dir] [file_or_dir] [...]
pytest: error: unrecognized arguments: --cov=src/mcp_ticketer --cov-branch
--cov-report=term-missing:skip-covered --cov-report=html --cov-report=xml
--cov-fail-under=12 --timeout=60 --timeout-method=thread
  inifile: /Users/masa/Projects/mcp-ticketer/pytest.ini
  rootdir: /Users/masa/Projects/mcp-ticketer
```

This prevented:
- Running unit tests
- Generating code coverage reports
- Using timeout features for long-running tests
- Continuous integration workflows

## Root Cause Analysis

### Environment Discovery

The system had multiple pytest installations:

| Location | Version | Plugins | Used By |
|----------|---------|---------|---------|
| `/Users/masa/.local/bin/pytest` | 8.4.2 | ❌ None | Global user install |
| `.venv/bin/pytest` | 8.4.2 | ✅ All | Project venv |
| `venv/bin/pytest` | 8.4.2 | ⚠️ Unknown | Old venv |

### The Problem

When running `pytest` without activating the virtual environment:

1. Shell searches `$PATH` for pytest executable
2. Finds `/Users/masa/.local/bin/pytest` first (global install)
3. Global pytest lacks required plugins:
   - `pytest-cov` (for coverage reports)
   - `pytest-timeout` (for test timeouts)
4. pytest.ini references these plugins in `addopts`
5. Global pytest rejects unrecognized arguments

### Expected Configuration

The `pytest.ini` configuration requires:

```ini
[pytest]
addopts =
    --cov=src/mcp_ticketer          # Requires: pytest-cov>=4.1.0
    --cov-branch
    --cov-report=term-missing:skip-covered
    --cov-report=html
    --cov-report=xml
    --cov-fail-under=12
    --timeout=60                     # Requires: pytest-timeout>=2.2.0
    --timeout-method=thread
```

These plugins are defined in `requirements-dev.txt`:
- `pytest>=7.4.0`
- `pytest-asyncio>=0.21.0`
- `pytest-cov>=4.1.0` ← Missing from global
- `pytest-timeout>=2.2.0` ← Missing from global
- `pytest-mock>=3.12.0`
- `pytest-xdist>=3.5.0`

## Solution Implemented

### Primary Solution: Use Project Virtual Environment

The `.venv` directory contains all required dependencies:

```bash
# Activate the virtual environment
source .venv/bin/activate

# Verify correct environment
which pytest
# Output: /Users/masa/Projects/mcp-ticketer/.venv/bin/pytest

# Verify plugins installed
pip list | grep pytest
# Output shows all pytest-* plugins
```

### Verification

Comprehensive testing confirms the fix:

```bash
=== Environment Check ===
Python:  /Users/masa/Projects/mcp-ticketer/.venv/bin/python (3.13.7)
Pytest:  /Users/masa/Projects/mcp-ticketer/.venv/bin/pytest (8.4.2)

=== Installed Plugins ===
pytest                 8.4.2
pytest-asyncio         1.2.0
pytest-cov             7.0.0    ✅ Required for --cov
pytest-mock            3.15.1
pytest-timeout         2.4.0    ✅ Required for --timeout
pytest-xdist           3.6.1

=== Test Collection ===
✅ Successfully collected 800+ tests across all modules
```

## Automation Added

### 1. Development Environment Guide

**File**: `docs/DEVELOPMENT_ENVIRONMENT.md`

Comprehensive guide covering:
- Environment setup and activation
- Troubleshooting common issues
- IDE configuration (VS Code, PyCharm)
- Best practices for development
- Command reference

### 2. Quick Activation Script

**File**: `activate-dev-env.sh`

```bash
# Usage:
source activate-dev-env.sh

# Automatically:
# 1. Activates .venv
# 2. Verifies setup
# 3. Shows helpful commands
```

### 3. Visual Reminder

**File**: `.venv-activate-reminder`

Quick reference card for developers:
```bash
./venv-activate-reminder
# Shows formatted reminder to activate venv
```

### 4. Direnv Support (Optional)

**File**: `.envrc`

For users with direnv installed:
- Automatically activates .venv when entering project directory
- Deactivates when leaving

### 5. Updated Documentation

**Modified Files**:
- `README.md` - Updated dev environment section
- Added reference to troubleshooting guide

**New Files**:
- `docs/DEVELOPMENT_ENVIRONMENT.md` - Complete guide
- `docs/PYTEST_FIX_SUMMARY.md` - Issue-specific summary
- `docs/ISSUE_RESOLUTION_PYTEST_PLUGINS.md` - This file

## Developer Workflow

### Before (Broken)

```bash
cd /Users/masa/Projects/mcp-ticketer
pytest  # ❌ Uses global pytest, fails
```

### After (Fixed)

```bash
cd /Users/masa/Projects/mcp-ticketer
source .venv/bin/activate  # ✅ Use project venv
pytest                      # ✅ Works correctly

# Or use quick script:
source activate-dev-env.sh  # ✅ Easier activation
```

### IDE Users

**VS Code**: Configure `.vscode/settings.json` to use `.venv/bin/python`
**PyCharm**: Set project interpreter to `.venv/bin/python`

## Prevention Measures

### 1. Documentation

- Clear setup instructions in README
- Troubleshooting guide for environment issues
- Quick reference for common commands

### 2. Helper Scripts

- `activate-dev-env.sh` - Easy activation
- `.venv-activate-reminder` - Visual reminder
- `.envrc` - Automatic activation (optional)

### 3. Development Practices

Added to documentation:
- Always activate venv before development
- Use `which python` to verify environment
- Run `make test` instead of direct pytest (handles venv)

### 4. CI/CD

CI/CD pipelines already use isolated environments and are not affected by this issue.

## Impact Assessment

### Before Fix

- ❌ Cannot run pytest locally
- ❌ Cannot generate coverage reports
- ❌ Blocked development workflow
- ⚠️ CI/CD unaffected (uses isolated environments)

### After Fix

- ✅ Pytest works correctly
- ✅ Coverage reports generate
- ✅ All dev tools functional
- ✅ Clear documentation prevents recurrence
- ✅ Helper scripts simplify workflow

## Lessons Learned

### For Developers

1. **Environment Isolation**: Always use project virtual environments
2. **Verification**: Check `which python` and `which pytest` regularly
3. **Documentation**: Read setup guides before starting development

### For Project Maintainers

1. **Clear Documentation**: Essential for onboarding and troubleshooting
2. **Helper Scripts**: Reduce friction in common tasks
3. **Environment Detection**: Consider adding environment checks to test scripts

## References

- **Setup Guide**: [docs/DEVELOPMENT_ENVIRONMENT.md](DEVELOPMENT_ENVIRONMENT.md)
- **Fix Summary**: [docs/PYTEST_FIX_SUMMARY.md](PYTEST_FIX_SUMMARY.md)
- **Build System**: [docs/DEVELOPMENT.md](DEVELOPMENT.md)
- **Makefile Ref**: [.makefiles/QUICK_REFERENCE.md](../.makefiles/QUICK_REFERENCE.md)

## Test Results

### Verification Commands

```bash
source .venv/bin/activate

# Test 1: Version check
pytest --version
# ✅ pytest 8.4.2

# Test 2: Plugin verification
pip list | grep pytest
# ✅ All plugins present

# Test 3: Test collection
pytest --co -q tests/ | head -10
# ✅ Successfully collected 800+ tests

# Test 4: Sample test run
pytest tests/adapters/linear/test_mappers.py -v
# ✅ All tests pass
```

## Resolution Summary

**Problem**: Pytest failed due to missing plugins in global installation
**Cause**: Using system pytest instead of project venv pytest
**Solution**: Activate `.venv` before running pytest
**Prevention**: Documentation, helper scripts, IDE configuration
**Status**: ✅ Fully resolved with comprehensive documentation

---

**Resolution Date**: 2025-11-24
**Resolved By**: AI Ops Agent (Claude Code)
**Verification**: Complete
**Documentation**: Complete
**Status**: ✅ Closed
