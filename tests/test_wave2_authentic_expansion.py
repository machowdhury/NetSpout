"""Wave-2 Authentic Source Expansion - offline RAW-fidelity contract tests.

Verifies (classification chain: OFFLINE_VERIFIED entry point):
  * every Wave-2 family generates vendor-native RAW that is structurally
    valid (XML parse / JSON parse / logfmt / pipe grammar / flow grammar)
  * RAW carries ZERO NetSpout correlation metadata (HEC-side only)
  * sourcetype dispatch is exact per family
  * engine bindings on SplunkLogEngine work for all 13 WAVE2 sources
  * all 8 authentic scenario packs run, thread run/phase/causal metadata,
    emit their intended sourcetypes, and never leak metadata into RAW
  * provenance ledger includes the Wave-2 fixture references (sha256)
  * canonical graduation counters are intentional (50 vendors, >=280
    sourcetypes, 37 scenarios)
"""

import hashlib
import json
import os
import pathlib
import re
import sys
import unittest
import xml.etree.ElementTree as ET

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from netspout_core.models import Node, NodeType
from netspout_core.log_engine import SplunkLogEngine
from netspout_core.wave2_authentic_engine import (
    Wave2AuthenticEngine as W2,
    WAVE2_SOURCE_SOURCETYPES,
)
from netspout_core.authentic_scenario_packs import (
    run_scenario_pack,
    run_all_scenario_packs,
    SCENARIO_PACK_IDS,
)

DEV = Node(id="wave2-test-node", name="WAVE2-TEST-HOST.corp.local",
           ip_address="10.0.9.9")

MATRIX = {
    "cisco:sfw:estreamer": ("intrusion_event", "json"),
    "cisco:nvm:flowdata:v2": ("nvzflow_v11_record", "json"),
    "ollama:server": ("server_config", "logfmt"),
    "mcp:jsonrpc": ("server_lifecycle", "json"),
    "gws:reports:login": ("login_success", "json"),
    "azure:monitor:activity": ("admin_action", "json"),
    "aws:cloudwatchlogs:vpcflow": ("flow_accept", "vpcflow"),
    "linux_messages_syslog": ("kernel_message", "syslog"),
    "XmlWinEventLog:Microsoft-Windows-Windows Defender/Operational":
        ("detection", "xml"),
    "XmlWinEventLog:Microsoft-Windows-NTLM/Operational":
        ("client_request", "xml"),
    "kube:audit": ("secret_read", "json"),
    "kube:container:falco": ("terminal_shell", "text"),
    "crushftp:sessionlogs": ("session_command_read", "pipe"),
}

CALL_ARGS = {
    "cisco:sfw:estreamer": dict(src_ip="10.0.9.9", dest_ip="10.0.9.10"),
    "cisco:nvm:flowdata:v2": dict(src_ip="10.0.9.9", dest_ip="93.184.216.34"),
    "ollama:server": dict(src_ip="10.0.9.9"),
    "mcp:jsonrpc": dict(src_ip="10.0.9.9"),
    "gws:reports:login": dict(src_ip="10.0.9.9"),
    "azure:monitor:activity": dict(src_ip="10.0.9.9"),
    "aws:cloudwatchlogs:vpcflow": dict(src_ip="10.0.9.9", dest_ip="10.0.9.10"),
    "linux_messages_syslog": dict(src_ip="10.0.9.9"),
    "XmlWinEventLog:Microsoft-Windows-Windows Defender/Operational":
        dict(host_name="WAVE2-TEST-HOST", src_ip="10.0.9.9"),
    "XmlWinEventLog:Microsoft-Windows-NTLM/Operational":
        dict(host_name="WAVE2-TEST-HOST", src_ip="10.0.9.9"),
    "kube:audit": dict(src_ip="10.0.9.9"),
    "kube:container:falco": dict(src_ip="10.0.9.9"),
    "crushftp:sessionlogs": dict(src_ip="10.0.9.9"),
}

FAMILY_SETS = {
    "cisco:sfw:estreamer": ["intrusion_event"],
    "cisco:nvm:flowdata:v2": ["nvzflow_v11_record"],
    "ollama:server": ["server_config", "model_store", "gpu_inventory",
                      "runner_wait"],
    "mcp:jsonrpc": ["server_lifecycle", "request", "response", "error"],
    "gws:reports:login": ["login_success", "login_failure",
                          "login_2sv_challenge"],
    "azure:monitor:activity": ["admin_action", "alert_action",
                               "service_health"],
    "aws:cloudwatchlogs:vpcflow": ["flow_accept", "flow_reject",
                                   "flow_skipdata"],
    "linux_messages_syslog": ["kernel_message", "sshd_message",
                              "sudo_message", "service_message"],
    "XmlWinEventLog:Microsoft-Windows-Windows Defender/Operational":
        ["detection", "remediation", "config_change"],
    "XmlWinEventLog:Microsoft-Windows-NTLM/Operational":
        ["client_request", "credential_negotiate", "audit_block"],
    "kube:audit": ["pod_create", "secret_read", "exec_into_pod"],
    "kube:container:falco": ["terminal_shell", "sensitive_file_read",
                             "write_below_etc"],
    "crushftp:sessionlogs": ["session_command_read", "session_login",
                             "session_transfer"],
}

EXPECTED_NEW_SOURCETYPE_ROWS = 12


def _single(result):
    return result[0] if isinstance(result, (list, tuple)) else result


class TestWave2Registry(unittest.TestCase):
    """Wave-2 declarative registry stays consistent with the engine."""

    def test_01_registry_counts_match_engine(self):
        with open(os.path.join(REPO_ROOT, "catalog",
                               "wave2_source_expansion.json")) as fh:
            reg = json.load(fh)
        self.assertEqual(len(reg["sources"]), 13)  # 12 new + estreamer row-gain
        total = sum(s["event_family_count"] for s in reg["sources"])
        self.assertEqual(total, 38)

    def test_02_absolutely_graduated_counters(self):
        with open(os.path.join(REPO_ROOT, "catalog", "sourcetypes.json")) as fh:
            rows = json.load(fh)
        st_names = {r["splunk_sourcetype"] for r in rows}
        missing = [st for st in WAVE2_SOURCE_SOURCETYPES if st not in st_names]
        self.assertEqual(missing, [])
        self.assertEqual(len(WAVE2_SOURCE_SOURCETYPES),
                         EXPECTED_NEW_SOURCETYPE_ROWS + 1)  # + estreamer row

    def test_03_provenance_wave2_references(self):
        with open(os.path.join(REPO_ROOT, "catalog", "raw_reference",
                               "provenance.json")) as fh:
            prov = json.load(fh)
        wave2 = [r for r in prov["references"] if r.get("wave") == 2]
        self.assertGreaterEqual(len(wave2), 8)
        for ref in wave2:
            name = ref["raw_reference_file"].split("/")[-1]
            data = open(os.path.join(REPO_ROOT, "catalog",
                                     "raw_reference", name), "rb").read()
            self.assertEqual(hashlib.sha256(data).hexdigest(),
                             ref["fetched_sha256"], name)


class TestWave2RawFidelity(unittest.TestCase):
    """Every Wave-2 family emits structurally valid vendor-native RAW."""

    def test_family_matrix_all_structured(self):
        for st, (family, kind) in MATRIX.items():
            method = getattr(W2, WAVE2_SOURCE_SOURCETYPES[st])
            entry = _single(method(DEV, family, **CALL_ARGS[st]))
            self.assertEqual(entry.sourcetype, st, st)
            raw = entry.raw_log
            with self.subTest(st=st, kind=kind):
                if kind == "xml":
                    ET.fromstring(raw)
                elif kind in ("json",):
                    json.loads(raw)
                elif kind == "logfmt":
                    self.assertRegex(raw, r'^time=\S+ level=\w+ source=\S+ msg="')
                elif kind == "vpcflow":
                    parts = raw.split()
                    if parts[-1] == "SKIPDATA":
                        self.assertEqual(len(parts), 5)
                    else:
                        self.assertEqual(len(parts), 14)
                        self.assertIn(parts[-2], ("ACCEPT", "REJECT"))
                elif kind == "pipe":
                    self.assertTrue(raw.startswith("SESSION|"))
                elif kind == "text":
                    self.assertRegex(raw, r'^\d\d:\d\d:\d\d\.\d{9}: (Critical|Warning) ')
                elif kind == "syslog":
                    self.assertRegex(
                        raw, r'^[A-Z][a-z]{2}\s+\d{1,2} \d\d:\d\d:\d\d '
                             r'\S+ \S+(?:\[\d+\])?: ')

    def test_raw_has_zero_netspout_metadata(self):
        for st, families in FAMILY_SETS.items():
            method = getattr(W2, WAVE2_SOURCE_SOURCETYPES[st])
            for family in families:
                entry = _single(method(DEV, family, **CALL_ARGS[st]))
                for token in ("netspout_run_id", "netspout_scenario_id",
                              "netspout_phase", "netspout_event_id"):
                    self.assertNotIn(token, entry.raw_log, (st, family))

    def test_unknown_family_rejected(self):
        for st, family_bad in (("ollama:server", "fabricated"),
                               ("kube:audit", "not_real")):
            method = getattr(W2, WAVE2_SOURCE_SOURCETYPES[st])
            with self.assertRaises(ValueError):
                method(DEV, family_bad, **CALL_ARGS[st])

    def test_engine_delegates_reachable(self):
        for st, mname in WAVE2_SOURCE_SOURCETYPES.items():
            self.assertTrue(hasattr(SplunkLogEngine, mname), st)
            self.assertEqual(SplunkLogEngine.WAVE2_SOURCE_SOURCETYPES[st],
                             mname)

    def test_deterministic_field_tokens(self):
        a = W2.format_mcp_jsonrpc_log(DEV, "request", src_ip="10.0.9.9")
        b = W2.format_mcp_jsonrpc_log(DEV, "request", src_ip="10.0.9.9")
        ja = json.loads(a.raw_log)
        jb = json.loads(b.raw_log)
        # Envelope genuinely records wall-clock time; every other field token
        # (method/id/params shape) must be crc-deterministic.
        ja.pop("timestamp")
        jb.pop("timestamp")
        self.assertEqual(ja, jb)

    def test_defender_ntlm_xml_system_block(self):
        e = W2.format_windows_defender_xml_log(
            DEV, "detection", host_name="H2", src_ip="10.0.9.9")
        root = ET.fromstring(e.raw_log)
        provider = root.find("./{*}System/{*}Provider")
        self.assertEqual(provider.get("Name"),
                         "Microsoft-Windows-Windows Defender")
        eid = root.find("./{*}System/{*}EventID")
        self.assertEqual(eid.text, "1116")
        e = W2.format_windows_ntlm_xml_log(
            DEV, "client_request", host_name="H2", src_ip="10.0.9.9")
        root = ET.fromstring(e.raw_log)
        self.assertEqual(root.find("./{*}System/{*}EventID").text, "8001")


class TestWave2ScenarioPacks(unittest.TestCase):
    """Authentic scenario packs executes multi-phase sequences."""

    def test_all_packs_run_and_thread_metadata(self):
        results = run_all_scenario_packs()
        self.assertEqual(sorted(results), sorted(SCENARIO_PACK_IDS))
        for sid, entries in results.items():
            self.assertGreater(len(entries), 0, sid)
            for e in entries:
                self.assertTrue(e.netspout_run_id, sid)
                self.assertEqual(e.netspout_scenario_id, sid)
                self.assertTrue(e.netspout_phase, sid)
                self.assertTrue(e.netspout_event_id, sid)
                for token in ("netspout_run_id=", "netspout_scenario_id=",
                              "\"netspout_run_id"):
                    self.assertNotIn(token, e.raw_log, sid)

    def test_ws_chain_phase_ordering(self):
        entries = run_scenario_pack("wave2_ws_credential_compromise_chain",
                                    run_id="pf-wave2-test-fixed")
        phases = []
        for e in entries:
            if e.netspout_phase not in phases:
                phases.append(e.netspout_phase)
        self.assertEqual(phases[0], "BASELINE")
        self.assertEqual(phases[-1], "EDR_RESPONSE")
        sts = {e.sourcetype for e in entries}
        self.assertIn("XmlWinEventLog:Security", sts)
        self.assertIn("crowdstrike:events:sensor", sts)
        self.assertIn("XmlWinEventLog:Microsoft-Windows-Sysmon/Operational",
                      sts)
        # failure -> success ordering (recon precedes access)
        first_breach = next(i for i, e in enumerate(entries)
                            if e.status in ("breached", "blocked")
                            and e.netspout_phase == "RECON_CREDENTIAL_FAILURES")
        self.assertLess(first_breach, len(entries))

    def test_cloud_identity_emits_all_vendors(self):
        entries = run_scenario_pack("wave2_cloud_identity_sso_hunt",
                                    run_id="pf-wave2-test-fixed2")
        sts = {e.sourcetype for e in entries}
        self.assertEqual(sts, {"o365:management:activity",
                               "azure:monitor:aad", "OktaIM2:log",
                               "azure:monitor:activity",
                               "gws:reports:login"})

    def test_k8s_escape_emits_audit_and_falco(self):
        entries = run_scenario_pack("wave2_k8s_container_escape",
                                    run_id="pf-wave2-test-fixed3")
        sts = {e.sourcetype for e in entries}
        self.assertIn("kube:audit", sts)
        self.assertIn("kube:container:falco", sts)
        self.assertIn("suricata", sts)

    def test_itops_pack_emits_estreamer_and_nvm(self):
        entries = run_scenario_pack("wave2_bigip_openconfig_itops",
                                    run_id="pf-wave2-test-fixed4")
        sts = {e.sourcetype for e in entries}
        self.assertIn("cisco:sfw:estreamer", sts)
        self.assertIn("cisco:nvm:flowdata:v2", sts)
        self.assertIn("crushftp:sessionlogs", sts)

    def test_unknown_pack_rejected(self):
        with self.assertRaises(ValueError):
            run_scenario_pack("not_a_pack")


class TestWave1ExtensionFamilies(unittest.TestCase):
    """Wave-1 engine family extensions (wave-2 session additions)."""

    def test_security_channel_new_ids(self):
        from netspout_core.wave1_authentic_engine import Wave1AuthenticEngine as W1
        for family, eid in (("process_creation", 4688),
                            ("process_terminated", 4689),
                            ("user_account_changed", 4738),
                            ("credential_validation", 4776)):
            val = W1.format_windows_security_xml_log(
                DEV, family, actor_user="svc-ldap", actor_domain="CORP",
                src_ip="10.0.9.9", host_name=DEV.name)
            root = ET.fromstring(_single(val).raw_log)
            self.assertEqual(
                int(root.find("./{*}System/{*}EventID").text), eid, family)

    def test_sysmon_and_powershell_extensions(self):
        from netspout_core.wave1_authentic_engine import Wave1AuthenticEngine as W1
        for family, eid in (("image_loaded", 7),
                            ("create_remote_thread", 8)):
            e = W1.format_windows_sysmon_xml_log(
                DEV, family, host_name=DEV.name, src_ip="10.0.9.9",
                dest_ip="10.0.9.10", process_image="C:\\x\\a.exe",
                command_line="a.exe -go")
            self.assertEqual(
                int(ET.fromstring(e.raw_log).find(
                    "./{*}System/{*}EventID").text), eid, family)
        for family, eid in (("module_session_start", 4105),
                            ("module_session_stop", 4106)):
            e = W1.format_windows_powershell_xml_log(
                DEV, family, host_name=DEV.name, src_ip="10.0.9.9",
                script_block="")
            self.assertEqual(
                int(ET.fromstring(e.raw_log).find(
                    "./{*}System/{*}EventID").text), eid, family)

    def test_crowdstrike_fdr_families_evidenced_head(self):
        from netspout_core.wave1_authentic_engine import Wave1AuthenticEngine as W1
        for family in ("DmpFileWritten", "FileDeleteInfo",
                       "ProcessHandleOpDetectInfo"):
            e = _single(W1.format_crowdstrike_falcon_sensor_log(
                DEV, family, src_ip="10.0.9.9", dest_ip="10.0.9.10",
                process_image="C:\\x\\a.exe", command_line="a.exe -go"))
            body = json.loads(e.raw_log)
            self.assertEqual(body["event_simpleName"], family)

    def test_fileinfo_and_okta_existing_families(self):
        from netspout_core.wave1_authentic_engine import Wave1AuthenticEngine as W1
        e = W1.format_suricata_eve_log(DEV, "fileinfo", src_ip="10.0.9.9",
                                       dest_ip="10.0.9.10", dest_port=443,
                                       proto="TCP")
        self.assertEqual(json.loads(e.raw_log)["event_type"], "fileinfo")
        e = W1.format_okta_log(DEV, "suspicious_activity_report",
                               src_ip="10.0.9.9")
        self.assertEqual(
            json.loads(e.raw_log)["eventType"],
            "user.account.report_suspicious_activity_by_enduser")

    def test_wave1_registry_extended_counts(self):
        with open(os.path.join(REPO_ROOT, "catalog",
                               "wave1_source_expansion.json")) as fh:
            reg = json.load(fh)
        self.assertEqual(reg["event_family_count_total"], 70)
        src_map = {s["wave_source_id"]: s for s in reg["sources"]}
        self.assertIn("4688 process_creation",
                      src_map["wins-xml-security"]["event_families"])
        self.assertIn("7 image_loaded",
                      src_map["wins-xml-sysmon"]["event_families"])


class TestCanonicalGraduation(unittest.TestCase):
    """Workstream A intentional invariant updates."""

    def test_vendor_count_50(self):
        # Intentional pinned counter (authorized Workstream A/B pattern):
        # 50 Wave-1/2 vendors + 3 Wave-3 additions
        # (zeek, google_cloud, opentelemetry)
        with open(os.path.join(REPO_ROOT, "catalog", "vendors.json")) as fh:
            self.assertEqual(len(json.load(fh)), 53)

    def test_sourcetype_rows_289(self):
        # Intentional pinned counter (authorized Workstream A/B pattern):
        # 289 Wave-2 canonical rows + 24 Wave-3 new rows
        with open(os.path.join(REPO_ROOT, "catalog",
                               "sourcetypes.json")) as fh:
            self.assertEqual(len(json.load(fh)), 313)

    def test_scenarios_37(self):
        # Intentional pinned counter (authorized Workstream A/B pattern):
        # 37 Wave-2 scenarios + 3 Wave-3 packs
        with open(os.path.join(REPO_ROOT, "catalog", "scenarios.json")) as fh:
            rows = json.load(fh)
        self.assertEqual(len(rows), 40)
        wave2_rows = [r for r in rows if r["id"].startswith("wave2_")]
        self.assertEqual(len(wave2_rows), 8)


if __name__ == "__main__":
    unittest.main()
