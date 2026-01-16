# Engram Memory Architecture Roadmap

## The Core Problem

**Research finding:** Systems that store everything then prune performed **10% WORSE than no memory at all.**

Current engram stores memories on request, then hopes access patterns reveal quality. This is backwards. Quality must be enforced at **formation time**, not after pollution occurs.

---

## Current State (v1)

### What Works ✓
- SQLite + ChromaDB hybrid (semantic + structured)
- Role affinity (15% boost for same-role memories)
- Graph relationships (entities, links)
- Access tracking (`access_count`, `surface_count`)
- Consolidation candidates detection
- Temporal decay (30-day half-life)

### What's Missing ✗
- **Quality gate at formation** - anything can be stored
- **Working memory layer** - no ephemeral buffer
- **Adaptive forgetting** - fixed decay for all memories
- **Trust scoring** - no outcome tracking
- **Agent isolation** - weak 15% boost insufficient
- **Automatic dedup** - opt-in only

---

## Architecture Improvements

### Phase 1: Quality Gate (HIGH PRIORITY)

**Goal:** Reject low-value content BEFORE it enters the database.

**Implementation:**

```python
# Add to storage.py

def quality_gate(self, content: str, memory_type: str) -> dict:
    """
    Pre-storage quality check.
    Returns: {pass: bool, score: float, reason: str, suggestion: str}
    """
    result = {"pass": True, "score": 1.0, "reason": "", "suggestion": ""}

    # Gate 1: Minimum length (5+ words)
    word_count = len(content.split())
    if word_count < 5:
        return {
            "pass": False,
            "score": 0.1,
            "reason": "Too short",
            "suggestion": "Memory should be at least 5 words with actionable content"
        }

    # Gate 2: Semantic novelty (reject near-duplicates)
    similar = self.recall(content, limit=1, threshold=0.0)
    if similar and similar[0]["similarity"] > 0.92:
        return {
            "pass": False,
            "score": 0.2,
            "reason": f"Near-duplicate of existing memory",
            "suggestion": f"Similar memory exists: {similar[0]['id'][:20]}... Consider updating instead."
        }

    # Gate 3: Research/speculation detection
    speculation_signals = [
        content.lower().startswith("i recommend"),
        content.lower().startswith("i suggest"),
        content.lower().startswith("we could"),
        content.lower().startswith("consider using"),
        "research complete" in content.lower() and "recommend" in content.lower(),
    ]
    if any(speculation_signals):
        return {
            "pass": False,
            "score": 0.3,
            "reason": "Appears to be recommendation/speculation, not validated knowledge",
            "suggestion": "Wait until implemented/tested before storing. Keep in chat or plan files."
        }

    # Gate 4: Actionability check (for solutions/patterns)
    if memory_type in ("solution", "pattern"):
        action_words = ["use", "run", "set", "add", "fix", "enable", "configure", "install", "create"]
        has_action = any(word in content.lower() for word in action_words)
        if not has_action and word_count < 20:
            result["score"] *= 0.7
            result["reason"] = "Low actionability for solution/pattern type"

    # Gate 5: Information density (penalize vague content)
    vague_phrases = ["something like", "maybe", "probably", "i think", "not sure"]
    vague_count = sum(1 for phrase in vague_phrases if phrase in content.lower())
    if vague_count >= 2:
        return {
            "pass": False,
            "score": 0.4,
            "reason": "Too vague/uncertain",
            "suggestion": "Memory should contain validated facts, not speculation"
        }

    return result
```

**Integration in server.py:**

```python
# In handle_tool_call for engram_remember:

# Run quality gate BEFORE storing
gate_result = store.quality_gate(content, memory_type)

if not gate_result["pass"]:
    # Return rejection to user with explanation
    return {
        "content": [
            TextContent(
                type="text",
                text=f"❌ Memory rejected: {gate_result['reason']}\n\n"
                     f"💡 Suggestion: {gate_result['suggestion']}\n\n"
                     f"Score: {gate_result['score']:.1f}/1.0\n\n"
                     f"To override, use `force=true` parameter."
            )
        ]
    }

# If passed, proceed with storage
```

**Add `force` parameter** to `engram_remember` tool schema for overriding gate.

---

### Phase 2: Working Memory Layer (HIGH PRIORITY)

**Goal:** Ephemeral buffer for session context that auto-promotes to long-term.

**Concept:**
- Working memory = in-memory, fast, session-scoped
- Long-term memory = SQLite/ChromaDB, persistent
- Auto-promotion: If working memory item surfaces 2+ times in 24hrs → promote

**Implementation:**

```python
# Add to storage.py

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class WorkingMemoryItem:
    content: str
    memory_type: str
    importance: float
    created_at: datetime
    surface_count: int = 0
    project: str = None
    source_role: str = None

class WorkingMemory:
    """
    Short-term memory buffer. Items here are ephemeral unless promoted.
    """
    def __init__(self, capacity: int = 50, promotion_threshold: int = 2):
        self.buffer: dict[str, WorkingMemoryItem] = {}  # keyed by content hash
        self.capacity = capacity
        self.promotion_threshold = promotion_threshold
        self.promotion_window = timedelta(hours=24)

    def add(self, content: str, memory_type: str = "fact",
            importance: float = 0.5, project: str = None,
            source_role: str = None) -> str:
        """Add to working memory. Returns item ID."""
        import hashlib
        item_id = f"wm_{hashlib.md5(content.encode()).hexdigest()[:12]}"

        # If at capacity, evict oldest
        if len(self.buffer) >= self.capacity:
            oldest_id = min(self.buffer, key=lambda k: self.buffer[k].created_at)
            del self.buffer[oldest_id]

        self.buffer[item_id] = WorkingMemoryItem(
            content=content,
            memory_type=memory_type,
            importance=importance,
            created_at=datetime.now(),
            project=project,
            source_role=source_role,
        )
        return item_id

    def surface(self, item_id: str) -> WorkingMemoryItem | None:
        """Mark item as surfaced. Returns item if promotion threshold reached."""
        if item_id not in self.buffer:
            return None

        item = self.buffer[item_id]
        item.surface_count += 1

        # Check promotion criteria
        if item.surface_count >= self.promotion_threshold:
            age = datetime.now() - item.created_at
            if age <= self.promotion_window:
                return item  # Ready for promotion

        return None

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Quick search of working memory (keyword-based, fast)."""
        results = []
        query_lower = query.lower()

        for item_id, item in self.buffer.items():
            if query_lower in item.content.lower():
                results.append({
                    "id": item_id,
                    "content": item.content,
                    "memory_type": item.memory_type,
                    "importance": item.importance,
                    "surface_count": item.surface_count,
                    "source": "working_memory",
                })

        return sorted(results, key=lambda x: -x["surface_count"])[:limit]

    def clear_expired(self, max_age: timedelta = timedelta(hours=24)):
        """Remove items older than max_age that weren't promoted."""
        now = datetime.now()
        expired = [
            item_id for item_id, item in self.buffer.items()
            if now - item.created_at > max_age
        ]
        for item_id in expired:
            del self.buffer[item_id]
```

**Integration:**

```python
# In MemoryStore.__init__:
self.working_memory = WorkingMemory(capacity=50, promotion_threshold=2)

# In recall():
# First check working memory (fast)
wm_results = self.working_memory.search(query, limit=3)

# Then check long-term (semantic search)
lt_results = self._recall_from_chromadb(query, limit=limit)

# Merge results, working memory items marked
combined = wm_results + lt_results

# Check for promotion candidates
for wm_item in wm_results:
    promoted = self.working_memory.surface(wm_item["id"])
    if promoted:
        # Auto-promote to long-term
        self.remember(
            promoted.content,
            memory_type=promoted.memory_type,
            importance=promoted.importance * 1.1,  # Boost for validation
            project=promoted.project,
            source_role=promoted.source_role,
        )
```

**New MCP tools:**

```python
# engram_working_add - Add to working memory (ephemeral)
# engram_working_promote - Manually promote to long-term
# engram_working_clear - Clear working memory
```

---

### Phase 3: Adaptive Forgetting (MEDIUM PRIORITY)

**Goal:** Per-memory decay rates based on access patterns.

**Current:** Fixed 30-day half-life for all memories.

**New:** Dynamic half-life based on access frequency.

```python
def adaptive_decay_factor(self, memory: dict, days_since_touch: float) -> float:
    """
    Calculate decay based on memory's access history.

    Frequently accessed → slow decay (90-day half-life)
    Rarely accessed → fast decay (7-day half-life)
    Never accessed → very fast decay (3-day half-life)
    """
    access_count = memory.get("access_count", 0)
    validated = memory.get("validated", False)

    # Determine half-life based on access pattern
    if validated:
        half_life = 180  # Validated memories decay very slowly
    elif access_count == 0:
        half_life = 3    # Never accessed → fast decay
    elif access_count < 3:
        half_life = 7    # Rarely accessed → moderate decay
    elif access_count < 10:
        half_life = 30   # Sometimes accessed → slow decay
    else:
        half_life = 90   # Frequently accessed → very slow decay

    # Exponential decay
    decay_constant = math.log(2) / half_life
    return math.exp(-decay_constant * days_since_touch)
```

**Replace in storage.py line ~665:**
```python
# OLD:
decay_factor = math.exp(-0.023 * days_since_touch)

# NEW:
decay_factor = self.adaptive_decay_factor(row, days_since_touch)
```

---

### Phase 4: Trust Scoring (MEDIUM PRIORITY)

**Goal:** Track whether memories lead to successful outcomes.

**Implementation:**

```sql
-- Add to memories table
ALTER TABLE memories ADD COLUMN trust_score REAL DEFAULT 0.5;
ALTER TABLE memories ADD COLUMN success_count INTEGER DEFAULT 0;
ALTER TABLE memories ADD COLUMN failure_count INTEGER DEFAULT 0;
```

```python
def record_outcome(self, memory_ids: list[str], success: bool):
    """
    Record task outcome for memories that were used.
    Adjusts trust scores based on success/failure.
    """
    for mem_id in memory_ids:
        if success:
            self.db.execute("""
                UPDATE memories
                SET success_count = success_count + 1,
                    trust_score = MIN(1.0, trust_score + 0.05)
                WHERE id = ?
            """, (mem_id,))
        else:
            self.db.execute("""
                UPDATE memories
                SET failure_count = failure_count + 1,
                    trust_score = MAX(0.0, trust_score - 0.1)
                WHERE id = ?
            """, (mem_id,))
    self.db.commit()

def recall(self, query: str, ..., min_trust: float = 0.3):
    """Filter out low-trust memories from results."""
    # Add to WHERE clause:
    # AND trust_score >= min_trust
```

**New MCP tool:**

```python
# engram_outcome - Record success/failure for memories used in task
{
    "name": "engram_outcome",
    "parameters": {
        "memory_ids": ["mem_xxx", "mem_yyy"],
        "success": true,
        "task_description": "Fixed the CUDA OOM error"
    }
}
```

---

### Phase 5: Agent Isolation Tiers (MEDIUM PRIORITY)

**Goal:** Stronger agent specialization than 15% boost.

**Current:** All memories in one pool, 15% role affinity boost.

**New:** Three visibility tiers.

```sql
-- Add to memories table
ALTER TABLE memories ADD COLUMN visibility TEXT DEFAULT 'universal';
-- Values: 'private', 'role', 'universal'
```

```python
# Visibility rules:
VISIBILITY_MULTIPLIERS = {
    "private": {
        "same_agent": 1.5,    # 50% boost for exact agent match
        "same_role": 0.3,     # 70% penalty for other agents in same role
        "other": 0.0,         # Not visible to other roles
    },
    "role": {
        "same_agent": 1.3,    # 30% boost for creator
        "same_role": 1.15,    # 15% boost for same role (current behavior)
        "other": 0.5,         # 50% penalty for other roles
    },
    "universal": {
        "same_agent": 1.1,    # 10% boost for creator
        "same_role": 1.05,    # 5% boost for same role
        "other": 1.0,         # Full visibility
    },
}

def get_visibility_multiplier(
    self,
    memory_visibility: str,
    memory_source_role: str,
    current_role: str
) -> float:
    """Calculate visibility multiplier for memory retrieval."""
    tier = VISIBILITY_MULTIPLIERS.get(memory_visibility, VISIBILITY_MULTIPLIERS["universal"])

    if memory_source_role == current_role:
        return tier["same_role"]
    else:
        return tier["other"]
```

**Usage guidance:**
- `visibility="private"` - Agent-specific learnings (e.g., gpu-specialist CUDA tricks)
- `visibility="role"` - Role-specific patterns (e.g., all architects share design patterns)
- `visibility="universal"` - Cross-cutting knowledge (e.g., Eric's preferences)

---

### Phase 6: Episodic Memory (LOWER PRIORITY)

**Goal:** Group memories by work sessions for temporal queries.

```sql
-- New table
CREATE TABLE episodes (
    id TEXT PRIMARY KEY,
    agent_id TEXT,
    task_description TEXT,
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    ended_at TEXT,
    summary TEXT,
    memory_count INTEGER DEFAULT 0
);

-- Add to memories table
ALTER TABLE memories ADD COLUMN episode_id TEXT;
CREATE INDEX idx_episode ON memories(episode_id);
```

```python
def start_episode(self, agent_id: str, task_description: str) -> str:
    """Begin a new episode for grouping related memories."""
    episode_id = f"ep_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{agent_id}"
    self.db.execute(
        "INSERT INTO episodes (id, agent_id, task_description) VALUES (?, ?, ?)",
        (episode_id, agent_id, task_description)
    )
    self.current_episode = episode_id
    return episode_id

def end_episode(self, episode_id: str, generate_summary: bool = True):
    """End episode and optionally generate summary."""
    if generate_summary:
        memories = self.get_episode_memories(episode_id)
        summary = self._generate_episode_summary(memories)
        # Store summary as a new pattern memory
        self.remember(summary, memory_type="pattern", importance=0.7)

    self.db.execute(
        "UPDATE episodes SET ended_at = ? WHERE id = ?",
        (datetime.now().isoformat(), episode_id)
    )

def get_episode_memories(self, episode_id: str) -> list[dict]:
    """Get all memories from an episode in chronological order."""
    # Query by episode_id
```

---

### Phase 7: Multi-Hop Retrieval (LOWER PRIORITY)

**Goal:** Graph traversal for reasoning chains.

```python
def recall_with_reasoning(
    self,
    query: str,
    limit: int = 10,
    max_hops: int = 2
) -> list[dict]:
    """
    Retrieve memories + their graph neighbors for reasoning chains.

    Example: "Why did we choose SQLite?"
    → Returns: Decision memory + linked evidence + context memories
    """
    # Step 1: Semantic search
    primary = self.recall(query, limit=limit)

    if not self.graph or max_hops == 0:
        return primary

    # Step 2: Expand via graph relationships
    expanded_ids = set(m["id"] for m in primary)

    for memory in primary:
        # Get graph neighbors (caused_by, motivated_by, requires, etc.)
        neighbors = self.graph.get_neighbors(
            memory["id"],
            max_depth=max_hops,
            relation_types=["caused_by", "motivated_by", "requires", "resulted_in"]
        )
        for neighbor in neighbors[:3]:  # Top 3 per memory
            expanded_ids.add(neighbor["id"])

    # Step 3: Fetch full details
    all_memories = []
    for mem_id in expanded_ids:
        mem = self.get_memory_by_id(mem_id)
        if mem:
            mem["is_primary"] = mem_id in [m["id"] for m in primary]
            all_memories.append(mem)

    # Sort: primary first, then by relevance
    return sorted(all_memories, key=lambda m: (not m["is_primary"], -m.get("relevance", 0)))
```

---

## Migration Plan

### v1.1 (Next Release)
- [ ] Quality gate at formation
- [ ] Working memory layer
- [ ] `force` parameter for overriding gate

### v1.2
- [ ] Adaptive forgetting curves
- [ ] Trust scoring + outcome tracking
- [ ] Evaluation harness (precision/recall tests)

### v1.3
- [ ] Agent isolation tiers (private/role/universal)
- [ ] Automatic dedup (not opt-in)

### v2.0
- [ ] Episodic memory
- [ ] Multi-hop retrieval
- [ ] Summary generation for long memories

---

## Evaluation Metrics

Track these to measure improvements:

| Metric | Current | Target |
|--------|---------|--------|
| Precision@5 | Unknown | >70% |
| Recall@5 | Unknown | >60% |
| Duplicate rate | ~5%? | <1% |
| Never-accessed rate (30d) | Unknown | <20% |
| Rejection rate (quality gate) | 0% | 15-25% |

**Test harness:**
```python
# tests/test_retrieval_quality.py

EVAL_QUERIES = [
    {
        "query": "How to fix CUDA out of memory?",
        "expected": ["mem_cuda_fix_1", "mem_cuda_fix_2"],
        "not_expected": ["mem_unrelated"],
    },
    # ... more test cases
]

def test_precision_at_5():
    for test in EVAL_QUERIES:
        results = store.recall(test["query"], limit=5)
        relevant = [r for r in results if r["id"] in test["expected"]]
        precision = len(relevant) / len(results) if results else 0
        assert precision >= 0.5, f"Low precision for: {test['query']}"
```

---

## References

- [Memory in the Age of AI Agents](https://arxiv.org/abs/2512.13564) - Taxonomy survey
- [SimpleMem](https://arxiv.org/abs/2601.02553) - Semantic lossless compression
- [Harvard D3](https://d3.harvard.edu/smarter-memories-stronger-agents/) - Add-all performed worse
- [Mem0 Research](https://mem0.ai/research) - 26% accuracy boost, 90% token savings
- [Adaptive Forgetting](https://pmc.ncbi.nlm.nih.gov/articles/PMC7334729/) - Spaced repetition research
