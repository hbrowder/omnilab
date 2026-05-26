# CRE-68 Phase 3 Milestone 4 Task 3: Frontend UI Updates for Batching

**Status:** IN PROGRESS  
**Prerequisites:** Task 2 (Event Batching & Throttling) ✅  
**Date:** 2026-05-26

---

## Objective

Update the frontend to handle the new `traffic_batch` WebSocket message type,
expanding batched events into individual link animations while maintaining
backward compatibility with the old `traffic_match` format.

---

## Background

Task 2 introduced a new WebSocket message type: `traffic_batch`

**Old format** (still supported):
```json
{
  "type": "traffic_match",
  "filter_id": "abc123",
  "link_id": "def456",
  "packet_summary": "eth0: ICMP echo request...",
  "timestamp": 1234567890.123
}
```

**New format** (batched):
```json
{
  "type": "traffic_batch",
  "events": [
    {
      "lab_id": "...",
      "filter_id": "abc123",
      "link_id": "def456",
      "packet_summary": "eth0: ICMP echo request..."
    },
    {
      "lab_id": "...",
      "filter_id": "abc123",
      "link_id": "ghi789",
      "packet_summary": "eth1: ICMP echo reply..."
    }
  ],
  "count": 2,
  "timestamp": 1234567890.123
}
```

---

## Implementation Plan

### Step 1: Locate the WebSocket Event Handler

Find where `traffic_match` events are currently processed. Likely locations:
- `frontend/src/hooks/useTrafficWebSocket.js` or `.ts`
- `frontend/src/components/canvas/*` (TrafficManager, Canvas component)
- `frontend/src/components/TrafficFilterPanel.*`

### Step 2: Add Handler for traffic_batch

Expand batch events into individual animations:

```typescript
// In WebSocket message handler
if (event.type === 'traffic_match') {
    // Existing single-event handler
    animateTraffic(event.link_id, event.filter_id);
    incrementPacketCount(event.filter_id, 1);
}
else if (event.type === 'traffic_batch') {
    // NEW: Handle batch of events
    for (const packet of event.events) {
        animateTraffic(packet.link_id, packet.filter_id);
    }
    
    // Update counter once with total count
    if (event.events.length > 0) {
        const filter_id = event.events[0].filter_id;
        incrementPacketCount(filter_id, event.count);
    }
}
```

### Step 3: Update Packet Counter Logic

The counter may currently increment by 1 per `traffic_match`.
Update it to handle batch counts:

```typescript
// Old (increment by 1)
setPacketCounts(prev => ({
    ...prev,
    [filter_id]: (prev[filter_id] || 0) + 1
}));

// New (increment by count)
setPacketCounts(prev => ({
    ...prev,
    [filter_id]: (prev[filter_id] || 0) + count
}));
```

### Step 4: Animation Timing (Optional Enhancement)

Current approach: animate all packets immediately (fast burst)

Optional improvement: stagger animations over the batch interval

```typescript
if (event.type === 'traffic_batch') {
    const delay_ms = 100 / event.count;  // Spread over 100ms
    
    event.events.forEach((packet, idx) => {
        setTimeout(() => {
            animateTraffic(packet.link_id, packet.filter_id);
        }, idx * delay_ms);
    });
}
```

This creates smoother visual flow instead of all particles spawning at once.

---

## Files to Modify

Based on OmniLab frontend structure (need to verify actual paths):

1. **WebSocket Hook**
   - Likely: `frontend/src/hooks/useTrafficWebSocket.ts`
   - Add case for `traffic_batch` message type

2. **Traffic Animation Component**
   - Likely: `frontend/src/components/canvas/TrafficManager.tsx`
   - May need to expose `animateTraffic()` or handle batches internally

3. **Packet Counter State**
   - Likely: `frontend/src/components/TrafficFilterPanel.tsx`
   - Update increment logic to accept count parameter

---

## Verification

### Test 1: Single Packet (backward compat)
1. Start backend + frontend
2. Create ICMP filter, enable it
3. Send 1 ping
4. Verify animation appears on correct link
5. Verify counter shows 1 packet

### Test 2: Batch of Packets
1. Generate high-volume traffic (100 pings/sec)
2. Open browser DevTools → Network → WS
3. Confirm receiving `traffic_batch` messages (not `traffic_match`)
4. Verify animations appear on correct links
5. Verify counter increments correctly (should match packet count)

### Test 3: Multiple Links
1. Use smoketest-v2 lab (2 containers, 1 link)
2. Generate bidirectional traffic (ping between containers)
3. Verify animations on correct link for both directions
4. Verify counter includes both directions

---

## Success Criteria

✅ Frontend handles both `traffic_match` and `traffic_batch` messages  
✅ Batch events expand into individual link animations  
✅ Packet counter increments correctly for batches  
✅ No visual regressions (animations still smooth)  
✅ No console errors when receiving batches  

---

## Notes

- Maintain backward compatibility: old `traffic_match` must still work
- Animation staggering (Step 4) is optional - implement only if burst animations look bad
- If frontend already batches animations internally, this may be simpler than expected
- Test with various batch sizes (1, 5, 20 packets) to ensure smooth performance

---

## Next Steps After Task 3

Once frontend handles batching:
- Task 4: Error handling (tcpdump failures, WebSocket disconnects)
- Task 5: UI polish (status indicators, limits on particle counts)
- Final E2E testing with realistic multi-link labs
