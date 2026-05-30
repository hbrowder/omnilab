"""
Topology Mapper: Maps network interfaces to link_id for traffic visualization.

CRE-68 Phase 3 Milestone 2: Packet Capture Integration
- Queries lab topology from database
- Maps interface names (eth0, br-123, etc.) to link_id
- Handles node-to-node and node-to-network links
- Caches topology for performance
"""

import re
import sqlite3
from pathlib import Path


class TopologyMapper:
    """Maps network interface names to link IDs in a lab topology."""

    def __init__(self, db_path: str | None = None):
        """Initialize mapper with database path."""
        if db_path is None:
            db_path = str(Path.home() / '.omnilab' / 'omnilab.db')
        self.db_path: str = db_path
        self._topology_cache = {}  # {lab_id: {interface_name: link_id}}

    def get_link_id_for_interface(self, lab_id: str, interface: str) -> str | None:
        """
        Get link_id for a network interface.

        Args:
            lab_id: Lab identifier
            interface: Interface name (e.g., 'eth0', 'br-lab1-net2')

        Returns:
            link_id if found, None otherwise
        """
        # Load topology if not cached
        if lab_id not in self._topology_cache:
            self._load_topology(lab_id)

        # Direct lookup
        cache = self._topology_cache.get(lab_id, {})
        if interface in cache:
            return cache[interface]

        # Try pattern matching for bridge interfaces
        # Format: br-{lab_name}-net{network_id} or br-{lab_id}-{network_id}
        bridge_match = re.match(r'br-[\w-]+-(?:net)?(\d+)', interface)
        if bridge_match:
            net_id = int(bridge_match.group(1))
            # Find links connected to this network
            for iface, link_id in cache.items():
                if f'net{net_id}' in iface or f'-{net_id}' in iface:
                    return link_id

        return None

    def _load_topology(self, lab_id: str):
        """Load topology from database and build interface -> link_id mapping."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        mapping = {}

        try:
            # Get all nodes in the lab
            cursor.execute("""
                SELECT id, name, interfaces
                FROM nodes
                WHERE lab_id = ?
            """, (lab_id,))

            nodes = {row['id']: {'name': row['name'], 'interfaces': row['interfaces']}
                    for row in cursor.fetchall()}

            # Get all links in the lab
            cursor.execute("""
                SELECT id, src_node_id, dst_node_id, network_id, src_interface, dst_interface
                FROM links
                WHERE lab_id = ?
            """, (lab_id,))

            for row in cursor.fetchall():
                link_id = row['id']
                src_node_id = row['src_node_id']
                dst_node_id = row['dst_node_id']
                network_id = row['network_id']
                src_iface = row['src_interface']
                dst_iface = row['dst_interface']

                # Node-to-node link
                if dst_node_id:
                    src_node = nodes.get(src_node_id, {})
                    dst_node = nodes.get(dst_node_id, {})

                    # Map source interface
                    if src_iface:
                        mapping[src_iface] = link_id
                        # Also map as node_name:interface
                        if src_node.get('name'):
                            mapping[f"{src_node['name']}:{src_iface}"] = link_id

                    # Map destination interface
                    if dst_iface:
                        mapping[dst_iface] = link_id
                        if dst_node.get('name'):
                            mapping[f"{dst_node['name']}:{dst_iface}"] = link_id

                # Node-to-network link
                elif network_id:

                    # Map source interface
                    if src_iface:
                        mapping[src_iface] = link_id
                        src_node = nodes.get(src_node_id, {})
                        if src_node.get('name'):
                            mapping[f"{src_node['name']}:{src_iface}"] = link_id

                    # Map network bridge
                    # Common formats: br-lab1-net2, br-{lab_id}-2
                    bridge_name = f"br-{lab_id}-net{network_id}"
                    mapping[bridge_name] = link_id
                    mapping[f"br-{lab_id}-{network_id}"] = link_id
                    mapping[f"net{network_id}"] = link_id

            self._topology_cache[lab_id] = mapping

        finally:
            conn.close()

    def clear_cache(self, lab_id: str | None = None):
        """Clear topology cache for a lab or all labs."""
        if lab_id:
            self._topology_cache.pop(lab_id, None)
        else:
            self._topology_cache.clear()

    def get_all_interfaces(self, lab_id: str) -> dict[str, str]:
        """Get all interface -> link_id mappings for a lab."""
        if lab_id not in self._topology_cache:
            self._load_topology(lab_id)
        return self._topology_cache.get(lab_id, {}).copy()

    def get_container_interfaces(self, lab_id: str) -> dict[tuple[str, str], str]:
        """
        Get container-interface to link_id mappings for in-container tcpdump.

        Returns:
            Dict mapping (container_name, interface_name) -> link_id
            Example: {("omnilab-209b6bf7...", "eth0"): "860d1ee1..."}
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        mapping = {}
        CONTAINER_PREFIX = "omnilab-"

        try:
            # Get all links with their node and interface information
            cursor.execute("""
                SELECT
                    l.id as link_id,
                    l.src_node_id,
                    l.dst_node_id,
                    l.src_interface,
                    l.dst_interface,
                    src.name as src_name,
                    dst.name as dst_name
                FROM links l
                LEFT JOIN nodes src ON l.src_node_id = src.id
                LEFT JOIN nodes dst ON l.dst_node_id = dst.id
                WHERE l.lab_id = ?
            """, (lab_id,))

            for row in cursor.fetchall():
                link_id = row['link_id']

                # Source side: map (container_name, interface) -> link_id
                if row['src_node_id'] and row['src_interface']:
                    container_name = f"{CONTAINER_PREFIX}{row['src_node_id']}"
                    mapping[(container_name, row['src_interface'])] = link_id

                # Destination side: map (container_name, interface) -> link_id
                if row['dst_node_id'] and row['dst_interface']:
                    container_name = f"{CONTAINER_PREFIX}{row['dst_node_id']}"
                    mapping[(container_name, row['dst_interface'])] = link_id

            return mapping

        finally:
            conn.close()


# Global instance
_mapper = None

def get_topology_mapper() -> TopologyMapper:
    """Get global topology mapper instance."""
    global _mapper
    if _mapper is None:
        _mapper = TopologyMapper()
    return _mapper
