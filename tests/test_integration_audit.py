"""
Integration tests for ChainMind helper audit improvements.

Tests cover:
- Full request flow with real providers (mocked)
- Fallback scenarios
- Error handling paths
- Configuration loading
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os

# Add engram-mcp to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestFullRequestFlow:
    """Test complete request flow with all improvements."""

    @pytest.mark.asyncio
    async def test_successful_request_with_caching(self):
        """Test successful request that gets cached."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Mock router
        mock_router = AsyncMock()
        mock_router.route = AsyncMock(return_value={
            "response": "test response",
            "provider": "anthropic",
            "metadata": {}
        })
        helper._router = mock_router
        helper._initialized = True

        # First request - should miss cache
        result1 = await helper.generate("test prompt", prefer_claude=True)

        assert result1["response"] == "test response"
        assert result1["from_cache"] == False
        assert helper._metrics["cache_misses"] == 1

        # Second request - should hit cache
        result2 = await helper.generate("test prompt", prefer_claude=True)

        assert result2["response"] == "test response"
        assert result2["from_cache"] == True
        assert helper._metrics["cache_hits"] == 1

        # Router should only be called once
        assert mock_router.route.call_count == 1

    @pytest.mark.asyncio
    async def test_fallback_scenario(self):
        """Test fallback when Claude hits usage limit."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Mock router to fail with quota error, then succeed with fallback
        mock_router = AsyncMock()

        # First call (Claude) fails with quota error
        quota_error = Exception("quota exceeded")
        quota_error.code = "CM-1801"

        # Second call (OpenAI) succeeds
        mock_router.route = AsyncMock(side_effect=[
            quota_error,
            {
                "response": "fallback response",
                "provider": "openai",
                "metadata": {}
            }
        ])

        helper._router = mock_router
        helper._initialized = True

        result = await helper.generate("test prompt", prefer_claude=True)

        assert result["response"] == "fallback response"
        assert result["provider"] == "openai"
        assert result["fallback_used"] == True
        assert result["usage_limit_hit"] == True
        assert helper._metrics["fallback_requests"] == 1

    @pytest.mark.asyncio
    async def test_all_fallbacks_fail(self):
        """Test error aggregation when all fallbacks fail."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Mock router to fail all attempts
        mock_router = AsyncMock()
        error = Exception("provider unavailable")
        mock_router.route = AsyncMock(side_effect=error)

        helper._router = mock_router
        helper._initialized = True

        # Mock error detection to return True for quota error
        with patch.object(helper, '_is_usage_limit_error', return_value=True):
            with pytest.raises(RuntimeError) as exc_info:
                await helper.generate("test prompt", prefer_claude=True)

            # Should have error details
            assert hasattr(exc_info.value, 'error_details') or "all fallback providers failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_correlation_id_propagation(self):
        """Test that correlation IDs are generated and propagated."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        mock_router = AsyncMock()
        mock_router.route = AsyncMock(return_value={
            "response": "test",
            "provider": "anthropic",
            "metadata": {}
        })

        helper._router = mock_router
        helper._initialized = True

        result = await helper.generate("test prompt")

        assert "correlation_id" in result
        assert len(result["correlation_id"]) == 8  # UUID first 8 chars
        assert result["latency_seconds"] > 0


class TestConfigurationIntegration:
    """Test configuration loading and usage."""

    def test_config_from_environment(self):
        """Test configuration loading from environment variables."""
        from engram.chainmind_helper import ChainMindHelper

        with patch.dict(os.environ, {
            "CHAINMIND_FALLBACK_PROVIDERS": "openai,gemini",
            "CHAINMIND_MAX_TOKENS": "2000",
            "CHAINMIND_TIMEOUT": "45.0"
        }):
            helper = ChainMindHelper()

            assert "openai" in helper._fallback_providers
            assert "gemini" in helper._fallback_providers
            assert helper._max_tokens_per_request == 2000
            assert helper._request_timeout_seconds == 45.0

    def test_config_priority_order(self):
        """Test that provided config overrides env and file."""
        from engram.chainmind_helper import ChainMindHelper

        with patch.dict(os.environ, {
            "CHAINMIND_FALLBACK_PROVIDERS": "openai"
        }):
            provided_config = {
                "fallback_providers": ["custom"]
            }

            helper = ChainMindHelper(config=provided_config)

            # Provided config should win
            assert helper._fallback_providers == ["custom"]


class TestErrorHandlingIntegration:
    """Test error handling in full flow."""

    @pytest.mark.asyncio
    async def test_error_classification_integration(self):
        """Test error classification in real request flow."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Mock error classifier
        mock_classifier = Mock()
        mock_classifier.classify_error = Mock(return_value="quota_exceeded")
        helper._error_classifier = mock_classifier

        # Mock router to raise quota error
        mock_router = AsyncMock()
        error = Exception("quota exceeded")
        mock_router.route = AsyncMock(side_effect=error)

        helper._router = mock_router
        helper._initialized = True

        # Should use classifier
        with patch.object(helper, '_is_usage_limit_error', return_value=True):
            try:
                await helper.generate("test")
            except RuntimeError:
                pass  # Expected to fail

        # Classifier should have been called
        assert mock_classifier.classify_error.called

    @pytest.mark.asyncio
    async def test_health_check_integration(self):
        """Test health checking in request flow."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Mark provider as unhealthy
        helper._update_provider_health("anthropic", False)
        helper._update_provider_health("anthropic", False)
        helper._update_provider_health("anthropic", False)

        mock_router = AsyncMock()
        helper._router = mock_router
        helper._initialized = True

        # Should skip unhealthy provider
        with pytest.raises(RuntimeError, match="circuit breaker open"):
            await helper._try_provider_with_timeout(
                "test prompt",
                "anthropic",
                correlation_id="test-123"
            )

        assert helper._metrics["circuit_breaker_skips"] > 0


class TestMetricsIntegration:
    """Test metrics collection in integration scenarios."""

    @pytest.mark.asyncio
    async def test_metrics_tracking_integration(self):
        """Test that metrics are tracked during requests."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        mock_router = AsyncMock()
        mock_router.route = AsyncMock(return_value={
            "response": "test",
            "provider": "anthropic",
            "metadata": {}
        })

        helper._router = mock_router
        helper._initialized = True

        initial_metrics = helper.get_metrics()
        initial_total = initial_metrics["total_requests"]

        await helper.generate("test prompt")

        updated_metrics = helper.get_metrics()

        assert updated_metrics["total_requests"] == initial_total + 1
        assert updated_metrics["successful_requests"] > initial_metrics.get("successful_requests", 0)
        assert updated_metrics["provider_usage"]["anthropic"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

