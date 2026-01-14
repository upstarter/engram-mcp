# ChainMind Integration Setup Checklist

## Quick Checklist

### API Keys
- [ ] `ANTHROPIC_API_KEY` - Get from https://console.anthropic.com/api-keys
- [x] `OPENAI_API_KEY` - Already configured ✓

### Dependencies
- [ ] `sentence-transformers` - Install in ChainMind environment
- [ ] `sentence-transformers` - Install in engram-mcp environment
- [x] `aiofiles` - Already installed in engram-mcp ✓

### Configuration Files
- [ ] Create `~/.chainmind.env` with API keys
- [ ] Or add keys to `~/.env`

## Setup Commands

```bash
# 1. Install dependencies
cd /mnt/dev/ai/ai-platform/chainmind
pip install sentence-transformers aiofiles

cd /mnt/dev/ai/engram-mcp
pip install sentence-transformers

# 2. Add API keys to ~/.chainmind.env
cat >> ~/.chainmind.env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
OPENAI_API_KEY=sk-your-openai-key-here
EOF

# 3. Verify setup
cd /mnt/dev/ai/ai-platform/chainmind
python3 utils/load_env.py

# 4. Test integration
cd /mnt/dev/ai/engram-mcp
python3 test_real_production.py
```

## What You'll Get

After setup:
- ✅ Real Claude API calls
- ✅ Automatic fallback to OpenAI when Claude hits limits
- ✅ Context-aware prompt generation
- ✅ Full production workflow

## Current Status

- ✅ Integration code: Working
- ✅ Error detection: Working (6/6 patterns)
- ✅ Provider routing: Configured
- ⚠️ API keys: Need ANTHROPIC_API_KEY
- ⚠️ Dependencies: Need sentence-transformers
