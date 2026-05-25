# Phase 1 Implementation Plan
**Date:** 2026-05-26  
**Sprint:** CRE-66, CRE-67, CRE-64, CRE-65  
**Status:** IN PROGRESS  

## Overview

Implementing EVE-NG feature parity based on codebase analysis. Working in priority order for maximum impact.

---

## 1. Link Styling (CRE-66) - IN PROGRESS

**Goal:** Rich interface labels and link styling  
**Estimate:** 1-2 hours  
**Status:** Starting now  

### Changes Required

#### A. Backend API Enhancement
**File:** `backend/src/routes/labs.py`  
**Add:** Link/interface metadata storage

```python
# Extend topology response to include interface styling
{
  "links": [
    {
      "id": 1,
      "src_node_id": 5,
      "dst_node_id": 9,
      "src_interface": "1/1/1",
      "dst_interface": "1/1/1",
      "color": "rgba(255, 128, 0, 1)",  # NEW
      "style": "Dashed",                 # NEW: Solid|Dashed
      "linkstyle": "Flowchart",          # NEW: Straight|Bezier|Flowchart
      "label": "DC1 - 5Gbps",            # NEW
      "labelpos": 0.5,                   # NEW: 0.0-1.0
      "width": 2                         # NEW: line thickness
    }
  ]
}
```

#### B. Frontend Data Model
**File:** `frontend/src/pages/LabCanvas.jsx`  
**Update:** Line 145-148 link mapping

```javascript
setLinks(topo.links.map(l => ({
  id: l.id,
  srcId: l.src_node_id,
  dstId: l.dst_node_id,
  srcIface: l.src_interface || 'GigabitEthernet0/0',
  dstIface: l.dst_interface || 'eth0',
  style: l.style || 'solid',           // NEW
  color: l.color || null,               // NEW
  linkstyle: l.linkstyle || 'straight', // NEW
  label: l.label || '',                 // NEW
  labelpos: l.labelpos || 0.5,          // NEW
  width: l.width || 1.5                 // NEW
})))
```

#### C. SVG Rendering Enhancement
**File:** `frontend/src/pages/LabCanvas.jsx`  
**Update:** Lines 460-491 link rendering

**Features to Add:**
1. **Custom Colors:** Use `link.color` instead of fixed `lc`
2. **Line Styles:** Support solid/dashed with `stroke-dasharray`
3. **Link Paths:**
   - Straight: direct line (current)
   - Bezier: curved path with control points
   - Flowchart: orthogonal (90° angles)
4. **Custom Labels:** Render `link.label` at midpoint (in addition to interface names)
5. **Label Position:** Place at `link.labelpos` (0.0=start, 1.0=end)
6. **Width:** Use `link.width` for stroke thickness

#### D. Context Menu Enhancement
**Add:** Right-click link → Edit Styling modal
- Color picker
- Style dropdown (Solid, Dashed)
- Link path dropdown (Straight, Bezier, Flowchart)
- Custom label input
- Width slider (1-5px)

### Implementation Steps

1. ✅ Analyze EVE-NG lab file format
2. ✅ Document link properties from XML
3. ⏳ Update backend topology API response
4. ⏳ Update frontend data model
5. ⏳ Implement path generation (bezier, flowchart)
6. ⏳ Implement label rendering at custom position
7. ⏳ Add link styling context menu
8. ⏳ Test with Harold's SOS LAB topology

---

## 2. In-Canvas Modals (CRE-67)

**Goal:** Replace `prompt()` with in-canvas modals  
**Estimate:** 2 hours  
**Status:** QUEUED  

### Problem Files
- `frontend/src/components/TopBar.jsx` - Lines 12, 14 (New Lab prompt)
- `frontend/src/components/NodePanel.jsx` - Line 134 (window.open popup)

### Solution
Create reusable modal component:
```jsx
<Modal title="Create New Lab" visible={showModal} onClose={...}>
  <input placeholder="Lab Name" />
  <button>Create</button>
</Modal>
```

**Key Requirement:** z-index above canvas (>999), backdrop overlay, click-outside to close

---

## 3. Drawing Tools (CRE-64)

**Goal:** Rectangle/circle/text annotation tools  
**Estimate:** 3-4 hours  
**Status:** QUEUED  

### Features
1. **Toolbar:** Add drawing mode buttons (Rectangle, Circle, Text, Line)
2. **Draw Mode:** Click-drag to create shapes
3. **Properties:**
   - Stroke color picker
   - Fill color picker (with transparency)
   - Dashed border toggle
   - Resize handles
4. **Storage:** Base64-encoded HTML in lab file (EVE-NG format)
5. **API:** `/api/labs/{id}/textobjects` CRUD operations

---

## 4. Network Visibility (CRE-65)

**Goal:** Render network objects when visibility=1  
**Estimate:** 2-3 hours  
**Status:** QUEUED  

### Changes
1. **Network Model:** Add `visibility` boolean property
2. **Rendering:** Show cloud icon + label when visible
3. **Context Menu:** Right-click network → Toggle Visibility
4. **Icon:** Use network `icon` property (lan.png, cloud.png)

---

## 5. Traffic Filter (CRE-68)

**Goal:** Real-time protocol visualization  
**Estimate:** 8-12+ hours  
**Status:** BLOCKED - awaiting user input  

### Open Questions
1. WHERE in EVE-NG GUI is this accessed?
2. WHAT does it look like visually?
3. HOW does it work? (Real-time? Post-capture?)
4. WHICH protocols are shown?

---

## Testing Plan

### CRE-66 Test Cases
1. Create link with custom label "DC1 - 5Gbps"
2. Set link color to orange (rgba(255, 128, 0, 1))
3. Change style to Dashed
4. Change path to Flowchart (orthogonal)
5. Verify label position at 0.5 (midpoint)
6. Export lab → verify styling preserved

### Integration Test
1. Import Harold's SOS LAB.unl
2. Verify all link colors render correctly
3. Verify all link labels display
4. Verify all link styles (solid/dashed) render
5. Verify all link paths (straight/bezier/flowchart) render

---

## Progress Tracking

### CRE-66: Link Styling
- [x] Analysis complete
- [ ] Backend API updated
- [ ] Frontend data model updated
- [ ] Path generation implemented
- [ ] Label rendering implemented
- [ ] Context menu added
- [ ] Testing complete

### CRE-67: Modals
- [ ] Modal component created
- [ ] TopBar.jsx updated
- [ ] NodePanel.jsx updated
- [ ] Testing complete

### CRE-64: Drawing Tools
- [ ] Toolbar UI created
- [ ] Rectangle tool implemented
- [ ] Circle tool implemented
- [ ] Text tool implemented
- [ ] Properties panel created
- [ ] API integration complete
- [ ] Testing complete

### CRE-65: Network Visibility
- [ ] Data model updated
- [ ] Rendering logic implemented
- [ ] Context menu added
- [ ] Testing complete

---

## Commit Strategy

**Per-Feature Commits:**
1. `CRE-66: Add link color/style/label support`
2. `CRE-67: Replace prompts with in-canvas modals`
3. `CRE-64: Implement drawing tools (rectangles, circles, text)`
4. `CRE-65: Add network visibility toggle`

**Each commit MUST include:**
1. Code changes
2. Updated relevant docs (this file, README)
3. Linear comment with verification numbers

---

## Current Status

**Active:** CRE-66 Link Styling  
**Next:** Implementation of path generation functions  
**Blocked:** CRE-68 (traffic filter) awaiting user clarification  
