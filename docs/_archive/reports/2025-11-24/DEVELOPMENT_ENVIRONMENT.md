# Development Environment Setup

## Problem: Pytest Configuration Error

If you encounter an error like:
```
ERROR: pytest: error: unrecognized arguments: --cov=src/mcp_ticketer ... --timeout=60
```

This means pytest is being run from the wrong Python environment.

## Solution: Use the Project Virtual Environment

### Quick Fix

The project has all required pytest plugins installed in `.venv`. Simply activate it:

```bash
# From project root
source .venv/bin/activate

# Verify pytest works
pytest --version

# Run tests
pytest
```

### Understanding the Issue

**Root Cause**: Multiple Python environments exist on the system:
- `/Users/masa/.local/bin/pytest` - Global user installation (missing plugins)
- `/Users/masa/Projects/mcp-ticketer/.venv/bin/pytest` - Project venv (✅ has all plugins)
- `/Users/masa/Projects/mcp-ticketer/venv/bin/pytest` - Another venv

**The Problem**: When you run `pytest` without activating the venv, your shell finds the global pytest installation first, which doesn't have the required plugins (`pytest-cov`, `pytest-timeout`).

### Installed Plugins in `.venv`

The `.venv` has all required plugins:
```
pytest                        8.4.2
pytest-asyncio                1.2.0
pytest-cov                    7.0.0       ✅ Required for coverage
pytest-mock                   3.15.1
pytest-timeout                2.4.0       ✅ Required for timeouts
pytest-xdist                  3.6.1       (for parallel testing)
```

## Development Workflow

### 1. Initial Setup (First Time)

```bash
# Clone repository
git clone https://github.com/mcp-ticketer/mcp-ticketer.git
cd mcp-ticketer

# The .venv already exists with dependencies installed
# Just activate it:
source .venv/bin/activate

# Verify setup
pytest --version
python --version
```

### 2. Daily Development

```bash
# Always activate venv first
cd /Users/masa/Projects/mcp-ticketer
source .venv/bin/activate

# Now all commands use the correct environment
pytest                    # Run tests
make test                # Run tests via Makefile
make test-parallel       # Parallel testing
make quality             # Code quality checks
```

### 3. Verification Commands

```bash
# After activating .venv, verify:
which python             # Should show: .venv/bin/python
which pytest             # Should show: .venv/bin/pytest
pip list | grep pytest   # Should show all pytest plugins

# Test pytest configuration
pytest --co -q tests/ | head -10
```

## Available Virtual Environments

The project has two venvs (you should use `.venv`):

| Directory | Status | Recommendation |
|-----------|--------|----------------|
| `.venv/` | ✅ Active, all deps installed | **Use this one** |
| `venv/` | ⚠️ Exists but outdated | Not recommended |

### Why `.venv`?

- Contains all development dependencies from `requirements-dev.txt`
- Matches the Python version (3.13.7)
- Up-to-date with latest package versions
- Tested and verified working

## Pytest Configuration

The `pytest.ini` file configures pytest with these options:

```ini
[pytest]
addopts =
    --cov=src/mcp_ticketer          # Requires: pytest-cov
    --cov-branch
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
    --timeout=60                     # Requires: pytest-timeout
    --timeout-method=thread
```

**These options require the pytest plugins to be installed!**

## Common Issues and Solutions

### Issue: "pytest: command not found"

**Solution**: Activate the venv first
```bash
source .venv/bin/activate
```

### Issue: "unrecognized arguments: --cov"

**Solution**: You're using the wrong pytest (global instead of venv)
```bash
# Activate venv
source .venv/bin/activate

# Verify correct pytest
which pytest  # Should show .venv/bin/pytest
```

### Issue: "ModuleNotFoundError: No module named 'mcp_ticketer'"

**Solution**: Install the package in development mode
```bash
source .venv/bin/activate
pip install -e .
```

### Issue: Multiple pytest installations conflict

**Solution**: Always use the venv pytest explicitly
```bash
# Option 1: Activate venv (recommended)
source .venv/bin/activate
pytest

# Option 2: Use venv python module directly
.venv/bin/python -m pytest

# Option 3: Use full path
.venv/bin/pytest
```

## IDE Configuration

### VS Code

Add to `.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestPath": "${workspaceFolder}/.venv/bin/pytest"
}
```

### PyCharm

1. File → Settings → Project → Python Interpreter
2. Click gear icon → Add
3. Select "Existing environment"
4. Choose `/Users/masa/Projects/mcp-ticketer/.venv/bin/python`

## Makefile Commands

The project Makefile automatically uses the correct environment:

```bash
# No need to activate venv manually for make commands
make test              # Runs tests
make test-parallel     # Parallel tests (3-4x faster)
make test-coverage     # Tests with HTML coverage
make quality           # All quality checks
make lint              # Linting
make format            # Code formatting
```

These commands handle venv activation internally.

## Environment Variables

The project uses a `.env` file for configuration. Example:

```bash
# Development settings
MCP_TICKETER_ADAPTER=aitrackdown
DEBUG=1

# Linear adapter (optional)
LINEAR_API_KEY=your_key_here
LINEAR_TEAM_ID=your_team_id

# JIRA adapter (optional)
JIRA_SERVER=https://company.atlassian.net
JIRA_EMAIL=your.email@company.com
JIRA_API_TOKEN=your_token
```

## Quick Reference

### Activate Virtual Environment
```bash
source .venv/bin/activate
```

### Deactivate Virtual Environment
```bash
deactivate
```

### Run Tests
```bash
# After activating venv
pytest                    # All tests
pytest tests/test_file.py # Specific file
pytest -k "test_name"     # Specific test
make test-parallel        # Parallel (fastest)
```

### Code Quality
```bash
make quality              # All checks
make lint                 # Linting only
make format               # Format code
make typecheck            # Type checking
```

### Package Management
```bash
# Install dependencies
pip install -e ".[dev,test]"

# Update dependencies
pip install --upgrade -r requirements-dev.txt

# Check installed packages
pip list
```

## Best Practices

1. **Always activate `.venv` before development**
   ```bash
   source .venv/bin/activate
   ```

2. **Verify correct environment**
   ```bash
   which python   # Should show .venv/bin/python
   which pytest   # Should show .venv/bin/pytest
   ```

3. **Use Make commands** (they handle venv automatically)
   ```bash
   make test-parallel
   make quality
   ```

4. **Keep dependencies updated**
   ```bash
   pip install --upgrade -r requirements-dev.txt
   ```

5. **Run quality checks before commits**
   ```bash
   make quality
   ```

## Troubleshooting

### Reset Virtual Environment (Nuclear Option)

If you have persistent issues:

```bash
# Backup current venv (optional)
mv .venv .venv.backup

# Create fresh venv
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install all dependencies
pip install --upgrade pip
pip install -e ".[dev,test,docs,all]"

# Verify
pytest --version
make test
```

## Summary

**The Golden Rule**: Always activate `.venv` before development work.

```bash
# Start of every development session:
cd /Users/masa/Projects/mcp-ticketer
source .venv/bin/activate

# Now you're ready to code!
pytest --version  # Verify
make test         # Run tests
```

This ensures you're using the correct Python environment with all required dependencies installed.
