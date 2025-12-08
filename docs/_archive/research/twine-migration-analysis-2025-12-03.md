# Twine Migration Analysis for mcp-ticketer

**Research Date**: 2025-12-03
**Project**: mcp-ticketer
**Current Version**: 2.0.3
**Objective**: Investigate current PyPI publishing setup and assess Twine migration needs

---

## Executive Summary

**FINDING**: Twine is **ALREADY DEPLOYED AND FULLY OPERATIONAL** in mcp-ticketer's publishing workflow.

**No migration is needed.** The project successfully uses Twine for all PyPI uploads as of v2.0.3 (released 2025-12-03). However, Twine is **NOT formally listed as a development dependency** in `pyproject.toml`, which creates a documentation gap and potential installation inconsistency.

**Key Findings**:
- ✅ Twine is installed and working (v6.2.0 confirmed)
- ✅ Makefile targets use `twine upload` for both TestPyPI and PyPI
- ✅ Authentication configured via `~/.pypirc` with API tokens
- ✅ Recent releases (v2.0.3) successfully published via Twine
- ⚠️ Twine **NOT** listed in `pyproject.toml` dev dependencies
- ⚠️ Documentation assumes Twine installation but doesn't enforce it
- ⚠️ No `twine check` validation step before upload

**Recommendations**:
1. **Add Twine to `pyproject.toml`** dev dependencies for consistency
2. **Add `twine check` validation** step to release workflow
3. **Document TestPyPI setup** in `~/.pypirc` configuration
4. **Add dist verification** target to Makefile (partially exists but incomplete)

---

## Current State Analysis

### 1. Publishing Method: Twine (Already Implemented)

**Current Implementation** (from `.makefiles/release.mk`, lines 54-77):

```makefile
.PHONY: publish-test
publish-test: check-release format lint test test-e2e build ## Build and publish to TestPyPI
	@echo "Publishing to TestPyPI..."
	@if [ -f .env.local ]; then \
		echo "Loading PyPI credentials from .env.local..."; \
		export $$(grep -E '^(TWINE_USERNAME|TWINE_PASSWORD)=' .env.local | xargs) && \
		twine upload --repository testpypi dist/*; \
	else \
		echo "No .env.local found, using default credentials (~/.pypirc or environment)..."; \
		twine upload --repository testpypi dist/*; \
	fi
	@echo "Published to TestPyPI!"

.PHONY: publish-prod
publish-prod: check-release format lint test test-e2e build ## Build and publish to PyPI
	@echo "Publishing to PyPI..."
	@if [ -f .env.local ]; then \
		echo "Loading PyPI credentials from .env.local..."; \
		export $$(grep -E '^(TWINE_USERNAME|TWINE_PASSWORD)=' .env.local | xargs) && \
		twine upload dist/*; \
	else \
		echo "No .env.local found, using default credentials (~/.pypirc or environment)..."; \
		twine upload dist/*; \
	fi
	@echo "Published successfully!"
```

**Analysis**:
- Uses `twine upload` for all PyPI interactions
- Supports dual authentication: `.env.local` (env vars) OR `~/.pypirc` (config file)
- Fallback to system credentials if `.env.local` not found
- Separates TestPyPI and production PyPI targets
- Runs full quality gate before publishing (format, lint, test, test-e2e, build)

**Verification** (from v2.0.3 release):
```
Uploading distributions to https://upload.pypi.org/legacy/
Uploading mcp_ticketer-2.0.3-py3-none-any.whl
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 508.7/508.7 kB
Uploading mcp_ticketer-2.0.3.tar.gz
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.3/2.3 MB

View at: https://pypi.org/project/mcp-ticketer/2.0.3/
```

✅ **WORKING AS EXPECTED**

---

### 2. Build System: python -m build

**Current Implementation** (from `.makefiles/release.mk`, lines 32-37):

```makefile
.PHONY: build
build: clean-build ## Build distribution packages
	@echo "Building distribution..."
	$(PYTHON) -m build
	@$(PYTHON) scripts/manage_version.py track-build
	@echo "Build complete! Packages in dist/"
```

**Build Backend** (from `pyproject.toml`, lines 1-3):

```toml
[build-system]
requires = ["setuptools>=68", "setuptools-scm>=8", "wheel"]
build-backend = "setuptools.build_meta"
```

**Analysis**:
- Uses `python -m build` (PEP 517 compliant)
- Build backend: `setuptools.build_meta`
- Produces wheel (`.whl`) and source distribution (`.tar.gz`)
- Tracks build metadata via `scripts/manage_version.py`

✅ **STANDARDS-COMPLIANT**

---

### 3. Dependencies Analysis

**Current `pyproject.toml` Dev Dependencies** (lines 71-84):

```toml
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "pytest-timeout>=2.2.0",
    "pytest-mock>=3.12.0",
    "pytest-xdist>=3.0.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.5.0",
    "tox>=4.11.0",
    "pre-commit>=3.5.0",
    "bump2version>=1.0.1",
]
```

**Missing Dependencies**:
- ❌ `twine` (not listed, but required by Makefile)
- ❌ `build` (not listed, but required by Makefile)

**Installed in System**:
- ✅ Twine v6.2.0 installed at `/Users/masa/.local/bin/twine`
- ✅ Working successfully for recent releases

**Problem**:
Dev dependencies don't include Twine or build module, creating inconsistency between documentation (which says "pip install build twine") and actual dependency declarations.

⚠️ **NEEDS STANDARDIZATION**

---

### 4. Authentication Configuration

**Method 1: `~/.pypirc` (Currently Active)**

```ini
[distutils]
index-servers =
    pypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-AgEIcHlwaS5vcmcC...  # API token (confirmed working)
```

✅ **PROPERLY CONFIGURED** (PyPI production only)

**Method 2: `.env.local` (Optional)**

```bash
LINEAR_API_KEY=lin_api_YOUR_LINEAR_API_KEY_HERE
LINEAR_TEAM_KEY=YOUR_TEAM_KEY
```

**Missing**: TWINE_USERNAME and TWINE_PASSWORD variables

**Gap**: `.env.local` exists but doesn't include PyPI credentials. Makefile expects either:
1. `.env.local` with `TWINE_USERNAME` and `TWINE_PASSWORD`, OR
2. `~/.pypirc` configuration (current working setup)

⚠️ **DOCUMENTATION GAP**: TestPyPI not configured in `~/.pypirc`

---

### 5. Documentation Analysis

**RELEASE.md Documentation** (lines 47-109):

**Prerequisites Section** (lines 56-58):
```markdown
2. **Build Tools**
   ```bash
   pip install build twine
   ```
```

**PyPI Credentials Setup** (lines 77-107):
- Option 1: Environment Variables (`.env.local`)
- Option 2: PyPI Configuration File (`~/.pypirc`)

**Analysis**:
- ✅ Documents Twine installation
- ✅ Documents authentication setup (both methods)
- ✅ Includes TestPyPI configuration example
- ⚠️ Assumes manual installation instead of enforcing via `pyproject.toml`

**Inconsistency**:
Documentation says "pip install build twine" but `pyproject.toml` doesn't include these in dev dependencies. Users installing via `pip install -e ".[dev]"` won't get Twine automatically.

---

### 6. Release Workflow Analysis

**Full Release Commands** (from `.makefiles/release.mk`, lines 84-97):

```makefile
.PHONY: release-patch
release-patch: version-bump-patch build publish-prod
	@echo "✅ Patch release complete!"
	@$(PYTHON) scripts/manage_version.py get-version

.PHONY: release-minor
release-minor: version-bump-minor build publish-prod
	@echo "✅ Minor release complete!"
	@$(PYTHON) scripts/manage_version.py get-version

.PHONY: release-major
release-major: version-bump-major build publish-prod
	@echo "✅ Major release complete!"
	@$(PYTHON) scripts/manage_version.py get-version
```

**Workflow Dependencies**:
1. `version-bump-*` → Bumps version, commits, tags
2. `build` → Cleans, builds wheel + sdist, tracks metadata
3. `publish-prod` → Runs quality gates + uploads via Twine

**Quality Gates in `publish-prod`** (line 67):
```makefile
publish-prod: check-release format lint test test-e2e build
```

**Missing Steps**:
- ❌ No `twine check dist/*` validation before upload
- ❌ No explicit dist verification target (exists but not called)

**Existing but Unused** (lines 101-109):
```makefile
.PHONY: verify-dist
verify-dist: ## Verify distribution packages
	@echo "Verifying distribution packages..."
	@if [ ! -d dist ]; then echo "Error: dist/ directory not found..."; exit 1; fi
	@echo "Packages in dist/:"
	@ls -lh dist/
	@echo "Checking package integrity..."
	@twine check dist/*
	@echo "✅ Distribution packages verified"
```

⚠️ **IMPROVEMENT OPPORTUNITY**: `verify-dist` target exists but not integrated into release workflow

---

## Gap Analysis

### Critical Gaps (Should Fix)

1. **Twine Not in `pyproject.toml` Dev Dependencies**
   - **Impact**: Users running `pip install -e ".[dev]"` won't get Twine
   - **Risk**: Publishing will fail for new contributors
   - **Fix**: Add `twine>=5.0.0` to dev dependencies

2. **Build Module Not in `pyproject.toml` Dev Dependencies**
   - **Impact**: `python -m build` will fail without manual installation
   - **Risk**: Build failures for new contributors
   - **Fix**: Add `build>=1.0.0` to dev dependencies

3. **No `twine check` Validation in Release Workflow**
   - **Impact**: Malformed packages could be uploaded to PyPI
   - **Risk**: Publishing broken packages that can't be deleted
   - **Fix**: Add `verify-dist` to `publish-prod` dependencies

### Documentation Gaps (Nice to Have)

4. **TestPyPI Not Configured in `~/.pypirc`**
   - **Impact**: `make publish-test` may fail without TestPyPI credentials
   - **Risk**: Can't test publishing before production
   - **Fix**: Add TestPyPI section to `~/.pypirc` example in docs

5. **`.env.local` Template Missing PyPI Variables**
   - **Impact**: Users expecting `.env.local` to work won't have Twine credentials
   - **Risk**: Confusion about authentication methods
   - **Fix**: Add `.env.local.example` with TWINE_* variables

---

## Migration Plan (Actually: Standardization Plan)

### Phase 1: Add Twine to Dependencies ✅ RECOMMENDED

**File**: `pyproject.toml`

**Current** (lines 71-84):
```toml
dev = [
    "pytest>=7.4.0",
    ...
    "bump2version>=1.0.1",
]
```

**Proposed Change**:
```toml
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "pytest-timeout>=2.2.0",
    "pytest-mock>=3.12.0",
    "pytest-xdist>=3.0.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.5.0",
    "tox>=4.11.0",
    "pre-commit>=3.5.0",
    "bump2version>=1.0.1",
    "build>=1.0.0",        # NEW: PEP 517 build tool
    "twine>=5.0.0",        # NEW: PyPI publishing tool
]
```

**Rationale**:
- Enforces Twine installation via `pip install -e ".[dev]"`
- Documents minimum required Twine version (5.0.0 = current stable)
- Adds `build` module for consistency
- Aligns with RELEASE.md documentation

**Impact**: LOW RISK
- Additive change only
- Existing installations unaffected
- New contributors get correct tools automatically

---

### Phase 2: Add Dist Validation to Workflow ✅ RECOMMENDED

**File**: `.makefiles/release.mk`

**Current** (line 67):
```makefile
publish-prod: check-release format lint test test-e2e build
```

**Proposed Change**:
```makefile
publish-prod: check-release format lint test test-e2e build verify-dist
```

**Rationale**:
- Validates packages before upload (catches metadata issues)
- `verify-dist` target already exists but unused
- Adds minimal overhead (~1-2 seconds)
- Prevents publishing broken packages to PyPI

**Impact**: LOW RISK
- Existing `verify-dist` target already implemented
- No behavioral changes, just adds safety check
- May catch edge cases before they reach PyPI

**Same change for `publish-test`** (line 54):
```makefile
publish-test: check-release format lint test test-e2e build verify-dist
```

---

### Phase 3: Update Documentation ✅ RECOMMENDED

**File**: `docs/RELEASE.md`

**Section to Update**: Prerequisites (lines 56-64)

**Current**:
```markdown
2. **Build Tools**
   ```bash
   pip install build twine
   ```

3. **Development Environment**
   ```bash
   make install-dev  # Installs all dev dependencies
   ```
```

**Proposed Change**:
```markdown
2. **Build Tools**

   Build and publishing tools are included in dev dependencies:
   ```bash
   pip install -e ".[dev]"  # Includes build, twine, and all dev tools
   ```

   Or install separately:
   ```bash
   pip install build twine
   ```

3. **Development Environment**
   ```bash
   make install-dev  # Installs all dev dependencies (includes build + twine)
   ```
```

**Rationale**:
- Clarifies that dev dependencies now include Twine
- Maintains backward compatibility with manual installation
- Reduces confusion about installation methods

**Impact**: DOCUMENTATION ONLY
- No code changes
- Improves developer onboarding
- Aligns docs with implementation

---

### Phase 4: Add TestPyPI Configuration Guide ✅ OPTIONAL

**File**: `docs/RELEASE.md`

**Section to Update**: PyPI Credentials Setup (lines 89-107)

**Current `~/.pypirc` Example**:
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

**Current User's `~/.pypirc` (MISSING TestPyPI)**:
```ini
[distutils]
index-servers =
    pypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-AgEIcHlwaS5vcmcC...
```

**Proposed Documentation Addition**:

```markdown
### Setting Up TestPyPI (Recommended for Testing)

Before publishing to production PyPI, test your package on TestPyPI:

1. **Create TestPyPI Account**
   - Register at [test.pypi.org](https://test.pypi.org/account/register/)
   - Enable 2FA for security
   - Generate API token at [test.pypi.org/manage/account/token/](https://test.pypi.org/manage/account/token/)

2. **Update `~/.pypirc`**
   ```ini
   [distutils]
   index-servers =
       pypi
       testpypi

   [pypi]
   repository = https://upload.pypi.org/legacy/
   username = __token__
   password = pypi-AgEIcHlwaS5vcmcC...  # Production PyPI token

   [testpypi]
   repository = https://test.pypi.org/legacy/
   username = __token__
   password = pypi-AgEIcHlwaS5vcmcC...  # TestPyPI token (different from production)
   ```

3. **Test Publishing**
   ```bash
   make publish-test  # Publishes to TestPyPI
   ```

4. **Verify on TestPyPI**
   ```bash
   open https://test.pypi.org/project/mcp-ticketer/
   ```

**Note**: TestPyPI has a separate user database and API tokens from production PyPI.
You must create a separate account and generate a separate API token.
```

**Rationale**:
- Current user setup lacks TestPyPI configuration
- `make publish-test` may fail without TestPyPI credentials
- TestPyPI testing is a best practice before production releases

**Impact**: DOCUMENTATION ONLY
- Improves testing workflow
- Reduces risk of production publishing issues
- Optional: users can skip TestPyPI if confident

---

### Phase 5: Add `.env.local.example` Template ✅ OPTIONAL

**File**: `.env.local.example` (NEW)

**Content**:
```bash
# mcp-ticketer Local Environment Configuration
# Copy to .env.local and fill in your values
# WARNING: Never commit .env.local to version control!

# Linear Adapter Configuration
LINEAR_API_KEY=your_linear_api_key_here
LINEAR_TEAM_KEY=your_team_key_here

# PyPI Publishing (Alternative to ~/.pypirc)
# Uncomment and set these to use .env.local for PyPI credentials
# TWINE_USERNAME=__token__
# TWINE_PASSWORD=pypi-AgEIcHlwaS5vcmcC...  # Your PyPI API token

# TestPyPI Publishing (Optional)
# TWINE_TEST_USERNAME=__token__
# TWINE_TEST_PASSWORD=pypi-AgEIcHlwaS5vcmcC...  # Your TestPyPI API token
```

**Update `.gitignore`**:
```
.env.local
```

**Rationale**:
- Provides template for environment-based configuration
- Documents both Linear and PyPI environment variables
- Prevents accidental credential commits

**Impact**: LOW RISK
- New file, doesn't affect existing workflow
- Users can continue using `~/.pypirc` if preferred
- Improves security documentation

---

## Twine Configuration Best Practices

### Current Setup Review

**Twine Version**: 6.2.0 (latest stable as of 2025-12)
**Installation Location**: `/Users/masa/.local/bin/twine`
**Authentication Method**: `~/.pypirc` with API tokens
**Upload Targets**: PyPI production only (TestPyPI not configured)

✅ **SECURITY**: Using API tokens (not username/password)
✅ **METHOD**: Using `~/.pypirc` (persistent, secure)
⚠️ **GAP**: TestPyPI not configured

### Recommended Configuration

**Complete `~/.pypirc` Setup**:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-AgEIcHlwaS5vcmcC...  # Production PyPI API token

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgEIcHlwaS5vcmcC...  # TestPyPI API token (different from production)
```

**Key Points**:
- **Two separate tokens required**: PyPI and TestPyPI use different databases
- **Token format**: `pypi-AgEI...` (starts with `pypi-` prefix)
- **Username**: Always `__token__` when using API tokens
- **Repository URLs**: Use `/legacy/` endpoint for Twine compatibility

### Verification Commands

```bash
# Check Twine installation
twine --version
# Expected: twine version 6.2.0 (or higher)

# Validate built packages
twine check dist/*
# Expected: Checking dist/mcp_ticketer-X.Y.Z-py3-none-any.whl: PASSED
#          Checking dist/mcp_ticketer-X.Y.Z.tar.gz: PASSED

# Test upload to TestPyPI (dry run)
twine upload --repository testpypi dist/* --verbose
# Validates credentials and package metadata without uploading

# Production upload to PyPI
twine upload dist/*
# Uploads to production PyPI
```

---

## Testing Strategy

### Pre-Migration Testing (Already Working)

**Current Workflow Test** (v2.0.3 release):
```bash
# 1. Version bump
python scripts/manage_version.py bump patch
# Expected: Version bumped: 2.0.2 → 2.0.3

# 2. Build
python -m build
# Expected: dist/mcp_ticketer-2.0.3-py3-none-any.whl
#          dist/mcp_ticketer-2.0.3.tar.gz

# 3. Upload
twine upload dist/*
# Expected: Successfully uploaded to PyPI
```

✅ **VERIFIED**: v2.0.3 published successfully on 2025-12-03

### Post-Standardization Testing

**After Adding Twine to `pyproject.toml`**:

```bash
# 1. Clean environment test
python -m venv test-venv
source test-venv/bin/activate

# 2. Install dev dependencies
pip install -e ".[dev]"

# 3. Verify Twine installed
which twine
twine --version
# Expected: twine version 5.0.0 or higher

# 4. Verify build module installed
python -m build --version
# Expected: build X.Y.Z

# 5. Test build
make clean
make build
# Expected: dist/mcp_ticketer-X.Y.Z-py3-none-any.whl
#          dist/mcp_ticketer-X.Y.Z.tar.gz

# 6. Test verification
make verify-dist
# Expected: ✅ Distribution packages verified

# 7. Deactivate
deactivate
```

**After Adding `verify-dist` to Workflow**:

```bash
# Test integrated workflow
make release-patch
# Should include verify-dist step before upload
# Expected output:
#   Verifying distribution packages...
#   Checking package integrity...
#   twine check dist/*
#   ✅ Distribution packages verified
#   Publishing to PyPI...
```

### TestPyPI Testing (After Configuration)

```bash
# 1. Configure TestPyPI in ~/.pypirc (see Phase 4)

# 2. Test upload to TestPyPI
make publish-test
# Expected: Package uploaded to https://test.pypi.org/project/mcp-ticketer/

# 3. Verify TestPyPI package
open https://test.pypi.org/project/mcp-ticketer/

# 4. Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ mcp-ticketer
mcp-ticketer --version
# Expected: mcp-ticketer version X.Y.Z

# 5. If successful, publish to production
make publish-prod
```

---

## Rollback Plan

**No Rollback Required**: Current setup already uses Twine successfully.

**If Standardization Changes Cause Issues**:

1. **Revert `pyproject.toml` Changes**:
   ```bash
   git checkout HEAD -- pyproject.toml
   pip install -e ".[dev]"
   ```

2. **Manually Install Twine** (fallback to current method):
   ```bash
   pip install twine
   ```

3. **Continue Using Current Workflow**:
   ```bash
   make release-patch  # Still works with system-installed Twine
   ```

**Low Risk**: Changes are additive only. Removing Twine from `pyproject.toml` doesn't break anything if it's still installed system-wide.

---

## Success Criteria

### Immediate Success (Already Met)

- ✅ Twine is installed and working
- ✅ Recent releases published successfully via Twine
- ✅ Authentication configured securely with API tokens
- ✅ Build system uses `python -m build` (PEP 517 compliant)
- ✅ Quality gates run before publishing

### Post-Standardization Success Criteria

1. **Dependency Management**:
   - [ ] Twine listed in `pyproject.toml` dev dependencies
   - [ ] `pip install -e ".[dev]"` installs Twine automatically
   - [ ] Build module listed in `pyproject.toml` dev dependencies

2. **Release Workflow**:
   - [ ] `make verify-dist` runs before every publish
   - [ ] `twine check dist/*` validates packages before upload
   - [ ] Zero manual dependency installation required

3. **Documentation**:
   - [ ] `docs/RELEASE.md` updated to reflect Twine in dev deps
   - [ ] TestPyPI configuration guide added
   - [ ] `.env.local.example` template created

4. **Testing**:
   - [ ] Clean environment installation test passes
   - [ ] Release workflow includes verification step
   - [ ] TestPyPI testing workflow documented

---

## Conclusion

**Current State**: mcp-ticketer already uses Twine successfully. No migration is needed.

**Recommendation**: Standardize the setup by adding Twine to `pyproject.toml` dev dependencies and integrating the existing `verify-dist` target into the release workflow. This eliminates dependency installation inconsistencies and adds package validation before PyPI uploads.

**Impact**: LOW RISK, HIGH VALUE
- Additive changes only
- Improves developer experience
- Adds safety checks to publishing workflow
- No behavioral changes to existing release process

**Priority**:
1. **CRITICAL**: Add Twine and build to `pyproject.toml` (5 min, high value)
2. **HIGH**: Add `verify-dist` to release workflow (2 min, safety improvement)
3. **MEDIUM**: Update RELEASE.md documentation (10 min, clarity)
4. **LOW**: Add TestPyPI configuration guide (15 min, optional improvement)
5. **LOW**: Add `.env.local.example` template (5 min, optional security improvement)

**Estimated Total Work**: 37 minutes for full standardization

---

## Implementation Files

### Files to Modify

1. **`pyproject.toml`** (lines 71-84)
   - Add `build>=1.0.0` to dev dependencies
   - Add `twine>=5.0.0` to dev dependencies

2. **`.makefiles/release.mk`** (lines 54, 67)
   - Add `verify-dist` to `publish-test` dependencies
   - Add `verify-dist` to `publish-prod` dependencies

3. **`docs/RELEASE.md`** (lines 56-107)
   - Update Prerequisites section to mention Twine in dev deps
   - Expand TestPyPI configuration guide

### Files to Create (Optional)

4. **`.env.local.example`** (NEW)
   - Template for environment variables
   - Include TWINE_* variables
   - Document Linear and PyPI configuration

### Files to Update (Optional)

5. **`.gitignore`**
   - Add `.env.local` if not already present
   - Ensure `.env.local.example` is NOT ignored

---

## Code Snippets for Implementation

### 1. `pyproject.toml` Patch

**Location**: Lines 71-84

**Before**:
```toml
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "pytest-timeout>=2.2.0",
    "pytest-mock>=3.12.0",
    "pytest-xdist>=3.0.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.5.0",
    "tox>=4.11.0",
    "pre-commit>=3.5.0",
    "bump2version>=1.0.1",
]
```

**After**:
```toml
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "pytest-timeout>=2.2.0",
    "pytest-mock>=3.12.0",
    "pytest-xdist>=3.0.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.5.0",
    "tox>=4.11.0",
    "pre-commit>=3.5.0",
    "bump2version>=1.0.1",
    "build>=1.0.0",
    "twine>=5.0.0",
]
```

---

### 2. `.makefiles/release.mk` Patch

**Location**: Line 54

**Before**:
```makefile
publish-test: check-release format lint test test-e2e build
```

**After**:
```makefile
publish-test: check-release format lint test test-e2e build verify-dist
```

**Location**: Line 67

**Before**:
```makefile
publish-prod: check-release format lint test test-e2e build
```

**After**:
```makefile
publish-prod: check-release format lint test test-e2e build verify-dist
```

---

### 3. `docs/RELEASE.md` Documentation Patch

**Location**: Lines 56-64 (Prerequisites section)

**Before**:
```markdown
2. **Build Tools**
   ```bash
   pip install build twine
   ```

3. **Development Environment**
   ```bash
   make install-dev  # Installs all dev dependencies
   ```
```

**After**:
```markdown
2. **Build Tools**

   Build and publishing tools are included in dev dependencies:
   ```bash
   pip install -e ".[dev]"  # Includes build, twine, and all dev tools
   ```

   Or install separately:
   ```bash
   pip install build twine
   ```

3. **Development Environment**
   ```bash
   make install-dev  # Installs all dev dependencies (includes build + twine)
   ```
```

---

### 4. `.env.local.example` Template (NEW FILE)

**File**: `.env.local.example`

**Content**:
```bash
# mcp-ticketer Local Environment Configuration
# Copy to .env.local and fill in your values
# WARNING: Never commit .env.local to version control!

# Linear Adapter Configuration
LINEAR_API_KEY=your_linear_api_key_here
LINEAR_TEAM_KEY=your_team_key_here

# PyPI Publishing (Alternative to ~/.pypirc)
# Uncomment and set these to use .env.local for PyPI credentials
# TWINE_USERNAME=__token__
# TWINE_PASSWORD=pypi-AgEIcHlwaS5vcmcC...  # Your PyPI API token

# TestPyPI Publishing (Optional)
# Uncomment to enable TestPyPI publishing via .env.local
# TWINE_TEST_USERNAME=__token__
# TWINE_TEST_PASSWORD=pypi-AgEIcHlwaS5vcmcC...  # Your TestPyPI API token
```

---

## Related Issues and Context

### Recent Releases Using Twine

- **v2.0.3** (2025-12-03): Published successfully via Twine
  - Upload confirmed: https://pypi.org/project/mcp-ticketer/2.0.3/
  - Verification: `pipx upgrade mcp-ticketer` worked immediately
  - Zero issues with Twine upload process

### Historical Context

- **Build System**: Uses `python -m build` (PEP 517 compliant)
- **Twine Adoption**: Already in use, but not documented in dependencies
- **Quality Gates**: Strong pre-publish validation (format, lint, test, e2e)
- **Authentication**: Secure API token-based authentication via `~/.pypirc`

### Project Information

- **Primary Issue Tracker**: https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267/issues
- **GitHub Repository**: https://github.com/bobmatnyc/mcp-ticketer
- **PyPI Package**: https://pypi.org/project/mcp-ticketer/
- **Current Version**: 2.0.3
- **Python Support**: 3.10, 3.11, 3.12, 3.13

---

## Appendix: Publishing Workflow Comparison

### Current Workflow (Already Using Twine)

```
User runs: make release-patch
    │
    ├─ version-bump-patch
    │   └─ scripts/manage_version.py bump patch --git-commit --git-tag
    │
    ├─ build (via publish-prod dependency)
    │   ├─ clean-build
    │   ├─ python -m build
    │   └─ scripts/manage_version.py track-build
    │
    └─ publish-prod
        ├─ check-release
        ├─ format (black, ruff format)
        ├─ lint (ruff check, mypy)
        ├─ test (pytest)
        ├─ test-e2e (end-to-end tests)
        ├─ build (builds dist/)
        └─ twine upload dist/*  # ← ALREADY USING TWINE
```

### Proposed Workflow (With Verification)

```
User runs: make release-patch
    │
    ├─ version-bump-patch
    │   └─ scripts/manage_version.py bump patch --git-commit --git-tag
    │
    ├─ build (via publish-prod dependency)
    │   ├─ clean-build
    │   ├─ python -m build
    │   └─ scripts/manage_version.py track-build
    │
    └─ publish-prod
        ├─ check-release
        ├─ format (black, ruff format)
        ├─ lint (ruff check, mypy)
        ├─ test (pytest)
        ├─ test-e2e (end-to-end tests)
        ├─ build (builds dist/)
        ├─ verify-dist  # ← NEW: Validates packages before upload
        │   └─ twine check dist/*
        └─ twine upload dist/*
```

**Change**: Adds `verify-dist` step between `build` and `twine upload` to catch package issues before PyPI upload.

---

## Memory Update Recommendations

**For Project Memory** (KuzuMemory):

1. **Publishing Method**: mcp-ticketer uses Twine for PyPI uploads (already operational)
2. **Authentication**: `~/.pypirc` with API tokens (production PyPI configured)
3. **Build System**: `python -m build` with setuptools backend
4. **Quality Gates**: Strong pre-publish validation (format, lint, test, e2e)
5. **Gap**: Twine not in `pyproject.toml`, should be added for consistency
6. **Improvement**: Add `verify-dist` to release workflow for package validation

**For Engineer Handoff**:

```json
{
  "memory-update": {
    "Publishing Infrastructure": [
      "Twine v6.2.0 already deployed and working for PyPI uploads",
      "Authentication via ~/.pypirc with API tokens (secure)",
      "Build system: python -m build (PEP 517 compliant)",
      "Release workflow: make release-{patch|minor|major}"
    ],
    "Identified Gaps": [
      "Twine not in pyproject.toml dev dependencies (should add twine>=5.0.0)",
      "Build module not in pyproject.toml dev dependencies (should add build>=1.0.0)",
      "verify-dist target exists but not integrated into publish workflow",
      "TestPyPI not configured in ~/.pypirc (optional improvement)"
    ],
    "Recommendations": [
      "Add twine>=5.0.0 and build>=1.0.0 to pyproject.toml [project.optional-dependencies.dev]",
      "Add verify-dist to publish-test and publish-prod dependencies in .makefiles/release.mk",
      "Update docs/RELEASE.md to reflect Twine in dev dependencies",
      "Optionally add TestPyPI configuration guide and .env.local.example template"
    ]
  }
}
```

---

**Research Complete**: 2025-12-03
**Researcher**: Claude Code Research Agent
**Status**: ✅ Analysis Complete, Ready for Implementation
**Risk Level**: LOW (additive changes only)
**Estimated Implementation Time**: 37 minutes
