#!/bin/bash
# Run all CI checks locally before pushing
# This script runs the same checks that GitHub Actions will run

set -e  # Exit on any error

echo "🔍 Running CI checks locally..."
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run a check
run_check() {
    local name=$1
    shift
    echo -e "${YELLOW}▶ Running: $name${NC}"
    if "$@"; then
        echo -e "${GREEN}✓ $name passed${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}✗ $name failed${NC}"
        echo ""
        return 1
    fi
}

# Track failures
failed=0

# Run linting
run_check "Ruff linting" ruff check src/ tests/ || failed=1

# Run tests with coverage
run_check "Pytest with coverage" pytest --cov --cov-fail-under=65 || failed=1

# Optional: Type checking (not required for CI, but good to run locally)
echo -e "${YELLOW}▶ Running: MyPy type checking (optional)${NC}"
if mypy src/ 2>&1 | head -20; then
    echo -e "${GREEN}ℹ MyPy type checking passed (optional check)${NC}"
else
    echo -e "${YELLOW}⚠ MyPy type checking has warnings (not a blocker for CI)${NC}"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $failed -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Safe to push.${NC}"
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Fix them before pushing.${NC}"
    exit 1
fi
