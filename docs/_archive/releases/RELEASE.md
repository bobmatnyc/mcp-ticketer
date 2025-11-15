# Release Management Guide

This document describes the release process for mcp-ticketer.

## Quick Start

### Simple Release (Recommended)

```bash
# For bug fixes and small improvements
make release-patch

# For new features
make release-minor

# For breaking changes
make release-major
```

This automatically:
1. Bumps the version
2. Creates a git commit and tag
3. Builds the package
4. Tracks build metadata
5. Validates the release
6. Publishes to PyPI

## Manual Release Process

For more control over each step:

### 1. Pre-Release Checklist

```bash
# Ensure all tests pass
make quality

# Check git status
git status

# Validate release readiness
make check-release
```

### 2. Version Bump

```bash
# Choose one:
make version-bump-patch  # 0.1.11 → 0.1.12
make version-bump-minor  # 0.1.11 → 0.2.0
make version-bump-major  # 0.1.11 → 1.0.0
```

This will:
- Update `src/mcp_ticketer/__version__.py`
- Create a git commit: `chore: bump version to X.Y.Z`
- Create a git tag: `vX.Y.Z`

### 3. Build Package

```bash
make build
```

This will:
- Clean previous build artifacts
- Build distribution packages (wheel and sdist)
- Track build metadata in `.build_metadata.json`

### 4. Test Release (Optional)

```bash
make publish-test
```

This publishes to TestPyPI for validation.

### 5. Publish to PyPI

```bash
make publish-prod
```

This will:
- Validate release readiness
- Upload to PyPI

## Version Management Commands

### Check Current Version

```bash
make version
# Or directly:
python3 scripts/manage_version.py get-version
```

### Validate Release Readiness

```bash
make check-release
```

Checks:
- ✅ Git working directory is clean
- ✅ Version follows semver format
- ✅ Git branch is valid

### Manual Version Script Usage

```bash
# Get version
python3 scripts/manage_version.py get-version

# Bump version (without git commit)
python3 scripts/manage_version.py bump patch

# Bump with git commit and tag
python3 scripts/manage_version.py bump patch --git-commit --git-tag

# Check release readiness
python3 scripts/manage_version.py check-release

# Track build
python3 scripts/manage_version.py track-build --notes "Release notes"
```

## Build Metadata

Build tracking data is stored in `.build_metadata.json`:

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

## Semantic Versioning

Follow [SemVer](https://semver.org/) guidelines:

- **MAJOR** (X.0.0): Breaking changes, incompatible API changes
- **MINOR** (0.X.0): New features, backward-compatible
- **PATCH** (0.0.X): Bug fixes, backward-compatible

## PyPI Configuration

### Setup PyPI Credentials

Create `~/.pypirc`:

```ini
[pypi]
username = __token__
password = pypi-AgE...

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgE...
```

### Install Required Tools

```bash
pip install build twine
```

## Troubleshooting

### Uncommitted Changes

```
❌ Release validation failed:
  - Git working directory has uncommitted changes
```

**Solution**: Commit or stash changes before releasing.

```bash
git status
git add .
git commit -m "Your commit message"
```

### Version Already Exists on PyPI

```
Error: File already exists
```

**Solution**: Bump to a new version.

```bash
make version-bump-patch
```

### Build Failures

```bash
# Clean and rebuild
make clean
make build
```

### Authentication Failures

Ensure PyPI token is correctly configured in `~/.pypirc` or set environment variables:

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-AgE...
```

## Release Checklist

- [ ] All tests pass (`make quality`)
- [ ] Git working directory is clean
- [ ] Version follows semver conventions
- [ ] CHANGELOG updated (if applicable)
- [ ] Documentation updated
- [ ] Version bumped appropriately
- [ ] Build succeeds
- [ ] Release notes added
- [ ] Published to PyPI
- [ ] Git tag pushed to remote

## CI/CD Integration

For automated releases via GitHub Actions:

```yaml
name: Release

on:
  workflow_dispatch:
    inputs:
      version_bump:
        description: 'Version bump type'
        required: true
        type: choice
        options:
          - patch
          - minor
          - major

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install build twine
      
      - name: Bump version
        run: python3 scripts/manage_version.py bump ${{ github.event.inputs.version_bump }} --git-commit --git-tag
      
      - name: Build package
        run: python3 -m build
      
      - name: Track build
        run: python3 scripts/manage_version.py track-build --notes "Automated release"
      
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
        run: twine upload dist/*
      
      - name: Push tags
        run: git push --follow-tags
```

## Post-Release

After a successful release:

1. Push tags to remote:
   ```bash
   git push --follow-tags
   ```

2. Create GitHub release (optional):
   ```bash
   gh release create v0.1.12 --notes "Release notes"
   ```

3. Announce release (optional):
   - Update documentation
   - Post on relevant channels
   - Update project website

## Resources

- [Semantic Versioning](https://semver.org/)
- [Python Packaging Guide](https://packaging.python.org/)
- [PyPI Publishing Guide](https://packaging.python.org/tutorials/packaging-projects/)
- [Twine Documentation](https://twine.readthedocs.io/)
