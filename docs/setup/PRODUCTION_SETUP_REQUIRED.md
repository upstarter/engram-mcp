# Production Setup Required

## Current Status

Based on testing, here's what ChainMind needs for full production functionality:

## ✅ Already Configured

- **OPENAI_API_KEY**: ✓ Found and configured
- **Error Detection**: ✓ Working correctly
- **Provider Routing**: ✓ Configured correctly
- **Fallback Logic**: ✓ Implemented correctly

## ⚠️ Needs Configuration

### 1. ANTHROPIC_API_KEY (Required for Claude)

**Status**: Not set in current environment

**Action Required**:
```bash
# Option 1: Export in current session
export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"

# Option 2: Add to ~/.chainmind.env (recommended)
echo "ANTHROPIC_API_KEY=sk-ant-api03-your-key-here" >> ~/.chainmind.env

# Option 3: Add to ~/.env
echo "ANTHROPIC_API_KEY=sk-ant-api03-your-key-here" >> ~/.env
```

**Get API Key**: https://console.anthropic.com/api-keys

### 2. Dependencies (Required for ChainMind)

**Missing**: `sentence-transformers` (needed by ChainMind's plugin system)

**Action Required**:
```bash
cd /mnt/dev/ai/ai-platform/chainmind
pip install sentence-transformers
```

Or install in ChainMind's virtual environment if it has one.

### 3. Dependencies (Required for engram-mcp memory)

**Missing**: `sentence-transformers` (needed for embeddings)

**Action Required**:
```bash
cd /mnt/dev/ai/engram-mcp
pip install sentence-transformers
```

Or use the venv:
```bash
cd /mnt/dev/ai/engram-mcp
source venv/bin/activate
pip install sentence-transformers
```

## Quick Setup Script

Run this to set up everything:

```bash
#!/bin/bash

# 1. Install dependencies
cd /mnt/dev/ai/ai-platform/chainmind
pip install sentence-transformers aiofiles

cd /mnt/dev/ai/engram-mcp
pip install sentence-transformers

# 2. Set API keys (replace with your actual keys)
cat >> ~/.chainmind.env << EOF
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
OPENAI_API_KEY=sk-your-openai-key-here
EOF

# 3. Verify
cd /mnt/dev/ai/ai-platform/chainmind
python3 utils/load_env.py
```

## What Works Now

Even without full setup, these work:
- ✅ Error detection (6/6 patterns detected)
- ✅ Provider routing logic
- ✅ Fallback chain configuration
- ✅ Integration code structure
- ✅ Graceful degradation

## What Needs Setup

To make real API calls:
1. **ANTHROPIC_API_KEY** - For Claude (primary provider)
2. **sentence-transformers** - For ChainMind and engram-mcp
3. **aiofiles** - For ChainMind (already installed in engram-mcp venv)

## Test After Setup

Once configured, run:

```bash
cd /mnt/dev/ai/engram-mcp
python3 test_real_production.py
```

This will make real API calls and test:
- Claude generation
- Fallback to OpenAI
- Error handling
- Complete workflows

## Configuration Files

ChainMind looks for API keys in (in order):
1. `.env` (current directory)
2. `~/.env` (home directory)
3. `~/.chainmind.env` (ChainMind-specific)
4. System environment variables

**Recommended**: Use `~/.chainmind.env` for ChainMind-specific configuration.

## Summary

**To enable full production functionality**:

1. ✅ Set `ANTHROPIC_API_KEY` (you have OpenAI key already)
2. ✅ Install `sentence-transformers` in both ChainMind and engram-mcp environments
3. ✅ Install `aiofiles` in ChainMind environment (if not already)

**Current capabilities**:
- Integration code works ✅
- Error detection works ✅
- Fallback logic works ✅
- Needs API keys and dependencies for real API calls ⚠️
