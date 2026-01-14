# Engram Autonomous Usage Design

## The Problem

Claude currently:
- Remembers too much (noise)
- Doesn't create entities unless told
- Doesn't link relationships unless told
- Doesn't validate useful memories

We need: **Judicious autonomous operation** - Claude should automatically:
1. Create high-value memories (not everything)
2. Extract and create entities when they're significant
3. Link relationships when they're meaningful
4. Validate memories when they prove useful
5. Skip low-value storage entirely

---

## Solution: Smart Remember with Auto-Extraction

### Option A: Enhance `engram_remember` to auto-extract

Instead of separate tools, make `engram_remember` smarter:

```python
def remember(content, auto_extract=True, auto_link=True):
    # 1. GATE: Should this even be stored?
    if not passes_value_gate(content):
        return {"status": "skipped", "reason": "low_value"}

    # 2. Store the memory
    memory_id = store_memory(content)

    # 3. Auto-extract significant entities
    if auto_extract:
        entities = extract_significant_entities(content)
        for entity in entities:
            if is_first_class_entity(entity):  # goal, blocker, decision
                create_entity_if_not_exists(entity)

    # 4. Auto-detect relationships
    if auto_link:
        relationships = detect_relationships(content, memory_id)
        for rel in relationships:
            add_relationship(rel)

    return memory_id
```

### Option B: Value Gate in CLAUDE.md Instructions

Add to global CLAUDE.md:

```markdown
### Engram Value Gate (CRITICAL)

Before calling engram_remember, ask:

1. **Is this ACTIONABLE?** Will future Claude use this to make decisions?
2. **Is this DURABLE?** Will this still be true in 1 week? 1 month?
3. **Is this UNIQUE?** Is this already captured elsewhere?

SKIP storing if:
- It's a transient fact (today's date, current file being edited)
- It's easily re-discoverable (file paths, command syntax)
- It's session-specific context (what we just discussed)
- It's a duplicate of existing memory

STORE if:
- Decision with reasoning (WHY not just WHAT)
- Pattern that worked (reusable approach)
- User preference (style, workflow, tools)
- Solution to problem (fix for future reference)
- Blocker identified (something that stops progress)
- Goal clarified (what success looks like)
```

---

## Recommended Approach: Hybrid

### 1. Value Gate in Instructions (CLAUDE.md)

Add explicit guidance on when to remember vs skip.

### 2. Auto-Entity Extraction in Code

When storing a memory that mentions:
- A goal → auto-create goal entity if doesn't exist
- A blocker → auto-create blocker entity
- A phase → link to workflow

### 3. Auto-Relationship Detection

Pattern matching in `remember()`:
- "because" / "motivated by" → `motivated_by` relationship
- "blocks" / "prevents" → `blocked_by` relationship
- "requires" / "needs" → `requires` relationship
- "supersedes" / "replaces" / "instead of" → `supersedes` relationship
- "after" / "then" / "enables" → `enables` relationship

### 4. Implicit Validation

When Claude uses a memory from `engram_recall` and it helps:
- Automatically call `validate_memory()` on that memory
- No explicit tool call needed

---

## Implementation Plan

### Phase 1: Value Gate (Instructions Only)

Update `~/.claude/CLAUDE.md` with explicit value criteria.

**Pros:** No code changes, immediate effect
**Cons:** Relies on Claude following instructions

### Phase 2: Auto-Extraction (Code Change)

Modify `remember()` to auto-detect and create entities.

```python
# In storage.py remember()

# Auto-create goal entities
if "goal:" in content.lower() or "objective:" in content.lower():
    goals = extract_goals(content)
    for goal in goals:
        self.add_entity("goal", goal)
        self.add_relationship(memory_id, f"entity:goal:{goal}", "motivated_by")

# Auto-create blocker entities
blocker_patterns = ["blocks", "prevents", "obstacle", "blocker", "stuck"]
if any(p in content.lower() for p in blocker_patterns):
    blockers = extract_blockers(content)
    for blocker in blockers:
        self.add_entity("blocker", blocker)
```

### Phase 3: Implicit Validation (Code Change)

In `recall()`, when memories are returned, mark them as "surfaced".
If the same memory is surfaced multiple times → auto-validate.

```python
def recall(query, ...):
    memories = search(query)

    for mem in memories:
        # Track that this memory was surfaced
        self.increment_surface_count(mem.id)

        # Auto-validate frequently surfaced memories
        if mem.surface_count > 3:
            self.validate_memory(mem.id)

    return memories
```

---

## Updated Tool Strategy

### Keep These Tools (Claude Uses Explicitly)
- `engram_remember` - But with stricter value gate
- `engram_recall` - Search
- `engram_context` - Session start
- `engram_graph` - Query insights (blockers, requirements)

### Make These Automatic (No Explicit Calls)
- `engram_entity` → Auto-created during remember
- `engram_link` → Auto-detected during remember
- `engram_validate` → Auto-triggered by repeated surfacing

### Remove/Deprecate
- `engram_consolidate` → Run as background maintenance, not user-triggered

---

## Value Gate Criteria (Final)

### ALWAYS Store
| Type | Example | Why |
|------|---------|-----|
| Decision + Reasoning | "Chose X because Y" | Future decisions |
| User Preference | "Eric prefers Z" | Personalization |
| Working Solution | "Fixed by doing X" | Problem solving |
| Validated Pattern | "This approach works for Y" | Reusable |
| Blocker Identified | "X blocks progress on Y" | Awareness |

### NEVER Store
| Type | Example | Why |
|------|---------|-----|
| Transient State | "Currently editing file X" | Session-only |
| Command Syntax | "Use `git add .`" | Easily googled |
| Obvious Facts | "Python is a language" | No value |
| Duplicates | Same info in different words | Noise |
| Speculative | "Maybe we should try X" | Not validated |

### MAYBE Store (Ask or Skip)
| Type | Default | Override |
|------|---------|----------|
| Configuration | Skip | Store if custom/non-obvious |
| File Paths | Skip | Store if repeatedly needed |
| Error Messages | Skip | Store if solution found |

---

## Summary

**The fix is primarily in INSTRUCTIONS, not code.**

1. Add Value Gate to `~/.claude/CLAUDE.md` (immediate)
2. Make entity/link extraction automatic in code (soon)
3. Make validation implicit (later)

This way Claude autonomously:
- Filters low-value memories OUT
- Extracts entities automatically
- Links relationships automatically
- Validates useful memories automatically

No more needing to tell Claude "use engram_link" - it just happens when appropriate.
