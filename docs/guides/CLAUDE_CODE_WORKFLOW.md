# Claude Code + ChainMind Workflow

## How It Works

### Primary Flow (Normal Operation)

1. **Claude Code** → Uses Claude API directly (via Claude Code's built-in integration)
   - This is your primary provider
   - Best quality, best reasoning
   - Uses your Claude Pro plan ($100/month)

### Fallback Flow (When Claude Hits Token Limits)

2. **Claude Code detects token limit** → Calls `chainmind_generate` tool via `engram-mcp`
3. **ChainMind** → Skips Claude (already tried), goes straight to:
   - **OpenAI** (primary fallback) - Your $20 pay-as-you-go account
   - **Local models** (last resort) - Only if OpenAI unavailable

## Configuration

### Current Setup

- **Primary**: Claude (via Claude Code) ✅
- **Fallback**: OpenAI (via ChainMind) ✅
- **Last Resort**: Local models (Ollama) ✅

### Why This Is Optimal

1. **Claude Code handles Claude API** - No need to duplicate
2. **OpenAI as fallback** - Good quality, cost-effective
3. **Local models last resort** - Only when APIs unavailable

## Usage

### Normal Operation

Just use Claude Code normally. It will use Claude API automatically.

### When Token Limits Hit

Claude Code will automatically call `chainmind_generate` which:
- Skips Claude (already tried)
- Uses OpenAI as fallback
- Falls back to local models if OpenAI unavailable

### Manual Override

If you want to explicitly use a different provider:

```python
# In Claude Code, call:
chainmind_generate(
    prompt="Your prompt",
    prefer_claude=False,  # Skip Claude (default)
    auto_select_model=True  # Let ChainMind choose best fallback
)
```

## Benefits

✅ **No duplicate Claude calls** - Claude Code handles Claude, ChainMind handles fallback
✅ **Cost efficient** - Only use OpenAI when Claude unavailable
✅ **Seamless fallback** - Automatic when token limits hit
✅ **Quality maintained** - OpenAI is good quality fallback

## Summary

**Flow**: Claude Code → Claude API (primary) → OpenAI (fallback) → Local (last resort)

This is the optimal setup! 🎯
