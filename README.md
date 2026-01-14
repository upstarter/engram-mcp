# Engram MCP

> *"The physical trace of a memory in the brain"*

**Give your AI assistant a memory.** Persistent, semantic, human-inspired.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

---

## The Problem

Every Claude user knows this pain:

```
You: "Remember yesterday when we fixed that GPU issue?"
Claude: "I don't have memory of previous conversations."

You: "We discussed using TypeScript for this project"
Claude: "I don't recall that conversation."
```

**Claude forgets everything between sessions.** Engram fixes that.

---

## Features

| Feature | Description |
|---------|-------------|
| **Semantic Search** | Find memories by meaning, not keywords |
| **Knowledge Graph** | Entity relationships via NetworkX |
| **Temporal Decay** | Recent/accessed memories rank higher |
| **Contradiction Detection** | Warns before storing conflicting info |
| **Auto-Consolidation** | Merge similar memories into wisdom |
| **Project-Aware** | Auto-detects project from working directory |

---

## Quick Start

### Installation

```bash
cd /mnt/dev/ai/engram-mcp
pip install -e .
```

### Configure Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "engram": {
      "command": "/mnt/dev/ai/engram-mcp/venv/bin/python",
      "args": ["-m", "engram.server"]
    }
  }
}
```

---

## MCP Tools

### `engram_remember` - Store a memory

```json
{
  "content": "User prefers functional React components",
  "memory_type": "preference",
  "importance": 0.8,
  "check_conflicts": true,
  "supersede": ["mem_old123"]
}
```

**Memory types:** `fact`, `preference`, `decision`, `solution`, `philosophy`, `pattern`

**Conflict detection:** Set `check_conflicts: true` to check for contradictions before storing. Use `supersede: [ids]` to replace old memories.

### `engram_recall` - Search memories

```json
{
  "query": "React component preferences",
  "limit": 5,
  "project": "my-project",
  "memory_types": ["preference", "decision"]
}
```

Returns memories ranked by composite score:
- 50% semantic similarity
- 25% importance
- 15% freshness (temporal decay)
- 10% access frequency (reinforcement)

### `engram_context` - Get relevant context

```json
{
  "query": "setting up the build system",
  "limit": 5
}
```

Auto-detects project from cwd, returns project-specific + universal memories.

### `engram_related` - Find by entity

```json
{
  "entity_type": "projects",
  "entity_name": "studioflow",
  "limit": 5
}
```

Or find memories related to a specific memory:

```json
{
  "memory_id": "mem_abc123",
  "limit": 5
}
```

Uses knowledge graph traversal instead of semantic search.

### `engram_consolidate` - Merge similar memories

Find clusters:
```json
{
  "action": "find_candidates",
  "similarity_threshold": 0.80
}
```

Merge them:
```json
{
  "action": "consolidate",
  "memory_ids": ["mem_1", "mem_2", "mem_3"],
  "consolidated_content": "Merged wisdom from 3 memories..."
}
```

---

## Architecture

```
~/.engram/data/
├── memories.db          # SQLite: content, metadata, timestamps
├── chromadb/            # Vector embeddings (HNSW index)
└── knowledge_graph.json # NetworkX entity relationships
```

### Storage Layers

| Layer | Technology | Purpose |
|-------|------------|---------|
| Structured | SQLite | Content, metadata, access tracking |
| Semantic | ChromaDB | Vector embeddings, similarity search |
| Relational | NetworkX | Entity extraction, graph traversal |

### Scoring Algorithm

```python
score = (
    similarity * 0.50 +      # Semantic relevance
    importance * 0.25 +      # User-assigned weight
    freshness * 0.15 +       # Temporal decay (30-day half-life)
    reinforcement * 0.10    # Access frequency boost
)
```

### Entity Extraction

Automatically extracts from memory content:
- **Projects:** studioflow, engram, CHANNEL, etc.
- **Tools:** docker, claude, git, etc.
- **Concepts:** episode, phase, MVP, etc.
- **Episodes:** EP001, EP002, etc.

---

## Integration

### With `proj` command (auto-capture)

Phase transitions and ideas are automatically captured:

```bash
proj idea "Video about AI memory systems"
# → Stored to engram automatically

proj EP001 advance
# → Phase transition captured
```

### Git hooks

Install commit hooks to capture decisions:

```bash
~/.spc/bin/engram-hook install /path/to/repo
```

Commits with keywords (decision, chose, architecture) are auto-captured.

### engram-bridge CLI

```bash
# Store a memory
engram-bridge remember "SQLite for MVP simplicity" --type decision

# Get context with proj fusion
engram-bridge context --query "database setup"

# Capture a decision
engram-bridge capture-decision "Use PostgreSQL" --context "Need JSONB support"
```

---

## Configuration

Data stored at `~/.engram/data/` by default.

Embedding model: `all-MiniLM-L6-v2` (384 dimensions, ~90MB)

Project detection patterns:
- `/mnt/dev/ai/<project>/`
- `/home/<user>/projects/<project>/`
- `/workspace/<project>/`

---

## Roadmap

- [x] Core MCP server
- [x] SQLite + ChromaDB storage
- [x] Semantic search with composite scoring
- [x] Knowledge graph (NetworkX)
- [x] Entity extraction
- [x] Temporal decay + reinforcement
- [x] Contradiction detection
- [x] Auto-consolidation
- [x] Project detection
- [x] Auto-capture hooks (proj, git)
- [ ] Web dashboard
- [ ] Import/export

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Built with:
- [MCP (Model Context Protocol)](https://modelcontextprotocol.io/)
- [ChromaDB](https://www.trychroma.com/)
- [Sentence Transformers](https://www.sbert.net/)
- [NetworkX](https://networkx.org/)
