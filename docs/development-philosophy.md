# Development Philosophy

> **Engram's Founding Memory** - This document captures the meta-development approach used to build Engram. It's the first real memory Engram will store, serving as both documentation and validation test data.

---

## The Three-Layer Memory Model

Every piece of knowledge exists at one of three levels:

### Layer 1: Universal Principles
*Applies to any project, any domain, any language*

| Principle | Description |
|-----------|-------------|
| **README-Driven Development** | Write comprehensive docs FIRST. Build to match. Creates accountability, clarifies thinking, produces marketing assets. |
| **Tests as Marketing Assets** | Test fixtures should be demo-worthy. Each test category maps to a YouTube video concept. Double-duty: verification AND content. |
| **MVP with Validation Criteria** | Define success metrics before building. "Does this actually help?" > "Is this technically impressive?" |
| **Decision Journaling** | Record WHY not just WHAT. Future you will forget the context. "Chose X because Y, considered Z." |
| **Concentric Documentation** | Full vision (README) + Current reality (MVP.md) + Technical depth (architecture.md). Honest about what exists vs planned. |

### Layer 2: Domain Patterns
*Applies to similar technology/problem space*

| Domain | Patterns |
|--------|----------|
| **MCP Servers** | stdio transport, JSON-RPC, tool definitions with schemas |
| **Python Packaging** | pyproject.toml, optional dependencies `[dev]`, `[gpu]` |
| **Embeddings** | sentence-transformers for local, all-MiniLM-L6-v2 is fast/good |
| **Vector Storage** | ChromaDB for persistence, cosine similarity, HNSW index |
| **Hybrid Search** | Vector similarity + metadata filtering + recency weighting |

### Layer 3: Project Decisions
*Applies only to specific project context*

| Decision | Reasoning | Alternatives Considered |
|----------|-----------|------------------------|
| SQLite + ChromaDB + JSON | No heavy deps (Neo4j, Redis), single-user MVP, easy to inspect | PostgreSQL (overkill), pure JSON (no queries) |
| 3 tools for MVP | Validate core value before building 7 | Full toolset (premature) |
| Project detection from cwd | Automatic context, no manual tagging | Explicit project parameter (friction) |

---

## Test-Driven Development as Content Strategy

### Test Categories Map to YouTube Videos

| Test Category | YouTube Concept | Demo Value |
|---------------|-----------------|------------|
| **"The Problem"** | "Claude Forgets Everything" | Show the pain point - re-explaining context |
| **"The Solution"** | "Give Claude a Memory" | Memory storage and retrieval working |
| **"Real Workflows"** | "AI That Knows Your Project" | Project detection, context switching |
| **"Decision Archaeology"** | "Never Lose Your Reasoning" | Retrieve decisions with full context |
| **"Layer Filtering"** | "Smart Context, Not All Context" | Right memories surface for right queries |

### Fixtures Are Demos

```python
# BAD: Synthetic test data
memories = ["test1", "test2", "test3"]

# GOOD: Real, meaningful examples that demonstrate value
memories = [
    {
        "content": "README-driven development: write docs first, build to match",
        "type": "philosophy",
        "importance": 0.9,
        "layer": "universal"
    },
    {
        "content": "MCP servers use stdio transport with JSON-RPC protocol",
        "type": "pattern",
        "importance": 0.7,
        "layer": "domain"
    },
    {
        "content": "Engram MVP: 3 tools (remember, recall, context) to validate core value",
        "type": "decision",
        "importance": 0.8,
        "layer": "project",
        "project": "engram-mcp"
    }
]
```

---

## Validation Strategy

### Phase 1: Build Engram MVP
- Tests define the spec
- Store real memories during development
- Each test is a potential demo clip

### Phase 2: Bootstrap Engram with Its Own Development
Store these memories AS we build:
- Layer 1: Universal principles (this document)
- Layer 2: Python/MCP patterns discovered
- Layer 3: Engram-specific decisions

### Phase 3: Validate on NEXT Project
Start building something different:
- Query: "how should I approach this new project?"
- Expected: Layer 1 surfaces, Layer 3 does NOT
- Document the experience for YouTube content

### Success Criteria

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Layer 1 retrieval | 100% for generic queries | "new project" → philosophy surfaces |
| Layer 2 retrieval | 80%+ for domain queries | "MCP setup" → patterns surface |
| Layer 3 filtering | 0% false positives | Engram decisions don't surface for Hallo2 |
| Daily usage | >5 recalls/day | Personal usage tracking |
| Relevance | >50% useful | Subjective but noticeable |

---

## Why This Approach Works

### Real Data > Synthetic Data
- We're actually building something, not making up examples
- The memories have genuine context and reasoning
- Validation happens naturally during development

### Double-Duty Everything
- Docs = Marketing + Implementation spec
- Tests = Verification + Demo content
- Fixtures = Test data + Real examples

### Concentric Validation
- Layer 1 validates universal transfer
- Layer 2 validates domain expertise
- Layer 3 validates project specificity
- Together they prove Engram works at all levels

### The Bootstrap IS the Validation
- If Engram can remember how to build things like Engram...
- ...and surface that for future projects...
- ...then it works.

---

## Applying This to Future Projects

When starting any new project, query Engram:
1. "development philosophy" → Layer 1 principles
2. "[technology] patterns" → Layer 2 domain knowledge
3. "similar project decisions" → Layer 3 if relevant

If the right memories surface at the right time, Engram is working.

---

*This document is both documentation AND test data. It will be stored in Engram as the founding memory, then retrieved to validate the system works.*
