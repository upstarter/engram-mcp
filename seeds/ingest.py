#!/usr/bin/env python3
"""
Seed Knowledge Ingestion Script

Loads structured seed knowledge into engram from JSON files.
Creates entities, memories, and relationships in bulk.

Usage:
    python seeds/ingest.py seeds/youtube-mastery.json
    python seeds/ingest.py seeds/*.json  # Load all seeds
"""

import json
import sys
import time
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from engram.storage import MemoryStore


def load_seed_file(filepath: str) -> dict:
    """Load a seed JSON file."""
    with open(filepath) as f:
        return json.load(f)


def ingest_seed(store: MemoryStore, seed: dict, dry_run: bool = False) -> dict:
    """
    Ingest a seed file into engram.

    Returns statistics about what was ingested.
    """
    stats = {
        "entities_created": 0,
        "entities_skipped": 0,
        "memories_created": 0,
        "memories_skipped": 0,
        "relationships_created": 0,
        "relationships_failed": 0,
        "errors": []
    }

    metadata = seed.get("metadata", {})
    project = metadata.get("category", "seed_knowledge")

    print(f"\n{'='*60}")
    print(f"Ingesting: {metadata.get('name', 'Unknown')}")
    print(f"Version: {metadata.get('version', '?')}")
    print(f"Project tag: {project}")
    print(f"{'='*60}\n")

    # Phase 1: Create entities
    entities = seed.get("entities", [])
    print(f"Creating {len(entities)} entities...")

    entity_id_map = {}  # Map name -> actual entity ID

    for entity in entities:
        entity_type = entity.get("type")
        name = entity.get("name")

        if not entity_type or not name:
            stats["errors"].append(f"Invalid entity: {entity}")
            continue

        # Check if entity exists (simple dedup by name)
        expected_id = f"entity:{entity_type}:{name.lower().replace(' ', '_')}"

        if dry_run:
            print(f"  [DRY RUN] Would create: {expected_id}")
            entity_id_map[name] = expected_id
            stats["entities_created"] += 1
            continue

        try:
            entity_id = store.add_entity(
                entity_type=entity_type,
                name=name,
                status=entity.get("status", "active"),
                priority=entity.get("priority"),
                description=entity.get("description")
            )

            if entity_id:
                entity_id_map[name] = entity_id
                stats["entities_created"] += 1
                print(f"  + {entity_id}")
            else:
                stats["entities_skipped"] += 1
                print(f"  - Skipped (exists?): {name}")

        except Exception as e:
            stats["errors"].append(f"Entity error '{name}': {e}")
            print(f"  ! Error: {name} - {e}")

    # Phase 2: Create memories
    memories = seed.get("memories", [])
    print(f"\nCreating {len(memories)} memories...")

    memory_id_map = {}  # Map content hash -> memory ID for relationship linking

    for i, mem in enumerate(memories):
        content = mem.get("content")
        if not content:
            stats["errors"].append(f"Memory {i} has no content")
            continue

        # Create a short key for the memory (first 50 chars)
        mem_key = content[:50]

        if dry_run:
            print(f"  [DRY RUN] Would create memory: {mem_key}...")
            stats["memories_created"] += 1
            continue

        try:
            # Check for duplicates by doing a quick recall
            existing = store.recall(content[:100], limit=1)
            if existing and existing[0].get("relevance", 0) > 0.95:
                stats["memories_skipped"] += 1
                print(f"  - Skipped (duplicate): {mem_key}...")
                memory_id_map[mem_key] = existing[0]["id"]
                continue

            memory_id = store.remember(
                content=content,
                memory_type=mem.get("type", "fact"),
                importance=mem.get("importance", 0.5),
                project=project
            )

            memory_id_map[mem_key] = memory_id
            stats["memories_created"] += 1
            print(f"  + {memory_id}: {mem_key}...")

            # Small delay to avoid overwhelming ChromaDB
            time.sleep(0.05)

        except Exception as e:
            stats["errors"].append(f"Memory error: {e}")
            print(f"  ! Error: {mem_key}... - {e}")

    # Phase 3: Create relationships
    relationships = seed.get("relationships", [])
    print(f"\nCreating {len(relationships)} relationships...")

    for rel in relationships:
        source = rel.get("source")
        target = rel.get("target")
        rel_type = rel.get("type")

        if not all([source, target, rel_type]):
            stats["errors"].append(f"Invalid relationship: {rel}")
            continue

        if dry_run:
            print(f"  [DRY RUN] Would link: {source} --{rel_type}--> {target}")
            stats["relationships_created"] += 1
            continue

        try:
            success = store.add_relationship(
                source_id=source,
                target_id=target,
                relation_type=rel_type,
                strength=rel.get("strength", 1.0)
            )

            if success:
                stats["relationships_created"] += 1
                print(f"  + {source} --{rel_type}--> {target}")
            else:
                stats["relationships_failed"] += 1
                print(f"  - Failed: {source} --{rel_type}--> {target}")

        except Exception as e:
            stats["errors"].append(f"Relationship error: {e}")
            stats["relationships_failed"] += 1
            print(f"  ! Error: {rel} - {e}")

    return stats


def print_summary(all_stats: list[dict]):
    """Print summary of all ingestions."""
    print(f"\n{'='*60}")
    print("INGESTION SUMMARY")
    print(f"{'='*60}")

    totals = {
        "entities_created": 0,
        "entities_skipped": 0,
        "memories_created": 0,
        "memories_skipped": 0,
        "relationships_created": 0,
        "relationships_failed": 0,
        "errors": []
    }

    for stats in all_stats:
        for key in totals:
            if key == "errors":
                totals[key].extend(stats.get(key, []))
            else:
                totals[key] += stats.get(key, 0)

    print(f"\nEntities:      {totals['entities_created']} created, {totals['entities_skipped']} skipped")
    print(f"Memories:      {totals['memories_created']} created, {totals['memories_skipped']} skipped (duplicates)")
    print(f"Relationships: {totals['relationships_created']} created, {totals['relationships_failed']} failed")

    if totals["errors"]:
        print(f"\nErrors ({len(totals['errors'])}):")
        for err in totals["errors"][:10]:
            print(f"  - {err}")
        if len(totals["errors"]) > 10:
            print(f"  ... and {len(totals['errors']) - 10} more")

    print(f"\n{'='*60}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Ingest seed knowledge into engram")
    parser.add_argument("files", nargs="+", help="JSON seed files to ingest")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--data-dir", help="Engram data directory (default: ~/.engram/data)")

    args = parser.parse_args()

    # Initialize store
    data_dir = Path(args.data_dir) if args.data_dir else None
    store = MemoryStore(data_dir=data_dir)

    print(f"Engram data directory: {store.data_dir}")
    if args.dry_run:
        print("*** DRY RUN MODE - No changes will be made ***")

    all_stats = []

    for filepath in args.files:
        try:
            seed = load_seed_file(filepath)
            stats = ingest_seed(store, seed, dry_run=args.dry_run)
            all_stats.append(stats)
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            all_stats.append({"errors": [str(e)]})

    print_summary(all_stats)

    # Print final stats
    if not args.dry_run:
        final_stats = store.get_stats()
        print(f"\nFinal engram stats:")
        print(f"  Total memories: {final_stats.get('total_memories', 0)}")
        print(f"  Graph nodes: {final_stats.get('graph', {}).get('total_nodes', 0)}")
        print(f"  Graph edges: {final_stats.get('graph', {}).get('total_edges', 0)}")


if __name__ == "__main__":
    main()
