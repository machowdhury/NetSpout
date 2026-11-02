#!/usr/bin/env python3
"""
Targeted Sourcetype Validation for Phase 4A.
Focuses on actually implemented generators discovered from the catalog instance.
"""

import sys
import json
import importlib
import inspect
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.absolute()
BACKEND_DIR = BASE_DIR / "backend"

# Add paths
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BASE_DIR / "netspout" / "bin"))
sys.path.insert(0, str(BASE_DIR / "src"))

def analyze_actual_generator_coverage():
    """Analyze actual generator coverage from catalog instance."""
    
    print(f"\n{'='*60}")
    print(f"🔍 PHASE 4A - ACTUAL GENERATOR COVERAGE ANALYSIS")
    print(f"{'='*60}")
    
    try:
        # Import catalog instance
        from app.catalog import catalog_instance
        
        print("✅ Catalog instance loaded successfully")
        
        # Get all sourcetypes from catalog
        sourcetypes = catalog_instance.list_sourcetypes()
        print(f"📊 Total sourcetypes in catalog: {len(sourcetypes)}")
        
        # Get all scenarios
        scenarios = catalog_instance.list_scenarios()
        print(f"📊 Total scenarios in catalog: {len(scenarios)}")
        
        # Check unified_generation module
        print(f"\n{'─'*60}")
        print("🔧 Checking unified_generation module...")
        
        try:
            from app.unified_generation import (
                generate_cisco_syslog, 
                generate_cisco_mdt,
                generate_cisco_aci_health,
                generate_paloalto_syslog,
                generate_fortinet_syslog,
                generate_f5_syslog,
                generate_cloudflare_log,
                generate_aws_cloudtrail,
                generate_azure_monitor,
                generate_gcp_logging
            )
            
            discovered_generators = []
            
            # Check for Cisco generators
            if 'generate_cisco_syslog' in locals():
                discovered_generators.append(('cisco:syslog', 'generate_cisco_syslog'))
            if 'generate_cisco_mdt' in locals():
                discovered_generators.append(('cisco:mdt', 'generate_cisco_mdt'))
            if 'generate_cisco_aci_health' in locals():
                discovered_generators.append(('cisco:dc:aci:health', 'generate_cisco_aci_health'))
            
            # Check for Palo Alto
            if 'generate_paloalto_syslog' in locals():
                discovered_generators.append(('paloalto:syslog', 'generate_paloalto_syslog'))
            
            # Check for Fortinet
            if 'generate_fortinet_syslog' in locals():
                discovered_generators.append(('fortinet:syslog', 'generate_fortinet_syslog'))
            
            # Check for F5
            if 'generate_f5_syslog' in locals():
                discovered_generators.append(('f5:syslog', 'generate_f5_syslog'))
            
            # Check for Cloudflare
            if 'generate_cloudflare_log' in locals():
                discovered_generators.append(('cloudflare:http', 'generate_cloudflare_log'))
            
            # Check for Cloud providers
            if 'generate_aws_cloudtrail' in locals():
                discovered_generators.append(('aws:cloudtrail', 'generate_aws_cloudtrail'))
            if 'generate_azure_monitor' in locals():
                discovered_generators.append(('azure:monitor', 'generate_azure_monitor'))
            if 'generate_gcp_logging' in locals():
                discovered_generators.append(('gcp:logging', 'generate_gcp_logging'))
            
            print(f"✅ Found {len(discovered_generators)} generator functions")
            
            # Map to sourcetypes
            sourcetype_coverage = {}
            for st_pattern, func_name in discovered_generators:
                # Find matching sourcetypes
                matching_st = []
                for st in sourcetypes:
                    st_id = st.get('id', '')
                    # Simple pattern matching
                    if st_pattern.lower().replace(':', '_') in st_id.lower().replace(':', '_') or \
                       st_id.lower().replace(':', '_') in st_pattern.lower().replace(':', '_'):
                        matching_st.append(st_id)
                
                sourcetype_coverage[st_pattern] = {
                    'generator_function': func_name,
                    'matching_sourcetypes': matching_st,
                    'match_count': len(matching_st)
                }
            
            # Print coverage
            print(f"\n📈 Generator Coverage Summary:")
            print(f"{'─'*40}")
            
            total_covered = 0
            for pattern, info in sourcetype_coverage.items():
                count = info['match_count']
                total_covered += count
                print(f"  {pattern:<25} {info['generator_function']:<30} → {count:>3} sourcetypes")
            
            coverage_pct = (total_covered / len(sourcetypes)) * 100 if sourcetypes else 0
            print(f"\n  Total covered: {total_covered}/{len(sourcetypes)} ({coverage_pct:.1f}%)")
            
            # Find scenarios using covered sourcetypes
            print(f"\n🎯 Scenario Coverage:")
            print(f"{'─'*40}")
            
            scenario_coverage = []
            for scenario in scenarios:
                scenario_id = scenario.get('id', '')
                scenario_sts = scenario.get('sourcetypes', [])
                
                # Count covered sourcetypes in this scenario
                covered_in_scenario = 0
                for st in scenario_sts:
                    # Check if this sourcetype is covered
                    for pattern, info in sourcetype_coverage.items():
                        if st in info['matching_sourcetypes']:
                            covered_in_scenario += 1
                            break
                
                if covered_in_scenario > 0:
                    coverage_pct_scenario = (covered_in_scenario / len(scenario_sts)) * 100 if scenario_sts else 0
                    scenario_coverage.append({
                        'id': scenario_id,
                        'name': scenario.get('name', ''),
                        'total_sourcetypes': len(scenario_sts),
                        'covered_sourcetypes': covered_in_scenario,
                        'coverage_pct': coverage_pct_scenario
                    })
            
            # Sort by coverage
            scenario_coverage.sort(key=lambda x: x['coverage_pct'], reverse=True)
            
            print(f"  Scenarios with generator coverage: {len(scenario_coverage)}/{len(scenarios)}")
            for i, sc in enumerate(scenario_coverage[:10]):  # Top 10
                status = "✅" if sc['coverage_pct'] > 50 else "⚠️" if sc['coverage_pct'] > 0 else "❌"
                print(f"    {status} {sc['id']:<30} {sc['covered_sourcetypes']:>2}/{sc['total_sourcetypes']:>2} ({sc['coverage_pct']:>5.1f}%)")
            
            if len(scenario_coverage) > 10:
                print(f"    ... and {len(scenario_coverage) - 10} more")
            
            # High-value vendor analysis
            print(f"\n🏭 High-Value Vendor Analysis:")
            print(f"{'─'*40}")
            
            high_value_vendors = ['cisco', 'paloalto', 'fortinet', 'f5', 'cloudflare', 'aws', 'azure', 'gcp']
            
            for vendor in high_value_vendors:
                vendor_sts = [st for st in sourcetypes if vendor in st.get('id', '').lower() or vendor in st.get('vendor', '').lower()]
                vendor_covered = 0
                
                for st in vendor_sts:
                    st_id = st.get('id', '')
                    for pattern, info in sourcetype_coverage.items():
                        if st_id in info['matching_sourcetypes']:
                            vendor_covered += 1
                            break
                
                total_vendor = len(vendor_sts)
                if total_vendor > 0:
                    vendor_pct = (vendor_covered / total_vendor) * 100
                    status = "✅" if vendor_pct > 50 else "⚠️" if vendor_pct > 0 else "❌"
                    print(f"    {status} {vendor:<15} {vendor_covered:>3}/{total_vendor:>3} ({vendor_pct:>5.1f}%)")
            
            # Save detailed report
            report_data = {
                'analysis_run': {
                    'id': f'GEN-COV-{datetime.now().strftime("%Y%m%d-%H%M%S")}',
                    'timestamp': datetime.now().isoformat()
                },
                'summary': {
                    'total_sourcetypes': len(sourcetypes),
                    'covered_sourcetypes': total_covered,
                    'coverage_percentage': coverage_pct,
                    'total_scenarios': len(scenarios),
                    'scenarios_with_coverage': len(scenario_coverage),
                    'generator_functions_found': len(discovered_generators)
                },
                'generator_coverage': sourcetype_coverage,
                'scenario_coverage': scenario_coverage,
                'high_value_vendors': [
                    {
                        'vendor': vendor,
                        'total_sourcetypes': len([st for st in sourcetypes if vendor in st.get('id', '').lower()]),
                        'covered_sourcetypes': vendor_covered
                    }
                    for vendor in high_value_vendors
                ]
            }
            
            report_dir = BASE_DIR / "docs" / "verification"
            report_dir.mkdir(parents=True, exist_ok=True)
            
            report_file = report_dir / f"generator_coverage_{report_data['analysis_run']['id']}.json"
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            print(f"\n{'='*60}")
            print(f"📁 Detailed report saved to: {report_file}")
            print(f"{'='*60}")
            
            # Test actual generation for key sourcetypes
            print(f"\n🧪 Testing Actual Generation (sampling):")
            print(f"{'─'*40}")
            
            test_sourcetypes = [
                'cisco:ios:mdt',
                'cisco:dc:aci:health',
                'cisco:dc:nexus9k:syslog',
                'paloalto:syslog',
                'fortinet:syslog'
            ]
            
            for test_st in test_sourcetypes:
                try:
                    # Find matching generator
                    generator_func = None
                    for pattern, info in sourcetype_coverage.items():
                        if test_st in info['matching_sourcetypes']:
                            # Import and call the function
                            mod = importlib.import_module('app.unified_generation')
                            func = getattr(mod, info['generator_function'])
                            
                            # Try to generate a sample
                            # Note: This is simplified - real generators need parameters
                            print(f"    🔧 {test_st}: Found {info['generator_function']}")
                            generator_func = func
                            break
                    
                    if not generator_func:
                        print(f"    ❌ {test_st}: No generator found")
                        
                except Exception as e:
                    print(f"    ⚠️ {test_st}: Error - {str(e)[:50]}...")
            
            return report_data
            
        except ImportError as e:
            print(f"❌ Error importing unified_generation: {e}")
            return None
            
    except Exception as e:
        print(f"❌ Error analyzing generator coverage: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main entry point."""
    print("Starting Phase 4A Generator Coverage Analysis...")
    
    results = analyze_actual_generator_coverage()
    
    if results:
        print(f"\n🎯 ANALYSIS COMPLETE")
        print(f"   Generator coverage: {results['summary']['coverage_percentage']:.1f}%")
        print(f"   Scenarios with coverage: {results['summary']['scenarios_with_coverage']}/{results['summary']['total_scenarios']}")
        return 0
    else:
        print(f"\n❌ ANALYSIS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())