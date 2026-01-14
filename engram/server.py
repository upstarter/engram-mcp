"""Engram MCP Server - Memory + Ollama routing."""

import os
import json
import asyncio
import aiohttp
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from engram.storage import MemoryStore

server = Server("engram")
_store: MemoryStore | None = None

def get_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store

CONTEXT_STATE_DIR = os.path.expanduser("~/.spc/projects/state")

def _get_context_from_files() -> tuple[str, str, str]:
    """Read role, project, agent_id from state files."""
    role = project = agent_id = ""

    role_file = os.path.join(CONTEXT_STATE_DIR, "current_role")
    if os.path.exists(role_file):
        try:
            with open(role_file) as f:
                role = f.read().strip()
        except Exception:
            pass

    project_file = os.path.normpath(os.path.join(CONTEXT_STATE_DIR, "..", "..", "active_project"))
    if os.path.exists(project_file):
        try:
            with open(project_file) as f:
                data = json.load(f)
                project = data.get("name", "").lower()
        except Exception:
            pass

    session_id_file = os.path.join(CONTEXT_STATE_DIR, "session_id")
    session_id = ""
    if os.path.exists(session_id_file):
        try:
            with open(session_id_file) as f:
                session_id = f.read().strip()
        except Exception:
            pass

    if role:
        agent_id = f"{role}:{session_id}" if session_id else role
    elif session_id:
        agent_id = session_id

    return role, project, agent_id


# =============================================================================
# OLLAMA ROUTING (from chainmind-router)
# =============================================================================

async def call_ollama(prompt: str, model: str = "llama3.1:8b", max_tokens: int = 1024) -> dict:
    """Call Ollama API directly."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.7},
    }
    async with aiohttp.ClientSession() as session:
        async with session.post("http://localhost:11434/api/chat", json=payload) as response:
            if response.status != 200:
                raise Exception(f"Ollama error: {await response.text()}")
            result = await response.json()
            return {
                "response": result.get("message", {}).get("content", "").strip(),
                "tokens": {"input": result.get("prompt_eval_count", 0), "output": result.get("eval_count", 0)},
                "eval_duration_ms": result.get("eval_duration", 0) / 1_000_000,
            }


def _should_use_ollama(prompt: str) -> tuple[bool, str]:
    """Quick check if Ollama can handle this prompt."""
    import re
    p = prompt.lower()

    # Hard NO for Ollama
    if any(x in p for x in ["write", "create", "implement", "build", "fix", "debug", "refactor"]):
        if any(x in p for x in ["function", "class", "code", "api", "component", "test"]):
            return False, "code generation"
    if re.search(r'```\w*\n.{100,}```', prompt, re.DOTALL):
        return False, "large code block"
    if any(x in p for x in ["json", "yaml", "config"]) and any(x in p for x in ["generate", "create", "give me"]):
        return False, "structured output"
    if any(x in p for x in ["design", "architect", "system", "database schema"]):
        return False, "system design"
    if any(x in p for x in ["fix that", "the bug", "we discussed", "above", "earlier"]):
        return False, "needs context"

    # YES for Ollama
    if any(x in p for x in ["what is", "who is", "when", "where", "define", "explain", "summarize", "translate"]):
        return True, "factual/simple"
    if len(prompt) < 200 and "?" in prompt:
        return True, "short question"

    return False, "uncertain"


# =============================================================================
# TOOL DEFINITIONS (MINIMAL DESCRIPTIONS)
# =============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="engram_remember",
            description="Store memory. Use confirmed=true after user approves preview.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "memory_type": {"type": "string", "enum": ["fact", "preference", "decision", "solution", "philosophy", "pattern"], "default": "fact"},
                    "importance": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.5},
                    "project": {"type": "string"},
                    "confirmed": {"type": "boolean", "default": False},
                    "reasoning": {"type": "string"},
                    "supersede": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="engram_recall",
            description="Search memories by query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                    "project": {"type": "string"},
                    "memory_types": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="engram_context",
            description="Get relevant context for current work.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 5}
                }
            }
        ),
        Tool(
            name="engram_related",
            description="Find memories by entity connection.",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string"},
                    "entity_type": {"type": "string", "enum": ["projects", "tools", "concepts", "episode"]},
                    "entity_name": {"type": "string"},
                    "limit": {"type": "integer", "default": 5}
                }
            }
        ),
        Tool(
            name="engram_consolidate",
            description="Find/merge similar memories. action=find_candidates or consolidate.",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["find_candidates", "consolidate"]},
                    "similarity_threshold": {"type": "number", "default": 0.85, "minimum": 0.5, "maximum": 0.99},
                    "memory_ids": {"type": "array", "items": {"type": "string"}},
                    "consolidated_content": {"type": "string"}
                },
                "required": ["action"]
            }
        ),
        Tool(
            name="engram_link",
            description="Create relationship between nodes. Types: supersedes, caused_by, blocked_by, requires, enables, similar_to, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_id": {"type": "string"},
                    "target_id": {"type": "string"},
                    "relation_type": {"type": "string", "enum": ["supersedes", "precedes", "evolved_from", "caused_by", "motivated_by", "resulted_in", "blocked_by", "triggered_by", "part_of", "contains", "instance_of", "phase_of", "requires", "enables", "blocks", "conflicts_with", "similar_to", "contradicts", "reinforces", "example_of"]},
                    "strength": {"type": "number", "minimum": 0, "maximum": 1, "default": 1.0},
                    "evidence": {"type": "string"}
                },
                "required": ["source_id", "target_id", "relation_type"]
            }
        ),
        Tool(
            name="engram_entity",
            description="Create entity node (goal, blocker, phase, pattern, etc).",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_type": {"type": "string", "enum": ["goal", "blocker", "phase", "pattern", "decision_point", "project", "tool", "concept"]},
                    "name": {"type": "string"},
                    "status": {"type": "string", "enum": ["active", "achieved", "abandoned"], "default": "active"},
                    "priority": {"type": "string", "enum": ["P0", "P1", "P2"]},
                    "description": {"type": "string"}
                },
                "required": ["entity_type", "name"]
            }
        ),
        Tool(
            name="engram_validate",
            description="Mark memory as validated/useful.",
            inputSchema={
                "type": "object",
                "properties": {"memory_id": {"type": "string"}},
                "required": ["memory_id"]
            }
        ),
        Tool(
            name="engram_graph",
            description="Query graph: blockers, requirements, contradictions, hubs, visualize, stats.",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["blockers", "requirements", "contradictions", "hubs", "visualize", "stats"]},
                    "target": {"type": "string"},
                    "target_type": {"type": "string", "enum": ["goal", "phase", "memory"], "default": "goal"},
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["action"]
            }
        ),
        Tool(
            name="smart_complete",
            description="Route to Ollama for simple queries (saves tokens). Returns defer_to_claude if complex.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "max_tokens": {"type": "integer", "default": 1024},
                    "model": {"type": "string", "default": "auto"},
                    "force_local": {"type": "boolean", "default": False}
                },
                "required": ["prompt"]
            }
        ),
    ]


# =============================================================================
# TOOL HANDLERS
# =============================================================================

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    store = get_store()
    cwd = os.getcwd()
    current_role, current_project, current_agent_id = _get_context_from_files()

    if name == "engram_remember":
        confirmed = arguments.get("confirmed", False)
        content = arguments["content"]
        memory_type = arguments.get("memory_type", "fact")
        importance = arguments.get("importance", 0.5)
        reasoning = arguments.get("reasoning", "")
        project = arguments.get("project")
        supersede = arguments.get("supersede", [])

        if not confirmed:
            lines = ["## Memory Preview\n"]
            lines.append(f"**Type:** {memory_type} | **Importance:** {importance:.0%}")
            if project:
                lines.append(f" | **Project:** {project}")
            lines.append(f"\n\n> {content}\n")
            if reasoning:
                lines.append(f"**Why:** {reasoning}\n")

            similar = store.recall(query=content, limit=3, memory_types=None)
            if similar:
                lines.append("### Similar Existing")
                for mem in similar:
                    r = mem.get('relevance', 0)
                    lines.append(f"- `{mem['id']}` ({r:.0%}): {mem['content'][:60]}...")
                if similar[0].get('relevance', 0) > 0.85:
                    lines.append(f"\n⚠️ Consider `supersede=['{similar[0]['id']}']`")

            lines.append("\n---\nCall with `confirmed=true` to store.")
            return [TextContent(type="text", text="\n".join(lines))]
        else:
            result = store.remember(
                content=content, memory_type=memory_type, importance=importance,
                project=project, source_role=current_role or None,
                check_conflicts=False, supersede=supersede,
            )
            return [TextContent(type="text", text=f"✅ Stored: {result}")]

    elif name == "engram_recall":
        memories = store.recall(
            query=arguments["query"],
            limit=arguments.get("limit", 5),
            project=arguments.get("project"),
            memory_types=arguments.get("memory_types"),
            current_role=current_role,
        )
        if not memories:
            return [TextContent(type="text", text=f"No memories found for: {arguments['query']}")]

        lines = [f"Found {len(memories)}:\n"]
        for i, mem in enumerate(memories, 1):
            lines.append(f"{i}. [{mem['memory_type']}] ({mem['relevance']:.0%}) {mem['content'][:80]}...")
        return [TextContent(type="text", text="\n".join(lines))]

    elif name == "engram_context":
        base_query = arguments.get("query", "current work")
        query_parts = [base_query]
        if current_role:
            query_parts.append(current_role)
        enhanced_query = " ".join(query_parts)

        memories = store.context(query=enhanced_query, cwd=cwd, limit=arguments.get("limit", 5), current_role=current_role)
        if not memories:
            return [TextContent(type="text", text=f"No context found. Role: {current_role or 'none'}")]

        lines = ["## Context\n"]
        by_type: dict = {}
        for mem in memories:
            t = mem["memory_type"]
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(mem)

        for mem_type, mems in by_type.items():
            lines.append(f"### {mem_type.title()}s")
            for mem in mems:
                lines.append(f"- {mem['content']}")
        return [TextContent(type="text", text="\n".join(lines))]

    elif name == "engram_related":
        memory_id = arguments.get("memory_id")
        entity_type = arguments.get("entity_type")
        entity_name = arguments.get("entity_name")
        limit = arguments.get("limit", 5)

        if not store.graph:
            return [TextContent(type="text", text="Graph not available")]

        if memory_id:
            memories = store.related(memory_id, limit=limit)
            header = f"Related to {memory_id}"
        elif entity_type and entity_name:
            memories = store.get_by_entity(entity_type, entity_name, limit=limit)
            header = f"{entity_type}: {entity_name}"
        else:
            return [TextContent(type="text", text="Provide memory_id OR (entity_type AND entity_name)")]

        if not memories:
            return [TextContent(type="text", text=f"No memories found for {header}")]

        lines = [f"{header}\n"]
        for i, mem in enumerate(memories, 1):
            lines.append(f"{i}. [{mem['memory_type']}] {mem['content'][:60]}...")
        return [TextContent(type="text", text="\n".join(lines))]

    elif name == "engram_consolidate":
        action = arguments.get("action")
        if action == "find_candidates":
            clusters = store.find_consolidation_candidates(
                similarity_threshold=arguments.get("similarity_threshold", 0.85),
                min_cluster_size=3,
            )
            if not clusters:
                return [TextContent(type="text", text="No clusters found. Try lower threshold.")]
            lines = [f"Found {len(clusters)} clusters:\n"]
            for i, c in enumerate(clusters, 1):
                lines.append(f"### {c['topic']} ({c['count']} memories)")
                for mem in c["memories"][:3]:
                    lines.append(f"- `{mem['id']}`: {mem['content'][:50]}...")
            return [TextContent(type="text", text="\n".join(lines))]
        elif action == "consolidate":
            memory_ids = arguments.get("memory_ids")
            content = arguments.get("consolidated_content")
            if not memory_ids or not content:
                return [TextContent(type="text", text="Need memory_ids and consolidated_content")]
            new_id = store.consolidate(memory_ids=memory_ids, consolidated_content=content, memory_type="pattern", importance=0.8)
            return [TextContent(type="text", text=f"✓ Consolidated into: {new_id}")]
        return [TextContent(type="text", text="action must be find_candidates or consolidate")]

    elif name == "engram_link":
        success = store.add_relationship(
            source_id=arguments["source_id"],
            target_id=arguments["target_id"],
            relation_type=arguments["relation_type"],
            strength=arguments.get("strength", 1.0),
            evidence=arguments.get("evidence"),
        )
        if success:
            return [TextContent(type="text", text=f"✓ {arguments['source_id']} --{arguments['relation_type']}--> {arguments['target_id']}")]
        return [TextContent(type="text", text="✗ Failed to link")]

    elif name == "engram_entity":
        entity_id = store.add_entity(
            entity_type=arguments["entity_type"],
            name=arguments["name"],
            status=arguments.get("status", "active"),
            priority=arguments.get("priority"),
            description=arguments.get("description"),
        )
        if entity_id:
            return [TextContent(type="text", text=f"✓ Entity: {entity_id}")]
        return [TextContent(type="text", text="✗ Failed")]

    elif name == "engram_validate":
        success = store.validate_memory(arguments["memory_id"])
        if success:
            return [TextContent(type="text", text=f"✓ Validated: {arguments['memory_id']}")]
        return [TextContent(type="text", text="✗ Failed")]

    elif name == "engram_graph":
        action = arguments.get("action")
        target = arguments.get("target")
        target_type = arguments.get("target_type", "goal")
        limit = arguments.get("limit", 10)

        if action == "blockers":
            if not target:
                return [TextContent(type="text", text="Need target")]
            blockers = store.get_blockers(target)
            if not blockers:
                return [TextContent(type="text", text=f"No blockers for: {target}")]
            lines = [f"Blockers for {target}:"]
            for b in blockers:
                lines.append(f"- {b['name']} ({b['strength']:.0%})")
            return [TextContent(type="text", text="\n".join(lines))]
        elif action == "requirements":
            if not target:
                return [TextContent(type="text", text="Need target")]
            reqs = store.get_requirements(target, target_type)
            if not reqs:
                return [TextContent(type="text", text=f"No requirements for: {target}")]
            lines = [f"Requirements for {target}:"]
            for r in reqs:
                lines.append(f"- [{r['type']}] {r['name']}")
            return [TextContent(type="text", text="\n".join(lines))]
        elif action == "hubs":
            hubs = store.get_hub_entities(limit)
            if not hubs:
                return [TextContent(type="text", text="No entities")]
            lines = ["Most connected:"]
            for h in hubs:
                lines.append(f"- [{h['type']}] {h['name']}: {h['connections']}")
            return [TextContent(type="text", text="\n".join(lines))]
        elif action == "visualize":
            if not target:
                return [TextContent(type="text", text="Need target")]
            viz = store.visualize_memory(target)
            return [TextContent(type="text", text=f"```\n{viz}\n```")]
        elif action == "stats":
            stats = store.get_stats()
            g = stats.get("graph", {})
            return [TextContent(type="text", text=f"Nodes: {g.get('total_nodes', 0)} | Edges: {g.get('total_edges', 0)}")]
        return [TextContent(type="text", text=f"Unknown action: {action}")]

    elif name == "smart_complete":
        prompt = arguments.get("prompt", "")
        max_tokens = arguments.get("max_tokens", 1024)
        model_override = arguments.get("model", "auto")
        force_local = arguments.get("force_local", False)

        use_local, reason = _should_use_ollama(prompt)
        use_local = use_local or force_local

        if not use_local and model_override == "auto":
            return [TextContent(type="text", text=json.dumps({
                "status": "defer_to_claude",
                "reason": reason,
            }, indent=2))]

        model = model_override if model_override != "auto" else "llama3.1:8b"
        try:
            result = await call_ollama(prompt, model=model, max_tokens=max_tokens)
            return [TextContent(type="text", text=json.dumps({
                "status": "completed",
                "model": model,
                "response": result["response"],
                "tokens": result["tokens"],
                "latency_ms": result["eval_duration_ms"],
            }, indent=2))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({
                "status": "error",
                "error": str(e),
                "fallback": "defer_to_claude",
            }, indent=2))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


def serve():
    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    asyncio.run(main())


if __name__ == "__main__":
    serve()
