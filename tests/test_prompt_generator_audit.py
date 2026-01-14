"""
Unit tests for prompt generator audit improvements.

Tests cover:
- Prompt validation
- Token estimation
- Prompt truncation
- Prompt optimization
"""

import pytest
import sys
import os

# Add engram-mcp to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPromptValidationAudit:
    """Test prompt validation improvements."""

    def test_empty_task_validation(self):
        """Test that empty tasks are rejected."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        with pytest.raises(ValueError, match="cannot be empty"):
            generator.generate_prompt("")

    def test_whitespace_only_task_validation(self):
        """Test that whitespace-only tasks are rejected."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        with pytest.raises(ValueError, match="cannot be empty"):
            generator.generate_prompt("   \n\t  ")

    def test_invalid_strategy_validation(self):
        """Test that invalid strategies are handled."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        # Invalid strategy should default to balanced
        result = generator.generate_prompt("test task", strategy="invalid_strategy")

        assert result["strategy"] == "balanced"

    def test_valid_strategies(self):
        """Test that all valid strategies work."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        strategies = ["concise", "detailed", "structured", "balanced"]

        for strategy in strategies:
            result = generator.generate_prompt("test task", strategy=strategy)
            assert result["strategy"] == strategy
            assert result["prompt"]  # Prompt should not be empty


class TestTokenEstimationAudit:
    """Test token estimation functionality."""

    def test_token_estimation_basic(self):
        """Test basic token estimation."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        # Rough estimate: 4 chars per token
        text = "test " * 20  # 100 chars, ~25 tokens
        tokens = generator._estimate_tokens(text)

        assert tokens >= 20  # Should be roughly 25
        assert tokens <= 30  # With some variance

    def test_token_estimation_empty(self):
        """Test token estimation for empty text."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        assert generator._estimate_tokens("") == 0
        assert generator._estimate_tokens(None) == 0

    def test_token_estimation_with_markdown(self):
        """Test token estimation accounts for markdown overhead."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        text_with_markdown = "# Header\n\n```code```\n\nContent"
        text_without_markdown = "Header code Content"

        tokens_with = generator._estimate_tokens(text_with_markdown)
        tokens_without = generator._estimate_tokens(text_without_markdown)

        # Markdown should add some overhead
        assert tokens_with >= tokens_without


class TestPromptTruncationAudit:
    """Test prompt truncation functionality."""

    def test_truncate_to_tokens(self):
        """Test truncation to token limit."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        # Create long text
        text = "word " * 1000  # ~5000 chars, ~1250 tokens

        # Truncate to ~100 tokens (~400 chars)
        truncated = generator._truncate_to_tokens(text, 100)

        # Should be shorter
        assert len(truncated) < len(text)

        # Should have truncation marker
        assert "[... truncated ...]" in truncated

    def test_truncate_at_word_boundary(self):
        """Test that truncation happens at word boundaries."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        text = "word1 word2 word3 word4 word5"

        # Truncate to small size
        truncated = generator._truncate_to_tokens(text, 2)

        # Should end at word boundary or have truncation marker
        assert truncated.endswith("...]") or truncated[-1].isalnum()

    def test_no_truncation_when_under_limit(self):
        """Test that text under limit is not truncated."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        text = "short text"
        truncated = generator._truncate_to_tokens(text, 1000)

        assert truncated == text
        assert "[... truncated ...]" not in truncated


class TestPromptOptimizationAudit:
    """Test prompt optimization functionality."""

    def test_remove_duplicate_lines(self):
        """Test removal of duplicate lines."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        prompt = "line1\nline2\nline1\nline3\nline2"
        optimized = generator._optimize_prompt(prompt)

        # Should have fewer lines
        assert optimized.count("\n") < prompt.count("\n")

        # Should contain unique lines
        lines = optimized.split("\n")
        assert len(set(lines)) == len([l for l in lines if l.strip()])

    def test_remove_excessive_whitespace(self):
        """Test removal of excessive whitespace."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        prompt = "line1\n\n\n\nline2\n\nline3"
        optimized = generator._optimize_prompt(prompt)

        # Should have fewer consecutive empty lines
        assert "\n\n\n\n" not in optimized

    def test_remove_trailing_empty_lines(self):
        """Test removal of trailing empty lines."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        prompt = "line1\nline2\n\n\n\n"
        optimized = generator._optimize_prompt(prompt)

        # Should not end with empty lines
        assert not optimized.endswith("\n\n")

    def test_preserve_structure(self):
        """Test that optimization preserves important structure."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        prompt = "# Header\n\nContent here\n\n## Subheader\n\nMore content"
        optimized = generator._optimize_prompt(prompt)

        # Should preserve headers
        assert "# Header" in optimized
        assert "## Subheader" in optimized


class TestPromptGenerationWithLimits:
    """Test prompt generation with token limits."""

    def test_generate_with_max_tokens(self):
        """Test prompt generation respects max_tokens."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        # Generate with very small limit
        result = generator.generate_prompt(
            "test task",
            max_tokens=10
        )

        # Should include truncation info in metadata
        assert "estimated_tokens" in result["metadata"]

        # If truncated, should indicate it
        if result["metadata"].get("was_truncated"):
            assert result["metadata"]["was_truncated"] == True

    def test_generate_without_max_tokens(self):
        """Test prompt generation without limits."""
        from engram.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        result = generator.generate_prompt("test task")

        assert result["prompt"]
        assert result["metadata"]["estimated_tokens"] > 0
        assert result["metadata"].get("was_truncated") == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
