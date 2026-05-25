#!/usr/bin/env python3
"""Quick WebSocket test client for CRE-68 Phase 3"""
import asyncio
import websockets
import json

async def test_traffic_websocket():
    uri = "ws://localhost:5000/api/labs/test-lab-123/traffic-ws"
    
    print(f"🔌 Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as ws:
            print("✅ Connected!")
            
            # Wait for initial message
            msg = await ws.recv()
            data = json.loads(msg)
            print(f"📨 Received: {json.dumps(data, indent=2)}")
            
            # Wait for heartbeat
            print("\n⏳ Waiting for heartbeat (30s)...")
            msg = await asyncio.wait_for(ws.recv(), timeout=35)
            data = json.loads(msg)
            print(f"💓 Heartbeat: {json.dumps(data, indent=2)}")
            
            print("\n✅ WebSocket working perfectly!")
            
    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket error: {e}")
    except asyncio.TimeoutError:
        print("⏰ Timeout waiting for heartbeat")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_traffic_websocket())
