"""
MCP Server - How Claude talks to Engram.

MCP (Model Context Protocol) is like a phone line between Claude and Engram.
This file sets up three "buttons" Claude can press:

1. engram_remember - "Save this for later"
2. engram_recall - "Find memories about X"
3. engram_context - "What should I know right now?"
"""

import os
import json
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from engram.storage import MemoryStore


# Create the MCP server
server = Server("engram")

# Create the memory store (lazy - initialized on first use)
_store: MemoryStore | None = None


def get_store() -> MemoryStore:
    """Get the memory store, creating it if needed."""
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store


# File-based context (MCP server can't access parent process env vars)
CONTEXT_STATE_DIR = os.path.expanduser("~/.spc/projects/state")


def _get_context_from_files() -> tuple[str, str, str]:
    """Read role, project, and agent_id from state files.

    Returns (role, project, agent_id) tuple. All may be empty strings if not set.

    Why files not env vars?
    The MCP server runs as a subprocess spawned by Claude Code, which doesn't
    inherit the shell environment where CLAUDE_TAB_ROLE and SPC_PROJECT are set.
    The tab-init scripts write these to files that the MCP server can read.

    agent_id: Stable identifier for this Claude Code tab/session.
              Used for context isolation (per-agent history tracking).
              Format: role + session_id if available, or role-based hash.
    """
    role = ""
    project = ""
    agent_id = ""

    # Read role from file (written by claude-tab-integration.sh)
    role_file = os.path.join(CONTEXT_STATE_DIR, "current_role")
    if os.path.exists(role_file):
        try:
            with open(role_file) as f:
                role = f.read().strip()
        except Exception:
            pass

    # Read project from active_project JSON (written by proj command)
    project_file = os.path.join(CONTEXT_STATE_DIR, "..", "..", "active_project")
    project_file = os.path.normpath(project_file)  # ~/.spc/active_project
    if os.path.exists(project_file):
        try:
            import json
            with open(project_file) as f:
                data = json.load(f)
                project = data.get("name", "").lower()
        except Exception:
            pass

    # Read or generate agent_id for context isolation
    # Try to read session_id from state file (if tab-init script writes it)
    session_id_file = os.path.join(CONTEXT_STATE_DIR, "session_id")
    session_id = ""
    if os.path.exists(session_id_file):
        try:
            with open(session_id_file) as f:
                session_id = f.read().strip()
        except Exception:
            pass

    # Generate stable agent_id: role + session_id, or role-based hash
    if role:
        if session_id:
            agent_id = f"{role}:{session_id}"
        else:
            # Use role as agent_id (less ideal but better than nothing)
            # This means all tabs with same role share context
            agent_id = role
    elif session_id:
        agent_id = session_id
    # If neither role nor session_id, agent_id remains empty (will use correlation_id as fallback)

    return role, project, agent_id


# =============================================================================
# TOOL DEFINITIONS - What buttons Claude can press
# =============================================================================

def _is_chainmind_enabled() -> bool:
    """Check if ChainMind is enabled in config."""
    import yaml
    from pathlib import Path
    import os

    # Check environment variable first (highest priority)
    env_enabled = os.getenv("CHAINMIND_ENABLED", "").lower()
    if env_enabled:
        return env_enabled in ("true", "1", "yes")

    # Check config file
    config_path = Path(__file__).parent.parent / "config" / "chainmind.yaml"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
                return config.get("enabled", True)  # Default to enabled
        except Exception:
            return True  # Default to enabled on error

    return True  # Default to enabled


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Tell Claude what tools are available."""
    tools = [
        Tool(
            name="engram_remember",
            description="""Store a memory for future recall.

IMPORTANT: Human-in-the-loop workflow:
1. By default, shows a preview for user confirmation before storing
2. Set confirmed=true only after user approves the memory
3. Preview shows: content, type, importance, similar memories, reasoning

Use this to save:
- Facts: "The project uses PostgreSQL 15"
- Preferences: "User prefers TypeScript over JavaScript"
- Decisions: "Chose SQLite because MVP simplicity"
- Solutions: "Fixed by setting PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512"
- Philosophy: "README-driven development: write docs first"
- Patterns: "MCP servers use stdio transport"

The memory will be stored with semantic indexing for future retrieval.

Contradiction detection: Similar memories are shown in preview for review.
If conflicts found, use supersede=[ids] to replace old memories with the new one.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The memory content to store"
                    },
                    "memory_type": {
                        "type": "string",
                        "enum": ["fact", "preference", "decision", "solution", "philosophy", "pattern"],
                        "default": "fact",
                        "description": "Category of memory"
                    },
                    "importance": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "default": 0.5,
                        "description": "How important is this? 0.0 (trivial) to 1.0 (critical)"
                    },
                    "project": {
                        "type": "string",
                        "description": "Project name (optional - auto-detected from cwd if not specified)"
                    },
                    "confirmed": {
                        "type": "boolean",
                        "default": False,
                        "description": "Set to true only after user confirms the memory. When false, shows preview for approval."
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why this memory is worth storing (shown to user for review)"
                    },
                    "supersede": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Memory IDs to supersede (archive) with this new memory"
                    }
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="engram_recall",
            description="""Search memories by semantic similarity.

Use this to find:
- Past decisions and their reasoning
- Solutions to problems you've solved before
- User preferences and facts
- Project-specific context

Returns memories ranked by relevance to your query.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for (natural language)"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 5,
                        "description": "Maximum number of results"
                    },
                    "project": {
                        "type": "string",
                        "description": "Filter to specific project (optional)"
                    },
                    "memory_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter to specific types: fact, preference, decision, solution, philosophy, pattern"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="engram_context",
            description="""Get relevant context for current work.

Use this at the start of a task to see what memories are relevant.
Automatically considers:
- Current project (detected from working directory)
- Universal principles and patterns
- Recent related work

Returns memories formatted for easy context injection.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What you're working on (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 5,
                        "description": "Maximum number of context items"
                    }
                }
            }
        ),
        Tool(
            name="engram_related",
            description="""Find memories related through entity connections.

Use this when you want to find memories connected by shared entities
(projects, tools, episodes, concepts) rather than semantic similarity.

Two modes:
1. By memory ID: Find memories related to a specific memory
2. By entity: Find all memories mentioning a project/tool/episode

Examples:
- Find all memories about "studioflow" project
- Find memories related to "EP001" episode
- Find what's connected to a specific memory""",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "Find memories related to this memory ID (optional)"
                    },
                    "entity_type": {
                        "type": "string",
                        "enum": ["projects", "tools", "concepts", "episode"],
                        "description": "Type of entity to search for"
                    },
                    "entity_name": {
                        "type": "string",
                        "description": "Name of the entity (e.g., 'studioflow', 'EP001')"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 5,
                        "description": "Maximum number of results"
                    }
                }
            }
        ),
        Tool(
            name="engram_consolidate",
            description="""Find and consolidate similar memories.

Use this to clean up memory bloat by merging similar memories into consolidated wisdom.

Two modes:
1. find_candidates: Discover clusters of similar memories that could be merged
2. consolidate: Merge specific memories into one (requires providing the merged content)

This helps prevent memory pollution and surfaces patterns from repeated learnings.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["find_candidates", "consolidate"],
                        "description": "Action to perform"
                    },
                    "similarity_threshold": {
                        "type": "number",
                        "default": 0.85,
                        "minimum": 0.5,
                        "maximum": 0.99,
                        "description": "How similar memories must be to cluster (0.85 = very similar)"
                    },
                    "memory_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Memory IDs to consolidate (for consolidate action)"
                    },
                    "consolidated_content": {
                        "type": "string",
                        "description": "The merged memory content (for consolidate action)"
                    }
                },
                "required": ["action"]
            }
        ),
        Tool(
            name="engram_link",
            description="""Create semantic relationships between memories or entities.

Use this to build a rich knowledge graph with meaningful connections:

RELATIONSHIP TYPES (15 types in 5 families):

Temporal (track currency):
- supersedes: New memory replaces old one
- precedes: Memory happened before another
- evolved_from: Thinking evolved from earlier memory

Causal (understand why):
- caused_by: Outcome was caused by decision/action
- motivated_by: Decision was motivated by philosophy/goal
- resulted_in: Action resulted in this outcome
- blocked_by: Goal is blocked by this obstacle
- triggered_by: Blocker was triggered by this situation

Structural (navigate hierarchy):
- part_of: Component is part of whole
- contains: Whole contains component
- instance_of: Specific is instance of general
- phase_of: Phase is part of workflow

Dependency (critical path):
- requires: Task requires prerequisite
- enables: Completing this enables that
- blocks: This blocks that
- conflicts_with: These conflict

Semantic (find relevance):
- similar_to: Memories are similar (consolidation candidates)
- contradicts: Memories conflict
- reinforces: Memory validates another
- example_of: Specific example of pattern

Examples:
- Link a decision to the philosophy that motivated it
- Link a blocker to the goal it blocks
- Link a new memory that supersedes an old one
- Link phases to show workflow dependencies""",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_id": {
                        "type": "string",
                        "description": "Source node ID (memory ID like 'mem_xxx' or entity ID like 'entity:goal:monetization')"
                    },
                    "target_id": {
                        "type": "string",
                        "description": "Target node ID"
                    },
                    "relation_type": {
                        "type": "string",
                        "enum": [
                            "supersedes", "precedes", "evolved_from",
                            "caused_by", "motivated_by", "resulted_in", "blocked_by", "triggered_by",
                            "part_of", "contains", "instance_of", "phase_of",
                            "requires", "enables", "blocks", "conflicts_with",
                            "similar_to", "contradicts", "reinforces", "example_of"
                        ],
                        "description": "Type of relationship"
                    },
                    "strength": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "default": 1.0,
                        "description": "Relationship strength (0.0-1.0)"
                    },
                    "evidence": {
                        "type": "string",
                        "description": "Memory ID that supports this relationship (optional)"
                    }
                },
                "required": ["source_id", "target_id", "relation_type"]
            }
        ),
        Tool(
            name="engram_entity",
            description="""Create standalone entities in the knowledge graph.

Entities are first-class nodes that memories can connect to:

ENTITY TYPES:
- goal: Desired outcomes (monetization, consistent publishing)
- blocker: Named obstacles (shiny object syndrome, perfectionism)
- phase: Workflow stages (research, scripting, recording)
- pattern: Reusable approaches (PAS structure, face+emotion thumbnail)
- decision_point: Recurring choice situations (new idea arrives)

After creating entities, use engram_link to connect them:
- Connect blockers to goals they block
- Connect phases to show workflow order
- Connect patterns to contexts where they apply

Examples:
- Create goal "YouTube Monetization" with priority P0
- Create blocker "Shiny Object Syndrome"
- Link: blocker --blocks--> goal""",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": ["goal", "blocker", "phase", "pattern", "decision_point", "project", "tool", "concept"],
                        "description": "Type of entity"
                    },
                    "name": {
                        "type": "string",
                        "description": "Entity name"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["active", "achieved", "abandoned"],
                        "default": "active",
                        "description": "Entity status"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["P0", "P1", "P2"],
                        "description": "Priority level (for goals)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description"
                    }
                },
                "required": ["entity_type", "name"]
            }
        ),
        Tool(
            name="engram_validate",
            description="""Mark a memory as validated/useful.

Call this when a memory proves helpful. This:
1. Increases the memory's validation_count
2. Boosts its confidence score
3. Updates last_validated timestamp

Memories with higher validation counts surface more prominently in searches.
This creates a learning loop where useful memories get reinforced.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "Memory ID to validate"
                    }
                },
                "required": ["memory_id"]
            }
        ),
        Tool(
            name="engram_graph",
            description="""Query the knowledge graph for insights.

Actions:
- blockers: Get all blockers for a goal
- requirements: Get prerequisites for a task/phase
- contradictions: Find memories that contradict one another
- hubs: Find most connected entities
- visualize: ASCII visualization of a memory's connections
- stats: Graph statistics

Examples:
- "What's blocking monetization?" → action=blockers, target=monetization
- "What does recording require?" → action=requirements, target=recording
- "Show connections for mem_xxx" → action=visualize, target=mem_xxx""",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["blockers", "requirements", "contradictions", "hubs", "visualize", "stats"],
                        "description": "Query action"
                    },
                    "target": {
                        "type": "string",
                        "description": "Target entity/memory name or ID (not needed for hubs/stats)"
                    },
                    "target_type": {
                        "type": "string",
                        "enum": ["goal", "phase", "memory"],
                        "default": "goal",
                        "description": "Type of target (for blockers/requirements)"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Max results (for hubs)"
                    }
                },
                "required": ["action"]
            }
        ),
    ]

    # Add ChainMind tools if available
    # Check if ChainMind is enabled in config
    chainmind_enabled = _is_chainmind_enabled()

    try:
        from engram.chainmind_helper import get_helper
        from engram.prompt_generator import PromptGenerator

        helper = get_helper()
        if chainmind_enabled and helper.is_available():
            tools.extend([
                Tool(
                    name="chainmind_generate",
                    description="""Generate text using ChainMind with smart model selection and automatic fallback.

Use this instead of direct provider APIs for optimal model selection and cost savings.

Key benefits:
- **Smart Model Selection**: Automatically selects the best model based on task type (coding, reasoning, creative, etc.)
- **Cost Optimization**: Uses cheaper models when appropriate (e.g., GPT-3.5 for coding, Ollama for simple tasks)
- **Automatic Fallback**: Falls back to alternative providers when Claude hits usage limits
- **Task-Aware**: Analyzes your prompt to select optimal model (coding → GPT-4, reasoning → Claude, etc.)

Model Selection Modes:
- **auto_select_model=true**: Uses ChainMind's strategic router for optimal model selection (recommended)
- **prefer_claude=true**: Tries Claude first, falls back on errors (default)
- **prefer_claude=false**: Uses ChainMind routing for cost optimization

When Claude hits its monthly usage limit (happens 1-2x per week), this tool automatically uses alternative providers so you don't need to purchase extra credits.""",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "The prompt to generate from"
                            },
                            "auto_select_model": {
                                "type": "boolean",
                                "default": False,
                                "description": "Use ChainMind's smart routing for optimal model selection based on task type (recommended). When true, automatically selects best model (coding → GPT-4, reasoning → Claude, simple → Ollama)."
                            },
                            "prefer_claude": {
                                "type": "boolean",
                                "default": True,
                                "description": "Try Claude first (default: true). Ignored if auto_select_model=true. Falls back automatically on usage limits."
                            },
                            "fallback_providers": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Alternative providers to use if Claude hits limits (default: ['openai', 'ollama'])"
                            },
                            "temperature": {
                                "type": "number",
                                "default": 0.7,
                                "description": "Generation temperature"
                            },
                            "max_tokens": {
                                "type": "integer",
                                "description": "Maximum tokens to generate"
                            }
                        },
                        "required": ["prompt"]
                    }
                ),
                Tool(
                    name="chainmind_generate_prompt",
                    description="""Generate optimized prompts for Claude with context from engram-mcp memories.

This tool creates better prompts by:
- Analyzing task requirements
- Incorporating relevant memories from engram-mcp
- Using Claude-specific optimizations
- Providing multiple prompt strategies

Use this to improve Claude's response quality by giving it better context and clearer instructions.""",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task": {
                                "type": "string",
                                "description": "What Claude needs to do"
                            },
                            "context": {
                                "type": "string",
                                "description": "Additional context (optional)"
                            },
                            "strategy": {
                                "type": "string",
                                "enum": ["concise", "detailed", "structured", "balanced"],
                                "default": "balanced",
                                "description": "Prompt strategy: concise (minimal), detailed (comprehensive), structured (organized), balanced (default)"
                            },
                            "project": {
                                "type": "string",
                                "description": "Project name for context retrieval (optional, auto-detected if not provided)"
                            },
                            "limit_context": {
                                "type": "integer",
                                "default": 5,
                                "description": "Maximum number of memories to include"
                            }
                        },
                        "required": ["task"]
                    }
                ),
                Tool(
                    name="chainmind_verify",
                    description="""Verify Claude responses using alternative models for critical tasks.

Use this to verify important responses by checking them with alternative models. This provides:
- Confidence scores
- Verification from multiple models
- Quality assurance for critical outputs

Useful when you need high confidence in Claude's responses.""",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "response": {
                                "type": "string",
                                "description": "The response to verify"
                            },
                            "original_prompt": {
                                "type": "string",
                                "description": "The original prompt that generated this response"
                            },
                            "verification_providers": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": ["openai"],
                                "description": "Providers to use for verification"
                            },
                            "confidence_threshold": {
                                "type": "number",
                                "default": 0.8,
                                "description": "Minimum confidence threshold (0.0-1.0)"
                            }
                        },
                        "required": ["response", "original_prompt"]
                    }
                ),
                Tool(
                    name="chainmind_generate_batch",
                    description="""Generate text for multiple prompts in batch using ChainMind.

Use this to process multiple prompts efficiently in a single call. All prompts are processed concurrently.

Benefits:
- Faster than individual calls
- Shared caching across batch
- Efficient resource usage
- Single correlation ID for tracking

Maximum 50 prompts per batch.""",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prompts": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of prompts to generate from (max 50)"
                            },
                            "prefer_claude": {
                                "type": "boolean",
                                "default": True,
                                "description": "Try Claude first for each prompt"
                            },
                            "fallback_providers": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Alternative providers if Claude hits limits"
                            },
                            "temperature": {
                                "type": "number",
                                "default": 0.7,
                                "description": "Generation temperature"
                            },
                            "max_tokens": {
                                "type": "integer",
                                "description": "Maximum tokens to generate per prompt"
                            }
                        },
                        "required": ["prompts"]
                    }
                ),
            ])
    except Exception as e:
        # ChainMind not available - skip tools
        pass

    return tools


# =============================================================================
# TOOL HANDLERS - What happens when Claude presses a button
# =============================================================================

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls from Claude."""

    store = get_store()

    # Get current working directory for project detection
    cwd = os.getcwd()

    # Read role, project, and agent_id from state files for context-aware storage/recall
    current_role, current_project, _ = _get_context_from_files()  # agent_id not needed for engram tools

    if name == "engram_remember":
        # HITL workflow: preview by default, store only when confirmed=true
        # Check for auto-approve setting (environment variable, config file, or default to False)
        auto_approve = False
        # Check environment variable first
        if os.environ.get("ENGRAM_AUTO_APPROVE", "").lower() == "true":
            auto_approve = True
        # Check config file
        else:
            try:
                config_path = os.path.expanduser("~/.engram/config/engram.yaml")
                if os.path.exists(config_path):
                    try:
                        import yaml
                    except ImportError:
                        # Try PyYAML alternative import
                        try:
                            from yaml import safe_load
                            yaml = type('obj', (object,), {'safe_load': safe_load})()
                        except ImportError:
                            yaml = None

                    if yaml:
                        with open(config_path) as f:
                            config = yaml.safe_load(f) or {}
                            auto_approve = config.get("auto_approve", False)
            except Exception:
                pass  # Gracefully handle config errors

        confirmed = arguments.get("confirmed", auto_approve)
        content = arguments["content"]
        memory_type = arguments.get("memory_type", "fact")
        importance = arguments.get("importance", 0.5)
        reasoning = arguments.get("reasoning", "")
        project = arguments.get("project") or None
        supersede = arguments.get("supersede", [])

        if not confirmed:
            # === PREVIEW MODE: Show memory for user approval ===
            lines = ["## 🔍 Memory Preview (awaiting confirmation)\n"]

            # Show the proposed memory
            lines.append("### Proposed Memory")
            lines.append(f"**Type:** {memory_type}")
            lines.append(f"**Importance:** {importance:.0%}")
            if project:
                lines.append(f"**Project:** {project}")
            lines.append(f"\n**Content:**\n> {content}\n")

            # Show reasoning if provided
            if reasoning:
                lines.append(f"**Why store this:**\n> {reasoning}\n")

            # Find similar existing memories
            similar = store.recall(
                query=content,
                limit=3,
                memory_types=None,  # Search all types
            )

            if similar:
                lines.append("### Similar Existing Memories")
                for i, mem in enumerate(similar, 1):
                    relevance = mem.get('relevance', 0)
                    if relevance > 0.7:
                        status = "⚠️ HIGH OVERLAP"
                    elif relevance > 0.5:
                        status = "📋 Related"
                    else:
                        status = "📝 Distant"

                    lines.append(f"{i}. {status} ({relevance:.0%} similar)")
                    lines.append(f"   `{mem['id']}` [{mem['memory_type']}]")
                    lines.append(f"   {mem['content'][:100]}{'...' if len(mem['content']) > 100 else ''}\n")

                # Check for near-duplicates
                if similar and similar[0].get('relevance', 0) > 0.85:
                    lines.append("⚠️ **Warning:** First result is very similar - may be a duplicate.\n")
                    lines.append(f"Consider using `supersede=['{similar[0]['id']}']` to replace it.\n")

            # User action options
            lines.append("---")
            lines.append("### Actions")
            lines.append("- **Approve as-is:** Call again with `confirmed=true`")
            lines.append("- **Modify and approve:** Edit content/type/importance, then `confirmed=true`")
            lines.append("- **Replace existing:** Add `supersede=['mem_xxx']` with `confirmed=true`")
            lines.append("- **Discard:** Don't call again (no action needed)")

            return [TextContent(type="text", text="\n".join(lines))]

        else:
            # === CONFIRMED: Actually store the memory ===
            result = store.remember(
                content=content,
                memory_type=memory_type,
                importance=importance,
                project=project,
                source_role=current_role or None,
                check_conflicts=False,  # Already reviewed in preview
                supersede=supersede,
            )

            # Success - memory stored
            memory_id = result
            supersede_msg = f"\n\n✓ Superseded {len(supersede)} old memories." if supersede else ""
            role_msg = f"\nRole: {current_role}" if current_role else ""
            project_msg = f"\nProject: {project}" if project else ""

            return [TextContent(
                type="text",
                text=f"✅ Memory stored (id: {memory_id}){role_msg}{project_msg}\n\n**Content:** {content[:100]}{'...' if len(content) > 100 else ''}{supersede_msg}"
            )]

    elif name == "engram_recall":
        # Log query for test suite generation
        try:
            from engram.query_logger import log_query
            log_query(
                prompt=arguments["query"],
                tool_name="engram_recall",
                agent_role=current_role,
                agent_id=current_agent_id,
                source="engram-mcp",
                metadata={
                    "limit": arguments.get("limit", 5),
                    "project": arguments.get("project"),
                    "memory_types": arguments.get("memory_types"),
                }
            )
        except Exception:
            pass  # Don't fail if logging fails

        # Search for memories with role affinity boost
        memories = store.recall(
            query=arguments["query"],
            limit=arguments.get("limit", 5),
            project=arguments.get("project"),
            memory_types=arguments.get("memory_types"),
            current_role=current_role,  # Pass role for affinity scoring
        )

        if not memories:
            return [TextContent(
                type="text",
                text=f"No memories found for: {arguments['query']}"
            )]

        # Format results nicely
        lines = [f"Found {len(memories)} memories:\n"]
        for i, mem in enumerate(memories, 1):
            project_tag = f" [{mem['project']}]" if mem['project'] else ""
            role_tag = f" @{mem['source_role']}" if mem.get('source_role') else ""
            affinity_tag = " ★" if mem.get('role_affinity', 1.0) > 1.0 else ""
            lines.append(
                f"{i}. [{mem['memory_type']}]{project_tag}{role_tag}{affinity_tag} (relevance: {mem['relevance']:.0%})\n"
                f"   {mem['content']}\n"
            )

        return [TextContent(type="text", text="\n".join(lines))]

    elif name == "engram_context":
        # Get relevant context - enhanced with role awareness (NOT project)
        base_query = arguments.get("query", "current work")

        # Build query: base + role name only
        # NOTE: Project names are NOT added - they pollute memory queries
        # Role names provide semantic context without tying to specific projects
        query_parts = [base_query]
        if current_role:
            # Role name (like "studioflow" or "gpu-specialist") is enough context
            query_parts.append(current_role)

        enhanced_query = " ".join(query_parts)

        # Log query for test suite generation
        try:
            from engram.query_logger import log_query
            log_query(
                prompt=base_query,
                tool_name="engram_context",
                agent_role=current_role,
                agent_id=current_agent_id,
                source="engram-mcp",
                metadata={
                    "enhanced_query": enhanced_query,
                    "limit": arguments.get("limit", 5),
                }
            )
        except Exception:
            pass  # Don't fail if logging fails

        memories = store.context(
            query=enhanced_query,
            cwd=cwd,
            limit=arguments.get("limit", 5),
            current_role=current_role,  # Pass for role affinity boost
        )

        if not memories:
            return [TextContent(
                type="text",
                text=f"No relevant context found.\n\nQuery: {enhanced_query}\nRole: {current_role or 'none'}"
            )]

        # Format as markdown for injection
        context_info = []
        if current_role:
            context_info.append(f"Role: {current_role}")

        header = "## Relevant Context"
        if context_info:
            header += f" ({', '.join(context_info)})"
        header += "\n"

        lines = [header]

        # Group by type
        by_type: dict[str, list] = {}
        for mem in memories:
            t = mem["memory_type"]
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(mem)

        for mem_type, mems in by_type.items():
            lines.append(f"### {mem_type.title()}s\n")
            for mem in mems:
                project_tag = f" *({mem['project']})*" if mem['project'] else ""
                lines.append(f"- {mem['content']}{project_tag}\n")
            lines.append("")

        return [TextContent(type="text", text="\n".join(lines))]

    elif name == "engram_related":
        # Find related memories via graph traversal
        memory_id = arguments.get("memory_id")
        entity_type = arguments.get("entity_type")
        entity_name = arguments.get("entity_name")
        limit = arguments.get("limit", 5)

        # Check if graph is available
        if not store.graph:
            return [TextContent(
                type="text",
                text="Knowledge graph not available (networkx not installed)"
            )]

        memories = []

        if memory_id:
            # Mode 1: Find memories related to a specific memory
            memories = store.related(memory_id, limit=limit)
            if not memories:
                return [TextContent(
                    type="text",
                    text=f"No related memories found for: {memory_id}"
                )]
            header = f"Memories related to {memory_id}"

        elif entity_type and entity_name:
            # Mode 2: Find memories by entity
            memories = store.get_by_entity(entity_type, entity_name, limit=limit)
            if not memories:
                return [TextContent(
                    type="text",
                    text=f"No memories found for {entity_type}: {entity_name}"
                )]
            header = f"Memories mentioning {entity_type}: {entity_name}"

        else:
            return [TextContent(
                type="text",
                text="Please provide either memory_id OR (entity_type AND entity_name)"
            )]

        # Format results
        lines = [f"{header}\n"]
        for i, mem in enumerate(memories, 1):
            project_tag = f" [{mem['project']}]" if mem.get('project') else ""
            lines.append(
                f"{i}. [{mem['memory_type']}]{project_tag}\n"
                f"   {mem['content']}\n"
            )

        return [TextContent(type="text", text="\n".join(lines))]

    elif name == "engram_consolidate":
        action = arguments.get("action")

        if action == "find_candidates":
            threshold = arguments.get("similarity_threshold", 0.85)
            clusters = store.find_consolidation_candidates(
                similarity_threshold=threshold,
                min_cluster_size=3,
            )

            if not clusters:
                return [TextContent(
                    type="text",
                    text=f"No consolidation candidates found at {threshold:.0%} similarity threshold.\nTry lowering the threshold (e.g., 0.75) to find more clusters."
                )]

            lines = [f"Found {len(clusters)} clusters that could be consolidated:\n"]
            for i, cluster in enumerate(clusters, 1):
                lines.append(f"### Cluster {i}: {cluster['topic']} ({cluster['count']} memories)\n")
                for mem in cluster["memories"][:5]:  # Show max 5 per cluster
                    lines.append(f"- `{mem['id']}` [{mem['memory_type']}]: {mem['content'][:60]}...")
                if cluster["count"] > 5:
                    lines.append(f"- ... and {cluster['count'] - 5} more")
                lines.append("")

            lines.append("\nTo consolidate, call with action='consolidate', memory_ids=[...], and consolidated_content='...'")

            return [TextContent(type="text", text="\n".join(lines))]

        elif action == "consolidate":
            memory_ids = arguments.get("memory_ids")
            content = arguments.get("consolidated_content")

            if not memory_ids or not content:
                return [TextContent(
                    type="text",
                    text="consolidate action requires 'memory_ids' (list) and 'consolidated_content' (string)"
                )]

            new_id = store.consolidate(
                memory_ids=memory_ids,
                consolidated_content=content,
                memory_type="pattern",
                importance=0.8,
            )

            return [TextContent(
                type="text",
                text=f"✓ Consolidated {len(memory_ids)} memories into: {new_id}\n\nNew content: {content[:100]}{'...' if len(content) > 100 else ''}\n\nOriginal memories archived (kept in SQLite but removed from search)."
            )]

        else:
            return [TextContent(
                type="text",
                text="action must be 'find_candidates' or 'consolidate'"
            )]

    elif name == "engram_link":
        # Create a relationship between nodes
        source_id = arguments.get("source_id")
        target_id = arguments.get("target_id")
        relation_type = arguments.get("relation_type")
        strength = arguments.get("strength", 1.0)
        evidence = arguments.get("evidence")

        success = store.add_relationship(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            strength=strength,
            evidence=evidence,
        )

        if success:
            return [TextContent(
                type="text",
                text=f"✓ Relationship created: {source_id} --{relation_type}--> {target_id}"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"✗ Failed to create relationship. Check that both nodes exist.\nSource: {source_id}\nTarget: {target_id}"
            )]

    elif name == "engram_entity":
        # Create a standalone entity
        entity_type = arguments.get("entity_type")
        name_val = arguments.get("name")
        status = arguments.get("status", "active")
        priority = arguments.get("priority")
        description = arguments.get("description")

        entity_id = store.add_entity(
            entity_type=entity_type,
            name=name_val,
            status=status,
            priority=priority,
            description=description,
        )

        if entity_id:
            return [TextContent(
                type="text",
                text=f"✓ Entity created: {entity_id}\nType: {entity_type}\nName: {name_val}\nStatus: {status}"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"✗ Failed to create entity. Invalid entity_type: {entity_type}"
            )]

    elif name == "engram_validate":
        # Validate/reinforce a memory
        memory_id = arguments.get("memory_id")

        success = store.validate_memory(memory_id)

        if success:
            return [TextContent(
                type="text",
                text=f"✓ Memory validated: {memory_id}\nConfidence boosted, validation_count incremented."
            )]
        else:
            return [TextContent(
                type="text",
                text=f"✗ Failed to validate memory: {memory_id}"
            )]

    elif name == "engram_graph":
        # Query the knowledge graph
        action = arguments.get("action")
        target = arguments.get("target")
        target_type = arguments.get("target_type", "goal")
        limit = arguments.get("limit", 10)

        if action == "blockers":
            if not target:
                return [TextContent(type="text", text="blockers action requires 'target' (goal name)")]

            blockers = store.get_blockers(target)
            if not blockers:
                return [TextContent(type="text", text=f"No blockers found for goal: {target}")]

            lines = [f"Blockers for '{target}':\n"]
            for b in blockers:
                lines.append(f"- {b['name']} (strength: {b['strength']:.0%})")
            return [TextContent(type="text", text="\n".join(lines))]

        elif action == "requirements":
            if not target:
                return [TextContent(type="text", text="requirements action requires 'target' (task/phase name)")]

            requirements = store.get_requirements(target, target_type)
            if not requirements:
                return [TextContent(type="text", text=f"No requirements found for {target_type}: {target}")]

            lines = [f"Requirements for '{target}':\n"]
            for r in requirements:
                lines.append(f"- [{r['type']}] {r['name']}")
            return [TextContent(type="text", text="\n".join(lines))]

        elif action == "contradictions":
            if not target:
                return [TextContent(type="text", text="contradictions action requires 'target' (memory ID)")]

            contradictions = store.find_contradictions(target)
            if not contradictions:
                return [TextContent(type="text", text=f"No contradictions found for: {target}")]

            lines = [f"Contradictions for '{target}':\n"]
            for c in contradictions:
                lines.append(f"- {c['id']} [{c['memory_type']}]: {c['content'][:60]}...")
            return [TextContent(type="text", text="\n".join(lines))]

        elif action == "hubs":
            hubs = store.get_hub_entities(limit)
            if not hubs:
                return [TextContent(type="text", text="No entities found in graph")]

            lines = ["Most connected entities:\n"]
            for h in hubs:
                lines.append(f"- [{h['type']}] {h['name']}: {h['connections']} connections")
            return [TextContent(type="text", text="\n".join(lines))]

        elif action == "visualize":
            if not target:
                return [TextContent(type="text", text="visualize action requires 'target' (node ID)")]

            viz = store.visualize_memory(target)
            return [TextContent(type="text", text=f"```\n{viz}\n```")]

        elif action == "stats":
            stats = store.get_stats()
            graph_stats = stats.get("graph", {})

            lines = ["## Graph Statistics\n"]
            lines.append(f"- Total nodes: {graph_stats.get('total_nodes', 0)}")
            lines.append(f"- Total edges: {graph_stats.get('total_edges', 0)}")
            lines.append(f"- Memories: {graph_stats.get('memory_count', 0)}")
            lines.append(f"- Entities: {graph_stats.get('entity_count', 0)}")

            if graph_stats.get("entity_types"):
                lines.append("\n### Entity Types:")
                for etype, count in graph_stats["entity_types"].items():
                    lines.append(f"  - {etype}: {count}")

            if graph_stats.get("edge_types"):
                lines.append("\n### Edge Types:")
                for etype, count in graph_stats["edge_types"].items():
                    lines.append(f"  - {etype}: {count}")

            if graph_stats.get("memory_status"):
                lines.append("\n### Memory Status:")
                for status, count in graph_stats["memory_status"].items():
                    lines.append(f"  - {status}: {count}")

            return [TextContent(type="text", text="\n".join(lines))]

        else:
            return [TextContent(type="text", text=f"Unknown graph action: {action}")]

    elif name == "chainmind_generate":
        # Generate text with ChainMind (usage limit handling)
        try:
            from engram.chainmind_helper import get_helper
            import logging

            logger = logging.getLogger("engram.server.chainmind")

            # Input validation
            if "prompt" not in arguments:
                return [TextContent(
                    type="text",
                    text="Error: 'prompt' parameter is required"
                )]

            prompt = arguments["prompt"]
            if not prompt or not prompt.strip():
                return [TextContent(
                    type="text",
                    text="Error: Prompt cannot be empty"
                )]

            # Validate parameters
            # IMPORTANT: Claude Code already uses Claude API by default
            # ChainMind is ONLY called when Claude Code's Claude API hits token limits
            # Therefore: Default to False (skip Claude, go straight to OpenAI fallback)
            auto_select_model = arguments.get("auto_select_model", False)
            prefer_claude = arguments.get("prefer_claude", False)  # Default False: Claude Code already tried Claude
            fallback_providers = arguments.get("fallback_providers")
            temperature = arguments.get("temperature", 0.7)
            max_tokens = arguments.get("max_tokens")

            # Validate temperature range
            if temperature is not None:
                if not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 2:
                    return [TextContent(
                        type="text",
                        text=f"Error: Temperature must be between 0 and 2, got {temperature}"
                    )]

            # Validate max_tokens
            if max_tokens is not None:
                if not isinstance(max_tokens, int) or max_tokens < 1:
                    return [TextContent(
                        type="text",
                        text=f"Error: max_tokens must be a positive integer, got {max_tokens}"
                    )]

            helper = get_helper()
            if not helper.is_available():
                return [TextContent(
                    type="text",
                    text="ChainMind helper not available. Check ChainMind installation and configuration."
                )]

            # Get role and agent_id from context files (for domain/model selection and context isolation)
            current_role, _, current_agent_id = _get_context_from_files()

            # Log query for test suite generation
            try:
                from engram.query_logger import log_query
                log_query(
                    prompt=prompt,
                    tool_name="chainmind_generate",
                    agent_role=current_role,
                    agent_id=current_agent_id,
                    source="engram-mcp",
                    metadata={
                        "auto_select_model": auto_select_model,
                        "prefer_claude": prefer_claude,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }
                )
            except Exception:
                pass  # Don't fail if logging fails

            kwargs = {}
            if temperature is not None:
                kwargs["temperature"] = float(temperature)
            if max_tokens is not None:
                kwargs["max_tokens"] = int(max_tokens)

            result = await helper.generate(
                prompt=prompt,
                prefer_claude=prefer_claude if not auto_select_model else None,
                auto_select_model=auto_select_model,
                fallback_providers=fallback_providers,
                agent_role=current_role,  # Pass role for optimal domain/model selection
                agent_id=current_agent_id,  # Pass agent_id for context isolation
                **kwargs
            )

            # Format response with provider info and metadata
            response_parts = [result["response"]]

            # Add metadata footer
            metadata_parts = []
            if result.get("from_cache"):
                metadata_parts.append("(from cache)")

            # Show model selection info if smart routing was used
            if result.get("model_selection"):
                model_sel = result["model_selection"]
                if model_sel.get("method") == "smart_routing":
                    metadata_parts.append(f"Model: {result.get('model', 'unknown')} (smart selection)")
                    metadata_parts.append(f"Task: {model_sel.get('task_type', 'unknown')}")

            if result.get("fallback_used"):
                metadata_parts.append(f"Used {result['provider']} (fallback)")
            elif result.get("usage_limit_hit"):
                metadata_parts.append(f"Used {result['provider']} (Claude limit hit)")
            else:
                provider_info = f"Provider: {result['provider']}"
                if result.get("model") and result.get("model") != "unknown":
                    provider_info += f" ({result['model']})"
                metadata_parts.append(provider_info)

            if "latency_seconds" in result:
                metadata_parts.append(f"Latency: {result['latency_seconds']:.2f}s")

            if metadata_parts:
                response_parts.append(f"\n\n[{' | '.join(metadata_parts)}]")

            return [TextContent(
                type="text",
                text="\n".join(response_parts)
            )]

        except ValueError as e:
            return [TextContent(
                type="text",
                text=f"Validation error: {e}"
            )]
        except RuntimeError as e:
            error_msg = str(e)
            if "router not available" in error_msg.lower():
                return [TextContent(
                    type="text",
                    text="ChainMind router not available. Please check ChainMind configuration and ensure API keys are set."
                )]
            return [TextContent(
                type="text",
                text=f"ChainMind error: {error_msg}"
            )]
        except Exception as e:
            import traceback
            logger.error(f"Unexpected error in chainmind_generate: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Unexpected error generating with ChainMind: {type(e).__name__}: {e}"
            )]

    elif name == "chainmind_generate_prompt":
        # Generate optimized prompt for Claude
        try:
            from engram.prompt_generator import PromptGenerator
            import logging

            logger = logging.getLogger("engram.server.chainmind")

            # Input validation
            if "task" not in arguments:
                return [TextContent(
                    type="text",
                    text="Error: 'task' parameter is required"
                )]

            task = arguments["task"]
            if not task or not task.strip():
                return [TextContent(
                    type="text",
                    text="Error: Task cannot be empty"
                )]

            # Log query for test suite generation
            try:
                from engram.query_logger import log_query
                log_query(
                    prompt=task,
                    tool_name="chainmind_generate_prompt",
                    agent_role=current_role,
                    agent_id=current_agent_id,
                    source="engram-mcp",
                    metadata={
                        "strategy": arguments.get("strategy", "balanced"),
                        "project": arguments.get("project") or current_project,
                    }
                )
            except Exception:
                pass  # Don't fail if logging fails

            context = arguments.get("context")
            strategy = arguments.get("strategy", "balanced")
            project = arguments.get("project") or current_project
            limit_context = arguments.get("limit_context", 5)
            max_tokens = arguments.get("max_tokens")

            # Validate strategy
            valid_strategies = ["concise", "detailed", "structured", "balanced"]
            if strategy not in valid_strategies:
                return [TextContent(
                    type="text",
                    text=f"Error: Strategy must be one of {valid_strategies}, got '{strategy}'"
                )]

            # Validate limit_context
            if not isinstance(limit_context, int) or limit_context < 1 or limit_context > 20:
                return [TextContent(
                    type="text",
                    text=f"Error: limit_context must be between 1 and 20, got {limit_context}"
                )]

            generator = PromptGenerator(memory_store=store)

            # Prompt generation is synchronous
            result = generator.generate_prompt(
                task=task,
                context=context,
                strategy=strategy,
                project=project,
                limit_context=limit_context,
                max_tokens=max_tokens
            )

            # Format response with metadata
            response_parts = [
                f"# Generated Prompt ({result['strategy']} strategy)",
                ""
            ]

            # Add metadata header
            metadata_info = []
            if result.get("metadata", {}).get("estimated_tokens"):
                metadata_info.append(f"~{result['metadata']['estimated_tokens']} tokens")
            if result.get("context_used", 0) > 0:
                metadata_info.append(f"{result['context_used']} memories")
            if result.get("metadata", {}).get("was_truncated"):
                metadata_info.append("(truncated)")

            if metadata_info:
                response_parts.append(f"*{', '.join(metadata_info)}*\n")

            response_parts.append(result["prompt"])

            if result.get("context_used", 0) > 0:
                response_parts.append(f"\n\n[Included {result['context_used']} relevant memories from engram-mcp]")

            return [TextContent(
                type="text",
                text="\n".join(response_parts)
            )]

        except ValueError as e:
            return [TextContent(
                type="text",
                text=f"Validation error: {e}"
            )]
        except Exception as e:
            import logging
            logger = logging.getLogger("engram.server.chainmind")
            logger.error(f"Error generating prompt: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error generating prompt: {type(e).__name__}: {e}"
            )]

    elif name == "chainmind_verify":
        # Verify response with alternative models
        try:
            from engram.chainmind_helper import get_helper
            import logging

            logger = logging.getLogger("engram.server.chainmind")

            # Input validation
            if "response" not in arguments:
                return [TextContent(
                    type="text",
                    text="Error: 'response' parameter is required"
                )]

            if "original_prompt" not in arguments:
                return [TextContent(
                    type="text",
                    text="Error: 'original_prompt' parameter is required"
                )]

            response = arguments["response"]
            original_prompt = arguments["original_prompt"]

            if not response or not response.strip():
                return [TextContent(
                    type="text",
                    text="Error: Response cannot be empty"
                )]

            if not original_prompt or not original_prompt.strip():
                return [TextContent(
                    type="text",
                    text="Error: Original prompt cannot be empty"
                )]

            verification_providers = arguments.get("verification_providers", ["openai"])
            confidence_threshold = arguments.get("confidence_threshold", 0.8)

            # Validate confidence threshold
            if not isinstance(confidence_threshold, (int, float)) or confidence_threshold < 0 or confidence_threshold > 1:
                return [TextContent(
                    type="text",
                    text=f"Error: confidence_threshold must be between 0 and 1, got {confidence_threshold}"
                )]

            # Validate verification providers
            if not isinstance(verification_providers, list) or not verification_providers:
                return [TextContent(
                    type="text",
                    text="Error: verification_providers must be a non-empty list"
                )]

            helper = get_helper()
            if not helper.is_available():
                return [TextContent(
                    type="text",
                    text="ChainMind helper not available. Check ChainMind installation."
                )]

            # Generate verification prompt
            verify_prompt = f"""Verify this response for accuracy and quality:

Original prompt: {original_prompt}

Response to verify: {response}

Please provide:
1. Accuracy score (0.0-1.0)
2. Quality assessment
3. Any concerns or improvements"""

            # Verify with first available provider
            verification_result = None
            verification_errors = []

            for provider in verification_providers:
                try:
                    result = await helper.generate(
                        prompt=verify_prompt,
                        prefer_claude=False,  # Don't use Claude for verification
                        fallback_providers=[p for p in verification_providers if p != provider],
                        temperature=0.3  # Lower temperature for verification
                    )
                    verification_result = result
                    break
                except Exception as e:
                    verification_errors.append(f"{provider}: {str(e)}")
                    logger.warning(f"Verification failed with {provider}: {e}")
                    continue

            if verification_result:
                response_parts = [
                    "## Verification Result",
                    "",
                    verification_result["response"],
                    ""
                ]

                # Add metadata
                metadata_parts = [f"Verified using: {verification_result['provider']}"]
                if "latency_seconds" in verification_result:
                    metadata_parts.append(f"Latency: {verification_result['latency_seconds']:.2f}s")
                response_parts.append(f"*{' | '.join(metadata_parts)}*")

                return [TextContent(
                    type="text",
                    text="\n".join(response_parts)
                )]
            else:
                error_details = "\n".join(f"- {e}" for e in verification_errors)
                return [TextContent(
                    type="text",
                    text=f"Verification failed: All verification providers unavailable\n\nErrors:\n{error_details}"
                )]

        except ValueError as e:
            return [TextContent(
                type="text",
                text=f"Validation error: {e}"
            )]
        except Exception as e:
            import logging
            logger = logging.getLogger("engram.server.chainmind")
            logger.error(f"Error verifying response: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error verifying response: {type(e).__name__}: {e}"
            )]

    elif name == "chainmind_generate_batch":
        # Generate text for multiple prompts in batch
        try:
            from engram.chainmind_helper import get_helper
            import logging

            logger = logging.getLogger("engram.server.chainmind")

            # Input validation
            if "prompts" not in arguments:
                return [TextContent(
                    type="text",
                    text="Error: 'prompts' parameter is required (list of prompts)"
                )]

            prompts = arguments["prompts"]
            if not isinstance(prompts, list) or not prompts:
                return [TextContent(
                    type="text",
                    text="Error: 'prompts' must be a non-empty list"
                )]

            if len(prompts) > 50:  # Reasonable limit
                return [TextContent(
                    type="text",
                    text=f"Error: Maximum 50 prompts per batch, got {len(prompts)}"
                )]

            # IMPORTANT: Claude Code already uses Claude API by default
            # Default to False: Skip Claude, go straight to OpenAI fallback
            prefer_claude = arguments.get("prefer_claude", False)
            fallback_providers = arguments.get("fallback_providers")
            temperature = arguments.get("temperature", 0.7)
            max_tokens = arguments.get("max_tokens")

            # Validate parameters
            if temperature is not None and (not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 2):
                return [TextContent(
                    type="text",
                    text=f"Error: Temperature must be between 0 and 2, got {temperature}"
                )]

            helper = get_helper()
            if not helper.is_available():
                return [TextContent(
                    type="text",
                    text="ChainMind helper not available. Check ChainMind installation."
                )]

            kwargs = {}
            if temperature is not None:
                kwargs["temperature"] = float(temperature)
            if max_tokens is not None:
                kwargs["max_tokens"] = int(max_tokens)

            results = await helper.generate_batch(
                prompts=prompts,
                prefer_claude=prefer_claude,
                fallback_providers=fallback_providers,
                **kwargs
            )

            # Format batch response
            response_parts = [
                f"# Batch Generation Results ({len(results)} prompts)",
                ""
            ]

            successful = sum(1 for r in results if "error" not in r)
            failed = len(results) - successful

            response_parts.append(f"**Summary:** {successful} successful, {failed} failed\n")

            for i, result in enumerate(results, 1):
                response_parts.append(f"## Prompt {i}")
                if "error" in result:
                    response_parts.append(f"❌ Error: {result['error']}")
                else:
                    response_parts.append(result["response"])
                    if result.get("fallback_used"):
                        response_parts.append(f"*[Used {result['provider']} (fallback)]*")
                response_parts.append("")

            return [TextContent(
                type="text",
                text="\n".join(response_parts)
            )]

        except ValueError as e:
            return [TextContent(
                type="text",
                text=f"Validation error: {e}"
            )]
        except Exception as e:
            import logging
            logger = logging.getLogger("engram.server.chainmind")
            logger.error(f"Error in batch generation: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error generating batch: {type(e).__name__}: {e}"
            )]

    else:
        return [TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]


# =============================================================================
# SERVER STARTUP
# =============================================================================

def serve():
    """Start the MCP server.

    This is called by Claude Code when it starts Engram.
    Uses stdio (standard input/output) to communicate.
    """
    import asyncio

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )

    asyncio.run(main())


if __name__ == "__main__":
    serve()
