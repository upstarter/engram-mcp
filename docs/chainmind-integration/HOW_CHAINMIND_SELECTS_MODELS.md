# How ChainMind Selects Models

## Overview

ChainMind uses a **hybrid approach** combining:
1. **Pattern-based analysis** (regex/keyword matching) - Fast, deterministic
2. **LLM-based analysis** (optional) - More sophisticated, can be enabled

## Current Implementation: Pattern-Based Analysis

### How It Works

ChainMind uses the `InputAnalyzer` class which analyzes prompts using **regex patterns** (not LLM analysis by default).

### Step-by-Step Process

1. **Input Analysis** (`InputAnalyzer.analyze()`)
   - Scans prompt text for patterns
   - Uses regex to detect:
     - Task type (coding, reasoning, planning, etc.)
     - Complexity (high, medium, low)
     - Domain (technical, business, scientific, etc.)
     - Required capabilities (code_generation, function_calling, etc.)

2. **Task Classification**
   ```python
   # Example patterns:
   "coding": [
       r"(write|create|implement|code|function|class|method)",
       r"(bug|error|exception|fix|debug)",
       r"(python|javascript|typescript|java)",
   ]
   "reasoning": [
       r"(explain|why|how|reason|analyze|examine)",
       r"(compare|contrast|difference)",
   ]
   ```

3. **Model Selection** (`StrategicRouter._apply_capability_match_strategy()`)
   - Matches task requirements to model capabilities
   - Considers:
     - Hardware compatibility
     - Cost constraints
     - Performance scores
     - Required capabilities

### Example Flow

```
Prompt: "Write a Python function to sort a list"
  ↓
InputAnalyzer detects:
  - task_type: "coding" (matches "write", "function", "python")
  - complexity: "medium" (no high/low indicators)
  - required_capabilities: ["code_generation"]
  ↓
StrategicRouter selects:
  - Provider: OpenAI (good for coding)
  - Model: GPT-4 Turbo or GPT-3.5 Turbo (cost-effective)
  ↓
TacticalRouter executes with selected model
```

## Pattern-Based vs LLM-Based Analysis

### Pattern-Based (Current)

**Pros**:
- ✅ Fast (no API calls)
- ✅ Deterministic (same input = same result)
- ✅ No cost
- ✅ Works offline

**Cons**:
- ❌ Less sophisticated
- ❌ May miss nuanced tasks
- ❌ Requires pattern maintenance

### LLM-Based (Optional)

ChainMind **can** use LLM analysis, but it's **not enabled by default** because:
- Adds latency (API call)
- Adds cost (LLM call for analysis)
- Pattern-based is usually sufficient

**To enable LLM analysis**, you would need to:
1. Configure `InputAnalyzer` with LLM provider
2. Use LLM to analyze prompt before routing
3. This is more sophisticated but slower/costlier

## Configuration Improvements Made

### 1. Hardware Detection

**Before**: Hardcoded defaults (16GB RAM, no GPU)
```python
default_hardware_info = {
    "system_memory_mb": 16384,  # Hardcoded!
    "gpu_count": 0,
}
```

**After**: Dynamic detection
```python
default_hardware_info = self._detect_hardware_info()  # Auto-detects 123GB RAM, RTX 5080
```

### 2. Hardware Profiles

**Before**: RTX 5080 (15.5GB) didn't qualify as "high_end_gpu" (needed 24GB)
```python
"high_end_gpu": {"min_vram_gb": 24}  # RTX 5080 excluded
```

**After**: RTX 5080 qualifies as high-end
```python
"high_end_gpu": {"min_vram_gb": 15}  # RTX 5080 included
```

### 3. Provider Order

**Before**: Hardcoded order
```python
provider_order = ["claude", "openai"]  # Always same order
```

**After**: Optimized for hardware and cost
```python
# For RTX 5080:
provider_order = ["anthropic", "openai", "gemini", "llamacpp", "ollama"]
# Claude first (quality), then OpenAI (fallback), then local (last resort)
```

### 4. Context Lengths

**Before**: Conservative limits
```python
if cpu_memory_gb >= 64:
    max_context_length = 16384  # 16KB
```

**After**: Optimized for large RAM
```python
if cpu_memory_gb >= 64:
    max_context_length = 32768  # 32KB (doubled!)
```

### 5. Memory Limits

**Before**: Too conservative
```python
memory_footprint_limit_mb: int = 512  # 512MB
```

**After**: Optimized for high-end systems
```python
memory_footprint_limit_mb: int = 8192  # 8GB (16x increase!)
```

### 6. Batch Sizes

**Before**: Conservative batches
```python
if vram_gb >= 12:
    n_batch = 1024
```

**After**: Optimized for RTX 5080
```python
if vram_gb >= 15:
    n_batch = 2048  # Doubled for RTX 5080
```

## Model Selection Strategy

### Current Strategy: Capability Matching

1. **Analyze prompt** → Detect task type, complexity, capabilities
2. **Find compatible models** → Filter by hardware, capabilities
3. **Score models** → Weight by:
   - Capability match (60%)
   - Performance score (40%)
4. **Select best** → Highest score wins

### Example Selection

```
Prompt: "Explain quantum computing"
  ↓
Analysis:
  - task_type: "reasoning"
  - complexity: "medium"
  - required_capabilities: ["reasoning"]
  ↓
Compatible models:
  - Claude Sonnet (capability: 1.0, performance: 0.93) → Score: 0.95
  - GPT-4 Turbo (capability: 0.9, performance: 0.93) → Score: 0.91
  - Llama 3.1 8B (capability: 0.8, performance: 0.88) → Score: 0.83
  ↓
Selected: Claude Sonnet (highest score)
```

## Summary

### How Model Selection Works

1. **Pattern-based analysis** (regex) - Fast, deterministic
2. **Capability matching** - Matches task requirements to model capabilities
3. **Scoring system** - Combines capability match + performance score
4. **Hardware-aware** - Considers available GPU/RAM

### Configuration Improvements

✅ **Hardware detection** - Auto-detects instead of hardcoded
✅ **Hardware profiles** - RTX 5080 recognized as high-end
✅ **Provider order** - Optimized for cost/quality
✅ **Resource limits** - Increased for high-end hardware
✅ **Batch sizes** - Optimized for RTX 5080

### Result

ChainMind now:
- ✅ Automatically detects your hardware (RTX 5080, 123GB RAM)
- ✅ Selects optimal models based on task analysis
- ✅ Uses pattern-based analysis (fast, no cost)
- ✅ Can optionally use LLM analysis (if configured)
