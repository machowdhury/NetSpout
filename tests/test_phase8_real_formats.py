"""Phase 8: generator corrections checked against independent evidence (tests/fixtures/phase7_real_samples, docs/contracts/phase7/phase8_metric_evidence.json).
Every test compares generated output with the real-data fixtures or with documented observations, not with itself."""
import json
import os
import random
import re
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "backend")]
os.environ.setdefault("NETSPOUT_HEC_TOKEN", "test-token")

from netspout_core import ingestion_profiles as ip  # noqa: E402
from netspout_core import real_format_generators as rfg  # noqa: E402
from netspout_core.models import TelemetryTransportConfig  # noqa: E402
from netspout_core.telemetry_dispatcher import dispatcher, is_metric_sourcetype  # noqa: E402
from netspout_core.yaml_sample_replay import load_sample_set  # noqa: E402

FIX = {s["real_sourcetype"]: s for s in reversed(json.loads((ROOT / "tests/fixtures/phase7_real_samples/sanitized_real_samples.json").read_text())["samples"])}
EVID = json.loads((ROOT / "docs/contracts/phase7/phase8_metric_evidence.json").read_text())
CFG = TelemetryTransportConfig(hec_enabled=True, hec_url="https://preview.invalid/services/collector", hec_token="t", hec_index="idx_event", hec_metric_index="cisco_metrics")
_SVC = None


def svc():
    global _SVC
    if _SVC is None:
        from app.generator_modes import TelemetryGeneratorService
        _SVC = TelemetryGeneratorService()
    return _SVC


def capture(entry):
    cap = []
    dispatcher._dispatch_log(entry, CFG, capture=cap)
    return cap[0]


# ------------------------------------------------------------------------------------------------------------------------------- Duo
class TestDuoCtime(unittest.TestCase):
    INSTANTS = [
        datetime(2026, 11, 3, 10, 33, 44, tzinfo=timezone.utc),            # the real fixture instant: a Tuesday
        datetime(2028, 2, 29, 23, 59, 59, tzinfo=timezone.utc),            # leap day (Tuesday)
        datetime(2100, 2, 28, 12, 0, 0, tzinfo=timezone.utc),              # 2100 is not a leap year
        datetime(2026, 3, 8, 6, 59, 59, tzinfo=timezone.utc),              # one second before the New York spring-forward
        datetime(2026, 3, 8, 7, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 11, 1, 5, 59, 59, tzinfo=timezone.utc),             # one second before the New York fall-back
        datetime(2026, 11, 1, 6, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc),           # year boundary
        datetime(2027, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    ]
    FILES = ("cisco-duo-account", "cisco-duo-activity", "cisco-duo-administrator", "cisco-duo-authentication-v2", "cisco-duo-user")

    def test_real_fixture_format(self):
        self.assertEqual(rfg.asctime_utc(self.INSTANTS[0]), "Tue Nov  3 10:33:44 2026")
        fx = json.loads(FIX["cisco:duo:authentication_v2"]["raw"].split(', "access_device"')[0] + "}")["ctime"]
        self.assertEqual(rfg.asctime_utc(self.INSTANTS[0]), fx)

    def test_weekday_always_matches_the_date(self):
        for now in self.INSTANTS:
            s = rfg.asctime_utc(now)
            parsed = datetime.strptime(s, "%a %b %d %H:%M:%S %Y")               # strptime verifies nothing about weekday; compare explicitly
            self.assertEqual((parsed.year, parsed.month, parsed.day, parsed.hour, parsed.minute, parsed.second), (now.year, now.month, now.day, now.hour, now.minute, now.second), s)
            self.assertEqual(s[:3], now.strftime("%a"), s)
            self.assertRegex(s, r"^[A-Z][a-z]{2} [A-Z][a-z]{2} [ 1-3]\d \d\d:\d\d:\d\d \d{4}$")
            self.assertEqual(len(s), 24)

    def test_timezone_aware_input_is_converted_to_utc(self):
        ny = ZoneInfo("America/New_York")
        for local in (datetime(2026, 3, 8, 1, 59, 59, tzinfo=ny), datetime(2026, 3, 8, 3, 0, 0, tzinfo=ny), datetime(2026, 12, 31, 23, 30, 0, tzinfo=ny), datetime(2026, 11, 1, 1, 30, 0, tzinfo=ny, fold=1)):
            utc = local.astimezone(timezone.utc)
            self.assertEqual(rfg.asctime_utc(local), rfg.asctime_utc(utc))
        # 23:30 on New Year's Eve in New York is already the next UTC day: the weekday must follow UTC, not the wall clock
        self.assertEqual(rfg.asctime_utc(datetime(2026, 12, 31, 23, 30, 0, tzinfo=ny))[:3], "Fri")

    def test_every_duo_sample_renders_consistent_date_fields(self):
        for f in self.FILES:
            ss = load_sample_set(str(ROOT / ("netspout/appserver/static/samples/%s/%s.yml" % (f, f))))
            for now in self.INSTANTS:
                for raw in ss.render_all(random.Random(1), now):
                    o = json.loads(raw)
                    self.assertEqual(o["ctime"], rfg.asctime_utc(now), f)
                    self.assertEqual(o["timestamp"], int(now.timestamp()), "%s: epoch must be the same instant as ctime" % f)
                    if "isotimestamp" in o:
                        self.assertTrue(o["isotimestamp"].startswith(now.strftime("%Y-%m-%dT%H:%M:%S")), f)

    def test_stale_sample_text_is_gone(self):
        for f in self.FILES:
            text = (ROOT / ("netspout/appserver/static/samples/%s/%s.yml" % (f, f))).read_text()
            self.assertNotIn('"ctime": "Fri', text, f)
            self.assertNotRegex(text, r'"timestamp": \d{9,}', f)

    def test_native_admin_log_uses_the_helper(self):
        from netspout_core.log_engine import SplunkLogEngine
        from netspout_core.models import Node, NodeType
        node = Node(id="duo", name="duo", type=NodeType.ROUTER, x=0, y=0, ip_address="192.0.2.1", vendor="cisco_duo", sourcetype="cisco:duo:administrator")
        for family in ("admin_action", "activity_event"):
            e = SplunkLogEngine.format_cisco_duo_admin_log(node, family, "192.0.2.1")
            c = json.loads(e.raw_log)["ctime"]
            self.assertRegex(c, r"^[A-Z][a-z]{2} [A-Z][a-z]{2} [ 1-3]\d \d\d:\d\d:\d\d \d{4}$")
            self.assertEqual(datetime.strptime(c, "%a %b %d %H:%M:%S %Y").strftime("%a"), c[:3])


# ----------------------------------------------------------------------------------------------------------------------------- Meraki
class TestMerakiFamily(unittest.TestCase):
    ST = "meraki:securityappliances"

    def real_keys(self):
        return set(json.loads(FIX[self.ST]["raw"]))

    def test_shipped_sample_is_only_the_real_event_family(self):
        samples, prov, _ = svc().get_grounded_samples(self.ST, vendor_id="cisco_meraki")
        self.assertEqual(prov, "VERIFIED_PUBLIC_SAMPLE")
        self.assertGreater(len(samples), 50)
        keys = self.real_keys() - {"clientId"}
        for raw in samples:
            o = json.loads(raw)
            self.assertTrue(keys <= set(o), sorted(keys - set(o)))
            self.assertFalse(set(o) & {"eventType", "ts", "ssid", "bssids", "fileHash", "disposition"})
        self.assertEqual(rfg.family_violations(self.ST, samples), [])

    def test_real_fixture_conforms_to_the_contract(self):
        self.assertEqual(rfg.family_violations(self.ST, [FIX[self.ST]["raw"]]), [])

    def test_amp_style_event_is_rejected(self):
        amp = json.dumps({"ts": "2026-03-11T22:43:18Z", "eventType": "File Scanned", "clientIp": "192.0.2.5", "disposition": "Malicious", "organizationId": "1"})
        v = rfg.family_violations(self.ST, [FIX[self.ST]["raw"], amp])
        self.assertEqual(len(v), 1)
        self.assertIn("event 1", v[0])

    def test_air_marshal_event_is_rejected(self):
        am = json.dumps({"ssid": "x", "bssids": [], "channels": [1], "firstSeen": 1, "lastSeen": 2, "organizationId": "1"})
        self.assertTrue(rfg.family_violations(self.ST, [am]))

    def test_non_json_is_rejected(self):
        self.assertTrue(rfg.family_violations(self.ST, ["not json"]))

    def test_mixed_sample_file_makes_the_sourcetype_unsupported(self):
        from app.generator_modes import TelemetryGeneratorService
        mixed = [FIX[self.ST]["raw"], json.dumps({"ts": "x", "eventType": "IDS Alert", "organizationId": "1"})]
        s = TelemetryGeneratorService()
        s._load_sample_events = lambda path, st: list(mixed)
        events, prov, ref = s._resolve_samples(self.ST, "cisco_meraki")
        self.assertEqual((events, prov), ([], "SAMPLE_INVALID"))
        self.assertIn("event-family contract", ref)

    def test_other_sourcetypes_have_no_contract_and_are_untouched(self):
        self.assertEqual(rfg.family_violations("meraki:organizationsecurity", ['{"eventType": "File Scanned"}']), [])

    def test_prepare_never_emits_a_foreign_family(self):
        entries, _ = svc().prepare_sourcetype_entries("cisco_meraki", self.ST, 200)
        self.assertEqual(rfg.family_violations(self.ST, [e.raw_log for e in entries]), [])


# ----------------------------------------------------------------------------------------------------------------------------- VMware
class TestVmwarePerfCpu(unittest.TestCase):
    ST = "vmware:perf:cpu"

    @staticmethod
    def kinds(cols):
        return ["F" if "." in c else "I" for c in cols]

    def test_row_layout_matches_the_real_fixture(self):
        real = FIX[self.ST]["raw"].split("\t")
        for e in svc().prepare_sourcetype_entries("vmware_nsx", self.ST, 8)[0]:
            cols = e.raw_log.split("\t")
            self.assertEqual((len(cols), len(real)), (19, 19))
            self.assertEqual(self.kinds(cols[4:]), self.kinds(real[4:]), "numeric type of every counter column must match the observed row")
            self.assertEqual(cols[2], real[2])                                   # instance
            self.assertEqual(cols[3], real[3])                                   # sampling interval
            self.assertRegex(cols[0], r"^host-\d+$")
            self.assertRegex(cols[1], r"^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
            for c, r in zip(cols[4:], real[4:]):
                float(c)
                if float(r) == 0:
                    self.assertEqual(float(c), 0)                                # zero columns stay zero
            self.assertNotIn("\n", e.raw_log)
            self.assertFalse(e.raw_log.lstrip().startswith(("{", "moid")), "no JSON and no header row")

    def test_routed_as_an_event_with_the_collector_metadata(self):
        self.assertFalse(is_metric_sourcetype(self.ST))
        e = svc().prepare_sourcetype_entries("vmware_nsx", self.ST, 1)[0][0]
        pl = capture(e)
        self.assertNotEqual(pl.get("event"), "metric")
        self.assertEqual((pl["index"], pl["sourcetype"], pl["source"]), ("idx_event", self.ST, "VMPerf:HostSystem"))
        self.assertEqual(pl["event"], e.raw_log)
        self.assertEqual(pl["source"], FIX[self.ST]["source"])

    def test_not_blocked_by_capability_routing(self):
        from netspout_core import capability
        self.assertIsNone(capability.routing_block(self.ST))
        self.assertIsNone(capability.block(self.ST))

    def test_unrelated_vmware_generators_stay_as_they_were(self):
        for st in ("vmware:perf:net",):
            try:
                es, _ = svc().prepare_sourcetype_entries("vmware_nsx", st, 1)
            except ValueError:
                continue                                                          # unsupported before and after
            self.assertTrue(es[0].raw_log.lstrip().startswith("{"), "%s must not have been converted to TSV" % st)


# ------------------------------------------------------------------------------------------------------------------------ IOS XR metrics
class TestIosXrMetrics(unittest.TestCase):
    ST = "cisco:ios:mdt:metric"

    def entries(self, n=60):
        return svc().prepare_sourcetype_entries("cisco_ios", self.ST, n)[0]

    def test_names_dimensions_and_ranges_match_the_observations(self):
        metrics = EVID["metrics"]
        seen = set()
        for e in self.entries():
            pl = capture(e)
            self.assertEqual(pl["event"], "metric")
            self.assertEqual(pl["index"], "cisco_metrics")
            f = pl["fields"]
            names = {k[len("metric_name:"):]: v for k, v in f.items() if k.startswith("metric_name:")}
            self.assertTrue(names)
            dims = {k for k in f if not k.startswith("metric_name:") and not k.startswith("netspout_") and k != "_value"}
            for n, v in names.items():
                self.assertIn(n, metrics, "metric name not observed on the reference instance")
                self.assertEqual(dims, set(metrics[n]["dims"]), n)
                self.assertEqual(f["path"], metrics[n]["path"], n)
                self.assertGreaterEqual(v, metrics[n]["observed_min"], n)
                self.assertLessEqual(v, metrics[n]["observed_max"], n)
                self.assertIsInstance(v, float)
                seen.add(n)
        self.assertEqual(seen, set(metrics), "every documented series is produced")

    def test_no_netspout_metadata_masquerades_as_a_dimension(self):
        for e in self.entries(14):
            f = capture(e)["fields"]
            for bare in ("device", "host", "vendor", "status", "action", "node_id_str", "sensor_path"):
                self.assertNotIn(bare, f)

    def test_observed_dimension_values_only(self):
        for e in self.entries(40):
            f = capture(e)["fields"]
            if "subscription" in f:
                self.assertEqual(f["subscription"], EVID["observed_dimension_values"]["subscription"][0])
                self.assertIn(f["node_name"], EVID["observed_dimension_values"]["node_name"])

    def test_counters_are_cumulative_per_interface(self):
        last = {}
        for e in self.entries(80):
            f = capture(e)["fields"]
            k = "metric_name:interface_generic_counters.bytes_received"
            if k in f:
                if f["interface_name"] in last:
                    self.assertGreater(f[k], last[f["interface_name"]])
                last[f["interface_name"]] = f[k]
        self.assertGreaterEqual(len(last), 3)

    def test_source_is_the_device_address_and_index_follows_the_transport(self):
        e = self.entries(1)[0]
        pl = capture(e)
        self.assertEqual(pl["source"], e.src_ip)
        cfg = TelemetryTransportConfig(hec_enabled=True, hec_url="https://x.invalid/", hec_token="t", hec_index="e", hec_metric_index="some_other_metric_index")
        cap = []
        dispatcher._dispatch_log(e, cfg, capture=cap)
        self.assertEqual(cap[0]["index"], "some_other_metric_index")

    def test_scenario_gnmi_path_is_unchanged(self):
        from netspout_core.log_engine import SplunkLogEngine
        from netspout_core.models import Node, NodeType
        n = Node(id="r", name="r", type=NodeType.ROUTER, x=0, y=0, ip_address="192.0.2.1", vendor="cisco_ios", sourcetype=self.ST)
        e = SplunkLogEngine.format_mdt_stream(n, interface_name="Gi0/0/0", in_octets=1, out_octets=2, cpu_pct=1.0, memory_pct=2.0, sourcetype=self.ST)
        self.assertIsNone(e.metric_profile)
        f = capture(e)["fields"]
        self.assertIn("metric_name:in_octets", f)
        self.assertIn("device", f)


# --------------------------------------------------------------------------------------------------------------- IOS / ISE profiles
class TestIngestionProfiles(unittest.TestCase):
    IOS_RE = re.compile(r"^%[A-Z0-9_]+-\d-[A-Z0-9_]+: ")
    ISE_RE = re.compile(r"^[A-Z][a-z]{2} [ \d]\d \d\d:\d\d:\d\d \d{1,3}(\.\d{1,3}){3} [A-Z][a-z]{2} [ \d]\d \d\d:\d\d:\d\d \S+ CISE_\w+ \d+ ")

    def test_fixtures_have_the_documented_shapes(self):
        self.assertRegex(FIX["cisco:ios"]["raw"], self.IOS_RE)
        self.assertRegex(FIX["cisco:ise:syslog"]["raw"], self.ISE_RE)
        self.assertFalse(FIX["cisco:ise:syslog"]["raw"].startswith("<"))

    def test_direct_is_the_default_and_unchanged(self):
        e = svc().prepare_sourcetype_entries("cisco_ios", "cisco:ios", 3)[0]
        e2 = svc().prepare_sourcetype_entries("cisco_ios", "cisco:ios", 3, ingestion_profile="direct")[0]
        for x in e + e2:
            self.assertRegex(x.raw_log, r"^[A-Z][a-z]{2} [ \d]\d \d\d:\d\d:\d\d \S+ ")          # syslog header kept
            self.assertIsNone(x.hec_source)
            pl = capture(x)
            self.assertEqual(pl["source"], "network-topology-simulator")
        ise = svc().prepare_sourcetype_entries("cisco_ise", "cisco:ise:syslog", 2)[0]
        self.assertTrue(all(x.raw_log.startswith("<") for x in ise), "direct ISE keeps its <PRI>")

    def test_ios_sc4s_profile(self):
        for e in svc().prepare_sourcetype_entries("cisco_ios", "cisco:ios", 20, ingestion_profile="sc4s")[0]:
            self.assertRegex(e.raw_log, self.IOS_RE)
            self.assertNotRegex(e.raw_log, r"^[A-Z][a-z]{2} ")
            pl = capture(e)
            self.assertEqual((pl["source"], pl["sourcetype"]), ("sc4s", "cisco:ios"))
            self.assertRegex(pl["host"], r"^\d{1,3}(\.\d{1,3}){3}$")
            self.assertEqual(pl["event"], e.raw_log)

    def test_ise_sc4s_profile(self):
        for e in svc().prepare_sourcetype_entries("cisco_ise", "cisco:ise:syslog", 6, ingestion_profile="sc4s")[0]:
            self.assertRegex(e.raw_log, self.ISE_RE)
            self.assertFalse(e.raw_log.startswith("<"))
            pl = capture(e)
            self.assertEqual((pl["source"], pl["sourcetype"]), ("sc4s", "cisco:ise:syslog"))

    def test_sc4s_does_not_change_other_sourcetypes_and_is_refused_for_them(self):
        for st, v in (("cisco:ftd:syslog", "cisco_ftd"), ("cisco:asa", "cisco_asa"), ("cisco:sdwan:utd:logs", "cisco_sdwan")):
            with self.assertRaises(ValueError) as cm:
                svc().prepare_sourcetype_entries(v, st, 1, ingestion_profile="sc4s")
            self.assertIn("not supported", str(cm.exception))
        es = svc().prepare_sourcetype_entries("cisco_ftd", "cisco:ftd:syslog", 1)[0]
        self.assertRegex(es[0].raw_log, r"^[A-Z][a-z]{2} [ \d]\d \d\d:\d\d:\d\d ")                  # header untouched, no global stripping

    def test_unknown_profile_is_rejected(self):
        with self.assertRaises(ValueError):
            svc().prepare_sourcetype_entries("cisco_ios", "cisco:ios", 1, ingestion_profile="bogus")

    def test_event_without_the_standard_message_is_not_guessed(self):
        self.assertIsNone(ip.convert("cisco:ios", "sc4s", "Nov 03 20:00:00 10.0.0.1 sshd[1]: no cisco mnemonic here"))
        self.assertIsNone(ip.convert("cisco:ise:syslog", "sc4s", "Nov 03 20:00:00 node something else"))
        self.assertEqual(ip.expressible("cisco:ios", "sc4s", ["plain line"]), [])
        with self.assertRaises(ValueError):
            ip.apply_to_entries("cisco:ios", "sc4s", [type("E", (), {"raw_log": "plain", "device_id": "d"})()])

    def test_profile_is_reported_in_provenance(self):
        _, prov = svc().prepare_sourcetype_entries("cisco_ios", "cisco:ios", 1, ingestion_profile="sc4s")
        self.assertEqual(prov["ingestion_profile"], "sc4s")
        _, prov = svc().prepare_sourcetype_entries("cisco_ios", "cisco:ios", 1)
        self.assertEqual(prov["ingestion_profile"], "direct")


if __name__ == "__main__":
    unittest.main()


class TestMerakiEventTime(unittest.TestCase):
    def test_occurred_at_is_rendered_at_generation_time_in_the_observed_format(self):
        fx = json.loads(FIX["meraki:securityappliances"]["raw"])["occurredAt"]
        now = datetime(2027, 6, 5, 4, 3, 2, 123456, tzinfo=timezone.utc)
        out = json.loads(rfg.refresh_event_time("meraki:securityappliances", FIX["meraki:securityappliances"]["raw"], now))
        self.assertEqual(out["occurredAt"], "2027-06-05T04:03:02.123456Z")
        self.assertRegex(out["occurredAt"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}Z$")
        self.assertRegex(fx, r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}Z$")
        self.assertEqual({k: v for k, v in out.items() if k != "occurredAt"}, {k: v for k, v in json.loads(FIX["meraki:securityappliances"]["raw"]).items() if k != "occurredAt"})

    def test_generated_events_are_current_and_other_sourcetypes_untouched(self):
        es, _ = svc().prepare_sourcetype_entries("cisco_meraki", "meraki:securityappliances", 5)
        for e in es:
            t = datetime.strptime(json.loads(e.raw_log)["occurredAt"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
            self.assertLess(abs((datetime.now(timezone.utc) - t).total_seconds()), 60)
        self.assertEqual(rfg.refresh_event_time("meraki:accesspoints", '{"occurredAt": "2020-01-01T00:00:00.000000Z"}'), '{"occurredAt": "2020-01-01T00:00:00.000000Z"}')


class TestFieldOwnershipEvidence(unittest.TestCase):
    """NAMESPACED_ONLY_SOURCETYPES exists only because the live check found NetSpout values under bare field names; every member needs passing live evidence."""

    def test_every_member_has_a_passing_live_shadow_check(self):
        from netspout_core import telemetry_dispatcher as td
        passed = set()
        for f in (ROOT / "docs/verification/evidence/phase8").glob("live_*.json"):
            for c in json.loads(f.read_text())["checks"]:
                m = re.match(r"splunk\.no_netspout_value_under_a_bare_field_name\[(.+?)(?:/\w+)?\]$", c["check"])
                if m and c["status"] == "PASS":
                    passed.add(m.group(1))
        self.assertEqual(set(td.NAMESPACED_ONLY_SOURCETYPES), passed - set(td.TA_PARSED_SOURCETYPES) - {"cisco:ios"})
        self.assertFalse(set(td.NAMESPACED_ONLY_SOURCETYPES) & set(td.TA_PARSED_SOURCETYPES))

    def test_bare_names_are_not_sent_but_netspout_copies_are(self):
        for st, v in (("cisco:ise:syslog", "cisco_ise"), ("meraki:securityappliances", "cisco_meraki"), ("cisco:duo:authentication_v2", "cisco_duo")):
            pl = capture(svc().prepare_sourcetype_entries(v, st, 1)[0][0])
            for k in ("action", "src_ip", "dest_ip", "status", "signature", "protocol", "vendor", "node_type"):
                self.assertNotIn(k, pl["fields"], "%s %s" % (st, k))
            self.assertIn("netspout_vendor", pl["fields"])

    def test_sourcetypes_outside_both_sets_are_unchanged(self):
        pl = capture(svc().prepare_sourcetype_entries("cisco_ftd", "cisco:ftd:syslog", 1)[0][0])
        self.assertIn("src_ip", pl["fields"])
        self.assertIn("netspout_src_ip", pl["fields"])
