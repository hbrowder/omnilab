BATCHING REVIEW: How It Works
================================================================================

## The Problem

Before batching, with 100 packets/sec:
- Backend captures 100 packets
- Backend sends 100 WebSocket messages (one per packet)
- Frontend receives 100 messages
- Frontend animates 100 times
- Result: WebSocket and UI are FLOODED

## The Solution

With batching (100ms intervals):
- Backend captures 100 packets
- Backend QUEUES them in memory (pending_events list)
- Every 100ms, backend sends ONE message containing 10-20 packets
- Frontend receives ~10 messages
- Frontend expands each batch into individual animations
- Result: 90% fewer WebSocket messages

## How It Works (Code Flow)

### 1. Packet Capture Thread
Location: traffic_service.py, _read_packets_from_interface()

```python
# When a packet arrives:
event = {
    "lab_id": session.lab_id,
    "filter_id": session.filter_id,
    "link_id": link_id,
    "packet_summary": "..."
}

# QUEUE it (don't send yet)
with self._lock:  # Thread-safe
    session.pending_events.append(event)
    
    # Check if 100ms has elapsed
    now = time.time()
    if now - session.last_batch_time >= 0.1:  # 100ms
        self._flush_batch(session, loop)
        session.last_batch_time = now
```

### 2. Batch Flushing
Location: traffic_service.py, _flush_batch()

```python
# Take up to 20 events from queue
batch = session.pending_events[:20]
session.pending_events = session.pending_events[20:]

# Send ALL of them in ONE WebSocket message
send_traffic_batch(session.lab_id, batch)
```

### 3. WebSocket Message
Location: traffic_websocket.py, send_traffic_batch()

```python
# Send this structure:
{
    "type": "traffic_batch",
    "events": [
        {"filter_id": "...", "link_id": "...", "packet_summary": "..."},
        {"filter_id": "...", "link_id": "...", "packet_summary": "..."},
        {"filter_id": "...", "link_id": "...", "packet_summary": "..."},
        ... up to 20 events ...
    ],
    "count": 6,
    "timestamp": 1234567890.123
}
```

## Test Results

Input: 100 pings/sec for 2 seconds = ~200 packets

WITHOUT batching:
✗ 198 WebSocket messages
✗ 58.6 messages/sec
✗ 17ms average interval
✗ UI would be FLOODED

WITH batching:
✓ 33 WebSocket messages (83% reduction!)
✓ 9.4 messages/sec
✓ 109ms average interval (right on target)
✓ UI receives manageable rate

## Batch Contents (Example from Test)

Batch #1: 1 packet   (startup - partial batch)
Batch #2: 4 packets  (100ms worth of traffic)
Batch #3: 2 packets
Batch #4: 7 packets
Batch #5: 6 packets
...and so on

Average: ~6 packets per batch
This varies based on traffic patterns!

## Thread Safety

Key insight: Multiple interfaces = multiple threads
- Each interface has its own capture thread
- All threads share the same pending_events queue
- We use a Lock to prevent race conditions:

```python
with self._lock:
    # Only one thread can access pending_events at a time
    session.pending_events.append(event)
    
    # Check time and flush atomically
    if now - session.last_batch_time >= session.batch_interval:
        self._flush_batch(session, loop)
        session.last_batch_time = now
```

Without the lock:
- Thread A checks time: "100ms elapsed, time to flush!"
- Thread B checks time: "100ms elapsed, time to flush!"
- Both flush simultaneously → duplicate batches, wrong timing

## Frontend Impact (Task 3)

The frontend currently expects individual traffic_match events.
Task 3 needs to:

1. Listen for BOTH message types:
   - 'traffic_match' (old, individual)
   - 'traffic_batch' (new, multiple)

2. Expand batches:
   ```javascript
   if (event.type === 'traffic_batch') {
       for (const packet of event.events) {
           // Animate this packet on its link
           animateTraffic(packet.link_id, packet.filter_id);
       }
   }
   ```

3. Update packet counters:
   ```javascript
   if (event.type === 'traffic_batch') {
       // Add the count of ALL packets in batch
       updateFilterCount(event.events[0].filter_id, event.count);
   }
   ```

## Configuration

Batching parameters (in CaptureSession):
- batch_interval: 0.1 (100ms) - how often to flush
- max_per_batch: 20 - max events in one batch

These could be made configurable later:
- Lower interval (50ms) = more responsive, more messages
- Higher interval (200ms) = fewer messages, less responsive
- Larger batches (50) = fewer messages, bigger payloads

Current settings (100ms, 20 events) are a good balance for
typical network lab traffic patterns.

================================================================================
