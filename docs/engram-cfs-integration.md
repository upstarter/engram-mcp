# Engram + CFS Integration Design

**Created:** 2026-01-10
**Status:** Active Development

## Overview

This document describes how Engram (Claude's persistent memory) integrates with the Context Flow System (CFS) - the proj/ks/hooks ecosystem that manages project context.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERACTION                                │
│                         proj <name>  │  ks <session>                        │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────────────┐
│                           CFS LAYER                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │    proj     │→ │    hooks    │→ │  tab-init   │→ │   claude    │        │
│  │   switch    │  │  on-switch  │  │   scripts   │  │   session   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│        │                │                │                │                 │
│        │                ▼                ▼                ▼                 │
│        │         ┌─────────────────────────────────────────────┐           │
│        │         │            STATE FILES                       │           │
│        │         │  ~/.spc/active_project (JSON)               │           │
│        │         │  ~/.spc/projects/state/current_role         │ ← NEW     │
│        │         │  ~/.spc/projects/state/engram_context.txt   │           │
│        │         │  ~/.spc/projects/state/engram-roles/*.md    │           │
│        │         └─────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ENGRAM LAYER                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   SQLite    │  │  ChromaDB   │  │  NetworkX   │  │  MCP Server │        │
│  │  memories   │  │   vectors   │  │    graph    │  │    tools    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                              │
│  Storage: ~/.engram/data/                                                   │
│  - memories.db (SQLite)                                                     │
│  - chromadb/ (vector store)                                                 │
│  - knowledge_graph.json (NetworkX)                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Integration Points

### 1. Project Switch Hook (20-engram.sh)

**Trigger:** `proj <name>` command
**Location:** `~/.spc/project-hooks/on-switch.d/20-engram.sh`

```bash
# Flow:
# 1. proj switch → runs hooks → 20-engram.sh receives (type, path, name)
# 2. Writes engram_context.txt with project info
# 3. Async fetches project-specific memories to engram_project_memories.md
```

**Purpose:**
- Capture project context change
- Pre-fetch relevant memories for the project
- Make project memories available to Claude

### 2. Role Cache Generator

**Trigger:** Manual or cron (`python ~/.spc/lib/engram_role_cache.py`)
**Location:** `~/.spc/lib/engram_role_cache.py`

**Roles Supported:**
| Role | Query Focus | Use Case |
|------|-------------|----------|
| engram-dev | architecture, storage, scoring | Engram development |
| studioflow | rough_cut, audio markers | Video pipeline |
| ai-dev | pytorch, cuda, models | AI/ML development |
| gpu-specialist | cuda, memory, debugging | GPU optimization |
| ai-content | whisper, voice, generation | Content AI |
| scriptwriter | hooks, structure, tutorials | Video scripts |
| recording | workflow, audio, teleprompter | Recording prep |
| youtube-growth | algorithm, ctr, thumbnails | Channel growth |
| analytics | metrics, retention, monetization | Analytics |
| storage-manager | disk, organization, backup | Storage |
| quick-actions | tasks, quick, simple | Quick tasks |

**Output:** `~/.spc/projects/state/engram-roles/{role}.md`

### 3. Tab Initialization

**Trigger:** New Kitty tab with CLAUDE_TAB_ROLE
**Location:** `~/.spc/shell/claude-tab-integration.sh`

```bash
# Flow:
# 1. Tab-init script sets CLAUDE_TAB_ROLE
# 2. Sources claude-tab-integration.sh
# 3. Writes role to ~/.spc/projects/state/current_role (for MCP server)
# 4. Checks for role cache file
# 5. Exports ENGRAM_ROLE_CONTEXT environment variable
# 6. Displays memory summary
```

**Critical Design Note:** The MCP server runs as a subprocess spawned by Claude Code
and does NOT inherit shell environment variables. Tab-init writes the role to a file
that the MCP server reads directly.

### 4. Claude Session Init

**Trigger:** Claude session start
**Location:** `~/.claude/CLAUDE.md` (Session Init Protocol)

```markdown
# Session Init Protocol

1. Check $ENGRAM_ROLE_CONTEXT → read role-specific memories
2. Read ~/.spc/projects/state/engram_project_memories.md
3. Call engram_context(query="current work")
4. Announce role and loaded context
```

## Data Flow

### On Project Switch

```
proj studioflow
    │
    ▼
run_hooks() in proj
    │
    ├── 10-env.sh: Export SPC_PROJECT=studioflow
    │
    ├── 20-engram.sh:
    │   ├── Write engram_context.txt
    │   └── (async) Fetch project memories → engram_project_memories.md
    │
    ├── 30-kitty-title.sh: Update terminal title
    │
    ├── 40-claude-context.sh: Update Claude overlay symlink
    │
    └── 50-kitty-broadcast.sh: Notify other terminals
```

### On Tab Launch

```
ks w (launch workspace)
    │
    ├── Tab 1: channel-script.sh
    │   ├── CLAUDE_TAB_ROLE=scriptwriter
    │   ├── source claude-tab-integration.sh
    │   │   ├── Write "scriptwriter" to current_role file
    │   │   └── export ENGRAM_ROLE_CONTEXT=~/.spc/.../scriptwriter.md
    │   └── Display: "📚 Engram: scriptwriter (10 memories)"
    │
    ├── Tab 2: ai-main.sh
    │   ├── CLAUDE_TAB_ROLE=ai-dev
    │   └── ... (writes "ai-dev" to current_role)
    │
    └── Tab 3: resolve-studioflow.sh
        ├── CLAUDE_TAB_ROLE=studioflow
        └── ... (writes "studioflow" to current_role)
```

### On Claude Session Start

```
Claude starts in tab
    │
    ▼
Read Session Init Protocol from CLAUDE.md
    │
    ├── Check $ENGRAM_ROLE_CONTEXT
    │   └── If set: Read role cache file
    │
    ├── Check engram_project_memories.md
    │   └── If exists: Read project memories
    │
    ├── Call engram_context()
    │   └── Get additional relevant memories
    │
    └── Announce: "[ROLE: studioflow] | Project: studioflow | 10 memories"
```

## Configuration Files

### Role-Query Mapping

```python
# ~/.spc/lib/engram_role_cache.py
ROLE_QUERIES = {
    "engram-dev": [
        "engram architecture decisions storage scoring",
        "engram gotchas chromadb sqlite",
        "memory system design patterns",
    ],
    "studioflow": [
        "studioflow rough_cut architecture gotchas",
        "studioflow audio markers whisper",
        "studioflow resolve integration",
    ],
    # ... 9 more roles
}
```

### Health Check Integration

```bash
# proj doctor checks:
# - Engram database exists
# - ChromaDB vector store exists
# - Role caches generated
# - engram_context.txt updated recently
# - No recent hook failures
```

## Optimization Opportunities

### Implemented

1. **Pre-cached role context** - Memories fetched ahead of time
2. **Async project fetch** - Non-blocking memory retrieval on switch
3. **Role-specific filtering** - Each agent gets relevant memories only
4. **Health monitoring** - `proj doctor` validates integration
5. **File-based context passing** - MCP server reads role/project from files
6. **Role-aware engram_context()** - Auto-enhances queries with role + project
7. **Validation feedback loop** - Access logging tracks memory usage

### Key Design Decision: File-Based Context

The MCP server runs as a subprocess spawned by Claude Code. It does NOT inherit
shell environment variables like `CLAUDE_TAB_ROLE` or `SPC_PROJECT`.

**Solution:**
- Tab-init writes role to `~/.spc/projects/state/current_role`
- `proj` writes project to `~/.spc/active_project` (JSON)
- MCP server reads these files directly in `_get_context_from_files()`
- Query enhancement uses role/project names for semantic similarity (no hardcoded terms)

### Pending

1. **Memory decay** - Reduce confidence of unused memories
2. **Cross-role learning** - Share discoveries between related roles

## Troubleshooting

### No Engram Context in Claude

1. Check current_role file: `cat ~/.spc/projects/state/current_role`
2. Check active_project: `cat ~/.spc/active_project`
3. Check role cache exists: `ls ~/.spc/projects/state/engram-roles/`
4. Regenerate caches: `python ~/.spc/lib/engram_role_cache.py`
5. Run health check: `proj doctor`

### Stale Memories

1. Restart MCP server (Claude Code restart)
2. Regenerate role caches
3. Check hook logs: `tail ~/.spc/state/hooks.log`

### Missing Project Memories

1. Switch project: `proj <name>` (triggers refresh)
2. Check async job ran: `cat ~/.spc/projects/state/engram_project_memories.md`
3. Manual fetch: Run 20-engram.sh directly

## Success Metrics

| Metric | Before | Current | Target |
|--------|--------|---------|--------|
| Context auto-loaded | No | Yes | Yes |
| Role-specific memories | 0% | 70% | 90% |
| Generic content | 52% | ~40% | <20% |
| Health check coverage | 0 | 6 checks | 10 checks |
| Memory validation | Manual | Manual | Auto |

## Related Documents

- [CFS Architecture](~/.spc/docs/CFS-ARCHITECTURE.md)
- [Engram Optimization Plan](./engram-optimization-plan.md)
- [Global CLAUDE.md](~/.claude/CLAUDE.md)
