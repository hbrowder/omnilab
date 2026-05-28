# EVE-NG Deep Dive Analysis
## Comprehensive UI/UX Study for OmniLab Parity & Excellence

**Date:** May 27, 2026  
**Analyst:** Kit (Hermes Agent 007)  
**Goal:** Make OmniLab GREATER THAN OR EQUAL TO EVE-NG in every way

---

## Executive Summary

EVE-NG (Emulated Virtual Environment - Next Generation) is a mature network emulation platform with 10+ years of refinement. This analysis breaks down **what makes EVE-NG feel professional** and **what OmniLab needs to match or exceed it**.

### Key Findings

1. **Textobjects & Annotations** — EVE-NG's secret weapon for professional diagrams
2. **Rich Context Menus** — Right-click everywhere reveals deep functionality
3. **Visual Design Language** — Consistent icons, colors, spacing create polish
4. **Topology Organization Tools** — Container boxes, shapes, grouping, alignment
5. **Workflow Efficiency** — Keyboard shortcuts, drag-drop, batch operations

---

## 1. DATA STRUCTURE ANALYSIS

### EVE-NG Lab File Format (.unl)

EVE-NG stores labs as XML files with three main sections:

#### 1.1 Topology Section
```xml
<topology>
  <nodes>
    <!-- Network devices with attributes -->
    <node id="2" name="switch4" type="iol" 
          left="777" top="294"
          icon="Switch L3.png">
      <interface id="0" name="e0/0" network_id="2"
                 labelpos="0.5" curviness="10" 
                 beziercurviness="150"/>
    </node>
  </nodes>
  
  <networks>
    <!-- Connections/bridges -->
    <network id="1" type="bridge" name="Net-sw2iface_0"
             left="306" top="190" 
             style="Solid" linkstyle="Straight"
             visibility="0" icon="lan.png"/>
  </networks>
</topology>
```

**Key Observations:**
- **Absolute positioning** (left/top in pixels) — simple, direct
- **Interface styling** — curviness, beziercurviness, labelpos, width
- **Network objects** — explicit position, visibility control, style attributes

#### 1.2 Objects Section (THE GAME CHANGER)
```xml
<objects>
  <textobjects>
    <textobject id="1" name="txt 1" type="text">
      <data>[base64-encoded HTML]</data>
    </textobject>
    <textobject id="34" name="circle34" type="circle">
      <data>[base64-encoded SVG shape]</data>
    </textobject>
  </textobjects>
</objects>
```

**Decoded Example — Text Annotation:**
```html
<div id="customText1" 
     class="customShape customText context-menu jtk-managed jtk-draggable editable"
     style="position: absolute; left: 564px; top: 27px; z-index: 1001;">
  <p><span style="font-size:20px;"><strong>Spanning-Tree</strong></span></p>
</div>
```

**Decoded Example — SVG Shape:**
```html
<div id="customShape34" class="customShape context-menu jtk-draggable ui-resizable"
     style="position: absolute; left: 1200px; top: 108px;">
  <svg width="12" height="71.7778">
    <ellipse cx="6" cy="35.8889" rx="4.75" ry="34.6389" 
             stroke="#000000" stroke-width="2.5" 
             fill="rgba(255, 255, 255, 0)"/>
  </svg>
</div>
```

**CRITICAL INSIGHT:** 
EVE-NG stores **rich HTML/SVG content** as base64-encoded data inside the lab file. This allows:
- Text labels with **custom fonts, sizes, colors, formatting**
- Arbitrary **SVG shapes** (circles, rectangles, lines, arrows)
- **Container boxes** (visual grouping with borders)
- **Editable annotations** (contenteditable=true)
- **Drag-and-drop** (jtk-draggable class)
- **Right-click menus** (context-menu class)
- **Resizable elements** (ui-resizable class)

---

## 2. TEXTOBJECTS — THE PROFESSIONAL EDGE

### 2.1 What Are Textobjects?

Textobjects are **floating HTML/SVG elements** overlaid on the canvas. They're NOT part of nodes or networks — they're independent decorative/organizational elements.

**Use Cases in the COX Hotel Lab:**

1. **Title Labels**
   - "Spanning-Tree" (large, bold, 20px) — lab title at top
   
2. **Port Role Indicators**
   - "DP" (Designated Port) — blue, bold
   - "RP" (Root Port) — black, bold
   - "BLK" (Blocking) — red, bold
   - Position: next to switch ports showing STP state

3. **Protocol/Config Annotations**
   - "802.1D", "802.1w" — protocol identifiers
   - "Trunk" — link type labels
   - "Root Bridge" — special role indicator

4. **Documentation Blocks**
   - Multi-line code blocks with port configurations
   - Path cost tables (10 Mbps = 100, 1 Gbps = 4)
   - QoS policy configurations
   - DHCP helper address notes

5. **MAC/IP Address Labels**
   - "aabb.cc00.0100" — MAC addresses near nodes
   - "172.24.10.1" — IP addresses for management

6. **Visual Grouping Shapes**
   - Vertical ellipses (SVG) — logical grouping boundaries
   - Used to show redundant pair relationships (sw5/sw6)

### 2.2 CSS Classes Used

```css
.customShape         /* Base class for all textobjects */
.customText          /* Text-specific styling */
.context-menu        /* Right-click menu enabled */
.jtk-managed         /* jsPlumb library manages it */
.jtk-draggable       /* Can be dragged */
.editable            /* Can be edited inline */
.ui-selectee         /* jQuery UI selectable */
.ui-resizable        /* Can be resized */
```

### 2.3 Z-Index Strategy

- **Nodes:** z-index ~500-800 (background)
- **Links:** z-index ~900-950 (middle)
- **Textobjects:** z-index 999-1001 (foreground)

This ensures text labels always appear **on top** of nodes and connections.

---

## 3. VISUAL DESIGN COMPARISON

### 3.1 OmniLab Current State (CRE-69 Analysis)

**STRENGTHS:**
- ✅ Interface labels implemented (eth0, eth1 on nodes)
- ✅ Network objects rendered (cloud icons for networks)
- ✅ Clean, modern aesthetic
- ✅ Dark mode support

**GAPS:**
- ❌ No free-floating text annotations
- ❌ No container/grouping boxes
- ❌ No SVG shape overlays
- ❌ Limited right-click menus on canvas
- ❌ No inline editing of labels
- ❌ No visual indicators for logical grouping

### 3.2 EVE-NG Visual Elements

#### Icons & Symbols
- **Device icons:** 100+ professional PNG/SVG icons
  - Cisco (routers, switches, firewalls)
  - Palo Alto (firewalls)
  - Windows/Linux (endpoints)
  - Nexus (datacenter switches)
- **Network icons:** Cloud, LAN, WAN shapes
- **Protocol badges:** OSPF, BGP, EIGRP overlays

#### Color Coding
- **Port states:** Green (up), Red (down), Yellow (admin down)
- **STP roles:** Blue (DP), Black (RP), Red (BLK)
- **Link types:** Solid (active), Dashed (backup), Dotted (virtual)

#### Typography
- **Labels:** Sans-serif, 12-14px default
- **Titles:** Bold, 16-20px
- **Code blocks:** Monospace, syntax highlighting
- **Annotations:** Variable size, bold/italic/underline support

---

## 4. INTERACTION PATTERNS

### 4.1 Right-Click Context Menus

**On Nodes:**
- Start/Stop/Restart
- Console access (Telnet/VNC/RDP)
- Edit configuration
- Clone device
- Export/Import config
- Wipe startup-config
- Delete

**On Links:**
- Edit link properties (delay, packet loss)
- Change line style (solid/dashed/dotted)
- Set bandwidth/latency
- Capture traffic (Wireshark integration)
- Delete

**On Canvas (empty space):**
- Add node (with template picker)
- Add network
- Add text label
- Add shape (circle, rectangle, line)
- Paste (if clipboard has node)
- Lab settings
- Zoom in/out/fit

**On Textobjects:**
- Edit text (inline editing)
- Change font/size/color
- Rotate element
- Bring to front/Send to back
- Duplicate
- Delete
- Lock position

### 4.2 Drag & Drop Behaviors

**Nodes:**
- Click-drag to move
- Shift-click-drag to multi-select
- Ctrl-drag to clone
- Links auto-update when nodes move

**Textobjects:**
- Grab handles to resize
- Corner drag maintains aspect ratio
- Rotate handle at top (for shapes)
- Snap-to-grid when enabled

**Links:**
- Drag midpoint to create curve/bend
- Drag label to reposition
- Drag endpoint to reconnect

### 4.3 Selection & Multi-Select

- **Single select:** Click element
- **Multi-select:** Shift-click to add/remove
- **Box select:** Click-drag on canvas (lasso)
- **Select all:** Ctrl+A
- **Batch operations:** Move, delete, export selected

### 4.4 Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **Ctrl+C** | Copy selected |
| **Ctrl+V** | Paste |
| **Ctrl+Z** | Undo |
| **Ctrl+Y** | Redo |
| **Delete** | Delete selected |
| **Ctrl+A** | Select all |
| **Ctrl+S** | Save lab |
| **Ctrl+F** | Find node |
| **Arrow keys** | Nudge selected (1px) |
| **Shift+Arrows** | Nudge selected (10px) |
| **+/-** | Zoom in/out |
| **0** | Zoom to 100% |
| **F** | Zoom to fit |
| **G** | Toggle grid |
| **L** | Toggle link labels |

---

## 5. JSPLUMB LIBRARY ANALYSIS

EVE-NG uses **jsPlumb Community Edition** for canvas topology rendering.

### 5.1 jsPlumb Features in EVE-NG

```javascript
// From jsplumb.browser-ui.es-CNieudsn.js

- Endpoint types: Dot, Rectangle, Image, Blank
- Connector types: Straight, Bezier, Flowchart, StateMachine
- Anchor positions: Top, Bottom, Left, Right, Center, Dynamic
- Overlay support: Arrow, Label, Custom
- Drag & drop: Constrained, grid snapping
- Connection validation: Prevent invalid links
- Event system: Click, hover, drag, drop, connect, disconnect
```

### 5.2 OmniLab's React Equivalent

OmniLab uses **React Flow** (similar to jsPlumb but React-native).

**Comparison:**

| Feature | jsPlumb | React Flow |
|---------|---------|------------|
| **Framework** | Vanilla JS | React |
| **Maturity** | 15+ years | 5+ years |
| **Customization** | High (CSS) | High (React components) |
| **Performance** | Good (up to 500 nodes) | Excellent (up to 1000+ nodes) |
| **Textobjects** | Manual HTML overlay | Custom React nodes |
| **Right-click** | Native context menu | react-contexify or custom |

**RECOMMENDATION:**  
React Flow supports custom node types — OmniLab can implement textobjects as **custom annotation nodes** with `type="annotation"`.

---

## 6. CONTAINER BOXES (CRE-71 FEATURE)

### 6.1 EVE-NG Container Box Examples

In the COX Hotel Lab, I observed:

1. **Vertical ellipse groupings** (lines 183-188)
   - Used to show redundant pairs (sw5/sw6 in ellipse)
   - SVG ellipse: `<ellipse rx="4.75" ry="34.6389">`
   - Transparent fill, black stroke

2. **Implicit grouping via text labels**
   - "802.1D" label groups sw1/sw2 (classic STP)
   - "BLK" labels identify all blocking ports
   - Configuration code blocks document port behavior

### 6.2 What OmniLab Needs

**Container Box Types:**

1. **Rectangle** (most common)
   - Rounded corners (border-radius: 8px)
   - Dashed border (stroke-dasharray)
   - Transparent or subtle fill
   - Drag-to-resize handles
   - Title label at top

2. **Ellipse** (for redundancy groups)
   - Same as EVE-NG implementation
   - Vertical or horizontal orientation

3. **Freeform Polygon** (advanced)
   - User draws arbitrary shape
   - Useful for complex network zones

**Container Properties:**
- Z-index control (above/below nodes)
- Send to back / Bring to front
- Lock/unlock (prevent accidental moves)
- Group membership (nodes inside container)
- Collapse/expand (hide child nodes)

---

## 7. WORKFLOW OBSERVATIONS

### 7.1 Lab Creation Flow (EVE-NG)

1. **New Lab** → Enter name, description, author
2. **Add Nodes** → Template picker (categorized: Cisco, Palo Alto, Linux, etc.)
3. **Position Nodes** → Drag to arrange
4. **Connect Interfaces** → Click interface, click target interface (jsPlumb draws line)
5. **Add Annotations** → Right-click canvas → "Add text label"
6. **Add Containers** → Right-click → "Add shape" → Rectangle/Ellipse
7. **Style Links** → Right-click link → Change style, color, label
8. **Start Lab** → Right-click nodes → "Start" (batch start all available)

### 7.2 OmniLab Workflow Gaps

| EVE-NG Feature | OmniLab Status |
|----------------|----------------|
| **Batch node start** | ❌ Missing (start one at a time) |
| **Template categories** | ⚠️ Partial (alphabetical list) |
| **Add text labels** | ❌ Missing |
| **Add container boxes** | ❌ Missing (CRE-71 in progress) |
| **Link styling** | ⚠️ Limited (only color via TrafficFilterPanel) |
| **Keyboard shortcuts** | ⚠️ Some (Ctrl+S works, but no Ctrl+Z/Y/C/V) |
| **Find node** | ❌ Missing |
| **Zoom controls** | ✅ Implemented |
| **Grid toggle** | ❌ Missing |

---

## 8. PROFESSIONAL POLISH DETAILS

### 8.1 Loading States & Animations

**EVE-NG:**
- Spinner when lab loads (Vue.js skeleton screens)
- Progress bar when starting multiple nodes
- Fade-in animation when canvas renders
- Smooth zoom/pan (CSS transitions)

**OmniLab:**
- ✅ Has loading states (React Suspense)
- ⚠️ No progress bar for batch operations
- ✅ Smooth canvas interactions (React Flow built-in)

### 8.2 Error Handling

**EVE-NG:**
- Toast notifications (top-right corner)
- Inline error messages (red border on failed nodes)
- Detailed logs in browser console
- Retry buttons on failed operations

**OmniLab:**
- ✅ Error banner in TrafficFilterPanel (CRE-68 M4 Task 4)
- ⚠️ No toast system (could add react-toastify)
- ✅ Console logs for debugging
- ⚠️ No retry buttons yet

### 8.3 Attention to Detail

**EVE-NG Examples:**
- Link labels auto-rotate to match line angle
- Hover tooltips on icons (show node type, status)
- Subtle drop shadow on nodes (depth perception)
- Anti-aliased fonts and icons (crisp rendering)
- Context-sensitive cursor changes (move, resize, pointer)

**OmniLab Can Add:**
- ⬆️ Tooltip component for node metadata
- ⬆️ CSS drop shadows (box-shadow on node cards)
- ⬆️ Cursor changes (cursor: move/nwse-resize/grab)
- ⬆️ Link label rotation (React Flow supports)

---

## 9. FEATURE PARITY CHECKLIST

### 9.1 Core Canvas Features

| Feature | EVE-NG | OmniLab | Priority |
|---------|--------|---------|----------|
| **Node rendering** | ✅ | ✅ | — |
| **Link rendering** | ✅ | ✅ | — |
| **Interface labels** | ✅ | ✅ | — |
| **Network objects** | ✅ | ✅ | — |
| **Text annotations** | ✅ | ❌ | 🔴 **P0** |
| **Container boxes** | ✅ | ❌ | 🔴 **P0** |
| **SVG shapes** | ✅ | ❌ | 🟡 **P1** |
| **Drag & drop** | ✅ | ✅ | — |
| **Multi-select** | ✅ | ⚠️ | 🟡 **P1** |
| **Right-click menus** | ✅ | ⚠️ | 🔴 **P0** |
| **Zoom controls** | ✅ | ✅ | — |
| **Pan** | ✅ | ✅ | — |
| **Grid** | ✅ | ❌ | 🟢 **P2** |
| **Snap-to-grid** | ✅ | ❌ | 🟢 **P2** |

### 9.2 Node Operations

| Feature | EVE-NG | OmniLab | Priority |
|---------|--------|---------|----------|
| **Start node** | ✅ | ✅ | — |
| **Stop node** | ✅ | ✅ | — |
| **Restart node** | ✅ | ❌ | 🟡 **P1** |
| **Batch start** | ✅ | ❌ | 🟡 **P1** |
| **Console access** | ✅ | ✅ | — |
| **Edit node config** | ✅ | ✅ | — |
| **Clone node** | ✅ | ❌ | 🟢 **P2** |
| **Delete node** | ✅ | ✅ | — |
| **Export config** | ✅ | ❌ | 🟢 **P2** |

### 9.3 Link Operations

| Feature | EVE-NG | OmniLab | Priority |
|---------|--------|---------|----------|
| **Connect interfaces** | ✅ | ✅ | — |
| **Disconnect link** | ✅ | ✅ | — |
| **Edit link style** | ✅ | ⚠️ | 🟡 **P1** |
| **Link labels** | ✅ | ❌ | 🟡 **P1** |
| **Curved links** | ✅ | ⚠️ | 🟢 **P2** |
| **Packet capture** | ✅ | ✅ | — |
| **Traffic visualization** | ❌ | ✅ | 🎉 **OmniLab Advantage!** |

### 9.4 Keyboard Shortcuts

| Shortcut | EVE-NG | OmniLab | Priority |
|----------|--------|---------|----------|
| **Ctrl+S** | ✅ | ✅ | — |
| **Ctrl+Z** | ✅ | ❌ | 🔴 **P0** |
| **Ctrl+Y** | ✅ | ❌ | 🔴 **P0** |
| **Ctrl+C/V** | ✅ | ❌ | 🟡 **P1** |
| **Delete** | ✅ | ✅ | — |
| **Arrow nudge** | ✅ | ❌ | 🟢 **P2** |
| **+/- zoom** | ✅ | ⚠️ | 🟡 **P1** |
| **F zoom-fit** | ✅ | ❌ | 🟡 **P1** |
| **G grid** | ✅ | ❌ | 🟢 **P2** |

---

## 10. TECHNOLOGY STACK COMPARISON

### 10.1 EVE-NG Stack

```
Frontend:
- Vue.js 3 (Composition API)
- jsPlumb Community Edition
- jQuery UI (for draggable/resizable)
- CKEditor (for PDF annotations)
- Vuetify (Material Design components)
- Axios (HTTP client)

Backend:
- PHP 8.x (FastCGI)
- Apache 2.4
- SQLite 3 (user management)
- XML (lab file storage)
- QEMU/KVM (virtualization)
- IOL/IOU (Cisco emulation)

Architecture:
- Monolithic PHP app
- XML-RPC API (legacy)
- REST API (modern endpoints)
- File-based lab storage
- Session-based auth (cookies)
```

### 10.2 OmniLab Stack

```
Frontend:
- React 18 (Hooks, Context)
- React Flow (canvas library)
- Tailwind CSS (utility-first styling)
- Axios (HTTP client)
- WebSocket (real-time traffic)
- Recharts (packet count graphs)

Backend:
- FastAPI (Python 3.10+)
- SQLAlchemy (ORM)
- PostgreSQL (primary DB)
- JSON (lab file storage)
- Docker (container orchestration)
- tcpdump (packet capture)

Architecture:
- Microservices (lab, traffic, auth)
- REST API (OpenAPI docs)
- WebSocket (live traffic feed)
- Database-backed labs
- JWT auth (tokens)
```

### 10.3 Architectural Advantages

**OmniLab Wins:**
- Modern tech stack (React, FastAPI)
- Better performance (async Python, React Flow)
- Real-time traffic visualization (WebSocket)
- Containerized deployment (Docker)
- API-first design (OpenAPI)

**EVE-NG Wins:**
- Battle-tested (10+ years production use)
- Rich ecosystem (100+ device templates)
- Extensive documentation
- Large community
- Proven scalability (hundreds of nodes per lab)

---

## 11. MISSING FEATURES ANALYSIS

### 11.1 Critical Gaps (Block EVE-NG Parity)

1. **Text Annotations** (P0)
   - **Impact:** Can't create professional-looking diagrams
   - **Complexity:** Medium (React Flow custom nodes)
   - **Effort:** 2-3 days (node type, toolbar, persistence)

2. **Container Boxes** (P0)
   - **Impact:** Can't visually group devices
   - **Complexity:** Medium (z-index layering, drag-to-resize)
   - **Effort:** 3-5 days (see CRE-71 implementation plan)

3. **Expanded Right-Click Menus** (P0)
   - **Impact:** Reduced discoverability, slower workflows
   - **Complexity:** Low (react-contexify library)
   - **Effort:** 1-2 days (menu definitions, handlers)

4. **Undo/Redo** (P0)
   - **Impact:** User frustration on mistakes
   - **Complexity:** High (state history management)
   - **Effort:** 5-7 days (command pattern, snapshots)

### 11.2 Important Enhancements (Improve UX)

5. **Batch Node Operations** (P1)
   - Multi-select → Right-click → "Start Selected"
   - Effort: 2-3 days

6. **Link Styling** (P1)
   - Dashed, dotted, colored links
   - Effort: 1-2 days (React Flow edge types)

7. **Link Labels** (P1)
   - Show interface names on connections
   - Effort: 1 day (React Flow edge labels)

8. **Keyboard Shortcuts** (P1)
   - Full Ctrl+Z/Y/C/V/arrow key support
   - Effort: 2-3 days (keyboard event handlers)

### 11.3 Nice-to-Have (Polish)

9. **Grid & Snap** (P2)
   - Effort: 1-2 days (React Flow built-in)

10. **Node Cloning** (P2)
    - Effort: 1 day (API endpoint, UI button)

11. **Find Node** (P2)
    - Effort: 1-2 days (search input, highlight)

12. **SVG Shapes** (P2)
    - Arbitrary shapes (lines, arrows, polygons)
    - Effort: 3-4 days (shape toolbar, rendering)

---

## 12. RECOMMENDATIONS

### 12.1 Immediate Actions (This Sprint)

1. **Create Linear Epic: "EVE-NG Feature Parity"**
   - Parent epic for all parity work
   - Link CRE-69 (container boxes) to it

2. **Implement Text Annotations (CRE-72)**
   - Custom React Flow node type: `AnnotationNode`
   - Toolbar button: "Add Text"
   - Persistence: `lab.annotations[]` in database
   - Right-click: Edit, Delete, Font/Size/Color
   - Z-index: Above nodes and links

3. **Expand Right-Click Menus (CRE-73)**
   - Install `react-contexify`
   - Node menu: Add "Restart", "Clone", "Export Config"
   - Canvas menu: Add "Add Text", "Add Shape", "Paste"
   - Link menu: Add "Edit Style", "Add Label"

4. **Complete Container Boxes (CRE-71)**
   - Follow existing implementation plan
   - Add rectangle and ellipse types
   - Drag-to-resize, z-index control

### 12.2 Next Sprint

5. **Undo/Redo System (CRE-74)**
   - Command pattern for all mutations
   - History stack (max 50 actions)
   - Ctrl+Z/Y keyboard shortcuts
   - Visual indicator ("Undo [action]")

6. **Batch Operations (CRE-75)**
   - Multi-select nodes (Shift-click, box select)
   - Right-click selected → "Start All", "Stop All", "Delete All"
   - Progress bar for batch start

7. **Link Styling (CRE-76)**
   - Edit link modal (color, width, style, label)
   - React Flow edge types: solid, dashed, dotted
   - Save in `lab.links[]`

### 12.3 Future Work (Backlog)

8. **Advanced Keyboard Shortcuts (CRE-77)**
9. **Grid & Snap-to-Grid (CRE-78)**
10. **Find Node (CRE-79)**
11. **SVG Shapes (CRE-80)**
12. **Node Cloning (CRE-81)**
13. **Config Export (CRE-82)**

---

## 13. COMPETITIVE ADVANTAGES

### 13.1 Where OmniLab Already Wins

1. **Real-Time Traffic Visualization**
   - Animated packet flows on links
   - Protocol filtering (TCP, UDP, ICMP, DNS, HTTP)
   - Packet count badges
   - WebSocket live feed
   - **EVE-NG has NOTHING like this**

2. **Modern Tech Stack**
   - React 18 (faster, cleaner than Vue 2)
   - FastAPI (faster than PHP)
   - Docker (easier deployment)
   - PostgreSQL (better than XML files)

3. **API-First Design**
   - OpenAPI docs auto-generated
   - JWT auth (stateless, scalable)
   - RESTful endpoints (predictable)

4. **Responsive Design**
   - Mobile-friendly (EVE-NG desktop-only)
   - Dark mode built-in

### 13.2 Where EVE-NG Wins (For Now)

1. **Mature Ecosystem**
   - 100+ device templates
   - 15+ virtualization backends
   - Telnet/VNC/RDP console access
   - Wireshark integration

2. **Rich Diagram Tools**
   - Text annotations
   - Container boxes
   - SVG shapes
   - Right-click everywhere

3. **Battle-Tested**
   - Used by Fortune 500 companies
   - Cisco/Juniper certifications
   - 10+ years of bug fixes

### 13.3 How OmniLab Can Win

**Strategy: "Better in Every Way"**

1. **Match EVE-NG core features** (this analysis)
2. **Add unique killer features** (real-time traffic already done)
3. **Deliver superior UX** (React performance, modern design)
4. **Build community** (open-source, docs, tutorials)
5. **Focus on speed** (10x faster lab startup vs EVE-NG)

**Timeline:**
- **Sprint 1-2:** Feature parity (text, containers, menus, undo)
- **Sprint 3-4:** Polish (keyboard shortcuts, batch ops, styling)
- **Sprint 5-6:** Killer features (AI-powered topology suggestions, 3D view)
- **Sprint 7+:** Ecosystem (marketplace for labs, integrations)

---

## 14. NEXT STEPS

### For Harold:

1. **Review this analysis** — Confirm direction aligns with vision
2. **Prioritize features** — Adjust P0/P1/P2 if needed
3. **Create Linear epic** — "EVE-NG Feature Parity"
4. **Approve CRE-72** (Text Annotations) — Green light to start

### For Kit (007):

1. **Write CRE-72 implementation plan** (Text Annotations)
2. **Write CRE-73 implementation plan** (Right-Click Menus)
3. **Finalize CRE-71** (Container Boxes) — push commits, Linear update
4. **Create feature comparison table** — OmniLab vs EVE-NG vs GNS3
5. **Build demo video script** — Show traffic viz advantage

---

## 15. APPENDIX

### A. EVE-NG File Structure

```
/opt/unetlab/
├── html/                 # Vue.js frontend
│   ├── assets/          # JS bundles, CSS
│   ├── index.html       # SPA entry point
│   └── doc/             # Documentation
├── labs/                # Lab XML files
│   ├── user1/
│   │   └── mylab.unl
│   └── Shared/
├── data/                # SQLite databases
│   └── Exports/
│       └── userManagement.db
└── scripts/             # Utility scripts
```

### B. Key EVE-NG APIs

```
POST /api/auth/login          # Authenticate
GET  /api/folders             # List lab folders
GET  /api/labs                # List all labs
GET  /api/labs/{path}/{name}  # Get lab details
POST /api/labs/{path}/{name}/nodes/{id}/start  # Start node
POST /api/labs/{path}/{name}/nodes/{id}/stop   # Stop node
GET  /api/status              # System status
```

### C. Lab File Size Analysis

**COX Hotel STP Lab:**
- File size: 47,938 bytes (47 KB)
- Nodes: 21 devices
- Links: 13 networks
- Textobjects: 48 annotations
- **Ratio:** ~2.3 KB per node (including annotations)

**Implications for OmniLab:**
- Annotations add ~30-40% to file size
- Need efficient JSON storage
- Consider gzip compression for large labs

### D. Browser Compatibility

**EVE-NG Requirements:**
- Chrome 90+ (recommended)
- Firefox 88+ (supported)
- Safari 14+ (partial support)
- IE11 (NOT supported)

**OmniLab Current:**
- Chrome 90+ ✅
- Firefox 88+ ✅
- Safari 14+ ✅
- Edge 90+ ✅

---

## CONCLUSION

EVE-NG's professional feel comes from **10+ years of UX refinement**, particularly:
1. **Textobjects** — Game changer for diagram quality
2. **Container boxes** — Visual organization
3. **Rich interactions** — Right-click menus everywhere
4. **Polish** — Animations, tooltips, keyboard shortcuts

**OmniLab can match AND exceed EVE-NG** by:
1. Implementing parity features (this document roadmap)
2. Leveraging unique advantages (real-time traffic viz)
3. Delivering modern UX (React, dark mode, mobile)
4. Building community (open-source, marketplace)

**Next:** Implement CRE-72 (Text Annotations) and CRE-73 (Right-Click Menus) to close the biggest UX gaps.

---

**Document Version:** 1.0  
**Last Updated:** May 27, 2026, 04:30 UTC  
**Author:** Kit (Hermes Agent 007)  
**Status:** Ready for Review
