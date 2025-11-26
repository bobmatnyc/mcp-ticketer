#!/usr/bin/env bash
# Linear Practical Workflow CLI
# Ticket: 1M-217
#
# Common Linear operations for development workflows.
# This script wraps workflow.py with environment validation.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Source environment if available
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Validate environment variables
if [ -z "${LINEAR_API_KEY:-}" ]; then
    echo "❌ ERROR: LINEAR_API_KEY not set"
    echo ""
    echo "Set it in .env or export it:"
    echo "  export LINEAR_API_KEY=lin_api_..."
    echo ""
    echo "Get your API key from: https://linear.app/settings/api"
    exit 1
fi

if [ -z "${LINEAR_TEAM_KEY:-}" ] && [ -z "${LINEAR_TEAM_ID:-}" ]; then
    echo "❌ ERROR: LINEAR_TEAM_KEY or LINEAR_TEAM_ID not set"
    echo ""
    echo "Set one of these in .env:"
    echo "  LINEAR_TEAM_KEY=BTA    # Team short code"
    echo "  LINEAR_TEAM_ID=<uuid>  # Team UUID"
    echo ""
    echo "Find your team key/ID in Linear workspace settings"
    exit 1
fi

# Delegate to Python implementation
exec python3 "$SCRIPT_DIR/workflow.py" "$@"
