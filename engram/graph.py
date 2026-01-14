"""
Knowledge Graph Layer v2 - Rich Entity Relationships.

This adds semantic relationships beyond simple "mentions" to enable:
- Temporal tracking (supersedes, precedes, evolved_from)
- Causal reasoning (caused_by, motivated_by, resulted_in, blocked_by)
- Structural navigation (part_of, contains, instance_of, phase_of)
- Dependency analysis (requires, enables, blocks, conflicts_with)
- Semantic connections (similar_to, related_to, contradicts, reinforces)

The graph becomes Eric's "externalized executive function" - tracking priorities,
maintaining focus, learning from outcomes, and preventing repeated mistakes.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass, field, asdict
from enum import Enum

import networkx as nx


# =============================================================================
# RELATIONSHIP TYPES
# =============================================================================

class RelationType(str, Enum):
    """All supported relationship types organized by family."""

    # Implicit (auto-extracted)
    MENTIONS = "mentions"

    # Temporal - track currency and evolution
    SUPERSEDES = "supersedes"        # memory → memory (new replaces old)
    PRECEDES = "precedes"            # memory → memory (happened before)
    EVOLVED_FROM = "evolved_from"    # memory → memory (thinking evolved)
    ACTIVE_DURING = "active_during"  # memory → episode (temporal scope)

    # Causal - understand why
    CAUSED_BY = "caused_by"          # outcome → decision/action
    MOTIVATED_BY = "motivated_by"    # decision → philosophy/goal
    RESULTED_IN = "resulted_in"      # action → outcome
    BLOCKED_BY = "blocked_by"        # goal → blocker
    ENABLED_BY = "enabled_by"        # achievement → enabler
    TRIGGERED_BY = "triggered_by"    # blocker → situation

    # Structural - navigate hierarchy
    PART_OF = "part_of"              # component → whole
    CONTAINS = "contains"            # whole → component
    INSTANCE_OF = "instance_of"      # specific → general
    PHASE_OF = "phase_of"            # phase → workflow
    VERSION_OF = "version_of"        # variant → original

    # Dependency - critical path
    REQUIRES = "requires"            # task → prerequisite
    ENABLES = "enables"              # enabler → enabled
    BLOCKS = "blocks"                # blocker → blocked
    CONFLICTS_WITH = "conflicts_with"  # item → item
    DEPENDS_ON = "depends_on"        # downstream → upstream

    # Semantic - find relevance
    SIMILAR_TO = "similar_to"        # memory → memory (consolidation candidates)
    RELATED_TO = "related_to"        # entity → entity
    EXAMPLE_OF = "example_of"        # specific → pattern
    CONTRADICTS = "contradicts"      # memory → memory (conflict)
    REINFORCES = "reinforces"        # memory → memory (validates)
    APPLIES_TO = "applies_to"        # pattern → context


class EntityType(str, Enum):
    """All supported entity types."""
    PROJECT = "project"
    EPISODE = "episode"
    PHASE = "phase"
    TOOL = "tool"
    CONCEPT = "concept"
    GOAL = "goal"
    BLOCKER = "blocker"
    PATTERN = "pattern"
    DECISION_POINT = "decision_point"
    PERSON = "person"


class MemoryStatus(str, Enum):
    """Memory lifecycle status."""
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    EXPERIMENTAL = "experimental"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class EdgeAttributes:
    """Rich attributes for graph edges."""
    edge_type: str
    strength: float = 1.0           # 0.0-1.0 relationship strength
    confidence: float = 1.0         # 0.0-1.0 confidence this is accurate
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = "auto"        # auto, claude, eric
    evidence: Optional[str] = None  # memory ID supporting this edge
    bidirectional: bool = False     # Should reverse edge be implied?

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MemoryNode:
    """Rich attributes for memory nodes."""
    id: str
    memory_type: str
    project: Optional[str] = None
    source_role: Optional[str] = None  # Agent role that created this memory
    status: str = "active"
    confidence: float = 0.5         # How validated is this?
    impact: str = "medium"          # high, medium, low
    validation_count: int = 0       # Times proven useful
    last_validated: Optional[str] = None
    trigger_context: Optional[str] = None  # When to surface this
    domains: list = field(default_factory=list)  # What contexts apply

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EntityNode:
    """Rich attributes for entity nodes."""
    id: str
    entity_type: str
    name: str
    status: str = "active"          # active, achieved, abandoned
    priority: Optional[str] = None  # P0, P1, P2
    description: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


# =============================================================================
# KNOWLEDGE GRAPH CLASS
# =============================================================================

class KnowledgeGraph:
    """
    Rich knowledge graph with semantic relationships.

    Node types:
    - memory: A stored memory with rich attributes
    - entity: Projects, tools, concepts, goals, blockers, etc.

    Edge types: See RelationType enum (15 relationship types + mentions)
    """

    # Known entities to always extract
    KNOWN_ENTITIES = {
        EntityType.PROJECT: [
            "CHANNEL", "studioflow", "avatar-factory", "engram", "engram-mcp",
            "hallo2", "chatterbox", "ai-products", "creator-ai-ecosystem",
        ],
        EntityType.TOOL: [
            "proj", "sf", "ks", "engram-bridge", "resolve", "kitty",
            "claude", "git", "docker", "ffmpeg", "whisper",
        ],
        EntityType.CONCEPT: [
            "episode", "script", "teleprompter", "recording",
            "post-production", "publishing", "MVP", "shipping", "retention",
            "hook", "thumbnail", "monetization",
        ],
        EntityType.PHASE: [
            "research", "scripting", "recording", "editing", "publishing",
            "pre-production", "post-production",
        ],
        EntityType.GOAL: [
            "monetization", "consistent publishing", "product launch",
        ],
        EntityType.BLOCKER: [
            "shiny object syndrome", "perfectionism", "scope creep",
            "context switching", "decision paralysis",
        ],
        EntityType.DECISION_POINT: [
            "new idea arrives", "stuck on task", "feature request",
            "tool choice", "architecture decision",
        ],
    }

    # Regex patterns for entity extraction
    ENTITY_PATTERNS = {
        EntityType.EPISODE: r"EP\d{3}(?:[_\-][\w-]+)?",
    }

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize the knowledge graph."""
        if data_dir is None:
            data_dir = Path.home() / ".engram" / "data"
        self.data_dir = Path(data_dir)
        self.graph_path = self.data_dir / "knowledge_graph.json"

        # Load or create graph
        self.graph = self._load_graph()

        # Clean up any garbage entities on load
        self._cleanup_garbage_entities()

    def _load_graph(self) -> nx.DiGraph:
        """Load graph from disk or create new."""
        if self.graph_path.exists():
            try:
                with open(self.graph_path) as f:
                    data = json.load(f)
                return nx.node_link_graph(data, edges="links")
            except Exception:
                pass
        return nx.DiGraph()

    def save(self):
        """Persist graph to disk."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        data = nx.node_link_data(self.graph, edges="links")
        with open(self.graph_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _cleanup_garbage_entities(self):
        """Remove malformed entities (like regex patterns that leaked in)."""
        garbage = []
        for node_id in self.graph.nodes:
            if node_id.startswith("entity:"):
                # Check for regex garbage
                if "(?P<" in node_id or "[^" in node_id or "\\d" in node_id:
                    garbage.append(node_id)
                # Check for empty or malformed names
                node_data = self.graph.nodes[node_id]
                name = node_data.get("name", "")
                if not name or len(name) < 2 or "(?P<" in name:
                    garbage.append(node_id)

        for node_id in set(garbage):
            self.graph.remove_node(node_id)

        if garbage:
            self.save()

    # =========================================================================
    # ENTITY EXTRACTION
    # =========================================================================

    def extract_entities(self, text: str) -> list[tuple[EntityType, str]]:
        """
        Extract entities from text.

        Returns list of (entity_type, entity_name) tuples.
        """
        entities = []
        text_lower = text.lower()

        # Extract from known entity lists
        for entity_type, entity_list in self.KNOWN_ENTITIES.items():
            if isinstance(entity_list, list):
                for entity in entity_list:
                    if entity.lower() in text_lower:
                        entities.append((entity_type, entity))

        # Extract from regex patterns
        for entity_type, pattern in self.ENTITY_PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                entities.append((entity_type, match.upper()))

        # Extract project references from paths
        path_matches = re.findall(r'/mnt/dev/(?:ai|video)/([^/\s]+)', text)
        for match in path_matches:
            if len(match) > 2 and not re.match(r'^[\d_]+$', match):
                entities.append((EntityType.PROJECT, match))

        # Dedupe while preserving order
        seen = set()
        unique = []
        for e in entities:
            key = (e[0], e[1].lower())
            if key not in seen:
                seen.add(key)
                unique.append(e)

        return unique

    def _make_entity_id(self, entity_type: EntityType, name: str) -> str:
        """Create consistent entity ID."""
        return f"entity:{entity_type.value}:{name.lower()}"

    # =========================================================================
    # NODE OPERATIONS
    # =========================================================================

    def add_memory(
        self,
        memory_id: str,
        content: str,
        memory_type: str,
        project: Optional[str] = None,
        source_role: Optional[str] = None,
        status: str = "active",
        confidence: float = 0.5,
        impact: str = "medium",
        trigger_context: Optional[str] = None,
        domains: Optional[list] = None,
    ) -> list[tuple[EntityType, str]]:
        """
        Add a memory to the graph with extracted entities.

        Creates:
        - Memory node with rich attributes
        - Entity nodes for each extracted entity
        - 'mentions' edges from memory to entities
        """
        # Create memory node with rich attributes
        node_attrs = MemoryNode(
            id=memory_id,
            memory_type=memory_type,
            project=project,
            source_role=source_role,
            status=status,
            confidence=confidence,
            impact=impact,
            validation_count=0,
            trigger_context=trigger_context,
            domains=domains or [],
        )

        self.graph.add_node(memory_id, node_type="memory", **node_attrs.to_dict())

        # Extract and link entities
        entities = self.extract_entities(content)

        # Also add project as entity if specified
        if project:
            entities.append((EntityType.PROJECT, project))

        for entity_type, entity_name in entities:
            entity_id = self._make_entity_id(entity_type, entity_name)

            # Add entity node if not exists
            if not self.graph.has_node(entity_id):
                entity_attrs = EntityNode(
                    id=entity_id,
                    entity_type=entity_type.value,
                    name=entity_name,
                )
                self.graph.add_node(entity_id, node_type="entity", **entity_attrs.to_dict())

            # Add 'mentions' edge with attributes
            edge_attrs = EdgeAttributes(
                edge_type=RelationType.MENTIONS.value,
                strength=0.5,  # Weak implicit relationship
                created_by="auto",
            )
            self.graph.add_edge(memory_id, entity_id, **edge_attrs.to_dict())

        self.save()
        return entities

    def add_entity(
        self,
        entity_type: EntityType,
        name: str,
        status: str = "active",
        priority: Optional[str] = None,
        description: Optional[str] = None,
    ) -> str:
        """Add a standalone entity node."""
        entity_id = self._make_entity_id(entity_type, name)

        entity_attrs = EntityNode(
            id=entity_id,
            entity_type=entity_type.value,
            name=name,
            status=status,
            priority=priority,
            description=description,
        )

        self.graph.add_node(entity_id, node_type="entity", **entity_attrs.to_dict())
        self.save()
        return entity_id

    def update_memory_status(self, memory_id: str, status: MemoryStatus):
        """Update a memory's status."""
        if self.graph.has_node(memory_id):
            self.graph.nodes[memory_id]["status"] = status.value
            self.save()

    def validate_memory(self, memory_id: str):
        """Record that a memory was validated as useful."""
        if self.graph.has_node(memory_id):
            node = self.graph.nodes[memory_id]
            node["validation_count"] = node.get("validation_count", 0) + 1
            node["last_validated"] = datetime.now().isoformat()

            # Boost confidence based on validations
            validations = node["validation_count"]
            node["confidence"] = min(0.95, 0.5 + (0.1 * validations))

            self.save()

    # =========================================================================
    # RELATIONSHIP OPERATIONS
    # =========================================================================

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        strength: float = 1.0,
        confidence: float = 1.0,
        created_by: str = "claude",
        evidence: Optional[str] = None,
        bidirectional: bool = False,
    ) -> bool:
        """
        Add a semantic relationship between nodes.

        Args:
            source_id: Source node ID (memory or entity)
            target_id: Target node ID (memory or entity)
            relation_type: Type of relationship
            strength: How strong is this relationship (0.0-1.0)
            confidence: How confident are we this is accurate (0.0-1.0)
            created_by: Who created this (auto, claude, eric)
            evidence: Memory ID that supports this relationship
            bidirectional: Create reverse edge too?

        Returns:
            True if relationship was added
        """
        if not self.graph.has_node(source_id):
            return False
        if not self.graph.has_node(target_id):
            return False

        edge_attrs = EdgeAttributes(
            edge_type=relation_type.value,
            strength=strength,
            confidence=confidence,
            created_by=created_by,
            evidence=evidence,
            bidirectional=bidirectional,
        )

        self.graph.add_edge(source_id, target_id, **edge_attrs.to_dict())

        # Add reverse edge if bidirectional
        if bidirectional:
            reverse_type = self._get_reverse_relation(relation_type)
            if reverse_type:
                reverse_attrs = EdgeAttributes(
                    edge_type=reverse_type.value,
                    strength=strength,
                    confidence=confidence,
                    created_by=created_by,
                    evidence=evidence,
                    bidirectional=True,
                )
                self.graph.add_edge(target_id, source_id, **reverse_attrs.to_dict())

        self.save()
        return True

    def _get_reverse_relation(self, relation: RelationType) -> Optional[RelationType]:
        """Get the reverse relationship type if applicable."""
        reverses = {
            RelationType.PART_OF: RelationType.CONTAINS,
            RelationType.CONTAINS: RelationType.PART_OF,
            RelationType.REQUIRES: RelationType.ENABLES,
            RelationType.ENABLES: RelationType.REQUIRES,
            RelationType.BLOCKS: RelationType.BLOCKED_BY,
            RelationType.BLOCKED_BY: RelationType.BLOCKS,
            RelationType.SUPERSEDES: RelationType.PRECEDES,
            RelationType.CAUSED_BY: RelationType.RESULTED_IN,
            RelationType.RESULTED_IN: RelationType.CAUSED_BY,
        }
        return reverses.get(relation)

    def supersede(self, new_memory_id: str, old_memory_id: str):
        """Mark new memory as superseding old one."""
        self.add_relationship(
            new_memory_id,
            old_memory_id,
            RelationType.SUPERSEDES,
            strength=1.0,
            confidence=1.0,
            created_by="auto",
        )
        self.update_memory_status(old_memory_id, MemoryStatus.SUPERSEDED)

    # =========================================================================
    # QUERY OPERATIONS
    # =========================================================================

    def get_related_memories(
        self,
        memory_id: str,
        relation_types: Optional[list[RelationType]] = None,
        depth: int = 2,
    ) -> list[dict]:
        """
        Find memories related to a given memory.

        Args:
            memory_id: Starting memory
            relation_types: Filter to specific relationship types (None = all)
            depth: How deep to traverse

        Returns:
            List of related memories with relationship info
        """
        if not self.graph.has_node(memory_id):
            return []

        related = {}  # memory_id -> {score, relationships}

        # Get entities mentioned by this memory
        entities = [
            n for n in self.graph.successors(memory_id)
            if self.graph.nodes[n].get("node_type") == "entity"
        ]

        # Find other memories mentioning same entities
        for entity_id in entities:
            for node in self.graph.predecessors(entity_id):
                if node != memory_id and self.graph.nodes[node].get("node_type") == "memory":
                    if node not in related:
                        related[node] = {"score": 0, "via": []}
                    related[node]["score"] += 1
                    entity_name = self.graph.nodes[entity_id].get("name", entity_id)
                    related[node]["via"].append(f"mentions:{entity_name}")

        # Also check direct relationships
        for successor in self.graph.successors(memory_id):
            if self.graph.nodes[successor].get("node_type") == "memory":
                edge_data = self.graph.edges[memory_id, successor]
                edge_type = edge_data.get("edge_type", "relates")

                if relation_types and edge_type not in [r.value for r in relation_types]:
                    continue

                if successor not in related:
                    related[successor] = {"score": 0, "via": []}
                related[successor]["score"] += edge_data.get("strength", 1.0) * 2
                related[successor]["via"].append(edge_type)

        for predecessor in self.graph.predecessors(memory_id):
            if self.graph.nodes[predecessor].get("node_type") == "memory":
                edge_data = self.graph.edges[predecessor, memory_id]
                edge_type = edge_data.get("edge_type", "relates")

                if relation_types and edge_type not in [r.value for r in relation_types]:
                    continue

                if predecessor not in related:
                    related[predecessor] = {"score": 0, "via": []}
                related[predecessor]["score"] += edge_data.get("strength", 1.0) * 2
                related[predecessor]["via"].append(f"←{edge_type}")

        # Sort by score
        sorted_related = sorted(related.items(), key=lambda x: x[1]["score"], reverse=True)

        return [
            {"memory_id": mem_id, "score": info["score"], "relationships": info["via"]}
            for mem_id, info in sorted_related
        ]

    def get_memories_by_entity(
        self,
        entity_type: EntityType,
        entity_name: str,
    ) -> list[str]:
        """Find all memories that mention a specific entity."""
        entity_id = self._make_entity_id(entity_type, entity_name)

        if not self.graph.has_node(entity_id):
            return []

        return [
            n for n in self.graph.predecessors(entity_id)
            if self.graph.nodes[n].get("node_type") == "memory"
        ]

    def get_active_memories(self, project: Optional[str] = None) -> list[str]:
        """Get all active (non-superseded) memories."""
        active = []
        for node_id in self.graph.nodes:
            node = self.graph.nodes[node_id]
            if node.get("node_type") != "memory":
                continue
            if node.get("status", "active") != "active":
                continue
            if project and node.get("project") != project:
                continue
            active.append(node_id)
        return active

    def get_superseded_by(self, memory_id: str) -> Optional[str]:
        """Find what memory superseded this one, if any."""
        for predecessor in self.graph.predecessors(memory_id):
            edge_data = self.graph.edges[predecessor, memory_id]
            if edge_data.get("edge_type") == RelationType.SUPERSEDES.value:
                return predecessor
        return None

    def get_current_version(self, memory_id: str) -> str:
        """Follow supersedes chain to find current version."""
        current = memory_id
        visited = {current}

        while True:
            superseded_by = None
            for predecessor in self.graph.predecessors(current):
                edge_data = self.graph.edges[predecessor, current]
                if edge_data.get("edge_type") == RelationType.SUPERSEDES.value:
                    superseded_by = predecessor
                    break

            if superseded_by and superseded_by not in visited:
                current = superseded_by
                visited.add(current)
            else:
                break

        return current

    def get_blockers_for(self, goal_entity_id: str) -> list[dict]:
        """Get all blockers for a goal."""
        blockers = []

        # Check if node exists first
        if not self.graph.has_node(goal_entity_id):
            return blockers

        for predecessor in self.graph.predecessors(goal_entity_id):
            edge_data = self.graph.edges[predecessor, goal_entity_id]
            if edge_data.get("edge_type") == RelationType.BLOCKS.value:
                node = self.graph.nodes[predecessor]
                blockers.append({
                    "id": predecessor,
                    "name": node.get("name", predecessor),
                    "strength": edge_data.get("strength", 1.0),
                })

        return blockers

    def get_requirements_for(self, task_id: str) -> list[dict]:
        """Get all prerequisites for a task/phase."""
        requirements = []

        # Check if node exists first
        if not self.graph.has_node(task_id):
            return requirements

        for successor in self.graph.successors(task_id):
            edge_data = self.graph.edges[task_id, successor]
            if edge_data.get("edge_type") == RelationType.REQUIRES.value:
                node = self.graph.nodes[successor]
                requirements.append({
                    "id": successor,
                    "name": node.get("name", successor),
                    "type": node.get("entity_type", node.get("node_type")),
                })

        return requirements

    def find_contradictions(self, memory_id: str) -> list[str]:
        """Find memories that contradict this one."""
        contradictions = []

        for successor in self.graph.successors(memory_id):
            edge_data = self.graph.edges[memory_id, successor]
            if edge_data.get("edge_type") == RelationType.CONTRADICTS.value:
                contradictions.append(successor)

        for predecessor in self.graph.predecessors(memory_id):
            edge_data = self.graph.edges[predecessor, memory_id]
            if edge_data.get("edge_type") == RelationType.CONTRADICTS.value:
                contradictions.append(predecessor)

        return list(set(contradictions))

    def get_validation_history(self, memory_id: str) -> dict:
        """Get validation info for a memory."""
        if not self.graph.has_node(memory_id):
            return {}

        node = self.graph.nodes[memory_id]
        return {
            "validation_count": node.get("validation_count", 0),
            "confidence": node.get("confidence", 0.5),
            "last_validated": node.get("last_validated"),
            "status": node.get("status", "active"),
        }

    # =========================================================================
    # GRAPH ANALYSIS
    # =========================================================================

    def get_entity_connections(
        self,
        entity_type: EntityType,
        entity_name: str,
    ) -> dict:
        """Get all entities connected to a given entity through shared memories."""
        entity_id = self._make_entity_id(entity_type, entity_name)

        if not self.graph.has_node(entity_id):
            return {}

        connections = {}
        memories = self.get_memories_by_entity(entity_type, entity_name)

        for mem_id in memories:
            for node in self.graph.successors(mem_id):
                if node != entity_id and self.graph.nodes[node].get("node_type") == "entity":
                    connections[node] = connections.get(node, 0) + 1

        return connections

    def find_path(self, source_id: str, target_id: str) -> list[str]:
        """Find shortest path between two nodes."""
        try:
            path = nx.shortest_path(
                self.graph.to_undirected(),
                source_id,
                target_id,
            )
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def get_hub_entities(self, limit: int = 10) -> list[dict]:
        """Find most connected entities (hubs)."""
        entity_degrees = []

        for node_id in self.graph.nodes:
            node = self.graph.nodes[node_id]
            if node.get("node_type") == "entity":
                degree = self.graph.in_degree(node_id) + self.graph.out_degree(node_id)
                entity_degrees.append({
                    "id": node_id,
                    "name": node.get("name", node_id),
                    "type": node.get("entity_type", "unknown"),
                    "connections": degree,
                })

        entity_degrees.sort(key=lambda x: x["connections"], reverse=True)
        return entity_degrees[:limit]

    def get_stats(self) -> dict:
        """Get comprehensive graph statistics."""
        memory_nodes = []
        entity_nodes = []

        for node_id in self.graph.nodes:
            node = self.graph.nodes[node_id]
            if node.get("node_type") == "memory":
                memory_nodes.append(node_id)
            elif node.get("node_type") == "entity":
                entity_nodes.append(node_id)

        # Entity type breakdown
        entity_types = {}
        for node_id in entity_nodes:
            etype = self.graph.nodes[node_id].get("entity_type", "unknown")
            entity_types[etype] = entity_types.get(etype, 0) + 1

        # Edge type breakdown
        edge_types = {}
        for u, v in self.graph.edges:
            etype = self.graph.edges[u, v].get("edge_type", "unknown")
            edge_types[etype] = edge_types.get(etype, 0) + 1

        # Memory status breakdown
        memory_status = {}
        for node_id in memory_nodes:
            status = self.graph.nodes[node_id].get("status", "active")
            memory_status[status] = memory_status.get(status, 0) + 1

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "memory_count": len(memory_nodes),
            "entity_count": len(entity_nodes),
            "entity_types": entity_types,
            "edge_types": edge_types,
            "memory_status": memory_status,
        }

    # =========================================================================
    # VISUALIZATION
    # =========================================================================

    def visualize_neighborhood(self, node_id: str, depth: int = 1) -> str:
        """Generate ASCII visualization of a node's neighborhood."""
        if not self.graph.has_node(node_id):
            return f"Node not found: {node_id}"

        lines = []
        node_data = self.graph.nodes[node_id]
        node_type = node_data.get("node_type", "unknown")

        # Center node
        if node_type == "memory":
            status = node_data.get("status", "active")
            lines.append(f"[MEMORY:{status.upper()}] {node_id}")
        else:
            name = node_data.get("name", node_id)
            etype = node_data.get("entity_type", "?")
            lines.append(f"[{etype.upper()}] {name}")

        lines.append("│")

        # Outgoing connections (grouped by edge type)
        out_edges = {}
        for succ in self.graph.successors(node_id):
            edge_data = self.graph.edges[node_id, succ]
            edge_type = edge_data.get("edge_type", "relates")
            if edge_type not in out_edges:
                out_edges[edge_type] = []
            out_edges[edge_type].append(succ)

        for edge_type, targets in out_edges.items():
            lines.append(f"├── {edge_type}:")
            for i, target in enumerate(targets[:5]):
                prefix = "│   └──" if i == len(targets[:5]) - 1 else "│   ├──"
                target_data = self.graph.nodes[target]
                if target_data.get("node_type") == "entity":
                    name = target_data.get("name", target)
                    etype = target_data.get("entity_type", "?")
                    lines.append(f"{prefix} [{etype}] {name}")
                else:
                    lines.append(f"{prefix} {target}")
            if len(targets) > 5:
                lines.append(f"│   └── ... and {len(targets) - 5} more")

        # Incoming connections
        in_edges = {}
        for pred in self.graph.predecessors(node_id):
            edge_data = self.graph.edges[pred, node_id]
            edge_type = edge_data.get("edge_type", "relates")
            if edge_type not in in_edges:
                in_edges[edge_type] = []
            in_edges[edge_type].append(pred)

        if in_edges:
            lines.append("│")
            for edge_type, sources in in_edges.items():
                lines.append(f"└── ←{edge_type}:")
                for i, source in enumerate(sources[:5]):
                    prefix = "    └──" if i == len(sources[:5]) - 1 else "    ├──"
                    lines.append(f"{prefix} {source}")
                if len(sources) > 5:
                    lines.append(f"    └── ... and {len(sources) - 5} more")

        return "\n".join(lines)
