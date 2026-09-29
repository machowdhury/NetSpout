"""
NetSpout Gate 12D — External SNMP Collector/Poller -> Splunk End-to-End Integration Test Suite.

Covers all 22 mandatory verification areas specified in Gate 12D Section 17:
  1. External trap receiver (/usr/sbin/snmptrapd) receives SNMPv2c Trap (0xA7)
  2. External trap receiver receives InformRequest (0xA6) and returns Response-PDU (0xA2)
  3. External poller (/usr/bin/snmpget) performs GET (0xA0)
  4. External poller (/usr/bin/snmpgetnext) performs GETNEXT (0xA1)
  5. External poller (/usr/bin/snmpbulkwalk) performs GETBULK (0xA5)
  6. External poller (/usr/bin/snmpwalk & /usr/bin/snmpbulkwalk) performs full OID walk
  7. Collector output normalization for traps/informs (sourcetype="netspout:snmp:trap")
  8. Poller output normalization for polled OIDs (sourcetype="netspout:snmp:poll")
  9. Out-of-band run correlation field attachment without polluting native SNMP wire
 10. Splunk HEC ingestion of trap/inform events
 11. Splunk HEC ingestion of polling events
 12. Fresh Splunk SPL observation of trap/inform events
 13. Fresh Splunk SPL observation of polling events
 14. Phase progression reconstruction in Splunk (BASELINE -> DEGRADE -> FAILOVER -> RECOVERY)
 15. Trap/Poll state coherence verification
 16. Scenario validation pass on complete Splunk evidence
 17. Controlled Failure A: receiver down -> validation FAIL
 18. Controlled Failure B: receiver up, Splunk down -> validation FAIL
 19. Controlled Failure C: agent down -> poll fails, no fabricated Splunk records
 20. Controlled Failure D: missing phase -> validation FAIL
 21. Controlled Failure E: duplicate/retried inform -> deduplicated deterministically
 22. Cross-run isolation & ScenarioRunner RunManifest integration
"""

import json
import os
import unittest
import uuid
from typing import Any, Dict, List

from netspout_core.models import (
    NormalizedSnmpEvent,
    ScenarioRunRequest,
    SnmpE2ERunScorecard,
    SnmpEvidenceStage,
    SnmpPduType,
)
from netspout_core.scenario_runner import ScenarioRunner
from netspout_core.snmp_agent import SimulatedSnmpAgent
from netspout_core.snmp_ber import SnmpBerDecoder, SnmpBerEncoder
from netspout_core.snmp_engine import snmp_engine
from netspout_core.snmp_splunk_e2e import (
    PHASE_POLL_OIDS,
    TRAP_OID_CATALOG,
    ExternalNetSnmpPoller,
    ExternalSnmpTrapReceiver,
    SnmpCollectorNormalizer,
    SnmpSplunkBridge,
    SnmpSplunkE2EOrchestrator,
    build_snmp_investigation_queries,
)
from netspout_core.transport_native_snmp import NativeSnmpTransport


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EVIDENCE_DIR = os.path.join(REPO_ROOT, "docs", "acceptance", "evidence", "gate12d")


class TestGate12DSnmpSplunkE2E(unittest.TestCase):
    """
    Comprehensive automated acceptance suite for Gate 12D:
    Native SNMP -> External SNMP Collector/Poller -> Splunk -> SPL Evidence -> NetSpout Validation.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.orchestrator = SnmpSplunkE2EOrchestrator(
            index="idx_network_ops",
            device_id="cisco-asr9k-pe1",
            seed=42,
        )
        suffix = uuid.uuid4().hex[:8]
        cls.shared_run_id = f"run-gate12d-suite-{suffix}"
        cls.scorecard, cls.raw_artifacts = cls.orchestrator.execute_e2e_run(
            run_id=cls.shared_run_id,
            receiver_available=True,
            agent_available=True,
            splunk_available=True,
        )
        cls.controlled_failures = cls.orchestrator.run_all_controlled_failures(
            run_prefix=f"run-gate12d-cf-{suffix}"
        )

    # ------------------------------------------------------------------
    # 1. External trap receiver receives SNMPv2c Trap (0xA7)
    # ------------------------------------------------------------------
    def test_01_external_receiver_snmpv2c_trap_0xa7(self) -> None:
        self.assertEqual(self.scorecard.traps_generated, 4)
        self.assertEqual(self.scorecard.traps_sent, 4)
        self.assertEqual(self.scorecard.traps_receiver_observed, 4)

        in_trap_frames = []
        for fr in self.raw_artifacts["trap_pcap_frames"]:
            if fr["direction"] == "IN":
                msg = SnmpBerDecoder.decode_message(fr["payload"])
                if int(msg.pdu_type) == SnmpPduType.SNMPV2_TRAP.value:
                    in_trap_frames.append(msg)
        self.assertEqual(len(in_trap_frames), 4)

    # ------------------------------------------------------------------
    # 2. External trap receiver receives InformRequest (0xA6) and returns Response-PDU (0xA2)
    # ------------------------------------------------------------------
    def test_02_external_receiver_inform_request_0xa6_and_ack_0xa2(self) -> None:
        self.assertEqual(self.scorecard.informs_generated, 4)
        self.assertEqual(self.scorecard.informs_sent, 4)
        self.assertEqual(self.scorecard.informs_acknowledged, 4)
        self.assertEqual(self.scorecard.informs_receiver_observed, 4)

        in_inform_ids = set()
        out_resp_ids = set()
        for fr in self.raw_artifacts["trap_pcap_frames"]:
            msg = SnmpBerDecoder.decode_message(fr["payload"])
            if fr["direction"] == "IN" and int(msg.pdu_type) == SnmpPduType.INFORM_REQUEST.value:
                in_inform_ids.add(msg.request_id)
            elif fr["direction"] == "OUT" and int(msg.pdu_type) == SnmpPduType.RESPONSE.value:
                out_resp_ids.add(msg.request_id)
                self.assertEqual(msg.error_status, 0)

        self.assertEqual(len(in_inform_ids), 4)
        self.assertEqual(in_inform_ids, out_resp_ids)

    # ------------------------------------------------------------------
    # 3. External poller performs GET (0xA0)
    # ------------------------------------------------------------------
    def test_03_external_poller_get_0xa0(self) -> None:
        self.assertGreaterEqual(self.scorecard.get_requests, 4)
        for phase in ("BASELINE", "DEGRADE", "FAILOVER", "RECOVERY"):
            out_txt = self.raw_artifacts["cli_outputs"].get(f"snmpget_{phase}", "")
            self.assertIn(".1.3.6.1.2.1.1.3.0 =", out_txt)
            self.assertIn(".1.3.6.1.2.1.2.2.1.8.1 =", out_txt)
            self.assertIn(".1.3.6.1.2.1.15.3.1.2.198.51.100.1 =", out_txt)

    # ------------------------------------------------------------------
    # 4. External poller performs GETNEXT (0xA1)
    # ------------------------------------------------------------------
    def test_04_external_poller_getnext_0xa1(self) -> None:
        self.assertGreaterEqual(self.scorecard.getnext_requests, 4)
        for phase in ("BASELINE", "DEGRADE", "FAILOVER", "RECOVERY"):
            out_txt = self.raw_artifacts["cli_outputs"].get(f"snmpgetnext_{phase}", "")
            self.assertIn(".1.3.6.1.2.1.1.1.0 =", out_txt)
            self.assertIn(".1.3.6.1.2.1.2.2.1.8.1 =", out_txt)

    # ------------------------------------------------------------------
    # 5. External poller performs GETBULK (0xA5)
    # ------------------------------------------------------------------
    def test_05_external_poller_getbulk_0xa5(self) -> None:
        self.assertGreaterEqual(self.scorecard.getbulk_requests, 10)
        bwalk_base = self.raw_artifacts["cli_outputs"].get("snmpbulkwalk_BASELINE", "")
        bwalk_fail = self.raw_artifacts["cli_outputs"].get("snmpbulkwalk_FAILOVER", "")
        self.assertGreater(len(bwalk_base.splitlines()), 100)
        self.assertGreater(len(bwalk_fail.splitlines()), 100)

    # ------------------------------------------------------------------
    # 6. External poller performs full OID walk
    # ------------------------------------------------------------------
    def test_06_external_poller_full_oid_walk(self) -> None:
        self.assertEqual(self.scorecard.walk_oids_observed, 127)
        walk_base = self.raw_artifacts["cli_outputs"].get("snmpwalk_BASELINE", "")
        bwalk_base = self.raw_artifacts["cli_outputs"].get("snmpbulkwalk_BASELINE", "")
        obs_walk, m1 = ExternalNetSnmpPoller.parse_cli_output(walk_base, "GetNextRequest")
        obs_bwalk, m2 = ExternalNetSnmpPoller.parse_cli_output(bwalk_base, "GetBulkRequest")
        self.assertEqual(m1, 0)
        self.assertEqual(m2, 0)
        self.assertEqual(len(obs_walk), 127)
        self.assertEqual(len(obs_bwalk), 127)
        self.assertEqual([o["oid"] for o in obs_walk], [o["oid"] for o in obs_bwalk])

    # ------------------------------------------------------------------
    # 7. Collector output normalization for traps/informs
    # ------------------------------------------------------------------
    def test_07_collector_normalization_traps_and_informs(self) -> None:
        trap_events = [
            e for e in self.raw_artifacts["normalized_events"]
            if e.sourcetype == "netspout:snmp:trap"
        ]
        self.assertEqual(len(trap_events), 8)
        pdu_types = {e.snmp_pdu_type for e in trap_events}
        self.assertEqual(pdu_types, {"SNMPv2-Trap", "InformRequest"})
        trap_oids = {e.snmp_trap_oid for e in trap_events}
        self.assertEqual(trap_oids, set(TRAP_OID_CATALOG.keys()))
        for ev in trap_events:
            self.assertEqual(ev.snmp_collector, "snmptrapd")
            self.assertEqual(ev.snmp_version, "2c")
            self.assertEqual(ev.telemetry_semantics, "NATIVE TRANSPORT / MODELED DEVICE STATE")
            self.assertIsNotNone(ev.sys_uptime)
            self.assertIn("SNMPv2-MIB::snmpTrapOID.0", ev.varbinds)

    # ------------------------------------------------------------------
    # 8. Poller output normalization for polled OIDs
    # ------------------------------------------------------------------
    def test_08_poller_normalization_polled_oids(self) -> None:
        poll_events = [
            e for e in self.raw_artifacts["normalized_events"]
            if e.sourcetype == "netspout:snmp:poll"
        ]
        self.assertEqual(len(poll_events), 318)
        pdu_types = {e.snmp_pdu_type for e in poll_events}
        self.assertEqual(pdu_types, {"GetRequest", "GetNextRequest", "GetBulkRequest"})
        for ev in poll_events:
            self.assertEqual(ev.snmp_collector, "net-snmp-cli")
            self.assertEqual(ev.snmp_version, "2c")
            self.assertIsNone(ev.snmp_trap_oid)
            self.assertTrue(ev.snmp_oid.startswith("1.3.6.1.2.1."))

    # ------------------------------------------------------------------
    # 9. Out-of-band run correlation field attachment (no wire pollution)
    # ------------------------------------------------------------------
    def test_09_out_of_band_run_correlation_no_wire_pollution(self) -> None:
        # Verify every normalized event has out-of-band correlation fields
        for ev in self.raw_artifacts["normalized_events"]:
            self.assertEqual(ev.netspout_run_id, self.shared_run_id)
            self.assertEqual(ev.netspout_scenario_id, "service_provider_cisco")
            self.assertIn(ev.netspout_phase, {"BASELINE", "DEGRADE", "FAILOVER", "RECOVERY"})
            self.assertEqual(ev.netspout_device_id, "cisco-asr9k-pe1")
            self.assertTrue(ev.netspout_event_id.startswith("snmp-"))

        # Verify zero proprietary NetSpout correlation strings or enterprise OIDs exist on the SNMP wire
        all_frames = self.raw_artifacts["trap_pcap_frames"] + self.raw_artifacts["poll_pcap_frames"]
        self.assertGreater(len(all_frames), 50)
        for fr in all_frames:
            payload_bytes: bytes = fr["payload"]
            self.assertNotIn(self.shared_run_id.encode("utf-8"), payload_bytes)
            self.assertNotIn(b"netspout_run_id", payload_bytes)
            msg = SnmpBerDecoder.decode_message(payload_bytes)
            for vb in msg.varbinds:
                self.assertTrue(
                    vb.oid == "1.3.6.1.2.1"
                    or vb.oid.startswith("1.3.6.1.2.1.")
                    or vb.oid.startswith("1.3.6.1.6.3."),
                    f"Unexpected non-standard OID on SNMP wire: {vb.oid}",
                )

    # ------------------------------------------------------------------
    # 10. Splunk HEC ingestion of trap/inform events
    # ------------------------------------------------------------------
    def test_10_splunk_hec_ingestion_trap_inform_events(self) -> None:
        trap_events = [
            e for e in self.raw_artifacts["normalized_events"]
            if e.sourcetype == "netspout:snmp:trap"
        ]
        self.assertEqual(len(trap_events), 8)
        for ev in trap_events:
            self.assertEqual(ev.evidence_stage, SnmpEvidenceStage.SPLUNK_DISPATCHED.value)
        self.assertEqual(self.scorecard.splunk_dispatch_failures, 0)
        self.assertEqual(self.scorecard.splunk_dispatched_status, "YES")

    # ------------------------------------------------------------------
    # 11. Splunk HEC ingestion of polling events
    # ------------------------------------------------------------------
    def test_11_splunk_hec_ingestion_polling_events(self) -> None:
        poll_events = [
            e for e in self.raw_artifacts["normalized_events"]
            if e.sourcetype == "netspout:snmp:poll"
        ]
        self.assertEqual(len(poll_events), 318)
        for ev in poll_events:
            self.assertEqual(ev.evidence_stage, SnmpEvidenceStage.SPLUNK_DISPATCHED.value)
        self.assertEqual(self.scorecard.splunk_dispatched_records, 326)

    # ------------------------------------------------------------------
    # 12. Fresh Splunk SPL observation of trap/inform events
    # ------------------------------------------------------------------
    def test_12_fresh_splunk_spl_observation_trap_inform(self) -> None:
        self.assertEqual(self.scorecard.splunk_observed_trap_records, 8)
        trap_spl_rows = self.raw_artifacts["splunk_search_results"]["trap_inform_evidence_spl"]
        self.assertEqual(len(trap_spl_rows), 8)
        observed_names = {r.get("snmp_trap_name") for r in trap_spl_rows}
        self.assertEqual(
            observed_names,
            {
                "IF-MIB::linkDown",
                "BGP4-MIB::bgpBackwardTransition",
                "IF-MIB::linkUp",
                "BGP4-MIB::bgpEstablished",
            },
        )

    # ------------------------------------------------------------------
    # 13. Fresh Splunk SPL observation of polling events
    # ------------------------------------------------------------------
    def test_13_fresh_splunk_spl_observation_polling(self) -> None:
        self.assertEqual(self.scorecard.splunk_observed_poll_records, 318)
        poll_spl_rows = self.raw_artifacts["splunk_search_results"]["polling_evidence_spl"]
        self.assertEqual(len(poll_spl_rows), 318)
        self.assertEqual(self.scorecard.observation_completeness_pct, 100.0)
        self.assertEqual(self.scorecard.splunk_observed_status, "YES")

    # ------------------------------------------------------------------
    # 14. Phase progression reconstruction in Splunk
    # ------------------------------------------------------------------
    def test_14_phase_progression_reconstruction_in_splunk(self) -> None:
        timeline_rows = self.raw_artifacts["splunk_search_results"]["timeline_spl"]
        self.assertEqual(len(timeline_rows), 4)
        phases_in_timeline = {r.get("netspout_phase") for r in timeline_rows}
        self.assertEqual(
            phases_in_timeline,
            {"BASELINE", "DEGRADE", "FAILOVER", "RECOVERY"},
        )
        corr_rows = self.raw_artifacts["splunk_search_results"]["notification_vs_poll_correlation_spl"]
        self.assertEqual(len(corr_rows), 4)
        by_phase = {r["netspout_phase"]: r for r in corr_rows}
        self.assertEqual(int(by_phase["BASELINE"]["notification_count"]), 0)
        self.assertEqual(int(by_phase["DEGRADE"]["notification_count"]), 2)
        self.assertEqual(int(by_phase["FAILOVER"]["notification_count"]), 2)
        self.assertEqual(int(by_phase["RECOVERY"]["notification_count"]), 4)

    # ------------------------------------------------------------------
    # 15. Trap/Poll state coherence verification
    # ------------------------------------------------------------------
    def test_15_trap_poll_state_coherence_verification(self) -> None:
        self.assertTrue(self.scorecard.trap_poll_coherence)
        checks = self.scorecard.coherence_details.get("checks", {})
        expected_keys = [
            "baseline_if_up",
            "baseline_bgp_est",
            "degrade_if_down_matches_linkDown_trap",
            "degrade_if_errors_elevated",
            "failover_bgp_idle_matches_bgpBackwardTransition_trap",
            "failover_backup_route_active",
            "recovery_if_up_matches_linkUp_trap",
            "recovery_bgp_est_matches_bgpEstablished_trap",
            "recovery_primary_route_restored",
        ]
        for k in expected_keys:
            self.assertTrue(checks.get(k), f"Coherence check '{k}' did not pass: {checks}")

    # ------------------------------------------------------------------
    # 16. Scenario validation pass on complete Splunk evidence
    # ------------------------------------------------------------------
    def test_16_scenario_validation_pass_on_complete_splunk_evidence(self) -> None:
        self.assertEqual(self.scorecard.validation_result, "PASS")
        self.assertEqual(self.scorecard.evidence_stage, SnmpEvidenceStage.VALIDATED.value)
        self.assertEqual(
            self.scorecard.stage_history,
            [
                "GENERATED",
                "ENCODED",
                "SENT",
                "ACKNOWLEDGED",
                "RECEIVER_OBSERVED",
                "SPLUNK_DISPATCHED",
                "SPLUNK_OBSERVED",
                "VALIDATED",
            ],
        )
        for k, v in self.scorecard.stage_classification.items():
            self.assertEqual(v, "YES", f"Stage {k} was not YES: {v}")

    # ------------------------------------------------------------------
    # 17. Failure A: receiver down -> validation FAIL
    # ------------------------------------------------------------------
    def test_17_controlled_failure_a_receiver_down(self) -> None:
        res_a = self.controlled_failures["results"]["failure_a"]
        self.assertTrue(res_a["expected_behavior_verified"])
        self.assertEqual(res_a["traps_sent"], 4)
        self.assertEqual(res_a["informs_acknowledged"], 0)
        self.assertEqual(res_a["receiver_observed_notifications"], 0)
        self.assertEqual(res_a["splunk_observed_records"], 0)
        self.assertEqual(res_a["stage_classification"]["SENT"], "YES")
        self.assertEqual(res_a["stage_classification"]["ACKNOWLEDGED"], "NO")
        self.assertEqual(res_a["stage_classification"]["RECEIVER_OBSERVED"], "NO")
        self.assertEqual(res_a["stage_classification"]["SPLUNK_OBSERVED"], "NO")
        self.assertEqual(res_a["validation_result"], "FAIL")

    # ------------------------------------------------------------------
    # 18. Failure B: receiver up, Splunk down -> validation FAIL
    # ------------------------------------------------------------------
    def test_18_controlled_failure_b_receiver_up_splunk_down(self) -> None:
        res_b = self.controlled_failures["results"]["failure_b"]
        self.assertTrue(res_b["expected_behavior_verified"])
        self.assertEqual(res_b["receiver_observed_notifications"], 8)
        self.assertGreater(res_b["polling_responses"], 0)
        self.assertEqual(res_b["splunk_dispatched_records"], 0)
        self.assertEqual(res_b["splunk_observed_records"], 0)
        self.assertEqual(res_b["stage_classification"]["RECEIVER_OBSERVED"], "YES")
        self.assertEqual(res_b["stage_classification"]["SPLUNK_DISPATCHED"], "NO")
        self.assertEqual(res_b["stage_classification"]["SPLUNK_OBSERVED"], "NO")
        self.assertEqual(res_b["validation_result"], "FAIL")

    # ------------------------------------------------------------------
    # 19. Failure C: agent down -> poll fails, no fabricated Splunk records
    # ------------------------------------------------------------------
    def test_19_controlled_failure_c_agent_down(self) -> None:
        res_c = self.controlled_failures["results"]["failure_c"]
        self.assertTrue(res_c["expected_behavior_verified"])
        self.assertGreaterEqual(res_c["polling_requests"], 1)
        self.assertEqual(res_c["polling_responses"], 0)
        self.assertEqual(res_c["normalized_poll_records"], 0)
        self.assertEqual(res_c["splunk_observed_poll_records"], 0)
        self.assertEqual(res_c["validation_result"], "FAIL")

    # ------------------------------------------------------------------
    # 20. Failure D: missing phase -> validation FAIL
    # ------------------------------------------------------------------
    def test_20_controlled_failure_d_missing_phase(self) -> None:
        res_d = self.controlled_failures["results"]["failure_d"]
        self.assertTrue(res_d["expected_behavior_verified"])
        self.assertEqual(res_d["suppressed_phase"], "RECOVERY")
        self.assertNotIn("RECOVERY", res_d["phases_verified"])
        self.assertFalse(res_d["missing_phase_check"]["passed"])
        self.assertEqual(res_d["validation_result"], "FAIL")

    # ------------------------------------------------------------------
    # 21. Failure E: duplicate/retried inform -> deduplicated deterministically
    # ------------------------------------------------------------------
    def test_21_controlled_failure_e_duplicate_retried_inform(self) -> None:
        res_e = self.controlled_failures["results"]["failure_e"]
        self.assertTrue(res_e["expected_behavior_verified"])
        self.assertEqual(res_e["raw_notifications_received"], 8)
        self.assertEqual(res_e["receiver_deduplicated_notifications"], 4)
        self.assertEqual(res_e["receiver_duplicate_informs_suppressed"], 4)
        self.assertEqual(res_e["normalizer_unique_events"], 4)
        self.assertEqual(res_e["normalizer_duplicate_events_suppressed"], 4)

    # ------------------------------------------------------------------
    # 22. Cross-run isolation & ScenarioRunner RunManifest integration
    # ------------------------------------------------------------------
    def test_22_cross_run_isolation_and_manifest_integration(self) -> None:
        # Inject a foreign run_id row into validate_splunk_evidence and confirm it is rejected
        contaminated_traps = list(self.raw_artifacts["splunk_search_results"]["trap_rows"]) + [
            {
                "netspout_run_id": "foreign-run-999",
                "netspout_phase": "DEGRADE",
                "snmp_pdu_type": "SNMPv2-Trap",
                "snmp_trap_oid": "1.3.6.1.6.3.1.1.5.3",
            }
        ]
        passed, checks, _, _ = SnmpSplunkE2EOrchestrator.validate_splunk_evidence(
            run_id=self.shared_run_id,
            trap_rows=contaminated_traps,
            poll_rows=self.raw_artifacts["splunk_search_results"]["poll_rows"],
        )
        self.assertFalse(passed)
        iso_check = next(c for c in checks if c["check_id"] == "run_correlation_isolation")
        self.assertFalse(iso_check["passed"])
        self.assertEqual(iso_check["foreign_records"], 1)

        # Verify committed Gate 12D evidence artifacts exist and are valid
        required_files = [
            "gate12d_e2e.pcap",
            "tshark_verbose_output.txt",
            "snmptrapd_output.txt",
            "external_polling_output.txt",
            "normalized_events.json",
            "splunk_search_evidence.json",
            "controlled_failures_evidence.json",
            "run_manifest.json",
            "e2e_scorecard.json",
        ]
        for fname in required_files:
            fpath = os.path.join(EVIDENCE_DIR, fname)
            self.assertTrue(os.path.exists(fpath), f"Missing Gate 12D evidence file: {fpath}")
            self.assertGreater(os.path.getsize(fpath), 100)


if __name__ == "__main__":
    unittest.main()
