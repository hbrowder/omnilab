# CRE-68 Phase 3 Milestone 4 Task 1: In-Container Packet Capture

**Status:** ✅ SHIPPED  
**Commit:** `93ea9e4`  
**GitHub:** https://github.com/hbrowder/omnilab/commit/93ea9e4  
**Date:** 2026-05-25

---

## Problem Statement

**Original approach failed:** Host-based `tcpdump -i eth0` doesn't work because `eth0` exists **inside Docker containers**, not on the host system.

```bash
# On host
$ ip link show eth0
Device "eth0" does not exist.

# Inside container
$ docker exec omnilab-209b6bf7... cat /proc/net/dev | grep eth0
eth0: 43073459     849    0    0    0     0          0         0
```

When we tried to run `tcpdump -i eth0` from the host, it failed silently — no interface, no capture, no events.

---

## Solution: In-Container Capture via `docker exec`

Instead of running tcpdump on the host, we run it **inside each container's network namespace**:

```bash
# Old (broken)
tcpdump -i eth0 -n -l icmp

# New (working)
docker exec -t omnilab-209b6bf7-0e95-46d7-adab-64aed9720826 tcpdump -i eth0 -n -l icmp
```

The `-t` flag allocates a pseudo-TTY so stdout/stderr are properly captured by our `subprocess.Popen`.

---

## Architecture

### 1. Topology Mapper Enhancement

**File:** `backend/services/topology_mapper.py`

**New Method:** `get_container_interfaces(lab_id: str) -> Dict[Tuple[str, str], str]`

Returns a mapping of `(container_name, interface) → link_id`:

```python
{
  ("omnilab-209b6bf7-0e95-46d7-adab-64aed9720826", "eth0"): "860d1ee1-5ec0-4e24-9bd3-e7b13e67e4f7",
  ("omnilab-12705356-60c6-4b02-801a-6dd4065f227b", "eth0"): "860d1ee1-5ec0-4e24-9bd3-e7b13e67e4f7"
}
```

**Implementation:**
- Queries `nodes` table for all nodes in the lab
- Parses `interfaces` JSON column (added in migration 003)
- Queries `links` table to map `src_interface`/`dst_interface` to `link_id`
- Constructs container names using pattern `omnilab-<node_id>`

### 2. Traffic Service Refactor

**File:** `backend/services/traffic_service.py`

**Key Changes:**

1. **Per-Container tcpdump Processes**
   ```python
   # Start one tcpdump per (container, interface) pair
   for (container_name, interface), link_id in container_interface_map.items():
       cmd = [
           'docker', 'exec',
           '-t',  # Allocate pseudo-TTY
           container_name,
           'tcpdump',
           '-i', interface,
           '-n', '-l', '-tt',
           expression
       ]
       proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
   ```

2. **Session Tracking**
   - Changed key from `interface` to `"container:interface"` string
   - Allows same interface name (e.g., `eth0`) on different containers
   - Example: `"omnilab-209b6bf7...:eth0"` vs `"omnilab-12705356...:eth0"`

3. **Thread Pool per Interface**
   - One background thread per (container, interface) reads tcpdump output
   - Parses packets and sends WebSocket events with correct `link_id`
   - Threads coordinate via `asyncio.loop.call_soon_threadsafe()`

---

## Testing

**Test Script:** `test_m3_simple.py`

**Lab:** smoketest-v2
- Node: kali (209b6bf7-0e95-46d7-adab-64aed9720826)
- Node: target (12705356-60c6-4b02-801a-6dd4065f227b)
- Link: kali[eth0] ↔ target[eth0] (860d1ee1-5ec0-4e24-9bd3-e7b13e67e4f7)

**Test Flow:**
1. Create ICMP filter
2. Connect WebSocket
3. Enable filter (starts tcpdump in both containers)
4. Generate traffic: `docker exec kali ping -c 2 target`
5. Wait for `traffic_match` events
6. Disable filter (stops tcpdump)
7. Cleanup

**Results:**
```
✅ 4 traffic_match events received
✅ All events correctly mapped to link_id: 860d1ee1
✅ Containers: kali + target both capturing
```

---

## Prerequisites Installed

**tcpdump in Containers:**

Both lab containers required tcpdump installation:

```bash
# Kali (kalilinux/kali-rolling)
docker exec omnilab-209b6bf7... apt-get update && apt-get install -y tcpdump

# Target (vulnerables/web-dvwa - Debian Stretch EOL)
# Required archive.debian.org repos + --allow-unauthenticated flag
docker exec omnilab-12705356... apt-get update && apt-get install -y --allow-unauthenticated tcpdump
```

**Future:** Update Docker images to include tcpdump by default.

---

## Files Changed

**3 files, 701 insertions(+), 117 deletions(-)**

1. `backend/services/topology_mapper.py` (+50 lines)
   - `get_container_interfaces()` method
   - Container name construction logic

2. `backend/services/traffic_service.py` (~150 lines modified)
   - `start_capture()`: docker exec logic
   - `_read_packets_from_interface()`: signature updated with `container_name`
   - Session key format changed to `"container:interface"`

3. `docs/CRE-68_PHASE3_MILESTONE4_PLAN.md` (+500 lines)
   - Milestone 4 task breakdown
   - Architecture notes
   - Testing strategy

---

## Impact

### ✅ Benefits

1. **True Per-Interface Accuracy**
   - Captures exactly what each container sees
   - Works for multi-link topologies (multiple containers, multiple interfaces per container)
   - No ambiguity about which interface sent/received a packet

2. **Clean Conceptual Model**
   - Follows Docker's network isolation model
   - Each container has its own network namespace
   - tcpdump runs where the traffic actually flows

3. **Scalable**
   - Supports N containers × M interfaces per lab
   - Thread pool architecture handles concurrent captures
   - WebSocket broadcasts to all connected clients

### 🎯 Use Cases Enabled

- **Multi-node labs:** 5+ routers/switches with complex interconnections
- **Per-link traffic visualization:** Show OSPF on one link, BGP on another
- **Accurate packet counts:** Each interface tracked independently
- **Container-native labs:** Works with any Docker-based network topology

---

## Known Limitations

1. **Container Must Be Running**
   - Cannot capture from stopped containers
   - Error handling: graceful failure with user notification (Task 4)

2. **tcpdump Must Be Installed**
   - Not in base images by default
   - Solution: Update Dockerfiles or pre-provision on first capture attempt

3. **Docker Socket Required**
   - Backend needs access to Docker daemon
   - Already available via `/var/run/docker.sock`

---

## Next Steps

**Remaining Milestone 4 Tasks:**

- **Task 2:** Event batching/throttling (prevent WebSocket flood)
- **Task 3:** UI packet counters (show real-time counts per filter)
- **Task 4:** Error handling polish (better messages, graceful failures)
- **Task 5:** Particle animation limits (performance optimization)

**Estimated Time:** ~3 hours total

---

## Retrospective

### What Went Right

✅ **Identified root cause quickly** — Host vs container namespace issue diagnosed in first test  
✅ **Clean solution** — `docker exec` is the "Docker way" to access container internals  
✅ **Minimal code changes** — Leveraged existing topology_mapper + traffic_service architecture  
✅ **Test-driven** — Had failing test, fixed code, test passed immediately  

### What We Learned

💡 **Docker networking model matters** — Can't assume host sees container interfaces  
💡 **`-t` flag is critical** — Without pseudo-TTY, subprocess stdout capture fails silently  
💡 **Thread-safe async coordination** — `loop.call_soon_threadsafe()` pattern for thread→async bridge  

### Technical Debt

⚠️ **tcpdump installation** — Should be baked into Docker images  
⚠️ **Container health checks** — Need to verify containers are running before starting capture  
⚠️ **Error messages** — Current failures are silent; need user-facing notifications  

All tracked for Task 4 (Error Handling Polish).

---

## References

- **Test:** `test_m3_simple.py`
- **Migration:** `backend/migrations/003_add_topology_columns.py`
- **Phase 3 Plan:** `docs/CRE-68_PHASE3_PLAN.md`
- **Milestone 3 Ship Report:** `docs/CRE-68_PHASE3_MILESTONE3_SHIP_REPORT.md`

---

**Shipped by:** Kit (Hermes Agent)  
**Verified by:** Harold  
**Test Results:** 4/4 events, 100% accuracy
