#!/usr/bin/env python3
"""
Upgrade Engram Embeddings

Migrates from all-MiniLM-L6-v2 (384d) to all-mpnet-base-v2 (768d).
This requires re-embedding all memories since dimensions changed.

Usage:
    python scripts/upgrade_embeddings.py
    python scripts/upgrade_embeddings.py --dry-run  # Preview only
    python scripts/upgrade_embeddings.py --model all-mpnet-base-v2
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engram.storage import MemoryStore


def upgrade_embeddings(new_model: str = "all-mpnet-base-v2", dry_run: bool = False):
    """Re-embed all memories with new model."""
    from sentence_transformers import SentenceTransformer
    import chromadb
    import sqlite3
    from pathlib import Path
    import shutil

    print(f"=== Embedding Upgrade ===")
    print(f"New model: {new_model}")

    # Load new model first (before touching ChromaDB)
    print(f"\nLoading {new_model}...")
    new_embedder = SentenceTransformer(new_model)
    new_dim = new_embedder.get_sentence_embedding_dimension()
    print(f"Dimensions: {new_dim}")

    # Get all memories from SQLite directly (avoid loading MemoryStore which opens ChromaDB)
    data_dir = Path.home() / ".engram" / "data"
    db_path = data_dir / "memories.db"
    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row
    cursor = db.execute("SELECT id, content, memory_type, project FROM memories")
    memories = [dict(row) for row in cursor]
    db.close()
    print(f"\nTotal memories to re-embed: {len(memories)}")

    if dry_run:
        print("\n[DRY RUN] Would re-embed all memories.")
        print("Run without --dry-run to execute.")
        return

    # Delete old ChromaDB directory completely
    print("\nRecreating ChromaDB...")
    chroma_path = data_dir / "chromadb"
    if chroma_path.exists():
        shutil.rmtree(chroma_path)

    # Create fresh ChromaDB client
    chroma = chromadb.PersistentClient(path=str(chroma_path))
    collection = chroma.create_collection(
        name="engram_memories",  # Must match storage.py
        metadata={"hnsw:space": "cosine"}
    )

    # Re-embed all memories
    print(f"\nRe-embedding {len(memories)} memories...")
    batch_size = 100
    for i in range(0, len(memories), batch_size):
        batch = memories[i:i+batch_size]
        ids = [m["id"] for m in batch]
        contents = [m["content"] for m in batch]

        # Generate new embeddings
        embeddings = new_embedder.encode(contents).tolist()

        # Build metadata
        metadatas = [{
            "memory_type": m["memory_type"] or "fact",
            "project": m["project"] or "",
        } for m in batch]

        # Add to ChromaDB
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas,
        )

        progress = min(i + batch_size, len(memories))
        print(f"  Progress: {progress}/{len(memories)} ({progress/len(memories):.0%})")

    # Verify
    print(f"\n✓ Successfully re-embedded {len(memories)} memories")
    print(f"  ChromaDB now has: {collection.count()} documents")
    print(f"  Old model: all-MiniLM-L6-v2 (384d)")
    print(f"  New model: {new_model} ({new_dim}d)")


def main():
    parser = argparse.ArgumentParser(description="Upgrade engram embeddings")
    parser.add_argument("--model", default="all-mpnet-base-v2",
                       help="New embedding model (default: all-mpnet-base-v2)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview without executing")
    args = parser.parse_args()

    upgrade_embeddings(new_model=args.model, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
