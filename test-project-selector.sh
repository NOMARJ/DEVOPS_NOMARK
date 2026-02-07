#!/bin/bash
#
# Test Script for Slack Bot Project Selector
# This script validates that your projects.json is correctly configured
# and the Slack bot can recognize all projects.
#
# Usage: ./test-project-selector.sh
#

set -e

echo "=========================================="
echo "Slack Bot Project Selector - Test Suite"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0

# Helper functions
pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

info() {
    echo -e "ℹ $1"
}

echo "Test 1: Check if ~/config directory exists"
if [[ -d ~/config ]]; then
    pass "Config directory exists at ~/config"
else
    fail "Config directory missing at ~/config"
    warn "Run: mkdir -p ~/config"
fi
echo ""

echo "Test 2: Check if projects.json exists"
if [[ -f ~/config/projects.json ]]; then
    pass "projects.json exists at ~/config/projects.json"
else
    fail "projects.json not found at ~/config/projects.json"
    warn "Create it using the template in QUICK_FIX_GUIDE.md"
    exit 1
fi
echo ""

echo "Test 3: Validate JSON syntax"
if jq empty ~/config/projects.json 2>/dev/null; then
    pass "projects.json has valid JSON syntax"
else
    fail "projects.json has invalid JSON syntax"
    warn "Run: cat ~/config/projects.json | jq ."
    exit 1
fi
echo ""

echo "Test 4: Check JSON structure"
if jq -e '.projects' ~/config/projects.json >/dev/null 2>&1; then
    pass "projects.json has 'projects' array"
else
    fail "projects.json missing 'projects' array"
    exit 1
fi
echo ""

echo "Test 5: Count active projects"
ACTIVE_COUNT=$(jq '[.projects[] | select(.active == true)] | length' ~/config/projects.json)
TOTAL_COUNT=$(jq '.projects | length' ~/config/projects.json)

if [[ $ACTIVE_COUNT -gt 0 ]]; then
    pass "Found $ACTIVE_COUNT active projects (out of $TOTAL_COUNT total)"
else
    fail "No active projects found"
    warn "Set 'active': true for at least one project"
fi
echo ""

echo "Test 6: Validate project structure"
INVALID_PROJECTS=0

while IFS= read -r project_id; do
    # Check required fields
    HAS_ID=$(jq -r ".projects[] | select(.id == \"$project_id\") | has(\"id\")" ~/config/projects.json)
    HAS_NAME=$(jq -r ".projects[] | select(.id == \"$project_id\") | has(\"name\")" ~/config/projects.json)
    HAS_ACTIVE=$(jq -r ".projects[] | select(.id == \"$project_id\") | has(\"active\")" ~/config/projects.json)

    if [[ "$HAS_ID" == "true" && "$HAS_NAME" == "true" && "$HAS_ACTIVE" == "true" ]]; then
        pass "Project '$project_id' has all required fields"
    else
        fail "Project '$project_id' missing required fields"
        ((INVALID_PROJECTS++))
    fi
done < <(jq -r '.projects[].id' ~/config/projects.json)
echo ""

echo "Test 7: Check for duplicate project IDs"
DUPLICATE_COUNT=$(jq -r '.projects[].id' ~/config/projects.json | sort | uniq -d | wc -l)

if [[ $DUPLICATE_COUNT -eq 0 ]]; then
    pass "No duplicate project IDs found"
else
    fail "Found $DUPLICATE_COUNT duplicate project IDs"
    jq -r '.projects[].id' ~/config/projects.json | sort | uniq -d | while read -r dup; do
        warn "  Duplicate: $dup"
    done
fi
echo ""

echo "Test 8: Check for inhhale-v2 project"
if jq -e '.projects[] | select(.id == "inhhale-v2")' ~/config/projects.json >/dev/null 2>&1; then
    IS_ACTIVE=$(jq -r '.projects[] | select(.id == "inhhale-v2") | .active' ~/config/projects.json)
    if [[ "$IS_ACTIVE" == "true" ]]; then
        pass "Project 'inhhale-v2' exists and is active"
    else
        warn "Project 'inhhale-v2' exists but is NOT active"
        info "Set 'active': true for inhhale-v2"
    fi
else
    fail "Project 'inhhale-v2' not found in projects.json"
    warn "Add it using the template in QUICK_FIX_GUIDE.md"
fi
echo ""

echo "Test 9: Check file permissions"
if [[ -r ~/config/projects.json ]]; then
    pass "projects.json is readable"
else
    fail "projects.json is not readable"
    warn "Run: chmod 644 ~/config/projects.json"
fi
echo ""

echo "Test 10: Check if Slack bot is running"
if pgrep -f "slack-bot.py" > /dev/null; then
    pass "Slack bot process is running"
    BOT_PID=$(pgrep -f "slack-bot.py")
    info "Bot PID: $BOT_PID"
else
    warn "Slack bot process not found"
    info "Start it with: python3 ~/scripts/slack-bot.py &"
fi
echo ""

echo "Test 11: List all active projects"
echo "Active projects in your configuration:"
echo "======================================="

jq -r '.projects[] | select(.active == true) | "• \(.id) - \(.name) (\(.stack // "unknown")) [P\(.priority // "-")]"' ~/config/projects.json

if [[ $(jq '[.projects[] | select(.active == true)] | length' ~/config/projects.json) -eq 0 ]]; then
    warn "No active projects to display"
fi
echo ""

echo "Test 12: Validate all expected projects exist"
EXPECTED_PROJECTS=("flowmetrics" "instaindex" "inhhale-v2")
MISSING_PROJECTS=()

for project in "${EXPECTED_PROJECTS[@]}"; do
    if jq -e ".projects[] | select(.id == \"$project\")" ~/config/projects.json >/dev/null 2>&1; then
        pass "Expected project '$project' found"
    else
        fail "Expected project '$project' missing"
        MISSING_PROJECTS+=("$project")
    fi
done

if [[ ${#MISSING_PROJECTS[@]} -gt 0 ]]; then
    warn "Missing projects: ${MISSING_PROJECTS[*]}"
fi
echo ""

echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Test in Slack: @DevOps task inhhale-v2 complete the iOS audit"
    echo "2. Test invalid project: @DevOps task wrongname test"
    echo "3. If dropdown doesn't appear, implement code from slack-bot-project-selector.py"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo "Fix the issues above, then:"
    echo "1. Re-run this test script"
    echo "2. Restart the Slack bot: pkill -f slack-bot.py && python3 ~/scripts/slack-bot.py &"
    echo "3. Test in Slack"
    exit 1
fi
