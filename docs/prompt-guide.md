# Engram Prompt Guide

## How to Talk to Claude for Optimal Memory Usage

This guide shows you how to structure your prompts so Claude automatically uses engram tools effectively - without you having to ask.

---

## The Core Principle

**Claude triggers engram tools based on signal words and prompt structure.**

| Signal | Claude's Response |
|--------|-------------------|
| "I've decided..." | → `engram_remember` (decision) |
| "Remember that..." | → `engram_remember` (fact/preference) |
| "What do you know about..." | → `engram_recall` |
| "My goal is..." | → `engram_entity` (goal) + `engram_remember` |
| "...is blocking..." | → `engram_entity` (blocker) + `engram_link` |

---

## Tool Trigger Patterns

### 1. `engram_remember` - Storing Memories

**Trigger phrases that signal "store this":**

```
# Decisions (type: decision, importance: 0.8-0.9)
"I've decided to use X because Y"
"We're going with X over Y because..."
"The decision is to..."
"Let's go with X - the reason is..."

# Preferences (type: preference, importance: 0.7)
"I prefer X over Y"
"Always use X for this"
"I like it when..."
"My preference is..."

# Solutions (type: solution, importance: 0.8)
"Fixed it by..."
"The solution was..."
"This worked: ..."
"Solved by..."

# Patterns (type: pattern, importance: 0.7-0.8)
"This approach works well for..."
"The pattern is..."
"When X happens, do Y"
"A good rule of thumb is..."

# Facts (type: fact, importance: 0.5-0.7)
"For the record, X is Y"
"Note that..."
"Important: ..."
"Remember that..."
```

**Example prompts:**

```
❌ Weak: "We talked about using TypeScript"
✅ Strong: "I've decided to use TypeScript for all new projects because it catches bugs early"

❌ Weak: "The bug is fixed now"
✅ Strong: "Fixed the CUDA OOM error by setting PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512"

❌ Weak: "I like dark mode"
✅ Strong: "I prefer dark mode in all editors - always configure this first"
```

---

### 2. `engram_recall` - Searching Memories

**Trigger phrases that signal "search for this":**

```
"What do you know about..."
"Have we dealt with X before?"
"What was the decision on..."
"How did we solve X last time?"
"What's my preference for..."
"Any past experience with..."
"Check if there's anything on..."
```

**Example prompts:**

```
❌ Weak: "How do I fix CUDA errors?"
✅ Strong: "Have we solved CUDA OOM errors before? What worked?"

❌ Weak: "What language should I use?"
✅ Strong: "What's my preference for programming languages in new projects?"

❌ Weak: "Help me with the API"
✅ Strong: "What do you know about my API design decisions?"
```

---

### 3. `engram_context` - Session Start

**Trigger phrases (usually automatic at session start):**

```
"Let's continue working on X"
"Back to the Y project"
"What's the context for..."
"Remind me where we left off"
"ec" (shortcut)
```

**Best practice:** Claude should call this automatically. You rarely need to trigger it manually.

---

### 4. `engram_entity` - Creating Goals/Blockers/Patterns

**Goal triggers:**

```
"My goal is to..."
"The objective is..."
"We're trying to achieve..."
"Success looks like..."
"The target is..."
"Priority: ..."
```

**Blocker triggers:**

```
"X is blocking Y"
"I can't progress because..."
"The obstacle is..."
"What's stopping me is..."
"The blocker here is..."
"I'm stuck on..."
```

**Pattern triggers:**

```
"This approach works: ..."
"The proven method is..."
"When X, always do Y"
"The winning formula is..."
```

**Example prompts:**

```
❌ Weak: "I want to make money on YouTube"
✅ Strong: "My P0 goal is YouTube monetization - 4000 watch hours and 1000 subscribers"

❌ Weak: "I get distracted"
✅ Strong: "Shiny object syndrome is blocking my goal of consistent publishing"

❌ Weak: "Thumbnails with faces work"
✅ Strong: "Proven pattern: thumbnails with face + emotion + 3 words get higher CTR"
```

---

### 5. `engram_link` - Creating Relationships

**Relationship trigger phrases:**

```
# blocked_by
"X blocks Y"
"Y is blocked by X"
"Can't do Y until X"

# motivated_by
"I chose X because of my goal to Y"
"This decision supports..."
"The reason is tied to..."

# requires
"X requires Y first"
"Before X, we need Y"
"X depends on Y"

# supersedes
"X replaces Y"
"Instead of Y, now we do X"
"Update: X (not Y anymore)"

# enables
"Once X is done, Y becomes possible"
"X unlocks Y"
"Completing X enables Y"
```

**Example prompts:**

```
❌ Weak: "I can't publish because I keep changing topics"
✅ Strong: "Shiny object syndrome blocks my consistent publishing goal"

❌ Weak: "I chose SQLite"
✅ Strong: "I chose SQLite because my goal is MVP simplicity - no server management"

❌ Weak: "Now I use Cursor instead of VSCode"
✅ Strong: "Update: Cursor replaces VSCode as my primary editor"
```

---

### 6. `engram_validate` - Reinforcing Useful Memories

**Trigger phrases:**

```
"That memory was helpful"
"Good recall - that worked"
"Yes, that's exactly what I needed"
"That solution worked again"
```

**Claude should auto-validate** when a recalled memory leads to success. You can also be explicit:

```
✅ "That CUDA fix you recalled - validate it, it worked again"
```

---

### 7. `engram_graph` - Querying Relationships

**Trigger phrases:**

```
# Blockers
"What's blocking [goal]?"
"Why can't I achieve [goal]?"
"Show blockers for..."

# Requirements
"What does [phase] require?"
"What are the prerequisites for..."
"What do I need before..."

# Contradictions
"Are there any conflicting memories about X?"
"Check for contradictions on..."

# Hub entities
"What are the most connected concepts?"
"What's central to my work?"
```

---

## Composite Prompt Patterns

### The "Decision + Rationale" Pattern

```
"I've decided to [DECISION] because [REASONING].
This supports my goal of [GOAL]."
```

**Triggers:**
- `engram_remember` (decision, importance: 0.8)
- `engram_link` (motivated_by → goal)

**Example:**
```
"I've decided to use SQLite instead of Postgres because I want MVP simplicity.
This supports my goal of shipping fast."
```

---

### The "Blocker Discovery" Pattern

```
"I realized [BLOCKER] is blocking my [GOAL].
It gets triggered when [CONTEXT]."
```

**Triggers:**
- `engram_entity` (blocker)
- `engram_link` (blocks → goal)
- `engram_remember` (fact about trigger context)

**Example:**
```
"I realized shiny object syndrome is blocking my consistent publishing goal.
It gets triggered when I see cool new AI tools on Twitter."
```

---

### The "Solution Found" Pattern

```
"Fixed [PROBLEM] by [SOLUTION].
Root cause was [CAUSE]."
```

**Triggers:**
- `engram_remember` (solution, importance: 0.8)

**Example:**
```
"Fixed CUDA OOM by setting max_split_size_mb:512.
Root cause was PyTorch memory fragmentation on long batches."
```

---

### The "Pattern Validated" Pattern

```
"Confirmed that [APPROACH] works for [CONTEXT].
Used it on [SPECIFIC CASE] and got [RESULT]."
```

**Triggers:**
- `engram_remember` (pattern, importance: 0.8)
- `engram_validate` (if updating existing pattern)

**Example:**
```
"Confirmed that PAS structure works for tutorial intros.
Used it on the MCP server video and retention jumped 20%."
```

---

### The "Update/Supersede" Pattern

```
"Update: [NEW INFO] replaces [OLD INFO].
Changed because [REASON]."
```

**Triggers:**
- `engram_remember` with check_conflicts=true
- `engram_link` (supersedes → old memory)

**Example:**
```
"Update: Cursor replaces VSCode as my primary editor.
Changed because AI integration is better."
```

---

### The "Context Request" Pattern

```
"What do you know about [TOPIC]?
Specifically, any [DECISIONS/PREFERENCES/SOLUTIONS] related to [ASPECT]?"
```

**Triggers:**
- `engram_recall` with type filter

**Example:**
```
"What do you know about my video production workflow?
Specifically, any decisions about thumbnail design?"
```

---

## Daily Workflow Prompts

### Morning/Session Start

```
"Back to work on [PROJECT].
ec"
```

Claude will call `engram_context` and load relevant memories.

---

### After Making a Decision

```
"I've decided: [DECISION].
Reasoning: [WHY].
This connects to my [GOAL/BLOCKER]."
```

---

### After Solving a Problem

```
"Solved: [PROBLEM] → [SOLUTION].
This might help with [FUTURE CONTEXT]."
```

---

### After Discovering a Blocker

```
"Blocker found: [BLOCKER] is blocking [GOAL].
Triggered by [CONTEXT]."
```

---

### End of Session

```
"Good stopping point. Key takeaways:
1. [DECISION/SOLUTION/PATTERN]
2. [DECISION/SOLUTION/PATTERN]"
```

---

## Anti-Patterns (What NOT to Say)

| Don't Say | Why | Say Instead |
|-----------|-----|-------------|
| "Remember everything from today" | Too vague, creates noise | "Key decision today: [X] because [Y]" |
| "Save this" | No context | "Remember this solution: [X] for [context]" |
| "Just in case, note that X" | Low value, speculative | Only store after validated |
| "I might use X later" | Speculative | Store when you actually decide |
| "We discussed X" | Session context, ephemeral | "Decision: X because Y" |

---

## Quick Reference Card

| Want Claude To... | Say... |
|-------------------|--------|
| Store a decision | "I've decided [X] because [Y]" |
| Store a solution | "Fixed [X] by [Y]" |
| Store a preference | "I prefer [X] over [Y]" |
| Store a pattern | "[Approach] works for [context]" |
| Search memories | "What do you know about [X]?" |
| Create a goal | "My goal is [X]" |
| Create a blocker | "[X] is blocking [goal]" |
| Link entities | "[X] blocks/enables/requires [Y]" |
| Update old info | "Update: [new] replaces [old]" |
| Get context | "ec" or start new session |
| Check blockers | "What's blocking [goal]?" |
| Validate memory | "That worked - good recall" |

---

## Importance Scoring Heuristics

Claude will auto-assign importance, but you can override:

```
"Important (0.9): [content]"
"Critical decision: [content]"
"Minor note: [content]"  (→ 0.5)
```

| Keyword | Importance |
|---------|------------|
| "Critical", "P0", "Core" | 0.9 |
| "Important", "Key" | 0.8 |
| "Useful", "Good to know" | 0.6-0.7 |
| "Minor", "FYI" | 0.5 |
| "Maybe", "Might" | 0.3 (probably skip) |

---

## Summary

**The formula for optimal engram prompts:**

```
[ACTION VERB] + [SPECIFIC CONTENT] + [CONTEXT/REASONING]
```

Examples:
- "**Decided** to **use TypeScript** because **type safety prevents runtime bugs**"
- "**Fixed** **CUDA OOM** by **setting max_split_size_mb:512**"
- "**Shiny object syndrome** is **blocking** my **consistent publishing goal**"

Claude will parse these structures and autonomously call the right engram tools with appropriate types, importance, and relationships.
