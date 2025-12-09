# mcp-ticketer Release Workflow Analysis

**Date**: 2025-12-09
**Researcher**: Research Agent
**Purpose**: Analyze current release process and identify automation gaps

## Executive Summary

The mcp-ticketer project has a **well-structured but partially manual** release workflow. Core distribution (PyPI) is automated, but GitHub releases, changelog management, and post-release verification are manual processes.

**Key Findings**:
- ✅ **Automated**: Version bumping, PyPI publishing, Homebrew tap updates, submodule management
- ❌ **Manual**: GitHub release creation, changelog maintenance, release notes, post-release verification
- ⚠️ **Partial**: Quality gates (runs but could be stricter), rollback procedures (undefined)

---

## Current State of Automation

### 1. What's Already Automated

#### Version Management (`scripts/manage_version.py`)
- **Semantic versioning**: Bump major/minor/patch versions
- **Multi-file updates**: Updates `__version__.py` and `pyproject.toml`
- **Git integration**: Creates commits and tags automatically
- **Build tracking**: Maintains `.build_metadata.json` with build numbers and timestamps
- **Release validation**: Checks for clean git state, valid semver format, git branch

**Usage**:
```bash
make release-patch  # Bumps version, builds, publishes to PyPI
make release-minor  # Minor version bump
make release-major  # Major version bump
```

#### PyPI Publishing (`release.mk`)
- **Build system**: Uses PEP 517 (`python -m build`)
- **Quality gates**: Runs format, lint, test, test-e2e before publishing
- **Package verification**: `twine check` for metadata validation
- **TestPyPI support**: `make publish-test` for pre-release testing
- **Credential management**: Supports `.env.local`, `~/.pypirc`, or environment variables

**Dependencies for `publish-prod`**:
```makefile
publish-prod: check-release format lint test test-e2e build verify-dist
```

#### Homebrew Tap Updates (`scripts/update_homebrew_tap.sh`)
- **Auto-detection**: Waits for PyPI to publish package (with retry logic)
- **SHA256 verification**: Fetches checksum from PyPI automatically
- **Formula updates**: Updates version, URL, and SHA256 in Formula file
- **Repository management**: Clones/updates tap repository (`bobmatnyc/homebrew-tools`)
- **Commit creation**: Creates commit with standardized message
- **Audit check**: Runs `brew audit --new` for syntax validation

**Usage**:
```bash
make update-homebrew-tap VERSION=1.2.10  # Manual version specification
make homebrew-tap-auto                   # Auto-detect current version
```

**Manual step**: Still requires `git push` to publish tap updates.

#### Submodule Management (`scripts/release_submodules.py`)
- **Change detection**: Checks git status of each submodule
- **Conditional releases**: Only releases submodules with uncommitted changes
- **Version synchronization**: Runs submodule's `./scripts/release.sh`
- **Parent repo updates**: Commits submodule pointer updates to parent repo

**Tracked submodule**:
- `py-mcp-installer` at `src/services/py_mcp_installer`

**Usage**:
```bash
make release-patch-full  # Releases submodules + main package
```

---

### 2. What's Manual

#### ❌ GitHub Releases
- **No automation**: No script or Makefile target to create GitHub releases
- **Manual process**: User must run `gh release create` manually
- **Release notes**: Must be written manually
- **Asset uploads**: Not configured (though likely not needed for Python packages)

**Current workflow requires**:
```bash
# After PyPI publish
git push origin main
git push origin v1.2.10
gh release create v1.2.10 --title "v1.2.10" --notes "Release notes here"
```

#### ❌ Changelog Management
- **No CHANGELOG file**: Project does not maintain a CHANGELOG.md
- **No automation**: No script to generate changelogs from commits or tickets
- **Linear integration potential**: Could pull from Linear project issues

**Missing**:
- `CHANGELOG.md` file in project root
- Script to generate changelog from git commits or Linear issues
- Integration with version bump workflow

#### ❌ Post-Release Verification
- **No verification script**: No automated check that published package works
- **Manual testing required**: User must manually test:
  - `pip install mcp-ticketer==X.Y.Z`
  - `brew upgrade mcp-ticketer`
  - MCP server installation

**Missing**:
- Script to verify PyPI package is installable
- Script to verify Homebrew formula works
- Integration test against published package

#### ❌ Rollback Procedures
- **No rollback automation**: No script to rollback failed releases
- **Manual cleanup required**: User must manually:
  - Delete git tags
  - Yank PyPI packages
  - Revert Homebrew formula commits

---

### 3. Distribution Channels

#### ✅ PyPI (Primary - Automated)
- **Repository**: https://pypi.org/project/mcp-ticketer/
- **Automation level**: Fully automated via `make release-{patch,minor,major}`
- **Credentials**: `.env.local` or `~/.pypirc`
- **Verification**: `twine check` before upload

#### ✅ Homebrew Tap (Automated with manual push)
- **Repository**: `bobmatnyc/homebrew-tools`
- **Formula path**: `Formula/mcp-ticketer.rb`
- **Automation level**: 90% automated (requires manual `git push`)
- **Update script**: `scripts/update_homebrew_tap.sh`

**Installation**:
```bash
brew tap bobmatnyc/tools
brew install mcp-ticketer
```

#### ✅ pipx Compatible (Implicit)
- **No special config**: Works by default since package has CLI entry points
- **Installation**: `pipx install mcp-ticketer`
- **Upgrade**: `pipx upgrade mcp-ticketer`

#### ❓ Other Channels (Not Currently Used)
- Docker: No Dockerfile or container registry
- conda-forge: Not published to conda
- snap/flatpak: Not packaged for Linux app stores
- GitHub Packages: Not published to GitHub Packages registry

---

### 4. Submodule Requirements

#### Current Submodule: `py-mcp-installer`
- **Path**: `src/services/py_mcp_installer`
- **Repository**: https://github.com/bobmatnyc/py-mcp-installer-service.git
- **Current commit**: `a0587b1` (v0.0.3-6-ga0587b1)

**Submodule release workflow** (`src/services/py_mcp_installer/scripts/release.sh`):
1. Detect Python executable
2. Get current version from `scripts/manage_version.py`
3. Bump version (patch/minor/major)
4. Commit version changes (`VERSION` + `__init__.py`)
5. Create git tag (`v$NEW_VERSION`)
6. Push changes and tag to origin/main
7. Create GitHub release using `gh release create`

**Integration with parent**:
- Parent's `make release-patch-full` checks submodule for changes
- If changes exist, runs submodule's `./scripts/release.sh`
- Updates parent's submodule pointer
- Commits pointer update before releasing parent

**Gap**: Submodule uses `gh release create` but parent doesn't (inconsistency).

---

### 5. Quality Gates

#### Pre-Publish Checks (`publish-prod` dependencies)
1. ✅ **check-release**: Git clean state, valid semver, on git branch
2. ✅ **format**: Code formatting (black, ruff)
3. ✅ **lint**: Static analysis (ruff, mypy)
4. ✅ **test**: Unit and integration tests
5. ✅ **test-e2e**: End-to-end tests (target exists but needs verification)
6. ✅ **build**: PEP 517 build (wheel + sdist)
7. ✅ **verify-dist**: Twine package validation

**Test targets** (from Makefile):
```bash
make test              # Run all tests
make test-parallel     # Run tests in parallel (3-4x faster)
make test-e2e          # End-to-end tests (need to verify existence)
make ci-test           # Simulate CI pipeline
```

**Missing checks**:
- ❌ Dependency vulnerability scan (e.g., `safety check`, `pip-audit`)
- ❌ Breaking change detection
- ❌ Backward compatibility tests
- ❌ Documentation build verification

---

## Identified Gaps

### Critical Gaps (Block releases or cause failures)

#### 1. No GitHub Release Automation
**Impact**: Manual step required after every release
**Current workaround**: User manually runs `gh release create`
**Recommendation**: Add `scripts/create_github_release.sh` script

**Proposed script**:
```bash
#!/usr/bin/env bash
# Create GitHub release with changelog
VERSION="$1"
CHANGELOG_FILE="CHANGELOG.md"

# Extract version-specific changelog section
NOTES=$(awk "/## \[${VERSION}\]/,/## \[/{print}" "$CHANGELOG_FILE" | head -n -1)

gh release create "v${VERSION}" \
    --title "mcp-ticketer v${VERSION}" \
    --notes "$NOTES" \
    --repo bobmatnyc/mcp-ticketer
```

**Integration**:
```makefile
.PHONY: release-github
release-github: ## Create GitHub release (requires VERSION)
	@bash scripts/create_github_release.sh $(VERSION)
```

---

#### 2. No Changelog Management
**Impact**: No single source of truth for release notes
**Current workaround**: Manual release notes in GitHub releases
**Recommendation**: Implement automated changelog generation

**Options**:
1. **Conventional Commits** (requires commit message discipline):
   - Use `git-cliff` or `standard-version`
   - Parses commits like `feat:`, `fix:`, `chore:`

2. **Linear Issue Integration** (leverages existing workflow):
   - Query Linear API for closed issues in milestone
   - Generate changelog from issue titles and descriptions
   - Use `scripts/generate_changelog_from_linear.py`

**Proposed structure** (CHANGELOG.md):
```markdown
# Changelog

All notable changes to mcp-ticketer will be documented in this file.

## [2.2.11] - 2025-12-09

### Added
- GitHub release automation script
- Changelog generation from Linear issues

### Fixed
- Homebrew tap push automation

### Changed
- Release workflow now includes GitHub release creation

## [2.2.10] - 2025-12-08
...
```

---

#### 3. Homebrew Tap Push Not Automated
**Impact**: Extra manual step after release
**Current state**: Script creates commit but requires manual `git push`
**Recommendation**: Add push to `update_homebrew_tap.sh`

**Change needed** (lines 142-153 of `scripts/update_homebrew_tap.sh`):
```bash
# Current (manual push required):
log_info "Formula updated successfully!"
echo ""
echo "Next steps:"
echo "1. Review the changes above"
echo "2. Push to GitHub:"
echo "   cd ${TAP_DIR}"
echo "   git push origin main"

# Proposed (automated push):
log_info "Formula updated successfully!"
log_info "Pushing to GitHub..."
git push origin main
log_info "✅ Homebrew tap updated and pushed!"
```

**Risk consideration**: Auto-push removes review opportunity. Mitigation:
- Add `--dry-run` flag to preview changes
- Add `--no-push` flag to skip push
- Default to auto-push for convenience

---

#### 4. test-e2e Target May Not Exist
**Impact**: Quality gate may not actually run
**Current state**: `publish-prod` depends on `test-e2e` but target not found in grep
**Recommendation**: Verify test-e2e exists or remove from dependencies

**Verification needed**:
```bash
make test-e2e  # Does this work?
```

**If missing**: Either create the target or remove from `publish-prod` dependencies.

---

### High-Priority Gaps (Improve reliability)

#### 5. No Post-Release Verification
**Impact**: Published package might not install correctly
**Recommendation**: Add verification script

**Proposed script** (`scripts/verify_release.sh`):
```bash
#!/usr/bin/env bash
VERSION="$1"

echo "🔍 Verifying PyPI release..."
pip install "mcp-ticketer==${VERSION}" --dry-run --no-deps || exit 1

echo "🔍 Verifying Homebrew formula..."
brew info mcp-ticketer | grep -q "${VERSION}" || exit 1

echo "✅ Release v${VERSION} verified successfully!"
```

---

#### 6. No Rollback Automation
**Impact**: Failed releases require manual cleanup
**Recommendation**: Add rollback script

**Proposed script** (`scripts/rollback_release.sh`):
```bash
#!/usr/bin/env bash
VERSION="$1"

echo "⚠️  Rolling back release v${VERSION}..."

# Delete git tag
git tag -d "v${VERSION}"
git push origin ":refs/tags/v${VERSION}"

# Yank PyPI package (doesn't delete, marks as unusable)
twine upload --skip-existing --repository pypi --yank "v${VERSION}"

# Revert Homebrew formula (if already pushed)
echo "Manual step: Revert Homebrew tap commit if already pushed"

echo "✅ Rollback complete. PyPI package yanked, git tag deleted."
```

---

#### 7. No Linear Issue Auto-Closure
**Impact**: Issues not auto-marked as done after release
**Current state**: Linear project URL exists in CLAUDE.md
**Recommendation**: Auto-transition Linear issues on release

**Proposed script** (`scripts/close_linear_issues.sh`):
```bash
#!/usr/bin/env bash
VERSION="$1"
MILESTONE="v${VERSION}"

# Query Linear for issues in milestone
# Transition to "Done" state
# Add comment with release URL
```

---

### Medium-Priority Gaps (Nice to have)

#### 8. No Breaking Change Detection
**Impact**: Major version bumps might be missed
**Recommendation**: Add `scripts/detect_breaking_changes.py`

#### 9. No Dependency Vulnerability Scanning
**Impact**: Security issues might be released
**Recommendation**: Add `make security-check` target with `pip-audit`

#### 10. No Release Notification System
**Impact**: Users don't know about new releases
**Recommendation**: Consider Discord/Slack webhook notifications

---

## Recommended Automation Approach

### Phase 1: Critical Automation (Week 1)
**Goal**: Eliminate all manual post-release steps

1. **Create `scripts/create_github_release.sh`**
   - Integrate with release workflow
   - Auto-generate release notes from git log or Linear

2. **Add `CHANGELOG.md` generation**
   - Choose between conventional commits or Linear integration
   - Auto-update on version bump

3. **Auto-push Homebrew tap updates**
   - Add `--auto-push` flag (default true)
   - Keep `--dry-run` option for safety

4. **Verify test-e2e target**
   - Check if it exists
   - Fix or remove from dependencies

**Deliverable**: Single command releases (no manual steps).

---

### Phase 2: Quality Improvements (Week 2)
**Goal**: Increase release reliability

5. **Add post-release verification**
   - `scripts/verify_release.sh`
   - Integrate into release workflow

6. **Create rollback script**
   - `scripts/rollback_release.sh`
   - Document rollback procedure

7. **Add security scanning**
   - `make security-check` with `pip-audit`
   - Integrate into pre-publish checks

**Deliverable**: Reliable releases with safety nets.

---

### Phase 3: Integration & Notifications (Week 3)
**Goal**: Full CI/CD integration

8. **Linear issue auto-closure**
   - Close issues on release
   - Add release links to issue comments

9. **Release notifications**
   - Discord/Slack webhooks
   - GitHub Discussions post

10. **GitHub Actions CI/CD**
    - Auto-release on tag push
    - Parallel testing
    - Multi-platform verification

**Deliverable**: Fully automated CI/CD pipeline.

---

## Complete Release Workflow (Proposed)

### Current Workflow (Manual Steps)
```bash
# 1. Update code and commit
git add .
git commit -m "feat: add feature"

# 2. Run release (automated)
make release-patch

# 3. Manual steps (❌ not automated)
git push origin main
git push origin v1.2.11
gh release create v1.2.11 --title "v1.2.11" --notes "..."
cd ~/.homebrew-taps/homebrew-tools && git push origin main
```

---

### Proposed Workflow (Fully Automated)
```bash
# 1. Update code and commit
git add .
git commit -m "feat: add feature"

# 2. Single release command (✅ fully automated)
make release-patch

# Behind the scenes:
# - Bump version in __version__.py and pyproject.toml
# - Update CHANGELOG.md with new version section
# - Run quality gates (format, lint, test, test-e2e)
# - Build packages (wheel + sdist)
# - Publish to PyPI
# - Create git tag
# - Push to origin/main and tag
# - Create GitHub release with changelog
# - Update Homebrew tap and push
# - Verify release on PyPI and Homebrew
# - Close Linear issues in milestone
# - Send release notifications
```

---

## Implementation Priority Matrix

| Task | Impact | Effort | Priority | Phase |
|------|--------|--------|----------|-------|
| GitHub release automation | High | Low | **P0** | Phase 1 |
| CHANGELOG.md generation | High | Medium | **P0** | Phase 1 |
| Homebrew tap auto-push | Medium | Low | **P1** | Phase 1 |
| Verify test-e2e exists | High | Low | **P0** | Phase 1 |
| Post-release verification | High | Low | **P1** | Phase 2 |
| Rollback automation | High | Medium | **P1** | Phase 2 |
| Security scanning | Medium | Low | **P2** | Phase 2 |
| Linear issue auto-closure | Low | High | **P3** | Phase 3 |
| Release notifications | Low | Medium | **P3** | Phase 3 |
| GitHub Actions CI/CD | Medium | High | **P3** | Phase 3 |

---

## Files to Create

### Phase 1 (Critical)
1. `scripts/create_github_release.sh` - GitHub release automation
2. `scripts/generate_changelog.py` - Changelog generation (Linear or git-based)
3. `CHANGELOG.md` - Changelog file (initial version)
4. `.makefiles/release.mk` updates - Integrate new scripts

### Phase 2 (Quality)
5. `scripts/verify_release.sh` - Post-release verification
6. `scripts/rollback_release.sh` - Release rollback automation
7. `scripts/security_check.sh` - Dependency vulnerability scanning

### Phase 3 (Integration)
8. `scripts/close_linear_issues.py` - Linear issue auto-closure
9. `scripts/notify_release.sh` - Release notification system
10. `.github/workflows/release.yml` - GitHub Actions CI/CD

---

## Conclusion

**Current State**: 70% automated (PyPI publishing, Homebrew tap updates, submodule management)
**Missing**: 30% manual (GitHub releases, changelog, verification, rollback)

**Recommendation**: Implement Phase 1 (critical automation) immediately to achieve **100% automated releases** with a single `make release-patch` command.

**Estimated Effort**:
- Phase 1: 4-6 hours
- Phase 2: 3-4 hours
- Phase 3: 8-10 hours

**Total**: ~2 work days for complete automation.

---

## Next Steps

1. Create GitHub issue for release automation work
2. Break down into subtasks (one per script)
3. Implement Phase 1 scripts first
4. Test on patch release (v2.2.11)
5. Iterate based on feedback
6. Document new workflow in `docs/RELEASE.md`

---

**Generated by**: Research Agent
**Date**: 2025-12-09
**Project**: mcp-ticketer v2.2.10
