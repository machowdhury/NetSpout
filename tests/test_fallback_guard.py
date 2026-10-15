"""Deterministic regression coverage for the release's scenario availability guard."""
import ast
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / 'backend', ROOT / 'src'):
    sys.path.insert(0, str(directory))

from netspout_core.catalog import NetSpoutCatalog
from netspout_core.models import ScenarioRunRequest
from netspout_core.scenario_runner import ScenarioRunner, SUPPORTED_SCENARIO_IDS

SUPPORTED = frozenset((
    'arch_lan_campus_access', 'arch_man_carrier_ring', 'arch_vpn_remote_workforce',
    'arch_wlan_meraki_catalyst', 'cisco_aci_microburst', 'cisco_campus_rogue',
    'cisco_sdwan_brownout', 'mixed_backbone_optical', 'mixed_edge_breach',
    'mixed_sase_degradation', 'openconfig_mdt_streaming', 'service_provider_cisco',
    'sql_injection', 'ddos_attack',
))
LOOKALIKES = ('does_not_exist', 'sdwan_custom_branch', 'cisco_sdwan_brownout_x',
              'ddos_syn_flood', 'CISCO_SDWAN_BROWNOUT', ' cisco_sdwan_brownout',
              'my_campus_rogue_test', 'openconfig_mdt', 'sql')


class TestFallbackGuard(unittest.TestCase):
    def unavailable_ids(self):
        return sorted({s['id'] for s in NetSpoutCatalog().list_scenarios()} - SUPPORTED) + list(LOOKALIKES)

    def test_supported_generators(self):
        self.assertEqual(SUPPORTED_SCENARIO_IDS, SUPPORTED)
        for sid in sorted(SUPPORTED):
            with self.subTest(scenario=sid):
                runner = ScenarioRunner()
                manifest = runner.run_scenario(ScenarioRunRequest(scenario_id=sid, seed=42, time_mode='TEST'))
                self.assertEqual(manifest.scenario_id, sid)
                logs = runner.get_run_logs(manifest.run_id)
                self.assertGreater(len(logs), 0)
                for log in logs:
                    for marker in ('%NETSPOUT-6-INFO', 'NetSpout Simulated Telemetry'):
                        self.assertNotIn(marker, (log.raw_log or '') + (log.signature or ''))

    def test_refusal_precedes_run_creation(self):
        runner = ScenarioRunner()
        for sid in self.unavailable_ids():
            with self.subTest(scenario=sid), patch.object(runner, 'generate_run_id', side_effect=AssertionError('run created')):
                with self.assertRaises(ValueError) as raised:
                    runner.run_scenario(ScenarioRunRequest(scenario_id=sid, seed=42, time_mode='TEST'))
                self.assertIn(sid, str(raised.exception))
                self.assertIn('not available in this release', str(raised.exception))
                self.assertEqual(runner.run_logs, {})
                self.assertEqual(runner.active_manifests, {})

    def test_exact_topology_and_telemetry_routing(self):
        runner = ScenarioRunner()
        for sid in LOOKALIKES:
            with self.subTest(scenario=sid), self.assertRaises(ValueError):
                runner._get_topology_for_scenario({'id': sid, 'topology_id': 'cisco_sdwan_brownout'})
        # Routing must not normalize identifiers or inspect the topology ID.
        source = (ROOT / 'src/netspout_core/scenario_runner.py').read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in ('_get_topology_for_scenario', '_generate_phase_telemetry'):
                for child in ast.walk(node):
                    if isinstance(child, ast.Compare):
                        for op, rhs in zip(child.ops, child.comparators):
                            if isinstance(op, (ast.In, ast.NotIn)):
                                self.assertNotIn(ast.unparse(rhs), ('scen_id', 'top_id', 'contract.id'))
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                        if ast.unparse(child.func.value) in ('scen_id', 'top_id', 'contract.id'):
                            self.assertNotIn(child.func.attr, ('lower', 'casefold', 'startswith', 'endswith', 'find'))

    def test_catalog_aliases_preserved(self):
        catalog = NetSpoutCatalog()
        aliases = json.loads((ROOT / 'catalog/aliases.json').read_text())
        for alias in aliases:
            canonical, resolved = catalog.resolve_scenario_id(alias)
            if resolved and canonical in SUPPORTED:
                with self.subTest(alias=alias):
                    manifest = ScenarioRunner().run_scenario(ScenarioRunRequest(scenario_id=alias, seed=42))
                    self.assertEqual(manifest.scenario_id, canonical)

    def test_api_refusal(self):
        from fastapi.testclient import TestClient
        import app.main as main
        client = TestClient(main.app)
        before = (dict(main.scenario_runner.run_logs), dict(main.scenario_runner.active_manifests))
        for sid in self.unavailable_ids():
            with self.subTest(scenario=sid):
                response = client.post('/api/generate/scenario', json={'scenario_id': sid, 'dispatch_telemetry': False})
                self.assertTrue(400 <= response.status_code < 500)
                self.assertIn(sid, json.dumps(response.json()))
        self.assertEqual(before, (main.scenario_runner.run_logs, main.scenario_runner.active_manifests))

    def test_generic_modes_and_legacy_simulation(self):
        from app.generator_modes import generator_service
        import app.main as main
        from app.models import ScenarioType
        common = dict(vendor_id='cisco_ios', dispatch=False, index='idx_network_ops')
        single = generator_service.generate_single_event(sourcetype='cisco:ios:syslog', event_name=None, **common)
        self.assertEqual(single['status'], 'GROUNDED')
        self.assertEqual(single['mode'], 'SINGLE_EVENT')
        batch = generator_service.generate_sourcetype_batch(sourcetype='cisco:ios:syslog', count=5, rate_eps=10, **common)
        data = generator_service.generate_data_source(product='IOS XR', transport='syslog', count=5, rate_eps=10, **common)
        for result in (batch, data):
            self.assertEqual(result['status'], 'GROUNDED')
            self.assertEqual(result['count_generated'], 5)
        for scenario_type in list(ScenarioType)[:4]:
            self.assertTrue(main.scenario_runner.execute_step(main.current_topology, scenario_type))


if __name__ == '__main__':
    unittest.main()
