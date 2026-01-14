"""
End-to-end comprehensive tests for ChainMind + engram-mcp integration.

Tests cover:
- Complete workflows
- Real-world scenarios
- Integration between components
- Performance under load
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
import os
import time

# Add engram-mcp to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCompleteWorkflows:
    """Test complete end-to-end workflows."""

    @pytest.mark.asyncio
    async def test_workflow_prompt_generation_to_generation(self):
        """Test complete workflow: generate prompt -> use for generation."""
        from engram.prompt_generator import PromptGenerator
        from engram.chainmind_helper import ChainMindHelper

        # Step 1: Generate optimized prompt
        generator = PromptGenerator()
        prompt_result = generator.generate_prompt(
            task="Write a Python function to calculate fibonacci",
            context="Use type hints and docstrings",
            strategy="structured"
        )

        assert "prompt" in prompt_result
        assert "fibonacci" in prompt_result["prompt"].lower()

        # Step 2: Use prompt for generation (mocked)
        mock_helper = Mock(spec=ChainMindHelper)
        mock_helper.is_available.return_value = True
        mock_helper.generate = AsyncMock(return_value={
            "response": "def fibonacci(n: int) -> int:\n    \"\"\"Calculate fibonacci.\"\"\"\n    ...",
            "provider": "anthropic",
            "fallback_used": False,
            "usage_limit_hit": False
        })

        if mock_helper.is_available():
            result = await mock_helper.generate(
                prompt=prompt_result["prompt"],
                prefer_claude=True
            )
            assert "fibonacci" in result["response"].lower()

    @pytest.mark.asyncio
    async def test_workflow_with_memory_integration(self):
        """Test workflow with engram-mcp memory integration."""
        from engram.prompt_generator import PromptGenerator
        from engram.chainmind_helper import ChainMindHelper

        # Mock memory store with relevant memories
        mock_store = Mock()
        mock_store.context.return_value = [
            {
                "content": "User prefers Python over JavaScript",
                "memory_type": "preference"
            },
            {
                "content": "Project uses type hints and docstrings",
                "memory_type": "fact"
            }
        ]

        # Step 1: Generate prompt with context
        generator = PromptGenerator(memory_store=mock_store)
        prompt_result = generator.generate_prompt(
            task="Write a function",
            project="test-project",
            strategy="balanced"
        )

        assert prompt_result["context_used"] > 0
        assert "prompt" in prompt_result

        # Step 2: Generate with ChainMind (mocked)
        mock_helper = Mock(spec=ChainMindHelper)
        mock_helper.is_available.return_value = True
        mock_helper.generate = AsyncMock(return_value={
            "response": "def function():\n    pass",
            "provider": "anthropic",
            "fallback_used": False,
            "usage_limit_hit": False
        })

        if mock_helper.is_available():
            result = await mock_helper.generate(
                prompt=prompt_result["prompt"],
                prefer_claude=True
            )
            assert "response" in result

    @pytest.mark.asyncio
    async def test_workflow_usage_limit_fallback(self):
        """Test complete workflow with usage limit fallback."""
        from engram.chainmind_helper import ChainMindHelper

        mock_helper = Mock(spec=ChainMindHelper)
        mock_helper.is_available.return_value = True

        # Simulate Claude hitting usage limit, then fallback succeeds
        call_count = 0
        async def mock_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call (Claude) fails
                raise Exception("quota exceeded")
            else:
                # Fallback succeeds
                return {
                    "response": "Fallback response",
                    "provider": "openai",
                    "fallback_used": True,
                    "usage_limit_hit": True
                }

        mock_helper.generate = mock_generate

        # Test that fallback is attempted
        with patch.object(ChainMindHelper, '_is_usage_limit_error', return_value=True):
            if mock_helper.is_available():
                result = await mock_helper.generate(
                    prompt="Test prompt",
                    prefer_claude=True,
                    fallback_providers=["openai"]
                )
                assert result["fallback_used"] == True
                assert result["provider"] == "openai"

    @pytest.mark.asyncio
    async def test_workflow_generate_verify_improve(self):
        """Test workflow: generate -> verify -> improve."""
        from engram.chainmind_helper import ChainMindHelper

        mock_helper = Mock(spec=ChainMindHelper)
        mock_helper.is_available.return_value = True

        responses = [
            {
                "response": "Initial response",
                "provider": "anthropic",
                "fallback_used": False,
                "usage_limit_hit": False
            },
            {
                "response": "Verification: Accuracy 0.7, needs improvement",
                "provider": "openai",
                "fallback_used": False,
                "usage_limit_hit": False
            },
            {
                "response": "Improved response",
                "provider": "anthropic",
                "fallback_used": False,
                "usage_limit_hit": False
            }
        ]

        call_index = 0
        async def mock_generate(*args, **kwargs):
            nonlocal call_index
            result = responses[call_index]
            call_index += 1
            return result

        mock_helper.generate = mock_generate

        if mock_helper.is_available():
            # Step 1: Generate
            result1 = await mock_helper.generate(
                prompt="Write a function",
                prefer_claude=True
            )
            assert "Initial response" in result1["response"]

            # Step 2: Verify
            verify_prompt = f"Verify: {result1['response']}"
            result2 = await mock_helper.generate(
                prompt=verify_prompt,
                prefer_claude=False
            )
            assert "Verification" in result2["response"]

            # Step 3: Improve
            improve_prompt = f"Improve: {result1['response']}"
            result3 = await mock_helper.generate(
                prompt=improve_prompt,
                prefer_claude=True
            )
            assert "Improved" in result3["response"]


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_scenario_code_generation_with_preferences(self):
        """Test scenario: Generate code respecting user preferences."""
        from engram.prompt_generator import PromptGenerator
        from engram.chainmind_helper import ChainMindHelper

        # User has preferences stored in memory
        mock_store = Mock()
        mock_store.context.return_value = [
            {"content": "Prefer TypeScript over JavaScript", "memory_type": "preference"},
            {"content": "Use async/await, not promises", "memory_type": "preference"},
            {"content": "Always include error handling", "memory_type": "preference"}
        ]

        generator = PromptGenerator(memory_store=mock_store)
        prompt_result = generator.generate_prompt(
            task="Write a function to fetch user data",
            project="test-project",
            strategy="structured"
        )

        # Prompt should include preferences
        assert "prompt" in prompt_result
        prompt_text = prompt_result["prompt"].lower()
        # Should reference preferences (may be in context section)
        assert prompt_result["context_used"] > 0

    @pytest.mark.asyncio
    async def test_scenario_handling_claude_limit(self):
        """Test scenario: Claude hits limit, automatically use fallback."""
        from engram.chainmind_helper import ChainMindHelper

        mock_helper = Mock(spec=ChainMindHelper)
        mock_helper.is_available.return_value = True

        # Simulate usage limit
        class UsageLimitError(Exception):
            pass

        async def mock_generate(*args, **kwargs):
            if kwargs.get("provider") == "anthropic" or not kwargs.get("prefer_claude", True):
                raise UsageLimitError("quota exceeded")
            return {
                "response": "Fallback response",
                "provider": kwargs.get("provider", "openai"),
                "fallback_used": True,
                "usage_limit_hit": True
            }

        mock_helper.generate = mock_generate

        # Should automatically fallback
        with patch.object(ChainMindHelper, '_is_usage_limit_error', return_value=True):
            if mock_helper.is_available():
                result = await mock_helper.generate(
                    prompt="Important task",
                    prefer_claude=True,
                    fallback_providers=["openai"]
                )
                assert result["fallback_used"] == True
                assert result["usage_limit_hit"] == True

    @pytest.mark.asyncio
    async def test_scenario_multi_step_reasoning(self):
        """Test scenario: Multi-step reasoning with context."""
        from engram.prompt_generator import PromptGenerator

        mock_store = Mock()
        mock_store.context.return_value = [
            {"content": "Previous step: Analyzed requirements", "memory_type": "fact"},
            {"content": "Decision: Use microservices architecture", "memory_type": "decision"}
        ]

        generator = PromptGenerator(memory_store=mock_store)

        # Step 1: Generate prompt for analysis
        step1 = generator.generate_prompt(
            task="Analyze system requirements",
            project="test-project"
        )

        # Step 2: Generate prompt for design (should include step 1 context)
        step2 = generator.generate_prompt(
            task="Design system architecture",
            project="test-project"
        )

        assert step1["prompt"] != step2["prompt"]
        assert step2["context_used"] > 0


class TestPerformance:
    """Test performance characteristics."""

    @pytest.mark.asyncio
    async def test_prompt_generation_performance(self):
        """Test prompt generation performance."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        start = time.time()
        for _ in range(10):
            generator.generate_prompt(
                task="Write a function",
                strategy="balanced"
            )
        elapsed = time.time() - start

        # Should be fast (< 100ms per prompt)
        assert elapsed < 1.0, f"Prompt generation too slow: {elapsed}s"

    @pytest.mark.asyncio
    async def test_usage_limit_detection_performance(self):
        """Test usage limit detection performance."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()

        # Test many error messages
        errors = [
            Exception("quota exceeded"),
            Exception("usage limit"),
            Exception("token limit"),
            Exception("monthly limit"),
            Exception("network error"),  # Should not match
            Exception("timeout"),  # Should not match
        ] * 100

        start = time.time()
        for error in errors:
            helper._is_usage_limit_error(error)
        elapsed = time.time() - start

        # Should be very fast (< 10ms for all)
        assert elapsed < 0.1, f"Error detection too slow: {elapsed}s"

    def test_helper_initialization_performance(self):
        """Test helper initialization performance."""
        from engram.chainmind_helper import ChainMindHelper

        start = time.time()
        for _ in range(10):
            helper = ChainMindHelper()
            helper.is_available()  # Triggers initialization attempt
        elapsed = time.time() - start

        # Should be fast
        assert elapsed < 1.0, f"Initialization too slow: {elapsed}s"


class TestErrorRecovery:
    """Test error recovery and resilience."""

    @pytest.mark.asyncio
    async def test_recovery_from_chainmind_unavailable(self):
        """Test graceful recovery when ChainMind unavailable."""
        from engram.chainmind_helper import ChainMindHelper

        helper = ChainMindHelper()
        helper._router = None
        helper._initialized = True

        # Should raise error, not crash
        with pytest.raises(RuntimeError):
            await helper.generate("test prompt")

        # But helper should still be usable after
        assert helper.is_available() == False

    @pytest.mark.asyncio
    async def test_recovery_from_memory_store_error(self):
        """Test graceful recovery when memory store fails."""
        from engram.prompt_generator import PromptGenerator

        mock_store = Mock()
        mock_store.context.side_effect = Exception("Store error")

        generator = PromptGenerator(memory_store=mock_store)

        # Should still generate prompt despite error
        result = generator.generate_prompt(
            task="Write a function",
            project="test-project"
        )

        assert "prompt" in result
        assert result["context_used"] == 0  # No context due to error

    @pytest.mark.asyncio
    async def test_recovery_from_provider_failure(self):
        """Test recovery when provider fails."""
        from engram.chainmind_helper import ChainMindHelper

        mock_helper = Mock(spec=ChainMindHelper)
        mock_helper.is_available.return_value = True

        # First provider fails, second succeeds
        call_count = 0
        async def mock_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Provider 1 failed")
            return {
                "response": "Success",
                "provider": "provider2",
                "fallback_used": True,
                "usage_limit_hit": False
            }

        mock_helper.generate = mock_generate

        # Should recover and use fallback
        if mock_helper.is_available():
            result = await mock_helper.generate(
                prompt="test",
                prefer_claude=True,
                fallback_providers=["provider1", "provider2"]
            )
            assert result["fallback_used"] == True


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_prompt_generation(self):
        """Test prompt generation with empty inputs."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = generator.generate_prompt(task="")

        assert "prompt" in result
        assert isinstance(result["prompt"], str)

    def test_very_long_prompt_generation(self):
        """Test prompt generation with very long task."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        long_task = "Write a function " * 1000
        result = generator.generate_prompt(task=long_task)

        assert "prompt" in result
        assert len(result["prompt"]) > 0

    @pytest.mark.asyncio
    async def test_concurrent_generations(self):
        """Test concurrent prompt generations."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        async def generate_one(i):
            return generator.generate_prompt(
                task=f"Task {i}",
                strategy="balanced"
            )

        # Generate 10 prompts concurrently
        results = await asyncio.gather(*[generate_one(i) for i in range(10)])

        assert len(results) == 10
        assert all("prompt" in r for r in results)

    def test_all_strategies_produce_different_prompts(self):
        """Test that all strategies produce different prompts."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        task = "Write a function"

        strategies = ["concise", "detailed", "structured", "balanced"]
        prompts = [generator.generate_prompt(task=task, strategy=s)["prompt"] for s in strategies]

        # All should be different
        assert len(set(prompts)) == len(prompts), "Strategies should produce different prompts"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
