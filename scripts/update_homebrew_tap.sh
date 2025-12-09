#!/usr/bin/env bash
# Update Homebrew tap formula for mcp-ticketer
# Usage: ./scripts/update_homebrew_tap.sh <version> [--push]
#
# Arguments:
#   version  - Version number (e.g., 2.2.11)
#   --push   - Automatically push changes to GitHub (optional)
#
# Examples:
#   ./scripts/update_homebrew_tap.sh 2.2.11           # Create commit but don't push
#   ./scripts/update_homebrew_tap.sh 2.2.11 --push    # Create commit and push

set -euo pipefail

# Configuration
TAP_REPO="bobmatnyc/homebrew-tools"
FORMULA_NAME="mcp-ticketer"
PACKAGE_NAME="mcp-ticketer"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Parse arguments
AUTO_PUSH=false
VERSION=""

# Handle --help flag
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: $0 <version> [--push]"
    echo ""
    echo "Update Homebrew tap formula for mcp-ticketer"
    echo ""
    echo "Arguments:"
    echo "  version       Version number in X.Y.Z format (e.g., 2.2.11) (required)"
    echo ""
    echo "Options:"
    echo "  --push        Automatically push changes to GitHub (optional)"
    echo "  -h, --help    Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 2.2.11           # Create commit but don't push"
    echo "  $0 2.2.11 --push    # Create commit and push"
    echo ""
    echo "What this script does:"
    echo "  1. Wait for PyPI to publish the specified version"
    echo "  2. Fetch SHA256 checksum from PyPI"
    echo "  3. Clone or update Homebrew tap repository"
    echo "  4. Update formula with new version and checksum"
    echo "  5. Run formula syntax check"
    echo "  6. Commit changes to tap repository"
    echo "  7. Optionally push to GitHub (with --push flag)"
    echo ""
    echo "Prerequisites:"
    echo "  - Package must be published on PyPI"
    echo "  - Git access to tap repository (${TAP_REPO})"
    echo "  - Homebrew installed (for formula audit)"
    exit 0
fi

while [ $# -gt 0 ]; do
    case "$1" in
        --push)
            AUTO_PUSH=true
            shift
            ;;
        *)
            if [ -z "$VERSION" ]; then
                VERSION="$1"
            else
                log_error "Unexpected argument: $1"
                exit 1
            fi
            shift
            ;;
    esac
done

# Check if version is provided
if [ -z "$VERSION" ]; then
    log_error "Version number required"
    echo "Usage: $0 <version> [--push]"
    echo "Example: $0 2.2.11"
    echo "Example: $0 2.2.11 --push"
    exit 1
fi

log_info "Updating Homebrew tap for version ${VERSION}"
if [ "$AUTO_PUSH" = true ]; then
    log_info "Auto-push enabled - changes will be pushed automatically"
fi

# Validate version format (X.Y.Z)
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    log_error "Invalid version format: ${VERSION}"
    echo "Version must be in format X.Y.Z (e.g., 1.2.10)"
    exit 1
fi

# Wait for PyPI to have the new version available
log_info "Waiting for PyPI to publish version ${VERSION}..."
MAX_RETRIES=10
RETRY_COUNT=0
SLEEP_DURATION=5

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s "https://pypi.org/pypi/${PACKAGE_NAME}/json" | grep -q "\"version\": \"${VERSION}\""; then
        log_info "Version ${VERSION} found on PyPI"
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        log_warn "Version not yet available on PyPI (attempt ${RETRY_COUNT}/${MAX_RETRIES}). Retrying in ${SLEEP_DURATION}s..."
        sleep $SLEEP_DURATION
    else
        log_error "Version ${VERSION} not found on PyPI after ${MAX_RETRIES} attempts"
        exit 1
    fi
done

# Fetch SHA256 from PyPI
log_info "Fetching SHA256 checksum from PyPI..."
PYPI_JSON=$(curl -s "https://pypi.org/pypi/${PACKAGE_NAME}/${VERSION}/json")

# Extract SHA256 for the tar.gz file
SHA256=$(echo "$PYPI_JSON" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for url_info in data['urls']:
    if url_info['packagetype'] == 'sdist' and url_info['filename'].endswith('.tar.gz'):
        print(url_info['digests']['sha256'])
        break
")

if [ -z "$SHA256" ]; then
    log_error "Failed to fetch SHA256 checksum from PyPI"
    exit 1
fi

log_info "SHA256: ${SHA256}"

# Clone or update tap repository
TAP_DIR="${HOME}/.homebrew-taps/${TAP_REPO#*/}"

if [ -d "$TAP_DIR" ]; then
    log_info "Updating existing tap repository..."
    cd "$TAP_DIR"
    git pull origin main
else
    log_info "Cloning tap repository..."
    mkdir -p "$(dirname "$TAP_DIR")"
    git clone "https://github.com/${TAP_REPO}.git" "$TAP_DIR"
    cd "$TAP_DIR"
fi

# Update formula
FORMULA_PATH="Formula/${FORMULA_NAME}.rb"

if [ ! -f "$FORMULA_PATH" ]; then
    log_error "Formula not found: ${FORMULA_PATH}"
    echo "Please create the formula first in the tap repository"
    exit 1
fi

log_info "Updating formula: ${FORMULA_PATH}"

# Update version and SHA256 in formula
# This uses BSD sed (macOS compatible)
sed -i '' "s/url \".*\"/url \"https:\/\/files.pythonhosted.org\/packages\/source\/m\/${PACKAGE_NAME}\/${PACKAGE_NAME}-${VERSION}.tar.gz\"/" "$FORMULA_PATH"
sed -i '' "s/sha256 \".*\"/sha256 \"${SHA256}\"/" "$FORMULA_PATH"
sed -i '' "s/version \".*\"/version \"${VERSION}\"/" "$FORMULA_PATH"

# Show diff
log_info "Changes to formula:"
git diff "$FORMULA_PATH"

# Run formula tests
log_info "Running formula syntax check..."
if ! brew audit --new "$FORMULA_PATH" 2>&1; then
    log_warn "Formula audit warnings detected (non-fatal)"
fi

# Commit changes
log_info "Committing changes..."
git add "$FORMULA_PATH"
git commit -m "feat: update ${FORMULA_NAME} to v${VERSION}

- Updated version to ${VERSION}
- Updated SHA256 checksum
- Source: PyPI release"

# Push if --push flag was provided
if [ "$AUTO_PUSH" = true ]; then
    log_info "Pushing changes to GitHub..."
    if git push origin main; then
        log_info "✅ Changes pushed successfully!"

        # Verify push succeeded
        REMOTE_COMMIT=$(git ls-remote origin main | cut -f1)
        LOCAL_COMMIT=$(git rev-parse HEAD)

        if [ "$REMOTE_COMMIT" = "$LOCAL_COMMIT" ]; then
            log_info "✅ Remote and local commits match"
        else
            log_warn "Remote commit doesn't match local - push may have failed"
            log_info "Remote: ${REMOTE_COMMIT}"
            log_info "Local:  ${LOCAL_COMMIT}"
        fi
    else
        log_error "Failed to push changes to GitHub"
        echo "You can manually push with:"
        echo "  cd ${TAP_DIR}"
        echo "  git push origin main"
        exit 1
    fi
else
    log_info "Changes committed locally (not pushed)"
    echo ""
    echo "Next steps:"
    echo "1. Review the changes above"
    echo "2. Push to GitHub:"
    echo "   cd ${TAP_DIR}"
    echo "   git push origin main"
    echo ""
fi

log_info "Formula updated successfully!"
echo ""
echo "Test installation:"
echo "  brew upgrade ${FORMULA_NAME}"
echo "  ${FORMULA_NAME} --version  # Should show ${VERSION}"
