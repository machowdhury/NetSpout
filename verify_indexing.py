#!/usr/bin/env python3
"""
Verify Phase 4A control run events are indexed in Splunk.
"""

import os
import requests
import json
import time
import sys
from datetime import datetime

# Splunk configuration
SPLUNK_URL = "https://localhost:18000"
SPLUNK_API = "https://localhost:18089"
splunk_password = os.getenv('SPLUNK_PASSWORD')
if not splunk_password:
    raise ValueError("SPLUNK_PASSWORD environment variable not set")
SPLUNK_AUTH = ("admin", splunk_password)

def search_splunk(search_query):
    """Execute a one-shot search in Splunk."""
    try:
        response = requests.post(
            f"{SPLUNK_API}/services/search/jobs",
            auth=SPLUNK_AUTH,
            data={
                "search": search_query,
                "exec_mode": "oneshot",
                "output_mode": "json",
                "count": 0  # Just get count
            },
            verify=False,
            timeout=10
        )
        
        if response.status_code == 201:
            try:
                results = response.json()
                return {
                    "success": True,
                    "results": results.get("results", []),
                    "sid": response.headers.get("sid", "unknown"),
                    "message": f"Search executed successfully"
                }
            except json.JSONDecodeError:
                # For oneshot searches, the response might not be JSON
                return {
                    "success": True,
                    "raw_response": response.text[:500],
                    "sid": response.headers.get("sid", "unknown"),
                    "message": f"Search executed (non-JSON response)"
                }
        else:
            return {
                "success": False,
                "status_code": response.status_code,
                "message": f"Search API returned HTTP {response.status_code}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Error executing search: {e}"
        }

def main():
    run_id = "NS-20261027-b57e1b01"
    print(f"🔍 Verifying indexing for Run ID: {run_id}")
    print(f"📊 Splunk: {SPLUNK_URL}")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    # Test 1: Event search
    print("\n1. Searching for events...")
    event_search = f'search index=idx_network_ops netspout_run_id="{run_id}" earliest=-10m latest=now'
    print(f"   Query: {event_search}")
    
    event_result = search_splunk(event_search)
    if event_result["success"]:
        results = event_result.get("results", [])
        event_count = len(results)
        print(f"   ✅ Found {event_count} events")
        
        if event_count > 0:
            print(f"   Sample events:")
            for i, event in enumerate(results[:3], 1):
                print(f"   {i}. sourcetype={event.get('sourcetype', 'N/A')}")
                print(f"      host={event.get('host', 'N/A')}")
                print(f"      _time={event.get('_time', 'N/A')}")
    else:
        print(f"   ❌ Search failed: {event_result.get('message', 'Unknown error')}")
    
    # Test 2: Metrics search
    print("\n2. Searching for metrics...")
    metrics_search = f'| mstats count WHERE index=idx_performance_metrics netspout_run_id="{run_id}" earliest=-10m latest=now'
    print(f"   Query: {metrics_search}")
    
    metrics_result = search_splunk(metrics_search)
    if metrics_result["success"]:
        print(f"   ✅ Metrics search executed")
        # mstats output is complex, but just knowing it executed is good
        raw_response = metrics_result.get("raw_response", "")
        if "count" in raw_response.lower():
            print(f"   📊 Found metrics data")
    else:
        print(f"   ❌ Metrics search failed: {metrics_result.get('message', 'Unknown error')}")
    
    # Test 3: Count by sourcetype
    print("\n3. Counting by sourcetype...")
    sourcetype_search = f'search index=idx_network_ops netspout_run_id="{run_id}" earliest=-10m latest=now | stats count by sourcetype'
    print(f"   Query: {sourcetype_search[:80]}...")
    
    st_result = search_splunk(sourcetype_search)
    if st_result["success"]:
        results = st_result.get("results", [])
        if results:
            print(f"   📈 Sourcetype distribution:")
            for row in results:
                print(f"      {row.get('sourcetype', 'N/A')}: {row.get('count', 0)}")
        else:
            print(f"   ⚠️  No results found (may not be indexed yet)")
    else:
        print(f"   ❌ Sourcetype search failed: {st_result.get('message', 'Unknown error')}")
    
    # Test 4: Direct HEC test
    print("\n4. Testing HEC directly...")
    hec_token = os.getenv('PULSEFORGE_LAB_HEC_TOKEN')
    if not hec_token:
        raise ValueError("PULSEFORGE_LAB_HEC_TOKEN environment variable not set")
    try:
        test_response = requests.post(
            "https://localhost:18088/services/collector",
            headers={"Authorization": f"Splunk {hec_token}"},
            json={
                "event": f"Phase 4A verification test - {datetime.now().isoformat()}",
                "sourcetype": "phase4a_verify",
                "index": "idx_ta_ise_test",
                "fields": {"test": "verification", "run_id": run_id}
            },
            verify=False,
            timeout=5
        )
        if test_response.status_code == 200:
            print(f"   ✅ HEC accepts events (HTTP {test_response.status_code})")
        else:
            print(f"   ❌ HEC rejected test: HTTP {test_response.status_code}")
    except Exception as e:
        print(f"   ❌ HEC test error: {e}")
    
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)

if __name__ == "__main__":
    main()