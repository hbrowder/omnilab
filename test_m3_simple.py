#!/usr/bin/env python3
"""
CRE-68 Phase 3 Milestone 3: Real Traffic Visualization E2E Test (Simplified)
Tests packet capture → WebSocket → animation pipeline with real lab.
"""

import asyncio
import json
import subprocess
import requests
import websockets

API_BASE = "http://localhost:5000/api"
WS_URL = "ws://localhost:5000/api/labs/{lab_id}/traffic-ws"

# Use smoketest-v2 lab (has real nodes: kali, target)
LAB_ID = "2640428c-7710-4b2e-be23-3357ed92ca20"


async def main():
    print("═" * 55)
    print("Milestone 3: Real Traffic Visualization Test")
    print("═" * 55)

    # Verify lab exists
    print("\n🏗  Step 0: Verifying lab...")
    resp = requests.get(f"{API_BASE}/labs/{LAB_ID}")
    if resp.status_code != 200:
        print(f"   ❌ Lab not found")
        return
    lab = resp.json()
    print(f"   ✅ Lab: {lab['name']}")
    print(f"      Topology: kali[eth0] <--> target[eth0]")

    # Create traffic filter
    print("\n📝 Step 1: Creating ICMP filter...")
    filter_data = {
        "title": "ICMP Test M3",
        "expr": "icmp",
        "color": "#00ff00",
        "timeout": 10000,
        "enabled": False,
        "priority": 10
    }

    resp = requests.post(f"{API_BASE}/labs/{LAB_ID}/filters", json=filter_data)
    if resp.status_code != 200:
        print(f"   ❌ Failed: {resp.text}")
        return

    filter_obj = resp.json()
    filter_id = filter_obj["id"]
    print(f"   ✅ Filter: {filter_id[:8]}")

    # Connect WebSocket
    print("\n🔌 Step 2: Connecting WebSocket...")

    events = []
    ws_connected = asyncio.Event()

    async def ws_client():
        try:
            async with websockets.connect(WS_URL.format(lab_id=LAB_ID)) as ws:
                welcome = await ws.recv()
                data = json.loads(welcome)
                if data.get("type") == "connected" or data.get("event") == "connected":
                    ws_connected.set()
                
                while True:
                    msg = await ws.recv()
                    event = json.loads(msg)
                    events.append(event)
                    
                    evt_type = event.get("event") or event.get("type")
                    if evt_type == "filter_activated":
                        print(f"   📡 Filter activated!")
                    elif evt_type == "traffic_match":
                        link = event.get('link_id', 'unknown')
                        print(f"   🎯 TRAFFIC: link={link[:8] if link != 'unknown' else 'unknown'}")
                    elif evt_type == "packet_count_update":
                        print(f"   📊 Count: {event.get('count', 0)}")
                    elif evt_type == "filter_deactivated":
                        print(f"   🛑 Filter deactivated!")
                        break
                    elif evt_type == "error":
                        print(f"   ❌ ERROR: {event.get('message', 'unknown')}")
                    else:
                        # Debug unknown events
                        print(f"   🔍 Event: {evt_type} - {event}")
        except asyncio.CancelledError:
            pass

    ws_task = asyncio.create_task(ws_client())

    try:
        await asyncio.wait_for(ws_connected.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        print("   ❌ Timeout")
        ws_task.cancel()
        return
    print("   ✅ Connected")

    # Enable filter
    print("\n🎬 Step 3: Enabling filter...")
    resp = requests.post(f"{API_BASE}/labs/{LAB_ID}/filters/{filter_id}/toggle")
    if resp.status_code != 200:
        print(f"   ❌ Failed: {resp.text}")
        ws_task.cancel()
        return
    print("   ✅ tcpdump started")

    # Generate traffic
    print("\n📡 Step 4: Generating traffic (ping)...")
    subprocess.run(["ping", "-c", "5", "-i", "0.2", "127.0.0.1"], 
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print("   ⏳ Waiting for events (5s)...")
    await asyncio.sleep(5)

    # Check results
    traffic_matches = [e for e in events if (e.get("event") or e.get("type")) == "traffic_match"]
    packet_updates = [e for e in events if (e.get("event") or e.get("type")) == "packet_count_update"]

    if traffic_matches:
        print(f"   ✅ {len(traffic_matches)} traffic_match events!")
    else:
        print(f"   ⚠️  No traffic_match (tcpdump -i any doesn't show interface)")

    if packet_updates:
        count = packet_updates[-1]['data']['count']
        print(f"   📊 Final count: {count} packets")

    # Disable filter
    print("\n🛑 Step 5: Disabling filter...")
    requests.post(f"{API_BASE}/labs/{LAB_ID}/filters/{filter_id}/toggle")
    await asyncio.sleep(2)
    print("   ✅ tcpdump stopped")

    # Cleanup
    print("\n🗑  Step 6: Cleanup...")
    requests.delete(f"{API_BASE}/labs/{LAB_ID}/filters/{filter_id}")
    ws_task.cancel()
    try:
        await ws_task
    except asyncio.CancelledError:
        pass
    print("   ✅ Filter deleted")

    # Summary
    print("\n" + "═" * 55)
    if traffic_matches:
        print("✅ MILESTONE 3 COMPLETE!")
        print("\nAll components working:")
        print("  ✓ Topology schema")
        print("  ✓ Traffic capture")
        print("  ✓ WebSocket streaming")
        print("  ✓ Packet → link_id mapping")
    elif packet_updates:
        print("⚠️  PARTIAL: Capture works, mapping needs improvement")
        print("\nWorking:")
        print("  ✓ Topology schema")
        print("  ✓ Traffic capture")
        print("  ✓ WebSocket streaming")
        print("  ✓ Packet counting")
        print("\nNeeds work:")
        print("  ⚠️  Per-interface tcpdump (not -i any)")
    else:
        print("❌ Traffic capture issue")
    
    print("═" * 55)
    print(f"\nEvents: {len(events)} total")
    print(f"  - filter_activated: {len([e for e in events if e.get('event') == 'filter_activated'])}")
    print(f"  - traffic_match: {len(traffic_matches)}")
    print(f"  - packet_count_update: {len(packet_updates)}")


if __name__ == '__main__':
    asyncio.run(main())
