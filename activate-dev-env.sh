#!/bin/bash
# Quick activation script for mcp-ticketer development environment
#
# Usage:
#   source activate-dev-env.sh
#   OR
#   . activate-dev-env.sh

# Check if script is being sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script must be sourced, not executed directly."
    echo "Usage: source activate-dev-env.sh"
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate the virtual environment
source "${SCRIPT_DIR}/.venv/bin/activate"

# Verify activation
if [ $? -eq 0 ]; then
    echo "✅ Development environment activated!"
    echo ""
    echo "Python: $(which python)"
    echo "Pytest: $(which pytest)"
    echo ""
    echo "Quick commands:"
    echo "  make test-parallel   - Run tests (3-4x faster)"
    echo "  make quality         - Code quality checks"
    echo "  make help            - Show all commands"
    echo "  pytest --version     - Verify pytest setup"
    echo ""
    echo "📖 See docs/DEVELOPMENT_ENVIRONMENT.md for details"
else
    echo "❌ Failed to activate virtual environment"
    echo "Check if .venv directory exists and is properly configured"
fi
