# CSF/ks Integration with ChainMind for Optimal Context

## Overview

This document explains how ChainMind's automatic model selection integrates with **CSF (Claude Session Framework)** and **ks (kitty session)** to provide optimal context for each kitty tab session.

## Current Configuration

### How ChainMind Works in engram-mcp

**Current behavior** (lines 466-506 in `chainmind_helper.py`):

```python
if prefer_claude:
    # Try Claude first, fallback on error
    ...
else:
    # Use ChainMind's routing with cost optimization
    result = await self._router.route(
        prompt=prompt,
        prefer_lower_cost=True,  # Cost-based selection
        **kwargs
    )
```

**What this means**:
- `prefer_claude=True` (default): Always tries Claude first, falls back on errors
- `prefer_claude=False`: Uses ChainMind's routing, but only considers cost, not task type

**Limitation**: Doesn't analyze task type or capabilities to select optimal model.

## How ChainMind's Strategic Router Selects Models

### Model Selection Process

ChainMind's **StrategicRouter** analyzes requests and selects optimal models:

1. **Task Analysis**:
   ```python
   # Analyzes prompt to determine:
   - Task type: coding, reasoning, creative, extraction
   - Complexity: low, medium, high
   - Required capabilities: function_calling, vision, json_mode
   ```

2. **Model Registry Lookup**:
   ```python
   # Finds models matching:
   - Required capabilities
   - Hardware constraints (GPU, memory)
   - Performance requirements (reliability, speed)
   - Cost constraints
   ```

3. **Strategy Application**:
   ```python
   # Applies strategy:
   - capability_match: Best model for capabilities
   - cost_optimize: Lowest cost meeting requirements
   - performance_optimize: Highest performance
   - balanced: Balance of performance and cost
   ```

### Example Selection

**Request**: "Write a Python function to parse JSON"

**Analysis**:
- Task type: `coding`
- Complexity: `medium`
- Required capabilities: `[function_calling, code_generation]`

**Model Registry finds**:
- Claude Sonnet: ✓ capabilities, high reliability, $0.003/1k tokens
- GPT-4 Turbo: ✓ capabilities, high reliability, $0.01/1k tokens
- GPT-3.5 Turbo: ✓ capabilities, good reliability, $0.0005/1k tokens
- Ollama Llama3: ✓ code_generation, local, free

**Strategy: balanced**
**Selection**: GPT-3.5 Turbo (meets requirements, lower cost than Claude)

## Integration with CSF/ks

### What is CSF/ks?

**CSF (Claude Session Framework)** + **ks (kitty session)**:
- Creates kitty terminal tabs with Claude sessions
- Each tab has its own context and memory
- Provides optimal context for each session

### How It Would Work

#### 1. Context-Aware Model Selection

**When creating a kitty tab**, analyze context and select optimal model:

```python
# engram/ks_helper.py
import os
import json
from pathlib import Path
from engram.chainmind_helper import get_helper

def create_kitty_session(project_path: str, context: Dict[str, Any] = None):
    """
    Create a kitty tab with optimal Claude session.

    Args:
        project_path: Path to project directory
        context: Optional context about what you're working on
    """
    helper = get_helper()

    # Auto-detect context if not provided
    if not context:
        context = detect_project_context(project_path)

    # Analyze task type from context
    task_type = detect_task_type(context)
    project_type = detect_project_type(project_path)

    # Select optimal model using ChainMind
    model_selection = await helper.select_optimal_model(
        task_type=task_type,
        project_type=project_type,
        context_size=estimate_context_size(project_path),
        strategy="balanced"
    )

    # Create kitty tab with selected model
    create_kitty_tab(
        title=f"{model_selection['model']} - {os.path.basename(project_path)}",
        command=f"claude --model {model_selection['model']} --context {project_path}",
        env={
            "CHAINMIND_PROVIDER": model_selection["provider"],
            "CHAINMIND_MODEL": model_selection["model"],
            "CLAUDE_PROJECT_PATH": project_path
        }
    )
```

#### 2. Dynamic Model Switching

**During session**, switch models based on current task:

```python
async def handle_user_request(
    prompt: str,
    session_context: Dict[str, Any],
    helper: ChainMindHelper
):
    """Handle user request with optimal model selection."""

    # Analyze current task
    task_analysis = analyze_task(prompt, session_context)

    # Select model for this specific task
    model_selection = await helper.select_optimal_model(
        task_type=task_analysis["task_type"],
        complexity=task_analysis["complexity"],
        required_capabilities=task_analysis["capabilities"],
        strategy="auto"  # Auto-select based on task
    )

    # Generate with selected model
    response = await helper.generate(
        prompt=prompt,
        prefer_claude=False,  # Use ChainMind routing
        auto_select_model=True,  # Enable automatic selection
        **model_selection["config"]
    )

    return response
```

#### 3. Context Injection with engram-mcp

**Use engram-mcp's PromptGenerator** with ChainMind's model selection:

```python
from engram.prompt_generator import PromptGenerator
from engram.chainmind_helper import get_helper

def create_optimal_prompt_for_kitty_tab(
    user_query: str,
    project_path: str,
    session_context: Dict[str, Any]
) -> Dict[str, Any]:
    """Create optimal prompt with context for kitty tab session."""

    # Get relevant memories from engram
    from engram.memory_store import get_store
    store = get_store()
    memories = store.search(
        query=user_query,
        project=project_path,
        limit=5
    )

    # Generate prompt with context
    prompt_gen = PromptGenerator(store)
    prompt_result = prompt_gen.generate_prompt(
        task=user_query,
        context=format_memories(memories),
        strategy="balanced",
        project=project_path
    )

    # Select optimal model for this prompt
    helper = get_helper()
    model_selection = await helper.select_optimal_model(
        task_type=analyze_task_type(prompt_result["prompt"]),
        prompt_length=len(prompt_result["prompt"]),
        context_size=prompt_result["metadata"]["estimated_tokens"],
        strategy="balanced"
    )

    return {
        "prompt": prompt_result["prompt"],
        "model": model_selection["model"],
        "provider": model_selection["provider"],
        "config": model_selection["config"],
        "context_memories": prompt_result["context_memories"]
    }
```

## Implementation: Enhanced ks Command

### Basic ks Command

```bash
#!/bin/bash
# ks - Create kitty tab with optimal Claude session

PROJECT_PATH=${1:-$(pwd)}

# Use ChainMind to select optimal model
python3 << EOF
import sys
import json
import os
sys.path.insert(0, '/mnt/dev/ai/engram-mcp')

from engram.ks_helper import create_kitty_session

project_path = sys.argv[1]
create_kitty_session(project_path)
EOF "$PROJECT_PATH"
```

### Enhanced ks Helper

**Create `engram/ks_helper.py`**:

```python
"""Helper for creating kitty sessions with optimal model selection."""
import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional
import asyncio

from engram.chainmind_helper import get_helper


def detect_project_context(project_path: str) -> Dict[str, Any]:
    """Detect project context from directory."""
    project_path = Path(project_path)
    files = list(project_path.iterdir())
    file_names = [f.name for f in files if f.is_file()]

    # Detect project type
    project_type = "general"
    if "package.json" in file_names:
        project_type = "nodejs"
    elif any(f in file_names for f in ["requirements.txt", "pyproject.toml", "setup.py"]):
        project_type = "python"
    elif "Cargo.toml" in file_names:
        project_type = "rust"
    elif "go.mod" in file_names:
        project_type = "go"

    # Estimate context size
    code_files = [f for f in files if f.suffix in [".py", ".js", ".ts", ".rs", ".go"]]
    context_size = sum(f.stat().st_size for f in code_files[:10])  # First 10 files

    return {
        "project_type": project_type,
        "project_path": str(project_path),
        "file_count": len(code_files),
        "estimated_context_size": context_size
    }


def detect_task_type(context: Dict[str, Any]) -> str:
    """Detect task type from context."""
    # Could be enhanced with ML or heuristics
    project_type = context.get("project_type", "general")

    # Map project types to task types
    if project_type in ["python", "nodejs", "rust", "go"]:
        return "coding"
    else:
        return "general"


def estimate_context_size(project_path: str) -> int:
    """Estimate context size in tokens."""
    project_path = Path(project_path)
    code_files = [f for f in project_path.rglob("*.py")][:10]

    total_chars = sum(f.stat().st_size for f in code_files)
    # Rough estimate: 4 chars per token
    return total_chars // 4


async def select_optimal_model_for_context(
    project_path: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Select optimal model for project context."""
    helper = get_helper()

    if not context:
        context = detect_project_context(project_path)

    task_type = detect_task_type(context)
    context_size = estimate_context_size(project_path)

    # Use ChainMind's strategic router to select model
    # This would require enhancing ChainMindHelper with model selection method
    # For now, use routing with task analysis

    # Build request for strategic routing
    request = {
        "prompt": f"Working on {context['project_type']} project",
        "task_type": task_type,
        "complexity": "medium" if context_size > 10000 else "low",
        "required_capabilities": ["function_calling"] if task_type == "coding" else []
    }

    # Get model selection (would need to be implemented)
    # For now, return default
    return {
        "provider": "anthropic",
        "model": "claude-3-sonnet-20240229",
        "strategy": "balanced"
    }


def create_kitty_tab(
    title: str,
    command: str,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None
):
    """Create a kitty tab with specified command."""
    kitty_cmd = ["kitty", "@", "new_tab"]

    if title:
        kitty_cmd.extend(["--title", title])

    if cwd:
        kitty_cmd.extend(["--cwd", cwd])

    # Add environment variables
    if env:
        for key, value in env.items():
            kitty_cmd.extend(["--env", f"{key}={value}"])

    kitty_cmd.append("--")
    kitty_cmd.extend(command.split())

    subprocess.run(kitty_cmd)


def create_kitty_session(project_path: str, context: Optional[Dict[str, Any]] = None):
    """Create kitty tab with optimal Claude session."""
    project_path = os.path.abspath(project_path)

    if not context:
        context = detect_project_context(project_path)

    # Select optimal model
    model_selection = asyncio.run(
        select_optimal_model_for_context(project_path, context)
    )

    # Create kitty tab
    title = f"{model_selection['model']} - {os.path.basename(project_path)}"
    command = f"claude --model {model_selection['model']} --context {project_path}"

    create_kitty_tab(
        title=title,
        command=command,
        cwd=project_path,
        env={
            "CHAINMIND_PROVIDER": model_selection["provider"],
            "CHAINMIND_MODEL": model_selection["model"],
            "CLAUDE_PROJECT_PATH": project_path
        }
    )
```

## Benefits

### 1. Optimal Model Selection
- **Coding tasks**: Use GPT-3.5 or GPT-4 (excellent for code)
- **Reasoning tasks**: Use Claude (better at reasoning)
- **Simple tasks**: Use Ollama (free, local, fast)

### 2. Cost Optimization
- **Small projects**: Use cheaper models
- **Large projects**: Use models with larger context windows
- **Local tasks**: Use Ollama when appropriate

### 3. Context-Aware
- **Project type**: Select models optimized for project type
- **File size**: Select models with appropriate context windows
- **Task type**: Select models optimized for specific tasks

### 4. Seamless Experience
- **Automatic**: No manual model selection
- **Transparent**: Logs show which model was selected
- **Adaptive**: Learns from usage patterns

## Configuration

**Add to `config/chainmind.yaml`**:

```yaml
# Model selection for CSF/ks integration
ks_integration:
  enabled: true

  # Auto-select model based on project type
  auto_select:
    enabled: true

    # Project type preferences
    project_preferences:
      python:
        preferred_provider: openai
        preferred_model: gpt-4-turbo
        strategy: cost_optimize
      nodejs:
        preferred_provider: openai
        preferred_model: gpt-4-turbo
        strategy: cost_optimize
      rust:
        preferred_provider: anthropic
        preferred_model: claude-3-sonnet
        strategy: performance_optimize
      general:
        preferred_provider: anthropic
        preferred_model: claude-3-sonnet
        strategy: balanced

  # Context-based selection
  context_based:
    enabled: true
    large_context_threshold: 8000  # tokens
    use_local_for_small: true  # Use Ollama for small contexts
```

## Summary

**Current State**:
- ChainMind defaults to Claude, falls back on errors
- Model selection is reactive, not proactive

**With CSF/ks Integration**:
- Analyzes project context and selects optimal model
- Creates kitty tabs with appropriate model
- Provides optimal context for each session

**Benefits**:
- Lower costs (use cheaper models when appropriate)
- Better performance (use faster models for simple tasks)
- Optimal context (select models with right capabilities)
- Seamless experience (automatic, transparent)
