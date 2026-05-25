#!/usr/bin/env python3
"""
Migration 003: Add topology columns for traffic visualization

Adds:
- nodes.interfaces (JSON column for interface definitions)
- links.network_id (optional network association)
- Defaults for existing links without interface names

This enables packet capture -> link_id mapping for traffic visualization.
"""

import sqlite3
import os
import json


def migrate(db_path: str):
    """Apply migration to add topology columns."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=== Migration 003: Add Topology Columns ===")
    
    try:
        # Check if nodes.interfaces already exists
        cursor.execute("PRAGMA table_info(nodes)")
        columns = {col[1] for col in cursor.fetchall()}
        
        if 'interfaces' not in columns:
            print("Adding nodes.interfaces column...")
            cursor.execute("""
                ALTER TABLE nodes 
                ADD COLUMN interfaces TEXT DEFAULT '[]'
            """)
            print("✓ Added nodes.interfaces")
        else:
            print("✓ nodes.interfaces already exists")
        
        # Check if links.network_id already exists
        cursor.execute("PRAGMA table_info(links)")
        columns = {col[1] for col in cursor.fetchall()}
        
        if 'network_id' not in columns:
            print("Adding links.network_id column...")
            cursor.execute("""
                ALTER TABLE links 
                ADD COLUMN network_id TEXT
            """)
            print("✓ Added links.network_id")
        else:
            print("✓ links.network_id already exists")
        
        # Initialize interfaces for existing nodes
        print("Initializing interfaces for existing nodes...")
        cursor.execute("SELECT id, name, type FROM nodes WHERE interfaces IS NULL OR interfaces = '' OR interfaces = '[]'")
        nodes = cursor.fetchall()
        
        for node_id, name, node_type in nodes:
            # Default interface configuration based on node type
            if node_type in ('router', 'switch', 'l3switch'):
                # Network devices get eth0-eth3
                interfaces = [
                    {"name": "eth0", "type": "ethernet", "status": "up"},
                    {"name": "eth1", "type": "ethernet", "status": "up"},
                    {"name": "eth2", "type": "ethernet", "status": "up"},
                    {"name": "eth3", "type": "ethernet", "status": "up"},
                ]
            elif node_type in ('docker', 'vm', 'qemu'):
                # Hosts get eth0-eth1
                interfaces = [
                    {"name": "eth0", "type": "ethernet", "status": "up"},
                    {"name": "eth1", "type": "ethernet", "status": "up"},
                ]
            else:
                # Generic: single interface
                interfaces = [
                    {"name": "eth0", "type": "ethernet", "status": "up"},
                ]
            
            cursor.execute("""
                UPDATE nodes 
                SET interfaces = ?
                WHERE id = ?
            """, (json.dumps(interfaces), node_id))
            print(f"  ✓ {name}: {len(interfaces)} interfaces")
        
        # Set default interface names for links without them
        print("Setting default interface names for links...")
        cursor.execute("""
            SELECT id, src_node_id, dst_node_id 
            FROM links 
            WHERE src_interface IS NULL OR dst_interface IS NULL
        """)
        links = cursor.fetchall()
        
        # Track interface usage per node
        interface_usage = {}
        
        for link_id, src_node_id, dst_node_id in links:
            # Assign next available interface for source node
            if src_node_id not in interface_usage:
                interface_usage[src_node_id] = 0
            src_if = f"eth{interface_usage[src_node_id]}"
            interface_usage[src_node_id] += 1
            
            # Assign next available interface for destination node
            if dst_node_id not in interface_usage:
                interface_usage[dst_node_id] = 0
            dst_if = f"eth{interface_usage[dst_node_id]}"
            interface_usage[dst_node_id] += 1
            
            cursor.execute("""
                UPDATE links
                SET src_interface = ?, dst_interface = ?
                WHERE id = ?
            """, (src_if, dst_if, link_id))
            print(f"  ✓ Link: {src_if} <--> {dst_if}")
        
        conn.commit()
        print("\n✅ Migration 003 completed successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration 003 failed: {e}")
        raise
    finally:
        conn.close()


def rollback(db_path: str):
    """Rollback is not supported for ALTER TABLE ADD COLUMN in SQLite."""
    print("⚠️  Rollback not supported (SQLite doesn't support DROP COLUMN)")
    print("   To rollback, restore from backup or recreate database")


if __name__ == '__main__':
    db_path = os.path.expanduser('~/.omnilab/omnilab.db')
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        rollback(db_path)
    else:
        migrate(db_path)
