import json
import re
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from netspout_core.catalog import NetSpoutCatalog
from netspout_core.pack_contracts import PackRegistry
from netspout_core.unified_generation import UnifiedGenerationService
from netspout_core.vendor_coverage import (
    CoverageMaturity,
    VendorCoverageService,
)


class TestPhase7CiscoCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = NetSpoutCatalog()
        cls.telemetry = cls.catalog.get_telemetry_catalog()
        cls.registry = PackRegistry.model_validate(
            cls.catalog.get_extension_pack_registry()
        )
        cls.coverage = VendorCoverageService(
            registry=cls.registry,
            source_ids={item["source_id"] for item in cls.telemetry["sources"]},
            integration_ids={
                item["integration_id"] for item in cls.telemetry["integrations"]
            },
        )

    def test_taxonomy_and_readiness_are_computed(self):
        view = self.coverage.view()
        family_names = {item["name"] for item in view["families"]}
        self.assertEqual(
            family_names,
            {
                "Enterprise Networking",
                "Service Provider",
                "Data Center",
                "Security",
                "Observability",
                "Collaboration",
            },
        )
        self.assertGreaterEqual(len(view["products"]), 25)
        self.assertEqual(view["summary"]["products_researched"], 2)
        self.assertEqual(view["summary"]["golden_sources"], 1)
        self.assertEqual(view["summary"]["golden_scenarios"], 1)
        self.assertNotIn("100", json.dumps(view["summary"]))

    def test_ios_xr_product_pack_uses_existing_pack_architecture(self):
        product = next(
            item
            for item in self.coverage.catalog.products
            if item.product_id == "cisco-ios-xr"
        )
        pack = next(
            item for item in self.registry.packs if item.pack_id == product.pack_id
        )
        self.assertEqual(pack.kind.value, "VENDOR_PRODUCT")
        self.assertIn("netspout-rfc5424-generation", pack.dependencies)
        self.assertEqual(
            [item.profile_id for item in pack.declarative_templates],
            ["template-cisco-ios-xr-link-updown"],
        )
        self.assertEqual(
            pack.declarative_templates[0].supported_state_keys,
            ["interface.status"],
        )
        self.assertEqual(len(product.scenario_ids), 1)

    def test_three_contracts_and_maturity_remain_separate(self):
        source = next(
            item
            for item in self.telemetry["sources"]
            if item["source_id"] == "cisco-ios-xr-interface-syslog"
        )
        self.assertEqual(
            source["native_contract"]["verification_state"], "VERIFIED"
        )
        self.assertEqual(
            source["splunk_contract"]["verification_state"], "PARTIALLY_VERIFIED"
        )
        self.assertEqual(
            source["netspout_contract"]["verification_state"], "VERIFIED"
        )
        self.assertEqual(source["splunk_contract"]["cim_mappings"], [])
        sourcetype = source["splunk_contract"]["sourcetypes"][0]
        self.assertEqual(sourcetype["authority"], "NETSPOUT_DEFINED")

    def test_declarative_generator_preserves_documented_structure(self):
        service = UnifiedGenerationService(catalog=self.catalog)
        raw = service._render_declarative_payload(
            "template-cisco-ios-xr-link-updown",
            phase="FAILOVER",
            ordinal=2,
            seed=42,
            entity_id="LC/0/0/CPU0",
            interface_id="HundredGigE0/0/0/1",
        )
        self.assertRegex(
            raw,
            re.compile(
                r"^LC/0/0/CPU0:[A-Z][a-z]{2} \d{2} \d{2}:\d{2}:\d{2}\.000 "
                r": ifmgr\[\d+\]: %PKT_INFRA-LINK-3-UPDOWN : "
                r"Interface HundredGigE0/0/0/1, changed state to Down$"
            ),
        )
        self.assertNotIn("cisco:ios", raw)
        self.assertNotIn("CIM", raw)

    def test_golden_scenario_uses_three_sources_and_shared_state(self):
        scenario = self.coverage.catalog.golden_scenarios[0]
        self.assertTrue(scenario.shared_state)
        self.assertTrue(scenario.native_runtime)
        self.assertTrue(scenario.studio_pack)
        self.assertEqual(len(scenario.source_ids), 3)
        manifest = next(
            item
            for pack in self.registry.packs
            for item in pack.scenarios
            if item.scenario_id == scenario.scenario_id
        )
        self.assertEqual(set(manifest.source_ids), set(scenario.source_ids))
        self.assertEqual(manifest.production_guide_id, scenario.production_guide_id)

    def test_research_required_fails_closed_without_guessed_ta(self):
        product = next(
            item
            for item in self.coverage.catalog.products
            if item.product_id == "cisco-secure-access"
        )
        source = product.sources[0]
        self.assertEqual(product.maturity, CoverageMaturity.RESEARCH_REQUIRED)
        self.assertEqual(source.maturity, CoverageMaturity.RESEARCH_REQUIRED)
        self.assertEqual(source.generator_status, "BLOCKED")
        self.assertIsNone(source.source_id)
        self.assertEqual(source.splunk.integration_ids, [])
        self.assertEqual(source.splunk.sourcetypes, [])

    def test_evidence_is_reference_only_and_has_applicability(self):
        for evidence in self.coverage.catalog.evidence:
            self.assertEqual(evidence.repository_storage, "REFERENCE_ONLY")
            self.assertTrue(evidence.claim)
            self.assertTrue(evidence.reference.startswith("https://"))
            self.assertTrue(evidence.product_applicability)
            self.assertTrue(evidence.verified_date)

    def test_api_exposes_coverage_and_research_required(self):
        client = TestClient(app)
        response = client.get("/api/coverage/cisco")
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["vendor_id"], "cisco")
        self.assertEqual(data["summary"]["source_contracts"], 3)
        product = client.get("/api/coverage/cisco/products/cisco-secure-access")
        self.assertEqual(product.status_code, 200, product.text)
        self.assertEqual(
            product.json()["product"]["maturity"], "RESEARCH_REQUIRED"
        )

    def test_no_cisco_branch_added_to_core_runtime(self):
        root = Path(__file__).resolve().parents[1] / "src" / "netspout_core"
        for filename in ("unified_generation.py", "native_runtime.py"):
            text = (root / filename).read_text(encoding="utf-8")
            self.assertNotRegex(text, r'if\s+vendor\s*==\s*["\']Cisco')


if __name__ == "__main__":
    unittest.main()
