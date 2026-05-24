#!/usr/bin/env python3
"""Garbage collection CLI tool for OmniLab orphaned labs and nodes.

Orphan detection criteria:
  - No live Docker container (omnilab-<node_id> for docker nodes)
  - No live Docker network (omnilab-lab-<lab_id> for the lab)
  - No QEMU pid file (for QEMU nodes)
  - Status is 'stopped' in DB
  - Created >24 hours ago

Usage:
  python3 -m backend.cli.gc --dry-run    # Report orphans, no changes
  python3 -m backend.cli.gc --apply      # Delete orphaned labs & nodes
"""

import argparse
import asyncio
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import docker  # type: ignore[import-untyped]
    from docker.errors import NotFound  # type: ignore[import-untyped]
    DOCKER_AVAILABLE = True
except ImportError:
    docker = None  # type: ignore[assignment]
    NotFound = Exception  # type: ignore[assignment,misc]
    DOCKER_AVAILABLE = False


def get_db_path() -> Path:
    """Return path to OmniLab production DB."""
    return Path.home() / ".omnilab" / "omnilab.db"


def connect_docker():
    """Connect to Docker daemon or return None if unavailable."""
    if not DOCKER_AVAILABLE:
        return None
    try:
        client = docker.from_env()
        client.ping()
        return client
    except Exception:
        return None


def is_container_running(docker_client, node_id: str) -> bool:
    """Check if a docker container for this node exists and is running."""
    if docker_client is None:
        return False
    
    container_name = f"omnilab-{node_id}"
    try:
        container = docker_client.containers.get(container_name)
        return container.status in ("running", "created", "restarting", "paused")
    except NotFound:
        return False
    except Exception:
        return False


def is_network_alive(docker_client, lab_id: str) -> bool:
    """Check if a docker network for this lab exists."""
    if docker_client is None:
        return False
    
    network_name = f"omnilab-lab-{lab_id}"
    try:
        docker_client.networks.get(network_name)
        return True
    except NotFound:
        return False
    except Exception:
        return False


def is_qemu_running(node_id: str) -> bool:
    """Check if QEMU pid file exists for this node."""
    pid_file = Path.home() / ".omnilab" / "labs" / f"{node_id}.pid"
    return pid_file.exists()


def find_orphans(db_path: Path, docker_client, min_age_hours: int = 24) -> tuple[list, list]:
    """Scan DB for orphaned labs and nodes.
    
    Returns:
        (orphaned_labs, orphaned_nodes) — each is a list of dicts with id, name, created_at, reason
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    cutoff = datetime.now(timezone.utc) - timedelta(hours=min_age_hours)
    cutoff_str = cutoff.isoformat()
    
    orphaned_labs = []
    orphaned_nodes = []
    
    # Find orphaned nodes first
    # If created_at is NULL, treat as older than cutoff (legacy data)
    cursor = conn.execute("""
        SELECT id, lab_id, name, type, status, created_at
        FROM nodes
        WHERE status = 'stopped'
          AND (created_at IS NULL OR created_at < ?)
        ORDER BY created_at ASC
    """, (cutoff_str,))
    
    for row in cursor:
        node_id = row["id"]
        node_type = row["type"]
        reasons = []
        
        # Check liveness based on node type
        if node_type == "docker":
            if is_container_running(docker_client, node_id):
                continue  # Not orphaned — container is alive
            reasons.append("no live container")
        else:
            # QEMU or other
            if is_qemu_running(node_id):
                continue  # Not orphaned — QEMU process active
            reasons.append("no QEMU pid file")
        
        orphaned_nodes.append({
            "id": node_id,
            "lab_id": row["lab_id"],
            "name": row["name"],
            "type": node_type,
            "created_at": row["created_at"],
            "reason": ", ".join(reasons),
        })
    
    # Find orphaned labs (labs with no live artifacts)
    # If created_at is NULL, treat as older than cutoff (legacy data)
    cursor = conn.execute("""
        SELECT id, name, status, created_at
        FROM labs
        WHERE status = 'stopped'
          AND (created_at IS NULL OR created_at < ?)
        ORDER BY created_at ASC
    """, (cutoff_str,))
    
    for row in cursor:
        lab_id = row["id"]
        reasons = []
        
        # Check if lab network is alive
        if is_network_alive(docker_client, lab_id):
            continue  # Not orphaned — network exists
        
        reasons.append("no live network")
        
        # Check if any nodes in this lab have live artifacts
        node_cursor = conn.execute("""
            SELECT id, type FROM nodes WHERE lab_id = ?
        """, (lab_id,))
        
        has_live_node = False
        for node_row in node_cursor:
            node_id = node_row["id"]
            node_type = node_row["type"]
            
            if node_type == "docker" and is_container_running(docker_client, node_id):
                has_live_node = True
                break
            elif node_type != "docker" and is_qemu_running(node_id):
                has_live_node = True
                break
        
        if has_live_node:
            continue  # Not orphaned — at least one node is alive
        
        orphaned_labs.append({
            "id": lab_id,
            "name": row["name"],
            "created_at": row["created_at"],
            "reason": ", ".join(reasons),
        })
    
    conn.close()
    return orphaned_labs, orphaned_nodes


def delete_orphans(db_path: Path, labs: list, nodes: list) -> tuple[int, int]:
    """Delete orphaned labs and nodes from DB.
    
    Returns:
        (deleted_lab_count, deleted_node_count)
    """
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    deleted_nodes = 0
    for node in nodes:
        cursor.execute("DELETE FROM nodes WHERE id = ?", (node["id"],))
        deleted_nodes += 1
    
    deleted_labs = 0
    for lab in labs:
        # Delete associated links first (foreign key constraint)
        cursor.execute("DELETE FROM links WHERE lab_id = ?", (lab["id"],))
        # Delete the lab
        cursor.execute("DELETE FROM labs WHERE id = ?", (lab["id"],))
        deleted_labs += 1
    
    conn.commit()
    conn.close()
    
    return deleted_labs, deleted_nodes


def main():
    parser = argparse.ArgumentParser(
        description="OmniLab orphan garbage collector — clean up stale labs and nodes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report orphans without deleting (default mode)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Delete orphaned labs and nodes from database",
    )
    parser.add_argument(
        "--min-age-hours",
        type=int,
        default=24,
        help="Minimum age in hours for orphan candidates (default: 24)",
    )
    
    args = parser.parse_args()
    
    # Default to dry-run if neither flag is set
    if not args.dry_run and not args.apply:
        args.dry_run = True
    
    db_path = get_db_path()
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}", file=sys.stderr)
        sys.exit(1)
    
    # Connect to Docker
    docker_client = connect_docker()
    if docker_client is None:
        print("⚠️  Docker daemon not available — orphan detection limited to DB state only", file=sys.stderr)
    
    # Scan for orphans
    print(f"🔍 Scanning for orphans (min age: {args.min_age_hours}h, stopped status)...\n")
    orphaned_labs, orphaned_nodes = find_orphans(db_path, docker_client, args.min_age_hours)
    
    # Report findings
    if orphaned_nodes:
        print(f"📦 Found {len(orphaned_nodes)} orphaned node(s):\n")
        for node in orphaned_nodes:
            print(f"  • {node['name'][:30]:30s} (ID: {node['id'][:8]}..., type: {node['type']:8s})")
            print(f"    Created: {node['created_at']}, Reason: {node['reason']}")
    else:
        print("✅ No orphaned nodes found.")
    
    print()
    
    if orphaned_labs:
        print(f"🗂️  Found {len(orphaned_labs)} orphaned lab(s):\n")
        for lab in orphaned_labs:
            print(f"  • {lab['name'][:40]:40s} (ID: {lab['id'][:8]}...)")
            print(f"    Created: {lab['created_at']}, Reason: {lab['reason']}")
    else:
        print("✅ No orphaned labs found.")
    
    print()
    
    # Execute deletion if --apply
    if args.apply:
        if not orphaned_labs and not orphaned_nodes:
            print("🎉 Nothing to delete.")
            return
        
        print("🗑️  Deleting orphans...")
        deleted_labs, deleted_nodes = delete_orphans(db_path, orphaned_labs, orphaned_nodes)
        print(f"✅ Deleted {deleted_labs} lab(s) and {deleted_nodes} node(s).")
    else:
        print("ℹ️  Dry-run mode — no changes made. Use --apply to delete.")


if __name__ == "__main__":
    main()
