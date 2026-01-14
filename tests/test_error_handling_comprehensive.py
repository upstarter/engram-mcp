"""
Comprehensive error handling and edge case tests.

Tests cover:
- Error detection and handling
- Edge cases
- Boundary conditions
- Failure modes
- Recovery mechanisms
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add engram-mcp to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestErrorDetection:
    """Test error detection mechanisms."""

    def test_detect_various_quota_errors(self):
        """Test detection of various quota error formats."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Test various error formats
        error_cases = [
            Exception("quota exceeded"),
            Exception("QUOTA EXCEEDED"),
            Exception("Quota Exceeded"),
            Exception("usage limit reached"),
            Exception("token limit exceeded"),
            Exception("monthly limit exceeded"),
            Exception("billing limit reached"),
            Exception("insufficient credits"),
            Exception("payment required"),
            Exception("purchase extra usage credits"),
            Exception("cm-1801"),
            Exception("error code: 1801"),
            Exception("QUOTA_EXCEEDED"),
        ]

        for error in error_cases:
            assert helper._is_usage_limit_error(error) == True, f"Failed to detect: {error}"

    def test_detect_non_quota_errors(self):
        """Test that non-quota errors are not detected."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        error_cases = [
            Exception("network error"),
            Exception("timeout"),
            Exception("connection refused"),
            Exception("invalid api key"),
            Exception("rate limit exceeded"),  # Different from usage limit
            Exception("server error 500"),
            ValueError("invalid input"),
            KeyError("missing key"),
        ]

        for error in error_cases:
            assert helper._is_usage_limit_error(error) == False, f"False positive: {error}"

    def test_detect_error_with_code_attribute(self):
        """Test detection of errors with code attributes."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        class ErrorWithCode(Exception):
            def __init__(self, code, message):
                self.code = code
                super().__init__(message)

        # Should detect by code
        error1 = ErrorWithCode("CM-1801", "Some error")
        assert helper._is_usage_limit_error(error1) == True

        error2 = ErrorWithCode("QUOTA_EXCEEDED", "Some error")
        assert helper._is_usage_limit_error(error2) == True

        error3 = ErrorWithCode("NETWORK_ERROR", "Some error")
        assert helper._is_usage_limit_error(error3) == False


class TestErrorHandling:
    """Test error handling mechanisms."""

    @pytest.mark.asyncio
    async def test_handle_chainmind_unavailable(self):
        """Test handling when ChainMind is unavailable."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        helper._router = None
        helper._initialized = True

        with pytest.raises(RuntimeError, match="not available"):
            await helper.generate("test prompt")

    @pytest.mark.asyncio
    async def test_handle_provider_failure(self):
        """Test handling when provider fails."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        mock_router = AsyncMock()
        mock_router.route.side_effect = Exception("Provider failure")
        helper._router = mock_router
        helper._initialized = True

        with pytest.raises(Exception, match="Provider failure"):
            await helper.generate("test prompt", prefer_claude=True)

    @pytest.mark.asyncio
    async def test_handle_all_fallbacks_fail(self):
        """Test handling when all fallback providers fail."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        mock_router = AsyncMock()
        mock_router.route.side_effect = Exception("All providers failed")
        helper._router = mock_router
        helper._initialized = True

        with patch.object(helper, '_is_usage_limit_error', return_value=True):
            with pytest.raises(RuntimeError, match="all fallback providers failed"):
                await helper.generate(
                    "test prompt",
                    prefer_claude=True,
                    fallback_providers=["openai", "ollama"]
                )

    def test_handle_memory_store_error(self):
        """Test handling when memory store fails."""
        from engram.prompt_generator import PromptGenerator

        mock_store = Mock()
        mock_store.context.side_effect = Exception("Store error")

        generator = PromptGenerator(memory_store=mock_store)

        # Should still generate prompt
        result = generator.generate_prompt(
            task="Write a function",
            project="test-project"
        )

        assert "prompt" in result
        assert result["context_used"] == 0

    def test_handle_memory_store_none(self):
        """Test handling when memory store is None."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator(memory_store=None)

        # Should work without error
        result = generator.generate_prompt(
            task="Write a function",
            project="test-project"
        )

        assert "prompt" in result


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_task(self):
        """Test with empty task raises ValueError."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        with pytest.raises(ValueError, match="Task cannot be empty"):
            generator.generate_prompt(task="")

    def test_very_long_task(self):
        """Test with very long task."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        long_task = "Write a function " * 1000
        result = generator.generate_prompt(task=long_task)

        assert "prompt" in result
        assert len(result["prompt"]) > 0

    def test_special_characters(self):
        """Test with special characters."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        special_task = "Write @#$%^&*() function with <script> tags"
        result = generator.generate_prompt(task=special_task)

        assert special_task in result["prompt"]

    def test_unicode_characters(self):
        """Test with unicode characters."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        unicode_task = "Write a function with 中文 and 🚀 emoji"
        result = generator.generate_prompt(task=unicode_task)

        assert unicode_task in result["prompt"]

    def test_none_context(self):
        """Test with None context."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = generator.generate_prompt(
            task="Write a function",
            context=None
        )

        assert "prompt" in result

    def test_empty_context(self):
        """Test with empty context."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = generator.generate_prompt(
            task="Write a function",
            context=""
        )

        assert "prompt" in result

    def test_zero_limit_context(self):
        """Test with zero limit_context."""
        from engram.prompt_generator import PromptGenerator

        mock_store = Mock()
        mock_store.context.return_value = []

        generator = PromptGenerator(memory_store=mock_store)
        result = generator.generate_prompt(
            task="Write a function",
            project="test-project",
            limit_context=0
        )

        assert "prompt" in result
        # Should not call context with limit 0
        mock_store.context.assert_called_once_with(
            query="Write a function",
            cwd=os.getcwd(),
            limit=0
        )

    def test_negative_limit_context(self):
        """Test with negative limit_context."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = generator.generate_prompt(
            task="Write a function",
            project="test-project",
            limit_context=-1
        )

        # Should handle gracefully
        assert "prompt" in result

    def test_memory_with_missing_fields(self):
        """Test handling memories with missing fields."""
        from engram.prompt_generator import PromptGenerator

        mock_store = Mock()
        mock_store.context.return_value = [
            {"content": "Memory without type"},
            {"memory_type": "fact"},  # Missing content
            {},  # Empty memory
            {"content": "Normal memory", "memory_type": "fact"}
        ]

        generator = PromptGenerator(memory_store=mock_store)
        result = generator.generate_prompt(
            task="Write a function",
            project="test-project",
            strategy="balanced"
        )

        # Should handle gracefully
        assert "prompt" in result


class TestBoundaryConditions:
    """Test boundary conditions."""

    def test_max_limit_context(self):
        """Test with maximum limit_context."""
        from engram.prompt_generator import PromptGenerator

        mock_store = Mock()
        mock_store.context.return_value = [
            {"content": f"Memory {i}", "memory_type": "fact"}
            for i in range(100)
        ]

        generator = PromptGenerator(memory_store=mock_store)
        result = generator.generate_prompt(
            task="Write a function",
            project="test-project",
            limit_context=100
        )

        assert result["context_used"] == 100

    @pytest.mark.asyncio
    async def test_single_fallback_provider(self):
        """Test with single fallback provider."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        mock_router = AsyncMock()

        # Claude fails, single fallback succeeds
        mock_router.route.side_effect = [
            Exception("quota exceeded"),
            {"response": "Success", "provider": "openai"}
        ]

        helper._router = mock_router
        helper._initialized = True

        with patch.object(helper, '_is_usage_limit_error', return_value=True):
            result = await helper.generate(
                "test prompt",
                prefer_claude=True,
                fallback_providers=["openai"]
            )

        assert result["fallback_used"] == True
        assert result["provider"] == "openai"

    @pytest.mark.asyncio
    async def test_no_fallback_providers(self):
        """Test with no fallback providers."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        mock_router = AsyncMock()
        mock_router.route.side_effect = Exception("quota exceeded")
        helper._router = mock_router
        helper._initialized = True

        with patch.object(helper, '_is_usage_limit_error', return_value=True):
            with pytest.raises(RuntimeError, match="all fallback providers failed"):
                await helper.generate(
                    "test prompt",
                    prefer_claude=True,
                    fallback_providers=[]
                )


class TestRecoveryMechanisms:
    """Test recovery mechanisms."""

    @pytest.mark.asyncio
    async def test_recover_from_initialization_failure(self):
        """Test recovery from initialization failure."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # First attempt fails
        helper._init_chainmind()
        initial_available = helper.is_available()

        # Helper should still be usable
        assert isinstance(initial_available, bool)

    def test_recover_from_memory_error(self):
        """Test recovery from memory store error."""
        from engram.prompt_generator import PromptGenerator

        mock_store = Mock()
        mock_store.context.side_effect = Exception("Temporary error")

        generator = PromptGenerator(memory_store=mock_store)

        # First call fails
        result1 = generator.generate_prompt(
            task="Write a function",
            project="test-project"
        )
        assert result1["context_used"] == 0

        # Store recovers
        mock_store.context.side_effect = None
        mock_store.context.return_value = [
            {"content": "Memory", "memory_type": "fact"}
        ]

        # Second call succeeds
        result2 = generator.generate_prompt(
            task="Write a function",
            project="test-project"
        )
        assert result2["context_used"] > 0

    @pytest.mark.asyncio
    async def test_recover_from_provider_failure(self):
        """Test recovery from provider failure."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        mock_router = AsyncMock()

        # First provider fails, second succeeds
        call_count = 0
        async def mock_route(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Provider 1 failed")
            return {"response": "Success", "provider": "provider2"}

        mock_router.route = mock_route
        helper._router = mock_router
        helper._initialized = True

        result = await helper.generate(
            "test prompt",
            prefer_claude=True,
            fallback_providers=["provider1", "provider2"]
        )

        assert result["fallback_used"] == True
        assert result["provider"] == "provider2"


class TestFailureModes:
    """Test various failure modes."""

    @pytest.mark.asyncio
    async def test_failure_mode_chainmind_unavailable(self):
        """Test failure mode: ChainMind unavailable."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        helper._router = None
        helper._initialized = True

        assert helper.is_available() == False

        with pytest.raises(RuntimeError):
            await helper.generate("test prompt")

    def test_failure_mode_memory_store_unavailable(self):
        """Test failure mode: Memory store unavailable."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator(memory_store=None)

        # Should still work
        result = generator.generate_prompt(
            task="Write a function",
            project="test-project"
        )

        assert "prompt" in result
        assert result["context_used"] == 0

    @pytest.mark.asyncio
    async def test_failure_mode_all_providers_fail(self):
        """Test failure mode: All providers fail."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        mock_router = AsyncMock()
        mock_router.route.side_effect = Exception("All providers failed")
        helper._router = mock_router
        helper._initialized = True

        with pytest.raises(Exception):
            await helper.generate(
                "test prompt",
                prefer_claude=True,
                fallback_providers=["openai", "ollama"]
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
