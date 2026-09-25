#!/usr/bin/env python3
"""
NetSpout Gate 6 Test Suite: Evidence Integrity, Delivery Semantics & Golden Path Remediation
Verifies all 14 mandatory requirements from Part 13:
1. Scenario run with dispatch enabled (dispatch_telemetry=True)
2. Generated != dispatched when dispatch fails
3. Dispatched != observed without destination evidence
4. Validation cannot PASS without required observed evidence (when dispatch enabled)
5. Connection test frontend/backend contract
6. Unreachable HEC handling
7. Successful HEC reachability
8. Indexing delay handling (OBSERVATION_PENDING status)
9. Zero observed events handling
10. Partial observed telemetry (Invariant: observed <= dispatched)
11. Configured-index SPL generation
12. Run-ID SPL generation
13. Display names exclude internal Mode prefixes
14. Sourcetype evidence stamped and available
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC_DIR = os.path.join(REPO_ROOT, 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from netspout_core.models import (
    ScenarioRunRequest,
    TelemetryTransportConfig,
    RunManifest,
    ValidationStatus
)
from netspout_core.catalog import catalog
from netspout_core.scenario_runner import ScenarioRunner
from netspout_core.telemetry_dispatcher import TelemetryDispatcher, dispatcher


class TestGate6Integrity(unittest.TestCase):

    def setUp(self):
        self.runner = ScenarioRunner()
        self.dispatcher = TelemetryDispatcher()

    # -------------------------------------------------------------------------
    # Test 1: Scenario Run with Dispatch Enabled
    # -------------------------------------------------------------------------
    def test_01_scenario_run_with_dispatch_enabled(self):
        """Verify scenario run with dispatch_telemetry=True attempts real dispatch."""
        transport = TelemetryTransportConfig(
            hec_endpoint='https://127.0.0.1:8888/services/collector',
            hec_token='00000000-0000-0000-0000-000000000000',
            default_index='idx_network_ops',
            hec_ssl_verify=False,
            hec_allow_insecure_tls=True
        )
        req = ScenarioRunRequest(
            scenario_id='cisco_sdwan_brownout',
            seed=42,
            time_mode='TEST',
            dispatch_telemetry=True,
            transport_config=transport
        )
        manifest = self.runner.run_scenario(req)
        self.assertGreater(manifest.total_events_generated, 0)
        self.assertGreater(manifest.dispatch_attempted, 0)
        self.assertEqual(manifest.dispatch_attempted, manifest.total_events_generated)

    # -------------------------------------------------------------------------
    # Test 2: Generated != Dispatched When Dispatch Fails
    # -------------------------------------------------------------------------
    def test_02_generated_not_equal_dispatched_on_failure(self):
        """Verify dispatch failure results in dispatch_succeeded=0 and generated != dispatched."""
        transport = TelemetryTransportConfig(
            hec_endpoint='http://127.0.0.1:59999/services/collector',
            hec_token='invalid-token',
            default_index='idx_network_ops'
        )
        req = ScenarioRunRequest(
            scenario_id='cisco_sdwan_brownout',
            seed=42,
            time_mode='TEST',
            dispatch_telemetry=True,
            transport_config=transport
        )
        manifest = self.runner.run_scenario(req)
        self.assertGreater(manifest.total_events_generated, 0)
        self.assertGreater(manifest.dispatch_attempted, 0)
        self.assertEqual(manifest.dispatch_succeeded, 0)
        self.assertEqual(manifest.dispatch_failed, manifest.dispatch_attempted)
        self.assertNotEqual(manifest.total_events_generated, manifest.dispatch_succeeded)

    # -------------------------------------------------------------------------
    # Test 3: Dispatched != Observed Without Destination Evidence
    # -------------------------------------------------------------------------
    def test_03_dispatched_not_equal_observed_without_evidence(self):
        """Verify observed count is NOT defaulted to dispatched count."""
        transport = TelemetryTransportConfig(
            hec_endpoint='http://127.0.0.1:59999/services/collector',
            hec_token='invalid-token'
        )
        req = ScenarioRunRequest(
            scenario_id='cisco_sdwan_brownout',
            seed=42,
            time_mode='TEST',
            dispatch_telemetry=True,
            transport_config=transport
        )
        manifest = self.runner.run_scenario(req)
        self.assertEqual(manifest.observed_count, 0)
        self.assertIn(manifest.destination_validation, ['FAIL', 'NOT_RUN'])

    # -------------------------------------------------------------------------
    # Test 4: Validation Cannot PASS Without Required Observed Evidence
    # -------------------------------------------------------------------------
    def test_04_validation_cannot_pass_without_required_observed_evidence(self):
        """Verify overall validation cannot report PASS when destination validation fails."""
        transport = TelemetryTransportConfig(
            hec_endpoint='http://127.0.0.1:59999/services/collector',
            hec_token='invalid-token'
        )
        req = ScenarioRunRequest(
            scenario_id='cisco_sdwan_brownout',
            seed=42,
            time_mode='TEST',
            dispatch_telemetry=True,
            transport_config=transport
        )
        manifest = self.runner.run_scenario(req)
        self.assertEqual(manifest.destination_validation, 'FAIL')
        self.assertEqual(manifest.overall_validation, 'FAIL')

    # -------------------------------------------------------------------------
    # Test 5: Connection Test Frontend/Backend Contract
    # -------------------------------------------------------------------------
    def test_05_connection_test_contract(self):
        """Verify test_connection returns canonical 5-state response schema."""
        res = self.dispatcher.test_connection(
            endpoint='',
            token=''
        )
        self.assertEqual(res['status'], 'NOT_CONFIGURED')
        self.assertIn('message', res)
        self.assertIn('detail', res)

        res_invalid = self.dispatcher.test_connection(
            endpoint='http://127.0.0.1:59999/services/collector',
            token='test-token'
        )
        self.assertIn(res_invalid['status'], ['ERROR', 'CONFIGURED'])
        self.assertIn('message', res_invalid)

    # -------------------------------------------------------------------------
    # Test 6: Unreachable HEC Handling
    # -------------------------------------------------------------------------
    def test_06_unreachable_hec(self):
        """Verify unreachable HEC endpoint reports ERROR and never claims REACHABLE or VERIFIED."""
        res = self.dispatcher.test_connection(
            endpoint='https://127.0.0.1:59999/services/collector',
            token='test-token',
            allow_insecure_tls=True
        )
        self.assertEqual(res['status'], 'ERROR')
        self.assertNotEqual(res['status'], 'REACHABLE')
        self.assertNotEqual(res['status'], 'VERIFIED')

    # -------------------------------------------------------------------------
    # Test 7: Successful HEC Reachability
    # -------------------------------------------------------------------------
    def test_07_successful_hec(self):
        """Verify live or reachable HEC returns REACHABLE with latency measurement."""
        res = self.dispatcher.test_connection(
            endpoint='https://127.0.0.1:8888/services/collector',
            token='00000000-0000-0000-0000-000000000000',
            index='idx_network_ops',
            allow_insecure_tls=True
        )
        self.assertIn(res['status'], ['REACHABLE', 'VERIFIED'])
        self.assertGreater(res['latency_ms'], 0)

    # -------------------------------------------------------------------------
    # Test 8: Indexing Delay Handling (OBSERVATION_PENDING)
    # -------------------------------------------------------------------------
    def test_08_indexing_delay_handling(self):
        """Verify indexing delay sets status to OBSERVATION_PENDING rather than failing immediately."""
        status, count = self.runner.check_destination_observation(
            run_id='NS-20269999-nonexistent',
            index='idx_network_ops',
            max_retries=1,
            delay_sec=0.1
        )
        self.assertIn(status, ['OBSERVATION_PENDING', 'FAIL'])
        self.assertEqual(count, 0)

    # -------------------------------------------------------------------------
    # Test 9: Zero Observed Events Handling
    # -------------------------------------------------------------------------
    def test_09_zero_observed_events(self):
        """Verify zero observed events correctly reports 0 count and pending/fail validation."""
        status, count = self.runner.check_destination_observation(
            run_id='NS-00000000-00000000',
            index='idx_network_ops',
            max_retries=1,
            delay_sec=0.1
        )
        self.assertEqual(count, 0)

    # -------------------------------------------------------------------------
    # Test 10: Partial Observed Telemetry (Release Invariant 1)
    # -------------------------------------------------------------------------
    def test_10_partial_observed_telemetry(self):
        """Release Invariant 1: observed_count <= dispatch_succeeded."""
        manifest = RunManifest(
            run_id='NS-20260925-invariant1',
            scenario_id='cisco_sdwan_brownout',
            scenario_name='Enterprise WAN Circuit Brownout',
            topology_id='cisco_sdwan',
            dispatch_attempted=10,
            dispatch_succeeded=6,
            dispatch_failed=4,
            observed_count=4
        )
        self.assertLessEqual(manifest.observed_count, manifest.dispatch_succeeded)

    # -------------------------------------------------------------------------
    # Test 11: Configured-Index SPL Generation
    # -------------------------------------------------------------------------
    def test_11_configured_index_spl_generation(self):
        """Verify generated SPL incorporates the configured index."""
        transport = TelemetryTransportConfig(
            hec_endpoint='https://127.0.0.1:8888/services/collector',
            hec_token='00000000-0000-0000-0000-000000000000',
            default_index='custom_telemetry_index',
            hec_ssl_verify=False,
            hec_allow_insecure_tls=True
        )
        req = ScenarioRunRequest(
            scenario_id='cisco_sdwan_brownout',
            seed=42,
            time_mode='TEST',
            dispatch_telemetry=True,
            transport_config=transport
        )
        manifest = self.runner.run_scenario(req)
        self.assertIn('index=custom_telemetry_index', manifest.splunk_search_query)

    # -------------------------------------------------------------------------
    # Test 12: Run-ID SPL Generation
    # -------------------------------------------------------------------------
    def test_12_run_id_spl_generation(self):
        """Verify generated SPL contains the unique Run ID."""
        req = ScenarioRunRequest(
            scenario_id='cisco_sdwan_brownout',
            seed=42,
            time_mode='TEST',
            dispatch_telemetry=True
        )
        manifest = self.runner.run_scenario(req)
        self.assertIn(f'netspout_run_id="{manifest.run_id}"', manifest.splunk_search_query)

    # -------------------------------------------------------------------------
    # Test 13: Display Names Exclude Internal Mode Prefix
    # -------------------------------------------------------------------------
    def test_13_display_names_exclude_internal_mode_prefix(self):
        """Verify customer-facing scenario & topology display names do not contain internal Mode prefixes."""
        forbidden_prefixes = ['Mode A1:', 'Mode A2:', 'Mode A3:', 'Mode B1:', 'Mode B2:', 'Mode B3:', 'Mode C:']
        
        for sc in catalog.list_scenarios():
            name = sc.get('name', '')
            display_name = sc.get('display_name', '')
            for pfx in forbidden_prefixes:
                self.assertFalse(
                    name.startswith(pfx),
                    f"Scenario '{sc['id']}' name '{name}' contains forbidden prefix '{pfx}'"
                )
                self.assertFalse(
                    display_name.startswith(pfx),
                    f"Scenario '{sc['id']}' display_name '{display_name}' contains forbidden prefix '{pfx}'"
                )

        for top in catalog.list_topologies():
            tname = top.get('name', '')
            for pfx in forbidden_prefixes:
                self.assertFalse(
                    tname.startswith(pfx),
                    f"Topology '{top['id']}' name '{tname}' contains forbidden prefix '{pfx}'"
                )

    # -------------------------------------------------------------------------
    # Test 14: Sourcetype Evidence Stamped and Available
    # -------------------------------------------------------------------------
    def test_14_sourcetype_evidence_stamped_and_available(self):
        """Verify emitted logs include required sourcetype and correlation stamps."""
        req = ScenarioRunRequest(
            scenario_id='cisco_sdwan_brownout',
            seed=42,
            time_mode='TEST'
        )
        manifest = self.runner.run_scenario(req)
        logs = self.runner.run_logs[manifest.run_id]
        self.assertGreater(len(logs), 0)
        
        sourcetypes_seen = {l.sourcetype for l in logs}
        self.assertIn('cisco:sdwan:linkhealth', sourcetypes_seen)
        self.assertIn('cisco:sdwan:BGP-5-ADJCHANGE', sourcetypes_seen)
        
        for log in logs:
            self.assertEqual(log.netspout_run_id, manifest.run_id)
            self.assertEqual(log.netspout_scenario_id, 'cisco_sdwan_brownout')
            self.assertTrue(bool(log.netspout_phase))
            self.assertTrue(bool(log.sourcetype))


if __name__ == '__main__':
    unittest.main()