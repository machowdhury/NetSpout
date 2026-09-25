#!/usr/bin/env python3
"""
NetSpout Gate 2 Single Python Source of Truth Regression Tests
Verifies:
1. Canonical netspout_core package importability and exposure of all 13 core modules.
2. Zero divergence and exact parity across canonical src/netspout_core, netspout/bin/netspout_core,
   netspout/bin, and backend/app via verify_sources guardrail.
3. Core engine execution purely via netspout_core (TopologyGraph, ScenarioRunner, SNMPEngine, OpenConfigYANGStore, TelemetryDispatcher).
4. Splunk package (.spl) build integrity and inclusion of netspout_core without invalid symlinks or bytecode caches.
5. Live simulator API operational readiness.
"""

import os
import sys
import json
import tarfile
import urllib.request
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

CORE_MODULES = [
    "models",
    "graph_engine",
    "log_engine",
    "scenario_runner",
    "snmp_engine",
    "gnmi_engine",
    "fault_injection_engine",
    "telemetry_dispatcher",
    "cisco_sample_provider",
    "spl_engine",
    "use_case_repo",
    "noc_soc_metrics",
    "vendor_catalog",
]


class TestGate2CanonicalSourceOfTruth(unittest.TestCase):

    def test_01_canonical_core_imports(self):
        """Ensure netspout_core and all 13 canonical modules import cleanly from src/."""
        import netspout_core
        self.assertTrue(hasattr(netspout_core, "__version__"))

        for mod_name in CORE_MODULES:
            with self.subTest(module=mod_name):
                full_name = f"netspout_core.{mod_name}"
                mod = __import__(full_name, fromlist=[mod_name])
                self.assertIsNotNone(mod, f"Failed to import {full_name}")

    def test_02_zero_drift_guardrail(self):
        """Ensure scripts/verify_sources.py guardrail passes with 0 divergence."""
        scripts_dir = os.path.join(REPO_ROOT, "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)

        import verify_sources
        self.assertTrue(hasattr(verify_sources, "verify_sources"))
        success = verify_sources.verify_sources()
        self.assertTrue(success, "verify_sources() failed! Architecture drift detected.")

    def test_03_graph_engine_with_canonical_models(self):
        """Validate topology modeling via canonical netspout_core."""
        from netspout_core.models import NodeType, Node, Edge, TopologyState
        from netspout_core.graph_engine import TopologyGraph

        node_a = Node(id="node-core-01", name="Core Switch", type=NodeType.SWITCH, x=100.0, y=100.0)
        node_b = Node(id="node-fw-01", name="Perimeter Firewall", type=NodeType.FIREWALL, x=200.0, y=100.0)
        edge = Edge(id="edge-1", source="node-core-01", target="node-fw-01")

        topo = TopologyState(nodes=[node_a, node_b], edges=[edge])
        graph = TopologyGraph(topo)

        self.assertEqual(len(graph.nodes_by_id), 2)
        fw_nodes = graph.find_nodes_by_type(NodeType.FIREWALL)
        self.assertEqual(len(fw_nodes), 1)
        self.assertEqual(fw_nodes[0].id, "node-fw-01")

    def test_04_scenario_runner_canonical_execution(self):
        """Validate scenario execution using netspout_core scenario runner."""
        from netspout_core.models import NodeType, Node, Edge, TopologyState, ScenarioType
        from netspout_core.scenario_runner import ScenarioRunner

        runner = ScenarioRunner()
        node_client = Node(id="client-01", name="Client", type=NodeType.CLIENT_EXTERNAL, x=0.0, y=0.0)
        node_fw = Node(id="fw-01", name="Firewall", type=NodeType.FIREWALL, x=100.0, y=0.0)
        node_web = Node(id="web-01", name="Web Server", type=NodeType.WEB_SERVER, x=200.0, y=0.0)
        edge1 = Edge(id="e1", source="client-01", target="fw-01")
        edge2 = Edge(id="e2", source="fw-01", target="web-01")
        topo = TopologyState(nodes=[node_client, node_fw, node_web], edges=[edge1, edge2])

        logs = runner.execute_step(topo, ScenarioType.NORMAL_TRAFFIC)
        self.assertIsInstance(logs, list)
        self.assertGreater(len(logs), 0)
        for log in logs:
            self.assertTrue(hasattr(log, "action"))
            self.assertTrue(hasattr(log, "sourcetype"))

    def test_05_snmp_engine_canonical(self):
        """Validate SNMP trap and poll generation via netspout_core."""
        from netspout_core.models import Node, NodeType
        from netspout_core.snmp_engine import SNMPEngine

        snmp = SNMPEngine()
        node = Node(id="switch-01", name="Catalyst-9300", type=NodeType.SWITCH, vendor="cisco", x=0.0, y=0.0)

        # Generate trap
        trap = snmp.generate_trap("linkDown", node)
        self.assertEqual(trap.trap_name, "linkDown")
        self.assertEqual(trap.trap_oid, "1.3.6.1.6.3.1.1.5.3")
        self.assertIn("ifIndex", trap.varbinds)
        self.assertEqual(trap.varbinds["ifOperStatus"], 2)

        # Generate SC4SNMP poll
        polls = snmp.simulate_snmp_poll(node, module="IF-MIB")
        self.assertGreater(len(polls), 0)
        self.assertEqual(polls[0]["sourcetype"], "sc4snmp:metric")
        self.assertEqual(polls[0]["index"], "cisco_mdt_metrics")

    def test_06_gnmi_engine_canonical(self):
        """Validate RFC 7951 compliant OpenConfig telemetry generation via netspout_core."""
        from netspout_core.models import Node, NodeType
        from netspout_core.gnmi_engine import OpenConfigYANGStore

        store = OpenConfigYANGStore()
        node = Node(id="core-router", name="Core-R1", type=NodeType.ROUTER, vendor="cisco", x=0.0, y=0.0)
        tree = store.get_or_create_tree(node)

        self.assertIsInstance(tree, dict)
        self.assertIn("openconfig-interfaces:interfaces", tree)
        self.assertIn("openconfig-platform:components", tree)
        self.assertIn("openconfig-system:system", tree)

        # Validate interface structure
        interfaces = tree["openconfig-interfaces:interfaces"]["interface"]
        self.assertIsInstance(interfaces, list)
        self.assertGreater(len(interfaces), 0)
        self.assertIn("name", interfaces[0])
        self.assertIn("state", interfaces[0])
        self.assertIn("counters", interfaces[0]["state"])

    def test_07_telemetry_dispatcher_canonical(self):
        """Validate TelemetryDispatcher formatting and structures via netspout_core."""
        from netspout_core.telemetry_dispatcher import TelemetryDispatcher, format_rfc5424_message

        dispatcher = TelemetryDispatcher()
        self.assertIn("hec_dispatched", dispatcher.stats)
        self.assertIn("otel_dispatched", dispatcher.stats)

        msg = format_rfc5424_message(
            facility=16,
            severity=6,
            hostname="core-switch-01",
            app_name="netspout",
            procid="101",
            msg_id="LINK_STATUS",
            message="Interface Gi0/0/1 changed state to up"
        )
        self.assertTrue(msg.startswith("<134>1 "))
        self.assertIn("core-switch-01", msg)
        self.assertIn("LINK_STATUS", msg)

    def test_08_splunk_package_integrity(self):
        """Ensure netspout.spl contains netspout_core and is valid."""
        spl_path = os.path.join(REPO_ROOT, "netspout.spl")
        self.assertTrue(os.path.isfile(spl_path), "netspout.spl does not exist!")

        with tarfile.open(spl_path, "r:gz") as tar:
            names = tar.getnames()
            # Verify root app directory
            self.assertTrue(any(n.startswith("netspout/") for n in names))
            # Verify canonical core is packaged in bin/netspout_core/
            for mod_name in CORE_MODULES:
                expected_member = f"netspout/bin/netspout_core/{mod_name}.py"
                self.assertIn(expected_member, names, f"Missing {expected_member} in netspout.spl")
            # Verify no pycache or pyc leaked in
            pyc_files = [n for n in names if n.endswith(".pyc") or "__pycache__" in n]
            self.assertEqual(len(pyc_files), 0, f"Bytecode leaked into package: {pyc_files[:5]}")

    def test_09_backend_api_operational(self):
        """Verify the running backend daemon reports healthy status."""
        url = "http://localhost:8081/api/status"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NetSpoutGate2Tester"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(data.get("status"), "online")
                self.assertIn("node_count", data)
                self.assertIn("simulation_running", data)
                self.assertIn("total_logs", data)
        except Exception as exc:
            self.fail(f"FastAPI simulator daemon query failed: {exc}")


if __name__ == "__main__":
    unittest.main()
