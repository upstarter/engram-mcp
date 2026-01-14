# Setup Guide

## Quick Setup

1. **Install Dependencies**:
   ```bash
   cd /mnt/dev/ai/engram-mcp
   pip install -e .
   ```

2. **Configure ChainMind** (if using ChainMind integration):
   ```bash
   # Edit config/chainmind.yaml
   enabled: true
   ```

3. **Set API Keys**:
   ```bash
   export ANTHROPIC_API_KEY=your_key
   export OPENAI_API_KEY=your_key
   ```

4. **Configure Claude Code**:
   ```json
   // ~/.claude/settings.json
   {
     "mcpServers": {
       "engram": {
         "command": "/mnt/dev/ai/engram-mcp/venv/bin/python",
         "args": ["-m", "engram.server"]
       }
     }
   }
   ```

## Local Models (Optional)

See [Local Models Setup](./LOCAL_MODELS_SETUP_COMPLETE.md) for Ollama setup.

## Verification

```bash
# Test integration
python -m pytest tests/ -v

# Check ChainMind status
python -c "from engram.chainmind_helper import ChainMindHelper; h = ChainMindHelper(); print(h.is_available())"
```

## See Also

- [Setup Checklist](./SETUP_CHECKLIST.md) - Detailed checklist
- [Install ChainMind Dependencies](./INSTALL_CHAINMIND_DEPS.md) - Dependency installation
