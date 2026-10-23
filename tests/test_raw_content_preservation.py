"""Raw-content preservation regressions (vendor-native RAW fidelity P0).

Layers covered:
- R5  SplunkLogEngine vendor-native formatters build vendor-native bodies with
      NO synthetic PulseForge KV tail; exact-byte expectations per family.
      Palo Alto traffic/threat are intentionally absent here: both formatter
      hunks remain frozen to HEAD pending a pinned PAN-OS CSV field contract
      (see tests/test_fortinet_checkpoint_fidelity.py::test_pan_raw_and_samples_unchanged
      and docs/catalog/FORTINET_CHECKPOINT_RAW_REPAIR.md).
- R1  ScenarioRunner.tag_log carries correlation only in LogEntry
      attributes; byte-exact vendor `raw_log` is never mutated. Legacy
      correlation-KV raw payloads are never re-appended.
- R2  TelemetryDispatcher HEC log payload: `event` equals the clean vendor
      raw bytes byte-for-byte while all netspout_* correlation fields stay
      searchable in the HEC `fields` block.
- R3  RFC5424 syslog formatter refuses double-headering payloads that
      already carry a PRI-aware syslog header.
- R4  BSD syslog day spacing follows the RFC 3164 space-padded convention.
"""
import datetime
import os
import re
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from netspout_core.models import (  # noqa: E402
    LogEntry,
    Node,
    NodeType,
    TelemetryTransportConfig,
)
from netspout_core.log_engine import SplunkLogEngine  # noqa: E402
from netspout_core.scenario_runner import ScenarioRunner  # noqa: E402
from netspout_core.telemetry_dispatcher import (  # noqa: E402
    format_rfc3164_message,
    format_rfc5424_message,
    get_bsd_syslog_timestamp,
    TelemetryDispatcher,
)

# In-band PulseForge KV markers that must never appear in vendor raw payloads
# after the P0 tail removal (PAN excluded by frozen contract).
SYNTHETIC_TAIL_MARKERS = (
    'timestamp="',
    'device_id="',
    'signature="',
    "action=",
    "status=",
    "protocol=",
    "duration=",
    "netspout_run_id=",
)

BSD_SYSLOG_TS = re.compile(r"[A-Z][a-z]{2} [ 1-3]\d \d{2}:\d{2}:\d{2}")


def make_node(name="Core-Switch-01", vendor="generic", sourcetype=None):
    return Node(
        id="node-1",
        name=name,
        type=NodeType.SWITCH,
        vendor=vendor,
        sourcetype=sourcetype,
    )


def vendor_entry(
    raw: str,
    device: str = "Core-Switch-01",
    sourcetype: str = "cisco:ios:syslog",
) -> LogEntry:
    """LogEntry built from a formatter's byte-exact vendor raw (R2 contract)."""
    return LogEntry(
        timestamp="2026-10-06T14:03:27.000 UTC",
        device_id=device,
        src_ip="10.0.0.1",
        dest_ip="10.0.0.2",
        protocol="TCP",
        duration="1ms",
        action="allowed",
        signature="Vendor raw",
        status="normal",
        raw_log=raw,
        node_type="switch",
        node_id="node-1",
        vendor="cisco",
        sourcetype=sourcetype,
        netspout_run_id="NS-20261006-RAWPRES",
        netspout_scenario_id="vendor_raw_scenario",
        netspout_phase="BASELINE",
        netspout_event_id="evt-rawpres-01",
        netspout_ground_truth="true",
    )


class TestVendorFormatterRawPreservation(unittest.TestCase):
    """R5: vendor-native formatters do not append synthetic KV tails."""

    def assert_clean_vendor_raw(self, raw: str, sourcetype: str = "") -> None:
        for marker in SYNTHETIC_TAIL_MARKERS:
            self.assertNotIn(marker, raw, f"sourcetype={sourcetype} leaked '{marker}' in raw: {raw}")
        self.assertFalse(raw.endswith(" "), raw)
        self.assertFalse(raw.endswith(","), raw)

    def test_router_switch_exact(self):
        device = make_node("ASR-9006", vendor="cisco_ios", sourcetype="cisco:ios:syslog")
        ts = SplunkLogEngine.current_timestamp_syslog()
        entry = SplunkLogEngine.format_router_switch_log(
            device=device,
            src_ip="10.0.20.5",
            dest_ip="10.0.30.9",
            interface="TenGigE0/0/0/2",
            action="blocked",
            signature="Routing flow",
            status="degraded",
        )
        self.assertEqual(
            entry.raw_log,
            f"{ts} ASR-9006 %ROUTING-5-FLOW: Ingress interface TenGigE0/0/0/2 forward packet "
            f"from 10.0.20.5 to 10.0.30.9 via BGP-RIB",
        )
        self.assertEqual(entry.sourcetype, "cisco:ios:syslog")
        self.assert_clean_vendor_raw(entry.raw_log, entry.sourcetype)

    def test_catalyst_rogue_exact(self):
        device = make_node("C9300-ASW-01", vendor="cisco_catalyst")
        ts = SplunkLogEngine.current_timestamp_syslog()
        entry = SplunkLogEngine.format_cisco_catalyst_rogue_log(
            device=device,
            rogue_mac="aa:bb:cc:00:11:22",
            bssid="11:22:33:44:55:66",
            ssid="Corp-Executive-Secure",
            channel=112,
            rssi=-42,
            action="breached",
            status="breached",
        )
        self.assertEqual(
            entry.raw_log,
            f"{ts} C9300-ASW-01 %CATALYST_SEC-4-ROGUE_ALERT: Rogue AP detected on campus RF matrix. "
            'rogue_mac=aa:bb:cc:00:11:22 bssid=11:22:33:44:55:66 ssid="Corp-Executive-Secure" channel=112 rssi=-42dBm',
        )
        self.assertEqual(entry.sourcetype, "cisco:catalyst:rogue:threat_details")

    def test_catalyst_security_event_exact(self):
        device = make_node("C9300-ASW-01", vendor="cisco_catalyst")
        ts = SplunkLogEngine.current_timestamp_syslog()
        entry = SplunkLogEngine.format_cisco_catalyst_security_event(
            device=device,
            client_mac="de:ad:be:ef:00:01",
            event_type="PORT_SHUTDOWN",
            action="blocked",
            status="blocked",
        )
        self.assertEqual(
            entry.raw_log,
            f'{ts} C9300-ASW-01 %CATALYST_SEC-6-EVENT: event_type="PORT_SHUTDOWN" '
            f'client_mac="de:ad:be:ef:00:01"',
        )
        self.assertEqual(entry.sourcetype, "cisco:catalyst:security:events")

    def test_sdwan_linkhealth_exact(self):
        device = make_node("vEdge-CAMPUS-01", vendor="cisco_sdwan")
        ts = SplunkLogEngine.current_timestamp_syslog()
        entry = SplunkLogEngine.format_cisco_sdwan_linkhealth_log(
            device=device,
            remote_system_ip="172.16.255.10",
            latency_ms=188.25,
            jitter_ms=14.5,
            loss_pct=8.125,
            sla_status="non-compliant",
            action="degraded",
            status="degraded",
        )
        self.assertEqual(
            entry.raw_log,
            f"{ts} vEdge-CAMPUS-01 SDWAN-BFD-SLA[512]: local_color=biz-internet remote_color=mpls "
            "remote_system_ip=172.16.255.10 latency=188.2ms jitter=14.5ms "
            "loss=8.1% sla_class=VoIP_Gold sla_compliance=non-compliant",
        )
        self.assertEqual(entry.sourcetype, "cisco:sdwan:linkhealth")

    def test_sdwan_bgp_exact(self):
        device = make_node("vEdge-CAMPUS-01", vendor="cisco_sdwan")
        ts = SplunkLogEngine.current_timestamp_syslog()
        entry = SplunkLogEngine.format_cisco_sdwan_bgp_log(
            device=device,
            neighbor_ip="172.16.255.10",
            state_change="Down",
            action="degraded",
            status="degraded",
        )
        self.assertEqual(
            entry.raw_log,
            f"{ts} vEdge-CAMPUS-01 %BGP-5-ADJCHANGE: neighbor 172.16.255.10 vpn 10 Down "
            "BFD session down; failover to secondary LTE/Broadband transport engaged",
        )
        self.assertEqual(entry.sourcetype, "cisco:sdwan:BGP-5-ADJCHANGE")

    def test_apic_health_exact(self):
        device = make_node("APIC-01", vendor="cisco_aci")
        ts = SplunkLogEngine.current_timestamp_syslog()
        entry = SplunkLogEngine.format_cisco_aci_health_log(
            device=device,
            fabric_health=58,
            action="breached",
            status="breached",
        )
        expected = f"{ts} APIC-01 %ACI-HEALTH-4-SCORE: fabricHealthScore=58"
        self.assertEqual(entry.raw_log, expected)
        self.assertEqual(entry.sourcetype, "cisco:dc:aci:health")
        self.assert_clean_vendor_raw(entry.raw_log, entry.sourcetype)

    def test_dhcp_snooping_exact(self):
        device = make_node("C9300-ASW-01", vendor="cisco_catalyst")
        ts = SplunkLogEngine.current_timestamp_syslog()
        entry = SplunkLogEngine.format_cisco_catalyst_dhcp_snooping_log(
            device=device,
            client_mac="ca:fe:ba:be:00:07",
            vlan_id=210,
            interface="Gi1/0/48",
            rogue_ip="203.0.113.66",
            event_code="DHCP_OFFER_DROPPED",
            action="blocked",
            status="blocked",
        )
        self.assertEqual(
            entry.raw_log,
            f"{ts} C9300-ASW-01 %DHCP_SNOOPING-5-DHCP_OFFER_DROPPED: Rogue DHCP offer packet dropped on "
            "untrusted port Gi1/0/48, vlan 210, rogue server IP 203.0.113.66, client MAC ca:fe:ba:be:00:07",
        )
        self.assertEqual(entry.sourcetype, "cisco:catalyst:security:events")

    def test_ios_xr_bgp_up_exact(self):
        device = make_node("XR-ASR-9006", vendor="cisco_xr")
        ts = SplunkLogEngine.current_timestamp_syslog()
        entry = SplunkLogEngine.format_cisco_ios_xr_bgp_log(
            device=device,
            neighbor_ip="192.0.2.11",
            event_type="BGP_UP",
            action="allowed",
            status="normal",
        )
        self.assertEqual(
            entry.raw_log,
            f"{ts} XR-ASR-9006 %ROUTING-BGP-5-ADJCHANGE: neighbor 192.0.2.11 Up - "
            "Peering re-established after carrier stabilization",
        )

    def test_wlan_rf_restored_exact(self):
        device = make_node("WLC-9800-01", vendor="cisco_catalyst")
        ts = SplunkLogEngine.current_timestamp_syslog()
        entry = SplunkLogEngine.format_cisco_catalyst_wlan_rf_log(
            device=device,
            channel=100,
            util_pct=41.0,
            noise_floor=-88,
            event_type="RF_RESTORED",
            action="allowed",
            status="normal",
        )
        self.assertEqual(
            entry.raw_log,
            f"{ts} WLC-9800-01 %DOT11-6-CLEANAIR_HEALTH: Channel 100 clean, channel "
            "utilization=41.0% noise_floor=-88dBm, client SNR=38dB",
        )

    def test_aci_nexus_exact(self):
        device = make_node("N9K-LEAF-01", vendor="cisco_nexus")
        ts = SplunkLogEngine.current_timestamp_syslog()
        entry = SplunkLogEngine.format_cisco_aci_nexus_log(
            device=device,
            asic_interface="eth1/32",
            buffer_util_pct=97.5,
            dropped_packets=412,
            fabric_health=62,
            action="degraded",
            status="degraded",
        )
        expected = (
            f"{ts} N9K-LEAF-01 %BUFFER_MGR-3-QUEUE_DROP: Ingress queue threshold exceeded on eth1/32. "
            "buffer_util=97.5% dropped_packets=412 fabricHealthScore=62"
        )
        self.assertEqual(entry.raw_log, expected)
        self.assertEqual(entry.sourcetype, "cisco:dc:nexus9k:syslog")
        self.assert_clean_vendor_raw(entry.raw_log, entry.sourcetype)

    def test_f5_lb_exact(self):
        device = make_node("rseries-boston-01", vendor="f5_bigip")
        ts = SplunkLogEngine.current_timestamp_syslog()
        entry = SplunkLogEngine.format_f5_lb_log(
            device=device,
            src_ip="10.128.20.4",
            dest_ip="10.129.44.9",
            backend_ip="10.200.0.14",
            backend_port=8443,
            action="allowed",
            signature="LTM pool",
            status="normal",
        )
        self.assertEqual(
            entry.raw_log,
            f"{ts} rseries-boston-01 local/tmm[1104]: 01070727:3: Pool /Common/web_farm member "
            "/Common/10.200.0.14:8443 connection established client=10.128.20.4 vip=10.129.44.9:80 target=10.200.0.14:8443",
        )
        self.assertEqual(entry.sourcetype, "f5:bigip:ltm")

    def test_nokia_sros_exact(self):
        device = make_node("SR-7750-BER-01", vendor="nokia_sros")
        ts = SplunkLogEngine.current_timestamp_syslog()
        entry = SplunkLogEngine.format_nokia_sros_log(
            device=device,
            port_id="1/1/c1/1",
            lsp_name="CAMPUS_FROZEN_LSP_NYC",
            action="degraded",
            status="degraded",
        )
        expected = (
            f"{ts} SR-7750-BER-01 Base %ROUTING-3-OPTICAL_LOS: Optical DWDM port 1/1/c1/1 Loss of Signal. "
            "RSVP-TE LSP CAMPUS_FROZEN_LSP_NYC path failed. Fast Reroute (FRR) facility bypass engaged."
        )
        self.assertEqual(entry.raw_log, expected)
        self.assertEqual(entry.sourcetype, "nokia:sros:syslog")
        self.assert_clean_vendor_raw(entry.raw_log, entry.sourcetype)


class TestScenarioRunnerCorrelationSeparation(unittest.TestCase):
    """R1: tag_log carries correlation in attributes, never in vendor raw bytes."""

    def setUp(self):
        self.runner = ScenarioRunner()

    def _clean_log(self, raw: str) -> LogEntry:
        return LogEntry(
            timestamp="2026-10-06T14:03:27.000 UTC",
            device_id="APIC-01",
            src_ip="10.0.0.1",
            dest_ip="10.0.0.2",
            protocol="TCP",
            duration="1ms",
            action="degraded",
            signature="Fabric health",
            status="degraded",
            raw_log=raw,
            node_type="switch",
            node_id="node-1",
            vendor="cisco_aci",
            sourcetype="cisco:dc:aci:health",
        )

    def test_tag_log_leaves_vendor_raw_byte_exact(self):
        raw = "Oct  6 14:03:27 APIC-01 %ACI-HEALTH-4-SCORE: fabricHealthScore=58 (clean vendor body)"
        log = self._clean_log(raw)
        tagged = self.runner.tag_log(
            log,
            run_id="NS-20261006-PRESERVE",
            scenario_id="cisco_aci_microburst",
            phase="BASELINE",
            device_id="APIC-01",
        )
        self.assertIs(tagged, log)
        self.assertEqual(log.raw_log, raw)
        self.assertEqual(log.netspout_run_id, "NS-20261006-PRESERVE")
        self.assertEqual(log.netspout_scenario_id, "cisco_aci_microburst")
        self.assertEqual(log.netspout_phase, "BASELINE")
        self.assertEqual(log.netspout_device_id, "APIC-01")
        self.assertTrue(log.netspout_event_id)
        self.assertEqual(log.netspout_ground_truth, "true")

    def test_tag_log_never_reappends_to_legacy_kv_raw(self):
        legacy_raw = 'Oct  6 14:03:27 APIC-01 %ACI-HEALTH-4-SCORE: fabricHealthScore=58 netspout_run_id="NS-LEGACY"'
        log = self._clean_log(legacy_raw)
        tagged = self.runner.tag_log(log, run_id="NS-20261006-NOTAPPENDED")
        self.assertEqual(tagged.raw_log, legacy_raw)
        self.assertEqual(tagged.netspout_run_id, "NS-20261006-NOTAPPENDED")


class TestHECPayloadFieldSeparation(unittest.TestCase):
    """R2: dispatcher forwards clean vendor bytes in `event`; correlation via `fields`."""

    def setUp(self):
        self.dispatcher = TelemetryDispatcher()
        self.transport = TelemetryTransportConfig(
            hec_enabled=True,
            hec_url="https://127.0.0.1:8088/services/collector/event",
            hec_token="st-shielded",
            hec_index="idx_network_ops",
        )

    @patch.object(TelemetryDispatcher, "emit_hec")
    def test_hec_event_is_clean_vendor_raw_and_fields_carry_correlation(self, mock_emit):
        mock_emit.return_value = (True, "OK")
        raw = "Oct  6 14:03:27 APIC-01 %ACI-HEALTH-4-SCORE: fabricHealthScore=58 vendor-only"
        log = vendor_entry(raw, device="APIC-01", sourcetype="cisco:dc:aci:health")
        tags = self.dispatcher.dispatch_log(log, transport=self.transport)
        self.assertTrue(tags["hec"]["success"])
        payload = mock_emit.call_args[0][0]
        self.assertEqual(payload["event"], raw)
        for marker in SYNTHETIC_TAIL_MARKERS:
            self.assertNotIn(marker, payload["event"])
        fields = payload["fields"]
        self.assertEqual(fields["netspout_run_id"], "NS-20261006-RAWPRES")
        self.assertEqual(fields["netspout_scenario_id"], "vendor_raw_scenario")
        self.assertEqual(fields["netspout_phase"], "BASELINE")
        self.assertEqual(fields["netspout_event_id"], "evt-rawpres-01")
        self.assertEqual(fields["netspout_ground_truth"], "true")


class TestSyslogHeaderGuards(unittest.TestCase):
    """R3 + R4: no double headers; RFC 3164 space-padded day convention."""

    VENDOR_SYSLOG = "<134>Oct  6 14:03:27 APIC-01 rpd[2941]: RPD_MPLS_LSP_CHANGE: LSP CAMPUS-AP-1"

    def test_rfc5424_never_double_headers_vendor_syslog(self):
        out = format_rfc5424_message(16, 6, "sim-host", "netops", "-", "-", self.VENDOR_SYSLOG)
        self.assertEqual(out, self.VENDOR_SYSLOG)

    def test_rfc5424_headers_plain_messages(self):
        out = format_rfc5424_message(16, 6, "sim-host", "netops", "-", "-", "plain message")
        self.assertTrue(out.startswith("<134>1 "))
        self.assertTrue(out.endswith("- plain message"))

    def test_bsd_day_spacing_rfc3164(self):
        self.assertEqual(get_bsd_syslog_timestamp(datetime.datetime(2026, 10, 6, 14, 3, 27)), "Oct  6 14:03:27")
        self.assertEqual(get_bsd_syslog_timestamp(datetime.datetime(2026, 10, 5, 14, 3, 27)), "Oct  5 14:03:27")
        self.assertEqual(get_bsd_syslog_timestamp(datetime.datetime(2026, 10, 23, 6, 1, 9)), "Oct 23 06:01:09")

    def test_rfc3164_uses_space_padded_day(self):
        payload = format_rfc3164_message(16, 6, "sim-host", "netops", "plain message")
        m = re.match(r"<\d+>([A-Z][a-z]{2}) ( ?\d{1,2}) \d{2}:\d{2}:\d{2} ", payload)
        self.assertTrue(m, payload)
        day = int(m.group(2))
        if day < 10:
            self.assertTrue(m.group(2).startswith(" "), payload)
        else:
            self.assertFalse(m.group(2).startswith(" "), payload)

    def test_current_timestamp_syslog_space_pads_day(self):
        ts = SplunkLogEngine.current_timestamp_syslog()
        m = BSD_SYSLOG_TS.fullmatch(ts)
        self.assertTrue(m, ts)
        day_field = ts.split(" ")[1]
        self.assertEqual(len(day_field), 2)
        day = int(day_field)
        if day < 10:
            self.assertEqual(day_field[0], " ", ts)


if __name__ == "__main__":
    unittest.main()
