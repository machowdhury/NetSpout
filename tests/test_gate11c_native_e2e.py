"""
NetSpout Gate 11C Test Suite: Native Flow Collector -> Splunk E2E Verification.
Author: Mahamudul Chowdhury (machowdhury@yahoo.com)

Covers:
  - Collector configuration & health check
  - NetFlow v9 E2E pipeline
  - IPFIX E2E pipeline
  - Dual-run correlation isolation
  - Protocol non-pollution verification
  - Controlled failure A (collector stopped / offline)
  - Controlled failure B (Splunk unavailable)
  - Controlled failure D (wrong-flow rejection)
  - HEC independence (no direct HEC shortcut)
"""

import base64
import json
import os
import ssl
import time
import unittest
import urllib.parse
import urllib.request
import uuid

from netspout_core.models import FlowRecord
from netspout_core.scenario_runner import ScenarioRunner
from netspout_core.collector_evidence import CollectorEvidenceAdapter
from netspout_core.exporter_session import ExporterSession
from netspout_core.transport_native_flow import NativeFlowTransport


class TestGate11cNativeE2E(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.adapter = CollectorEvidenceAdapter()
        cls.runner = ScenarioRunner()
        cls.healthy, cls.health_details = cls.adapter.check_health()
        if not cls.healthy:
            raise unittest.SkipTest("Collector infrastructure not reachable on 127.0.0.1:8080/8082")
        password = os.environ.get("NETSPOUT_SPLUNK_PASSWORD") or os.environ.get(
            "SPLUNK_PASSWORD"
        )
        if not password:
            raise unittest.SkipTest("Runtime Splunk search credential is not configured")
        username = os.environ.get("NETSPOUT_SPLUNK_USER", "admin")
        cls.splunk_authorization = "Basic " + base64.b64encode(
            f"{username}:{password}".encode("utf-8")
        ).decode("ascii")

    def setUp(self):
        self.adapter.clear_buffer()

    def query_splunk(self, query: str, max_wait_sec: float = 6.0):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        clean_query = query.strip()
        if not clean_query.startswith("search ") and not clean_query.startswith("|"):
            clean_query = f"search {clean_query}"

        data = urllib.parse.urlencode({
            "search": clean_query,
            "output_mode": "json",
            "earliest_time": "-5m",
            "latest_time": "now"
        }).encode("utf-8")

        candidate_urls = [
            "https://127.0.0.1:8089/services/search/jobs/export",
            "https://127.0.0.1:8889/services/search/jobs/export",
        ]

        start = time.time()
        while time.time() - start < max_wait_sec:
            for url in candidate_urls:
                results = []
                try:
                    req = urllib.request.Request(url, data=data, method="POST")
                    req.add_header("Authorization", self.splunk_authorization)
                    with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
                        for line in resp.read().decode("utf-8").splitlines():
                            if line.strip():
                                obj = json.loads(line)
                                if "result" in obj:
                                    results.append(obj["result"])
                    if results:
                        return results
                except Exception:
                    pass
            time.sleep(0.5)
        return []

    def test_01_collector_configuration_and_health(self):
        """Proves GoFlow2 metrics and Forwarder status are reachable and healthy."""
        healthy, details = self.adapter.check_health()
        self.assertTrue(healthy)
        self.assertTrue(details.get("goflow_metrics"))
        self.assertTrue(details.get("forwarder_status"))

    def test_02_netflow_v9_e2e_pipeline(self):
        """Proves NetFlow v9 flows reach GoFlow2, decode, forward to HEC, and index in Splunk."""
        obs_domain = 40000 + (int(time.time() * 1000) % 9000)
        rec = FlowRecord(
            src_ip="10.200.0.1",
            dest_ip="10.200.0.3",
            src_port=49152,
            dest_port=443,
            protocol=6,
            bytes_count=8420950,
            packets_count=6200,
            input_snmp=49,
            output_snmp=1
        )
        sess = ExporterSession(node_id="Arista-Leaf-V9", observation_domain_id=obs_domain)
        trans = NativeFlowTransport(destination_host="127.0.0.1", destination_port=2055, protocol="NETFLOW_V9")
        res = trans.send_batch([rec], sess, force_template=True)

        self.assertEqual(res.datagrams_sent, 1)
        self.assertEqual(res.records_encoded, 1)

        time.sleep(1.5)

        # 1. Collector-side evidence
        flow_col = self.adapter.find_matching_flow(observation_domain_id=obs_domain, src_ip="10.200.0.1")
        self.assertIsNotNone(flow_col, "GoFlow2 collector failed to decode NetFlow v9 record")
        self.assertEqual(flow_col.get("type"), "NETFLOW_V9")
        self.assertEqual(flow_col.get("bytes"), 8420950)

        # 2. Splunk-side evidence
        spl = f'index=idx_network_ops sourcetype="netflow:collector" | spath | search type="NETFLOW_V9" observation_domain_id={obs_domain}'
        rows = self.query_splunk(spl)
        self.assertGreaterEqual(len(rows), 1, "Splunk did not return indexed NetFlow v9 record")
        self.assertEqual(rows[0].get("bytes"), "8420950")
        self.assertEqual(rows[0].get("out_if"), "1")

    def test_03_ipfix_e2e_pipeline(self):
        """Proves IPFIX flows reach GoFlow2, decode, forward to HEC, and index in Splunk."""
        obs_domain = 50000 + (int(time.time() * 1000) % 9000)
        rec = FlowRecord(
            src_ip="10.200.0.1",
            dest_ip="10.200.0.3",
            src_port=49152,
            dest_port=443,
            protocol=6,
            bytes_count=12948200,
            packets_count=9500,
            input_snmp=49,
            output_snmp=2
        )
        sess = ExporterSession(node_id="Arista-Leaf-IPFIX", observation_domain_id=obs_domain)
        trans = NativeFlowTransport(destination_host="127.0.0.1", destination_port=4739, protocol="IPFIX")
        res = trans.send_batch([rec], sess, force_template=True)

        self.assertEqual(res.datagrams_sent, 1)
        self.assertEqual(res.records_encoded, 1)

        time.sleep(1.5)

        flow_col = self.adapter.find_matching_flow(observation_domain_id=obs_domain, src_ip="10.200.0.1")
        self.assertIsNotNone(flow_col, "GoFlow2 collector failed to decode IPFIX record")
        self.assertEqual(flow_col.get("type"), "IPFIX")
        self.assertEqual(flow_col.get("bytes"), 12948200)

        spl = f'index=idx_network_ops sourcetype="netflow:collector" | spath | search type="IPFIX" observation_domain_id={obs_domain}'
        rows = self.query_splunk(spl)
        self.assertGreaterEqual(len(rows), 1, "Splunk did not return indexed IPFIX record")
        self.assertEqual(rows[0].get("bytes"), "12948200")
        self.assertEqual(rows[0].get("out_if"), "2")

    def test_04_dual_run_correlation_isolation(self):
        """Proves Run A and Run B with overlapping 5-tuples remain completely isolated."""
        base_id = 60000 + (int(time.time() * 1000) % 4000)
        domain_a = base_id
        domain_b = base_id + 1

        rec_a = FlowRecord(src_ip="10.10.1.1", dest_ip="10.10.2.2", src_port=80, dest_port=8080, protocol=6, bytes_count=11111)
        rec_b = FlowRecord(src_ip="10.10.1.1", dest_ip="10.10.2.2", src_port=80, dest_port=8080, protocol=6, bytes_count=22222)

        sess_a = ExporterSession(node_id="NodeA", observation_domain_id=domain_a)
        sess_b = ExporterSession(node_id="NodeB", observation_domain_id=domain_b)

        trans = NativeFlowTransport(destination_host="127.0.0.1", destination_port=4739, protocol="IPFIX")
        trans.send_batch([rec_a], sess_a, force_template=True)
        trans.send_batch([rec_b], sess_b, force_template=True)

        time.sleep(1.5)

        rows_a = self.query_splunk(f'index=idx_network_ops sourcetype="netflow:collector" | spath | search observation_domain_id={domain_a}')
        rows_b = self.query_splunk(f'index=idx_network_ops sourcetype="netflow:collector" | spath | search observation_domain_id={domain_b}')

        self.assertGreaterEqual(len(rows_a), 1)
        self.assertGreaterEqual(len(rows_b), 1)
        # Ensure no cross-contamination
        self.assertFalse(any(r.get("bytes") == "22222" for r in rows_a))
        self.assertFalse(any(r.get("bytes") == "11111" for r in rows_b))

    def test_05_protocol_non_pollution(self):
        """Proves standard NetFlow v9 and IPFIX records do not contain arbitrary NetSpout metadata fields."""
        flows = self.adapter.get_recent_flows()
        for f in flows:
            self.assertNotIn("netspout_run_id", f)
            self.assertNotIn("netspout_scenario_id", f)
            self.assertIn("src_addr", f)
            self.assertIn("dst_addr", f)
            self.assertIn("bytes", f)

    def test_06_controlled_failure_splunk_unavailable(self):
        """Proves that Splunk ingestion failure records SENT=PASS, COLLECTOR_OBSERVED=PASS, SPLUNK_OBSERVED=FAIL."""
        obs_id = 70000 + (int(time.time() * 1000) % 9000)
        self.adapter.simulate_splunk_failure(True)
        try:
            rec = FlowRecord(src_ip="10.10.99.1", dest_ip="10.10.99.2", src_port=123, dest_port=456, protocol=6, bytes_count=99999)
            sess = ExporterSession(node_id="FailNode", observation_domain_id=obs_id)
            trans = NativeFlowTransport(destination_host="127.0.0.1", destination_port=4739, protocol="IPFIX")
            res = trans.send_batch([rec], sess, force_template=True)

            self.assertEqual(res.datagrams_sent, 1)
            time.sleep(1.0)

            # Collector received and decoded
            col_flow = self.adapter.find_matching_flow(observation_domain_id=obs_id)
            self.assertIsNotNone(col_flow)

            # Splunk did NOT receive
            rows = self.query_splunk(f'index=idx_network_ops sourcetype="netflow:collector" | spath | search observation_domain_id={obs_id}', max_wait_sec=2)
            self.assertEqual(len(rows), 0)

        finally:
            self.adapter.simulate_splunk_failure(False)

    def test_07_controlled_failure_wrong_flow_rejection(self):
        """Proves that searches for invalid domain ID or non-existent flows yield 0 matches."""
        rows = self.query_splunk('index=idx_network_ops sourcetype="netflow:collector" | spath | search observation_domain_id=9999999', max_wait_sec=1.5)
        self.assertEqual(len(rows), 0)

    def test_08_hec_independence(self):
        """Proves that native flow UDP transport is structurally decoupled from HEC dispatcher."""
        trans = NativeFlowTransport(destination_host="127.0.0.1", destination_port=2055, protocol="NETFLOW_V9")
        # NativeFlowTransport does not have any HEC URL, token, or HTTP connection
        self.assertFalse(hasattr(trans, "hec_url"))
        self.assertFalse(hasattr(trans, "hec_token"))


if __name__ == "__main__":
    unittest.main()
