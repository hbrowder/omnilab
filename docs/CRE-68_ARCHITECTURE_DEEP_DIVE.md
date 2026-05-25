# CRE-68: Traffic Visualization - Architecture Deep Dive

## System Architecture Layers

### Layer 1: Data Capture (Kernel/Process Level)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Physical Network Layer                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Device Container 1          Device Container 2          Device N    │
│  ┌─────────────────┐        ┌─────────────────┐        ┌────────┐  │
│  │ eth0 ◄─────────┼────────►│ eth0            │        │        │  │
│  │ eth1            │        │ eth1 ◄─────────┼────────►│ eth0   │  │
│  │                 │        │                 │        │        │  │
│  │   tcpdump       │        │   tcpdump       │        │ tcpdump│  │
│  │   (BPF filter)  │        │   (BPF filter)  │        │        │  │
│  │     │           │        │     │           │        │   │    │  │
│  └─────┼───────────┘        └─────┼───────────┘        └───┼────┘  │
│        │                           │                        │        │
│        └───────────────────────────┴────────────────────────┘        │
│                                    │                                 │
└────────────────────────────────────┼─────────────────────────────────┘
                                     │
                    ┌────────────────▼──────────────────┐
                    │  Capture Manager (Python)         │
                    │  - Process spawning               │
                    │  - Output parsing                 │
                    │  - Event generation               │
                    └────────────────┬──────────────────┘
                                     │
```

**Key Components:**

1. **tcpdump Processes:**
   - One per interface being monitored
   - BPF filter compiled at kernel level (efficient)
   - Line-buffered output for real-time streaming
   - Managed by Python subprocess module

2. **BPF (Berkeley Packet Filter):**
   - Kernel-level filtering = minimal CPU overhead
   - User provides high-level syntax: `tcp port 179`
   - Kernel compiles to bytecode: `ldh [12]` `jeq #0x800` etc.
   - Only matching packets copied to userspace

3. **Capture Strategies:**

   **Strategy A: Container Exec (Docker)**
   ```bash
   docker exec device_42 tcpdump -i eth0 -n -l 'proto 89'
   ```
   - Simple, works out of the box
   - Performance: ~5-10% overhead per exec
   - Scalability: 50 devices × 2 interfaces = 100 processes

   **Strategy B: Host-Level Capture (Bridge)**
   ```bash
   tcpdump -i omnilab-br0 -n -l 'proto 89 and vlan 100'
   ```
   - Single process captures ALL traffic
   - Requires VLAN tagging to identify device
   - Performance: Minimal overhead
   - Complexity: Mapping VLAN→device

   **Strategy C: eBPF (Future Optimization)**
   ```python
   from bcc import BPF
   bpf = BPF(text="""
       int packet_filter(struct __sk_buff *skb) {
           // Custom filtering logic
           return 0;
       }
   """)
   ```
   - Kernel-level filtering without tcpdump
   - Highest performance (zero-copy)
   - Steep learning curve
   - Use for Phase 2 optimization

**Recommendation:** Start with Strategy A (container exec), migrate to Strategy B for production scale.

---

### Layer 2: Event Processing (Backend)

```
┌──────────────────────────────────────────────────────────────────┐
│                     Capture Engine (Python)                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Process Pool                                              │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│  │  │ tcpdump  │  │ tcpdump  │  │ tcpdump  │  │ tcpdump  │  │  │
│  │  │ Reader 1 │  │ Reader 2 │  │ Reader 3 │  │ Reader N │  │  │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │  │
│  └───────┼─────────────┼─────────────┼─────────────┼────────┘  │
│          │             │             │             │            │
│          └─────────────┴─────────────┴─────────────┘            │
│                             │                                    │
│  ┌──────────────────────────▼─────────────────────────────────┐ │
│  │  Line Parser                                               │ │
│  │  - Regex extraction: src IP, dst IP, protocol            │ │
│  │  - Timestamp normalization                               │ │
│  │  - Packet summary generation                             │ │
│  └──────────────────────────┬─────────────────────────────────┘ │
│                             │                                    │
│  ┌──────────────────────────▼─────────────────────────────────┐ │
│  │  Link Resolver                                            │ │
│  │  - IP → Device mapping (cache)                           │ │
│  │  - Device pair → Link ID lookup                          │ │
│  │  - Fallback: Broadcast to all candidate links            │ │
│  └──────────────────────────┬─────────────────────────────────┘ │
│                             │                                    │
│  ┌──────────────────────────▼─────────────────────────────────┐ │
│  │  Event Aggregator                                         │ │
│  │  - Batch events (100ms windows)                          │ │
│  │  - Deduplicate (same link+filter in window)             │ │
│  │  - Increment packet counters                             │ │
│  └──────────────────────────┬─────────────────────────────────┘ │
│                             │                                    │
└─────────────────────────────┼──────────────────────────────────┘
                              │
                 ┌────────────▼───────────────┐
                 │   WebSocket Broadcaster    │
                 │   - Connected clients     │
                 │   - Per-lab channels      │
                 └────────────┬───────────────┘
                              │
                      ┌───────▼──────────┐
                      │   Frontend       │
                      │   (Animation)    │
                      └──────────────────┘
```

**Critical Path Latency Analysis:**

```
Packet arrives at interface:          T+0ms
tcpdump sees packet:                   T+1ms   (kernel → userspace)
Python reads line:                     T+2ms   (pipe buffer)
Parse src/dst:                         T+3ms   (regex)
Lookup link:                           T+4ms   (cache hit: O(1))
Aggregate batch:                       T+5-105ms (window)
WebSocket send:                        T+106ms (network)
Frontend receives:                     T+107ms
Animation starts:                      T+108ms

TOTAL: ~110ms (acceptable for real-time feel)
```

**Optimization Targets:**
- Reduce aggregation window to 50ms → 58ms total
- Use msgpack instead of JSON → 55ms total
- Client-side interpolation → perceived <10ms

---

### Layer 3: State Management (Database)

```
┌──────────────────────────────────────────────────────────────────┐
│                        SQLite Database                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  traffic_filters (Hot Read/Write)                          │ │
│  │  ┌──────┬────────┬─────────┬───────┬──────────┬──────────┐ │ │
│  │  │ id   │ name   │ filter  │ color │ is_active│ pkt_count│ │ │
│  │  ├──────┼────────┼─────────┼───────┼──────────┼──────────┤ │ │
│  │  │ 1    │ OSPF   │ proto 89│ #0F0  │ 1        │ 4523     │ │ │
│  │  │ 2    │ BGP    │ tcp 179 │ #F00  │ 1        │ 891      │ │ │
│  │  │ 3    │ VXLAN  │ udp 4789│ #82E  │ 0        │ 0        │ │ │
│  │  └──────┴────────┴─────────┴───────┴──────────┴──────────┘ │ │
│  │  Indexes: is_active (bitmap), category (hash)              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  capture_sessions (Process Tracking)                       │ │
│  │  ┌──────┬──────────┬──────────┬───────────┬─────┬────────┐ │ │
│  │  │ id   │ filter_id│ device_id│ interface │ pid │ active │ │ │
│  │  ├──────┼──────────┼──────────┼───────────┼─────┼────────┤ │ │
│  │  │ 1    │ 1 (OSPF) │ 42       │ eth0      │ 9823│ 1      │ │ │
│  │  │ 2    │ 1 (OSPF) │ 42       │ eth1      │ 9824│ 1      │ │ │
│  │  │ 3    │ 1 (OSPF) │ 43       │ eth0      │ 9825│ 1      │ │ │
│  │  │ 4    │ 2 (BGP)  │ 42       │ eth0      │ 9826│ 1      │ │ │
│  │  └──────┴──────────┴──────────┴───────────┴─────┴────────┘ │ │
│  │  Purpose: Track PIDs for cleanup on deactivate             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  device_interfaces (Link Resolution Cache)                 │ │
│  │  ┌──────┬──────────┬───────────┬─────────────┬──────────┐  │ │
│  │  │ id   │ device_id│ interface │ ip_address  │ link_id  │  │ │
│  │  ├──────┼──────────┼───────────┼─────────────┼──────────┤  │ │
│  │  │ 1    │ 42       │ eth0      │ 10.0.0.1/24 │ 15       │  │ │
│  │  │ 2    │ 42       │ eth1      │ 10.0.1.1/24 │ 16       │  │ │
│  │  │ 3    │ 43       │ eth0      │ 10.0.0.2/24 │ 15       │  │ │
│  │  │ 4    │ 43       │ eth1      │ 10.0.2.1/24 │ 17       │  │ │
│  │  └──────┴──────────┴───────────┴─────────────┴──────────┘  │ │
│  │  Query: "10.0.0.1 → 10.0.0.2" = link_id 15                 │ │
│  │  Updates: On topology change, IP assignment               │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  filter_matches (Analytics, Optional)                      │ │
│  │  ┌──────┬──────────┬─────────┬────────────────┬─────────┐  │ │
│  │  │ id   │ filter_id│ link_id │ matched_at     │ pkt_cnt │  │ │
│  │  ├──────┼──────────┼─────────┼────────────────┼─────────┤  │ │
│  │  │ 1    │ 1        │ 15      │ 2026-05-26 T+0 │ 1       │  │ │
│  │  │ 2    │ 1        │ 15      │ 2026-05-26 T+1 │ 50      │  │ │
│  │  │ 3    │ 2        │ 16      │ 2026-05-26 T+2 │ 3       │  │ │
│  │  └──────┴──────────┴─────────┴────────────────┴─────────┘  │ │
│  │  Purpose: Traffic timeline, replay, heatmaps              │ │
│  │  Retention: 7 days (auto-purge)                           │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

**Performance Considerations:**

1. **Hot Path Queries:**
   - `SELECT is_active FROM traffic_filters WHERE id = ?` → <1ms (index)
   - `SELECT link_id FROM device_interfaces WHERE ip_address = ?` → <1ms (index)
   
2. **Batch Updates:**
   - Packet count: Update every 1 second (not per packet)
   - Use `UPDATE traffic_filters SET packet_count = packet_count + ? WHERE id = ?`
   
3. **Write Amplification:**
   - 1000 packets/sec × 5 filters = 5000 db writes/sec = TOO MUCH
   - Solution: In-memory counters, flush to DB every 1 second

4. **Analytics Table:**
   - Write async (don't block event loop)
   - Use BULK INSERT (100 rows at a time)
   - Partition by date for fast purging

---

### Layer 4: Real-Time Communication (WebSocket)

```
┌──────────────────────────────────────────────────────────────────┐
│                      WebSocket Architecture                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Backend (FastAPI)                  Frontend (React)             │
│  ┌──────────────────────┐          ┌──────────────────────┐     │
│  │  WebSocket Server    │◄────────►│  WebSocket Client    │     │
│  │  /ws/{lab_id}        │          │  useWebSocket hook   │     │
│  └──────────────────────┘          └──────────────────────┘     │
│           │                                   │                   │
│           │  Message Types:                   │                   │
│           │                                   │                   │
│           │  ┌─────────────────────────────┐ │                   │
│           │  │ C→S: ACTIVATE_FILTER        │ │                   │
│           │  │ {                           │ │                   │
│           │  │   action: "activate",       │ │                   │
│           │  │   filter_id: 5              │ │                   │
│           │  │ }                           │ │                   │
│           │  └─────────────────────────────┘ │                   │
│           │                                   │                   │
│           │  ┌─────────────────────────────┐ │                   │
│           │  │ S→C: TRAFFIC_MATCH          │ │                   │
│           │  │ {                           │ │                   │
│           │  │   event: "traffic_match",   │ │                   │
│           │  │   filter_id: 5,             │ │                   │
│           │  │   link_id: 42,              │ │                   │
│           │  │   color: "#00FF00",         │ │                   │
│           │  │   duration: 3000,           │ │                   │
│           │  │   packet_count: 127,        │ │                   │
│           │  │   timestamp: 1234567890     │ │                   │
│           │  │ }                           │ │                   │
│           │  └─────────────────────────────┘ │                   │
│           │                                   │                   │
│           │  ┌─────────────────────────────┐ │                   │
│           │  │ S→C: COUNTER_UPDATE         │ │                   │
│           │  │ {                           │ │                   │
│           │  │   event: "counter_update",  │ │                   │
│           │  │   filter_id: 5,             │ │                   │
│           │  │   packet_count: 200         │ │                   │
│           │  │ }                           │ │                   │
│           │  └─────────────────────────────┘ │                   │
│           │                                   │                   │
└───────────┴───────────────────────────────────┴───────────────────┘

**Connection Management:**

┌────────────────────────────────────────────────────────────────┐
│  ConnectionManager (Python)                                    │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Active Connections                                      │ │
│  │  {                                                       │ │
│  │    lab_123: [ws_client_1, ws_client_2, ws_client_3],   │ │
│  │    lab_456: [ws_client_4]                              │ │
│  │  }                                                       │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  Broadcast Strategy:                                           │
│  - Lab-scoped: Only send events to clients viewing that lab   │
│  - Throttling: Max 50 events/sec per client                   │
│  - Batching: Group events in 100ms window → send as array     │
│                                                                │
│  Reconnection Handling:                                        │
│  - Client reconnects → send current state (active filters)    │
│  - Resume packet counters (fetch from DB)                     │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Message Format Optimization:**

```javascript
// Verbose JSON (current)
{
  "event": "traffic_match",
  "filter_id": 5,
  "link_id": 42,
  "color": "#00FF00",
  "duration": 3000,
  "packet_count": 127,
  "timestamp": 1234567890
}
// Size: ~150 bytes

// Compact format (future optimization)
{
  "e": "tm",  // event: traffic_match
  "f": 5,     // filter_id
  "l": 42,    // link_id
  "c": "#0F0", // color (shortened)
  "d": 3000,  // duration
  "p": 127,   // packet_count
  "t": 1234567890
}
// Size: ~80 bytes (47% reduction)

// Binary format (msgpack)
[1, 5, 42, "#0F0", 3000, 127, 1234567890]
// Size: ~30 bytes (80% reduction)
```

**Bandwidth Estimation:**

```
Scenario: 10 active filters, 100 packets/sec total
- Events/sec: 100 (assuming 1 event per packet)
- Message size: 150 bytes (JSON)
- Bandwidth: 100 × 150 = 15 KB/sec = 0.12 Mbps

With batching (100ms windows):
- Events/batch: 10 (100 events/sec ÷ 10 batches/sec)
- Batches/sec: 10
- Message size: 1.5 KB per batch
- Bandwidth: 10 × 1.5 = 15 KB/sec (same, but fewer TCP packets)

Conclusion: Bandwidth is negligible. Optimization unnecessary unless >1000 pps.
```

---

### Layer 5: Visualization (Frontend)

```
┌──────────────────────────────────────────────────────────────────┐
│                     Frontend Architecture                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  LabCanvas.jsx (Main View)                                  ││
│  │  ┌──────────────────────────────────────────────────────┐   ││
│  │  │  SVG Canvas                                          │   ││
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐             │   ││
│  │  │  │ Device  │  │ Device  │  │ Device  │             │   ││
│  │  │  │  [R1]   │  │  [R2]   │  │  [R3]   │             │   ││
│  │  │  └────┬────┘  └────┬────┘  └────┬────┘             │   ││
│  │  │       │            │            │                   │   ││
│  │  │       └────Link────┴────Link────┘                   │   ││
│  │  │            (animated)   (animated)                  │   ││
│  │  │                                                      │   ││
│  │  └──────────────────────────────────────────────────────┘   ││
│  │                                                              ││
│  │  Components:                                                 ││
│  │  - <Device> (nodes)                                          ││
│  │  - <Link> (edges, animated)                                  ││
│  │  - <AnimatedDot> (traffic visualization)                     ││
│  │  - <LinkLabel> (packet counter overlay)                      ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  TrafficFilterPanel.jsx (Sidebar)                           ││
│  │  ┌──────────────────────────────────────────────────────┐   ││
│  │  │  ┌───┐ OSPF                          [⏸] [✏] [🗑]    │   ││
│  │  │  │░░░│ Watch Hello, LSAs              4523 packets   │   ││
│  │  │  └───┘ proto 89                                       │   ││
│  │  │  ┌───┐ BGP                           [▶] [✏] [🗑]    │   ││
│  │  │  │░░░│ Track BGP updates               0 packets     │   ││
│  │  │  └───┘ tcp port 179                                   │   ││
│  │  │  ┌───┐ VXLAN                          [▶] [✏] [🗑]    │   ││
│  │  │  │░░░│ Overlay traffic                 0 packets     │   ││
│  │  │  └───┘ udp port 4789                                  │   ││
│  │  └──────────────────────────────────────────────────────┘   ││
│  │                                                              ││
│  │  States:                                                     ││
│  │  - filters: [{id, name, color, is_active, packet_count}]    ││
│  │  - selectedCategory: "routing"                               ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  LinkAnimationEngine.jsx (Logic Component)                  ││
│  │                                                              ││
│  │  Responsibilities:                                           ││
│  │  1. Listen for "traffic_match" events                        ││
│  │  2. Trigger link animations                                  ││
│  │  3. Manage animation timers                                  ││
│  │  4. Update packet counters                                   ││
│  │                                                              ││
│  │  Animation Strategies:                                       ││
│  │  - SVG <animateMotion> (simple, CPU-light)                   ││
│  │  - Canvas API (high-performance, 100+ concurrent)            ││
│  │  - CSS animations (hardware-accelerated)                     ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

**Animation Implementation Options:**

**Option 1: SVG animateMotion (Recommended for MVP)**
```jsx
<svg>
  <path id="link-42" d="M100,100 L500,300" stroke="#ccc" />
  
  {/* Animated dot */}
  <circle r="5" fill={filter.color}>
    <animateMotion dur="3s" repeatCount="indefinite">
      <mpath href="#link-42" />
    </animateMotion>
  </circle>
</svg>
```

**Pros:**
- Simple to implement
- Built-in browser support
- No animation loop needed

**Cons:**
- Limited to ~20 concurrent animations (browser-dependent)
- No dynamic duration changes

---

**Option 2: Canvas API (Recommended for Production)**
```javascript
const canvas = document.getElementById('animation-layer');
const ctx = canvas.getContext('2d');

class AnimatedDot {
  constructor(path, color, duration) {
    this.path = path;
    this.color = color;
    this.duration = duration;
    this.startTime = Date.now();
  }
  
  draw() {
    const elapsed = Date.now() - this.startTime;
    const progress = (elapsed % this.duration) / this.duration;
    
    const point = this.path.getPointAtLength(progress * this.path.getTotalLength());
    
    ctx.beginPath();
    ctx.arc(point.x, point.y, 5, 0, Math.PI * 2);
    ctx.fillStyle = this.color;
    ctx.fill();
  }
}

// Animation loop
function animate() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  activeDots.forEach(dot => dot.draw());
  requestAnimationFrame(animate);
}
```

**Pros:**
- Handles 1000+ concurrent animations
- Full control over rendering
- Can add motion blur, trails, etc.

**Cons:**
- More complex code
- Requires manual loop management

---

**Option 3: WebGL (Overkill, but future-proof)**
```javascript
// Three.js particles along spline curve
const geometry = new THREE.BufferGeometry();
const particles = new THREE.Points(geometry, material);
scene.add(particles);

// Update particles along Bezier curve
particles.position.lerpVectors(start, end, progress);
```

**Pros:**
- Can handle 10,000+ particles
- GPU-accelerated
- Stunning visual effects

**Cons:**
- Massive overkill for this use case
- Increases bundle size

**Recommendation:** SVG for MVP, Canvas for production optimization.

---

## Performance Benchmarks (Target)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Capture startup latency | <500ms | Time from API call → first tcpdump line |
| Link resolution time | <5ms | IP pair → link_id lookup |
| WebSocket message latency | <50ms | Backend event → Frontend receive |
| Animation frame rate | 60 FPS | requestAnimationFrame consistency |
| Concurrent filters (no lag) | 10 | User can activate 10 filters smoothly |
| Max topology size | 100 devices, 200 links | No UI slowdown |
| Packet processing rate | 1000 pps | Before throttling kicks in |
| Memory footprint | <100 MB | Python backend RSS |

---

## API Contract (OpenAPI Snippet)

```yaml
paths:
  /api/traffic-filters/filters:
    get:
      summary: List all traffic filters
      parameters:
        - name: category
          in: query
          schema:
            type: string
            enum: [layer2, routing, overlay, transport, vlan, multicast, custom]
      responses:
        200:
          description: List of filters
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/TrafficFilter'
  
  /api/traffic-filters/filters/{filter_id}/activate:
    post:
      summary: Activate a traffic filter
      parameters:
        - name: filter_id
          in: path
          required: true
          schema:
            type: integer
        - name: lab_id
          in: query
          required: true
          schema:
            type: integer
      responses:
        200:
          description: Filter activated
          content:
            application/json:
              schema:
                type: object
                properties:
                  filter_id:
                    type: integer
                  sessions_started:
                    type: integer
                  pids:
                    type: array
                    items:
                      type: integer

components:
  schemas:
    TrafficFilter:
      type: object
      properties:
        id:
          type: integer
        name:
          type: string
        description:
          type: string
        tcpdump_filter:
          type: string
        color:
          type: string
          pattern: '^#[0-9A-Fa-f]{6}$'
        category:
          type: string
        is_builtin:
          type: boolean
        is_active:
          type: boolean
        packet_count:
          type: integer
        animation_duration:
          type: integer
```

---

**END OF ARCHITECTURE DEEP DIVE**
