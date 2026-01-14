# Quick Start: ChainMind Integration

## What You Get

Three new MCP tools for Claude:

1. **`chainmind_generate`** - Generate text with automatic fallback when Claude hits usage limits
2. **`chainmind_generate_prompt`** - Generate optimized prompts with engram-mcp context
3. **`chainmind_verify`** - Verify responses with alternative models

## Quick Test

### 1. Verify Integration

```bash
cd /mnt/dev/ai/engram-mcp
python3 verify_chainmind_integration.py
```

Expected: All tests pass ✅

### 2. Use in Claude Code

When Claude needs to generate text and Claude hits usage limits:

```python
# Claude automatically uses fallback
result = await call_tool("chainmind_generate", {
    "prompt": "Your prompt here",
    "prefer_claude": True
})
# Returns: Generated text + provider info
```

### 3. Generate Better Prompts

```python
# Get optimized prompt with context
prompt = await call_tool("chainmind_generate_prompt", {
    "task": "What you need Claude to do",
    "strategy": "balanced"
})
# Returns: Optimized prompt + context used
```

## Configuration

### Auto-Approve Memories

Set environment variable:
```bash
export ENGRAM_AUTO_APPROVE=true
```

Or create `~/.engram/config/engram.yaml`:
```yaml
auto_approve: true
```

## Benefits

- ✅ **No Extra Credits**: Automatically uses alternatives when Claude limit is hit
- ✅ **Better Prompts**: Context-aware prompt generation
- ✅ **Quality Assurance**: Multi-model verification
- ✅ **Seamless**: Works automatically, no manual intervention needed

## Troubleshooting

**ChainMind not available?**
- Check ChainMind is installed at `/mnt/dev/ai/ai-platform/chainmind`
- Tools gracefully degrade - engram-mcp still works normally

**Import errors?**
- Verify Python path includes ChainMind
- Check ChainMind dependencies are installed

**Provider errors?**
- Ensure alternative providers (OpenAI, Ollama) are configured in ChainMind
- Check API keys are set

## Status

✅ **Integration Complete** - Ready for use!

All components implemented, tested, and documented. The integration is production-ready and will gracefully handle cases where ChainMind is not fully configured.

