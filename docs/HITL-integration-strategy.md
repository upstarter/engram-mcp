# HITL Integration Strategy for Eric's AI System

## Executive Summary

Apply Human-in-the-Loop patterns across the entire ~/.spc, /mnt/dev, and AI ecosystem to:
1. Curate knowledge quality (not quantity)
2. Build learning loops between Claude and Eric
3. Prevent memory pollution while capturing valuable discoveries
4. Create calibration signals for AI decision-making

---

## Current State Assessment

### Implemented Improvements
| Feature | Status | Location |
|---------|--------|----------|
| Hybrid search (keyword + semantic) | ✅ Done | `storage.py:recall()` |
| Embedding upgrade (768d mpnet) | ✅ Done | `storage.py` |
| HITL confirmation for `engram_remember` | ✅ Done | `server.py` |
| 28 HITL research memories | ✅ Done | `human-in-the-loop.seed.md` |
| Ground truth validation suite | ✅ Done | `test_search_quality.py` |

### NOT Yet Implemented
| Feature | Designed In | Priority |
|---------|-------------|----------|
| Auto-entity extraction | `engram-autonomous-design.md` | High |
| Auto-relationship detection | `engram-autonomous-design.md` | High |
| Implicit validation (surface count) | `engram-autonomous-design.md` | Medium |
| Memory decay for unused memories | `engram-optimization-plan.md` | Medium |
| More seed data (dev, AI, preferences) | `seed-data-strategy.md` | High |
| Additional relationship types | `engram-graph-design-v2.md` | Low |
| Cross-role learning | `engram-optimization-plan.md` | Low |

---

## HITL Integration Points Across System

### 1. Claude Code Sessions (Primary)

**Current:** `engram_remember` with preview/confirmation
**Enhance with:**

```
PATTERN: Confidence-based routing
┌─────────────────────────────────────────────────────────┐
│ Importance ≥ 0.9: Always ask confirmation              │
│ Importance 0.6-0.9: Show preview, ask to confirm       │
│ Importance < 0.6: Auto-store with post-session review  │
└─────────────────────────────────────────────────────────┘
```

**Implementation:**
- Add `importance_threshold` to `~/.claude/CLAUDE.md` instructions
- High-stakes (decisions, architecture) = always ask
- Low-stakes (facts, minor preferences) = batch for review

### 2. Project Hooks (`~/.spc/project-hooks/`)

**Current:** `20-engram.sh` refreshes context on project switch
**Enhance with:**

```
PATTERN: Phase completion HITL checkpoint
When: `proj next` advances episode phase
Do: Show memories created during phase for batch validation
Why: Natural decision point, not interrupt-driven
```

**New hook: `90-phase-hitl.sh`**
```bash
#!/bin/bash
# On phase transition, show memories created since last phase for review
engram_memories_since_phase "$PREV_PHASE" | format_for_review
```

### 3. Tab-Init Scripts (`~/.spc/kitty/tab-init/`)

**Current:** Each role gets pre-loaded context
**Enhance with:**

```
PATTERN: Session kickoff HITL
When: New session starts (not resume)
Do: Show 3-5 most relevant memories, ask "focus on anything specific?"
Why: Builds engagement, prevents rubber-stamping
```

**Implementation:** Update `claude-tab-integration.sh`:
```bash
if [ "$SESSION_TYPE" = "new" ]; then
    echo "📋 Top memories for $ROLE:"
    engram_recall "$ROLE top priorities" --limit 3 --compact
    echo ""
    echo "Press Enter to continue, or type focus area: "
fi
```

### 4. `proj` Command Integration

**Current:** `proj context` shows engram memories
**Enhance with:**

```
PATTERN: Async HITL review command
Command: proj review
Action: Show memories created in last session for batch validation
Options: ✓ Validate │ ✗ Discard │ ✎ Edit │ ⏭ Skip
```

**New subcommand:**
```bash
proj review        # Review last session's memories
proj review --all  # Review all unvalidated memories
proj review --prune # Show candidates for deletion
```

### 5. Engram Bridge (`~/.spc/lib/engram_bridge.py`)

**Current:** Captures phase transitions and ideas
**Enhance with:**

```
PATTERN: Deferred HITL queue
When: Auto-captured memory (phase change, idea capture)
Do: Add to pending review queue instead of immediate store
Later: `proj review` processes queue with user input
```

**Implementation:**
- Add `~/.spc/projects/state/engram_pending.json`
- Bridge writes to queue, not directly to engram
- `proj review` processes queue

### 6. Seed File Loading (`~/.spc/engram-seeds/`)

**Current:** `load-seeds.py` bulk loads memories
**Enhance with:**

```
PATTERN: Seed validation before load
When: Running `load-seeds.py` on new seed file
Do: Show preview of what will be added, ask confirmation
Check: Duplicates, conflicts with existing memories
```

**Implementation:**
- Add `--preview` flag (default on for new seeds)
- Show similar existing memories for each seed
- Allow selective loading: "Load items 1,3,5-8"

---

## Feedback Loop Architecture

### Three-Layer Feedback System

```
┌──────────────────────────────────────────────────────────────┐
│                    LAYER 1: EXPLICIT                         │
│  User directly confirms/rejects memories during session      │
│  Signal: High quality, low volume                            │
│  Tools: engram_remember(confirmed=true), proj review         │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    LAYER 2: IMPLICIT                         │
│  System tracks memory usage patterns                         │
│  Signal: Medium quality, high volume                         │
│  Tools: access_log, surface_count, validation_count          │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    LAYER 3: CALIBRATION                      │
│  Periodic human review of AI-judged cases                    │
│  Signal: Ground truth for drift detection                    │
│  Tools: proj review --random, monthly audit                  │
└──────────────────────────────────────────────────────────────┘
```

### Metrics to Track

| Metric | Healthy Range | What It Tells Us |
|--------|---------------|------------------|
| Confirmation rate | 70-90% | Too high = rubber-stamping, too low = miscalibrated |
| Avg. session memories | 1-3 | More = possible pollution |
| Validation rate | 20-40% of stored | Memories being useful |
| Prune candidates | <10% of total | Memory hygiene |
| Review time | <2 sec/memory | User engaged, not fatigued |

---

## Implementation Roadmap

### Phase 1: Immediate (This Week)
1. ✅ HITL confirmation in `engram_remember` (DONE)
2. Add `proj review` command for batch validation
3. Update `~/.claude/CLAUDE.md` with confidence routing rules
4. Load remaining seed files (dev, AI-ML, preferences)

### Phase 2: Short-term (2 Weeks)
1. Add pending queue for auto-captured memories
2. Implement phase-transition checkpoints in `proj next`
3. Add session kickoff focus prompt in `claude-tab`
4. Create calibration dashboard (CLI-based)

### Phase 3: Medium-term (Month)
1. Implement implicit validation (surface_count tracking)
2. Add memory decay for never-accessed memories
3. Create monthly audit workflow
4. Cross-role learning for shared discoveries

---

## HITL Patterns Applied to Your Workflow

### YouTube Episode Workflow

```
Phase        │ HITL Checkpoint
─────────────┼─────────────────────────────────────────────
research     │ "Found X sources - store as pattern?"
scripting    │ "Script uses Y hook - validate pattern?"
recording    │ [Minimal - flow state, don't interrupt]
editing      │ "Discovered Z shortcut - save solution?"
publishing   │ "Title/thumb performed - save benchmark?"
```

### AI Development Workflow

```
Phase        │ HITL Checkpoint
─────────────┼─────────────────────────────────────────────
planning     │ "Architecture decision - store with reasoning?"
implementing │ [Auto-capture, batch review at end]
debugging    │ "Found fix for X - save solution?"
testing      │ [Auto-capture test patterns]
deploying    │ "Deployment config - save pattern?"
```

### Daily Review Ritual (3-5 minutes)

```bash
# Morning: Load context
proj context

# Evening: Review day's captures
proj review  # 3-5 memories max, batch approval

# Weekly: Calibration check
proj review --random 5  # Spot-check stored memories
```

---

## Key HITL Principles (From Research)

1. **3-5 daily HITL interactions is sustainable** - Don't over-ask
2. **Sub-2-second confirmation latency** - Keep it fast
3. **Correction rate <10% = well-calibrated** - Track this
4. **Non-binary options** - "Yes/Edit/Supersede/Discard"
5. **Show reasoning** - Why is Claude proposing this?
6. **Natural decision points** - Phase transitions, session end
7. **Batch similar items** - Group for efficient review
8. **Track downstream outcomes** - Did stored memory help later?

---

## Files to Modify

| File | Change |
|------|--------|
| `~/.claude/CLAUDE.md` | Add confidence routing rules |
| `~/.spc/bin/proj` | Add `review` subcommand |
| `~/.spc/lib/engram_bridge.py` | Add pending queue |
| `~/.spc/kitty/tab-init/*.sh` | Add session kickoff prompt |
| `~/.spc/project-hooks/on-switch.d/90-phase-hitl.sh` | NEW: Phase checkpoint |
| `/mnt/dev/ai/engram-mcp/engram/storage.py` | Add surface_count tracking |

---

## Success Criteria

After 30 days of HITL operation:
- [ ] Confirmation rate between 70-90%
- [ ] <3 new memories per session average
- [ ] >20% of memories have validation_count > 0
- [ ] <10% of memories flagged as prune candidates
- [ ] User reports memories are "mostly useful"
- [ ] No major "memory pollution" events
