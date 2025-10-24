#!/bin/bash
# MCP Ticketer Server - Runs mcp-ticketer from local venv
# This script ensures the MCP server runs with the correct environment

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ] || [ ! -d "src/mcp_ticketer" ]; then
    echo "Error: This script must be run from the mcp-ticketer project directory" >&2
    exit 1
fi

# Get the absolute path of the project directory
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Check if .venv exists, create if not
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..." >&2
    python3.13 -m venv .venv

    echo "Installing dependencies..." >&2
    .venv/bin/pip install --quiet --upgrade pip
    .venv/bin/pip install --quiet -e .
    .venv/bin/pip install --quiet ai-trackdown-pytools gql
fi

# Load .env.local if it exists
if [ -f ".env.local" ]; then
    set -a
    source .env.local
    set +a
fi

# Execute mcp-ticketer command from local venv
# Pass all arguments through to mcp-ticketer
exec "${PROJECT_DIR}/.venv/bin/mcp-ticketer" "$@"