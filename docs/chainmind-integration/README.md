# ChainMind Integration

## Overview

engram-mcp integrates with ChainMind to provide automatic fallback when Claude hits token limits, intelligent prompt generation, and multi-model verification.

## Quick Start

1. **Configuration**: `config/chainmind.yaml`
2. **Enable/Disable**: Set `enabled: true/false` or `CHAINMIND_ENABLED=false`
3. **Usage**: Tools automatically available via MCP

## Architecture

```
Claude Code → engram-mcp MCP Server → ChainMindHelper → TwoTierRouter → Provider
```

**Key Components**:
- `engram/chainmind_helper.py` - Main adapter
- `engram/server.py` - MCP tool handlers
- `engram/query_logger.py` - Query logging

## MCP Tools

- `chainmind_generate` - Text generation with fallback
- `chainmind_generate_prompt` - Optimized prompt generation
- `chainmind_verify` - Multi-model verification
- `chainmind_generate_batch` - Batch generation

## Configuration

```yaml
# config/chainmind.yaml
enabled: true
model_selection:
  default_strategy: auto
  prefer_api_models: true
cost_optimization:
  mode: budget_only
```

## Request Flow

1. User query → MCP server
2. Extract `agent_role` and `agent_id` from state files
3. Call ChainMindHelper with context
4. StrategicRouter analyzes request (with agent context)
5. Model selection (cost optimization if budget exceeded)
6. TacticalRouter executes
7. Response returned to Claude Code

## Agent Context

- **agent_role**: Extracted from `~/.spc/projects/state/role`
- **agent_id**: Constructed as `role:session_id`
- **Isolation**: Each agent's context history tracked separately

## Troubleshooting

- **ChainMind not initializing**: Check API keys, dependencies
- **Wrong model selected**: Check InputAnalyzer classification
- **Cost optimization not working**: Verify budget constraints set

## See Also

- [How ChainMind Selects Models](./HOW_CHAINMIND_SELECTS_MODELS.md) - Model selection explained
- [ChainMind Setup](./CHAINMIND_SETUP.md) - Setup instructions
- [ChainMind Disable](./CHAINMIND_DISABLE.md) - How to disable

