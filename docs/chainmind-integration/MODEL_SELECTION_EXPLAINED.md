# ChainMind Model Selection in engram-mcp

## How ChainMind Selects the Appropriate Model

### Current State

**In engram-mcp**, ChainMindHelper currently defaults to:
- `prefer_claude=True` → Always tries Claude first
- Falls back to other providers only when Claude hits usage limits

**This means**: Model selection is **reactive** (fallback only), not **proactive** (smart selection).

### How ChainMind's Strategic Router Works

ChainMind uses a **two-tier routing system**:

1. **Strategic Router**: Analyzes the task and selects the best model
2. **Tactical Router**: Executes the request with the selected model

#### Strategic Router Model Selection Process

```
Request → Task Analysis → Model Selection → Execution
    ↓           ↓              ↓              ↓
Prompt    Complexity    ModelRegistry   Provider API
          Task Type     Capabilities
          Capabilities  Cost/Performance
```

**Selection Factors**:
1. **Task Analysis**:
   - Task type (coding, reasoning, creative, extraction)
   - Complexity (low, medium, high)
   - Required capabilities (function_calling, vision, json_mode)

2. **Model Registry Lookup**:
   - Finds models matching required capabilities
   - Considers hardware (GPU, memory)
   - Evaluates performance (reliability, speed, cost)

3. **Strategy Selection**:
   - **Capability Match**: Best model for capabilities
   - **Cost Optimize**: Lowest cost that meets requirements
   - **Performance Optimize**: Highest performance regardless of cost
   - **Balanced**: Balance of performance and cost

#### Example Selection Logic

```python
# Task: "Write a Python function to parse JSON"
# Analysis:
#   - Task type: coding
#   - Complexity: medium
#   - Required capabilities: [function_calling, code_generation]

# Model Registry finds:
#   - Claude Sonnet: ✓ function_calling, ✓ code_generation, high reliability
#   - GPT-4: ✓ function_calling, ✓ code_generation, high reliability
#   - GPT-3.5: ✓ function_calling, ✓ code_generation, lower cost
#   - Ollama Llama3: ✓ code_generation, local, free

# Strategy: balanced
# Selection: GPT-3.5 (meets requirements, lower cost than Claude)
```

## Enabling Automatic Model Selection in engram-mcp

### Option 1: Use ChainMind's Smart Routing (Recommended)

**Modify `chainmind_helper.py`** to use ChainMind's routing when appropriate:

```python
async def generate(
    self,
    prompt: str,
    prefer_claude: Optional[bool] = None,  # None = auto-select
    auto_select_model: bool = False,  # New parameter
    **kwargs
) -> Dict[str, Any]:
    """
    Generate text with automatic model selection.

    Args:
        prompt: The prompt to generate from
        prefer_claude: If True, try Claude first. If False, use ChainMind routing.
                     If None, auto-select based on task.
        auto_select_model: If True, use ChainMind's strategic router for model selection
        **kwargs: Additional parameters
    """
    # Auto-select model if requested
    if auto_select_model or prefer_claude is None:
        # Use ChainMind's strategic router
        return await self._generate_with_smart_routing(prompt, **kwargs)

    # Otherwise, use existing logic (prefer Claude, fallback on error)
    # ... existing code ...
```

### Option 2: Task-Based Auto-Selection

**Enhance prompt analysis** to detect task type and select model:

```python
def _analyze_task(self, prompt: str) -> Dict[str, Any]:
    """Analyze prompt to determine task type and requirements."""
    prompt_lower = prompt.lower()

    # Detect task type
    task_type = "general"
    if any(keyword in prompt_lower for keyword in ["function", "class", "def ", "import"]):
        task_type = "coding"
    elif any(keyword in prompt_lower for keyword in ["explain", "why", "how", "analyze"]):
        task_type = "reasoning"
    elif any(keyword in prompt_lower for keyword in ["write", "create", "generate", "story"]):
        task_type = "creative"
    elif any(keyword in prompt_lower for keyword in ["extract", "parse", "find", "get"]):
        task_type = "extraction"

    # Detect required capabilities
    required_capabilities = []
    if "function" in prompt_lower or "tool" in prompt_lower:
        required_capabilities.append("function_calling")
    if "json" in prompt_lower or "parse" in prompt_lower:
        required_capabilities.append("json_mode")
    if any(keyword in prompt_lower for keyword in ["image", "picture", "photo", "visual"]):
        required_capabilities.append("vision")

    # Estimate complexity
    complexity = "medium"
    if len(prompt) > 1000 or "complex" in prompt_lower:
        complexity = "high"
    elif len(prompt) < 100:
        complexity = "low"

    return {
        "task_type": task_type,
        "required_capabilities": required_capabilities,
        "complexity": complexity
    }

async def _generate_with_smart_routing(
    self,
    prompt: str,
    **kwargs
) -> Dict[str, Any]:
    """Generate using ChainMind's strategic router."""
    # Analyze task
    task_analysis = self._analyze_task(prompt)

    # Build request for strategic router
    request = {
        "prompt": prompt,
        "task_type": task_analysis["task_type"],
        "complexity": task_analysis["complexity"],
        "required_capabilities": task_analysis["required_capabilities"],
        **kwargs
    }

    # Use ChainMind's routing (without prefer_claude)
    result = await self._router.route(
        prompt=prompt,
        prefer_lower_cost=True,  # Use cost optimization
        **request
    )

    # Extract and return response
    # ... existing extraction logic ...
```

### Option 3: Configuration-Based Selection

**Add to `config/chainmind.yaml`**:

```yaml
# Model selection strategy
model_selection:
  # Strategy: auto, prefer_claude, cost_optimize, performance_optimize, balanced
  strategy: auto

  # Auto-select based on task type
  auto_select:
    enabled: true

    # Task-specific model preferences
    task_preferences:
      coding:
        preferred_provider: openai  # GPT-4 is great for code
        preferred_model: gpt-4-turbo
      reasoning:
        preferred_provider: anthropic  # Claude excels at reasoning
        preferred_model: claude-3-opus
      creative:
        preferred_provider: anthropic  # Claude is creative
        preferred_model: claude-3-sonnet
      extraction:
        preferred_provider: openai  # GPT-3.5 is cost-effective
        preferred_model: gpt-3.5-turbo
```

## Integration with CSF/ks (Kitty Session Tabs)

### What is CSF/ks?

**CSF (Claude Session Framework)** + **ks (kitty session)**:
- Creates kitty terminal tabs with Claude sessions
- Each tab has its own context and memory
- Provides optimal context for each session

### How ChainMind Integration Would Work

#### 1. Context-Aware Model Selection

**Each kitty tab** could have:
- **Project context**: What project/files are open
- **Task context**: What you're working on
- **Session history**: Previous interactions

**ChainMind would use this** to select the optimal model:

```python
# When creating a new kitty tab session
def create_kitty_session(project_path: str, context: Dict[str, Any]):
    """
    Create a kitty tab with optimal Claude session.

    Args:
        project_path: Path to project directory
        context: Context about what you're working on
    """
    # Analyze context
    task_type = detect_task_type(context)
    files_open = get_open_files(project_path)
    project_type = detect_project_type(files_open)

    # Select optimal model using ChainMind
    model_selection = chainmind_helper.select_optimal_model(
        task_type=task_type,
        project_type=project_type,
        context_size=estimate_context_size(files_open),
        budget_preference="balanced"
    )

    # Create kitty tab with selected model
    create_kitty_tab(
        title=f"{model_selection['model']} - {project_path}",
        command=f"claude --model {model_selection['model']} --context {project_path}"
    )
```

#### 2. Dynamic Model Switching

**Switch models based on task**:

```python
# In kitty tab session
def handle_user_request(prompt: str, session_context: Dict[str, Any]):
    """Handle user request with optimal model selection."""

    # Analyze current task
    task_analysis = analyze_task(prompt, session_context)

    # Select model for this specific task
    model_selection = chainmind_helper.select_optimal_model(
        task_type=task_analysis["task_type"],
        complexity=task_analysis["complexity"],
        required_capabilities=task_analysis["capabilities"]
    )

    # Generate with selected model
    response = await chainmind_helper.generate(
        prompt=prompt,
        auto_select_model=True,  # Use ChainMind routing
        **model_selection["config"]
    )

    return response
```

#### 3. Context Injection for Optimal Prompts

**Use engram-mcp's PromptGenerator** with ChainMind's model selection:

```python
def create_optimal_prompt_for_kitty_tab(
    user_query: str,
    project_path: str,
    session_context: Dict[str, Any]
) -> Dict[str, Any]:
    """Create optimal prompt with context for kitty tab session."""

    # Get relevant memories from engram
    memories = engram_store.search(
        query=user_query,
        project=project_path,
        limit=5
    )

    # Generate prompt with context
    prompt_result = prompt_generator.generate_prompt(
        task=user_query,
        context=format_memories(memories),
        strategy="balanced",
        project=project_path
    )

    # Select optimal model for this prompt
    model_selection = chainmind_helper.select_optimal_model(
        task_type=analyze_task_type(prompt_result["prompt"]),
        prompt_length=len(prompt_result["prompt"]),
        context_size=prompt_result["metadata"]["estimated_tokens"]
    )

    return {
        "prompt": prompt_result["prompt"],
        "model": model_selection["model"],
        "provider": model_selection["provider"],
        "config": model_selection["config"]
    }
```

### Implementation Example: ks Command Enhancement

**Enhanced `ks` command**:

```bash
#!/bin/bash
# ks - Create kitty tab with optimal Claude session

PROJECT_PATH=${1:-$(pwd)}
CONTEXT_FILE="${PROJECT_PATH}/.claude-context.json"

# Load context if available
if [ -f "$CONTEXT_FILE" ]; then
    CONTEXT=$(cat "$CONTEXT_FILE")
else
    # Auto-detect context
    CONTEXT=$(python3 -c "
import json
import os
import sys

project_path = sys.argv[1]
files = [f for f in os.listdir(project_path) if os.path.isfile(os.path.join(project_path, f))]

# Detect project type
if 'package.json' in files:
    project_type = 'nodejs'
elif 'requirements.txt' in files or 'pyproject.toml' in files:
    project_type = 'python'
elif 'Cargo.toml' in files:
    project_type = 'rust'
else:
    project_type = 'general'

context = {
    'project_path': project_path,
    'project_type': project_type,
    'files': files[:10]  # First 10 files
}

print(json.dumps(context))
" "$PROJECT_PATH")
fi

# Use ChainMind to select optimal model
MODEL_SELECTION=$(python3 -c "
import sys
import json
sys.path.insert(0, '/mnt/dev/ai/engram-mcp')

from engram.chainmind_helper import get_helper

context = json.loads(sys.argv[1])
helper = get_helper()

# Select optimal model based on context
selection = helper.select_optimal_model(
    project_type=context.get('project_type', 'general'),
    auto_select=True
)

print(json.dumps(selection))
" "$CONTEXT")

# Extract model and provider
MODEL=$(echo "$MODEL_SELECTION" | python3 -c "import sys, json; print(json.load(sys.stdin)['model'])")
PROVIDER=$(echo "$MODEL_SELECTION" | python3 -c "import sys, json; print(json.load(sys.stdin)['provider'])")

# Create kitty tab with optimal model
kitty @ new_tab \
    --title "$PROVIDER/$MODEL - $(basename $PROJECT_PATH)" \
    --cwd "$PROJECT_PATH" \
    --env CHAINMIND_PROVIDER="$PROVIDER" \
    --env CHAINMIND_MODEL="$MODEL" \
    --env CLAUDE_PROJECT_PATH="$PROJECT_PATH" \
    claude --model "$MODEL" --context "$PROJECT_PATH"
```

## Benefits of Automatic Model Selection

### 1. Cost Optimization
- **Coding tasks**: Use GPT-3.5 (cheaper, still excellent)
- **Reasoning tasks**: Use Claude (better quality)
- **Simple tasks**: Use Ollama (free, local)

### 2. Performance Optimization
- **Fast tasks**: Use faster models
- **Complex tasks**: Use more capable models
- **Local tasks**: Use Ollama (no network latency)

### 3. Context Optimization
- **Large context**: Use models with larger context windows
- **Small context**: Use faster, cheaper models
- **Specialized**: Use models optimized for specific tasks

### 4. Seamless Experience
- **Automatic**: No manual model selection needed
- **Transparent**: Logs show which model was selected and why
- **Adaptive**: Learns from usage patterns

## Configuration Example

**`config/chainmind.yaml`** with auto-selection:

```yaml
# Model selection
model_selection:
  strategy: auto  # auto, prefer_claude, cost_optimize, performance_optimize

  # Auto-select based on task
  auto_select:
    enabled: true

    # Task preferences
    task_preferences:
      coding:
        strategy: cost_optimize
        preferred_providers: [openai, anthropic]
      reasoning:
        strategy: performance_optimize
        preferred_providers: [anthropic, openai]
      creative:
        strategy: balanced
        preferred_providers: [anthropic]
      extraction:
        strategy: cost_optimize
        preferred_providers: [openai, ollama]

    # Context-based selection
    context_based:
      enabled: true
      large_context_threshold: 8000  # tokens
      use_local_for_small: true  # Use Ollama for small contexts
```

## Summary

**Current State**:
- engram-mcp defaults to Claude, falls back on errors
- Model selection is reactive, not proactive

**With Automatic Selection**:
- ChainMind analyzes tasks and selects optimal models
- Cost, performance, and capabilities are considered
- Seamless integration with CSF/ks for kitty tabs

**Benefits**:
- Lower costs (use cheaper models when appropriate)
- Better performance (use faster models for simple tasks)
- Optimal context (select models with right capabilities)
- Seamless experience (automatic, transparent)
