# CRE-68 Phase 3: Live Traffic Animation & WebSocket Integration

**Date:** 2026-05-25  
**Engineer:** Kit (007)  
**Status:** PLANNING → EXECUTION  
**Prerequisite:** Phase 2 complete ✅ (commit 5c543ca + e1ae8a0)

---

## Overview

Phase 3 brings the traffic visualization to life! We'll integrate:
1. **WebSocket real-time communication** (backend → frontend)
2. **Packet capture integration** (reuse existing `packet_capture.py` from CRE-57)
3. **Animated SVG flows** on canvas links
4. **Real-time packet counters** in the TrafficFilterPanel

**Goal:** When Harold toggles a filter ON, animated colored dots flow along the links where that protocol is detected.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                          │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │ TrafficFilter    │         │ LinkAnimation    │          │
│  │ Panel            │◄────────┤ Engine           │          │
│  │                  │         │                  │          │
│  │ - Toggle filter  │         │ - SVG particles  │          │
│  │ - Show counter   │         │ - Glow effects   │          │
│  └────────┬─────────┘         └────────┬─────────┘          │
│           │                            │                     │
│           └──────────WebSocket─────────┘                     │
│                        ▲                                     │
└────────────────────────┼─────────────────────────────────────┘
                         │
┌────────────────────────┼─────────────────────────────────────┐
│                  BACKEND (FastAPI)                           │
│                        │                                     │
│  ┌─────────────────────┴──────────────────────┐             │
│  │  WebSocket Manager                         │             │
│  │  - /api/labs/{lab_id}/traffic-ws           │             │
│  │  - Broadcast filter events                 │             │
│  │  - Connection pool                         │             │
│  └─────────────┬──────────────────────────────┘             │
│                │                                             │
│  ┌─────────────▼──────────────────────────────┐             │
│  │  Traffic Filter Service (NEW)              │             │
│  │  - Manage active filters                   │             │
│  │  - Start/stop packet capture per filter    │             │
│  │  - Parse tcpdump output → events           │             │
│  │  - Emit to WebSocket                       │             │
│  └─────────────┬──────────────────────────────┘             │
│                │                                             │
│  ┌─────────────▼──────────────────────────────┐             │
│  │  Packet Capture Service (CRE-57 EXISTING)  │             │
│  │  - backend/services/packet_capture.py      │             │
│  │  - tcpdump process management              │             │
│  │  - BPF filtering                           │             │
│  └────────────────────────────────────────────┘             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## What We're Building

### Backend Components

#### 1. **WebSocket Endpoint** (NEW)
**File:** `backend/api/traffic_websocket.py`

```python
@router.websocket("/labs/{lab_id}/traffic-ws")
async def traffic_websocket(websocket: WebSocket, lab_id: str):
    """
    Real-time traffic events for a lab.
    
    Events sent to client:
    - filter_activated: {filter_id, name, color}
    - filter_deactivated: {filter_id}
    - traffic_match: {filter_id, link_id, timestamp, packet_summary}
    - packet_count_update: {filter_id, count}
    """
```

#### 2. **Traffic Filter Service** (NEW)
**File:** `backend/services/traffic_service.py`

Responsibilities:
- Start packet capture when filter enabled
- Parse tcpdump output in real-time
- Map packets to links (using interface → link mapping)
- Emit events via WebSocket
- Manage filter lifecycle (activate/deactivate)

Key functions:
```python
async def activate_filter(lab_id: str, filter_id: int, db: Session)
async def deactivate_filter(lab_id: str, filter_id: int, db: Session)
async def process_tcpdump_output(capture_id: str, filter_id: int, lab_id: str)
```

#### 3. **Link-to-Interface Mapping**
**Challenge:** tcpdump captures on interfaces (e.g., `veth-node1-eth0`), but frontend needs link_id.

**Solution:** Query lab topology to build mapping:
- Each link connects two nodes
- Each node has interfaces
- Map interface names → link_id

**File:** `backend/services/topology_mapper.py` (NEW or extend existing)

```python
def get_link_for_interface(lab_id: str, interface: str) -> Optional[str]:
    """Return link_id for a given interface name."""
```

### Frontend Components

#### 1. **WebSocket Hook** (NEW)
**File:** `frontend/src/hooks/useTrafficWebSocket.js`

```javascript
export const useTrafficWebSocket = (labId) => {
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:5000/api/labs/${labId}/traffic-ws`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleTrafficEvent(data);
    };
    
    return () => ws.close();
  }, [labId]);
  
  return { events, connected };
};
```

#### 2. **LinkAnimationEngine Component** (NEW)
**File:** `frontend/src/components/LinkAnimationEngine.jsx`

Responsibilities:
- Listen to WebSocket events
- Render SVG particles (dots) on links
- Animate particles along link path
- Apply filter color to particles
- Fade out after animation_duration
- Add link glow effect when active

**Props:**
- `links`: Array of link objects from canvas
- `trafficEvents`: Stream from WebSocket
- `activeFilters`: Map of filter_id → {color, duration}

**Rendering:**
For each active traffic event:
1. Find the link SVG element by link_id
2. Create an SVG `<circle>` (particle)
3. Animate along the path using CSS transform or `<animateMotion>`
4. Remove after duration expires

Example SVG structure:
```jsx
{links.map(link => (
  <g key={link.id} className={activeTraffic[link.id] ? 'link-active' : ''}>
    {/* Existing link path */}
    <path d={link.path} className="link-path" />
    
    {/* Traffic particles */}
    {trafficParticles[link.id]?.map(particle => (
      <circle
        key={particle.id}
        r="4"
        fill={particle.color}
        className="traffic-particle"
      >
        <animateMotion
          dur={`${particle.duration}ms`}
          path={link.path}
          repeatCount="1"
        />
      </circle>
    ))}
  </g>
))}
```

#### 3. **TrafficFilterPanel Updates** (MODIFY EXISTING)
**File:** `frontend/src/components/TrafficFilterPanel.jsx`

Changes:
- Connect to WebSocket
- Show real-time packet counters
- Send enable/disable events to backend (via REST API)
- Display connection status indicator

Add to each filter item:
```jsx
<div className="filter-stats">
  <span className="packet-count">{filter.packet_count} packets</span>
  <span className={`status ${filter.is_active ? 'active' : 'inactive'}`}>
    {filter.is_active ? '● Live' : '○ Inactive'}
  </span>
</div>
```

---

## Implementation Tasks

### Milestone 1: WebSocket Foundation (2-3 hours)

**Backend:**
- [ ] Create `backend/api/traffic_websocket.py`
- [ ] Implement WebSocket endpoint with connection manager
- [ ] Add heartbeat/ping mechanism
- [ ] Test with dummy events (manual send from Python console)

**Frontend:**
- [ ] Create `useTrafficWebSocket` hook
- [ ] Add WebSocket connection to LabCanvas
- [ ] Display connection status (green dot = connected)
- [ ] Console.log incoming events for verification

**Verification:**
```bash
# Terminal 1: Start backend
cd ~/omnilab/backend && python -m uvicorn main:app --reload --port 5000

# Terminal 2: Test WebSocket with websocat
websocat ws://localhost:5000/api/labs/test-lab-123/traffic-ws

# Should see: connection accepted, events flow
```

---

### Milestone 2: Packet Capture Integration (3-4 hours)

**Backend:**
- [ ] Create `backend/services/traffic_service.py`
- [ ] Implement `activate_filter()` - start tcpdump via packet_capture service
- [ ] Implement `deactivate_filter()` - stop tcpdump
- [ ] Parse tcpdump real-time output (line-by-line)
- [ ] Emit `traffic_match` events via WebSocket

**Topology Mapping:**
- [ ] Build interface → link_id mapping from lab topology
- [ ] Handle multi-interface links (broadcast to all)
- [ ] Mock interface mapping for testing (test-lab-123)

**API Updates:**
- [ ] PATCH `/api/labs/{lab_id}/filters/{id}` → call traffic_service.activate/deactivate
- [ ] Add `is_active` field updates to database

**Verification:**
```bash
# Enable ICMP filter → should see tcpdump start
curl -X PATCH http://localhost:5000/api/labs/test-lab-123/filters/1 \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'

# Check process
ps aux | grep tcpdump

# Disable filter → should see tcpdump stop
curl -X PATCH http://localhost:5000/api/labs/test-lab-123/filters/1 \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

---

### Milestone 3: Frontend Animation (3-4 hours)

**Components:**
- [ ] Create `LinkAnimationEngine.jsx`
- [ ] Integrate into LabCanvas (render above links layer)
- [ ] Parse WebSocket `traffic_match` events
- [ ] Create SVG particles on correct link
- [ ] Animate particles along path (CSS or `<animateMotion>`)
- [ ] Remove particles after duration
- [ ] Add link glow effect (CSS filter or stroke-width increase)

**Styling:**
```css
.link-active {
  filter: drop-shadow(0 0 8px var(--filter-color));
  stroke-width: 3px;
}

.traffic-particle {
  filter: drop-shadow(0 0 4px currentColor);
  animation: pulse 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.2); }
}
```

**Verification:**
- Load lab in browser
- Enable filter in TrafficFilterPanel
- Generate traffic (ping, tcpreplay, or mock event from backend)
- Should see: animated colored dot flowing along link

---

### Milestone 4: Real-Time Counters & Polish (2 hours)

**TrafficFilterPanel Updates:**
- [ ] Display packet_count from WebSocket events
- [ ] Increment counter on each `traffic_match`
- [ ] Reset counter when filter disabled
- [ ] Show "● Live" status indicator when active

**Performance:**
- [ ] Throttle WebSocket events (max 10/sec per filter)
- [ ] Batch packet counts (send every 100ms, not per packet)
- [ ] Limit max particles on screen (remove oldest if > 50)

**Error Handling:**
- [ ] Handle WebSocket disconnection (show warning, auto-reconnect)
- [ ] Handle tcpdump permission errors (show helpful message)
- [ ] Handle invalid BPF expressions (validate on frontend)

---

## Testing Strategy

### Unit Tests
- `traffic_service.py`: activate/deactivate filter
- `topology_mapper.py`: interface → link_id mapping
- `traffic_websocket.py`: message serialization

### Integration Tests
- Enable filter → tcpdump starts → packet captured → event sent → frontend receives
- Disable filter → tcpdump stops → events cease
- Multiple filters active simultaneously → correct colors/links

### Manual QA
1. **Basic Flow:**
   - Open lab
   - Toggle ICMP filter ON
   - Ping between nodes
   - See animated green dots on links
   - Toggle filter OFF → animation stops

2. **Multi-Filter:**
   - Enable ICMP (green) + SSH (blue)
   - Generate both types of traffic
   - Verify correct colors on correct links

3. **Performance:**
   - Enable 5 filters
   - Generate heavy traffic (iperf, tcpreplay)
   - Verify smooth animations (no browser lag)

4. **Edge Cases:**
   - WebSocket disconnect/reconnect
   - tcpdump permission denied
   - Invalid BPF expression
   - Lab with no active nodes (no interfaces)

---

## Deliverables

### Code
- [ ] `backend/api/traffic_websocket.py` (NEW)
- [ ] `backend/services/traffic_service.py` (NEW)
- [ ] `backend/services/topology_mapper.py` (NEW)
- [ ] `frontend/src/hooks/useTrafficWebSocket.js` (NEW)
- [ ] `frontend/src/components/LinkAnimationEngine.jsx` (NEW)
- [ ] `frontend/src/components/TrafficFilterPanel.jsx` (MODIFIED)
- [ ] `frontend/src/pages/LabCanvas.jsx` (MODIFIED)

### Documentation
- [ ] `docs/CRE-68_PHASE3_VERIFICATION.md` (test report)
- [ ] Update `docs/CRE-68_TRAFFIC_VISUALIZATION_MASTER_PLAN.md` (mark Phase 3 done)
- [ ] Update README with WebSocket requirements

### Git
- [ ] Commit: `feat(CRE-68): Phase 3 - WebSocket traffic animation engine`
- [ ] Update Linear with verification numbers
- [ ] Push to GitHub

---

## Technical Decisions

### 1. Animation Approach: SVG `<animateMotion>` vs CSS Transform

**Decision:** Start with SVG `<animateMotion>` for simplicity.
- Pros: Follows path automatically, built-in timing
- Cons: Less control, harder to pause/modify mid-animation

If performance becomes an issue (>50 links), upgrade to Canvas rendering.

### 2. WebSocket vs Server-Sent Events (SSE)

**Decision:** WebSocket (bidirectional, even though we mostly need server→client).
- Future: client can send filter commands via WebSocket
- Existing console.py already uses WebSocket, consistent pattern

### 3. Packet Capture Granularity

**Decision:** One tcpdump per active filter.
- Simple, isolated
- Each filter has its own BPF expression
- No complex event parsing/routing

Alternative (future optimization): One tcpdump per lab with all filters combined as BPF "or" expression.

### 4. Interface → Link Mapping

**Decision:** Build mapping from lab topology on filter activation.
- Query devices → interfaces → links
- Cache for duration of capture session
- Rebuild on topology changes

---

## Known Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **tcpdump requires root/CAP_NET_RAW** | Can't capture packets | Check permissions on startup, show setup instructions |
| **WebSocket connection drops** | Animations freeze | Auto-reconnect with exponential backoff |
| **Heavy traffic overwhelms browser** | UI lag | Throttle events (max 10/sec), batch counters |
| **Interface names don't match Docker convention** | Can't map to links | Fallback to mock mode with synthetic events |
| **Multiple labs open → mixed WebSocket events** | Wrong animations | Each WebSocket scoped to lab_id, verify in event handler |

---

## Success Criteria

Phase 3 is DONE when:
1. ✅ Filter toggle ON → animated dots appear on links
2. ✅ Filter toggle OFF → animations stop immediately
3. ✅ Correct color applied (filter.color → particle.fill)
4. ✅ Real-time packet counters increment
5. ✅ Multiple filters work simultaneously
6. ✅ WebSocket reconnects automatically on disconnect
7. ✅ 12+ integration tests passing
8. ✅ Documentation complete
9. ✅ Committed + pushed to GitHub
10. ✅ Linear updated with verification numbers

---

## Next Phase Preview

**Phase 4:** Advanced Features
- Filter templates (apply multiple filters at once)
- Visual BPF filter builder (drag-drop UI)
- Filter analytics dashboard
- Performance optimization (Canvas rendering, batching)
- Community filter library (import/export)

**Phase 5:** Polish & Launch
- Onboarding tour
- Video demo
- Stress testing (50+ devices)
- Browser compatibility (Firefox, Safari, Edge)
- Documentation site update

---

**Ready to build!** 🚀

Let's start with Milestone 1 (WebSocket foundation).
