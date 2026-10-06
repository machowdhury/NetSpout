"""Phase 2 telemetry catalog schema and trust-boundary tests."""

import copy
import json
import os
import sys
import unittest

from pydantic import ValidationError


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from netspout_core.catalog import NetSpoutCatalog
from netspout_core.catalog_contracts import TelemetryCatalog


CATALOG_PATH = os.path.join(REPO_ROOT, "catalog", "telemetry_catalog.json")


class TestPhase2TelemetryCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(CATALOG_PATH, "r", encoding="utf-8") as catalog_file:
            cls.raw = json.load(catalog_file)

    def validate(self, mutation=None):
        candidate = copy.deepcopy(self.raw)
        if mutation:
            mutation(candidate)
        return TelemetryCatalog.model_validate(candidate)

    def test_01_catalog_schema_validates(self):
        catalog = self.validate()
        self.assertEqual(len(catalog.sources), 10)
        self.assertEqual(len(catalog.integrations), 4)
        self.assertEqual(len(catalog.source_manifests), 3)

    def test_02_invalid_provenance_is_rejected(self):
        def mutate(candidate):
            candidate["sources"][0]["provenance"][0] = "PLAUSIBLE_LOOKING"

        with self.assertRaises(ValidationError):
            self.validate(mutate)

    def test_03_unsupported_source_fails_closed(self):
        source = self.validate().sources[-1]
        self.assertEqual(source.verification_state.value, "UNSUPPORTED")
        self.assertEqual(source.netspout_contract.runtime_status, "UNSUPPORTED")
        self.assertFalse(source.splunk_contract.sourcetypes)

        def mutate(candidate):
            candidate["sources"][-1]["netspout_contract"]["runtime_status"] = "READY"

        with self.assertRaises(ValidationError):
            self.validate(mutate)

    def test_04_research_required_source_cannot_be_ready(self):
        source = self.validate().sources[-2]
        self.assertEqual(source.verification_state.value, "RESEARCH_REQUIRED")

        def mutate(candidate):
            candidate["sources"][-2]["netspout_contract"]["runtime_status"] = "AVAILABLE"

        with self.assertRaises(ValidationError):
            self.validate(mutate)

    def test_05_duplicate_source_identity_is_rejected(self):
        def mutate(candidate):
            duplicate = copy.deepcopy(candidate["sources"][0])
            duplicate["source_id"] = "another-source-id"
            candidate["sources"].append(duplicate)

        with self.assertRaisesRegex(ValidationError, "duplicate source identity"):
            self.validate(mutate)

    def test_06_official_sourcetype_requires_splunk_evidence(self):
        def mutate(candidate):
            candidate["sources"][-2]["splunk_contract"]["sourcetypes"] = [
                {
                    "name": "invented:official",
                    "authority": "SPLUNK_DOCUMENTED",
                    "evidence_ids": ["EVID-NETSPOUT-CONTRACT-SCHEMA"],
                }
            ]

        with self.assertRaisesRegex(ValidationError, "lacks Splunk evidence"):
            self.validate(mutate)

    def test_07_netspout_sourcetype_is_explicitly_classified(self):
        catalog = self.validate()
        claims = [
            claim
            for source in catalog.sources
            for claim in source.splunk_contract.sourcetypes
            if claim.authority.value == "NETSPOUT_DEFINED"
        ]
        self.assertEqual({claim.name for claim in claims}, {
            "openconfig:gnmi:telemetry",
            "netspout:agentic:activity",
        })

        def mutate(candidate):
            candidate["sources"][4]["splunk_contract"]["sourcetypes"][0][
                "evidence_ids"
            ] = []

        with self.assertRaisesRegex(ValidationError, "lacks NetSpout schema evidence"):
            self.validate(mutate)

    def test_08_source_integration_relationships_are_symmetric(self):
        catalog = self.validate()
        source = next(
            item
            for item in catalog.sources
            if item.source_id == "opentelemetry-otlp"
        )
        self.assertEqual(
            source.splunk_contract.integration_ids,
            ["splunk-otel-hec-exporter"],
        )

        def mutate(candidate):
            candidate["integrations"][1]["supported_source_ids"] = []

        with self.assertRaisesRegex(ValidationError, "relationship is not symmetric"):
            self.validate(mutate)

    def test_09_source_manifest_relationships_validate(self):
        catalog = self.validate()
        manifest = next(
            item
            for item in catalog.source_manifests
            if item.scenario_id == "openconfig_mdt_streaming"
        )
        self.assertEqual(manifest.source_ids, ["openconfig-gnmi-interfaces"])

        def mutate(candidate):
            candidate["source_manifests"][0]["source_ids"] = ["missing-source"]

        with self.assertRaisesRegex(ValidationError, "unknown values"):
            self.validate(mutate)

    def test_10_catalog_loader_filters_and_summarizes(self):
        catalog = NetSpoutCatalog(catalog_dir=os.path.join(REPO_ROOT, "catalog"))
        self.assertEqual(
            len(catalog.list_telemetry_sources(domain="supply-chain")), 1
        )
        self.assertEqual(
            len(
                catalog.list_telemetry_sources(
                    verification_state="RESEARCH_REQUIRED"
                )
            ),
            1,
        )
        summary = catalog.get_telemetry_catalog_summary()
        self.assertEqual(summary["source_count"], 10)
        self.assertEqual(summary["sourcetype_counts"]["SPLUNK_DOCUMENTED"], 1)
        self.assertEqual(summary["sourcetype_counts"]["NETSPOUT_DEFINED"], 2)

    def test_11_unknown_source_and_integration_are_absent(self):
        catalog = NetSpoutCatalog(catalog_dir=os.path.join(REPO_ROOT, "catalog"))
        self.assertIsNone(catalog.get_telemetry_source("not-a-source"))
        self.assertIsNone(catalog.get_splunk_integration("not-an-integration"))

    def test_12_industry_associations_are_nonduplicating_metadata(self):
        catalog = self.validate()
        for source in catalog.sources:
            self.assertIsInstance(source.applicable_industries, list)
            self.assertEqual(len(source.applicable_industries), len(set(source.applicable_industries)))

    def test_13_legacy_addon_view_delegates_to_authoritative_catalog(self):
        modal_path = os.path.join(
            REPO_ROOT, "frontend", "src", "components", "VendorAddonsModal.tsx"
        )
        with open(modal_path, "r", encoding="utf-8") as modal_file:
            content = modal_file.read()
        self.assertIn("/catalog/splunk-integrations", content)
        self.assertIn("unverified", content)
        self.assertIn("presentation layer", content)
        self.assertNotIn("const VENDOR_ADDONS", content)
        self.assertNotIn("Live CIM Normalization Test", content)


if __name__ == "__main__":
    unittest.main()
