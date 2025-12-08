#!/bin/bash

# GitHub Projects V2 Integration Test Runner
# This script runs the integration test with proper environment setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}GitHub Projects V2 Integration Test Runner${NC}"
echo -e "${BLUE}============================================================${NC}"
echo

# Check for GitHub token
if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${YELLOW}GITHUB_TOKEN not set in environment${NC}"
    echo

    # Check for .env.local
    if [ -f "$PROJECT_ROOT/.env.local" ]; then
        echo -e "${BLUE}Found .env.local, checking for GITHUB_TOKEN...${NC}"

        if grep -q "^GITHUB_TOKEN=" "$PROJECT_ROOT/.env.local"; then
            echo -e "${GREEN}✓ GITHUB_TOKEN found in .env.local${NC}"
            echo -e "${BLUE}Loading environment variables from .env.local...${NC}"

            # Export variables from .env.local
            set -a
            source <(grep -v '^#' "$PROJECT_ROOT/.env.local" | grep -v '^$')
            set +a

            echo -e "${GREEN}✓ Environment loaded${NC}"
        else
            echo -e "${RED}✗ GITHUB_TOKEN not found in .env.local${NC}"
            echo
            echo -e "${YELLOW}Please add your GitHub token to .env.local:${NC}"
            echo -e "  echo 'GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE' >> .env.local"
            echo
            echo -e "${YELLOW}Or export it as an environment variable:${NC}"
            echo -e "  export GITHUB_TOKEN='ghp_YOUR_TOKEN_HERE'"
            echo
            exit 1
        fi
    else
        echo -e "${RED}✗ No .env.local file found${NC}"
        echo
        echo -e "${YELLOW}Please create .env.local with your GitHub token:${NC}"
        echo -e "  echo 'GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE' > .env.local"
        echo
        echo -e "${YELLOW}Or export it as an environment variable:${NC}"
        echo -e "  export GITHUB_TOKEN='ghp_YOUR_TOKEN_HERE'"
        echo
        exit 1
    fi
else
    echo -e "${GREEN}✓ GITHUB_TOKEN found in environment${NC}"
fi

echo

# Verify token format
if [[ ! $GITHUB_TOKEN =~ ^(ghp_|github_pat_) ]]; then
    echo -e "${YELLOW}⚠ Warning: Token doesn't match expected GitHub PAT format${NC}"
    echo -e "${YELLOW}  Expected: ghp_... or github_pat_...${NC}"
    echo -e "${YELLOW}  Got: ${GITHUB_TOKEN:0:10}...${NC}"
    echo
fi

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

# Run the test
echo -e "${BLUE}Running integration test...${NC}"
echo

cd "$PROJECT_ROOT"
python3 tests/integration/test_github_projects_integration.py

# Capture exit code
TEST_EXIT_CODE=$?

echo
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}Integration test completed successfully!${NC}"
    echo -e "${GREEN}============================================================${NC}"
else
    echo -e "${RED}============================================================${NC}"
    echo -e "${RED}Integration test failed with exit code $TEST_EXIT_CODE${NC}"
    echo -e "${RED}============================================================${NC}"
fi

exit $TEST_EXIT_CODE
