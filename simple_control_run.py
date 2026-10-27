#!/usr/bin/env python3
"""
Simple direct control run test.
"""

import requests
import json
import time

# Configuration
BACKEND_URL = "http://localhost:8000"
SCENARIO_ID = "cisco_aci_microburst"
RUN_ID = f"NS-PHASE4A-{int(time.time())}"

print(f"🚀 Phase 4A Simple Control Run")
print(f"Run ID: {RUN_ID}")
print(f"Scenario: {SCENARIO_ID}")
print(f"Backend: {BACKEND_URL}")
print("-" * 60)

# 1. Check if backend is running
print("\n1. Checking backend health...")
try:
    response = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
    print(f"   Health check: HTTP {response.status_code}")
    if response.status_code == 200:
        print("   ✅ Backend healthy")
    else:
        print(f"   ❌ Backend unhealthy: {response.text}")
        exit(1)
except Exception as e:
    print(f"   ❌ Backend not reachable: {e}")
    exit(1)

# 2. Get available destinations
print("\n2. Checking available destinations...")
try:
    response = requests.get(f"{BACKEND_URL}/api/destinations/", timeout=5)
    destinations = response.json()
    print(f"   Found {len(destinations)} destinations:")
    for dest in destinations:
        print(f"   - {dest['id']}: {dest['name']} ({dest['deployment_type']})")
        
    # Look for a working destination
    working_dest = None
    for dest in destinations:
        if dest.get('enabled', False):
            working_dest = dest['id']
            print(f"   ✅ Using destination: {working_dest}")
            break
    
    if not working_dest:
        print("   ❌ No enabled destinations found")
        # Try docker_local anyway
        working_dest = "docker_local"
        print(f"   ⚠️  Trying {working_dest} anyway...")
        
except Exception as e:
    print(f"   ❌ Error getting destinations: {e}")
    print("   ⚠️  Trying with 'docker_local'...")
    working_dest = "docker_local"

# 3. Test scenario preview
print(f"\n3. Testing scenario preview for '{SCENARIO_ID}'...")
try:
    response = requests.post(
        f"{BACKEND_URL}/api/acceptance/preview/{SCENARIO_ID}",
        json={},
        timeout=30
    )
    
    if response.status_code == 200:
        preview = response.json()
        events = preview.get('events', [])
        print(f"   ✅ Preview generated {len(events)} events")
        print(f"   Dispatch enabled: {preview.get('dispatch_enabled', False)}")
        
        # Show sourcetype distribution
        st_counts = {}
        for event in events:
            st = event.get('sourcetype', 'unknown')
            st_counts[st] = st_counts.get(st, 0) + 1
        
        print(f"   Sourcetype distribution:")
        for st, count in st_counts.items():
            print(f"     - {st}: {count}")
    else:
        print(f"   ❌ Preview failed: HTTP {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        exit(1)
        
except Exception as e:
    print(f"   ❌ Preview error: {e}")
    exit(1)

# 4. Execute scenario
print(f"\n4. Executing scenario '{SCENARIO_ID}'...")
try:
    payload = {
        "scenario_id": SCENARIO_ID,
        "destination_id": working_dest,
        "seed": 42  # Deterministic seed
    }
    
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(
        f"{BACKEND_URL}/api/scenarios/run-with-destination",
        json=payload,
        timeout=60
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ Execution successful!")
        print(f"   Run ID: {result.get('run_id', 'unknown')}")
        print(f"   Generated: {result.get('total_events_generated', 0)}")
        print(f"   Accepted: {result.get('dispatch_succeeded', 0)}")
        print(f"   Failed: {result.get('dispatch_failed', 0)}")
        print(f"   Observed: {result.get('observed_count', 0)}")
        print(f"   Status: {result.get('observation_status', 'unknown')}")
        
        # Save results
        with open(f"control_run_{RUN_ID}.json", "w") as f:
            json.dump(result, f, indent=2)
        print(f"   📁 Results saved to: control_run_{RUN_ID}.json")
        
        # Check for errors
        errors = result.get('errors', [])
        if errors:
            print(f"   ⚠️  Errors: {errors}")
            
    else:
        print(f"   ❌ Execution failed: HTTP {response.status_code}")
        print(f"   Response: {response.text}")
        exit(1)
        
except Exception as e:
    print(f"   ❌ Execution error: {e}")
    exit(1)

print("\n" + "=" * 60)
print("🎉 CONTROL RUN COMPLETED SUCCESSFULLY!")
print(f"Run ID: {RUN_ID}")
print("=" * 60)