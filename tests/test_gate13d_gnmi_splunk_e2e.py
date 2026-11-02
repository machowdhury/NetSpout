"""
NetSpout Gate 13D — Native gNMI/OpenConfig -> External Collector -> Splunk E2E Test Suite.

Covers all 27 mandatory verification items from Gate 13D Section 26 against live:
  - NativeGnmiServer (TCP -> HTTP/2 -> gRPC -> gNMI Protobuf)
  - External Collector (/opt/homebrew/bin/gnmic v0.49.0)
  - GnmiTelemetryNormalizer & GnmiSplunkAdapter
  - Live Splunk HEC (idx_network_ops [netspout:gnmi:event] & cisco_mdt_metrics [netspout:gnmi:metric])
  - Live Splunk REST Search (`search` & `| mstats`)
  - ValidationEngine & 7-stage evidence ledger
"""

import json
import os
import sys
import unittest
from typing import Any, Dict

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from scripts.artifact_isolation import artifact_dir

from netspout_core.gnmi.splunk_e2e import (
    DEFAULT_EVENT_INDEX,
    DEFAULT_EVENT_SOURCETYPE,
    DEFAULT_METRIC_INDEX,
    DEFAULT_METRIC_SOURCETYPE,
    UNSUPPORTED_TELEMETRY_CATALOG,
    GnmiSplunkAdapter,
    GnmiSplunkBridge,
    GnmiSplunkE2EOrchestrator,
    GnmiSplunkE2EScorecard,
    build_gnmi_investigation_queries,
    build_scenario_validation_rules,
)
from netspout_core.models import (
    ValidationRule,
    ValidationStatus,
    ValidationType,
)
from netspout_core.scenario_runner import ValidationEngine


class TestGate13DGnmiSplunkE2E(unittest.TestCase):
    """
    End-to-end verification of Gate 13D:
    ScenarioStateStore -> NativeGnmiServer -> External gnmic Collector ->
    Normalization -> Splunk HEC -> Fresh SPL / mstats -> ValidationEngine.
    """

    orchestrator: GnmiSplunkE2EOrchestrator
    spc_scorecard: GnmiSplunkE2EScorecard
    spc_artifacts: Dict[str, Any]
    oc_scorecard: GnmiSplunkE2EScorecard
    oc_artifacts: Dict[str, Any]
    aci_scorecard: GnmiSplunkE2EScorecard
    aci_artifacts: Dict[str, Any]
    mv_scorecard: GnmiSplunkE2EScorecard
    mv_artifacts: Dict[str, Any]
    xtrans_report: Dict[str, Any]
    controlled_failures: Dict[str, Any]
    perf_benchmark: Dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.orchestrator = GnmiSplunkE2EOrchestrator()
        # 1. Run service_provider_cisco E2E (including ONCE, STREAM/SAMPLE, STREAM/ON_CHANGE)
        cls.spc_scorecard, cls.spc_artifacts = cls.orchestrator.run_scenario_e2e(
            scenario_id="service_provider_cisco",
            seed=42,
            include_stream_modes=True,
        )
        # 2. Run openconfig_mdt_streaming E2E
        cls.oc_scorecard, cls.oc_artifacts = cls.orchestrator.run_scenario_e2e(
            scenario_id="openconfig_mdt_streaming",
            seed=42,
            include_stream_modes=True,
        )
        # 3. Run cisco_aci_microburst E2E
        cls.aci_scorecard, cls.aci_artifacts = cls.orchestrator.run_scenario_e2e(
            scenario_id="cisco_aci_microburst",
            seed=42,
            include_stream_modes=False,
        )
        # 4. Run 4-Vendor Multi-Vendor E2E
        cls.mv_scorecard, cls.mv_artifacts = cls.orchestrator.run_multivendor_e2e(seed=42)
        # 5. Run Cross-Transport Coherence E2E (gNMI + SNMP + Syslog + NetFlow)
        cls.xtrans_report = cls.orchestrator.run_cross_transport_coherence_e2e(seed=42)
        # 6. Run Controlled Failures A-I
        cls.controlled_failures = cls.orchestrator.run_controlled_failures()
        # 7. Run Collector-to-Splunk Performance Benchmark
        cls.perf_benchmark = cls.orchestrator.run_performance_benchmark()

        # Persist all 13 mandatory Gate 13D evidence artifacts
        cls._write_evidence_artifacts()

    @classmethod
    def _write_evidence_artifacts(cls) -> None:
        ev_dir = artifact_dir("gate13d", "evidence")

        def _dump(filename: str, payload: Any) -> None:
            path = ev_dir / filename
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, sort_keys=True, default=str)

        # 1. e2e_scorecard.json
        _dump(
            "e2e_scorecard.json",
            {
                "gate": "13D",
                "title": "Native gNMI/OpenConfig -> External Collector -> Splunk E2E Scorecard",
                "external_collector": "/opt/homebrew/bin/gnmic (v0.49.0)",
                "scenarios": {
                    "service_provider_cisco": cls.spc_scorecard.to_dict(),
                    "openconfig_mdt_streaming": cls.oc_scorecard.to_dict(),
                    "cisco_aci_microburst": cls.aci_scorecard.to_dict(),
                    "multivendor_gnmi_e2e": cls.mv_scorecard.to_dict(),
                },
                "cross_transport_coherence_run_id": cls.xtrans_report["run_id"],
                "cross_transport_coherent": cls.xtrans_report["cross_transport_coherent"],
                "all_controlled_failures_verified": cls.controlled_failures["all_9_controlled_failures_verified"],
            },
        )

        # 2. service_provider_cisco_splunk_events.json
        _dump(
            "service_provider_cisco_splunk_events.json",
            {
                "run_id": cls.spc_scorecard.run_id,
                "scenario_id": "service_provider_cisco",
                "index": DEFAULT_EVENT_INDEX,
                "sourcetype": DEFAULT_EVENT_SOURCETYPE,
                "observed_event_count": len(cls.spc_artifacts["splunk_observed_events"]),
                "events": cls.spc_artifacts["splunk_observed_events"],
            },
        )

        # 3. service_provider_cisco_splunk_metrics.json
        _dump(
            "service_provider_cisco_splunk_metrics.json",
            {
                "run_id": cls.spc_scorecard.run_id,
                "scenario_id": "service_provider_cisco",
                "index": DEFAULT_METRIC_INDEX,
                "sourcetype": DEFAULT_METRIC_SOURCETYPE,
                "observed_metric_series_count": len(cls.spc_artifacts["splunk_observed_metrics"]),
                "observed_metric_samples_total": cls.spc_scorecard.splunk_observed_metrics,
                "mstats_rows": cls.spc_artifacts["splunk_observed_metrics"],
            },
        )

        # 4. openconfig_mdt_streaming_splunk.json
        _dump(
            "openconfig_mdt_streaming_splunk.json",
            {
                "scorecard": cls.oc_scorecard.to_dict(),
                "observed_event_count": len(cls.oc_artifacts["splunk_observed_events"]),
                "observed_metric_series_count": len(cls.oc_artifacts["splunk_observed_metrics"]),
                "sample_observed_events": cls.oc_artifacts["splunk_observed_events"][:40],
                "observed_metrics": cls.oc_artifacts["splunk_observed_metrics"],
            },
        )

        # 5. cisco_aci_microburst_splunk.json
        _dump(
            "cisco_aci_microburst_splunk.json",
            {
                "scorecard": cls.aci_scorecard.to_dict(),
                "unsupported_telemetry_declarations": cls.aci_scorecard.unsupported_telemetry_declarations,
                "observed_events": cls.aci_artifacts["splunk_observed_events"],
                "observed_metrics": cls.aci_artifacts["splunk_observed_metrics"],
            },
        )

        # 6. multivendor_splunk_verification.json
        _dump(
            "multivendor_splunk_verification.json",
            {
                "scorecard": cls.mv_scorecard.to_dict(),
                "vendor_summary_rows": cls.mv_artifacts["vendor_summary_rows"],
                "sample_observed_events": cls.mv_artifacts["splunk_observed_events"][:40],
                "observed_metrics": cls.mv_artifacts["splunk_observed_metrics"],
            },
        )

        # 7. spl_query_outputs.json
        spl_only = {
            k: v
            for k, v in cls.spc_artifacts["query_outputs"].items()
            if k.endswith("_spl")
        }
        spl_only["q8_multivendor_comparison_spl"] = cls.mv_artifacts["vendor_summary_rows"]
        spl_only["q10_cross_source_correlation_spl"] = cls.xtrans_report["timeline_by_phase"]
        _dump(
            "spl_query_outputs.json",
            {
                "service_provider_cisco_run_id": cls.spc_scorecard.run_id,
                "multivendor_run_id": cls.mv_scorecard.run_id,
                "cross_transport_run_id": cls.xtrans_report["run_id"],
                "queries": cls.spc_scorecard.investigation_queries,
                "outputs": spl_only,
            },
        )

        # 8. mstats_query_outputs.json
        mstats_only = {
            k: v
            for k, v in cls.spc_artifacts["query_outputs"].items()
            if k.endswith("_mstats")
        }
        _dump(
            "mstats_query_outputs.json",
            {
                "service_provider_cisco_run_id": cls.spc_scorecard.run_id,
                "cisco_aci_microburst_run_id": cls.aci_scorecard.run_id,
                "spc_mstats_outputs": mstats_only,
                "aci_qos_mstats_outputs": cls.aci_artifacts["query_outputs"].get("q5_qos_congestion_drops_mstats", []),
            },
        )

        # 9. cross_transport_coherence_splunk.json
        _dump("cross_transport_coherence_splunk.json", cls.xtrans_report)

        # 10. validation_engine_results.json
        _dump(
            "validation_engine_results.json",
            {
                "service_provider_cisco": cls.spc_scorecard.validation_results,
                "openconfig_mdt_streaming": cls.oc_scorecard.validation_results,
                "cisco_aci_microburst": cls.aci_scorecard.validation_results,
                "multivendor_gnmi_e2e": cls.mv_scorecard.validation_results,
                "cross_transport_coherence": cls.xtrans_report["coherence_validation"],
            },
        )

        # 11. controlled_failures.json
        _dump("controlled_failures.json", cls.controlled_failures)

        # 12. performance_benchmark.json
        _dump("performance_benchmark.json", cls.perf_benchmark)

        # 13. stage_accounting_ledger.json
        _dump(
            "stage_accounting_ledger.json",
            {
                "service_provider_cisco": cls.spc_scorecard.ledger.to_dict() if cls.spc_scorecard.ledger else {},
                "openconfig_mdt_streaming": cls.oc_scorecard.ledger.to_dict() if cls.oc_scorecard.ledger else {},
                "cisco_aci_microburst": cls.aci_scorecard.ledger.to_dict() if cls.aci_scorecard.ledger else {},
                "multivendor_gnmi_e2e": cls.mv_scorecard.ledger.to_dict() if cls.mv_scorecard.ledger else {},
            },
        )

    # ---------------------------------------------------------------------
    # Section 26 Required Verification Tests (1 through 27)
    # ---------------------------------------------------------------------
    def test_01_native_gnmi_server_to_collector_to_splunk_e2e(self) -> None:
        """Item 1: Native gNMI server -> external collector -> Splunk E2E run completes all 7 stages."""
        self.assertEqual(self.spc_scorecard.highest_verified_stage, "VALIDATED")
        self.assertEqual(self.spc_scorecard.validation_status, "PASS")
        self.assertGreater(self.spc_scorecard.generated_state_mutations, 0)
        self.assertGreater(self.spc_scorecard.server_published_notifications, 0)
        self.assertGreater(self.spc_scorecard.collector_received_updates, 0)
        self.assertGreater(self.spc_scorecard.normalized_total_records, 0)
        self.assertGreater(self.spc_scorecard.splunk_dispatched_total, 0)
        self.assertGreater(self.spc_scorecard.splunk_observed_total, 0)

    def test_02_gnmic_collector_output_ingested_into_splunk(self) -> None:
        """Item 2: External gnmic v0.49.0 collector output is ingested into Splunk with collector metadata."""
        events = self.spc_artifacts["splunk_observed_events"]
        self.assertGreater(len(events), 0)
        for ev in events[:10]:
            self.assertEqual(ev.get("collector_name"), "gnmic")
            self.assertEqual(ev.get("transport_type"), "GNMI_GRPC_HTTP2")
            self.assertEqual(ev.get("transport_truth_device_side"), "Native gNMI over gRPC/HTTP2")
            self.assertEqual(ev.get("transport_truth_collector_side"), "Splunk HEC over HTTPS")

    def test_03_event_telemetry_indexed_and_searchable(self) -> None:
        """Item 3: Event telemetry is indexed in idx_network_ops with sourcetype netspout:gnmi:event."""
        events = self.spc_artifacts["splunk_observed_events"]
        self.assertGreaterEqual(len(events), 25)
        sourcetypes = {ev.get("sourcetype") for ev in events}
        self.assertIn(DEFAULT_EVENT_SOURCETYPE, sourcetypes)
        modes = {str(ev.get("collector_mode")) for ev in events}
        self.assertIn("ONCE", modes)
        self.assertTrue(any("ON_CHANGE" in m for m in modes))

    def test_04_metric_telemetry_indexed_and_queryable_via_mstats(self) -> None:
        """Item 4: Numeric leaf telemetry is indexed in cisco_mdt_metrics and queryable via | mstats."""
        metrics = self.spc_artifacts["splunk_observed_metrics"]
        self.assertGreaterEqual(len(metrics), 15)
        for m in metrics:
            self.assertIsNotNone(m.get("avg_val"))
            self.assertIsNotNone(m.get("max_val"))
            self.assertIsNotNone(m.get("gnmi_leaf"))
            self.assertIsNotNone(m.get("gnmi_path"))

    def test_05_splunk_dispatched_vs_splunk_observed_separation(self) -> None:
        """Item 5: SPLUNK_DISPATCHED and SPLUNK_OBSERVED are tracked separately and never conflated."""
        fail_c = self.controlled_failures["failure_C_splunk_unavailable"]
        self.assertTrue(fail_c["collector_received"])
        self.assertTrue(fail_c["normalized"])
        self.assertFalse(fail_c["splunk_dispatched"])
        self.assertFalse(fail_c["splunk_observed"])
        self.assertEqual(fail_c["highest_verified_stage"], "NORMALIZED")

        # On live run, origin_evidence_stage is NORMALIZED, hec_dispatch_stage is SPLUNK_DISPATCHED,
        # and current_evidence_stage is upgraded to SPLUNK_OBSERVED only by execute_spl_search
        sample_ev = self.spc_artifacts["splunk_observed_events"][0]
        self.assertEqual(sample_ev.get("origin_evidence_stage"), "NORMALIZED")
        self.assertEqual(sample_ev.get("hec_dispatch_stage"), "SPLUNK_DISPATCHED")
        self.assertEqual(sample_ev.get("current_evidence_stage"), "SPLUNK_OBSERVED")

    def test_06_service_provider_cisco_e2e_run(self) -> None:
        """Item 6: service_provider_cisco E2E run passes all 10 validation rules across BASELINE -> DEGRADE -> FAILOVER -> RECOVERY."""
        self.assertEqual(self.spc_scorecard.scenario_id, "service_provider_cisco")
        self.assertEqual(self.spc_scorecard.phases_executed, ["BASELINE", "DEGRADE", "FAILOVER", "RECOVERY"])
        self.assertEqual(self.spc_scorecard.validation_status, "PASS")
        self.assertEqual(self.spc_scorecard.validation_rules_passed, 10)
        self.assertEqual(self.spc_scorecard.validation_rules_failed, 0)

    def test_07_openconfig_mdt_streaming_e2e_run(self) -> None:
        """Item 7: openconfig_mdt_streaming E2E run verifies OpenConfig ONCE, SAMPLE, and ON_CHANGE in Splunk."""
        self.assertEqual(self.oc_scorecard.scenario_id, "openconfig_mdt_streaming")
        self.assertEqual(self.oc_scorecard.highest_verified_stage, "VALIDATED")
        self.assertEqual(self.oc_scorecard.validation_status, "PASS")
        self.assertEqual(self.oc_scorecard.validation_rules_passed, 6)
        self.assertGreater(self.oc_scorecard.splunk_observed_events, 20)
        self.assertGreater(self.oc_scorecard.splunk_observed_metrics, 20)

    def test_08_cisco_aci_microburst_e2e_run_and_honesty(self) -> None:
        """Item 8: cisco_aci_microburst E2E run verifies queue/drop progression and declares ACI DME MOs as UNSUPPORTED_TELEMETRY."""
        self.assertEqual(self.aci_scorecard.scenario_id, "cisco_aci_microburst")
        self.assertEqual(self.aci_scorecard.highest_verified_stage, "VALIDATED")
        self.assertEqual(self.aci_scorecard.validation_status, "PASS")
        self.assertEqual(self.aci_scorecard.validation_rules_passed, 6)
        self.assertEqual(len(self.aci_scorecard.unsupported_telemetry_declarations), 1)
        decl = self.aci_scorecard.unsupported_telemetry_declarations[0]
        self.assertEqual(decl["classification"], "UNSUPPORTED_TELEMETRY")
        self.assertIn("dbgacTenant", decl["requested_telemetry"])

    def test_09_cisco_ios_xr_openconfig_and_native_in_splunk(self) -> None:
        """Item 9: Cisco IOS XR OpenConfig and Cisco-IOS-XR-* native paths observed in Splunk."""
        events = [
            e for e in self.mv_artifacts["splunk_observed_events"]
            if e.get("gnmi_platform") == "CISCO_IOS_XR"
        ]
        origins = {e.get("gnmi_origin") for e in events}
        self.assertIn("openconfig", origins)
        self.assertTrue(any(str(o).startswith("Cisco-IOS-XR-") for o in origins))

    def test_10_cisco_ios_xe_openconfig_and_native_in_splunk(self) -> None:
        """Item 10: Cisco IOS XE OpenConfig and Cisco-IOS-XE-* native paths observed in Splunk."""
        events = [
            e for e in self.mv_artifacts["splunk_observed_events"]
            if e.get("gnmi_platform") == "CISCO_IOS_XE"
        ]
        origins = {e.get("gnmi_origin") for e in events}
        self.assertIn("openconfig", origins)
        self.assertTrue(any(str(o).startswith("Cisco-IOS-XE-") for o in origins))

    def test_11_arista_eos_openconfig_and_native_in_splunk(self) -> None:
        """Item 11: Arista EOS OpenConfig and eos_native paths observed in Splunk."""
        events = [
            e for e in self.mv_artifacts["splunk_observed_events"]
            if e.get("gnmi_platform") == "ARISTA_EOS"
        ]
        origins = {e.get("gnmi_origin") for e in events}
        self.assertIn("openconfig", origins)
        self.assertIn("eos_native", origins)

    def test_12_juniper_junos_openconfig_and_native_in_splunk(self) -> None:
        """Item 12: Juniper Junos OpenConfig and junos native paths observed in Splunk."""
        events = [
            e for e in self.mv_artifacts["splunk_observed_events"]
            if e.get("gnmi_platform") == "JUNIPER_JUNOS"
        ]
        origins = {e.get("gnmi_origin") for e in events}
        self.assertIn("openconfig", origins)
        self.assertIn("junos", origins)

    def test_13_interface_state_transition_in_splunk(self) -> None:
        """Item 13: Interface state transitions (UP -> DOWN -> UP) observed in Splunk."""
        q3_rows = self.spc_artifacts["query_outputs"]["q3_interface_state_transition_spl"]
        self.assertGreater(len(q3_rows), 0)
        primary_oper = {
            r.get("netspout_phase"): r.get("gnmi_value")
            for r in q3_rows
            if r.get("gnmi_path") == "/interfaces/interface[name=HundredGigE0/0/0/0]/state/oper-status"
        }
        self.assertEqual(primary_oper.get("BASELINE"), "UP")
        self.assertEqual(primary_oper.get("FAILOVER"), "DOWN")
        self.assertEqual(primary_oper.get("RECOVERY"), "UP")

    def test_14_bgp_neighbor_state_transition_in_splunk(self) -> None:
        """Item 14: BGP neighbor state transitions (ESTABLISHED -> IDLE -> ESTABLISHED) observed in Splunk."""
        q4_rows = self.spc_artifacts["query_outputs"]["q4_bgp_neighbor_transition_spl"]
        self.assertGreater(len(q4_rows), 0)
        bgp_states = {
            r.get("netspout_phase"): r.get("gnmi_value")
            for r in q4_rows
            if "10.255.0.2" in str(r.get("gnmi_path", "")) and r.get("gnmi_leaf") == "session-state"
        }
        self.assertEqual(bgp_states.get("BASELINE"), "ESTABLISHED")
        self.assertEqual(bgp_states.get("FAILOVER"), "IDLE")
        self.assertEqual(bgp_states.get("RECOVERY"), "ESTABLISHED")

    def test_15_qos_congestion_and_drop_progression_in_splunk(self) -> None:
        """Item 15: QoS queue depth and packet drop progression observed in Splunk via | mstats."""
        q5_rows = self.aci_artifacts["query_outputs"]["q5_qos_congestion_drops_mstats"]
        self.assertGreater(len(q5_rows), 0)
        qlen_by_phase = {
            r.get("netspout_phase"): float(r.get("max_val", 0))
            for r in q5_rows
            if r.get("gnmi_leaf") == "max-queue-len"
        }
        self.assertGreater(qlen_by_phase.get("DEGRADE", 0), qlen_by_phase.get("BASELINE", 0))
        self.assertLess(qlen_by_phase.get("RECOVERY", 0), qlen_by_phase.get("DEGRADE", 0))

    def test_16_optical_degradation_and_recovery_in_splunk(self) -> None:
        """Item 16: Optical RX power degradation and recovery observed in Splunk via | mstats."""
        q6_rows = self.spc_artifacts["query_outputs"]["q6_optical_signal_degradation_mstats"]
        self.assertGreater(len(q6_rows), 0)
        rx_by_phase = {
            r.get("netspout_phase"): float(r.get("avg_dbm", 0))
            for r in q6_rows
            if "input-power" in str(r.get("gnmi_path", ""))
            or r.get("gnmi_leaf") == "laser-rx-optical-power-dbm"
        }
        self.assertGreater(rx_by_phase.get("BASELINE", -99.0), -10.0)
        self.assertLess(rx_by_phase.get("DEGRADE", 0.0), -20.0)
        self.assertLess(rx_by_phase.get("FAILOVER", 0.0), -20.0)
        self.assertGreater(rx_by_phase.get("RECOVERY", -99.0), -10.0)

    def test_17_cpu_memory_temperature_telemetry_in_splunk(self) -> None:
        """Item 17: CPU, memory, and temperature telemetry observed in Splunk via | mstats."""
        q7_rows = self.oc_artifacts["query_outputs"]["q7_system_cpu_memory_health_mstats"]
        self.assertGreater(len(q7_rows), 0)
        categories = {r.get("telemetry_category") for r in q7_rows}
        self.assertIn("system", categories)
        self.assertIn("environment", categories)

    def test_18_correlation_fields_preserved_and_wire_pure(self) -> None:
        """Item 18: Out-of-band correlation fields are preserved in Splunk while wire payloads remain 100% pure."""
        self.assertTrue(self.spc_scorecard.wire_payload_pure)
        self.assertTrue(self.oc_scorecard.wire_payload_pure)
        self.assertTrue(self.mv_scorecard.wire_payload_pure)
        for ev in self.spc_artifacts["splunk_observed_events"][:15]:
            self.assertEqual(ev.get("netspout_run_id"), self.spc_scorecard.run_id)
            self.assertEqual(ev.get("netspout_scenario_id"), "service_provider_cisco")
            self.assertIn(ev.get("netspout_phase"), ("BASELINE", "DEGRADE", "FAILOVER", "RECOVERY"))
            self.assertEqual(ev.get("netspout_device_id"), "cisco-asr9k-pe1")
            self.assertTrue(len(str(ev.get("netspout_event_id", ""))) > 10)
            self.assertTrue(str(ev.get("fault_correlation_id", "")).startswith("fc-"))

    def test_19_keyed_gnmi_paths_preserved_in_splunk(self) -> None:
        """Item 19: Keyed gNMI paths ([name=HundredGigE0/0/0/0], [neighbor-address=10.255.0.2]) are preserved in Splunk."""
        paths = {ev.get("gnmi_path") for ev in self.spc_artifacts["splunk_observed_events"]}
        self.assertIn("/interfaces/interface[name=HundredGigE0/0/0/0]/state/oper-status", paths)
        self.assertIn(
            "/network-instances/network-instance[name=default]/protocols/protocol[identifier=BGP][name=BGP]/bgp/neighbors/neighbor[neighbor-address=10.255.0.2]/state/session-state",
            paths,
        )

    def test_20_native_datatypes_preserved_in_splunk(self) -> None:
        """Item 20: Native datatypes (int, float, bool, str, object) are preserved across event and metric stores."""
        ev_types = {ev.get("gnmi_value_type") for ev in self.spc_artifacts["splunk_observed_events"]}
        met_types = {m.get("gnmi_value_type") for m in self.spc_artifacts["metric_records"]}
        combined_types = ev_types | met_types
        for expected_t in ("int", "float", "bool", "str", "object"):
            self.assertIn(expected_t, combined_types)

    def test_21_spl_investigation_queries_execute_and_return_results(self) -> None:
        """Item 21: All canonical SPL investigation queries (q1, q2, q3, q4, q8, q10) execute and return results."""
        for qk in ("q1_run_overview_spl", "q2_phase_progression_spl", "q3_interface_state_transition_spl", "q4_bgp_neighbor_transition_spl"):
            self.assertGreater(self.spc_scorecard.query_execution_summary.get(qk, 0), 0, f"Query {qk} returned 0 rows")
        self.assertEqual(len(self.mv_artifacts["vendor_summary_rows"]), 4)
        self.assertEqual(len(self.xtrans_report["timeline_by_phase"]), 4)

    def test_22_mstats_queries_execute_and_return_results(self) -> None:
        """Item 22: All canonical | mstats queries (q5, q6, q7, q9) execute against cisco_mdt_metrics."""
        for qk in ("q5_qos_congestion_drops_mstats", "q6_optical_signal_degradation_mstats", "q7_system_cpu_memory_health_mstats", "q9_metric_catalog_mstats"):
            self.assertGreater(self.spc_scorecard.query_execution_summary.get(qk, 0), 0, f"mstats query {qk} returned 0 rows")

    def test_23_validation_engine_passes_on_valid_splunk_evidence(self) -> None:
        """Item 23: ValidationEngine passes all scenario validation rules on valid Splunk evidence."""
        for sc in (self.spc_scorecard, self.oc_scorecard, self.aci_scorecard, self.mv_scorecard):
            self.assertEqual(sc.validation_status, "PASS")
            self.assertEqual(sc.validation_rules_failed, 0)
            self.assertGreater(sc.validation_rules_passed, 0)

    def test_24_validation_engine_fails_on_missing_splunk_evidence(self) -> None:
        """Item 24: ValidationEngine strictly fails when required Splunk event or metric evidence is missing."""
        rules = build_scenario_validation_rules("service_provider_cisco")
        empty_results = ValidationEngine.evaluate_all(rules, [], metrics=[])
        for r in empty_results:
            self.assertEqual(r.status, ValidationStatus.FAIL, f"Rule {r.rule_id} did not fail on empty evidence")

    def test_25_controlled_failures_a_through_i_verified(self) -> None:
        """Item 25: All 9 controlled failure scenarios (A through I) are verified with honest stage accounting."""
        self.assertTrue(self.controlled_failures["all_9_controlled_failures_verified"])
        for key in (
            "failure_A_server_unavailable",
            "failure_B_collector_unavailable",
            "failure_C_splunk_unavailable",
            "failure_D_invalid_auth",
            "failure_E_unsupported_path",
            "failure_F_missing_correlation_phase",
            "failure_G_missing_vendor_field",
            "failure_H_metric_destination_failure",
            "failure_I_duplicate_collector_records",
        ):
            self.assertIn(key, self.controlled_failures)
            self.assertTrue(self.controlled_failures[key]["passed_negative_check"], f"{key} failed check")

    def test_26_cross_transport_coherence_verified_in_splunk(self) -> None:
        """Item 26: Cross-transport coherence (gNMI + SNMP + Syslog + NetFlow/IPFIX) verified in Splunk."""
        self.assertTrue(self.xtrans_report["cross_transport_coherent"])
        self.assertEqual(self.xtrans_report["coherence_validation"]["status"], "PASS")
        self.assertEqual(len(self.xtrans_report["timeline_by_phase"]), 4)

    def test_27_performance_and_resource_guardrails_verified(self) -> None:
        """Item 27: Collector-to-Splunk performance benchmark and resource guardrails verified."""
        self.assertGreater(self.perf_benchmark["collector_receive_latency_ms"], 0.0)
        self.assertGreater(self.perf_benchmark["normalized_to_splunk_hec_dispatch_latency_ms"], 0.0)
        self.assertGreater(self.perf_benchmark["splunk_dispatch_to_searchable_observation_latency_ms"], 0.0)
        self.assertEqual(self.perf_benchmark["ingestion_counts"]["dispatch_errors"], 0)
        self.assertEqual(self.perf_benchmark["guardrails_enforced"]["loopback_only_bind"], "127.0.0.1")
        self.assertEqual(self.perf_benchmark["guardrails_enforced"]["min_sample_interval_ms"], 500)


if __name__ == "__main__":
    unittest.main()
