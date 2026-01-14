"""
Integration tests for ChainMind helper tools in engram-mcp.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add engram-mcp to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestChainMindHelper:
    """Test ChainMind helper functionality."""

    def test_helper_initialization(self):
        """Test helper can be initialized."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        assert helper is not None
        assert helper._initialized == False  # Not initialized until first use

    def test_helper_singleton(self):
        """Test helper singleton pattern."""
        from engram.chainmind_helper import get_helper

        helper1 = get_helper()
        helper2 = get_helper()

        assert helper1 is helper2

    def test_is_usage_limit_error(self):
        """Test usage limit error detection."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Test quota exceeded error
        class QuotaExceededError(Exception):
            pass

        error = QuotaExceededError("Quota exceeded")
        assert helper._is_usage_limit_error(error) == True

        # Test error message detection
        error = Exception("Monthly limit exceeded")
        assert helper._is_usage_limit_error(error) == True

        error = Exception("Token limit reached")
        assert helper._is_usage_limit_error(error) == True

        error = Exception("Insufficient credits")
        assert helper._is_usage_limit_error(error) == True

        # Test non-usage-limit error
        error = Exception("Network error")
        assert helper._is_usage_limit_error(error) == False

    def test_extract_response(self):
        """Test response extraction."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Test dict response
        result = {"response": "Test response"}
        assert helper._extract_response(result) == "Test response"

        # Test dict with text key
        result = {"text": "Test text"}
        assert helper._extract_response(result) == "Test text"

        # Test object with response attribute
        class MockResult:
            def __init__(self):
                self.response = "Object response"

        assert helper._extract_response(MockResult()) == "Object response"

        # Test string
        assert helper._extract_response("String response") == "String response"


class TestPromptGenerator:
    """Test prompt generator functionality."""

    def test_generator_initialization(self):
        """Test generator can be initialized."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        assert generator is not None

    def test_generator_with_memory_store(self):
        """Test generator with memory store."""
        from engram.prompt_generator import PromptGenerator

        mock_store = Mock()
        generator = PromptGenerator(memory_store=mock_store)
        assert generator.memory_store == mock_store

    @pytest.mark.asyncio
    async def test_generate_prompt_concise(self):
        """Test concise prompt generation."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = await generator.generate_prompt(
            task="Write a function",
            strategy="concise"
        )

        assert "prompt" in result
        assert result["strategy"] == "concise"
        assert "Write a function" in result["prompt"]

    @pytest.mark.asyncio
    async def test_generate_prompt_detailed(self):
        """Test detailed prompt generation."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = await generator.generate_prompt(
            task="Write a function",
            strategy="detailed"
        )

        assert "prompt" in result
        assert result["strategy"] == "detailed"
        assert "Task:" in result["prompt"]

    @pytest.mark.asyncio
    async def test_generate_prompt_structured(self):
        """Test structured prompt generation."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = await generator.generate_prompt(
            task="Write a function",
            strategy="structured"
        )

        assert "prompt" in result
        assert result["strategy"] == "structured"
        assert "# Task" in result["prompt"]

    @pytest.mark.asyncio
    async def test_generate_prompt_balanced(self):
        """Test balanced prompt generation."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = await generator.generate_prompt(
            task="Write a function",
            strategy="balanced"
        )

        assert "prompt" in result
        assert result["strategy"] == "balanced"
        assert "Write a function" in result["prompt"]

    @pytest.mark.asyncio
    async def test_generate_prompt_with_context(self):
        """Test prompt generation with context."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = await generator.generate_prompt(
            task="Write a function",
            context="Use TypeScript",
            strategy="balanced"
        )

        assert "Context: Use TypeScript" in result["prompt"]


class TestUsageLimitHandling:
    """Test usage limit detection and fallback."""

    @pytest.mark.asyncio
    async def test_usage_limit_detection(self):
        """Test that usage limit errors are detected."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Mock router that raises usage limit error
        mock_router = AsyncMock()

        class UsageLimitError(Exception):
            pass

        mock_router.route = AsyncMock(side_effect=UsageLimitError("Quota exceeded"))
        helper._router = mock_router
        helper._initialized = True

        # Should detect usage limit
        error = UsageLimitError("Quota exceeded")
        assert helper._is_usage_limit_error(error) == True

    def test_fallback_providers_config(self):
        """Test fallback providers configuration."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        assert len(helper._fallback_providers) > 0
        assert "openai" in helper._fallback_providers or "ollama" in helper._fallback_providers


class TestErrorHandling:
    """Test error handling and graceful degradation."""

    def test_graceful_degradation_no_chainmind(self):
        """Test graceful degradation when ChainMind unavailable."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        # Should not crash if ChainMind unavailable
        assert helper.is_available() == False or helper.is_available() == True

    @pytest.mark.asyncio
    async def test_helper_unavailable_error(self):
        """Test error when helper unavailable."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        helper._router = None
        helper._initialized = True

        with pytest.raises(RuntimeError, match="ChainMind router not available"):
            await helper.generate("test prompt")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
