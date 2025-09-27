#!/usr/bin/env bash

# MCP Ticketer Installation Script

set -e

echo "MCP Ticketer Installation"
echo "========================="
echo

# Check Python version
PYTHON_CMD=""
if command -v python3.13 &> /dev/null; then
    PYTHON_CMD="python3.13"
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    if [ "$PYTHON_VERSION" = "3.13" ]; then
        PYTHON_CMD="python3"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "Error: Python 3.13 is required but not found."
    echo "Please install Python 3.13 and try again."
    exit 1
fi

echo "✓ Found Python: $($PYTHON_CMD --version)"

# Create virtual environment
echo
echo "Creating virtual environment..."
$PYTHON_CMD -m .venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --quiet --upgrade pip

# Install package in editable mode
echo "Installing MCP Ticketer..."
pip install --quiet -e .

echo
echo "✓ Installation complete!"
echo
echo "To get started:"
echo "  1. Activate the virtual environment: source .venv/bin/activate"
echo "  2. Initialize configuration: mcp-ticketer init"
echo "  3. Create your first ticket: mcp-ticketer create 'Hello World'"
echo
echo "Or use the wrapper scripts directly:"
echo "  ./mcp-ticketer init"
echo "  ./mcp-ticketer create 'Hello World'"
echo
echo "Run tests to verify installation:"
echo "  python test_basic.py"