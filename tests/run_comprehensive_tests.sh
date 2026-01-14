#!/bin/bash

# Comprehensive test runner for ChainMind + engram-mcp integration

set -e

echo "=========================================="
echo "Comprehensive Test Suite Runner"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

cd "$(dirname "$0")/.."

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest not found. Install with: pip install pytest pytest-asyncio${NC}"
    exit 1
fi

# Test categories
declare -a TEST_CATEGORIES=(
    "unit:Unit tests"
    "integration:Integration tests"
    "e2e:End-to-end tests"
    "performance:Performance tests"
    "error_handling:Error handling tests"
)

# Run tests by category
TOTAL_PASSED=0
TOTAL_FAILED=0

for category_info in "${TEST_CATEGORIES[@]}"; do
    IFS=':' read -r marker description <<< "$category_info"

    echo -e "${BLUE}Running $description...${NC}"
    echo "-----------------------------------"

    if pytest -m "$marker" tests/ -v --tb=short 2>&1 | tee /tmp/test_output_$marker.txt; then
        PASSED=$(grep -c "PASSED" /tmp/test_output_$marker.txt 2>/dev/null || echo "0")
        FAILED=$(grep -c "FAILED" /tmp/test_output_$marker.txt 2>/dev/null || echo "0")

        if [ "$FAILED" -eq 0 ]; then
            echo -e "${GREEN}✓ $description: PASSED${NC}"
            TOTAL_PASSED=$((TOTAL_PASSED + PASSED))
        else
            echo -e "${RED}✗ $description: FAILED ($FAILED tests)${NC}"
            TOTAL_FAILED=$((TOTAL_FAILED + FAILED))
        fi
    else
        echo -e "${RED}✗ $description: FAILED${NC}"
        TOTAL_FAILED=$((TOTAL_FAILED + 1))
    fi

    echo ""
done

# Run all comprehensive tests
echo -e "${BLUE}Running comprehensive test files...${NC}"
echo "-----------------------------------"

COMPREHENSIVE_TESTS=(
    "test_chainmind_helper_comprehensive.py"
    "test_prompt_generator_comprehensive.py"
    "test_mcp_integration_comprehensive.py"
    "test_e2e_comprehensive.py"
    "test_performance_comprehensive.py"
    "test_error_handling_comprehensive.py"
)

for test_file in "${COMPREHENSIVE_TESTS[@]}"; do
    if [ -f "tests/$test_file" ]; then
        echo -e "${BLUE}Running $test_file...${NC}"
        if pytest "tests/$test_file" -v --tb=short; then
            echo -e "${GREEN}✓ $test_file: PASSED${NC}"
        else
            echo -e "${RED}✗ $test_file: FAILED${NC}"
            TOTAL_FAILED=$((TOTAL_FAILED + 1))
        fi
        echo ""
    fi
done

# Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed:${NC} $TOTAL_PASSED"
echo -e "${RED}Failed:${NC} $TOTAL_FAILED"
echo ""

if [ $TOTAL_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Check output above.${NC}"
    exit 1
fi
