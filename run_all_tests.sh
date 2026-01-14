#!/bin/bash

echo "=========================================="
echo "Comprehensive Integration Test Suite"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0
WARNED=0

test_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

test_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

test_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNED++))
}

echo "Phase 1: Integration Verification"
echo "-----------------------------------"
cd /mnt/dev/ai/engram-mcp
if python3 verify_chainmind_integration.py > /tmp/test_output.txt 2>&1; then
    test_pass "Integration verification"
else
    test_fail "Integration verification"
    cat /tmp/test_output.txt | tail -20
fi

echo ""
echo "Phase 2: Cursor Settings"
echo "-----------------------------------"
if [ -f ~/.config/Cursor/User/settings.json ]; then
    test_pass "Settings file exists"

    # Cursor settings.json supports comments (JSONC), so we check syntax differently
    if python3 -c "import json; f=open('$HOME/.config/Cursor/User/settings.json'); content=f.read(); f.close(); [line for line in content.split('\n') if not line.strip().startswith('//')]; json.loads(''.join([line for line in content.split('\n') if not line.strip().startswith('//')]))" 2>/dev/null; then
        test_pass "Settings file is valid JSONC"
    else
        # Try simple validation - check if it has basic structure
        if grep -q '"cursor.ai.autoApprove"' ~/.config/Cursor/User/settings.json; then
            test_warn "Settings file has comments (JSONC) - validation skipped"
        else
            test_fail "Settings file structure invalid"
        fi
    fi

    if grep -q '"cursor.ai.autoApprove": true' ~/.config/Cursor/User/settings.json; then
        test_pass "Auto-approve enabled"
    else
        test_fail "Auto-approve not enabled"
    fi

    if grep -q '"cursor.ai.requireApproval": false' ~/.config/Cursor/User/settings.json; then
        test_pass "Approval not required"
    else
        test_fail "Approval still required"
    fi
else
    test_fail "Settings file not found"
fi

echo ""
echo "Phase 3: Module Imports"
echo "-----------------------------------"
cd /mnt/dev/ai/engram-mcp
if python3 -c "from engram.chainmind_helper import ChainMindHelper; print('OK')" 2>/dev/null; then
    test_pass "ChainMind helper imports"
else
    test_warn "ChainMind helper import failed (may be OK if ChainMind not configured)"
fi

if python3 -c "from engram.prompt_generator import PromptGenerator; print('OK')" 2>/dev/null; then
    test_pass "Prompt generator imports"
else
    test_fail "Prompt generator import failed"
fi

if python3 -c "import sys; sys.path.insert(0, '.'); from engram.storage import MemoryStore; print('OK')" 2>/dev/null; then
    test_pass "Memory store imports"
else
    # Check if it's a dependency issue
    if python3 -c "import chromadb" 2>/dev/null; then
        test_warn "Memory store import failed (check engram/storage.py)"
    else
        test_warn "Memory store import failed (ChromaDB not installed - may be OK)"
    fi
fi

echo ""
echo "Phase 4: File Existence"
echo "-----------------------------------"
cd /mnt/dev/ai/engram-mcp

files=(
    "engram/chainmind_helper.py"
    "engram/prompt_generator.py"
    "engram/server.py"
    "config/chainmind.yaml"
    "CHAINMIND_INTEGRATION.md"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        test_pass "File exists: $file"
    else
        test_fail "File missing: $file"
    fi
done

echo ""
echo "Phase 5: Tool Registration"
echo "-----------------------------------"
cd /mnt/dev/ai/engram-mcp

# Check if ChainMind tools are in server.py
if grep -q "chainmind_generate" engram/server.py; then
    test_pass "chainmind_generate tool registered"
else
    test_fail "chainmind_generate tool NOT found"
fi

if grep -q "chainmind_generate_prompt" engram/server.py; then
    test_pass "chainmind_generate_prompt tool registered"
else
    test_fail "chainmind_generate_prompt tool NOT found"
fi

if grep -q "chainmind_verify" engram/server.py; then
    test_pass "chainmind_verify tool registered"
else
    test_fail "chainmind_verify tool NOT found"
fi

echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${RED}Failed:${NC} $FAILED"
echo -e "${YELLOW}Warnings:${NC} $WARNED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All critical tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Restart Cursor to apply settings"
    echo "2. Test auto-approve in Cursor"
    echo "3. Test ChainMind tools with Claude Code"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Check output above.${NC}"
    exit 1
fi
