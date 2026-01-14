"""
Performance tests for ChainMind helper audit improvements.

Tests cover:
- Cache hit rates
- Latency improvements
- Concurrent request handling
- Metrics accuracy
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add engram-mcp to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCachePerformance:
    """Test caching performance improvements."""

    @pytest.mark.asyncio
    async def test_cache_hit_rate(self):
        """Test that cache achieves good hit rate for repeated requests."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        mock_router = AsyncMock()
        mock_router.route = AsyncMock(return_value={
            "response": "cached response",
            "provider": "anthropic",
            "metadata": {}
        })

        helper._router = mock_router
        helper._initialized = True

        # Make 10 identical requests
        prompt = "test prompt"
        for _ in range(10):
            await helper.generate(prompt, prefer_claude=True)

        metrics = helper.get_metrics()

        # Should have 1 miss and 9 hits
        assert metrics["cache_misses"] == 1
        assert metrics["cache_hits"] == 9
        assert metrics["cache_hit_rate_percent"] == 90.0

        # Router should only be called once
        assert mock_router.route.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_latency_improvement(self):
        """Test that cached requests are faster."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Simulate slow router
        async def slow_route(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return {
                "response": "response",
                "provider": "anthropic",
                "metadata": {}
            }

        mock_router = AsyncMock()
        mock_router.route = AsyncMock(side_effect=slow_route)

        helper._router = mock_router
        helper._initialized = True

        # First request (cache miss)
        start = time.time()
        await helper.generate("test prompt")
        first_latency = time.time() - start

        # Second request (cache hit)
        start = time.time()
        await helper.generate("test prompt")
        second_latency = time.time() - start

        # Cached request should be much faster
        assert second_latency < first_latency * 0.1  # At least 10x faster

    @pytest.mark.asyncio
    async def test_cache_size_limit(self):
        """Test that cache respects size limit."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper(cache_size=3)

        mock_router = AsyncMock()
        mock_router.route = AsyncMock(return_value={
            "response": "response",
            "provider": "anthropic",
            "metadata": {}
        })

        helper._router = mock_router
        helper._initialized = True

        # Fill cache beyond limit
        for i in range(5):
            await helper.generate(f"prompt {i}")

        # Cache should not exceed size limit
        assert len(helper._response_cache) <= 3


class TestConcurrentRequests:
    """Test concurrent request handling."""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling of concurrent requests."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        mock_router = AsyncMock()
        mock_router.route = AsyncMock(return_value={
            "response": "response",
            "provider": "anthropic",
            "metadata": {}
        })

        helper._router = mock_router
        helper._initialized = True

        # Make 10 concurrent requests
        tasks = [
            helper.generate(f"prompt {i}")
            for i in range(10)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all("response" in r for r in results)

        metrics = helper.get_metrics()
        assert metrics["total_requests"] == 10

    @pytest.mark.asyncio
    async def test_concurrent_cached_requests(self):
        """Test that concurrent identical requests share cache."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        call_count = 0

        async def counting_route(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return {
                "response": "response",
                "provider": "anthropic",
                "metadata": {}
            }

        mock_router = AsyncMock()
        mock_router.route = AsyncMock(side_effect=counting_route)

        helper._router = mock_router
        helper._initialized = True

        # Make 10 concurrent identical requests
        tasks = [
            helper.generate("same prompt")
            for _ in range(10)
        ]

        await asyncio.gather(*tasks)

        # Should only call router once (or very few times due to race condition)
        # In practice, there might be a few calls due to race conditions, but should be much less than 10
        assert call_count < 10


class TestMetricsAccuracy:
    """Test metrics collection accuracy."""

    @pytest.mark.asyncio
    async def test_latency_metrics(self):
        """Test that latency metrics are accurate."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        async def delayed_route(*args, **kwargs):
            await asyncio.sleep(0.1)
            return {
                "response": "response",
                "provider": "anthropic",
                "metadata": {}
            }

        mock_router = AsyncMock()
        mock_router.route = AsyncMock(side_effect=delayed_route)

        helper._router = mock_router
        helper._initialized = True

        await helper.generate("test")

        metrics = helper.get_metrics()

        # Average latency should be around 0.1 seconds
        assert 0.05 < metrics["average_latency_seconds"] < 0.15
        assert metrics["total_latency"] > 0

    @pytest.mark.asyncio
    async def test_provider_usage_tracking(self):
        """Test provider usage statistics."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        mock_router = AsyncMock()
        mock_router.route = AsyncMock(return_value={
            "response": "response",
            "provider": "anthropic",
            "metadata": {}
        })

        helper._router = mock_router
        helper._initialized = True

        # Make requests
        await helper.generate("test1", prefer_claude=True)
        await helper.generate("test2", prefer_claude=True)

        metrics = helper.get_metrics()

        assert metrics["provider_usage"]["anthropic"] == 2

    @pytest.mark.asyncio
    async def test_error_count_tracking(self):
        """Test error count tracking."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        mock_router = AsyncMock()
        mock_router.route = AsyncMock(side_effect=Exception("test error"))

        helper._router = mock_router
        helper._initialized = True

        try:
            await helper.generate("test")
        except Exception:
            pass

        metrics = helper.get_metrics()

        assert metrics["failed_requests"] > 0
        assert "Exception" in metrics["error_counts"] or len(metrics["error_counts"]) > 0


class TestPerformanceTargets:
    """Test that performance meets targets."""

    @pytest.mark.asyncio
    async def test_cache_hit_rate_target(self):
        """Test cache hit rate meets >30% target."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        mock_router = AsyncMock()
        mock_router.route = AsyncMock(return_value={
            "response": "response",
            "provider": "anthropic",
            "metadata": {}
        })

        helper._router = mock_router
        helper._initialized = True

        # Mix of unique and repeated prompts
        prompts = ["prompt1", "prompt2", "prompt1", "prompt3", "prompt2"] * 2

        for prompt in prompts:
            await helper.generate(prompt)

        metrics = helper.get_metrics()

        # Should have >30% hit rate
        assert metrics["cache_hit_rate_percent"] >= 30.0

    @pytest.mark.asyncio
    async def test_latency_target(self):
        """Test that p95 latency meets <2s target."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        async def fast_route(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms
            return {
                "response": "response",
                "provider": "anthropic",
                "metadata": {}
            }

        mock_router = AsyncMock()
        mock_router.route = AsyncMock(side_effect=fast_route)

        helper._router = mock_router
        helper._initialized = True

        # Make multiple requests
        for _ in range(20):
            await helper.generate("test")

        metrics = helper.get_metrics()

        # Average latency should be well under 2s
        assert metrics["average_latency_seconds"] < 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

