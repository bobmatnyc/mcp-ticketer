# Versioning and Build Tracking

**Status**: ✅ IMPLEMENTED
**Last Updated**: 2025-10-24
**Version**: 0.3.2

## Overview

MCP Ticketer has a comprehensive version management and build tracking system already implemented via `scripts/manage_version.py`.

## Current Implementation

### Version Management

**Location**: `scripts/manage_version.py`

**Features**:
- ✅ Semantic versioning (MAJOR.MINOR.PATCH)
- ✅ Automatic version bumping (major, minor, patch)
- ✅ Git commit creation for version bumps
- ✅ Git tag creation for releases
- ✅ Release readiness validation
- ✅ Version file synchronization (`__version__.py` and `pyproject.toml`)

**Usage**:
```bash
# Get current version
python3 scripts/manage_version.py get-version

# Bump version (with optional git commit and tag)
python3 scripts/manage_version.py bump patch
python3 scripts/manage_version.py bump patch --git-commit --git-tag
python3 scripts/manage_version.py bump minor --git-commit --git-tag
python3 scripts/manage_version.py bump major --git-commit --git-tag

# Validate release readiness
python3 scripts/manage_version.py check-release
```

### Build Tracking

**Location**: `.build_metadata.json`

**Tracked Metadata**:
- ✅ Version number
- ✅ Build number (auto-incrementing)
- ✅ Git commit SHA
- ✅ Git branch name
- ✅ Build timestamp (ISO 8601 with timezone)
- ✅ Release notes
- ✅ Previous version

**Current Build Metadata**:
```json
{
  "version": "0.3.2",
  "build_number": 111,
  "git_commit": "bd063ed",
  "git_branch": "main",
  "build_timestamp": "2025-10-25T03:32:31.858613+00:00",
  "release_notes": "",
  "previous_version": "0.3.2"
}
```

**Usage**:
```bash
# Track build (automatically increments build number)
python3 scripts/manage_version.py track-build

# Track build with release notes
python3 scripts/manage_version.py track-build --notes "Fixed Linear auth issue"
```

### Makefile Integration

**Version Management Targets**:
```makefile
# Show current version
make version

# Bump version and create git commit + tag
make version-bump-patch   # 0.3.2 → 0.3.3
make version-bump-minor   # 0.3.2 → 0.4.0
make version-bump-major   # 0.3.2 → 1.0.0

# Validate release readiness
make check-release
```

**Full Release Workflow Targets**:
```makefile
# Complete release workflow (bump + build + publish)
make release-patch   # Patch version release
make release-minor   # Minor version release
make release-major   # Major version release
```

**Build Target** (automatically tracks build):
```makefile
make build
# → Runs: python3 -m build
# → Then: python3 scripts/manage_version.py track-build
```

## Release Workflow

### Standard Release Process

**Current (v0.3.2 release)**:
```bash
# 1. Make changes and commit
git add .
git commit -m "fix: correct Linear API authentication"

# 2. Bump version (creates git commit and tag)
make version-bump-patch

# 3. Publish to PyPI
make publish
# → Runs: check-release format lint test test-e2e build upload
```

### Automated Release Workflow

**Makefile provides fully automated workflows**:
```bash
# Patch release (0.3.2 → 0.3.3)
make release-patch

# Minor release (0.3.2 → 0.4.0)
make release-minor

# Major release (0.3.2 → 1.0.0)
make release-major
```

**These commands execute**:
1. `version-bump-{patch|minor|major}` - Bump version, commit, tag
2. `build` - Build distribution packages + track build metadata
3. `publish-prod` - Upload to PyPI

## Release Validation

### Pre-Release Checks (`check-release`)

**Validation Steps**:
1. ✅ Git working directory is clean (no uncommitted changes)
2. ✅ Version is valid semver format
3. ✅ On a git branch (not detached HEAD)

**Example**:
```bash
$ make check-release
Validating release readiness...
✅ Release validation passed
```

**Failure Example**:
```bash
$ make check-release
Validating release readiness...
❌ Release validation failed:
  - Git working directory has uncommitted changes
  - Not on a git branch
```

## Test Integration

### Test Requirements Before Publishing

**Current Makefile Flow** (updated 2025-10-24):
```makefile
publish-prod: check-release format lint test test-e2e build
publish-test: check-release format lint test test-e2e build
```

**Execution Order**:
1. `check-release` - Validate git state and version
2. `format` - Format code (black + isort)
3. `lint` - Run linters (ruff + mypy)
4. `test` - Run all unit tests
5. `test-e2e` - **NEW**: Run E2E tests
6. `build` - Build distribution packages
7. Upload to PyPI (prod or test)

**Impact**: Publishing now requires ALL tests (including E2E) to pass.

## Changelog Automation

### Current Status

**Not Yet Implemented** ⚠️

**Recommendation**: Add changelog generation to release workflow.

**Proposed Implementation**:
```bash
# Use standard-version or similar tool
npm install -g standard-version

# Add to Makefile
changelog:
    standard-version --skip.bump --skip.tag

release-patch: version-bump-patch changelog build publish-prod
```

**Alternative**: Manual CHANGELOG.md updates (current practice).

## Commit Message Convention

**Current Practice**: Conventional Commits

**Format**:
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Test additions/updates
- `chore`: Maintenance tasks

**Examples**:
```bash
feat(linear): add story point estimation support
fix(cache): prevent memory leak in long-running processes
docs: update CLAUDE.md with versioning instructions
chore: bump version to 0.3.3
```

## Build Number Tracking

### Build Metadata File

**Location**: `.build_metadata.json` (git-ignored)

**Purpose**: Track every build with unique build number

**Auto-Increment**: Each `make build` increments `build_number`

**Example History**:
```json
Build #109: v0.3.1 (commit: abc123, branch: main)
Build #110: v0.3.2 (commit: def456, branch: main)
Build #111: v0.3.2 (commit: bd063ed, branch: main)  ← Current
```

### Build Metadata Usage

**Debugging**: Link production issues to specific build
**Auditing**: Track when and what was deployed
**Rollback**: Identify previous stable build numbers
**CI/CD**: Build numbers can be used in artifact naming

## Version Sources

### Single Source of Truth

**Primary**: `src/mcp_ticketer/__version__.py`
```python
__version__ = "0.3.2"
```

**Secondary**: `pyproject.toml` (dynamic versioning)
```toml
[project]
dynamic = ["version"]

[tool.setuptools.dynamic]
version = {attr = "mcp_ticketer.__version__"}
```

**Build Metadata**: `.build_metadata.json` (tracks version + metadata)

### Version Propagation

**Update Sequence**:
1. `scripts/manage_version.py` updates `__version__.py`
2. `setuptools` reads version from `__version__.py` during build
3. Build metadata is written to `.build_metadata.json`

## Recommendations

### ✅ Already Excellent

1. **Comprehensive version management script**
2. **Build tracking with metadata**
3. **Git integration (commits, tags)**
4. **Release validation**
5. **Makefile automation**
6. **E2E test integration in publish workflow** (newly added)

### 🟡 Consider Adding

1. **Changelog Automation**
   - Tool: `standard-version` or `git-cliff`
   - Benefit: Auto-generate CHANGELOG.md from commits

2. **Pre-commit Hook for Version Checks**
   - Validate version was bumped before release commits
   - Prevent accidental duplicate versions

3. **CI/CD Build Number Integration**
   - Pass build number to CI/CD systems
   - Use in Docker image tags, artifact names

4. **Version Bump Detection from Commits**
   - Auto-detect if commit should bump major/minor/patch
   - Based on conventional commit types

### ⚪ Optional Enhancements

1. **Release Notes Template**
   - Structured template for release notes
   - Categories: Features, Fixes, Breaking Changes

2. **Version History Tracking**
   - Maintain history of all builds in separate file
   - Archive old build metadata

3. **Semantic Release Full Automation**
   - Fully automated version bumps
   - Based on commit messages only

## Summary

**Current Status**: ✅ EXCELLENT

MCP Ticketer already has a robust version management and build tracking system:

- ✅ Semantic versioning with automation
- ✅ Build tracking with comprehensive metadata
- ✅ Git integration (commits, tags)
- ✅ Release validation
- ✅ Makefile automation for all workflows
- ✅ E2E test integration before publishing (newly added)

**No critical improvements needed**. The system is production-ready and follows best practices.

**Optional**: Add changelog automation for even better developer experience.
