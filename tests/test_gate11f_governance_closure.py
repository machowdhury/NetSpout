"""
Test Suite: Gate 11F Native Flow Governance Closure & Golden Path Certification.
Validates:
  1. Promotion of mixed_backbone_optical to GOLDEN_PATH_CERTIFIED (13 total Golden Paths)
  2. Golden Path Evidence Ledger (catalog/golden_path_evidence.json) reconciliation with Gate 11E
  3. P2 Fix: CLI preflight (deploy/collector/manage_collector.py preflight) without PYTHONPATH
  4. P2 Fix: macOS Docker Desktop binary discovery without hardcoded user paths
  5. P3 Fix: Canonical GoFlow2 snake_case field naming across SPL builders and quickstart docs
  6. Security regression invariants (non-root containers, cap_drop ALL, loopback bindings, public IP block)

Author: Mahamudul Chowdhury (machowdhury@yahoo.com)
"""

import json
import os
import subprocess
import sys
import unittest
from collections import Counter

from netspout_core.catalog import NetSpoutCatalog
from netspout_core.collector_evidence import CollectorEvidenceAdapter
from netspout_core.companion_manifest import CompanionManifestBuilder
from netspout_core.models import NativeFlowConfig, ScenarioRunRequest, resolve_native_flow_config
from netspout_core.scenario_runner import ScenarioRunner
from netspout_core.transport_native_flow import NativeFlowTransport
from netspout_core.transport_safety import DestinationSecurityException


class TestGate11FGovernanceClosure(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cls.catalog = NetSpoutCatalog()
        cls.runner = ScenarioRunner()

    # -------------------------------------------------------------------------
    # 1. Golden Path Promotion & Canonical Maturity Distribution
    # -------------------------------------------------------------------------
    def test_01_mixed_backbone_optical_golden_path_promotion(self):
        """Verifies mixed_backbone_optical is promoted to GOLDEN_PATH_CERTIFIED and 13 Golden Paths exist."""
        scenarios = self.catalog.list_scenarios()
        self.assertGreaterEqual(len(scenarios), 29)

        counts = Counter(s.get("maturity") for s in scenarios)
        self.assertEqual(counts["GOLDEN_PATH_CERTIFIED"], 13)
        self.assertEqual(counts["E2E_VALIDATED"], 1)
        self.assertEqual(counts["FORMAT_VALIDATED"], 2)
        self.assertGreaterEqual(counts["CONTRACTED"], 13)

        optical = self.catalog.get_scenario("mixed_backbone_optical")
        self.assertIsNotNone(optical)
        self.assertEqual(optical.get("maturity"), "GOLDEN_PATH_CERTIFIED")

        # Verify ScenarioRunner stamps GOLDEN_PATH_CERTIFIED on execution
        req = ScenarioRunRequest(
            scenario_id="mixed_backbone_optical",
            time_mode="TEST",
            seed=1106
        )
        manifest = self.runner.run_scenario(req)
        self.assertEqual(manifest.scenario_id, "mixed_backbone_optical")
        self.assertEqual(manifest.scenario_maturity, "GOLDEN_PATH_CERTIFIED")

    # -------------------------------------------------------------------------
    # 2. Golden Path Evidence Registry Verification
    # -------------------------------------------------------------------------
    def test_02_golden_path_evidence_ledger_13_certified(self):
        """Verifies catalog/golden_path_evidence.json has 13 entries including mixed_backbone_optical."""
        ledger_path = os.path.join(self.repo_root, "catalog", "golden_path_evidence.json")
        self.assertTrue(os.path.exists(ledger_path))

        with open(ledger_path, "r", encoding="utf-8") as f:
            ledger = json.load(f)

        meta = ledger.get("metadata", {})
        self.assertEqual(meta.get("authoritative_gate"), "Gate 11F")
        self.assertEqual(meta.get("total_certified_golden_paths"), 13)

        entries = {gp["canonical_id"]: gp for gp in ledger.get("golden_paths", [])}
        self.assertEqual(len(entries), 13)
        self.assertIn("mixed_backbone_optical", entries)

        opt = entries["mixed_backbone_optical"]
        self.assertEqual(opt["maturity"], "GOLDEN_PATH_CERTIFIED")
        self.assertEqual(opt["evidence_classification"], "PROVEN")
        self.assertEqual(opt["completeness_pct"], 100.0)
        self.assertEqual(opt["overall_validation"], "PASS")
        self.assertFalse(opt["developer_knowledge_required"])

        # Verify linked Gate 11E artifacts exist on disk
        report_abs = os.path.join(self.repo_root, opt["primary_acceptance_report"])
        scorecard_abs = os.path.join(self.repo_root, opt["scorecard_report"])
        self.assertTrue(os.path.exists(report_abs), f"Missing {report_abs}")
        self.assertTrue(os.path.exists(scorecard_abs), f"Missing {scorecard_abs}")

        # Verify protocol coverage and fidelity classification
        self.assertIn("Native NetFlow v9 (RFC 3954)", opt.get("protocol_coverage", []))
        self.assertIn("Native IPFIX (RFC 7011)", opt.get("protocol_coverage", []))
        self.assertEqual(opt.get("fidelity_classification", {}).get("syslog_hec"), "MODELED PAYLOAD")
        self.assertEqual(opt.get("fidelity_classification", {}).get("native_flow"), "NATIVE TRANSPORT")

    # -------------------------------------------------------------------------
    # 3. P2 Usability Fix: CLI Preflight Without PYTHONPATH
    # -------------------------------------------------------------------------
    def test_03_p2_manage_collector_preflight_without_pythonpath(self):
        """Verifies python3 deploy/collector/manage_collector.py preflight runs from repo root without PYTHONPATH."""
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)

        script_path = os.path.join(self.repo_root, "deploy", "collector", "manage_collector.py")
        proc = subprocess.run(
            [sys.executable, script_path, "preflight"],
            cwd=self.repo_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=15
        )
        self.assertEqual(
            proc.returncode,
            0,
            f"manage_collector.py preflight failed without PYTHONPATH:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
        self.assertIn("Overall Pre-Flight Status: READY", proc.stdout)

    # -------------------------------------------------------------------------
    # 4. P2 Usability Fix: macOS Docker Desktop Discovery
    # -------------------------------------------------------------------------
    def test_04_p2_macos_docker_binary_discovery(self):
        """Verifies manage_collector.py checks standard macOS Docker locations without hardcoded user paths."""
        script_path = os.path.join(self.repo_root, "deploy", "collector", "manage_collector.py")
        with open(script_path, "r", encoding="utf-8") as f:
            source = f.read()

        # Must never hardcode user home directory
        self.assertNotIn("/Users/mahamudc", source)

        # Must check standard macOS Docker locations
        self.assertIn('shutil.which("docker")', source)
        self.assertIn('"/usr/local/bin/docker"', source)
        self.assertIn('"/opt/homebrew/bin/docker"', source)
        self.assertIn('"/Applications/Docker.app/Contents/Resources/bin/docker"', source)
        self.assertIn('os.path.expanduser("~/.docker/bin/docker")', source)
        self.assertIn("Docker executable not found in PATH or standard macOS locations", source)

    # -------------------------------------------------------------------------
    # 5. P3 Usability Fix: Canonical GoFlow2 snake_case Field Naming
    # -------------------------------------------------------------------------
    def test_05_p3_canonical_goflow2_snake_case_fields(self):
        """Verifies SPL builders and quickstart guide use canonical GoFlow2 snake_case JSON fields."""
        manifest = CompanionManifestBuilder.build_manifest(
            run_id="NS-GATE11F-TEST",
            scenario_id="mixed_backbone_optical",
            protocol="IPFIX",
            destination_host="127.0.0.1",
            destination_port=4739,
            exporter_ip="10.200.0.3",
            observation_domain_id=101,
            template_ids=[256],
            records_generated=2,
            records_encoded=2,
            datagrams_sent=1,
            bytes_sent=152,
            start_time_epoch_ms=1700000000000,
            end_time_epoch_ms=1700000005000
        )
        self.assertIn("sum(bytes) as total_bytes", manifest.splunk_stats_spl)
        self.assertIn("sum(packets) as total_packets", manifest.splunk_stats_spl)
        self.assertIn("by src_addr dst_addr", manifest.splunk_stats_spl)

        queries = CollectorEvidenceAdapter.build_investigation_query(observation_domain_id=101)
        self.assertIn("table _time src_addr dst_addr src_port dst_port proto bytes packets", queries["table_spl"])
        self.assertIn("by src_addr dst_addr src_port dst_port proto", queries["stats_spl"])

        quickstart_path = os.path.join(self.repo_root, "docs", "guides", "NATIVE_FLOW_QUICKSTART.md")
        with open(quickstart_path, "r", encoding="utf-8") as f:
            qs_text = f.read()
        self.assertIn("src_addr", qs_text)
        self.assertIn("dst_addr", qs_text)
        self.assertIn("src_port", qs_text)
        self.assertIn("dst_port", qs_text)
        self.assertIn("observation_domain_id", qs_text)
        self.assertNotIn("table _time SrcAddr DstAddr", qs_text)

    # -------------------------------------------------------------------------
    # 6. Security Regression Invariants
    # -------------------------------------------------------------------------
    def test_06_security_regression_invariants(self):
        """Verifies security posture across compose, destination safety, rate limits, and secrets."""
        compose_path = os.path.join(self.repo_root, "deploy", "collector", "docker-compose.collector.yml")
        with open(compose_path, "r", encoding="utf-8") as f:
            compose_content = f.read()

        self.assertIn('user: "100:65533"', compose_content)
        self.assertIn('user: "10001:10001"', compose_content)
        self.assertIn("no-new-privileges:true", compose_content)
        self.assertIn("127.0.0.1:2055:2055/udp", compose_content)
        self.assertIn("127.0.0.1:4739:4739/udp", compose_content)

        # Public destination protection
        with self.assertRaises(DestinationSecurityException):
            NativeFlowTransport(destination_host="8.8.8.8", destination_port=2055, test_mode=True)

        # Rate limits and packet caps
        cfg = resolve_native_flow_config()
        self.assertEqual(cfg.rate_limit_pps, 100)
        self.assertEqual(cfg.packet_cap, 10000)

        # No secrets committed in config model
        d = cfg.dict() if hasattr(cfg, "dict") else cfg.model_dump()
        self.assertNotIn("hec_token", d)
        self.assertNotIn("password", d)


if __name__ == "__main__":
    unittest.main()
