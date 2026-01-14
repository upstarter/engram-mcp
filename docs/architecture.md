# Engram Architecture

> Technical deep dive for contributors and curious users

---

## Design Philosophy

### Human-Inspired Memory

Engram's architecture is inspired by how human memory actually works, based on cognitive science research:

1. **Working Memory**: Short-term, limited capacity, current focus
2. **Episodic Memory**: Events with temporal/spatial context ("when/where did I learn this?")
3. **Semantic Memory**: Facts and knowledge, abstracted from episodes

Current LLMs have no episodic memory - they can't form memories of runtime events. Engram fills this gap.

### Key Principles

- **Persistence over sessions**: Memories survive Claude restarts
- **Semantic over keyword**: Find by meaning, not exact text
- **Context-aware**: Know what project you're in
- **Explainable**: Understand why memories were retrieved
- **Lightweight**: No heavy infrastructure (Neo4j, Redis, etc.)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         MCP Server                               │
│                        (server.py)                               │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │remember │ │ recall  │ │ context │ │ entity  │ │ decide  │   │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘   │
└───────┼──────────┼──────────┼──────────┼──────────┼────────────┘
        │          │          │          │          │
        ▼          ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Unified Memory                              │
│                     (memory/unified.py)                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │   Episodic   │ │   Semantic   │ │  Decisions   │            │
│  │ (episodes,   │ │ (knowledge   │ │ (decision    │            │
│  │  facts)      │ │  graph)      │ │  journal)    │            │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘            │
└─────────┼────────────────┼────────────────┼────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Storage Layer                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │   SQLite     │ │  ChromaDB    │ │    JSON      │            │
│  │ (episodic.db)│ │ (embeddings) │ │ (graph.json) │            │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Storage Layer

### SQLite (episodic.db)

**Why SQLite?**
- Single file, no server
- ACID transactions
- Excellent for temporal queries
- Built into Python

**Schema:**

```sql
-- Core memories table
CREATE TABLE memories (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    memory_type TEXT DEFAULT 'fact',
    project TEXT,
    importance REAL DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accessed_at TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    session_id TEXT,
    embedding_id TEXT,
    metadata JSON
);

-- Decision journal
CREATE TABLE decisions (
    id TEXT PRIMARY KEY,
    decision TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    alternatives JSON,
    constraints JSON,
    outcome TEXT,
    project TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX idx_memories_project ON memories(project);
CREATE INDEX idx_memories_type ON memories(memory_type);
CREATE INDEX idx_memories_created ON memories(created_at DESC);
CREATE INDEX idx_decisions_project ON decisions(project);
```

### ChromaDB (Vector Store)

**Why ChromaDB?**
- GPU-accelerated similarity search
- Persistent storage
- Excellent Python integration
- Active development

**Configuration:**

```python
import chromadb
from chromadb.config import Settings

client = chromadb.PersistentClient(
    path=str(data_dir / "chromadb"),
    settings=Settings(
        anonymized_telemetry=False,
        allow_reset=True,
    )
)

collection = client.get_or_create_collection(
    name="engram_memories",
    metadata={"hnsw:space": "cosine"}  # Cosine similarity
)
```

**Embedding Model:**

```python
from sentence_transformers import SentenceTransformer

# all-MiniLM-L6-v2: Fast, 384 dimensions, good quality
model = SentenceTransformer('all-MiniLM-L6-v2')

# GPU acceleration if available
if torch.cuda.is_available():
    model = model.to('cuda')
```

### JSON (Knowledge Graph)

**Why JSON?**
- Human-readable
- Easy to inspect/debug
- No server needed
- Good enough for moderate scale

**Structure:**

```json
{
  "entities": {
    "RTX-5080": {
      "type": "hardware",
      "observations": [
        "Blackwell architecture sm_120",
        "16GB VRAM",
        "Requires PyTorch nightly cu128"
      ],
      "created_at": "2025-01-09T10:00:00",
      "updated_at": "2025-01-09T15:30:00"
    }
  },
  "relations": [
    {
      "from": "Hallo2",
      "to": "RTX-5080",
      "type": "requires",
      "created_at": "2025-01-09T10:00:00"
    }
  ]
}
```

---

## Retrieval Pipeline

### Overview

```
Query: "GPU setup issues"
         │
         ▼
┌─────────────────────┐
│  1. Embed Query     │  → [0.12, -0.45, 0.78, ...]
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  2. Vector Search   │  → Top 20 candidates by similarity
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  3. Graph Expansion │  → Add related entities
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  4. Project Filter  │  → Boost current project memories
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  5. Recency Decay   │  → Recent memories rank higher
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  6. Final Ranking   │  → Top K results
└─────────────────────┘
         │
         ▼
Return: Memories with scores and explanations
```

### Scoring Formula

```python
def compute_score(memory, query_embedding, current_project):
    # Base: Vector similarity (0-1)
    similarity = cosine_similarity(memory.embedding, query_embedding)

    # Project boost: 2x if same project
    project_factor = 2.0 if memory.project == current_project else 1.0

    # Recency decay: e^(-days/30)
    days_old = (now - memory.created_at).days
    recency_factor = math.exp(-days_old / 30)

    # Importance: User-defined (0-1)
    importance_factor = memory.importance

    # Access frequency boost
    access_factor = 1 + math.log1p(memory.access_count) * 0.1

    # Combined score
    score = (
        similarity * 0.5 +
        recency_factor * 0.2 +
        importance_factor * 0.2 +
        access_factor * 0.1
    ) * project_factor

    return score
```

### Explainable Retrieval

```python
def explain_retrieval(memory, query, score_components):
    explanations = []

    if score_components['similarity'] > 0.8:
        explanations.append(f"High semantic match to '{query}'")

    if score_components['project_boost']:
        explanations.append(f"Same project: {memory.project}")

    if score_components['recency'] > 0.9:
        explanations.append("Very recent memory")

    if memory.access_count > 10:
        explanations.append("Frequently accessed")

    return " • ".join(explanations)
```

---

## Project Detection

### Path-Based Detection

```python
import re
from pathlib import Path

PROJECT_PATTERNS = [
    r"/mnt/dev/ai/(?P<project>[^/]+)",
    r"/home/[^/]+/projects/(?P<project>[^/]+)",
    r"/workspace/(?P<project>[^/]+)",
]

def detect_project(cwd: str) -> str | None:
    for pattern in PROJECT_PATTERNS:
        match = re.match(pattern, cwd)
        if match:
            return match.group("project")
    return None
```

### Configuration Override

```yaml
# ~/.engram/config.yaml
projects:
  patterns:
    - "/mnt/dev/ai/(?P<project>[^/]+)"
    - "~/work/(?P<project>[^/]+)"

  aliases:
    "creator-ai-ecosystem": "creator-ai"
    "ai-platform": "chainmind"
```

---

## Hook Integration (Future)

### Claude Code Hooks

```
UserPromptSubmit
       │
       ▼
┌──────────────────┐
│ engram context   │  → Inject relevant memories
│ --query "$PROMPT"│     before Claude sees prompt
└──────────────────┘


SessionEnd
    │
    ▼
┌──────────────────┐
│ engram extract   │  → Extract learnings from
│ --session $ID    │     conversation summary
└──────────────────┘
```

### Auto-Capture Patterns

```python
CAPTURE_PATTERNS = {
    "preference": [
        r"I (?:prefer|like|want|always use)\s+(.+)",
        r"(?:My|Our) preference is\s+(.+)",
    ],
    "decision": [
        r"(?:Let's|We'll|I'll) (?:use|go with|choose)\s+(.+?)(?:\s+because\s+(.+))?",
        r"(?:Decided|Choosing) to\s+(.+)",
    ],
    "solution": [
        r"(?:The fix|The solution|To solve this)\s+(?:is|was)\s+(.+)",
        r"(?:Fixed|Solved) by\s+(.+)",
    ],
    "learning": [
        r"(?:TIL|I learned|Turns out)\s+(.+)",
        r"(?:Discovered|Found out) that\s+(.+)",
    ],
}
```

---

## Data Flow

### Store Memory

```
engram_remember(content="X prefers Y")
         │
         ▼
┌─────────────────────┐
│ 1. Detect project   │  → project = "hallo2"
│    from cwd         │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ 2. Generate         │  → [0.12, -0.45, 0.78, ...]
│    embedding        │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ 3. Store in         │  → INSERT INTO memories...
│    SQLite           │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ 4. Store in         │  → collection.add(...)
│    ChromaDB         │
└─────────────────────┘
         │
         ▼
Return: {"id": "mem_abc123", "stored": true}
```

### Recall Memories

```
engram_recall(query="GPU issues", limit=5)
         │
         ▼
┌─────────────────────┐
│ 1. Embed query      │  → [0.08, -0.52, 0.81, ...]
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ 2. ChromaDB search  │  → Top 20 candidates
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ 3. Fetch metadata   │  → SQLite JOIN
│    from SQLite      │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ 4. Re-rank with     │  → Apply project boost,
│    full scoring     │     recency, importance
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ 5. Generate         │  → "High semantic match..."
│    explanations     │
└─────────────────────┘
         │
         ▼
Return: {"memories": [...], "explanations": [...]}
```

---

## Performance Considerations

### Embedding Caching

```python
# LRU cache for repeated queries
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_embedding(text: str) -> list[float]:
    return model.encode(text).tolist()
```

### Batch Operations

```python
# Batch store for efficiency
async def store_batch(memories: list[dict]):
    embeddings = model.encode([m['content'] for m in memories])

    # Batch SQLite insert
    cursor.executemany(INSERT_SQL, memories)

    # Batch ChromaDB add
    collection.add(
        ids=[m['id'] for m in memories],
        embeddings=embeddings.tolist(),
        documents=[m['content'] for m in memories]
    )
```

### Index Tuning

```python
# ChromaDB HNSW parameters for large collections
collection = client.get_or_create_collection(
    name="engram_memories",
    metadata={
        "hnsw:space": "cosine",
        "hnsw:construction_ef": 200,  # Build quality
        "hnsw:search_ef": 100,        # Search quality
        "hnsw:M": 16,                 # Connections per node
    }
)
```

---

## Security Considerations

### Local-First
- All data stored locally (~/.engram/)
- No network calls except embedding model download
- No telemetry

### Future: Encryption at Rest

```python
# Planned for Pro tier
from cryptography.fernet import Fernet

def encrypt_content(content: str, key: bytes) -> bytes:
    return Fernet(key).encrypt(content.encode())

def decrypt_content(encrypted: bytes, key: bytes) -> str:
    return Fernet(key).decrypt(encrypted).decode()
```

---

## Testing Strategy

### Unit Tests

```python
# test_storage.py
def test_sqlite_store_and_retrieve():
    store = SQLiteStore(":memory:")
    memory_id = store.store(content="Test", memory_type="fact")
    retrieved = store.get(memory_id)
    assert retrieved.content == "Test"

# test_retrieval.py
def test_semantic_search_finds_similar():
    store.store("Python is a programming language")
    store.store("JavaScript runs in browsers")

    results = store.search("coding languages")
    assert "Python" in results[0].content
```

### Integration Tests

```python
# test_mcp.py
async def test_remember_recall_cycle():
    # Store via MCP
    result = await call_tool("engram_remember", {
        "content": "Integration test memory",
        "memory_type": "fact"
    })
    assert result["stored"]

    # Recall via MCP
    results = await call_tool("engram_recall", {
        "query": "integration test"
    })
    assert len(results["memories"]) > 0
```

---

## Future Architecture

### Phase 2: Knowledge Graph

```
┌─────────────────────────────────────────┐
│           Semantic Memory               │
│  ┌─────────┐    ┌─────────┐            │
│  │ Entity  │───▶│ Entity  │            │
│  │ "Eric"  │    │"TypeScript"          │
│  └─────────┘    └─────────┘            │
│       │              │                  │
│       │   "prefers"  │  "has feature"  │
│       ▼              ▼                  │
│  ┌─────────────────────────┐           │
│  │ Relation: prefers       │           │
│  │ Observation: strict mode│           │
│  └─────────────────────────┘           │
└─────────────────────────────────────────┘
```

### Phase 4: Hooks + Auto-Capture

```
┌────────────────────────────────────────────────────────────┐
│                    Hook Pipeline                            │
│                                                             │
│  UserPrompt ──▶ Pattern Match ──▶ Extract ──▶ Store        │
│       │              │                           │          │
│       │         "I prefer X"               preferences      │
│       │         "Let's use Y"              decisions        │
│       │         "The fix was Z"            solutions        │
│       │                                                     │
│       ▼                                                     │
│  Context Inject ◀── Retrieve ◀── Query                     │
└────────────────────────────────────────────────────────────┘
```

---

*Architecture evolves based on validation. This document will be updated as we learn what works.*
