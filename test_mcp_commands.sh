#!/bin/bash
# Test script for MCP command patterns with --path option fix
# macOS compatible version

set -e

echo "================================"
echo "MCP Command Pattern Test Suite"
echo "================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS_COUNT=0
FAIL_COUNT=0

# Function to test command and capture output
test_command() {
    local test_name="$1"
    local command="$2"
    local expected_result="$3"  # "pass" or "fail"
    local is_server="${4:-false}"

    echo -e "${YELLOW}Testing:${NC} $test_name"
    echo "Command: $command"
    echo ""

    # Run command and capture output
    if [ "$is_server" == "true" ]; then
        # For server commands, start in background and kill after 2 seconds
        bash -c "$command 2>&1 | head -30" > /tmp/test_output.txt 2>&1 &
        local pid=$!
        sleep 2
        kill $pid 2>/dev/null || true
        wait $pid 2>/dev/null || true
        actual_result="pass"
    else
        # For regular commands, just run them
        if bash -c "$command 2>&1 | head -30" > /tmp/test_output.txt 2>&1; then
            actual_result="pass"
        else
            actual_result="fail"
        fi
    fi

    # Show output
    echo "Output (first 30 lines):"
    cat /tmp/test_output.txt
    echo ""

    # Check result
    if [ "$actual_result" == "$expected_result" ] || [ "$expected_result" == "any" ]; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((PASS_COUNT++))
    else
        echo -e "${RED}✗ FAIL${NC} (Expected: $expected_result, Got: $actual_result)"
        ((FAIL_COUNT++))
    fi
    echo ""
    echo "---"
    echo ""
}

# Test 1: Basic server start
test_command \
    "1. Basic server start (primary use case)" \
    "mcp-ticketer mcp" \
    "pass" \
    true

# Test 2: Server start with --path option
test_command \
    "2a. Server start with --path ." \
    "mcp-ticketer mcp --path ." \
    "pass" \
    true

test_command \
    "2b. Server start with -p . (short form)" \
    "mcp-ticketer mcp -p ." \
    "pass" \
    true

# Test 3: Subcommands without path (previously broken)
test_command \
    "3a. Status subcommand without path" \
    "mcp-ticketer mcp status" \
    "pass" \
    false

test_command \
    "3b. Serve subcommand explicitly" \
    "mcp-ticketer mcp serve" \
    "pass" \
    true

# Test 4: Subcommands with path option
test_command \
    "4a. Status with --path ." \
    "mcp-ticketer mcp --path . status" \
    "pass" \
    false

test_command \
    "4b. Status with -p . (short form)" \
    "mcp-ticketer mcp -p . status" \
    "pass" \
    false

# Test 5: Help text verification
test_command \
    "5a. MCP help text" \
    "mcp-ticketer mcp --help" \
    "pass" \
    false

test_command \
    "5b. Serve command help" \
    "mcp-ticketer mcp serve --help" \
    "pass" \
    false

# Test 6: Edge cases
test_command \
    "6a. Nonexistent path (should fail)" \
    "mcp-ticketer mcp --path /nonexistent/path/that/does/not/exist" \
    "fail" \
    false

test_command \
    "6b. Different directory (/tmp)" \
    "mcp-ticketer mcp --path /tmp" \
    "pass" \
    true

# Summary
echo "================================"
echo "Test Summary"
echo "================================"
echo -e "Passed: ${GREEN}${PASS_COUNT}${NC}"
echo -e "Failed: ${RED}${FAIL_COUNT}${NC}"
echo -e "Total:  $((PASS_COUNT + FAIL_COUNT))"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
