# CRE-68 Phase 3 Milestone 4: Performance + Polish

**Date:** 2026-05-25  
**Engineer:** Kit (007)  
**Status:** PLANNING  
**Prerequisites:** Milestones 1-3 complete ✅

---

## Objective

Optimize the traffic visualization pipeline for production use with:
1. **Per-interface packet capture** (accurate multi-link attribution)
2. **Performance optimizations** (event batching, throttling)
3. **Error handling** (tcpdump crashes, WebSocket disconnects)
4. **UI polish** (counters, status indicators, particle limits)

---

## Current State

✅ **Working:**
- Database schema with nodes.interfaces and links.src_interface/dst_interface
- WebSocket endpoint streaming traffic_match events
- Topology mapper resolving interface → link_id
- E2E test capturing 8 ICMP packets successfully

❌ **Known Issues:**
1. **tcpdump -i any doesn't report interface** - packets attributed to first link only
2. **No event throttling** - high traffic could spam 1000s of WebSocket messages/sec
3. **No packet counters in UI** - user can't see match rate
4. **No error recovery** - tcpdump crash leaves filter in zombie state

---

## Milestone 4 Tasks

### Task 1: Per-Interface Packet Capture (HIGH PRIORITY)

**Problem:** `tcpdump -i any` captures all traffic but doesn't reliably show which interface each packet came from. Multi-link topologies show all traffic on the first link.

**Solution:** Spawn one tcpdump process per interface in the lab topology.

**Implementation:**

#### 1.1 Extend CaptureSession Model
**File:** `backend/services/traffic_service.py`

```python
@dataclass
class CaptureSession:
    filter_id: str
    lab_id: str
    expression: str
    color: str
    processes: Dict[str, subprocess.Popen]  # interface → process
    threads: Dict[str, threading.Thread]    # interface → reader thread
    interface_to_link: Dict[str, str]       # interface → link_id (from topology)
    packet_count: int = 0
    active: bool = True
```

**Changes:**
- Replace single `process` with `processes: Dict[str, Popen]`
- Replace single `thread` with `threads: Dict[str, Thread]`
- Store `interface_to_link` mapping at session creation

#### 1.2 Modify start_capture()
**File:** `backend/services/traffic_service.py`

```python
async def start_capture(self, filter_id: str, lab_id: str, 
                       expression: str, color: str):
    # 1. Get topology interfaces
    topology = TopologyMapper(self.db_path)
    interface_map = await topology.get_all_interfaces(lab_id)
    
    # 2. Get unique interfaces from the map
    interfaces = set()
    for iface_key in interface_map.keys():
        if ':' not in iface_key:  # Only bare interface names (eth0, not kali:eth0)
            interfaces.add(iface_key)
    
    if not interfaces:
        raise ValueError(f"No interfaces found for lab {lab_id}")
    
    # 3. Spawn one tcpdump per interface
    processes = {}
    threads = {}
    loop = asyncio.get_running_loop()
    
    for iface in interfaces:
        cmd = [
            "tcpdump", "-i", iface, "-l", "-n", 
            "-e",  # Include link-level header (for verification)
            expression
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, 
                               stderr=subprocess.DEVNULL, text=True)
        processes[iface] = proc
        
        # Start reader thread for this interface
        thread = threading.Thread(
            target=self._read_packets,
            args=(proc, filter_id, lab_id, iface, interface_map, loop),
            daemon=True
        )
        thread.start()
        threads[iface] = thread
    
    # 4. Store session
    session = CaptureSession(
        filter_id=filter_id,
        lab_id=lab_id,
        expression=expression,
        color=color,
        processes=processes,
        threads=threads,
        interface_to_link=interface_map,
        packet_count=0,
        active=True
    )
    self._sessions[filter_id] = session
    
    # 5. Notify activation
    await send_filter_activated(lab_id, filter_id, expression, color, 10000)
```

#### 1.3 Modify _read_packets()
**File:** `backend/services/traffic_service.py`

```python
def _read_packets(self, proc: subprocess.Popen, filter_id: str, 
                 lab_id: str, interface: str, 
                 interface_map: Dict[str, str], loop):
    """
    Read tcpdump output for a specific interface.
    Now we KNOW which interface this packet came from!
    """
    for line in proc.stdout:
        session = self._sessions.get(filter_id)
        if not session or not session.active:
            break
        
        line = line.strip()
        if not line:
            continue
        
        # Direct lookup - we KNOW it's from this interface
        link_id = interface_map.get(interface)
        
        if link_id:
            session.packet_count += 1
            
            # Broadcast to WebSocket
            future = asyncio.run_coroutine_threadsafe(
                send_traffic_match(
                    lab_id=lab_id,
                    filter_id=filter_id,
                    link_id=link_id,
                    packet_summary=f"Interface {interface}: {line[:80]}"
                ),
                loop
            )
            try:
                future.result(timeout=1.0)
            except Exception as e:
                print(f"Failed to send traffic_match: {e}")
```

#### 1.4 Modify stop_capture()
**File:** `backend/services/traffic_service.py`

```python
async def stop_capture(self, filter_id: str, lab_id: str):
    session = self._sessions.get(filter_id)
    if not session:
        return
    
    session.active = False
    
    # Kill all tcpdump processes
    for iface, proc in session.processes.items():
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception as e:
            print(f"Error stopping tcpdump on {iface}: {e}")
            proc.kill()
    
    # Wait for threads
    for thread in session.threads.values():
        thread.join(timeout=1)
    
    # Remove session
    del self._sessions[filter_id]
    
    # Notify deactivation
    await send_filter_deactivated(lab_id, filter_id)
```

**Verification:**
- Test with smoketest-v2 (1 link, 2 interfaces)
- Verify packets on eth0 → link_id A, packets on eth1 → link_id B
- Test with multi-link lab (3+ links) → each link gets correct traffic

---

### Task 2: Event Batching & Throttling (MEDIUM PRIORITY)

**Problem:** High traffic rates (1000 pkt/sec) spam WebSocket with 1000 events/sec → browser lag.

**Solution:** Batch `traffic_match` events and throttle to max 10-20 updates/sec.

#### 2.1 Add Batching Logic
**File:** `backend/services/traffic_service.py`

```python
@dataclass
class CaptureSession:
    # ... existing fields ...
    pending_events: List[Dict] = field(default_factory=list)
    last_batch_time: float = 0.0
    batch_interval: float = 0.1  # Send batches every 100ms
```

#### 2.2 Modify _read_packets() to Queue Events
```python
def _read_packets(self, proc, filter_id, lab_id, interface, interface_map, loop):
    for line in proc.stdout:
        session = self._sessions.get(filter_id)
        if not session or not session.active:
            break
        
        link_id = interface_map.get(interface)
        if link_id:
            session.packet_count += 1
            
            # Queue event instead of sending immediately
            event = {
                "lab_id": lab_id,
                "filter_id": filter_id,
                "link_id": link_id,
                "packet_summary": f"Interface {interface}: {line[:80]}"
            }
            session.pending_events.append(event)
            
            # Send batch if interval elapsed
            now = time.time()
            if now - session.last_batch_time >= session.batch_interval:
                self._flush_batch(session, loop)
                session.last_batch_time = now
```

#### 2.3 Add Flush Method
```python
def _flush_batch(self, session: CaptureSession, loop):
    """Send all pending events in one batch."""
    if not session.pending_events:
        return
    
    # Send up to 20 events per batch (prevent massive bursts)
    batch = session.pending_events[:20]
    session.pending_events = session.pending_events[20:]
    
    for event in batch:
        future = asyncio.run_coroutine_threadsafe(
            send_traffic_match(**event),
            loop
        )
        try:
            future.result(timeout=0.5)
        except Exception as e:
            print(f"Failed to send batched event: {e}")
```

**Verification:**
- Generate high traffic (100 pings/sec)
- Verify WebSocket message rate ≤ 10-20/sec
- Verify packet_count still accurate (no dropped counts)

---

### Task 3: Packet Count Display in UI (LOW PRIORITY)

**File:** `frontend/src/components/TrafficFilterPanel.jsx`

#### 3.1 Add Counter State
```jsx
const [packetCounts, setPacketCounts] = useState({}); // filter_id → count
```

#### 3.2 Listen to traffic_match Events
```jsx
useEffect(() => {
  if (traffic.lastEvent?.type === 'traffic_match') {
    const { filter_id } = traffic.lastEvent;
    setPacketCounts(prev => ({
      ...prev,
      [filter_id]: (prev[filter_id] || 0) + 1
    }));
  }
}, [traffic.lastEvent]);
```

#### 3.3 Display Counter in Filter Row
```jsx
<div className="filter-row">
  <span>{filter.name}</span>
  {filter.enabled && (
    <span className="packet-badge">
      {packetCounts[filter.id] || 0} pkts
    </span>
  )}
  <ToggleSwitch ... />
</div>
```

**Verification:**
- Enable filter
- Generate traffic
- See counter increment in real-time

---

### Task 4: Error Handling (MEDIUM PRIORITY)

#### 4.1 Handle tcpdump Permission Errors
**File:** `backend/services/traffic_service.py`

```python
async def start_capture(...):
    for iface in interfaces:
        try:
            proc = subprocess.Popen(...)
            # Check if process died immediately (permission error)
            time.sleep(0.1)
            if proc.poll() is not None:
                stderr = proc.stderr.read() if proc.stderr else ""
                raise RuntimeError(
                    f"tcpdump failed on {iface}. "
                    f"Check permissions (CAP_NET_RAW required). "
                    f"Error: {stderr}"
                )
            processes[iface] = proc
        except Exception as e:
            # Clean up already-started processes
            for p in processes.values():
                p.kill()
            raise RuntimeError(f"Failed to start capture on {iface}: {e}")
```

#### 4.2 Handle WebSocket Disconnects (Frontend)
**File:** `frontend/src/hooks/useTrafficWebSocket.js`

Already implemented in Milestone 1! ✅
- Auto-reconnect with exponential backoff
- Connection status exposed to UI

#### 4.3 Show Status Indicator
**File:** `frontend/src/components/TrafficFilterPanel.jsx`

```jsx
{traffic.isConnected ? (
  <span className="status-indicator online">● Live</span>
) : (
  <span className="status-indicator offline">○ Offline</span>
)}
```

**Verification:**
- Stop backend → UI shows "Offline"
- Restart backend → UI auto-reconnects, shows "Live"
- Run tcpdump without permissions → helpful error shown

---

### Task 5: Particle Limit (LOW PRIORITY)

**File:** `frontend/src/components/LinkAnimationEngine.jsx`

```jsx
const MAX_PARTICLES_PER_LINK = 20;

useEffect(() => {
  if (traffic.lastEvent?.type === 'traffic_match') {
    const { link_id, filter_id } = traffic.lastEvent;
    
    setParticles(prev => {
      const linkParticles = prev.filter(p => p.linkId === link_id);
      
      // Remove oldest if at limit
      if (linkParticles.length >= MAX_PARTICLES_PER_LINK) {
        const oldestId = linkParticles[0].id;
        prev = prev.filter(p => p.id !== oldestId);
      }
      
      return [...prev, newParticle];
    });
  }
}, [traffic.lastEvent]);
```

**Verification:**
- Generate 100 packets/sec on one link
- Verify max 20 particles visible at once
- No memory leak / browser slowdown

---

## Testing Strategy

### Test 1: Per-Interface Accuracy
**Lab:** smoketest-v2 (2 nodes, 1 link, 2 interfaces each)
**Steps:**
1. Create ICMP filter
2. Enable filter
3. Ping kali → target (traffic on eth0)
4. Verify: traffic_match events have link_id for kali[eth0]↔target[eth0]
5. Generate traffic on eth1 (if possible)
6. Verify: separate link_id (or no events if eth1 not connected)

### Test 2: High Traffic Load
**Lab:** Any lab with active connections
**Steps:**
1. Create TCP filter (port 22)
2. Enable filter
3. Run `dd if=/dev/zero | ssh target dd of=/dev/null` (generates 100+ MB/sec)
4. Verify:
   - WebSocket message rate ≤ 20/sec
   - Packet counter accurate (within 5% of actual)
   - No browser lag
   - Animations smooth

### Test 3: Multi-Filter
**Lab:** smoketest-v2
**Steps:**
1. Create 3 filters: ICMP (green), TCP (blue), UDP (orange)
2. Enable all 3
3. Generate mixed traffic (ping + ssh + DNS)
4. Verify:
   - Each filter shows separate packet count
   - Correct colors on links
   - No event cross-contamination

### Test 4: Error Recovery
**Steps:**
1. Start server WITHOUT tcpdump permissions (`sudo setcap -r /usr/bin/tcpdump`)
2. Enable filter
3. Verify: error message shown to user
4. Restore permissions (`sudo setcap cap_net_admin,cap_net_raw=eip /usr/bin/tcpdump`)
5. Enable filter again
6. Verify: works correctly

### Test 5: WebSocket Reconnect
**Steps:**
1. Open lab, enable filter
2. Generate traffic → see animations
3. Stop backend (Ctrl+C uvicorn)
4. Wait 5 seconds
5. Restart backend
6. Verify: UI shows "reconnecting..." then "Live"
7. Generate traffic → animations resume

---

## Deliverables

### Code Changes
- ✅ `backend/services/traffic_service.py` - per-interface capture + batching
- ✅ `frontend/src/components/TrafficFilterPanel.jsx` - packet counters + status
- ✅ `frontend/src/components/LinkAnimationEngine.jsx` - particle limit

### Tests
- ✅ `test_milestone4_performance.py` - automated test suite
- ✅ Manual QA checklist (above)

### Documentation
- ✅ `docs/CRE-68_PHASE3_MILESTONE4_SHIP_REPORT.md`
- ✅ Update master plan with Milestone 4 completion

### Git
- ✅ Commit with verification numbers
- ✅ Push to GitHub
- ✅ Update Linear CRE-68

---

## Success Criteria

Milestone 4 is DONE when:
1. ✅ Per-interface tcpdump spawns correctly (1 process per eth0/eth1/etc.)
2. ✅ Packets attributed to correct link_id (multi-link accuracy test passes)
3. ✅ WebSocket event rate throttled to ≤ 20/sec under heavy load
4. ✅ Packet counters display in UI and increment correctly
5. ✅ Status indicator shows "Live" / "Offline" correctly
6. ✅ Max 20 particles per link (no memory leak)
7. ✅ tcpdump permission error shows helpful message
8. ✅ WebSocket auto-reconnects on disconnect
9. ✅ All 5 test scenarios pass
10. ✅ Committed + Linear updated

---

## Estimated Time

- **Task 1 (Per-Interface):** 1.5 hours (core refactor)
- **Task 2 (Batching):** 1 hour
- **Task 3 (UI Counters):** 0.5 hours
- **Task 4 (Error Handling):** 1 hour
- **Task 5 (Particle Limit):** 0.5 hours
- **Testing:** 1 hour
- **Documentation:** 0.5 hours

**Total:** ~6 hours

---

**Ready to implement!** Starting with Task 1 (Per-Interface Capture) as it's the highest priority fix. 🚀
