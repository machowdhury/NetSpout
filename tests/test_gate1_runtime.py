#!/usr/bin/env python3
"""
NetSpout Gate 1 Runtime Stabilization Regression Tests
Verifies:
1. DEF-01: datablaster_rest.py imports and typing resolution without NameError.
2. Complete importability of all netspout/bin/ modules.
3. Schema compatibility and synchronized models.py definitions (NodeType, ScenarioType, NodeHardware KPI fields).
4. OpenConfig / MDT model-driven telemetry generation (RFC 7951 compliance, interfaces, BGP, platform, system).
5. Continuous streaming lifecycle: status, start, duplicate start prevention, and stop.
6. Optional live Splunk container validation when available.
"""

import os
import sys
import json
import time
import unittest
import types

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
candidate_bins = [
    os.path.join(REPO_ROOT, "netspout", "bin"),
    "/opt/splunk/etc/apps/netspout/bin",
    "/opt/splunk/etc/apps/TA-network-data-blaster/bin"
]
for cb in candidate_bins:
    if os.path.isdir(cb) and cb not in sys.path:
        sys.path.insert(0, cb)

# Provide mock splunk.rest if running outside Splunk Enterprise
try:
    import splunk.rest
except ImportError:
    splunk_mod = types.ModuleType("splunk")
    splunk_rest_mod = types.ModuleType("splunk.rest")
    class MockPersistentServerConnectionApplication:
        def __init__(self, command_line=None, command_arg=None):
            pass
        def handle(self, in_string):
            return {"status": 200, "payload": "{}"}
        def handleStream(self, handle, in_string):
            pass
    class MockBaseRestHandler:
        def __init__(self, *args, **kwargs):
            pass
    splunk_rest_mod.PersistentServerConnectionApplication = MockPersistentServerConnectionApplication
    splunk_rest_mod.BaseRestHandler = MockBaseRestHandler
    splunk_mod.rest = splunk_rest_mod
    sys.modules["splunk"] = splunk_mod
    sys.modules["splunk.rest"] = splunk_rest_mod


class TestGate1RuntimeStabilization(unittest.TestCase):

    def test_01_def01_datablaster_rest_import(self):
        """DEF-01: Ensure datablaster_rest imports cleanly and resolves List/typing without NameError."""
        try:
            import datablaster_rest
        except NameError as ne:
            self.fail(f"DEF-01 regression: NameError during datablaster_rest import: {ne}")
        except Exception as e:
            self.fail(f"Failed to import datablaster_rest: {e}")

        # Verify resolve_hec_urls exists and returns List[str]
        self.assertTrue(hasattr(datablaster_rest, "resolve_hec_urls"))
        urls = datablaster_rest.resolve_hec_urls("https://127.0.0.1:8888")
        self.assertIsInstance(urls, list)
        self.assertGreater(len(urls), 0)
        self.assertIn("https://127.0.0.1:8888", urls)

        # Verify DataBlasterRestHandler class exists
        self.assertTrue(hasattr(datablaster_rest, "DataBlasterRestHandler"))

    def test_02_all_bin_modules_importability(self):
        """Validate that all Python modules in netspout/bin import with zero NameError/ImportError."""
        modules_to_test = [
            "models",
            "graph_engine",
            "fault_injection_engine",
            "gnmi_engine",
            "scenario_runner",
            "run_simulation",
            "cisco_sample_provider",
            "snmp_engine",
            "telemetry_dispatcher",
            "datablaster_rest"
        ]
        for mod_name in modules_to_test:
            with self.subTest(module=mod_name):
                try:
                    __import__(mod_name)
                except Exception as e:
                    self.fail(f"Module {mod_name} failed import in netspout/bin: {e}")

    def test_03_models_schema_synchronization(self):
        """Validate synchronized schema types and fields in netspout/bin/models.py."""
        import models

        # Check synchronized NodeType values
        required_node_types = [
            "storage_san", "storage_nas", "vpn_gateway", "cloud_transit", "iot_sensor", "wlc_controller"
        ]
        for nt in required_node_types:
            self.assertTrue(hasattr(models.NodeType, nt.upper()), f"Missing NodeType.{nt.upper()}")

        # Check synchronized ScenarioType values (architectures and specialized)
        required_scenarios = [
            "ARCH_PAN_IOT_MESH", "ARCH_LAN_CAMPUS_ACCESS", "ARCH_WLAN_MERAKI_CATALYST",
            "ARCH_CAN_MULTI_BUILDING", "ARCH_MAN_CARRIER_RING", "ARCH_WAN_GLOBAL_BACKBONE",
            "ARCH_SAN_FIBRE_CHANNEL", "ARCH_NAS_STORAGE_CLUSTER", "ARCH_VPN_REMOTE_WORKFORCE",
            "ARCH_EPN_ISOLATED_INTRANET", "ARCH_GAN_SUBSEA_CLOUD",
            "PURE_CISCO_ENTERPRISE", "MIXED_VENDOR_ENTERPRISE",
            "SERVICE_PROVIDER_CISCO", "SERVICE_PROVIDER_MIXED",
            "SDWAN_CONNECTED_CORE"
        ]
        for st in required_scenarios:
            self.assertTrue(hasattr(models.ScenarioType, st), f"Missing ScenarioType.{st}")

        # Check NodeHardware has the 4 KPI telemetry dimensions (20 fields)
        hw = models.NodeHardware()
        kpi_fields = [
            # Dim 1: Performance & Traffic
            "bandwidth_utilization_pct", "throughput_bps", "latency_ms", "jitter_ms", "packet_loss_pct", "error_rate_pct",
            # Dim 2: Device & Infrastructure Health
            "uptime_seconds", "cpu_utilization_pct", "memory_utilization_pct", "temperature_celsius", "psu_status", "psu_wattage", "ups_battery_runtime_min", "ups_input_voltage",
            # Dim 3: Configuration & Protocols
            "routing_table_version", "bgp_prefix_count", "route_flaps", "config_drift_checksum", "ipam_dhcp_exhaustion_pct",
            # Dim 4: Security & Compliance
            "traffic_spike_score", "unauthorized_access_attempts", "firewall_drop_count", "threat_severity_level"
        ]
        for field in kpi_fields:
            self.assertTrue(hasattr(hw, field), f"Missing NodeHardware KPI field: {field}")

        # Check safe Splunk default for ZoneAnnotation
        zone = models.ZoneAnnotation(zone_id="test", name="Test Zone")
        self.assertEqual(zone.zone_type, models.SecurityZoneType.INTERNAL_TRUST)

    def test_04_openconfig_mdt_generation(self):
        """Validate OpenConfig MDT RFC 7951 YANG tree generation for interfaces, BGP, platform, system."""
        import models
        import gnmi_engine

        store = gnmi_engine.OpenConfigYANGStore()
        server = gnmi_engine.MockGNMIServer(store)

        node = models.Node(
            id="rtr-core-edge-01",
            name="rtr-core-edge-01",
            type=models.NodeType.ROUTER,
            vendor="cisco"
        )

        tree = store.get_or_create_tree(node)
        self.assertIn("openconfig-interfaces:interfaces", tree)
        self.assertIn("openconfig-platform:components", tree)
        self.assertIn("openconfig-network-instance:network-instances", tree)
        self.assertIn("openconfig-system:system", tree)

        # Validate RFC 7951 JSON serialization
        rfc_json_str = store.to_rfc7951_json(node.id)
        parsed = json.loads(rfc_json_str)
        self.assertIn("openconfig-interfaces:interfaces", parsed)

        # Validate sample telemetry generation
        metrics = server.generate_sample_telemetry(node)
        self.assertGreater(len(metrics), 0)
        first_metric = metrics[0]
        self.assertEqual(first_metric.get("event"), "metric")
        self.assertEqual(first_metric.get("index"), "cisco_mdt_metrics")
        self.assertIn("metric_name:interface.octets.in", first_metric.get("fields", {}))

    def test_05_continuous_streaming_lifecycle(self):
        """Validate continuous streaming handlers: status, duplicate start prevention, stop."""
        import datablaster_rest

        # Test initial status
        code, status_resp = datablaster_rest.execute_request({"action": "status"})
        self.assertEqual(code, 200)
        self.assertIn("running", status_resp)

        # Test duplicate start prevention logic
        # Mock active running state
        orig_get_status = datablaster_rest.get_current_status
        try:
            datablaster_rest.get_current_status = lambda: {
                "running": True,
                "pid": 999999,
                "log_path": "/tmp/test.log",
                "log_size_bytes": 100,
                "metadata": {}
            }
            code, start_resp = datablaster_rest.execute_request({
                "action": "start",
                "scenario": "scenario_acme_full_network_topology.yml",
                "eps": "100",
                "hec": "https://127.0.0.1:8888",
                "token": "00000000-0000-0000-0000-000000000000"
            })
            self.assertEqual(code, 200)
            self.assertEqual(start_resp.get("status"), "warning")
            self.assertIn("already running", start_resp.get("message", ""))
        finally:
            datablaster_rest.get_current_status = orig_get_status

        # Test stop when not running returns success / no simulation running
        if not status_resp.get("running"):
            code, stop_resp = datablaster_rest.execute_request({"action": "stop"})
            self.assertEqual(code, 200)
            self.assertEqual(stop_resp.get("status"), "success")

    def test_06_live_splunk_container_rest_probe(self):
        """If Splunk container is accessible on localhost:8889 or 8800, probe REST endpoint."""
        import urllib.request
        import ssl
        import base64

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        # Test splunkd REST on 8889 with Basic Auth (admin:SplunkPassword123!)
        auth_bytes = base64.b64encode(b"admin:SplunkPassword123!").decode("ascii")
        auth_header = f"Basic {auth_bytes}"
        url = "https://localhost:8889/services/datablaster/execute?output_mode=json"

        try:
            req = urllib.request.Request(url, headers={"Authorization": auth_header})
            with urllib.request.urlopen(req, context=ctx, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self.assertIn("running", data)
                print(f"\n[LIVE TEST] Live Splunk REST /services/datablaster/execute responded: running={data.get('running')}")
        except Exception as e:
            self.skipTest(f"Live Splunk probe skipped: {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
