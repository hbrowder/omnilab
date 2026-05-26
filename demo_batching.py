#!/usr/bin/env python3
"""
Interactive demo showing the batching behavior in action.
This connects to the WebSocket and prints exactly what messages arrive.
"""

import asyncio
import websockets
import json
import subprocess
import time

LAB_ID = "2640428c-7710-4b2e-be23-3357ed92ca20"

async def demo():
    print("=" * 70)
    print("OmniLab Traffic Batching Demo")
    print("=" * 70)
    
    # Create filter
    print("\n1. Creating ICMP filter...")
    result = subprocess.run([
        'curl', '-s', '-X', 'POST',
        f'http://localhost:5000/api/labs/{LAB_ID}/filters',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps({
            "title": "Demo Filter",
            "expr": "icmp",
            "color": "#00ff00",
            "timeout": 5000,
            "enabled": True,
            "priority": 1
        })
    ], capture_output=True, text=True)
    
    filter_data = json.loads(result.stdout)
    filter_id = filter_data['id']
    print(f"   ✓ Filter created: {filter_id}")
    
    # Connect WebSocket
    print("\n2. Connecting to WebSocket...")
    uri = f"ws://localhost:5000/api/labs/{LAB_ID}/traffic-ws"
    
    async with websockets.connect(uri) as ws:
        # Get connected message
        msg = await ws.recv()
        print(f"   ✓ Connected")
        
        # Enable filter
        print("\n3. Enabling filter...")
        subprocess.run([
            'curl', '-s', '-X', 'POST',
            f'http://localhost:5000/api/labs/{LAB_ID}/filters/{filter_id}/toggle',
            '-H', 'Content-Type: application/json',
            '-d', '{"enabled": true}'
        ], capture_output=True)
        
        await asyncio.sleep(0.5)
        print("   ✓ Filter enabled")
        
        # Start traffic
        print("\n4. Generating 50 pings (50 packets/sec)...")
        print("   Watch how packets get BATCHED into groups:\n")
        
        traffic_proc = await asyncio.create_subprocess_exec(
            'docker', 'exec',
            'omnilab-209b6bf7-0e95-46d7-adab-64aed9720826',
            'ping', '-c', '50', '-i', '0.02', '10.0.0.2',
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        start_time = time.time()
        batch_count = 0
        total_packets = 0
        
        # Collect batches for 2 seconds
        try:
            while time.time() - start_time < 2.5:
                msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
                event = json.loads(msg)
                
                if event['type'] == 'traffic_batch':
                    batch_count += 1
                    packet_count = event['count']
                    total_packets += packet_count
                    elapsed = time.time() - start_time
                    
                    print(f"   Batch #{batch_count:2d} @ {elapsed:5.2f}s: {packet_count:2d} packets")
                    
                    # Show first event in batch as sample
                    if batch_count <= 3 and event['events']:
                        first_event = event['events'][0]
                        print(f"              Sample: {first_event['packet_summary'][:60]}")
                
                elif event['type'] == 'traffic_match':
                    # Old-style individual event (shouldn't happen with batching)
                    print(f"   [OLD] Individual event (not batched)")
        
        except asyncio.TimeoutError:
            pass
        
        await traffic_proc.wait()
        
        # Disable filter
        print("\n5. Disabling filter...")
        subprocess.run([
            'curl', '-s', '-X', 'POST',
            f'http://localhost:5000/api/labs/{LAB_ID}/filters/{filter_id}/toggle',
            '-H', 'Content-Type: application/json',
            '-d', '{"enabled": false}'
        ], capture_output=True)
        
        # Cleanup
        subprocess.run([
            'curl', '-s', '-X', 'DELETE',
            f'http://localhost:5000/api/labs/{LAB_ID}/filters/{filter_id}'
        ], capture_output=True)
        
        print("\n" + "=" * 70)
        print("SUMMARY:")
        print("=" * 70)
        print(f"  Total batches received: {batch_count}")
        print(f"  Total packets captured: {total_packets}")
        print(f"  Avg packets per batch:  {total_packets / batch_count:.1f}")
        print(f"  Batching ratio:         {total_packets}:{batch_count} = {total_packets/batch_count:.1f}x reduction")
        print()
        print("  WITHOUT batching: you'd receive 50 separate WebSocket messages")
        print(f"  WITH batching:    you received {batch_count} messages (~{100/batch_count:.0f}ms intervals)")
        print("=" * 70)

if __name__ == "__main__":
    asyncio.run(demo())
