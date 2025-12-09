#!/usr/bin/env bash
# Full release workflow for mcp-ticketer
# Orchestrates: version bump → quality gates → build → PyPI → GitHub → Homebrew
#
# Usage: ./scripts/release_full.sh [patch|minor|major] [--dry-run]
#
# Arguments:
#   bump_type  - Version bump type: patch, minor, or major
#   --dry-run  - Preview what would happen without making changes
#
# Examples:
#   ./scripts/release_full.sh patch              # Patch release (X.Y.Z+1)
#   ./scripts/release_full.sh minor              # Minor release (X.Y+1.0)
#   ./scripts/release_full.sh major              # Major release (X+1.0.0)
#   ./scripts/release_full.sh patch --dry-run    # Preview patch release

set -euo pipefail

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}[STEP $1/$2]${NC} $3"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

log_success() {
    echo ""
    echo -e "${GREEN}✅ $1${NC}"
    echo ""
}

log_header() {
    echo ""
    echo -e "${MAGENTA}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║${NC}  $1"
    echo -e "${MAGENTA}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Parse arguments
BUMP_TYPE=""
DRY_RUN=false

# Handle --help flag
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: $0 [patch|minor|major] [--dry-run]"
    echo ""
    echo "Full release workflow for mcp-ticketer"
    echo "Orchestrates: version bump → quality gates → build → PyPI → GitHub → Homebrew"
    echo ""
    echo "Arguments:"
    echo "  bump_type     Version bump type: patch, minor, or major (required)"
    echo "                - patch: Bug fixes (X.Y.Z+1)"
    echo "                - minor: New features (X.Y+1.0)"
    echo "                - major: Breaking changes (X+1.0.0)"
    echo ""
    echo "Options:"
    echo "  --dry-run     Preview what would happen without making changes"
    echo "  -h, --help    Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 patch              # Patch release (X.Y.Z+1)"
    echo "  $0 minor              # Minor release (X.Y+1.0)"
    echo "  $0 major              # Major release (X+1.0.0)"
    echo "  $0 patch --dry-run    # Preview patch release"
    echo ""
    echo "Release Steps:"
    echo "  1. Check git working directory is clean"
    echo "  2. Run quality gates (make pre-publish)"
    echo "  3. Bump version based on bump_type"
    echo "  4. Commit and tag version"
    echo "  5. Push to origin (main + tags)"
    echo "  6. Build package (make build)"
    echo "  7. Publish to PyPI (make release-pypi)"
    echo "  8. Create GitHub release with notes"
    echo "  9. Update Homebrew tap formula"
    echo "  10. Verify release on PyPI"
    echo ""
    echo "Prerequisites:"
    echo "  - Git working directory must be clean"
    echo "  - CHANGELOG.md should be updated"
    echo "  - PyPI credentials configured (.env.local or ~/.pypirc)"
    echo "  - GitHub CLI (gh) authenticated"
    exit 0
fi

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        patch|minor|major)
            BUMP_TYPE="$1"
            shift
            ;;
        *)
            log_error "Unknown argument: $1"
            echo "Usage: $0 [patch|minor|major] [--dry-run]"
            exit 1
            ;;
    esac
done

# Validate bump type
if [ -z "$BUMP_TYPE" ]; then
    log_error "Bump type required"
    echo "Usage: $0 [patch|minor|major] [--dry-run]"
    echo ""
    echo "Examples:"
    echo "  $0 patch        # Bug fixes (X.Y.Z+1)"
    echo "  $0 minor        # New features (X.Y+1.0)"
    echo "  $0 major        # Breaking changes (X+1.0.0)"
    exit 1
fi

# Show header
log_header "mcp-ticketer Full Release Workflow ($BUMP_TYPE)"

if [ "$DRY_RUN" = true ]; then
    log_warn "DRY RUN MODE - No changes will be made"
fi

# Get current version
CURRENT_VERSION=$(python3 scripts/manage_version.py get-version)
log_info "Current version: ${CURRENT_VERSION}"

# Calculate new version (simulation)
case "$BUMP_TYPE" in
    patch)
        # Increment patch: X.Y.Z → X.Y.Z+1
        NEW_VERSION=$(echo "$CURRENT_VERSION" | awk -F. '{print $1"."$2"."$3+1}')
        ;;
    minor)
        # Increment minor: X.Y.Z → X.Y+1.0
        NEW_VERSION=$(echo "$CURRENT_VERSION" | awk -F. '{print $1"."$2+1".0"}')
        ;;
    major)
        # Increment major: X.Y.Z → X+1.0.0
        NEW_VERSION=$(echo "$CURRENT_VERSION" | awk -F. '{print $1+1".0.0"}')
        ;;
esac

log_info "New version will be: ${NEW_VERSION}"

# Show release plan
echo ""
echo "Release Plan:"
echo "  1. ✅ Check git is clean"
echo "  2. 🔧 Run quality gates (make pre-publish)"
echo "  3. 📦 Bump version (${CURRENT_VERSION} → ${NEW_VERSION})"
echo "  4. 💾 Commit and tag version"
echo "  5. 🚀 Push to origin"
echo "  6. 🏗️  Build package (make build)"
echo "  7. 📤 Publish to PyPI (make release-pypi)"
echo "  8. 🎉 Create GitHub release"
echo "  9. 🍺 Update Homebrew tap"
echo "  10. ✅ Verify release"
echo ""

if [ "$DRY_RUN" = true ]; then
    log_info "Dry run complete - no changes made"
    exit 0
fi

# Confirm with user
read -p "Proceed with release? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warn "Release cancelled by user"
    exit 0
fi

TOTAL_STEPS=10
CURRENT_STEP=0

# Step 1: Check git is clean
CURRENT_STEP=$((CURRENT_STEP + 1))
log_step $CURRENT_STEP $TOTAL_STEPS "Check git working directory"
if ! git diff-index --quiet HEAD --; then
    log_error "Git working directory has uncommitted changes"
    echo "Commit or stash changes before releasing"
    git status
    exit 1
fi
log_success "Git working directory is clean"

# Step 2: Run quality gates
CURRENT_STEP=$((CURRENT_STEP + 1))
log_step $CURRENT_STEP $TOTAL_STEPS "Run quality gates (format, lint, test)"
if ! make pre-publish; then
    log_error "Quality gates failed"
    echo "Fix issues before releasing"
    exit 1
fi
log_success "Quality gates passed"

# Step 3: Bump version
CURRENT_STEP=$((CURRENT_STEP + 1))
log_step $CURRENT_STEP $TOTAL_STEPS "Bump version ($BUMP_TYPE: $CURRENT_VERSION → $NEW_VERSION)"
if ! python3 scripts/manage_version.py bump "$BUMP_TYPE"; then
    log_error "Version bump failed"
    exit 1
fi

# Verify version was updated
BUMPED_VERSION=$(python3 scripts/manage_version.py get-version)
if [ "$BUMPED_VERSION" != "$NEW_VERSION" ]; then
    log_error "Version mismatch after bump: expected ${NEW_VERSION}, got ${BUMPED_VERSION}"
    exit 1
fi
log_success "Version bumped to ${NEW_VERSION}"

# Step 4: Commit and tag version
CURRENT_STEP=$((CURRENT_STEP + 1))
log_step $CURRENT_STEP $TOTAL_STEPS "Commit and tag version"

# Create git commit
git add src/mcp_ticketer/__version__.py
if git diff --cached --quiet; then
    log_warn "No changes to commit (version file may be unchanged)"
else
    git commit -m "chore: bump version to ${NEW_VERSION}"
    log_info "Commit created"
fi

# Create git tag
TAG="v${NEW_VERSION}"
if git rev-parse "$TAG" >/dev/null 2>&1; then
    log_warn "Tag ${TAG} already exists, skipping tag creation"
else
    git tag -a "$TAG" -m "Release ${TAG}"
    log_info "Tag created: ${TAG}"
fi
log_success "Version committed and tagged"

# Step 5: Push to origin
CURRENT_STEP=$((CURRENT_STEP + 1))
log_step $CURRENT_STEP $TOTAL_STEPS "Push to origin (main + tags)"
if ! git push origin main; then
    log_error "Failed to push main branch"
    exit 1
fi
if ! git push origin "$TAG"; then
    log_error "Failed to push tag ${TAG}"
    exit 1
fi
log_success "Pushed to origin"

# Step 6: Build package
CURRENT_STEP=$((CURRENT_STEP + 1))
log_step $CURRENT_STEP $TOTAL_STEPS "Build package"
if ! make build; then
    log_error "Build failed"
    exit 1
fi
log_success "Package built successfully"

# Step 7: Publish to PyPI
CURRENT_STEP=$((CURRENT_STEP + 1))
log_step $CURRENT_STEP $TOTAL_STEPS "Publish to PyPI"
log_info "Publishing to PyPI..."

# Use make target which handles credentials from .env.local or ~/.pypirc
if ! make release-pypi; then
    log_error "PyPI publish failed"
    echo ""
    echo "Manual publish command:"
    echo "  twine upload dist/*"
    exit 1
fi
log_success "Published to PyPI"

# Step 8: Create GitHub release
CURRENT_STEP=$((CURRENT_STEP + 1))
log_step $CURRENT_STEP $TOTAL_STEPS "Create GitHub release"
if ! bash scripts/create_github_release.sh "$TAG"; then
    log_error "GitHub release creation failed"
    log_warn "Continuing anyway (can be created manually later)"
else
    log_success "GitHub release created"
fi

# Step 9: Update Homebrew tap
CURRENT_STEP=$((CURRENT_STEP + 1))
log_step $CURRENT_STEP $TOTAL_STEPS "Update Homebrew tap"
log_info "Updating Homebrew formula..."

# Wait a bit for PyPI to propagate
log_info "Waiting 10 seconds for PyPI to propagate..."
sleep 10

if ! bash scripts/update_homebrew_tap.sh "$NEW_VERSION" --push; then
    log_error "Homebrew tap update failed"
    log_warn "Continuing anyway (can be updated manually later)"
    echo ""
    echo "Manual update command:"
    echo "  bash scripts/update_homebrew_tap.sh ${NEW_VERSION} --push"
else
    log_success "Homebrew tap updated"
fi

# Step 10: Verify release
CURRENT_STEP=$((CURRENT_STEP + 1))
log_step $CURRENT_STEP $TOTAL_STEPS "Verify release"
log_info "Verifying PyPI package..."

# Check PyPI
PYPI_URL="https://pypi.org/project/mcp-ticketer/${NEW_VERSION}/"
log_info "PyPI URL: ${PYPI_URL}"

# Brief pause for PyPI to fully update
sleep 5

# Try to verify package is installable (in a subshell to not affect current environment)
log_info "Testing package installation..."
if (python3 -m pip index versions mcp-ticketer 2>&1 | grep -q "$NEW_VERSION"); then
    log_success "Package verified on PyPI"
else
    log_warn "Could not verify package on PyPI (may need a few minutes to propagate)"
fi

# Final summary
log_header "Release Complete! 🎉"

echo "Version: ${NEW_VERSION}"
echo "Tag: ${TAG}"
echo ""
echo "URLs:"
echo "  PyPI:    ${PYPI_URL}"
echo "  GitHub:  https://github.com/mcp-ticketer/mcp-ticketer/releases/tag/${TAG}"
echo ""
echo "Next steps:"
echo "  1. ✅ Verify package installation:"
echo "     pip install --upgrade mcp-ticketer==${NEW_VERSION}"
echo "     mcp-ticketer --version"
echo ""
echo "  2. ✅ Test Homebrew installation:"
echo "     brew upgrade mcp-ticketer"
echo "     mcp-ticketer --version"
echo ""
echo "  3. ✅ Announce release (optional):"
echo "     - Social media (Twitter/X, Discord)"
echo "     - Blog post for major releases"
echo "     - Documentation updates"
echo ""

log_success "Full release workflow completed successfully!"
