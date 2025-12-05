# Release Process Documentation

Complete guide for releasing new versions of mcp-ticketer to PyPI.

## Table of Contents

- [Quick Reference](#quick-reference)
- [Prerequisites](#prerequisites)
- [Version Management](#version-management)
- [Release Workflow](#release-workflow)
- [Step-by-Step Guides](#step-by-step-guides)
- [Quality Gates](#quality-gates)
- [Post-Release Tasks](#post-release-tasks)
- [Troubleshooting](#troubleshooting)

---

## Quick Reference

### Release Commands

```bash
# Patch release (bug fixes: 0.0.X)
make release-patch

# Minor release (new features: 0.X.0)
make release-minor

# Major release (breaking changes: X.0.0)
make release-major

# Test publish (TestPyPI)
make publish-test

# Production publish (PyPI)
make publish-prod
```

### Semantic Versioning

- **MAJOR** (X.0.0): Breaking changes, incompatible API changes
- **MINOR** (0.X.0): New features, backward-compatible functionality
- **PATCH** (0.0.X): Bug fixes, backward-compatible fixes

---

## Prerequisites

### Required Tools

1. **Python 3.9+**
   ```bash
   python --version  # Should be 3.9 or higher
   ```

2. **Build Tools**

   Build and publishing tools are included in dev dependencies:

   ```bash
   # Install all dev dependencies (includes build, twine, pytest, ruff, etc.)
   pip install -e ".[dev]"
   ```

   Or install individually if needed:
   ```bash
   pip install build twine
   ```

   **Note**: As of v2.0.4, `build` and `twine` are declared in `pyproject.toml`
   dev dependencies for consistency across the team.

3. **Development Environment**
   ```bash
   make install-dev  # Installs all dev dependencies
   ```

### Required Access

1. **PyPI Account**
   - Create account at [pypi.org](https://pypi.org)
   - Enable 2FA for security
   - Generate API token for mcp-ticketer project

2. **GitHub Access**
   - Write access to repository
   - Ability to create tags and releases

### PyPI Credentials Setup

#### Option 1: Environment Variables

Create `.env.local` in project root:

```bash
# .env.local (git-ignored)
TWINE_USERNAME=__token__
TWINE_PASSWORD=pypi-AgEIcHlwaS5vcmcC...  # Your PyPI API token
```

#### Option 2: PyPI Configuration File

Create `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmcC...  # Your PyPI API token

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgEIcHlwaS5vcmcC...  # Your TestPyPI API token
```

**Security Note**: Never commit `.env.local` or `~/.pypirc` to version control!

---

## Version Management

### Using `manage_version.py` Script

The `scripts/manage_version.py` script handles all version management tasks.

#### Get Current Version

```bash
python scripts/manage_version.py get-version
# Output: 0.15.0
```

Or use make target:

```bash
make version
# Output: 0.15.0
```

#### Manual Version Bump

```bash
# Bump patch version (0.15.0 → 0.15.1)
python scripts/manage_version.py bump patch

# Bump minor version (0.15.0 → 0.16.0)
python scripts/manage_version.py bump minor

# Bump major version (0.15.0 → 1.0.0)
python scripts/manage_version.py bump major
```

#### Version Bump with Git Integration

```bash
# Bump version + create git commit
python scripts/manage_version.py bump patch --git-commit

# Bump version + create git commit + create git tag
python scripts/manage_version.py bump minor --git-commit --git-tag
```

**Note**: The `make release-*` commands automatically handle git commits and tags.

#### Check Release Readiness

```bash
python scripts/manage_version.py check-release
# OR
make check-release
```

This validates:
- Git working directory is clean
- Version follows semantic versioning
- On a valid git branch

#### Track Build Metadata

```bash
python scripts/manage_version.py track-build --notes "Release notes here"
```

Automatically called during `make build` to track:
- Version number
- Build number (auto-incremented)
- Git commit SHA
- Git branch
- Build timestamp
- Release notes

#### Verifying the Package

Before publishing, verify the distribution packages are valid:

```bash
# Verify package metadata and structure
make verify-dist

# Or manually
twine check dist/*
```

This checks for:
- Valid package metadata
- Proper long_description rendering
- Required fields present
- No malformed distributions

**Always run this before uploading to PyPI!**

---

## Release Workflow

### Overview

The release process follows this workflow:

```
1. Prepare Release
   ├─ Update CHANGELOG.md
   ├─ Update documentation
   └─ Commit changes

2. Version Bump (automatic)
   ├─ Update __version__.py
   ├─ Create git commit
   └─ Create git tag

3. Quality Checks (automatic)
   ├─ Format code (black, isort)
   ├─ Run linters (ruff, mypy)
   ├─ Run tests (pytest)
   └─ Run e2e tests

4. Build (automatic)
   ├─ Clean old builds
   ├─ Build wheel and sdist
   └─ Track build metadata

5. Publish (automatic)
   ├─ Upload to PyPI
   └─ Verify package

6. Post-Release Tasks (manual)
   ├─ Create GitHub release
   ├─ Push git tags
   └─ Announce release
```

### What Each Release Type Does

#### `make release-patch`

1. Bumps patch version (X.Y.Z+1)
2. Creates git commit: `chore: bump version to X.Y.Z+1`
3. Creates git tag: `vX.Y.Z+1`
4. Runs quality checks (format, lint, test, e2e)
5. Builds distribution packages
6. Publishes to PyPI
7. Displays new version

**Use for**: Bug fixes, minor improvements, documentation updates

#### `make release-minor`

1. Bumps minor version (X.Y+1.0)
2. Creates git commit: `chore: bump version to X.Y+1.0`
3. Creates git tag: `vX.Y+1.0`
4. Runs quality checks (format, lint, test, e2e)
5. Builds distribution packages
6. Publishes to PyPI
7. Displays new version

**Use for**: New features, backward-compatible enhancements

#### `make release-major`

1. Bumps major version (X+1.0.0)
2. Creates git commit: `chore: bump version to X+1.0.0`
3. Creates git tag: `vX+1.0.0`
4. Runs quality checks (format, lint, test, e2e)
5. Builds distribution packages
6. Publishes to PyPI
7. Displays new version

**Use for**: Breaking changes, major API changes

---

## Step-by-Step Guides

### Patch Release (Bug Fix)

**Example**: Releasing v0.15.1 with bug fixes

1. **Ensure clean working directory**
   ```bash
   git status
   # Should show no uncommitted changes
   ```

2. **Update CHANGELOG.md**
   ```markdown
   ## [0.15.1] - 2025-11-21

   ### Fixed
   - Fixed bug in ticket creation validation
   - Resolved error handling in Linear adapter
   ```

3. **Commit changelog**
   ```bash
   git add CHANGELOG.md
   git commit -m "docs: update changelog for v0.15.1"
   ```

4. **Run release command**
   ```bash
   make release-patch
   ```

5. **Expected output**:
   ```
   Bumping patch version...
   Version bumped: 0.15.0 → 0.15.1
   Updated src/mcp_ticketer/__version__.py
   ✅ Git commit created: chore: bump version to 0.15.1
   ✅ Git tag created: v0.15.1
   Running linters...
   Running tests...
   Cleaning build artifacts...
   Building distribution...
   Build tracked: #123 for v0.15.1
   Publishing to PyPI...
   ✅ Patch release complete!
   0.15.1
   ```

6. **Verify package**
   ```bash
   # Check PyPI
   open https://pypi.org/project/mcp-ticketer/

   # Test installation
   pip install --upgrade mcp-ticketer
   mcp-ticketer --version
   ```

### Minor Release (New Features)

**Example**: Releasing v0.16.0 with compact mode feature

1. **Ensure clean working directory**
   ```bash
   git status
   ```

2. **Update CHANGELOG.md**
   ```markdown
   ## [0.16.0] - 2025-11-21

   ### Added
   - Token optimization: compact mode for ticket_list (78% reduction)
   - New compact parameter for MCP tools
   - Comprehensive test coverage (17 new tests)

   ### Changed
   - Enhanced ticket_list function with conditional filtering
   - Updated documentation with usage examples
   ```

3. **Update documentation** (if needed)
   ```bash
   # Update README.md, docs/, etc.
   ```

4. **Commit all changes**
   ```bash
   git add CHANGELOG.md README.md docs/
   git commit -m "docs: update documentation for v0.16.0"
   ```

5. **Run release command**
   ```bash
   make release-minor
   ```

6. **Expected output**:
   ```
   Bumping minor version...
   Version bumped: 0.15.1 → 0.16.0
   Updated src/mcp_ticketer/__version__.py
   ✅ Git commit created: chore: bump version to 0.16.0
   ✅ Git tag created: v0.16.0
   Formatting code...
   Running linters...
   Running tests...
   Running e2e tests...
   Cleaning build artifacts...
   Building distribution...
   Publishing to PyPI...
   ✅ Minor release complete!
   0.16.0
   ```

7. **Push tags to GitHub**
   ```bash
   git push origin main
   git push origin v0.16.0
   ```

### Major Release (Breaking Changes)

**Example**: Releasing v1.0.0 with API redesign

1. **Ensure clean working directory**
   ```bash
   git status
   ```

2. **Update CHANGELOG.md**
   ```markdown
   ## [1.0.0] - 2025-11-21

   ### Breaking Changes
   - Redesigned MCP tool interface (incompatible with v0.x)
   - Removed deprecated ticket_type field
   - Changed adapter initialization API

   ### Added
   - New unified adapter interface
   - Enhanced error handling
   - Comprehensive migration guide

   ### Migration Guide
   See [MIGRATION.md](MIGRATION.md) for upgrade instructions.
   ```

3. **Create migration guide** (if needed)
   ```bash
   # Create docs/MIGRATION.md with upgrade instructions
   ```

4. **Update all documentation**
   ```bash
   # Update README.md, API docs, examples
   ```

5. **Commit all changes**
   ```bash
   git add .
   git commit -m "docs: update documentation for v1.0.0"
   ```

6. **Run release command**
   ```bash
   make release-major
   ```

7. **Expected output**:
   ```
   Bumping major version...
   Version bumped: 0.16.0 → 1.0.0
   Updated src/mcp_ticketer/__version__.py
   ✅ Git commit created: chore: bump version to 1.0.0
   ✅ Git tag created: v1.0.0
   Running quality checks...
   Publishing to PyPI...
   ✅ Major release complete!
   1.0.0
   ```

8. **Push tags and create GitHub release**
   ```bash
   git push origin main
   git push origin v1.0.0
   ```

### Test Release (TestPyPI)

Before publishing to production PyPI, test on TestPyPI:

1. **Update TestPyPI credentials** (if using .env.local)
   ```bash
   # Add TestPyPI token to .env.local
   TWINE_USERNAME=__token__
   TWINE_PASSWORD=pypi-AgEIcHlwaS5vcmcC...  # TestPyPI token
   ```

2. **Run test publish**
   ```bash
   make publish-test
   ```

3. **Verify on TestPyPI**
   ```bash
   open https://test.pypi.org/project/mcp-ticketer/
   ```

4. **Test installation from TestPyPI**
   ```bash
   pip install --index-url https://test.pypi.org/simple/ mcp-ticketer
   ```

5. **If successful, publish to production**
   ```bash
   make publish-prod
   ```

---

## Quality Gates

All releases must pass these quality gates:

### Pre-Release Checklist

- [ ] All tests passing (`make test`)
- [ ] E2E tests passing (`make test-e2e`)
- [ ] Linting passing (`make lint`)
- [ ] Type checking passing (`make typecheck`)
- [ ] Code formatted (`make format`)
- [ ] CHANGELOG.md updated
- [ ] Documentation updated
- [ ] Git working directory clean
- [ ] On correct git branch (usually `main`)

### Automated Checks (make release-*)

These checks run automatically during release:

1. **check-release**: Validates release readiness
   - Git working directory clean
   - Valid semantic version
   - On valid git branch

2. **format**: Formats code
   - Black (code formatting)
   - isort (import sorting)

3. **lint**: Runs linters
   - Ruff (Python linting)
   - mypy (type checking)

4. **test**: Runs all tests
   - Unit tests
   - Integration tests
   - Test coverage

5. **test-e2e**: Runs end-to-end tests
   - Full workflow tests
   - Real adapter integration

6. **build**: Builds packages
   - Cleans old builds
   - Creates wheel and sdist
   - Tracks build metadata

### Manual Quality Checks

Before releasing, manually verify:

1. **Version number is correct**
   ```bash
   make version
   ```

2. **CHANGELOG.md is accurate**
   - All changes documented
   - Correct version number
   - Correct date

3. **Documentation is up-to-date**
   - README.md reflects new features
   - API docs updated
   - Examples work

4. **No debug code or TODOs**
   ```bash
   grep -r "TODO\|FIXME\|DEBUG" src/
   ```

---

## Post-Release Tasks

After a successful release:

### 1. Push Git Tags

```bash
# Push main branch
git push origin main

# Push version tag
git push origin v0.15.0
```

### 2. Create GitHub Release

1. Go to [GitHub Releases](https://github.com/yourusername/mcp-ticketer/releases)
2. Click "Draft a new release"
3. Select the version tag (e.g., `v0.15.0`)
4. Title: `v0.15.0 - Token Optimization & Auto-Install`
5. Description: Copy from CHANGELOG.md

**GitHub Release Template**:

```markdown
## What's New

[Brief summary of major features]

## Added
- Feature 1 description
- Feature 2 description

## Changed
- Change 1 description

## Fixed
- Fix 1 description

## Installation

```bash
pip install --upgrade mcp-ticketer
```

## Full Changelog
See [CHANGELOG.md](CHANGELOG.md) for complete details.
```

3. Click "Publish release"

### 3. Verify PyPI Package

```bash
# Check PyPI page
open https://pypi.org/project/mcp-ticketer/

# Test installation
pip install --upgrade mcp-ticketer
mcp-ticketer --version

# Should show new version
```

### 4. Verify Package Metadata

Check that PyPI shows:
- Correct version number
- Updated description
- All classifiers
- Correct dependencies
- README rendering correctly

### 5. Announce Release

Optional announcements:

- **Twitter/X**: Announce new features
- **Discord/Slack**: Notify community
- **Blog Post**: For major releases
- **Documentation Site**: Update version number

**Announcement Template**:

```
🎉 mcp-ticketer v0.15.0 released!

✨ New features:
- Token optimization (78% reduction)
- Automatic dependency installation

📦 Install: pip install --upgrade mcp-ticketer
📖 Changelog: https://github.com/yourusername/mcp-ticketer/releases/tag/v0.15.0
```

### 6. Update Documentation Sites

If you have external documentation:

- Update version number in docs
- Rebuild and deploy documentation
- Update any external links

---

## Troubleshooting

### Common Issues and Solutions

#### Issue: Git Working Directory Not Clean

**Error**:
```
❌ Release validation failed:
  - Git working directory has uncommitted changes
```

**Solution**:
```bash
# Check what's uncommitted
git status

# Commit or stash changes
git add .
git commit -m "chore: prepare for release"

# Or stash for later
git stash
```

---

#### Issue: PyPI Authentication Failed

**Error**:
```
Upload failed (403): Invalid or non-existent authentication information
```

**Solution 1**: Check `.env.local` credentials
```bash
# Verify .env.local exists and has correct format
cat .env.local

# Should contain:
# TWINE_USERNAME=__token__
# TWINE_PASSWORD=pypi-AgEIcHlwaS5vcmcC...
```

**Solution 2**: Use `~/.pypirc`
```bash
# Create or update ~/.pypirc
cat ~/.pypirc

# Should contain [pypi] section with token
```

**Solution 3**: Regenerate PyPI token
1. Go to [PyPI Account Settings](https://pypi.org/manage/account/)
2. Generate new API token for mcp-ticketer
3. Update `.env.local` or `~/.pypirc`

---

#### Issue: Tests Failing

**Error**:
```
FAILED tests/unit/test_feature.py::test_something
```

**Solution**:
```bash
# Run tests to identify failures
make test

# Fix failing tests
# Re-run tests
pytest tests/unit/test_feature.py -v

# Once fixed, retry release
make release-patch
```

---

#### Issue: Build Failed

**Error**:
```
ERROR: Could not build wheels for mcp-ticketer
```

**Solution 1**: Clean and rebuild
```bash
make clean
make build
```

**Solution 2**: Check build dependencies
```bash
pip install --upgrade build wheel setuptools
```

**Solution 3**: Check pyproject.toml syntax
```bash
# Validate pyproject.toml
python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))"
```

---

#### Issue: Version Already Exists on PyPI

**Error**:
```
Upload failed (400): File already exists
```

**Solution**:
```bash
# PyPI doesn't allow re-uploading same version
# Bump to next version
python scripts/manage_version.py bump patch
make build
make publish-prod
```

**Note**: You cannot delete or replace versions on PyPI. Always increment version.

---

#### Issue: E2E Tests Failing

**Error**:
```
FAILED tests/e2e/test_workflow.py::test_full_workflow
```

**Solution**:
```bash
# Run e2e tests with verbose output
pytest tests/e2e/ -v -s

# Check adapter credentials
# E2E tests may require real adapter setup

# Skip e2e tests if necessary (not recommended)
make format lint test build publish-prod
```

---

#### Issue: Linting Errors

**Error**:
```
ruff check failed with errors
```

**Solution**:
```bash
# Auto-fix linting issues
make lint-fix

# Format code
make format

# Re-run linting
make lint
```

---

#### Issue: Type Checking Errors

**Error**:
```
mypy found type errors
```

**Solution**:
```bash
# Run mypy with verbose output
mypy src --show-error-context

# Fix type annotations
# Add type: ignore comments if necessary

# Re-run type checking
make typecheck
```

---

#### Issue: Build Metadata Tracking Failed

**Error**:
```
Error tracking build metadata
```

**Solution**:
```bash
# Check git is configured
git config user.name
git config user.email

# Verify .build_metadata.json permissions
ls -la .build_metadata.json

# Manually track build
python scripts/manage_version.py track-build
```

---

### Rollback Procedures

#### Rollback Git Commit and Tag

If release failed after version bump:

```bash
# Remove git tag
git tag -d v0.15.1

# Reset to previous commit
git reset --hard HEAD~1

# If already pushed
git push origin :refs/tags/v0.15.1  # Delete remote tag
git push origin main --force         # Force push (use carefully!)
```

**Warning**: Only force push if you're sure no one has pulled the changes!

#### Rollback PyPI Release

PyPI doesn't support deleting or replacing versions. Options:

1. **Yank the release** (marks as unavailable but keeps it):
   ```bash
   # Go to PyPI project page → Manage → Options → Yank
   # Or use twine:
   twine upload --skip-existing dist/*
   ```

2. **Release a patch version** (recommended):
   ```bash
   # Fix the issue
   make release-patch
   ```

3. **Contact PyPI support** (for serious issues like security):
   - File support ticket at [pypi.org/help](https://pypi.org/help/)

---

### Getting Help

If you encounter issues not covered here:

1. **Check build logs**:
   ```bash
   # Review full output of make commands
   make release-patch 2>&1 | tee release.log
   ```

2. **Check GitHub Issues**:
   - Search existing issues
   - Create new issue with:
     - Error message
     - Steps to reproduce
     - Environment details

3. **Verify environment**:
   ```bash
   make check-env
   python --version
   pip --version
   ```

4. **Test in clean environment**:
   ```bash
   # Create new virtual environment
   python -m venv test-venv
   source test-venv/bin/activate
   pip install -e ".[dev,test]"
   make test
   ```

---

## Additional Resources

### Helpful Commands

```bash
# Check current version
make version

# Validate release readiness
make check-release

# Run full quality checks
make quality

# Simulate CI pipeline
make ci

# Clean everything
make clean

# View all make targets
make help
```

### Related Documentation

- [CHANGELOG.md](../CHANGELOG.md) - Version history
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- [README.md](../README.md) - Project overview
- [Makefile](../Makefile) - All available commands

### External Links

- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [PyPI Publishing Guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
- [Python Packaging Guide](https://packaging.python.org/)

---

## Submodule Releases

mcp-ticketer includes submodules that may need independent releases:

### py-mcp-installer-service

Located at `src/services/py_mcp_installer/`, this submodule has its own versioning.

#### Automatic Submodule Release

Use the full-release commands to automatically:
1. Check submodule for changes
2. Release submodule if needed
3. Update parent's submodule pointer
4. Continue with parent release

```bash
# Patch release with submodule check
make release-patch-full

# Minor release with submodule check
make release-minor-full

# Major release with submodule check
make release-major-full
```

#### Manual Submodule Release

Enter submodule and release independently:

```bash
cd src/services/py_mcp_installer
make release-patch  # or release-minor, release-major
cd ../../..
git add src/services/py_mcp_installer
git commit -m "chore: update py-mcp-installer-service"
```

#### Version Compatibility

| mcp-ticketer | py-mcp-installer |
|--------------|------------------|
| 2.1.x        | 0.0.3+           |
| 2.2.x        | 0.1.x+           |

#### Submodule Release Notes

- Submodule releases create GitHub releases only (no PyPI)
- Submodule changes are detected automatically by `release-*-full` commands
- Parent's submodule pointer is updated automatically
- See submodule's `RELEASING.md` for more details

---

## Summary

This release process ensures:

- Consistent version management
- Automated quality checks
- Reliable package publishing
- Clear documentation
- Easy rollback if needed

For most releases, you'll simply run:

```bash
# Update CHANGELOG.md
# Commit changes
make release-patch-full  # or release-minor-full, release-major-full
# Push tags
# Create GitHub release
```

The automation handles the rest!
