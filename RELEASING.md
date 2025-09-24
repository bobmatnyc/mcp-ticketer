# Release Process

This document describes the release process for MCP Ticketer.

## Table of Contents

- [Overview](#overview)
- [Version Numbering](#version-numbering)
- [Release Types](#release-types)
- [Release Checklist](#release-checklist)
- [Automated Release Process](#automated-release-process)
- [Manual Release Process](#manual-release-process)
- [Post-Release Tasks](#post-release-tasks)
- [Rollback Procedure](#rollback-procedure)

## Overview

MCP Ticketer follows a structured release process to ensure quality and consistency across releases. We use semantic versioning and maintain multiple release channels.

## Version Numbering

We follow [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR** (X.0.0): Incompatible API changes
- **MINOR** (0.X.0): Backward-compatible functionality additions
- **PATCH** (0.0.X): Backward-compatible bug fixes

Additional labels:
- **Pre-release**: `-alpha.N`, `-beta.N`, `-rc.N`
- **Development**: `-dev.N` (for development builds)

## Release Types

### Stable Release
- Production-ready releases
- Published to PyPI main index
- Full testing and documentation required

### Pre-Release
- Alpha/Beta/RC releases for testing
- Published to PyPI with pre-release flag
- May contain known issues

### Development Release
- Nightly/development builds
- Published to TestPyPI only
- For testing and development purposes

## Release Checklist

### Pre-Release Checklist

- [ ] All tests passing on main branch
- [ ] Documentation updated
- [ ] CHANGELOG.md updated with release notes
- [ ] Version bumped in `src/mcp_ticketer/__version__.py`
- [ ] Dependencies updated and locked
- [ ] Security audit completed
- [ ] Performance benchmarks acceptable
- [ ] Manual smoke tests completed

### Release Preparation

1. **Create Release Branch**
   ```bash
   git checkout -b release/v0.X.Y
   git push -u origin release/v0.X.Y
   ```

2. **Update Version**
   ```bash
   # Edit src/mcp_ticketer/__version__.py
   __version__ = "0.X.Y"

   # Commit changes
   git add src/mcp_ticketer/__version__.py
   git commit -m "chore: bump version to 0.X.Y"
   ```

3. **Update CHANGELOG**
   ```bash
   # Edit CHANGELOG.md
   # Add release notes under ## [0.X.Y] - YYYY-MM-DD

   git add CHANGELOG.md
   git commit -m "docs: update changelog for v0.X.Y"
   ```

4. **Run Final Checks**
   ```bash
   # Run all tests
   tox

   # Build documentation
   cd docs && make html

   # Build package
   python -m build

   # Check package
   twine check dist/*
   ```

## Automated Release Process

### GitHub Release Workflow

1. **Create and Push Tag**
   ```bash
   git tag -a v0.X.Y -m "Release v0.X.Y"
   git push origin v0.X.Y
   ```

2. **GitHub Actions Automation**
   - Tests run automatically
   - Package built and validated
   - Published to PyPI
   - Documentation deployed
   - GitHub Release created

3. **Monitor Release**
   - Check [GitHub Actions](https://github.com/mcp-ticketer/mcp-ticketer/actions)
   - Verify [PyPI Package](https://pypi.org/project/mcp-ticketer/)
   - Check [Documentation](https://mcp-ticketer.readthedocs.io/)

### Manual Trigger

For manual releases or re-runs:

```bash
# Trigger workflow manually
gh workflow run publish.yml -f environment=pypi
```

## Manual Release Process

If automated release fails, follow these steps:

### 1. Build Package

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build source distribution and wheel
python -m build

# Verify build
ls -la dist/
twine check dist/*
```

### 2. Test Installation

```bash
# Create test environment
python -m venv test_env
source test_env/bin/activate

# Test wheel installation
pip install dist/*.whl
mcp-ticketer --version

# Test source distribution
pip uninstall -y mcp-ticketer
pip install dist/*.tar.gz
mcp-ticketer --version

deactivate
rm -rf test_env
```

### 3. Upload to TestPyPI

```bash
# Upload to TestPyPI first
twine upload -r testpypi dist/*

# Test installation from TestPyPI
pip install -i https://test.pypi.org/simple/ mcp-ticketer==0.X.Y
```

### 4. Upload to PyPI

```bash
# Upload to production PyPI
twine upload dist/*

# Verify installation
pip install mcp-ticketer==0.X.Y
```

## Post-Release Tasks

### 1. Create GitHub Release

```bash
gh release create v0.X.Y \
  --title "Release v0.X.Y" \
  --notes-file RELEASE_NOTES.md \
  dist/*
```

### 2. Update Documentation

- Ensure ReadTheDocs builds successfully
- Update version switcher if needed
- Verify all links work

### 3. Announcement

- [ ] Update project website
- [ ] Post on social media
- [ ] Send announcement to mailing list
- [ ] Update Discord/Slack channels

### 4. Merge Release Branch

```bash
# Merge to main
git checkout main
git merge --no-ff release/v0.X.Y
git push origin main

# Tag the release
git tag -a v0.X.Y -m "Release v0.X.Y"
git push origin v0.X.Y

# Delete release branch
git branch -d release/v0.X.Y
git push origin --delete release/v0.X.Y
```

### 5. Prepare Next Development Cycle

```bash
# Bump to next development version
# Edit src/mcp_ticketer/__version__.py
__version__ = "0.X.Y+1.dev0"

git add src/mcp_ticketer/__version__.py
git commit -m "chore: bump version to 0.X.Y+1.dev0"
git push origin main
```

## Rollback Procedure

If a release has critical issues:

### 1. Yank from PyPI

```bash
# Mark release as yanked (doesn't delete, just hides)
# This must be done via PyPI web interface
```

### 2. Revert Changes

```bash
# Create hotfix from previous stable tag
git checkout -b hotfix/v0.X.Y-1 v0.X.Y-1
git cherry-pick <fix-commits>
```

### 3. Release Hotfix

```bash
# Bump patch version
# Follow normal release process for v0.X.Y+1
```

### 4. Communicate

- [ ] Update GitHub release notes with rollback notice
- [ ] Post announcement about the issue
- [ ] Document lessons learned

## Version Management Commands

### Using bump2version

```bash
# Install bump2version
pip install bump2version

# Bump patch version (0.1.0 -> 0.1.1)
bump2version patch

# Bump minor version (0.1.0 -> 0.2.0)
bump2version minor

# Bump major version (0.1.0 -> 1.0.0)
bump2version major

# Bump pre-release (0.1.0 -> 0.1.1-alpha.1)
bump2version --tag-name v{new_version} prerelease
```

### Manual Version Update

```python
# Edit src/mcp_ticketer/__version__.py
__version__ = "NEW_VERSION"
```

## CI/CD Integration

### Environment Variables

Required secrets in GitHub:
- `PYPI_API_TOKEN`: PyPI API token
- `TEST_PYPI_API_TOKEN`: TestPyPI API token
- `CODECOV_TOKEN`: Codecov integration
- `READTHEDOCS_TOKEN`: ReadTheDocs webhook

### Release Triggers

- **Tag Push**: Triggers full release pipeline
- **Release Creation**: Publishes to PyPI
- **Manual Dispatch**: Allows manual release

## Troubleshooting

### Common Issues

1. **Build Fails**
   ```bash
   # Clean and rebuild
   rm -rf build dist *.egg-info
   python -m build --sdist --wheel
   ```

2. **Twine Upload Fails**
   ```bash
   # Check credentials
   twine check dist/*

   # Use token authentication
   twine upload dist/* -u __token__ -p <pypi-token>
   ```

3. **Version Conflict**
   ```bash
   # Ensure version is unique
   pip index versions mcp-ticketer
   ```

4. **Documentation Not Updating**
   - Check ReadTheDocs webhook
   - Manually trigger build
   - Verify `.readthedocs.yaml`

## Release Schedule

- **Patch Releases**: As needed for bug fixes
- **Minor Releases**: Monthly or bi-monthly
- **Major Releases**: Annually or as needed

## Support

For release-related questions:
- GitHub Issues: [Report problems](https://github.com/mcp-ticketer/mcp-ticketer/issues)
- Discord: #releases channel
- Email: releases@mcp-ticketer.io

---

Last updated: 2025-01-24