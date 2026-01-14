#!/usr/bin/env python3
"""
Bootstrap Engram with its Founding Memories.

This script stores the development philosophy used to build Engram.
These memories become Engram's "knowledge of how to build things."

Run this once after installation:
    python scripts/bootstrap.py

Then when you start a NEW project and ask:
    "How should I approach this?"

Engram will surface the universal principles used here.
"""

from engram.storage import MemoryStore


def bootstrap():
    """Store the founding memories in Engram."""

    print("🧠 Bootstrapping Engram with founding memories...\n")

    store = MemoryStore()

    # =================================================================
    # LAYER 1: UNIVERSAL PRINCIPLES
    # These should surface for ANY new project
    # =================================================================

    universal = [
        {
            "content": "README-driven development: write comprehensive documentation first, then build to match. This creates accountability, clarifies thinking, and produces marketing assets as a byproduct.",
            "memory_type": "philosophy",
            "importance": 0.95,
            "project": None,
        },
        {
            "content": "Tests should serve double-duty: verification AND marketing/demo assets. Each test category can map to a video concept. Fixtures should use real, meaningful examples - not synthetic data.",
            "memory_type": "philosophy",
            "importance": 0.9,
            "project": None,
        },
        {
            "content": "MVP with validation criteria: define success metrics BEFORE building. Ask 'does this actually help?' rather than 'is this technically impressive?' Build the minimum to validate, then expand.",
            "memory_type": "philosophy",
            "importance": 0.9,
            "project": None,
        },
        {
            "content": "Decision journaling: record WHY you made choices, not just WHAT you chose. Include alternatives considered and constraints that informed the decision. Future you will forget the context.",
            "memory_type": "philosophy",
            "importance": 0.85,
            "project": None,
        },
        {
            "content": "Concentric documentation: create docs at multiple levels - full vision (README), current reality (MVP.md), and technical depth (architecture.md). Be honest about what exists vs what's planned.",
            "memory_type": "philosophy",
            "importance": 0.8,
            "project": None,
        },
        {
            "content": "Three-layer memory structure: Universal principles (any project), Domain patterns (similar tech), Project-specific decisions. This enables smart context retrieval without information overload.",
            "memory_type": "philosophy",
            "importance": 0.85,
            "project": None,
        },
    ]

    # =================================================================
    # LAYER 2: DOMAIN PATTERNS (Python/MCP/AI)
    # These should surface for similar technology stacks
    # =================================================================

    domain = [
        {
            "content": "MCP (Model Context Protocol) servers use stdio transport with JSON-RPC. Define tools with JSON schemas. Use mcp.server.Server and stdio_server() for the connection.",
            "memory_type": "pattern",
            "importance": 0.8,
            "project": None,
        },
        {
            "content": "For local text embeddings, sentence-transformers with all-MiniLM-L6-v2 is a good balance of speed and quality. 384 dimensions, ~90MB model, GPU-accelerated if available.",
            "memory_type": "pattern",
            "importance": 0.8,
            "project": None,
        },
        {
            "content": "ChromaDB works well for vector storage: persistent, supports GPU, cosine similarity with HNSW index. Use PersistentClient for data that survives restarts.",
            "memory_type": "pattern",
            "importance": 0.8,
            "project": None,
        },
        {
            "content": "Python packaging: use pyproject.toml (not setup.py). Define optional dependencies like [dev] for testing and [gpu] for acceleration. Use hatchling as build backend.",
            "memory_type": "pattern",
            "importance": 0.75,
            "project": None,
        },
        {
            "content": "For hybrid search (text + vectors), store structured data in SQLite and embeddings in a vector DB. Join results by ID. SQLite handles temporal queries well, vectors handle semantic similarity.",
            "memory_type": "pattern",
            "importance": 0.8,
            "project": None,
        },
    ]

    # =================================================================
    # LAYER 3: ENGRAM-SPECIFIC DECISIONS
    # These should ONLY surface when working on Engram
    # =================================================================

    project = [
        {
            "content": "Engram architecture decision: SQLite for structured data + ChromaDB for vectors + JSON for knowledge graph (future). Avoided heavy dependencies like Neo4j, Redis, or PostgreSQL for MVP simplicity.",
            "memory_type": "decision",
            "importance": 0.85,
            "project": "engram-mcp",
        },
        {
            "content": "Engram MVP scope: only 3 MCP tools (remember, recall, context). Validate that core memory value exists before building all 7 planned tools. Success = user recalls >5x/day, >50% relevant results.",
            "memory_type": "decision",
            "importance": 0.9,
            "project": "engram-mcp",
        },
        {
            "content": "Engram project detection: regex patterns on cwd path like /mnt/dev/ai/(?P<project>[^/]+). Auto-detects current project to prioritize relevant memories without manual tagging.",
            "memory_type": "decision",
            "importance": 0.75,
            "project": "engram-mcp",
        },
        {
            "content": "Engram retrieval scoring: similarity * 0.5 + recency * 0.2 + importance * 0.2 + access_frequency * 0.1, with 2x boost for current project. Balances relevance with freshness and user priorities.",
            "memory_type": "decision",
            "importance": 0.8,
            "project": "engram-mcp",
        },
        {
            "content": "Engram storage location: ~/.engram/data/ with memories.db (SQLite) and chromadb/ directory. Single-user, local-first, no cloud dependencies for MVP.",
            "memory_type": "decision",
            "importance": 0.7,
            "project": "engram-mcp",
        },
    ]

    # Store all memories
    counts = {"universal": 0, "domain": 0, "project": 0}

    print("Storing Layer 1 (Universal Principles)...")
    for mem in universal:
        store.remember(**mem)
        counts["universal"] += 1

    print("Storing Layer 2 (Domain Patterns)...")
    for mem in domain:
        store.remember(**mem)
        counts["domain"] += 1

    print("Storing Layer 3 (Project Decisions)...")
    for mem in project:
        store.remember(**mem)
        counts["project"] += 1

    # Show stats
    stats = store.get_stats()

    print(f"""
✅ Bootstrap complete!

Memories stored:
  • Universal principles: {counts['universal']}
  • Domain patterns: {counts['domain']}
  • Project decisions: {counts['project']}
  • Total: {stats['total_memories']}

Data location: ~/.engram/data/

Test it out:
  • Query "how to approach new project" → should get universal principles
  • Query "MCP server setup" → should get domain patterns
  • Query "engram architecture" (from engram dir) → should get project decisions

Engram now knows how it was built! 🧠
""")


if __name__ == "__main__":
    bootstrap()
