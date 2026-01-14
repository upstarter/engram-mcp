# Engram Seed Data Strategy

## Goal
Populate engram with high-value knowledge that maximizes Claude's effectiveness across Eric's workflows.

## Eric's Key Workflows

| Workflow | Priority | Current Knowledge Gap |
|----------|----------|----------------------|
| YouTube Production | P0 | ✓ Seeded (youtube-mastery.json) |
| Software Development | P0 | Need Python, TypeScript, architecture patterns |
| AI/ML Development | P0 | Need PyTorch, model training, GPU optimization |
| Claude Effectiveness | P1 | Need prompt engineering, tool usage patterns |
| Personal Productivity | P1 | Need execution patterns, anti-procrastination |

## Seed Data Files to Create

### 1. `software-dev-mastery.json` (P0)
- Python best practices 2025
- TypeScript patterns
- Git workflows
- Code review patterns
- Testing strategies
- Architecture decisions
- Debugging patterns
- Performance optimization

### 2. `ai-ml-mastery.json` (P0)
- PyTorch patterns and gotchas
- GPU memory optimization
- Model training workflows
- Inference optimization
- Common errors and solutions
- CUDA/cuDNN issues
- Hugging Face patterns
- Local model deployment

### 3. `claude-effectiveness.json` (P1)
- Prompt engineering patterns
- Tool usage best practices
- Context management
- Multi-agent coordination
- MCP server patterns
- Claude Code specific tips

### 4. `execution-system.json` (P1)
- Anti-procrastination patterns
- Focus management
- Project completion strategies
- Shiny object defense
- Energy management
- Decision fatigue reduction

### 5. `eric-preferences.json` (P1)
- Coding style preferences
- Tool preferences
- Communication preferences
- Workflow preferences
- Environment setup

## Entity Graph Structure

```
GOALS (P0)
├── YouTube Monetization
│   ├── blocked_by: Inconsistent Publishing
│   ├── blocked_by: Low CTR
│   └── requires: Channel Growth
├── Ship AI Products
│   ├── blocked_by: Scope Creep
│   ├── blocked_by: Perfectionism
│   └── enables: YouTube Content
└── Superior Code Quality
    ├── requires: Testing Discipline
    ├── requires: Code Review
    └── blocked_by: Technical Debt

BLOCKERS
├── Shiny Object Syndrome → blocks → ALL GOALS
├── Perfectionism → blocks → Ship AI Products
├── Scope Creep → blocks → Ship AI Products
├── Technical Debt → blocks → Superior Code Quality
└── Context Switching → blocks → Deep Work

PATTERNS (proven approaches)
├── Small Scoped Wins → defeats → Procrastination
├── README-Driven Dev → defeats → Scope Creep
├── Ship Then Iterate → defeats → Perfectionism
├── One Active Project → defeats → Context Switching
└── Visible Progress → defeats → Motivation Loss

PHASES (workflows)
├── Episode Production: research → script → record → edit → publish
├── AI Product: ideate → prototype → validate → ship → iterate
└── Software Dev: design → implement → test → review → deploy
```

## Memory Categories by Type

### Decisions (type: decision)
- Architecture choices with reasoning
- Tool/library selections
- Workflow design choices
- Trade-off resolutions

### Solutions (type: solution)
- Bug fixes with root cause
- Performance optimizations
- Error resolutions
- Workarounds discovered

### Patterns (type: pattern)
- Reusable approaches
- Best practices
- Anti-patterns to avoid
- Workflow templates

### Facts (type: fact)
- API specifications
- Configuration values
- System constraints
- Compatibility info

### Preferences (type: preference)
- Coding style
- Tool choices
- Communication style
- Workflow preferences

### Philosophy (type: philosophy)
- Guiding principles
- Decision frameworks
- Quality standards
- Priority systems

## Importance Scoring Guide

| Score | When to Use |
|-------|-------------|
| 0.95 | Primary goals, critical blockers |
| 0.9 | Architecture decisions, core patterns |
| 0.85 | Important solutions, validated patterns |
| 0.8 | Useful patterns, preferences |
| 0.7 | Standard best practices |
| 0.6 | Nice-to-know facts |
| 0.5 | General information |

## Relationship Types to Use

| Relationship | Use Case |
|--------------|----------|
| `blocks` | Blocker → Goal |
| `enables` | Pattern → Goal, Phase → Phase |
| `requires` | Goal → Prerequisite |
| `supersedes` | New decision → Old decision |
| `motivated_by` | Decision → Philosophy |
| `example_of` | Specific → General pattern |

## Validation Criteria

After seeding, verify:
1. `engram_recall("how to fix CUDA OOM")` → Returns GPU optimization solutions
2. `engram_recall("Python best practices")` → Returns relevant patterns
3. `engram_graph(action=blockers, target="youtube monetization")` → Returns known blockers
4. `engram_context("AI development")` → Returns relevant AI/ML patterns

## Estimated Scale

| Category | Memories | Entities | Relationships |
|----------|----------|----------|---------------|
| YouTube Production | ~35 | 16 | 15 |
| Software Dev | ~50 | 20 | 25 |
| AI/ML | ~40 | 15 | 20 |
| Claude Effectiveness | ~25 | 10 | 15 |
| Execution System | ~20 | 12 | 20 |
| Eric Preferences | ~15 | 5 | 10 |
| **TOTAL** | **~185** | **~78** | **~105** |
