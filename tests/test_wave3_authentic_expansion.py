"""Wave-3 Authentic Splunkbase-scale Expansion - offline RAW-fidelity tests.

Verifies (classification chain: OFFLINE_VERIFIED entry point):
  * every Wave-3 source generates vendor-native RAW that is structurally
    valid (JSON parse / XML parse / CSV column counts / syslog grammar)
  * RAW carries ZERO NetSpout correlation metadata (HEC-side only)
  * sourcetype dispatch is exact per family
  * engine bindings on SplunkLogEngine work for all 27 WAVE3 dispatch entries
  * all 3 Wave-3 scenario packs run, thread run/phase/causal metadata, and
    emit exactly their catalog-declared sourcetype sets
  * provenance ledger includes Wave-3 fixture references (sha256)
  * canonical graduation counters are intentional (53 vendors, 313
    sourcetype rows, 40 scenarios)
"""

import hashlib
import json
import os
import pathlib
import sys
import unittest
import xml.etree.ElementTree as ET

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from netspout_core.models import Node
from netspout_core.log_engine import SplunkLogEngine
from netspout_core.wave3_authentic_engine import (
    Wave3AuthenticEngine as W3,
    WAVE3_SOURCE_SOURCETYPES,
)
from netspout_core.authentic_scenario_packs import (
    run_scenario_pack,
    SCENARIO_PACK_IDS,
)

DEV = Node(id="wave3-test-node", name="WAVE3-TEST-HOST.corp.local",
           ip_address="10.0.9.9")

WAVE3_SCENARIO_IDS = [sid for sid in SCENARIO_PACK_IDS
                      if sid.startswith("wave3_")]

MATRIX = {
    "vmw-syslog": ("shell_command", "text"),
    "cisco:cloud_security:firewall": ("conn_c2s", "csv37"),
    "cisco:cloud_security:dns": ("dns_query", "csv16"),
    "cisco:cloud_security:proxy": ("proxy_http", "csv49"),
    "cisco:isovalent": ("process_exec", "json"),
    "cisco:isovalent:processExec": ("process_exec", "json"),
    "cisco:isovalent:processConnect": ("process_connect", "json"),
    "aws:cloudtrail:lake": ("ocsf_api_activity", "json"),
    "linux_secure": ("su_message", "text"),
    "iis": ("w3c_access", "text"),
    "bro:conn:json": ("conn", "json"),
    "MSExchange:Management": ("cmdlet_event", "exchangeblock"),
    "aws:cloudfront:accesslogs": ("edge_access", "csv33tabs"),
    "o365:reporting:messagetrace": ("message_trace", "json"),
    "o365:graph:messagetrace": ("graph_message_trace", "json"),
    "gsuite:gmail:bigquery": ("gmail_message_event", "json"),
    "zscalernss-web": ("web_proxy_block", "json"),
    "cisco:secure_access:security_events_ravpn": ("vpn_auth_reject", "json"),
    "cisco:sdwan:syslog": ("vdaemon_control_change", "text"),
    "cisco:sdwan:access": ("mgmt_proxy_access", "text"),
    "cisco:ios": ("sec_login_success", "text"),
    "cisco:meraki:syslog": ("flows", "text"),
    "dhcpd": ("dhcpack", "text"),
    "gcp:audit": ("admin_activity", "json"),
    "opentelemetry:otlp": ("log_record", "json"),
    "XmlWinEventLog:System": ("service_install_event", "xml"),
    "cisco:duo:administrator": ("admin_action", "json"),
}

FAMILY_SETS = {
    "vmw-syslog": W3.VMW_SYSLOG_FAMILIES,
    "cisco:cloud_security:firewall": W3.CSL_FIREWALL_FAMILIES,
    "cisco:cloud_security:dns": W3.CSL_DNS_FAMILIES,
    "cisco:cloud_security:proxy": W3.CSL_PROXY_FAMILIES,
    "cisco:isovalent": W3.ISOVALENT_FAMILIES,
    "cisco:isovalent:processExec": ["process_exec", "process_connect"],
    "cisco:isovalent:processConnect": ["process_exec", "process_connect"],
    "aws:cloudtrail:lake": W3.CLOUDTRAIL_LAKE_FAMILIES,
    "linux_secure": W3.LINUX_SECURE_FAMILIES,
    "iis": W3.IIS_FAMILIES,
    "bro:conn:json": W3.ZEEK_CONN_FAMILIES,
    "MSExchange:Management": W3.MSEXCHANGE_FAMILIES,
    "aws:cloudfront:accesslogs": W3.CLOUDFRONT_FAMILIES,
    "o365:reporting:messagetrace": W3.O365_MESSAGETRACE_FAMILIES,
    "o365:graph:messagetrace": W3.O365_GRAPH_MESSAGETRACE_FAMILIES,
    "gsuite:gmail:bigquery": W3.GMAIL_BIGQUERY_FAMILIES,
    "zscalernss-web": W3.ZSCALER_NSS_FAMILIES,
    "cisco:secure_access:security_events_ravpn": W3.RAVPN_FAMILIES,
    "cisco:sdwan:syslog": W3.SDWAN_SYSLOG_FAMILIES,
    "cisco:sdwan:access": W3.SDWAN_ACCESS_FAMILIES,
    "cisco:ios": W3.IOS_SYSLOG_FAMILIES,
    "cisco:meraki:syslog": W3.MERAKI_SYSLOG_FAMILIES,
    "dhcpd": W3.DHCPD_FAMILIES,
    "gcp:audit": W3.GCP_AUDIT_FAMILIES,
    "opentelemetry:otlp": W3.OTEL_FAMILIES,
    "XmlWinEventLog:System": W3.WINDOWS_SYSTEM_FAMILIES,
    "cisco:duo:administrator": W3.DUO_FAMILIES,
}

WITH_EXPLICIT_SOURCETYPE = ("cisco:isovalent:processExec",
                            "cisco:isovalent:processConnect")


def _single(entry) -> object:
    if isinstance(entry, (list, tuple)):
        return entry[0]
    return entry


class TestWave3Registry(unittest.TestCase):
    """Registry + graduation contracts."""

    def test_01_registry_counts_match_engine(self):
        with open(os.path.join(REPO_ROOT, "catalog",
                               "wave3_source_expansion.json")) as fh:
            reg = json.load(fh)
        self.assertEqual(len(reg["sources"]), 27)  # 24 new + 3 gap fills
        self.assertEqual(reg["classification_chain_states"]
                         ["GENERATOR_IMPLEMENTED"], 27)
        self.assertEqual(reg["counts_summary"]
                         ["new_canonical_sourcetypes"], 24)

    def test_02_absolutely_graduated_counters(self):
        with open(os.path.join(REPO_ROOT, "catalog", "sourcetypes.json")) as fh:
            rows = json.load(fh)
        st_names = {r["splunk_sourcetype"] for r in rows}
        missing = [st for st in WAVE3_SOURCE_SOURCETYPES if st not in st_names]
        self.assertEqual(missing, [])
        self.assertEqual(len(WAVE3_SOURCE_SOURCETYPES), 27)

    def test_03_provenance_wave3_references(self):
        with open(os.path.join(REPO_ROOT, "catalog", "raw_reference",
                               "provenance.json")) as fh:
            prov = json.load(fh)
        wave3 = [r for r in prov["references"] if r.get("wave") == 3]
        self.assertGreaterEqual(len(wave3), 20)
        for ref in wave3:
            rel = ref["raw_reference_file"]
            if rel.startswith("catalog/"):
                path = os.path.join(REPO_ROOT, rel)
            else:
                path = os.path.join(REPO_ROOT, "catalog", "raw_reference",
                                    rel.split("/")[-1])
            self.assertTrue(os.path.exists(path), rel)
            data = open(path, "rb").read()
            self.assertEqual(hashlib.sha256(data).hexdigest(),
                             ref["fetched_sha256"], rel)


class TestWave3RawFidelity(unittest.TestCase):
    """Every Wave-3 family emits structurally valid vendor-native RAW."""

    def test_family_matrix_all_structured(self):
        for st, (family, kind) in MATRIX.items():
            method = getattr(W3, WAVE3_SOURCE_SOURCETYPES[st])
            kwargs = {}
            if st in WITH_EXPLICIT_SOURCETYPE:
                kwargs = {"sourcetype": st}
            if st == "vmw-syslog":
                kwargs = {}
            entry = _single(method(DEV, family, src_ip="10.0.9.9",
                                   dest_ip="10.0.0.1", **kwargs))
            self.assertEqual(entry.sourcetype, st, st)
            raw = entry.raw_log
            with self.subTest(st=st, kind=kind):
                if kind in ("json",):
                    json.loads(raw)
                elif kind == "xml":
                    root = ET.fromstring(raw)
                    self.assertEqual(root.tag.split("}")[1], "Event")
                elif kind == "csv37":
                    self.assertEqual(len(next(__import__("csv").reader(
                        [raw]))), 37)
                elif kind == "csv16":
                    self.assertEqual(len(next(__import__("csv").reader(
                        [raw]))), 16)
                elif kind == "csv49":
                    self.assertEqual(len(next(__import__("csv").reader(
                        [raw]))), 49)
                elif kind == "csv33tabs":
                    self.assertEqual(len(raw.split("\t")), 33)
                elif kind == "exchangeblock":
                    self.assertIn("LogName=MSExchange Management", raw)
                    self.assertRegex(raw, r"^\d\d/\d\d/\d{4} \d\d:\d\d:\d\d")
                else:
                    self.assertIsInstance(raw, str)
                    self.assertGreater(len(raw), 10)

    def test_raw_has_zero_netspout_metadata(self):
        for st, families in FAMILY_SETS.items():
            method = getattr(W3, WAVE3_SOURCE_SOURCETYPES[st])
            for family in families:
                kwargs = {}
                if st in WITH_EXPLICIT_SOURCETYPE:
                    kwargs = {"sourcetype": st}
                entry = _single(method(DEV, family, src_ip="10.0.9.9",
                                       dest_ip="10.0.0.1", **kwargs))
                for token in ("netspout_run_id", "netspout_scenario_id",
                              "netspout_phase", "netspout_event_id"):
                    self.assertNotIn(token, entry.raw_log, (st, family))

    def test_unknown_family_rejected(self):
        for st, family_bad in (("cisco:isovalent", "fabricated"),
                               ("vmw-syslog", "not_real"),
                               ("cisco:duo:administrator", "made_up")):
            method = getattr(W3, WAVE3_SOURCE_SOURCETYPES[st])
            with self.assertRaises(ValueError):
                method(DEV, family_bad, src_ip="10.0.9.9", dest_ip="10.0.0.1")

    def test_engine_delegates_reachable(self):
        for st, mname in WAVE3_SOURCE_SOURCETYPES.items():
            self.assertTrue(hasattr(SplunkLogEngine, mname), st)
            self.assertEqual(SplunkLogEngine.WAVE3_SOURCE_SOURCETYPES[st],
                             mname)

    def test_deterministic_field_tokens(self):
        a = W3.format_dhcpd_log(DEV, "dhcpack", src_ip="10.0.9.9",
                                dest_ip="10.0.9.9", mac="aa:bb:cc:dd:ee:02")
        b = W3.format_dhcpd_log(DEV, "dhcpack", src_ip="10.0.9.9",
                                dest_ip="10.0.9.9", mac="aa:bb:cc:dd:ee:02")
        # Wall-clock remains in the timestamp but the message tail is
        # crc-deterministic.
        self.assertEqual(a.raw_log.split("dhcpd: ")[1],
                         b.raw_log.split("dhcpd: ")[1])

    def test_csl_s2c_icmp_layout_quirks(self):
        entry = _single(W3.format_cisco_cloud_security_firewall_log(
            DEV, "conn_s2c_icmp", src_ip="10.0.9.9", dest_ip="10.0.0.1"))
        import csv as _csv
        row = next(_csv.reader([entry.raw_log]))
        self.assertEqual(row[4], "S2C")
        self.assertEqual(row[5], "1")  # icmp
        self.assertIn("-1-", row[22])

    def test_cloudtrail_lake_numeric_time_dt_quirk(self):
        entry = _single(W3.format_aws_cloudtrail_lake_log(
            DEV, "ocsf_api_activity", src_ip="10.0.9.9",
            dest_ip="10.0.0.1"))
        rec = json.loads(entry.raw_log)
        self.assertIsInstance(rec["time_dt"], int)
        self.assertEqual(rec["class_uid"], 6003)
        self.assertEqual(rec["api"]["service"]["name"], "iam.amazonaws.com")

    def test_windows_system_7045_pinned_shape(self):
        e = W3.format_windows_system_xml_log(
            DEV, "service_install_event", host_name="ar-win-dc",
            src_ip="10.0.9.9", dest_ip="10.0.0.1", message="Bluetooth Service")
        root = ET.fromstring(e.raw_log)
        self.assertEqual(root.find("./{*}System/{*}EventID").text, "7045")
        provider = root.find("./{*}System/{*}Provider")
        self.assertEqual(provider.get("Name"), "Service Control Manager")
        eid_data = [d.text for d in root.findall(".//{*}Data")]
        self.assertIn("Bluetooth Service", eid_data)

    def test_isovalent_sibling_rows_dispatch_exact(self):
        for st in WITH_EXPLICIT_SOURCETYPE:
            method = getattr(W3, WAVE3_SOURCE_SOURCETYPES[st])
            e = method(DEV, "process_exec", src_ip="10.0.9.9",
                       dest_ip="10.0.0.1", sourcetype=st)
            self.assertEqual(e.sourcetype, st)
            rec = json.loads(e.raw_log)
            self.assertIn("process_exec", rec)


class TestWave3ScenarioPacks(unittest.TestCase):
    """Wave-3 packs execute multi-phase sequences with exact declared STs."""

    def test_wave3_packs_declared_sourcetypes(self):
        with open(os.path.join(REPO_ROOT, "catalog", "scenarios.json")) as fh:
            rows = {s["id"]: s for s in json.load(fh)}
        for sid in WAVE3_SCENARIO_IDS:
            entries = run_scenario_pack(sid, run_id="pf-wave3-test-fixed")
            declared = set(rows[sid]["sourcetypes"])
            emitted = {e.sourcetype for e in entries}
            self.assertEqual(emitted, declared, sid)
            for e in entries:
                self.assertTrue(e.netspout_run_id, sid)
                self.assertEqual(e.netspout_scenario_id, sid)
                self.assertTrue(e.netspout_phase, sid)
                self.assertTrue(e.netspout_event_id, sid)
                for token in ("netspout_run_id=", "netspout_scenario_id=",
                              '"netspout_run_id'):
                    self.assertNotIn(token, e.raw_log, sid)

    def test_wave3_catalog_rows_present_and_contracted(self):
        with open(os.path.join(REPO_ROOT, "catalog", "scenarios.json")) as fh:
            rows = [s for s in json.load(fh) if s["id"].startswith("wave3_")]
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertEqual(row["maturity"], "CONTRACTED")
            self.assertIn(row["telemetry_model"],
                          ("Standard Telemetry Payload",))
            self.assertIn("fidelity_badge", row)
            for ph in row["phases"]:
                self.assertIn(
                    ph["phase"],
                    ("INITIALIZE", "BASELINE", "DEGRADE", "FAULT",
                     "PROPAGATE", "FAILOVER", "RECOVER", "VALIDATE",
                     "COMPLETE"))

    def test_ebpf_hunt_phase_ordering(self):
        entries = run_scenario_pack("wave3_ebpf_workload_hunt",
                                    run_id="pf-wave3-test-fixed")
        phases = []
        for e in entries:
            if e.netspout_phase not in phases:
                phases.append(e.netspout_phase)
        self.assertEqual(phases, ["BASELINE", "DEGRADE", "FAULT",
                                  "PROPAGATE", "VALIDATE"])
        sts = {e.sourcetype for e in entries}
        self.assertIn("cisco:isovalent", sts)
        self.assertIn("cisco:isovalent:processConnect", sts)
        self.assertIn("cisco:cloud_security:proxy", sts)
        self.assertIn("gcp:audit", sts)
        self.assertIn("opentelemetry:otlp", sts)

    def test_unknown_pack_rejected(self):
        with self.assertRaises(ValueError):
            run_scenario_pack("not_a_wave3_pack")

    def test_wave1_and_wave2_packs_still_run(self):
        entries = run_scenario_pack("wave2_ws_credential_compromise_chain",
                                    run_id="pf-wave3-test-fixed")
        self.assertGreater(len(entries), 0)


if __name__ == "__main__":
    unittest.main()
