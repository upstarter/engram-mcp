"""
Prompt Generator for Claude
============================

Generates optimized prompts specifically for Claude, incorporating context
from engram-mcp memories to improve response quality.
"""

import os
import logging
from typing import Optional, Dict, Any, List

# Setup structured logging
logger = logging.getLogger("engram.prompt_generator")
if not logger.handlers:
    import sys
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class PromptGenerator:
    """
    Generates optimized prompts for Claude with context integration.

    Features:
    - Task-aware prompt generation
    - Context integration from engram-mcp
    - Multiple prompt strategies
    - Claude-specific optimizations
    """

    def __init__(self, memory_store=None):
        """
        Initialize prompt generator.

        Args:
            memory_store: Optional engram-mcp MemoryStore for context
        """
        self.memory_store = memory_store

    def generate_prompt(
        self,
        task: str,
        context: Optional[str] = None,
        strategy: str = "balanced",
        project: Optional[str] = None,
        limit_context: int = 5,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate optimized prompt for Claude.

        Args:
            task: What Claude needs to do
            context: Optional additional context
            strategy: Prompt strategy ("concise", "detailed", "structured", "balanced")
            project: Optional project name for context retrieval
            limit_context: Max number of memories to include
            max_tokens: Optional maximum token limit for prompt (truncates if exceeded)

        Returns:
            Dict with:
            - prompt: Generated prompt
            - strategy: Strategy used
            - context_used: Context memories included
            - metadata: Additional metadata including token estimates
        """
        # Validate inputs
        if not task or not task.strip():
            raise ValueError("Task cannot be empty")

        if strategy not in ["concise", "detailed", "structured", "balanced"]:
            logger.warning(f"Unknown strategy '{strategy}', using 'balanced'")
            strategy = "balanced"

        logger.debug(f"Generating prompt with strategy '{strategy}'", extra={
            "strategy": strategy,
            "has_context": context is not None,
            "project": project,
            "limit_context": limit_context
        })

        # Get relevant context from engram-mcp if available
        context_memories = []
        if self.memory_store and project:
            try:
                context_memories = self.memory_store.context(
                    query=task,
                    cwd=os.getcwd(),
                    limit=limit_context
                )
                logger.debug(f"Retrieved {len(context_memories)} context memories", extra={
                    "context_count": len(context_memories),
                    "project": project
                })
            except Exception as e:
                logger.warning(f"Failed to retrieve context memories: {e}", exc_info=True)

        # Build prompt based on strategy
        if strategy == "concise":
            prompt = self._build_concise_prompt(task, context, context_memories)
        elif strategy == "detailed":
            prompt = self._build_detailed_prompt(task, context, context_memories)
        elif strategy == "structured":
            prompt = self._build_structured_prompt(task, context, context_memories)
        else:  # balanced (default)
            prompt = self._build_balanced_prompt(task, context, context_memories)

        # Validate prompt
        if not prompt or not prompt.strip():
            raise ValueError("Generated prompt is empty")

        # Estimate token count
        estimated_tokens = self._estimate_tokens(prompt)

        # Truncate if exceeds max_tokens
        original_length = len(prompt)
        if max_tokens and estimated_tokens > max_tokens:
            logger.warning(f"Prompt exceeds token limit ({estimated_tokens} > {max_tokens}), truncating")
            prompt = self._truncate_to_tokens(prompt, max_tokens)
            estimated_tokens = self._estimate_tokens(prompt)
            logger.info(f"Truncated prompt from {original_length} to {len(prompt)} chars", extra={
                "original_tokens": estimated_tokens,
                "truncated_tokens": estimated_tokens,
                "max_tokens": max_tokens
            })

        # Optimize prompt (remove redundancy)
        prompt = self._optimize_prompt(prompt)

        logger.info(f"Generated prompt successfully", extra={
            "strategy": strategy,
            "prompt_length": len(prompt),
            "estimated_tokens": estimated_tokens,
            "context_memories_used": len(context_memories)
        })

        return {
            "prompt": prompt,
            "strategy": strategy,
            "context_used": len(context_memories),
            "context_memories": [
                {"type": m.get("memory_type"), "content": m.get("content", "")[:100]}
                for m in context_memories[:3]  # Include first 3 for reference
            ],
            "metadata": {
                "project": project,
                "has_context": len(context_memories) > 0,
                "estimated_tokens": estimated_tokens,
                "prompt_length": len(prompt),
                "was_truncated": max_tokens is not None and estimated_tokens > max_tokens
            }
        }

    def _build_concise_prompt(
        self,
        task: str,
        context: Optional[str],
        memories: List[Dict]
    ) -> str:
        """Build concise prompt (minimal, direct)."""
        parts = [task]

        if context:
            parts.append(f"\nContext: {context}")

        if memories:
            relevant = "\n".join([f"- {m.get('content', '')[:100]}" for m in memories[:2]])
            parts.append(f"\nRelevant information:\n{relevant}")

        return "\n".join(parts)

    def _build_detailed_prompt(
        self,
        task: str,
        context: Optional[str],
        memories: List[Dict]
    ) -> str:
        """Build detailed prompt (comprehensive, thorough)."""
        parts = ["Task:", task]

        if context:
            parts.append(f"\nAdditional Context:\n{context}")

        if memories:
            parts.append("\nRelevant Memories:")
            for i, mem in enumerate(memories, 1):
                mem_type = mem.get("memory_type", "fact")
                content = mem.get("content", "")
                parts.append(f"{i}. [{mem_type}] {content}")

        parts.append("\nPlease provide a comprehensive response.")
        return "\n".join(parts)

    def _build_structured_prompt(
        self,
        task: str,
        context: Optional[str],
        memories: List[Dict]
    ) -> str:
        """Build structured prompt (organized, clear sections)."""
        parts = [
            "# Task",
            task,
            ""
        ]

        if context:
            parts.extend([
                "# Context",
                context,
                ""
            ])

        if memories:
            parts.append("# Relevant Information")
            for mem in memories:
                mem_type = mem.get("memory_type", "fact")
                content = mem.get("content", "")
                parts.append(f"## {mem_type.title()}")
                parts.append(content)
                parts.append("")

        parts.append("# Instructions")
        parts.append("Please provide a clear, structured response.")

        return "\n".join(parts)

    def _build_balanced_prompt(
        self,
        task: str,
        context: Optional[str],
        memories: List[Dict]
    ) -> str:
        """Build balanced prompt (good detail without being verbose)."""
        parts = [task]

        if context:
            parts.append(f"\nContext: {context}")

        if memories:
            # Include top 3 most relevant memories
            relevant = []
            for mem in memories[:3]:
                mem_type = mem.get("memory_type", "fact")
                content = mem.get("content", "")[:150]
                relevant.append(f"[{mem_type}] {content}")

            if relevant:
                parts.append("\nRelevant information:")
                parts.append("\n".join(f"- {r}" for r in relevant))

        return "\n".join(parts)

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses a simple heuristic: ~4 characters per token for English text.
        This is a rough estimate; actual tokenization varies by model.
        """
        if not text:
            return 0

        # Rough estimate: 4 chars per token for English
        # Add some overhead for special tokens and formatting
        char_count = len(text)
        estimated = char_count // 4

        # Add overhead for markdown, special formatting
        if "#" in text or "```" in text:
            estimated = int(estimated * 1.1)

        return max(estimated, 1)  # At least 1 token

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """
        Truncate text to approximately max_tokens.

        Tries to truncate at word boundaries to avoid cutting words.
        """
        if not text:
            return text

        # Estimate max characters (4 chars per token)
        max_chars = max_tokens * 4

        if len(text) <= max_chars:
            return text

        # Truncate at word boundary
        truncated = text[:max_chars]
        last_space = truncated.rfind(" ")
        last_newline = truncated.rfind("\n")

        # Prefer newline boundary, then space boundary
        if last_newline > max_chars * 0.8:  # If newline is reasonably close
            truncated = truncated[:last_newline]
        elif last_space > max_chars * 0.8:  # If space is reasonably close
            truncated = truncated[:last_space]

        return truncated + "\n[... truncated ...]"

    def _optimize_prompt(self, prompt: str) -> str:
        """
        Optimize prompt by removing redundancy and improving structure.

        - Removes duplicate lines
        - Removes excessive whitespace
        - Normalizes line endings
        """
        if not prompt:
            return prompt

        lines = prompt.split("\n")
        seen_lines = set()
        optimized_lines = []

        for line in lines:
            stripped = line.strip()
            # Skip empty lines if previous line was also empty
            if not stripped:
                if optimized_lines and optimized_lines[-1].strip():
                    optimized_lines.append("")
                continue

            # Skip duplicate lines (case-insensitive)
            line_lower = stripped.lower()
            if line_lower not in seen_lines:
                seen_lines.add(line_lower)
                optimized_lines.append(line)

        # Remove trailing empty lines
        while optimized_lines and not optimized_lines[-1].strip():
            optimized_lines.pop()

        return "\n".join(optimized_lines)
