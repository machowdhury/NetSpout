"""
NetSpout Gate 12F — Native SNMP Productization & Acceptance Closure Test Suite.

Covers all 12 mandatory Gate 12F assertions across:
  - F-12E-01: Customer workflow & HTTP API wiring for Native SNMPv2c E2E (`service_provider_cisco`)
  - F-12E-02: Canonical catalog registration (`netspout:snmp:trap`, `netspout:snmp:poll`, `native_snmp_supported`, `native_snmp_capabilities`)
  - F-12E-03: Evidence-stage provenance preservation (`origin_evidence_stage="RECEIVER_OBSERVED"` vs `current_evidence_stage`)
  - F-12E-04: Canonical device identity alignment (`cisco-asr9k-pe1`) and elimination of redundant port 1162 UDP send
  - F-12E-05: Legacy Mode A (`sc4snmp:metric` / `sc4snmp:event`) UI disambiguation and workflow launcher
  - Preflight check API (`GET /api/native-snmp/preflight`, `POST /api/native-snmp/preflight`)
  - Controlled Failure 6: Refusal of silent downgrade to Mode A on missing/invalid native transport config
  - Controlled Failures A–E & G: Receiver down, Splunk down, Agent poll down, Missing phase, Duplicate inform dedup, Bad community/Malformed BER/SET rejection
  - Frontend workflow components & Honesty guardrails (`NATIVE TRANSPORT` + `MODELED DEVICE STATE`)
"""

import asyncio
import json
import os
import socket
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.main import app
from netspout_core.catalog import catalog_instance
from netspout_core.models import (
    NormalizedSnmpEvent,
    ScenarioRunRequest,
    SnmpEvidenceStage,
    SnmpMessage,
    SnmpPduType,
    SnmpVarBind,
)
from netspout_core.scenario_runner import ScenarioRunner, scenario_runner
from netspout_core.snmp_agent import (
    SimulatedSnmpAgent,
    build_service_provider_cisco_oid_store,
)
from netspout_core.snmp_ber import SnmpBerDecodeError, SnmpBerDecoder, SnmpBerEncoder
from netspout_core.snmp_splunk_e2e import (
    SnmpSplunkE2EOrchestrator,
    run_snmp_preflight_check,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


class _AsgiResponse:
    def __init__(self, status_code: int, body: bytes):
        self.status_code = status_code
        self.text = body.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.text)


class _AsgiClient:
    def __init__(self, asgi_app):
        self.app = asgi_app

    def request(self, method: str, path: str, json_body=None) -> _AsgiResponse:
        body_bytes = (
            json.dumps(json_body).encode("utf-8") if json_body is not None else b""
        )
        headers = [(b"host", b"testserver")]
        if json_body is not None:
            headers.append((b"content-type", b"application/json"))
            headers.append((b"content-length", str(len(body_bytes)).encode("ascii")))

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method.upper(),
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
        }
        sent_req = False
        status_code = 500
        resp_chunks = []

        async def receive():
            nonlocal sent_req
            if not sent_req:
                sent_req = True
                return {
                    "type": "http.request",
                    "body": body_bytes,
                    "more_body": False,
                }
            return {"type": "http.disconnect"}

        async def send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                resp_chunks.append(message.get("body", b""))

        asyncio.run(self.app(scope, receive, send))
        return _AsgiResponse(status_code, b"".join(resp_chunks))

    def get(self, path: str) -> _AsgiResponse:
        return self.request("GET", path)

    def post(self, path: str, json=None) -> _AsgiResponse:
        return self.request("POST", path, json_body=json)


class TestGate12FSnmpProductization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = _AsgiClient(app)

    def test_01_f12e01_customer_workflow_native_snmp_execution(self):
        """F-12E-01: ScenarioRunner executes Native SNMPv2c E2E when transport_mode=NATIVE_TRANSPORT."""
        req = ScenarioRunRequest(
            scenario_id="service_provider_cisco",
            time_mode="TEST",
            seed=42,
            dispatch_telemetry=False,
            transport_mode="NATIVE_TRANSPORT",
            native_protocol="SNMPV2C_E2E",
            native_snmp_e2e=True,
            native_snmp_pdu_mode="MIXED",
            native_snmp_community="netspout-lab",
        )
        manifest = scenario_runner.run_scenario(req)
        self.assertEqual(manifest.scenario_id, "service_provider_cisco")
        self.assertEqual(manifest.transport_mode, "NATIVE_TRANSPORT")
        self.assertEqual(manifest.native_protocol, "SNMPV2C_E2E")
        self.assertIsNotNone(manifest.snmp_e2e_scorecard)
        self.assertEqual(manifest.snmp_e2e_scorecard.validation_result, "PASS")
        self.assertEqual(manifest.snmp_e2e_scorecard.device_id, "cisco-asr9k-pe1")
        self.assertIsNotNone(manifest.native_snmp_result)
        self.assertIsNotNone(manifest.companion_manifest)
        self.assertGreaterEqual(len(manifest.snmp_normalized_events), 300)
        self.assertIsNotNone(manifest.snmp_polling_evidence)

    def test_02_f12e01_http_api_forwards_native_snmp_parameters(self):
        """F-12E-01: POST /api/scenarios/service_provider_cisco/run forwards native SNMP params and returns E2E scorecard."""
        resp = self.client.post(
            "/api/scenarios/service_provider_cisco/run",
            json={
                "speed_mode": "TEST",
                "seed": 42,
                "dispatch_telemetry": False,
                "transport_mode": "NATIVE_TRANSPORT",
                "native_protocol": "SNMPV2C_E2E",
                "native_snmp_e2e": True,
                "native_snmp_pdu_mode": "MIXED",
                "native_snmp_community": "netspout-lab",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(data["transport_mode"], "NATIVE_TRANSPORT")
        self.assertEqual(data["native_protocol"], "SNMPV2C_E2E")
        scorecard = data.get("snmp_e2e_scorecard")
        self.assertIsNotNone(scorecard)
        self.assertEqual(scorecard["validation_result"], "PASS")
        self.assertEqual(scorecard["origin_evidence_stage"], "RECEIVER_OBSERVED")
        self.assertIn(scorecard["current_evidence_stage"], ("SPLUNK_OBSERVED", "VALIDATED"))
        self.assertGreaterEqual(scorecard["splunk_observed_records"], 300)

    def test_03_f12e02_catalog_sourcetypes_and_scenario_contract(self):
        """F-12E-02: Canonical catalog registers netspout:snmp:trap, netspout:snmp:poll, and service_provider_cisco capabilities."""
        st_data = json.loads((REPO_ROOT / "catalog" / "sourcetypes.json").read_text(encoding="utf-8"))
        st_map = {item["splunk_sourcetype"]: item for item in st_data}
        self.assertIn("netspout:snmp:trap", st_map)
        self.assertIn("netspout:snmp:poll", st_map)
        self.assertFalse(st_map["netspout:snmp:trap"]["is_benchmark_197"])
        self.assertFalse(st_map["netspout:snmp:poll"]["is_benchmark_197"])

        contract = catalog_instance.get_scenario_contract("service_provider_cisco")
        self.assertIsNotNone(contract)
        self.assertTrue(contract.native_snmp_supported)
        self.assertIn("snmp", contract.telemetry_requirements)
        self.assertIn("netspout:snmp:trap", contract.sourcetypes)
        self.assertIn("netspout:snmp:poll", contract.sourcetypes)
        self.assertEqual(contract.affected_entities, ["cisco-asr9k-pe1"])
        caps = contract.native_snmp_capabilities or {}
        self.assertEqual(caps.get("transport_fidelity"), "NATIVE TRANSPORT")
        self.assertEqual(caps.get("device_state_fidelity"), "MODELED DEVICE STATE")
        self.assertEqual(caps.get("canonical_device_id"), "cisco-asr9k-pe1")

    def test_04_f12e02_use_cases_api_exposes_native_snmp_metadata(self):
        """F-12E-02: GET /api/use-cases exposes native_snmp_supported and capabilities for service_provider_cisco."""
        resp = self.client.get("/api/use-cases")
        self.assertEqual(resp.status_code, 200)
        use_cases = resp.json().get("use_cases", [])
        sp_uc = next((u for u in use_cases if u.get("scenario_id") == "service_provider_cisco"), None)
        self.assertIsNotNone(sp_uc)
        self.assertTrue(sp_uc["native_snmp_supported"])
        self.assertIn("snmp", sp_uc["telemetry_requirements"])
        self.assertIn("netspout:snmp:trap", sp_uc["sourcetypes"])
        self.assertIn("netspout:snmp:poll", sp_uc["sourcetypes"])
        self.assertEqual(sp_uc["affected_entities"], ["cisco-asr9k-pe1"])
        self.assertIsNotNone(sp_uc["native_snmp_capabilities"])

    def test_05_f12e03_evidence_stage_provenance_preserved(self):
        """F-12E-03: NormalizedSnmpEvent preserves origin_evidence_stage=RECEIVER_OBSERVED across HEC dispatch and Splunk observation."""
        ev = NormalizedSnmpEvent(
            netspout_run_id="NS-TEST-PROV",
            netspout_scenario_id="service_provider_cisco",
            netspout_phase="DEGRADE",
            netspout_device_id="cisco-asr9k-pe1",
            netspout_event_id="evt-1",
            timestamp=time.time(),
            sourcetype="netspout:snmp:trap",
            index="idx_network_ops",
            snmp_collector="snmptrapd",
            snmp_pdu_type="SNMPv2-Trap",
            snmp_oid="1.3.6.1.2.1.2.2.1.8.1",
            snmp_oid_name="IF-MIB::ifOperStatus.1",
            snmp_value="2",
            snmp_value_type="INTEGER",
        )
        self.assertEqual(ev.origin_evidence_stage, SnmpEvidenceStage.RECEIVER_OBSERVED.value)
        self.assertEqual(ev.current_evidence_stage, SnmpEvidenceStage.RECEIVER_OBSERVED.value)
        hec_payload = ev.to_hec_payload()
        self.assertEqual(hec_payload["event"]["origin_evidence_stage"], "RECEIVER_OBSERVED")
        self.assertEqual(hec_payload["event"]["current_evidence_stage"], "RECEIVER_OBSERVED")

    def test_06_f12e04_device_identity_aligned_and_no_redundant_udp_1162_send(self):
        """F-12E-04: Canonical device identity is cisco-asr9k-pe1 everywhere and E2E mode does not invoke redundant port 1162 send_batch."""
        from netspout_core.transport_native_snmp import NativeSnmpTransport

        orig_send_batch = NativeSnmpTransport.send_batch
        with patch.object(
            NativeSnmpTransport,
            "send_batch",
            autospec=True,
            side_effect=lambda self_inst, *a, **kw: orig_send_batch(self_inst, *a, **kw),
        ) as spy_send_batch:
            req = ScenarioRunRequest(
                scenario_id="service_provider_cisco",
                time_mode="TEST",
                seed=42,
                dispatch_telemetry=False,
                transport_mode="NATIVE_TRANSPORT",
                native_protocol="SNMPV2C_E2E",
                native_snmp_e2e=True,
            )
            manifest = scenario_runner.run_scenario(req)
            self.assertEqual(manifest.affected_devices, ["cisco-asr9k-pe1"])
            for gt in manifest.ground_truth_records:
                if gt.affected_nodes:
                    self.assertIn("cisco-asr9k-pe1", gt.affected_nodes)
                    self.assertNotIn("node-cisco8k-core01", gt.affected_nodes)
            logs = scenario_runner.get_run_logs(manifest.run_id)
            self.assertGreater(len(logs), 0)
            for log_entry in logs:
                self.assertEqual(log_entry.device_id, "cisco-asr9k-pe1")
            # NativeSnmpTransport.send_batch is called only inside SnmpSplunkE2EOrchestrator against live snmptrapd ephemeral port, never against unobserved port 1162
            self.assertGreaterEqual(spy_send_batch.call_count, 1)
            for call in spy_send_batch.call_args_list:
                transport_inst = call[0][0]
                self.assertNotEqual(transport_inst.destination_port, 1162)

    def test_07_f12e05_legacy_mode_a_sc4snmp_disambiguation(self):
        """F-12E-05: TopBar.tsx and SNMPMibModal.tsx clearly disambiguate Mode A preview from Mode B Native SNMPv2c."""
        topbar_src = (REPO_ROOT / "frontend" / "src" / "components" / "TopBar.tsx").read_text(encoding="utf-8")
        modal_src = (REPO_ROOT / "frontend" / "src" / "components" / "SNMPMibModal.tsx").read_text(encoding="utf-8")

        self.assertIn("Mode A — HEC Payload Preview (SC4SNMP)", topbar_src)
        self.assertIn("open-mode-a-snmp-modal-btn", topbar_src)
        self.assertIn("Mode A — HEC Payload Preview (sc4snmp:metric / sc4snmp:event)", modal_src)
        self.assertIn("NOT the native UDP SNMPv2c BER/ASN.1 protocol engine", modal_src)
        self.assertIn("launch-native-snmp-workflow-btn", modal_src)

    def test_08_native_snmp_preflight_api_and_checks(self):
        """Section 8: Preflight API validates Net-SNMP binaries, snmptrapd, UDP bind, Splunk HEC, REST search, and index."""
        direct = run_snmp_preflight_check(index="idx_network_ops")
        self.assertEqual(direct["status"], "READY")
        self.assertTrue(direct["all_passed"])
        check_ids = {c["id"] for c in direct["checks"]}
        self.assertEqual(
            check_ids,
            {
                "net_snmp_cli_binaries",
                "snmptrapd_binary",
                "local_udp_bind",
                "splunk_hec_reachability",
                "splunk_rest_search",
                "target_index_availability",
            },
        )

        resp_get = self.client.get("/api/native-snmp/preflight")
        self.assertEqual(resp_get.status_code, 200)
        self.assertEqual(resp_get.json()["status"], "READY")

        resp_post = self.client.post("/api/native-snmp/preflight", json={"index": "idx_network_ops"})
        self.assertEqual(resp_post.status_code, 200)
        self.assertEqual(resp_post.json()["status"], "READY")

    def test_09_controlled_failure_no_silent_downgrade_to_mode_a(self):
        """Section 3 & 13: Missing or invalid Native Transport parameters fail explicitly (HTTP 400 / ValueError) without silent Mode A fallback."""
        # 1. Missing native_protocol / native_snmp_pdu_mode / native_snmp_e2e when transport_mode=NATIVE_TRANSPORT
        resp_missing = self.client.post(
            "/api/scenarios/service_provider_cisco/run",
            json={"transport_mode": "NATIVE_TRANSPORT"},
        )
        self.assertEqual(resp_missing.status_code, 400)
        self.assertIn("Refusing silent downgrade to Mode A", resp_missing.json()["detail"])

        # 2. Invalid native_protocol for service_provider_cisco
        resp_bad_proto = self.client.post(
            "/api/scenarios/service_provider_cisco/run",
            json={"transport_mode": "NATIVE_TRANSPORT", "native_protocol": "NETFLOW_V9"},
        )
        self.assertEqual(resp_bad_proto.status_code, 400)

        # 3. Unsupported scenario for Native SNMP
        resp_unsupported = self.client.post(
            "/api/scenarios/cisco_sdwan_brownout/run",
            json={
                "transport_mode": "NATIVE_TRANSPORT",
                "native_protocol": "SNMPV2C_E2E",
                "native_snmp_e2e": True,
            },
        )
        self.assertEqual(resp_unsupported.status_code, 400)

    def test_10_controlled_failures_a_through_e_and_g(self):
        """Section 13: Controlled Failures A–E and G behave deterministically and honestly."""
        orch = SnmpSplunkE2EOrchestrator(index="idx_network_ops", device_id="cisco-asr9k-pe1", seed=42)
        cf_all = orch.run_all_controlled_failures(run_prefix="NS-20260929-unit-cf")
        self.assertTrue(cf_all["all_verified"], json.dumps(cf_all, indent=2))

        # Controlled Failure G: Invalid community, malformed BER, and read-only SET rejection
        store = build_service_provider_cisco_oid_store(seed=42, device_id="cisco-asr9k-pe1")
        agent = SimulatedSnmpAgent(oid_store=store, bind_host="127.0.0.1", bind_port=0, community="netspout-lab")
        port = agent.start()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(0.3)
            bad_msg = SnmpMessage(
                version=1,
                community="invalid-community",
                pdu_type=SnmpPduType.GET_REQUEST,
                request_id=9101,
                varbinds=[SnmpVarBind(oid="1.3.6.1.2.1.1.5.0", asn1_type="Null", value=None)],
            )
            sock.sendto(SnmpBerEncoder.encode_message(bad_msg), ("127.0.0.1", port))
            with self.assertRaises(socket.timeout):
                sock.recvfrom(4096)

            with self.assertRaises(SnmpBerDecodeError):
                SnmpBerDecoder.decode_message(b"\x30\x82\x01\x00\x02\x01")
            sock.sendto(b"\x30\x82\x01\x00\x02\x01", ("127.0.0.1", port))
            time.sleep(0.05)

            get_wire = bytearray(
                SnmpBerEncoder.encode_message(
                    SnmpMessage(
                        version=1,
                        community="netspout-lab",
                        pdu_type=SnmpPduType.GET_REQUEST,
                        request_id=9102,
                        varbinds=[SnmpVarBind(oid="1.3.6.1.2.1.1.5.0", asn1_type="OctetString", value="write-attempt")],
                    )
                )
            )
            idx_a0 = get_wire.find(b"\xa0")
            get_wire[idx_a0] = 0xA3
            sock.sendto(bytes(get_wire), ("127.0.0.1", port))
            resp_bytes, _ = sock.recvfrom(4096)
            resp_msg = SnmpBerDecoder.decode_message(resp_bytes)
            self.assertNotEqual(resp_msg.error_status, 0)
            sock.close()
        finally:
            agent.stop()

        self.assertGreaterEqual(agent.bad_community_requests, 1)
        self.assertGreaterEqual(agent.malformed_requests, 1)
        self.assertGreaterEqual(agent.set_requests_rejected, 1)

    def test_11_frontend_workflow_components_expose_native_snmp_controls_and_scorecard(self):
        """Section 6: Workflow UI components expose Native SNMPv2c badges, preflight, 8-stage ladder, and 7 SPL queries."""
        wf_dir = REPO_ROOT / "frontend" / "src" / "components" / "workflow"
        step_choose = (wf_dir / "StepChoose.tsx").read_text(encoding="utf-8")
        step_preview = (wf_dir / "StepPreview.tsx").read_text(encoding="utf-8")
        step_connect = (wf_dir / "StepConnect.tsx").read_text(encoding="utf-8")
        step_run = (wf_dir / "StepRun.tsx").read_text(encoding="utf-8")
        step_prove = (wf_dir / "StepProve.tsx").read_text(encoding="utf-8")

        self.assertIn("NATIVE TRANSPORT", step_choose)
        self.assertIn("MODELED DEVICE STATE", step_choose)
        self.assertIn("Native SNMPv2c E2E Specification", step_preview)
        self.assertIn("/api/native-snmp/preflight", step_connect)
        self.assertIn("MODE B / E2E: NATIVE SNMPv2c (UDP WIRE)", step_run)
        self.assertIn("8-Stage Native SNMPv2c Evidence Ladder", step_prove)
        self.assertIn("origin_evidence_stage", step_prove)
        self.assertIn("current_evidence_stage", step_prove)
        self.assertIn("7 Copyable SPL Queries", step_prove)

    def test_12_honesty_guardrails_native_transport_modeled_device_state(self):
        """Section 9: Strict honesty separation between NATIVE TRANSPORT and MODELED DEVICE STATE."""
        contract = catalog_instance.get_scenario_contract("service_provider_cisco")
        caps = contract.native_snmp_capabilities or {}
        stmt = caps.get("semantic_statement", "")
        self.assertIn("standards-compliant ASN.1 BER over UDP", stmt)
        self.assertIn("modeled by NetSpout", stmt)
        self.assertIn("no physical Cisco router is required", stmt)


if __name__ == "__main__":
    unittest.main()
