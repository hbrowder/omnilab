# CRE-71: Container Boxes - Phased Implementation Plan

**Created:** 2026-05-27  
**Status:** Ready to Start  
**Linear:** https://linear.app/harold-browder/issue/CRE-71/canvas-visual-hierarchy-eve-ng-parity  
**Strategy:** Incremental UI Enhancement (A→B→C→D)

---

## Strategic Context

**Why Now:**
- EVE-NG 7 in testing with "new look" and visual refresh
- Container boxes are the #1 visual hierarchy tool for professional diagrams
- Interface labels ✅ and network objects ✅ already done
- This completes our EVE-NG UI parity

**User Need:**
- Group nodes visually (datacenters, PODs, network layers)
- Self-documenting topologies with labeled regions
- Professional presentation for documentation/training

---

## Phase A: Foundation (Basic Container Rendering)

**Goal:** Get dashed rectangles on canvas with labels

### Backend (30 min)

**1. Database Migration**
```sql
-- File: backend/migrations/add_containers_table.sql
CREATE TABLE IF NOT EXISTS containers (
    id TEXT PRIMARY KEY,
    lab_id INTEGER NOT NULL,
    x REAL NOT NULL,
    y REAL NOT NULL,
    width REAL NOT NULL,
    height REAL NOT NULL,
    label TEXT NOT NULL DEFAULT 'Container',
    stroke_color TEXT DEFAULT '#94a3b8',
    stroke_style TEXT DEFAULT 'dashed',
    stroke_width REAL DEFAULT 2,
    fill_color TEXT DEFAULT 'transparent',
    z_index INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lab_id) REFERENCES labs(id) ON DELETE CASCADE
);
```

**2. API Routes** (`backend/routes/topology.py`)
```python
@router.get("/labs/{lab_id}/containers")
async def get_containers(lab_id: int, db: AsyncSession = Depends(get_db)):
    """Get all containers for a lab"""
    result = await db.execute(
        select(Container).where(Container.lab_id == lab_id)
    )
    return result.scalars().all()

@router.post("/labs/{lab_id}/containers")
async def create_container(lab_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    """Create a new container"""
    container = Container(
        id=f"cont-{uuid.uuid4()}",
        lab_id=lab_id,
        **data
    )
    db.add(container)
    await db.commit()
    await db.refresh(container)
    return container

@router.put("/labs/{lab_id}/containers/{container_id}")
async def update_container(lab_id: int, container_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Update container position, size, or label"""
    result = await db.execute(
        select(Container).where(
            Container.id == container_id,
            Container.lab_id == lab_id
        )
    )
    container = result.scalar_one_or_none()
    if not container:
        raise HTTPException(404, "Container not found")
    
    for key, value in data.items():
        setattr(container, key, value)
    
    await db.commit()
    await db.refresh(container)
    return container

@router.delete("/labs/{lab_id}/containers/{container_id}")
async def delete_container(lab_id: int, container_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a container"""
    result = await db.execute(
        select(Container).where(
            Container.id == container_id,
            Container.lab_id == lab_id
        )
    )
    container = result.scalar_one_or_none()
    if not container:
        raise HTTPException(404, "Container not found")
    
    await db.delete(container)
    await db.commit()
    return {"success": True}
```

**3. Database Model** (`backend/models/topology.py`)
```python
class Container(Base):
    __tablename__ = "containers"
    
    id = Column(String, primary_key=True)
    lab_id = Column(Integer, ForeignKey("labs.id", ondelete="CASCADE"), nullable=False)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    width = Column(Float, nullable=False)
    height = Column(Float, nullable=False)
    label = Column(String, nullable=False, default="Container")
    stroke_color = Column(String, default="#94a3b8")
    stroke_style = Column(String, default="dashed")
    stroke_width = Column(Float, default=2)
    fill_color = Column(String, default="transparent")
    z_index = Column(Integer, default=0)
    created_at = Column(String, default=datetime.utcnow)
    
    lab = relationship("Lab", back_populates="containers")
```

### Frontend (45 min)

**4. State Management** (`LabCanvas.jsx` line ~95)
```javascript
const [containers, setContainers] = useState([])
```

**5. Load Containers** (in useEffect after loading lab)
```javascript
// Fetch containers
const contRes = await axios.get(`${API_URL}/labs/${labId}/containers`)
setContainers(contRes.data)
```

**6. Render Containers** (BEFORE nodes rendering, ~line 600)
```javascript
{/* Containers - rendered first so they appear behind nodes */}
{containers
  .sort((a, b) => a.z_index - b.z_index)
  .map(cont => (
    <g key={cont.id}>
      {/* Main container rectangle */}
      <rect
        x={cont.x}
        y={cont.y}
        width={cont.width}
        height={cont.height}
        fill={cont.fill_color}
        stroke={cont.stroke_color}
        strokeWidth={cont.stroke_width}
        strokeDasharray={
          cont.stroke_style === 'dashed' ? '8,4' :
          cont.stroke_style === 'dotted' ? '2,2' : '0'
        }
        style={{cursor: 'move'}}
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
    </g>
  ))}
```

**7. Create Container via Console** (for testing)
```javascript
// In browser console:
await fetch('http://192.168.174.132:5000/api/labs/1/containers', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    x: 100,
    y: 100,
    width: 400,
    height: 300,
    label: 'Alpharetta DC1'
  })
})
```

### Verification Criteria ✅

- [ ] Database table exists (check with `sqlite3 omnilab.db ".schema containers"`)
- [ ] API endpoints return 200 (test with curl)
- [ ] Container appears on canvas as dashed rectangle
- [ ] Label appears above rectangle
- [ ] Multiple containers render correctly
- [ ] Dark mode styling works (label color, stroke visibility)

### Estimated Time: 1.5 hours

---

## Phase B: Drag & Move (Interactive Positioning)

**Goal:** Containers can be dragged around canvas

### Implementation (30 min)

**1. Add Drag Handler** (LabCanvas.jsx)
```javascript
// In rect onMouseDown
onMouseDown={e => {
  e.stopPropagation()
  startDrag(e, 'container', cont.id, cont.x, cont.y)
}}
```

**2. Update onMove Handler** (existing drag logic)
```javascript
// In onMove function, add case for containers
if (d.kind === 'container') {
  setContainers(p => p.map(ct =>
    ct.id === d.id ? {...ct, x: nx, y: ny} : ct
  ))
}
```

**3. Update onMouseUp Handler** (save to backend)
```javascript
// In onMouseUp, after node/network cases
if (d.kind === 'container') {
  const cont = containers.find(c => c.id === d.id)
  if (cont) {
    await axios.put(
      `${API_URL}/labs/${labId}/containers/${cont.id}`,
      {x: cont.x, y: cont.y}
    )
  }
}
```

### Verification Criteria ✅

- [ ] Container can be dragged with mouse
- [ ] Position updates visually in real-time
- [ ] Position persists after page reload
- [ ] Nodes inside containers don't move with container (independent positioning)
- [ ] Dragging is smooth (no jank)

### Estimated Time: 30 min

---

## Phase C: Resize & Polish (Professional Interaction)

**Goal:** Resize handles, selection states, hover feedback

### Implementation (1 hour)

**1. Selection State**
```javascript
// Add containers to selection system (existing selected Set)
const isSelected = selected.has(cont.id)
const isHovered = hoveredId === cont.id

// Update stroke when selected/hovered
stroke={isSelected ? '#3b82f6' : isHovered ? '#60a5fa' : cont.stroke_color}
strokeWidth={isSelected ? 3 : cont.stroke_width}
```

**2. Resize Handles** (when selected)
```javascript
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
```

**3. Resize Logic**
```javascript
function startResize(e, containerId, handle) {
  e.stopPropagation()
  setDrag({
    kind: 'container',
    id: containerId,
    resizeHandle: handle,
    ox: e.clientX,
    oy: e.clientY
  })
}

// In onMove, add resize case
if (d.kind === 'container' && d.resizeHandle) {
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
}
```

### Verification Criteria ✅

- [ ] Click container → blue highlight border appears
- [ ] Blue resize handles appear at corners when selected
- [ ] Drag bottom-right handle → width/height increase
- [ ] Drag top-left handle → x/y/width/height adjust
- [ ] Minimum size enforced (100x80)
- [ ] Hover → lighter blue color
- [ ] Resize persists to backend

### Estimated Time: 1 hour

---

## Phase D: Context Menu & Drawing Tool (Production Ready)

**Goal:** Create/edit/delete containers via UI

### Implementation (1.5 hours)

**1. Context Menu Options** (LabCanvas.jsx)
```javascript
onContextMenu={e => {
  e.preventDefault()
  setContextMenu({
    x: e.clientX,
    y: e.clientY,
    target: {type: 'container', id: cont.id}
  })
}}

// Add container menu options
if (contextMenu.target.type === 'container') {
  const cont = containers.find(c => c.id === contextMenu.target.id)
  options = [
    {label: 'Edit Label', action: () => editContainerLabel(cont)},
    {label: 'Change Style', action: () => changeContainerStyle(cont)},
    {label: 'Change Color', action: () => changeContainerColor(cont)},
    {label: 'Send to Back', action: () => changeContainerZIndex(cont, 'back')},
    {label: 'Bring to Front', action: () => changeContainerZIndex(cont, 'front')},
    {label: 'Delete Container', action: () => deleteContainer(cont.id)}
  ]
}
```

**2. Drawing Tool Integration**
```javascript
// Add to DrawingToolbar.jsx
<button
  onClick={() => setDrawingTool('container')}
  className={drawingTool === 'container' ? 'active' : ''}
  title="Draw Container (Shift+C)"
>
  📦 Container
</button>

// In LabCanvas, handle container drawing mode
if (drawingTool === 'container' && isDrawing) {
  // Show preview rectangle while dragging
  const width = Math.abs(c.x - drawStart.x)
  const height = Math.abs(c.y - drawStart.y)
  const x = Math.min(c.x, drawStart.x)
  const y = Math.min(c.y, drawStart.y)
  
  return (
    <rect
      x={x}
      y={y}
      width={width}
      height={height}
      fill="rgba(148,163,184,0.1)"
      stroke="#94a3b8"
      strokeWidth={2}
      strokeDasharray="8,4"
    />
  )
}

// On mouse up, create container
if (drawingTool === 'container') {
  const label = prompt('Container label:', 'Container')
  if (!label) return
  
  await axios.post(`${API_URL}/labs/${labId}/containers`, {
    x, y, width, height, label
  })
  
  // Refresh containers
  const res = await axios.get(`${API_URL}/labs/${labId}/containers`)
  setContainers(res.data)
}
```

**3. Keyboard Shortcuts**
```javascript
// In useEffect keyboard handler
case 'C':
  if (e.shiftKey) {
    setDrawingTool(drawingTool === 'container' ? null : 'container')
  }
  break
```

### Verification Criteria ✅

- [ ] Shift+C activates container drawing mode
- [ ] Click-drag draws preview rectangle
- [ ] Release prompts for label
- [ ] Container appears on canvas
- [ ] Right-click → context menu with 6 options
- [ ] Edit label → prompt updates label
- [ ] Change style cycles solid/dashed/dotted
- [ ] Change color shows palette or cycles presets
- [ ] Send to back/front adjusts z-index
- [ ] Delete removes from canvas and DB
- [ ] All actions persist to backend

### Estimated Time: 1.5 hours

---

## Total Estimated Time: 4.5 hours

**Phase A:** 1.5 hours (foundation)  
**Phase B:** 0.5 hours (drag/move)  
**Phase C:** 1.0 hours (resize/polish)  
**Phase D:** 1.5 hours (creation/editing)

---

## Success Criteria (Final)

**Functional:**
- ✅ Create containers via drawing tool (Shift+C)
- ✅ Drag containers to reposition
- ✅ Resize containers via corner handles
- ✅ Edit labels via context menu
- ✅ Change visual style (solid/dashed/dotted)
- ✅ Change colors
- ✅ Adjust z-order (front/back)
- ✅ Delete containers
- ✅ All changes persist to database

**Visual:**
- ✅ Containers render behind nodes (z-index < nodes)
- ✅ Labels positioned outside box (top-left)
- ✅ Selection state (blue highlight + handles)
- ✅ Hover state (lighter blue)
- ✅ Dark mode support
- ✅ Professional appearance (matches EVE-NG quality)

**UX:**
- ✅ Smooth drag interaction (no jank)
- ✅ Intuitive resize handles
- ✅ Context menu discoverability
- ✅ Keyboard shortcut (Shift+C)
- ✅ Clear visual feedback for all states

---

## Commit Strategy

Each phase gets its own commit:

**Phase A:**
```
feat(canvas): container boxes foundation (CRE-71 Phase A)

- Add containers table and API endpoints
- Render dashed rectangles with labels
- Basic data model and state management

Verification: containers appear on canvas with labels
```

**Phase B:**
```
feat(canvas): container drag and move (CRE-71 Phase B)

- Implement drag handlers for containers
- Position updates persist to backend
- Smooth real-time positioning

Verification: containers can be dragged and persist position
```

**Phase C:**
```
feat(canvas): container resize and selection polish (CRE-71 Phase C)

- Corner resize handles when selected
- Selection and hover states
- Blue highlight borders
- Minimum size constraints

Verification: professional resize interaction with visual feedback
```

**Phase D:**
```
feat(canvas): container creation and context menu (CRE-71 Phase D)

- Drawing tool integration (Shift+C)
- Context menu (edit, style, color, z-order, delete)
- Keyboard shortcuts
- Complete CRUD operations

Verification: full container lifecycle via UI

CLOSES CRE-71 - Canvas visual hierarchy EVE-NG parity complete
```

---

## Documentation Updates (Phase D)

**README.md:**
```markdown
### Canvas Features

- **Container Boxes**: Draw labeled rectangles to organize topology regions
  - Press `Shift+C` to activate drawing tool
  - Click-drag to define area, enter label
  - Right-click for styling options (solid/dashed/dotted borders)
  - Drag to reposition, resize via corner handles
  - Send to back/front to adjust layering
```

**Linear Comment:**
```
CRE-71 COMPLETE ✅

Container boxes shipped with full EVE-NG parity:

FEATURES:
- Drawing tool (Shift+C): click-drag to create
- Drag to reposition containers independently
- Resize via corner handles (NW and SE)
- Context menu: edit label, style, color, z-order, delete
- Selection states: blue highlight + handles
- Hover states: lighter blue feedback
- Dark mode support

TECHNICAL:
- Backend: containers table + 4 API endpoints (GET/POST/PUT/DELETE)
- Frontend: 250 lines across LabCanvas.jsx + DrawingToolbar.jsx
- Z-index layering: containers render behind nodes
- Persistent state: all changes saved to SQLite

VERIFICATION:
- ✅ Create via Shift+C drawing tool
- ✅ Drag and resize smoothly
- ✅ Context menu with 6 options
- ✅ All CRUD operations via UI
- ✅ Professional visual polish

COMPETITIVE STATUS:
- EVE-NG parity ACHIEVED
- Interface labels ✅ (already done)
- Network objects ✅ (already done)  
- Container boxes ✅ (NEW)

Ready for production testing with complex topologies.

Commits: [SHA-A], [SHA-B], [SHA-C], [SHA-D]
```

---

**Ready to begin Phase A?**
