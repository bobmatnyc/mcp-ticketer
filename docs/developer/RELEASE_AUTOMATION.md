# Release Automation Guide

Complete guide to automated releases for mcp-ticketer using the new single-command release workflow.

## Overview

The mcp-ticketer release automation provides a **single-command release** that handles:
- ✅ PyPI publishing
- ✅ GitHub releases with automated notes
- ✅ Homebrew tap updates
- ✅ Quality gates (linting, testing, type checking)
- ✅ Version bumping and git tagging
- ✅ Post-release verification

## Quick Start

### One-Command Full Release

```bash
# Patch release (bug fixes: X.Y.Z+1)
make release-full-patch

# Minor release (new features: X.Y+1.0)
make release-full-minor

# Major release (breaking changes: X+1.0.0)
make release-full-major
```

That's it! The automation handles everything from version bumping to Homebrew tap updates.

## What Gets Automated

### Full Release Workflow

When you run `make release-full-patch` (or minor/major), the system:

1. **Validates** git working directory is clean
2. **Runs quality gates**: format → lint → test → e2e tests
3. **Bumps version** in `__version__.py`
4. **Creates git commit** with version bump
5. **Creates git tag** (e.g., `v2.2.12`)
6. **Pushes** commit and tag to GitHub
7. **Builds** wheel and source distribution
8. **Publishes** to PyPI with Twine
9. **Creates GitHub release** with auto-generated notes
10. **Updates Homebrew tap** formula with SHA256
11. **Verifies** package is installable from PyPI

### Dry Run Mode

Preview what would happen without making changes:

```bash
./scripts/release_full.sh patch --dry-run
```

This shows the release plan and new version without executing any changes.

## Individual Release Components

You can also run individual steps if needed:

### GitHub Releases

```bash
# Create GitHub release for current version
make github-release

# Create GitHub release for specific version
make github-release-version VERSION=2.2.12
```

**Features:**
- Automatically extracts changelog section for the version
- Generates commit summary since last tag
- Attaches wheel and source dist files
- Creates nicely formatted release notes with installation instructions

### Homebrew Tap Updates

```bash
# Update Homebrew tap (commit only, no push)
make homebrew-tap-auto

# Update Homebrew tap and push automatically
make homebrew-tap-push

# Update specific version
make update-homebrew-tap VERSION=2.2.12
```

**Features:**
- Waits for PyPI to publish the version
- Fetches SHA256 checksum from PyPI
- Updates formula with new version and SHA256
- Runs formula validation checks
- Optionally pushes to Homebrew tap repository

### PyPI Publishing

```bash
# Publish to PyPI with full quality checks
make release-pypi

# Or use the standard targets
make publish-prod   # Production PyPI
make publish-test   # TestPyPI
```

### Version Management

```bash
# Show current version
make version

# Bump version manually
python scripts/manage_version.py bump patch
python scripts/manage_version.py bump minor
python scripts/manage_version.py bump major

# Check release readiness
make check-release
```

### Release Verification

```bash
# Verify package exists on PyPI
make verify-release

# Verify distribution packages
make verify-dist
```

## Script Reference

### `scripts/create_github_release.sh`

Creates GitHub releases with automated release notes.

**Usage:**
```bash
./scripts/create_github_release.sh [version]

# Examples
./scripts/create_github_release.sh              # Current version
./scripts/create_github_release.sh v2.2.12      # Specific version
```

**Features:**
- Detects version automatically or accepts as argument
- Extracts changelog section from CHANGELOG.md
- Generates commit summary since last tag
- Attaches distribution files (wheel + source)
- Uses GitHub CLI (`gh`) for creation

**Requirements:**
- GitHub CLI (`gh`) installed and authenticated
- Git tag must exist for the version
- Distribution files in `dist/` directory

### `scripts/update_homebrew_tap.sh`

Updates Homebrew tap formula with new version.

**Usage:**
```bash
./scripts/update_homebrew_tap.sh <version> [--push]

# Examples
./scripts/update_homebrew_tap.sh 2.2.12           # Commit only
./scripts/update_homebrew_tap.sh 2.2.12 --push    # Commit and push
```

**Features:**
- Validates version format (X.Y.Z)
- Waits for PyPI to publish version (with retries)
- Fetches SHA256 checksum from PyPI
- Updates formula URL, version, and SHA256
- Runs Homebrew formula audit checks
- Optionally pushes changes to GitHub

**Configuration:**
- Tap repo: `bobmatnyc/homebrew-tools`
- Formula: `mcp-ticketer`
- Clone location: `~/.homebrew-taps/homebrew-tools/`

### `scripts/release_full.sh`

Full release orchestration script.

**Usage:**
```bash
./scripts/release_full.sh [patch|minor|major] [--dry-run]

# Examples
./scripts/release_full.sh patch              # Full patch release
./scripts/release_full.sh minor              # Full minor release
./scripts/release_full.sh major              # Full major release
./scripts/release_full.sh patch --dry-run    # Preview changes
```

**Features:**
- Interactive confirmation before proceeding
- Colored progress output with step tracking
- Validates git working directory is clean
- Runs all quality gates (format, lint, test, e2e)
- Handles version bumping, tagging, and pushing
- Coordinates PyPI, GitHub, and Homebrew updates
- Provides detailed final summary with URLs

**Steps executed:**
1. Check git is clean
2. Run quality gates (make pre-publish)
3. Bump version
4. Commit and tag version
5. Push to origin
6. Build package
7. Publish to PyPI
8. Create GitHub release
9. Update Homebrew tap
10. Verify release

## Makefile Targets

### Full Release Automation

| Target | Description |
|--------|-------------|
| `release-full-patch` | Complete patch release (PyPI + GitHub + Homebrew) |
| `release-full-minor` | Complete minor release (PyPI + GitHub + Homebrew) |
| `release-full-major` | Complete major release (PyPI + GitHub + Homebrew) |

### GitHub Release Management

| Target | Description |
|--------|-------------|
| `github-release` | Create GitHub release for current version |
| `github-release-version VERSION=X.Y.Z` | Create GitHub release for specific version |

### Homebrew Tap Management

| Target | Description |
|--------|-------------|
| `homebrew-tap-auto` | Update Homebrew tap (commit only, no push) |
| `homebrew-tap-push` | Update Homebrew tap and push automatically |
| `update-homebrew-tap VERSION=X.Y.Z` | Update specific version |

### Release Verification

| Target | Description |
|--------|-------------|
| `verify-release` | Verify package is installable from PyPI |
| `verify-dist` | Verify distribution packages with Twine |

### Publishing

| Target | Description |
|--------|-------------|
| `release-pypi` | Publish to PyPI (alias for publish-prod) |
| `publish-prod` | Publish to production PyPI |
| `publish-test` | Publish to TestPyPI |

## Prerequisites

### Required Tools

1. **Python 3.10+** (for project development)
   ```bash
   python --version  # Should be 3.10 or higher
   ```

2. **GitHub CLI** (for GitHub releases)
   ```bash
   brew install gh
   gh auth login
   ```

3. **Homebrew** (for formula validation)
   ```bash
   # Already installed on macOS
   brew --version
   ```

4. **Build Tools** (installed via dev dependencies)
   ```bash
   pip install -e ".[dev]"
   ```

### Required Access

1. **PyPI Account**
   - API token for mcp-ticketer project
   - Stored in `.env.local` or `~/.pypirc`

2. **GitHub Access**
   - Write access to mcp-ticketer repository
   - Authenticated with `gh` CLI

3. **Homebrew Tap Access**
   - Write access to `bobmatnyc/homebrew-tools` repository
   - Git configured with SSH keys

### Configuration Files

#### `.env.local` (PyPI credentials)

```bash
# .env.local (git-ignored)
TWINE_USERNAME=__token__
TWINE_PASSWORD=pypi-AgEIcHlwaS5vcmcC...  # Your PyPI API token
```

#### `~/.pypirc` (Alternative PyPI config)

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmcC...

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgEIcHlwaS5vcmcC...
```

## Release Workflow Comparison

### Before (Manual Process)

```bash
# 1. Update CHANGELOG.md manually
# 2. Bump version manually
python scripts/manage_version.py bump patch
# 3. Commit and tag manually
git add src/mcp_ticketer/__version__.py
git commit -m "chore: bump version to X.Y.Z"
git tag -a vX.Y.Z -m "Release vX.Y.Z"
# 4. Run quality checks
make format lint test test-e2e
# 5. Build package
make build
# 6. Publish to PyPI
make publish-prod
# 7. Push git changes
git push origin main
git push origin vX.Y.Z
# 8. Create GitHub release manually in web UI
# 9. Update Homebrew tap manually
./scripts/update_homebrew_tap.sh X.Y.Z
cd ~/.homebrew-taps/homebrew-tools
git push origin main
# 10. Verify installation
pip install --upgrade mcp-ticketer
```

**Time:** 15-20 minutes
**Steps:** 10+ manual commands
**Error-prone:** High (easy to skip steps)

### After (Automated Process)

```bash
# 1. Update CHANGELOG.md (still manual)
# 2. Run single command
make release-full-patch
```

**Time:** 5-10 minutes (mostly automated waiting)
**Steps:** 1 command
**Error-prone:** Low (automated validation)

## Troubleshooting

### GitHub CLI Not Authenticated

**Error:**
```
Not authenticated with GitHub CLI
```

**Solution:**
```bash
gh auth login
# Follow the prompts to authenticate
```

### PyPI Authentication Failed

**Error:**
```
Upload failed (403): Invalid or non-existent authentication information
```

**Solution:**
1. Check `.env.local` exists and has correct format
2. Verify PyPI API token is valid
3. Regenerate token if needed at [pypi.org](https://pypi.org/manage/account/)

### Homebrew Tap Update Failed

**Error:**
```
Version X.Y.Z not found on PyPI after 10 attempts
```

**Solution:**
1. Verify package was published to PyPI
2. Wait a few minutes for PyPI to propagate
3. Manually retry: `make homebrew-tap-push`

### Git Working Directory Not Clean

**Error:**
```
Git working directory has uncommitted changes
```

**Solution:**
```bash
# Commit or stash changes
git status
git add .
git commit -m "chore: prepare for release"

# Or stash for later
git stash
```

### Version Already Exists on PyPI

**Error:**
```
Upload failed (400): File already exists
```

**Solution:**
- PyPI doesn't allow re-uploading same version
- Bump to next version: `make release-full-patch`

## Best Practices

### Pre-Release Checklist

Before running `make release-full-*`:

- [ ] Update CHANGELOG.md with all changes
- [ ] Commit all changes (working directory clean)
- [ ] All tests passing locally (`make test`)
- [ ] Documentation updated (if needed)
- [ ] No debug code or TODOs in release

### Release Schedule

- **Patch releases**: Weekly or as-needed for bug fixes
- **Minor releases**: Monthly for new features
- **Major releases**: Quarterly or for breaking changes

### Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes, incompatible API
- **MINOR** (0.X.0): New features, backward-compatible
- **PATCH** (0.0.X): Bug fixes, backward-compatible

### Testing Before Release

```bash
# Run full test suite
make test test-e2e

# Test in clean environment
python -m venv test-venv
source test-venv/bin/activate
pip install .
mcp-ticketer --version
```

### Post-Release Verification

```bash
# Verify PyPI
pip install --upgrade mcp-ticketer
mcp-ticketer --version

# Verify GitHub release
open https://github.com/mcp-ticketer/mcp-ticketer/releases

# Verify Homebrew
brew upgrade mcp-ticketer
mcp-ticketer --version
```

## Examples

### Example 1: Bug Fix Release

```bash
# 1. Fix bug in code
# 2. Update CHANGELOG.md
cat >> CHANGELOG.md <<EOF
## [2.2.12] - 2025-12-09

### Fixed
- Fixed error handling in Linear adapter
- Resolved ticket creation validation issue
EOF

# 3. Commit changes
git add .
git commit -m "fix: improve error handling in Linear adapter"

# 4. Release
make release-full-patch

# Done! Package is on PyPI, GitHub, and Homebrew
```

### Example 2: Feature Release

```bash
# 1. Implement feature
# 2. Update CHANGELOG.md
cat >> CHANGELOG.md <<EOF
## [2.3.0] - 2025-12-09

### Added
- Added support for GitHub Projects v2
- New migration tool for importing tickets

### Changed
- Improved token optimization (85% reduction)
EOF

# 3. Commit changes
git add .
git commit -m "feat: add GitHub Projects v2 support"

# 4. Release
make release-full-minor

# Done! New feature is live
```

### Example 3: Preview Changes (Dry Run)

```bash
# Preview what would happen
./scripts/release_full.sh patch --dry-run

# Output shows:
# - Current version: 2.2.11
# - New version will be: 2.2.12
# - Release plan (10 steps)
# No changes made
```

## Architecture

### Script Dependencies

```
release_full.sh (orchestrator)
├── manage_version.py (version bumping)
├── make pre-publish (quality gates)
├── make build (package building)
├── make release-pypi (PyPI publishing)
├── create_github_release.sh
│   ├── gh CLI (GitHub API)
│   └── CHANGELOG.md (release notes)
└── update_homebrew_tap.sh
    ├── PyPI API (SHA256 fetch)
    └── git (Homebrew tap updates)
```

### File Locations

```
mcp-ticketer/
├── scripts/
│   ├── create_github_release.sh     # NEW: GitHub release automation
│   ├── update_homebrew_tap.sh       # UPDATED: Added --push flag
│   ├── release_full.sh              # NEW: Full release orchestration
│   └── manage_version.py            # Existing: Version management
├── .makefiles/
│   └── release.mk                   # UPDATED: New targets
├── Makefile                         # Entry point
└── docs/developer/
    ├── RELEASE.md                   # Manual release guide
    └── RELEASE_AUTOMATION.md        # This document
```

## Migration from Old Process

If you've been using the old manual process:

### Old Commands → New Commands

| Old Command | New Command |
|-------------|-------------|
| `make release-patch` | `make release-full-patch` |
| `make release-minor` | `make release-full-minor` |
| `make release-major` | `make release-full-major` |
| Manual GitHub release | Automated by `release-full-*` |
| Manual Homebrew update | Automated by `release-full-*` |

### What Changed

- **Old `make release-patch`**: PyPI only
- **New `make release-full-patch`**: PyPI + GitHub + Homebrew
- **Old**: Manual GitHub release creation
- **New**: Automated with `create_github_release.sh`
- **Old**: Manual Homebrew push
- **New**: Automated with `--push` flag

### Backward Compatibility

Old commands still work for PyPI-only releases:
- `make release-patch` → PyPI only
- `make release-minor` → PyPI only
- `make release-major` → PyPI only

## Summary

The new release automation provides:

✅ **Single-command releases** via `make release-full-*`
✅ **Automated GitHub releases** with generated notes
✅ **Automated Homebrew updates** with auto-push
✅ **Quality gates** ensuring code quality
✅ **Verification steps** confirming success
✅ **Dry-run mode** for previewing changes
✅ **Comprehensive logging** for debugging

**Result**: Releases take 5-10 minutes instead of 15-20, with fewer errors and better consistency.

## Related Documentation

- [RELEASE.md](RELEASE.md) - Detailed manual release guide
- [CHANGELOG.md](../../CHANGELOG.md) - Version history
- [Makefile](../../Makefile) - All available commands
- [GitHub CLI Manual](https://cli.github.com/manual/) - `gh` documentation

---

**Last Updated:** 2025-12-09
**Version:** 1.0.0
**Status:** Production Ready
