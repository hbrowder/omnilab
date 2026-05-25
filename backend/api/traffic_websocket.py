"""
WebSocket endpoint for real-time traffic visualization events.

CRE-68 Phase 3: Live traffic animation
- Broadcasts filter activation/deactivation events
- Streams packet match events to frontend
- Manages per-lab WebSocket connections
"""
import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()

# Connection pool: {lab_id: Set[WebSocket]}
_connections: Dict[str, Set[WebSocket]] = {}


class ConnectionManager:
    """Manage WebSocket connections per lab."""
    
    @staticmethod
    async def connect(websocket: WebSocket, lab_id: str):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        if lab_id not in _connections:
            _connections[lab_id] = set()
        _connections[lab_id].add(websocket)
        logger.info(f"Client connected to lab {lab_id} (total: {len(_connections[lab_id])})")
    
    @staticmethod
    def disconnect(websocket: WebSocket, lab_id: str):
        """Remove a WebSocket connection."""
        if lab_id in _connections:
            _connections[lab_id].discard(websocket)
            if not _connections[lab_id]:
                del _connections[lab_id]
        logger.info(f"Client disconnected from lab {lab_id}")
    
    @staticmethod
    async def broadcast(lab_id: str, message: dict):
        """Send a message to all clients connected to a lab."""
        if lab_id not in _connections:
            return
        
        dead_connections = set()
        message_json = json.dumps(message)
        
        for websocket in _connections[lab_id]:
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send message to client: {e}")
                dead_connections.add(websocket)
        
        # Clean up dead connections
        for ws in dead_connections:
            _connections[lab_id].discard(ws)
    
    @staticmethod
    def get_connection_count(lab_id: str) -> int:
        """Get number of active connections for a lab."""
        return len(_connections.get(lab_id, set()))


@router.websocket("/labs/{lab_id}/traffic-ws")
async def traffic_websocket(websocket: WebSocket, lab_id: str):
    """
    Real-time traffic visualization events for a specific lab.
    
    Event Types (server → client):
    - filter_activated: {type, filter_id, name, color, duration}
    - filter_deactivated: {type, filter_id}
    - traffic_match: {type, filter_id, link_id, timestamp, packet_summary}
    - packet_count_update: {type, filter_id, count}
    - error: {type, message}
    
    Client can send (future):
    - ping: heartbeat
    - subscribe: {filter_ids: [1, 2, 3]}  # Only receive events for specific filters
    
    Args:
        websocket: FastAPI WebSocket connection
        lab_id: Lab UUID or identifier
    """
    manager = ConnectionManager()
    await manager.connect(websocket, lab_id)
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "lab_id": lab_id,
            "timestamp": asyncio.get_event_loop().time(),
            "message": "Traffic visualization WebSocket connected"
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for client messages (currently just for heartbeat/ping)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0  # 30-second timeout for client ping
                )
                
                # Parse and handle client message
                try:
                    message = json.loads(data)
                    message_type = message.get("type")
                    
                    if message_type == "ping":
                        # Respond to heartbeat
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": asyncio.get_event_loop().time()
                        })
                    else:
                        logger.warning(f"Unknown message type: {message_type}")
                
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from client: {data}")
            
            except asyncio.TimeoutError:
                # No message in 30 seconds - send heartbeat to keep connection alive
                try:
                    await websocket.send_json({
                        "type": "heartbeat",
                        "timestamp": asyncio.get_event_loop().time()
                    })
                except Exception:
                    # Connection likely dead
                    break
    
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from lab {lab_id}")
    except Exception as e:
        logger.error(f"WebSocket error for lab {lab_id}: {e}", exc_info=True)
    finally:
        manager.disconnect(websocket, lab_id)


# Utility functions for other modules to send events

async def send_filter_activated(lab_id: str, filter_id: str, name: str, color: str, duration: int):
    """Notify clients that a filter was activated."""
    await ConnectionManager.broadcast(lab_id, {
        "type": "filter_activated",
        "filter_id": filter_id,
        "name": name,
        "color": color,
        "duration": duration,
        "timestamp": asyncio.get_event_loop().time()
    })


async def send_filter_deactivated(lab_id: str, filter_id: str):
    """Notify clients that a filter was deactivated."""
    await ConnectionManager.broadcast(lab_id, {
        "type": "filter_deactivated",
        "filter_id": filter_id,
        "timestamp": asyncio.get_event_loop().time()
    })


async def send_traffic_match(lab_id: str, filter_id: str, link_id: str, packet_summary: str = ""):
    """Notify clients of a packet match on a specific link."""
    await ConnectionManager.broadcast(lab_id, {
        "type": "traffic_match",
        "filter_id": filter_id,
        "link_id": link_id,
        "timestamp": asyncio.get_event_loop().time(),
        "packet_summary": packet_summary
    })


async def send_traffic_batch(lab_id: str, events: list[dict]):
    """Send a batch of traffic_match events as a single message."""
    await ConnectionManager.broadcast(lab_id, {
        "type": "traffic_batch",
        "events": events,
        "count": len(events),
        "timestamp": asyncio.get_event_loop().time()
    })


async def send_packet_count_update(lab_id: str, filter_id: str, count: int):
    """Send updated packet count for a filter."""
    await ConnectionManager.broadcast(lab_id, {
        "type": "packet_count_update",
        "filter_id": filter_id,
        "count": count,
        "timestamp": asyncio.get_event_loop().time()
    })


async def send_error(lab_id: str, message: str, filter_id: str | None = None):
    """Send error message to clients."""
    event = {
        "type": "error",
        "message": message,
        "timestamp": asyncio.get_event_loop().time()
    }
    if filter_id is not None:
        event["filter_id"] = filter_id
    
    await ConnectionManager.broadcast(lab_id, event)
