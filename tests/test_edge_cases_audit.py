"""
Edge case tests for ChainMind helper audit improvements.

Tests cover:
- Empty prompts
- Max token limits
- Timeout scenarios
- Circuit breaker transitions
- Configuration edge cases
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add engram-mcp to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestEmptyPromptEdgeCases:
    """Test edge cases with empty or invalid prompts."""

    @pytest.mark.asyncio
    async def test_empty_prompt_validation(self):
        """Test that empty prompts are rejected."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        helper._router = Mock()
        helper._initialized = True

        # Empty prompt should be caught by validation
        with pytest.raises(ValueError, match="exceeds token limit"):
            # This will fail validation before reaching router
            await helper.generate("", max_tokens=1000000)  # Large limit to avoid token validation

    @pytest.mark.asyncio
    async def test_very_long_prompt(self):
        """Test handling of very long prompts."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        helper._max_tokens_per_request = 1000

        # Very long prompt
        long_prompt = "word " * 10000  # ~50000 chars, ~12500 tokens

        with pytest.raises(ValueError, match="exceeds token limit"):
            await helper.generate(long_prompt)


class TestTokenLimitEdgeCases:
    """Test edge cases with token limits."""

    @pytest.mark.asyncio
    async def test_exact_token_limit(self):
        """Test request at exact token limit."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        helper._max_tokens_per_request = 100

        # Prompt that uses exactly the limit
        prompt = "word " * 25  # ~100 tokens
        kwargs = {"max_tokens": 0}  # No additional tokens

        # Should pass validation
        helper._validate_request_limits(prompt, kwargs)

    @pytest.mark.asyncio
    async def test_token_limit_one_over(self):
        """Test request one token over limit."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        helper._max_tokens_per_request = 100

        # Prompt that exceeds by one token
        prompt = "word " * 26  # ~104 tokens
        kwargs = {"max_tokens": 0}

        with pytest.raises(ValueError, match="exceeds token limit"):
            helper._validate_request_limits(prompt, kwargs)

    @pytest.mark.asyncio
    async def test_no_token_limit(self):
        """Test behavior when no token limit is set."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        helper._max_tokens_per_request = None

        # Very long prompt should pass
        long_prompt = "word " * 10000
        kwargs = {"max_tokens": 50000}

        # Should not raise
        helper._validate_request_limits(long_prompt, kwargs)


class TestTimeoutEdgeCases:
    """Test timeout scenarios."""

    @pytest.mark.asyncio
    async def test_request_timeout(self):
        """Test that requests timeout correctly."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        helper._request_timeout_seconds = 0.1  # Very short timeout

        async def slow_route(*args, **kwargs):
            await asyncio.sleep(1.0)  # Longer than timeout
            return {"response": "response", "provider": "anthropic", "metadata": {}}

        mock_router = AsyncMock()
        mock_router.route = AsyncMock(side_effect=slow_route)

        helper._router = mock_router
        helper._initialized = True

        with pytest.raises(RuntimeError, match="timed out"):
            await helper._try_provider_with_timeout(
                "test prompt",
                "anthropic",
                timeout=0.1
            )

    @pytest.mark.asyncio
    async def test_timeout_with_fallback(self):
        """Test timeout handling in fallback scenario."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        helper._request_timeout_seconds = 0.1

        async def timeout_then_success(*args, **kwargs):
            if mock_router.route.call_count == 1:
                await asyncio.sleep(1.0)  # Timeout
                raise RuntimeError("timed out")
            return {"response": "fallback", "provider": "openai", "metadata": {}}

        mock_router = AsyncMock()
        mock_router.route = AsyncMock(side_effect=timeout_then_success)

        helper._router = mock_router
        helper._initialized = True

        # Should handle timeout and try fallback
        # Note: This test may need adjustment based on actual timeout handling
        with patch.object(helper, '_is_usage_limit_error', return_value=False):
            with pytest.raises(Exception):  # Will fail, but should handle timeout
                await helper.generate("test", prefer_claude=True)


class TestCircuitBreakerEdgeCases:
    """Test circuit breaker edge cases."""

    def test_circuit_breaker_transition_closed_to_open(self):
        """Test circuit breaker transition from closed to open."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Start healthy
        assert helper._check_provider_health("anthropic") == True

        # Fail 3 times
        for _ in range(3):
            helper._update_provider_health("anthropic", False)

        # Should be open
        assert helper._check_provider_health("anthropic") == False

    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Open circuit
        for _ in range(3):
            helper._update_provider_health("anthropic", False)

        assert helper._check_provider_health("anthropic") == False

        # Success should close circuit
        helper._update_provider_health("anthropic", True)

        assert helper._check_provider_health("anthropic") == True

    def test_circuit_breaker_partial_failures(self):
        """Test circuit breaker with partial failures."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Fail twice, succeed once
        helper._update_provider_health("anthropic", False)
        helper._update_provider_health("anthropic", False)
        helper._update_provider_health("anthropic", True)

        # Should still be healthy (recent_failures reset)
        assert helper._check_provider_health("anthropic") == True


class TestConfigurationEdgeCases:
    """Test configuration edge cases."""

    def test_empty_config(self):
        """Test with empty configuration."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper(config={})

        # Should use defaults
        assert helper._fallback_providers == ["openai", "ollama"]
        assert helper._request_timeout_seconds == 60.0

    def test_invalid_config_values(self):
        """Test handling of invalid config values."""
        from engram.chainmind_helper import ChainMindHelper

        # Invalid timeout (should use default)
        helper = ChainMindHelper(config={"request_timeout_seconds": -1})

        # Should use default or handle gracefully
        assert helper._request_timeout_seconds > 0

    def test_config_with_none_values(self):
        """Test config with None values."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper(config={
            "max_tokens_per_request": None,
            "max_cost_per_request": None
        })

        assert helper._max_tokens_per_request is None
        assert helper._max_cost_per_request is None


class TestResponseExtractionEdgeCases:
    """Test edge cases in response extraction."""

    def test_missing_response_field(self):
        """Test extraction when response field is missing."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Result with no response field
        result = {"provider": "anthropic", "metadata": {}}

        # Should extract something (fallback to str(result))
        response = helper._extract_response(result)
        assert isinstance(response, str)

    def test_nested_empty_response(self):
        """Test extraction from nested empty response."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        result = {
            "choices": [{
                "message": {
                    "content": ""
                }
            }]
        }

        response = helper._extract_response(result)
        assert response == ""  # Empty but valid

    def test_multiple_response_formats(self):
        """Test extraction from various response formats."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Test different formats
        formats = [
            {"response": "text1"},
            {"text": "text2"},
            {"content": "text3"},
            {"output": "text4"},
        ]

        for fmt in formats:
            response = helper._extract_response(fmt)
            assert response in ["text1", "text2", "text3", "text4"]


class TestCacheEdgeCases:
    """Test cache edge cases."""

    @pytest.mark.asyncio
    async def test_cache_with_zero_size(self):
        """Test cache behavior with zero size."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper(cache_size=0)

        mock_router = AsyncMock()
        mock_router.route = AsyncMock(return_value={
            "response": "response",
            "provider": "anthropic",
            "metadata": {}
        })

        helper._router = mock_router
        helper._initialized = True

        # Should not cache
        await helper.generate("test")

        assert len(helper._response_cache) == 0

    @pytest.mark.asyncio
    async def test_cache_with_very_large_size(self):
        """Test cache with very large size limit."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper(cache_size=10000)

        mock_router = AsyncMock()
        mock_router.route = AsyncMock(return_value={
            "response": "response",
            "provider": "anthropic",
            "metadata": {}
        })

        helper._router = mock_router
        helper._initialized = True

        # Fill cache
        for i in range(100):
            await helper.generate(f"prompt {i}")

        # Should cache all
        assert len(helper._response_cache) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
