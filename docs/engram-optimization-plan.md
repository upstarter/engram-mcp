# Engram Optimization Plan

**Last Updated:** 2026-01-10
**Status:** ALL PHASES COMPLETE

## Executive Summary

Engram's value is UNIQUE when it stores what Claude can't know otherwise:
- Project-specific gotchas
- System configurations
- Session decisions
- Learned preferences

~~Currently 52% of memories are generic~~ **UPDATE: Pruned to ~40% generic after consolidation**

### Implementation Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Enhanced 20-engram.sh hook | ✅ COMPLETE |
| Phase 2 | Role-aware memory cache | ✅ COMPLETE |
| Phase 3 | Tab-init integration | ✅ COMPLETE |
| Phase 4 | Claude session init protocol | ✅ COMPLETE |
| Phase 5 | Auto-context in engram_context() | ✅ COMPLETE |
| Phase 6 | Validation loop | ✅ COMPLETE |
| Phase 7 | Role affinity + file-based context | ✅ COMPLETE (2026-01-10) |

### What Was Implemented

1. **Role cache generator** (`~/.spc/lib/engram_role_cache.py`)
   - Generates per-role memory caches for 11 roles
   - Output: `~/.spc/projects/state/engram-roles/{role}.md`

2. **Tab-init integration** (`~/.spc/shell/claude-tab-integration.sh`)
   - Auto-exports `$ENGRAM_ROLE_CONTEXT`
   - Shows memory summary on tab init

3. **Session Init Protocol** (`~/.claude/CLAUDE.md`)
   - Updated to read role context files
   - Reads project-specific memories

4. **CFS Health Check** (`proj doctor`)
   - Validates engram integration
   - Checks role caches exist

5. **Memory consolidation**
   - Merged 7 duplicate memories → 2
   - Archived 6 generic memories

6. **Role-aware engram_context()** (`engram/server.py`)
   - Auto-detects CLAUDE_TAB_ROLE from environment
   - Enhances queries with role-specific terms
   - 11 roles with custom query terms

7. **Validation feedback loop** (`engram/storage.py`)
   - `access_log` table tracks every memory access
   - Logs query, role, project, and relevance
   - `get_validation_candidates()` finds high-value memories
   - `get_prune_candidates()` finds unused memories

8. **Enhanced health check** (`proj doctor`)
   - Validates knowledge graph
   - Checks access logging
   - Reports memory and node counts

## Current Architecture

### The Stack
```
┌─────────────────────────────────────────────────────────────┐
│                         ks (kitty sessions)                  │
│  ks w (work) │ ks r (resolve) │ ks sf (studioflow)          │
└─────────────────────┬───────────────────────────────────────┘
                      │ launches tabs with
                      ▼
┌─────────────────────────────────────────────────────────────┐
│               tab-init scripts (per tab)                     │
│  Each sets: CLAUDE_TAB_ROLE, CLAUDE_TAB_CONTEXT             │
│  Examples: ai-engram.sh, resolve-studioflow.sh              │
└─────────────────────┬───────────────────────────────────────┘
                      │ uses
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   proj (project switcher)                    │
│  Runs hooks in ~/.spc/project-hooks/on-switch.d/            │
│  Sets: SPC_PROJECT, SPC_PROJECT_TYPE, SPC_PROJECT_PATH      │
└─────────────────────┬───────────────────────────────────────┘
                      │ triggers
                      ▼
┌─────────────────────────────────────────────────────────────┐
│               20-engram.sh hook                              │
│  Currently: writes engram_context.txt (not consumed)        │
│  Gap: Not integrated with Claude sessions                   │
└─────────────────────────────────────────────────────────────┘
```

### Agent Roles in Tab System
| Tab Init Script | CLAUDE_TAB_ROLE | Purpose |
|-----------------|-----------------|---------|
| ai-engram.sh | engram-dev | Engram development |
| ai-main.sh | ai-dev | General AI development |
| ai-gpu.sh | gpu-specialist | GPU/CUDA work |
| resolve-studioflow.sh | studioflow | Video pipeline CLI |
| resolve-ai.sh | ai-content | Transcription/generation |
| channel-script.sh | scriptwriter | Video scripting |
| channel-record.sh | recording | Recording prep |

## The Vision: Agent-Aware Engram

### Each Agent Gets Role-Specific Context

When Claude starts in a tab with `CLAUDE_TAB_ROLE=studioflow`:
1. **Automatic recall** of StudioFlow-specific memories
2. **Filtered context** relevant to video pipeline work
3. **Pre-loaded gotchas** for this specific domain

When Claude starts in a tab with `CLAUDE_TAB_ROLE=gpu-specialist`:
1. **Automatic recall** of GPU/CUDA/PyTorch memories
2. **Filtered context** for hardware optimization
3. **Pre-loaded solutions** for common GPU issues

### Role-to-Engram Mapping

```python
ROLE_QUERIES = {
    # Development roles
    "engram-dev": ["engram architecture decisions", "engram gotchas", "memory storage patterns"],
    "ai-dev": ["pytorch cuda patterns", "gpu optimization", "model deployment"],
    "gpu-specialist": ["cuda memory oom", "pytorch debugging", "gpu performance"],
    "studioflow": ["studioflow architecture", "rough_cut gotchas", "audio markers"],

    # Content roles
    "ai-content": ["whisper transcription", "voice synthesis", "content generation"],
    "scriptwriter": ["video script structure", "hook formulas", "tutorial format"],
    "recording": ["recording workflow", "audio quality", "teleprompter"],

    # Analytics roles
    "youtube-growth": ["youtube algorithm", "ctr optimization", "thumbnail patterns"],
    "analytics": ["channel metrics", "audience retention", "monetization"],
}
```

## Implementation Plan

### Phase 1: Enhanced 20-engram.sh Hook

Update to pre-fetch memories and create role-aware cache:

```bash
#!/bin/bash
# ~/.spc/project-hooks/on-switch.d/20-engram.sh
# Enhanced engram integration - project + role aware

type="$1"
path="$2"
name="$3"

STATE_DIR="$HOME/.spc/projects/state"
mkdir -p "$STATE_DIR"

# 1. Write project context (existing)
echo "Project: $name ($type)" > "$STATE_DIR/engram_context.txt"

# 2. Pre-fetch project-specific memories
python3 << PYTHON
from engram.storage import MemoryStore
store = MemoryStore()

project = "$name".lower()
results = store.recall(f"{project} architecture gotchas critical", limit=5)

with open("$STATE_DIR/engram_project_memories.md", "w") as f:
    f.write(f"# Engram Context: $name\n\n")
    for r in results:
        f.write(f"**[{r['relevance']:.0%}]** {r['content']}\n\n---\n\n")
PYTHON
```

### Phase 2: Role-Aware Memory Cache

Create script that generates per-role memory files:

```bash
#!/bin/bash
# ~/.spc/engram/generate-role-cache.sh
# Run periodically or on engram updates

STATE_DIR="$HOME/.spc/projects/state/engram-roles"
mkdir -p "$STATE_DIR"

python3 << 'PYTHON'
import os
from engram.storage import MemoryStore

store = MemoryStore()
state_dir = os.path.expanduser("~/.spc/projects/state/engram-roles")

ROLE_QUERIES = {
    "engram-dev": "engram architecture decisions storage gotchas",
    "ai-dev": "pytorch cuda ai development patterns",
    "gpu-specialist": "gpu cuda oom memory pytorch debugging",
    "studioflow": "studioflow rough_cut audio markers architecture",
    "ai-content": "whisper transcription voice synthesis generation",
    "scriptwriter": "video script hook formula tutorial structure",
    "youtube-growth": "youtube algorithm ctr thumbnail viral",
}

for role, query in ROLE_QUERIES.items():
    results = store.recall(query, limit=7)

    filepath = os.path.join(state_dir, f"{role}.md")
    with open(filepath, "w") as f:
        f.write(f"# Engram Context: {role}\n\n")
        f.write("*Auto-generated role-specific memories*\n\n")

        for r in results:
            f.write(f"## [{r['relevance']:.0%}] {r['memory_type']}\n")
            f.write(f"{r['content']}\n\n")

    print(f"Generated: {filepath} ({len(results)} memories)")
PYTHON
```

### Phase 3: Tab-Init Integration

Update each tab-init script to inject engram context:

```bash
# Template for tab-init scripts
# Add to: ~/.spc/kitty/tab-init/*.sh

# After setting CLAUDE_TAB_ROLE...
ROLE_CACHE="$HOME/.spc/projects/state/engram-roles/${CLAUDE_TAB_ROLE}.md"

if [ -f "$ROLE_CACHE" ]; then
    echo -e "${M}ENGRAM CONTEXT (${CLAUDE_TAB_ROLE}):${R}"
    echo -e "${D}$(head -20 "$ROLE_CACHE" | grep -E '^\*\*\[' | head -5)${R}"
    echo ""

    # Export for Claude to read
    export ENGRAM_ROLE_CONTEXT="$ROLE_CACHE"
fi
```

### Phase 4: Claude Session Init

Update global CLAUDE.md to consume role context:

```markdown
## Session Init Protocol (MANDATORY)

On EVERY session start:

1. **Check role context** (if in Kitty tab):
   - Read $ENGRAM_ROLE_CONTEXT if set
   - This contains pre-fetched memories for your role

2. **Check project context**:
   - Read ~/.spc/projects/state/engram_project_memories.md
   - This contains current project's relevant memories

3. **Load additional context**:
   - Call engram_context(query="current work")
   - This supplements the pre-cached context

4. **Announce state**:
   [ROLE: {role}] | Project: {project} | Context loaded: {count} memories
```

### Phase 5: Auto-Context in engram_context()

Enhance engram server to be role-aware:

```python
# In engram/server.py - file-based context reading (env vars don't cross process boundary)

def _get_context_from_files() -> tuple[str, str]:
    """Read role and project from state files."""
    role = ""
    project = ""

    # Read role from file (written by claude-tab-integration.sh)
    role_file = os.path.join(CONTEXT_STATE_DIR, "current_role")
    if os.path.exists(role_file):
        with open(role_file) as f:
            role = f.read().strip()

    # Read project from active_project JSON
    project_file = os.path.expanduser("~/.spc/active_project")
    if os.path.exists(project_file):
        data = json.load(open(project_file))
        project = data.get("name", "").lower()

    return role, project

# Query enhancement: role/project names provide semantic context
# NO hardcoded query terms - let vector similarity do the work
query_parts = [base_query]
if project:
    query_parts.append(project)
if role:
    query_parts.append(role)  # Role name itself is enough
```

**Key insight:** Hardcoded query terms are unnecessary. The role and project names
themselves provide semantic context for vector similarity search. "studioflow" will
naturally match memories about StudioFlow, "gpu-specialist" will match GPU memories.

## Phase 6: Validation Loop

Track memory usage and auto-validate:

```python
# In storage.py - access logging reads role/project from files

def log_access(memory_id, query, role, project, relevance):
    """Log memory access for feedback analysis."""
    self.db.execute("""
        INSERT INTO access_log (memory_id, query, role, project, relevance)
        VALUES (?, ?, ?, ?, ?)
    """, (memory_id, query, role, project, relevance))
```

## Memory Optimization

### Prune Generic Content

Remove memories that Claude already knows:

```python
# Candidates for removal - generic knowledge
PRUNE_PATTERNS = [
    "debugging hierarchy",  # Claude knows debugging
    "code smell",           # Textbook knowledge
    "productivity",         # Generic advice
    "procrastination",      # Self-help content
    "pricing psychology",   # Business basics
]

# Keep - unique value
KEEP_PATTERNS = [
    "STUDIOFLOW",          # Project-specific
    "ENGRAM",              # Project-specific
    "Eric",                # Personal
    "RTX 5080",            # System-specific
    "chose .* because",    # Decisions with reasoning
]
```

### Focus Areas by Role

| Role | Engram Should Contain |
|------|----------------------|
| engram-dev | Architecture decisions, storage gotchas, scoring formula |
| studioflow | rough_cut IP, audio marker gotchas, Resolve integration |
| gpu-specialist | CUDA OOM fixes, PyTorch debugging, Blackwell specifics |
| ai-content | Whisper fuzzy matching, voice model configs |
| scriptwriter | Eric's hook preferences, proven structures |
| youtube-growth | Algorithm insights specific to Eric's niche |

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Total memories | 157 | <100 (pruned) |
| Generic content | 52% | <20% |
| Role-specific memories | ~30% | >70% |
| Auto-context on init | No | Yes |
| Agent-aware recall | No | Yes |

## The Complete Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     ks w (launch workspace)                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ Tab 1: Script │ │ Tab 2: AI     │ │ Tab 3: SF     │
│ ROLE=script   │ │ ROLE=ai-dev   │ │ ROLE=studio   │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ Load:         │ │ Load:         │ │ Load:         │
│ script.md     │ │ ai-dev.md     │ │ studioflow.md │
│ (pre-cached)  │ │ (pre-cached)  │ │ (pre-cached)  │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ Claude knows: │ │ Claude knows: │ │ Claude knows: │
│ - Hook forms  │ │ - GPU gotchas │ │ - rough_cut   │
│ - Script fmt  │ │ - PyTorch fix │ │ - Audio marks │
│ - Eric prefs  │ │ - CUDA OOM    │ │ - Resolve API │
└───────────────┘ └───────────────┘ └───────────────┘
```

## Implementation Priority

1. ✅ **Prune generic content** - Archived 6 generic memories
2. ✅ **Create role-query mapping** - 11 roles defined in engram_role_cache.py
3. ✅ **Generate role cache files** - Pre-fetch per-role memories
4. ✅ **Update tab-init scripts** - Inject context via claude-tab-integration.sh
5. ✅ **Enhance engram_context()** - Role-aware queries with auto-detection
6. ✅ **Update CLAUDE.md** - Documented role-aware init protocol
7. ✅ **Add validation tracking** - access_log table + analysis functions

## Files Modified/Created

| File | Status | Change |
|------|--------|--------|
| `~/.spc/project-hooks/on-switch.d/20-engram.sh` | ✅ Done | Enhanced with async project memory fetch |
| `~/.spc/lib/engram_role_cache.py` | ✅ Created | Role cache generator (11 roles) |
| `~/.spc/shell/claude-tab-integration.sh` | ✅ Modified | Auto-loads engram role context |
| `~/.spc/kitty/tab-init/*.sh` | ✅ Done | Source claude-tab-integration.sh |
| `~/.claude/CLAUDE.md` | ✅ Modified | Session Init Protocol updated |
| `~/.spc/bin/proj` | ✅ Modified | Added `proj doctor` with engram checks |
| `~/.spc/docs/CFS-ARCHITECTURE.md` | ✅ Created | Full CFS documentation |
| `engram/server.py` | ✅ Modified | File-based context, role passed to recall/remember |
| `engram/storage.py` | ✅ Modified | source_role column, role affinity scoring |
| `engram/graph.py` | ✅ Modified | source_role in MemoryNode |
| `docs/engram-cfs-integration.md` | ✅ Created | CFS+Engram integration design |
| `tests/test_role_context.py` | ✅ Created | 29 tests for role affinity feature |

## Phase 7: Role Affinity (Added 2026-01-10)

Beyond the original plan, we implemented **agent-owned memories with cross-agent visibility**:

### What Was Added

1. **source_role storage** - Each memory tagged with creating agent's role
   - SQLite: `source_role` column
   - ChromaDB: `source_role` metadata
   - Graph: `source_role` node attribute

2. **Role affinity scoring** - 15% relevance boost for same-role queries
   ```python
   if current_role == source_role:
       role_affinity = 1.15  # 15% boost
   ```

3. **File-based context passing** - MCP server reads from files (not env vars)
   - Tab-init writes: `~/.spc/projects/state/current_role`
   - MCP reads via `_get_context_from_files()`

4. **Removed hardcoded query terms** - Role/project names provide semantic context naturally

5. **Comprehensive tests** - 29 tests in `tests/test_role_context.py`

### How It Works

```
gpu-specialist stores "CUDA OOM fix"
    → tagged with source_role="gpu-specialist"
    → stored in SQLite, ChromaDB, Graph

studioflow queries "memory fix"
    → finds CUDA memory (semantic match)
    → role_affinity = 1.0 (no boost)

gpu-specialist queries "memory fix"
    → finds CUDA memory (semantic match)
    → role_affinity = 1.15 (boosted)
    → ranks higher in results
```

### Key Design Decision

**No silos** - All agents can access all memories. Role affinity is additive boosting, not filtering. This enables:
- Agents build domain expertise over time
- Cross-pollination of knowledge still works
- Semantic relevance remains primary ranking factor

## Next Steps (Future Enhancements)

All phases are complete. Future improvements could include:

### Auto-Validation
- Detect when Claude quotes/uses memory content in responses
- Auto-call validate_memory() for quoted memories
- Could use response parsing in a post-hook

### Memory Decay
- Periodic job to reduce importance of never-accessed memories
- `get_prune_candidates()` already identifies them
- Could integrate with cron or session-end hook

### Dashboard
- Web UI to visualize memory health
- Show access patterns, prune candidates, validation candidates
- Role-specific memory distribution
