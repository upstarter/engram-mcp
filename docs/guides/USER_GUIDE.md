# User Guide: ChainMind + engram-mcp Integration

## Table of Contents

1. [How It Works](#how-it-works)
2. [Quick Start](#quick-start)
3. [Features](#features)
4. [Usage Examples](#usage-examples)
5. [Configuration](#configuration)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)

---

## How It Works

### Architecture Overview

The ChainMind + engram-mcp integration creates a seamless bridge between Claude Code, your persistent memory system (engram-mcp), and ChainMind's intelligent routing capabilities. Here's how it all fits together:

```
┌─────────────────┐
│   Claude Code   │  ← You interact here
└────────┬────────┘
         │ MCP Protocol
         │
┌────────▼─────────────────────────────────────┐
│         engram-mcp MCP Server                 │
│  ┌─────────────────────────────────────────┐ │
│  │  engram_remember                        │ │  ← Store memories
│  │  engram_recall                          │ │  ← Retrieve memories
│  │  engram_context                         │ │  ← Get context
│  │  engram_consolidate                     │ │  ← Merge memories
│  └─────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────┐ │
│  │  chainmind_generate                    │ │  ← Generate with fallback
│  │  chainmind_generate_prompt              │ │  ← Optimize prompts
│  │  chainmind_verify                      │ │  ← Verify responses
│  └─────────────────────────────────────────┘ │
└────────┬─────────────────────────────────────┘
         │
         │ Uses ChainMind Helper
         │
┌────────▼─────────────────────────────────────┐
│         ChainMind Router                     │
│  ┌─────────────────────────────────────────┐ │
│  │  Strategic Router                       │ │  ← Selects best provider
│  │  Tactical Router                         │ │  ← Executes request
│  └─────────────────────────────────────────┘ │
└────────┬─────────────────────────────────────┘
         │
         ├──► Anthropic (Claude) ← Preferred
         ├──► OpenAI (GPT)        ← Fallback 1
         └──► Ollama (Local)      ← Fallback 2
```

### Core Components

#### 1. **engram-mcp** (Memory System)
- **Purpose**: Persistent memory for Claude
- **Storage**: ChromaDB (vectors) + SQLite (structured data)
- **Features**: Semantic search, knowledge graph, temporal decay
- **Location**: `/mnt/dev/ai/engram-mcp`

#### 2. **ChainMind Helper** (Routing Layer)
- **Purpose**: Intelligent provider routing with usage limit handling
- **Features**:
  - Detects Claude usage/token limits
  - Automatically falls back to alternative providers
  - Provides seamless provider switching
- **Location**: `/mnt/dev/ai/engram-mcp/engram/chainmind_helper.py`

#### 3. **Prompt Generator** (Optimization Layer)
- **Purpose**: Generate optimized prompts for Claude
- **Features**:
  - Incorporates engram-mcp memories as context
  - Multiple prompt strategies (concise, detailed, structured, balanced)
  - Project-aware context retrieval
- **Location**: `/mnt/dev/ai/engram-mcp/engram/prompt_generator.py`

#### 4. **ChainMind Router** (Execution Layer)
- **Purpose**: Multi-provider LLM routing
- **Features**:
  - Cost optimization
  - Capability-based routing
  - Provider fallback chain
- **Location**: `/mnt/dev/ai/ai-platform/chainmind`

### How It Works: Step by Step

#### Scenario 1: Normal Operation (Claude Available)

```
1. You ask Claude: "Remember: I prefer Python over JavaScript"
   ↓
2. Claude calls: engram_remember(content="I prefer Python...")
   ↓
3. engram-mcp stores memory in ChromaDB + SQLite
   ↓
4. Memory is now available for future queries
```

#### Scenario 2: Text Generation (Claude Available)

```
1. You ask Claude: "Generate a summary of my preferences"
   ↓
2. Claude calls: chainmind_generate(prompt="Summarize...", prefer_claude=True)
   ↓
3. ChainMind Helper tries Claude first
   ↓
4. Claude responds successfully
   ↓
5. Response returned to you
```

#### Scenario 3: Usage Limit Hit (Automatic Fallback)

```
1. You ask Claude: "Generate a long document"
   ↓
2. Claude calls: chainmind_generate(prompt="Generate...", prefer_claude=True)
   ↓
3. ChainMind Helper tries Claude first
   ↓
4. Claude returns: QuotaExceededError (usage limit hit)
   ↓
5. ChainMind Helper detects usage limit error
   ↓
6. Automatically tries OpenAI (fallback provider)
   ↓
7. OpenAI responds successfully
   ↓
8. Response returned with note: "Used OpenAI due to Claude usage limit"
   ↓
9. You get your result without purchasing extra credits!
```

#### Scenario 4: Optimized Prompt Generation

```
1. You ask Claude: "Write a function"
   ↓
2. Claude calls: chainmind_generate_prompt(task="Write a function", project="my-project")
   ↓
3. Prompt Generator retrieves relevant memories from engram-mcp:
   - "User prefers Python over JavaScript"
   - "Project uses type hints"
   - "Always include docstrings"
   ↓
4. Prompt Generator builds optimized prompt:
   "Write a function

   Context: Use Python

   Relevant information:
   - [preference] User prefers Python over JavaScript
   - [fact] Project uses type hints
   - [preference] Always include docstrings"
   ↓
5. Optimized prompt returned to Claude
   ↓
6. Claude uses optimized prompt for better results
```

### Usage Limit Detection

The system detects Claude usage limits through multiple mechanisms:

1. **Exception Type Detection**:
   - `QuotaExceededError` (ChainMind's error type)
   - Any exception with "QuotaExceeded" in the name

2. **Error Code Detection**:
   - `CM-1801` (ChainMind's quota exceeded code)
   - `QUOTA_EXCEEDED` in error code

3. **Error Message Detection**:
   - "quota exceeded"
   - "usage limit"
   - "token limit"
   - "monthly limit"
   - "insufficient credits"
   - "purchase extra usage credits"

When any of these are detected, the system automatically switches to fallback providers.

### Fallback Chain

Default fallback order:
1. **Claude (anthropic)** - Tried first (your preferred provider)
2. **OpenAI** - First fallback (if Claude fails)
3. **Ollama** - Second fallback (if OpenAI fails)

You can customize the fallback chain in the configuration.

### Memory Integration

engram-mcp provides context-aware memory:

- **Semantic Search**: Finds relevant memories by meaning, not just keywords
- **Project Awareness**: Automatically detects current project from working directory
- **Temporal Decay**: Older memories gradually decrease in importance
- **Contradiction Detection**: Identifies conflicting memories
- **Auto-Consolidation**: Merges similar memories to prevent bloat

The Prompt Generator leverages these memories to create context-rich prompts for Claude.

---

## Quick Start

### Prerequisites

1. **engram-mcp** installed and configured
2. **ChainMind** installed at `/mnt/dev/ai/ai-platform/chainmind` (optional)
3. **Claude Code** with MCP server configured

### Installation

The integration is already installed! Just verify it works:

```bash
cd /mnt/dev/ai/engram-mcp
python3 verify_chainmind_integration.py
```

Expected output: `5/5 tests passed ✅`

### First Use

1. **Open Claude Code** in Cursor
2. **Ask Claude to remember something**:
   ```
   Remember: I prefer Python over JavaScript
   ```
3. **Ask Claude to recall it**:
   ```
   What do I prefer?
   ```
4. **Test ChainMind tools** (if ChainMind configured):
   ```
   Use chainmind_generate to write a haiku about coding
   ```

---

## Features

### 1. Automatic Usage Limit Handling

**Problem**: Claude hits monthly usage limit → Need to purchase extra credits

**Solution**: Automatic fallback to alternative providers

**How to Use**: Just use Claude normally! The system handles fallback automatically.

```python
# Claude automatically uses fallback when needed
result = await call_tool("chainmind_generate", {
    "prompt": "Your prompt here",
    "prefer_claude": True  # Tries Claude first, falls back if needed
})
```

### 2. Optimized Prompt Generation

**Problem**: Prompts lack context → Claude gives generic responses

**Solution**: Context-aware prompt generation with engram-mcp memories

**How to Use**: Generate optimized prompts before asking Claude

```python
# Generate optimized prompt
prompt_result = await call_tool("chainmind_generate_prompt", {
    "task": "Write a function to calculate Fibonacci",
    "strategy": "balanced",  # concise, detailed, structured, balanced
    "project": "my-project"  # Optional, auto-detected
})

# Use the optimized prompt
optimized_prompt = prompt_result["prompt"]
# Now use this prompt with Claude
```

### 3. Multi-Model Verification

**Problem**: Need to verify Claude's responses for accuracy

**Solution**: Verify responses with alternative models

**How to Use**: Verify important responses

```python
# Verify a response
verification = await call_tool("chainmind_verify", {
    "response": "Claude's response here",
    "original_prompt": "Original prompt",
    "verification_providers": ["openai"]
})
```

### 4. Persistent Memory

**Problem**: Claude forgets previous conversations

**Solution**: engram-mcp stores memories persistently

**How to Use**: Remember important information

```python
# Store a memory
await call_tool("engram_remember", {
    "content": "I prefer Python over JavaScript",
    "memory_type": "preference"
})

# Recall memories
memories = await call_tool("engram_recall", {
    "query": "What do I prefer?"
})
```

---

## Usage Examples

### Example 1: Code Generation with Preferences

```
You: "Write a function to fetch user data"

Claude's workflow:
1. Calls chainmind_generate_prompt(task="Write a function...", project="my-project")
2. Prompt Generator retrieves memories:
   - "User prefers TypeScript"
   - "Use async/await"
   - "Always include error handling"
3. Returns optimized prompt with context
4. Calls chainmind_generate(prompt=optimized_prompt, prefer_claude=True)
5. Returns code that matches your preferences!
```

### Example 2: Handling Usage Limits

```
You: "Generate a comprehensive analysis document"

Claude's workflow:
1. Calls chainmind_generate(prompt="Generate analysis...", prefer_claude=True)
2. ChainMind tries Claude → QuotaExceededError
3. Automatically tries OpenAI → Success
4. Returns: "Generated document [Used OpenAI due to Claude usage limit]"
5. You get your document without extra credits!
```

### Example 3: Memory Consolidation

```
You: "Consolidate my memories about Python preferences"

Claude's workflow:
1. Calls engram_consolidate(action="find_candidates")
2. Finds similar memories about Python
3. Calls chainmind_generate(prompt="Consolidate these memories...")
4. Gets consolidated text
5. Calls engram_consolidate(action="consolidate", content=consolidated_text)
6. Stores consolidated memory
```

---

## Configuration

### Auto-Approve Memories

By default, `engram_remember` shows a preview for confirmation. To auto-approve:

**Option 1: Environment Variable**
```bash
export ENGRAM_AUTO_APPROVE=true
```

**Option 2: Config File**
Create `~/.engram/config/engram.yaml`:
```yaml
auto_approve: true
```

### ChainMind Configuration

Optional config at `~/.engram/config/chainmind.yaml`:
```yaml
enabled: true
fallback:
  providers:
    - openai
    - ollama
  auto_fallback: true
```

### Cursor Auto-Accept Settings

See [Cursor Configuration](#cursor-configuration) section below.

---

## Troubleshooting

### ChainMind Tools Not Available

**Symptom**: `chainmind_generate` returns "ChainMind helper not available"

**Solutions**:
1. Check ChainMind is installed: `ls /mnt/dev/ai/ai-platform/chainmind`
2. Verify ChainMind dependencies: `cd chainmind && pip list | grep chainmind`
3. Check error messages in Cursor's developer console
4. **Note**: engram-mcp still works normally without ChainMind!

### Import Errors

**Symptom**: Python import errors when using ChainMind tools

**Solutions**:
1. Verify Python path includes ChainMind: `python3 -c "import sys; print('/mnt/dev/ai/ai-platform/chainmind' in sys.path)"`
2. Check ChainMind dependencies are installed
3. Try activating ChainMind's virtual environment if it has one

### Provider Errors

**Symptom**: Fallback providers fail

**Solutions**:
1. Check provider API keys are configured in ChainMind
2. Verify providers are available: Check ChainMind's provider configuration
3. Check network connectivity
4. Review ChainMind logs for provider errors

### Memory Not Found

**Symptom**: `engram_recall` returns no results

**Solutions**:
1. Check memory was stored: Use `engram_context` to see all memories
2. Try different query terms (semantic search, not exact match)
3. Check project context: Memories might be project-specific
4. Verify ChromaDB is working: Check `~/.engram/data/chroma/`

### Auto-Accept Not Working

**Symptom**: Still seeing confirmation dialogs

**Solutions**:
1. Restart Cursor after changing settings
2. Check settings file location: `~/.config/Cursor/User/settings.json`
3. Verify JSON syntax is valid
4. See [Cursor Configuration](#cursor-configuration) section

---

## Best Practices

### 1. Use Prompt Generation for Complex Tasks

For complex tasks, generate an optimized prompt first:

```python
# Good: Generate prompt first
prompt = await call_tool("chainmind_generate_prompt", {
    "task": "Complex task description",
    "strategy": "structured"
})
# Then use the prompt

# Less optimal: Direct prompt
# Just asking Claude directly without context
```

### 2. Remember Important Preferences

Store your preferences so they're always available:

```python
# Remember preferences
await call_tool("engram_remember", {
    "content": "I prefer TypeScript over JavaScript",
    "memory_type": "preference",
    "importance": 0.9
})
```

### 3. Use Appropriate Prompt Strategies

- **concise**: Quick tasks, simple requests
- **detailed**: Complex tasks, need thoroughness
- **structured**: Multi-step tasks, need organization
- **balanced**: General use (default)

### 4. Verify Critical Responses

For important responses, verify with alternative models:

```python
# Generate response
response = await call_tool("chainmind_generate", {...})

# Verify if critical
if is_critical:
    verification = await call_tool("chainmind_verify", {
        "response": response,
        "original_prompt": prompt
    })
```

### 5. Consolidate Memories Regularly

Prevent memory bloat by consolidating similar memories:

```python
# Find consolidation candidates
candidates = await call_tool("engram_consolidate", {
    "action": "find_candidates",
    "similarity_threshold": 0.85
})

# Consolidate if needed
if candidates:
    await call_tool("engram_consolidate", {
        "action": "consolidate",
        "memory_ids": [...],
        "consolidated_content": "..."
    })
```

---

## Cursor Configuration

### Auto-Accept Settings

To enable auto-accept for all AI changes in Cursor, add these settings to `~/.config/Cursor/User/settings.json`:

```json
{
  "cursor.chat.autoApply": true,
  "cursor.composer.autoApply": true,
  "cursor.composer.skipPreview": true,
  "cursor.composer.confirmBeforeApply": false,
  "workbench.editor.autoSave": "afterDelay",
  "workbench.editor.autoSaveDelay": 100
}
```

**Important**: Restart Cursor after changing settings!

### Troubleshooting Auto-Accept

If auto-accept isn't working:

1. **Check settings file exists**: `~/.config/Cursor/User/settings.json`
2. **Validate JSON syntax**: Use `python3 -m json.tool ~/.config/Cursor/User/settings.json`
3. **Restart Cursor**: Settings only load on startup
4. **Check Cursor version**: Update to latest version
5. **Check for conflicting settings**: Some settings might override auto-accept

---

## Advanced Topics

### Custom Fallback Providers

You can customize the fallback provider chain:

```python
result = await call_tool("chainmind_generate", {
    "prompt": "Your prompt",
    "prefer_claude": True,
    "fallback_providers": ["openai", "ollama", "custom_provider"]
})
```

### Prompt Strategy Selection

Choose the right strategy for your task:

- **concise**: < 100 words, simple tasks
- **balanced**: 100-500 words, general tasks (default)
- **detailed**: 500+ words, complex tasks
- **structured**: Multi-section tasks, documentation

### Memory Importance Levels

Set importance when remembering:

- **0.9-1.0**: Critical preferences, core decisions
- **0.7-0.9**: Important facts, patterns
- **0.5-0.7**: General information
- **0.0-0.5**: Temporary, low-priority

---

## Support

For issues or questions:

1. Check this guide first
2. Review troubleshooting section
3. Check test results: `python3 verify_chainmind_integration.py`
4. Review logs in Cursor's developer console

---

## Summary

The ChainMind + engram-mcp integration provides:

✅ **Automatic usage limit handling** - No more extra credits needed
✅ **Context-aware prompts** - Better Claude responses
✅ **Persistent memory** - Claude remembers your preferences
✅ **Multi-model verification** - Quality assurance
✅ **Seamless integration** - Works automatically

**Ready to use!** Just start using Claude normally, and the system handles everything automatically.
