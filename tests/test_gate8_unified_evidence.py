"""
NetSpout Gate 8 Test Suite: Unified Evidence Discovery & Metric Harmonization
Author: Mahamudul Chowdhury (machowdhury@yahoo.com)

Verifies all 22 required Gate 8 areas:
 1. Multi-destination discovery from run telemetry
 2. Storage destination typing (EVENT vs METRIC)
 3. Destination role assignment (REQUIRED vs SUPPORTING)
 4. Query mechanism assignment (SPL_SEARCH vs MSTATS)
 5. SPL search query generation with run correlation
 6. Metric | mstats query generation with run correlation
 7. Observation completeness calculation across heterogeneous destinations
 8. Decoupled contract validation vs observation completeness
 9. Partial observation status
10. Complete observation status (100% across all destinations)
11. Failed observation status handling
12. HEC metric payload construction with metric dimensions
13. Metric extraction from MDT raw_log payloads
14. Preservation of true Splunk metric storage semantics (no event flattening)
15. Multi-store observation API response structure
16. RunManifest serialization with unified evidence fields
17. Invariant: Contract PASS does not require SUPPORTING metrics
18. Invariant: Destination PASS requires observed evidence
19. GP01 evidence discovery (event + catalog-classified metric destination)
20. GP02 evidence discovery (single event destination, GOLDEN_PATH_CERTIFIED)
21. GP03 evidence discovery (dual destination: event + metric, E2E_VALIDATED)
22. GP04 evidence discovery (single event destination, GOLDEN_PATH_CERTIFIED)
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from netspout_core.models import (
    ScenarioContract,
    RunManifest,
    ScenarioRunRequest,
    ValidationRule,
    ValidationType,
    ValidationStatus,
    ScenarioPhase,
    TelemetryTransportConfig,
    TelemetryType,
    QueryMechanism,
    EvidenceRole,
    EvidenceDestination,
    EvidenceObservation,
    UnifiedRunEvidence,
    LogEntry
)
from netspout_core.scenario_runner import ScenarioRunner
from netspout_core.telemetry_dispatcher import TelemetryDispatcher
from netspout_core.catalog import NetSpoutCatalog


class TestGate8UnifiedEvidence(unittest.TestCase):

    def setUp(self):
        self.runner = ScenarioRunner()
        self.dispatcher = TelemetryDispatcher()
        self.catalog = NetSpoutCatalog()
        # Hermetic: the HEC emit is stubbed, so no live Splunk or real token is needed.
        # Individual tests may re-patch emit_hec; the outer patch is the default.
        hec_url = "https://127.0.0.1:8088/services/collector"
        patcher = patch.object(TelemetryDispatcher, "emit_hec", return_value=(True, "OK"))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.transport = TelemetryTransportConfig(
            hec_enabled=True,
            hec_url=hec_url,
            hec_token="test-token-not-a-secret",
            hec_index="idx_network_ops",
            hec_metric_index="cisco_mdt_metrics",
            hec_allow_insecure_tls=True
        )

    # -------------------------------------------------------------------------
    # Area 1: Multi-destination discovery from run telemetry
    # -------------------------------------------------------------------------
    def test_01_multi_destination_discovery(self):
        run_id = "test_run_disc_01"
        self.runner.run_logs[run_id] = [
            LogEntry(
                timestamp="2026-09-25T12:00:00Z",
                device_id="Leaf-01",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="TCP",
                duration="1ms",
                action="allowed",
                signature="ACI Health Normal",
                status="normal",
                raw_log='{"health": 100}',
                node_type="switch",
                node_id="leaf-01",
                sourcetype="cisco:aci:health"
            ),
            LogEntry(
                timestamp="2026-09-25T12:00:01Z",
                device_id="Leaf-01",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="gNMI/MDT",
                duration="2ms",
                action="allowed",
                signature="MDT Telemetry",
                status="normal",
                raw_log='{"data": {"queue_depth_bytes": 1250000}}',
                node_type="switch",
                node_id="leaf-01",
                sourcetype="cisco:ios:mdt"
            )
        ]
        evidence = self.runner.get_run_evidence(run_id, self.transport)
        self.assertEqual(len(evidence.destinations), 2)
        target_indices = {d.target_index for d in evidence.destinations}
        self.assertIn("idx_network_ops", target_indices)
        self.assertIn("cisco_mdt_metrics", target_indices)

    # -------------------------------------------------------------------------
    # Area 2: Storage destination typing (EVENT vs METRIC)
    # -------------------------------------------------------------------------
    def test_02_storage_destination_typing(self):
        run_id = "test_run_typing_02"
        self.runner.run_logs[run_id] = [
            LogEntry(
                timestamp="2026-09-25T12:00:00Z",
                device_id="Leaf-01",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="TCP",
                duration="1ms",
                action="allowed",
                signature="Event Log",
                status="normal",
                raw_log='{"event": "log"}',
                node_type="switch",
                node_id="leaf-01",
                sourcetype="cisco:nexus:syslog"
            ),
            LogEntry(
                timestamp="2026-09-25T12:00:01Z",
                device_id="Leaf-01",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="gNMI/MDT",
                duration="2ms",
                action="allowed",
                signature="Metric Telemetry",
                status="normal",
                raw_log='{"data": {"queue_depth_bytes": 1000}}',
                node_type="switch",
                node_id="leaf-01",
                sourcetype="cisco:ios:mdt:metric"
            )
        ]
        evidence = self.runner.get_run_evidence(run_id, self.transport)
        event_dest = next(d for d in evidence.destinations if d.target_index == "idx_network_ops")
        metric_dest = next(d for d in evidence.destinations if d.target_index == "cisco_mdt_metrics")
        self.assertEqual(event_dest.telemetry_type, TelemetryType.EVENT)
        self.assertEqual(metric_dest.telemetry_type, TelemetryType.METRIC)

    # -------------------------------------------------------------------------
    # Area 3: Destination role assignment (REQUIRED vs SUPPORTING)
    # -------------------------------------------------------------------------
    def test_03_destination_role_assignment(self):
        run_id = "test_run_roles_03"
        self.runner.active_manifests[run_id] = RunManifest(
            run_id=run_id,
            scenario_id="cisco_aci_microburst"
        )
        self.runner.run_logs[run_id] = [
            LogEntry(
                timestamp="2026-09-25T12:00:00Z",
                device_id="Leaf-01",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="TCP",
                duration="1ms",
                action="allowed",
                signature="Syslog",
                status="normal",
                raw_log="log entry",
                node_type="switch",
                node_id="leaf-01",
                sourcetype="cisco:dc:nexus9k:syslog"
            ),
            LogEntry(
                timestamp="2026-09-25T12:00:01Z",
                device_id="Leaf-01",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="gNMI/MDT",
                duration="2ms",
                action="allowed",
                signature="MDT",
                status="normal",
                raw_log='{"data": {"queue_depth_bytes": 1000}}',
                node_type="switch",
                node_id="leaf-01",
                sourcetype="cisco:ios:mdt:metric"
            )
        ]
        evidence = self.runner.get_run_evidence(run_id, self.transport)
        event_dest = next(d for d in evidence.destinations if d.target_index == "idx_network_ops")
        metric_dest = next(d for d in evidence.destinations if d.target_index == "cisco_mdt_metrics")
        self.assertEqual(event_dest.role, EvidenceRole.REQUIRED)
        self.assertEqual(metric_dest.role, EvidenceRole.SUPPORTING)

    # -------------------------------------------------------------------------
    # Area 4: Query mechanism assignment (SPL_SEARCH vs MSTATS)
    # -------------------------------------------------------------------------
    def test_04_query_mechanism_assignment(self):
        run_id = "test_run_mech_04"
        self.runner.run_logs[run_id] = [
            LogEntry(
                timestamp="2026-09-25T12:00:00Z",
                device_id="sw1",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="TCP",
                duration="1ms",
                action="allowed",
                signature="test",
                status="normal",
                raw_log="log",
                node_type="switch",
                node_id="sw1",
                sourcetype="cisco:ios:syslog"
            ),
            LogEntry(
                timestamp="2026-09-25T12:00:01Z",
                device_id="sw1",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="gNMI",
                duration="2ms",
                action="allowed",
                signature="mdt",
                status="normal",
                raw_log='{"data": {"q": 1}}',
                node_type="switch",
                node_id="sw1",
                sourcetype="cisco:ios:mdt"
            )
        ]
        evidence = self.runner.get_run_evidence(run_id, self.transport)
        event_dest = next(d for d in evidence.destinations if d.telemetry_type == TelemetryType.EVENT)
        metric_dest = next(d for d in evidence.destinations if d.telemetry_type == TelemetryType.METRIC)
        self.assertEqual(event_dest.query_mechanism, QueryMechanism.SPL_SEARCH)
        self.assertEqual(metric_dest.query_mechanism, QueryMechanism.MSTATS)

    # -------------------------------------------------------------------------
    # Area 5: SPL search query generation with run correlation
    # -------------------------------------------------------------------------
    def test_05_spl_search_query_generation(self):
        run_id = "run_gate8_test_05"
        self.runner.run_logs[run_id] = [
            LogEntry(
                timestamp="2026-09-25T12:00:00Z",
                device_id="rt1",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="TCP",
                duration="1ms",
                action="allowed",
                signature="test",
                status="normal",
                raw_log="log",
                node_type="router",
                node_id="rt1",
                sourcetype="cisco:sdwan:syslog"
            )
        ]
        evidence = self.runner.get_run_evidence(run_id, self.transport)
        event_dest = next(d for d in evidence.destinations if d.telemetry_type == TelemetryType.EVENT)
        self.assertIn("search index=idx_network_ops", event_dest.query)
        self.assertIn(f'netspout_run_id="{run_id}"', event_dest.query)

    # -------------------------------------------------------------------------
    # Area 6: Metric | mstats query generation with run correlation
    # -------------------------------------------------------------------------
    def test_06_mstats_query_generation(self):
        run_id = "run_gate8_test_06"
        self.runner.run_logs[run_id] = [
            LogEntry(
                timestamp="2026-09-25T12:00:00Z",
                device_id="sw1",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="gNMI",
                duration="1ms",
                action="allowed",
                signature="test",
                status="normal",
                raw_log="{}",
                node_type="switch",
                node_id="sw1",
                sourcetype="cisco:ios:mdt:metric"
            )
        ]
        evidence = self.runner.get_run_evidence(run_id, self.transport)
        metric_dest = next(d for d in evidence.destinations if d.telemetry_type == TelemetryType.METRIC)
        self.assertTrue(metric_dest.query.startswith("| mstats count where index=cisco_mdt_metrics"))
        self.assertIn(f'netspout_run_id="{run_id}"', metric_dest.query)
        self.assertIn("metric_name=*", metric_dest.query)

    # -------------------------------------------------------------------------
    # Area 7: Observation completeness calculation across heterogeneous destinations
    # -------------------------------------------------------------------------
    @patch.object(ScenarioRunner, "_execute_splunk_rest_query")
    def test_07_observation_completeness_calculation(self, mock_query):
        run_id = "run_gate8_test_07"
        self.runner.run_logs[run_id] = [
            LogEntry(
                timestamp="2026-09-25T12:00:00Z",
                device_id="dev",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="TCP",
                duration="1ms",
                action="allowed",
                signature="evt",
                status="normal",
                raw_log="log",
                node_type="switch",
                node_id="sw",
                sourcetype="cisco:nexus:syslog"
            )
            for _ in range(10)
        ] + [
            LogEntry(
                timestamp="2026-09-25T12:00:00Z",
                device_id="dev",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="gNMI",
                duration="1ms",
                action="allowed",
                signature="metric",
                status="normal",
                raw_log="{}",
                node_type="switch",
                node_id="sw",
                sourcetype="cisco:ios:mdt"
            )
            for _ in range(4)
        ]

        def query_side_effect(q, trans=None):
            if "mstats" in q:
                return 4, None
            return 10, None

        mock_query.side_effect = query_side_effect
        evidence = self.runner.get_run_evidence(run_id, self.transport)
        self.assertEqual(evidence.total_generated, 14)
        self.assertEqual(evidence.event_observed_count, 10)
        self.assertEqual(evidence.metric_observed_count, 4)
        self.assertEqual(evidence.total_observed, 14)
        self.assertEqual(evidence.observation_completeness_pct, 100.0)
        self.assertEqual(evidence.observation_status, "COMPLETE")

    # -------------------------------------------------------------------------
    # Area 8: Decoupled contract validation vs observation completeness
    # -------------------------------------------------------------------------
    @patch.object(ScenarioRunner, "_execute_splunk_rest_query")
    def test_08_decoupled_contract_vs_observation(self, mock_query):
        run_id = "run_gate8_test_08"
        self.runner.run_logs[run_id] = [
            LogEntry(
                timestamp="2026-09-25T12:00:00Z",
                device_id="dev",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="TCP",
                duration="1ms",
                action="allowed",
                signature="evt",
                status="normal",
                raw_log="log",
                node_type="switch",
                node_id="sw",
                sourcetype="cisco:nexus:syslog"
            )
            for _ in range(10)
        ] + [
            LogEntry(
                timestamp="2026-09-25T12:00:00Z",
                device_id="dev",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="gNMI",
                duration="1ms",
                action="allowed",
                signature="metric",
                status="normal",
                raw_log="{}",
                node_type="switch",
                node_id="sw",
                sourcetype="cisco:ios:mdt"
            )
            for _ in range(4)
        ]

        def query_side_effect(q, trans=None):
            if "mstats" in q:
                return 0, None
            return 10, None

        mock_query.side_effect = query_side_effect
        evidence = self.runner.get_run_evidence(run_id, self.transport)
        self.assertTrue(evidence.required_evidence_satisfied)
        self.assertEqual(evidence.observation_status, "PARTIAL")
        self.assertEqual(evidence.observation_completeness_pct, 71.4)

    # -------------------------------------------------------------------------
    # Area 9: Partial observation status
    # -------------------------------------------------------------------------
    @patch.object(ScenarioRunner, "_execute_splunk_rest_query")
    def test_09_partial_observation_status(self, mock_query):
        run_id = "run_gate8_test_09"
        self.runner.run_logs[run_id] = [
            LogEntry(
                timestamp="2026-09-25T12:00:00Z",
                device_id="dev",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="TCP",
                duration="1ms",
                action="allowed",
                signature="evt",
                status="normal",
                raw_log="log",
                node_type="switch",
                node_id="sw",
                sourcetype="cisco:nexus:syslog"
            ),
            LogEntry(
                timestamp="2026-09-25T12:00:00Z",
                device_id="dev",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="gNMI",
                duration="1ms",
                action="allowed",
                signature="metric",
                status="normal",
                raw_log="{}",
                node_type="switch",
                node_id="sw",
                sourcetype="cisco:ios:mdt"
            )
        ]
        mock_query.side_effect = lambda q, trans=None: (1, None) if "mstats" not in q else (0, None)
        evidence = self.runner.get_run_evidence(run_id, self.transport)
        self.assertEqual(evidence.observation_status, "PARTIAL")
        self.assertEqual(evidence.observation_completeness_pct, 50.0)

    # -------------------------------------------------------------------------
    # Area 10: Complete observation status (100% across all destinations)
    # -------------------------------------------------------------------------
    @patch.object(ScenarioRunner, "_execute_splunk_rest_query")
    def test_10_complete_observation_status(self, mock_query):
        run_id = "run_gate8_test_10"
        self.runner.run_logs[run_id] = [
            LogEntry(
                timestamp="2026-09-25T12:00:00Z",
                device_id="dev",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="TCP",
                duration="1ms",
                action="allowed",
                signature="evt",
                status="normal",
                raw_log="log",
                node_type="switch",
                node_id="sw",
                sourcetype="cisco:nexus:syslog"
            ),
            LogEntry(
                timestamp="2026-09-25T12:00:00Z",
                device_id="dev",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="gNMI",
                duration="1ms",
                action="allowed",
                signature="metric",
                status="normal",
                raw_log="{}",
                node_type="switch",
                node_id="sw",
                sourcetype="cisco:ios:mdt"
            )
        ]
        mock_query.side_effect = lambda q, trans=None: (1, None)
        evidence = self.runner.get_run_evidence(run_id, self.transport)
        self.assertEqual(evidence.observation_status, "COMPLETE")
        self.assertEqual(evidence.observation_completeness_pct, 100.0)
        self.assertTrue(evidence.required_evidence_satisfied)

    # -------------------------------------------------------------------------
    # Area 11: Failed observation status handling
    # -------------------------------------------------------------------------
    @patch.object(ScenarioRunner, "_execute_splunk_rest_query")
    def test_11_failed_observation_status(self, mock_query):
        run_id = "run_gate8_test_11"
        self.runner.run_logs[run_id] = [
            LogEntry(
                timestamp="2026-09-25T12:00:00Z",
                device_id="dev",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="TCP",
                duration="1ms",
                action="allowed",
                signature="evt",
                status="normal",
                raw_log="log",
                node_type="switch",
                node_id="sw",
                sourcetype="cisco:nexus:syslog"
            )
        ]
        mock_query.return_value = (0, "Connection refused: [Errno 61]")
        evidence = self.runner.get_run_evidence(run_id, self.transport)
        self.assertEqual(evidence.total_observed, 0)
        self.assertFalse(evidence.required_evidence_satisfied)
        self.assertEqual(len(evidence.errors), 1)
        self.assertIn("Connection refused", evidence.errors[0])

    # -------------------------------------------------------------------------
    # Area 12: HEC metric payload construction with metric dimensions
    # -------------------------------------------------------------------------
    @patch.object(TelemetryDispatcher, "emit_hec")
    def test_12_hec_metric_payload_dimensions(self, mock_emit):
        mock_emit.return_value = (True, "OK")
        entry = LogEntry(
            timestamp="2026-09-25T12:00:00Z",
            device_id="Nexus-9336-Leaf01",
            src_ip="10.255.0.11",
            dest_ip="10.255.1.1",
            protocol="gNMI/MDT",
            duration="2ms",
            action="allowed",
            signature="MDT Telemetry",
            status="normal",
            raw_log='{"data": {"queue_depth_bytes": 1250000}}',
            node_type="switch",
            node_id="leaf-01",
            sourcetype="cisco:ios:mdt",
            netspout_run_id="run_dim_test_12",
            netspout_scenario_id="cisco_aci_microburst",
            netspout_phase="BASELINE",
            netspout_event_id="evt_001",
            netspout_ground_truth="true"
        )
        res = self.dispatcher.dispatch_log(entry, transport=self.transport)
        self.assertTrue(res["hec"]["success"])
        self.assertTrue(mock_emit.called)
        payload = mock_emit.call_args[0][0]
        self.assertEqual(payload.get("event"), "metric")
        fields = payload.get("fields", {})
        self.assertEqual(fields.get("netspout_run_id"), "run_dim_test_12")
        self.assertEqual(fields.get("netspout_scenario_id"), "cisco_aci_microburst")
        self.assertEqual(fields.get("netspout_phase"), "BASELINE")
        self.assertEqual(fields.get("netspout_event_id"), "evt_001")
        self.assertEqual(fields.get("netspout_ground_truth"), "true")
        self.assertEqual(fields.get("device"), "Nexus-9336-Leaf01")
        # single measurement -> `_value` mirrors it
        self.assertEqual(fields.get("_value"), 1250000.0)

    # -------------------------------------------------------------------------
    # Area 13: Metric extraction from MDT raw_log payloads
    # -------------------------------------------------------------------------
    @patch.object(TelemetryDispatcher, "emit_hec")
    def test_13_metric_extraction_from_raw_log(self, mock_emit):
        mock_emit.return_value = (True, "OK")
        entry = LogEntry(
            timestamp="2026-09-25T12:00:00Z",
            device_id="Nexus-9336-Leaf01",
            src_ip="10.255.0.11",
            dest_ip="10.255.1.1",
            protocol="gNMI/MDT",
            duration="2ms",
            action="alerted",
            signature="Incast Active",
            status="degraded",
            raw_log='{"sensor_path": "buffer-stats", "data": {"queue_depth_bytes": 26500000, "buffer_utilization_pct": 98.5}}',
            node_type="switch",
            node_id="leaf-01",
            sourcetype="cisco:ios:mdt",
            netspout_run_id="run_extract_13"
        )
        self.dispatcher.dispatch_log(entry, transport=self.transport)
        payload = mock_emit.call_args[0][0]
        fields = payload.get("fields", {})
        self.assertEqual(fields.get("metric_name:queue_depth"), 26500000.0)
        self.assertEqual(fields.get("metric_name:buffer_utilization"), 98.5)
        # two measurements -> no ambiguous single `_value`
        self.assertNotIn("_value", fields)
        self.assertEqual(fields.get("sensor_path"), "buffer-stats")

    # -------------------------------------------------------------------------
    # Area 14: Preservation of true Splunk metric storage semantics (no event flattening)
    # -------------------------------------------------------------------------
    @patch.object(TelemetryDispatcher, "emit_hec")
    def test_14_preservation_of_true_splunk_metric_semantics(self, mock_emit):
        mock_emit.return_value = (True, "OK")
        entry = LogEntry(
            timestamp="2026-09-25T12:00:00Z",
            device_id="Nexus-9336-Leaf01",
            src_ip="10.255.0.11",
            dest_ip="10.255.1.1",
            protocol="gNMI/MDT",
            duration="2ms",
            action="allowed",
            signature="MDT Telemetry",
            status="normal",
            raw_log='{"data": {"queue_depth_bytes": 1400000}}',
            node_type="switch",
            node_id="leaf-01",
            sourcetype="cisco:ios:mdt"
        )
        self.dispatcher.dispatch_log(entry, transport=self.transport)
        payload = mock_emit.call_args[0][0]
        self.assertEqual(payload.get("event"), "metric")
        self.assertEqual(payload.get("index"), "cisco_mdt_metrics")
        self.assertIsInstance(payload.get("fields"), dict)

    # -------------------------------------------------------------------------
    # Area 15: Multi-store observation API response structure
    # -------------------------------------------------------------------------
    @patch.object(ScenarioRunner, "_execute_splunk_rest_query")
    def test_15_api_observation_response_structure(self, mock_query):
        run_id = "run_api_test_15"
        self.runner.run_logs[run_id] = [
            LogEntry(
                timestamp="2026-09-25T12:00:00Z",
                device_id="dev",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="TCP",
                duration="1ms",
                action="allowed",
                signature="evt",
                status="normal",
                raw_log="log",
                node_type="switch",
                node_id="sw",
                sourcetype="cisco:nexus:syslog"
            )
        ]
        mock_query.return_value = (1, None)
        evidence = self.runner.get_run_evidence(run_id, self.transport)
        d_dict = [d.dict() for d in evidence.destinations]
        self.assertIsInstance(d_dict, list)
        self.assertEqual(len(d_dict), 1)
        self.assertIn("destination_id", d_dict[0])
        self.assertIn("telemetry_type", d_dict[0])
        self.assertIn("query_mechanism", d_dict[0])
        self.assertIn("query", d_dict[0])
        self.assertIn("role", d_dict[0])
        self.assertIn("observed_count", d_dict[0])

    # -------------------------------------------------------------------------
    # Area 16: RunManifest serialization with unified evidence fields
    # -------------------------------------------------------------------------
    def test_16_run_manifest_serialization(self):
        evidence = UnifiedRunEvidence(
            run_id="run_ser_16",
            scenario_id="cisco_aci_microburst",
            destinations=[
                EvidenceObservation(
                    destination_id="splunk_event_idx_network_ops",
                    name="Splunk Event Index",
                    telemetry_type=TelemetryType.EVENT,
                    target_index="idx_network_ops",
                    query_mechanism=QueryMechanism.SPL_SEARCH,
                    query='search index=idx_network_ops netspout_run_id="run_ser_16"',
                    observed_count=10,
                    expected_count=10,
                    status="PASS",
                    role=EvidenceRole.REQUIRED
                ),
                EvidenceObservation(
                    destination_id="splunk_metric_cisco_mdt_metrics",
                    name="Splunk Metric Store",
                    telemetry_type=TelemetryType.METRIC,
                    target_index="cisco_mdt_metrics",
                    query_mechanism=QueryMechanism.MSTATS,
                    query='| mstats count where index=cisco_mdt_metrics metric_name=* AND netspout_run_id="run_ser_16"',
                    observed_count=4,
                    expected_count=4,
                    status="PASS",
                    role=EvidenceRole.SUPPORTING
                )
            ],
            total_generated=14,
            total_dispatched=14,
            total_observed=14,
            event_observed_count=10,
            event_expected_count=10,
            metric_observed_count=4,
            metric_expected_count=4,
            observation_completeness_pct=100.0,
            observation_status="COMPLETE",
            contract_validation="PASS",
            required_evidence_satisfied=True
        )
        manifest = RunManifest(
            run_id="run_ser_16",
            scenario_id="cisco_aci_microburst",
            event_observed_count=10,
            metric_observed_count=4,
            observation_completeness_pct=100.0,
            splunk_search_query='search index=idx_network_ops netspout_run_id="run_ser_16"',
            splunk_metric_query='| mstats count where index=cisco_mdt_metrics metric_name=* AND netspout_run_id="run_ser_16"',
            evidence_summary=evidence
        )
        data = manifest.dict()
        self.assertEqual(data["event_observed_count"], 10)
        self.assertEqual(data["metric_observed_count"], 4)
        self.assertEqual(data["observation_completeness_pct"], 100.0)
        self.assertIn("splunk_metric_query", data)
        self.assertEqual(len(data["evidence_summary"]["destinations"]), 2)

    # -------------------------------------------------------------------------
    # Area 17: Invariant: Contract PASS does not require SUPPORTING metrics
    # -------------------------------------------------------------------------
    @patch.object(ScenarioRunner, "_execute_splunk_rest_query")
    def test_17_contract_pass_does_not_require_supporting_metrics(self, mock_query):
        run_id = "run_inv_17"
        self.runner.active_manifests[run_id] = RunManifest(
            run_id=run_id,
            scenario_id="cisco_aci_microburst",
            destination_validation="PASS"
        )
        self.runner.run_logs[run_id] = [
            LogEntry(
                timestamp="2026-09-25T12:00:00Z",
                device_id="leaf",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="TCP",
                duration="1ms",
                action="allowed",
                signature="syslog",
                status="normal",
                raw_log="log",
                node_type="switch",
                node_id="sw",
                sourcetype="cisco:nexus:syslog"
            ),
            LogEntry(
                timestamp="2026-09-25T12:00:00Z",
                device_id="leaf",
                src_ip="10.0.0.1",
                dest_ip="10.0.0.2",
                protocol="gNMI",
                duration="1ms",
                action="allowed",
                signature="mdt",
                status="normal",
                raw_log="{}",
                node_type="switch",
                node_id="sw",
                sourcetype="cisco:ios:mdt"
            )
        ]
        mock_query.side_effect = lambda q, trans=None: (1, None) if "mstats" not in q else (0, None)
        evidence = self.runner.get_run_evidence(run_id, self.transport)
        self.assertTrue(evidence.required_evidence_satisfied)

    # -------------------------------------------------------------------------
    # Area 18: Invariant: Destination PASS requires observed evidence
    # -------------------------------------------------------------------------
    @patch.object(ScenarioRunner, "_execute_splunk_rest_query")
    def test_18_destination_pass_requires_observed_evidence(self, mock_query):
        req = ScenarioRunRequest(
            scenario_id="cisco_sdwan_brownout",
            dispatch_telemetry=True,
            transport_config=self.transport
        )
        mock_query.return_value = (0, None)
        manifest = self.runner.run_scenario(req)
        self.assertNotEqual(manifest.destination_validation, ValidationStatus.PASS.value)
        self.assertNotEqual(manifest.overall_validation, ValidationStatus.PASS.value)

    # -------------------------------------------------------------------------
    # Area 19: GP01 evidence discovery (single event destination)
    # -------------------------------------------------------------------------
    @patch.object(ScenarioRunner, "_execute_splunk_rest_query")
    def test_19_gp01_evidence_discovery(self, mock_query):
        mock_query.return_value = (14, None)
        req = ScenarioRunRequest(
            scenario_id="cisco_sdwan_brownout",
            dispatch_telemetry=True,
            transport_config=self.transport
        )
        manifest = self.runner.run_scenario(req)
        evidence = manifest.evidence_summary
        self.assertIsNotNone(evidence)
        # cisco:thousandeyes:metric is a catalog metric sourcetype, so the dispatcher sends it to the metric
        # index; evidence must query where the data went (previously miscounted against the event index).
        by_type = {d.telemetry_type: d for d in evidence.destinations}
        self.assertEqual(set(by_type), {TelemetryType.EVENT, TelemetryType.METRIC})
        self.assertEqual(by_type[TelemetryType.EVENT].target_index, "idx_network_ops")
        self.assertEqual(by_type[TelemetryType.METRIC].target_index, "cisco_mdt_metrics")
        self.assertTrue(manifest.splunk_metric_query.startswith("| mstats"))

    # -------------------------------------------------------------------------
    # Area 20: GP02 evidence discovery (single event destination, verified certified)
    # -------------------------------------------------------------------------
    @patch.object(ScenarioRunner, "_execute_splunk_rest_query")
    def test_20_gp02_evidence_discovery_certified(self, mock_query):
        scen = self.catalog.get_scenario("cisco_campus_rogue")
        self.assertIsNotNone(scen)
        self.assertEqual(scen.get("maturity"), "GOLDEN_PATH_CERTIFIED")

        mock_query.return_value = (14, None)
        req = ScenarioRunRequest(
            scenario_id="cisco_campus_rogue",
            dispatch_telemetry=True,
            transport_config=self.transport
        )
        manifest = self.runner.run_scenario(req)
        evidence = manifest.evidence_summary
        self.assertIsNotNone(evidence)
        self.assertEqual(len(evidence.destinations), 1)
        self.assertEqual(evidence.destinations[0].telemetry_type, TelemetryType.EVENT)

    # -------------------------------------------------------------------------
    # Area 21: GP03 evidence discovery (dual destination: event + metric, E2E_VALIDATED)
    # -------------------------------------------------------------------------
    @patch.object(ScenarioRunner, "_execute_splunk_rest_query")
    def test_21_gp03_evidence_discovery_dual_store(self, mock_query):
        scen = self.catalog.get_scenario("cisco_aci_microburst")
        self.assertIsNotNone(scen)
        self.assertIn(scen.get("maturity"), ("E2E_VALIDATED", "GOLDEN_PATH_CERTIFIED"))

        def mock_side_effect(q, trans=None):
            if "mstats" in q:
                return 4, None
            return 10, None

        mock_query.side_effect = mock_side_effect

        req = ScenarioRunRequest(
            scenario_id="cisco_aci_microburst",
            dispatch_telemetry=True,
            transport_config=self.transport
        )
        manifest = self.runner.run_scenario(req)
        evidence = manifest.evidence_summary
        self.assertIsNotNone(evidence)
        self.assertEqual(len(evidence.destinations), 2)
        self.assertEqual(manifest.event_observed_count, 10)
        self.assertEqual(manifest.metric_observed_count, 4)
        self.assertEqual(manifest.observed_count, 14)
        self.assertEqual(manifest.observation_completeness_pct, 100.0)
        self.assertIsNotNone(manifest.splunk_metric_query)
        self.assertTrue(manifest.splunk_metric_query.startswith("| mstats count where index=cisco_mdt_metrics"))

    # -------------------------------------------------------------------------
    # Area 22: GP04 evidence discovery (single event destination, verified certified)
    # -------------------------------------------------------------------------
    @patch.object(ScenarioRunner, "_execute_splunk_rest_query")
    def test_22_gp04_evidence_discovery_certified(self, mock_query):
        scen = self.catalog.get_scenario("mixed_edge_breach")
        self.assertIsNotNone(scen)
        self.assertEqual(scen.get("maturity"), "GOLDEN_PATH_CERTIFIED")

        mock_query.return_value = (14, None)
        req = ScenarioRunRequest(
            scenario_id="mixed_edge_breach",
            dispatch_telemetry=True,
            transport_config=self.transport
        )
        manifest = self.runner.run_scenario(req)
        evidence = manifest.evidence_summary
        self.assertIsNotNone(evidence)
        self.assertEqual(len(evidence.destinations), 1)
        self.assertEqual(evidence.destinations[0].telemetry_type, TelemetryType.EVENT)

    # -------------------------------------------------------------------------
    # Phase 4E: versioned, truthful evidence
    # -------------------------------------------------------------------------
    def _entry(self, sourcetype):
        return LogEntry(
            timestamp="2026-09-25T12:00:00Z", device_id="d1", src_ip="10.0.0.1", dest_ip="10.0.0.2",
            protocol="x", duration="1ms", action="allowed", signature="s", status="normal",
            raw_log="{}", node_type="switch", node_id="n1", sourcetype=sourcetype,
        )

    @patch.object(ScenarioRunner, "_execute_splunk_rest_query", return_value=(0, None))
    def test_23_evidence_is_versioned_and_timestamped(self, _q):
        self.runner.run_logs["run_v"] = [self._entry("cisco:ios")]
        ev = self.runner.get_run_evidence("run_v", self.transport)
        dumped = ev.model_dump(mode="json")
        self.assertEqual(dumped["schema_version"], "1.0")
        self.assertGreater(dumped["observed_at"], 0)

    @patch.object(ScenarioRunner, "_execute_splunk_rest_query", return_value=(0, None))
    def test_24_catalog_metric_sourcetype_queries_metric_index(self, _q):
        from netspout_core.telemetry_dispatcher import metric_sourcetypes
        non_cisco = sorted(st for st in metric_sourcetypes() if not st.startswith("cisco:ios:mdt"))
        self.assertTrue(non_cisco, "catalog should classify at least one non-Cisco metric sourcetype")
        self.runner.run_logs["run_m"] = [self._entry(non_cisco[0])]
        ev = self.runner.get_run_evidence("run_m", self.transport)
        self.assertEqual([d.telemetry_type for d in ev.destinations], [TelemetryType.METRIC])
        self.assertTrue(ev.destinations[0].query.startswith("| mstats"))

    @patch.object(ScenarioRunner, "_execute_splunk_rest_query", return_value=(0, None))
    def test_25_no_fabricated_expectations_without_logs_or_manifest(self, _q):
        ev = self.runner.get_run_evidence("run_unknown", self.transport)
        self.assertEqual(ev.total_dispatched, 0)
        self.assertEqual(ev.metric_expected_count, 0)
        self.assertEqual(ev.observation_status, "PENDING")

    def test_26_observation_endpoint_never_fabricates_pass_or_completeness(self):
        backend_dir = os.path.join(REPO_ROOT, "backend")
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        from fastapi.testclient import TestClient
        from app.main import app
        from app.scenario_runner import ScenarioRunner as AppRunner
        with patch.object(AppRunner, "_execute_splunk_rest_query", return_value=(0, None)):
            body = TestClient(app).get("/api/scenarios/runs/no-such-run/observation").json()
        self.assertEqual(body["schema_version"], "1.0")
        self.assertEqual(body["observation_completeness_pct"], 0.0)
        self.assertFalse(body["required_evidence_satisfied"])
        self.assertEqual(body["destination_validation"], "FAIL")


if __name__ == "__main__":
    unittest.main()
