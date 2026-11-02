#!/usr/bin/env python3
"""
Comprehensive coverage assessment for all PulseForge sourcetypes.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set
import re

ROOT = Path(__file__).resolve().parents[1]

def load_json(path: Path) -> Any:
    with open(path, 'r') as f:
        return json.load(f)

def get_all_sourcetypes():
    """Get all sourcetypes from the system."""
    sourcetypes = set()
    
    # Load vendor universe
    vendor_universe = load_json(ROOT / 'catalog' / 'vendor_universe.json')
    for vendor_data in vendor_universe.get('vendors', {}).values():
        for platform in vendor_data.get('platforms', []):
            for protocol in platform.get('protocols', []):
                if 'sourcetype' in protocol:
                    sourcetypes.add(protocol['sourcetype'])
    
    # Load Batch 4 sources
    universe = load_json(ROOT / 'catalog' / 'universe_batch4.json')
    for source in universe.get('sources', []):
        if 'splunk_sourcetype' in source:
            sourcetypes.add(source['splunk_sourcetype'])
    
    # Load telemetry catalog
    telemetry_catalog_path = ROOT / 'netspout' / 'bin' / 'netspout_core' / 'catalog_data' / 'telemetry_catalog.json'
    if telemetry_catalog_path.exists():
        telemetry_catalog = load_json(telemetry_catalog_path)
        for entry in telemetry_catalog.get('sources', []):
            if 'sourcetype' in entry:
                sourcetypes.add(entry['sourcetype'])
    
    return sorted(list(sourcetypes))

def assess_sourcetype_completeness(sourcetype: str) -> Dict[str, bool]:
    """Assess completeness for a single sourcetype."""
    assessment = {
        'sourcetype': sourcetype,
        'has_generator': False,
        'has_scenario': False,
        'has_spl_query': False,
        'has_dashboard': False,
        'has_verification': False,
        'has_cim_mapping': False
    }
    
    # Load data
    dashboard_recipes = load_json(ROOT / 'netspout' / 'bin' / 'netspout_core' / 'catalog_data' / 'dashboard_recipes.json')
    
    # Check 1: Has generator
    # Look in scenario_runner.py and authentic_scenario_packs.py
    scenario_runner_path = ROOT / 'src' / 'netspout_core' / 'scenario_runner.py'
    if scenario_runner_path.exists():
        content = scenario_runner_path.read_text()
        # Check for sourcetype references
        if sourcetype.lower().replace(':', '_') in content.lower():
            assessment['has_generator'] = True
    
    # Check 2: Has scenario
    universe = load_json(ROOT / 'catalog' / 'universe_batch4.json')
    for source in universe.get('sources', []):
        if source.get('splunk_sourcetype') == sourcetype:
            # Check if source is in any scenario
            source_id = source.get('batch_source_id', '')
            for scenario_sources in universe.get('scenarios', {}).values():
                if source_id in scenario_sources:
                    assessment['has_scenario'] = True
                    break
    
    # Check 3: Has SPL query
    for recipe in dashboard_recipes.get('recipes', []):
        if sourcetype in recipe.get('required_sourcetypes', []):
            if recipe.get('query_template'):
                assessment['has_spl_query'] = True
                break
    
    # Check 4: Has dashboard
    for recipe in dashboard_recipes.get('recipes', []):
        if sourcetype in recipe.get('required_sourcetypes', []):
            assessment['has_dashboard'] = True
            break
    
    # Check 5: Has verification
    coverage_matrix = load_json(ROOT / 'catalog' / 'coverage_matrix.json')
    evidence_levels = coverage_matrix.get('evidence_levels', {})
    
    # Check SNMP verification
    if 'sc4snmp' in sourcetype.lower():
        if evidence_levels.get('snmp', {}).get('generator_tested'):
            assessment['has_verification'] = True
    
    # Check YANG/OpenConfig verification
    elif 'openconfig' in sourcetype.lower():
        if evidence_levels.get('yang', {}).get('generator_implemented'):
            assessment['has_verification'] = True
    
    # Check Batch 4 verification
    elif evidence_levels.get('batch4', {}).get('live_raw_equality_verified'):
        assessment['has_verification'] = True
    
    # Check 6: Has CIM mapping (simplified check)
    # Look for CIM references in dashboard recipes
    for recipe in dashboard_recipes.get('recipes', []):
        if sourcetype in recipe.get('required_sourcetypes', []):
            query = recipe.get('query_template', '')
            if 'cim_' in query.lower() or 'datamodel' in query.lower():
                assessment['has_cim_mapping'] = True
                break
    
    return assessment

def main():
    print("Comprehensive PulseForge Coverage Assessment")
    print("=" * 80)
    
    # Get all sourcetypes
    sourcetypes = get_all_sourcetypes()
    print(f"Total sourcetypes identified: {len(sourcetypes)}")
    
    # Assess each sourcetype
    assessments = []
    for st in sourcetypes[:50]:  # Limit to first 50 for performance
        assessment = assess_sourcetype_completeness(st)
        assessments.append(assessment)
    
    # Calculate metrics
    total_assessed = len(assessments)
    metrics = {
        'has_generator': sum(1 for a in assessments if a['has_generator']),
        'has_scenario': sum(1 for a in assessments if a['has_scenario']),
        'has_spl_query': sum(1 for a in assessments if a['has_spl_query']),
        'has_dashboard': sum(1 for a in assessments if a['has_dashboard']),
        'has_verification': sum(1 for a in assessments if a['has_verification']),
        'has_cim_mapping': sum(1 for a in assessments if a['has_cim_mapping']),
        'fully_complete': sum(1 for a in assessments if all([
            a['has_generator'], a['has_scenario'], a['has_spl_query'],
            a['has_dashboard'], a['has_verification'], a['has_cim_mapping']
        ]))
    }
    
    # Print metrics
    print(f"\nASSESSMENT METRICS (first {total_assessed} sourcetypes):")
    print(f"{'='*80}")
    for key, value in metrics.items():
        percentage = (value / total_assessed * 100) if total_assessed > 0 else 0
        print(f"{key.replace('_', ' ').title():<20} {value:>3}/{total_assessed:>3} ({percentage:5.1f}%)")
    
    # Identify high-priority sourcetypes (common ones)
    priority_sourcetypes = [
        'sc4snmp:metric',
        'sc4snmp:event',
        'cisco:ise:syslog',
        'openconfig-gnmi-interfaces',
        'slack:audit',
        'github:enterprise:audit'
    ]
    
    print(f"\n{'='*80}")
    print("PRIORITY SOURCETYPES ASSESSMENT:")
    print(f"{'='*80}")
    
    for st in priority_sourcetypes:
        if st in sourcetypes:
            idx = sourcetypes.index(st)
            if idx < len(assessments):
                assessment = assessments[idx]
                print(f"\n{st}:")
                missing = []
                for key, value in assessment.items():
                    if key.startswith('has_') and not value:
                        missing.append(key.replace('has_', ''))
                if missing:
                    print(f"  Missing: {', '.join(missing)}")
                else:
                    print(f"  ✅ Complete")
    
    # Recommendations
    print(f"\n{'='*80}")
    print("RECOMMENDATIONS:")
    print(f"{'='*80}")
    
    if metrics['fully_complete'] / total_assessed < 0.3:
        print("🚨 HIGH PRIORITY: Focus on end-to-end completeness for key sourcetypes")
        print("   Select 5-10 high-impact sourcetypes and ensure:")
        print("   1. Authentic generator exists")
        print("   2. Executable scenario available")
        print("   3. SPL query templates")
        print("   4. Dashboard visualization")
        print("   5. Verification evidence")
        print("   6. CIM mapping where applicable")
    
    if metrics['has_spl_query'] / total_assessed < 0.5:
        print("\n📊 MEDIUM PRIORITY: Expand SPL query coverage")
        print("   Add query templates to dashboard recipes for missing sourcetypes")
    
    if metrics['has_cim_mapping'] / total_assessed < 0.2:
        print("\n🗺️  MEDIUM PRIORITY: Add CIM mappings")
        print("   Enhance SPL queries with CIM data model references")
    
    print(f"\n{'='*80}")
    print("ACTION PLAN:")
    print(f"{'='*80}")
    print("1. Select 5 priority sourcetypes for end-to-end completion")
    print("2. Create missing generators/scenarios for selected sourcetypes")
    print("3. Enhance dashboard recipes with complete SPL and visualizations")
    print("4. Generate verification evidence")
    print("5. Create actual dashboard JSON exports")
    print("6. Document the complete flow for demonstration")

if __name__ == '__main__':
    main()