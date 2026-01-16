# Engram MCP

Semantic memory system for Claude Code via MCP protocol.

## Architecture Roadmap

**READ FIRST:** `MEMORY_ARCHITECTURE_ROADMAP.md` contains the full improvement plan based on AI memory research.

**Key insight:** Systems that store everything then prune performed 10% WORSE than no memory.

**Priority improvements:**
1. Quality gate at formation (reject low-value content BEFORE storing)
2. Working memory layer (ephemeral buffer, auto-promotes after validation)
3. Adaptive forgetting (per-memory decay based on access patterns)

## Session Start

**First, ensure venv is cached to RAM for fast imports:**
```bash
venv work engram-mcp
```

Then activate: `source /mnt/ramdisk/venvs/engram-mcp/bin/activate`

Or just `cd` here - direnv auto-activates.

## Project Structure

```
engram/
├── server.py           # MCP server entry point
├── storage.py          # SQLite + vector storage
├── chainmind_helper.py # ChainMind integration for fallback
└── prompt_generator.py # Optimized prompt generation
```

## Dependencies

- **Venv:** `/mnt/cache/venvs/engram-mcp/` (or ramdisk when cached)
- **ChainMind:** `/mnt/dev/ai/chainmind` (for model routing/fallback)

## Running

```bash
# As MCP server (stdio)
python -m engram.server

# Test imports
python -c "from engram.server import main; print('OK')"
```

## Key Commands

| Command | Purpose |
|---------|---------|
| `venv work engram-mcp` | Cache venv to RAM (10x faster imports) |
| `venv list` | Check if venv is cached |
| `pytest tests/` | Run tests |
