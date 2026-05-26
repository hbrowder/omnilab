#!/usr/bin/env python3
"""
Simple demo: just show what ONE batch message looks like.
"""

import asyncio
import websockets
import json
import subprocess
import time

LAB_ID = "2640428c-7710-4b2e-be23-3357ed92ca20"

async def show_batch_message():
    print("Waiting for a batch message from the WebSocket...")
    print("(You may need to manually enable a filter in the UI if none are active)\n")
    
    uri = f"ws://localhost:5000/api/labs/{LAB_ID}/traffic-ws"
    
    async with websockets.connect(uri) as ws:
        # Skip connected message
        await ws.recv()
        
        print("Connected. Listening for traffic_batch messages...")
        print("(Generate some traffic: ping between containers)\n")
        
        # Wait for first batch
        for i in range(30):  # Try for 30 seconds
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                event = json.loads(msg)
                
                if event['type'] == 'traffic_batch':
                    print("=" * 70)
                    print("RECEIVED BATCH MESSAGE:")
                    print("=" * 70)
                    print(json.dumps(event, indent=2))
                    print("\n" + "=" * 70)
                    print("EXPLANATION:")
                    print("=" * 70)
                    print(f"  Message type:       {event['type']}")
                    print(f"  Number of packets:  {event['count']}")
                    print(f"  Events in batch:    {len(event['events'])}")
                    print()
                    print("  Each 'event' in the array represents ONE packet:")
                    for idx, evt in enumerate(event['events'][:3], 1):
                        print(f"\n  Packet {idx}:")
                        print(f"    Filter:  {evt['filter_id'][:8]}...")
                        print(f"    Link:    {evt['link_id'][:8]}...")
                        print(f"    Summary: {evt['packet_summary'][:60]}")
                    
                    if event['count'] > 3:
                        print(f"\n  ... and {event['count'] - 3} more packets")
                    
                    print("\n" + "=" * 70)
                    return
                    
            except asyncio.TimeoutError:
                continue
        
        print("No batch messages received in 30 seconds.")

if __name__ == "__main__":
    asyncio.run(show_batch_message())
