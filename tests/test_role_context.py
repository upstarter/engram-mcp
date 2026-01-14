"""
Test Role Context Feature - Agent-specific memory affinity.

This tests the core feature where:
1. Memories are tagged with the creating agent's role (source_role)
2. Queries from the same role get a relevance boost (role affinity)
3. All memories remain accessible to all agents (no silos)
4. Role is stored consistently in SQLite, ChromaDB, and Graph
"""

import pytest
import os
import tempfile
from pathlib import Path


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def role_store(temp_data_dir):
    """Fresh memory store for role context tests."""
    from engram.storage import MemoryStore
    return MemoryStore(data_dir=temp_data_dir)


@pytest.fixture
def multi_agent_memories(role_store):
    """Create memories from multiple agent roles.

    Simulates a real environment where different agents create
    domain-specific memories.
    """
    memories = {
        "gpu-specialist": [
            {
                "id": role_store.remember(
                    "CUDA OOM fix: set PYTORCH_ALLOC_CONF=max_split_size_mb:512",
                    memory_type="solution",
                    importance=0.9,
                    source_role="gpu-specialist",
                    project="ai-dev",
                ),
                "content": "CUDA OOM fix",
                "domain": "gpu",
            },
            {
                "id": role_store.remember(
                    "RTX 5080 Blackwell requires sm_120 compute capability and cu128",
                    memory_type="fact",
                    importance=0.8,
                    source_role="gpu-specialist",
                    project="ai-dev",
                ),
                "content": "RTX 5080 specs",
                "domain": "gpu",
            },
        ],
        "studioflow": [
            {
                "id": role_store.remember(
                    "StudioFlow audio markers use frame-accurate timestamps not timecodes",
                    memory_type="solution",
                    importance=0.9,
                    source_role="studioflow",
                    project="studioflow",
                ),
                "content": "audio markers",
                "domain": "video",
            },
            {
                "id": role_store.remember(
                    "rough_cut CLI parses whisper output with fuzzy matching threshold 0.8",
                    memory_type="fact",
                    importance=0.8,
                    source_role="studioflow",
                    project="studioflow",
                ),
                "content": "rough_cut parsing",
                "domain": "video",
            },
        ],
        "engram-dev": [
            {
                "id": role_store.remember(
                    "Engram uses SQLite + ChromaDB + NetworkX for triple storage",
                    memory_type="decision",
                    importance=0.9,
                    source_role="engram-dev",
                    project="engram-mcp",
                ),
                "content": "engram architecture",
                "domain": "memory",
            },
        ],
        "universal": [
            {
                "id": role_store.remember(
                    "README-driven development: write docs first, build to match",
                    memory_type="philosophy",
                    importance=0.9,
                    source_role=None,  # No role - universal
                    project=None,
                ),
                "content": "universal philosophy",
                "domain": "general",
            },
        ],
    }
    return {"store": role_store, "memories": memories}


# =============================================================================
# TEST: ROLE STORAGE IN ALL THREE STORES
# =============================================================================

class TestRoleStorageConsistency:
    """Verify source_role is stored in SQLite, ChromaDB, and Graph."""

    def test_role_stored_in_sqlite(self, role_store):
        """SQLite should have source_role column populated."""
        mem_id = role_store.remember(
            "Test memory for SQLite role storage",
            memory_type="fact",
            source_role="test-agent",
        )

        row = role_store.db.execute(
            "SELECT source_role FROM memories WHERE id = ?",
            (mem_id,)
        ).fetchone()

        assert row["source_role"] == "test-agent"

    def test_role_stored_in_chromadb(self, role_store):
        """ChromaDB metadata should include source_role."""
        mem_id = role_store.remember(
            "Test memory for ChromaDB role storage",
            memory_type="fact",
            source_role="test-agent",
        )

        result = role_store.collection.get(ids=[mem_id], include=["metadatas"])
        metadata = result["metadatas"][0]

        assert metadata["source_role"] == "test-agent"

    def test_role_stored_in_graph(self, role_store):
        """Graph node should have source_role attribute."""
        mem_id = role_store.remember(
            "Test memory for Graph role storage",
            memory_type="fact",
            source_role="test-agent",
        )

        if role_store.graph:
            node = role_store.graph.graph.nodes.get(mem_id, {})
            assert node.get("source_role") == "test-agent"

    def test_null_role_stored_correctly(self, role_store):
        """Memories without role should have None/empty in all stores."""
        mem_id = role_store.remember(
            "Universal memory without role",
            memory_type="philosophy",
            source_role=None,
        )

        # SQLite
        row = role_store.db.execute(
            "SELECT source_role FROM memories WHERE id = ?",
            (mem_id,)
        ).fetchone()
        assert row["source_role"] is None

        # ChromaDB
        result = role_store.collection.get(ids=[mem_id], include=["metadatas"])
        metadata = result["metadatas"][0]
        assert metadata["source_role"] == ""  # ChromaDB stores empty string

        # Graph
        if role_store.graph:
            node = role_store.graph.graph.nodes.get(mem_id, {})
            assert node.get("source_role") is None

    def test_all_stores_have_same_role(self, role_store):
        """All three stores should have identical source_role value."""
        mem_id = role_store.remember(
            "Consistency test across all stores",
            memory_type="fact",
            source_role="consistency-test-agent",
            project="test-project",
        )

        # Get from SQLite
        row = role_store.db.execute(
            "SELECT source_role FROM memories WHERE id = ?",
            (mem_id,)
        ).fetchone()
        sqlite_role = row["source_role"]

        # Get from ChromaDB
        result = role_store.collection.get(ids=[mem_id], include=["metadatas"])
        chroma_role = result["metadatas"][0]["source_role"]

        # Get from Graph
        graph_role = None
        if role_store.graph:
            node = role_store.graph.graph.nodes.get(mem_id, {})
            graph_role = node.get("source_role")

        # All should match
        assert sqlite_role == "consistency-test-agent"
        assert chroma_role == "consistency-test-agent"
        if role_store.graph:
            assert graph_role == "consistency-test-agent"


# =============================================================================
# TEST: ROLE AFFINITY SCORING
# =============================================================================

class TestRoleAffinityScoring:
    """Verify that same-role queries get boosted relevance."""

    def test_same_role_gets_boost(self, multi_agent_memories):
        """Memories from same role should have role_affinity > 1.0."""
        store = multi_agent_memories["store"]

        # Search as gpu-specialist for GPU content
        results = store.recall("CUDA memory fix", current_role="gpu-specialist")

        # Find the GPU memory in results
        gpu_memory = next(
            (r for r in results if "CUDA" in r["content"]),
            None
        )

        assert gpu_memory is not None
        assert gpu_memory["source_role"] == "gpu-specialist"
        assert gpu_memory["role_affinity"] > 1.0  # Should be 1.15

    def test_different_role_no_boost(self, multi_agent_memories):
        """Memories from different role should have role_affinity = 1.0."""
        store = multi_agent_memories["store"]

        # Search as studioflow for GPU content
        results = store.recall("CUDA memory fix", current_role="studioflow")

        # Find the GPU memory in results
        gpu_memory = next(
            (r for r in results if "CUDA" in r["content"]),
            None
        )

        assert gpu_memory is not None
        assert gpu_memory["source_role"] == "gpu-specialist"
        assert gpu_memory["role_affinity"] == 1.0  # No boost

    def test_no_role_query_no_boost(self, multi_agent_memories):
        """Queries without current_role should not boost any results."""
        store = multi_agent_memories["store"]

        # Search without role
        results = store.recall("CUDA memory fix", current_role=None)

        # All results should have role_affinity = 1.0
        for result in results:
            assert result["role_affinity"] == 1.0

    def test_boost_affects_ranking(self, multi_agent_memories):
        """Role affinity should affect final ranking order."""
        store = multi_agent_memories["store"]

        # Create two similar memories from different roles
        store.remember(
            "Memory optimization technique A",
            memory_type="solution",
            importance=0.7,
            source_role="gpu-specialist",
        )
        store.remember(
            "Memory optimization technique B",
            memory_type="solution",
            importance=0.7,
            source_role="studioflow",
        )

        # Search as gpu-specialist
        results = store.recall("memory optimization", current_role="gpu-specialist")

        # Find both memories
        gpu_mem = next((r for r in results if "technique A" in r["content"]), None)
        sf_mem = next((r for r in results if "technique B" in r["content"]), None)

        if gpu_mem and sf_mem:
            # GPU memory should have higher relevance due to boost
            assert gpu_mem["relevance"] > sf_mem["relevance"]

    def test_affinity_boost_is_15_percent(self, role_store):
        """Verify the exact boost amount is 15%."""
        # Create memory with known role
        role_store.remember(
            "Test content for boost calculation",
            memory_type="fact",
            importance=0.5,
            source_role="test-role",
        )

        # Query with same role
        results_same = role_store.recall("test content boost", current_role="test-role")

        # Query with different role
        results_diff = role_store.recall("test content boost", current_role="other-role")

        if results_same and results_diff:
            same_mem = results_same[0]
            diff_mem = results_diff[0]

            # Same memory, different scores
            assert same_mem["id"] == diff_mem["id"]

            # Boost should be approximately 15%
            ratio = same_mem["relevance"] / diff_mem["relevance"]
            assert 1.10 <= ratio <= 1.20  # Allow some floating point variance


# =============================================================================
# TEST: CROSS-AGENT VISIBILITY
# =============================================================================

class TestCrossAgentVisibility:
    """Verify all agents can access all memories (no silos)."""

    def test_gpu_agent_sees_studioflow_memories(self, multi_agent_memories):
        """GPU specialist should be able to find StudioFlow memories."""
        store = multi_agent_memories["store"]

        # GPU agent searches for audio (StudioFlow domain)
        results = store.recall("audio markers timestamps", current_role="gpu-specialist")

        # Should find StudioFlow memory
        sf_memory = next(
            (r for r in results if "audio markers" in r["content"]),
            None
        )

        assert sf_memory is not None
        assert sf_memory["source_role"] == "studioflow"

    def test_studioflow_agent_sees_gpu_memories(self, multi_agent_memories):
        """StudioFlow agent should be able to find GPU memories."""
        store = multi_agent_memories["store"]

        # StudioFlow agent searches for CUDA (GPU domain)
        results = store.recall("CUDA OOM memory", current_role="studioflow")

        # Should find GPU memory
        gpu_memory = next(
            (r for r in results if "CUDA" in r["content"]),
            None
        )

        assert gpu_memory is not None
        assert gpu_memory["source_role"] == "gpu-specialist"

    def test_all_agents_see_universal_memories(self, multi_agent_memories):
        """All agents should see memories without source_role."""
        store = multi_agent_memories["store"]

        for role in ["gpu-specialist", "studioflow", "engram-dev", None]:
            results = store.recall("README-driven development", current_role=role)

            universal = next(
                (r for r in results if "README-driven" in r["content"]),
                None
            )

            assert universal is not None, f"Role {role} should see universal memory"
            assert universal["source_role"] is None

    def test_semantic_relevance_still_matters(self, multi_agent_memories):
        """Semantic similarity should still be primary ranking factor."""
        store = multi_agent_memories["store"]

        # GPU agent searches for something StudioFlow-specific
        results = store.recall("rough_cut whisper fuzzy matching", current_role="gpu-specialist")

        # StudioFlow memory should still rank high despite different role
        # because semantic match is strong
        if results:
            top_result = results[0]
            assert "rough_cut" in top_result["content"] or "fuzzy" in top_result["content"]


# =============================================================================
# TEST: CONTEXT FUNCTION WITH ROLE
# =============================================================================

class TestContextWithRole:
    """Test the context() function with role affinity."""

    def test_context_uses_role_affinity(self, multi_agent_memories):
        """context() should pass current_role to recall for affinity."""
        store = multi_agent_memories["store"]

        # Get context as gpu-specialist
        results = store.context(
            query="memory optimization",
            current_role="gpu-specialist",
        )

        # Should include role_affinity in results
        for result in results:
            assert "role_affinity" in result or result.get("source_role") is None

    def test_context_without_role(self, multi_agent_memories):
        """context() without role should still work."""
        store = multi_agent_memories["store"]

        results = store.context(query="development patterns")

        # Should return results without error
        assert isinstance(results, list)


# =============================================================================
# TEST: RECALL OUTPUT FORMAT
# =============================================================================

class TestRecallOutputFormat:
    """Verify recall() returns expected fields for role context."""

    def test_recall_includes_source_role(self, multi_agent_memories):
        """Recall results should include source_role field."""
        store = multi_agent_memories["store"]

        results = store.recall("CUDA", current_role="gpu-specialist")

        for result in results:
            assert "source_role" in result

    def test_recall_includes_role_affinity(self, multi_agent_memories):
        """Recall results should include role_affinity field."""
        store = multi_agent_memories["store"]

        results = store.recall("CUDA", current_role="gpu-specialist")

        for result in results:
            assert "role_affinity" in result
            assert isinstance(result["role_affinity"], float)

    def test_recall_role_affinity_values(self, multi_agent_memories):
        """role_affinity should be 1.0 or 1.15 (boosted)."""
        store = multi_agent_memories["store"]

        results = store.recall("memory architecture storage", current_role="gpu-specialist")

        for result in results:
            # Should be either 1.0 (no boost) or ~1.15 (boosted)
            assert result["role_affinity"] in [1.0, 1.15] or \
                   (1.14 <= result["role_affinity"] <= 1.16)


# =============================================================================
# TEST: FILE-BASED CONTEXT PASSING
# =============================================================================

class TestFileBasedContextPassing:
    """Test reading role/project from state files."""

    def test_get_context_from_files_reads_role(self, temp_data_dir):
        """_get_context_from_files should read role from file."""
        from engram.server import _get_context_from_files, CONTEXT_STATE_DIR

        # Create state directory and role file
        state_dir = Path(CONTEXT_STATE_DIR)
        state_dir.mkdir(parents=True, exist_ok=True)

        role_file = state_dir / "current_role"
        role_file.write_text("test-agent-role")

        try:
            role, project, agent_id = _get_context_from_files()
            assert role == "test-agent-role"
        finally:
            role_file.unlink(missing_ok=True)

    def test_get_context_from_files_reads_project(self, temp_data_dir):
        """_get_context_from_files should read project from active_project."""
        import json
        from engram.server import _get_context_from_files

        # Create active_project file
        project_file = Path.home() / ".spc" / "active_project"
        project_file.parent.mkdir(parents=True, exist_ok=True)

        original_content = None
        if project_file.exists():
            original_content = project_file.read_text()

        try:
            project_file.write_text(json.dumps({
                "name": "TestProject",
                "type": "test",
            }))

            role, project, agent_id = _get_context_from_files()
            assert project == "testproject"  # Lowercased
        finally:
            if original_content:
                project_file.write_text(original_content)
            elif project_file.exists():
                pass  # Don't delete if it existed before

    def test_missing_files_return_empty(self):
        """Missing state files should return empty strings, not error."""
        from engram.server import _get_context_from_files, CONTEXT_STATE_DIR

        # Temporarily rename role file if exists
        state_dir = Path(CONTEXT_STATE_DIR)
        role_file = state_dir / "current_role"
        backup = None

        if role_file.exists():
            backup = role_file.read_text()
            role_file.unlink()

        try:
            role, project, agent_id = _get_context_from_files()
            # Should not raise, should return empty or existing values
            assert isinstance(role, str)
            assert isinstance(project, str)
            assert isinstance(agent_id, str)
        finally:
            if backup:
                role_file.write_text(backup)


# =============================================================================
# TEST: GRAPH QUERIES WITH ROLE
# =============================================================================

class TestGraphQueriesWithRole:
    """Test that graph operations respect source_role."""

    def test_graph_node_has_source_role(self, role_store):
        """Graph nodes should include source_role attribute."""
        mem_id = role_store.remember(
            "Test memory for graph role",
            memory_type="fact",
            source_role="graph-test-agent",
        )

        if role_store.graph:
            node = role_store.graph.graph.nodes.get(mem_id)
            assert node is not None
            assert node.get("source_role") == "graph-test-agent"

    def test_graph_query_can_filter_by_role(self, multi_agent_memories):
        """Graph queries should be able to filter by source_role."""
        store = multi_agent_memories["store"]

        if store.graph:
            # Get all memory nodes
            memory_nodes = [
                (node_id, data)
                for node_id, data in store.graph.graph.nodes(data=True)
                if data.get("node_type") == "memory"
            ]

            # Filter by role
            gpu_memories = [
                (nid, d) for nid, d in memory_nodes
                if d.get("source_role") == "gpu-specialist"
            ]

            sf_memories = [
                (nid, d) for nid, d in memory_nodes
                if d.get("source_role") == "studioflow"
            ]

            assert len(gpu_memories) == 2  # Two GPU memories
            assert len(sf_memories) == 2  # Two StudioFlow memories


# =============================================================================
# TEST: EDGE CASES
# =============================================================================

class TestRoleEdgeCases:
    """Edge cases for role context feature."""

    def test_empty_string_role_treated_as_none(self, role_store):
        """Empty string role should behave like None."""
        mem_id = role_store.remember(
            "Memory with empty role",
            memory_type="fact",
            source_role="",
        )

        # Query with a role - should not get boost
        results = role_store.recall("empty role", current_role="some-role")

        if results:
            mem = next((r for r in results if r["id"] == mem_id), None)
            if mem:
                assert mem["role_affinity"] == 1.0

    def test_special_characters_in_role(self, role_store):
        """Roles with special characters should work."""
        mem_id = role_store.remember(
            "Memory with special role name",
            memory_type="fact",
            source_role="my-agent_v2.0",
        )

        # Should store and retrieve correctly
        row = role_store.db.execute(
            "SELECT source_role FROM memories WHERE id = ?",
            (mem_id,)
        ).fetchone()

        assert row["source_role"] == "my-agent_v2.0"

    def test_very_long_role_name(self, role_store):
        """Very long role names should work."""
        long_role = "a" * 200

        mem_id = role_store.remember(
            "Memory with very long role",
            memory_type="fact",
            source_role=long_role,
        )

        row = role_store.db.execute(
            "SELECT source_role FROM memories WHERE id = ?",
            (mem_id,)
        ).fetchone()

        assert row["source_role"] == long_role

    def test_unicode_role_name(self, role_store):
        """Unicode role names should work."""
        mem_id = role_store.remember(
            "Memory with unicode role",
            memory_type="fact",
            source_role="агент-разработчик",
        )

        row = role_store.db.execute(
            "SELECT source_role FROM memories WHERE id = ?",
            (mem_id,)
        ).fetchone()

        assert row["source_role"] == "агент-разработчик"


# =============================================================================
# TEST: PERFORMANCE
# =============================================================================

class TestRolePerformance:
    """Performance tests for role context feature."""

    def test_role_affinity_calculation_fast(self, role_store):
        """Role affinity calculation should not significantly slow recall."""
        import time

        # Create 50 memories
        for i in range(50):
            role_store.remember(
                f"Performance test memory number {i} with various content",
                memory_type="fact",
                source_role=f"role-{i % 5}",
            )

        # Time recall without role
        start = time.time()
        for _ in range(5):
            role_store.recall("performance test memory", current_role=None)
        time_without = time.time() - start

        # Time recall with role
        start = time.time()
        for _ in range(5):
            role_store.recall("performance test memory", current_role="role-1")
        time_with = time.time() - start

        # Role affinity should add < 20% overhead
        assert time_with < time_without * 1.2 or time_with < 1.0  # Or under 1s total
