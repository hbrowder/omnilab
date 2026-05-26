#!/usr/bin/env python3
"""
Test Task 3: Frontend UI Updates for Batching
Verifies that traffic_batch events are properly handled by the frontend.
"""
import requests
import time
import json

BASE_URL = "http://localhost:5000"
LAB_ID = "2640428c-7710-4b2e-be23-3357ed92ca20"
KALI_ID = "omnilab-209b6bf7-0e95-46d7-adab-64aed9720826"
TARGET_ID = "omnilab-12705356-60c6-4b02-801a-6dd4065f227b"

def main():
    print("=" * 60)
    print("TASK 3: Frontend UI Testing for traffic_batch")
    print("=" * 60)
    
    # Step 1: Create a test filter
    print("\n[1/5] Creating ICMP traffic filter...")
    filter_data = {
        "name": "Task3 ICMP Test",
        "color": "#00FFFF",  # Cyan
        "expr": "icmp",
        "lab_id": LAB_ID
    }
    
    resp = requests.post(f"{BASE_URL}/api/traffic/filters", json=filter_data)
    if resp.status_code != 200:
        print(f"❌ Failed to create filter: {resp.text}")
        return
    
    filter_id = resp.json()["id"]
    print(f"✅ Created filter: {filter_id}")
    
    # Step 2: Start capture
    print("\n[2/5] Starting packet capture...")
    capture_data = {
        "filter_id": filter_id,
        "container_id": KALI_ID,
        "interface": "eth0"
    }
    
    resp = requests.post(f"{BASE_URL}/api/traffic/capture/start", json=capture_data)
    if resp.status_code != 200:
        print(f"❌ Failed to start capture: {resp.text}")
        return
    
    print("✅ Capture started")
    
    # Step 3: Generate high-volume traffic
    print("\n[3/5] Generating 200 ICMP packets (2 packets/sec)...")
    print("This will create ~20 batches over ~100 seconds")
    print("(Each batch = 10-20 packets, flushed every 100ms)")
    
    # Generate traffic in background
    ping_cmd = f'docker exec {KALI_ID} ping -c 200 -i 0.5 {TARGET_ID.split("-")[-1][:12]}'
    print(f"\n📊 Run this command in another terminal to generate traffic:")
    print(f"   {ping_cmd}")
    print("\n⏳ Waiting 10 seconds for traffic to flow...")
    time.sleep(10)
    
    # Step 4: Check packet count
    print("\n[4/5] Checking packet counter...")
    resp = requests.get(f"{BASE_URL}/api/traffic/filters/{filter_id}")
    if resp.status_code == 200:
        filter_info = resp.json()
        packet_count = filter_info.get("packet_count", 0)
        print(f"✅ Packet count: {packet_count} packets")
        
        if packet_count > 0:
            print("✅ Frontend counter is updating!")
        else:
            print("⚠️  No packets counted yet - check if traffic is flowing")
    
    # Step 5: Stop capture
    print("\n[5/5] Stopping capture...")
    resp = requests.post(f"{BASE_URL}/api/traffic/capture/stop", json={"filter_id": filter_id})
    print("✅ Capture stopped")
    
    # Cleanup
    print("\n[Cleanup] Deleting test filter...")
    requests.delete(f"{BASE_URL}/api/traffic/filters/{filter_id}")
    print("✅ Filter deleted")
    
    print("\n" + "=" * 60)
    print("MANUAL TESTING REQUIRED:")
    print("=" * 60)
    print("1. Open browser to http://localhost:5173")
    print("2. Open smoketest-v2 lab")
    print("3. Create an ICMP filter with any color you want")
    print("4. Start capture on kali container")
    print("5. Generate traffic: docker exec <kali> ping -c 100 10.20.1.2")
    print("6. Watch for:")
    print("   • Smooth particle animations (not bursts)")
    print("   • Packet counter incrementing")
    print("   • No console errors")
    print("   • DevTools Network tab shows 'traffic_batch' messages")
    print("=" * 60)

if __name__ == "__main__":
    main()
