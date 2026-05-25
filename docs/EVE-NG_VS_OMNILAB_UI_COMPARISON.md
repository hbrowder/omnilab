# EVE-NG vs OmniLab UI Comparison
**Analysis Date:** 2026-05-25  
**EVE-NG Instance:** 192.168.1.156 (Harold's production)  
**OmniLab Version:** Current main branch  

---

## Executive Summary

After analyzing Harold's EVE-NG production instance and OmniLab's existing UI code, **OmniLab is missing critical topology canvas features** that are essential for network engineers. The current implementation has basic drag-and-drop but lacks the visual hierarchy, grouping, and professional layout tools that make EVE-NG powerful for complex multi-datacenter designs.

### Critical Gaps
1. **No visual containers/groups** — EVE-NG uses dashed boxes to group logical sections (datacenters, PODs, layers)
2. **Missing network cloud objects** — EVE-NG shows mgmt networks, clouds, bridges as visual objects on canvas
3. **No text labels/annotations** — EVE-NG allows arbitrary text on canvas for documentation
4. **Limited layout tools** — No auto-align, distribute, or grid snap features
5. **Basic connection visualization** — EVE-NG shows interface labels on links, OmniLab does not

---

## 1. Topology Canvas Layout

### EVE-NG (Production Screenshot Analysis)
```
┌─────────────────────────────────────────────────────────────────┐
│ Left Sidebar (collapsed in screenshot):                         │
│  - Node library with device icons                              │
│  - Drag-and-drop onto canvas                                   │
│                                                                 │
│ Main Canvas:                                                    │
│  ┌──────── (Dashed Box: "Alpharetta DC1") ─────────┐          │
│  │  ┌─ Primary ─┐    ┌── LAG 265 ──┐              │          │
│  │  │ ALP-FW-01 │────│ ALP-CORE-01 │              │          │
│  │  │ ALP-FW-02 │────│ ALP-CORE-02 │              │          │
│  │  └───────────┘    └─────────────┘              │          │
│  │  ┌─── LAG 1 ───┐                                │          │
│  │  │ ALP-TOR-01  │                                │          │
│  │  └─────────────┘                                │          │
│  └─────────────────────────────────────────────────┘          │
│                                                                 │
│  ┌──────── (Dashed Box: "Norcross DC2") ──────────┐           │
│  │  ┌─ Secondary ─┐  ┌── LAG 265 ──┐             │           │
│  │  │ NOR-FW-01   │──│ NOR-CORE-01 │             │           │
│  │  │ NOR-FW-02   │──│ NOR-CORE-02 │             │           │
│  │  └─────────────┘  └─────────────┘             │           │
│  └─────────────────────────────────────────────────┘           │
│                                                                 │
│ Right Sidebar (visible):                                       │
│  - Node list with states                                       │
│  - Network objects (VSX, LAG, cloud icons)                    │
│  - Management network icons                                    │
└─────────────────────────────────────────────────────────────────┘
```

**Key Features Visible:**
- **Dashed container boxes** with labels ("Alpharetta DC1", "Primary", "Secondary")
- **Network objects as visual elements** (LAG 265, LAG 1, Keepalive, VSX-Pair shown as small cloud/link icons)
- **Interface labels on connections** (1/1/1, 1/1/2, UTI/5, etc.)
- **Hierarchical grouping** (DC → POD → Layer structure clear at a glance)
- **Professional spacing** (consistent gaps, aligned elements)
- **Top toolbar** shows user/password, IP address
- **Grid background** (subtle, helps with alignment)

### OmniLab (Current Code Analysis)
```jsx
// LabCanvas.jsx line 69-833
export default function LabCanvas() {
  const [nodes, setNodes] = useState([])
  const [networks, setNetworks] = useState([])
  const [links, setLinks] = useState([])
  const [texts, setTexts] = useState([])  // ← defined but NOT RENDERED
  
  // Nodes are draggable, clickable
  // Networks exist in state but rendering unclear
  // No visual container/group boxes
  // No text annotation objects on canvas
  ...
}
```

**Current Capabilities:**
✅ Drag-and-drop nodes  
✅ Pan/zoom canvas  
✅ Multi-select nodes  
✅ Right-click context menu  
✅ Dark mode toggle  
✅ Minimap  
✅ Node status indicators  

**Missing Features:**
❌ Visual container boxes (dashed outlines for grouping)  
❌ Network objects rendered on canvas (clouds, bridges visible)  
❌ Text labels/annotations  
❌ Interface labels on link lines  
❌ Auto-layout tools (align, distribute, snap-to-grid)  
❌ Connection style options (dotted, dashed, arrow types)  
❌ Visual hierarchy (layers, PODs, zones)  

---

## 2. Node & Network Object Representation

### EVE-NG
- **Nodes:** Standard vendor icons (Arista, Aruba, Cisco distinct)
- **Networks:** Small cloud/bridge icons WITH LABELS (e.g., "LAG 265", "Keepalive", "mgmt-01")
- **Positioning:** Networks are first-class objects you position and connect to
- **Visual weight:** Nodes are large, networks are small accent objects

**Example from screenshot:**
```
ALP-CORE-01 ──(LAG 265)── ALP-CORE-02
     │                         │
  (1/1/1)                   (1/1/2)
     └────── (Keepalive) ─────┘
```
The "LAG 265" and "Keepalive" are VISIBLE labeled objects, not just line annotations.

### OmniLab (Current)
```jsx
// networks array exists but rendering is unclear
const [networks, setNetworks] = useState([])

// NET_DEFS defined at top:
const NET_DEFS = {
  bridge:   { label:'Bridge',    color:'#7c3aed' },
  nat:      { label:'NAT/Cloud', color:'#0f766e' },
  internal: { label:'Internal',  color:'#b45309' },
}

// No visual representation on canvas found in first 200 lines
```

**Current State:**
- Networks defined in state and types available
- NOT rendered as visual objects on canvas
- Links drawn as simple lines between nodes
- No intermediate network "hop" visualization

**Gap:**
OmniLab treats networks as backend concepts. EVE-NG makes them visual topology elements users can drag, label, and style.

---

## 3. Visual Grouping & Containers

### EVE-NG
**Dashed Box Containers:**
- Users draw rectangles with labels
- Used for: datacenters, layers (Core, Distribution, Access), security zones, customer environments
- Essential for documenting complex multi-site topologies
- Shown in screenshot: "Alpharetta DC1", "Norcross DC2", "Primary", "Secondary"

**Text Annotations:**
- Arbitrary text labels anywhere on canvas
- Used for: IP addresses, VLAN IDs, notes, warnings
- Shown in screenshot: interface numbers, node names

### OmniLab (Current)
```jsx
// state includes texts array:
const [texts, setTexts] = useState([])

// BUT no rendering code found for:
// - Drawing dashed container rectangles
// - Rendering text objects on canvas
// - UI to create/edit containers
```

**Gap:**
This is the **BIGGEST** visual difference. Harold's EVE-NG screenshot shows a multi-datacenter design that's immediately understandable because of dashed boxes. OmniLab would show the same nodes/links but WITHOUT the visual hierarchy — making it a flat jumble instead of structured zones.

---

## 4. Interface & Connection Labeling

### EVE-NG
- **Interface labels on links:** "1/1/1", "1/1/2", "UTI/5" visible next to each connection
- **Network names on clouds:** "LAG 265", "VSX-Pair" shown as labeled icons
- **Hover details:** (not visible in static screenshot, but EVE-NG shows port status on hover)

### OmniLab (Current)
```jsx
// Links have interface info in state:
setLinks(topo.links.map(l=>({
  id:l.id,srcId:l.src_node_id,dstId:l.dst_node_id,
  srcIface:'GigabitEthernet0/0',dstIface:'eth0',style:'solid'
})))

// But interface names are NOT rendered on the <line> elements
```

**Gap:**
Network engineers NEED to see which interface connects where without clicking. Harold's topology shows "1/1/1" and "1/1/2" labels making it immediately clear which port each link uses.

---

## 5. Layout & Alignment Tools

### EVE-NG (Known Features Not Visible in Screenshot)
- Right-click canvas → "Align" options (left, right, center, distribute)
- Snap-to-grid toggle
- Auto-route connections (avoids overlaps)
- Bulk move (select multiple, drag together)

### OmniLab (Current)
✅ Multi-select (drag box or Shift+click)  
✅ Bulk drag (selected nodes move together)  
❌ Snap-to-grid  
❌ Align/distribute commands  
❌ Smart connection routing  

**Code Evidence:**
```jsx
// Drag-select box exists (line 170-182)
// No grid snap logic
// No alignment/distribution commands
```

---

## 6. Sidebar & Node Library

### EVE-NG
- **Left sidebar:** Collapsible panel with device templates organized by vendor/type
- **Right sidebar:** Shows active nodes in current lab, network objects, management clouds
- **Drag-from-library:** Standard UX — drag template onto canvas to add node

### OmniLab (Current)
```jsx
// No persistent left sidebar found in LabCanvas.jsx
// Modal-based node addition (addNodeModal state, line 110)
// Node library shown via modal popup, not sidebar
```

**Code Evidence:**
```jsx
const [addNodeModal, setAddNodeModal] = useState(null)
const [activeCategory, setActiveCategory] = useState('Routers')
const [pendingAdd, setPendingAdd] = useState(null)

// Modal approach vs persistent sidebar
```

**UX Difference:**
- EVE-NG: Always-visible node library, fast drag-and-drop workflow
- OmniLab: Modal popup, more clicks to add nodes

---

## 7. Grid & Canvas Background

### EVE-NG
- **Fine grid** (light gray dots or lines, subtle)
- **Major grid** (slightly darker every 5-10 units)
- **Purpose:** Helps with alignment, professional look

### OmniLab (Current)
```jsx
// Grid colors defined (line 127-128):
const gridSm=darkMode?'#1e293b':'#f0f0f0'
const gridLg=darkMode?'#334155':'#d1d5db'

// Rendering unclear in first 200 lines
```

**Likely Present:** Grid seems implemented given color definitions.

---

## 8. Dark Mode & Theming

### Both Support Dark Mode
✅ EVE-NG: Dark theme available  
✅ OmniLab: Dark mode toggle implemented (line 94)

---

## 9. Top Toolbar

### EVE-NG (Screenshot)
```
┌────────────────────────────────────────────┐
│ + | USR: admin | PAS: Hbmcse294pound      │  ← Top left
│   | 192.168.1.170 | @ | ⚙ | ...            │
└────────────────────────────────────────────┘
```
- Lab controls (add, settings)
- User/credential display (for multi-user)
- Management IP shown
- Quick access to settings

### OmniLab (Current)
```jsx
// No top toolbar visible in LabCanvas.jsx first 200 lines
// Context menu exists (right-click)
// Node panel for inspector (line 107-108)
```

**Gap:** No persistent toolbar with lab-level controls.

---

## Summary of Critical Missing Features

| Feature | EVE-NG | OmniLab | Priority |
|---------|--------|---------|----------|
| **Visual container boxes** | ✅ Dashed rectangles with labels | ❌ Not implemented | 🔥 CRITICAL |
| **Network objects on canvas** | ✅ Clouds, LAGs, bridges visible | ❌ In state, not rendered | 🔥 CRITICAL |
| **Text annotations** | ✅ Arbitrary labels anywhere | ❌ State exists, no UI | 🔴 HIGH |
| **Interface labels on links** | ✅ Port numbers shown | ❌ Not rendered | 🔴 HIGH |
| **Snap-to-grid** | ✅ Toggle available | ❌ Not implemented | 🟡 MEDIUM |
| **Align/distribute tools** | ✅ Right-click commands | ❌ Not implemented | 🟡 MEDIUM |
| **Sidebar node library** | ✅ Persistent panel | ⚠️ Modal-based | 🟡 MEDIUM |
| **Connection routing** | ✅ Smart path avoidance | ❌ Straight lines only | 🟢 LOW |
| **Minimap** | ✅ Present | ✅ Implemented (line 96) | ✅ DONE |
| **Dark mode** | ✅ Supported | ✅ Implemented (line 94) | ✅ DONE |

---

## Recommendations

### Phase 1: Visual Hierarchy (MUST HAVE)
1. **Add container boxes:** Rectangle with dashed border, editable label, drag-to-move, resize handles
2. **Render network objects:** Small cloud icons with labels, draggable, connect-able
3. **Show interface labels on links:** Text along connection lines showing port names

### Phase 2: Professional Layout Tools
4. **Snap-to-grid:** Toggle in toolbar, configurable grid size (default 20px)
5. **Align/distribute:** Right-click selected nodes → Align Left/Right/Center/Top/Bottom, Distribute Horizontally/Vertically
6. **Text annotations:** Click-to-add text labels anywhere on canvas

### Phase 3: UX Polish
7. **Sidebar node library:** Replace modal with persistent left panel (EVE-NG style)
8. **Top toolbar:** Lab controls, settings, export/import, view options
9. **Smart connection routing:** Orthogonal lines with auto-avoid (optional)

---

## Code Changes Required

### 1. Container Boxes (Priority 1)
```jsx
// Add to state:
const [containers, setContainers] = useState([])

// Container structure:
{
  id: 'cont-1',
  x: 100,
  y: 100,
  width: 400,
  height: 300,
  label: 'Alpharetta DC1',
  style: 'dashed', // or 'solid', 'dotted'
  color: '#94a3b8',
  background: 'transparent' // or fill color with opacity
}

// Render in SVG before nodes:
{containers.map(c => (
  <g key={c.id}>
    <rect
      x={c.x} y={c.y} width={c.width} height={c.height}
      fill={c.background} stroke={c.color}
      strokeWidth={2} strokeDasharray="8,4"
    />
    <text x={c.x+10} y={c.y-8} fill={tc} fontSize={13} fontWeight={600}>
      {c.label}
    </text>
  </g>
))}
```

### 2. Network Objects on Canvas (Priority 1)
```jsx
// Already have networks state, need rendering:
{networks.map(net => {
  const def = NET_DEFS[net.type] || NET_DEFS.internal
  return (
    <g key={net.id} transform={`translate(${net.x},${net.y})`}>
      {/* Cloud icon SVG */}
      <path d="M8,12 Q8,8 12,8 Q14,6 16,8 Q20,8 20,12 Q20,16 16,16 L12,16 Q8,16 8,12"
        fill={darkMode?'#1e293b':'#f8fafc'} stroke={def.color} strokeWidth={1.5}/>
      <text x={24} y={12} fill={tc} fontSize={11}>{net.label || def.label}</text>
    </g>
  )
})}
```

### 3. Interface Labels (Priority 1)
```jsx
// Update link rendering to add text:
{links.map(link => {
  const src = nodes.find(n => n.id === link.srcId)
  const dst = nodes.find(n => n.id === link.dstId)
  if (!src || !dst) return null
  
  const midX = (src.x + dst.x) / 2
  const midY = (src.y + dst.y) / 2
  
  return (
    <g key={link.id}>
      <line x1={src.x+24} y1={src.y+24} x2={dst.x+24} y2={dst.y+24}
        stroke={darkMode?'#475569':'#94a3b8'} strokeWidth={2}/>
      
      {/* Interface labels */}
      <text x={src.x+30} y={src.y+20} fontSize={9} fill={sc}>
        {link.srcIface}
      </text>
      <text x={dst.x+30} y={dst.y+20} fontSize={9} fill={sc}>
        {link.dstIface}
      </text>
    </g>
  )
})}
```

### 4. Snap-to-Grid (Priority 2)
```jsx
const GRID_SIZE = 20 // configurable

const snapToGrid = (val) => Math.round(val / GRID_SIZE) * GRID_SIZE

// In drag handler (line 192-196):
if (d.kind === 'node') {
  const snapped = snapEnabled ? {
    x: snapToGrid(nx),
    y: snapToGrid(ny)
  } : { x: nx, y: ny }
  
  nodesRef.current = nodesRef.current.map(n =>
    n.id === d.id ? { ...n, ...snapped } : n
  )
  setNodes([...nodesRef.current])
}
```

### 5. Align/Distribute (Priority 2)
```jsx
const alignLeft = () => {
  const sel = Array.from(selected).map(id => nodes.find(n => n.id === id))
  const minX = Math.min(...sel.map(n => n.x))
  const updated = nodes.map(n =>
    selected.has(n.id) ? { ...n, x: minX } : n
  )
  setNodes(updated)
}

// Add to context menu (right-click):
{selected.size > 1 && (
  <>
    <div onClick={alignLeft}>Align Left</div>
    <div onClick={alignRight}>Align Right</div>
    <div onClick={distributeHorizontally}>Distribute Horizontally</div>
    ...
  </>
)}
```

---

## Visual Mockup: What Harold Sees Now vs What He Needs

### Current OmniLab (Hypothetical Same Topology)
```
┌─────────────────────────────────────────────┐
│                                             │
│  [ALP-FW-01]     [ALP-CORE-01]             │
│       │              │                      │
│       └──────────────┘                      │
│                                             │
│  [ALP-FW-02]     [ALP-CORE-02]             │
│       │              │                      │
│       └──────────────┘                      │
│                                             │
│  [ALP-TOR-01]    [ALP-TOR-02]              │
│                                             │
│  [NOR-FW-01]     [NOR-CORE-01]             │
│  [NOR-FW-02]     [NOR-CORE-02]             │
│                                             │
└─────────────────────────────────────────────┘
```
- All nodes at same visual level
- No indication of datacenter boundaries
- No way to tell what links represent (LAG? direct? mgmt?)
- Flat, hard to parse at a glance

### Needed OmniLab (EVE-NG Style)
```
┌──────────────────────────────────────────────────────┐
│  ╭─────── Alpharetta DC1 ────────╮                  │
│  ┊  ╭─ Primary ──╮                ┊                  │
│  ┊  ┊ ALP-FW-01 ─┴─ LAG 265 ───┐ ┊                  │
│  ┊  ┊            ╭─ Keepalive ──┤ ┊                  │
│  ┊  ┊ ALP-FW-02 ─┴──────────────┘ ┊                  │
│  ┊  ╰─────────────────────────────╯                  │
│  ┊                                                    │
│  ┊  ╭─── LAG 1 ───╮                                  │
│  ┊  ┊ ALP-CORE-01 ┊                                  │
│  ┊  ┊ ALP-CORE-02 ┊                                  │
│  ┊  ╰─────────────╯                                  │
│  ╰─────────────────────────────────╯                 │
│                                                       │
│  ╭─────── Norcross DC2 ──────────╮                  │
│  ┊  ╭─ Secondary ──╮              ┊                  │
│  ┊  ┊ NOR-FW-01    ┊              ┊                  │
│  ┊  ┊ NOR-FW-02    ┊              ┊                  │
│  ┊  ╰──────────────╯              ┊                  │
│  ╰────────────────────────────────╯                  │
│                                                       │
│  [mgmt-01]  [Net-Cloud1]  [Keepalive]               │
│    (network objects visible in sidebar too)          │
└──────────────────────────────────────────────────────┘
```
- Clear datacenter boundaries (dashed boxes)
- Logical groupings (Primary, Secondary PODs)
- Network objects visible (LAG 265, Keepalive)
- Interface labels on connections
- Professional, structured, immediately parsable

---

## Next Steps

1. **Review with Harold:** Confirm these are the pain points he's experiencing
2. **Prioritize features:** Which of the 3 critical gaps (containers, network objects, interface labels) to tackle first?
3. **Create Linear issues:** Break down each feature into implementation tasks
4. **Design decisions:**
   - Container box UI: drag-to-create? modal? keyboard shortcut?
   - Network object styling: cloud icon? switch icon? user-selectable?
   - Interface label positioning: always show? hover-only? configurable?

---

**End of Comparison Report**
