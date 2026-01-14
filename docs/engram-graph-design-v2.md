# Engram Knowledge Graph v2 - Deep Design Analysis

## The Core Question

What graph structure would maximally enhance Claude's ability to help Eric:
1. Ship YouTube content consistently (monetization path)
2. Build AI products that create a content ↔ product flywheel
3. Overcome shiny object syndrome and execution bottlenecks
4. Make better decisions faster with accumulated wisdom

---

## Understanding Eric's Cognitive Landscape

### What Eric Struggles With
- **Completion over initiation** - starts many, finishes few
- **Context switching** - new ideas derail active work
- **Decision paralysis** - too many options, unclear tradeoffs
- **Lost learnings** - solves same problems repeatedly
- **Invisible progress** - can't see momentum building

### What Eric Excels At
- **Systems thinking** - builds infrastructure that scales
- **Technical depth** - understands AI/ML deeply
- **Vision** - sees connections between products and content
- **Tool building** - creates force multipliers

### The Insight
The graph shouldn't just store facts - it should **encode patterns of successful execution** and **surface them at decision points**.

---

## Relationship Type Analysis

### Current State: Only `mentions`
- Memory → Entity: "this memory mentions this entity"
- Flat, undifferentiated, no semantic meaning
- Can't answer: "what blocks this?" or "what caused this decision?"

### Proposed Relationship Categories

I've organized these into **5 relationship families** based on what cognitive operations they enable:

---

## Family 1: TEMPORAL (When/Sequence)

**Purpose:** Understand order of events, track evolution, find what's current vs stale.

| Relationship | From → To | Use Case |
|--------------|-----------|----------|
| `supersedes` | memory → memory | "This new decision replaces that old one" |
| `precedes` | memory → memory | "X happened before Y" |
| `evolved_from` | memory → memory | "This pattern evolved from that earlier pattern" |
| `active_during` | memory → episode | "This was true during EP001 production" |

**Why Critical for Eric:**
- Prevents acting on stale decisions
- Shows how thinking evolved (learning from past self)
- Enables "what was the context when I decided X?"

**Query Examples:**
- "What's the CURRENT decision about thumbnail style?" (follow supersedes chain)
- "How has my recording workflow evolved?" (evolved_from traversal)

---

## Family 2: CAUSAL (Why/Because)

**Purpose:** Capture reasoning chains, enable "why did I..." queries, learn from outcomes.

| Relationship | From → To | Use Case |
|--------------|-----------|----------|
| `caused_by` | outcome → decision/action | "This result happened because of that choice" |
| `motivated_by` | decision → philosophy/goal | "I chose this because of that principle" |
| `resulted_in` | action → outcome | "Doing X led to Y" |
| `blocked_by` | goal → blocker | "This goal is blocked by this obstacle" |
| `enabled_by` | achievement → enabler | "I could do this because of that" |

**Why Critical for Eric:**
- Surfaces WHY behind past decisions (faster future decisions)
- Connects principles to outcomes (validates philosophies)
- Identifies recurring blockers (shiny object → blocked_by → completion)

**Query Examples:**
- "Why did I choose this script structure?" (motivated_by traversal)
- "What outcomes resulted from rushing to record?" (resulted_in)
- "What keeps blocking my shipping?" (blocked_by aggregation)

---

## Family 3: STRUCTURAL (Part/Whole/Contains)

**Purpose:** Navigate hierarchies, understand scope, chunk work appropriately.

| Relationship | From → To | Use Case |
|--------------|-----------|----------|
| `part_of` | component → whole | "Scripting is part_of episode production" |
| `contains` | whole → component | "Episode contains script, teleprompter, raw footage" |
| `instance_of` | specific → general | "EP001 is instance_of episode" |
| `phase_of` | phase → workflow | "Recording is phase_of channel production" |
| `version_of` | variant → original | "This is v2 of that approach" |

**Why Critical for Eric:**
- Enables proper scoping ("what's the smallest shippable piece?")
- Shows where current work fits in bigger picture
- Helps break down overwhelming tasks

**Query Examples:**
- "What are all the parts of publishing an episode?"
- "What phase am I in and what remains?"

---

## Family 4: DEPENDENCY (Requires/Enables/Blocks)

**Purpose:** Critical path analysis, unblock work, sequence tasks correctly.

| Relationship | From → To | Use Case |
|--------------|-----------|----------|
| `requires` | task → prerequisite | "Recording requires teleprompter" |
| `enables` | enabler → enabled | "Completing script enables teleprompter creation" |
| `blocks` | blocker → blocked | "Missing audio gear blocks recording" |
| `conflicts_with` | item → item | "This approach conflicts with that principle" |
| `depends_on` | downstream → upstream | "Thumbnail depends_on having recording footage" |

**Why Critical for Eric:**
- Prevents skipping prerequisites (no recording without script!)
- Shows what completing X unlocks
- Identifies true blockers vs excuses

**Query Examples:**
- "What's blocking EP001 from shipping?"
- "What does completing the script enable?"
- "Are any of my active decisions in conflict?"

---

## Family 5: SEMANTIC (Similarity/Relevance/Association)

**Purpose:** Find related knowledge, surface relevant context, consolidate duplicates.

| Relationship | From → To | Use Case |
|--------------|-----------|----------|
| `similar_to` | memory → memory | "These two memories say similar things" (consolidation candidates) |
| `related_to` | entity → entity | "These concepts are related" |
| `example_of` | specific → pattern | "This specific fix is example_of this general pattern" |
| `contradicts` | memory → memory | "These two memories conflict" |
| `reinforces` | memory → memory | "This memory reinforces/validates that one" |
| `applies_to` | pattern → context | "This pattern applies to this project/domain" |

**Why Critical for Eric:**
- Surfaces relevant past experience automatically
- Identifies contradictions before they cause problems
- Shows when patterns are being validated repeatedly

**Query Examples:**
- "What patterns apply to my current recording session?"
- "Do I have any contradictory memories about X?"
- "What memories reinforce this decision?"

---

## Special Relationship: `mentions` (Keep but Downgrade)

Keep `mentions` as a **weak/implicit** relationship that's auto-extracted, but treat the 5 families above as **strong/explicit** relationships that carry more weight in retrieval.

---

## Entity Type Refinements

### Current Entity Types
- projects, tools, concepts, episode

### Proposed Entity Types

| Type | Purpose | Examples |
|------|---------|----------|
| `project` | Major work streams | CHANNEL, studioflow, avatar-factory |
| `episode` | Content units | EP001, EP002 |
| `phase` | Workflow stages | research, scripting, recording, editing, publishing |
| `tool` | Software/utilities | claude, resolve, kitty, proj, sf |
| `concept` | Abstract ideas | MVP, shipping, retention, hook |
| `person` | People | Eric, collaborators |
| `goal` | Desired outcomes | "monetization", "consistent publishing" |
| `blocker` | Obstacles | "shiny object syndrome", "perfectionism" |
| `pattern` | Reusable approaches | "PAS script structure", "face+emotion thumbnail" |
| `decision_point` | Recurring choice situations | "new idea arrives", "stuck on task" |

### New: Goal and Blocker as First-Class Entities

This is crucial. Eric's blockers (shiny object syndrome, perfectionism, scope creep) should be **explicit nodes** that memories can connect to. Then we can:
- Track what triggers blockers
- Track what overcomes blockers
- Surface blocker-awareness at decision points

---

## Node Attributes Enrichment

### Memory Node Attributes

```json
{
  "id": "mem_xxx",
  "node_type": "memory",
  "memory_type": "decision|pattern|fact|solution|philosophy|preference",
  "content": "...",
  "project": "CHANNEL",

  // NEW ATTRIBUTES
  "status": "active|superseded|archived|experimental",
  "confidence": 0.0-1.0,  // How validated is this?
  "impact": "high|medium|low",  // How important when surfaced?
  "last_validated": "2026-01-10",  // When was this confirmed still true?
  "validation_count": 5,  // How many times has this proven useful?
  "domain": ["channel", "recording"],  // What contexts does this apply to?
  "trigger_context": "when starting recording session"  // When to surface this
}
```

### Entity Node Attributes

```json
{
  "id": "entity:goal:monetization",
  "node_type": "entity",
  "entity_type": "goal",
  "name": "YouTube Monetization",

  // NEW ATTRIBUTES
  "status": "active|achieved|abandoned",
  "priority": "P0|P1|P2",
  "target_date": "2027-06",
  "progress": 0.15,
  "blockers": ["entity:blocker:shiny-object-syndrome"]
}
```

---

## Query Patterns This Enables

### 1. Decision Support
"I'm about to start a new project idea..."
→ Traverse: idea → `triggers` → blocker:shiny-object → `blocked_by` → all memories about shiny object defense
→ Surface: "You have 5 memories about this pattern. Current active project is EP001 at 45%. Want to capture this idea and return to EP001?"

### 2. Workflow Guidance
"I'm in the recording phase..."
→ Traverse: phase:recording → `requires` → prerequisites
→ Check: Are all prerequisites satisfied?
→ Surface: "Recording requires: ✓ script, ✓ teleprompter, ✗ lighting setup"

### 3. Learning Loops
"That recording session went well!"
→ Create: outcome node with `resulted_from` → decisions made
→ Later: "What made past recordings successful?" → traverse `resulted_from` backwards

### 4. Contradiction Detection
Before storing new memory:
→ Check: Does this `contradict` any existing active memory?
→ If yes: "This conflicts with [existing memory]. Which is correct? Supersede or keep both?"

### 5. Pattern Validation
When pattern is applied successfully:
→ Add `reinforces` edge from outcome to pattern
→ Increment pattern's validation_count
→ Over time: high-validation patterns surface more prominently

### 6. Blocker Awareness
At session start or when new idea mentioned:
→ Check: Active blockers for current goal
→ Traverse: blocker → `blocks` → goals, blocker → `triggered_by` → situations
→ Surface: "Watch out: 'new shiny idea' is a known trigger for your 'shiny object syndrome' blocker"

---

## Edge Attributes

Edges should carry metadata too:

```json
{
  "source": "mem_xxx",
  "target": "entity:blocker:shiny-object",
  "edge_type": "triggered_by",

  // NEW ATTRIBUTES
  "strength": 0.9,  // How strong is this relationship?
  "confidence": 0.8,  // How confident are we this is accurate?
  "created_at": "2026-01-10",
  "created_by": "claude|eric|auto",  // Who created this edge?
  "evidence": "mem_yyy"  // What memory supports this edge?
}
```

---

## Priority Implementation Order

Based on impact for Eric's success:

### Phase 1: Foundation (Immediate)
1. `supersedes` - Stop acting on stale info
2. `requires` / `enables` - Workflow dependencies
3. `blocked_by` - Surface blockers
4. Add `status` attribute to memories (active/superseded)

### Phase 2: Causality (Soon)
5. `motivated_by` - Connect decisions to principles
6. `resulted_in` - Track outcomes
7. `triggered_by` - Blocker triggers
8. Add `goal` and `blocker` entity types

### Phase 3: Learning (Later)
9. `reinforces` / `contradicts` - Validation loops
10. `evolved_from` - Track thinking evolution
11. `similar_to` - Consolidation support
12. Add confidence/validation_count attributes

### Phase 4: Advanced (Future)
13. `conflicts_with` - Detect inconsistencies
14. `applies_to` - Context-aware retrieval
15. `example_of` - Pattern instantiation
16. Full edge attributes with strength/confidence

---

## The Meta-Pattern

The graph should encode **Eric's execution system**, not just facts:

```
GOAL: Ship EP001
  ├── blocked_by: perfectionism (blocker)
  │     └── overcome_by: "good enough to ship" (philosophy)
  ├── requires: research phase (completed)
  ├── requires: script phase (completed)
  ├── requires: teleprompter phase (completed)
  ├── requires: recording phase (IN PROGRESS)
  │     ├── requires: lighting setup
  │     ├── requires: audio check
  │     └── enables: editing phase
  └── next_phase: editing
        └── enables: publishing
              └── enables: GOAL:monetization
```

This structure lets Claude:
1. See exactly where Eric is
2. Know what's blocking progress
3. Know what philosophies counter the blockers
4. Know what completing current phase unlocks
5. Connect current work to ultimate goals

---

## Summary: The 15 Relationships

| Family | Relationships | Purpose |
|--------|--------------|---------|
| **Temporal** | supersedes, precedes, evolved_from, active_during | Track time/currency |
| **Causal** | caused_by, motivated_by, resulted_in, blocked_by, enabled_by | Understand why |
| **Structural** | part_of, contains, instance_of, phase_of, version_of | Navigate hierarchy |
| **Dependency** | requires, enables, blocks, conflicts_with, depends_on | Critical path |
| **Semantic** | similar_to, related_to, example_of, contradicts, reinforces, applies_to | Find relevance |

Plus enhanced `mentions` as weak/implicit.

---

## Final Insight

The optimal graph isn't about storing more information - it's about storing **the right relationships** that let Claude:

1. **Prevent mistakes** (contradicts, conflicts_with, blocked_by)
2. **Accelerate decisions** (motivated_by, resulted_in, supersedes)
3. **Maintain focus** (requires, enables, part_of, blocked_by)
4. **Learn and improve** (reinforces, evolved_from, validation_count)
5. **Surface relevant context** (applies_to, similar_to, trigger_context)

The graph becomes Eric's **externalized executive function** - the part of the brain that tracks priorities, maintains focus, learns from outcomes, and prevents repeated mistakes.
