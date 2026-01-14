# Request Flow Tracing

## Overview

The `trace_request_flow.py` script traces a prompt through the entire ChainMind + engram-mcp integration, logging all data transformations, inputs, and outputs at each stage.

## Directory

**Run from:** `/mnt/dev/ai/engram-mcp`

```bash
cd /mnt/dev/ai/engram-mcp
python3 trace_request_flow.py
```

**Why this directory?**
- Script uses hardcoded paths that expect this location
- Trace files are saved here (`trace_*.json`)
- Imports expect `engram` module to be available
- All paths are relative to this directory

## Usage

### Basic Usage (No API Calls)

```bash
cd /mnt/dev/ai/engram-mcp
python3 trace_request_flow.py
```

This will:
- Trace the prompt through all analysis stages
- Log all data transformations
- Save a JSON trace file: `trace_YYYYMMDD_HHMMSS.json`
- **Skip actual API calls** (to avoid costs)

### With Actual API Execution

```bash
cd /mnt/dev/ai/engram-mcp
TRACE_EXECUTE=true python3 trace_request_flow.py
```

This will also execute the actual request through ChainMind (requires API keys).

## Output

### Console Output

The script prints each step with:
- Step number and stage name
- Description of what's happening
- Complete data structure at that point

### JSON Trace File

The trace file is saved to: `/mnt/dev/ai/engram-mcp/trace_*.json`

Contains:
- All steps with timestamps
- Complete data structures at each stage
- Input/output transformations
- Error information (if any)

### Viewing the Trace

```bash
cd /mnt/dev/ai/engram-mcp

# View full trace
cat trace_*.json | jq '.'

# View specific step
cat trace_*.json | jq '.[0]'  # First step

# View all InputAnalyzer steps
cat trace_*.json | jq '.[] | select(.stage == "INPUT_ANALYZER")'

# View analysis result
cat trace_*.json | jq '.[] | select(.step_name == "Complete Analysis Result") | .data'

# View domain detection
cat trace_*.json | jq '.[] | select(.step_name == "Domain Detection") | .data'
```

## Stages Traced

1. **INITIAL_REQUEST**: User input with role and agent_id
2. **CHAINMIND_HELPER**: Initialization and configuration
3. **CHAINMIND_HELPER**: Request dict construction
4. **STRATEGIC_ROUTER**: Request received, ready for analysis
5. **INPUT_ANALYZER**: Input analysis start
6. **INPUT_ANALYZER**: Prompt structure analysis
7. **INPUT_ANALYZER**: Domain detection (with role boost)
8. **INPUT_ANALYZER**: Task type detection (with role boost)
9. **INPUT_ANALYZER**: Context-aware boosting
10. **INPUT_ANALYZER**: Complete analysis result
11. **STRATEGIC_ROUTER**: Strategy selection
12. **MODEL_REGISTRY**: Model selection input
13. **EXECUTION**: Request execution (if enabled)
14. **SUMMARY**: Trace complete

## Key Data Transformations

### 1. Initial Input → Request Dict

**Input:**
```json
{
  "prompt": "how do i fix this python function?",
  "agent_role": "software_engineer",
  "agent_id": "software_engineer:session_123"
}
```

**Request Dict:**
```json
{
  "prompt": "how do i fix this python function?",
  "provider": "openai",
  "agent_role": "software_engineer",
  "agent_id": "software_engineer:session_123",
  "context": {
    "agent_role": "software_engineer",
    "agent_id": "software_engineer:session_123"
  },
  "budget_constraints": {...}
}
```

### 2. Domain Detection (Role Boost)

**Input:**
- Prompt: "how do i fix this python function?"
- Role: "software_engineer"

**Output:**
```json
{
  "detected_domain": "technical",
  "agent_role": "software_engineer",
  "role_domain_mapping": true,
  "mapped_domain": "technical"
}
```

**Transformation:**
- Role maps to "technical" domain
- Domain gets 2x boost if detected, or 3.0 score if not detected

### 3. Task Type Detection (Role Boost)

**Input:**
- Prompt: "how do i fix this python function?"
- Role: "software_engineer"
- Domain: "technical"

**Output:**
```json
{
  "task_type": "coding",
  "confidence": 0.855
}
```

**Transformation:**
- Pattern matching scores "coding" task
- Role boosts "coding" by 1.5x (role_task_preferences)
- Domain boost (2x for "technical")
- Structure analysis (no code blocks, but "python function" keyword)
- Final confidence: 0.855

### 4. Complete Analysis Result

**Output:**
```json
{
  "task_type": "coding",
  "domain": "technical",
  "complexity": "low",
  "capabilities": ["code_generation"],
  "confidence": 0.855,
  "agent_role": "software_engineer",
  "metadata": {
    "structure": {...},
    "agent_role": "software_engineer"
  }
}
```

## Example Trace Output

See `trace_*.json` files for complete traces. Each step includes:

```json
{
  "step": 1,
  "stage": "INITIAL_REQUEST",
  "step_name": "User Input",
  "timestamp": "2026-01-11T19:34:11.123456",
  "description": "Initial request from Claude Code with role and agent_id",
  "data": {
    "prompt": "how do i fix this python function?",
    "agent_role": "software_engineer",
    "agent_id": "software_engineer:session_123",
    "parameters": {...}
  }
}
```

## Customization

### Test Different Prompts

Edit `trace_request_flow.py` and modify the `test_prompts` list:

```python
test_prompts = [
    {
        "prompt": "your prompt here",
        "agent_role": "your_role",
        "agent_id": "your_role:session_id",
        "description": "Description"
    }
]
```

### Test Different Roles

Try different roles to see how they affect domain/task detection:
- `"software_engineer"` → `technical` domain, boosts `coding`
- `"youtube_content_creator"` → `youtube` domain, boosts `reasoning`
- `"video_editor"` → `video_production` domain, boosts `creative`

## Troubleshooting

### Router Not Initialized

If you see "Router initialization issue", the router may need full initialization. This is normal for tracing without API calls.

### Missing API Keys

If execution fails, check that API keys are set:
```bash
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY
```

### View Trace File

```bash
cd /mnt/dev/ai/engram-mcp

# Pretty print
cat trace_*.json | python3 -m json.tool

# Search for specific data
cat trace_*.json | jq '.[] | select(.data.task_type == "coding")'
```

## Quick Start

```bash
# 1. Navigate to directory
cd /mnt/dev/ai/engram-mcp

# 2. Run trace
python3 trace_request_flow.py

# 3. View results
ls -la trace_*.json
cat trace_*.json | jq '.[] | select(.stage == "INPUT_ANALYZER")'
```
