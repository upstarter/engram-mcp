# How to Disable/Enable ChainMind Routing

## Current Behavior

**By default, ChainMind is NOT routing your queries.**

Claude Code uses Claude API directly. ChainMind is only called when:
1. Claude Code explicitly calls the `chainmind_generate` tool (rare)
2. This happens automatically when Claude hits token limits (1-2x per week)
3. Or when you manually request it

## How to Disable ChainMind Completely

### Option 1: Disable in Config (Recommended)

Edit `/mnt/dev/ai/engram-mcp/config/chainmind.yaml`:

```yaml
# Disable ChainMind integration
enabled: false
```

This will:
- Hide ChainMind tools from Claude Code
- Prevent any ChainMind routing
- Claude Code will use Claude API only (no fallback)

### Option 2: Remove Tools from MCP Server

Edit `/mnt/dev/ai/engram-mcp/engram/server.py`:

Comment out the ChainMind tools in `list_tools()`:

```python
@server.list_tools()
async def list_tools() -> list[Tool]:
    """Tell Claude what tools are available."""
    tools = [
        Tool(name="engram_remember", ...),
        Tool(name="engram_recall", ...),
        Tool(name="engram_context", ...),
        # Tool(name="chainmind_generate", ...),  # DISABLED
        # Tool(name="chainmind_generate_prompt", ...),  # DISABLED
        # Tool(name="chainmind_verify", ...),  # DISABLED
    ]
    return tools
```

### Option 3: Environment Variable

Set environment variable:

```bash
export CHAINMIND_ENABLED=false
```

## How to Re-Enable ChainMind

### Option 1: Enable in Config

Edit `/mnt/dev/ai/engram-mcp/config/chainmind.yaml`:

```yaml
enabled: true
```

### Option 2: Uncomment Tools

Uncomment the ChainMind tools in `server.py`.

### Option 3: Environment Variable

```bash
export CHAINMIND_ENABLED=true
# or unset it
unset CHAINMIND_ENABLED
```

## Verify Current Status

Check if ChainMind is enabled:

```bash
# Check config file
cat /mnt/dev/ai/engram-mcp/config/chainmind.yaml | grep enabled

# Check if tools are available (in Claude Code)
# Look for chainmind_generate in available tools
```

## What Happens When Disabled

✅ **Claude Code works normally** - Uses Claude API directly
✅ **No ChainMind routing** - All queries go to Claude
❌ **No fallback** - If Claude hits token limits, you'll need to purchase credits
❌ **No smart routing** - No automatic model selection

## What Happens When Enabled

✅ **Claude Code works normally** - Uses Claude API directly (primary)
✅ **Automatic fallback** - When Claude hits limits, uses OpenAI
✅ **Smart routing** - Optimal model selection when explicitly requested
⚠️ **Tools available** - Claude Code can call ChainMind tools if needed

## Recommended Setup

For your `ks w` kitty session:

**If you want pure Claude (no ChainMind):**
```yaml
# config/chainmind.yaml
enabled: false
```

**If you want fallback when Claude hits limits:**
```yaml
# config/chainmind.yaml
enabled: true
```

The default behavior (enabled: true) is safe because:
- Claude Code uses Claude API by default
- ChainMind is only called when Claude hits limits
- You can always ignore ChainMind tools if you don't want to use them

## Quick Check

To see if ChainMind is currently routing queries:

1. **Check if tools are available** - Look in Claude Code's tool list
2. **Check logs** - Look for ChainMind calls in `backend/data/logs/`
3. **Check config** - `cat config/chainmind.yaml | grep enabled`

## Summary

- **Default**: ChainMind is enabled but NOT routing queries automatically
- **Claude Code**: Uses Claude API directly (primary)
- **ChainMind**: Only used as fallback when Claude hits limits
- **To disable**: Set `enabled: false` in config
- **To enable**: Set `enabled: true` in config (default)
