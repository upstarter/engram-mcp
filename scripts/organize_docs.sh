#!/bin/bash
# Organize engram-mcp documentation files
set -e

ENGRAM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ENGRAM_DIR"

echo "Organizing engram-mcp documentation..."

# Create docs subdirectories
mkdir -p docs/chainmind-integration
mkdir -p docs/setup
mkdir -p docs/testing
mkdir -p docs/guides

# Move ChainMind integration docs
echo "Moving ChainMind integration docs..."
[ -f CHAINMIND_INTEGRATION.md ] && mv CHAINMIND_INTEGRATION.md docs/chainmind-integration/
[ -f CHAINMIND_SETUP.md ] && mv CHAINMIND_SETUP.md docs/chainmind-integration/
[ -f CHAINMIND_DISABLE.md ] && mv CHAINMIND_DISABLE.md docs/chainmind-integration/
[ -f CHAINMIND_CONFIGURATION_SUMMARY.md ] && mv CHAINMIND_CONFIGURATION_SUMMARY.md docs/chainmind-integration/
[ -f CHAINMIND_AUDIT_IMPLEMENTATION_SUMMARY.md ] && mv CHAINMIND_AUDIT_IMPLEMENTATION_SUMMARY.md docs/chainmind-integration/
[ -f HOW_CHAINMIND_SELECTS_MODELS.md ] && mv HOW_CHAINMIND_SELECTS_MODELS.md docs/chainmind-integration/
[ -f MODEL_SELECTION_EXPLAINED.md ] && mv MODEL_SELECTION_EXPLAINED.md docs/chainmind-integration/
[ -f SMART_ROUTING_IMPLEMENTED.md ] && mv SMART_ROUTING_IMPLEMENTED.md docs/chainmind-integration/ 2>/dev/null || true
[ -f INTEGRATION_EXPLAINED.md ] && mv INTEGRATION_EXPLAINED.md docs/chainmind-integration/ 2>/dev/null || true
[ -f INTEGRATION_STATUS.md ] && mv INTEGRATION_STATUS.md docs/chainmind-integration/ 2>/dev/null || true

# Move setup docs
echo "Moving setup docs..."
[ -f SETUP_COMPLETE.md ] && mv SETUP_COMPLETE.md docs/setup/
[ -f SETUP_STATUS.md ] && mv SETUP_STATUS.md docs/setup/
[ -f SETUP_CHECKLIST.md ] && mv SETUP_CHECKLIST.md docs/setup/
[ -f INSTALL_CHAINMIND_DEPS.md ] && mv INSTALL_CHAINMIND_DEPS.md docs/setup/
[ -f LOCAL_MODELS_SETUP_COMPLETE.md ] && mv LOCAL_MODELS_SETUP_COMPLETE.md docs/setup/ 2>/dev/null || true
[ -f LOCAL_MODELS_FOR_REASONING.md ] && mv LOCAL_MODELS_FOR_REASONING.md docs/setup/ 2>/dev/null || true
[ -f PRODUCTION_SETUP_REQUIRED.md ] && mv PRODUCTION_SETUP_REQUIRED.md docs/setup/ 2>/dev/null || true

# Move testing docs
echo "Moving testing docs..."
[ -f TEST_RESULTS.md ] && mv TEST_RESULTS.md docs/testing/
[ -f TEST_SUITE_README.md ] && mv TEST_SUITE_README.md docs/testing/
[ -f TEST_SUITE_SUMMARY.md ] && mv TEST_SUITE_SUMMARY.md docs/testing/
[ -f TESTING_GUIDE.md ] && mv TESTING_GUIDE.md docs/testing/
[ -f TESTING_WHILE_WORKING.md ] && mv TESTING_WHILE_WORKING.md docs/testing/
[ -f QUICK_TEST_GUIDE.md ] && mv QUICK_TEST_GUIDE.md docs/testing/ 2>/dev/null || true
[ -f QUICK_TEST.md ] && mv QUICK_TEST.md docs/testing/ 2>/dev/null || true
[ -f PRODUCTION_TEST_RESULTS.md ] && mv PRODUCTION_TEST_RESULTS.md docs/testing/ 2>/dev/null || true
[ -f TRACE_USAGE.md ] && mv TRACE_USAGE.md docs/testing/ 2>/dev/null || true
[ -f TRACING_PATTERN_ANALYSIS.md ] && mv TRACING_PATTERN_ANALYSIS.md docs/testing/ 2>/dev/null || true

# Move guide docs
echo "Moving guide docs..."
[ -f USER_GUIDE.md ] && mv USER_GUIDE.md docs/guides/
[ -f HOW_IT_WORKS.md ] && mv HOW_IT_WORKS.md docs/guides/
[ -f VISUAL_GUIDE.md ] && mv VISUAL_GUIDE.md docs/guides/ 2>/dev/null || true
[ -f QUICK_START_CHAINMIND.md ] && mv QUICK_START_CHAINMIND.md docs/guides/ 2>/dev/null || true
[ -f QUICK_DISABLE_CHAINMIND.md ] && mv QUICK_DISABLE_CHAINMIND.md docs/guides/ 2>/dev/null || true
[ -f CURSOR_AUTO_ACCEPT_FIX.md ] && mv CURSOR_AUTO_ACCEPT_FIX.md docs/guides/ 2>/dev/null || true
[ -f CSF_KS_INTEGRATION.md ] && mv CSF_KS_INTEGRATION.md docs/guides/ 2>/dev/null || true
[ -f CLAUDE_CODE_WORKFLOW.md ] && mv CLAUDE_CODE_WORKFLOW.md docs/guides/ 2>/dev/null || true

# Move completion/status docs to appropriate places
[ -f COMPLETION_SUMMARY.md ] && mv COMPLETION_SUMMARY.md docs/chainmind-integration/ 2>/dev/null || true
[ -f IMPLEMENTATION_COMPLETE.md ] && mv IMPLEMENTATION_COMPLETE.md docs/chainmind-integration/ 2>/dev/null || true

echo "Documentation organization complete!"
echo ""
echo "Documentation structure:"
echo "  docs/chainmind-integration/ - ChainMind integration docs"
echo "  docs/setup/ - Setup and installation guides"
echo "  docs/testing/ - Testing documentation"
echo "  docs/guides/ - User guides and workflows"
