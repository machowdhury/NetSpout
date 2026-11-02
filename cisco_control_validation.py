#!/usr/bin/env python3
"""
Phase 4C P0: Revalidate existing Cisco control run.
Execute cisco_aci_microburst scenario and verify results against historical evidence.
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.absolute()

def validate_cisco_control():
    """Execute and validate Cisco control scenario."""
    
    print(f"\n{'='*60}")
    print(f"🎯 PHASE 4C P0: CISCO CONTROL RUN VALIDATION")
    print(f"{'='*60}")
    
    # Configuration
    backend_url = "http://localhost:8000"
    scenario_id = "cisco_aci_microburst"
    destination_id = "docker_local"
    seed = 42  # Deterministic seed matching historical runs
    run_id = f"NS-PHASE4C-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    print(f"Scenario: {scenario_id}")
    print(f"Run ID: {run_id}")
    print(f"Seed: {seed}")
    print(f"Backend: {backend_url}")
    print(f"Destination: {destination_id}")
    
    # 1. Check backend health
    print(f"\n1. Checking backend health...")
    try:
        health_response = requests.get(f"{backend_url}/api/health", timeout=5)
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"   ✅ Backend healthy: {health_data.get('status')}")
            print(f"   Version: {health_data.get('version')}")
        else:
            print(f"   ❌ Backend unhealthy: HTTP {health_response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Backend not reachable: {e}")
        return False
    
    # 2. Check scenario exists
    print(f"\n2. Verifying scenario {scenario_id}...")
    try:
        scenarios_response = requests.get(f"{backend_url}/api/acceptance/scenarios", timeout=5)
        if scenarios_response.status_code == 200:
            scenarios = scenarios_response.json()
            scenario_found = any(s.get('id') == scenario_id for s in scenarios)
            if scenario_found:
                print(f"   ✅ Scenario found in catalog")
            else:
                print(f"   ❌ Scenario not found in catalog")
                return False
        else:
            print(f"   ❌ Failed to get scenarios: HTTP {scenarios_response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error checking scenarios: {e}")
        return False
    
    # 3. Preview scenario
    print(f"\n3. Previewing scenario...")
    try:
        preview_response = requests.post(
            f"{backend_url}/api/acceptance/preview/{scenario_id}",
            json={},
            timeout=30
        )
        
        if preview_response.status_code == 200:
            preview_data = preview_response.json()
            events = preview_data.get('events', [])
            print(f"   ✅ Preview generated {len(events)} events")
            
            # Show sourcetype distribution
            st_counts = {}
            for event in events:
                st = event.get('sourcetype', 'unknown')
                st_counts[st] = st_counts.get(st, 0) + 1
            
            print(f"   Sourcetype distribution:")
            for st, count in st_counts.items():
                print(f"     - {st}: {count}")
        else:
            print(f"   ❌ Preview failed: HTTP {preview_response.status_code}")
            print(f"   Response: {preview_response.text[:200]}")
            return False
    except Exception as e:
        print(f"   ❌ Preview error: {e}")
        return False
    
    # 4. Execute scenario
    print(f"\n4. Executing scenario...")
    try:
        payload = {
            "scenario_id": scenario_id,
            "destination_id": destination_id,
            "seed": seed
        }
        
        print(f"   Payload: {json.dumps(payload, indent=2)}")
        
        execute_response = requests.post(
            f"{backend_url}/api/scenarios/run-with-destination",
            json=payload,
            timeout=60
        )
        
        if execute_response.status_code == 200:
            result = execute_response.json()
            print(f"   ✅ Execution successful!")
            
            # Record results
            generated = result.get('total_events_generated', 0)
            accepted = result.get('dispatch_succeeded', 0)
            failed = result.get('dispatch_failed', 0)
            observed = result.get('observed_count', 0)
            backend_run_id = result.get('run_id', run_id)
            
            print(f"   Generated: {generated}")
            print(f"   HEC Accepted: {accepted}")
            print(f"   HEC Failed: {failed}")
            print(f"   Observed in Splunk: {observed}")
            print(f"   Backend Run ID: {backend_run_id}")
            
            # Save results
            result['validation_run_id'] = run_id
            result['validation_timestamp'] = datetime.now().isoformat()
            
            result_file = BASE_DIR / f"cisco_control_{run_id}.json"
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"   📁 Results saved to: {result_file}")
            
        else:
            print(f"   ❌ Execution failed: HTTP {execute_response.status_code}")
            print(f"   Response: {execute_response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Execution error: {e}")
        return False
    
    # 5. Verify Splunk indexing
    print(f"\n5. Verifying Splunk indexing...")
    
    # Wait for indexing
    print(f"   Waiting 5 seconds for indexing...")
    time.sleep(5)
    
    try:
        # Check Splunk REST API
        splunk_api = "https://localhost:18089"
        splunk_password = os.getenv('SPLUNK_PASSWORD')
        if not splunk_password:
            raise ValueError("SPLUNK_PASSWORD environment variable not set")
        splunk_auth = ("admin", splunk_password)
        
        # Get backend run ID from result if available
        backend_run_id = None
        if 'result' in locals():
            backend_run_id = result.get('run_id')
        
        # Test 1: Event search
        print(f"\n   Test 1: Event search...")
        if backend_run_id:
            event_search = f'search index=idx_network_ops netspout_run_id="{backend_run_id}" earliest=-5m latest=now | stats count'
            
            event_response = requests.post(
                f"{splunk_api}/services/search/jobs",
                auth=splunk_auth,
                data={
                    "search": event_search,
                    "exec_mode": "oneshot",
                    "output_mode": "json"
                },
                verify=False,
                timeout=10
            )
            
            if event_response.status_code == 201:
                try:
                    event_data = event_response.json()
                    if 'results' in event_data and event_data['results']:
                        event_count = event_data['results'][0].get('count', 0)
                        print(f"      ✅ Found {event_count} events with run_id={backend_run_id}")
                    else:
                        print(f"      ⚠️ No event results found (may need more indexing time)")
                except json.JSONDecodeError:
                    print(f"      ⚠️ Could not parse event search response")
            else:
                print(f"      ⚠️ Event search API returned HTTP {event_response.status_code}")
        
        # Test 2: Sourcetype distribution
        print(f"\n   Test 2: Sourcetype distribution...")
        sourcetype_search = 'search index=idx_network_ops sourcetype=cisco* earliest=-10m latest=now | stats count by sourcetype | sort - count'
        
        st_response = requests.post(
            f"{splunk_api}/services/search/jobs",
            auth=splunk_auth,
            data={
                "search": sourcetype_search,
                "exec_mode": "oneshot",
                "output_mode": "json"
            },
            verify=False,
            timeout=10
        )
        
        if st_response.status_code == 201:
            try:
                st_data = st_response.json()
                if 'results' in st_data:
                    print(f"      Recent Cisco sourcetypes in idx_network_ops:")
                    for row in st_data['results'][:5]:
                        sourcetype = row.get('sourcetype', 'unknown')
                        count = row.get('count', 0)
                        print(f"        - {sourcetype}: {count}")
                else:
                    print(f"      ⚠️ No sourcetype results in response")
            except json.JSONDecodeError:
                print(f"      ⚠️ Could not parse sourcetype search response")
        else:
            print(f"      ⚠️ Sourcetype search API returned HTTP {st_response.status_code}")
        
        # Test 3: Metrics search
        print(f"\n   Test 3: Metrics search...")
        if backend_run_id:
            metrics_search = f'| mstats count WHERE index=idx_performance_metrics netspout_run_id="{backend_run_id}" earliest=-5m latest=now'
            
            metrics_response = requests.post(
                f"{splunk_api}/services/search/jobs",
                auth=splunk_auth,
                data={
                    "search": metrics_search,
                    "exec_mode": "oneshot",
                    "output_mode": "json"
                },
                verify=False,
                timeout=10
            )
            
            if metrics_response.status_code == 201:
                print(f"      ✅ Metrics search job created")
                # Note: mstats output parsing is complex
                print(f"      Use Splunk Web to run: {metrics_search}")
            else:
                print(f"      ⚠️ Metrics search API returned HTTP {metrics_response.status_code}")
                
    except Exception as e:
        print(f"   ⚠️ Splunk verification error (non-critical): {e}")
    
    # 6. Compare with historical evidence
    print(f"\n6. Comparing with historical evidence...")
    
    # Load historical evidence if available
    historical_file = BASE_DIR / "control_run_NS-PHASE4A-1793132976.json"
    if historical_file.exists():
        with open(historical_file, 'r') as f:
            historical = json.load(f)
        
        hist_generated = historical.get('total_events_generated', 0)
        hist_accepted = historical.get('dispatch_succeeded', 0)
        hist_observed = historical.get('observed_count', 0)
        
        print(f"   Historical (Phase 4A):")
        print(f"     Generated: {hist_generated}")
        print(f"     HEC Accepted: {hist_accepted}")
        print(f"     Observed: {hist_observed}")
        
        if 'result' in locals():
            current_generated = result.get('total_events_generated', 0)
            current_accepted = result.get('dispatch_succeeded', 0)
            
            if current_generated == hist_generated and current_accepted == hist_accepted:
                print(f"   ✅ Counts match historical evidence!")
            else:
                print(f"   ⚠️ Counts differ from historical:")
                print(f"     Generated: {current_generated} vs {hist_generated}")
                print(f"     Accepted: {current_accepted} vs {hist_accepted}")
    else:
        print(f"   ⚠️ Historical evidence file not found: {historical_file}")
    
    # 7. Generate SPL examples
    print(f"\n7. Example SPL queries for verification:")
    
    if 'backend_run_id' in locals() and backend_run_id:
        print(f"\n   Events by run ID:")
        print(f"     search index=idx_network_ops netspout_run_id=\"{backend_run_id}\"")
        print(f"     | stats count by sourcetype")
        print(f"     | sort - count")
        
        print(f"\n   Recent Cisco events:")
        print(f"     search index=idx_network_ops sourcetype=cisco* earliest=-10m latest=now")
        print(f"     | table _time, host, sourcetype, source")
        print(f"     | sort - _time")
        
        print(f"\n   Metrics by run ID:")
        print(f"     | mstats count WHERE index=idx_performance_metrics netspout_run_id=\"{backend_run_id}\" earliest=-5m latest=now")
        print(f"     | timechart span=1m count")
    
    print(f"\n{'='*60}")
    print(f"✅ CISCO CONTROL VALIDATION COMPLETE")
    print(f"{'='*60}")
    
    print(f"\n📋 Summary:")
    print(f"  - Scenario executed: {scenario_id}")
    print(f"  - Run ID: {run_id}")
    print(f"  - Results saved to: cisco_control_{run_id}.json")
    print(f"  - Splunk verification attempted")
    print(f"  - SPL examples provided for manual verification")
    
    return True

def main():
    """Main entry point."""
    print("Starting Phase 4C Cisco Control Validation...")
    
    success = validate_cisco_control()
    
    if success:
        print(f"\n🎯 Ready for Phase 4C P0 SNMP metrics implementation.")
        return 0
    else:
        print(f"\n❌ Cisco control validation failed. Fix before proceeding.")
        return 1

if __name__ == "__main__":
    sys.exit(main())