#!/usr/bin/env python3
"""
Analyze actual coverage from catalog and successful control run.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.absolute()
BACKEND_DIR = BASE_DIR / "backend"

# Add paths
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BASE_DIR / "netspout" / "bin"))
sys.path.insert(0, str(BASE_DIR / "src"))

def main():
    print(f"\n{'='*60}")
    print(f"🔍 PHASE 4A - ACTUAL COVERAGE ANALYSIS FROM CONTROL RUN")
    print(f"{'='*60}")
    
    # 1. Load catalog data directly
    sourcetypes_path = BACKEND_DIR / "app" / "catalog_data" / "sourcetypes.json"
    scenarios_path = BACKEND_DIR / "app" / "catalog_data" / "scenarios.json"
    
    with open(sourcetypes_path, 'r') as f:
        sourcetypes = json.load(f)
    
    with open(scenarios_path, 'r') as f:
        scenarios = json.load(f)
    
    print(f"📊 Catalog Data Loaded:")
    print(f"   Sourcetypes: {len(sourcetypes)}")
    print(f"   Scenarios: {len(scenarios)}")
    
    # 2. Analyze control run sourcetypes
    print(f"\n{'─'*60}")
    print(f"🎯 CONTROL RUN SOURCETYPES (cisco_aci_microburst):")
    
    # Find the scenario
    cisco_scenario = None
    for scenario in scenarios:
        if scenario.get('id') == 'cisco_aci_microburst':
            cisco_scenario = scenario
            break
    
    if cisco_scenario:
        scenario_sourcetypes = cisco_scenario.get('sourcetypes', [])
        print(f"   Scenario uses {len(scenario_sourcetypes)} sourcetypes:")
        
        for st_id in scenario_sourcetypes:
            # Find sourcetype details
            st_details = None
            for st in sourcetypes:
                if st.get('id') == st_id:
                    st_details = st
                    break
            
            vendor = st_details.get('vendor', 'unknown') if st_details else 'unknown'
            status = st_details.get('status', 'unknown') if st_details else 'unknown'
            print(f"     • {st_id}")
            print(f"       Vendor: {vendor}, Status: {status}")
    
    # 3. Analyze vendor distribution
    print(f"\n{'─'*60}")
    print(f"🏭 VENDOR DISTRIBUTION (348 sourcetypes):")
    
    vendor_counts = {}
    for st in sourcetypes:
        vendor = st.get('vendor', 'unknown')
        vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1
    
    # Sort by count
    sorted_vendors = sorted(vendor_counts.items(), key=lambda x: x[1], reverse=True)
    
    for vendor, count in sorted_vendors[:15]:  # Top 15
        pct = (count / len(sourcetypes)) * 100
        print(f"   {vendor:<25} {count:>4} ({pct:>5.1f}%)")
    
    # 4. Analyze status distribution
    print(f"\n{'─'*60}")
    print(f"📊 STATUS DISTRIBUTION:")
    
    status_counts = {}
    for st in sourcetypes:
        status = st.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    for status, count in sorted(status_counts.items()):
        pct = (count / len(sourcetypes)) * 100
        print(f"   {status:<20} {count:>4} ({pct:>5.1f}%)")
    
    # 5. Analyze high-value vendor coverage
    print(f"\n{'─'*60}")
    print(f"🎯 HIGH-VALUE VENDOR COVERAGE:")
    
    high_value_vendors = ['cisco', 'paloalto', 'fortinet', 'f5', 'cloudflare', 'aws', 'azure', 'gcp']
    
    for vendor in high_value_vendors:
        vendor_sts = [st for st in sourcetypes if vendor in st.get('id', '').lower() or vendor in st.get('vendor', '').lower()]
        active_sts = [st for st in vendor_sts if st.get('status') in ['active', 'implemented', 'experimental']]
        
        if vendor_sts:
            pct_active = (len(active_sts) / len(vendor_sts)) * 100 if vendor_sts else 0
            status = "✅" if pct_active > 50 else "⚠️" if pct_active > 0 else "❌"
            print(f"   {status} {vendor:<15} {len(active_sts):>3}/{len(vendor_sts):>3} active ({pct_active:>5.1f}%)")
    
    # 6. Check SNMP OID inventory
    print(f"\n{'─'*60}")
    print(f"📡 SNMP METRICS COVERAGE:")
    
    snmp_path = BACKEND_DIR / "app" / "catalog_data" / "snmp_mib_oid_inventory.json"
    if snmp_path.exists():
        with open(snmp_path, 'r') as f:
            snmp_data = json.load(f)
        
        oids = snmp_data.get('rows', [])
        print(f"   Found {len(oids)} SNMP OIDs in inventory")
        
        # Count vendors
        snmp_vendors = {}
        for oid in oids:
            vendor = oid.get('vendor', 'unknown')
            snmp_vendors[vendor] = snmp_vendors.get(vendor, 0) + 1
        
        print(f"   Vendor distribution (top 10):")
        for vendor, count in sorted(snmp_vendors.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"     {vendor:<20} {count:>4}")
    else:
        print(f"   ❌ SNMP inventory not found")
    
    # 7. Analyze scenario executability
    print(f"\n{'─'*60}")
    print(f"🎬 SCENARIO EXECUTABILITY ANALYSIS:")
    
    executable_scenarios = []
    blocked_scenarios = []
    
    for scenario in scenarios:
        scenario_id = scenario.get('id')
        sourcetypes_needed = scenario.get('sourcetypes', [])
        
        # Check if all needed sourcetypes are active
        all_active = True
        for st_id in sourcetypes_needed:
            st_details = next((st for st in sourcetypes if st.get('id') == st_id), None)
            if not st_details or st_details.get('status') not in ['active', 'implemented', 'experimental']:
                all_active = False
                break
        
        if all_active and sourcetypes_needed:
            executable_scenarios.append(scenario_id)
        else:
            blocked_scenarios.append(scenario_id)
    
    print(f"   Potentially executable: {len(executable_scenarios)}/{len(scenarios)}")
    print(f"   Blocked: {len(blocked_scenarios)}/{len(scenarios)}")
    
    print(f"\n   Top executable scenarios:")
    for i, scenario_id in enumerate(executable_scenarios[:10]):
        scenario = next((s for s in scenarios if s.get('id') == scenario_id), None)
        if scenario:
            st_count = len(scenario.get('sourcetypes', []))
            print(f"     {i+1:2}. {scenario_id:<30} ({st_count} sourcetypes)")
    
    # 8. Generate actionable findings
    print(f"\n{'='*60}")
    print(f"🔍 ACTIONABLE FINDINGS FOR PHASE 4A")
    print(f"{'='*60}")
    
    findings = []
    
    # Finding 1: Cisco coverage
    cisco_sts = [st for st in sourcetypes if 'cisco' in st.get('id', '').lower()]
    cisco_active = [st for st in cisco_sts if st.get('status') in ['active', 'implemented']]
    if cisco_active:
        findings.append(f"✅ Cisco has {len(cisco_active)}/{len(cisco_sts)} active sourcetypes - good foundation")
    
    # Finding 2: Missing high-value vendors
    for vendor in ['paloalto', 'fortinet', 'f5', 'cloudflare']:
        vendor_sts = [st for st in sourcetypes if vendor in st.get('id', '').lower()]
        vendor_active = [st for st in vendor_sts if st.get('status') in ['active', 'implemented']]
        if vendor_sts and len(vendor_active) == 0:
            findings.append(f"❌ {vendor.capitalize()} has {len(vendor_sts)} catalog entries but 0 active - blocker")
    
    # Finding 3: Scenario coverage
    if len(executable_scenarios) > 0:
        findings.append(f"✅ {len(executable_scenarios)} scenarios appear executable based on sourcetype status")
    else:
        findings.append(f"❌ No scenarios appear fully executable - critical blocker")
    
    # Finding 4: SNMP coverage
    if 'oids' in locals() and len(oids) > 0:
        findings.append(f"✅ {len(oids)} SNMP OIDs available - metrics foundation exists")
    
    # Print findings
    for i, finding in enumerate(findings, 1):
        print(f"  {i}. {finding}")
    
    # Save analysis
    report_dir = BASE_DIR / "docs" / "verification"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    report_data = {
        'analysis_run': {
            'id': f'COV-ANALYSIS-{datetime.now().strftime("%Y%m%d-%H%M%S")}',
            'timestamp': datetime.now().isoformat()
        },
        'summary': {
            'total_sourcetypes': len(sourcetypes),
            'total_scenarios': len(scenarios),
            'vendor_distribution': vendor_counts,
            'status_distribution': status_counts,
            'executable_scenarios': executable_scenarios,
            'blocked_scenarios': blocked_scenarios
        },
        'control_run_sourcetypes': scenario_sourcetypes if 'scenario_sourcetypes' in locals() else [],
        'high_value_vendor_analysis': {
            vendor: {
                'total': len([st for st in sourcetypes if vendor in st.get('id', '').lower()]),
                'active': len([st for st in sourcetypes if vendor in st.get('id', '').lower() and st.get('status') in ['active', 'implemented']])
            }
            for vendor in high_value_vendors
        },
        'findings': findings
    }
    
    report_file = report_dir / f"coverage_analysis_{report_data['analysis_run']['id']}.json"
    with open(report_file, 'w') as f:
        json.dump(report_data, f, indent=2, default=str)
    
    print(f"\n📁 Full analysis saved to: {report_file}")
    
    return report_data

if __name__ == "__main__":
    main()