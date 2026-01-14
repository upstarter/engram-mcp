# engram-mcp Documentation

Welcome to the engram-mcp documentation! This directory contains all documentation organized by topic.

## Quick Navigation

### Essential Docs
- [ChainMind Integration](./chainmind-integration/README.md) - **START HERE** - Integration overview
- [Setup Guide](./setup/README.md) - Setup instructions
- [Testing Guide](./testing/README.md) - Testing documentation
- [User Guides](./guides/HOW_IT_WORKS.md) - How the system works

### Detailed Documentation

**ChainMind Integration** (`chainmind-integration/`):
- [README](./chainmind-integration/README.md) - Integration overview and quick reference
- [ChainMind Integration](./chainmind-integration/CHAINMIND_INTEGRATION.md) - Detailed integration guide
- [ChainMind Setup](./chainmind-integration/CHAINMIND_SETUP.md) - Setup instructions
- [How ChainMind Selects Models](./chainmind-integration/HOW_CHAINMIND_SELECTS_MODELS.md) - Model selection
- [Model Selection Explained](./chainmind-integration/MODEL_SELECTION_EXPLAINED.md) - Detailed guide
- [ChainMind Disable](./chainmind-integration/CHAINMIND_DISABLE.md) - How to disable
- [ChainMind Configuration Summary](./chainmind-integration/CHAINMIND_CONFIGURATION_SUMMARY.md) - Config overview
- [ChainMind Audit Implementation Summary](./chainmind-integration/CHAINMIND_AUDIT_IMPLEMENTATION_SUMMARY.md) - Audit results

**Setup** (`setup/`):
- [README](./setup/README.md) - Setup overview and quick start
- [Setup Complete](./setup/SETUP_COMPLETE.md) - Setup completion details
- [Setup Checklist](./setup/SETUP_CHECKLIST.md) - Detailed checklist
- [Install ChainMind Dependencies](./setup/INSTALL_CHAINMIND_DEPS.md) - Dependency installation
- [Local Models Setup](./setup/LOCAL_MODELS_SETUP_COMPLETE.md) - Local models setup
- [Local Models for Reasoning](./setup/LOCAL_MODELS_FOR_REASONING.md) - Reasoning models guide
- [Production Setup](./setup/PRODUCTION_SETUP_REQUIRED.md) - Production requirements

**Testing** (`testing/`):
- [README](./testing/README.md) - Testing overview
- [Testing Guide](./testing/TESTING_GUIDE.md) - Comprehensive guide
- [Testing While Working](./testing/TESTING_WHILE_WORKING.md) - Development testing
- [Test Results](./testing/TEST_RESULTS.md) - Test results summary
- [Trace Usage](./testing/TRACE_USAGE.md) - Request tracing
- [Tracing Pattern Analysis](./testing/TRACING_PATTERN_ANALYSIS.md) - Tracing explanation
- [Quick Test Guide](./testing/QUICK_TEST_GUIDE.md) - Quick testing
- [Production Test Results](./testing/PRODUCTION_TEST_RESULTS.md) - Production tests

**Guides** (`guides/`):
- [How It Works](./guides/HOW_IT_WORKS.md) - System overview
- [User Guide](./guides/USER_GUIDE.md) - User guide
- [Visual Guide](./guides/VISUAL_GUIDE.md) - Visual guide
- [Quick Start ChainMind](./guides/QUICK_START_CHAINMIND.md) - Quick start
- [Quick Disable ChainMind](./guides/QUICK_DISABLE_CHAINMIND.md) - Quick disable
- [Cursor Auto Accept Fix](./guides/CURSOR_AUTO_ACCEPT_FIX.md) - Cursor config
- [CSF KS Integration](./guides/CSF_KS_INTEGRATION.md) - CSF integration
- [Claude Code Workflow](./guides/CLAUDE_CODE_WORKFLOW.md) - Workflow guide

## Other Documentation

- [Main README](../README.md) - Project overview and quick start
- [Architecture Documentation](./architecture.md) - System architecture
- [Development Philosophy](./development-philosophy.md) - Development approach

## For AI Agents

**Start with**: [ChainMind Integration README](./chainmind-integration/README.md) for integration overview

Key integration points:
- `engram/chainmind_helper.py` - Main adapter
- `engram/server.py` - MCP tool handlers
- `engram/query_logger.py` - Query logging
- Request flow: MCP Server → ChainMindHelper → TwoTierRouter → Provider
