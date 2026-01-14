"""
Comprehensive unit tests for ChainMind helper.

Tests cover:
- Initialization and availability
- Usage limit detection
- Fallback logic
- Provider routing
- Error handling
- Response extraction
- Metadata handling
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os

# Add engram-mcp to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestChainMindHelperInitialization:
    """Test ChainMind helper initialization and configuration."""

    def test_helper_initialization(self):
        """Test helper can be initialized."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        assert helper is not None
        assert helper._initialized == False
        assert helper._router is None
        assert helper._usage_limit_detected == False
        assert len(helper._fallback_providers) > 0

    def test_helper_singleton_pattern(self):
        """Test helper singleton pattern."""
        from engram.chainmind_helper import get_helper

        helper1 = get_helper()
        helper2 = get_helper()

        assert helper1 is helper2
        assert id(helper1) == id(helper2)

    def test_fallback_providers_default(self):
        """Test default fallback providers."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        assert isinstance(helper._fallback_providers, list)
        assert len(helper._fallback_providers) > 0
        # Should include common fallbacks
        assert any("openai" in p.lower() or "ollama" in p.lower() for p in helper._fallback_providers)

    def test_is_available_before_init(self):
        """Test availability check before initialization."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        # Should attempt initialization
        available = helper.is_available()
        assert isinstance(available, bool)

    @patch('engram.chainmind_helper.get_container')
    def test_init_chainmind_with_di_container(self, mock_get_container):
        """Test initialization with DI container."""
        from engram.chainmind_helper import ChainMindHelper

        # Mock DI container
        mock_container = Mock()
        mock_router = Mock()
        mock_container.resolve.return_value = mock_router
        mock_get_container.return_value = mock_container

        helper = ChainMindHelper()
        helper._init_chainmind()

        assert helper._initialized == True
        assert helper._router == mock_router

    @patch('engram.chainmind_helper.get_container')
    @patch('engram.chainmind_helper.StrategicRouter')
    @patch('engram.chainmind_helper.TacticalRouter')
    @patch('engram.chainmind_helper.TwoTierRouter')
    def test_init_chainmind_fallback(self, mock_two_tier, mock_tactical, mock_strategic, mock_get_container):
        """Test initialization fallback when DI container fails."""
        from engram.chainmind_helper import ChainMindHelper

        # Mock DI container failure
        mock_get_container.return_value = None

        # Mock router components
        mock_strategic_router = Mock()
        mock_tactical_router = Mock()
        mock_strategic.return_value = mock_strategic_router
        mock_tactical.return_value = mock_tactical_router
        mock_two_tier_router = Mock()
        mock_two_tier.return_value = mock_two_tier_router

        helper = ChainMindHelper()
        helper._init_chainmind()

        assert helper._initialized == True
        mock_two_tier.assert_called_once()

    @patch('engram.chainmind_helper.get_container')
    def test_init_chainmind_graceful_failure(self, mock_get_container):
        """Test graceful failure when ChainMind unavailable."""
        from engram.chainmind_helper import ChainMindHelper

        # Mock import failure
        mock_get_container.side_effect = ImportError("Module not found")

        helper = ChainMindHelper()
        helper._init_chainmind()

        assert helper._initialized == True  # Marked as attempted
        assert helper._router is None  # But router not available


class TestUsageLimitDetection:
    """Test usage limit error detection."""

    def test_quota_exceeded_error_detection(self):
        """Test detection of QuotaExceededError."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Test ChainMind QuotaExceededError
        try:
            from backend.core.errors.additional_errors import QuotaExceededError
            error = QuotaExceededError("Quota exceeded")
            assert helper._is_usage_limit_error(error) == True
        except ImportError:
            # If ChainMind not available, test with mock
            class QuotaExceededError(Exception):
                pass
            error = QuotaExceededError("Quota exceeded")
            # Should detect by type name
            assert helper._is_usage_limit_error(error) == True

    def test_error_message_detection(self):
        """Test detection by error message."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Test various error messages
        test_cases = [
            "quota exceeded",
            "usage limit reached",
            "token limit exceeded",
            "monthly limit exceeded",
            "billing limit reached",
            "insufficient credits",
            "payment required",
            "purchase extra usage credits",
            "cm-1801",  # ChainMind error code
            "error code: 1801",
        ]

        for msg in test_cases:
            error = Exception(msg)
            assert helper._is_usage_limit_error(error) == True, f"Failed to detect: {msg}"

    def test_error_code_detection(self):
        """Test detection by error code."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Test error with code attribute
        class ErrorWithCode(Exception):
            def __init__(self, code):
                self.code = code
                super().__init__(f"Error {code}")

        error = ErrorWithCode("CM-1801")
        assert helper._is_usage_limit_error(error) == True

        error = ErrorWithCode("QUOTA_EXCEEDED")
        assert helper._is_usage_limit_error(error) == True

    def test_non_usage_limit_errors(self):
        """Test that non-usage-limit errors are not detected."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Test various non-usage-limit errors
        test_cases = [
            Exception("Network error"),
            Exception("Timeout"),
            Exception("Invalid API key"),
            Exception("Rate limit exceeded"),  # Different from usage limit
            Exception("Server error 500"),
            ValueError("Invalid input"),
        ]

        for error in test_cases:
            assert helper._is_usage_limit_error(error) == False, f"False positive: {error}"

    def test_case_insensitive_detection(self):
        """Test that detection is case-insensitive."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        test_cases = [
            "QUOTA EXCEEDED",
            "Quota Exceeded",
            "quota exceeded",
            "Token Limit Reached",
            "MONTHLY LIMIT",
        ]

        for msg in test_cases:
            error = Exception(msg)
            assert helper._is_usage_limit_error(error) == True


class TestProviderRouting:
    """Test provider routing and mapping."""

    @pytest.mark.asyncio
    async def test_provider_mapping(self):
        """Test provider name mapping."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        mock_router = AsyncMock()
        helper._router = mock_router
        helper._initialized = True

        # Test provider mappings
        provider_tests = [
            ("anthropic", "anthropic"),
            ("claude", "anthropic"),
            ("openai", "openai"),
            ("gpt", "openai"),
            ("ollama", "ollama"),
            ("local", "ollama"),
        ]

        for input_provider, expected_provider in provider_tests:
            mock_router.route.return_value = {"response": "test", "provider": expected_provider}
            await helper._try_provider("test prompt", input_provider)
            call_args = mock_router.route.call_args
            assert call_args[1]["provider"] == expected_provider

    @pytest.mark.asyncio
    async def test_try_provider_success(self):
        """Test successful provider call."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        mock_router = AsyncMock()
        mock_router.route.return_value = {"response": "Test response", "provider": "anthropic"}
        helper._router = mock_router
        helper._initialized = True

        result = await helper._try_provider("test prompt", "anthropic")
        assert result == {"response": "Test response", "provider": "anthropic"}
        mock_router.route.assert_called_once()

    @pytest.mark.asyncio
    async def test_try_provider_error(self):
        """Test provider call error handling."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        mock_router = AsyncMock()
        mock_router.route.side_effect = Exception("Provider error")
        helper._router = mock_router
        helper._initialized = True

        with pytest.raises(Exception, match="Provider error"):
            await helper._try_provider("test prompt", "anthropic")


class TestFallbackLogic:
    """Test fallback logic when Claude hits usage limits."""

    @pytest.mark.asyncio
    async def test_claude_success_no_fallback(self):
        """Test successful Claude call without fallback."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        mock_router = AsyncMock()
        mock_router.route.return_value = {"response": "Claude response", "provider": "anthropic"}
        helper._router = mock_router
        helper._initialized = True

        result = await helper.generate("test prompt", prefer_claude=True)

        assert result["response"] == "Claude response"
        assert result["provider"] == "anthropic"
        assert result["fallback_used"] == False
        assert result["usage_limit_hit"] == False

    @pytest.mark.asyncio
    async def test_claude_usage_limit_fallback(self):
        """Test fallback when Claude hits usage limit."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        mock_router = AsyncMock()

        # First call (Claude) fails with usage limit
        class UsageLimitError(Exception):
            pass

        usage_limit_error = UsageLimitError("quota exceeded")
        mock_router.route.side_effect = [
            usage_limit_error,  # Claude fails
            {"response": "OpenAI response", "provider": "openai"}  # Fallback succeeds
        ]

        helper._router = mock_router
        helper._initialized = True

        # Mock error detection
        with patch.object(helper, '_is_usage_limit_error', return_value=True):
            result = await helper.generate("test prompt", prefer_claude=True, fallback_providers=["openai"])

        assert result["response"] == "OpenAI response"
        assert result["provider"] == "openai"
        assert result["fallback_used"] == True
        assert result["usage_limit_hit"] == True
        assert "fallback_reason" in result

    @pytest.mark.asyncio
    async def test_all_fallbacks_fail(self):
        """Test when all fallback providers fail."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        mock_router = AsyncMock()

        # All providers fail
        mock_router.route.side_effect = Exception("All providers failed")

        helper._router = mock_router
        helper._initialized = True

        with patch.object(helper, '_is_usage_limit_error', return_value=True):
            with pytest.raises(RuntimeError, match="all fallback providers failed"):
                await helper.generate("test prompt", prefer_claude=True, fallback_providers=["openai", "ollama"])

    @pytest.mark.asyncio
    async def test_fallback_chain_order(self):
        """Test fallback providers are tried in order."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        mock_router = AsyncMock()

        call_order = []
        def track_calls(*args, **kwargs):
            call_order.append(kwargs.get("provider", "unknown"))
            if len(call_order) == 1:
                raise Exception("quota exceeded")
            return {"response": "Success", "provider": call_order[-1]}

        mock_router.route.side_effect = track_calls
        helper._router = mock_router
        helper._initialized = True

        with patch.object(helper, '_is_usage_limit_error', return_value=True):
            await helper.generate("test prompt", prefer_claude=True, fallback_providers=["openai", "ollama"])

        assert call_order[0] == "anthropic"  # Claude first
        assert call_order[1] == "openai"  # First fallback
        assert len(call_order) == 2  # Should stop after first success

    @pytest.mark.asyncio
    async def test_non_usage_limit_error_no_fallback(self):
        """Test that non-usage-limit errors don't trigger fallback."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        mock_router = AsyncMock()
        mock_router.route.side_effect = Exception("Network error")

        helper._router = mock_router
        helper._initialized = True

        with patch.object(helper, '_is_usage_limit_error', return_value=False):
            with pytest.raises(Exception, match="Network error"):
                await helper.generate("test prompt", prefer_claude=True)


class TestResponseExtraction:
    """Test response extraction from various result formats."""

    def test_extract_response_from_dict(self):
        """Test extracting response from dict."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Test with "response" key
        result = {"response": "Test response"}
        assert helper._extract_response(result) == "Test response"

        # Test with "text" key
        result = {"text": "Test text"}
        assert helper._extract_response(result) == "Test text"

        # Test with both (response takes precedence)
        result = {"response": "Response", "text": "Text"}
        assert helper._extract_response(result) == "Response"

    def test_extract_response_from_object(self):
        """Test extracting response from object."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Test with response attribute
        class MockResult:
            def __init__(self):
                self.response = "Object response"

        assert helper._extract_response(MockResult()) == "Object response"

        # Test with text attribute
        class MockResultText:
            def __init__(self):
                self.text = "Object text"

        assert helper._extract_response(MockResultText()) == "Object text"

    def test_extract_response_from_string(self):
        """Test extracting response from string."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        assert helper._extract_response("String response") == "String response"

    def test_extract_response_fallback(self):
        """Test fallback to string conversion."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Test with dict that has neither response nor text
        result = {"data": "some data"}
        assert helper._extract_response(result) == str(result)

    def test_extract_provider(self):
        """Test provider extraction."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Test from dict
        result = {"provider": "anthropic"}
        assert helper._extract_provider(result) == "anthropic"

        # Test from object
        class MockResult:
            def __init__(self):
                self.provider = "openai"

        assert helper._extract_provider(MockResult()) == "openai"

        # Test fallback
        result = {}
        assert helper._extract_provider(result) == "unknown"

    def test_extract_metadata(self):
        """Test metadata extraction."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Test from dict
        metadata = {"tokens": 100, "cost": 0.001}
        result = {"metadata": metadata}
        assert helper._extract_metadata(result) == metadata

        # Test from object
        class MockResult:
            def __init__(self):
                self.metadata = {"tokens": 200}

        assert helper._extract_metadata(MockResult()) == {"tokens": 200}

        # Test fallback
        result = {}
        assert helper._extract_metadata(result) == {}


class TestUsageStatus:
    """Test usage status tracking."""

    def test_usage_status_initial(self):
        """Test initial usage status."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        status = helper.get_usage_status()

        assert status["usage_limit_detected"] == False
        assert "fallback_providers" in status

    def test_usage_status_after_limit(self):
        """Test usage status after limit detected."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        helper._usage_limit_detected = True

        status = helper.get_usage_status()
        assert status["usage_limit_detected"] == True


class TestGenerateWithoutClaudePreference:
    """Test generation without preferring Claude."""

    @pytest.mark.asyncio
    async def test_generate_with_chainmind_routing(self):
        """Test generation using ChainMind's routing."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        mock_router = AsyncMock()
        mock_router.route.return_value = {
            "response": "Routed response",
            "provider": "openai"
        }
        helper._router = mock_router
        helper._initialized = True

        result = await helper.generate("test prompt", prefer_claude=False)

        assert result["response"] == "Routed response"
        assert result["provider"] == "openai"
        assert result["fallback_used"] == False
        assert result["usage_limit_hit"] == False

        # Should call with prefer_lower_cost
        call_args = mock_router.route.call_args
        assert call_args[1]["prefer_lower_cost"] == True


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_generate_without_router(self):
        """Test error when router not available."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        helper._router = None
        helper._initialized = True

        with pytest.raises(RuntimeError, match="ChainMind router not available"):
            await helper.generate("test prompt")

    @pytest.mark.asyncio
    async def test_generate_with_kwargs(self):
        """Test generation with additional kwargs."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        mock_router = AsyncMock()
        mock_router.route.return_value = {"response": "Test", "provider": "anthropic"}
        helper._router = mock_router
        helper._initialized = True

        await helper.generate(
            "test prompt",
            temperature=0.7,
            max_tokens=100,
            top_p=0.9
        )

        call_args = mock_router.route.call_args
        assert call_args[1]["temperature"] == 0.7
        assert call_args[1]["max_tokens"] == 100
        assert call_args[1]["top_p"] == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
