# EVE-NG Codebase Analysis
**Date:** 2026-05-26  
**System:** EVE-NG at 192.168.1.156  
**User:** root  
**Analysis By:** 007  

## Executive Summary

After SSH access to EVE-NG backend and full codebase scan, I discovered that **"container boxes" are NOT functional grouping containers** - they're simply **drawing/annotation tools** (rectangles, circles, text labels) that overlay the canvas. This is fundamentally different from what I initially thought.

---

## Key Discoveries

### 1. Drawing Tools (NOT Container Logic)

EVE-NG provides **annotation/drawing tools** via two API endpoints:

#### A. Text Objects (`/api/labs{path}/textobjects`)
Types include:
- `type="text"` - Text labels (HTML div with styled text)
- `type="circle"` - Ellipse shapes (SVG ellipse)
- `type="shape"` - Rectangle shapes (SVG rect)

**Example from lab file:**
```xml
<textobject id="4" name="_copy" type="shape">
  <data>BASE64_ENCODED_HTML</data>
</textobject>
```

**Decoded HTML (Dashed Rectangle Box):**
```html
<div id="customShape4" class="customShape context-menu resizable-content" 
     style="display: inline; z-index: 998; width: 418px; height: 124px; 
            position: absolute; left: 871px; top: 97px">
  <svg width="418px" height="124px">
    <rect x="1" y="1" width="416px" height="122px" 
          fill="#FFFFFF" stroke="#000000" stroke-width="1" 
          stroke-dasharray="10,10"></rect>
  </svg>
</div>
```

**Properties:**
- Absolute positioned HTML div
- SVG shapes inside
- Resizable via CSS classes
- Context menu enabled
- z-index: 998-999 (above canvas, below modals)
- Custom fill colors (e.g., `fill="#FFFFFF"`)
- Stroke styles: solid, dashed (`stroke-dasharray="10,10"`)

#### B. Line Objects (`/api/labs{path}/lineobjects`)
- Custom lines/arrows drawn on canvas
- Independent of network connections
- Used for visual annotation

**API Operations:**
```
GET    /api/labs{path}/textobjects           # List all
GET    /api/labs{path}/textobjects/{id}      # Get one
POST   /api/labs{path}/textobjects           # Create
PUT    /api/labs{path}/textobjects           # Bulk update
PUT    /api/labs{path}/textobjects/{id}      # Update one
DELETE /api/labs{path}/textobjects/{id}      # Delete

GET    /api/labs{path}/lineobjects           # List all
POST   /api/labs{path}/lineobjects           # Create
PUT    /api/labs{path}/lineobjects/{id}      # Update style
DELETE /api/labs{path}/lineobjects/{id}      # Delete
```

---

### 2. Network Link Styling (Interface-Level)

Each interface in a node has rich styling properties:

```xml
<interface id="8" name="1/1/8" type="ethernet" network_id="19" 
           vid="1" 
           color="rgba(255, 128, 0, 1)" 
           style="Dashed" 
           linkstyle="Flowchart" 
           label="DC1 - 5Gbps" 
           labelpos="0.5" 
           stub="5" 
           width="1" 
           curviness="10" 
           beziercurviness="150" 
           round="0" 
           midpoint="0.5" 
           srcpos="0.15" 
           dstpos="0.85"/>
```

**Key Properties:**
- `color` - RGBA/hex color for the link
- `style` - "Solid" | "Dashed" (line style)
- `linkstyle` - "Straight" | "Bezier" | "Flowchart" | "StateMachine" (path shape)
- `label` - Text shown on the link (e.g., "DC1 - 5Gbps")
- `labelpos` - 0.0 to 1.0 (position along link)
- `curviness` - Curve amount for Bezier paths
- `width` - Line thickness
- `stub` - Stub length (for T-junctions)

---

### 3. Network Objects API

```
GET    /api/labs{path}/networks              # List all networks
GET    /api/labs{path}/networks/{id}         # Get one network
POST   /api/labs{path}/networks              # Create network
PUT    /api/labs{path}/networks/{id}         # Update network
DELETE /api/labs{path}/networks/{id}         # Delete network
```

**Network Properties (from lab file):**
```xml
<network id="8" 
         smart="0" 
         native_vlan="1" 
         vlan8021ad="0" 
         type="bridge" 
         name="Net-ArubaCX-10.0410iface3" 
         left="0" 
         top="0" 
         style="Solid" 
         linkstyle="Straight" 
         color="" 
         label="" 
         visibility="0" 
         icon="lan.png" 
         width="0" 
         hideme="0" 
         l2filter_lldp="0" 
         l2filter_stp="0" 
         l2filter_cisco="0" 
         l2filter_lacp="0"/>
```

**Key Insight:** Networks have `visibility` property - when visible, they could be rendered as objects on canvas (not currently visible in Harold's lab - all set to `visibility="0"`).

---

### 4. Packet Capture / Traffic Filter

**API Endpoint:**
```
POST /api/capture/{path}
  Body: { interface/node/network, filter, duration }
```

**Purpose:** Start packet capture on a specific interface, node, or network.

**What I DON'T See:**
- Real-time traffic visualization on canvas
- Protocol badges/icons on links during live traffic
- Live traffic flow animation

**What Likely Exists:**
- Capture to PCAP file
- Download for Wireshark analysis
- Post-capture analysis (not live visualization)

**ACTION REQUIRED:** Harold needs to show me WHERE in EVE-NG GUI he sees "traffic filter" visualization. Possible locations:
1. Right-click link → "Start Capture" → shows real-time protocols?
2. Separate monitoring panel showing active traffic?
3. Network statistics overlay?

---

### 5. Node Properties (Critical for Rendering)

```xml
<node id="5" 
      name="ALP-TOR-01" 
      type="qemu" 
      template="arubacx" 
      image="arubacx-10.05" 
      console="telnet" 
      icon="Switch-3D-L2-S.svg" 
      width="79" 
      config="0" 
      left="226" 
      top="697">
```

**Key for OmniLab:**
- `left`, `top` - Canvas position (pixels)
- `width` - Icon render width
- `icon` - SVG filename (from `/opt/unetlab/html/images/icons/`)

---

## What This Means for OmniLab

### ✅ Already Have (or Easy to Add)
1. **Nodes on canvas** - Already implemented in LabCanvas.jsx
2. **Draggable nodes** - Already working
3. **Network connections** - Already rendering
4. **Link styling** - Need to add color, style (solid/dashed), linkstyle (straight/bezier/flowchart)
5. **Interface labels** - Need to add `label` property on interface connections

### ❌ Missing (Need to Implement)

#### Priority 1: Drawing Tools (Those "Container Boxes")
**CRE-64 REVISED:** Implement drawing/annotation tools
- Rectangle shapes (solid/dashed borders, custom fill colors)
- Circle/ellipse shapes
- Text labels (positioned HTML divs)
- Resizable, draggable, z-index layering
- Store as base64-encoded HTML in lab file
- API: `/api/labs/{path}/textobjects`

#### Priority 2: Network Object Visibility
**CRE-65 REVISED:** Render network objects when `visibility="1"`
- Cloud icons for networks (from `icon` property)
- Positioned at `left`, `top` coordinates
- Show `label` text
- Show connection count badge

#### Priority 3: Link Styling
**CRE-66 REVISED:** Rich link styling
- Interface labels on links (`label` property)
- Link colors (RGBA/hex)
- Link styles (solid, dashed)
- Link paths (straight, bezier, flowchart, state machine)
- Curviness controls
- Width/thickness

#### Priority 4: Modals (Not Popups)
**CRE-67:** Already correct - replace prompt() with in-canvas modals

#### Priority 5: Traffic Filter (BLOCKED - Need User Input)
**CRE-68:** Cannot design without seeing what Harold means by "traffic filter visualization" in EVE-NG

---

## EVE-NG Codebase Structure

```
/opt/unetlab/
├── html/
│   ├── api.php              # Main API router
│   ├── eve_api.txt          # API documentation (923 lines)
│   ├── images/
│   │   └── icons/           # Node icons (SVG)
│   └── src/                 # Vue.js frontend
│       ├── components/
│       │   ├── EVE_Main.vue
│       │   ├── Topology/
│       │   └── Common/
│       └── pages/
│           ├── labview.vue
│           └── main.vue
└── labs/
    ├── index                # Lab index file
    ├── SOS Lab/
    │   └── SOS LAB.unl      # XML lab definition
    └── ...
```

**Lab File Format:** XML with base64-encoded HTML for text/shape objects

---

## Revised Understanding of "Container Boxes"

**What I Initially Thought:**
- Functional grouping containers (like Docker Compose networks)
- Nodes belong to containers
- Collapse/expand logic
- Automatic layout within container

**What They Actually Are:**
- **Visual annotation rectangles** (SVG rects with dashed borders)
- **No functional grouping** - just a drawing on top of canvas
- Nodes don't "belong" to them - just positioned under/over via z-index
- User manually draws box around nodes for visual organization
- Stored as HTML divs with SVG shapes inside

**Example Use Case (from Harold's lab):**
- Draw dashed rectangle around "Alpharetta DC1 Primary" nodes
- Draw another dashed rectangle around "Norcross DC2 Secondary" nodes
- These are just visual guides - no logic, no grouping, just decoration

---

## Questions for Harold

1. **Traffic Filter Feature:**
   - WHERE in EVE-NG GUI do you access "traffic filter" visualization?
   - WHAT does it look like? (Screenshot or describe)
   - WHEN does it show traffic? (Real-time during lab run? Post-capture?)
   - WHICH protocols are displayed? (Just ARP/BGP/OSPF or all packets?)

2. **Drawing Tools Priority:**
   - Do you actively use the rectangle/circle drawing tools in your production labs?
   - How important is this vs. other features (link styling, interface labels)?

3. **Network Object Visibility:**
   - Have you ever turned on `visibility` for a network object?
   - Do you want OmniLab to show network clouds on canvas?

---

## Next Steps (Pending Harold's Input)

1. **Wait for traffic filter clarification** before designing CRE-68
2. **Revise Linear tickets** based on new understanding:
   - CRE-64: "Drawing Tools (Rectangles, Circles, Text Labels)"
   - CRE-65: "Network Object Visibility Toggle"
   - CRE-66: "Rich Link Styling (Colors, Styles, Labels)"
3. **Prioritize** based on Harold's actual usage patterns
4. **Implementation order:**
   - CRE-66 (link styling) - Most impactful, easiest
   - CRE-67 (modals) - UX pain point, already designed
   - CRE-64 (drawing tools) - Visual polish, moderate effort
   - CRE-65 (network visibility) - Nice-to-have
   - CRE-68 (traffic filter) - BLOCKED on user input

---

## Files Analyzed

- `/opt/unetlab/html/eve_api.txt` - 923 lines, full API documentation
- `/opt/unetlab/labs/SOS Lab/SOS LAB.unl` - 61KB XML lab file with:
  - 14 nodes (ArubaOS-CX switches, Palo Alto firewalls)
  - 28 networks
  - 47 textobjects (shapes, text labels)
  - Rich interface styling with colors, labels, link styles

**Key Finding:** Container boxes are `<textobject type="shape">` with base64-encoded HTML containing SVG rectangles. They are purely visual annotations, not functional containers.
