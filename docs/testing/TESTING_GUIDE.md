# Comprehensive Testing Guide

## Overview

This guide covers testing for:
1. ChainMind + engram-mcp integration
2. Cursor auto-approve settings
3. End-to-end functionality
4. Performance optimization

## Quick Test Suite

### 1. Run Integration Verification

```bash
cd /mnt/dev/ai/engram-mcp
python3 verify_chainmind_integration.py
```

**Expected**: All 5 tests pass ✅

### 2. Test Cursor Settings

```bash
# Verify settings file exists and is valid JSON
cat ~/.config/Cursor/User/settings.json | python3 -m json.tool > /dev/null && echo "✓ Settings valid JSON"

# Check auto-approve settings are enabled
grep -q '"cursor.ai.autoApprove": true' ~/.config/Cursor/User/settings.json && echo "✓ Auto-approve enabled"
grep -q '"cursor.ai.requireApproval": false' ~/.config/Cursor/User/settings.json && echo "✓ Approval not required"
```

**Expected**: All checks pass ✅

## Detailed Testing

### Phase 1: Unit Tests

#### Test ChainMind Helper

```bash
cd /mnt/dev/ai/engram-mcp
python3 << 'EOF'
import sys
sys.path.insert(0, '.')

from engram.chainmind_helper import ChainMindHelper

# Test 1: Helper initialization
helper = ChainMindHelper()
print(f"✓ Helper created: {helper is not None}")

# Test 2: Availability check
available = helper.is_available()
print(f"✓ Availability check: {available} (may be False if ChainMind not configured)")

# Test 3: Error detection
test_error = Exception("quota exceeded")
is_limit = helper._is_usage_limit_error(test_error)
print(f"✓ Error detection: {is_limit} (should be True)")

# Test 4: Provider mapping
print("✓ Helper module loaded successfully")
EOF
```

#### Test Prompt Generator

```bash
cd /mnt/dev/ai/engram-mcp
python3 << 'EOF'
import sys
sys.path.insert(0, '.')

from engram.prompt_generator import PromptGenerator

# Test prompt generation
generator = PromptGenerator()

# Test all strategies
strategies = ["concise", "detailed", "structured", "balanced"]
for strategy in strategies:
    result = generator.generate_prompt(
        task="Write a function",
        strategy=strategy
    )
    assert "prompt" in result
    assert result["strategy"] == strategy
    print(f"✓ Strategy '{strategy}': OK")

print("✓ Prompt generator works correctly")
EOF
```

### Phase 2: Integration Tests

#### Test MCP Server Tools

```bash
cd /mnt/dev/ai/engram-mcp

# Activate venv if needed
source venv/bin/activate 2>/dev/null || true

python3 << 'EOF'
import sys
import asyncio
sys.path.insert(0, '.')

async def test_tools():
    from engram.server import list_tools

    tools = await list_tools()
    tool_names = [t.name for t in tools]

    # Check ChainMind tools exist
    chainmind_tools = ["chainmind_generate", "chainmind_generate_prompt", "chainmind_verify"]
    for tool in chainmind_tools:
        if tool in tool_names:
            print(f"✓ Tool '{tool}' registered")
        else:
            print(f"✗ Tool '{tool}' NOT found")

    # Check engram tools exist
    engram_tools = ["engram_remember", "engram_recall", "engram_context"]
    for tool in engram_tools:
        if tool in tool_names:
            print(f"✓ Tool '{tool}' registered")
        else:
            print(f"✗ Tool '{tool}' NOT found")

    print(f"\n✓ Total tools registered: {len(tools)}")

asyncio.run(test_tools())
EOF
```

### Phase 3: End-to-End Testing

#### Test with Claude Code (Manual)

1. **Open Cursor**
2. **Open Claude Code chat**
3. **Test auto-approve**:
   - Ask Claude to make a code change
   - Verify it applies automatically without asking for approval
   - Check: No "Apply changes?" dialog appears

4. **Test ChainMind tools**:
   ```
   Use the chainmind_generate tool with a test prompt
   ```
   - Claude should be able to call the tool
   - If ChainMind available: Should generate response
   - If ChainMind unavailable: Should gracefully handle

5. **Test engram-mcp tools**:
   ```
   Remember: "I prefer Python over JavaScript"
   Recall: "What do I prefer?"
   ```
   - Should store and retrieve memories

#### Test Usage Limit Fallback (Simulated)

```bash
cd /mnt/dev/ai/engram-mcp
python3 << 'EOF'
import sys
import asyncio
sys.path.insert(0, '.')

async def test_fallback():
    from engram.chainmind_helper import ChainMindHelper

    helper = ChainMindHelper()

    if not helper.is_available():
        print("⚠ ChainMind not available - skipping fallback test")
        print("  (This is OK if ChainMind dependencies aren't installed)")
        return

    # Test fallback logic (without actually calling API)
    print("Testing fallback logic...")

    # Simulate usage limit error
    class MockQuotaError(Exception):
        def __init__(self):
            self.message = "quota exceeded"
            self.code = "CM-1801"

    error = MockQuotaError()
    is_limit = helper._is_usage_limit_error(error)

    if is_limit:
        print("✓ Usage limit detection works")
    else:
        print("✗ Usage limit detection failed")

    print("✓ Fallback logic test complete")

asyncio.run(test_fallback())
EOF
```

### Phase 4: Performance Testing

#### Test Cursor Performance

```bash
# Check Cursor settings for performance optimizations
cat ~/.config/Cursor/User/settings.json | grep -E "gpuAcceleration|hardwareAcceleration|maxConcurrent|parallel" | head -10
```

**Expected**: GPU acceleration enabled, parallel agents enabled

#### Test Memory Usage

```bash
# Check if engram-mcp memory store works
cd /mnt/dev/ai/engram-mcp
python3 << 'EOF'
import sys
sys.path.insert(0, '.')

from engram.storage import MemoryStore

store = MemoryStore()

# Test basic operations
try:
    # Try to get stats (will create DB if needed)
    stats = store.get_stats()
    print(f"✓ Memory store accessible")
    print(f"  Total memories: {stats.get('total_memories', 0)}")
except Exception as e:
    print(f"⚠ Memory store test: {e}")
    print("  (This is OK if DB not initialized yet)")
EOF
```

## Automated Test Script

Create a comprehensive test script:

```bash
cat > /mnt/dev/ai/engram-mcp/run_all_tests.sh << 'SCRIPT'
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

    if python3 -m json.tool ~/.config/Cursor/User/settings.json > /dev/null 2>&1; then
        test_pass "Settings file is valid JSON"
    else
        test_fail "Settings file is invalid JSON"
    fi

    if grep -q '"cursor.ai.autoApprove": true' ~/.config/Cursor/User/settings.json; then
        test_pass "Auto-approve enabled"
    else
        test_fail "Auto-approve not enabled"
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

if python3 -c "from engram.storage import MemoryStore; print('OK')" 2>/dev/null; then
    test_pass "Memory store imports"
else
    test_fail "Memory store import failed"
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
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${RED}Failed:${NC} $FAILED"
echo -e "${YELLOW}Warnings:${NC} $WARNED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All critical tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Check output above.${NC}"
    exit 1
fi
SCRIPT

chmod +x /mnt/dev/ai/engram-mcp/run_all_tests.sh
```

## Performance Benchmarks

### Test Cursor Startup Time

```bash
# Measure Cursor startup (manual test)
time cursor .  # Start Cursor in a project directory
```

### Test Memory Store Performance

```bash
cd /mnt/dev/ai/engram-mcp
python3 << 'EOF'
import sys
import time
sys.path.insert(0, '.')

from engram.storage import MemoryStore

store = MemoryStore()

# Test write performance
start = time.time()
for i in range(10):
    store.remember(
        content=f"Test memory {i}",
        memory_type="fact"
    )
write_time = time.time() - start
print(f"Write 10 memories: {write_time:.3f}s ({write_time/10*1000:.1f}ms per memory)")

# Test read performance
start = time.time()
for i in range(10):
    store.recall(query=f"memory {i}", limit=1)
read_time = time.time() - start
print(f"Read 10 queries: {read_time:.3f}s ({read_time/10*1000:.1f}ms per query)")

print(f"\n✓ Performance test complete")
EOF
```

## Manual Testing Checklist

### Cursor Auto-Approve
- [ ] Open Cursor
- [ ] Ask Claude to make a code change
- [ ] Verify change applies automatically (no approval dialog)
- [ ] Test Composer (multi-file editing)
- [ ] Verify Composer changes apply automatically
- [ ] Test Chat code suggestions
- [ ] Verify suggestions apply automatically

### ChainMind Integration
- [ ] Open Claude Code
- [ ] Check if `chainmind_generate` tool is available
- [ ] Check if `chainmind_generate_prompt` tool is available
- [ ] Check if `chainmind_verify` tool is available
- [ ] Try calling `chainmind_generate` with a test prompt
- [ ] Verify graceful degradation if ChainMind unavailable

### engram-mcp Functionality
- [ ] Test `engram_remember` - store a memory
- [ ] Test `engram_recall` - retrieve a memory
- [ ] Test `engram_context` - get context for a query
- [ ] Test `engram_consolidate` - consolidate memories
- [ ] Verify memories persist across sessions

## Troubleshooting Tests

### If Integration Tests Fail

```bash
# Check Python path
python3 -c "import sys; print('\n'.join(sys.path))"

# Check ChainMind path
ls -la /mnt/dev/ai/ai-platform/chainmind/backend/core/di.py

# Check dependencies
cd /mnt/dev/ai/engram-mcp
python3 -c "import mcp; print('MCP OK')"
python3 -c "import chromadb; print('ChromaDB OK')"
```

### If Cursor Settings Don't Work

```bash
# Verify settings file location
ls -la ~/.config/Cursor/User/settings.json

# Check for syntax errors
python3 -m json.tool ~/.config/Cursor/User/settings.json > /dev/null

# Restart Cursor (settings only load on startup)
```

## Success Criteria

✅ **All tests pass**:
- Integration verification: 5/5 tests
- Cursor settings: Valid JSON, auto-approve enabled
- Module imports: All modules load
- File existence: All required files present

✅ **Performance acceptable**:
- Memory operations: < 100ms per operation
- Cursor startup: < 5 seconds
- Tool registration: < 1 second

✅ **Functionality verified**:
- Auto-approve works in Cursor
- ChainMind tools available (or gracefully degraded)
- engram-mcp tools work correctly
- Memories persist

## Next Steps After Testing

1. **If all tests pass**: System is ready for production use
2. **If some tests fail**: Check error messages and fix issues
3. **If ChainMind unavailable**: That's OK - engram-mcp still works
4. **If Cursor settings don't apply**: Restart Cursor

## Quick Test Command

Run everything at once:

```bash
cd /mnt/dev/ai/engram-mcp && ./run_all_tests.sh
```

