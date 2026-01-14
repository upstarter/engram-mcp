"""
Query Logger for Engram-MCP
===========================

Logs all user queries passed through the MCP server for test suite generation.
Captures queries from your daily CFS workflow (ks + engram-mcp).
"""

import os
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Query database location
QUERY_DB_PATH = Path.home() / ".engram" / "data" / "queries.db"


class QueryLogger:
    """Logs user queries for test suite generation."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize query logger."""
        self.db_path = db_path or QUERY_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize the queries database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                id TEXT PRIMARY KEY,
                prompt TEXT NOT NULL,
                tool_name TEXT,
                agent_role TEXT,
                agent_id TEXT,
                source TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                is_test_query INTEGER DEFAULT 0
            )
        """)

        # Indexes for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON queries(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_role ON queries(agent_role)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tool_name ON queries(tool_name)
        """)

        conn.commit()
        conn.close()

    def log_query(
        self,
        prompt: str,
        tool_name: Optional[str] = None,
        agent_role: Optional[str] = None,
        agent_id: Optional[str] = None,
        source: str = "engram-mcp",
        metadata: Optional[Dict[str, Any]] = None,
        is_test_query: bool = False,
    ):
        """Log a query to the database.

        Args:
            prompt: The user's query/prompt
            tool_name: Which tool was called (chainmind_generate, engram_recall, etc.)
            agent_role: Agent role (e.g., "software_engineer")
            agent_id: Agent ID for context isolation
            source: Source of the query (engram-mcp, direct-api, etc.)
            metadata: Additional metadata
            is_test_query: Whether this is a test query (to filter out)
        """
        if not prompt or len(prompt.strip()) == 0:
            return

        # Filter out known test queries
        test_patterns = [
            "how do i fix this python function?",
            "test query",
            "example prompt",
            "test prompt",
        ]
        prompt_lower = prompt.lower().strip()
        if any(pattern in prompt_lower for pattern in test_patterns):
            is_test_query = True

        query_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        metadata_json = json.dumps(metadata or {})

        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO queries (
                    id, prompt, tool_name, agent_role, agent_id, source,
                    timestamp, metadata, is_test_query
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                query_id,
                prompt.strip(),
                tool_name,
                agent_role,
                agent_id,
                source,
                timestamp,
                metadata_json,
                1 if is_test_query else 0,
            ))

            conn.commit()
            conn.close()
        except Exception as e:
            # Don't fail if logging fails
            import sys
            print(f"Warning: Failed to log query: {e}", file=sys.stderr)

    def get_queries(
        self,
        limit: int = 1000,
        exclude_test: bool = True,
        agent_role: Optional[str] = None,
        tool_name: Optional[str] = None,
        min_length: int = 10,
    ) -> list[Dict[str, Any]]:
        """Get queries from the database.

        Args:
            limit: Maximum number of queries to return
            exclude_test: Whether to exclude test queries
            agent_role: Filter by agent role
            tool_name: Filter by tool name
            min_length: Minimum prompt length

        Returns:
            List of query dictionaries
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM queries WHERE LENGTH(prompt) >= ?"
        params = [min_length]

        if exclude_test:
            query += " AND is_test_query = 0"

        if agent_role:
            query += " AND agent_role = ?"
            params.append(agent_role)

        if tool_name:
            query += " AND tool_name = ?"
            params.append(tool_name)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        queries = []
        for row in rows:
            metadata = {}
            if row["metadata"]:
                try:
                    metadata = json.loads(row["metadata"])
                except:
                    pass

            queries.append({
                "id": row["id"],
                "prompt": row["prompt"],
                "tool_name": row["tool_name"],
                "agent_role": row["agent_role"],
                "agent_id": row["agent_id"],
                "source": row["source"],
                "timestamp": row["timestamp"],
                "metadata": metadata,
                "is_test_query": bool(row["is_test_query"]),
            })

        conn.close()
        return queries

    def get_unique_queries(
        self,
        exclude_test: bool = True,
        min_length: int = 10,
    ) -> list[str]:
        """Get unique queries (deduplicated).

        Returns:
            List of unique prompt strings
        """
        queries = self.get_queries(
            limit=10000,
            exclude_test=exclude_test,
            min_length=min_length,
        )

        # Deduplicate by prompt text (case-insensitive)
        seen = set()
        unique = []
        for q in queries:
            prompt_lower = q["prompt"].lower().strip()
            if prompt_lower not in seen:
                seen.add(prompt_lower)
                unique.append(q["prompt"])

        return unique


# Global instance
_logger: Optional[QueryLogger] = None


def get_logger() -> QueryLogger:
    """Get the global query logger instance."""
    global _logger
    if _logger is None:
        _logger = QueryLogger()
    return _logger


def log_query(
    prompt: str,
    tool_name: Optional[str] = None,
    agent_role: Optional[str] = None,
    agent_id: Optional[str] = None,
    source: str = "engram-mcp",
    metadata: Optional[Dict[str, Any]] = None,
):
    """Convenience function to log a query."""
    logger = get_logger()
    logger.log_query(
        prompt=prompt,
        tool_name=tool_name,
        agent_role=agent_role,
        agent_id=agent_id,
        source=source,
        metadata=metadata,
    )
