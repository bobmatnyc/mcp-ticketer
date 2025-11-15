#!/bin/bash
# Quick verification test for MCP command patterns
# Run this after making changes to verify basic functionality

set -e

echo "Quick MCP Command Verification"
echo "==============================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

PASS=0
FAIL=0

# Test 1: Help shows --path option
echo -n "1. Help shows --path option... "
if mcp-ticketer mcp --help 2>&1 | grep -q "\-\-path.*\-p"; then
    echo -e "${GREEN}✓${NC}"
    ((PASS++))
else
    echo -e "${RED}✗${NC}"
    ((FAIL++))
fi

# Test 2: Status subcommand works (not interpreted as path)
echo -n "2. Status subcommand works... "
if mcp-ticketer mcp status 2>&1 | grep -q "MCP Server Status"; then
    echo -e "${GREEN}✓${NC}"
    ((PASS++))
else
    echo -e "${RED}✗${NC}"
    ((FAIL++))
fi

# Test 3: --path option is accepted
echo -n "3. --path option accepted... "
(mcp-ticketer mcp --path . 2>&1 | head -5) &
PID=$!
sleep 1
kill $PID 2>/dev/null || true
wait $PID 2>/dev/null || true
if mcp-ticketer mcp --path . 2>&1 | head -5 | grep -q "Configured.*adapter"; then
    echo -e "${GREEN}✓${NC}"
    ((PASS++))
else
    echo -e "${RED}✗${NC}"
    ((FAIL++))
fi

# Test 4: -p short form works
echo -n "4. -p short form works... "
if mcp-ticketer mcp -p . 2>&1 | head -5 | grep -q "Configured.*adapter"; then
    echo -e "${GREEN}✓${NC}"
    ((PASS++))
else
    echo -e "${RED}✗${NC}"
    ((FAIL++))
fi

# Test 5: Status with --path works
echo -n "5. Status with --path works... "
if mcp-ticketer mcp --path . status 2>&1 | grep -q "MCP Server Status"; then
    echo -e "${GREEN}✓${NC}"
    ((PASS++))
else
    echo -e "${RED}✗${NC}"
    ((FAIL++))
fi

echo ""
echo "==============================="
echo -e "Results: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
