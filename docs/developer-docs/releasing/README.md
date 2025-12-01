# Release Management

Documentation for creating and publishing MCP Ticketer releases.

## 📚 Contents

### Release Guides

- **[Release Process](RELEASING.md)** - How to create and publish releases
  - Release preparation
  - Version bumping
  - Changelog updates
  - Build and test
  - Publishing to PyPI
  - GitHub release creation
  - Post-release tasks

- **[Versioning Guide](VERSIONING.md)** - Version numbering scheme
  - Semantic versioning
  - Version format
  - When to bump major/minor/patch
  - Pre-release versions
  - Version tags

## 🚀 Quick Release Guide

### Release Types

**Patch Release** (bug fixes only):
```bash
make release-patch
```

**Minor Release** (new features, backwards compatible):
```bash
make release-minor
```

**Major Release** (breaking changes):
```bash
make release-major
```

See: [Release Process - Quick Release](RELEASING.md#quick-release)

## 📋 Release Checklist

### Before Release
- [ ] Update CHANGELOG.md with changes
- [ ] Commit all changes
- [ ] Ensure clean working directory (`git status`)
- [ ] Run `make check-release` to validate readiness
- [ ] Run full test suite (`make test`)
- [ ] Update version numbers if needed

### During Release
- [ ] Run appropriate release command (`make release-{patch|minor|major}`)
- [ ] Verify version bump
- [ ] Verify CHANGELOG.md updated
- [ ] Verify git tag created

### After Release
- [ ] Push git tags: `git push origin main && git push origin vX.Y.Z`
- [ ] Create GitHub release with changelog
- [ ] Verify package on PyPI
- [ ] Announce release (if major/minor)

See: [Release Process - Checklist](RELEASING.md#release-checklist)

## 🔧 Release Commands

### Validation
```bash
# Check if ready to release
make check-release

# Run tests
make test

# Type check
make mypy

# Lint code
make lint
```

### Publishing
```bash
# Test publish to TestPyPI
make publish-test

# Publish to PyPI (done automatically by release commands)
make publish
```

See: [Release Process - Commands](RELEASING.md#make-commands)

## 📖 Version Numbering

MCP Ticketer follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version: Breaking changes
- **MINOR** version: New features (backwards compatible)
- **PATCH** version: Bug fixes (backwards compatible)

Format: `MAJOR.MINOR.PATCH` (e.g., `1.4.2`)

See: [Versioning Guide](VERSIONING.md)

## 📊 Release Verification

After each release, create a verification report in [`/docs/releases/`](../../releases/):

Example: [`v1.4.4-verification-report.md`](../../releases/v1.4.4-verification-report.md)

Include:
- What was tested
- Test results
- Known issues
- Verification checklist

## 📋 Related Documentation

- **[Developer Guide](../getting-started/DEVELOPER_GUIDE.md)** - Development guide
- **[Contributing Guide](../getting-started/CONTRIBUTING.md)** - Contribution guidelines
- **[CHANGELOG.md](../../../CHANGELOG.md)** - Complete changelog
- **[Release Documentation](../../releases/README.md)** - Verification reports

## 🆘 Getting Help

### Release Issues
- Check: [Troubleshooting](../../user-docs/troubleshooting/TROUBLESHOOTING.md)
- Ask: [GitHub Discussions](https://github.com/mcp-ticketer/mcp-ticketer/discussions)
- Report: [GitHub Issues](https://github.com/mcp-ticketer/mcp-ticketer/issues)

### First Time Releasing?
1. Read: [Release Process](RELEASING.md) thoroughly
2. Try: Test publish first (`make publish-test`)
3. Ask: For review from maintainers
4. Document: Any issues you encounter

---

[← Back to Developer Documentation](../README.md)
