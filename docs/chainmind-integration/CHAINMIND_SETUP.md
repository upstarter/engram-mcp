# ChainMind Setup for engram-mcp Integration

## Quick Setup Guide

To enable full ChainMind functionality in the engram-mcp integration, you need to configure API keys.

## Required API Keys

### 1. Anthropic (Claude) - **Primary Provider**

**Environment Variable**: `ANTHROPIC_API_KEY`

**Get it**: https://console.anthropic.com/api-keys

**Set it**:
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."
```

### 2. OpenAI - **Fallback Provider**

**Environment Variable**: `OPENAI_API_KEY`

**Get it**: https://platform.openai.com/api-keys

**Set it**:
```bash
export OPENAI_API_KEY="sk-..."
```

### 3. Ollama - **Local Fallback (Optional)**

**Setup**:
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama
ollama serve

# Pull a model
ollama pull llama3
```

No API key needed - runs locally.

## Configuration File

Create `~/.chainmind.env`:

```bash
# Primary provider (Claude)
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# Fallback provider (OpenAI)
OPENAI_API_KEY=sk-your-openai-key-here

# Local fallback (optional)
OLLAMA_BASE_URL=http://localhost:11434
```

## Verify Setup

```bash
cd /mnt/dev/ai/ai-platform/chainmind
python3 utils/load_env.py
```

Should show:
```
✓ ANTHROPIC_API_KEY found
✓ OPENAI_API_KEY found
```

## Test Integration

After setting up keys:

```bash
cd /mnt/dev/ai/engram-mcp
python3 test_production_integration.py
```

This will make real API calls and test the full integration including fallback.

## What You Get

With API keys configured:

✅ **Full ChainMind functionality**
- Claude as primary provider
- Automatic fallback to OpenAI when Claude hits limits
- Local Ollama fallback if needed
- Usage limit detection and handling
- Cost optimization

Without API keys:

⚠️ **Graceful degradation**
- engram-mcp still works normally
- ChainMind tools report "not available"
- No API calls made
- Integration handles unavailability gracefully

## Minimum Setup

**For basic functionality**: Just `ANTHROPIC_API_KEY`

**For full fallback**: `ANTHROPIC_API_KEY` + `OPENAI_API_KEY`

**For local fallback**: Install and run Ollama
