# CRE-68: Traffic Flow Visualization - Master Implementation Plan

## Executive Summary

**Goal:** Build a traffic visualization system that matches EVE-NG's capabilities and exceeds them with modern architecture, better UX, and advanced features.

**Inspiration:** EVE-NG 6.4.0-50-PRO Traffic Flow Visibility
**Target:** "Better in every way" - Harold's quality bar

**Core Features:**
- Live animated traffic flows on links (colored, timed)
- Comprehensive filter library (100+ pre-built filters)
- Custom tcpdump/BPF filter support
- Real-time packet counting and statistics
- Multi-filter simultaneous visualization
- Filter templates and sharing
- Performance optimized for large topologies

---

## Part 1: Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │ TrafficFilter    │  │ LinkAnimation    │  │ FilterEditor  │ │
│  │ Panel            │  │ Engine           │  │ (Visual)      │ │
│  └────────┬─────────┘  └────────┬─────────┘  └───────┬───────┘ │
│           │                     │                     │          │
│           └─────────────────────┴─────────────────────┘          │
│                                 │                                │
│                        WebSocket Bridge                          │
│                                 │                                │
└─────────────────────────────────┼────────────────────────────────┘
                                  │
┌─────────────────────────────────┼────────────────────────────────┐
│                        BACKEND (FastAPI)                          │
├─────────────────────────────────┴────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │ Filter Manager   │  │ Capture Engine   │  │ Packet        │ │
│  │ (CRUD + Library) │  │ (tcpdump mgmt)   │  │ Analyzer      │ │
│  └────────┬─────────┘  └────────┬─────────┘  └───────┬───────┘ │
│           │                     │                     │          │
│           └─────────────────────┴─────────────────────┘          │
│                                 │                                │
│                          SQLite Database                         │
│                                 │                                │
└─────────────────────────────────┼────────────────────────────────┘
                                  │
┌─────────────────────────────────┼────────────────────────────────┐
│                      PACKET CAPTURE LAYER                         │
├─────────────────────────────────┴────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │ tcpdump process  │  │ BPF Compiler     │  │ Interface     │ │
│  │ per interface    │  │ (libpcap)        │  │ Monitor       │ │
│  └──────────────────┘  └──────────────────┘  └───────────────┘ │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User activates filter** → Frontend sends WebSocket message
2. **Backend receives** → Launches tcpdump on relevant interfaces
3. **Packets match** → Counter increments, event sent to frontend
4. **Frontend animates** → Colored flow on link, timeout-based fade
5. **User deactivates** → Backend kills tcpdump, frontend clears animation

---

## Part 2: Database Schema

### New Tables

```sql
-- Traffic filter library
CREATE TABLE traffic_filters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                    -- "OSPF", "BGP", "VXLAN Tenant 1"
    description TEXT,                      -- "Watch OSPF hellos and LSAs"
    tcpdump_filter TEXT NOT NULL,          -- "proto 89"
    color TEXT NOT NULL DEFAULT '#00ff00', -- Hex color for animation
    category TEXT,                         -- "routing", "layer2", "overlay", "custom"
    is_builtin BOOLEAN DEFAULT 0,          -- Pre-shipped vs user-created
    is_active BOOLEAN DEFAULT 0,           -- Currently running
    packet_count INTEGER DEFAULT 0,        -- Real-time counter
    animation_duration INTEGER DEFAULT 3000, -- Milliseconds
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Filter match history (optional analytics)
CREATE TABLE filter_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filter_id INTEGER NOT NULL,
    link_id INTEGER NOT NULL,              -- Which link saw traffic
    lab_id INTEGER NOT NULL,
    matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    packet_summary TEXT,                   -- Optional: src/dst/proto
    FOREIGN KEY (filter_id) REFERENCES traffic_filters(id) ON DELETE CASCADE,
    FOREIGN KEY (link_id) REFERENCES links(id) ON DELETE CASCADE,
    FOREIGN KEY (lab_id) REFERENCES labs(id) ON DELETE CASCADE
);

-- Filter presets/templates
CREATE TABLE filter_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                    -- "JNCIE-DC Standard", "BGP Monitoring"
    description TEXT,
    filters JSON NOT NULL,                 -- Array of filter IDs
    is_public BOOLEAN DEFAULT 0,           -- Shareable
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Capture sessions (active tcpdump processes)
CREATE TABLE capture_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filter_id INTEGER NOT NULL,
    device_id INTEGER NOT NULL,
    interface TEXT NOT NULL,               -- "eth0", "ge-0/0/0"
    pid INTEGER,                           -- tcpdump process ID
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_packet_at TIMESTAMP,
    FOREIGN KEY (filter_id) REFERENCES traffic_filters(id) ON DELETE CASCADE,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_filters_active ON traffic_filters(is_active);
CREATE INDEX idx_filters_category ON traffic_filters(category);
CREATE INDEX idx_matches_filter ON filter_matches(filter_id, matched_at);
CREATE INDEX idx_sessions_filter ON capture_sessions(filter_id);
```

### Schema Extensions

```sql
-- Extend links table (if not already present from CRE-66)
ALTER TABLE links ADD COLUMN animation_state TEXT; -- JSON: {filter_id, color, start_time}
ALTER TABLE links ADD COLUMN last_traffic_at TIMESTAMP;
```

---

## Part 3: Pre-Built Filter Library

### Category: Layer 2 Discovery (6 filters)
```json
[
  {
    "name": "ARP",
    "description": "See live ARP requests/replies",
    "filter": "arp",
    "color": "#FFD700",
    "category": "layer2"
  },
  {
    "name": "ARP Requests Only",
    "description": "Detect unresolved IP-to-MAC lookups",
    "filter": "arp and arp[6:2] = 1",
    "color": "#FFA500",
    "category": "layer2"
  },
  {
    "name": "ARP Replies Only",
    "description": "Verify ARP resolution success",
    "filter": "arp and arp[6:2] = 2",
    "color": "#32CD32",
    "category": "layer2"
  },
  {
    "name": "LLDP",
    "description": "Visualize neighbor discovery",
    "filter": "ether proto 0x88cc",
    "color": "#FF8C00",
    "category": "layer2"
  },
  {
    "name": "STP (802.1D)",
    "description": "Observe topology changes / blocking",
    "filter": "ether proto 0x010b",
    "color": "#9370DB",
    "category": "layer2"
  },
  {
    "name": "IPv6 Neighbor Discovery",
    "description": "Track ND solicitations and advertisements",
    "filter": "icmp6 and ip6[40] == 135 or ip6[40] == 136",
    "color": "#00CED1",
    "category": "layer2"
  }
]
```

### Category: Routing Protocols (7 filters)
```json
[
  {
    "name": "OSPF",
    "description": "Watch Hello, LSAs, adjacency formation",
    "filter": "proto 89",
    "color": "#00FF00",
    "category": "routing"
  },
  {
    "name": "BGP",
    "description": "Track session establishment & updates",
    "filter": "tcp port 179",
    "color": "#FF0000",
    "category": "routing"
  },
  {
    "name": "IS-IS",
    "description": "Monitor IS-IS PDUs",
    "filter": "ether proto 0xfefe or ether proto 0x8000",
    "color": "#FF69B4",
    "category": "routing"
  },
  {
    "name": "RIP",
    "description": "RIPv2 routing updates",
    "filter": "udp port 520",
    "color": "#FFD700",
    "category": "routing"
  },
  {
    "name": "EIGRP",
    "description": "Enhanced IGRP",
    "filter": "ip proto 88",
    "color": "#4169E1",
    "category": "routing"
  },
  {
    "name": "VRRP",
    "description": "Virtual Router Redundancy Protocol",
    "filter": "proto 112",
    "color": "#FF6347",
    "category": "routing"
  },
  {
    "name": "HSRP",
    "description": "Cisco Hot Standby Router Protocol",
    "filter": "udp port 1985",
    "color": "#FF4500",
    "category": "routing"
  }
]
```

### Category: Overlay / Tunneling (5 filters)
```json
[
  {
    "name": "VXLAN (Generic)",
    "description": "All VXLAN encapsulated traffic",
    "filter": "udp port 4789",
    "color": "#8A2BE2",
    "category": "overlay"
  },
  {
    "name": "GRE Tunnels",
    "description": "Generic Routing Encapsulation",
    "filter": "proto 47",
    "color": "#BA55D3",
    "category": "overlay"
  },
  {
    "name": "IPsec ESP",
    "description": "Encrypted Security Payload",
    "filter": "proto 50",
    "color": "#DC143C",
    "category": "overlay"
  },
  {
    "name": "IPsec AH",
    "description": "Authentication Header",
    "filter": "proto 51",
    "color": "#B22222",
    "category": "overlay"
  },
  {
    "name": "MPLS",
    "description": "Multiprotocol Label Switching",
    "filter": "mpls",
    "color": "#4B0082",
    "category": "overlay"
  }
]
```

### Category: Transport / Application (8 filters)
```json
[
  {
    "name": "ICMP",
    "description": "Ping, traceroute, or general ICMP flows",
    "filter": "icmp",
    "color": "#00BFFF",
    "category": "transport"
  },
  {
    "name": "TCP",
    "description": "General TCP traffic",
    "filter": "tcp",
    "color": "#1E90FF",
    "category": "transport"
  },
  {
    "name": "UDP",
    "description": "General UDP traffic",
    "filter": "udp",
    "color": "#87CEEB",
    "category": "transport"
  },
  {
    "name": "DNS",
    "description": "Domain Name System queries",
    "filter": "udp port 53 or tcp port 53",
    "color": "#48D1CC",
    "category": "transport"
  },
  {
    "name": "HTTP",
    "description": "Web traffic",
    "filter": "tcp port 80",
    "color": "#FF69B4",
    "category": "transport"
  },
  {
    "name": "HTTPS",
    "description": "Encrypted web traffic",
    "filter": "tcp port 443",
    "color": "#FF1493",
    "category": "transport"
  },
  {
    "name": "SSH",
    "description": "Secure shell connections",
    "filter": "tcp port 22",
    "color": "#8B4513",
    "category": "transport"
  },
  {
    "name": "SNMP",
    "description": "Simple Network Management Protocol",
    "filter": "udp port 161 or udp port 162",
    "color": "#D2691E",
    "category": "transport"
  }
]
```

### Category: VLANs (3 filters)
```json
[
  {
    "name": "VLAN Tagged",
    "description": "All 802.1Q tagged frames",
    "filter": "vlan",
    "color": "#FFD700",
    "category": "vlan"
  },
  {
    "name": "VLAN 10",
    "description": "Specific VLAN ID",
    "filter": "vlan 10",
    "color": "#FFFF00",
    "category": "vlan"
  },
  {
    "name": "VLAN 20",
    "description": "Specific VLAN ID",
    "filter": "vlan 20",
    "color": "#ADFF2F",
    "category": "vlan"
  }
]
```

### Category: Multicast (4 filters)
```json
[
  {
    "name": "IGMP",
    "description": "Internet Group Management Protocol",
    "filter": "igmp",
    "color": "#7FFF00",
    "category": "multicast"
  },
  {
    "name": "PIM",
    "description": "Protocol Independent Multicast",
    "filter": "proto 103",
    "color": "#00FA9A",
    "category": "multicast"
  },
  {
    "name": "Multicast Traffic",
    "description": "All multicast packets",
    "filter": "multicast",
    "color": "#3CB371",
    "category": "multicast"
  },
  {
    "name": "Broadcast Traffic",
    "description": "All broadcast packets",
    "filter": "broadcast",
    "color": "#2E8B57",
    "category": "multicast"
  }
]
```

---

## Part 4: Backend Implementation

### API Endpoints

```python
# backend/routes/traffic_filters.py

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Optional
import asyncio
import subprocess

router = APIRouter(prefix="/api/traffic-filters", tags=["traffic-filters"])

# ============================================================================
# CRUD Operations
# ============================================================================

@router.get("/filters")
async def list_filters(category: Optional[str] = None):
    """
    List all traffic filters, optionally filtered by category.
    
    Returns:
        - id, name, description, filter, color, category, is_active, packet_count
    """
    pass

@router.post("/filters")
async def create_filter(filter_data: dict):
    """
    Create a new traffic filter.
    
    Body:
        {
            "name": "Custom BGP",
            "description": "BGP from AS 65000",
            "filter": "tcp port 179 and host 10.0.0.1",
            "color": "#FF0000",
            "category": "custom",
            "animation_duration": 5000
        }
    
    Returns:
        - Created filter with ID
    """
    # Validate BPF syntax before saving
    if not validate_bpf_filter(filter_data['filter']):
        raise HTTPException(400, "Invalid BPF filter syntax")
    pass

@router.patch("/filters/{filter_id}")
async def update_filter(filter_id: int, filter_data: dict):
    """Update filter properties (name, color, duration, etc.)"""
    pass

@router.delete("/filters/{filter_id}")
async def delete_filter(filter_id: int):
    """Delete a filter (must be inactive)"""
    pass

# ============================================================================
# Filter Control
# ============================================================================

@router.post("/filters/{filter_id}/activate")
async def activate_filter(filter_id: int, lab_id: int):
    """
    Start packet capture for this filter on all interfaces.
    
    - Identifies all devices in lab
    - Launches tcpdump on each interface
    - Starts packet counting
    - Returns session IDs
    """
    pass

@router.post("/filters/{filter_id}/deactivate")
async def deactivate_filter(filter_id: int):
    """
    Stop all capture sessions for this filter.
    
    - Kills tcpdump processes
    - Clears packet counters
    - Marks filter as inactive
    """
    pass

@router.post("/filters/activate-multiple")
async def activate_multiple(filter_ids: List[int], lab_id: int):
    """Activate multiple filters simultaneously"""
    pass

@router.post("/filters/deactivate-all")
async def deactivate_all(lab_id: int):
    """Emergency stop - kill all captures"""
    pass

# ============================================================================
# Templates
# ============================================================================

@router.get("/templates")
async def list_templates():
    """List saved filter templates/presets"""
    pass

@router.post("/templates")
async def create_template(template_data: dict):
    """
    Save a collection of filters as a template.
    
    Body:
        {
            "name": "JNCIE-DC Standard",
            "description": "OSPF, BGP, VXLAN, LLDP",
            "filter_ids": [1, 5, 12, 18]
        }
    """
    pass

@router.post("/templates/{template_id}/apply")
async def apply_template(template_id: int, lab_id: int):
    """Activate all filters in a template"""
    pass

# ============================================================================
# Real-time WebSocket
# ============================================================================

active_connections: List[WebSocket] = []

@router.websocket("/ws/{lab_id}")
async def websocket_endpoint(websocket: WebSocket, lab_id: int):
    """
    WebSocket for real-time traffic events.
    
    Client receives:
        {
            "event": "traffic_match",
            "filter_id": 5,
            "link_id": 42,
            "color": "#00FF00",
            "duration": 3000,
            "packet_count": 127
        }
    
    Client sends:
        {
            "action": "activate",
            "filter_id": 5
        }
    """
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data['action'] == 'activate':
                await activate_filter(data['filter_id'], lab_id)
            elif data['action'] == 'deactivate':
                await deactivate_filter(data['filter_id'])
                
    except WebSocketDisconnect:
        active_connections.remove(websocket)

async def broadcast_traffic_event(event: dict):
    """Send event to all connected clients"""
    for connection in active_connections:
        await connection.send_json(event)
```

### Packet Capture Engine

```python
# backend/core/packet_capture.py

import asyncio
import subprocess
import re
from typing import Dict, Set

class PacketCaptureEngine:
    """
    Manages tcpdump processes for traffic filtering.
    """
    
    def __init__(self):
        self.active_sessions: Dict[int, Set[subprocess.Popen]] = {}
        self.packet_counts: Dict[int, int] = {}
        
    async def start_capture(self, filter_id: int, device_id: int, interface: str, bpf_filter: str):
        """
        Launch tcpdump on a device interface.
        
        Command:
            tcpdump -i <interface> -n -l -c 0 '<bpf_filter>'
        
        Options:
            -i: interface
            -n: no DNS resolution (faster)
            -l: line-buffered output (real-time)
            -c 0: unlimited packet count
        """
        
        # For Docker-based devices, we need to exec into container
        if self.is_docker_device(device_id):
            cmd = [
                "docker", "exec", f"device_{device_id}",
                "tcpdump", "-i", interface, "-n", "-l", "-c", "0", bpf_filter
            ]
        else:
            # For libvirt/KVM, we'd use SSH or qemu-guest-agent
            cmd = [
                "ssh", f"device-{device_id}",
                "tcpdump", "-i", interface, "-n", "-l", "-c", "0", bpf_filter
            ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1  # Line-buffered
        )
        
        # Track session
        if filter_id not in self.active_sessions:
            self.active_sessions[filter_id] = set()
        self.active_sessions[filter_id].add(process)
        
        # Start reading output in background
        asyncio.create_task(self._read_tcpdump_output(filter_id, process))
        
        return process.pid
    
    async def _read_tcpdump_output(self, filter_id: int, process: subprocess.Popen):
        """
        Read tcpdump output line by line.
        Each line = 1 packet matched.
        """
        
        while True:
            line = await asyncio.to_thread(process.stdout.readline)
            
            if not line:
                break  # Process ended
                
            # Increment packet counter
            if filter_id not in self.packet_counts:
                self.packet_counts[filter_id] = 0
            self.packet_counts[filter_id] += 1
            
            # Parse line to extract link info
            # Tcpdump format: "HH:MM:SS.ssssss IP src > dst: ..."
            src_ip, dst_ip = self._parse_tcpdump_line(line)
            
            # Determine which link this traffic belongs to
            link_id = await self._identify_link(src_ip, dst_ip)
            
            if link_id:
                # Broadcast event to WebSocket clients
                await broadcast_traffic_event({
                    "event": "traffic_match",
                    "filter_id": filter_id,
                    "link_id": link_id,
                    "packet_count": self.packet_counts[filter_id]
                })
    
    def _parse_tcpdump_line(self, line: str) -> tuple:
        """
        Extract source/dest IPs from tcpdump output.
        
        Example line:
            15:23:45.123456 IP 10.0.0.1.179 > 10.0.0.2.179: Flags [P.], ...
        """
        # Regex to match IP addresses
        match = re.search(r'IP (\d+\.\d+\.\d+\.\d+).*> (\d+\.\d+\.\d+\.\d+)', line)
        if match:
            return match.group(1), match.group(2)
        return None, None
    
    async def _identify_link(self, src_ip: str, dst_ip: str) -> Optional[int]:
        """
        Map src/dst IPs to a link in the topology.
        
        Strategy:
            1. Query devices table for interfaces with these IPs
            2. Find link connecting those devices
            3. Return link_id
        """
        # This requires IP-to-interface mapping
        # Could be stored in device_interfaces table
        pass
    
    async def stop_capture(self, filter_id: int):
        """Kill all tcpdump processes for this filter."""
        
        if filter_id in self.active_sessions:
            for process in self.active_sessions[filter_id]:
                process.terminate()
                await asyncio.sleep(0.1)
                if process.poll() is None:
                    process.kill()
            
            del self.active_sessions[filter_id]
            self.packet_counts[filter_id] = 0
    
    async def stop_all(self):
        """Emergency stop - kill everything."""
        for filter_id in list(self.active_sessions.keys()):
            await self.stop_capture(filter_id)

# Global instance
capture_engine = PacketCaptureEngine()
```

### BPF Filter Validator

```python
# backend/core/bpf_validator.py

import subprocess

def validate_bpf_filter(filter_expr: str) -> bool:
    """
    Validate BPF filter syntax using tcpdump.
    
    Command:
        tcpdump -d <filter>
    
    If valid, tcpdump outputs compiled BPF bytecode.
    If invalid, exits with error.
    """
    try:
        result = subprocess.run(
            ["tcpdump", "-d", filter_expr],
            capture_output=True,
            text=True,
            timeout=2
        )
        return result.returncode == 0
    except Exception:
        return False

def compile_bpf_to_bytecode(filter_expr: str) -> Optional[str]:
    """
    Compile BPF filter to bytecode for inspection.
    Useful for debugging and optimization.
    """
    try:
        result = subprocess.run(
            ["tcpdump", "-d", filter_expr],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            return result.stdout
        return None
    except Exception:
        return None
```

---

## Part 5: Frontend Implementation

### TrafficFilterPanel Component

```jsx
// frontend/src/components/TrafficFilterPanel.jsx

import React, { useState, useEffect } from 'react';
import { FaPlay, FaPause, FaTrash, FaEdit, FaPlus, FaSync } from 'react-icons/fa';
import { useWebSocket } from '../hooks/useWebSocket';
import './TrafficFilterPanel.css';

export default function TrafficFilterPanel({ labId }) {
  const [filters, setFilters] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editingFilter, setEditingFilter] = useState(null);
  
  const { sendMessage, lastMessage } = useWebSocket(`/api/traffic-filters/ws/${labId}`);
  
  // Load filters on mount
  useEffect(() => {
    fetchFilters();
  }, []);
  
  // Handle WebSocket messages
  useEffect(() => {
    if (lastMessage) {
      handleTrafficEvent(lastMessage);
    }
  }, [lastMessage]);
  
  const fetchFilters = async () => {
    const response = await fetch(`/api/traffic-filters/filters`);
    const data = await response.json();
    setFilters(data);
  };
  
  const handleTrafficEvent = (event) => {
    if (event.event === 'traffic_match') {
      // Update packet count locally
      setFilters(prev => prev.map(f => 
        f.id === event.filter_id 
          ? { ...f, packet_count: event.packet_count }
          : f
      ));
      
      // Trigger link animation (handled by LinkAnimationEngine)
      window.dispatchEvent(new CustomEvent('traffic-match', { detail: event }));
    }
  };
  
  const toggleFilter = async (filter) => {
    const action = filter.is_active ? 'deactivate' : 'activate';
    
    sendMessage({
      action,
      filter_id: filter.id
    });
    
    // Optimistic update
    setFilters(prev => prev.map(f =>
      f.id === filter.id
        ? { ...f, is_active: !f.is_active, packet_count: action === 'deactivate' ? 0 : f.packet_count }
        : f
    ));
  };
  
  const deleteFilter = async (filterId) => {
    if (!confirm('Delete this filter?')) return;
    
    await fetch(`/api/traffic-filters/filters/${filterId}`, { method: 'DELETE' });
    setFilters(prev => prev.filter(f => f.id !== filterId));
  };
  
  const categories = ['all', 'layer2', 'routing', 'overlay', 'transport', 'vlan', 'multicast', 'custom'];
  
  const filteredFilters = selectedCategory === 'all'
    ? filters
    : filters.filter(f => f.category === selectedCategory);
  
  return (
    <div className="traffic-filter-panel">
      <header className="panel-header">
        <h3>Traffic Filters</h3>
        <button onClick={() => setIsEditorOpen(true)} className="btn-add">
          <FaPlus /> New Filter
        </button>
      </header>
      
      <div className="category-tabs">
        {categories.map(cat => (
          <button
            key={cat}
            className={selectedCategory === cat ? 'active' : ''}
            onClick={() => setSelectedCategory(cat)}
          >
            {cat.charAt(0).toUpperCase() + cat.slice(1)}
          </button>
        ))}
      </div>
      
      <div className="filter-list">
        {filteredFilters.map(filter => (
          <div key={filter.id} className="filter-item">
            <div className="filter-color" style={{ backgroundColor: filter.color }} />
            
            <div className="filter-info">
              <div className="filter-name">{filter.name}</div>
              <div className="filter-description">{filter.description}</div>
              <div className="filter-syntax">{filter.filter}</div>
            </div>
            
            <div className="filter-counter">
              {filter.is_active && (
                <span className="packet-count">{filter.packet_count}</span>
              )}
            </div>
            
            <div className="filter-actions">
              <button
                onClick={() => toggleFilter(filter)}
                className={filter.is_active ? 'btn-pause' : 'btn-play'}
                title={filter.is_active ? 'Stop capture' : 'Start capture'}
              >
                {filter.is_active ? <FaPause /> : <FaPlay />}
              </button>
              
              {!filter.is_builtin && (
                <>
                  <button
                    onClick={() => {
                      setEditingFilter(filter);
                      setIsEditorOpen(true);
                    }}
                    className="btn-edit"
                    title="Edit filter"
                  >
                    <FaEdit />
                  </button>
                  
                  <button
                    onClick={() => deleteFilter(filter.id)}
                    className="btn-delete"
                    title="Delete filter"
                  >
                    <FaTrash />
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
      
      {isEditorOpen && (
        <FilterEditor
          filter={editingFilter}
          onClose={() => {
            setIsEditorOpen(false);
            setEditingFilter(null);
            fetchFilters();
          }}
        />
      )}
    </div>
  );
}
```

### FilterEditor Component

```jsx
// frontend/src/components/FilterEditor.jsx

import React, { useState, useEffect } from 'react';
import { FaTimes, FaCheck } from 'react-icons/fa';
import { ChromePicker } from 'react-color';
import './FilterEditor.css';

export default function FilterEditor({ filter, onClose }) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    filter: '',
    color: '#00FF00',
    category: 'custom',
    animation_duration: 3000
  });
  
  const [isValidating, setIsValidating] = useState(false);
  const [validationError, setValidationError] = useState(null);
  const [showColorPicker, setShowColorPicker] = useState(false);
  
  useEffect(() => {
    if (filter) {
      setFormData(filter);
    }
  }, [filter]);
  
  const validateFilter = async () => {
    setIsValidating(true);
    setValidationError(null);
    
    try {
      const response = await fetch('/api/traffic-filters/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filter: formData.filter })
      });
      
      const result = await response.json();
      
      if (!result.valid) {
        setValidationError(result.error);
        return false;
      }
      
      return true;
    } catch (error) {
      setValidationError('Validation failed');
      return false;
    } finally {
      setIsValidating(false);
    }
  };
  
  const handleSave = async () => {
    // Validate BPF syntax
    const isValid = await validateFilter();
    if (!isValid) return;
    
    const method = filter ? 'PATCH' : 'POST';
    const url = filter
      ? `/api/traffic-filters/filters/${filter.id}`
      : '/api/traffic-filters/filters';
    
    await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    });
    
    onClose();
  };
  
  const commonFilters = [
    { label: 'ARP', value: 'arp' },
    { label: 'OSPF', value: 'proto 89' },
    { label: 'BGP', value: 'tcp port 179' },
    { label: 'ICMP', value: 'icmp' },
    { label: 'VXLAN', value: 'udp port 4789' },
    { label: 'LLDP', value: 'ether proto 0x88cc' }
  ];
  
  return (
    <div className="filter-editor-overlay">
      <div className="filter-editor">
        <header className="editor-header">
          <h3>{filter ? 'Edit Filter' : 'New Filter'}</h3>
          <button onClick={onClose} className="btn-close">
            <FaTimes />
          </button>
        </header>
        
        <div className="editor-body">
          <div className="form-group">
            <label>Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., OSPF Hellos"
            />
          </div>
          
          <div className="form-group">
            <label>Description</label>
            <input
              type="text"
              value={formData.description}
              onChange={e => setFormData({ ...formData, description: e.target.value })}
              placeholder="What does this filter capture?"
            />
          </div>
          
          <div className="form-group">
            <label>
              tcpdump Filter (BPF Syntax)
              <button onClick={validateFilter} className="btn-validate">
                {isValidating ? 'Validating...' : 'Validate'}
              </button>
            </label>
            <textarea
              value={formData.filter}
              onChange={e => setFormData({ ...formData, filter: e.target.value })}
              placeholder="e.g., proto 89 or tcp port 179"
              rows="3"
            />
            {validationError && (
              <div className="validation-error">{validationError}</div>
            )}
            
            <div className="filter-shortcuts">
              <span>Quick filters:</span>
              {commonFilters.map(cf => (
                <button
                  key={cf.label}
                  onClick={() => setFormData({ ...formData, filter: cf.value })}
                  className="btn-shortcut"
                >
                  {cf.label}
                </button>
              ))}
            </div>
          </div>
          
          <div className="form-group">
            <label>Category</label>
            <select
              value={formData.category}
              onChange={e => setFormData({ ...formData, category: e.target.value })}
            >
              <option value="layer2">Layer 2</option>
              <option value="routing">Routing</option>
              <option value="overlay">Overlay/Tunneling</option>
              <option value="transport">Transport/Application</option>
              <option value="vlan">VLAN</option>
              <option value="multicast">Multicast</option>
              <option value="custom">Custom</option>
            </select>
          </div>
          
          <div className="form-group-row">
            <div className="form-group">
              <label>Color</label>
              <div
                className="color-preview"
                style={{ backgroundColor: formData.color }}
                onClick={() => setShowColorPicker(!showColorPicker)}
              />
              {showColorPicker && (
                <div className="color-picker-popover">
                  <ChromePicker
                    color={formData.color}
                    onChange={color => setFormData({ ...formData, color: color.hex })}
                  />
                </div>
              )}
            </div>
            
            <div className="form-group">
              <label>Animation Duration (ms)</label>
              <input
                type="number"
                value={formData.animation_duration}
                onChange={e => setFormData({ ...formData, animation_duration: parseInt(e.target.value) })}
                min="500"
                max="10000"
                step="500"
              />
            </div>
          </div>
        </div>
        
        <footer className="editor-footer">
          <button onClick={onClose} className="btn-cancel">
            Cancel
          </button>
          <button onClick={handleSave} className="btn-save">
            <FaCheck /> Save Filter
          </button>
        </footer>
      </div>
    </div>
  );
}
```

### LinkAnimationEngine

```jsx
// frontend/src/components/LinkAnimationEngine.jsx

import { useEffect, useRef } from 'react';

export default function LinkAnimationEngine({ links, setLinks }) {
  const animationTimers = useRef({});
  
  useEffect(() => {
    // Listen for traffic match events
    const handleTrafficMatch = (event) => {
      const { filter_id, link_id, color, duration = 3000 } = event.detail;
      
      // Update link to show animation
      setLinks(prev => prev.map(link =>
        link.id === link_id
          ? {
              ...link,
              animation: {
                active: true,
                color,
                startTime: Date.now(),
                duration
              }
            }
          : link
      ));
      
      // Clear previous timer for this link
      if (animationTimers.current[link_id]) {
        clearTimeout(animationTimers.current[link_id]);
      }
      
      // Set timer to clear animation after duration
      animationTimers.current[link_id] = setTimeout(() => {
        setLinks(prev => prev.map(link =>
          link.id === link_id
            ? { ...link, animation: null }
            : link
        ));
      }, duration);
    };
    
    window.addEventListener('traffic-match', handleTrafficMatch);
    
    return () => {
      window.removeEventListener('traffic-match', handleTrafficMatch);
      
      // Clear all timers
      Object.values(animationTimers.current).forEach(timer => clearTimeout(timer));
    };
  }, [setLinks]);
  
  return null; // This is a logic-only component
}

// Modify Link component to support animation
// frontend/src/components/Link.jsx (additions)

export function Link({ link, source, target }) {
  const pathRef = useRef();
  const animationRef = useRef();
  
  useEffect(() => {
    if (link.animation?.active && pathRef.current) {
      animateTraffic(pathRef.current, link.animation);
    }
  }, [link.animation]);
  
  const animateTraffic = (path, animation) => {
    const { color, duration } = animation;
    
    // Create animated dot using SVG <circle> + <animateMotion>
    const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    dot.setAttribute('r', '5');
    dot.setAttribute('fill', color);
    dot.setAttribute('opacity', '0.8');
    
    const motion = document.createElementNS('http://www.w3.org/2000/svg', 'animateMotion');
    motion.setAttribute('dur', `${duration / 1000}s`);
    motion.setAttribute('repeatCount', 'indefinite');
    
    const motionPath = document.createElementNS('http://www.w3.org/2000/svg', 'mpath');
    motionPath.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', `#${path.id}`);
    
    motion.appendChild(motionPath);
    dot.appendChild(motion);
    
    path.parentElement.appendChild(dot);
    
    // Clean up after duration
    setTimeout(() => {
      dot.remove();
    }, duration);
  };
  
  // Add glow effect when active
  const linkStyle = link.animation?.active
    ? {
        stroke: link.animation.color,
        strokeWidth: link.strokeWidth + 2,
        filter: 'drop-shadow(0 0 8px currentColor)'
      }
    : {
        stroke: link.color,
        strokeWidth: link.strokeWidth
      };
  
  return (
    <path
      ref={pathRef}
      id={`link-${link.id}`}
      d={calculatePath(source, target, link.pathType)}
      style={linkStyle}
      className="topology-link"
    />
  );
}
```

---

## Part 6: Phased Implementation Plan

### Phase 1: Foundation (Week 1-2) 🏗️

**Database:**
- [x] Create `traffic_filters` table
- [x] Create `filter_templates` table
- [x] Create `capture_sessions` table
- [x] Add indexes
- [x] Write migration script

**Backend:**
- [ ] Basic CRUD API for filters
- [ ] Filter validation endpoint (BPF syntax check)
- [ ] Seed built-in filter library (33 filters)

**Frontend:**
- [ ] TrafficFilterPanel component (list view)
- [ ] Filter toggle (UI only, no capture yet)
- [ ] Category tabs

**Deliverable:** Filter library management UI (no actual capture)

---

### Phase 2: Packet Capture Engine (Week 3-4) ⚙️

**Backend:**
- [ ] PacketCaptureEngine class
- [ ] tcpdump process management
- [ ] Output parsing (extract src/dst IPs)
- [ ] Link identification logic
- [ ] WebSocket server for events

**Testing:**
- [ ] Single filter, single device
- [ ] Multiple filters simultaneously
- [ ] Graceful shutdown (kill processes)

**Deliverable:** Working packet capture + packet counting

---

### Phase 3: Animation & Visualization (Week 5-6) 🎨

**Frontend:**
- [ ] LinkAnimationEngine component
- [ ] SVG animation (moving dots on links)
- [ ] Link glow effect when active
- [ ] Real-time packet counter updates

**Integration:**
- [ ] WebSocket connection
- [ ] Event handling (traffic_match)
- [ ] Animation timing (configurable duration)

**Deliverable:** Live animated traffic flows

---

### Phase 4: Advanced Features (Week 7-8) 🚀

**Backend:**
- [ ] Filter templates CRUD
- [ ] Template application (activate multiple)
- [ ] Performance optimization (batching, caching)
- [ ] Analytics (filter_matches history)

**Frontend:**
- [ ] FilterEditor visual builder (drag-drop?)
- [ ] Template management UI
- [ ] Filter search/sorting
- [ ] Keyboard shortcuts (space to toggle, etc.)

**Deliverable:** Production-ready feature

---

### Phase 5: Polish & Optimization (Week 9-10) ✨

**Performance:**
- [ ] Optimize tcpdump for large topologies
- [ ] Reduce WebSocket message frequency (throttling)
- [ ] Canvas-based animation (if SVG lags)

**UX:**
- [ ] Onboarding tour ("Click OSPF to see routing updates")
- [ ] Filter recommendations ("You're using VXLAN devices - try the VXLAN filter!")
- [ ] Filter analytics dashboard

**Testing:**
- [ ] Stress test: 50 devices, 10 filters
- [ ] Memory leak testing
- [ ] Browser compatibility

**Documentation:**
- [ ] User guide with screenshots
- [ ] Video demo (like Netzwerkonkel's)
- [ ] API documentation

**Deliverable:** Polished, documented, battle-tested feature

---

## Part 7: How We Beat EVE-NG

### Category: UX/UI 🎯

**1. Visual Filter Builder**
EVE-NG: Text-only BPF syntax entry
OmniLab: Drag-drop visual builder + text mode
- "Show me traffic FROM device A TO device B using PROTOCOL X"
- Translates to BPF automatically

**2. Smart Recommendations**
EVE-NG: Static filter list
OmniLab: Context-aware suggestions
- Lab has VXLAN? Suggest "VXLAN Tenant 1" filter
- Devices running OSPF? Highlight OSPF filter

**3. Filter Templates**
EVE-NG: No templates
OmniLab: Save/share filter collections
- "JNCIE-DC Standard" = OSPF + BGP + VXLAN + LLDP
- Community templates (import/export JSON)

**4. Keyboard Shortcuts**
EVE-NG: Mouse-only
OmniLab: Power user shortcuts
- Space: Toggle selected filter
- 1-9: Quick-activate filters 1-9
- Shift+A: Activate all
- Esc: Deactivate all

### Category: Performance 🚀

**1. Efficient Packet Processing**
EVE-NG: Unknown implementation
OmniLab: Batched updates
- Group WebSocket events (100ms window)
- Canvas rendering for 100+ concurrent animations

**2. Smart Link Detection**
EVE-NG: Unknown
OmniLab: IP-to-link mapping cache
- Pre-compute device interface IPs
- Hash-based lookup (O(1) instead of query-per-packet)

**3. Resource Management**
EVE-NG: Unknown
OmniLab: Intelligent capture scope
- Only capture on "visible" links (viewport optimization)
- Auto-pause when user navigates away
- Configurable buffer sizes

### Category: Features 🌟

**1. Packet History**
EVE-NG: Real-time only
OmniLab: Capture history
- Timeline: "Show me BGP traffic from last 5 minutes"
- Replay mode: Animate past captures
- Export to PCAP for Wireshark analysis

**2. Filter Analytics**
EVE-NG: Basic counters
OmniLab: Rich statistics
- Top talkers per filter
- Traffic patterns (hourly heatmap)
- Alert thresholds ("Notify me if BGP > 1000 pps")

**3. Collaborative Filters**
EVE-NG: Local only
OmniLab: Share with team
- Public filter library (community-contributed)
- Team workspaces (shared templates)
- Filter comments/documentation

**4. Link Capacity Visualization**
EVE-NG: Traffic yes/no
OmniLab: Traffic intensity
- Link thickness based on packet rate
- Color gradient (green→yellow→red)
- Bandwidth utilization %

**5. Multi-Lab Comparison**
EVE-NG: Single lab
OmniLab: Compare topologies
- Run same filter on Lab A vs Lab B
- Diff view ("Lab A has OSPF traffic but Lab B doesn't - why?")

---

## Part 8: Success Metrics

### Launch Criteria ✅

- [ ] 30+ built-in filters across 6 categories
- [ ] Sub-100ms latency from packet match → animation
- [ ] Supports 5+ simultaneous filters without lag
- [ ] Works on lab with 50 devices + 100 links
- [ ] Zero crashes after 1-hour stress test
- [ ] User can create custom filter in <30 seconds
- [ ] Documentation with 5+ video examples

### Post-Launch Metrics 📊

- **Adoption:** % of users who activate ≥1 filter per session
- **Engagement:** Average # filters used per lab
- **Custom Filters:** # of user-created filters
- **Performance:** 95th percentile animation latency
- **Feedback:** User rating (1-5 stars)

---

## Part 9: Risk Mitigation

### Risk 1: tcpdump Performance on Large Labs
**Mitigation:**
- Lightweight mode: Count-only (no full packet capture)
- Interface selection: User chooses which links to monitor
- Sampling: Capture 1 in every N packets (configurable)

### Risk 2: WebSocket Message Flood
**Mitigation:**
- Throttling: Max 10 events/sec per filter
- Batching: Group events in 100ms windows
- Client-side rate limiting

### Risk 3: Docker Exec Overhead
**Mitigation:**
- Use netns for direct interface access (bypass Docker)
- Host-level capture with VLAN tags (map to devices)
- Investigate eBPF for kernel-level filtering

### Risk 4: Link Identification Ambiguity
**Problem:** tcpdump shows IPs, but links connect devices (not IPs)
**Mitigation:**
- Maintain IP→Device mapping (refresh on topology change)
- User can manually label links ("This is the BGP peering link")
- Fallback: Show all matching links (highlight multiple)

---

## Part 10: Next Steps

### Immediate (This Week):
1. **Create database schema** (migration SQL)
2. **Seed built-in filter library** (INSERT statements)
3. **Stub out API endpoints** (routes skeleton)
4. **Design TrafficFilterPanel CSS** (match OmniLab theme)

### Week 2:
5. **Implement BPF validator**
6. **Build CRUD frontend**
7. **Test filter creation flow**

### Week 3:
8. **Start PacketCaptureEngine**
9. **Test tcpdump integration on Docker devices**

---

## Part 11: Open Questions

1. **Device Access:** How do we exec into libvirt/KVM devices?
   - SSH keys pre-installed?
   - qemu-guest-agent?
   
2. **Interface Discovery:** How to list interfaces per device?
   - Docker: `docker exec device ip link`
   - Libvirt: virsh domiflist?
   
3. **IP Mapping:** Where do we store device interface IPs?
   - New table: `device_interfaces` (device_id, interface, ip, netmask)?
   - Auto-discover via ARP/LLDP?
   
4. **Performance Target:** What's acceptable latency?
   - EVE-NG appears to be <1 sec
   - Should we aim for <500ms?

---

## Appendix A: Complete Database Migration

```sql
-- migration_008_traffic_filters.sql

BEGIN TRANSACTION;

-- Main filter table
CREATE TABLE IF NOT EXISTS traffic_filters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    tcpdump_filter TEXT NOT NULL,
    color TEXT NOT NULL DEFAULT '#00ff00',
    category TEXT NOT NULL DEFAULT 'custom',
    is_builtin BOOLEAN DEFAULT 0,
    is_active BOOLEAN DEFAULT 0,
    packet_count INTEGER DEFAULT 0,
    animation_duration INTEGER DEFAULT 3000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name)
);

-- Templates
CREATE TABLE IF NOT EXISTS filter_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    filters JSON NOT NULL,
    is_public BOOLEAN DEFAULT 0,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name)
);

-- Active capture sessions
CREATE TABLE IF NOT EXISTS capture_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filter_id INTEGER NOT NULL,
    device_id INTEGER NOT NULL,
    interface TEXT NOT NULL,
    pid INTEGER,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_packet_at TIMESTAMP,
    FOREIGN KEY (filter_id) REFERENCES traffic_filters(id) ON DELETE CASCADE,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- Match history (optional)
CREATE TABLE IF NOT EXISTS filter_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filter_id INTEGER NOT NULL,
    link_id INTEGER,
    lab_id INTEGER NOT NULL,
    matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    packet_summary TEXT,
    FOREIGN KEY (filter_id) REFERENCES traffic_filters(id) ON DELETE CASCADE,
    FOREIGN KEY (link_id) REFERENCES links(id) ON DELETE CASCADE,
    FOREIGN KEY (lab_id) REFERENCES labs(id) ON DELETE CASCADE
);

-- Device interfaces (NEW - for IP mapping)
CREATE TABLE IF NOT EXISTS device_interfaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    interface_name TEXT NOT NULL,
    ip_address TEXT,
    netmask TEXT,
    is_up BOOLEAN DEFAULT 1,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    UNIQUE(device_id, interface_name)
);

-- Indexes
CREATE INDEX idx_filters_active ON traffic_filters(is_active);
CREATE INDEX idx_filters_category ON traffic_filters(category);
CREATE INDEX idx_sessions_filter ON capture_sessions(filter_id);
CREATE INDEX idx_sessions_device ON capture_sessions(device_id);
CREATE INDEX idx_matches_filter_time ON filter_matches(filter_id, matched_at);
CREATE INDEX idx_interfaces_device ON device_interfaces(device_id);
CREATE INDEX idx_interfaces_ip ON device_interfaces(ip_address);

-- Extend links table
ALTER TABLE links ADD COLUMN animation_state TEXT;
ALTER TABLE links ADD COLUMN last_traffic_at TIMESTAMP;

COMMIT;
```

---

## Appendix B: Built-in Filter Seed Data

(See Part 3 for the full 33-filter JSON - convert to INSERT statements)

---

**END OF MASTER PLAN**

This is our roadmap to build the ULTIMATE traffic visualization feature. It's ambitious, but completely achievable in 10 weeks with focused execution.

Ready to start implementation, Kit? 🚀
