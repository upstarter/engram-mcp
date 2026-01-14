# ChainMind Integration

## Overview

engram-mcp integrates with ChainMind to provide:

1. **Automatic Fallback**: Falls back to OpenAI/Ollama when Claude hits token limits
2. **Smart Routing**: Two-tier routing with cost optimization
3. **Prompt Generation**: Intelligent prompt crafting with engram-mcp context
4. **Multi-Model Verification**: Verify responses with alternative models
5. **Agent Context**: Tracks agent_role and agent_id for context isolation

## Quick Start

### Prerequisites

1. ChainMind installed at `/mnt/dev/ai/ai-platform/chainmind`
2. ChainMind DI container initialized
3. Alternative providers configured (OpenAI, Ollama, etc.)

### Usage

The integration adds three new MCP tools that Claude can use:

#### 1. `chainmind_generate` - Text Generation with Fallback

```python
# Claude can call this tool
result = await call_tool("chainmind_generate", {
    "prompt": "Consolidate these memories...",
    "prefer_claude": True,  # Try Claude first
    "temperature": 0.7
})
```

**Features**:
- Tries Claude first (your preferred provider)
- Automatically falls back to OpenAI/Ollama when Claude hits usage limits
- Returns provider used and fallback status

#### 2. `chainmind_generate_prompt` - Optimized Prompt Generation

```python
# Generate optimized prompt for Claude
result = await call_tool("chainmind_generate_prompt", {
    "task": "Write a function to calculate Fibonacci",
    "strategy": "balanced",  # concise, detailed, structured, balanced
    "project": "my-project"  # Optional, auto-detected
})
```

**Features**:
- Incorporates relevant memories from engram-mcp
- Multiple prompt strategies
- Project-aware context

#### 3. `chainmind_verify` - Multi-Model Verification

```python
# Verify Claude response with alternative models
result = await call_tool("chainmind_verify", {
    "response": "Generated response text",
    "original_prompt": "Original prompt",
    "verification_providers": ["openai"]
})
```

## Configuration

### Environment Variable

Set `ENGRAM_AUTO_APPROVE=true` to auto-approve all memories (skip confirmation).

### Config File

Create `~/.engram/config/engram.yaml`:

```yaml
auto_approve: false  # Set to true for auto-approval
```

### ChainMind Config

Optional config at `~/.engram/config/chainmind.yaml`:

```yaml
enabled: true
fallback:
  providers:
    - openai
    - ollama
  auto_fallback: true
```

## How It Works

### Usage Limit Detection

When Claude hits its monthly usage limit:

1. ChainMind detects `QuotaExceededError` or usage limit indicators
2. Automatically tries fallback providers (OpenAI, Ollama)
3. Returns result from fallback provider
4. Reports fallback status to Claude

### Error Detection

The system detects usage limits by checking for:
- `QuotaExceededError` exception type
- Error code `CM-1801` (ChainMind quota exceeded)
- Error messages containing: "quota exceeded", "usage limit", "insufficient credits", etc.

### Fallback Chain

Default fallback order:
1. Claude (anthropic) - tried first
2. OpenAI - first fallback
3. Ollama - second fallback

## Testing

### Test Helper Import

```bash
cd /mnt/dev/ai/engram-mcp
python3 -c "from engram.chainmind_helper import get_helper; print('OK')"
```

### Test Prompt Generator

```bash
python3 -c "from engram.prompt_generator import PromptGenerator; print('OK')"
```

### Test Server Tools

```bash
python3 -m engram.server
# Then test tools via MCP client
```

## Troubleshooting

### ChainMind Not Available

If ChainMind helper is not available:
- Check ChainMind is installed at `/mnt/dev/ai/ai-platform/chainmind`
- Verify ChainMind DI container can be initialized
- Check error messages in stderr

### Import Errors

If you get import errors:
- Ensure ChainMind path is correct
- Check Python path includes ChainMind
- Verify dependencies are installed

### Provider Errors

If fallback providers fail:
- Check provider API keys are configured
- Verify providers are available in ChainMind
- Check network connectivity

## Benefits

1. **Avoid Extra Credits**: No need to purchase extra Claude credits when limit is hit
2. **Seamless Fallback**: Automatic provider switching
3. **Better Prompts**: Context-aware prompt generation
4. **Quality Assurance**: Multi-model verification for critical tasks

## Example Workflow

### Memory Consolidation with Fallback

```
1. Claude calls engram_consolidate(action="find_candidates")
   → Finds similar memories

2. Claude calls chainmind_generate(
       prompt="Consolidate these memories...",
       prefer_claude=True
   )
   → Tries Claude first
   → If Claude hits limit, automatically uses OpenAI
   → Returns consolidated text

3. Claude calls engram_consolidate(
       action="consolidate",
       content=consolidated_text
   )
   → Stores consolidated memory
```

## Files Created

- `/mnt/dev/ai/engram-mcp/engram/chainmind_helper.py` - ChainMind integration helper
- `/mnt/dev/ai/engram-mcp/engram/prompt_generator.py` - Prompt generation for Claude
- `/mnt/dev/ai/engram-mcp/config/chainmind.yaml` - ChainMind configuration
- `/mnt/dev/ai/engram-mcp/tests/test_chainmind_integration.py` - Integration tests

## Files Modified

- `/mnt/dev/ai/engram-mcp/engram/server.py` - Added three new MCP tools

## Next Steps

1. Test the integration with Claude Code
2. Verify usage limit detection works
3. Test fallback to alternative providers
4. Use prompt generation for better Claude responses
