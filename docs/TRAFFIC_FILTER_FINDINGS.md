# Traffic Filter Feature - EVE-NG Analysis
**Date:** 2026-05-26  
**Analyzed Lab:** Cisco Spine-leaf Network Topology (VXLAN EVPN)

## Executive Summary

Harold's VXLAN/EVPN lab has **10 active traffic filters** configured to visualize different protocol types in real-time on the topology canvas. This is an educational feature that helps understand what protocols are flowing between network devices.

## What We Found

### 1. Filter Configuration (Lab-Level Storage)

The traffic filters are stored in the `.unl` lab file in an XML `<filters>` section:

```xml
<filters>
  <filter id="UUID" enabled="1" expr="BPF" color="#HEX" title="NAME" timeout="5000"/>
  ...
</filters>
```

### 2. Harold's Active Filters

| Protocol | BPF Expression | Color | Purpose |
|----------|---------------|-------|---------|
| **OSPF** | `proto 89` | #00ff00 (green) | OSPF routing protocol |
| **VXLAN** | `udp port 4789` | #800000 (maroon) | VXLAN encapsulation |
| **VLAN** | `vlan` | #0080ff (blue) | 802.1Q VLAN tags |
| **VXLAN ARP Suppression** | `udp port 4789 and arp` | #ff0000 (red) | ARP in VXLAN tunnel |
| **VXLAN BFD** | `udp port 3784` | #8000ff (purple) | BFD over VTEP |
| **VXLAN ARP/MAC Learning** | `udp port 4789 and arp` | #808000 (olive) | MAC learning verification |
| **ARP** | `arp` | #ff8000 (orange) | ARP requests/replies |
| **BGP** | `tcp port 179` | #ff0000 (red) | BGP routing protocol |
| **ICMP** | `icmp` | #00ffff (cyan) | Ping/traceroute |
| **OSPF LSAs** | `ip proto 89 and ip[24] != 1` | #0080ff (blue) | OSPF link-state advertisements |

### 3. How It Works (EVE-NG Architecture)

**Backend (Packet Capture):**
1. EVE-NG runs packet capture on Linux bridge interfaces (virtual networks)
2. Uses BPF (Berkeley Packet Filter) expressions to match specific traffic
3. When a packet matches, sends event to frontend

**Frontend (Visual Overlay):**
1. Link between nodes flashes/pulses in the filter's color
2. Effect lasts for `timeout` milliseconds (5000ms = 5 seconds default)
3. Multiple filters can trigger simultaneously on same link

**Purpose:**
Educational visualization - see protocols in action:
- Watch OSPF hellos propagate between routers (green flash)
- See BGP sessions establish (red flash)
- Visualize VXLAN encapsulation tunneling traffic (maroon flash)
- Track ARP resolution (orange flash)
- Monitor ICMP pings (cyan flash)

### 4. API Endpoints (from EVE-NG JavaScript Analysis)

```javascript
// Get all filters for a lab
GET /api/labs/{path}/filter
→ Returns: array of filter objects

// Activate filters (start packet monitoring)
POST /api/labs/{path}/filter/activate
→ Starts capture threads, returns activation status

// Add new filter
POST /api/labs/{path}/filter
Body: { expr, color, title, timeout, enabled }

// Edit existing filter
PUT /api/labs/{path}/filter/{id}
Body: { expr, color, title, timeout, enabled }

// Delete filter
DELETE /api/labs/{path}/filter/{id}
```

### 5. Network-Level L2 Filters

Networks also have suppression filters for common L2 protocols:

```xml
<network ... 
  l2filter_lldp="0"   <!-- LLDP (neighbor discovery) -->
  l2filter_stp="0"    <!-- STP (spanning tree) -->
  l2filter_cisco="0"  <!-- CDP/VTP (Cisco discovery) -->
  l2filter_lacp="0"   <!-- LACP (link aggregation) -->
/>
```

These **suppress** (drop) specific L2 protocols from being forwarded through the bridge - useful for reducing noise in capture.

## Harold's Feedback: "Wonky Sometimes"

### Likely Issues with EVE-NG Implementation

1. **Performance Degradation**
   - High packet rates overwhelm capture
   - Missed or delayed flash animations
   - CPU spike during heavy traffic

2. **Visual Confusion**
   - 5-second timeout too long → overlapping flashes blur together
   - Multiple filters on same link → color confusion
   - No indication of filter activity when no traffic

3. **No Traffic Stats**
   - Can't see packet counts per filter
   - No history/timeline of when filters triggered
   - No way to know if filter is broken vs. no matching traffic

4. **Limited Feedback**
   - Hard to tell if filters are active
   - No "last seen" timestamp
   - Can't distinguish 1 packet vs 100 packets

## OmniLab Strategy: "Make Ours A Lot More Functional"

### Design Goals
1. **Clearer visual feedback** - don't just flash, show what's happening
2. **Better performance** - handle high packet rates smoothly
3. **More information** - show counts, rates, direction, history
4. **Easier to use** - preset filters, quick toggles, templates

### Enhanced Feature Set

#### 1. **Animated Traffic Indicators**
- **Flowing Dots:** Small colored circles that travel along link paths
  - Direction-aware: dot moves from source → destination
  - Speed proportional to packet rate
  - Color from filter
- **Intensity Scaling:** More packets = brighter/faster animation
- **Smooth 60fps:** GPU-accelerated canvas rendering

#### 2. **Real-Time Statistics**
- **Per-Filter Counters:** Badge on each filter showing match count
- **Per-Link Badges:** Hover link → tooltip shows:
  - Last 10 seconds: "23 OSPF, 5 BGP, 120 ICMP"
  - Active filters on this link
- **Live Timeline:** Bottom panel (like Chrome DevTools)
  - Horizontal timeline showing filter triggers over time
  - Click bar → jump to that moment, highlight link
  - Export section to PCAP

#### 3. **Filter Management UI**
- **Filter Library Sidebar:**
  - Preset common filters (OSPF, BGP, ICMP, DNS, HTTP, VXLAN)
  - Custom filters (BPF expression builder)
  - Quick enable/disable checkboxes
  - Color picker per filter
  - Timeout slider (100ms - 10s)
- **Filter Status Indicators:**
  - Green dot: active and matching traffic
  - Yellow dot: active but no recent matches
  - Red dot: filter error (invalid BPF)
  - Gray dot: disabled

#### 4. **Advanced Capabilities**
- **Directional Filters:** Show A→B separate from B→A
- **Regex Support:** More powerful than BPF for application-layer filtering
- **Packet Capture Integration:**
  - Click animated link → "Capture to PCAP"
  - Save matching packets to file
  - Open in Wireshark (if installed locally)
- **Alerts:**
  - "Notify me when BGP session establishes" (tcp port 179 SYN)
  - "Alert if OSPF adjacency drops" (no proto 89 for >30s)
- **Heatmap Mode:**
  - Color links by total traffic volume
  - Thicker lines = more bandwidth
  - Overlay filter matches on heatmap

#### 5. **Performance Optimizations**
- **eBPF In-Kernel Filtering:** Linux kernel does the work, not userspace
- **Batched Updates:** Send match events every 100ms, not per-packet
- **Client-Side Sampling:** For high-rate traffic, sample 1 in N packets
- **GPU Canvas Rendering:** Smooth animations even with 50+ active filters
- **60-Second Rolling Buffer:** Only keep last minute of match data

### Technical Implementation Notes

**Backend (Python/FastAPI):**
- Use `scapy` or `pyshark` for packet capture
- BPF expression validation before save
- WebSocket for real-time match events (not polling)
- Capture threads per network bridge

**Frontend (React):**
- SVG for links (scalable, flexible)
- Canvas overlay for animated dots (performance)
- D3.js for timeline visualization
- Zustand for filter state management

**Database Schema:**
```sql
CREATE TABLE filters (
  id UUID PRIMARY KEY,
  lab_id INTEGER REFERENCES labs(id),
  enabled BOOLEAN DEFAULT true,
  expr TEXT NOT NULL,  -- BPF expression
  color TEXT NOT NULL,  -- hex color
  title TEXT NOT NULL,
  timeout INTEGER DEFAULT 5000,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

CREATE TABLE filter_matches (
  id SERIAL PRIMARY KEY,
  filter_id UUID REFERENCES filters(id),
  link_id INTEGER,  -- which network/link matched
  direction TEXT,  -- 'A_to_B' or 'B_to_A'
  packet_count INTEGER,
  timestamp TIMESTAMP
);
```

## Implementation Priority

**Phase 1 (CRE-68 Foundation):** 2-3 hours
1. Database schema (filters table)
2. CRUD API endpoints (GET/POST/PUT/DELETE /api/labs/{id}/filters)
3. BPF expression validator
4. Basic filter management UI (add/edit/delete/toggle)

**Phase 2 (Visual Overlay):** 2-3 hours
1. Simple link flash animation (SVG stroke pulse)
2. WebSocket connection for real-time events
3. Match counter badges on links
4. Filter library sidebar (presets)

**Phase 3 (Advanced Features):** 4-6 hours
1. Animated flowing dots (canvas overlay)
2. Timeline view (D3.js)
3. Statistics panel
4. Packet capture integration (export to PCAP)

**Phase 4 (Polish):** 2-3 hours
1. Heatmap mode
2. Direction-aware visualization
3. Alert system
4. Performance tuning (eBPF, batching)

**Total Estimate:** 10-15 hours for complete feature

## BPF Expression Examples (Filter Library Presets)

```
# Common Routing Protocols
OSPF:        proto 89
BGP:         tcp port 179
EIGRP:       proto 88
RIP:         udp port 520

# Data Center / Overlay
VXLAN:       udp port 4789
GENEVE:      udp port 6081
GRE:         proto 47

# Discovery Protocols
LLDP:        ether proto 0x88cc
CDP:         ether dst 01:00:0c:cc:cc:cc
ARP:         arp

# Management
SSH:         tcp port 22
Telnet:      tcp port 23
SNMP:        udp port 161
Syslog:      udp port 514

# Diagnostics
ICMP:        icmp
ICMP Echo:   icmp[0] == 8
Traceroute:  udp and ip[8] == 1

# Application Layer
DNS:         udp port 53
HTTP:        tcp port 80
HTTPS:       tcp port 443
NTP:         udp port 123

# Layer 2
STP:         ether dst 01:80:c2:00:00:00
LACP:        ether proto 0x8809
VLAN:        vlan
```

## Verification Criteria (Definition of Done)

- [ ] Filters stored in database (not just XML)
- [ ] CRUD API endpoints functional and tested
- [ ] BPF expressions validated before save (invalid → error message)
- [ ] Filter UI: add/edit/delete/toggle working
- [ ] Real-time visual feedback on links when packets match
- [ ] Animated indicators (dots or flashes) smooth at 60fps
- [ ] Match counters visible (per-filter and per-link)
- [ ] Timeline view showing filter activity over time
- [ ] Export to PCAP functional
- [ ] No performance impact when filters disabled
- [ ] Works with 10+ concurrent filters without lag
- [ ] Better UX than EVE-NG (user feedback: "not wonky anymore")

## References
- EVE-NG lab: `/opt/unetlab/labs/VXLAN/Cisco Spine-leaf Network Topology Cisco nx-os.unl`
- BPF syntax: https://biot.com/capstats/bpf.html
- tcpdump expressions: https://www.tcpdump.org/manpages/pcap-filter.7.html
- eBPF for packet filtering: https://ebpf.io/
