# CRE-71: Canvas Visual Hierarchy Implementation Plan

**Created:** 2026-05-27  
**Status:** In Progress  
**Linear:** https://linear.app/harold-browder/issue/CRE-71/canvas-visual-hierarchy-eve-ng-parity

---

## Current State Analysis

After inspecting LabCanvas.jsx, **2 of 3 critical features are already complete**:

### ✅ ALREADY DONE
1. **Interface labels on links** (lines 628-647)
   - Source interface shown near source node
   - Destination interface shown near destination node
   - Abbreviated labels (Gi0/0, Fa0/1, eth0)
   - Rotated to align with link angle
   
2. **Network objects visible on canvas** (lines 702-772)
   - Cloud icons for NAT/Internet type
   - Line topology for internal networks
   - Bridge/Switch icons for bridge type
   - Always-visible labels
   - Connection count badges
   - Size scaling based on connections
   - Draggable and connectable

### ❌ CRITICAL MISSING FEATURE
**Container boxes** (dashed rectangles for grouping) — This is the #1 visual hierarchy tool Harold needs.

---

## Implementation: Container Boxes

### User Stories
- As a network engineer, I want to draw dashed rectangles around groups of nodes so I can visually organize datacenters, PODs, and network layers
- As a lab designer, I want to label these containers (e.g., "Alpharetta DC1", "Core Layer") so complex topologies are self-documenting
- As a user, I want to resize and move containers independently of the nodes inside them

### Data Model

Add to state (line 95):
```javascript
const [containers, setContainers] = useState([])
```

Container structure:
```javascript
{
  id: 'cont-UUID',
  x: 100,              // Top-left X
  y: 100,              // Top-left Y
  width: 400,          // Box width
  height: 300,         // Box height
  label: 'Alpharetta DC1',
  strokeColor: '#94a3b8',     // Border color
  strokeStyle: 'dashed',       // 'solid', 'dashed', 'dotted'
  strokeWidth: 2,
  fillColor: 'transparent',    // or rgba with opacity
  zIndex: 0            // Render order (lower = behind)
}
```

### Backend API

New endpoints needed in `backend/routes/topology.py`:

```python
@router.get("/labs/{lab_id}/containers")
async def get_containers(lab_id: int):
    """Get all containers for a lab"""
    pass

@router.post("/labs/{lab_id}/containers")
async def create_container(lab_id: int, data: dict):
    """Create a new container"""
    pass

@router.put("/labs/{lab_id}/containers/{container_id}")
async def update_container(lab_id: int, container_id: str, data: dict):
    """Update container position, size, or label"""
    pass

@router.delete("/labs/{lab_id}/containers/{container_id}")
async def delete_container(lab_id: int, container_id: str):
    """Delete a container"""
    pass
```

Database schema (new table):
```sql
CREATE TABLE containers (
    id TEXT PRIMARY KEY,
    lab_id INTEGER NOT NULL,
    x REAL NOT NULL,
    y REAL NOT NULL,
    width REAL NOT NULL,
    height REAL NOT NULL,
    label TEXT NOT NULL,
    stroke_color TEXT DEFAULT '#94a3b8',
    stroke_style TEXT DEFAULT 'dashed',
    stroke_width REAL DEFAULT 2,
    fill_color TEXT DEFAULT 'transparent',
    z_index INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lab_id) REFERENCES labs(id) ON DELETE CASCADE
);
```

### Frontend Rendering

Render containers BEFORE nodes (so they appear as background):

```javascript
{/* Containers - rendered first so they appear behind nodes */}
{containers
  .sort((a, b) => a.zIndex - b.zIndex)
  .map(cont => {
    const isSelected = selected.has(cont.id)
    const isHovered = hoveredId === cont.id
    
    return (
      <g key={cont.id}>
        {/* Main container rectangle */}
        <rect
          x={cont.x}
          y={cont.y}
          width={cont.width}
          height={cont.height}
          fill={cont.fillColor}
          stroke={isSelected ? '#3b82f6' : isHovered ? '#60a5fa' : cont.strokeColor}
          strokeWidth={isSelected ? 3 : cont.strokeWidth}
          strokeDasharray={
            cont.strokeStyle === 'dashed' ? '8,4' :
            cont.strokeStyle === 'dotted' ? '2,2' : '0'
          }
          style={{cursor: 'move'}}
          onMouseDown={e => startDrag(e, 'container', cont.id, cont.x, cont.y)}
          onContextMenu={e => onContainerRightClick(e, cont)}
        />
        
        {/* Label - positioned at top-left outside the box */}
        <text
          x={cont.x + 10}
          y={cont.y - 8}
          fill={tc}
          fontSize={13}
          fontWeight={600}
          fontFamily="sans-serif"
          style={{pointerEvents: 'none'}}
        >
          {cont.label}
        </text>
        
        {/* Resize handles (when selected) */}
        {isSelected && (
          <>
            {/* Bottom-right resize handle */}
            <rect
              x={cont.x + cont.width - 8}
              y={cont.y + cont.height - 8}
              width={16}
              height={16}
              fill="#3b82f6"
              stroke={bg}
              strokeWidth={2}
              style={{cursor: 'nwse-resize'}}
              onMouseDown={e => startResize(e, cont.id, 'se')}
            />
            {/* Top-left resize handle */}
            <rect
              x={cont.x - 8}
              y={cont.y - 8}
              width={16}
              height={16}
              fill="#3b82f6"
              stroke={bg}
              strokeWidth={2}
              style={{cursor: 'nwse-resize'}}
              onMouseDown={e => startResize(e, cont.id, 'nw')}
            />
          </>
        )}
      </g>
    )
  })}
```

### Drag & Resize Logic

Add to drag handlers (lines 193-280):

```javascript
// In onMove handler
if (d.kind === 'container') {
  if (d.resizeHandle) {
    // Resize mode
    const cont = containers.find(c => c.id === d.id)
    if (!cont) return
    
    if (d.resizeHandle === 'se') {
      // Bottom-right: adjust width and height
      const newWidth = Math.max(100, c.x - cont.x)
      const newHeight = Math.max(80, c.y - cont.y)
      setContainers(p => p.map(ct =>
        ct.id === cont.id ? {...ct, width: newWidth, height: newHeight} : ct
      ))
    } else if (d.resizeHandle === 'nw') {
      // Top-left: adjust x, y, width, height
      const deltaX = c.x - cont.x
      const deltaY = c.y - cont.y
      const newWidth = Math.max(100, cont.width - deltaX)
      const newHeight = Math.max(80, cont.height - deltaY)
      setContainers(p => p.map(ct =>
        ct.id === cont.id ? {
          ...ct,
          x: cont.x + deltaX,
          y: cont.y + deltaY,
          width: newWidth,
          height: newHeight
        } : ct
      ))
    }
  } else {
    // Move mode
    setContainers(p => p.map(ct =>
      ct.id === d.id ? {...ct, x: nx, y: ny} : ct
    ))
  }
}
```

### Context Menu Actions

Add container options:
- **Edit Label** - prompt() to change text
- **Change Style** - toggle between solid/dashed/dotted
- **Change Color** - color picker or preset palette
- **Send to Back** - set zIndex = min(all zIndex) - 1
- **Bring to Front** - set zIndex = max(all zIndex) + 1
- **Delete Container** - remove from state and DB

### Drawing Toolbar Integration

Add "Container" tool to DrawingToolbar (CRE-64):
- Click Container button
- Click-drag to define box area
- Prompt for label on release
- Create container at that position/size

---

## Phase 1 Tasks (Container MVP)

### Task 1: Backend Database & API
- [ ] Create `containers` table in SQLite schema
- [ ] Add migration script if needed
- [ ] Implement GET /labs/{id}/containers
- [ ] Implement POST /labs/{id}/containers  
- [ ] Implement PUT /labs/{id}/containers/{id}
- [ ] Implement DELETE /labs/{id}/containers/{id}
- [ ] Test with curl/Postman

### Task 2: Frontend State & API Client
- [ ] Add `getContainers`, `createContainer`, `updateContainer`, `deleteContainer` to `utils/api.js`
- [ ] Add `containers` state to LabCanvas
- [ ] Load containers on mount (useEffect alongside nodes/links)
- [ ] Wire up drag/resize refs

### Task 3: Rendering & Selection
- [ ] Render containers before nodes in SVG
- [ ] Implement selection (click adds to selected Set)
- [ ] Implement hover state
- [ ] Show resize handles when selected
- [ ] Z-index sorting (render order)

### Task 4: Drag & Resize
- [ ] Add 'container' case to startDrag
- [ ] Add 'container' move logic to onMove
- [ ] Implement startResize handler
- [ ] Implement resize logic in onMove
- [ ] Persist position/size changes to backend on mouseup

### Task 5: Creation & Editing
- [ ] Add "Container" button to DrawingToolbar
- [ ] Implement click-drag to create container
- [ ] Prompt for label on creation
- [ ] Context menu: Edit Label, Change Style, Change Color, Delete
- [ ] Right-click canvas → "Add Container Here"

### Task 6: Visual Polish
- [ ] Dashed border styling (8,4 dasharray)
- [ ] Label positioning (top-left, outside box)
- [ ] Selection highlight (blue border)
- [ ] Hover preview (subtle highlight)
- [ ] Dark mode color adjustments

---

## Phase 2: Advanced Features (Post-MVP)

### Snap-to-Grid
- Toggle in toolbar (already has grid defined)
- Round container x/y/width/height to nearest GRID_SIZE (20px)

### Align/Distribute Tools
- Right-click multiple selected containers → Align Left/Right/Top/Bottom
- Distribute Horizontally/Vertically with even spacing

### Template Containers
- Preset sizes for common layouts:
  - Datacenter (800x600)
  - POD (400x300)
  - Layer (600x200)
- Preset color schemes (datacenter blue, security red, management green)

### Container Nesting
- Allow containers inside containers
- Render order based on parent-child relationships
- Move child containers when parent moves

### Auto-Layout
- "Fit to Contents" - resize container to wrap selected nodes with padding
- "Distribute Nodes in Container" - evenly space nodes within bounds

---

## Testing Checklist

- [ ] Create container via click-drag
- [ ] Move container (drag)
- [ ] Resize container (bottom-right handle)
- [ ] Resize container (top-left handle)
- [ ] Select container (click)
- [ ] Multi-select containers (Shift+click)
- [ ] Edit label via context menu
- [ ] Change stroke style (solid/dashed/dotted)
- [ ] Delete container
- [ ] Containers save/load correctly (refresh page)
- [ ] Containers render behind nodes
- [ ] Z-index Send to Back / Bring to Front
- [ ] Dark mode colors look good
- [ ] Selection highlight visible
- [ ] Hover state works

---

## Success Criteria

✅ **Must Have (Phase 1)**
1. Can create dashed rectangle containers
2. Can label containers
3. Can move and resize containers
4. Containers render behind nodes
5. Containers persist across page reloads
6. Can delete containers

✅ **Nice to Have (Phase 2)**
7. Snap-to-grid for clean alignment
8. Align/distribute tools
9. Preset templates (datacenter, POD, layer)
10. Container nesting

---

## References

- EVE-NG comparison: `docs/EVE-NG_VS_OMNILAB_UI_COMPARISON.md`
- Existing drawing tools: `frontend/src/components/DrawingToolbar.jsx` (CRE-64)
- Existing text objects: LabCanvas.jsx lines 816-845 (drag/context menu pattern)
- Network objects: LabCanvas.jsx lines 702-772 (similar drag/select logic)

---

## Next Steps

1. Start with Task 1 (Backend) - database schema and API endpoints
2. Then Task 2 (Frontend API client)
3. Then Task 3-6 in order
4. Test thoroughly with Harold's EVE-NG screenshot as reference
5. Get feedback on Phase 1 MVP before implementing Phase 2 features
