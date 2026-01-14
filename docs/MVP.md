# Engram MVP (v0.1)

> **Honest documentation for the current state**

This document describes what Engram v0.1 actually provides - not the full vision, but what's implemented and ready to use.

---

## What's Included

### 3 Core Tools

| Tool | Description | Status |
|------|-------------|--------|
| `engram_remember` | Store a memory with type and importance | ✅ Working |
| `engram_recall` | Search memories by semantic similarity | ✅ Working |
| `engram_context` | Get relevant context for current work | ✅ Working |

### Storage

- **SQLite**: Single table for all memories
- **ChromaDB**: Vector embeddings for semantic search
- **No knowledge graph yet** - just flat memories

### Features

| Feature | Status |
|---------|--------|
| Semantic search | ✅ Working |
| Project detection from cwd | ✅ Basic (path matching) |
| Memory types (fact, preference, etc.) | ✅ Working |
| Importance scoring | ✅ Working |
| Timestamps | ✅ Working |

---

## What's NOT Included (Yet)

### Deferred to Later Phases

| Feature | Why Deferred |
|---------|--------------|
| Knowledge graph | Adds complexity, validate basics first |
| Decision journal | Nice-to-have, not core |
| Claude Code hooks | Need to research feasibility first |
| Auto-capture | Depends on hooks |
| Explainable retrieval | Polish feature |
| Memory decay | Optimization |
| CLI tool | Can use MCP tools directly |
| `engram_entity` | Needs knowledge graph |
| `engram_decide` | Phase 3 |
| `engram_forget` | Phase 5 |
| `engram_stats` | Phase 5 |

---

## MVP Schema

### SQLite Table

```sql
CREATE TABLE memories (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    memory_type TEXT DEFAULT 'fact',
    project TEXT,
    importance REAL DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accessed_at TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    embedding_id TEXT  -- Reference to ChromaDB
);

CREATE INDEX idx_memories_project ON memories(project);
CREATE INDEX idx_memories_type ON memories(memory_type);
CREATE INDEX idx_memories_created ON memories(created_at);
```

### ChromaDB Collection

```python
collection = client.create_collection(
    name="engram_memories",
    metadata={"hnsw:space": "cosine"}
)
```

---

## MVP Tools API

### `engram_remember`

```json
{
  "content": "string (required)",
  "memory_type": "fact|preference|episode|solution",
  "importance": 0.0-1.0,
  "project": "string (optional, auto-detected)"
}
```

Returns:
```json
{
  "id": "mem_abc123",
  "stored": true
}
```

### `engram_recall`

```json
{
  "query": "string (required)",
  "project": "string (optional, filter to project)",
  "limit": 10
}
```

Returns:
```json
{
  "memories": [
    {
      "id": "mem_abc123",
      "content": "RTX 5080 requires PyTorch nightly",
      "memory_type": "fact",
      "relevance": 0.89,
      "project": "hallo2",
      "age": "2 days ago"
    }
  ]
}
```

### `engram_context`

```json
{
  "query": "string (optional)",
  "limit": 5
}
```

Returns formatted markdown for injection:
```markdown
## Relevant Context

**Facts:**
- RTX 5080 requires PyTorch nightly cu128
- This project uses TypeScript strict mode

**Project (hallo2):**
- Venv at /mnt/cache/venvs/hallo2
- Last worked on: avatar lip-sync
```

---

## Known Limitations

### 1. No Graph Relationships
Memories are flat - no "X relates to Y" connections yet. If you store "Eric uses TypeScript" and "TypeScript has strict mode", they won't automatically connect.

### 2. Basic Project Detection
Project is detected by simple path matching:
```python
# /mnt/dev/ai/hallo2/src/main.py → project = "hallo2"
# /home/eric/projects/foo/bar.py → project = "foo"
```

No smart inference or configuration.

### 3. No Auto-Capture
You must explicitly call `engram_remember`. No automatic extraction from conversations.

### 4. No Decay
Old memories never fade. Storage will grow indefinitely until you manually clean up.

### 5. No Explanations
`recall` returns relevance scores but doesn't explain *why* a memory matched.

### 6. Single User Only
No multi-user support, no sync, no encryption.

---

## Validation Criteria

After 1 week of personal use, evaluate:

### Usage Metrics
- [ ] **Frequency**: Do I call `recall` more than 5 times per day?
- [ ] **Relevance**: Are >50% of returned memories actually useful?
- [ ] **Storage**: Am I actively using `remember` to store things?

### Qualitative Assessment
- [ ] Does it reduce repetition in conversations?
- [ ] Is project detection helpful or annoying?
- [ ] What memories do I wish it had captured automatically?
- [ ] What's missing that would make this 10x better?

### Decision Point
- **If validates** → Proceed to Phase 2 (knowledge graph)
- **If fails** → Identify what didn't work, consider pivot

---

## Feedback Requested

If you're using the MVP, I'd love to know:

1. **What worked well?**
   - Which memories were most useful?
   - Did semantic search find what you expected?

2. **What was frustrating?**
   - False positives in search?
   - Missing features you expected?

3. **What would you add?**
   - Specific features?
   - Different workflow?

File issues at: https://github.com/creator-ai-studio/engram-mcp/issues

---

## Upgrading from MVP

When full features are added:

1. **Database migration** will be automatic
2. **Existing memories** will be preserved
3. **New features** opt-in by default

Your MVP data is safe.

---

## Technical Notes

### Embedding Model
Using `all-MiniLM-L6-v2` (384 dimensions, fast, good quality).
- ~90MB model
- GPU accelerated if available
- Falls back to CPU

### Performance
- Store: ~50ms (embedding + SQLite + ChromaDB)
- Recall: ~100ms (embedding + vector search)
- First load: ~2s (model loading)

### Storage Size
Rough estimates:
- 1000 memories ≈ 5MB SQLite + 50MB ChromaDB
- Embedding model: 90MB (shared)

---

*This is v0.1 - expect rough edges. Your feedback shapes what comes next.*
