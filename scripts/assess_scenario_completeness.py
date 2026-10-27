#!/usr/bin/env python3
"""
Assess scenario completeness for PulseForge transformation into Splunk-native demo platform.
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

def assess_sources():
    """Assess all sources for completeness requirements."""
    # Load data
    universe = load_json(ROOT / 'catalog' / 'universe_batch4.json')
    vendor_universe = load_json(ROOT / 'catalog' / 'vendor_universe.json')
    dashboard_recipes = load_json(ROOT / 'netspout' / 'bin' / 'netspout_core' / 'catalog_data' / 'dashboard_recipes.json')
    
    sources = universe.get('sources', [])
    scenarios = universe.get('scenarios', {})
    
    print("=" * 80)
    print("PULSEFORGE SCENARIO COMPLETENESS ASSESSMENT")
    print("=" * 80)
    
    # Track completeness metrics
    metrics = {
        'total_sources': len(sources),
        'with_scenario': 0,
        'with_generator': 0,
        'with_spl_mapping': 0,
        'with_dashboard': 0,
        'with_verification': 0,
        'fully_complete': 0
    }
    
    # Check scenario runner for executable scenarios
    scenario_runner_path = ROOT / 'src' / 'netspout_core' / 'scenario_runner.py'
    scenario_runner_content = scenario_runner_path.read_text() if scenario_runner_path.exists() else ""
    
    # Check authentic scenario packs
    authentic_packs_path = ROOT / 'src' / 'netspout_core' / 'authentic_scenario_packs.py'
    authentic_packs_content = authentic_packs_path.read_text() if authentic_packs_path.exists() else ""
    
    # Check each source
    for source in sources:
        source_id = source.get('batch_source_id', 'unknown')
        sourcetype = source.get('splunk_sourcetype', 'unknown')
        generator = source.get('generator', 'unknown')
        
        completeness = {
            'source_id': source_id,
            'sourcetype': sourcetype,
            'generator': generator,
            'has_scenario': False,
            'has_generator': False,
            'has_spl_mapping': False,
            'has_dashboard': False,
            'has_verification': False
        }
        
        # Check 1: Has executable scenario
        # Look for scenario packs that include this source
        for scenario_id, source_list in scenarios.items():
            if source_id in source_list:
                completeness['has_scenario'] = True
                metrics['with_scenario'] += 1
                break
        
        # Check 2: Has authentic generator
        if generator and generator != 'unknown':
            completeness['has_generator'] = True
            metrics['with_generator'] += 1
        
        # Check 3: Has SPL mapping (check dashboard recipes)
        for recipe in dashboard_recipes.get('recipes', []):
            required_sourcetypes = recipe.get('required_sourcetypes', [])
            if sourcetype in required_sourcetypes:
                completeness['has_spl_mapping'] = True
                metrics['with_spl_mapping'] += 1
                break
        
        # Check 4: Has dashboard visualization
        for recipe in dashboard_recipes.get('recipes', []):
            if recipe.get('query_template'):
                # Check if query template references this sourcetype
                if sourcetype in recipe['query_template']:
                    completeness['has_dashboard'] = True
                    metrics['with_dashboard'] += 1
                    break
        
        # Check 5: Has verification status (check coverage matrix)
        coverage_matrix = load_json(ROOT / 'catalog' / 'coverage_matrix.json')
        evidence_levels = coverage_matrix.get('evidence_levels', {})
        
        # SNMP verification
        if 'sc4snmp' in sourcetype or 'snmp' in source_id.lower():
            if evidence_levels.get('snmp', {}).get('generator_tested'):
                completeness['has_verification'] = True
        
        # YANG/OpenConfig verification  
        elif 'openconfig' in sourcetype.lower() or 'gnmi' in source_id.lower():
            if evidence_levels.get('yang', {}).get('generator_implemented'):
                completeness['has_verification'] = True
        
        # Batch 4 verification
        elif evidence_levels.get('batch4', {}).get('live_raw_equality_verified'):
            completeness['has_verification'] = True
        
        if completeness['has_verification']:
            metrics['with_verification'] += 1
        
        # Check if fully complete
        if all([completeness['has_scenario'], completeness['has_generator'], 
                completeness['has_spl_mapping'], completeness['has_dashboard'], 
                completeness['has_verification']]):
            metrics['fully_complete'] += 1
        
        # Print source assessment
        if not all(completeness.values()):
            print(f"\n🔍 Source: {source_id} ({sourcetype})")
            print(f"   Generator: {generator}")
            missing = []
            for key, value in completeness.items():
                if key.startswith('has_') and not value:
                    missing.append(key.replace('has_', ''))
            if missing:
                print(f"   Missing: {', '.join(missing)}")
    
    # Print summary
    print(f"\n{'='*80}")
    print("COMPLETENESS SUMMARY")
    print(f"{'='*80}")
    print(f"Total sources: {metrics['total_sources']}")
    print(f"  With scenario: {metrics['with_scenario']} ({metrics['with_scenario']/metrics['total_sources']*100:.1f}%)")
    print(f"  With generator: {metrics['with_generator']} ({metrics['with_generator']/metrics['total_sources']*100:.1f}%)")
    print(f"  With SPL mapping: {metrics['with_spl_mapping']} ({metrics['with_spl_mapping']/metrics['total_sources']*100:.1f}%)")
    print(f"  With dashboard: {metrics['with_dashboard']} ({metrics['with_dashboard']/metrics['total_sources']*100:.1f}%)")
    print(f"  With verification: {metrics['with_verification']} ({metrics['with_verification']/metrics['total_sources']*100:.1f}%)")
    print(f"  Fully complete: {metrics['fully_complete']} ({metrics['fully_complete']/metrics['total_sources']*100:.1f}%)")
    
    # Check dashboard recipes
    print(f"\n{'='*80}")
    print("DASHBOARD RECIPES ASSESSMENT")
    print(f"{'='*80}")
    
    recipes = dashboard_recipes.get('recipes', [])
    print(f"Total recipes: {len(recipes)}")
    
    recipes_with_spl = sum(1 for r in recipes if r.get('query_template'))
    recipes_with_visualizations = sum(1 for r in recipes if r.get('visualization_ids'))
    
    print(f"Recipes with SPL: {recipes_with_spl}/{len(recipes)}")
    print(f"Recipes with visualizations: {recipes_with_visualizations}/{len(recipes)}")
    
    # Check for visualization compatibility
    visualizations = dashboard_recipes.get('visualizations', [])
    verified_viz = sum(1 for v in visualizations if v.get('compatibility') == 'VERIFIED')
    documented_viz = sum(1 for v in visualizations if v.get('compatibility') == 'DOCUMENTED')
    
    print(f"\nVisualizations: {len(visualizations)} total")
    print(f"  Verified: {verified_viz}")
    print(f"  Documented: {documented_viz}")
    print(f"  Not verified: {len(visualizations) - verified_viz - documented_viz}")
    
    return metrics

def identify_gaps():
    """Identify gaps in the implementation."""
    print(f"\n{'='*80}")
    print("CRITICAL GAPS IDENTIFIED")
    print(f"{'='*80}")
    
    # Load data
    universe = load_json(ROOT / 'catalog' / 'universe_batch4.json')
    sources = universe.get('sources', [])
    
    gaps = {
        'missing_scenarios': [],
        'missing_generators': [],
        'missing_spl_mappings': [],
        'missing_dashboards': [],
        'missing_verification': []
    }
    
    for source in sources:
        source_id = source.get('batch_source_id', 'unknown')
        sourcetype = source.get('splunk_sourcetype', 'unknown')
        generator = source.get('generator', 'unknown')
        
        # Check for obvious gaps
        if not generator or generator == 'unknown':
            gaps['missing_generators'].append(f"{source_id} ({sourcetype})")
        
        # Check if it's a Batch 4 source without clear scenario
        scenarios = universe.get('scenarios', {})
        has_scenario = any(source_id in source_list for source_list in scenarios.values())
        
        if not has_scenario:
            gaps['missing_scenarios'].append(f"{source_id} ({sourcetype})")
    
    # Print gaps
    for gap_type, items in gaps.items():
        if items:
            print(f"\n{gap_type.replace('_', ' ').title()}:")
            for item in items[:10]:  # Show first 10
                print(f"  • {item}")
            if len(items) > 10:
                print(f"  ... and {len(items)-10} more")
    
    return gaps

def main():
    print("Assessing PulseForge scenario completeness...")
    metrics = assess_sources()
    gaps = identify_gaps()
    
    # Generate recommendations
    print(f"\n{'='*80}")
    print("RECOMMENDATIONS FOR SPLUNK-NATIVE DEMO PLATFORM")
    print(f"{'='*80}")
    
    total_sources = metrics['total_sources']
    
    if metrics['fully_complete'] < total_sources * 0.8:  # Less than 80% complete
        print("🚨 PRIORITY: Focus on completing end-to-end coverage for key sources")
        print("  1. Select 5-10 high-impact sources (e.g., SNMP, OpenConfig, critical SaaS)")
        print("  2. Ensure each has:")
        print("     • Authentic generator")
        print("     • Executable scenario")
        print("     • Dashboard visualization")
        print("     • Verification evidence")
    
    if metrics['with_dashboard'] < total_sources * 0.5:
        print("\n📊 PRIORITY: Expand dashboard coverage")
        print("  1. Create dashboard recipes for missing sourcetypes")
        print("  2. Ensure each recipe includes:")
        print("     • Valid SPL query template")
        print("     • Appropriate visualizations")
        print("     • Drilldown capabilities")
    
    if metrics['with_verification'] < total_sources * 0.7:
        print("\n✅ PRIORITY: Strengthen verification evidence")
        print("  1. Document verification status for each source")
        print("  2. Include evidence levels:")
        print("     • Schema verified")
        print("     • Generator implemented")
        print("     • Generator tested")
        print("     • Splunk ingestion verified")
    
    print(f"\n{'='*80}")
    print("NEXT STEPS")
    print(f"{'='*80}")
    print("1. Create missing scenario packs for sources without scenarios")
    print("2. Enhance dashboard recipes with complete SPL and visualizations")
    print("3. Generate verification evidence for all sources")
    print("4. Build actual dashboard JSON exports for Splunk Dashboard Studio")
    print("5. Create documentation demonstrating end-to-end flow")

if __name__ == '__main__':
    main()