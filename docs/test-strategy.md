# Test Strategy: Verification Meets Marketing

> Tests that prove Engram works AND create content for Creator AI Studio

---

## Philosophy: Double-Duty Tests

Every test serves two purposes:
1. **Verification**: Does the code work correctly?
2. **Demonstration**: Can this be shown in a YouTube video?

The test suite IS the demo. The fixtures ARE real examples.

---

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures (the founding memories)
├── fixtures/
│   ├── philosophy.py           # Layer 1: Universal principles
│   ├── patterns.py             # Layer 2: Domain patterns
│   └── decisions.py            # Layer 3: Project decisions
│
├── unit/
│   ├── test_storage.py         # SQLite + ChromaDB operations
│   ├── test_embeddings.py      # Vector similarity
│   └── test_project_detection.py
│
├── integration/
│   ├── test_remember_recall.py # Full store → retrieve cycle
│   ├── test_layer_filtering.py # Right memories for right context
│   └── test_mcp_protocol.py    # MCP tool invocations
│
└── demos/                      # YouTube-ready demonstrations
    ├── test_the_problem.py     # "Claude Forgets Everything"
    ├── test_the_solution.py    # "Give Claude a Memory"
    ├── test_real_workflows.py  # "AI That Knows Your Project"
    └── test_decision_archaeology.py  # "Never Lose Your Reasoning"
```

---

## Fixture Design: The Founding Memories

### `conftest.py` - Shared Test Data

```python
import pytest
from engram.storage import MemoryStore

@pytest.fixture
def founding_memories():
    """The three-layer memory structure used across all tests.

    These are REAL memories from Engram's development, not synthetic data.
    They serve as both test fixtures and marketing examples.
    """
    return {
        "layer1_universal": [
            {
                "content": "README-driven development: write comprehensive docs first, build to match. Creates accountability and clarifies thinking.",
                "memory_type": "philosophy",
                "importance": 0.9,
                "project": None,  # Universal - no project
            },
            {
                "content": "Tests should serve double-duty: verification AND marketing assets. Each test category maps to a YouTube video concept.",
                "memory_type": "philosophy",
                "importance": 0.9,
                "project": None,
            },
            {
                "content": "MVP with validation criteria: define success metrics before building. 'Does this actually help?' over 'Is this technically impressive?'",
                "memory_type": "philosophy",
                "importance": 0.9,
                "project": None,
            },
            {
                "content": "Decision journaling: record WHY not just WHAT. Future you will forget the context.",
                "memory_type": "philosophy",
                "importance": 0.85,
                "project": None,
            },
        ],
        "layer2_domain": [
            {
                "content": "MCP servers use stdio transport with JSON-RPC protocol. Define tools with JSON schemas.",
                "memory_type": "pattern",
                "importance": 0.8,
                "project": None,  # Domain-wide, not project-specific
            },
            {
                "content": "For local embeddings, sentence-transformers with all-MiniLM-L6-v2 is fast and good quality. 384 dimensions, ~90MB model.",
                "memory_type": "pattern",
                "importance": 0.8,
                "project": None,
            },
            {
                "content": "ChromaDB for vector storage: persistent, GPU-accelerated, cosine similarity with HNSW index.",
                "memory_type": "pattern",
                "importance": 0.8,
                "project": None,
            },
            {
                "content": "Python packaging: use pyproject.toml with optional dependencies [dev], [gpu]. Avoid setup.py.",
                "memory_type": "pattern",
                "importance": 0.7,
                "project": None,
            },
        ],
        "layer3_project": [
            {
                "content": "Engram architecture: SQLite for structured data + ChromaDB for vectors + JSON for knowledge graph. No heavy dependencies like Neo4j or Redis.",
                "memory_type": "decision",
                "importance": 0.85,
                "project": "engram-mcp",
            },
            {
                "content": "Engram MVP scope: 3 tools only (remember, recall, context). Validate core value before building all 7 planned tools.",
                "memory_type": "decision",
                "importance": 0.9,
                "project": "engram-mcp",
            },
            {
                "content": "Engram project detection: regex on cwd path to auto-detect project. Patterns like /mnt/dev/ai/(?P<project>[^/]+)",
                "memory_type": "decision",
                "importance": 0.75,
                "project": "engram-mcp",
            },
        ],
    }


@pytest.fixture
def memory_store(tmp_path):
    """Fresh memory store for each test."""
    return MemoryStore(data_dir=tmp_path)


@pytest.fixture
def populated_store(memory_store, founding_memories):
    """Memory store pre-populated with founding memories."""
    for layer in founding_memories.values():
        for memory in layer:
            memory_store.remember(**memory)
    return memory_store
```

---

## Demo Tests: YouTube-Ready

### `test_the_problem.py` - "Claude Forgets Everything"

```python
"""
YOUTUBE VIDEO: "The Problem Every Claude User Has"

This test demonstrates the pain point Engram solves.
Run this test, record the output, use in video intro.
"""

class TestTheProblem:
    """Demonstrates why memory matters."""

    def test_session_context_loss(self):
        """DEMO: Context is lost between sessions.

        Scenario:
        - Session 1: User explains they prefer TypeScript
        - Session 2: Claude has no memory of this
        - User must re-explain

        This is the status quo WITHOUT Engram.
        """
        # Session 1
        session1_context = "User said: I prefer TypeScript over JavaScript"

        # Session 2 (new instance, no memory)
        session2_memory = None  # Claude's actual state

        # The problem: previous context is gone
        assert session2_memory is None, "Without Engram, sessions are isolated"

        # This test PASSES because it demonstrates the problem exists
        # The "failure" IS the point - there's no memory

    def test_repeated_explanations(self):
        """DEMO: Same questions asked repeatedly.

        Count how many times common context must be re-explained
        without a memory system.
        """
        common_questions = [
            "What GPU do you have?",
            "What's your project structure?",
            "Which venv should I use?",
            "What was that fix we used last time?",
        ]

        sessions_per_week = 20
        explanations_without_memory = len(common_questions) * sessions_per_week

        # 80 re-explanations per week for just 4 common topics
        assert explanations_without_memory == 80

        # With Engram: 0 re-explanations (query memory instead)
```

### `test_the_solution.py` - "Give Claude a Memory"

```python
"""
YOUTUBE VIDEO: "Finally, Claude Remembers You"

This test demonstrates Engram working. Record this for the "after" segment.
"""

class TestTheSolution:
    """Demonstrates Engram solving the memory problem."""

    def test_memory_persists(self, populated_store):
        """DEMO: Memories survive across sessions.

        Store something, "restart", retrieve it.
        """
        # Store a preference
        memory_id = populated_store.remember(
            content="User prefers TypeScript over JavaScript for new projects",
            memory_type="preference",
            importance=0.8
        )

        # Simulate session boundary (in reality: Claude Code restart)
        # Memory store persists to disk

        # New session: query for preferences
        results = populated_store.recall("TypeScript preferences")

        assert len(results) > 0
        assert "TypeScript" in results[0]["content"]

        # This is the magic moment for the video

    def test_semantic_not_keyword(self, populated_store):
        """DEMO: Find by meaning, not exact text.

        Query with different words, still find relevant memory.
        """
        # Stored: "README-driven development: write docs first"

        # Query with completely different words
        results = populated_store.recall("documentation before coding")

        assert len(results) > 0
        assert "README" in results[0]["content"] or "docs" in results[0]["content"]

        # Semantic search finds it despite no keyword overlap
```

### `test_real_workflows.py` - "AI That Knows Your Project"

```python
"""
YOUTUBE VIDEO: "Context-Aware AI Assistant"

This test demonstrates project detection and context switching.
"""

class TestRealWorkflows:
    """Demonstrates project-aware memory retrieval."""

    def test_project_detection(self, populated_store):
        """DEMO: Engram knows what project you're in.

        cwd determines which memories are prioritized.
        """
        # Simulate being in engram-mcp project
        cwd = "/mnt/dev/ai/engram-mcp/src"

        results = populated_store.context(
            query="design decisions",
            cwd=cwd
        )

        # Should prioritize engram-mcp specific memories
        assert any("Engram" in r["content"] for r in results)

    def test_layer_filtering(self, populated_store):
        """DEMO: Right memories for right context.

        Universal principles surface for any project.
        Project-specific decisions only surface in that project.
        """
        # Generic query from a DIFFERENT project
        cwd = "/mnt/dev/ai/hallo2/src"

        results = populated_store.context(
            query="how to approach development",
            cwd=cwd
        )

        # Should get Layer 1 (universal) but NOT Layer 3 (engram-specific)
        contents = [r["content"] for r in results]

        # Universal philosophy should surface
        assert any("README-driven" in c or "MVP" in c for c in contents)

        # Engram-specific decisions should NOT surface for Hallo2
        assert not any("Engram MVP scope" in c for c in contents)
```

### `test_decision_archaeology.py` - "Never Lose Your Reasoning"

```python
"""
YOUTUBE VIDEO: "Remember WHY, Not Just WHAT"

This test demonstrates decision retrieval with full context.
"""

class TestDecisionArchaeology:
    """Demonstrates decision journaling and retrieval."""

    def test_retrieve_decision_with_reasoning(self, populated_store):
        """DEMO: Get the WHY behind decisions.

        Query past decisions, get full context.
        """
        results = populated_store.recall(
            query="why SQLite",
            memory_types=["decision"]
        )

        assert len(results) > 0
        decision = results[0]["content"]

        # Should include reasoning, not just the choice
        assert "SQLite" in decision
        assert "heavy dependencies" in decision.lower() or "neo4j" in decision.lower()

    def test_alternatives_preserved(self, populated_store):
        """DEMO: Know what was considered and rejected.

        Future you will want to know what else was on the table.
        """
        # Store a decision with alternatives
        populated_store.remember(
            content="Chose ChromaDB over FAISS: better persistence, easier API. Considered Pinecone (too expensive for MVP), Weaviate (too complex).",
            memory_type="decision",
            importance=0.8,
            project="engram-mcp"
        )

        results = populated_store.recall("vector database choice")

        assert len(results) > 0
        assert "FAISS" in results[0]["content"]  # Alternative is preserved
        assert "Pinecone" in results[0]["content"]  # Rejection reason too
```

---

## Integration Tests: Full Cycles

### `test_remember_recall.py`

```python
"""Full store → retrieve cycle with realistic data."""

class TestRememberRecall:

    def test_store_and_retrieve_preserves_content(self, memory_store):
        """Content integrity through the full cycle."""
        original = "The RTX 5080 requires PyTorch nightly cu128 for Blackwell sm_120 support"

        memory_id = memory_store.remember(
            content=original,
            memory_type="fact",
            importance=0.9
        )

        results = memory_store.recall("GPU PyTorch requirements")

        assert len(results) > 0
        assert results[0]["content"] == original
        assert results[0]["id"] == memory_id

    def test_importance_affects_ranking(self, memory_store):
        """Higher importance memories rank higher."""
        memory_store.remember(
            content="Minor style preference",
            memory_type="preference",
            importance=0.3
        )
        memory_store.remember(
            content="Critical security configuration",
            memory_type="fact",
            importance=0.95
        )

        results = memory_store.recall("configuration")

        # Higher importance should rank first
        assert "security" in results[0]["content"].lower()
```

---

## Running Tests for Content

### Generate Demo Output

```bash
# Run demo tests with verbose output (good for screen recording)
pytest tests/demos/ -v --tb=short

# Run specific demo for a video segment
pytest tests/demos/test_the_solution.py -v

# Generate HTML report for review
pytest tests/ --html=report.html
```

### Test Output as Content

Configure pytest to produce clean, recordable output:

```python
# conftest.py additions
def pytest_configure(config):
    """Configure test output for content creation."""
    config.addinivalue_line(
        "markers", "demo: mark test as YouTube-demo-worthy"
    )

# Use custom reporter for clean output
# Consider: pytest-sugar for prettier terminal output
```

---

## Validation Metrics

After running the full test suite, evaluate:

| Metric | Target | Actual |
|--------|--------|--------|
| All demo tests pass | 100% | |
| Layer 1 retrieval accuracy | 100% | |
| Layer 2 retrieval accuracy | 80%+ | |
| Layer 3 false positives | 0% | |
| Semantic search precision | 70%+ | |

---

*This test suite is designed to be recorded. Each test tells a story. The fixtures are real examples from Engram's own development.*
