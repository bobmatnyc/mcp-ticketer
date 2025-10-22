# MCP Ticketer Scripts

This directory contains automation scripts for managing the mcp-ticketer project.

## Version Management (`manage_version.py`)

Comprehensive version management script that handles semantic versioning, build tracking, and release validation.

### Features

- **Semantic Version Bumping**: Automated major, minor, and patch version increments
- **Build Tracking**: Tracks build metadata including commit SHA, timestamps, and build numbers
- **Release Validation**: Ensures the repository is in a clean state before releases
- **Git Integration**: Automatic commit creation and tagging for version bumps

### Usage

#### Get Current Version
```bash
python3 scripts/manage_version.py get-version
# Output: 0.1.11
```

#### Bump Version
```bash
# Bump patch version (0.1.11 → 0.1.12)
python3 scripts/manage_version.py bump patch

# Bump minor version (0.1.11 → 0.2.0)
python3 scripts/manage_version.py bump minor

# Bump major version (0.1.11 → 1.0.0)
python3 scripts/manage_version.py bump major

# Bump with automatic git commit and tag
python3 scripts/manage_version.py bump patch --git-commit --git-tag
```

#### Check Release Readiness
```bash
python3 scripts/manage_version.py check-release

# Checks:
# ✅ Git working directory is clean
# ✅ Version follows semver format
# ✅ Git branch is valid
```

#### Track Build
```bash
python3 scripts/manage_version.py track-build --notes "Bug fixes and improvements"

# Creates/updates .build_metadata.json with:
# - version
# - build_number (auto-incremented)
# - git_commit
# - git_branch
# - build_timestamp
# - release_notes
# - previous_version
```

### Build Metadata Format

`.build_metadata.json` contains:

```json
{
  "version": "0.1.12",
  "build_number": 15,
  "git_commit": "abc123d",
  "git_branch": "main",
  "build_timestamp": "2025-10-22T19:30:00Z",
  "release_notes": "Bug fixes and improvements",
  "previous_version": "0.1.11"
}
```

### Integration with Makefile

The version management script is integrated into the project's Makefile:

#### Version Commands
```bash
# Show current version
make version

# Bump versions (includes git commit and tag)
make version-bump-patch
make version-bump-minor
make version-bump-major

# Check if ready for release
make check-release
```

#### Build Commands
```bash
# Build package (includes build tracking)
make build

# Clean build artifacts
make clean-build
```

#### Publishing Commands
```bash
# Publish to TestPyPI (includes release check)
make publish-test

# Publish to PyPI (includes release check)
make publish-prod
```

#### Full Release Workflow
```bash
# Complete patch release (bump + build + publish)
make release-patch

# Complete minor release
make release-minor

# Complete major release
make release-major
```

### Release Workflow

The recommended release workflow:

```bash
# 1. Ensure all changes are committed and tests pass
git status
make quality  # Run tests, linting, formatting

# 2. Create a release (bumps version, builds, publishes)
make release-patch  # or release-minor, release-major

# This executes:
# - version-bump-patch (updates version, creates git commit and tag)
# - build (builds package, tracks build metadata)
# - publish-prod (validates release, uploads to PyPI)
```

### Manual Release Steps

For more control over the release process:

```bash
# 1. Check if ready for release
make check-release

# 2. Bump version
make version-bump-patch

# 3. Build package
make build

# 4. Test publish (optional)
make publish-test

# 5. Publish to PyPI
make publish-prod
```

### Error Handling

The script provides clear error messages for common issues:

```bash
# Uncommitted changes
❌ Release validation failed:
  - Git working directory has uncommitted changes

# Invalid version format
Error: Version must be X.Y.Z

# Version downgrade attempt
Error: New version must be > current

# Missing version file
Error: Version file not found: src/mcp_ticketer/__version__.py
```

### Requirements

- Python 3.9+
- Git repository
- Setuptools-based build system

### Version File Format

The script expects `src/mcp_ticketer/__version__.py` to contain:

```python
"""Version information for mcp-ticketer."""

__version__ = "0.1.11"
__version_info__ = tuple(int(part) for part in __version__.split("."))
```

### PyPI Configuration

For publishing, ensure you have:

1. **PyPI Credentials**: Configure in `~/.pypirc` or use environment variables:
   ```ini
   [pypi]
   username = __token__
   password = pypi-...

   [testpypi]
   repository = https://test.pypi.org/legacy/
   username = __token__
   password = pypi-...
   ```

2. **Build Tools**: Install build and publishing tools:
   ```bash
   pip install build twine
   ```

### Continuous Integration

The version management script is designed to work in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Bump version
  run: python3 scripts/manage_version.py bump patch --git-commit --git-tag

- name: Build package
  run: python3 -m build

- name: Track build
  run: python3 scripts/manage_version.py track-build --notes "Automated release"

- name: Publish to PyPI
  run: twine upload dist/*
  env:
    TWINE_USERNAME: __token__
    TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
```

### Development

The script is fully type-annotated and follows strict Python standards:

- Type hints with mypy compatibility
- Comprehensive docstrings
- Error handling with specific exceptions
- Structured logging and output

### Testing the Script

```bash
# Test version retrieval
python3 scripts/manage_version.py get-version

# Test release validation (should fail if uncommitted changes)
python3 scripts/manage_version.py check-release

# Test build tracking
python3 scripts/manage_version.py track-build --notes "Test build"

# Dry-run version bump (check but don't commit)
python3 scripts/manage_version.py bump patch
# (without --git-commit flag)
```

## Future Enhancements

Potential additions:

- [ ] CHANGELOG.md automatic generation
- [ ] GitHub release creation via API
- [ ] Pre-release version support (alpha, beta, rc)
- [ ] Version comparison and history
- [ ] Integration with CI/CD platforms
- [ ] Rollback capabilities
