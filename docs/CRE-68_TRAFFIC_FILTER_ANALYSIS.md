# CRE-68: Traffic Filter Feature Analysis
**Date:** 2026-05-26  
**Source:** EVE-NG Cisco VXLAN EVPN Lab Analysis

## Overview
Traffic filters are packet visualization overlays that highlight specific protocols/traffic types on lab links in real-time using color-coded visual indicators.

## EVE-NG Implementation

### Data Structure (from .unl XML)
```xml
<filters>
  <filter 
    id="3ed240ca-7350-43f5-b80f-2469d56f4aa6" 
    enabled="1" 
    expr="proto 89" 
    color="#00ff00" 
    title="OSPF&#9;proto 89" 
    timeout="5000"/>
  <filter 
    id="c793e326-fc96-476f-b0a6-e5cc4a159488" 
    enabled="1" 
    expr="udp port 4789" 
    color="#800000" 
    title="VXLAN (UDP 4789)&#9;udp port 4789" 
    timeout="5000"/>
  <filter 
    id="52222ac2-6a6a-4b47-bdf1-dd206157c475" 
    enabled="1" 
    expr="vlan" 
    color="#0080ff" 
    title="VLAN (802.1Q)" 
    timeout="5000"/>
  <filter 
    id="77d8a3da-ab7c-4a17-ae51-99155d8451dd" 
    enabled="1" 
    expr="udp port 4789 and arp" 
    color="#ff0000" 
    title="VXLAN ARP Suppression" 
    timeout="5000"/>
  <filter 
    id="bc85e2dd-d523-4cf7-afb5-4de1d0f62dad" 
    enabled="1" 
    expr="udp port 3784" 
    color="#8000ff" 
    title="VXLAN BFD over VTEP" 
    timeout="5000"/>
  <filter 
    id="c4de4a44-4fb6-4d96-a84c-5cb62bfd2abd" 
    enabled="1" 
    expr="arp" 
    color="#ff8000" 
    title="ARP" 
    timeout="5000"/>
  <filter 
    id="9b95c335-9128-4ab9-9d39-2f58dc3ff2f5" 
    enabled="1" 
    expr="tcp port 179" 
    color="#ff0000" 
    title="BGP" 
    timeout="5000"/>
  <filter 
    id="c2c4cb1d-e2e0-4f04-bf72-b32492ad8e4b" 
    enabled="1" 
    expr="icmp" 
    color="#00ffff" 
    title="ICMP" 
    timeout="5000"/>
  <filter 
    id="0d047e20-4d04-45c0-99fa-c9a1d1fa32cb" 
    enabled="1" 
    expr="ip proto 89 and ip[24] != 1" 
    color="#0080ff" 
    title="OSPF LSAs" 
    timeout="5000"/>
</filters>
```

### API Endpoints (from EVE-NG JavaScript)
```javascript
// Get all filters for a lab
GET /api/labs/{path}/filter
Response: Array of filter objects

// Activate filters (start monitoring)
POST /api/labs/{path}/filter/activate
Response: activation status

// Add new filter
POST /api/labs/{path}/filter
Body: { expr, color, title, timeout, enabled }

// Edit filter
PUT /api/labs/{path}/filter/{id}
Body: { expr, color, title, timeout, enabled }

// Delete filter
DELETE /api/labs/{path}/filter/{id}
```

### Filter Properties
- **id**: UUID for the filter
- **enabled**: 1 (active) or 0 (disabled)
- **expr**: BPF (Berkeley Packet Filter) expression
  - Examples: `proto 89`, `udp port 4789`, `tcp port 179`, `icmp`
  - Complex: `udp port 4789 and arp`, `ip proto 89 and ip[24] != 1`
- **color**: Hex color code for visual overlay (e.g., `#00ff00`, `#ff0000`)
- **title**: Human-readable name shown in UI
- **timeout**: Duration in ms to show visual indicator after packet match (default: 5000ms)

### Network-Level Filters (L2 Protocol Filtering)
Networks also have filter attributes:
```xml
<network ... 
  l2filter_lldp="0" 
  l2filter_stp="0" 
  l2filter_cisco="0" 
  l2filter_lacp="0"/>
```

These suppress specific Layer 2 protocols from being forwarded.

## How It Works

### 1. Backend Packet Capture
- EVE-NG captures packets on bridge interfaces (virtual networks)
- Applies BPF filters to match specific traffic types
- Sends match events to frontend via WebSocket/polling

### 2. Visual Overlay
When a packet matches a filter:
1. Link between nodes flashes or pulses in the filter's color
2. Effect duration = `timeout` value (5 seconds default)
3. Multiple matches can overlap (multiple colors)

### 3. Purpose
Educational visualization for networking labs:
- See OSPF hellos propagating (green flash)
- Watch BGP sessions establish (red flash on TCP 179)
- Visualize VXLAN encapsulation (maroon flash on UDP 4789)
- Identify ARP traffic (orange flash)
- Monitor ICMP pings (cyan flash)

## Harold's Feedback: "Wonky Sometimes"

Likely issues with EVE-NG implementation:
1. **Performance**: High packet rates can overwhelm the capture → missed/delayed flashes
2. **Timing**: 5-second timeout may be too long or too short depending on use case
3. **Overlap**: Multiple filters on same link create visual confusion
4. **False Positives**: BPF expressions may match unintended traffic
5. **No Visual Feedback**: Hard to tell if filter is active or if traffic just isn't matching

## OmniLab Enhancement Strategy

### Make It "A Lot More Functional"

#### 1. **Enhanced Visual Indicators**
- **Animated Dots**: Small colored dots flow along the link path (direction-aware)
- **Intensity Scaling**: More packets = brighter/faster animation
- **Count Badges**: Show packet count per filter per link
- **Timeline**: Bottom panel showing filter matches over time (like Chrome DevTools Network)

#### 2. **Better UX**
- **Filter Library**: Preset common filters (OSPF, BGP, ICMP, DNS, HTTP, VXLAN)
- **Quick Toggle**: Enable/disable filters without editing
- **Visual Feedback**: Active filters shown in sidebar with match counts
- **Hover Details**: Hover link to see which protocols matched in last N seconds

#### 3. **Advanced Features**
- **Directional Filters**: Show traffic direction (A→B vs B→A)
- **Regex Support**: More powerful than BPF for complex matching
- **Export**: Save matched packets to PCAP
- **Alerts**: Notify when specific filter triggers (e.g., "BGP session established")
- **Statistics**: Show bandwidth per protocol, packet rates, etc.

#### 4. **Performance Improvements**
- **Client-Side Filtering**: Stream raw packet metadata, filter in browser
- **Sampling**: For high-rate traffic, sample 1 in N packets
- **Buffering**: Smooth out visual updates to avoid flicker
- **GPU Acceleration**: Use Canvas/WebGL for smooth 60fps animations

#### 5. **Integration with Packet Capture**
- Link to CRE-56 (NAT) and CRE-57 (packet capture)
- Click animated link → open capture view filtered to that protocol
- "Capture to file" button on filter → save matching packets to PCAP

## Implementation Plan (CRE-68)

### Phase 1: Data Model & API (Backend)
1. Add `filters` table to database
2. Implement CRUD endpoints matching EVE-NG API
3. BPF expression validation
4. Packet capture integration (libpcap/tshark)

### Phase 2: Basic Visualization (Frontend)
1. Filter management UI (add/edit/delete/toggle)
2. Simple link flash animation (SVG stroke animation)
3. Match counter badges
4. WebSocket or SSE for real-time updates

### Phase 3: Advanced Features
1. Animated flowing dots (SVG `<animate>` or canvas)
2. Filter library/presets
3. Timeline view (d3.js or similar)
4. Statistics panel

### Phase 4: Integration
1. Connect to packet capture system
2. Export to PCAP
3. Alert system
4. Direction-aware visualization

## Technical Notes

### BPF Expression Examples (Common Protocols)
```
OSPF:        proto 89
BGP:         tcp port 179
VXLAN:       udp port 4789
ICMP:        icmp
ARP:         arp
DNS:         udp port 53
HTTP:        tcp port 80
HTTPS:       tcp port 443
SSH:         tcp port 22
Telnet:      tcp port 23
EIGRP:       proto 88
RIP:         udp port 520
LACP:        ether proto 0x8809
LLDP:        ether proto 0x88cc
STP:         ether dst 01:80:c2:00:00:00
```

### Performance Considerations
- Capture at bridge level (Linux bridge interfaces)
- Use eBPF for in-kernel filtering (faster than userspace pcap)
- Batch updates: send match events every 100ms, not per-packet
- Limit history: keep only last 60 seconds of match data

## Verification Criteria
1. ✅ Filters stored in database
2. ✅ CRUD API endpoints functional
3. ✅ BPF expressions validated before save
4. ✅ Real-time visual feedback on link matches
5. ✅ No performance impact when filters disabled
6. ✅ Better UX than EVE-NG (clearer, smoother, more informative)
7. ✅ Integration with packet capture feature

## References
- EVE-NG lab file: `/opt/unetlab/labs/VXLAN/Cisco Spine-leaf Network Topology Cisco nx-os.unl`
- BPF syntax: https://biot.com/capstats/bpf.html
- libpcap documentation: https://www.tcpdump.org/manpages/pcap.3pcap.html
