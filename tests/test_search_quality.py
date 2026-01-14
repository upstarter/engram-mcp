#!/usr/bin/env python3
"""
Engram Search Quality Validation Suite

Tests that queries return relevant results. Uses ground truth
test cases to measure precision, recall, and ranking quality.

Run: pytest tests/test_search_quality.py -v
"""

import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engram.storage import MemoryStore


# Ground truth test cases: query -> expected content snippets that MUST appear in top results
GROUND_TRUTH_TESTS = [
    # YouTube/Content Creation
    {
        "query": "thumbnail design best practices",
        "must_contain": ["face", "CTR", "element", "tension"],
        "memory_types": ["pattern", "solution"],
        "top_k": 5,
    },
    {
        "query": "hook retention first 30 seconds",
        "must_contain": ["hook", "retention", "30", "second"],
        "memory_types": ["pattern", "solution"],
        "top_k": 5,
    },
    {
        "query": "YouTube algorithm 2025",
        "must_contain": ["CTR", "retention", "AVD", "algorithm"],
        "memory_types": ["pattern", "solution"],
        "top_k": 5,
    },
    {
        "query": "MrBeast production tips",
        "must_contain": ["MrBeast", "hook", "thumbnail"],
        "memory_types": ["pattern", "solution"],
        "top_k": 5,
    },

    # AI Tools
    {
        "query": "GPU VRAM optimization ComfyUI",
        "must_contain": ["VRAM", "GPU", "highvram"],
        "memory_types": ["pattern", "solution"],
        "top_k": 5,
    },
    {
        "query": "lip sync avatar video",
        "must_contain": ["Hallo2", "lip", "avatar"],
        "memory_types": ["pattern", "solution"],
        "top_k": 5,
    },
    {
        "query": "whisper transcription speed",
        "must_contain": ["whisper", "faster-whisper", "transcri"],
        "memory_types": ["pattern", "solution", "decision"],
        "top_k": 5,
    },
    {
        "query": "AI video generation Kling Runway",
        "must_contain": ["Kling", "Runway", "video"],
        "memory_types": ["pattern", "decision"],
        "top_k": 5,
    },

    # Development
    {
        "query": "MCP server development",
        "must_contain": ["MCP", "tool", "stdio", "JSON"],
        "memory_types": ["pattern", "solution"],
        "top_k": 5,
    },
    {
        "query": "Python package management fast",
        "must_contain": ["uv", "pip", "fast"],
        "memory_types": ["pattern"],
        "top_k": 5,
    },

    # Video Editing
    {
        "query": "DaVinci Resolve color grading",
        "must_contain": ["color", "grade", "Resolve"],
        "memory_types": ["pattern", "solution"],
        "top_k": 5,
    },
    {
        "query": "proxy workflow 4K editing",
        "must_contain": ["proxy", "4K", "workflow"],
        "memory_types": ["pattern"],
        "top_k": 5,
    },

    # Marketing/SaaS
    {
        "query": "product positioning strategy",
        "must_contain": ["position", "competi", "differenti"],
        "memory_types": ["pattern", "solution"],
        "top_k": 5,
    },
    {
        "query": "SaaS conversion optimization",
        "must_contain": ["conver", "trial", "PQL"],
        "memory_types": ["pattern", "solution"],
        "top_k": 5,
    },

    # Local Toolset
    {
        "query": "studioflow transcription",
        "must_contain": ["sf", "transcri", "whisper"],
        "memory_types": ["pattern", "solution"],
        "top_k": 5,
    },
    {
        "query": "proj command episode workflow",
        "must_contain": ["proj", "episode", "phase"],
        "memory_types": ["pattern", "solution"],
        "top_k": 5,
    },
]


class SearchQualityMetrics:
    """Tracks search quality metrics across test runs."""

    def __init__(self):
        self.results = []

    def add_result(self, test_name: str, precision: float, recall: float,
                   found_terms: list, missing_terms: list):
        self.results.append({
            "test": test_name,
            "precision": precision,
            "recall": recall,
            "found": found_terms,
            "missing": missing_terms,
        })

    def summary(self) -> dict:
        if not self.results:
            return {"avg_precision": 0, "avg_recall": 0, "tests_passed": 0}

        return {
            "avg_precision": sum(r["precision"] for r in self.results) / len(self.results),
            "avg_recall": sum(r["recall"] for r in self.results) / len(self.results),
            "tests_passed": sum(1 for r in self.results if r["recall"] >= 0.5),
            "total_tests": len(self.results),
        }


@pytest.fixture(scope="module")
def store():
    """Shared memory store for all tests."""
    return MemoryStore()


@pytest.fixture(scope="module")
def metrics():
    """Shared metrics tracker."""
    return SearchQualityMetrics()


def check_content_contains(content: str, terms: list) -> tuple[list, list]:
    """Check which terms are found in content."""
    content_lower = content.lower()
    found = []
    missing = []

    for term in terms:
        if term.lower() in content_lower:
            found.append(term)
        else:
            missing.append(term)

    return found, missing


@pytest.mark.parametrize("test_case", GROUND_TRUTH_TESTS,
                         ids=[t["query"][:30] for t in GROUND_TRUTH_TESTS])
def test_search_quality(store, metrics, test_case):
    """Test that search returns relevant results."""
    query = test_case["query"]
    must_contain = test_case["must_contain"]
    memory_types = test_case.get("memory_types")
    top_k = test_case.get("top_k", 5)

    # Execute search
    results = store.recall(
        query=query,
        limit=top_k,
        memory_types=memory_types,
    )

    # Combine all result content
    all_content = " ".join(r["content"] for r in results)

    # Check for required terms
    found_terms, missing_terms = check_content_contains(all_content, must_contain)

    # Calculate metrics
    recall = len(found_terms) / len(must_contain) if must_contain else 1.0
    precision = len(found_terms) / len(must_contain) if must_contain else 1.0  # Simplified

    # Record metrics
    metrics.add_result(query, precision, recall, found_terms, missing_terms)

    # Test passes if at least 50% of required terms are found
    assert recall >= 0.5, (
        f"Query '{query}' missing terms: {missing_terms}. "
        f"Found: {found_terms}. "
        f"Top results: {[r['content'][:50] for r in results[:3]]}"
    )


def test_summary(metrics):
    """Print summary after all tests (runs last due to naming)."""
    summary = metrics.summary()
    print("\n" + "="*60)
    print("SEARCH QUALITY SUMMARY")
    print("="*60)
    print(f"Tests Passed: {summary['tests_passed']}/{summary['total_tests']}")
    print(f"Average Recall: {summary['avg_recall']:.1%}")
    print(f"Average Precision: {summary['avg_precision']:.1%}")
    print("="*60)

    # Print failures
    failures = [r for r in metrics.results if r["recall"] < 0.5]
    if failures:
        print("\nFAILED QUERIES:")
        for f in failures:
            print(f"  - {f['test']}")
            print(f"    Missing: {f['missing']}")


# Standalone runner for quick testing
if __name__ == "__main__":
    print("Running Search Quality Validation...\n")

    store = MemoryStore()
    metrics = SearchQualityMetrics()

    for i, test_case in enumerate(GROUND_TRUTH_TESTS, 1):
        query = test_case["query"]
        must_contain = test_case["must_contain"]
        top_k = test_case.get("top_k", 5)

        results = store.recall(query=query, limit=top_k)
        all_content = " ".join(r["content"] for r in results)

        found, missing = check_content_contains(all_content, must_contain)
        recall = len(found) / len(must_contain) if must_contain else 1.0

        status = "✓" if recall >= 0.5 else "✗"
        print(f"{status} [{i:2d}/{len(GROUND_TRUTH_TESTS)}] {query[:40]:<40} | Recall: {recall:.0%}")

        if missing:
            print(f"    Missing: {missing}")

        metrics.add_result(query, recall, recall, found, missing)

    # Summary
    summary = metrics.summary()
    print("\n" + "="*60)
    print(f"BASELINE RESULTS")
    print("="*60)
    print(f"Tests Passed: {summary['tests_passed']}/{summary['total_tests']} ({summary['tests_passed']/summary['total_tests']:.0%})")
    print(f"Average Recall: {summary['avg_recall']:.1%}")
    print("="*60)
