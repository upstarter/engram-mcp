"""
Storage Layer - Where memories live.

Think of this like a filing system with two parts:
1. SQLite = A filing cabinet (stores the actual text, dates, labels)
2. ChromaDB = A smart index (finds similar memories by meaning)

When you store a memory:
1. Save the text in SQLite (the filing cabinet)
2. Convert text to numbers (embedding) and save in ChromaDB (the index)

When you search for a memory:
1. Convert your question to numbers
2. ChromaDB finds similar numbers (similar meanings)
3. SQLite gives you the full memory details
"""

import sqlite3
import uuid
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings

# Import graph layer (optional - graceful fallback if networkx not installed)
try:
    from engram.graph import (
        KnowledgeGraph,
        RelationType,
        EntityType,
        MemoryStatus,
    )
    HAS_GRAPH = True
except ImportError:
    HAS_GRAPH = False
    KnowledgeGraph = None
    RelationType = None
    EntityType = None
    MemoryStatus = None


class MemoryStore:
    """The main memory storage system.

    Usage:
        store = MemoryStore()
        store.remember("TypeScript is preferred for new projects", memory_type="preference")
        results = store.recall("programming language preferences")
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """Set up the storage.

        Args:
            data_dir: Where to save data. Defaults to ~/.engram/data/
        """
        # Figure out where to store data
        if data_dir is None:
            data_dir = Path.home() / ".engram" / "data"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Set up the filing cabinet (SQLite)
        self._init_sqlite()

        # Set up the smart index (ChromaDB)
        self._init_chromadb()

        # Set up the knowledge graph (NetworkX)
        self._init_graph()

        # Load the embedding model (converts text to numbers)
        # This is lazy-loaded to speed up startup
        self._embedder = None

    def _init_sqlite(self):
        """Create the filing cabinet (database tables)."""
        db_path = self.data_dir / "memories.db"
        self.db = sqlite3.connect(str(db_path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row  # Return rows as dictionaries

        # Create the memories table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                memory_type TEXT DEFAULT 'fact',
                project TEXT,
                source_role TEXT,
                importance REAL DEFAULT 0.5,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                accessed_at TEXT,
                access_count INTEGER DEFAULT 0,
                metadata TEXT
            )
        """)

        # Add source_role column if it doesn't exist (migration for existing DBs)
        try:
            self.db.execute("ALTER TABLE memories ADD COLUMN source_role TEXT")
            self.db.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Add surface_count column for implicit validation tracking
        try:
            self.db.execute("ALTER TABLE memories ADD COLUMN surface_count INTEGER DEFAULT 0")
            self.db.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Add validated column for HITL validation status
        try:
            self.db.execute("ALTER TABLE memories ADD COLUMN validated INTEGER DEFAULT 0")
            self.db.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Create indexes for faster searches
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_project ON memories(project)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(memory_type)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_source_role ON memories(source_role)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_created ON memories(created_at)")

        # Create access log table for feedback loop tracking
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id TEXT NOT NULL,
                query TEXT,
                role TEXT,
                project TEXT,
                relevance REAL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (memory_id) REFERENCES memories(id)
            )
        """)
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_access_log_memory ON access_log(memory_id)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_access_log_time ON access_log(timestamp)")

        self.db.commit()

    def _init_chromadb(self):
        """Create the smart index (vector database)."""
        chroma_path = self.data_dir / "chromadb"

        self.chroma = chromadb.PersistentClient(
            path=str(chroma_path),
            settings=Settings(
                anonymized_telemetry=False,  # Don't send usage data
                allow_reset=True,
            )
        )

        # Get or create our collection of memory embeddings
        self.collection = self.chroma.get_or_create_collection(
            name="engram_memories",
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )

    def _init_graph(self):
        """Create the knowledge graph (entity relationships)."""
        if HAS_GRAPH:
            self.graph = KnowledgeGraph(self.data_dir)
        else:
            self.graph = None

    @property
    def embedder(self):
        """Load the embedding model (lazy - only when first needed).

        This converts text into numbers (vectors) that capture meaning.
        Similar meanings = similar numbers.
        """
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            # all-mpnet-base-v2 provides better quality (768d vs 384d)
            # ~420MB download on first use, but significantly better semantic understanding
            self._embedder = SentenceTransformer('all-mpnet-base-v2')
        return self._embedder

    def check_contradictions(
        self,
        content: str,
        similarity_threshold: float = 0.5,
        project: Optional[str] = None,
    ) -> list[dict]:
        """
        Check if new content contradicts existing memories.

        Looks for semantically similar memories that might conflict.
        Uses keyword signals to detect potential contradictions.

        Args:
            content: The new memory content to check
            similarity_threshold: How similar memories must be to check
            project: Filter to same project (None = check all)

        Returns:
            List of potentially contradicting memories with conflict info
        """
        # Find similar memories
        similar = self.recall(
            query=content,
            limit=10,
            project=project,
        )

        # Contradiction signal words/patterns
        contradiction_signals = [
            # Negation patterns
            ("don't", "do"), ("do", "don't"),
            ("never", "always"), ("always", "never"),
            ("avoid", "use"), ("use", "avoid"),
            ("disable", "enable"), ("enable", "disable"),
            ("not", ""), ("", "not"),
            # Preference changes
            ("prefer", "avoid"), ("instead of", "use"),
            # Tech choices
            ("sqlite", "postgresql"), ("postgresql", "sqlite"),
            ("typescript", "javascript"), ("javascript", "typescript"),
            ("react", "vue"), ("vue", "react"),
        ]

        contradictions = []
        content_lower = content.lower()

        for mem in similar:
            if mem["similarity"] < similarity_threshold:
                continue

            mem_lower = mem["content"].lower()

            # Check for contradiction signals
            conflict_reason = None

            # Check negation patterns
            for sig_a, sig_b in contradiction_signals:
                if sig_a and sig_b:
                    # Both signals present - check if flipped
                    if sig_a in content_lower and sig_b in mem_lower:
                        conflict_reason = f"Potential conflict: new has '{sig_a}', existing has '{sig_b}'"
                        break
                elif sig_a:  # Only first signal (e.g., "not")
                    # Check if one has negation, other doesn't
                    if sig_a in content_lower and sig_a not in mem_lower:
                        conflict_reason = f"Potential negation conflict"
                        break
                    if sig_a in mem_lower and sig_a not in content_lower:
                        conflict_reason = f"Potential negation conflict"
                        break

            # High similarity + same type often means update/contradiction
            if not conflict_reason and mem["similarity"] > 0.55:
                if mem["memory_type"] in ("fact", "preference", "decision", "pattern"):
                    conflict_reason = f"Very similar {mem['memory_type']} ({mem['similarity']:.0%}) - may be an update"

            if conflict_reason:
                contradictions.append({
                    **mem,
                    "conflict_reason": conflict_reason,
                })

        return contradictions

    def remember(
        self,
        content: str,
        memory_type: str = "fact",
        importance: float = 0.5,
        project: Optional[str] = None,
        source_role: Optional[str] = None,
        metadata: Optional[dict] = None,
        check_conflicts: bool = False,
        supersede: Optional[list[str]] = None,
    ) -> str | dict:
        """Store a new memory.

        Args:
            content: The memory text (what to remember)
            memory_type: Category - "fact", "preference", "decision", "solution", "philosophy", "pattern"
            importance: How important is this? 0.0 to 1.0 (higher = more important)
            project: Which project is this for? None = universal
            source_role: Which agent role created this? (e.g., "gpu-specialist", "studioflow")
                         When recalling, memories from the same role get a relevance boost.
            metadata: Any extra info to store
            check_conflicts: If True, check for contradictions before storing
            supersede: List of memory IDs this new memory supersedes (archives them)

        Returns:
            If check_conflicts=False: The ID of the stored memory
            If check_conflicts=True and conflicts found: Dict with 'conflicts' list
            If check_conflicts=True and no conflicts: The ID of the stored memory

        Example:
            store.remember(
                "README-driven development: write docs first",
                memory_type="philosophy",
                importance=0.9,
                source_role="ai-dev"
            )
        """
        # Clamp importance to valid range [0.0, 1.0]
        importance = max(0.0, min(1.0, importance))

        # Check for contradictions if requested
        if check_conflicts:
            conflicts = self.check_contradictions(content, project=project)
            if conflicts:
                return {
                    "status": "conflicts_found",
                    "conflicts": conflicts,
                    "message": "Potential contradictions found. Use supersede=[ids] to replace, or proceed without check_conflicts.",
                }

        # Handle superseding old memories
        if supersede:
            for old_id in supersede:
                # Mark old memory as superseded
                self.db.execute(
                    """
                    UPDATE memories
                    SET metadata = json_set(COALESCE(metadata, '{}'), '$.superseded_by', ?)
                    WHERE id = ?
                    """,
                    (f"pending:{content[:50]}", old_id)
                )
                # Remove from search index
                try:
                    self.collection.delete(ids=[old_id])
                except Exception:
                    pass
            self.db.commit()

        # Generate a unique ID
        memory_id = f"mem_{uuid.uuid4().hex[:12]}"

        # Update supersede records with actual ID
        if supersede:
            for old_id in supersede:
                self.db.execute(
                    """
                    UPDATE memories
                    SET metadata = json_set(metadata, '$.superseded_by', ?)
                    WHERE id = ?
                    """,
                    (memory_id, old_id)
                )

        # Convert text to numbers (embedding)
        embedding = self.embedder.encode(content).tolist()

        # Store in SQLite (the filing cabinet)
        self.db.execute(
            """
            INSERT INTO memories (id, content, memory_type, project, source_role, importance, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id,
                content,
                memory_type,
                project,
                source_role,
                importance,
                json.dumps(metadata) if metadata else None,
            )
        )
        self.db.commit()

        # Store in ChromaDB (the smart index)
        self.collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                "memory_type": memory_type,
                "project": project or "",
                "source_role": source_role or "",
                "importance": importance,
            }]
        )

        # Store in knowledge graph (entity relationships)
        if self.graph:
            self.graph.add_memory(
                memory_id,
                content,
                memory_type,
                project=project,
                source_role=source_role,
                status="active",
                confidence=importance,  # Use importance as initial confidence
                impact="high" if importance > 0.7 else "medium" if importance > 0.4 else "low",
            )

            # Handle supersede relationships in graph
            if supersede:
                for old_id in supersede:
                    self.graph.supersede(memory_id, old_id)

            # Auto-extract entities and relationships from content
            self._auto_extract(memory_id, content)

        return memory_id

    def _auto_extract(self, memory_id: str, content: str) -> None:
        """Auto-extract entities and relationships from memory content.

        Detects goals, blockers, and relationships based on keyword patterns.
        This runs automatically on remember() to reduce manual entity/link calls.
        """
        if not self.graph or not HAS_GRAPH:
            return

        content_lower = content.lower()

        # =====================================================================
        # ENTITY EXTRACTION
        # =====================================================================

        # Goal patterns: "goal:", "objective:", "aiming to", "want to achieve"
        goal_patterns = [
            (r'goal:\s*(.+?)(?:\.|$)', 0.9),
            (r'objective:\s*(.+?)(?:\.|$)', 0.9),
            (r'primary goal[:\s]+(.+?)(?:\.|$)', 0.9),
            (r'aiming to\s+(.+?)(?:\.|$)', 0.7),
        ]

        # Blocker patterns: "blocks", "prevents", "obstacle", "stuck on"
        blocker_patterns = [
            (r'blocker:\s*(.+?)(?:\.|$)', 0.9),
            (r'blocked by\s+(.+?)(?:\.|$)', 0.8),
            (r'obstacle:\s*(.+?)(?:\.|$)', 0.8),
            (r'stuck on\s+(.+?)(?:\.|$)', 0.7),
            (r'prevents?\s+(.+?)(?:\.|$)', 0.7),
        ]

        # Pattern patterns: "pattern:", "approach:", "best practice"
        pattern_patterns = [
            (r'pattern:\s*(.+?)(?:\.|$)', 0.8),
            (r'approach:\s*(.+?)(?:\.|$)', 0.7),
            (r'best practice:\s*(.+?)(?:\.|$)', 0.8),
        ]

        import re

        # Extract goals
        for pattern, confidence in goal_patterns:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            for match in matches[:2]:  # Limit to 2 per pattern
                name = match.strip()[:50]  # Cap length
                if len(name) > 5:  # Skip tiny matches
                    entity_id = self.add_entity("goal", name)
                    if entity_id:
                        self.add_relationship(
                            memory_id, entity_id, "motivated_by",
                            confidence=confidence
                        )

        # Extract blockers
        for pattern, confidence in blocker_patterns:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            for match in matches[:2]:
                name = match.strip()[:50]
                if len(name) > 5:
                    entity_id = self.add_entity("blocker", name)
                    if entity_id:
                        self.add_relationship(
                            memory_id, entity_id, "blocked_by",
                            confidence=confidence
                        )

        # Extract patterns (only for solution/pattern memory types)
        if memory_id and self.db:
            row = self.db.execute(
                "SELECT memory_type FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()
            if row and row[0] in ("solution", "pattern"):
                for pattern, confidence in pattern_patterns:
                    matches = re.findall(pattern, content_lower, re.IGNORECASE)
                    for match in matches[:2]:
                        name = match.strip()[:50]
                        if len(name) > 5:
                            entity_id = self.add_entity("pattern", name)
                            if entity_id:
                                self.add_relationship(
                                    memory_id, entity_id, "example_of",
                                    confidence=confidence
                                )

        # =====================================================================
        # RELATIONSHIP EXTRACTION
        # =====================================================================

        # Relationship patterns: keyword -> relation_type
        relationship_keywords = {
            # Causal
            "because": "motivated_by",
            "motivated by": "motivated_by",
            "caused by": "caused_by",
            "results in": "resulted_in",
            "leads to": "resulted_in",
            # Blocking
            "blocks": "blocks",
            "prevents": "blocks",
            "enables": "enables",
            "unlocks": "enables",
            # Structural
            "requires": "requires",
            "needs": "requires",
            "depends on": "depends_on",
            # Evolution
            "supersedes": "supersedes",
            "replaces": "supersedes",
            "instead of": "supersedes",
            "evolved from": "evolved_from",
            # Semantic
            "contradicts": "contradicts",
            "conflicts with": "contradicts",
            "reinforces": "reinforces",
            "supports": "reinforces",
            "similar to": "similar_to",
        }

        # Look for relationship keywords and try to extract target
        for keyword, rel_type in relationship_keywords.items():
            if keyword in content_lower:
                # Try to find what follows the keyword
                pattern = rf'{keyword}\s+["\']?([^"\'.,]+)["\']?'
                matches = re.findall(pattern, content_lower)
                for match in matches[:1]:  # Only first match per keyword
                    target_name = match.strip()[:50]
                    if len(target_name) > 3:
                        # Try to find existing entity that matches
                        # Check common entity types
                        for entity_type in ["goal", "blocker", "pattern", "tool", "concept"]:
                            target_id = f"entity:{entity_type}:{target_name.lower().replace(' ', '_')}"
                            if self.graph.graph.has_node(target_id):
                                self.add_relationship(
                                    memory_id, target_id, rel_type,
                                    confidence=0.6  # Lower confidence for auto-detected
                                )
                                break

    def recall(
        self,
        query: str,
        limit: int = 10,
        project: Optional[str] = None,
        memory_types: Optional[list[str]] = None,
        current_role: Optional[str] = None,
        hybrid_search: bool = True,
    ) -> list[dict]:
        """Search for memories by meaning with hybrid semantic + keyword search.

        Args:
            query: What you're looking for (natural language)
            limit: Maximum number of results
            project: Filter to specific project (None = all projects)
            memory_types: Filter to specific types (None = all types)
            current_role: The agent role doing the query (for role affinity boost)
                          Memories created by the same role get a relevance boost.
            hybrid_search: If True, boost results that contain query keywords (default: True)

        Returns:
            List of matching memories, sorted by relevance

        Example:
            results = store.recall("how to approach new projects", current_role="gpu-specialist")
        """
        # Extract keywords for hybrid search (simple approach: significant words)
        query_keywords = []
        if hybrid_search:
            import re
            # Extract words, filter stopwords, keep significant terms
            stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                        'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                        'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                        'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                        'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                        'through', 'during', 'before', 'after', 'above', 'below',
                        'between', 'under', 'again', 'further', 'then', 'once',
                        'here', 'there', 'when', 'where', 'why', 'how', 'all',
                        'each', 'few', 'more', 'most', 'other', 'some', 'such',
                        'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
                        'too', 'very', 'just', 'and', 'but', 'if', 'or', 'because',
                        'until', 'while', 'what', 'which', 'who', 'this', 'that',
                        'these', 'those', 'am', 'it', 'its', 'i', 'me', 'my', 'we',
                        'our', 'you', 'your', 'he', 'him', 'his', 'she', 'her',
                        'they', 'them', 'their', 'best', 'practices', 'tips', 'help'}
            words = re.findall(r'\b[a-zA-Z0-9]+\b', query.lower())
            query_keywords = [w for w in words if w not in stopwords and len(w) > 2]

        # Convert query to numbers
        query_embedding = self.embedder.encode(query).tolist()

        # Build filters
        where_filter = {}
        if project:
            where_filter["project"] = project
        if memory_types and len(memory_types) == 1:
            where_filter["memory_type"] = memory_types[0]

        # Search ChromaDB for similar meanings
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit * 2,  # Get extra to filter/re-rank
            where=where_filter if where_filter else None,
        )

        if not results["ids"] or not results["ids"][0]:
            return []

        # Get full details from SQLite
        memories = []
        for i, memory_id in enumerate(results["ids"][0]):
            # Get from SQLite
            row = self.db.execute(
                "SELECT * FROM memories WHERE id = ?",
                (memory_id,)
            ).fetchone()

            if row:
                # Update access stats and surface count for implicit validation
                self.db.execute(
                    """
                    UPDATE memories
                    SET accessed_at = ?,
                        access_count = access_count + 1,
                        surface_count = COALESCE(surface_count, 0) + 1
                    WHERE id = ?
                    """,
                    (datetime.now().isoformat(), memory_id)
                )

                # Implicit validation: auto-validate memories surfaced 5+ times
                # This creates a learning loop - frequently useful memories get validated
                current_surface = (row["surface_count"] if "surface_count" in row.keys() else 0) or 0
                current_surface += 1
                validated = row["validated"] if "validated" in row.keys() else 0
                if current_surface >= 5 and not validated:
                    self.db.execute(
                        "UPDATE memories SET validated = 1 WHERE id = ?",
                        (memory_id,)
                    )
                    # Also validate in graph if available
                    if self.graph:
                        try:
                            self.graph.validate_memory(memory_id)
                        except Exception:
                            pass

                # Calculate relevance score with temporal decay + reinforcement
                distance = results["distances"][0][i] if results["distances"] else 0
                similarity = 1 - distance  # Convert distance to similarity

                # Temporal decay: memories lose relevance over time
                # Half-life of ~30 days (memories lose 50% relevance per month if not accessed)
                created = datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now()
                accessed = datetime.fromisoformat(row["accessed_at"]) if row["accessed_at"] else created
                last_touch = max(created, accessed)
                days_since_touch = (datetime.now() - last_touch).days
                decay_factor = math.exp(-0.023 * days_since_touch)  # ~30 day half-life

                # Reinforcement: frequently accessed memories are boosted
                # Log scale so first few accesses matter most
                access_count = row["access_count"] or 0
                reinforcement = 1 + (0.1 * math.log1p(access_count))  # +10% per order of magnitude

                # Role affinity: memories from the same agent role get a boost
                # This allows agents to build expertise without siloing knowledge
                source_role = row["source_role"] if "source_role" in row.keys() else None
                role_affinity = 1.0
                if current_role and source_role:
                    if current_role == source_role:
                        role_affinity = 1.15  # 15% boost for same-role memories
                    # Could add partial matches here for related roles

                # Keyword match boost (hybrid search)
                # Memories containing query keywords get a relevance boost
                keyword_boost = 1.0
                keyword_matches = 0
                if query_keywords:
                    content_lower = row["content"].lower()
                    for keyword in query_keywords:
                        if keyword in content_lower:
                            keyword_matches += 1
                    # Boost based on fraction of keywords matched
                    match_ratio = keyword_matches / len(query_keywords)
                    keyword_boost = 1.0 + (match_ratio * 0.25)  # Up to 25% boost for full match

                # Composite score (similarity-dominant):
                # - Similarity is the PRIMARY signal (query-specific)
                # - Importance is a BOOST, not a dominator
                # - Other factors provide minor adjustments
                #
                # Formula: similarity^1.3 gives high-similarity results more weight
                # Importance contributes 0.5 + (importance * 0.5) = 50-100% multiplier
                # This means importance can boost by up to 50%, not dominate
                similarity_weight = max(0.0, similarity) ** 1.3  # Amplify similarity differences (clamp to avoid complex)
                importance_factor = 0.5 + (row["importance"] * 0.5)  # 0.5-1.0 range

                base_score = (
                    similarity_weight * 0.55 +  # Dominant factor
                    decay_factor * 0.15 +
                    min(reinforcement * 0.10, 0.12)  # Cap reinforcement
                )
                # Apply importance as a multiplier (not additive) along with other boosts
                composite = base_score * importance_factor * keyword_boost * role_affinity

                memory_data = {
                    "id": row["id"],
                    "content": row["content"],
                    "memory_type": row["memory_type"],
                    "project": row["project"],
                    "source_role": source_role,
                    "importance": row["importance"],
                    "relevance": round(composite, 3),
                    "similarity": round(similarity, 3),
                    "freshness": round(decay_factor, 3),
                    "role_affinity": round(role_affinity, 2),
                    "keyword_boost": round(keyword_boost, 2),
                    "keyword_matches": keyword_matches,
                    "access_count": row["access_count"],
                    "created_at": row["created_at"],
                }
                memories.append(memory_data)

                # Log access for feedback loop (non-blocking)
                try:
                    self.log_access(
                        memory_id=row["id"],
                        query=query,
                        role=current_role,
                        project=project or row["project"],
                        relevance=round(composite, 3),
                    )
                except Exception:
                    pass  # Don't fail recall on logging error

        self.db.commit()

        # Filter by memory_types if multiple specified
        if memory_types and len(memory_types) > 1:
            memories = [m for m in memories if m["memory_type"] in memory_types]

        # Sort by composite relevance score (already includes all factors)
        memories.sort(key=lambda m: m["relevance"], reverse=True)

        return memories[:limit]

    def context(
        self,
        query: Optional[str] = None,
        cwd: Optional[str] = None,
        limit: int = 5,
        current_role: Optional[str] = None,
    ) -> list[dict]:
        """Get relevant context for current work.

        This is the main "auto-inject" function. It figures out what
        memories are relevant based on what you're doing.

        Args:
            query: What you're working on (optional)
            cwd: Current working directory (for project detection)
            limit: How many memories to return
            current_role: The agent role doing the query (for role affinity boost)

        Returns:
            List of relevant memories, formatted for injection
        """
        # Detect project from directory
        project = None
        if cwd:
            project = self._detect_project(cwd)

        # If we have a project, get project-specific + universal memories
        if project:
            # Get project-specific memories (with role affinity)
            project_memories = self.recall(
                query=query or "context",
                limit=limit,
                project=project,
                current_role=current_role,
            )

            # Get universal memories (no project filter, but still with role affinity)
            universal_memories = self.recall(
                query=query or "general principles",
                limit=limit,
                project=None,
                current_role=current_role,
            )
            # Filter to only truly universal (project=None)
            universal_memories = [m for m in universal_memories if not m["project"]]

            # Combine, prioritizing project-specific
            memories = project_memories + universal_memories
            # Remove duplicates
            seen = set()
            unique = []
            for m in memories:
                if m["id"] not in seen:
                    seen.add(m["id"])
                    unique.append(m)
            memories = unique[:limit]
        else:
            # No project context, just search (still with role affinity)
            memories = self.recall(query=query or "context", limit=limit, current_role=current_role)

        return memories

    def _detect_project(self, cwd: str) -> Optional[str]:
        """Figure out which project we're in based on the directory.

        Examples:
            /mnt/dev/ai/engram-mcp/src → "engram-mcp"
            /mnt/dev/ai/hallo2/lib → "hallo2"
            /home/eric/random → None
        """
        import re

        patterns = [
            r"/mnt/dev/ai/([^/]+)",      # /mnt/dev/ai/PROJECT/...
            r"/home/[^/]+/projects/([^/]+)",  # ~/projects/PROJECT/...
            r"/workspace/([^/]+)",        # /workspace/PROJECT/...
        ]

        for pattern in patterns:
            match = re.search(pattern, cwd)
            if match:
                return match.group(1)

        return None

    def related(
        self,
        memory_id: str,
        limit: int = 5,
    ) -> list[dict]:
        """
        Find memories related to a given memory via entity connections.

        Uses the knowledge graph to find memories that share entities
        with the given memory (more precise than semantic similarity).

        Args:
            memory_id: The memory to find relations for
            limit: Maximum number of results

        Returns:
            List of related memories with connection info
        """
        if not self.graph:
            return []

        # Get related memory IDs from graph
        related_results = self.graph.get_related_memories(memory_id, depth=2)

        # Fetch full memory details
        memories = []
        for rel_info in related_results[:limit]:
            # get_related_memories returns dicts with memory_id, score, relationships
            rel_id = rel_info.get("memory_id") if isinstance(rel_info, dict) else rel_info
            if not rel_id or not isinstance(rel_id, str):
                continue

            row = self.db.execute(
                "SELECT * FROM memories WHERE id = ?",
                (rel_id,)
            ).fetchone()

            if row:
                memories.append({
                    "id": row["id"],
                    "content": row["content"],
                    "memory_type": row["memory_type"],
                    "project": row["project"],
                    "importance": row["importance"],
                    "created_at": row["created_at"],
                })

        return memories

    def get_by_entity(
        self,
        entity_type: str,
        entity_name: str,
        limit: int = 10,
    ) -> list[dict]:
        """
        Find all memories mentioning a specific entity.

        Args:
            entity_type: Type of entity (projects, tools, concepts, episode)
            entity_name: Name of the entity
            limit: Maximum results

        Returns:
            List of memories mentioning this entity
        """
        if not self.graph:
            return []

        memory_ids = self.graph.get_memories_by_entity(entity_type, entity_name)

        memories = []
        for mem_id in memory_ids[:limit]:
            row = self.db.execute(
                "SELECT * FROM memories WHERE id = ?",
                (mem_id,)
            ).fetchone()

            if row:
                memories.append({
                    "id": row["id"],
                    "content": row["content"],
                    "memory_type": row["memory_type"],
                    "project": row["project"],
                    "importance": row["importance"],
                    "created_at": row["created_at"],
                })

        return memories

    def find_consolidation_candidates(
        self,
        similarity_threshold: float = 0.85,
        min_cluster_size: int = 3,
    ) -> list[dict]:
        """
        Find groups of similar memories that could be consolidated.

        Uses vector similarity to find clusters of memories about the same topic.
        Returns clusters sorted by potential impact (more memories = higher impact).

        Args:
            similarity_threshold: How similar memories must be (0.85 = very similar)
            min_cluster_size: Minimum memories to form a cluster

        Returns:
            List of clusters, each with 'memories' list and 'topic' summary
        """
        # Get all memory embeddings from ChromaDB
        all_data = self.collection.get(include=["embeddings", "documents", "metadatas"])

        if not all_data["ids"]:
            return []

        ids = all_data["ids"]
        embeddings = all_data["embeddings"]
        documents = all_data["documents"]

        # Find clusters using simple greedy approach
        # (More sophisticated: DBSCAN or HDBSCAN, but this works for small sets)
        import numpy as np

        embeddings_array = np.array(embeddings)
        used = set()
        clusters = []

        for i, embed_i in enumerate(embeddings_array):
            if ids[i] in used:
                continue

            # Find all similar memories
            cluster_ids = [ids[i]]
            cluster_docs = [documents[i]]

            for j, embed_j in enumerate(embeddings_array):
                if i == j or ids[j] in used:
                    continue

                # Cosine similarity
                similarity = np.dot(embed_i, embed_j) / (
                    np.linalg.norm(embed_i) * np.linalg.norm(embed_j)
                )

                if similarity >= similarity_threshold:
                    cluster_ids.append(ids[j])
                    cluster_docs.append(documents[j])

            if len(cluster_ids) >= min_cluster_size:
                # Mark all as used
                used.update(cluster_ids)

                # Get full memory details
                memories = []
                for mem_id in cluster_ids:
                    row = self.db.execute(
                        "SELECT * FROM memories WHERE id = ?", (mem_id,)
                    ).fetchone()
                    if row:
                        memories.append({
                            "id": row["id"],
                            "content": row["content"],
                            "memory_type": row["memory_type"],
                            "project": row["project"],
                            "importance": row["importance"],
                        })

                # Extract common theme (simple: use most common words)
                all_text = " ".join(cluster_docs).lower()
                words = [w for w in all_text.split() if len(w) > 4]
                word_counts = {}
                for w in words:
                    word_counts[w] = word_counts.get(w, 0) + 1
                top_words = sorted(word_counts.items(), key=lambda x: -x[1])[:5]
                topic = ", ".join(w[0] for w in top_words)

                clusters.append({
                    "topic": topic,
                    "count": len(memories),
                    "memories": memories,
                })

        # Sort by cluster size (highest impact first)
        clusters.sort(key=lambda c: -c["count"])
        return clusters

    def consolidate(
        self,
        memory_ids: list[str],
        consolidated_content: str,
        memory_type: str = "pattern",
        importance: float = 0.8,
    ) -> str:
        """
        Consolidate multiple memories into one, archiving the originals.

        Args:
            memory_ids: IDs of memories to consolidate
            consolidated_content: The new consolidated memory text
            memory_type: Type for consolidated memory (usually 'pattern')
            importance: Importance of consolidated memory

        Returns:
            ID of the new consolidated memory
        """
        # Get project from first memory (assume same project)
        row = self.db.execute(
            "SELECT project FROM memories WHERE id = ?", (memory_ids[0],)
        ).fetchone()
        project = row["project"] if row else None

        # Create consolidated memory
        new_id = self.remember(
            content=consolidated_content,
            memory_type=memory_type,
            importance=importance,
            project=project,
            metadata={
                "consolidated_from": memory_ids,
                "consolidated_at": datetime.now().isoformat(),
            }
        )

        # Archive originals (mark as consolidated, keep for reference)
        for mem_id in memory_ids:
            self.db.execute(
                """
                UPDATE memories
                SET metadata = json_set(COALESCE(metadata, '{}'), '$.consolidated_into', ?)
                WHERE id = ?
                """,
                (new_id, mem_id)
            )
            # Remove from ChromaDB (no longer searchable)
            try:
                self.collection.delete(ids=[mem_id])
            except Exception:
                pass  # Already deleted or doesn't exist

        self.db.commit()
        return new_id

    def get_stats(self) -> dict:
        """Get memory statistics.

        Returns info about how many memories, types, projects, etc.
        """
        total = self.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

        by_type = dict(self.db.execute(
            "SELECT memory_type, COUNT(*) FROM memories GROUP BY memory_type"
        ).fetchall())

        by_project = dict(self.db.execute(
            "SELECT COALESCE(project, 'universal'), COUNT(*) FROM memories GROUP BY project"
        ).fetchall())

        # Count consolidated vs active
        active_in_chroma = self.collection.count()

        stats = {
            "total_memories": total,
            "active_memories": active_in_chroma,
            "archived_memories": total - active_in_chroma,
            "by_type": by_type,
            "by_project": by_project,
        }

        # Add graph stats if available
        if self.graph:
            stats["graph"] = self.graph.get_stats()

        # Add access log stats
        stats["access_stats"] = self._get_access_stats()

        return stats

    def log_access(
        self,
        memory_id: str,
        query: Optional[str] = None,
        role: Optional[str] = None,
        project: Optional[str] = None,
        relevance: Optional[float] = None,
    ) -> None:
        """Log a memory access for feedback tracking."""
        self.db.execute(
            """
            INSERT INTO access_log (memory_id, query, role, project, relevance)
            VALUES (?, ?, ?, ?, ?)
            """,
            (memory_id, query, role, project, relevance)
        )
        self.db.commit()

    def _get_access_stats(self) -> dict:
        """Get access pattern statistics for feedback analysis."""
        # Most accessed memories (candidates for validation)
        most_accessed = self.db.execute("""
            SELECT memory_id, COUNT(*) as access_count
            FROM access_log
            WHERE timestamp > datetime('now', '-30 days')
            GROUP BY memory_id
            ORDER BY access_count DESC
            LIMIT 10
        """).fetchall()

        # Memories by role (shows role-specific usage)
        by_role = dict(self.db.execute("""
            SELECT COALESCE(role, 'unknown'), COUNT(DISTINCT memory_id)
            FROM access_log
            WHERE role IS NOT NULL
            GROUP BY role
        """).fetchall())

        # Never accessed memories (candidates for pruning)
        never_accessed = self.db.execute("""
            SELECT COUNT(*) FROM memories m
            WHERE NOT EXISTS (
                SELECT 1 FROM access_log a WHERE a.memory_id = m.id
            )
        """).fetchone()[0]

        # Total accesses in last 30 days
        recent_accesses = self.db.execute("""
            SELECT COUNT(*) FROM access_log
            WHERE timestamp > datetime('now', '-30 days')
        """).fetchone()[0]

        return {
            "most_accessed": [
                {"memory_id": row[0], "count": row[1]}
                for row in most_accessed
            ],
            "accesses_by_role": by_role,
            "never_accessed_count": never_accessed,
            "recent_accesses_30d": recent_accesses,
        }

    def get_validation_candidates(self, limit: int = 10) -> list[dict]:
        """Get memories that should be validated based on access patterns.

        Returns memories that are:
        1. Frequently accessed
        2. High relevance when accessed
        3. Not already highly validated
        """
        rows = self.db.execute("""
            SELECT
                m.id,
                m.content,
                m.memory_type,
                COUNT(a.id) as access_count,
                AVG(a.relevance) as avg_relevance,
                m.importance
            FROM memories m
            JOIN access_log a ON m.id = a.memory_id
            WHERE a.timestamp > datetime('now', '-30 days')
            GROUP BY m.id
            HAVING access_count >= 3
            ORDER BY access_count * COALESCE(AVG(a.relevance), 0.5) DESC
            LIMIT ?
        """, (limit,)).fetchall()

        return [
            {
                "id": row[0],
                "content": row[1][:100] + "..." if len(row[1]) > 100 else row[1],
                "memory_type": row[2],
                "access_count": row[3],
                "avg_relevance": round(row[4] or 0, 2),
                "importance": row[5],
            }
            for row in rows
        ]

    def get_prune_candidates(self, limit: int = 20) -> list[dict]:
        """Get memories that could be pruned based on lack of use.

        Returns memories that are:
        1. Never or rarely accessed
        2. Old (created > 30 days ago)
        3. Low importance
        """
        rows = self.db.execute("""
            SELECT
                m.id,
                m.content,
                m.memory_type,
                m.importance,
                m.created_at,
                COALESCE(m.access_count, 0) as access_count
            FROM memories m
            WHERE m.created_at < datetime('now', '-30 days')
              AND COALESCE(m.access_count, 0) < 3
              AND m.importance < 0.7
              AND m.metadata NOT LIKE '%archived%'
            ORDER BY m.importance ASC, m.access_count ASC
            LIMIT ?
        """, (limit,)).fetchall()

        return [
            {
                "id": row[0],
                "content": row[1][:100] + "..." if len(row[1]) > 100 else row[1],
                "memory_type": row[2],
                "importance": row[3],
                "created_at": row[4],
                "access_count": row[5],
            }
            for row in rows
        ]

    def get_recent_memories(
        self,
        hours: int = 24,
        limit: int = 20,
        exclude_seeds: bool = True,
    ) -> list[dict]:
        """Get recently created memories for HITL review.

        Returns memories created in the last N hours, useful for
        batch reviewing what was captured during a session.

        Args:
            hours: Look back this many hours (default 24)
            limit: Maximum memories to return
            exclude_seeds: Skip memories from seed files (importance >= 0.7 and type=pattern)

        Returns:
            List of memories with full content for review
        """
        # Build exclusion clause for seed-like memories
        seed_clause = ""
        if exclude_seeds:
            seed_clause = "AND NOT (importance >= 0.7 AND memory_type = 'pattern')"

        rows = self.db.execute(f"""
            SELECT
                id,
                content,
                memory_type,
                importance,
                project,
                source_role,
                created_at
            FROM memories
            WHERE created_at > datetime('now', '-{hours} hours')
              {seed_clause}
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()

        return [
            {
                "id": row[0],
                "content": row[1],
                "memory_type": row[2],
                "importance": row[3],
                "project": row[4],
                "source_role": row[5],
                "created_at": row[6],
            }
            for row in rows
        ]

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory completely (SQLite + ChromaDB).

        Used for HITL rejection of memories during review.

        Args:
            memory_id: The memory ID to delete

        Returns:
            True if deleted successfully
        """
        try:
            # Delete from SQLite
            cursor = self.db.execute(
                "DELETE FROM memories WHERE id = ?",
                (memory_id,)
            )
            deleted = cursor.rowcount > 0

            if deleted:
                # Delete from ChromaDB
                try:
                    self.collection.delete(ids=[memory_id])
                except Exception:
                    pass  # May not be in ChromaDB (archived)

                # Delete from graph if exists
                if self.graph:
                    try:
                        self.graph.remove_node(memory_id)
                    except Exception:
                        pass

                self.db.commit()

            return deleted

        except Exception:
            return False

    def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        memory_type: Optional[str] = None,
        importance: Optional[float] = None,
    ) -> bool:
        """Update a memory's content or metadata.

        Used for HITL editing of memories during review.

        Args:
            memory_id: The memory ID to update
            content: New content (re-embeds if changed)
            memory_type: New type
            importance: New importance

        Returns:
            True if updated successfully
        """
        # Clamp importance to valid range [0.0, 1.0]
        if importance is not None:
            importance = max(0.0, min(1.0, importance))

        # Build update query dynamically
        updates = []
        params = []

        if content is not None:
            updates.append("content = ?")
            params.append(content)
        if memory_type is not None:
            updates.append("memory_type = ?")
            params.append(memory_type)
        if importance is not None:
            updates.append("importance = ?")
            params.append(importance)

        if not updates:
            return False

        params.append(memory_id)

        try:
            cursor = self.db.execute(
                f"UPDATE memories SET {', '.join(updates)} WHERE id = ?",
                params
            )
            updated = cursor.rowcount > 0

            if updated and content is not None:
                # Re-embed the updated content
                embedding = self.embedder.encode(content).tolist()

                # Get metadata for ChromaDB
                row = self.db.execute(
                    "SELECT memory_type, project FROM memories WHERE id = ?",
                    (memory_id,)
                ).fetchone()

                if row:
                    # Update ChromaDB
                    try:
                        self.collection.update(
                            ids=[memory_id],
                            embeddings=[embedding],
                            documents=[content],
                            metadatas=[{
                                "memory_type": row[0] or "fact",
                                "project": row[1] or "",
                            }],
                        )
                    except Exception:
                        pass  # May not exist in ChromaDB

            self.db.commit()
            return updated

        except Exception:
            return False

    # =========================================================================
    # GRAPH RELATIONSHIP METHODS
    # =========================================================================

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        strength: float = 1.0,
        confidence: float = 1.0,
        evidence: Optional[str] = None,
    ) -> bool:
        """
        Add a semantic relationship between memories or entities.

        Args:
            source_id: Source node (memory ID or entity ID like 'entity:goal:monetization')
            target_id: Target node
            relation_type: One of: supersedes, requires, blocked_by, motivated_by,
                          resulted_in, reinforces, contradicts, part_of, etc.
            strength: Relationship strength (0.0-1.0)
            confidence: Confidence this is accurate (0.0-1.0)
            evidence: Memory ID that supports this relationship

        Returns:
            True if relationship was added
        """
        if not self.graph or not HAS_GRAPH:
            return False

        try:
            rel_type = RelationType(relation_type)
        except ValueError:
            return False

        return self.graph.add_relationship(
            source_id=source_id,
            target_id=target_id,
            relation_type=rel_type,
            strength=strength,
            confidence=confidence,
            evidence=evidence,
        )

    def add_entity(
        self,
        entity_type: str,
        name: str,
        status: str = "active",
        priority: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[str]:
        """
        Add a standalone entity to the graph (goal, blocker, etc.).

        Args:
            entity_type: One of: project, episode, phase, tool, concept,
                        goal, blocker, pattern, decision_point
            name: Entity name
            status: active, achieved, abandoned
            priority: P0, P1, P2
            description: Optional description

        Returns:
            Entity ID if created
        """
        if not self.graph or not HAS_GRAPH:
            return None

        try:
            etype = EntityType(entity_type)
        except ValueError:
            return None

        return self.graph.add_entity(
            entity_type=etype,
            name=name,
            status=status,
            priority=priority,
            description=description,
        )

    def validate_memory(self, memory_id: str) -> bool:
        """
        Record that a memory was validated as useful.

        This increases the memory's confidence score and validation count.
        """
        if not self.graph:
            return False

        self.graph.validate_memory(memory_id)
        return True

    def get_current_memory(self, memory_id: str) -> Optional[dict]:
        """
        Get the current (non-superseded) version of a memory.

        Follows the supersedes chain to find the latest version.
        """
        if not self.graph:
            return None

        current_id = self.graph.get_current_version(memory_id)

        row = self.db.execute(
            "SELECT * FROM memories WHERE id = ?",
            (current_id,)
        ).fetchone()

        if row:
            return {
                "id": row["id"],
                "content": row["content"],
                "memory_type": row["memory_type"],
                "project": row["project"],
                "importance": row["importance"],
                "created_at": row["created_at"],
                "is_current": current_id != memory_id,
            }
        return None

    def get_blockers(self, goal_name: str) -> list[dict]:
        """Get all blockers for a goal."""
        if not self.graph:
            return []

        goal_id = f"entity:goal:{goal_name.lower()}"
        return self.graph.get_blockers_for(goal_id)

    def get_requirements(self, task_name: str, task_type: str = "phase") -> list[dict]:
        """Get all prerequisites for a task/phase."""
        if not self.graph:
            return []

        task_id = f"entity:{task_type}:{task_name.lower()}"
        return self.graph.get_requirements_for(task_id)

    def find_contradictions(self, memory_id: str) -> list[dict]:
        """Find memories that contradict a given memory."""
        if not self.graph:
            return []

        contradiction_ids = self.graph.find_contradictions(memory_id)

        memories = []
        for mem_id in contradiction_ids:
            row = self.db.execute(
                "SELECT * FROM memories WHERE id = ?",
                (mem_id,)
            ).fetchone()
            if row:
                memories.append({
                    "id": row["id"],
                    "content": row["content"],
                    "memory_type": row["memory_type"],
                    "project": row["project"],
                })

        return memories

    def get_hub_entities(self, limit: int = 10) -> list[dict]:
        """Get the most connected entities in the knowledge graph."""
        if not self.graph:
            return []
        return self.graph.get_hub_entities(limit)

    def visualize_memory(self, memory_id: str) -> str:
        """Get ASCII visualization of a memory's graph neighborhood."""
        if not self.graph:
            return "Graph not available"
        return self.graph.visualize_neighborhood(memory_id)
