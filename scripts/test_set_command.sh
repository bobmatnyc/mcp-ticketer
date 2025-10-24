#!/bin/bash

# Source environment variables
source .env.local

# Activate virtual environment
source .venv/bin/activate

echo "Testing 'set' command functionality..."
echo "========================================"

# 1. Show current configuration
echo -e "\n1. Current configuration:"
./mcp-ticketer set

# 2. Set Linear as default
echo -e "\n2. Setting Linear as default adapter..."
./mcp-ticketer set --adapter linear --team-key BTA

# 3. Create a ticket with default adapter (Linear)
echo -e "\n3. Creating ticket with Linear (default)..."
./mcp-ticketer create "[TEST] Set command test" --description "Testing default adapter"

# 4. List tickets with default adapter
echo -e "\n4. Listing tickets with Linear (default)..."
./mcp-ticketer list --limit 3

# 5. Switch to GitHub as default
echo -e "\n5. Switching to GitHub as default..."
./mcp-ticketer set --adapter github

# 6. List tickets with new default (GitHub)
echo -e "\n6. Listing tickets with GitHub (new default)..."
./mcp-ticketer list --limit 3

# 7. Override default with --adapter flag
echo -e "\n7. Override default (GitHub) with JIRA..."
./mcp-ticketer list --adapter jira --limit 3

# 8. Show final configuration
echo -e "\n8. Final configuration:"
./mcp-ticketer set

echo -e "\n✅ Set command testing complete!"