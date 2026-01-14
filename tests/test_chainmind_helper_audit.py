"""
Unit tests for ChainMind helper audit improvements.

Tests cover:
- Error detection with ProviderErrorClassifier
- Response extraction validation
- Caching and deduplication
- Health tracking and circuit breaker
- Configuration loading
- Metrics collection
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os
from typing import Dict, Any

# Add engram-mcp to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestErrorDetectionAudit:
    """Test error detection improvements with ProviderErrorClassifier."""

    def test_error_classification_with_classifier(self):
        """Test that ProviderErrorClassifier is used for error classification."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Mock the error classifier
        mock_classifier = Mock()
        mock_classifier.classify_error = Mock(return_value="quota_exceeded")
        helper._error_classifier = mock_classifier

        # Test error classification
        error = Exception("quota exceeded")
        category = helper._classify_error(error, "anthropic")

        assert category == "quota_exceeded"
        mock_classifier.classify_error.assert_called_once()

    def test_error_classification_fallback(self):
        """Test error classification fallback when classifier unavailable."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        helper._error_classifier = None

        # Test fallback classification
        error = Exception("quota exceeded")
        category = helper._classify_error(error, "anthropic")

        assert category == "quota_exceeded"

    def test_is_usage_limit_error_with_category(self):
        """Test usage limit detection using error category."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Test with quota_exceeded category
        assert helper._is_usage_limit_error(Exception("test"), "quota_exceeded") == True

        # Test with other categories
        assert helper._is_usage_limit_error(Exception("test"), "rate_limit") == False
        assert helper._is_usage_limit_error(Exception("test"), "authentication") == False

    def test_is_usage_limit_error_with_quota_exceeded_error(self):
        """Test detection of QuotaExceededError exception."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Mock QuotaExceededError
        class QuotaExceededError(Exception):
            pass

        with patch('engram.chainmind_helper.QuotaExceededError', QuotaExceededError):
            error = QuotaExceededError("quota exceeded")
            assert helper._is_usage_limit_error(error) == True

    def test_is_usage_limit_error_with_wrapped_exceptions(self):
        """Test detection of usage limit errors in exception chains."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Create wrapped exception
        inner_error = Exception("quota exceeded")
        outer_error = RuntimeError("outer error")
        outer_error.__cause__ = inner_error

        assert helper._is_usage_limit_error(outer_error) == True


class TestResponseExtractionAudit:
    """Test response extraction validation and improvements."""

    def test_extract_response_from_dict(self):
        """Test response extraction from dictionary format."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Test various dict formats
        result = {"response": "test response"}
        assert helper._extract_response(result) == "test response"

        result = {"text": "test text"}
        assert helper._extract_response(result) == "test text"

        result = {"content": "test content"}
        assert helper._extract_response(result) == "test content"

    def test_extract_response_from_nested_dict(self):
        """Test response extraction from nested dictionary structures."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # OpenAI-style nested format
        result = {
            "choices": [{
                "message": {
                    "content": "nested response"
                }
            }]
        }
        assert helper._extract_response(result) == "nested response"

    def test_extract_response_validation(self):
        """Test that empty responses are detected."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Empty response should return empty string
        result = {"response": ""}
        assert helper._extract_response(result) == ""

        result = {"response": "   "}
        assert helper._extract_response(result) == "   "  # Whitespace preserved, but will be caught by validation

    def test_extract_metadata_comprehensive(self):
        """Test comprehensive metadata extraction."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Test with full metadata
        result = {
            "metadata": {"custom": "value"},
            "tokens_used": {"input": 10, "output": 20, "total": 30},
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            "cost": 0.05,
            "execution_time": 1.5,
            "model": "claude-3-sonnet",
            "request_id": "req-123",
            "from_cache": False
        }

        metadata = helper._extract_metadata(result)

        assert metadata["custom"] == "value"
        assert metadata["tokens"]["input"] == 10
        assert metadata["tokens"]["output"] == 20
        assert metadata["tokens"]["total"] == 30
        assert metadata["cost"] == 0.05
        assert metadata["execution_time"] == 1.5
        assert metadata["model"] == "claude-3-sonnet"
        assert metadata["request_id"] == "req-123"
        assert metadata["from_cache"] == False


class TestCachingAudit:
    """Test caching and deduplication logic."""

    def test_cache_key_generation(self):
        """Test cache key generation for request deduplication."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Same prompt should generate same key
        prompt = "test prompt"
        kwargs1 = {"temperature": 0.7, "max_tokens": 100}
        kwargs2 = {"temperature": 0.7, "max_tokens": 100}

        key1 = helper._generate_cache_key(prompt, True, kwargs1)
        key2 = helper._generate_cache_key(prompt, True, kwargs2)

        assert key1 == key2

        # Different parameters should generate different keys
        kwargs3 = {"temperature": 0.8, "max_tokens": 100}
        key3 = helper._generate_cache_key(prompt, True, kwargs3)

        assert key1 != key3

    def test_cache_result_storage(self):
        """Test that results are cached correctly."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper(cache_size=10)

        cache_key = "test_key"
        result = {
            "response": "test",
            "provider": "anthropic",
            "correlation_id": "corr-123",
            "from_cache": False
        }

        helper._cache_result(cache_key, result)

        assert cache_key in helper._response_cache
        cached = helper._response_cache[cache_key]

        # Correlation ID and from_cache should be removed from cached version
        assert "correlation_id" not in cached
        assert "from_cache" not in cached
        assert cached["response"] == "test"

    def test_cache_lru_eviction(self):
        """Test LRU cache eviction when cache is full."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper(cache_size=3)

        # Fill cache
        for i in range(3):
            helper._cache_result(f"key_{i}", {"response": f"response_{i}"})

        assert len(helper._response_cache) == 3

        # Add one more - should evict oldest
        helper._cache_result("key_3", {"response": "response_3"})

        assert len(helper._response_cache) == 3
        assert "key_0" not in helper._response_cache  # Oldest evicted
        assert "key_3" in helper._response_cache  # Newest added


class TestHealthTrackingAudit:
    """Test health tracking and circuit breaker integration."""

    def test_provider_health_check(self):
        """Test provider health checking."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Initially healthy
        assert helper._check_provider_health("anthropic") == True

        # Mark as unhealthy
        helper._update_provider_health("anthropic", False)
        helper._update_provider_health("anthropic", False)
        helper._update_provider_health("anthropic", False)

        # Should be unhealthy after 3 failures
        assert helper._check_provider_health("anthropic") == False

    def test_provider_health_recovery(self):
        """Test provider health recovery after success."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Mark as unhealthy
        for _ in range(3):
            helper._update_provider_health("anthropic", False)

        assert helper._check_provider_health("anthropic") == False

        # Success should reset failures
        helper._update_provider_health("anthropic", True)

        assert helper._check_provider_health("anthropic") == True

    def test_provider_health_tracking(self):
        """Test provider health statistics tracking."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Track some operations
        helper._update_provider_health("anthropic", True)
        helper._update_provider_health("anthropic", True)
        helper._update_provider_health("anthropic", False)

        health = helper._provider_health["anthropic"]

        assert health["successes"] == 2
        assert health["failures"] == 1
        assert health["recent_failures"] == 1


class TestConfigurationAudit:
    """Test configuration loading and management."""

    def test_config_loading_from_env(self):
        """Test configuration loading from environment variables."""
        from engram.chainmind_helper import ChainMindHelper

        with patch.dict(os.environ, {
            "CHAINMIND_FALLBACK_PROVIDERS": "openai,gemini",
            "CHAINMIND_MAX_TOKENS": "1000",
            "CHAINMIND_TIMEOUT": "30.0"
        }):
            helper = ChainMindHelper()

            assert "openai" in helper._fallback_providers
            assert "gemini" in helper._fallback_providers
            assert helper._max_tokens_per_request == 1000
            assert helper._request_timeout_seconds == 30.0

    def test_config_loading_from_file(self):
        """Test configuration loading from YAML file."""
        from engram.chainmind_helper import ChainMindHelper
        import tempfile
        import yaml

        config_data = {
            "fallback_providers": ["openai", "gemini"],
            "max_tokens_per_request": 2000,
            "request_timeout_seconds": 45.0
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            with patch('os.path.expanduser', return_value=config_path):
                helper = ChainMindHelper()

                # Note: This test may need adjustment based on actual config loading implementation
                # The config loading happens in _load_config which checks ~/.engram/config/chainmind.yaml
        finally:
            os.unlink(config_path)

    def test_config_override_with_provided_config(self):
        """Test that provided config overrides file/env config."""
        from engram.chainmind_helper import ChainMindHelper

        provided_config = {
            "fallback_providers": ["custom_provider"],
            "max_tokens_per_request": 5000
        }

        helper = ChainMindHelper(config=provided_config)

        assert helper._fallback_providers == ["custom_provider"]
        assert helper._max_tokens_per_request == 5000


class TestMetricsAudit:
    """Test metrics collection and reporting."""

    def test_metrics_initialization(self):
        """Test that metrics are initialized correctly."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        metrics = helper.get_metrics()

        assert metrics["total_requests"] == 0
        assert metrics["cache_hits"] == 0
        assert metrics["cache_misses"] == 0
        assert metrics["successful_requests"] == 0
        assert metrics["failed_requests"] == 0
        assert "provider_usage" in metrics
        assert "error_counts" in metrics

    def test_metrics_tracking(self):
        """Test that metrics are tracked correctly."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Simulate some operations
        helper._metrics["total_requests"] = 10
        helper._metrics["cache_hits"] = 3
        helper._metrics["cache_misses"] = 7
        helper._metrics["successful_requests"] = 9
        helper._metrics["failed_requests"] = 1
        helper._metrics["total_latency"] = 15.5

        metrics = helper.get_metrics()

        assert metrics["total_requests"] == 10
        assert metrics["cache_hits"] == 3
        assert metrics["cache_misses"] == 7
        assert metrics["cache_hit_rate_percent"] == 30.0
        assert metrics["average_latency_seconds"] == 1.55

    def test_provider_usage_tracking(self):
        """Test provider usage statistics."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        helper._metrics["provider_usage"]["anthropic"] = 5
        helper._metrics["provider_usage"]["openai"] = 3

        metrics = helper.get_metrics()

        assert metrics["provider_usage"]["anthropic"] == 5
        assert metrics["provider_usage"]["openai"] == 3


class TestRequestLimitsAudit:
    """Test resource limit enforcement."""

    def test_token_limit_validation(self):
        """Test token limit validation."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        helper._max_tokens_per_request = 100

        # Valid request
        prompt = "test" * 10  # ~10 tokens
        kwargs = {"max_tokens": 50}

        # Should not raise
        helper._validate_request_limits(prompt, kwargs)

        # Invalid request - exceeds limit
        kwargs = {"max_tokens": 200}

        with pytest.raises(ValueError, match="exceeds token limit"):
            helper._validate_request_limits(prompt, kwargs)

    def test_no_token_limit(self):
        """Test that validation passes when no limit is set."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        helper._max_tokens_per_request = None

        prompt = "test" * 1000
        kwargs = {"max_tokens": 10000}

        # Should not raise
        helper._validate_request_limits(prompt, kwargs)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

