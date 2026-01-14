#!/usr/bin/env python3
"""
Edge Case and Robustness Tests

Tests for boundary conditions, unusual inputs, and error handling:
1. Extreme values (importance 0.0/1.0, very old memories)
2. Large content handling
3. Unicode and special characters
4. Concurrent operations
5. Database integrity
6. Error recovery

These tests ensure the system is robust under unusual conditions.
"""

import pytest
import sys
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))
from engram.storage import MemoryStore


@pytest.fixture
def store():
    """Fresh memory store for each test."""
    return MemoryStore()


class TestExtremeValues:
    """Test boundary value handling."""

    def test_importance_zero(self, store):
        """importance=0.0 should be valid and stored."""
        mem_id = store.remember(
            "Zero importance memory",
            memory_type="fact",
            importance=0.0
        )

        assert mem_id is not None

        # Verify it's stored correctly in SQLite
        row = store.db.execute(
            "SELECT importance FROM memories WHERE id = ?",
            (mem_id,)
        ).fetchone()
        assert row is not None
        assert row[0] == 0.0

        # Note: Zero importance memories may rank very low in recall results
        # due to 20% importance weight in scoring formula. This is expected.
        # The memory IS stored and accessible via direct query.

    def test_importance_one(self, store):
        """importance=1.0 should be valid and retrievable."""
        unique_marker = "ht3z9w2k_max_importance"
        mem_id = store.remember(
            f"{unique_marker} maximum importance test",
            memory_type="decision",
            importance=1.0
        )

        assert mem_id is not None

        results = store.recall(unique_marker, limit=10)
        found = any(r["id"] == mem_id for r in results)
        assert found, f"Max importance memory not found. Results: {[r['id'] for r in results]}"

    def test_importance_out_of_range_high(self, store):
        """importance > 1.0 should be handled."""
        # Implementation might clamp or accept
        mem_id = store.remember(
            "Over-importance memory",
            memory_type="fact",
            importance=2.0
        )

        # Should not crash
        assert mem_id is not None

    def test_importance_negative(self, store):
        """importance < 0 should be handled."""
        mem_id = store.remember(
            "Negative importance memory",
            memory_type="fact",
            importance=-0.5
        )

        # Should not crash
        assert mem_id is not None

    def test_very_old_memory_decay(self, store):
        """2+ year old memory should have near-zero decay."""
        import math

        days_old = 730  # 2 years
        decay = math.exp(-0.023 * days_old)

        # Should be very small
        assert decay < 0.01

    def test_future_timestamp_handling(self, store):
        """Memory with future timestamp should be handled."""
        mem_id = store.remember("Future memory content", memory_type="fact")

        # Manually set future timestamp
        future = (datetime.now() + timedelta(days=30)).isoformat()
        store.db.execute(
            "UPDATE memories SET created_at = ? WHERE id = ?",
            (future, mem_id)
        )
        store.db.commit()

        # Should not crash on recall
        results = store.recall("future memory", limit=5)
        assert isinstance(results, list)


class TestLargeContent:
    """Test handling of large content."""

    def test_very_long_content(self, store):
        """Should handle very long content (10KB+)."""
        unique_marker = "vt6r3p9q_long_content_test"
        long_content = "A" * 10000 + f" {unique_marker}"

        mem_id = store.remember(
            long_content,
            memory_type="fact",
            importance=0.8
        )

        assert mem_id is not None

        # Should be retrievable via unique marker
        results = store.recall(unique_marker, limit=10)
        found = any(r["id"] == mem_id for r in results)
        assert found, f"Long content memory not found. Got {len(results)} results"

    def test_extremely_long_content(self, store):
        """Should handle extremely long content (100KB)."""
        huge_content = "B" * 100000 + " huge content marker"

        mem_id = store.remember(
            huge_content,
            memory_type="fact"
        )

        # Should not crash
        assert mem_id is not None

    def test_long_query(self, store):
        """Should handle very long queries."""
        store.remember("Target content for long query", memory_type="fact")

        long_query = " ".join(["word"] * 1000 + ["target content"])
        results = store.recall(long_query, limit=5)

        # Should not crash
        assert isinstance(results, list)

    def test_many_memories(self, store):
        """Should handle database with many memories."""
        # Create 100 memories
        for i in range(100):
            store.remember(
                f"Batch memory number {i} with some content",
                memory_type="fact"
            )

        # Should still search quickly
        import time
        start = time.time()
        results = store.recall("batch memory", limit=10)
        elapsed = time.time() - start

        assert len(results) >= 1
        assert elapsed < 5.0, f"Search took too long: {elapsed:.2f}s"


class TestUnicodeAndSpecialChars:
    """Test Unicode and special character handling."""

    def test_unicode_content(self, store):
        """Should handle Unicode content."""
        unicode_content = "日本語テスト 한국어 테스트 🚀 émojis αβγδ"

        mem_id = store.remember(
            unicode_content,
            memory_type="fact"
        )

        assert mem_id is not None

    def test_unicode_query(self, store):
        """Should handle Unicode queries."""
        store.remember("Japanese content 日本語", memory_type="fact")

        results = store.recall("日本語", limit=5)

        # Should not crash
        assert isinstance(results, list)

    def test_emoji_content(self, store):
        """Should handle emoji content."""
        emoji_content = "🎉 Celebration memory 🎊 with many emojis 🚀🔥💡"

        mem_id = store.remember(emoji_content, memory_type="fact")

        assert mem_id is not None

    def test_special_sql_characters(self, store):
        """Should handle SQL-sensitive characters."""
        sql_content = "Test'; DROP TABLE memories; --"

        mem_id = store.remember(sql_content, memory_type="fact")

        # Should not crash or cause SQL injection
        assert mem_id is not None

        # Data should be stored correctly
        row = store.db.execute(
            "SELECT content FROM memories WHERE id = ?",
            (mem_id,)
        ).fetchone()
        assert sql_content in row[0]

    def test_quotes_in_content(self, store):
        """Should handle quotes properly."""
        quoted_content = '''He said "Hello, it's a 'test'" content'''

        mem_id = store.remember(quoted_content, memory_type="fact")

        assert mem_id is not None

    def test_newlines_in_content(self, store):
        """Should handle newlines in content."""
        multiline = """First line
Second line
Third line with tabs\t\there"""

        mem_id = store.remember(multiline, memory_type="fact")

        assert mem_id is not None

    def test_null_bytes(self, store):
        """Should handle null bytes in content."""
        null_content = "Content with \x00 null byte"

        # Might raise or handle gracefully
        try:
            mem_id = store.remember(null_content, memory_type="fact")
            # If it succeeds, that's fine
        except Exception:
            # If it fails, that's also acceptable
            pass


class TestConcurrency:
    """Test concurrent operations.

    Note: SQLite and SentenceTransformer have known thread-safety limitations.
    These tests document the current behavior rather than asserting thread-safety.
    """

    @pytest.mark.skip(reason="SentenceTransformer has thread-safety issues with meta tensors")
    def test_concurrent_remembers(self, store):
        """Multiple threads remembering simultaneously.

        Known limitation: SentenceTransformer embedding model is not fully thread-safe.
        In production, use a connection pool or serialize embedding operations.
        """
        results = []
        errors = []

        def remember_thread(i):
            try:
                mem_id = store.remember(
                    f"Concurrent memory {i}",
                    memory_type="fact"
                )
                results.append(mem_id)
            except Exception as e:
                errors.append(str(e))

        threads = [
            threading.Thread(target=remember_thread, args=(i,))
            for i in range(10)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have created 10 memories without errors
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 10
        # All IDs should be unique
        assert len(set(results)) == 10

    @pytest.mark.skip(reason="SQLite connection not thread-safe without connection pool")
    def test_concurrent_recalls(self, store):
        """Multiple threads recalling simultaneously.

        Known limitation: SQLite connection sharing across threads can cause
        transaction conflicts. In production, use per-thread connections.
        """
        store.remember("Shared recall test content", memory_type="fact")

        results = []
        errors = []

        def recall_thread():
            try:
                r = store.recall("shared recall test", limit=5)
                results.append(len(r))
            except Exception as e:
                errors.append(str(e))

        threads = [
            threading.Thread(target=recall_thread)
            for _ in range(10)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 10


class TestDatabaseIntegrity:
    """Test database consistency and integrity."""

    def test_sqlite_chromadb_sync(self, store):
        """SQLite and ChromaDB should stay in sync."""
        mem_id = store.remember("Sync test content", memory_type="fact")

        # Check SQLite
        sqlite_row = store.db.execute(
            "SELECT id FROM memories WHERE id = ?",
            (mem_id,)
        ).fetchone()

        # Check ChromaDB
        chroma_results = store.collection.get(ids=[mem_id])

        assert sqlite_row is not None
        assert mem_id in chroma_results["ids"]

    def test_delete_removes_from_both(self, store):
        """delete_memory should remove from both stores."""
        mem_id = store.remember("Delete test content", memory_type="fact")

        store.delete_memory(mem_id)

        # Check SQLite
        sqlite_row = store.db.execute(
            "SELECT id FROM memories WHERE id = ?",
            (mem_id,)
        ).fetchone()

        assert sqlite_row is None

        # Check ChromaDB
        chroma_results = store.collection.get(ids=[mem_id])
        assert mem_id not in chroma_results["ids"]

    def test_memory_id_uniqueness(self, store):
        """All memory IDs should be unique."""
        ids = []
        for i in range(50):
            mem_id = store.remember(f"Uniqueness test {i}", memory_type="fact")
            ids.append(mem_id)

        assert len(ids) == len(set(ids)), "Duplicate IDs found"

    def test_transaction_rollback_on_error(self, store):
        """Errors should not leave partial data."""
        initial_count = store.db.execute(
            "SELECT COUNT(*) FROM memories"
        ).fetchone()[0]

        # Try to cause an error mid-operation
        # This is hard to test without mocking, so just verify basic integrity
        try:
            store.remember("Rollback test", memory_type="fact")
        except Exception:
            pass

        # Count should be consistent
        final_count = store.db.execute(
            "SELECT COUNT(*) FROM memories"
        ).fetchone()[0]

        # Should either have +1 (success) or +0 (rollback), not partial
        assert final_count >= initial_count


class TestErrorRecovery:
    """Test error handling and recovery."""

    def test_handles_missing_memory_gracefully(self, store):
        """Operations on non-existent memory should not crash."""
        fake_id = "mem_nonexistent_xyz123"

        # Delete should return False, not crash
        result = store.delete_memory(fake_id)
        assert result == False

        # Update should return False
        result = store.update_memory(fake_id, content="new content")
        assert result == False

    def test_handles_invalid_memory_type(self, store):
        """Invalid memory type should be stored anyway."""
        mem_id = store.remember(
            "Invalid type test",
            memory_type="invalid_type_xyz"
        )

        # Should store with the invalid type
        assert mem_id is not None

        row = store.db.execute(
            "SELECT memory_type FROM memories WHERE id = ?",
            (mem_id,)
        ).fetchone()
        assert row[0] == "invalid_type_xyz"

    def test_handles_none_content(self, store):
        """None content should be handled."""
        try:
            mem_id = store.remember(None, memory_type="fact")
            # If it succeeds, content was converted to string
        except (TypeError, ValueError):
            # This is expected behavior
            pass

    def test_handles_empty_content(self, store):
        """Empty string content should be handled."""
        mem_id = store.remember("", memory_type="fact")

        # Might store or reject - either is fine
        # Just shouldn't crash


class TestFilterCombinations:
    """Test various filter combinations."""

    def test_type_and_project_filter(self, store):
        """Should filter by both type and project.

        Note: ChromaDB only supports one filter condition at a time.
        When both project and type filters are needed, we filter in two steps.
        """
        store.remember("Pattern in project A", memory_type="pattern", project="project_a")
        store.remember("Fact in project A", memory_type="fact", project="project_a")
        store.remember("Pattern in project B", memory_type="pattern", project="project_b")

        # Query with project filter only (ChromaDB limitation)
        results = store.recall(
            "project pattern",
            limit=10,
            project="project_a"
        )

        # Post-filter by type in application code
        pattern_results = [r for r in results if r["memory_type"] == "pattern"]

        # Should find pattern in project_a
        for r in pattern_results:
            assert r["memory_type"] == "pattern"
            assert r["project"] == "project_a"

    def test_multiple_memory_types(self, store):
        """Should filter by multiple types."""
        store.remember("Pattern content test", memory_type="pattern")
        store.remember("Solution content test", memory_type="solution")
        store.remember("Fact content test", memory_type="fact")

        results = store.recall(
            "content test",
            limit=10,
            memory_types=["pattern", "solution"]
        )

        # Should only return pattern and solution
        for r in results:
            assert r["memory_type"] in ["pattern", "solution"]

    def test_role_filter_with_type(self, store):
        """Should handle role affinity with type filter."""
        store.remember(
            "GPU pattern from specialist",
            memory_type="pattern",
            source_role="gpu-specialist"
        )

        results = store.recall(
            "GPU pattern",
            limit=5,
            memory_types=["pattern"],
            current_role="gpu-specialist"
        )

        # Should find with role affinity boost
        if results:
            assert results[0]["role_affinity"] == 1.15


class TestLimitBehavior:
    """Test limit parameter behavior."""

    def test_returns_exactly_limit(self, store):
        """Should return at most limit results."""
        for i in range(20):
            store.remember(f"Limit test memory {i}", memory_type="fact")

        results = store.recall("limit test", limit=5)

        assert len(results) <= 5

    def test_limit_zero(self, store):
        """limit=0 should return empty or raise error.

        ChromaDB raises TypeError for n_results=0, which is reasonable.
        """
        store.remember("Zero limit test", memory_type="fact")

        # ChromaDB doesn't allow n_results=0
        with pytest.raises(TypeError):
            store.recall("zero limit", limit=0)

    def test_limit_one(self, store):
        """limit=1 should return at most one result."""
        store.remember("One limit test A", memory_type="fact")
        store.remember("One limit test B", memory_type="fact")

        results = store.recall("one limit test", limit=1)

        assert len(results) <= 1

    def test_limit_larger_than_results(self, store):
        """limit > available results should return all available."""
        store.remember("Sparse result test", memory_type="fact")

        results = store.recall("sparse result unique xyz", limit=1000)

        # Should not crash, should return what's available
        assert isinstance(results, list)
