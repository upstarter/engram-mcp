# Project Knowledge Encoding Strategy

## The Problem

Basic knowledge (easily Googled) wastes engram storage and context window. What Claude needs is **distilled wisdom** - insights that:
- Take hours/days to discover through trial and error
- Aren't in documentation or obvious from code structure
- Represent architectural decisions and their non-obvious consequences
- Capture failure modes and their workarounds

## What Makes Knowledge "Advanced"?

| Level | Example | Value |
|-------|---------|-------|
| **Basic** | "Use type hints in Python" | LOW - Easily Googled |
| **Intermediate** | "This project uses Pydantic for validation" | MEDIUM - Saves discovery time |
| **Advanced** | "Pydantic validates at LOAD time, not usage - broken config prevents ANY command from running" | HIGH - Prevents debugging spiral |
| **Wisdom** | "The rough_cut engine operates on filename metadata, not video analysis. This means SCREEN_ prefix required for screen captures to be categorized correctly." | CRITICAL - Non-obvious behavior |

## Knowledge Categories for Projects

### 1. Architectural Decisions (importance: 0.9)
- **What**: Why the system was built this way
- **Why valuable**: Prevents "improvements" that break design assumptions
- **Example**: "Single-user local-first design - no multi-user without major refactor"

### 2. Critical Dependencies (importance: 0.9)
- **What**: External systems the project relies on
- **Why valuable**: Explains mysterious failures
- **Example**: "Resolve API requires Resolve RUNNING - graceful degradation if unavailable"

### 3. Silent Failure Modes (importance: 0.85)
- **What**: Things that fail without obvious errors
- **Why valuable**: Saves hours of debugging
- **Example**: "NLP features degrade silently - missing spacy reduces functionality without error"

### 4. Non-Obvious Behaviors (importance: 0.85)
- **What**: System behaviors that surprise new developers
- **Why valuable**: Prevents incorrect assumptions
- **Example**: "Scene numbers OVERRIDE timestamps - 1.5 sorts between 1 and 2 regardless of recording order"

### 5. File/Module Importance Map (importance: 0.8)
- **What**: Which files are critical vs routine
- **Why valuable**: Guides code exploration
- **Example**: "rough_cut.py (3745 lines) is the intellectual center - NEVER modify without full understanding"

### 6. Integration Gotchas (importance: 0.8)
- **What**: External API quirks and workarounds
- **Why valuable**: Saves rediscovery of known issues
- **Example**: "Whisper fuzzy matching handles slate→state mis-transcriptions - see SLATE_VARIANTS list"

### 7. Resource Constraints (importance: 0.85)
- **What**: Performance limitations and their workarounds
- **Why valuable**: Prevents OOM and performance issues
- **Example**: "GPU coordination gap - simultaneous Whisper + FFmpeg can OOM on 16GB VRAM"

## Encoding Process

### Step 1: Deep Exploration
Use Task tool with Explore subagent to thoroughly analyze:
```
- Overall architecture and component interactions
- Non-obvious design decisions and their WHY
- Critical files with line counts
- Pain points, gotchas, complex areas
- Integration points and their failure modes
```

### Step 2: Extract Wisdom
From exploration, identify:
- What would take 2+ hours to discover?
- What behavior is counter-intuitive?
- What breaks silently?
- What architectural constraints shape future changes?

### Step 3: Encode in Seed Format
Create `{project}-wisdom.json` with:
```json
{
  "metadata": {
    "name": "Project Deep Wisdom",
    "category": "project_knowledge",
    "project": "project_name"
  },
  "entities": [
    // Project-specific goals, blockers, patterns
  ],
  "memories": [
    {
      "content": "PREFIX: Detailed wisdom...",
      "type": "decision|solution|pattern|fact",
      "importance": 0.8-0.95,
      "tags": ["project", "category", "subcategory"]
    }
  ],
  "relationships": [
    // How blockers affect goals, patterns enable goals
  ]
}
```

### Step 4: Memory Formatting Rules

**Always prefix with project name in CAPS**:
```
STUDIOFLOW CROWN JEWEL: rough_cut.py (3745 lines)...
ENGRAM ARCHITECTURE: SQLite + ChromaDB + NetworkX...
```

**Include specifics, not vague guidance**:
```
BAD:  "Be careful with audio markers"
GOOD: "Audio markers parse 'slate [qualifier] [scene] done' from Whisper transcripts with fuzzy matching for slate→state/slayt/slait variants"
```

**Capture the WHY and the GOTCHA**:
```
BAD:  "Use decimal scene numbers"
GOOD: "Decimal scene numbers OVERRIDE timestamp order - 1.5 sorts between 1 and 2 regardless of recording time. GOTCHA: Can confuse if expecting timestamp-based order"
```

**Include file paths and line counts**:
```
BAD:  "The rough cut module is important"
GOOD: "rough_cut.py (3745 lines, 160KB) in studioflow/core/ - contains quote extraction, thematic organization, 10+ cut styles, B-roll matching"
```

## Importance Scoring for Project Knowledge

| Score | Criteria |
|-------|----------|
| **0.95** | Crown jewel modules, core IP, break-the-system if modified wrong |
| **0.9** | Architectural decisions, critical dependencies, major gotchas |
| **0.85** | Silent failures, non-obvious behaviors, resource constraints |
| **0.8** | File maps, integration details, configuration quirks |
| **0.7** | Standard patterns, routine behaviors |

## Validation: Did We Capture the Right Knowledge?

After encoding, test with these queries:
```python
# Should return architectural decisions
engram_recall("studioflow architecture decisions constraints")

# Should return the gotcha
engram_recall("studioflow whisper audio markers fail")

# Should return GPU warning
engram_recall("studioflow gpu memory oom")

# Should identify critical file
engram_recall("studioflow most important file code")
```

If queries return vague or irrelevant results, the encoding is too basic.

## Template: Project Wisdom Seed File

```json
{
  "metadata": {
    "name": "{Project} Deep Architectural Wisdom",
    "version": "1.0",
    "created": "YYYY-MM-DD",
    "category": "project_knowledge",
    "project": "{project_lowercase}",
    "purpose": "Non-obvious insights that take hours to discover"
  },
  "entities": [
    {"type": "project", "name": "{ProjectName}", "description": "One-line purpose"},
    {"type": "goal", "name": "{Primary Goal}", "priority": "P0", "description": "What success looks like"},
    {"type": "blocker", "name": "{Known Blocker}", "description": "What prevents goal"},
    {"type": "pattern", "name": "{Key Pattern}", "description": "Proven approach"}
  ],
  "memories": [
    {
      "content": "{PROJECT} CROWN JEWEL: {critical_file} ({lines} lines) - {why_critical}. {specific_behavior}. NEVER {warning}.",
      "type": "decision",
      "importance": 0.95,
      "tags": ["{project}", "architecture", "critical"]
    },
    {
      "content": "{PROJECT} {CATEGORY}: {Specific behavior}. {How it works}. GOTCHA: {Non-obvious consequence}. WORKAROUND: {Solution if applicable}.",
      "type": "solution",
      "importance": 0.85,
      "tags": ["{project}", "{category}", "{subcategory}"]
    }
  ],
  "relationships": [
    {"source": "entity:blocker:{blocker}", "target": "entity:goal:{goal}", "type": "blocks"},
    {"source": "entity:pattern:{pattern}", "target": "entity:goal:{goal}", "type": "enables"}
  ]
}
```

## Anti-Patterns to Avoid

❌ **Generic advice**: "Write good tests" - Useless without project context
❌ **Obvious documentation**: "This project uses Python" - Discoverable in seconds
❌ **Vague warnings**: "Be careful here" - Doesn't explain what or why
❌ **Implementation details**: "Line 234 does X" - Changes constantly
❌ **Tool preferences**: "I prefer VS Code" - Personal, not project wisdom

✅ **Architectural constraints**: "Can't add multi-user without refactoring state manager"
✅ **Silent failures**: "NLP degrades without error if spacy missing"
✅ **Non-obvious coupling**: "Audio markers depend on Whisper accuracy"
✅ **File importance**: "rough_cut.py is the IP - understand fully before modifying"
✅ **Resource limits**: "GPU ops not coordinated - sequence heavy tasks"
