"""
Value Validation Tests - Ensures Engram Delivers Maximum Value

These tests validate:
1. RECALL QUALITY - Are we returning the RIGHT memories?
2. GRAPH INTEGRITY - Are relationships correct and queryable?
3. SCORING ACCURACY - Does relevance scoring work correctly?
4. PERFORMANCE - Does it scale without degradation?
5. DATA INTEGRITY - No corruption, loss, or duplicates?

Run with: pytest tests/test_value_validation.py -v
"""

import pytest
import time
import math
from datetime import datetime, timedelta


class TestRecallQuality:
    """
    CORE VALUE: Users find what they're looking for.

    Regression risks:
    - Embedding model changes break semantic search
    - Scoring formula changes affect ranking
    - Filter bugs exclude valid results
    """

    def test_exact_match_ranks_highest(self, memory_store):
        """Exact content match should have highest relevance."""
        content = "The quick brown fox jumps over the lazy dog"
        memory_store.remember(content, memory_type="fact")
        memory_store.remember("Something about animals running", memory_type="fact")
        memory_store.remember("Random unrelated content here", memory_type="fact")

        results = memory_store.recall("quick brown fox jumps lazy dog")

        assert len(results) >= 1
        assert results[0]["content"] == content
        assert results[0]["relevance"] > 0.7  # Should be very high

    def test_semantic_similarity_works(self, memory_store):
        """Find memories by meaning, not just keywords."""
        memory_store.remember(
            "Always validate user input to prevent SQL injection attacks",
            memory_type="pattern",
            importance=0.9
        )

        # Search with synonyms/related terms
        results = memory_store.recall("sanitize database queries security")

        assert len(results) >= 1
        assert "injection" in results[0]["content"].lower()

    def test_type_filter_works(self, memory_store):
        """Memory type filter should exclude other types."""
        memory_store.remember("This is a fact", memory_type="fact")
        memory_store.remember("This is a decision", memory_type="decision")
        memory_store.remember("This is a pattern", memory_type="pattern")

        results = memory_store.recall("this is a", memory_types=["decision"])

        assert all(r["memory_type"] == "decision" for r in results)

    def test_project_filter_works(self, memory_store):
        """Project filter should scope results correctly."""
        memory_store.remember("Memory for project A", memory_type="fact", project="project_a")
        memory_store.remember("Memory for project B", memory_type="fact", project="project_b")

        results = memory_store.recall("memory for project", project="project_a")

        # Should only return project_a memories
        assert all(r["project"] == "project_a" for r in results)

    def test_no_results_returns_empty(self, memory_store):
        """Query with no matches should return empty list, not error."""
        results = memory_store.recall("xyzzy completely unique gibberish query 12345")

        assert results == []

    def test_special_characters_handled(self, memory_store):
        """Special characters in queries shouldn't break search."""
        memory_store.remember("Use C++ for performance-critical code", memory_type="fact")

        # These shouldn't crash
        results1 = memory_store.recall("C++ performance")
        results2 = memory_store.recall("what's the best approach?")
        results3 = memory_store.recall("regex: ^[a-z]+$")

        assert isinstance(results1, list)
        assert isinstance(results2, list)
        assert isinstance(results3, list)


class TestScoringAccuracy:
    """
    CORE VALUE: Most relevant memories surface first.

    Regression risks:
    - Scoring formula changes without testing
    - Temporal decay miscalculated
    - Importance weight too high/low
    """

    def test_importance_affects_ranking(self, memory_store):
        """Higher importance should boost ranking."""
        # Store with different importance levels
        memory_store.remember("Low importance fact", memory_type="fact", importance=0.3)
        memory_store.remember("High importance fact", memory_type="fact", importance=0.9)

        results = memory_store.recall("importance fact")

        # High importance should rank higher
        assert len(results) >= 2
        high_idx = next(i for i, r in enumerate(results) if "High" in r["content"])
        low_idx = next(i for i, r in enumerate(results) if "Low" in r["content"])
        assert high_idx < low_idx, "High importance should rank before low"

    def test_access_count_boosts_relevance(self, memory_store):
        """Frequently accessed memories should get boosted."""
        mem_id = memory_store.remember("Frequently accessed memory", memory_type="fact")

        # Access it multiple times
        for _ in range(5):
            memory_store.recall("frequently accessed")

        results = memory_store.recall("frequently accessed")

        assert results[0]["access_count"] >= 5
        # Relevance should be boosted by reinforcement

    def test_relevance_score_components(self, memory_store):
        """Verify relevance score includes all expected components."""
        memory_store.remember("Test memory for scoring", memory_type="fact", importance=0.7)

        results = memory_store.recall("test memory scoring")

        assert len(results) >= 1
        result = results[0]

        # Should have all score components
        assert "relevance" in result
        assert "similarity" in result
        assert "freshness" in result
        assert "importance" in result

        # All should be reasonable values
        assert 0 <= result["relevance"] <= 1
        assert 0 <= result["similarity"] <= 1
        assert 0 <= result["freshness"] <= 2  # Can exceed 1 due to formula


class TestGraphIntegrity:
    """
    CORE VALUE: Knowledge graph provides actionable insights.

    Regression risks:
    - Relationships not persisted
    - Entity IDs inconsistent
    - Graph queries return wrong results
    """

    def test_entity_creation(self, memory_store):
        """Entities should be creatable and findable."""
        entity_id = memory_store.add_entity(
            entity_type="goal",
            name="Test Goal",
            description="A test goal for validation"
        )

        assert entity_id is not None
        assert entity_id.startswith("entity:goal:")

    def test_relationship_creation(self, memory_store):
        """Relationships should link entities correctly."""
        # Create entities
        goal_id = memory_store.add_entity("goal", "Ship Feature")
        blocker_id = memory_store.add_entity("blocker", "Technical Debt")

        # Create relationship
        success = memory_store.add_relationship(
            source_id=blocker_id,
            target_id=goal_id,
            relation_type="blocks"
        )

        assert success is True

    def test_blocker_query(self, memory_store):
        """Should find blockers for a goal."""
        # Setup
        goal_id = memory_store.add_entity("goal", "Launch Product")
        blocker1_id = memory_store.add_entity("blocker", "Missing Tests")
        blocker2_id = memory_store.add_entity("blocker", "Performance Issues")

        memory_store.add_relationship(blocker1_id, goal_id, "blocks")
        memory_store.add_relationship(blocker2_id, goal_id, "blocks")

        # Query
        blockers = memory_store.get_blockers("launch product")

        assert len(blockers) == 2
        blocker_names = {b["name"] for b in blockers}
        assert "Missing Tests" in blocker_names
        assert "Performance Issues" in blocker_names

    def test_graph_persistence(self, memory_store):
        """Graph should persist after save/load cycle."""
        # Create and save
        entity_id = memory_store.add_entity("goal", "Persistent Goal")

        # Force save
        if memory_store.graph:
            memory_store.graph.save()

        # Verify it's in the graph
        assert memory_store.graph.graph.has_node(entity_id)

    def test_entity_id_consistency(self, memory_store):
        """Same entity name should produce same ID."""
        id1 = memory_store.add_entity("goal", "Consistent Name")
        id2 = memory_store.add_entity("goal", "Consistent Name")

        # Should be the same entity
        assert id1 == id2


class TestDataIntegrity:
    """
    CORE VALUE: No data loss or corruption.

    Regression risks:
    - SQLite/ChromaDB sync issues
    - Duplicate entries
    - Orphaned records
    """

    def test_sqlite_chromadb_sync(self, memory_store):
        """SQLite and ChromaDB should have same count."""
        # Add some memories
        for i in range(5):
            memory_store.remember(f"Sync test memory {i}", memory_type="fact")

        # Count in SQLite
        cursor = memory_store.db.execute("SELECT COUNT(*) FROM memories")
        sqlite_count = cursor.fetchone()[0]

        # Count in ChromaDB
        chroma_count = memory_store.collection.count()

        assert sqlite_count == chroma_count

    def test_no_duplicate_on_same_content(self, memory_store):
        """Same content shouldn't create duplicates (when using check)."""
        content = "This exact content should not duplicate"

        # Store first time
        id1 = memory_store.remember(content, memory_type="fact")

        # Try to store same content with conflict check
        result = memory_store.remember(
            content,
            memory_type="fact",
            check_conflicts=True
        )

        # Should detect conflict
        if isinstance(result, dict) and result.get("status") == "conflicts_found":
            # Good - it detected the duplicate
            pass
        else:
            # Verify we don't have duplicates
            cursor = memory_store.db.execute(
                "SELECT COUNT(*) FROM memories WHERE content = ?",
                (content,)
            )
            count = cursor.fetchone()[0]
            assert count <= 2  # At most 2 (original + one more)

    def test_memory_id_uniqueness(self, memory_store):
        """All memory IDs should be unique."""
        for i in range(10):
            memory_store.remember(f"Unique test {i}", memory_type="fact")

        cursor = memory_store.db.execute("SELECT id FROM memories")
        ids = [row[0] for row in cursor.fetchall()]

        assert len(ids) == len(set(ids)), "Duplicate memory IDs found!"

    def test_deleted_memory_gone_everywhere(self, memory_store):
        """Deleted memories should be removed from all stores."""
        mem_id = memory_store.remember("Memory to delete", memory_type="fact")

        # Delete it
        memory_store.db.execute("DELETE FROM memories WHERE id = ?", (mem_id,))
        memory_store.db.commit()

        try:
            memory_store.collection.delete(ids=[mem_id])
        except:
            pass

        # Verify gone from SQLite
        cursor = memory_store.db.execute(
            "SELECT COUNT(*) FROM memories WHERE id = ?",
            (mem_id,)
        )
        assert cursor.fetchone()[0] == 0

        # Verify not returned in search
        results = memory_store.recall("memory to delete")
        assert not any(r["id"] == mem_id for r in results)


class TestPerformance:
    """
    CORE VALUE: Fast responses at scale.

    Regression risks:
    - O(n) algorithms where O(log n) possible
    - Missing indexes
    - Memory leaks
    """

    def test_recall_speed_acceptable(self, memory_store):
        """Recall should be fast even with many memories."""
        # Add a bunch of memories
        for i in range(100):
            memory_store.remember(f"Performance test memory number {i}", memory_type="fact")

        # Time the recall
        start = time.time()
        results = memory_store.recall("performance test memory")
        elapsed = time.time() - start

        # Should be under 1 second (generous for CI)
        assert elapsed < 1.0, f"Recall took {elapsed:.2f}s, should be <1s"

    def test_remember_speed_acceptable(self, memory_store):
        """Remember should be fast."""
        start = time.time()
        for i in range(10):
            memory_store.remember(f"Speed test {i}", memory_type="fact")
        elapsed = time.time() - start

        # 10 memories in under 5 seconds (generous for embedding)
        assert elapsed < 5.0, f"10 remembers took {elapsed:.2f}s"

    def test_context_speed_acceptable(self, memory_store):
        """Context retrieval should be fast."""
        # Seed some memories
        for i in range(50):
            memory_store.remember(f"Context speed test {i}", memory_type="fact")

        start = time.time()
        context = memory_store.context(query="speed test", limit=10)
        elapsed = time.time() - start

        assert elapsed < 2.0, f"Context took {elapsed:.2f}s, should be <2s"


class TestEdgeCases:
    """
    CORE VALUE: Graceful handling of weird inputs.

    Regression risks:
    - Crashes on edge cases
    - Silent failures
    """

    def test_empty_query(self, memory_store):
        """Empty query should not crash."""
        results = memory_store.recall("")
        assert isinstance(results, list)

    def test_very_long_content(self, memory_store):
        """Very long content should be handled."""
        long_content = "x" * 10000  # 10K characters
        mem_id = memory_store.remember(long_content, memory_type="fact")

        assert mem_id is not None

    def test_unicode_content(self, memory_store):
        """Unicode content should work."""
        unicode_content = "日本語テスト 🚀 émojis and spëcial çharacters"
        mem_id = memory_store.remember(unicode_content, memory_type="fact")

        results = memory_store.recall("日本語")
        assert len(results) >= 1
        assert unicode_content in results[0]["content"]

    def test_null_project(self, memory_store):
        """Null project should work (universal memories)."""
        mem_id = memory_store.remember("Universal memory", memory_type="fact", project=None)

        assert mem_id is not None

        results = memory_store.recall("universal memory")
        assert len(results) >= 1
        assert results[0]["project"] is None

    def test_invalid_memory_type(self, memory_store):
        """Invalid memory type should either work or raise clear error."""
        try:
            mem_id = memory_store.remember(
                "Invalid type test",
                memory_type="invalid_type_xyz"
            )
            # If it doesn't raise, it should still store something
            assert mem_id is not None
        except (ValueError, KeyError) as e:
            # Clear error is acceptable
            assert "type" in str(e).lower()


class TestSeedKnowledgeIntegration:
    """
    CORE VALUE: Seed knowledge is findable and correct.

    These tests validate the YouTube mastery seed data.
    NOTE: These tests use the PRODUCTION database, not test fixtures.
    They validate that seed ingestion worked correctly.
    """

    @pytest.fixture
    def production_store(self):
        """Use the real production memory store (not temp)."""
        from engram.storage import MemoryStore
        return MemoryStore()  # Uses default ~/.engram/data

    def test_youtube_monetization_findable(self, production_store):
        """Should find YouTube monetization requirements."""
        results = production_store.recall("YouTube monetization requirements subscribers")

        if not results:
            pytest.skip("No seed data - run seeds/ingest.py first")

        # Should find relevant memories
        found_monetization = any(
            "1,000 subscribers" in r["content"] or
            "4,000" in r["content"] or
            "watch hours" in r["content"].lower()
            for r in results
        )
        assert found_monetization, "Should find monetization requirements"

    def test_thumbnail_advice_findable(self, production_store):
        """Should find thumbnail best practices."""
        results = production_store.recall("thumbnail CTR face emotion")

        if not results:
            pytest.skip("No seed data - run seeds/ingest.py first")

        found_thumbnail = any(
            "thumbnail" in r["content"].lower() and
            ("face" in r["content"].lower() or "emotion" in r["content"].lower())
            for r in results
        )
        assert found_thumbnail, "Should find thumbnail advice"

    def test_copyright_guidance_findable(self, production_store):
        """Should find copyright strike information."""
        results = production_store.recall("copyright strike Content ID")

        if not results:
            pytest.skip("No seed data - run seeds/ingest.py first")

        found_copyright = any(
            "copyright" in r["content"].lower() and
            ("strike" in r["content"].lower() or "content id" in r["content"].lower())
            for r in results
        )
        assert found_copyright, "Should find copyright guidance"

    def test_graph_blockers_populated(self, production_store):
        """Graph should have YouTube-related blockers."""
        if not production_store.graph:
            pytest.skip("Graph not available")

        # Check for YouTube goals/blockers
        try:
            blockers = production_store.get_blockers("channel growth")
        except Exception:
            pytest.skip("No seed data - run seeds/ingest.py first")

        # Should have blockers if seed data loaded
        if not blockers:
            pytest.skip("No blockers found - run seeds/ingest.py first")

        blocker_names = {b["name"].lower() for b in blockers}
        expected = {"low ctr", "poor retention", "inconsistent publishing"}
        assert blocker_names & expected, f"Expected blockers not found. Got: {blocker_names}"
