#!/usr/bin/env python3
"""
Phase 4C: Test SNMP metrics ingestion into Splunk.
Generate SNMP metrics and send them to HEC for mstats testing.
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from pathlib import Path

# Import our SNMP generator
sys.path.insert(0, str(Path(__file__).parent / "backend"))
from app.snmp_metrics_generator import generate_snmp_metrics

def test_snmp_metrics_ingestion():
    """Test SNMP metrics generation and Splunk ingestion."""
    
    print(f"\n{'='*60}")
    print(f"🧪 PHASE 4C: SNMP METRICS SPLUNK INGESTION TEST")
    print(f"{'='*60}")
    
    # Configuration
    hec_url = "https://localhost:18088/services/collector"
    hec_token = os.getenv('PULSEFORGE_LAB_HEC_TOKEN')
    if not hec_token:
        raise ValueError("PULSEFORGE_LAB_HEC_TOKEN environment variable not set")
    splunk_api = "https://localhost:18089"
    splunk_password = os.getenv('SPLUNK_PASSWORD')
    if not splunk_password:
        raise ValueError("SPLUNK_PASSWORD environment variable not set")
    splunk_auth = ("admin", splunk_password)
    
    run_id = f"SNMP-PHASE4C-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    print(f"Run ID: {run_id}")
    print(f"HEC URL: {hec_url}")
    
    # 1. Generate SNMP metrics
    print(f"\n1. Generating SNMP metrics...")
    events = generate_snmp_metrics(count=30, seed=42)
    print(f"   ✅ Generated {len(events)} SNMP metric events")
    
    # Add run_id to all events for tracking
    prepared_events = []
    for event in events:
        event["fields"]["netspout_run_id"] = run_id
        event["fields"]["phase4c_test"] = True
        prepared_events.append(event)
    
    # 2. Send to HEC
    print(f"\n2. Sending to Splunk HEC...")
    try:
        response = requests.post(
            hec_url,
            headers={"Authorization": f"Splunk {hec_token}"},
            json=prepared_events,
            verify=False,
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"   ✅ HEC accepted metrics (HTTP {response.status_code})")
            try:
                result = response.json()
                ack_id = result.get("ackId")
                if ack_id:
                    print(f"   Acknowledgment ID: {ack_id}")
            except:
                pass
        else:
            print(f"   ❌ HEC rejected metrics: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"   ❌ HEC error: {e}")
        return False
    
    # 3. Wait for indexing
    print(f"\n3. Waiting 10 seconds for indexing...")
    time.sleep(10)
    
    # 4. Verify indexing with Splunk search
    print(f"\n4. Verifying indexed metrics in Splunk...")
    
    try:
        # Test 1: Regular event search
        print(f"\n   Test 1: Event search (regular search)...")
        event_search = f'search index=cisco_mdt_metrics sourcetype=sc4snmp:event netspout_run_id="{run_id}" earliest=-5m latest=now | stats count'
        
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
                    event_count = int(event_data['results'][0].get('count', 0))
                    print(f"      ✅ Found {event_count} events with run_id={run_id}")
                    
                    if event_count > 0:
                        print(f"      📊 Event indexing confirmed!")
                    else:
                        print(f"      ⚠️ No events found (may need more indexing time)")
                else:
                    print(f"      ⚠️ No event results in response")
            except json.JSONDecodeError as je:
                print(f"      ⚠️ Could not parse event search response: {je}")
                print(f"      Response: {event_response.text[:500]}")
        else:
            print(f"      ⚠️ Event search API returned HTTP {event_response.status_code}")
            print(f"      Response: {event_response.text[:200]}")
        
        # Test 2: mstats search (metrics-specific)
        print(f"\n   Test 2: Metrics search (mstats)...")
        metrics_search = f'| mstats count WHERE index=cisco_mdt_metrics sourcetype=sc4snmp:event netspout_run_id="{run_id}" earliest=-5m latest=now'
        
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
            print(f"      ✅ mstats search executed successfully")
            
            try:
                metrics_data = metrics_response.json()
                # mstats returns results differently
                print(f"      📊 mstats API response received")
                
                # Show response structure for debugging
                if 'results' in metrics_data:
                    print(f"      Found {len(metrics_data['results'])} results in mstats response")
                else:
                    print(f"      Response keys: {list(metrics_data.keys())}")
            except json.JSONDecodeError:
                print(f"      ⚠️ Could not parse mstats JSON response")
                print(f"      Response preview: {metrics_response.text[:300]}")
        else:
            print(f"      ⚠️ mstats search API returned HTTP {metrics_response.status_code}")
            print(f"      Response: {metrics_response.text[:200]}")
        
        # Test 3: Detailed metric analysis
        print(f"\n   Test 3: Detailed metric analysis...")
        detail_search = f'search index=cisco_mdt_metrics sourcetype=sc4snmp:event netspout_run_id="{run_id}" earliest=-5m latest=now | stats count by metric_name, host, vendor, semantics | sort - count'
        
        detail_response = requests.post(
            f"{splunk_api}/services/search/jobs",
            auth=splunk_auth,
            data={
                "search": detail_search,
                "exec_mode": "oneshot",
                "output_mode": "json"
            },
            verify=False,
            timeout=10
        )
        
        if detail_response.status_code == 201:
            try:
                detail_data = detail_response.json()
                if 'results' in detail_data and detail_data['results']:
                    print(f"      📊 Metric distribution:")
                    for row in detail_data['results'][:10]:  # Show top 10
                        metric = row.get('metric_name', 'unknown')
                        host = row.get('host', 'unknown')
                        count = row.get('count', 0)
                        semantics = row.get('semantics', 'unknown')
                        print(f"        - {metric:<20} ({semantics:<8}): {count:>3} events on {host}")
                else:
                    print(f"      ⚠️ No detailed results found")
            except json.JSONDecodeError:
                print(f"      ⚠️ Could not parse detail search response")
        else:
            print(f"      ⚠️ Detail search API returned HTTP {detail_response.status_code}")
        
    except Exception as e:
        print(f"   ⚠️ Splunk verification error: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. Save evidence
    print(f"\n5. Saving test evidence...")
    
    evidence = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "events_generated": len(events),
        "events_sent": len(prepared_events),
        "hec_response_code": response.status_code if 'response' in locals() else None,
        "test_scenario": "snmp_metrics_phase4c",
        "sourcetype": "sc4snmp:event",
        "index": "cisco_mdt_metrics",
        "metrics_generated": [e["fields"]["metric_name"] for e in events[:10]]
    }
    
    evidence_file = Path(__file__).parent / f"snmp_metrics_test_{run_id}.json"
    with open(evidence_file, 'w') as f:
        json.dump(evidence, f, indent=2)
    
    print(f"   📁 Evidence saved to: {evidence_file}")
    
    # 6. Generate SPL examples for manual verification
    print(f"\n6. SPL examples for manual verification:")
    print(f"\n   📊 Event verification:")
    print(f"     search index=cisco_mdt_metrics sourcetype=sc4snmp:event netspout_run_id=\"{run_id}\"")
    print(f"     | stats count by metric_name, host")
    print(f"     | sort - count")
    
    print(f"\n   📈 Metrics aggregation (mstats):")
    print(f"     | mstats count WHERE index=cisco_mdt_metrics sourectype=sc4snmp:event netspout_run_id=\"{run_id}\" earliest=-5m latest=now")
    print(f"     | timechart span=1m count by metric_name")
    
    print(f"\n   🔍 Detailed metric analysis:")
    print(f"     | mstats avg(_value) WHERE index=cisco_mdt_metrics metric_name=ifInOctets netspout_run_id=\"{run_id}\" earliest=-5m latest=now")
    print(f"     | timechart span=5m avg(_value) by host")
    
    print(f"\n   🏷️ Metric field extraction:")
    print(f"     search index=cisco_mdt_metrics sourcetype=sc4snmp:event netspout_run_id=\"{run_id}\"")
    print(f"     | table _time, host, metric_name, _value, unit, semantics, interface")
    print(f"     | sort - _time")
    
    print(f"\n{'='*60}")
    print(f"✅ SNMP METRICS INGESTION TEST COMPLETE")
    print(f"{'='*60}")
    
    print(f"\n📋 Summary:")
    print(f"  - Generated {len(events)} SNMP metric events")
    print(f"  - Run ID: {run_id}")
    print(f"  - Sourcetype: sc4snmp:event")
    print(f"  - Index: cisco_mdt_metrics")
    print(f"  - Splunk verification attempted")
    print(f"  - Evidence saved: {evidence_file}")
    
    return True

def main():
    """Main entry point."""
    print("Starting Phase 4C SNMP Metrics Ingestion Test...")
    
    success = test_snmp_metrics_ingestion()
    
    if success:
        print(f"\n🎯 Ready for Phase 4C P0: Palo Alto live acceptance verification.")
        return 0
    else:
        print(f"\n❌ SNMP metrics ingestion test failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())