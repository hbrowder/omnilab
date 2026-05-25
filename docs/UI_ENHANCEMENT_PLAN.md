# OmniLab UI Enhancement - Linear Issues Created
**Date:** 2026-05-25  
**Request:** Option D - Comprehensive fix for topology canvas + additional features  

---

## Issues Created

| Issue | Title | Priority | Effort |
|-------|-------|----------|--------|
| **CRE-64** | Topology: Visual Container Boxes (Dashed Grouping Rectangles) | 🔥 CRITICAL | 3-4 hours |
| **CRE-65** | Topology: Network Objects Visible on Canvas (LAGs, Clouds, Bridges) | 🔥 CRITICAL | 2-3 hours |
| **CRE-66** | Topology: Interface Labels on Connection Lines | 🔥 CRITICAL | 1-2 hours |
| **CRE-67** | UX: Replace Browser prompt() with In-Canvas Modals | 🔴 HIGH | 2 hours |
| **CRE-68** | Feature: Real-Time Traffic Filter & Protocol Visualization | 🟡 HIGH | 8-12 hours (needs Harold's input) |
| **CRE-69** | UI: Enhanced Left Sidebar (Better than EVE-NG) | 🟡 MEDIUM | 4-6 hours |
| **CRE-70** | Topology: Layout Tools (Snap-to-Grid, Align, Distribute) | 🟢 MEDIUM | 2-3 hours |

**Total Estimated Effort:** 22-32 hours (excluding CRE-68 pending details)

---

## Issue Details

### CRE-64: Visual Container Boxes 🔥
**The Big One** - Harold's dual-datacenter topology uses dashed boxes to group "Alpharetta DC1", "Norcross DC2", "Primary", "Secondary". Without this, complex topologies look flat and unreadable.

**Features:**
- Dashed-border rectangles with labels
- Drag-to-resize (8 handles)
- Custom fill colors with opacity
- Double-click label to edit
- Z-order management (behind nodes)

**Code Ready:** Sample implementation in comparison doc

**Impact:** HIGHEST - this is what Harold noticed most when comparing

---

### CRE-65: Network Objects on Canvas 🔥
**Second Critical** - EVE-NG shows "LAG 265", "Keepalive", "mgmt-01" as small cloud/bridge icons. OmniLab has the data but doesn't render them.

**Features:**
- Cloud/bridge/LAG icons with labels
- Draggable like nodes
- Connect nodes to networks (multi-point)
- Color-coded by type (bridge/NAT/internal/LAG)

**Code Ready:** `NET_DEFS` already exists in LabCanvas.jsx, just needs rendering

**Impact:** HIGH - essential for showing network topology structure

---

### CRE-66: Interface Labels on Links 🔥
**Quick Win** - Network engineers NEED to see which port connects where (1/1/1, GigabitEthernet0/0, eth0).

**Features:**
- Text labels near each link endpoint
- Double-click to edit
- Show/hide toggle for dense topologies
- Auto-position to avoid node overlap

**Code Ready:** Link data already has srcIface/dstIface, just needs rendering

**Impact:** HIGH - critical for troubleshooting and documentation

**Effort:** LOWEST of the 3 critical (1-2 hours)

---

### CRE-67: Fix Browser Popup Modal 🔴
**Harold's Pain Point** - "I don't want anything popping up in the browser!"

**Current Bug:**
```jsx
const name = prompt('Lab name:')  // ← Opens OS dialog
```

**Fix:**
- Create reusable `<Modal>` component
- Styled in-canvas overlay
- Form for name + category dropdown
- ESC key / backdrop click to close

**Impact:** HIGH UX annoyance, quick fix (2 hours)

---

### CRE-68: Traffic Filter & Protocol Visualization 🟡
**Harold's New Feature Request** - "EVE-NG has traffic filters... visualize ARP, BGP, OSPF in real-time... we need something like that if not better!"

**Questions for Harold:**
1. Where in EVE-NG do you access this? (toolbar, menu, separate tab?)
2. What does it look like? (animated lines, color overlays, packet count bubbles?)
3. Live capture or replay?
4. Most critical protocols? (BGP, OSPF, ARP, ...?)
5. Do you see packet payloads or just flow visualization?

**Pending Harold's Answers:**
- Requires backend packet capture (CRE-57 already shipped)
- WebSocket for real-time updates
- Canvas animation layer
- Performance considerations (50+ nodes)

**Impact:** TBD - depends on Harold's usage

---

### CRE-69: Enhanced Left Sidebar 🟡
**Harold's Request:** "Clean left sidebar... but BETTER than EVE-NG"

**EVE-NG Sidebar:**
- Device library by vendor
- Drag onto canvas
- Collapsible sections

**OmniLab Enhancement Ideas:**
- Search/filter devices
- Pin favorites
- Recently used section
- Bulk add (select + quantity)
- Tag-based filtering (e.g., "BGP-capable")
- Keyboard shortcut (/ to search)
- Resizable width

**Impact:** MEDIUM - improves workflow speed but not blocking

---

### CRE-70: Layout Tools 🟢
**Professional Polish** - Snap-to-grid, align, distribute nodes

**Features:**
- Snap-to-grid toggle (configurable grid size)
- Right-click → Align (left/right/top/bottom/center)
- Right-click → Distribute (horizontal/vertical)
- Arrow keys nudge nodes (10px or grid size)
- Shift+Arrow = large nudge (50px)

**Impact:** MEDIUM - nice-to-have for clean layouts, not blocking

---

## Recommended Implementation Order

### Phase 1: Critical UX Fixes (6-9 hours)
1. **CRE-66:** Interface labels (1-2h) - quickest win
2. **CRE-67:** Fix modal popups (2h) - Harold's immediate pain
3. **CRE-64:** Container boxes (3-4h) - biggest visual impact
4. **CRE-65:** Network objects (2-3h) - completes topology visualization

**Result:** Harold can recreate his dual-datacenter topology with proper visual hierarchy

### Phase 2: Enhanced Workflow (6-8 hours)
5. **CRE-69:** Left sidebar (4-6h) - better device library
6. **CRE-70:** Layout tools (2-3h) - snap-to-grid, align, distribute

**Result:** Faster lab creation workflow, professional layouts

### Phase 3: Advanced Features (8-12+ hours)
7. **CRE-68:** Traffic visualization (pending Harold's specs)

**Result:** Real-time protocol monitoring and visualization

---

## Next Steps

**Immediate:**
1. Get Harold's traffic filter details (CRE-68)
2. Start implementation on Phase 1 (CRE-66, CRE-67, CRE-64, CRE-65)
3. Update Linear issues to "In Progress" as work begins

**Questions for Harold:**
- Do you want all of Phase 1 done before review, or iterate one-by-one?
- Any other EVE-NG features we missed?
- Traffic filter: Can you show me where it is in your EVE-NG or describe how you use it?

---

## Code Structure Plan

### New Files:
```
frontend/src/components/
  Modal.jsx                    # CRE-67: Reusable modal
  TopologyToolbar.jsx          # CRE-70: Snap-to-grid, layout tools
  DeviceSidebar.jsx            # CRE-69: Enhanced left sidebar
  TrafficVisualization.jsx     # CRE-68: Protocol overlay (future)

frontend/src/pages/LabCanvas.jsx (major updates)
  - Add containers state & rendering (CRE-64)
  - Render network objects (CRE-65)
  - Show interface labels on links (CRE-66)
  - Align/distribute functions (CRE-70)
```

### State Additions:
```jsx
const [containers, setContainers] = useState([])  // CRE-64
const [snapToGrid, setSnapToGrid] = useState(false)  // CRE-70
const [showInterfaceLabels, setShowInterfaceLabels] = useState(true)  // CRE-66
const [trafficFilters, setTrafficFilters] = useState({})  // CRE-68
```

---

**End of Implementation Plan**
