"""
Comprehensive performance tests for ChainMind + engram-mcp integration.

Tests cover:
- Response times
- Throughput
- Memory usage
- Concurrent operations
- Scalability
"""

import pytest
import asyncio
import time
import sys
import os
from unittest.mock import Mock, AsyncMock
from statistics import mean, median

# Add engram-mcp to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestResponseTimes:
    """Test response time performance."""

    def test_prompt_generation_speed(self):
        """Test prompt generation is fast."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        times = []

        for _ in range(20):
            start = time.perf_counter()
            generator.generate_prompt(
                task="Write a function",
                strategy="balanced"
            )
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        avg_time = mean(times)
        p95_time = sorted(times)[int(len(times) * 0.95)]

        # Should be very fast (< 10ms average)
        assert avg_time < 0.01, f"Average time too slow: {avg_time*1000:.2f}ms"
        assert p95_time < 0.05, f"P95 time too slow: {p95_time*1000:.2f}ms"

    def test_usage_limit_detection_speed(self):
        """Test usage limit detection is fast."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        times = []

        errors = [
            Exception("quota exceeded"),
            Exception("usage limit"),
            Exception("token limit"),
            Exception("network error"),
        ] * 50

        for error in errors:
            start = time.perf_counter()
            helper._is_usage_limit_error(error)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        avg_time = mean(times)
        max_time = max(times)

        # Should be extremely fast (< 1ms)
        assert avg_time < 0.001, f"Average detection time too slow: {avg_time*1000:.3f}ms"
        assert max_time < 0.01, f"Max detection time too slow: {max_time*1000:.3f}ms"

    @pytest.mark.asyncio
    async def test_helper_initialization_speed(self):
        """Test helper initialization is fast."""
        from engram.chainmind_helper import ChainMindHelper

        times = []

        for _ in range(10):
            helper = ChainMindHelper()
            start = time.perf_counter()
            helper.is_available()  # Triggers initialization
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        avg_time = mean(times)
        p95_time = sorted(times)[int(len(times) * 0.95)]

        # Should be reasonably fast
        assert avg_time < 0.1, f"Average initialization time too slow: {avg_time*1000:.2f}ms"
        assert p95_time < 0.5, f"P95 initialization time too slow: {p95_time*1000:.2f}ms"


class TestThroughput:
    """Test throughput performance."""

    def test_prompt_generation_throughput(self):
        """Test prompt generation throughput."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        count = 100

        start = time.perf_counter()
        for _ in range(count):
            generator.generate_prompt(
                task="Write a function",
                strategy="balanced"
            )
        elapsed = time.perf_counter() - start

        throughput = count / elapsed

        # Should handle at least 100 prompts/second
        assert throughput > 100, f"Throughput too low: {throughput:.1f} prompts/sec"

    def test_error_detection_throughput(self):
        """Test error detection throughput."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        count = 1000

        errors = [Exception("quota exceeded")] * count

        start = time.perf_counter()
        for error in errors:
            helper._is_usage_limit_error(error)
        elapsed = time.perf_counter() - start

        throughput = count / elapsed

        # Should handle at least 10k detections/second
        assert throughput > 10000, f"Throughput too low: {throughput:.1f} detections/sec"


class TestConcurrentOperations:
    """Test concurrent operation performance."""

    @pytest.mark.asyncio
    async def test_concurrent_prompt_generation(self):
        """Test concurrent prompt generation."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        async def generate_one(i):
            return generator.generate_prompt(
                task=f"Task {i}",
                strategy="balanced"
            )

        count = 50
        start = time.perf_counter()
        results = await asyncio.gather(*[generate_one(i) for i in range(count)])
        elapsed = time.perf_counter() - start

        assert len(results) == count
        assert all("prompt" in r for r in results)

        # Concurrent should be faster than sequential
        throughput = count / elapsed
        assert throughput > 50, f"Concurrent throughput too low: {throughput:.1f} prompts/sec"

    @pytest.mark.asyncio
    async def test_concurrent_error_detection(self):
        """Test concurrent error detection."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        async def detect_one(error):
            return helper._is_usage_limit_error(error)

        errors = [Exception("quota exceeded")] * 100

        start = time.perf_counter()
        results = await asyncio.gather(*[detect_one(e) for e in errors])
        elapsed = time.perf_counter() - start

        assert len(results) == len(errors)
        assert all(isinstance(r, bool) for r in results)

        throughput = len(errors) / elapsed
        assert throughput > 1000, f"Concurrent detection throughput too low: {throughput:.1f} detections/sec"


class TestMemoryUsage:
    """Test memory usage characteristics."""

    def test_prompt_generator_memory_footprint(self):
        """Test prompt generator has small memory footprint."""
        import sys
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        size = sys.getsizeof(generator)

        # Should be small (< 1KB)
        assert size < 1024, f"Generator too large: {size} bytes"

    def test_helper_memory_footprint(self):
        """Test helper has small memory footprint."""
        import sys
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        size = sys.getsizeof(helper)

        # Should be small (< 2KB)
        assert size < 2048, f"Helper too large: {size} bytes"

    def test_prompt_result_size(self):
        """Test prompt result size is reasonable."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = generator.generate_prompt(
            task="Write a function",
            strategy="balanced"
        )

        # Serialize to estimate size
        import json
        size = len(json.dumps(result))

        # Should be reasonable (< 10KB for typical prompt)
        assert size < 10240, f"Result too large: {size} bytes"


class TestScalability:
    """Test scalability characteristics."""

    def test_prompt_generation_scales_linearly(self):
        """Test prompt generation scales linearly."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        counts = [10, 50, 100]
        times_per_count = []

        for count in counts:
            start = time.perf_counter()
            for _ in range(count):
                generator.generate_prompt(
                    task="Write a function",
                    strategy="balanced"
                )
            elapsed = time.perf_counter() - start
            times_per_count.append(elapsed / count)

        # Times should be roughly similar (linear scaling)
        avg_time = mean(times_per_count)
        max_variance = max(times_per_count) / min(times_per_count)

        # Variance should be reasonable (< 2x difference)
        assert max_variance < 2.0, f"Scaling not linear: {max_variance:.2f}x variance"

    @pytest.mark.asyncio
    async def test_concurrent_scaling(self):
        """Test concurrent operations scale well."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        counts = [10, 50, 100]
        throughputs = []

        for count in counts:
            async def generate_one(i):
                return generator.generate_prompt(
                    task=f"Task {i}",
                    strategy="balanced"
                )

            start = time.perf_counter()
            await asyncio.gather(*[generate_one(i) for i in range(count)])
            elapsed = time.perf_counter() - start
            throughputs.append(count / elapsed)

        # Throughput should increase or stay stable with concurrency
        # (may not be perfectly linear due to GIL, but shouldn't degrade)
        assert throughputs[-1] >= throughputs[0] * 0.5, "Concurrent scaling degraded"


class TestOptimization:
    """Test optimization characteristics."""

    def test_strategy_performance_comparison(self):
        """Compare performance of different strategies."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        strategies = ["concise", "detailed", "structured", "balanced"]

        times = {}
        for strategy in strategies:
            start = time.perf_counter()
            for _ in range(20):
                generator.generate_prompt(
                    task="Write a function",
                    strategy=strategy
                )
            elapsed = time.perf_counter() - start
            times[strategy] = elapsed / 20

        # All strategies should be fast
        for strategy, avg_time in times.items():
            assert avg_time < 0.05, f"{strategy} too slow: {avg_time*1000:.2f}ms"

        # Concise should be fastest
        assert times["concise"] <= times["detailed"], "Concise should be faster than detailed"

    def test_caching_effectiveness(self):
        """Test that repeated operations are fast (if cached)."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # First call (may initialize)
        start1 = time.perf_counter()
        helper.is_available()
        time1 = time.perf_counter() - start1

        # Second call (should be faster if cached)
        start2 = time.perf_counter()
        helper.is_available()
        time2 = time.perf_counter() - start2

        # Second call should be at least as fast
        assert time2 <= time1 * 2, "No caching benefit observed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
