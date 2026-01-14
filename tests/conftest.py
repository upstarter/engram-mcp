"""
Shared test fixtures - The Founding Memories.

These fixtures are REAL memories from Engram's development.
They serve as both test data AND marketing examples.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import sys
import os


# Check if ChainMind is available and functional
CHAINMIND_PATH = "/mnt/dev/ai/ai-platform/chainmind"
CHAINMIND_AVAILABLE = False

if os.path.exists(CHAINMIND_PATH):
    # Path exists, but check if we can actually use it
    try:
        _orig_path = sys.path.copy()
        sys.path.insert(0, CHAINMIND_PATH)
        # Try importing a core ChainMind module
        from backend.core.di import get_container
        CHAINMIND_AVAILABLE = True
    except ImportError:
        # ChainMind deps not installed in this venv
        CHAINMIND_AVAILABLE = False
    finally:
        sys.path = _orig_path

# Add marker for ChainMind tests
def pytest_configure(config):
    """Register markers."""
    config.addinivalue_line(
        "markers", "chainmind: tests that require ChainMind to be available"
    )


def pytest_collection_modifyitems(config, items):
    """Skip ChainMind tests if ChainMind is not available."""
    if CHAINMIND_AVAILABLE:
        return

    skip_chainmind = pytest.mark.skip(reason="ChainMind not available")

    # Test files that depend on ChainMind
    chainmind_test_files = {
        "test_chainmind",
        "test_integration_audit",
        "test_performance_comprehensive",
        "test_performance_audit",
        "test_e2e_comprehensive",
        "test_edge_cases_audit",
    }

    # Test classes/functions that depend on ChainMind
    chainmind_test_classes = {
        "TestErrorDetection",
        "TestErrorHandling",
        "TestBoundaryConditions",
        "TestRecoveryMechanisms",
        "TestFailureModes",
        "TestFullRequestFlow",
        "TestConfigurationIntegration",
        "TestErrorHandlingIntegration",
        "TestResponseTimes",
        "TestThroughput",
        "TestConcurrentOperations",
        "TestOptimization",
    }

    for item in items:
        basename = item.fspath.basename.lower().replace(".py", "")

        # Skip tests in chainmind-related test files
        if "chainmind" in basename or basename in chainmind_test_files:
            item.add_marker(skip_chainmind)
            continue

        # Skip tests in classes that test ChainMind
        if hasattr(item, 'cls') and item.cls and item.cls.__name__ in chainmind_test_classes:
            item.add_marker(skip_chainmind)
            continue

        # Skip tests that import ChainMindHelper fixture
        if hasattr(item, 'fixturenames') and 'chainmind_helper' in item.fixturenames:
            item.add_marker(skip_chainmind)


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def memory_store(temp_data_dir):
    """Fresh memory store for each test."""
    from engram.storage import MemoryStore
    return MemoryStore(data_dir=temp_data_dir)


@pytest.fixture
def founding_memories():
    """The three-layer memory structure.

    LAYER 1: Universal (applies to ANY project)
    LAYER 2: Domain (applies to similar tech/problems)
    LAYER 3: Project (applies only to Engram)

    These are REAL memories from building Engram!
    """
    return {
        # =================================================================
        # LAYER 1: UNIVERSAL - Any project, any domain, any language
        # =================================================================
        "universal": [
            {
                "content": "README-driven development: write comprehensive docs first, then build to match. Creates accountability and clarifies thinking.",
                "memory_type": "philosophy",
                "importance": 0.9,
                "project": None,
            },
            {
                "content": "Tests should serve double-duty: verification AND marketing assets. Each test category can map to a YouTube video concept.",
                "memory_type": "philosophy",
                "importance": 0.9,
                "project": None,
            },
            {
                "content": "MVP with validation criteria: define success metrics before building. Ask 'does this actually help?' not 'is this technically impressive?'",
                "memory_type": "philosophy",
                "importance": 0.9,
                "project": None,
            },
            {
                "content": "Decision journaling: record WHY not just WHAT. Future you will forget the context that made the decision obvious.",
                "memory_type": "philosophy",
                "importance": 0.85,
                "project": None,
            },
        ],

        # =================================================================
        # LAYER 2: DOMAIN - Python, MCP, AI tooling patterns
        # =================================================================
        "domain": [
            {
                "content": "MCP servers use stdio transport with JSON-RPC protocol. Define tools with JSON schemas for parameters.",
                "memory_type": "pattern",
                "importance": 0.8,
                "project": None,
            },
            {
                "content": "For local embeddings, sentence-transformers with all-MiniLM-L6-v2 is fast and good quality. 384 dimensions, ~90MB model.",
                "memory_type": "pattern",
                "importance": 0.8,
                "project": None,
            },
            {
                "content": "ChromaDB for vector storage: persistent, can use GPU, cosine similarity with HNSW index works well.",
                "memory_type": "pattern",
                "importance": 0.8,
                "project": None,
            },
            {
                "content": "Python packaging: use pyproject.toml with optional dependencies like [dev] and [gpu]. Avoid setup.py.",
                "memory_type": "pattern",
                "importance": 0.7,
                "project": None,
            },
        ],

        # =================================================================
        # LAYER 3: PROJECT - Engram-specific decisions
        # =================================================================
        "project": [
            {
                "content": "Engram architecture decision: SQLite for structured data + ChromaDB for vectors + JSON for knowledge graph. Avoided heavy deps like Neo4j or Redis.",
                "memory_type": "decision",
                "importance": 0.85,
                "project": "engram-mcp",
            },
            {
                "content": "Engram MVP scope: only 3 tools (remember, recall, context). Validate core value before building all 7 planned tools.",
                "memory_type": "decision",
                "importance": 0.9,
                "project": "engram-mcp",
            },
            {
                "content": "Engram project detection: regex on cwd path like /mnt/dev/ai/(?P<project>[^/]+) to auto-detect current project.",
                "memory_type": "decision",
                "importance": 0.75,
                "project": "engram-mcp",
            },
        ],
    }


@pytest.fixture
def populated_store(memory_store, founding_memories):
    """Memory store with all founding memories loaded.

    This is the state after Engram has been "bootstrapped"
    with knowledge of its own development.
    """
    for layer_name, memories in founding_memories.items():
        for mem in memories:
            memory_store.remember(**mem)
    return memory_store
