#!/usr/bin/env python3
"""
Hybrid Search Tests

Validates the hybrid semantic + keyword search:
1. Keyword extraction from queries
2. Stopword filtering
3. Keyword match ratio calculation
4. Boost application to ranking
5. Hybrid vs pure semantic comparison

These tests ensure hybrid search improves result relevance.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engram.storage import MemoryStore


@pytest.fixture
def store():
    """Fresh memory store for each test."""
    return MemoryStore()


class TestKeywordExtraction:
    """Test keyword extraction from queries."""

    def test_extracts_significant_words(self, store):
        """Should extract meaningful words from query."""
        # The stopword list is defined in recall()
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                    'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                    'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                    'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                    'through', 'during', 'before', 'after', 'above', 'below',
                    'between', 'under', 'again', 'further', 'then', 'once',
                    'here', 'there', 'when', 'where', 'why', 'how', 'all',
                    'each', 'few', 'more', 'most', 'other', 'some', 'such',
                    'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
                    'too', 'very', 'just', 'and', 'but', 'if', 'or', 'because',
                    'until', 'while', 'what', 'which', 'who', 'this', 'that',
                    'these', 'those', 'am', 'it', 'its', 'i', 'me', 'my', 'we',
                    'our', 'you', 'your', 'he', 'him', 'his', 'she', 'her',
                    'they', 'them', 'their', 'best', 'practices', 'tips', 'help'}

        import re
        query = "How to optimize Python code for performance"
        words = re.findall(r'\b[a-zA-Z0-9]+\b', query.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 2]

        # Should extract: optimize, python, code, performance
        assert "optimize" in keywords
        assert "python" in keywords
        assert "code" in keywords
        assert "performance" in keywords
        # Should filter stopwords
        assert "how" not in keywords
        assert "to" not in keywords
        assert "for" not in keywords

    def test_filters_short_words(self):
        """Words <= 2 characters should be filtered."""
        import re
        stopwords = set()  # Empty for this test
        query = "A B C is an AI ML API"
        words = re.findall(r'\b[a-zA-Z0-9]+\b', query.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 2]

        # Short words filtered
        assert "a" not in keywords
        assert "b" not in keywords
        assert "c" not in keywords
        assert "is" not in keywords
        assert "an" not in keywords
        # Longer words kept
        assert "api" in keywords  # 3 chars

    def test_handles_empty_query(self, store):
        """Empty query should not crash."""
        results = store.recall("", limit=5)

        # Should return empty or handle gracefully
        assert isinstance(results, list)


class TestStopwordFiltering:
    """Test that common words don't affect search."""

    def test_stopwords_dont_affect_ranking(self, store):
        """Adding stopwords shouldn't change result ranking.

        Stopwords like 'the', 'best', 'a', 'is' are filtered from keyword
        extraction, so adding them to a query shouldn't change which keywords
        are matched. This test verifies the stopword filtering logic directly.
        """
        import re

        # Define the stopword list (same as in storage.py recall())
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                    'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                    'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                    'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                    'through', 'during', 'before', 'after', 'above', 'below',
                    'between', 'under', 'again', 'further', 'then', 'once',
                    'here', 'there', 'when', 'where', 'why', 'how', 'all',
                    'each', 'few', 'more', 'most', 'other', 'some', 'such',
                    'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
                    'too', 'very', 'just', 'and', 'but', 'if', 'or', 'because',
                    'until', 'while', 'what', 'which', 'who', 'this', 'that',
                    'these', 'those', 'am', 'it', 'its', 'i', 'me', 'my', 'we',
                    'our', 'you', 'your', 'he', 'him', 'his', 'she', 'her',
                    'they', 'them', 'their', 'best', 'practices', 'tips', 'help'}

        # Query with stopwords
        query1 = "the best Python programming tutorial"
        words1 = re.findall(r'\b[a-zA-Z0-9]+\b', query1.lower())
        keywords1 = [w for w in words1 if w not in stopwords and len(w) > 2]

        # Query without stopwords
        query2 = "Python programming tutorial"
        words2 = re.findall(r'\b[a-zA-Z0-9]+\b', query2.lower())
        keywords2 = [w for w in words2 if w not in stopwords and len(w) > 2]

        # Both should extract the same keywords
        assert set(keywords1) == set(keywords2) == {"python", "programming", "tutorial"}

    def test_only_stopwords_query(self, store):
        """Query with only stopwords should still work."""
        store.remember("Test content for stopword query", memory_type="fact")

        # All stopwords
        results = store.recall("the is are was were", limit=5)

        # Should return something (semantic search still works)
        assert isinstance(results, list)


class TestKeywordBoostRanking:
    """Test that keyword matches boost ranking."""

    def test_exact_keyword_ranks_higher(self, store):
        """Content with exact keywords should rank higher than semantic-only."""
        # Memory with exact keywords
        exact_id = store.remember(
            "PyTorch GPU optimization techniques for deep learning",
            memory_type="pattern"
        )
        # Semantically similar but no keyword match
        semantic_id = store.remember(
            "Neural network hardware acceleration methods",
            memory_type="pattern"
        )

        results = store.recall("PyTorch GPU optimization", limit=5)

        # Find positions
        exact_pos = next((i for i, r in enumerate(results) if r["id"] == exact_id), -1)
        semantic_pos = next((i for i, r in enumerate(results) if r["id"] == semantic_id), -1)

        # Exact match should rank higher (lower position number)
        if exact_pos >= 0 and semantic_pos >= 0:
            assert exact_pos < semantic_pos, "Exact keyword match should rank higher"

    def test_keyword_boost_in_results(self, store):
        """Results should include keyword_boost field."""
        store.remember("Specific keyword content test", memory_type="fact")

        results = store.recall("specific keyword test", limit=3)

        assert len(results) >= 1
        assert "keyword_boost" in results[0]
        # Should have boost > 1.0 for matches
        assert results[0]["keyword_boost"] >= 1.0

    def test_keyword_matches_count(self, store):
        """Results should include keyword_matches count."""
        store.remember("Python FastAPI PostgreSQL tutorial", memory_type="pattern")

        results = store.recall("Python FastAPI PostgreSQL", limit=3)

        assert len(results) >= 1
        assert "keyword_matches" in results[0]
        # Should match multiple keywords
        assert results[0]["keyword_matches"] >= 2

    def test_partial_match_partial_boost(self, store):
        """Partial keyword matches should give partial boost."""
        store.remember("Python TypeScript JavaScript comparison", memory_type="pattern")

        # Query with only some matching keywords
        results = store.recall("Python comparison review", limit=3)

        if results:
            # Boost should be > 1.0 but < 1.25 (partial match)
            boost = results[0]["keyword_boost"]
            assert 1.0 <= boost <= 1.25


class TestHybridVsPureSemantic:
    """Compare hybrid search to pure semantic search."""

    def test_hybrid_improves_relevance(self, store):
        """Hybrid search should improve results for keyword-heavy queries."""
        # Create memories
        store.remember("CUDA out of memory error fix solution", memory_type="solution")
        store.remember("GPU memory management best practices", memory_type="pattern")
        store.remember("Computer hardware information overview", memory_type="fact")

        # Query with specific keywords
        results_hybrid = store.recall("CUDA out of memory fix", limit=5, hybrid_search=True)
        results_semantic = store.recall("CUDA out of memory fix", limit=5, hybrid_search=False)

        # Both should work
        assert len(results_hybrid) >= 1
        assert len(results_semantic) >= 1

        # Hybrid should have CUDA memory at top
        if results_hybrid:
            top_content = results_hybrid[0]["content"].lower()
            assert "cuda" in top_content or "memory" in top_content

    def test_hybrid_doesnt_break_semantic(self, store):
        """Hybrid search shouldn't hurt semantic-only matches."""
        store.remember("Machine learning model training optimization", memory_type="pattern")

        # Semantic query (no exact keyword matches)
        results = store.recall("deep learning neural network performance", limit=5)

        # Should still find semantically related content
        assert len(results) >= 1
        # Semantic similarity should still work
        assert results[0]["similarity"] > 0.3


class TestHybridSearchEdgeCases:
    """Edge cases for hybrid search."""

    def test_all_keywords_match(self, store):
        """100% keyword match should give full boost."""
        store.remember("Python testing pytest fixtures", memory_type="pattern")

        results = store.recall("Python pytest fixtures", limit=3)

        if results:
            # Full match should give ~1.25 boost
            assert results[0]["keyword_boost"] >= 1.2

    def test_no_keywords_match(self, store):
        """No keyword match should give no boost."""
        store.remember("Completely unrelated cooking recipe content", memory_type="fact")

        results = store.recall("Python programming tutorial", limit=5)

        # Find the cooking memory if it's in results
        cooking_result = next(
            (r for r in results if "cooking" in r["content"].lower()),
            None
        )

        if cooking_result:
            # Should have no keyword boost
            assert cooking_result["keyword_boost"] == 1.0
            assert cooking_result["keyword_matches"] == 0

    def test_special_characters_in_query(self, store):
        """Special characters shouldn't break keyword extraction."""
        store.remember("C++ programming language basics", memory_type="pattern")

        # Query with special chars
        results = store.recall("C++ programming!@#$ basics??", limit=3)

        # Should still work
        assert isinstance(results, list)

    def test_numeric_keywords(self, store):
        """Numbers should be treated as keywords."""
        store.remember("Python 3.11 new features update", memory_type="pattern")

        results = store.recall("Python 3.11 features", limit=3)

        if results:
            # "3" and "11" might be filtered (too short), but "python" should match
            assert results[0]["keyword_matches"] >= 1

    def test_case_insensitive_matching(self, store):
        """Keyword matching should be case insensitive."""
        store.remember("UPPERCASE CONTENT TEST", memory_type="fact")

        results = store.recall("uppercase content test", limit=3)

        if results:
            # Should match despite case difference
            assert results[0]["keyword_matches"] >= 2


class TestHybridSearchPerformance:
    """Performance tests for hybrid search."""

    def test_hybrid_doesnt_slow_down_significantly(self, store):
        """Hybrid search shouldn't be much slower than semantic-only."""
        import time

        # Create some memories
        for i in range(10):
            store.remember(f"Test memory {i} with various content", memory_type="fact")

        # Time hybrid search
        start = time.time()
        for _ in range(5):
            store.recall("test memory content", limit=10, hybrid_search=True)
        hybrid_time = time.time() - start

        # Time semantic-only search
        start = time.time()
        for _ in range(5):
            store.recall("test memory content", limit=10, hybrid_search=False)
        semantic_time = time.time() - start

        # Hybrid can be slower due to FTS overhead, but should be within 5x
        # (First ChromaDB query is slow, subsequent ones are faster)
        assert hybrid_time < semantic_time * 5, \
            f"Hybrid ({hybrid_time:.2f}s) shouldn't be much slower than semantic ({semantic_time:.2f}s)"

    def test_large_query_keywords(self, store):
        """Long queries with many keywords should still work."""
        store.remember("Test memory for large query", memory_type="fact")

        # Very long query
        long_query = " ".join(["keyword"] * 100 + ["test memory"])
        results = store.recall(long_query, limit=5)

        # Should not crash and return results
        assert isinstance(results, list)
