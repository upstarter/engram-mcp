"""
Comprehensive unit tests for Prompt Generator.

Tests cover:
- Initialization
- All prompt strategies
- Context integration
- Memory store integration
- Edge cases
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add engram-mcp to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPromptGeneratorInitialization:
    """Test prompt generator initialization."""

    def test_generator_initialization_default(self):
        """Test generator initialization without memory store."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        assert generator is not None
        assert generator.memory_store is None

    def test_generator_initialization_with_store(self):
        """Test generator initialization with memory store."""
        from engram.prompt_generator import PromptGenerator

        mock_store = Mock()
        generator = PromptGenerator(memory_store=mock_store)
        assert generator.memory_store == mock_store


class TestPromptStrategies:
    """Test all prompt generation strategies."""

    def test_concise_strategy(self):
        """Test concise prompt strategy."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = generator.generate_prompt(
            task="Write a function",
            strategy="concise"
        )

        assert "prompt" in result
        assert result["strategy"] == "concise"
        assert "Write a function" in result["prompt"]
        assert len(result["prompt"]) < 500  # Should be concise

    def test_detailed_strategy(self):
        """Test detailed prompt strategy."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = generator.generate_prompt(
            task="Write a function",
            strategy="detailed"
        )

        assert "prompt" in result
        assert result["strategy"] == "detailed"
        assert "Task:" in result["prompt"]
        assert "comprehensive response" in result["prompt"].lower()

    def test_structured_strategy(self):
        """Test structured prompt strategy."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = generator.generate_prompt(
            task="Write a function",
            strategy="structured"
        )

        assert "prompt" in result
        assert result["strategy"] == "structured"
        assert "# Task" in result["prompt"]
        assert "# Instructions" in result["prompt"]

    def test_balanced_strategy(self):
        """Test balanced prompt strategy (default)."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = generator.generate_prompt(
            task="Write a function",
            strategy="balanced"
        )

        assert "prompt" in result
        assert result["strategy"] == "balanced"
        assert "Write a function" in result["prompt"]

    def test_default_strategy(self):
        """Test default strategy (should be balanced)."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = generator.generate_prompt(task="Write a function")

        assert result["strategy"] == "balanced"

    def test_invalid_strategy_fallback(self):
        """Test fallback to balanced for invalid strategy."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = generator.generate_prompt(
            task="Write a function",
            strategy="invalid_strategy"
        )

        # Should fallback to balanced
        assert result["strategy"] == "balanced"


class TestContextIntegration:
    """Test context integration in prompts."""

    def test_prompt_with_context(self):
        """Test prompt generation with additional context."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = generator.generate_prompt(
            task="Write a function",
            context="Use TypeScript",
            strategy="balanced"
        )

        assert "Context: Use TypeScript" in result["prompt"]

    def test_concise_with_context(self):
        """Test concise strategy with context."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = generator.generate_prompt(
            task="Write a function",
            context="Use TypeScript",
            strategy="concise"
        )

        assert "Context: Use TypeScript" in result["prompt"]

    def test_detailed_with_context(self):
        """Test detailed strategy with context."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = generator.generate_prompt(
            task="Write a function",
            context="Use TypeScript",
            strategy="detailed"
        )

        assert "Additional Context:" in result["prompt"]
        assert "Use TypeScript" in result["prompt"]

    def test_structured_with_context(self):
        """Test structured strategy with context."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = generator.generate_prompt(
            task="Write a function",
            context="Use TypeScript",
            strategy="structured"
        )

        assert "# Context" in result["prompt"]
        assert "Use TypeScript" in result["prompt"]


class TestMemoryStoreIntegration:
    """Test integration with engram-mcp memory store."""

    def test_prompt_with_memory_store(self):
        """Test prompt generation with memory store."""
        from engram.prompt_generator import PromptGenerator

        mock_store = Mock()
        mock_store.context.return_value = [
            {"content": "User prefers TypeScript", "memory_type": "preference"},
            {"content": "Project uses React", "memory_type": "fact"}
        ]

        generator = PromptGenerator(memory_store=mock_store)
        result = generator.generate_prompt(
            task="Write a function",
            project="test-project",
            strategy="balanced"
        )

        assert result["context_used"] == 2
        assert len(result["context_memories"]) > 0
        mock_store.context.assert_called_once()

    def test_prompt_with_memory_store_no_project(self):
        """Test prompt generation without project (should not call store)."""
        from engram.prompt_generator import PromptGenerator

        mock_store = Mock()
        generator = PromptGenerator(memory_store=mock_store)
        result = generator.generate_prompt(
            task="Write a function",
            strategy="balanced"
        )

        # Should not call context without project
        mock_store.context.assert_not_called()
        assert result["context_used"] == 0

    def test_prompt_with_memory_store_error(self):
        """Test graceful handling when memory store fails."""
        from engram.prompt_generator import PromptGenerator

        mock_store = Mock()
        mock_store.context.side_effect = Exception("Store error")

        generator = PromptGenerator(memory_store=mock_store)
        result = generator.generate_prompt(
            task="Write a function",
            project="test-project",
            strategy="balanced"
        )

        # Should still generate prompt despite error
        assert "prompt" in result
        assert result["context_used"] == 0

    def test_prompt_with_limit_context(self):
        """Test limiting context memories."""
        from engram.prompt_generator import PromptGenerator

        mock_store = Mock()
        mock_store.context.return_value = [
            {"content": f"Memory {i}", "memory_type": "fact"}
            for i in range(10)
        ]

        generator = PromptGenerator(memory_store=mock_store)
        result = generator.generate_prompt(
            task="Write a function",
            project="test-project",
            limit_context=3,
            strategy="balanced"
        )

        # Should limit to 3 memories
        call_args = mock_store.context.call_args
        assert call_args[1]["limit"] == 3
        assert result["context_used"] == 10  # Store returns 10, but we use top 3

    def test_concise_with_memories(self):
        """Test concise strategy with memories."""
        from engram.prompt_generator import PromptGenerator

        mock_store = Mock()
        mock_store.context.return_value = [
            {"content": "Memory 1", "memory_type": "fact"},
            {"content": "Memory 2", "memory_type": "preference"}
        ]

        generator = PromptGenerator(memory_store=mock_store)
        result = generator.generate_prompt(
            task="Write a function",
            project="test-project",
            strategy="concise"
        )

        assert "Relevant information:" in result["prompt"]
        assert "Memory 1" in result["prompt"] or "Memory 2" in result["prompt"]

    def test_detailed_with_memories(self):
        """Test detailed strategy with memories."""
        from engram.prompt_generator import PromptGenerator

        mock_store = Mock()
        mock_store.context.return_value = [
            {"content": "Memory 1", "memory_type": "fact"},
            {"content": "Memory 2", "memory_type": "preference"}
        ]

        generator = PromptGenerator(memory_store=mock_store)
        result = generator.generate_prompt(
            task="Write a function",
            project="test-project",
            strategy="detailed"
        )

        assert "Relevant Memories:" in result["prompt"]
        assert "[fact]" in result["prompt"] or "[preference]" in result["prompt"]

    def test_structured_with_memories(self):
        """Test structured strategy with memories."""
        from engram.prompt_generator import PromptGenerator

        mock_store = Mock()
        mock_store.context.return_value = [
            {"content": "Memory 1", "memory_type": "fact"},
            {"content": "Memory 2", "memory_type": "preference"}
        ]

        generator = PromptGenerator(memory_store=mock_store)
        result = generator.generate_prompt(
            task="Write a function",
            project="test-project",
            strategy="structured"
        )

        assert "# Relevant Information" in result["prompt"]
        assert "## Fact" in result["prompt"] or "## Preference" in result["prompt"]

    def test_balanced_with_memories(self):
        """Test balanced strategy with memories."""
        from engram.prompt_generator import PromptGenerator

        mock_store = Mock()
        mock_store.context.return_value = [
            {"content": "Memory 1", "memory_type": "fact"},
            {"content": "Memory 2", "memory_type": "preference"},
            {"content": "Memory 3", "memory_type": "decision"}
        ]

        generator = PromptGenerator(memory_store=mock_store)
        result = generator.generate_prompt(
            task="Write a function",
            project="test-project",
            strategy="balanced"
        )

        assert "Relevant information:" in result["prompt"]
        # Should include top 3 memories
        assert result["context_used"] == 3


class TestPromptMetadata:
    """Test prompt generation metadata."""

    def test_metadata_without_project(self):
        """Test metadata without project."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = generator.generate_prompt(task="Write a function")

        assert "metadata" in result
        assert result["metadata"]["project"] is None
        assert result["metadata"]["has_context"] == False

    def test_metadata_with_project(self):
        """Test metadata with project."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        result = generator.generate_prompt(
            task="Write a function",
            project="test-project"
        )

        assert result["metadata"]["project"] == "test-project"

    def test_metadata_with_context(self):
        """Test metadata with context memories."""
        from engram.prompt_generator import PromptGenerator

        mock_store = Mock()
        mock_store.context.return_value = [
            {"content": "Memory 1", "memory_type": "fact"}
        ]

        generator = PromptGenerator(memory_store=mock_store)
        result = generator.generate_prompt(
            task="Write a function",
            project="test-project"
        )

        assert result["metadata"]["has_context"] == True
        assert result["context_used"] == 1

    def test_context_memories_preview(self):
        """Test context memories preview in result."""
        from engram.prompt_generator import PromptGenerator

        mock_store = Mock()
        mock_store.context.return_value = [
            {"content": "This is a long memory that should be truncated in preview", "memory_type": "fact"},
            {"content": "Short memory", "memory_type": "preference"},
            {"content": "Another memory", "memory_type": "decision"}
        ]

        generator = PromptGenerator(memory_store=mock_store)
        result = generator.generate_prompt(
            task="Write a function",
            project="test-project"
        )

        assert len(result["context_memories"]) == 3  # First 3
        assert all("type" in m for m in result["context_memories"])
        assert all("content" in m for m in result["context_memories"])
        # Content should be truncated
        assert len(result["context_memories"][0]["content"]) <= 100


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_task(self):
        """Test prompt generation with empty task raises ValueError."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        with pytest.raises(ValueError, match="Task cannot be empty"):
            generator.generate_prompt(task="")

    def test_very_long_task(self):
        """Test prompt generation with very long task."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        long_task = "Write a function " * 100
        result = generator.generate_prompt(task=long_task)

        assert "prompt" in result
        assert long_task[:50] in result["prompt"]

    def test_special_characters_in_task(self):
        """Test prompt generation with special characters."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        special_task = "Write a function with @#$%^&*() characters"
        result = generator.generate_prompt(task=special_task)

        assert special_task in result["prompt"]

    def test_memory_store_none(self):
        """Test prompt generation when memory_store is None."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator(memory_store=None)
        result = generator.generate_prompt(
            task="Write a function",
            project="test-project"
        )

        # Should work without error
        assert "prompt" in result
        assert result["context_used"] == 0

    def test_memory_with_missing_fields(self):
        """Test handling memories with missing fields."""
        from engram.prompt_generator import PromptGenerator

        mock_store = Mock()
        mock_store.context.return_value = [
            {"content": "Memory without type"},
            {"memory_type": "fact"},  # Missing content
            {}  # Empty memory
        ]

        generator = PromptGenerator(memory_store=mock_store)
        result = generator.generate_prompt(
            task="Write a function",
            project="test-project",
            strategy="balanced"
        )

        # Should handle gracefully
        assert "prompt" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
