#!/usr/bin/env bash
# Create GitHub release with automated release notes and artifact uploads
# Usage: ./scripts/create_github_release.sh [version]
#
# Example: ./scripts/create_github_release.sh v2.2.11
#          ./scripts/create_github_release.sh        (uses current version)

set -euo pipefail

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${PROJECT_ROOT}/dist"
CHANGELOG="${PROJECT_ROOT}/CHANGELOG.md"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Handle --help flag
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: $0 [version] [options]"
    echo ""
    echo "Create GitHub release with automated release notes and artifact uploads"
    echo ""
    echo "Arguments:"
    echo "  version       Version tag (e.g., v2.2.11). Optional - uses current version if omitted"
    echo ""
    echo "Options:"
    echo "  -h, --help    Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 v2.2.11          # Create release for specific version"
    echo "  $0                  # Create release for current version"
    echo ""
    echo "Prerequisites:"
    echo "  - GitHub CLI (gh) must be installed and authenticated"
    echo "  - Git tag must exist for the version"
    echo "  - Distribution packages must be built (run 'make build' first)"
    echo ""
    echo "The script will:"
    echo "  1. Validate version format and git tag"
    echo "  2. Generate release notes from CHANGELOG.md and git commits"
    echo "  3. Create GitHub release with distribution files attached"
    echo "  4. Display release URL for verification"
    exit 0
fi

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    log_error "GitHub CLI (gh) is not installed"
    echo "Install with: brew install gh"
    echo "Or see: https://cli.github.com/manual/installation"
    exit 1
fi

# Check if user is authenticated
if ! gh auth status &> /dev/null; then
    log_error "Not authenticated with GitHub CLI"
    echo "Run: gh auth login"
    exit 1
fi

# Get version from argument or current version
if [ $# -eq 0 ]; then
    log_info "No version specified, detecting current version..."
    VERSION=$(python3 "${PROJECT_ROOT}/scripts/manage_version.py" get-version)
    TAG="v${VERSION}"
    log_info "Detected version: ${VERSION}"
else
    TAG="$1"
    # Remove 'v' prefix if present for version string
    VERSION="${TAG#v}"
fi

log_info "Creating GitHub release for ${TAG}"

# Validate version format
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    log_error "Invalid version format: ${VERSION}"
    echo "Version must be in format X.Y.Z (e.g., 2.2.11)"
    exit 1
fi

# Check if tag exists
if ! git rev-parse "$TAG" &> /dev/null; then
    log_error "Git tag ${TAG} does not exist"
    echo "Create tag first with: git tag -a ${TAG} -m \"Release ${TAG}\""
    exit 1
fi

# Check if dist directory exists
if [ ! -d "$DIST_DIR" ]; then
    log_error "Distribution directory not found: ${DIST_DIR}"
    echo "Build packages first with: make build"
    exit 1
fi

# Check if dist files exist
WHEEL_FILE=$(find "$DIST_DIR" -name "mcp_ticketer-${VERSION}-*.whl" | head -n 1)
SDIST_FILE=$(find "$DIST_DIR" -name "mcp-ticketer-${VERSION}.tar.gz" | head -n 1)

if [ -z "$WHEEL_FILE" ]; then
    log_warn "Wheel file not found for version ${VERSION}"
fi

if [ -z "$SDIST_FILE" ]; then
    log_warn "Source distribution not found for version ${VERSION}"
fi

# Generate release notes from git commits since last tag
log_step "Generating release notes from git history..."

# Find previous tag
PREV_TAG=$(git describe --tags --abbrev=0 "${TAG}^" 2>/dev/null || echo "")

if [ -z "$PREV_TAG" ]; then
    log_warn "No previous tag found, using all commits"
    COMMIT_RANGE="${TAG}"
else
    log_info "Previous tag: ${PREV_TAG}"
    COMMIT_RANGE="${PREV_TAG}..${TAG}"
fi

# Generate commit summary
COMMITS=$(git log "${COMMIT_RANGE}" --pretty=format:"- %s (%h)" --no-merges)

# Try to extract changelog section for this version
CHANGELOG_SECTION=""
if [ -f "$CHANGELOG" ]; then
    log_info "Extracting changelog section for ${VERSION}..."

    # Extract section between this version and next version header
    CHANGELOG_SECTION=$(awk -v version="$VERSION" '
        /^## \[/ {
            if (found) exit;
            if ($0 ~ "\\[" version "\\]") {
                found=1;
                next;
            }
        }
        found { print }
    ' "$CHANGELOG" | sed '/^$/d' | head -n 50)

    if [ -n "$CHANGELOG_SECTION" ]; then
        log_info "Found changelog section (${#CHANGELOG_SECTION} chars)"
    else
        log_warn "Could not extract changelog section for version ${VERSION}"
    fi
fi

# Build release notes
RELEASE_NOTES_FILE=$(mktemp)
cat > "$RELEASE_NOTES_FILE" <<EOF
## What's New in v${VERSION}

EOF

if [ -n "$CHANGELOG_SECTION" ]; then
    echo "$CHANGELOG_SECTION" >> "$RELEASE_NOTES_FILE"
    echo "" >> "$RELEASE_NOTES_FILE"
else
    cat >> "$RELEASE_NOTES_FILE" <<EOF
### Changes

$COMMITS

EOF
fi

cat >> "$RELEASE_NOTES_FILE" <<EOF

## Installation

\`\`\`bash
pip install --upgrade mcp-ticketer==${VERSION}
\`\`\`

## Verification

\`\`\`bash
mcp-ticketer --version  # Should show ${VERSION}
\`\`\`

## Distribution Files

EOF

if [ -n "$WHEEL_FILE" ]; then
    echo "- **Wheel**: $(basename "$WHEEL_FILE")" >> "$RELEASE_NOTES_FILE"
fi

if [ -n "$SDIST_FILE" ]; then
    echo "- **Source**: $(basename "$SDIST_FILE")" >> "$RELEASE_NOTES_FILE"
fi

cat >> "$RELEASE_NOTES_FILE" <<EOF

## Resources

- **PyPI**: https://pypi.org/project/mcp-ticketer/${VERSION}/
- **Full Changelog**: https://github.com/mcp-ticketer/mcp-ticketer/blob/main/CHANGELOG.md
- **Documentation**: https://mcp-ticketer.readthedocs.io

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF

# Preview release notes
log_step "Release notes preview:"
echo ""
cat "$RELEASE_NOTES_FILE"
echo ""

# Create GitHub release
log_step "Creating GitHub release ${TAG}..."

GH_RELEASE_ARGS=(
    "release" "create" "$TAG"
    "--title" "v${VERSION}"
    "--notes-file" "$RELEASE_NOTES_FILE"
)

# Add distribution files if they exist
if [ -n "$WHEEL_FILE" ]; then
    GH_RELEASE_ARGS+=("$WHEEL_FILE")
fi

if [ -n "$SDIST_FILE" ]; then
    GH_RELEASE_ARGS+=("$SDIST_FILE")
fi

# Execute gh release create
if gh "${GH_RELEASE_ARGS[@]}"; then
    log_info "✅ GitHub release created successfully!"

    # Get release URL
    RELEASE_URL=$(gh release view "$TAG" --json url -q .url)
    echo ""
    echo "Release URL: ${RELEASE_URL}"
    echo ""

    # Cleanup
    rm -f "$RELEASE_NOTES_FILE"

    log_info "Next steps:"
    echo "  1. Verify release at: ${RELEASE_URL}"
    echo "  2. Update Homebrew tap: make homebrew-tap-auto"
    echo "  3. Announce release (social media, Discord, etc.)"

    exit 0
else
    log_error "Failed to create GitHub release"
    log_info "Release notes saved to: ${RELEASE_NOTES_FILE}"
    exit 1
fi
