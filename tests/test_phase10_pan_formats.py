"""Phase 10: pan:traffic, pan:threat and pan:system from Generate Data line up with the Splunk Add-on for Palo Alto Networks 4.0.0 (field positions and action names below are the
add-on's own, from its extract_threat / extract_system FIELDS lists and pan_vendor_actions_300.csv; verified live in the isolated lab, see tests/ta_specs/palo_alto_*.json)."""
import csv
import io
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "backend")]
os.environ.setdefault("NETSPOUT_HEC_TOKEN", "test-token")

from netspout_core import telemetry_dispatcher as td  # noqa: E402
from netspout_core.models import TelemetryTransportConfig  # noqa: E402

VENDOR_ACTIONS = {"alert", "allow", "block", "block-ip", "block-url", "block-continue", "continue", "deny", "drop", "drop-all-packets", "drop-packet", "forward", "reset-both", "reset-client", "reset-server",
                  "sinkhole", "wildfire-upload-skip", "wildfire-upload-success", "wildfire-upload-fail", "block-override", "override", "override-lockout", "random-drop", "syncookie-sent"}
SEVERITIES = {"informational", "low", "medium", "high", "critical"}
_SVC = None


def svc():
    global _SVC
    if _SVC is None:
        from app.generator_modes import TelemetryGeneratorService
        _SVC = TelemetryGeneratorService()
    return _SVC


def rows(st, n=60):
    es, prov = svc().prepare_sourcetype_entries("palo_alto", st, n)
    assert prov["mode"] == "native"
    return es, [next(csv.reader(io.StringIO(e.raw_log))) for e in es]


def stamp(s):
    return datetime.strptime(s, "%Y/%m/%d %H:%M:%S").replace(tzinfo=timezone.utc)


class TestPanFormats(unittest.TestCase):
    def test_threat_columns_match_the_addon_field_list(self):
        for r in rows("pan:threat")[1]:
            self.assertEqual(r[3], "THREAT")
            self.assertIn(r[30], VENDOR_ACTIONS, "action must be a name the add-on maps (block-ip, not blockip)")
            self.assertIn("(", r[32]); self.assertTrue(r[32].endswith(")"), "threat name with its id in parentheses (extract_threat_name / extract_threat_id)")
            self.assertEqual(r[33], "any")                                     # raw_category: position 33 of the add-on's list
            self.assertIn(r[34], SEVERITIES)                                   # severity: the add-on's regex needs it as the field right after raw_category
            self.assertIn(r[35], {"client-to-server", "server-to-client", "client-to-client", "unknown"})
            self.assertTrue(r[24].isdigit() and r[25].isdigit())               # src_port, dest_port

    def test_system_columns_match_the_addon_field_list(self):
        for r in rows("pan:system")[1]:
            self.assertEqual(r[3], "SYSTEM")
            self.assertEqual(r[12], r[4])                                       # module equals the sub type here
            self.assertIn(r[13], {"informational", "low", "medium", "high", "critical", "warning"})
            self.assertTrue(r[14])                                              # description
            self.assertTrue(r[15].isdigit())                                    # sequence_number

    def test_traffic_columns(self):
        for r in rows("pan:traffic")[1]:
            self.assertEqual(r[3], "TRAFFIC")
            self.assertIn(r[30], VENDOR_ACTIONS)
            self.assertTrue(r[24].isdigit() and r[25].isdigit())

    def test_timestamps_are_current_not_fixed_text(self):
        now = datetime.now(timezone.utc)
        for st in ("pan:traffic", "pan:threat", "pan:system"):
            for r in rows(st, 20)[1]:
                for i in (1, 6):
                    self.assertLess(abs((now - stamp(r[i])).total_seconds()), 120, "%s column %d" % (st, i))
                self.assertNotIn("2026/09/18", ",".join(r))

    def test_events_differ_between_calls_and_runs(self):
        a = {",".join(r) for r in rows("pan:threat", 30)[1]}
        self.assertGreater(len(a), 5, "more than the two fixed sample lines")

    def test_blockip_is_gone_from_the_generator(self):
        from netspout_core.panos_generator import THREAT_ACTIONS
        self.assertNotIn("blockip", THREAT_ACTIONS)
        self.assertIn("block-ip", THREAT_ACTIONS)

    def test_no_netspout_value_is_sent_under_a_vendor_field_name(self):
        cfg = TelemetryTransportConfig(hec_enabled=True, hec_url="https://x.invalid/services/collector", hec_token="t", hec_index="ta_validation")
        for st in ("pan:traffic", "pan:threat", "pan:system"):
            self.assertIn(st, td.TA_PARSED_SOURCETYPES)
            cap = []
            td.dispatcher._dispatch_log(rows(st, 1)[0][0], cfg, capture=cap)
            for k in td.NETSPOUT_NAMESPACED_FIELDS:
                self.assertNotIn(k, cap[0]["fields"], "%s %s" % (st, k))
            self.assertIn("netspout_vendor", cap[0]["fields"])

    def test_the_yaml_sample_lines_are_not_what_generate_data_sends(self):
        for st in ("pan:traffic", "pan:threat", "pan:system"):
            _, prov = svc().prepare_sourcetype_entries("palo_alto", st, 1)
            self.assertEqual(prov["mode"], "native")
            self.assertNotIn("pan-", str(prov.get("source")))


if __name__ == "__main__":
    unittest.main()
